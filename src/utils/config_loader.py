import os
import yaml
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    The config file is determined by:
    1. MEMDID_CONFIG_FILE environment variable
    2. Default: 'config.yaml'
    
    Paths are resolved relative to the project root (parent of src/).
    """
    # Determine project root (parent of this utils directory is src, parent of src is root)
    root_path = Path(__file__).parent.parent.parent
    
    config_filename = os.environ.get("MEMDID_CONFIG_FILE", "config.yaml")
    config_path = root_path / config_filename
    
    if not config_path.exists():
        # Fallback/Error handling
        # If we are in specific test environments, we might want to warn
        print(f"[WARN] Config file not found at {config_path}")
        return {}
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    return config

def get_project_root() -> Path:
    """Return the absolute path to the project root."""
    return Path(__file__).parent.parent.parent
