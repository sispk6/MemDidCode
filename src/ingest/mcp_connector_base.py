"""
MCP-compatible base connector for all data sources.
Path: src/ingest/mcp_connector_base.py

This provides a base class for creating MCP-compatible connectors
that can be easily extended for different platforms (Gmail, Slack, etc.)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server


class MCPConnectorBase(ABC):
    """
    Abstract base class for MCP-compatible platform connectors.
    
    This class bridges between the MCP protocol and your existing
    connector architecture, allowing gradual migration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MCP connector with configuration.
        
        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.platform_name = self._get_platform_name()
        self.server = Server(self.platform_name)
        
        # Register MCP handlers
        self._register_resources()
        self._register_tools()
    
    @abstractmethod
    def _get_platform_name(self) -> str:
        """Return the platform name (e.g., 'gmail', 'slack')"""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the platform API.
        
        Returns:
            bool: True if authentication successful
        """
        pass
    
    @abstractmethod
    async def fetch_messages(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch messages from the platform.
        
        Args:
            max_results: Maximum number of messages to fetch
            
        Returns:
            List of message dictionaries in universal format
        """
        pass
    
    def _register_resources(self):
        """Register MCP resources (read-only data access)"""
        
        @self.server.list_resources()
        async def list_resources() -> List[types.Resource]:
            """List available resources"""
            return [
                types.Resource(
                    uri=f"{self.platform_name}://messages",
                    name=f"{self.platform_name.title()} Messages",
                    description=f"Access to {self.platform_name} messages",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific resource"""
            if uri == f"{self.platform_name}://messages":
                messages = await self.fetch_messages()
                import json
                return json.dumps(messages, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    def _register_tools(self):
        """Register MCP tools (actions that can be performed)"""
        
        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name=f"{self.platform_name}_list_messages",
                    description=f"List messages from {self.platform_name}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of messages to fetch",
                                "default": 100
                            }
                        }
                    }
                ),
                types.Tool(
                    name=f"{self.platform_name}_search_messages",
                    description=f"Search messages in {self.platform_name}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Execute a tool"""
            if name == f"{self.platform_name}_list_messages":
                max_results = arguments.get("max_results", 100)
                messages = await self.fetch_messages(max_results)
                
                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(messages, indent=2)
                )]
            
            elif name == f"{self.platform_name}_search_messages":
                query = arguments["query"]
                max_results = arguments.get("max_results", 10)
                
                # Implement search logic (to be overridden by subclasses)
                results = await self.search_messages(query, max_results)
                
                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def search_messages(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search messages (to be implemented by subclasses).
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of matching messages
        """
        # Default implementation: fetch all and filter by simple text match
        all_messages = await self.fetch_messages(max_results * 2)
        
        results = []
        for msg in all_messages:
            content = msg.get('content', '').lower()
            subject = msg.get('subject', '').lower()
            
            if query.lower() in content or query.lower() in subject:
                results.append(msg)
                
                if len(results) >= max_results:
                    break
        
        return results
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
