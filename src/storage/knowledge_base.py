import sqlite3
import json
import uuid
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

class KnowledgeBase:
    """
    Manages personal identities and organizational context in an 
    Identity Registry (SQLite). Decouples entities from platform IDs.
    """
    
    def __init__(self, db_path: str = "./data/knowledge_base.db"):
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users Table (System Level)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Accounts Table (Gmail, Slack configs linked to users)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    platform TEXT NOT NULL, -- 'gmail', 'slack'
                    account_name TEXT NOT NULL, -- e.g. 'Personal'
                    config_json TEXT, -- JSON blob for token_file, credentials_file
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, platform, account_name)
                )
            ''')

            # Entities Table (People, Organizations, Groups)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT, -- Optional: owner of this entity record
                    type TEXT NOT NULL, -- 'person', 'organization', 'group'
                    canonical_name TEXT NOT NULL,
                    metadata TEXT, -- JSON blob for role, department, etc.
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Aliases Table (Emails, Slack IDs, Phone numbers)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    alias_type TEXT NOT NULL, -- 'email', 'slack_id', 'handle'
                    value TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (entity_id) REFERENCES entities (id)
                )
            ''')
            
            # Relationships Table (Alice belongs to ABC Corp)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    rel_type TEXT NOT NULL, -- 'member_of', 'works_at', 'manages'
                    FOREIGN KEY (subject_id) REFERENCES entities (id),
                    FOREIGN KEY (object_id) REFERENCES entities (id)
                )
            ''')
            
            conn.commit()

    def add_entity(self, name: str, entity_type: str = 'person', metadata: Dict = None) -> str:
        """Add a new entity and return its ID."""
        entity_id = str(uuid.uuid4())
        meta_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO entities (id, type, canonical_name, metadata) VALUES (?, ?, ?, ?)",
                (entity_id, entity_type, name, meta_json)
            )
            conn.commit()
        return entity_id

    def add_alias(self, entity_id: str, value: str, alias_type: str = 'email'):
        """Bind an identifier to an entity."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO aliases (entity_id, alias_type, value) VALUES (?, ?, ?)",
                    (entity_id, alias_type, value)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # Value already exists, check if it belongs to same entity
                cursor = conn.execute("SELECT entity_id FROM aliases WHERE value = ?", (value,))
                row = cursor.fetchone()
                if row and row[0] != entity_id:
                    print(f"[WARN] Identifier {value} is already mapped to entity {row[0]}.")

    def resolve_identity(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Resolve an identifier (email, handle) to its canonical entity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT e.id, e.type, e.canonical_name, e.metadata
                FROM entities e
                JOIN aliases a ON e.id = a.entity_id
                WHERE a.value = ?
            ''', (identifier,))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                result['metadata'] = json.loads(result['metadata'] or '{}')
                
                # Fetch organizational context
                cursor = conn.execute('''
                    SELECT e.id, e.canonical_name 
                    FROM entities e
                    JOIN relationships r ON e.id = r.object_id
                    WHERE r.subject_id = ? AND r.rel_type = 'works_at'
                ''', (result['id'],))
                org_row = cursor.fetchone()
                if org_row:
                    result['organization'] = dict(org_row)
                
                return result
        return None

    def link_to_org(self, person_id: str, org_id: str):
        """Link a person to an organization."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO relationships (subject_id, object_id, rel_type) VALUES (?, ?, ?)",
                (person_id, org_id, 'works_at')
            )
            conn.commit()

    def get_all_entities(self, user_id: str, entity_type: str = None) -> List[Dict]:
        """List all entities for a specific user, optionally filtered by type."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM entities WHERE user_id = ?"
            params = [user_id]
            
            if entity_type:
                query += " AND type = ?"
                params.append(entity_type)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Multi-Tenancy Management ---

    def register_user(self, username: str, display_name: str = None) -> str:
        """Register a new system user."""
        user_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, username, display_name) VALUES (?, ?, ?)",
                (user_id, username, display_name or username)
            )
            conn.commit()
        return user_id

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Fetch user by username."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_account(self, user_id: str, platform: str, account_name: str, config: Dict = None) -> str:
        """Add a service account (Gmail/Slack) for a user."""
        account_id = str(uuid.uuid4())
        config_json = json.dumps(config or {})
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO accounts (id, user_id, platform, account_name, config_json) VALUES (?, ?, ?, ?, ?)",
                (account_id, user_id, platform, account_name, config_json)
            )
            conn.commit()
        return account_id

    def get_user_accounts(self, user_id: str, platform: str = None) -> List[Dict]:
        """List all accounts for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM accounts WHERE user_id = ?"
            params = [user_id]
            if platform:
                query += " AND platform = ?"
                params.append(platform)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
