import google.generativeai as genai
from app.config import GEMINI_API_KEY
from app.vector_store import get_vector_store

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def ask_gemini(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text

def ask_chatbot(query: str):
    retriever = get_vector_store().as_retriever(search_type="similarity", k=6)
    context_docs = retriever.invoke(query)  # Updated from get_relevant_documents()

    jobposts = [doc.page_content for doc in context_docs if doc.metadata.get("type") == "jobpost"]
    candidates = [doc.page_content for doc in context_docs if doc.metadata.get("type") == "candidate"]

    job_context = "\n\n".join(jobposts)
    candidate_context = "\n\n".join(candidates)

    final_prompt = f"""
You are an intelligent HR assistant AI helping a recruiter.
Answer user questions based only on the data below.
DO NOT mention internal MongoDB IDs. Focus on real job titles, descriptions, or candidate names.

- Respond professionally and clearly.
- If the question is vague, try your best to infer.
- If you don't find matching data, say so politely.

### JOB POST CONTEXT:
{job_context if job_context else "No relevant job post data."}

### CANDIDATE CONTEXT:
{candidate_context if candidate_context else "No relevant candidate data."}

### QUESTION:
{query}

### ANSWER:
"""

    return ask_gemini(final_prompt)
