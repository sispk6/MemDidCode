"""
Verification script for SemanticCleaner and optimized TextChunker.
Path: scripts/verify_semantic_cleaner.py
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessing.chunker import TextChunker
from src.preprocessing.semantic_cleaner import SemanticCleaner

def test_semantic_cleaner():
    print("--- Testing SemanticCleaner Heuristics ---")
    
    # 1. Boilerplate removal
    text_with_boilerplate = "Header: Info\n" * 10 + "Real content here.\n" + "Footer: Page 1\n" * 10
    cleaned = SemanticCleaner.clean(text_with_boilerplate)
    print(f"Boilerplate Test: {'PASSED' if 'Header' not in cleaned and 'Real content' in cleaned else 'FAILED'}")
    
    # 2. Key section extraction (Oversized)
    # Each line is approx 130 chars. 3000 lines approx 390KB.
    oversized_text = "\n".join([f"Line {i}: This is some content that is repeated to make the file very large and trigger the oversized extraction logic." for i in range(3000)])
    cleaned_oversized = SemanticCleaner.clean(oversized_text)
    print(f"Oversized Test: {'PASSED' if 'LARGE CONTENT REMOVED' in cleaned_oversized else 'FAILED'}")
    print(f"Oversized Length: {len(cleaned_oversized)} chars (Original: {len(oversized_text)})")

def test_chunker_integration():
    print("\n--- Testing TextChunker Integration ---")
    chunker = TextChunker(chunk_size=500, overlap=50)
    
    mock_message = {
        'id': 'test_123',
        'subject': 'Test Subject',
        'content': 'This is the main email body.',
        'attachments': [
            {
                'filename': 'large_doc.txt',
                'content': '\n'.join([f"Line {i} of the attachment" for i in range(1000)])
            }
        ]
    }
    
    chunks = chunker.chunk_message(mock_message)
    print(f"Total chunks created: {len(chunks)}")
    
    found_attachment_chunks = [c for c in chunks if c.get('source_type') == 'attachment']
    print(f"Attachment chunks: {len(found_attachment_chunks)}")
    
    # Check for memory optimization (attachments should NOT be in the chunk dictionary)
    if any('attachments' in c for c in chunks):
        print("Memory Cleanup: FAILED (attachments still present in chunks)")
    else:
        print("Memory Cleanup: PASSED")
        
    for c in chunks[:3]:
        print(f"Chunk ID: {c['id']}, Type: {c['source_type']}, Preview: {c['content'][:50]}...")

if __name__ == "__main__":
    test_semantic_cleaner()
    test_chunker_integration()
