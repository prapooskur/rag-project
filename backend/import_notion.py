import argparse
import requests
import json
from datetime import datetime, date
from notion.notion_exporter import NotionExporter
from notion.notion_page_exporter import NotionPageExporter
from dotenv import load_dotenv

#slopmaxxed script.

def upload_notion_pages_to_api(pages, api_url):
    """Upload Notion pages to the RAG API endpoint"""
    endpoint = f"{api_url}/uploadNotionDocs"
    
    # Convert pages to JSON serializable format
    def make_serializable(obj):
        """Recursively convert datetimes to ISO strings and pydantic models to dicts."""
        # Pydantic models have model_dump
        if hasattr(obj, "model_dump"):
            return make_serializable(obj.model_dump())
        # dicts: process values
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        # lists/tuples: process items
        if isinstance(obj, (list, tuple)):
            return [make_serializable(v) for v in obj]
        # dates/datetimes: convert to ISO
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        # fallback: return as-is (json will error if not serializable)
        return obj

    pages_data = [make_serializable(p) for p in pages]
    
    try:
        response = requests.post(
            endpoint,
            json=pages_data,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minute timeout for large uploads
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result.get('message', 'Upload successful')}")
            return True
        else:
            print(f"❌ API request failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {error_detail}")
            except:
                print(f"Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The upload may still be processing.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to API at {api_url}")
        print("Make sure the RAG API server is running.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Notion pages to RAG API")
    parser.add_argument(
        "--api-url", 
        default="http://localhost:7007",
        help="Base URL of the RAG API server (default: http://localhost:7007)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading"
    )
    parser.add_argument(
        "--timer-file",
        default="notion_last_export.txt",
        help="Path to the timer file for tracking last export time (default: notion_last_export.txt)"
    )
    
    args = parser.parse_args()
    
    load_dotenv()
    
    print(f"🔄 Starting Notion import to {args.api_url}")
    
    try:
        notion_exporter = NotionExporter(timer_file_path=args.timer_file)
        current_time = notion_exporter.get_timestamp()
        pages = notion_exporter.get_pages()
        
        print(f"📄 Found {len(pages)} pages to process")
        
        if args.dry_run:
            print("🔍 Dry run mode - showing pages that would be uploaded:")
            for i, page in enumerate(pages, 1):
                if hasattr(page, 'data') and hasattr(page.data, 'title'):
                    title = page.data.title
                elif isinstance(page, dict) and 'data' in page:
                    title = page['data'].get('title', 'Unknown')
                else:
                    title = 'Unknown'
                print(f"  {i}. {title}")
            print("No pages were uploaded (dry run mode)")
        else:
            success = upload_notion_pages_to_api(pages, args.api_url)
            
            if success:
                notion_exporter.save_timestamp(current_time)
                print("✅ Import completed successfully!")
            else:
                print("❌ Import failed - timestamp not updated")
                exit(1)
                
    except Exception as e:
        print(f"❌ Error during import: {e}")
        exit(1)
    