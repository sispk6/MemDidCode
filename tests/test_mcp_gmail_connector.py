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


import pytest

@pytest.fixture(scope="module")
def config():
    """Load configuration"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="module")
def connector(config):
    """Test MCP connector initialization"""
    gmail_config = config['gmail']
    return MCPGmailConnector(gmail_config)

def test_initialization(connector):
    """Test MCP connector initialization"""
    assert connector is not None
    assert connector.platform_name == "gmail"
    assert connector.gmail_connector is not None

def test_authentication(connector):
    """Test authentication"""
    assert connector.authenticate_sync() is True

def test_fetch_messages(connector):
    """Test message fetching"""
    # Fetch a small number of messages for testing
    messages = connector.fetch_messages_sync(max_results=5)
    
    if messages:
        # Verify message format
        first_msg = messages[0]
        required_fields = ['id', 'platform', 'from', 'to', 'date', 'subject', 'content']
        
        for field in required_fields:
            assert field in first_msg, f"Missing required field: {field}"
            
        assert first_msg['platform'] == 'gmail'
        assert isinstance(first_msg['id'], str)
    else:
        # If inbox is empty, it's not a failure but we print a warning
        pytest.skip("No messages fetched (might be empty inbox)")
