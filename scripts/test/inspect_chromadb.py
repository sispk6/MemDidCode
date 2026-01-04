"""
Script to inspect ChromaDB's SQLite database structure.
Shows what tables and data ChromaDB stores in SQLite.
"""
import sqlite3
from pathlib import Path

# Connect to ChromaDB's SQLite database
db_path = Path(__file__).parent.parent / "data" / "chromadb" / "chroma.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("ChromaDB SQLite Database Structure")
print("=" * 80)
print()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"Found {len(tables)} tables:")
print()

for table in tables:
    table_name = table[0]
    print(f"Table: {table_name}")
    print("-" * 80)
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print("Columns:")
    for col in columns:
        col_id, col_name, col_type, not_null, default, pk = col
        print(f"  - {col_name} ({col_type})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"Row count: {count}")
    
    # Show sample data for small tables
    if count > 0 and count <= 5:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        rows = cursor.fetchall()
        print("Sample data:")
        for row in rows:
            print(f"  {row}")
    
    print()

conn.close()

print("=" * 80)
print("Summary:")
print("- SQLite stores metadata, relationships, and document info")
print("- Vector embeddings are stored separately in DuckDB/custom format")
print("- ChromaDB uses SQLite for fast metadata filtering")
print("=" * 80)
