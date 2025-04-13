from fastapi import APIRouter
from pydantic import BaseModel
from app.chatbot import ask_chatbot

router = APIRouter()

class Query(BaseModel):
    question: str

@router.post("/ask")
def ask_api(query: Query):
    answer = ask_chatbot(query.question)
    return {"answer": answer}
