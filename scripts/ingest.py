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


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


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
        '--full',
        action='store_true',
        help='Force full ingestion (ignore last state)'
    )
    return parser.parse_args()


def main():
    # Load config first to get defaults
    config = load_config()
    mcp_config = config.get('mcp', {})
    default_mode = mcp_config.get('default_mode', 'mcp')
    
    # Parse arguments
    args = parse_arguments(default_mode=default_mode)
    
    print("=" * 80)
    print(f"DidI? - Data Ingestion ({args.mode.upper()} mode)")
    print("=" * 80)
    print()
    
    # Initialize StateManager
    state_mgr = StateManager()
    
    # Use loaded config
    gmail_config = config['gmail']
    paths_config = config['paths']
    
    # Override max_results if provided
    max_results = args.max_results if args.max_results else gmail_config.get('max_results', 100)
    
    # Initialize connector based on mode
    if args.mode == 'mcp':
        print("[MCP] Using MCP connector")
        connector = MCPGmailConnector(gmail_config)
        use_mcp = True
    else:
        print("[LEGACY] Using legacy connector")
        connector = GmailConnector(gmail_config)
        use_mcp = False
    
    platform = connector.platform_name
    
    # Get last state if not doing a full ingest
    since_date = None
    since_id = None
    if not args.full:
        state = state_mgr.get_state("ingestion", platform, {})
        since_date = state.get("last_date")
        since_id = state.get("last_id")
        if since_date:
            print(f"[INFO] Performing incremental ingest since {since_date}")
    else:
        print("[INFO] Performing FULL ingest (ignoring state)")

    # Authenticate
    print("Step 1: Authenticating with Gmail...")
    if use_mcp:
        # MCP connector has sync wrapper for backward compatibility
        if not connector.authenticate_sync():
            print("❌ Authentication failed. Exiting.")
            return
    else:
        if not connector.authenticate():
            print("❌ Authentication failed. Exiting.")
            return
    
    print()
    
    # Fetch messages
    print(f"Step 2: Fetching up to {max_results} messages...")
    if use_mcp:
        # MCP connector has sync wrapper for backward compatibility
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
        print("No new messages fetched.")
        return
    
    print()
    
    # Save raw data
    print("Step 3: Saving raw data...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_suffix = "_mcp" if use_mcp else ""
    output_path = Path(paths_config['raw_data']) / f"gmail{mode_suffix}_{timestamp}.json"
    
    connector.save_raw_data(messages, str(output_path))
    
    # Update state with the newest message from this batch
    # Since we sorted them ascending in the connector, the last one is the newest
    newest_msg = messages[-1]
    state_mgr.update_state("ingestion", platform, {
        "last_date": newest_msg['date'],
        "last_id": newest_msg['id']
    })
    
    print()
    print("=" * 80)
    print("[OK] Ingestion complete!")
    print(f"   Mode: {args.mode.upper()}")
    print(f"   Messages fetched: {len(messages)}")
    print(f"   Saved to: {output_path}")
    print(f"   Updated state: {newest_msg['date']}")
    print("=" * 80)
    print()
    print("Next step: Run 'python scripts/embed.py' to generate embeddings")


if __name__ == "__main__":
    main()
