
from src.storage.vector_store import VectorStore
import sys

vs = VectorStore()
base_id = "gmail_17b9142fdec6f1d1"
keywords = ['indian', 'dinner', 'party', 'traditional', 'meal', 'delivery']

for i in range(10):
    match_id = f"{base_id}_chunk_{i}"
    res = vs.get_by_id(match_id)
    if res:
        text = res['document'].lower()
        matches = [k for k in keywords if k in text]
        print(f"Chunk {i}: {len(matches)} matches ({matches})")
    else:
        print(f"Chunk {i}: MISSING")
