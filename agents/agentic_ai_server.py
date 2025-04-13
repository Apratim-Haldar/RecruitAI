import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import asyncio

app = FastAPI()

# --- MongoDB Configuration ---
MONGO_URI = "mongodb+srv://enbodyAdmin:O0r1MK2YLQ7QPkec@atlascluster.mz70pny.mongodb.net/GENAI"
client = AsyncIOMotorClient(MONGO_URI)
db_name = "vectorDB"
db = client[db_name]
applications_col = db["applications"]
jobposts_col = db["jobposts"]

# --- Global Vector Index Variables ---
faiss_index = None  # This will hold our FAISS index (in-memory)
document_metadata = []  # Metadata corresponding to each indexed document

# --- Load an Embedding Model ---
# Using a Sentence Transformers model for creating semantic embeddings.
model = SentenceTransformer('all-mpnet-base-v2')

# --- Helper Functions to Build Document Strings ---
def create_document_from_candidate(candidate: dict) -> str:
    """
    Create a text representation (document) for a candidate.
    """
    candidate_text = f"Candidate Name: {candidate.get('firstName', '')} {candidate.get('lastName', '')}. "
    candidate_text += f"Status: {candidate.get('status', '')}. Applied at: {candidate.get('appliedAt', {}).get('$date', 'N/A')}. "
    ai_eval = candidate.get("aiEvaluation", {})
    candidate_text += f"Match percentage: {ai_eval.get('matchPercentage', 'N/A')}. "
    candidate_text += f"Resume details: {candidate.get('resume_details', '')}"
    return candidate_text

def create_document_from_jobpost(jobpost: dict) -> str:
    """
    Create a text representation (document) for a job post.
    """
    job_text = f"Job Title: {jobpost.get('title', '')}. "
    job_text += f"Description: {jobpost.get('description', '')}. "
    job_text += f"Location: {jobpost.get('location', '')}."
    return job_text

# --- Request/Response Pydantic Models ---
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str

# --- Build the Vector Index on Startup ---
async def build_faiss_index():
    """
    Load candidate and job post data from MongoDB, compute embeddings, and index them in FAISS.
    """
    global faiss_index, document_metadata

    documents = []
    document_metadata = []

    # Retrieve candidate data.
    candidates_cursor = applications_col.find({})
    candidates = await candidates_cursor.to_list(length=None)
    for candidate in candidates:
        doc = create_document_from_candidate(candidate)
        documents.append(doc)
        document_metadata.append({
            "type": "candidate",
            "id": str(candidate.get("_id")),
            "snippet": doc[:200]  # store first 200 characters as a snippet
        })

    # Retrieve job post data.
    jobposts_cursor = jobposts_col.find({})
    jobposts = await jobposts_cursor.to_list(length=None)
    for job in jobposts:
        doc = create_document_from_jobpost(job)
        documents.append(doc)
        document_metadata.append({
            "type": "job",
            "id": str(job.get("_id")),
            "snippet": doc[:200]
        })

    # Compute semantic embeddings for all documents.
    embeddings = model.encode(documents, convert_to_numpy=True)
    dimension = embeddings.shape[1]

    # Build a FAISS index with L2 (Euclidean) distance.
    faiss_index_local = faiss.IndexFlatL2(dimension)
    faiss_index_local.add(embeddings)
    faiss_index = faiss_index_local
    print(f"FAISS index built with {faiss_index.ntotal} documents.")

@app.on_event("startup")
async def startup_event():
    # Build the FAISS index on startup (this will block until the index is built).
    await build_faiss_index()

# --- REST API Endpoint ---
@app.post("/chatbot", response_model=QueryResponse)
async def chatbot_endpoint(query_request: QueryRequest):
    global faiss_index, document_metadata
    if faiss_index is None:
        raise HTTPException(status_code=500, detail="Search index not initialized.")
    
    query_text = query_request.query
    query_embedding = model.encode([query_text], convert_to_numpy=True)
    
    k = 3  # Number of nearest neighbors to retrieve.
    distances, indices = faiss_index.search(query_embedding, k)
    
    response_parts = []
    for idx in indices[0]:
        if idx < len(document_metadata):
            meta = document_metadata[idx]
            response_parts.append(
                f"Type: {meta['type']} | ID: {meta['id']} | Snippet: {meta['snippet']}"
            )
    
    response_text = "\n".join(response_parts)
    return QueryResponse(response=response_text)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
