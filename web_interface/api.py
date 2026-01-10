import os
import sys
import subprocess
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
import yaml
from pathlib import Path
import json
import shutil
import uuid

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
from evaluation.benchmark import run_benchmark



app = FastAPI(title="Did-I Personal Memory Assistant")

# Add session middleware with a secret key
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# --- Dependencies & Helpers ---

async def get_user_id(request: Request) -> str:
    """Extract user ID from session. Raises HTTPException if not logged in."""
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id

async def get_user_id_optional(request: Request) -> str:
    """Extract user ID from session. Returns 'system' for legacy/local mode."""
    return request.session.get('user_id', 'system')

def get_user_workspace(user_id: str) -> Path:
    """Ensure user workspace exists and return path."""
    users_base = Path(config.get('paths', {}).get('users_base_dir', './data/users'))
    user_path = users_base / user_id
    (user_path / "raw").mkdir(parents=True, exist_ok=True)
    return user_path

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

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None

class EvaluationRequest(BaseModel):
    num_queries: int = 5
    metrics: List[str] = ["mrr", "p@5", "llm", "latency"]
    save_results: bool = True

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

def _get_all_gmail_configs(user_id: str = "system") -> List[Dict]:
    """Get all Gmail configs for a user from DB or config fallback"""
    kb = get_kb()
    db_accounts = kb.get_user_accounts(user_id, platform="gmail")
    
    if db_accounts:
        accounts = []
        for acc in db_accounts:
            acc_config = json.loads(acc['config_json'])
            acc_config['name'] = acc['account_name']
            accounts.append(acc_config)
        return accounts
    
    # Fallback to system config if user is 'system' or no DB accounts
    gmail_accounts = config.get('gmail_accounts', [])
    if not gmail_accounts and 'gmail' in config:
        return [config['gmail']]
    return gmail_accounts

def _get_token_path(account_config: Dict[str, Any], user_id: str) -> Path:
    """Resolve token path for a given account config and user_id."""
    user_workspace = get_user_workspace(user_id)
    token_file = account_config.get('token_file', 'token.json')
    
    # If token_file is an absolute path, use it as is.
    if os.path.isabs(token_file):
        return Path(token_file)
    
    # For multi-user workspaces, tokens live in user workspace
    if user_id != "system":
        account_name = account_config.get('name', 'default')
        # Ensure name is safe for filename
        safe_name = account_name.replace(" ", "_").lower()
        return user_workspace / f"token_{safe_name}.json"
        
    return root_path / token_file


# API Endpoints
@app.get("/")
async def read_index():
    return FileResponse(str(static_dir / "index.html"))

@app.post("/api/search")
async def search(query: SearchQuery, user_id: str = Depends(get_user_id)):
    try:
        engine = get_search_engine()
        results = engine.search(
            query_text=query.text,
            n_results=query.limit,
            platform=query.platform,
            entity_id=query.entity_id,
            org=query.org,
            user_id=user_id # Pass user_id to search engine
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

@app.get("/api/search_simple")
async def search_simple(q: str, user_id: str = Depends(get_user_id)):
    """Semantic search for messages belonging to a specific user"""
    try:
        embedder = get_embedder()
        vector_store = get_vector_store()

        # 1. Embed query
        query_embedding = embedder.embed_text(q)
        
        # 2. Search vector store with mandatory user filter
        results = vector_store.search(
            query_embedding=query_embedding, 
            user_id=user_id,
            n_results=10
        )
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Auth Endpoints
@app.post("/api/auth/register")
async def register(request: Request, body: RegisterRequest):
    """Register a new user."""
    try:
        kb = get_kb()
        
        # Check if username already exists
        existing_user = kb.get_user_by_username(body.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Register new user
        user_id = kb.register_user(
            username=body.username,
            password=body.password,
            display_name=body.display_name
        )
        
        # Set session
        request.session['user_id'] = user_id
        request.session['username'] = body.username
        
        return {"status": "success", "user_id": user_id, "username": body.username}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login_user(request: Request, body: LoginRequest):
    """Login with username/password."""
    try:
        kb = get_kb()
        
        # Verify credentials
        user = kb.verify_user_credentials(body.username, body.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Set session
        request.session['user_id'] = user['id']
        request.session['username'] = user['username']
        
        return {
            "status": "success",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "display_name": user['display_name']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/logout")
async def logout_user(request: Request):
    """Logout current user."""
    request.session.clear()
    return {"status": "success", "message": "Logged out successfully"}

@app.get("/api/auth/current-user")
async def get_current_user(request: Request):
    """Get currently logged-in user."""
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    kb = get_kb()
    user = kb.get_user_by_id(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check if user has any accounts
    accounts = kb.get_user_accounts(user_id)
    
    return {
        "authenticated": True,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "display_name": user['display_name']
        },
        "has_accounts": len(accounts) > 0
    }


@app.post("/api/ingest")
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_user_id)):
    # Run ingestion in the background so the UI doesn't hang
    def run_ingest():
        # The ingest.py script now handles multiple accounts automatically
        cmd = [
            sys.executable, 
            "scripts/ingest.py", 
            "--mode", request.mode, 
            "--max-results", str(request.max_results),
            "--user-id", user_id # Pass user_id to the ingest script
        ]
        subprocess.run(cmd, cwd=str(root_path))

    background_tasks.add_task(run_ingest)
    return {"status": f"Ingestion started in background for all accounts for user {user_id}"}


@app.post("/api/embed")
async def embed(background_tasks: BackgroundTasks, user_id: str = Depends(get_user_id)):
    def run_embed():
        cmd = [sys.executable, "scripts/embed.py", "--user-id", user_id] # Pass user_id to embed script
        subprocess.run(cmd, cwd=str(root_path))

    background_tasks.add_task(run_embed)
    return {"status": f"Embedding generation started in background for user {user_id}"}

@app.get("/api/kb/entities")
async def get_entities(user_id: str = Depends(get_user_id)):
    try:
        kb = get_kb()
        entities = kb.get_all_entities(user_id=user_id) # Pass user_id to KB
        return {"entities": entities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evaluate")
async def evaluate(request: EvaluationRequest, user_id: str = Depends(get_user_id)):
    """Run search quality benchmark for the user."""
    try:
        # Define save path if requested
        save_path = None
        if request.save_results:
            timestamp = int(time.time())
            save_path = f"evaluation/results/eval_{user_id}_{timestamp}.json"
        
        # Run the benchmark
        # Note: This is a synchronous call that might take some time (LLM judging)
        # For a better UX in a real app, this should be a background task with status polling
        results = run_benchmark(
            user_id=user_id,
            num_queries=request.num_queries,
            metrics=request.metrics,
            save_path=save_path
        )
        
        return {
            "status": "success",
            "results": results,
            "save_path": save_path
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats(user_id: str = Depends(get_user_id)):
    try:
        vs = get_vector_store()
        stats = vs.get_stats(user_id=user_id) # Pass user_id to vector store stats
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Auth Endpoints
@app.get("/api/auth/status")
async def get_auth_status(user_id: str = Depends(get_user_id)):
    """Check authentication status for all configured/legacy accounts."""
    account_configs = _get_all_gmail_configs(user_id)
    
    statuses = []
    for acc in account_configs:
        token_path = _get_token_path(acc, user_id)
        statuses.append({
            "name": acc.get('name', 'default'),
            "authenticated": token_path.exists()
        })
        
    return {
        "authenticated": any(s["authenticated"] for s in statuses),
        "accounts": statuses
    }

# Gmail OAuth Endpoints  
@app.get("/api/gmail/status")
async def get_gmail_status(user_id: str = Depends(get_user_id)):
    """Check Gmail authentication status for all configured accounts."""
    account_configs = _get_all_gmail_configs(user_id)
    
    statuses = []
    for acc in account_configs:
        token_path = _get_token_path(acc, user_id)
        statuses.append({
            "name": acc.get('name', 'default'),
            "authenticated": token_path.exists()
        })
        
    return {
        "authenticated": any(s["authenticated"] for s in statuses),
        "accounts": statuses
    }

@app.post("/api/gmail/connect")
async def gmail_connect(account_name: Optional[str] = None, user_id: str = Depends(get_user_id)):
    """Trigger Gmail authentication flow for a specific account (opens browser on server)."""
    try:
        kb = get_kb()
        account_configs = _get_all_gmail_configs(user_id)
        
        # Find the specific account config
        target_config = None
        if account_name:
            target_config = next((acc for acc in account_configs if acc.get('name') == account_name), None)
            if not target_config:
                raise HTTPException(status_code=404, detail=f"Account '{account_name}' not found")
        else:
            if account_configs:
                target_config = account_configs[0]
            else:
                # Fallback to system config if NO accounts configured for this user yet
                system_configs = _get_all_gmail_configs("system")
                if system_configs:
                    target_config = system_configs[0]
                    # We'll treat this as a "Personal" account for the new user
                    target_config = target_config.copy()
                    target_config['name'] = "Personal"
                else:
                    raise HTTPException(status_code=404, detail="No Gmail accounts configured in system")
        
        # Override token_file to the user-specific one
        token_path = _get_token_path(target_config, user_id)
        target_config = target_config.copy()
        target_config['token_file'] = str(token_path)
        
        from src.ingest.gmail_connector import GmailConnector
        connector = GmailConnector(target_config)
        
        # This will open the browser locally (on the system running the API)
        success = connector.authenticate()
        
        if success:
            # If successful, ensure the account is saved in the KB for this user
            existing_user_accounts = kb.get_user_accounts(user_id, platform="gmail")
            name = target_config.get('name', 'Personal')
            
            if not any(acc['account_name'] == name for acc in existing_user_accounts):
                # Add account record to DB
                kb.add_account(
                    user_id=user_id,
                    platform="gmail",
                    account_name=name,
                    config={
                        "credentials_file": target_config.get('credentials_file', 'credentials.json'),
                        "token_file": str(token_path.name), # Just the filename, _get_token_path handles resolution
                        "max_results": target_config.get('max_results', 100)
                    }
                )
                print(f"[INFO] New Gmail account '{name}' registered in database for user {user_id}")
            
            return {"status": "success", "message": f"Authentication successful for {name}"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
            
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gmail/disconnect")
async def gmail_disconnect(account_name: Optional[str] = None, user_id: str = Depends(get_user_id)):
    """Disconnect a specific Gmail account by deleting its token file."""
    account_configs = _get_all_gmail_configs(user_id)
    
    # If no account specified, log out ALL accounts
    targets = []
    if account_name:
        target = next((acc for acc in account_configs if acc.get('name') == account_name), None)
        if target:
            targets.append(target)
        else:
            raise HTTPException(status_code=404, detail=f"Account '{account_name}' not found")
    else:
        targets = account_configs

    logged_out_names = []
    for acc in targets:
        token_path = _get_token_path(acc, user_id)
        if token_path.exists():
            os.remove(token_path)
            logged_out_names.append(acc.get('name', 'default'))
            
    return {
        "status": "success", 
        "message": f"Logged out accounts: {', '.join(logged_out_names) if logged_out_names else 'none'}"
    }

