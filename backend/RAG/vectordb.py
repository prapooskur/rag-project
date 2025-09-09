from llama_index.core import VectorStoreIndex, Document
from llama_index.core.settings import Settings
from llama_index.core.schema import BaseNode

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
import chromadb

from typing import List

from models import MessageJson, MessageMetadata, MessageData

class VectorDB:
    def __init__(self):
        self.embed_model = Settings.embed_model = HuggingFaceEmbedding(
            model_name="Qwen/Qwen3-Embedding-0.6B",
        )
        
        # Configure local LLM (currently via lm studio)
        Settings.llm = OpenAI(
            api_base="http://localhost:1234/v1",
            api_key="lm-studio",  
            model="gpt-oss-20b",
            temperature=0.8
        )
        
        self.db = chromadb.PersistentClient(path="./chroma_db")
        self.chroma_collection = self.db.get_or_create_collection("bmai_embeddings")
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        self.index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)
            
    def store_message(self, message: MessageJson) -> None:
        messageDoc = self.build_message(message)
        self.index.insert(messageDoc)

    def store_message_list(self, messages: List[MessageJson]) -> None:
        messageDocs = []
        for message in messages:
            messageDocs.append(self.build_message(message))
        
        self.index.insert(messageDocs)

    def retrieve_message(self) -> List[Document]:
        pass
    
    def build_message(self, message: MessageJson) -> Document:
        doc_text = f"Channel: {message.data.channelName}\n"
        doc_text += f"Sender: {message.data.senderNickname}\n"
        doc_text += f"Content: {message.data.content}"
        
        doc = Document(
            text=doc_text,
            metadata=message.metadata.model_dump()
        )
        
        return doc
        

vector_db_instance = VectorDB()