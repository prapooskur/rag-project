import asyncio
import os

from dotenv.main import load_dotenv
from fastapi import FastAPI, HTTPException
from typing import List
from RAG.vectordb import vector_db_instance
from contextlib import asynccontextmanager
from models import MessageData, MessageMetadata, MessageJson, QueryRequest, NotionPageJson, DeleteMessageRequest, SourceType
from notion.notion_exporter import NotionExporter

# lifecycle stuff
database = None
notion_import_task = None


def _get_notion_interval() -> int:
    """Return the configured Notion import interval in minutes (defaults to daily)."""
    raw_value = os.getenv("NOTION_INTERVAL", 1440)
    if raw_value is None:
        return 1440

    try:
        minutes = int(raw_value)
        # Negative values disable the importer
        return max(minutes, 0)
    except ValueError:
        print(f"Invalid NOTION_IMPORT_INTERVAL_MINUTES value '{raw_value}'. Falling back to 1440 minutes.")
        return 1440


async def import_notion(timer_file_path: str) -> int:
    """Import Notion pages once and persist them to the vector database."""
    if database is None:
        print("Skipping Notion import: database not initialized")
        return 0

    exporter = NotionExporter(timer_file_path=timer_file_path)
    current_time = exporter.get_timestamp()

    try:
        pages = await asyncio.to_thread(exporter.get_pages)

        if not pages:
            print("No new Notion pages to import.")
            exporter.save_timestamp(current_time)
            return 0

        await asyncio.to_thread(database.store_notion_pages, pages)
        exporter.save_timestamp(current_time)
        print(f"Imported {len(pages)} Notion pages into the vector database.")
        return len(pages)
    except Exception as exc:
        print(f"Error during Notion import: {exc}")
        return 0


async def notion_import_worker(interval_minutes: int, timer_file_path: str) -> None:
    """Background task that periodically imports Notion pages."""
    try:
        if interval_minutes <= 0:
            print("Notion import worker disabled via interval configuration.")
            return
        
        await import_notion(timer_file_path)

        wait_seconds = max(interval_minutes, 1) * 60
        while True:
            await asyncio.sleep(wait_seconds)
            try:
                await import_notion(timer_file_path)
            except Exception as exc:
                print(f"Notion import worker encountered an error and will retry after {wait_seconds} seconds: {exc}")
    except asyncio.CancelledError:
        print("Notion import worker cancelled.")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    
    global database
    global notion_import_task
    try:
        # Startup: Initialize the database connection
        database = vector_db_instance
        print("Database initialized successfully")
        interval_minutes = _get_notion_interval()
        timer_file_path = os.getenv("NOTION_TIMER_FILE", "notion_last_export.txt")

        notion_import_task = asyncio.create_task(
            notion_import_worker(interval_minutes=interval_minutes, timer_file_path=timer_file_path)
        )

        if interval_minutes <= 0:
            print("Notion import background task will perform a single startup run and then stop (interval <= 0).")
        else:
            print(f"Notion import background task scheduled every {interval_minutes} minutes.")
        
        yield  # This separates startup from shutdown
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        raise
    finally:
        # Shutdown: Clean up resources if needed
        if notion_import_task is not None:
            notion_import_task.cancel()
            try:
                await notion_import_task
            except asyncio.CancelledError:
                pass
        notion_import_task = None

        if database is not None:
            database.shutdown()
        database = None
        print("Database connection closed")

app = FastAPI(title="RAG API", version="1.0.0", lifespan=lifespan)

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "RAG API is running", "status": "healthy"}

@app.get("/stats")
async def stats_endpoint(server_id: str | None = None):
    try:
        if database is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Database not initialized",
                    "status": "error"
                }
            )

        stats = database.get_stats(server_id=server_id)
        return {
            "status": "success",
            **stats
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Stats endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to retrieve stats: {e}",
                "status": "error"
            }
        )

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
        # Generate LLM response based on retrieved context
        enabled_sources = []
        if request.enable_discord:
            enabled_sources.append(SourceType.DISCORD)
        if request.enable_notion:
            enabled_sources.append(SourceType.NOTION)
        llm_response_tuple = database.llm_response(
            query=request.query,
            server_id=request.serverId,
            enabled_sources=enabled_sources,
        )

        print(llm_response_tuple)
        
        response_text, sources = llm_response_tuple
        
        return {
            "query": request.query,
            "response": response_text,
            "sources": sources,
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
        database.delete_discord_message(old_message.metadata.messageId)
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
        database.delete_discord_message(request.id)
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
