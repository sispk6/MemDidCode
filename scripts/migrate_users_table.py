#!/usr/bin/env python3
"""
Database migration script to add password_hash column to users table.
This script safely adds the missing column to existing databases.
"""
import sqlite3
import sys
from pathlib import Path

# Add project root to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.utils.config_loader import load_config

def migrate_users_table(db_path: str):
    """Add password_hash column to users table if it doesn't exist."""
    print(f"Migrating database: {db_path}")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Current columns in users table: {columns}")
        
        if 'password_hash' in columns:
            print("[INFO] password_hash column already exists. No migration needed.")
            return
        
        print("Adding password_hash column...")
        
        # Add the missing column
        cursor.execute("""
            ALTER TABLE users ADD COLUMN password_hash TEXT
        """)
        
        conn.commit()
        print("[SUCCESS] Migration complete! password_hash column added successfully.")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(users)")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns in users table: {new_columns}")

if __name__ == "__main__":
    # Load config to get database path
    config = load_config()
    
    # Get database path from config or use default
    db_path = config.get('storage', {}).get('sqlite_path', './data/knowledge_base.db')
    
    print(f"Knowledge Base Migration Tool")
    print(f"=" * 50)
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"Database not found at {db_path}")
        print("No migration needed - new database will be created with correct schema.")
        sys.exit(0)
    
    # Run migration
    try:
        migrate_users_table(db_path)
        print("\n[SUCCESS] Migration completed successfully!")
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)
