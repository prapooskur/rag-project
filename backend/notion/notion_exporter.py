import uuid
from dotenv import load_dotenv
import requests, os, json
from notion_page_exporter import NotionPageExporter

class NotionExporter:
    def __init__(self):
        
        self.NOTION_TOKEN = os.getenv("NOTION_TOKEN")
        self.BASE_URL = "https://api.notion.com/v1"
        self.NOTION_PAGE_EXPORTER = NotionPageExporter()

    def list_workspace_pages(self) -> json:
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
    
    def get_pages(self) -> list[str]:
        page_list = self.list_workspace_pages()
        export_list = []
        for page in page_list["results"]:
            if page["object"] == "page":
                export_list.append(self.NOTION_PAGE_EXPORTER.parse_page(page["id"]))
        return export_list
                
                # self.parse_page(page)
        



# test method
if __name__ == "__main__":
    load_dotenv()
    notion_exporter = NotionExporter()
    pages = notion_exporter.get_pages()
    for page in pages:
        print(page)

