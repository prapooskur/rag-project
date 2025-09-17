from dotenv import load_dotenv
import requests, os, json
from typing import Dict, List, Any

class NotionPageExporter:
    def __init__(self):
        
        load_dotenv() # todo see if this can be removed
        self.NOTION_TOKEN = os.getenv("NOTION_TOKEN")
        self.BASE_URL = "https://api.notion.com/v1"

    def parse_page(self, page_id: str) -> str:
        """Parse a Notion page and return its content as markdown"""
        blocks = self.get_page_blocks(page_id)
        markdown_content = []
        
        for block in blocks.get('results', []):
            block_markdown = self.parse_block(block)
            if block_markdown:
                markdown_content.append(block_markdown)
        
        return '\n\n'.join(markdown_content)
    
    def get_page_blocks(self, page_id: str) -> Dict[str, Any]:
        """Get all blocks from a Notion page"""
        blocks_url = f"{self.BASE_URL}/blocks/{page_id}/children"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.NOTION_TOKEN}",
            "Notion-Version": "2025-09-03"
        }
        
        response = requests.get(url=blocks_url, headers=headers)
        return response.json()
    
    def parse_block(self, block: Dict[str, Any]) -> str:
        """Convert a Notion block to markdown"""
        block_type = block.get('type')
        
        if not block_type:
            return ""
        
        # Handle different block types
        if block_type == 'paragraph':
            return self._parse_paragraph(block)
        elif block_type == 'heading_1':
            return self._parse_heading(block, 1)
        elif block_type == 'heading_2':
            return self._parse_heading(block, 2)
        elif block_type == 'heading_3':
            return self._parse_heading(block, 3)
        elif block_type == 'bulleted_list_item':
            return self._parse_bulleted_list_item(block)
        elif block_type == 'numbered_list_item':
            return self._parse_numbered_list_item(block)
        elif block_type == 'to_do':
            return self._parse_todo(block)
        elif block_type == 'code':
            return self._parse_code(block)
        elif block_type == 'quote':
            return self._parse_quote(block)
        elif block_type == 'divider':
            return "---"
        elif block_type == 'image':
            return self._parse_image(block)
        elif block_type == 'table':
            return self._parse_table(block)
        else:
            # For unsupported block types, try to extract text if available
            return self._extract_text_from_block(block)
    
    def _parse_rich_text(self, rich_text: List[Dict]) -> str:
        """Parse Notion rich text to markdown"""
        result = ""
        for text_obj in rich_text:
            text = text_obj.get('plain_text', '')
            annotations = text_obj.get('annotations', {})
            
            # Apply formatting
            if annotations.get('bold'):
                text = f"**{text}**"
            if annotations.get('italic'):
                text = f"*{text}*"
            if annotations.get('strikethrough'):
                text = f"~~{text}~~"
            if annotations.get('code'):
                text = f"`{text}`"
            
            # Handle links
            if text_obj.get('href'):
                text = f"[{text}]({text_obj['href']})"
            
            result += text
        
        return result
    
    def _parse_paragraph(self, block: Dict) -> str:
        """Parse paragraph block"""
        rich_text = block.get('paragraph', {}).get('rich_text', [])
        return self._parse_rich_text(rich_text)
    
    def _parse_heading(self, block: Dict, level: int) -> str:
        """Parse heading block"""
        heading_key = f'heading_{level}'
        rich_text = block.get(heading_key, {}).get('rich_text', [])
        heading_text = self._parse_rich_text(rich_text)
        return f"{'#' * level} {heading_text}"
    
    def _parse_bulleted_list_item(self, block: Dict, indent_level: int = 0) -> str:
        """Parse bulleted list item with support for nested items"""
        rich_text = block.get('bulleted_list_item', {}).get('rich_text', [])
        item_text = self._parse_rich_text(rich_text)
        
        # Create indentation for nested items
        indent = "  " * indent_level
        result = f"{indent}- {item_text}"
        
        # Check for nested items (children)
        if block.get('has_children', False):
            children = self._get_block_children(block.get('id'))
            for child in children:
                if child.get('type') == 'bulleted_list_item':
                    child_markdown = self._parse_bulleted_list_item(child, indent_level + 1)
                    result += "\n" + child_markdown
                elif child.get('type') == 'numbered_list_item':
                    child_markdown = self._parse_numbered_list_item(child, indent_level + 1)
                    result += "\n" + child_markdown
        
        return result
    
    def _parse_numbered_list_item(self, block: Dict, indent_level: int = 0) -> str:
        """Parse numbered list item with support for nested items"""
        rich_text = block.get('numbered_list_item', {}).get('rich_text', [])
        item_text = self._parse_rich_text(rich_text)
        
        # Create indentation for nested items
        indent = "  " * indent_level
        result = f"{indent}1. {item_text}"
        
        # Check for nested items (children)
        if block.get('has_children', False):
            children = self._get_block_children(block.get('id'))
            for child in children:
                if child.get('type') == 'bulleted_list_item':
                    child_markdown = self._parse_bulleted_list_item(child, indent_level + 1)
                    result += "\n" + child_markdown
                elif child.get('type') == 'numbered_list_item':
                    child_markdown = self._parse_numbered_list_item(child, indent_level + 1)
                    result += "\n" + child_markdown
        
        return result
    
    def _parse_todo(self, block: Dict) -> str:
        """Parse to-do block"""
        todo_data = block.get('to_do', {})
        rich_text = todo_data.get('rich_text', [])
        checked = todo_data.get('checked', False)
        item_text = self._parse_rich_text(rich_text)
        checkbox = "[x]" if checked else "[ ]"
        return f"- {checkbox} {item_text}"
    
    def _parse_code(self, block: Dict) -> str:
        """Parse code block"""
        code_data = block.get('code', {})
        rich_text = code_data.get('rich_text', [])
        language = code_data.get('language', '')
        code_text = self._parse_rich_text(rich_text)
        return f"```{language}\n{code_text}\n```"
    
    def _parse_quote(self, block: Dict) -> str:
        """Parse quote block"""
        rich_text = block.get('quote', {}).get('rich_text', [])
        quote_text = self._parse_rich_text(rich_text)
        return f"> {quote_text}"
    
    def _parse_image(self, block: Dict) -> str:
        """Parse image block"""
        image_data = block.get('image', {})
        caption_text = ""
        
        if 'caption' in image_data:
            caption_text = self._parse_rich_text(image_data['caption'])
        
        # Handle different image types
        if 'external' in image_data:
            url = image_data['external']['url']
        elif 'file' in image_data:
            url = image_data['file']['url']
        else:
            return f"![{caption_text}](image_url_not_found)"
        
        return f"![{caption_text}]({url})"
    
    def _parse_table(self, block: Dict) -> str:
        """Parse table block by getting its rows"""
        table_id = block.get('id')
        if not table_id:
            return "[Table parsing error: no table ID]"
        
        # Get table rows
        table_rows = self._get_table_rows(table_id)
        if not table_rows:
            return "[Empty table]"
        
        markdown_table = []
        is_first_row = True
        
        for row_block in table_rows:
            if row_block.get('type') == 'table_row':
                row_markdown = self._parse_table_row(row_block)
                markdown_table.append(row_markdown)
                
                # Add header separator after first row
                if is_first_row:
                    cells = row_block.get('table_row', {}).get('cells', [])
                    separator = '|' + '|'.join([' --- ' for _ in cells]) + '|'
                    markdown_table.append(separator)
                    is_first_row = False
        
        return '\n'.join(markdown_table)
    
    def _get_table_rows(self, table_id: str) -> List[Dict]:
        """Get all rows from a table"""
        blocks_url = f"{self.BASE_URL}/blocks/{table_id}/children"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.NOTION_TOKEN}",
            "Notion-Version": "2025-09-03"
        }
        
        try:
            response = requests.get(url=blocks_url, headers=headers)
            data = response.json()
            return data.get('results', [])
        except Exception:
            return []
    
    def _parse_table_row(self, block: Dict) -> str:
        """Parse table row block"""
        cells = block.get('table_row', {}).get('cells', [])
        parsed_cells = []
        
        for cell in cells:
            # Each cell contains rich text
            cell_text = self._parse_rich_text(cell) if cell else ""
            # Escape pipe characters in cell content
            cell_text = cell_text.replace('|', '\\|')
            parsed_cells.append(f" {cell_text} ")
        
        return '|' + '|'.join(parsed_cells) + '|'

    def _extract_text_from_block(self, block: Dict) -> str:
        """Extract text from unsupported block types"""
        block_type = block.get('type')
        block_data = block.get(block_type, {})
        
        if 'rich_text' in block_data:
            return self._parse_rich_text(block_data['rich_text'])
        
        return f"[Unsupported block type: {block_type}]"

    def list_workspace_pages(self) -> json:
        search_url = f"{self.BASE_URL}/search"
        payload = { "page_size": 100 }
        headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {self.NOTION_TOKEN}", "Notion-Version": "2025-09-03"}

        response = requests.post(
            url=search_url,
            json=payload,
            headers=headers,
        )
        return response.json()

# test method
if __name__ == "__main__":
    notion_exporter = NotionPageExporter()
    print(json.dumps(notion_exporter.list_workspace_pages(), indent=2))