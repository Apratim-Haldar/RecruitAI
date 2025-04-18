from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.chatbot import ask_chatbot
from pymongo import MongoClient
import pdfplumber
import google.generativeai as genai
import os
import io
import json
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
from typing import Dict, List
from uuid import uuid4

router = APIRouter()
conversation_sessions: Dict[str, List[str]] = {}
class Query(BaseModel):
    question: str
    session_id: str = None

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# Configure MongoDB
client = MongoClient("mongodb+srv://enbodyAdmin:O0r1MK2YLQ7QPkec@atlascluster.mz70pny.mongodb.net/GENAI")
db = client['GENAI']
collection = db['jobposts']


def extract_job_data_with_gemini(text):
    prompt = f"""
Extract structured job data from the following text. Return it in JSON format with these fields:
- title (job title)
- description (detailed job description)
- jobType (full-time, part-time, contract, etc.)
- location (job location)
- noOfOpenings (number of positions available, default to 1 if not specified)
- deadline (application deadline date in YYYY-MM-DD format, default to 30 days from now if not specified)

Include any additional relevant fields too. Skip fields that are missing. Do not include explanations.

Text:
\"\"\"
{text}
\"\"\"
JSON:
"""
    response = model.generate_content(prompt)
    try:
        # The output will be a JSON-like string
        content = response.text.strip()
        # Clean up the content to ensure it's valid JSON
        if content.startswith('```json'):
            content = content.split('```json')[1].split('```')[0].strip()
        elif content.startswith('```'):
            content = content.split('```')[1].split('```')[0].strip()
            
        data = json.loads(content) if content.startswith('{') else {}
        
        # Set default values for required fields
        if 'noOfOpenings' not in data or not data['noOfOpenings']:
            data['noOfOpenings'] = 1
        else:
            # Ensure noOfOpenings is an integer
            try:
                data['noOfOpenings'] = int(data['noOfOpenings'])
            except:
                data['noOfOpenings'] = 1
                
        if 'deadline' not in data or not data['deadline']:
            # Set default deadline to 30 days from now
            data['deadline'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
        if 'status' not in data:
            data['status'] = 'open'
            
        return data
    except Exception as e:
        print(f"Error parsing response: {e}")
        return {}


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), user_id: str = None):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        contents = await file.read()
        
        # Save the file temporarily to handle potential PDF issues
        temp_file_path = "temp_pdf.pdf"
        with open(temp_file_path, "wb") as f:
            f.write(contents)
        
        try:
            # Try to open with pdfplumber with error handling
            with pdfplumber.open(temp_file_path) as pdf:
                pages_text = []
                for page in pdf.pages:
                    try:
                        text = page.extract_text()
                        if text:
                            pages_text.append(text)
                    except Exception as page_error:
                        print(f"Error extracting text from page: {page_error}")
                        continue
                
                full_text = "\n".join(pages_text)
                
                if not full_text:
                    raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        except Exception as pdf_error:
            print(f"Error opening PDF with pdfplumber: {pdf_error}")
            raise HTTPException(status_code=400, detail="Invalid PDF format or corrupted file")
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
        extracted_data = extract_job_data_with_gemini(full_text)
        
        if not extracted_data.get("title") or not extracted_data.get("description"):
            raise HTTPException(status_code=400, detail="Essential fields missing from PDF")
        
        # Format the data to match JobPosts schema
        job_post_data = {
            "title": extracted_data.get("title"),
            "description": extracted_data.get("description"),
            "jobType": extracted_data.get("jobType", "full-time"),
            "location": extracted_data.get("location", "Remote"),
            "noOfOpenings": extracted_data.get("noOfOpenings", 1),
            "deadline": extracted_data.get("deadline"),
            "status": "open",
            "createdAt": datetime.now(),
            # Use the user_id from the request
            "createdBy": ObjectId(user_id)
        }
        
        # Insert into MongoDB
        result = collection.insert_one(job_post_data)
        
        return {
            "message": "Job post created successfully from PDF",
            "job_id": str(result.inserted_id),
            "data": {
                "title": job_post_data["title"],
                "description": job_post_data["description"][:100] + "..." if len(job_post_data["description"]) > 100 else job_post_data["description"],
                "jobType": job_post_data["jobType"],
                "location": job_post_data["location"],
                "noOfOpenings": job_post_data["noOfOpenings"],
                "deadline": job_post_data["deadline"]
            }
        }
    
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@router.post("/ask")
def ask_api(query: Query):
    session_id = query.session_id or str(uuid4())
    context = conversation_sessions.get(session_id, [])
    
    # Get answer with context
    answer = ask_chatbot(query.question, session_id)
    
    # Update context (store last 5 exchanges)
    context.append(f"Q: {query.question}")
    context.append(f"A: {answer}")
    conversation_sessions[session_id] = context[-10:]

    return { "answer": answer }
