#!/usr/bin/env python3
"""
VectorDB Management Tool

This script provides command-line utilities for managing the vector database,
including operations to delete all documents from Discord or Notion stores.
"""

import argparse
import sys
from RAG.vectordb import vector_db_instance


def main():
    """Main function with argparse to handle command line operations"""
    parser = argparse.ArgumentParser(description='VectorDB management tool')
    parser.add_argument('--delete-discord', action='store_true', 
                       help='Delete all Discord documents from the vector store')
    parser.add_argument('--delete-notion', action='store_true',
                       help='Delete all Notion documents from the vector store')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # Initialize VectorDB instance
    try:
        print("Initializing VectorDB...")
        db = vector_db_instance
        
        if args.delete_discord:
            print("Deleting all Discord documents...")
            db.delete_all_discord_documents()
            
        if args.delete_notion:
            print("Deleting all Notion documents...")
            db.delete_all_notion_documents()
            
        # Clean shutdown
        print("Shutting down VectorDB...")
        db.shutdown()
        print("Operation completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()