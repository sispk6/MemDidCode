import sys
print(f"Python version: {sys.version}")

try:
    import chromadb
    print("✅ ChromaDB installed")
except ImportError:
    print("❌ ChromaDB not found")

try:
    from sentence_transformers import SentenceTransformer
    print("✅ Sentence Transformers installed")
except ImportError:
    print("❌ Sentence Transformers not found")

try:
    from bs4 import BeautifulSoup
    print("✅ BeautifulSoup installed")
except ImportError:
    print("❌ BeautifulSoup not found")

print("\n🎉 Setup complete!")