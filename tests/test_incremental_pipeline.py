import os
import shutil
import json
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.state_manager import StateManager

TEST_DATA_DIR = "./data/test_incremental"
TEST_STATE_FILE = os.path.join(TEST_DATA_DIR, "system_state.json")

@pytest.fixture
def clean_incremental_env():
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    os.makedirs(TEST_DATA_DIR)
    
    # Mock config to use this directory
    yield
    
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)

def test_state_manager_logic(clean_incremental_env):
    state_mgr = StateManager(state_file=TEST_STATE_FILE)
    
    # 1. Initial state should be None by default
    state = state_mgr.get_state("ingestion", "gmail")
    assert state is None
    
    # Or with default
    state = state_mgr.get_state("ingestion", "gmail", default={})
    assert state == {}
    
    # 2. Update state
    state_mgr.update_state("ingestion", "gmail", {"last_date": "2024-01-01", "last_id": "123"})
    
    # 3. Read back
    state = state_mgr.get_state("ingestion", "gmail")
    assert state["last_date"] == "2024-01-01"
    assert state["last_id"] == "123"
    
    # 4. List management
    assert not state_mgr.is_in_list("embedding", "gmail", "file1.json")
    state_mgr.add_to_list("embedding", "gmail", "file1.json")
    assert state_mgr.is_in_list("embedding", "gmail", "file1.json")
    
    # 5. Persistence
    new_mgr = StateManager(state_file=TEST_STATE_FILE)
    assert new_mgr.is_in_list("embedding", "gmail", "file1.json")
    assert new_mgr.get_state("ingestion", "gmail")["last_id"] == "123"
