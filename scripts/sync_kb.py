"""
Sync Identity script - Incrementally extract and resolve identities in the Knowledge Base.
Path: scripts/sync_kb.py
"""
import sys
import os
import json
import yaml
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.knowledge_base import KnowledgeBase
from src.utils.state_manager import StateManager
from src.utils.config_loader import load_config

def main():
    print("=" * 80)
    print("Did-I - Knowledge Base Identity Sync (Incremental)")
    print("=" * 80)
    print()

    # Load config
    config = load_config()
    paths_config = config['paths']
    
    # Initialize StateManager and KB
    state_mgr = StateManager()
    kb = KnowledgeBase()
    
    # Get last sync state
    platform = "gmail" # Default for now
    last_sync = state_mgr.get_state("kb_sync", platform, {})
    last_date = last_sync.get("last_date", "1970-01-01")
    
    print(f"[INFO] Scanning for new identities since {last_date}...")
    
    # Find all raw files
    raw_dir = Path(paths_config['raw_data'])
    json_files = sorted(list(raw_dir.glob("gmail_*.json")), key=lambda p: p.stat().st_mtime)
    
    if not json_files:
        print("[ERROR] No data files found.")
        return

    new_identities = 0
    resolved_count = 0
    max_msg_date = last_date
    
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get('messages', [])
        for msg in messages:
            msg_date = msg.get('date', '')
            if msg_date <= last_date:
                continue
            
            if msg_date > max_msg_date:
                max_msg_date = msg_date
                
            sender = msg.get('from', {})
            email = sender.get('email', '')
            name = sender.get('name', '') or email
            
            if not email:
                continue
                
            # Try to resolve
            identity = kb.resolve_identity(email)
            if not identity:
                # Add as new entity
                eid = kb.add_entity(name, 'person')
                kb.add_alias(eid, email, 'email')
                print(f"  [NEW] Added identity: {name} <{email}>")
                new_identities += 1
            else:
                resolved_count += 1
    
    # Update state
    state_mgr.update_state("kb_sync", platform, {
        "last_date": max_msg_date,
        "sync_timestamp": datetime.now().isoformat()
    })
    
    print()
    print("=" * 80)
    print("[OK] Identity Sync complete!")
    print(f"   New identities added: {new_identities}")
    print(f"   Existing identities resolved: {resolved_count}")
    print(f"   Last processed message date: {max_msg_date}")
    print("=" * 80)
    print()
    print("Next step: Use 'python scripts/manage_kb.py list' to see all identities")

if __name__ == "__main__":
    main()
