
from src.storage.vector_store import VectorStore
import sys

vs = VectorStore()
base_id = "gmail_17b9142fdec6f1d1"
ids = [f"{base_id}_chunk_{i}" for i in range(10)]

results = vs.collection.get(ids=ids, include=['documents'])
for i in range(10):
    match_id = f"{base_id}_chunk_{i}"
    if match_id in results['ids']:
        idx = results['ids'].index(match_id)
        content = results['documents'][idx]
        print(f"--- Chunk {i} ---")
        print(content[:500])
    else:
        print(f"--- Chunk {i}: MISSING ---")
