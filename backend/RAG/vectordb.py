from llama_index.core import VectorStoreIndex, Document
from llama_index.core.settings import Settings
from llama_index.core.schema import BaseNode, NodeWithScore
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.postprocessor import SentenceTransformerRerank

import os

from typing import List, Union
from models import MessageJson, MessageMetadata, MessageData, FormattedSource, SourceType, NotionPageJson, FormattedNotionSource

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class VectorDB:
    def __init__(self):        
        # Configure local LLM and embedding model (currently via ollama, todo make this more agnostic)
        self.embed_model = Settings.embed_model = HuggingFaceEmbedding(
            model_name="Qwen/Qwen3-Embedding-0.6B",
            query_instruction="Given a Discord search query, retrieve relevant passages that answer the query"
        )

        # reranker (prune irrelevant context)
        # todo test effectiveness
        self.rerank_model = SentenceTransformerRerank(
            model="BAAI/bge-reranker-v2-m3",
            top_n=5
        )

        # Choose LLM based on environment variables
        if os.getenv("OPENAI_API_KEY"):
            from llama_index.llms.openai import OpenAI
            Settings.llm = OpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
                api_base=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=os.getenv("OPENAI_API_KEY"),
                max_retries=3,
                request_timeout=60.0,
            )

            self.model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        
        else:
            from llama_index.llms.ollama import Ollama
            Settings.llm = Ollama(
                model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                request_timeout=60.0, 
            )

            self.model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
        
        PG_USER = os.getenv("POSTGRES_USER", "postgres")
        PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
        PG_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
        PG_PORT = os.getenv("POSTGRES_PORT", "5432")

        connection_string = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/postgres"
        async_connection_string = f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/postgres"

        # for stats and relational writes
        self._engine = create_engine(connection_string)
        self._ensure_relational_tables()

        self.discord_vector_store = PGVectorStore.from_params(
            connection_string=connection_string,
            async_connection_string=async_connection_string,

            table_name="discord_embeddings",
            embed_dim=1024,
            use_jsonb=True,
            hnsw_kwargs={
                "hnsw_m": 16,
                "hnsw_ef_construction": 64,
                "hnsw_ef_search": 40,
                "hnsw_dist_method": "vector_cosine_ops",
            },
            hybrid_search=True
        )
        
        self.notion_vector_store = PGVectorStore.from_params(
            connection_string=connection_string,
            async_connection_string=async_connection_string,

            table_name="notion_embeddings",
            embed_dim=1024,
            use_jsonb=True,
            hnsw_kwargs={
                "hnsw_m": 16,
                "hnsw_ef_construction": 64,
                "hnsw_ef_search": 40,
                "hnsw_dist_method": "vector_cosine_ops",
            },
            hybrid_search=True
        )
        
        self.messages_index = VectorStoreIndex.from_vector_store(vector_store=self.discord_vector_store)
        self.notion_index = VectorStoreIndex.from_vector_store(vector_store=self.notion_vector_store)

    def get_stats(self, server_id: str | None = None) -> dict[str, int | str]:
        """Return basic document counts for Discord messages and Notion pages."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")

        stats: dict[str, int | str] = {}

        try:
            with self._engine.connect() as conn:
                discord_table = conn.execute(text("SELECT to_regclass('data_discord_embeddings')")).scalar()
                if discord_table:
                    total_discord = conn.execute(text("SELECT COUNT(*) FROM data_discord_embeddings")).scalar_one()
                    stats["discord_messages_total"] = int(total_discord)

                    if server_id:
                        server_discord = conn.execute(
                            text("SELECT COUNT(*) FROM data_discord_embeddings WHERE metadata_ ->> 'serverId' = :server_id"),
                            {"server_id": server_id}
                        ).scalar_one()
                        stats["discord_messages_for_server"] = int(server_discord)
                        stats["server_id"] = server_id
                else:
                    print("Discord embeddings table does not exist")
                    stats["discord_messages_total"] = 0
                    if server_id:
                        stats["discord_messages_for_server"] = 0
                        stats["server_id"] = server_id

                notion_table = conn.execute(text("SELECT to_regclass('data_notion_embeddings')")).scalar()
                if notion_table:
                    notion_count = conn.execute(text("SELECT COUNT(*) FROM data_notion_embeddings")).scalar_one()
                    stats["notion_documents_total"] = int(notion_count)
                else:
                    print("Notion embeddings table does not exist")
                    stats["notion_documents_total"] = 0

        except SQLAlchemyError as exc:
            print(f"Error retrieving vector store stats: {exc}")
            raise

        return stats
    
    def _ensure_relational_tables(self) -> None:
        """Create auxiliary Postgres tables required by the API if missing."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")

        create_table_stmt = text(
            """
            CREATE TABLE IF NOT EXISTS discord_text (
                message_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                server_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_username TEXT NOT NULL,
                sender_nickname TEXT,
                channel_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        index_statements = [
            text("CREATE INDEX IF NOT EXISTS idx_discord_text_server_channel ON discord_text (server_id, channel_id)"),
            text("CREATE INDEX IF NOT EXISTS idx_discord_text_sender ON discord_text (sender_id)"),
            text("CREATE INDEX IF NOT EXISTS idx_discord_text_created_at ON discord_text (created_at)")
        ]

        try:
            with self._engine.begin() as conn:
                conn.execute(create_table_stmt)
                for stmt in index_statements:
                    conn.execute(stmt)
        except SQLAlchemyError as exc:
            print(f"Error ensuring discord_text table exists: {exc}")
            raise
    
    def shutdown(self) -> None:
        """Properly unload models and clean up resources"""
        try:
            # Unload the embedding model
            if hasattr(self, 'embed_model') and self.embed_model is not None:
                # For HuggingFace models, we need to clear the model
                if hasattr(self.embed_model, '_model') and self.embed_model._model is not None:
                    del self.embed_model._model
                self.embed_model = None
                print("Embedding model unloaded successfully")
            
            # Unload the reranking model
            if hasattr(self, 'rerank_model') and self.rerank_model is not None:
                # For SentenceTransformer models, clear the internal model
                if hasattr(self.rerank_model, '_model') and self.rerank_model._model is not None:
                    del self.rerank_model._model
                self.rerank_model = None
                print("Reranking model unloaded successfully")
            
            # Clear Settings references
            Settings.embed_model = None
            Settings.llm = None
            
            # Force garbage collection to free memory
            import gc
            gc.collect()

            if hasattr(self, '_engine') and self._engine is not None:
                self._engine.dispose()
                self._engine = None
                print("Database engine disposed successfully")
            
            print("VectorDB shutdown completed successfully")
            
        except Exception as e:
            print(f"Error during VectorDB shutdown: {e}")
            
    def delete_notion_page_by_id(self, page_id: str) -> None:
        """Delete existing Notion page documents with the specified page ID"""
        try:
            # Create a filter to match documents with the specific page ID
            filters = MetadataFilters(filters=[ExactMatchFilter(key="pageId", value=page_id)])
            
            # Delete documents from the vector store that match the filter
            self.notion_vector_store.delete_nodes(filters=filters)
           
            print(f"Deleted existing documents for page ID: {page_id}")
        except Exception as e:
            print(f"Warning: Could not delete existing documents for page ID {page_id}: {e}")

    def delete_all_notion_documents(self):
        """Delete all documents from the Notion vector store"""
        try:
            # Clear all documents from the Notion table
            self.notion_vector_store.delete_nodes()
            print("Successfully deleted all Notion documents from the vector store")
        except Exception as e:
            print(f"Error deleting all Notion documents: {e}")
            raise
            
    def store_notion_page(self, page: NotionPageJson) -> None:
        """Store a single Notion page in the vector database"""
        # Delete any existing documents with the same page ID
        self.delete_notion_page_by_id(page.metadata.pageId)
        
        # Insert the new document
        page_doc = self.build_notion_page(page)
        self.notion_index.insert(page_doc)

    def store_notion_pages(self, pages: List[NotionPageJson]) -> None:
        """Store a list of Notion pages in the vector database"""
        # Delete existing documents for each page ID
        for page in pages:
            self.delete_notion_page_by_id(page.metadata.pageId)
        
        # Insert all new documents
        page_list = [self.build_notion_page(page) for page in pages]
        self.notion_index.insert_nodes(page_list)
    
    def retrieve_notion(self, query: str) -> List[Document]:
        """Retrieve relevant Notion pages based on a query"""
        retriever = self.notion_index.as_retriever()
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
    
    def store_discord_message(self, message: MessageJson) -> None:
        message_id = message.metadata.messageId

        filters = MetadataFilters(filters=[ExactMatchFilter(key="messageId", value=message_id)])
        existing_nodes = self.discord_vector_store.get_nodes(filters=filters)

        # insert to vector store if not exists
        if existing_nodes:
            print(f"Message {message_id} already exists in vector index; skipping insert")
        else:
            messageDoc = self.build_message(message)
            self.messages_index.insert(messageDoc)

        # insert to postgres table if not exists
        with self._engine.begin() as conn:
            insert_query = text("""
                INSERT INTO discord_text (server_id, channel_id, message_id, sender_id, sender_username, sender_nickname, channel_name, content, created_at)
                VALUES (:server_id, :channel_id, :message_id, :sender_id, :sender_username, :sender_nickname, :channel_name, :content, :created_at)
                ON CONFLICT (message_id) DO NOTHING;
            """)
            conn.execute(insert_query, {
                "server_id": message.metadata.serverId,
                "channel_id": message.metadata.channelId,
                "message_id": message.metadata.messageId,
                "sender_id": message.metadata.senderId,
                "sender_username": message.data.senderUsername,
                "sender_nickname": message.data.senderNickname,
                "channel_name": message.data.channelName,
                "content": message.data.content,
                "created_at": message.metadata.dateTime
            })
        

    def store_discord_message_list(self, messages: List[MessageJson]) -> None:

        if not messages:
            return

        # insert to vector store
        message_documents = [self.build_message(message) for message in messages]
        self.messages_index.insert_nodes(message_documents)

        # insert to postgres table
        message_rows = []
        for message in messages:
            message_rows.append({
                "server_id": message.metadata.serverId,
                "channel_id": message.metadata.channelId,
                "message_id": message.metadata.messageId,
                "sender_id": message.metadata.senderId,
                "sender_username": message.data.senderUsername,
                "sender_nickname": message.data.senderNickname,
                "channel_name": message.data.channelName,
                "content": message.data.content,
                "created_at": message.metadata.dateTime
            })

        with self._engine.begin() as conn:
            insert_query = text("""
                INSERT INTO discord_text (server_id, channel_id, message_id, sender_id, sender_username, sender_nickname, channel_name, content, created_at)
                VALUES (:server_id, :channel_id, :message_id, :sender_id, :sender_username, :sender_nickname, :channel_name, :content, :created_at)
                ON CONFLICT (message_id) DO NOTHING;
            """)
            conn.execute(insert_query, message_rows)

        
    
    def delete_discord_message(self, messageId: str):
        try:
            # Create a filter to match documents with the specific page ID
            filters = MetadataFilters(filters=[ExactMatchFilter(key="messageId", value=messageId)])            
            # Delete documents from the vector store that match the filter
            nodes_to_delete = self.discord_vector_store.get_nodes(filters=filters)
            delete_ids = [node.node_id for node in nodes_to_delete]

            self.discord_vector_store.delete_nodes(node_ids=delete_ids,filters=filters)

            if self._engine is None:
                raise RuntimeError("Database engine not initialized")

            # Keep SQL representation in sync with vector store entries
            with self._engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM discord_text WHERE message_id = :message_id"),
                    {"message_id": messageId}
                )
           
            print(f"Deleted existing documents for message ID: {messageId}")
        except Exception as e:
            print(f"Warning: Could not delete existing documents for message ID {messageId}: {e}")

    def delete_all_discord_documents(self):
        """Delete all documents from the Discord vector store"""
        try:
            # Clear all documents from the Discord tables
            self.discord_vector_store.delete_nodes()

            if self._engine is None:
                raise RuntimeError("Database engine not initialized")

            with self._engine.begin() as conn:
                conn.execute(text("DELETE FROM discord_text"))

            print("Successfully deleted all Discord documents from the vector store")
        except Exception as e:
            print(f"Error deleting all Discord documents: {e}")
            raise

    def retrieve_discord(self, query: str, server_id: str) -> List[Document]:
        """Retrieve relevant Discord messages based on a query"""
        filters = MetadataFilters(filters=[ExactMatchFilter(key="serverId", value=server_id)])
        retriever = self.messages_index.as_retriever(filters=filters)
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
    
    def llm_response(self, query: str, server_id: str, similarity_top_k: int = 7, enabled_sources: List[SourceType] = [SourceType.DISCORD, SourceType.NOTION]) -> tuple[str, List[Union[FormattedSource, FormattedNotionSource]]]:
        """Generate an LLM response based on retrieved messages"""

        # Collect nodes from enabled sources
        all_nodes = []
        
        # Retrieve from Discord if enabled
        if SourceType.DISCORD in enabled_sources:
            filters = MetadataFilters(filters=[ExactMatchFilter(key="serverId", value=server_id)])
            discord_retriever = self.messages_index.as_retriever(
                filters=filters,
                similarity_top_k=similarity_top_k,
                vector_store_query_mode="hybrid"
            )
            discord_nodes = discord_retriever.retrieve(query)
            all_nodes.extend(discord_nodes)
        
        # Retrieve from Notion if enabled
        if SourceType.NOTION in enabled_sources:
            # retrieve from Notion without server filtering
            notion_retriever = self.notion_index.as_retriever(
                similarity_top_k=similarity_top_k,
                vector_store_query_mode="hybrid"
            )
            notion_nodes = notion_retriever.retrieve(query)
            all_nodes.extend(notion_nodes)
        
        # Rerank the combined results (up to 14 total retrieved sources pre-rerank)
        if all_nodes and self.rerank_model is not None:
            reranked_nodes = self.rerank_model.postprocess_nodes(all_nodes, query_str=query)
        else:
            reranked_nodes = all_nodes
        
        # Generate response using LLM with the reranked context 
        
        # Create context from reranked nodes
        context_str = ""
        for i, node in enumerate(reranked_nodes):
            context_str += f"Source {i+1}:\n{node.node.text}\n\n"
        
        # Generate response using the LLM
        llm = Settings.llm
        response = llm.complete(
            f"You are a Discord bot powered by {self.model} answering user questions. Keep your responses concise and under 1000 characters.\nBased on the following context, please answer the question: {query}\n\nContext:\n{context_str}"
        )

        print(response, response.additional_kwargs)

        response_text = response.text

        
        # Format sources
        sourceList = []
        for node in reranked_nodes:
            sourceList.append(self.format_discord_source(node))

        return (response_text, sourceList)
    
    def build_message(self, message: MessageJson) -> Document:
        doc_text = f"Channel: {message.data.channelName}\n"
        doc_text += f"Sender: {message.data.senderNickname if message.data.senderNickname else message.data.senderUsername}\n"
        doc_text += f"Content: {message.data.content}"
        
        doc = Document(
            text=doc_text,
            metadata=message.metadata.model_dump(mode='json')
        )
        
        return doc

    def build_notion_page(self, page: NotionPageJson) -> Document:
        """Convert NotionPageJson to Document format for vector storage"""
        doc_text = f"Title: {page.data.title}\n"
        doc_text += f"Author: {page.data.author}\n"
        doc_text += f"Content: {page.data.content}"
        
        doc = Document(
            text=doc_text,
            metadata=page.metadata.model_dump(mode='json')
        )
        
        return doc
    
    def format_discord_source(self, node: NodeWithScore) -> Union[FormattedSource, FormattedNotionSource]:
        """Convert NodeWithScore to appropriate source format based on content type"""
        
        # Extract text content and parse it
        text_lines = node.node.text.split('\n')
        
        # Detect if this is a Discord message or Notion page based on structure
        is_discord = any(line.startswith("Channel: ") for line in text_lines)
        is_notion = any(line.startswith("Title: ") for line in text_lines)
        
        if is_discord:
            return self._format_discord_source(node)
        elif is_notion:
            return self._format_notion_source(node)
        else:
            # Fallback - assume Discord format
            return self._format_discord_source(node)
    
    def _format_discord_source(self, node: NodeWithScore) -> FormattedSource:
        """Convert NodeWithScore to FormattedSource for Discord messages"""
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
        
        return FormattedSource(
            channel=channel,
            sender=sender if sender != "None" else None,
            senderId=sender_id,
            content=content,
            channelId=channel_id,
            messageId=message_id
        )
    
    def _format_notion_source(self, node: NodeWithScore) -> FormattedNotionSource:
        """Convert NodeWithScore to FormattedNotionSource for Notion pages"""
        text_lines = node.node.text.split('\n')
        
        # Parse the structured text
        title = ""
        author = ""
        content = ""
        
        for line in text_lines:
            if line.startswith("Title: "):
                title = line.replace("Title: ", "")
            elif line.startswith("Author: "):
                author = line.replace("Author: ", "")
            elif line.startswith("Content: "):
                content = line.replace("Content: ", "")
        
        # Extract metadata
        page_id = node.node.metadata.get('pageId', '')
        author_id = node.node.metadata.get('authorId', '')
        url = node.node.metadata.get('url', None)
        
        return FormattedNotionSource(
            title=title,
            author=author,
            authorId=author_id,
            content=content,
            pageId=page_id,
            url=url
        )

vector_db_instance = VectorDB()
