"""
Base connector interface for all data sources.
Path: src/ingest/base_connector.py
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class BaseConnector(ABC):
    """Abstract base class for all platform connectors (Gmail, Slack, etc.)"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration.
        
        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.platform_name = self._get_platform_name()
    
    @abstractmethod
    def _get_platform_name(self) -> str:
        """Return the platform name (e.g., 'gmail', 'slack')"""
        pass
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the platform API.
        
        Returns:
            bool: True if authentication successful
        """
        pass
    
    @abstractmethod
    def fetch_messages(self, max_results: int = 100, since_date: str = None, since_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch messages from the platform.
        
        Args:
            max_results: Maximum number of messages to fetch
            since_date: ISO format date to fetch messages from
            since_id: Last processed message ID
            
        Returns:
            List of message dictionaries in universal format
        """
        pass
    
    def normalize_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert platform-specific message format to universal format.
        
        Args:
            raw_message: Platform-specific message data
            
        Returns:
            Normalized message in universal format
        """
        return {
            "id": self._extract_id(raw_message),
            "platform": self.platform_name,
            "type": self._extract_type(raw_message),
            "from": self._extract_sender(raw_message),
            "to": self._extract_recipients(raw_message),
            "date": self._extract_date(raw_message),
            "subject": self._extract_subject(raw_message),
            "content": self._extract_content(raw_message),
            "attachments": self._extract_attachments(raw_message),
            "thread_id": self._extract_thread_id(raw_message),
            "url": self._generate_url(raw_message),
            "raw_data": raw_message  # Keep original for reference
        }
    
    @abstractmethod
    def _extract_id(self, raw_message: Dict[str, Any]) -> str:
        """Extract unique message ID"""
        pass
    
    @abstractmethod
    def _extract_type(self, raw_message: Dict[str, Any]) -> str:
        """Extract message type (email, dm, channel_message, etc.)"""
        pass
    
    @abstractmethod
    def _extract_sender(self, raw_message: Dict[str, Any]) -> Dict[str, str]:
        """Extract sender information"""
        pass
    
    @abstractmethod
    def _extract_recipients(self, raw_message: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract recipient information"""
        pass
    
    @abstractmethod
    def _extract_date(self, raw_message: Dict[str, Any]) -> str:
        """Extract and normalize timestamp to ISO format"""
        pass
    
    @abstractmethod
    def _extract_subject(self, raw_message: Dict[str, Any]) -> str:
        """Extract subject/title"""
        pass
    
    @abstractmethod
    def _extract_attachments(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract attachments from message.
        
        Returns:
            List of dicts with 'filename', 'content' (extracted text), 'mime_type'
        """
        pass
    
    @abstractmethod
    def _extract_content(self, raw_message: Dict[str, Any]) -> str:
        """Extract message content/body"""
        pass
    
    @abstractmethod
    def _extract_thread_id(self, raw_message: Dict[str, Any]) -> str:
        """Extract thread/conversation ID"""
        pass
    
    @abstractmethod
    def _generate_url(self, raw_message: Dict[str, Any]) -> str:
        """Generate URL to view original message"""
        pass
    
    def save_raw_data(self, messages: List[Dict[str, Any]], output_path: str):
        """
        Save raw messages to JSON file.
        
        Args:
            messages: List of messages
            output_path: Path to save JSON file
        """
        import json
        from pathlib import Path
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "platform": self.platform_name,
                "fetch_date": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": messages
            }, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Saved {len(messages)} messages to {output_path}")