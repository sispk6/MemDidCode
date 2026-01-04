"""
MCP-compatible Gmail connector.
Path: src/ingest/mcp_gmail_connector.py

This wraps the existing GmailConnector to provide MCP compatibility
while maintaining backward compatibility with existing code.
"""
from typing import List, Dict, Any
from .mcp_connector_base import MCPConnectorBase
from .gmail_connector import GmailConnector


class MCPGmailConnector(MCPConnectorBase):
    """
    MCP-compatible Gmail connector that wraps the existing GmailConnector.
    
    This allows using Gmail through the MCP protocol while maintaining
    the same data format and authentication flow.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MCP Gmail connector.
        
        Args:
            config: Configuration dictionary (same as GmailConnector)
        """
        # Initialize the legacy Gmail connector
        self.gmail_connector = GmailConnector(config)
        
        # Initialize MCP base
        super().__init__(config)
    
    def _get_platform_name(self) -> str:
        """Return platform name"""
        return "gmail"
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Uses the existing GmailConnector authentication flow.
        """
        # The existing connector is synchronous, so we just call it directly
        return self.gmail_connector.authenticate()
    
    async def fetch_messages(self, max_results: int = 100, since_date: str = None, since_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch messages from Gmail.
        """
        # The existing connector is synchronous, so we just call it directly
        return self.gmail_connector.fetch_messages(max_results, since_date, since_id)
    
    async def search_messages(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Gmail messages.
        
        This uses Gmail's native search syntax for better results.
        
        Args:
            query: Search query (Gmail search syntax supported)
            max_results: Maximum number of results
            
        Returns:
            List of matching messages
        """
        if not self.gmail_connector.service:
            await self.authenticate()
        
        try:
            # Use Gmail's search API
            results = self.gmail_connector.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch full message details
            detailed_messages = []
            for msg in messages:
                try:
                    full_msg = self.gmail_connector.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    normalized = self.gmail_connector.normalize_message(full_msg)
                    detailed_messages.append(normalized)
                    
                except Exception as e:
                    print(f"[WARN] Error fetching message {msg['id']}: {e}")
                    continue
            
            return detailed_messages
            
        except Exception as e:
            print(f"[ERROR] Error searching messages: {e}")
            # Fallback to base class implementation
            return await super().search_messages(query, max_results)
    
    # Synchronous wrapper methods for backward compatibility
    def authenticate_sync(self) -> bool:
        """Synchronous authentication (backward compatible)"""
        return self.gmail_connector.authenticate()
    
    def fetch_messages_sync(self, max_results: int = 100, since_date: str = None, since_id: str = None) -> List[Dict[str, Any]]:
        """Synchronous message fetching (backward compatible)"""
        return self.gmail_connector.fetch_messages(max_results, since_date, since_id)
    
    def save_raw_data(self, messages: List[Dict[str, Any]], output_path: str):
        """Save raw messages to JSON file (backward compatible)"""
        self.gmail_connector.save_raw_data(messages, output_path)


# Convenience function for creating MCP Gmail connector
def create_mcp_gmail_connector(config: Dict[str, Any]) -> MCPGmailConnector:
    """
    Create and return an MCP Gmail connector.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        MCPGmailConnector instance
    """
    return MCPGmailConnector(config)
