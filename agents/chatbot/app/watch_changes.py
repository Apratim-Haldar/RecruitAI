import threading
from pymongo import MongoClient
from bson import ObjectId
from app.config import MONGO_URI, VECTOR_DIR, GEMINI_API_KEY
from langchain.vectorstores import Chroma
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)
client = MongoClient(MONGO_URI)
db = client["your_db"]

def embed_and_add(doc_type: str, data: dict):
    vectordb = Chroma(persist_directory=VECTOR_DIR, embedding_function=embedding)
    if doc_type == "candidate":
        text = f"Candidate: {data['firstName']} {data['lastName']}, Email: {data['email']}, Status: {data['status']}, Experience: {data.get('experience', 'NA')} years, AI Eval: {data.get('aiEvaluation', {})}"
        doc = Document(page_content=text, metadata={"type": "candidate", "id": str(data["_id"])})
        vectordb.add_documents([doc])
    elif doc_type == "jobpost":
        text = f"JobPost: {data['title']} at {data['location']} ({data['jobType']}), Openings: {data['noOfOpenings']}, Deadline: {data['deadline']}"
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
    t1 = threading.Thread(target=watch_collection, args=("candidates", "candidate"), daemon=True)
    t2 = threading.Thread(target=watch_collection, args=("jobposts", "jobpost"), daemon=True)
    t1.start()
    t2.start()
