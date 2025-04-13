import google.generativeai as genai
from app.config import GEMINI_API_KEY
from app.vector_store import get_vector_store

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def ask_gemini(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text

def ask_chatbot(query: str):
    retriever = get_vector_store().as_retriever(search_type="similarity", k=5)
    context_docs = retriever.get_relevant_documents(query)
    context = "\n\n".join(doc.page_content for doc in context_docs)
    final_prompt = f"""You are an HR assistant AI. Answer based only on the data below.

Context:
{context}

Question:
{query}

Answer:"""
    return ask_gemini(final_prompt)
