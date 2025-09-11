from llama_index.core import VectorStoreIndex, Document
from llama_index.core.settings import Settings
from llama_index.core.schema import BaseNode, NodeWithScore
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.ollama import Ollama
import chromadb

from typing import List

from models import MessageJson, MessageMetadata, MessageData, FormattedSource

class VectorDB:
    def __init__(self):
        self.embed_model = Settings.embed_model = HuggingFaceEmbedding(
            model_name="Qwen/Qwen3-Embedding-0.6B",
        )
        
        # Configure local LLM (currently via lm studio)
        Settings.llm = Ollama(
            model="gpt-oss:20b", 
            request_timeout=60.0, 
            base_url="http://localhost:7008"
        )
        
        self.db = chromadb.PersistentClient(path="./chroma_db")
        self.chroma_collection = self.db.get_or_create_collection("bmai_embeddings")
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        self.index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)
            
    def store_message(self, message: MessageJson) -> None:
        messageDoc = self.build_message(message)
        self.index.insert(messageDoc)

    def store_message_list(self, messages: List[MessageJson]) -> None:
        message_list = [self.build_message(message) for message in messages]
        self.index.insert_nodes(message_list)
        # for message in messages:
        #     self.index.insert(self.build_message(message))

    def retrieve_message(self, query: str, server_id: str, similarity_top_k: int = 7) -> List[Document]:
        """Retrieve relevant messages based on a query"""
        filters = MetadataFilters(filters=[ExactMatchFilter(key="serverId", value=server_id)])
        retriever = self.index.as_retriever(similarity_top_k=similarity_top_k, filters=filters)
        nodes = retriever.retrieve(query)
        
        # Convert nodes back to documents
        documents = []
        for node in nodes:
            doc = Document(
                text=node.text,
                metadata=node.metadata
            )
            documents.append(doc)
        
        print(documents)
        
        return documents
    
    def llm_response(self, query: str, server_id: str, similarity_top_k: int = 7) -> tuple[str, List[FormattedSource]]:
        """Generate an LLM response based on retrieved messages"""

        print(self.retrieve_message(query, server_id))
        
        filters = MetadataFilters(filters=[ExactMatchFilter(key="serverId", value=server_id)])
        query_engine = self.index.as_query_engine(
            similarity_top_k=similarity_top_k,
            response_mode="compact",
            filters=filters
        )
        
        response = query_engine.query(query)
        # print(response)

        sources = response.source_nodes

        sourceList = []
        for source in sources:
            sourceList.append(self.format_source(source))

        return (str(response), sourceList)
    
    def build_message(self, message: MessageJson) -> Document:
        doc_text = f"Channel: {message.data.channelName}\n"
        doc_text += f"Sender: {message.data.senderNickname if message.data.senderNickname else message.data.senderUsername}\n"
        doc_text += f"Content: {message.data.content}"
        
        doc = Document(
            text=doc_text,
            metadata=message.metadata.model_dump()
        )
        
        return doc
    
    def format_source(self, node: NodeWithScore) -> FormattedSource:
        """Convert NodeWithScore to FormattedSource model with channel, sender, content, channelId, messageId"""
        
        # Extract text content and parse it
        text_lines = node.node.text.split('\n')
        
        # Parse the structured text
        channel = ""
        sender = ""
        content = ""
        
        for line in text_lines:
            if line.startswith("Channel: "):
                channel = line.replace("Channel: ", "")
            elif line.startswith("Sender: "):
                sender = line.replace("Sender: ", "")
            elif line.startswith("Content: "):
                content = line.replace("Content: ", "")
        
        # Extract metadata
        channel_id = node.node.metadata.get('channelId', '')
        message_id = node.node.metadata.get('messageId', '')
        sender_id = node.node.metadata.get('senderId', '')

        print(str(FormattedSource(
            channel=channel,
            sender=sender if sender != "None" else None,
            senderId=sender_id,
            content=content,
            channelId=channel_id,
            messageId=message_id
        )))
        
        return FormattedSource(
            channel=channel,
            sender=sender if sender != "None" else None,
            senderId=sender_id,
            content=content,
            channelId=channel_id,
            messageId=message_id
        )

vector_db_instance = VectorDB()