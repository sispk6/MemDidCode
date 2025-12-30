"""
Text chunking utilities for long documents.
Path: src/preprocessing/chunker.py
"""
from typing import List, Dict, Any


class TextChunker:
    """Split long texts into overlapping chunks for better retrieval"""
    
    def __init__(self, chunk_size: int = 2000, overlap: int = 200):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # If not the last chunk, try to break at sentence/word boundary
            if end < len(text):
                # Look for sentence boundary (., !, ?)
                sentence_end = max(
                    text.rfind('. ', start, end),
                    text.rfind('! ', start, end),
                    text.rfind('? ', start, end)
                )
                
                if sentence_end > start:
                    end = sentence_end + 1  # Include the punctuation
                else:
                    # Fall back to word boundary
                    space_pos = text.rfind(' ', start, end)
                    if space_pos > start:
                        end = space_pos
            
            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.overlap if end < len(text) else end
        
        return chunks
    
    def chunk_message(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk a message and create separate records for each chunk.
        
        Args:
            message: Message dictionary with id, content, metadata
            
        Returns:
            List of chunked message dictionaries
        """
        # Combine subject and content for chunking
        subject = message.get('subject', '')
        content = message.get('content', '')
        full_text = f"{subject}\n\n{content}" if subject else content
        
        # Get chunks
        text_chunks = self.chunk_text(full_text)
        
        # If no chunking needed, return original
        if len(text_chunks) <= 1:
            return [message]
        
        # Create chunked messages
        chunked_messages = []
        original_id = message['id']
        
        for idx, chunk in enumerate(text_chunks):
            chunked_msg = message.copy()
            
            # Update ID to include chunk index
            chunked_msg['id'] = f"{original_id}_chunk_{idx}"
            
            # Store chunk text
            chunked_msg['content'] = chunk
            chunked_msg['chunk_index'] = idx
            chunked_msg['total_chunks'] = len(text_chunks)
            chunked_msg['original_id'] = original_id
            
            chunked_messages.append(chunked_msg)
        
        return chunked_messages
    
    def chunk_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk multiple messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of chunked message dictionaries
        """
        chunked = []
        for msg in messages:
            chunked.extend(self.chunk_message(msg))
        
        print(f"[INFO] Chunked {len(messages)} messages into {len(chunked)} chunks")
        return chunked
