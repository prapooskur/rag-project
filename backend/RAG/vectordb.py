from llama_index.core import VectorStoreIndex, Document
from llama_index.core.settings import Settings
from llama_index.core.schema import BaseNode

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from typing import List

class VectorDB:
    def __init__(self):
        self.embed_model = Settings.embed_model = HuggingFaceEmbedding(
            model_name="Qwen/Qwen3-Embedding-0.6B"
        )
        Settings.llm = None
        
        self.db = chromadb.PersistentClient(path="./chroma_db")
        self.chroma_collection = self.db.get_or_create_collection("bmai_discord_embeddings")
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        self.index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)
        
    def store_message(self) -> None:
        pass

    def retrieve_message(self) -> List[Document]:
        pass

vector_db_instance = VectorDB()