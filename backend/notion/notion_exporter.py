import uuid
from dotenv import load_dotenv
import requests, os, json

from models import NotionPageJson
from .notion_page_exporter import NotionPageExporter
import datetime

class NotionExporter:
    def __init__(self, timer_file_path="notion_last_export.txt"):
        
        self.NOTION_TOKEN = os.getenv("NOTION_TOKEN")
        self.BASE_URL = "https://api.notion.com/v1"
        self.NOTION_PAGE_EXPORTER = NotionPageExporter()
        self.timer_file_path = timer_file_path
        self.most_recent_timestamp = self.load_timestamp()
    
    def save_timestamp(self, timestamp):
        # save to file
        with open(self.timer_file_path, "w") as f:
            f.write(timestamp)

    def get_timestamp(self) -> str:
        current_time = datetime.datetime.now(tz = datetime.timezone.utc).isoformat(timespec='milliseconds')
        return current_time

    def load_timestamp(self) -> str:
        # load from file
        try:
            with open(self.timer_file_path, "r") as f:
                timestamp = f.read()
                return timestamp
        except FileNotFoundError:
            return "1970-01-01T00:00:00.000Z"

    def list_workspace_pages(self):
        search_url = f"{self.BASE_URL}/search"
        
        headers = {
            "accept": "application/json", 
            "content-type": "application/json", 
            "authorization": f"Bearer {self.NOTION_TOKEN}", 
            "Notion-Version": "2025-09-03"
        }
        sort = {
            "direction": "descending",
            "timestamp": "last_edited_time"
        }
        payload = { "page_size": 100, "sort": sort }

        response = requests.post(
            url=search_url,
            json=payload,
            headers=headers,
        )
        return response.json()
    
    def get_pages(self) -> list[NotionPageJson]:
        page_list = self.list_workspace_pages()
        export_list: list[NotionPageJson] = []
        for page in page_list["results"]:
            if page["object"] == "page":
                if page["last_edited_time"] > self.most_recent_timestamp:
                    export_list.append(self.NOTION_PAGE_EXPORTER.parse_page(page["id"]))
                else:
                    # Get the title text from the first title element
                    title_text = page["properties"]["title"]["title"][0]["text"]["content"] if page["properties"]["title"]["title"] else "Untitled"
                    print(f"skipping {title_text}: {page["last_edited_time"]} < {self.most_recent_timestamp}")
        return export_list        



# test method
if __name__ == "__main__":
    load_dotenv()
    notion_file_path = os.getenv("NOTION_TIMER_FILE", "notion_last_export.txt")
    notion_exporter = NotionExporter(timer_file_path=notion_file_path)
    current_time = notion_exporter.get_timestamp()
    pages = notion_exporter.get_pages()
    for page in pages:
        print(page)
    # try:
    #     vector_db_instance.store_notion_pages(pages)
    #     notion_exporter.save_timestamp(current_time)
    # except Exception as e:
    #     print(e)
    

