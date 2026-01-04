"""
StateManager for tracking ingestion, embedding, and other system progress.
Path: src/utils/state_manager.py
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

class StateManager:
    """
    Manages a JSON state file to track progress across multiple modules and platforms.
    """
    
    def __init__(self, state_file: str = "data/system_state.json", auto_save: bool = True):
        self.state_file = Path(state_file)
        self.auto_save = auto_save
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load state file: {e}. Starting fresh.")
                return {}
        return {}

    def save(self):
        """Save current state to JSON file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2)
            
    def _save(self):
        """Internal save method that checks auto_save flag."""
        if self.auto_save:
            self.save()

    def get_state(self, module: str, platform: str, default: Any = None) -> Any:
        """
        Get state for a specific module and platform.
        Examples: module="ingestion", platform="gmail"
        """
        return self.state.get(module, {}).get(platform, default)

    def update_state(self, module: str, platform: str, data: Any):
        """
        Update state for a specific module and platform.
        """
        if module not in self.state:
            self.state[module] = {}
        
        # If data is a dict, merge it if possible, otherwise replace
        if isinstance(data, dict) and isinstance(self.state[module].get(platform), dict):
            self.state[module][platform].update(data)
        else:
            self.state[module][platform] = data
            
        self._save()

    def add_to_list(self, module: str, platform: str, item: Any):
        """
        Add an item to a list in the state (useful for tracking processed files).
        """
        if module not in self.state:
            self.state[module] = {}
        if platform not in self.state[module]:
            self.state[module][platform] = []
        
        if isinstance(self.state[module][platform], list):
            if item not in self.state[module][platform]:
                self.state[module][platform].append(item)
                self._save()
        else:
            print(f"[ERROR] Cannot add to list: state[{module}][{platform}] is not a list.")

    def is_in_list(self, module: str, platform: str, item: Any) -> bool:
        """Check if an item is in a list state."""
        items = self.get_state(module, platform, default=[])
        return item in items if isinstance(items, list) else False
