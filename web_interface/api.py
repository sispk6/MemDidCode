import os
import sys
import subprocess
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yaml
from pathlib import Path

# Add project root to path so we can import from src
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.storage.vector_store import VectorStore
from src.embeddings.embedder import Embedder
from src.retrieval.search import SearchEngine
from src.retrieval.brain import RAGBrain
from src.storage.knowledge_base import KnowledgeBase

def load_config():
    """Load configuration from config.yaml"""
    config_path = root_path / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

app = FastAPI(title="Did-I Personal Memory Assistant")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Models
class SearchQuery(BaseModel):
    text: str
    platform: Optional[str] = None
    entity_id: Optional[str] = None
    org: Optional[str] = None
    limit: int = 10

class IngestRequest(BaseModel):
    mode: str = "legacy"
    max_results: int = 10

# Initialization
config = load_config()
storage_config = config['storage']
embeddings_config = config['embeddings']

# We initialize these lazily to avoid overhead if not needed immediately
_vector_store = None
_embedder = None
_search_engine = None
_kb = None
_rag_brain = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(
            persist_directory=storage_config['chromadb_path'],
            collection_name=storage_config['collection_name']
        )
    return _vector_store

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = Embedder(model_name=embeddings_config['model_name'])
    return _embedder

def get_search_engine():
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine(get_vector_store(), get_embedder())
    return _search_engine

def get_kb():
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb

def get_rag_brain():
    global _rag_brain
    if _rag_brain is None:
        try:
            _rag_brain = RAGBrain()
        except Exception as e:
            print(f"[WARN] RAG Brain initialization failed: {e}")
            _rag_brain = None
    return _rag_brain

# API Endpoints
@app.get("/")
async def read_index():
    return FileResponse(str(static_dir / "index.html"))

@app.post("/api/search")
async def search(query: SearchQuery):
    try:
        engine = get_search_engine()
        results = engine.search(
            query_text=query.text,
            n_results=query.limit,
            platform=query.platform,
            entity_id=query.entity_id,
            org=query.org
        )
        
        # Generate RAG answer if brain is available
        answer = None
        brain = get_rag_brain()
        if brain and results:
            try:
                answer_data = brain.generate_answer(query.text, results)
                answer = answer_data
            except Exception as e:
                print(f"[WARN] RAG answer generation failed: {e}")
        
        return {
            "results": results,
            "answer": answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest")
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    # Run ingestion in the background so the UI doesn't hang
    def run_ingest():
        cmd = [
            sys.executable, 
            "scripts/ingest.py", 
            "--mode", request.mode, 
            "--max-results", str(request.max_results)
        ]
        subprocess.run(cmd, cwd=str(root_path))

    background_tasks.add_task(run_ingest)
    return {"status": "Ingestion started in background"}

@app.post("/api/embed")
async def embed(background_tasks: BackgroundTasks):
    def run_embed():
        cmd = [sys.executable, "scripts/embed.py"]
        subprocess.run(cmd, cwd=str(root_path))

    background_tasks.add_task(run_embed)
    return {"status": "Embedding generation started in background"}

@app.get("/api/kb/entities")
async def get_entities():
    try:
        kb = get_kb()
        entities = kb.get_all_entities()
        return {"entities": entities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    try:
        vs = get_vector_store()
        stats = vs.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
