import sys
import os
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.gmail_connector import GmailConnector
from src.preprocessing.chunker import TextChunker

def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_attachments():
    print("Step 1: Initializing Gmail Connector...")
    config = load_config()
    connector = GmailConnector(config['gmail'])
    
    if not connector.authenticate():
        print("Authentication failed")
        return

    print("\nStep 2: Fetching messages (searching for attachments specifically)...")
    # We use a query to find messages with pdf or docx attachments to be efficient
    try:
        results = connector.service.users().messages().list(
            userId='me',
            q="has:attachment (filename:pdf OR filename:docx)",
            maxResults=3
        ).execute()
        
        msg_ids = results.get('messages', [])
        if not msg_ids:
            print("No messages with PDF/DOCX attachments found in the last few emails.")
            print("Fetching regular messages instead...")
            messages = connector.fetch_messages(max_results=5)
        else:
            messages = []
            for m in msg_ids:
                full_msg = connector.service.users().messages().get(
                    userId='me',
                    id=m['id'],
                    format='full'
                ).execute()
                messages.append(connector.normalize_message(full_msg))
    except Exception as e:
        print(f"Error fetching: {e}")
        return

    print(f"\nFound {len(messages)} messages.")
    
    found_any_attachment = False
    for msg in messages:
        atts = msg.get('attachments', [])
        if atts:
            found_any_attachment = True
            print(f"\n--- Message: {msg['subject']} ---")
            print(f"ID: {msg['id']}")
            print(f"Number of attachments: {len(atts)}")
            
            for att in atts:
                print(f"  - Filename: {att['filename']}")
                print(f"  - Extract Start: {att['content'][:100]}...")
                
            # Test Chunking
            print("\nStep 3: Testing Chunking Strategy...")
            chunker = TextChunker(chunk_size=500, overlap=50) # Small chunks for testing
            chunks = chunker.chunk_message(msg)
            
            print(f"Created {len(chunks)} chunks in total.")
            for c in chunks:
                print(f"  Chunk ID: {c['id']}")
                print(f"    Type: {c.get('source_type')}")
                print(f"    Parent: {c.get('parent_id')}")
                if c.get('source_type') == 'attachment':
                    print(f"    Filename: {c.get('filename')}")
                print(f"    Text Preview: {c['content'][:50]}...")
                print("-" * 20)

    if not found_any_attachment:
        print("\n[WARN] No attachments were found/processed in the sampled messages.")
        print("Please ensure you have an email with a .pdf or .docx attachment in your inbox.")

if __name__ == "__main__":
    test_attachments()
