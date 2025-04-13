from fastapi import FastAPI
from app.api import router
from app.vector_store import create_vector_store
from fastapi.middleware.cors import CORSMiddleware
from app.watch_changes import start_change_watchers

app = FastAPI(title="HR ChatBot with Gemini")

# Allow requests from your frontend (React, Angular, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://localhost:3000"] for tighter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    print("Indexing data into vector DB...")
    create_vector_store()
    print("Starting MongoDB change stream watchers...")
    start_change_watchers()

app.include_router(router)
