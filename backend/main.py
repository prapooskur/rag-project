from dotenv.main import load_dotenv
from fastapi import FastAPI, HTTPException
from typing import List
from RAG.vectordb import vector_db_instance
from contextlib import asynccontextmanager
from models import MessageData, MessageMetadata, MessageJson, QueryRequest, NotionPageJson, DeleteMessageRequest

# lifecycle stuff
database = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    
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
        if database is not None:
            database.shutdown()
        database = None
        print("Database connection closed")

app = FastAPI(title="RAG API", version="1.0.0", lifespan=lifespan)

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "RAG API is running", "status": "healthy"}

# Query endpoint
@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        if database is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Database not initialized",
                    "status": "error"
                }
            )
        
        if request.response_type == "retrieval":
            # Return raw retrieved documents
            retrieved_docs = database.retrieve_discord(
                query=request.query,
                server_id=request.serverId,
            )
            
            # Convert documents to a serializable format
            results = []
            for doc in retrieved_docs:
                results.append({
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', None)  # Include score if available
                })
            
            return {
                "query": request.query,
                "results": results,
                "total_results": len(results),
                "response_type": "retrieval",
                "status": "success"
            }
        
        else:  # Default to LLM response
            # Generate LLM response based on retrieved context
            llm_response_tuple = database.llm_response(
                query=request.query,
                server_id=request.serverId,
            )
            
            response_text, sources = llm_response_tuple
            
            return {
                "query": request.query,
                "response": response_text,
                "sources": sources,
                "response_type": "llm",
                "status": "success"
            }
            
    except Exception as e:
        print(f"Query error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Query failed: {str(e)}",
                "status": "error"
            }
        )

# Upload single message endpoint
@app.post("/uploadMessage")
async def upload_message_endpoint(message: MessageJson):
    try:
        database.store_discord_message(message)
        return {
            "message": "Message uploaded successfully",
            "status": "success"
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to upload message: {str(e)}",
                "status": "error"
            }
        )

# Upload multiple messages endpoint
@app.post("/uploadMessages")
async def upload_messages_endpoint(message_list: List[MessageJson]):
    try:
        database.store_discord_message_list(message_list)
        return {
            "message": f"Successfully uploaded {len(message_list)} messages",
            "status": "success"
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to upload messages: {str(e)}",
                "status": "error"
            }
        )

@app.post("/updateMessage")
async def update_message_endpoint(old_message: MessageJson, new_message: MessageJson):
    if old_message.metadata.messageId != new_message.metadata.messageId:
        print(f"Message ID mismatch: old_message ID = {old_message.metadata.messageId}, new_message ID = {new_message.metadata.messageId}")
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Message ID mismatch: old_message ID = {old_message.metadata.messageId}, new_message ID = {new_message.metadata.messageId}",
                "status": "error"
            }
        )
    try:
        database.delete_discord_messages(old_message.metadata.messageId)
        database.store_discord_message(new_message)
        return {
            "message": f"Successfully updated message with ID {old_message.metadata.messageId}",
            "status": "success"
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to update message with ID {old_message.metadata.messageId}",
                "status": "error"
            }
        )
    
@app.post("/deleteMessage")
async def delete_message_endpoint(request: DeleteMessageRequest):
    try:
        database.delete_discord_messages(request.id)
        return {
            "message": f"Successfully deleted message with ID {request.id}",
            "status": "success"
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to delete message with ID {request.id}",
                "status": "error"
            }
        )


# Upload single Notion page endpoint
@app.post("/uploadNotionDoc")
async def upload_notion_doc_endpoint(notion_page: NotionPageJson):
    try:
        if database is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Database not initialized",
                    "status": "error"
                }
            )
        
        database.store_notion_page(notion_page)
        return {
            "message": "Notion document uploaded successfully",
            "status": "success"
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to upload Notion document: {str(e)}",
                "status": "error"
            }
        )

# Upload multiple Notion pages endpoint
@app.post("/uploadNotionDocs")
async def upload_notion_docs_endpoint(notion_pages: List[NotionPageJson]):
    try:
        if database is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Database not initialized",
                    "status": "error"
                }
            )
        
        database.store_notion_pages(notion_pages)
        return {
            "message": f"Successfully uploaded {len(notion_pages)} Notion documents",
            "status": "success"
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to upload Notion documents: {str(e)}",
                "status": "error"
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7007)
