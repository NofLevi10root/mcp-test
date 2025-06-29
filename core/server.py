# core/server.py
"""
Core MCP Server implementation.
Handles JSON-RPC protocol and coordinates with security modules.
"""

import asyncio
import json
import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .module_loader import ModuleLoader
from .module_base import ModuleRegistry

class SecurityMCPServer:
    """
    Main MCP Server that handles the Model Context Protocol.
    
    Coordinates between the MCP protocol and security modules.
    """
    
    def __init__(self, 
                 name: str = "security-mcp-server", 
                 version: str = "2.0.0",
                 modules_dir: str = "modules",
                 config_path: str = "config"):
        
        self.name = name
        self.version = version
        self.initialized = False
        self.logger = logging.getLogger("mcp_server")
        
        # Module management
        self.module_loader = ModuleLoader(
            modules_dir=modules_dir,
            config_path=f"{config_path}/modules_config.yaml"
        )
        self.registry: ModuleRegistry = self.module_loader.get_registry()
        
        # Server statistics
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        
        self.logger.info(f"Security MCP Server initialized: {name} v{version}")
    
    async def initialize_modules(self, enabled_modules: Optional[List[str]] = None) -> int:
        """
        Initialize and load security modules.
        """
        self.logger.info("Loading security modules...")
        loaded_count = self.module_loader.load_all_modules(enabled_modules)
        
        # Log module status
        for module in self.registry.get_all_modules():
            status = "✅ ENABLED" if module.enabled else "❌ DISABLED"
            self.logger.info(f"Module {module.name}: {status}")
        
        self.logger.info(f"Module initialization complete: {loaded_count} modules loaded")
        return loaded_count
    
    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle incoming JSON-RPC messages.
        """
        self.request_count += 1
        
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        self.logger.debug(f"Handling request: {method} (ID: {msg_id})")
        
        try:
            if method == "initialize":
                return await self._handle_initialize(msg_id, params)
            elif method == "tools/list":
                return await self._handle_tools_list(msg_id)
            elif method == "tools/call":
                return await self._handle_tools_call(msg_id, params)
            elif method == "server/status":
                return await self._handle_server_status(msg_id)
            else:
                return self._error_response(msg_id, -32601, f"Method not found: {method}")
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error handling message: {str(e)}")
            return self._error_response(msg_id, -32603, f"Internal error: {str(e)}")
    
    async def _handle_initialize(self, msg_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle client initialization request."""
        self.initialized = True
        
        client_info = params.get("clientInfo", {})
        self.logger.info(f"Client connected: {client_info.get('name', 'Unknown')}")
        
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            }
        }
    
    async def _handle_tools_list(self, msg_id: int) -> Dict[str, Any]:
        """Handle tools listing request."""
        tools = self.registry.get_all_tools()
        
        # Convert Tool objects to dictionaries for JSON serialization
        tools_dict = []
        for tool in tools:
            tools_dict.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        
        self.logger.debug(f"Returning {len(tools_dict)} tools")
        
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": tools_dict
            }
        }
    
    async def _handle_tools_call(self, msg_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return self._error_response(msg_id, -32602, "Missing tool name")
        
        self.logger.info(f"Executing tool: {tool_name}")
        
        # Execute tool through registry
        result = await self.registry.execute_tool(tool_name, **arguments)
        
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
        }
    
    async def _handle_server_status(self, msg_id: int) -> Dict[str, Any]:
        """Handle server status request."""
        uptime = datetime.now() - self.start_time
        status = {
            "server": {
                "name": self.name,
                "version": self.version,
                "uptime_seconds": int(uptime.total_seconds()),
                "requests_handled": self.request_count,
                "errors": self.error_count
            },
            "modules": self.registry.get_status()
        }
        
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": status
        }
    
    def _error_response(self, msg_id: Optional[int], code: int, message: str) -> Dict[str, Any]:
        """Create JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def run_stdio(self):
        """Main event loop for stdio transport."""
        self.logger.info("🛡️  Security MCP Server started (stdio mode)")
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                message = json.loads(line)
                response = await self.handle_message(message)
                
                if response:
                    print(json.dumps(response), flush=True)
                    
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                break
        
        self.logger.info("MCP Server shutdown")