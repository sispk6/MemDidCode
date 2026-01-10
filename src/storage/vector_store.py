"""
ChromaDB vector storage implementation.
Path: src/storage/vector_store.py
"""
import sqlite3
import json
from typing import Dict, List, Optional, Any, Union
from src.storage.knowledge_base import KnowledgeBase
import chromadb
from chromadb.config import Settings
import os
import pickle
import re
from rank_bm25 import BM25Okapi


class VectorStore:
    """Manage vector embeddings using ChromaDB with Identity enrichment"""
    
    def __init__(self, persist_directory: str = "./data/chromadb", 
                 collection_name: str = "didi_messages",
                 kb_path: str = "./data/knowledge_base.db"):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            kb_path: Path to the KnowledgeBase SQLite database
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.kb = KnowledgeBase(db_path=kb_path)
        
        print(f"[INFO] Initializing ChromaDB at {persist_directory}...")
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Did-I Personal Memory Assistant messages"}
        )
        
        print(f"[OK] ChromaDB initialized. Collection: {collection_name}")
        print(f"   Current document count: {self.collection.count()}")
        
        # BM25 Index path
        self.bm25_dir = os.path.join(persist_directory, "bm25")
        os.makedirs(self.bm25_dir, exist_ok=True)
    
    def add_messages(self, messages: List[Dict[str, Any]], user_id: str) -> bool:
        """
        Add messages with embeddings to the vector store.
        
        Args:
            messages: List of message dictionaries with 'embedding' field
            user_id: ID of the user who owns these messages
            
        Returns:
            bool: True if successful
        """
        if not messages:
            print("[WARN] No messages to add")
            return False
        
        print(f"[INFO] Adding {len(messages)} messages to ChromaDB...")
        
        try:
            # Prepare data for ChromaDB
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for msg in messages:
                # ID
                ids.append(msg['id'])
                
                # Embedding
                embeddings.append(msg['embedding'])
                
                
                # Document (full text for display - no truncation)
                doc_text = f"{msg.get('subject', '')} {msg.get('content', '')}"
                documents.append(doc_text)
                
                # Metadata (searchable fields)
                # Extract recipients
                recipients = msg.get('to', [])
                recipient_emails = ','.join([r.get('email', '') for r in recipients if r.get('email')])
                recipient_names = ','.join([r.get('name', '') for r in recipients if r.get('name')])
                
                # Extract sender info
                sender_email = msg.get('from', {}).get('email', '')
                sender_name = msg.get('from', {}).get('name', '')
                
                # Build participants list (sender + recipients)
                all_participants = [sender_email] + [r.get('email', '') for r in recipients if r.get('email')]
                participants = ','.join(filter(None, all_participants))
                participant_count = len([p for p in all_participants if p])
                
                # Determine message direction (requires user email in config)
                # For now, we'll add a placeholder - can be configured later
                direction = "unknown"  # Will be "sent" or "received" when user email is configured
                
                # Parse date for temporal fields
                date_str = msg.get('date', '')
                year, month, day_of_week, hour = None, None, None, None
                if date_str:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        year = dt.year
                        month = dt.month
                        day_of_week = dt.strftime('%A')  # Monday, Tuesday, etc.
                        hour = dt.hour
                    except:
                        pass  # Keep None values if parsing fails
                
                # Knowledge Base Enrichment
                sender_info = self.kb.resolve_identity(sender_email)
                sender_entity_id = sender_info['id'] if sender_info else ""
                sender_org_name = sender_info.get('organization', {}).get('canonical_name', '') if sender_info else ""
                
                metadata = {
                    # Identity & Platform
                    "user_id": user_id,
                    "platform": msg.get('platform', ''),
                    "account": msg.get('account', 'default'),
                    "type": msg.get('type', ''),
                    
                    # People (Enhanced)
                    "sender_email": sender_email,
                    "sender_name": sender_name,
                    "sender_entity_id": sender_entity_id,  # KB Unified ID
                    "sender_org": sender_org_name,         # KB Org Name
                    "recipient_emails": recipient_emails,
                    "recipient_names": recipient_names,
                    "participants": participants,
                    "participant_count": str(participant_count),
                    "direction": direction,
                    
                    # Temporal (Enhanced)
                    "date": date_str,
                    "year": str(year) if year else "",     # NEW
                    "month": str(month) if month else "",  # NEW
                    "day_of_week": day_of_week or "",      # NEW
                    "hour": str(hour) if hour is not None else "",  # NEW
                    
                    # Content
                    "subject": msg.get('subject', '')[:500],  # Truncate subject
                    
                    # Context
                    "thread_id": msg.get('thread_id', ''),
                    
                    # Chunking metadata
                    "chunk_index": str(msg.get('chunk_index', 0)),
                    "total_chunks": str(msg.get('total_chunks', 1)),
                    "original_id": msg.get('original_id', msg['id']),
                    "source_type": msg.get('source_type', 'email_body'),
                    "filename": msg.get('filename', ''),
                    
                    # Access
                    "url": msg.get('url', ''),
                }
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            print(f"[OK] Successfully added {len(messages)} messages")
            print(f"   Total documents in collection: {self.collection.count()}")
            
            # --- PHASE: Storage (Hybrid) ---
            # Update BM25 index for this user
            self.update_bm25_index(user_id)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error adding messages: {e}")
            return False
    
    def search(self, query_embedding: List[float], 
               user_id: str,
               n_results: int = 10,
               where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar messages using query embedding.
        
        Args:
            query_embedding: Embedding vector for the query
            user_id: ID of the user performing the search
            n_results: Number of results to return
            where: Optional additional metadata filters
            
        Returns:
            List of matching messages with metadata
        """
        # Enforce multi-tenancy filter
        user_where = {"user_id": user_id}
        if where:
            # Combine filters using $and if where is not empty
            combined_where = {"$and": [user_where, where]}
        else:
            combined_where = user_where

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=combined_where,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i],
                        'similarity': 1 - results['distances'][0][i]  # Convert distance to similarity
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"[ERROR] Error searching: {e}")
            return []

    # --- BM25 PERSISTENT METHODS ---
    
    def _get_bm25_path(self, user_id: str):
        """Get the path to a user's BM25 index"""
        return os.path.join(self.bm25_dir, f"bm25_{user_id}.pkl")

    def _tokenize(self, text):
        """Standard tokenizer for BM25 and Hybrid Search"""
        return [t for t in re.findall(r'\w+', text.lower()) if t]

    def update_bm25_index(self, user_id: str):
        """Rebuild and persist the BM25 index for a user"""
        print(f"[STORAGE] Refreshing BM25 index for user {user_id}...")
        
        # Fetch ALL documents for this user (up to 10k)
        results = self.collection.get(
            where={"user_id": user_id},
            include=['documents', 'metadatas'],
            limit=10000
        )
        
        if not results['ids']:
            print(f"[STORAGE] No documents for user {user_id}, skipping BM25")
            return
            
        corpus = results['documents']
        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Save index and corpus data
        data = {
            'bm25': bm25,
            'corpus': corpus,
            'metadatas': results['metadatas'],
            'ids': results['ids']
        }
        
        path = self._get_bm25_path(user_id)
        with open(path, 'wb') as f:
            pickle.dump(data, f)
            
        print(f"[STORAGE] BM25 index saved for {user_id} ({len(corpus)} docs)")

    def search_bm25(self, query_text: str, user_id: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Perform keyword search using persistent BM25 index"""
        path = self._get_bm25_path(user_id)
        if not os.path.exists(path):
            # If index doesn't exist, try to build it once
            self.update_bm25_index(user_id)
            if not os.path.exists(path): return []
            
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
        bm25 = data['bm25']
        
        tokenized_query = self._tokenize(query_text)
        if not tokenized_query:
            return []
            
        scores = bm25.get_scores(tokenized_query)
        
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:n_results]
        
        results = []
        for idx in top_indices:
            if scores[idx] <= 0: continue
            results.append({
                'id': data['ids'][idx],
                'document': data['corpus'][idx],
                'metadata': data['metadatas'][idx],
                'bm25_score': float(scores[idx]),
                'similarity': float(scores[idx]) # Map to similarity for blending
            })
            
        return results
    
    def get_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific message by ID.
        
        Args:
            message_id: Message ID to retrieve
            
        Returns:
            Message dictionary or None if not found
        """
        try:
            result = self.collection.get(
                ids=[message_id],
                include=['documents', 'metadatas', 'embeddings']
            )
            
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'document': result['documents'][0],
                    'metadata': result['metadatas'][0],
                    'embedding': result['embeddings'][0]
                }
            return None
            
        except Exception as e:
            print(f"[ERROR] Error retrieving message: {e}")
            return None
    
    def delete_messages(self, message_ids: List[str]) -> bool:
        """
        Delete messages by IDs.
        
        Args:
            message_ids: List of message IDs to delete
            
        Returns:
            bool: True if successful
        """
        try:
            self.collection.delete(ids=message_ids)
            print(f"[OK] Deleted {len(message_ids)} messages")
            return True
        except Exception as e:
            print(f"[ERROR] Error deleting messages: {e}")
            return False

    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all messages belonging to a specific user.
        
        Args:
            user_id: ID of the user whose data should be deleted
            
        Returns:
            bool: True if successful
        """
        try:
            self.collection.delete(where={"user_id": user_id})
            print(f"[OK] Deleted all ChromaDB data for user: {user_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Error deleting user data: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """Delete all messages from the collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Did-I Personal Memory Assistant messages"}
            )
            print(f"[OK] Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"[ERROR] Error clearing collection: {e}")
            return False
    
    def get_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get collection statistics"""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "total_messages": count,
            "persist_directory": self.persist_directory
        }