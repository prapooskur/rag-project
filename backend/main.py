from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from RAG.vectordb import vector_db_instance
from contextlib import asynccontextmanager

# lifecycle stuff
database = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    global database
    try:
        # Startup: Initialize the database connection
        database = vector_db_instance
        print("Database initialized successfully")
        
        yield  # This separates startup from shutdown
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        raise
    finally:
        # Shutdown: Clean up resources if needed
        database = None
        print("Database connection closed")

app = FastAPI(title="RAG API", version="1.0.0", lifespan=lifespan)

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "RAG API is running", "status": "healthy"}

# Query endpoint
@app.post("/query")
async def query_endpoint(message: ):
    database.store_message(message)
    return {
        "message": "Query endpoint working",
    }

# Upload single message endpoint
@app.post("/uploadMessage")
async def upload_message_endpoint():
    database.sto
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
    uvicorn.run(app, host="127.0.0.1", port=7007)
