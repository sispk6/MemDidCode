#!/usr/bin/env python3
"""
Comprehensive KB migration v2.
Adds missing user_id column to entities table.
"""
import sqlite3
import sys
import os
from pathlib import Path

# Add project root to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.utils.config_loader import load_config

def migrate_kb(db_path: str):
    print(f"Checking for migrations in: {db_path}")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Check entities table
        cursor.execute("PRAGMA table_info(entities)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("[INFO] Adding 'user_id' column to 'entities' table...")
            cursor.execute("ALTER TABLE entities ADD COLUMN user_id TEXT")
            print("[OK] Column 'user_id' added to 'entities'.")
        else:
            print("[INFO] 'entities' table already has 'user_id' column.")
            
        conn.commit()

if __name__ == "__main__":
    config = load_config()
    db_path = config.get('storage', {}).get('sqlite_path', './data/knowledge_base.db')
    
    if not os.path.exists(db_path):
        print(f"No DB found at {db_path} - nothing to migrate.")
        sys.exit(0)
    
    try:
        migrate_kb(db_path)
        print("\n[SUCCESS] Knowledge Base is up to date.")
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)
