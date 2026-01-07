"""
Ingest script - Fetch messages from Gmail and save as JSON.
Path: scripts/ingest.py

Usage:
    python scripts/ingest.py                    # Legacy mode (default)
    python scripts/ingest.py --mode legacy      # Legacy mode (explicit)
    python scripts/ingest.py --mode mcp         # MCP mode
    python scripts/ingest.py --max-results 50   # Custom max results
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.gmail_connector import GmailConnector
from src.ingest.mcp_gmail_connector import MCPGmailConnector
from src.utils.state_manager import StateManager
from src.utils.config_loader import load_config
from src.storage.knowledge_base import KnowledgeBase
import json


def parse_arguments(default_mode='mcp'):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Ingest messages from Gmail')
    parser.add_argument(
        '--mode',
        choices=['legacy', 'mcp'],
        default=default_mode,
        help=f'Connector mode: legacy or mcp (default: {default_mode})'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        default=None,
        help='Maximum number of messages to fetch (overrides config)'
    )
    parser.add_argument(
        '--user-id',
        type=str,
        default=None,
        help='User ID for multi-tenant ingestion'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Perform a full ingest (ignoring last state)'
    )
    return parser.parse_args()


def process_account(account_config, paths_config, args, state_mgr, mode, user_id=None):
    """Process a single account ingestion."""
    account_name = account_config.get('name', account_config.get('account_name', 'default'))
    print("-" * 40)
    print(f"Processing Account: {account_name}")
    print("-" * 40)
    
    # Initialize connector based on mode
    if mode == 'mcp':
        print(f"[MCP] Using MCP connector for {account_name}")
        connector = MCPGmailConnector(account_config)
        use_mcp = True
    else:
        print(f"[LEGACY] Using legacy connector for {account_name}")
        connector = GmailConnector(account_config)
        use_mcp = False
    
    # Platform name for state tracking includes account name if not default
    platform = connector.platform_name
    state_platform = f"{platform}:{account_name}" if account_name != "default" else platform
    
    # Get last state if not doing a full ingest
    since_date = None
    since_id = None
    if not args.full:
        state = state_mgr.get_state("ingestion", state_platform, {})
        since_date = state.get("last_date")
        since_id = state.get("last_id")
        if since_date:
            print(f"[INFO] Performing incremental ingest since {since_date}")
    else:
        print("[INFO] Performing FULL ingest (ignoring state)")

    # Authenticate
    print(f"Step 1: Authenticating {account_name}...")
    if use_mcp:
        if not connector.authenticate_sync():
            print(f"❌ Authentication failed for {account_name}. Skipping.")
            return
    else:
        if not connector.authenticate():
            print(f"❌ Authentication failed for {account_name}. Skipping.")
            return
    
    print()
    
    # Fetch messages
    max_results = args.max_results if args.max_results else account_config.get('max_results', 100)
    print(f"Step 2: Fetching up to {max_results} messages for {account_name}...")
    if use_mcp:
        messages = connector.fetch_messages_sync(
            max_results=max_results, 
            since_date=since_date, 
            since_id=since_id
        )
    else:
        messages = connector.fetch_messages(
            max_results=max_results,
            since_date=since_date,
            since_id=since_id
        )
    
    if not messages:
        print(f"No new messages fetched for {account_name}.")
        return
    
    # Add account and user tag to each message for storage
    for msg in messages:
        msg['account'] = account_name
        if user_id:
            msg['user_id'] = user_id
    
    print()
    
    # Save raw data
    print(f"Step 3: Saving raw data for {account_name}...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_suffix = "_mcp" if use_mcp else ""
    acc_suffix = f"_{account_name}" if account_name != "default" else ""
    
    # Use user-specific or default raw data path
    raw_data_base = Path(paths_config['raw_data'])
    if user_id:
        raw_data_base = Path(paths_config['users_base_dir']) / user_id / "raw"
    
    raw_data_base.mkdir(parents=True, exist_ok=True)
    output_path = raw_data_base / f"gmail{mode_suffix}{acc_suffix}_{timestamp}.json"
    
    connector.save_raw_data(messages, str(output_path))
    
    # Update state with the newest message from this batch
    newest_msg = messages[-1]
    state_mgr.update_state("ingestion", state_platform, {
        "last_date": newest_msg['date'],
        "last_id": newest_msg['id']
    })
    
    print(f"[OK] {account_name} Ingestion complete!")
    print(f"   Messages fetched: {len(messages)}")
    print(f"   Saved to: {output_path}")
    print()


def main():
    # Load config first to get defaults
    config = load_config()
    mcp_config = config.get('mcp', {})
    default_mode = mcp_config.get('default_mode', 'mcp')
    
    # Parse arguments
    args = parse_arguments(default_mode=default_mode)
    
    # Determine user-specific paths
    user_id = args.user_id
    paths_config = config['paths']
    
    state_file = "data/system_state.json"
    if user_id:
        user_dir = Path(paths_config['users_base_dir']) / user_id
        state_file = user_dir / "system_state.json"
        print(f"[INFO] Using isolated workspace for User: {user_id}")
    else:
        print("[INFO] No User ID provided. Using global system workspace.")

    print("=" * 80)
    print(f"DidI - Data Ingestion ({args.mode.upper()} mode)")
    print("=" * 80)
    print()
    
    # Initialize StateManager with user-specific state
    state_mgr = StateManager(state_file=str(state_file))
    
    # Identity Discovery: Database vs Config
    kb = KnowledgeBase()
    
    if user_id:
        print(f"[DB] Querying KnowledgeBase for accounts registered to {user_id}...")
        db_accounts = kb.get_user_accounts(user_id)
        if not db_accounts:
            print(f"[WARN] No accounts found in DB for {user_id}. Checking config as fallback...")
            # Fallback to config if DB is empty for this user (convenience)
            accounts = config.get('gmail_accounts', [])
        else:
            # Convert DB rows to account configs
            accounts = []
            for acc in db_accounts:
                acc_config = json.loads(acc['config_json'])
                acc_config['name'] = acc['account_name']
                acc_config['platform'] = acc['platform']
                accounts.append(acc_config)
    else:
        # Legacy/System mode
        accounts = config.get('gmail_accounts')

    if accounts and isinstance(accounts, list):
        print(f"[INFO] Found {len(accounts)} configured Gmail accounts.")
        for account in accounts:
            process_account(account, paths_config, args, state_mgr, args.mode, user_id=user_id)
    else:
        # Fall back to single account in config if no list/DB accounts
        if 'gmail' in config:
            print("[INFO] Using single Gmail account configuration from config.yaml.")
            process_account(config['gmail'], paths_config, args, state_mgr, args.mode, user_id=user_id)
        else:
            print("[ERROR] No Gmail configuration found in DB or config.yaml!")
            return

    print("=" * 80)
    print("[OK] All ingestions complete!")
    print("=" * 80)
    print()
    print("Next step: Run 'python scripts/embed.py' to generate embeddings")


if __name__ == "__main__":
    main()
