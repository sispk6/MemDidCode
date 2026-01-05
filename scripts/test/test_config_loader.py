import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import load_config

def test_config_loader():
    print("Testing Config Loader...")
    
    # Test 1: Default Config
    if "MEMDID_CONFIG_FILE" in os.environ:
        del os.environ["MEMDID_CONFIG_FILE"]
    
    config = load_config()
    print(f"Default config loaded: {len(config)} keys")
    # Check a key that should exist in both
    if 'gmail' in config:
        print("[PASS] Default config loading")
    else:
        print("[FAIL] Default config loading")

    # Test 2: Standalone Config
    os.environ["MEMDID_CONFIG_FILE"] = "config_standalone.yaml"
    config_standalone = load_config()
    print(f"Standalone config loaded: {len(config_standalone)} keys")
    
    if 'gmail' in config_standalone:
         print("[PASS] Standalone config loading")
    else:
         print("[FAIL] Standalone config loading")

if __name__ == "__main__":
    test_config_loader()
