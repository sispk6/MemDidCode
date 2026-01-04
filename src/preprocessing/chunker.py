"""
Text chunking utilities for long documents.
Path: src/preprocessing/chunker.py
"""
from typing import List, Dict, Any
from src.preprocessing.semantic_cleaner import SemanticCleaner


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
        print(f"      [DEBUG] chunk_text: Starting with {len(text)} chars", flush=True)
        if not text or len(text) <= self.chunk_size:
            result = [text] if text else []
            print(f"      [DEBUG] chunk_text: Text fits in one chunk, returning {len(result)} chunks", flush=True)
            return result
        
        chunks = []
        start = 0
        iteration = 0
        
        while start < len(text):
            iteration += 1
            if iteration % 10 == 0:
                print(f"      [DEBUG] chunk_text: Iteration {iteration}, start={start}, len={len(text)}", flush=True)
            
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
                
                # CRITICAL: Only use sentence boundary if it provides meaningful progress
                # Must be at least halfway through the chunk to avoid infinite loops
                min_acceptable_end = start + (self.chunk_size // 2)
                if sentence_end > min_acceptable_end:
                    end = sentence_end + 1  # Include the punctuation
                else:
                    # Fall back to word boundary
                    space_pos = text.rfind(' ', start, end)
                    if space_pos > min_acceptable_end:
                        end = space_pos
                    # else: keep end = start + chunk_size (no boundary found)
            
            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap, or break if we've reached the end
            if end >= len(text):
                break
            
            # CRITICAL SAFETY: Ensure we always make forward progress
            new_start = end - self.overlap
            if new_start <= start:
                # This should never happen, but if it does, force progress
                print(f"      [ERROR] Detected backward movement! start={start}, end={end}, forcing progress", flush=True)
                new_start = start + 1
            start = new_start
        
        print(f"      [DEBUG] chunk_text: Done, created {len(chunks)} chunks in {iteration} iterations", flush=True)
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
        print(f"    [DEBUG] chunk_message: Starting for ID {original_id[:30]}...", flush=True)
        all_chunks = []
        
        # 1. Prepare Base Metadata (Avoid copying all attachments multiple times)
        base_meta = {k: v for k, v in message.items() if k not in ['attachments', 'content', 'embedding_text']}
        print(f"    [DEBUG] chunk_message: Prepared base metadata", flush=True)
        
        # 2. Chunk the main body
        subject = message.get('subject', '')
        content = message.get('content', '')
        full_text = f"{subject}\n\n{content}" if subject else content
        print(f"    [DEBUG] chunk_message: Main body text length: {len(full_text)} chars", flush=True)
        
        print(f"    [DEBUG] chunk_message: Calling chunk_text for main body...", flush=True)
        text_chunks = self.chunk_text(full_text)
        print(f"    [DEBUG] chunk_message: Got {len(text_chunks)} chunks from main body", flush=True)
        for idx, chunk in enumerate(text_chunks):
            chunked_msg = base_meta.copy()
            chunked_msg['id'] = f"{original_id}_chunk_{idx}"
            chunked_msg['content'] = chunk
            chunked_msg['embedding_text'] = chunk
            chunked_msg['chunk_index'] = idx
            chunked_msg['total_chunks'] = len(text_chunks)
            chunked_msg['original_id'] = original_id
            chunked_msg['parent_id'] = original_id
            chunked_msg['source_type'] = 'email_body'
            
            all_chunks.append(chunked_msg)
            
        # 3. Chunk each attachment (with Semantic Cleaning)
        attachments = message.get('attachments', [])
        for att_idx, att in enumerate(attachments):
            att_name = att.get('filename', 'unknown_attachment')
            att_content = att.get('content', '')
            
            if not att_content:
                continue
            
            print(f"    [DEBUG] Processing attachment {att_idx+1}/{len(attachments)}: {att_name} ({len(att_content)} chars)", flush=True)
                
            # --- SEMANTIC CLEANING ---
            cleaned_content = SemanticCleaner.clean(att_content)
            print(f"    [DEBUG] After cleaning: {len(cleaned_content)} chars", flush=True)
            # -------------------------
            
            att_text_chunks = self.chunk_text(cleaned_content)
            print(f"    [DEBUG] Created {len(att_text_chunks)} chunks from {att_name}", flush=True)
            for chunk_idx, chunk in enumerate(att_text_chunks):
                chunked_att = base_meta.copy()
                chunked_att['id'] = f"{original_id}_att_{att_idx}_chunk_{chunk_idx}"
                chunked_att['content'] = chunk
                chunked_att['chunk_index'] = chunk_idx
                chunked_att['total_chunks'] = len(att_text_chunks)
                chunked_att['original_id'] = original_id
                chunked_att['parent_id'] = original_id
                chunked_att['source_type'] = 'attachment'
                chunked_att['filename'] = att_name
                
                # Prepend filename for context in embedding
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
        for idx, msg in enumerate(messages):
            print(f"  [DEBUG] Chunking message {idx+1}/{len(messages)} (ID: {msg.get('id', 'unknown')[:30]}...)", end='\r', flush=True)
            chunked.extend(self.chunk_message(msg))
        
        print(f"\n[INFO] Chunked {len(messages)} messages into {len(chunked)} chunks", flush=True)
        return chunked
