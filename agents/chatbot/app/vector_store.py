from app.data_loader import load_candidates, load_job_posts
from langchain.vectorstores import Chroma
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import GEMINI_API_KEY, VECTOR_DIR

embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)

def format_documents():
    candidates = load_candidates()
    jobposts = load_job_posts()
    docs = []

    for c in candidates:
        text = f"Candidate: {c['firstName']}, JobPostID:{c['jobPost']}, {c['lastName']}, Email: {c['email']}, Status: {c['status']}, Experience: {c.get('experience', 'NA')} years, resume_details: {c['resume_details']}, AI Eval: {c.get('aiEvaluation', {})}"
        docs.append(Document(page_content=text, metadata={"type": "candidate", "id": str(c["_id"]), "jobPostId": str(c["jobPost"])}))

    for j in jobposts:
        text = f"JobPost: {j['title']} at {j['location']} ({j['jobType']}), Openings: {j['noOfOpenings']}, Deadline: {j['deadline']}, Description: {j.get('description', '')}"
        docs.append(Document(page_content=text, metadata={"type": "jobpost", "id": str(j["_id"]), "description": j.get('description', '')}))

    return docs

def create_vector_store():
    docs = format_documents()
    vectordb = Chroma.from_documents(documents=docs, embedding=embedding, persist_directory=VECTOR_DIR)
    vectordb.persist()
    return vectordb

def get_vector_store():
    return Chroma(persist_directory=VECTOR_DIR, embedding_function=embedding)
