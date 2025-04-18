import google.generativeai as genai
from app.config import GEMINI_API_KEY
from app.vector_store import get_vector_store

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

session_memory = {}  # Dict[str, List[Dict[str, str]]]

def ask_gemini(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text

def ask_chatbot(query: str, session_id: str = "default"):
    retriever = get_vector_store().as_retriever(search_type="similarity", k=8)
    context_docs = retriever.invoke(query)

    jobposts = [doc.page_content for doc in context_docs if doc.metadata.get("type") == "jobpost"]
    candidates = [doc.page_content for doc in context_docs if doc.metadata.get("type") == "candidate"]

    job_context = "\n\n".join(jobposts)
    candidate_context = "\n\n".join(candidates)

    if session_id not in session_memory:
        session_memory[session_id] = [] 

    history = "\n\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in session_memory[session_id]])

    final_prompt = f"""
You are an intelligent HR assistant AI helping a recruiter.
Answer user questions based only on the data below.
DO NOT mention internal MongoDB IDs. Focus on real job titles, descriptions, or candidate names.

### JOB POST CONTEXT:
{job_context if job_context else "No relevant job post data."}

### CANDIDATE CONTEXT:
{candidate_context if candidate_context else "No relevant candidate data."}

### CHAT HISTORY:
{history}

### NEW QUESTION:
User: {query}

Assistant:
"""
    answer = ask_gemini(final_prompt)

    # Update session memory
    session_memory[session_id].append({"role": "user", "content": query})
    session_memory[session_id].append({"role": "assistant", "content": answer})

    return answer
