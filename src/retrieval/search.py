"""
Search and retrieval logic.
Path: src/retrieval/search.py
"""
from typing import List, Dict, Any, Optional
from datetime import datetime


class SearchEngine:
    """Handle search queries and result ranking"""
    
    def __init__(self, vector_store, embedder):
        """
        Initialize search engine.
        
        Args:
            vector_store: VectorStore instance
            embedder: Embedder instance
        """
        self.vector_store = vector_store
        self.embedder = embedder
    
    def search(self, query_text: str, n_results: int = 10, 
               platform: Optional[str] = None,
               sender: Optional[str] = None,
               entity_id: Optional[str] = None,
               org: Optional[str] = None,
               date_from: Optional[str] = None,
               date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for messages matching the query with optional knowledge-based filters.
        """
        print(f"🔍 Searching for: '{query_text}'")
        
        # Generate query embedding
        query_embedding = self.embedder.embed_text(query_text)
        
        # Build metadata filters
        where = {}
        if platform:
            where['platform'] = platform
        if sender:
            where['sender_email'] = sender
        if entity_id:
            where['sender_entity_id'] = entity_id
        if org:
            where['sender_org'] = org
            
        # Handle multiple filters for ChromaDB
        where_clause = None
        if len(where) > 1:
            where_clause = {"$and": [{k: v} for k, v in where.items()]}
        elif len(where) == 1:
            where_clause = where
            
        # Search in vector store
        results = self.vector_store.search(
            query_embedding=query_embedding.tolist(),
            n_results=n_results,
            where=where_clause
        )
        
        # Apply date filters if specified
        if date_from or date_to:
            results = self._filter_by_date(results, date_from, date_to)
        
        # Enhance results with formatting
        enhanced_results = self._enhance_results(results)
        
        print(f"[OK] Found {len(enhanced_results)} results")
        return enhanced_results
    
    def _filter_by_date(self, results: List[Dict[str, Any]], 
                       date_from: Optional[str], 
                       date_to: Optional[str]) -> List[Dict[str, Any]]:
        """Filter results by date range"""
        filtered = []
        
        for result in results:
            msg_date_str = result['metadata'].get('date', '')
            if not msg_date_str:
                continue
            
            try:
                msg_date = datetime.fromisoformat(msg_date_str)
                
                if date_from:
                    if msg_date < datetime.fromisoformat(date_from):
                        continue
                
                if date_to:
                    if msg_date > datetime.fromisoformat(date_to):
                        continue
                
                filtered.append(result)
                
            except ValueError:
                # Skip if date parsing fails
                continue
        
        return filtered
    
    def _enhance_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add formatting and snippets to results"""
        enhanced = []
        
        for result in results:
            metadata = result['metadata']
            
            # Format date
            date_str = metadata.get('date', '')
            try:
                date_obj = datetime.fromisoformat(date_str)
                formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = date_str
            
            # Create snippet
            document = result.get('document', '')
            snippet = document[:200] + "..." if len(document) > 200 else document
            
            enhanced.append({
                'id': result['id'],
                'subject': metadata.get('subject', '(No Subject)'),
                'sender': metadata.get('sender_name', metadata.get('sender_email', 'Unknown')),
                'sender_email': metadata.get('sender_email', ''),
                'date': formatted_date,
                'platform': metadata.get('platform', ''),
                'snippet': snippet,
                'url': metadata.get('url', ''),
                'similarity': round(result.get('similarity', 0), 3),
                'full_text': document
            })
        
        return enhanced
    
    def format_results_for_display(self, results: List[Dict[str, Any]]) -> str:
        """
        Format search results for terminal display.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted string for display
        """
        if not results:
            return "No results found."
        
        output = []
        output.append(f"\n{'='*80}")
        output.append(f"Found {len(results)} results:")
        output.append(f"{'='*80}\n")
        
        for i, result in enumerate(results, 1):
            output.append(f"Result #{i} (Similarity: {result['similarity']})")
            output.append(f"  Subject: {result['subject']}")
            output.append(f"  From: {result['sender']} ({result['sender_email']})")
            output.append(f"  Date: {result['date']}")
            output.append(f"  Platform: {result['platform']}")
            output.append(f"  Snippet: {result['snippet']}")
            
            if result['url']:
                output.append(f"  Link: {result['url']}")
            
            output.append(f"{'-'*80}\n")
        
        return '\n'.join(output)