import uuid
from dotenv import load_dotenv
import requests, os, json

from models import NotionPageJson
from .notion_page_exporter import NotionPageExporter
import datetime
from tqdm import tqdm

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

        page_list = []

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
        ).json()
        page_list.extend(response.get("results", []))

        while response.get("has_more", False):
            response = requests.post(
                url=search_url,
                json={**payload, "start_cursor": response.get("next_cursor")},
                headers=headers,
            ).json()
            page_list.extend(response.get("results", []))

        return page_list
    
    def get_pages(self, show_progress: bool = False) -> list[NotionPageJson]:
        page_list = self.list_workspace_pages()
        export_list: list[NotionPageJson] = []
        progress = tqdm(page_list, desc="Fetching Notion pages", unit="page") if show_progress else None
        iterator = progress if progress is not None else page_list

        for page in iterator:
            if page["object"] == "page":
                if page["last_edited_time"] > self.most_recent_timestamp:
                    export_list.append(self.NOTION_PAGE_EXPORTER.parse_page(page["id"]))
                else:
                    # Get the title text from the first title element when available
                    title_property = page.get("properties", {}).get("title", {})
                    title_elements = title_property.get("title") or []
                    if not title_elements:
                        for prop in page.get("properties", {}).values():
                            if isinstance(prop, dict) and prop.get("type") == "title":
                                title_elements = prop.get("title") or []
                                break
                    first_element = title_elements[0] if title_elements else {}
                    title_text = first_element.get("plain_text") or first_element.get("text", {}).get("content", "Untitled")
                    message = f"skipping {title_text}: {page['last_edited_time']} < {self.most_recent_timestamp}"
                    if progress is not None:
                        progress.write(message)
                    else:
                        print(message)

        if progress is not None:
            progress.close()

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
    

