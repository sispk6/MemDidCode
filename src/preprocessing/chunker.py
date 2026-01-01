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
        Chunk a message and its attachments, creating separate linked records.
        
        Args:
            message: Message dictionary with id, content, metadata, and attachments
            
        Returns:
            List of chunked dictionaries (main body chunks + attachment chunks)
        """
        original_id = message['id']
        all_chunks = []
        
        # 1. Chunk the main body
        subject = message.get('subject', '')
        content = message.get('content', '')
        full_text = f"{subject}\n\n{content}" if subject else content
        
        text_chunks = self.chunk_text(full_text)
        for idx, chunk in enumerate(text_chunks):
            chunked_msg = message.copy()
            # Clean up attachments from body chunks to save space/DB weight
            if 'attachments' in chunked_msg:
                del chunked_msg['attachments']
                
            chunked_msg['id'] = f"{original_id}_chunk_{idx}"
            chunked_msg['content'] = chunk
            chunked_msg['embedding_text'] = chunk
            chunked_msg['chunk_index'] = idx
            chunked_msg['total_chunks'] = len(text_chunks)
            chunked_msg['original_id'] = original_id
            chunked_msg['parent_id'] = original_id # Self-link for consistency
            chunked_msg['source_type'] = 'email_body'
            
            all_chunks.append(chunked_msg)
            
        # 2. Chunk each attachment
        attachments = message.get('attachments', [])
        for att_idx, att in enumerate(attachments):
            att_name = att.get('filename', 'unknown_attachment')
            att_content = att.get('content', '')
            
            if not att_content:
                continue
                
            att_text_chunks = self.chunk_text(att_content)
            for chunk_idx, chunk in enumerate(att_text_chunks):
                chunked_att = message.copy()
                # Clean up attachments from its own chunk
                if 'attachments' in chunked_att:
                    del chunked_att['attachments']
                
                chunked_att['id'] = f"{original_id}_att_{att_idx}_chunk_{chunk_idx}"
                chunked_att['content'] = chunk
                chunked_att['chunk_index'] = chunk_idx
                chunked_att['total_chunks'] = len(att_text_chunks)
                chunked_att['original_id'] = original_id
                chunked_att['parent_id'] = original_id # Link to parent email
                chunked_att['source_type'] = 'attachment'
                chunked_att['filename'] = att_name
                
                # Prepend filename for context in embedding if it's an attachment
                chunked_att['embedding_text'] = f"Attachment: {att_name}\n\n{chunk}"
                
                all_chunks.append(chunked_att)
        
        return all_chunks
    
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
