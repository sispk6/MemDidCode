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
from src.ingest.gmail_connector import GmailConnector
from src.utils.config_loader import load_config



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

def _get_all_gmail_configs() -> List[Dict[str, Any]]:
    """Helper to get all configured Gmail accounts, falling back to legacy 'gmail' block."""
    accounts = config.get('gmail_accounts')
    if accounts and isinstance(accounts, list):
        return accounts
    if 'gmail' in config:
        # For legacy compatibility, we treat the single account as 'default'
        legacy_config = config['gmail'].copy()
        if 'name' not in legacy_config:
            legacy_config['name'] = 'default'
        return [legacy_config]
    return []

def _get_token_path(account_config: Dict[str, Any]) -> Path:
    """Resolve token path for a given account config."""
    token_file = account_config.get('token_file', 'token.json')
    if not os.path.isabs(token_file):
        return root_path / token_file
    return Path(token_file)

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
        # The ingest.py script now handles multiple accounts automatically
        cmd = [
            sys.executable, 
            "scripts/ingest.py", 
            "--mode", request.mode, 
            "--max-results", str(request.max_results)
        ]
        subprocess.run(cmd, cwd=str(root_path))

    background_tasks.add_task(run_ingest)
    return {"status": "Ingestion started in background for all accounts"}

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

# Auth Endpoints
@app.get("/api/auth/status")
async def get_auth_status():
    """Check authentication status for all configured/legacy accounts."""
    account_configs = _get_all_gmail_configs()
    
    statuses = []
    for acc in account_configs:
        token_path = _get_token_path(acc)
        statuses.append({
            "name": acc.get('name', 'default'),
            "authenticated": token_path.exists()
        })
        
    return {"accounts": statuses}

@app.post("/api/auth/login")
async def login(account_name: Optional[str] = None):
    """Trigger Gmail authentication flow for a specific account (opens browser on server)."""
    try:
        account_configs = _get_all_gmail_configs()
        
        # Find the specific account config
        target_config = None
        if account_name:
            for acc in account_configs:
                if acc.get('name') == account_name:
                    target_config = acc
                    break
            if not target_config:
                raise HTTPException(status_code=404, detail=f"Account '{account_name}' not found in config")
        else:
            # Default to the first account if none specified
            if account_configs:
                target_config = account_configs[0]
            else:
                raise HTTPException(status_code=404, detail="No Gmail accounts configured")
        
        from src.ingest.gmail_connector import GmailConnector
        connector = GmailConnector(target_config)
        
        # This will open the browser locally (on the system running the API)
        success = connector.authenticate()
        
        if success:
            return {"status": "success", "message": f"Authentication successful for {target_config.get('name', 'default')}"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
            
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/logout")
async def logout(account_name: Optional[str] = None):
    """Log out a specific account by deleting its token file."""
    account_configs = _get_all_gmail_configs()
    
    # If no account specified, log out ALL accounts
    targets = []
    if account_name:
        for acc in account_configs:
            if acc.get('name') == account_name:
                targets.append(acc)
                break
        if not targets:
            raise HTTPException(status_code=404, detail=f"Account '{account_name}' not found")
    else:
        targets = account_configs

    logged_out_names = []
    for acc in targets:
        token_path = _get_token_path(acc)
        if token_path.exists():
            os.remove(token_path)
            logged_out_names.append(acc.get('name', 'default'))
            
    return {
        "status": "success", 
        "message": f"Logged out accounts: {', '.join(logged_out_names) if logged_out_names else 'none'}"
    }

