import sqlite3
import json
from pathlib import Path

def dump_kb():
    db_path = Path("data/knowledge_base.db")
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    tables = ['users', 'accounts', 'entities']
    
    for table in tables:
        print(f"--- {table.upper()} ---")
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(" (Table is empty)")
            for row in rows:
                # Convert row to dict for easier printing
                d = dict(row)
                # Cleanup password for security if it exists
                if 'password_hash' in d:
                    d['password_hash'] = '[REDACTED]'
                print(d)
        except Exception as e:
            print(f" Error reading {table}: {e}")
        print()
    
    conn.close()

if __name__ == "__main__":
    dump_kb()
