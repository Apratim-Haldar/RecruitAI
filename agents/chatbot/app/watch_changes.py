import threading
from pymongo import MongoClient
from bson import ObjectId
from app.config import MONGO_URI, VECTOR_DIR, GEMINI_API_KEY
from langchain.vectorstores import Chroma
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)
client = MongoClient(MONGO_URI)
db = client["GENAI"]

def embed_and_add(doc_type: str, data: dict):
    vectordb = Chroma(persist_directory=VECTOR_DIR, embedding_function=embedding)

    if doc_type == "candidate":
        job_id = str(data["jobPost"])
        job_info = db["jobposts"].find_one({"_id": ObjectId(job_id)})
        job_title = job_info["title"] if job_info else "Unknown Role"
        job_location = job_info["location"] if job_info else "Unknown Location"

        text = (
            f"Candidate: {data['firstName']} {data['lastName']} applied for the role of {job_title} in {job_location}. "
            f"Email: {data['email']}, Status: {data['status']}, Experience: {data.get('experience', 'NA')} years. "
            f"Resume Summary: {data.get('resume_details', 'N/A')}. "
            f"AI Evaluation: {data.get('aiEvaluation', {})}"
        )
        doc = Document(page_content=text, metadata={"type": "candidate", "id": str(data["_id"])})

    elif doc_type == "jobpost":
        text = (
            f"JobPost: {data['title']} at {data['location']} ({data['jobType']}). "
            f"Openings: {data['noOfOpenings']}, Deadline: {data['deadline']}. "
            f"Description: {data.get('description', 'N/A')}"
        )
        doc = Document(page_content=text, metadata={"type": "jobpost", "id": str(data["_id"])})

    vectordb.add_documents([doc])
    vectordb.persist()


def watch_collection(collection_name: str, doc_type: str):
    collection = db[collection_name]
    with collection.watch() as stream:
        for change in stream:
            if change["operationType"] in ["insert", "update", "replace"]:
                doc_id = change["documentKey"]["_id"]
                full_doc = collection.find_one({"_id": ObjectId(doc_id)})
                if full_doc:
                    embed_and_add(doc_type, full_doc)

def start_change_watchers():
    t1 = threading.Thread(target=watch_collection, args=("applications", "candidate"), daemon=True)
    t2 = threading.Thread(target=watch_collection, args=("jobposts", "jobpost"), daemon=True)
    t1.start()
    t2.start()
