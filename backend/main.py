from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="RAG API", version="1.0.0")

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "RAG API is running", "status": "healthy"}

# Query endpoint
@app.post("/query")
async def query_endpoint():
    return {
        "message": "Query endpoint working",
    }

# Upload single message endpoint
@app.post("/uploadMessage")
async def upload_message_endpoint():
    return {
        "message": "Upload message endpoint working",
        "status": "success"
    }

# Upload multiple messages endpoint
@app.post("/uploadMessages")
async def upload_messages_endpoint():
    return {
        "message": "Upload bulk endpoint working",
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7007)
