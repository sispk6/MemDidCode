"""
Test script for MCP Gmail connector.
Path: tests/test_mcp_gmail_connector.py

This tests the MCP Gmail connector to ensure it works correctly.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.mcp_gmail_connector import MCPGmailConnector
import yaml


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def test_initialization():
    """Test MCP connector initialization"""
    print("=" * 80)
    print("Test 1: MCP Connector Initialization")
    print("=" * 80)
    print()
    
    config = load_config()
    gmail_config = config['gmail']
    
    try:
        connector = MCPGmailConnector(gmail_config)
        print("[PASS] MCP connector initialized successfully")
        print(f"   Platform: {connector.platform_name}")
        print(f"   Has Gmail connector: {connector.gmail_connector is not None}")
        return True
    except Exception as e:
        print(f"[FAIL] Initialization failed: {e}")
        return False


def test_authentication():
    """Test authentication"""
    print()
    print("=" * 80)
    print("Test 2: Authentication")
    print("=" * 80)
    print()
    
    config = load_config()
    gmail_config = config['gmail']
    
    try:
        connector = MCPGmailConnector(gmail_config)
        
        # Test sync authentication
        if connector.authenticate_sync():
            print("[PASS] Authentication successful")
            return True
        else:
            print("[FAIL] Authentication failed")
            return False
    except Exception as e:
        print(f"[FAIL] Authentication error: {e}")
        return False


def test_fetch_messages():
    """Test message fetching"""
    print()
    print("=" * 80)
    print("Test 3: Fetch Messages")
    print("=" * 80)
    print()
    
    config = load_config()
    gmail_config = config['gmail']
    
    try:
        connector = MCPGmailConnector(gmail_config)
        connector.authenticate_sync()
        
        # Fetch a small number of messages for testing
        messages = connector.fetch_messages_sync(max_results=5)
        
        if messages:
            print(f"[PASS] Fetched {len(messages)} messages")
            
            # Verify message format
            first_msg = messages[0]
            required_fields = ['id', 'platform', 'from', 'to', 'date', 'subject', 'content']
            
            missing_fields = [field for field in required_fields if field not in first_msg]
            
            if not missing_fields:
                print("[PASS] Message format is correct")
                print(f"   Sample message ID: {first_msg['id']}")
                print(f"   Platform: {first_msg['platform']}")
                print(f"   Subject: {first_msg['subject'][:50]}...")
                return True
            else:
                print(f"[FAIL] Missing fields in message: {missing_fields}")
                return False
        else:
            print("[WARN] No messages fetched (might be empty inbox)")
            return True  # Not a failure if inbox is empty
            
    except Exception as e:
        print(f"[FAIL] Fetch error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("=" * 80)
    print(" " * 20 + "MCP Gmail Connector Tests")
    print("=" * 80)
    print()
    
    results = []
    
    # Run tests
    results.append(("Initialization", test_initialization()))
    results.append(("Authentication", test_authentication()))
    results.append(("Fetch Messages", test_fetch_messages()))
    
    # Summary
    print()
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}  {test_name}")
    
    print()
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
