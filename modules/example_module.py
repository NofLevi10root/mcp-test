# modules/example_module.py
"""
Example security module template.
Copy this file to create new modules.
"""

import asyncio
from typing import List

from core.module_base import SecurityModuleBase, Tool, ModuleConfig
from utils.validators import validate_target

class ExampleModule(SecurityModuleBase):
    """
    Example module showing how to implement security tools.
    
    This module provides basic example tools for demonstration.
    """
    
    def _register_tools(self) -> List[Tool]:
        """Register tools provided by this module."""
        return [
            Tool(
                name="example_ping",
                description="Example ping tool for testing connectivity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target to ping (IP or domain)"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of ping packets",
                            "minimum": 1,
                            "maximum": 10,
                            "default": 4
                        }
                    },
                    "required": ["target"]
                }
            ),
            Tool(
                name="example_info",
                description="Get example module information",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    def _check_dependencies(self) -> bool:
        """
        Check if module dependencies are available.
        
        For this example, we just check if ping command exists.
        """
        try:
            import subprocess
            result = subprocess.run(['ping', '-c', '1', '127.0.0.1'], 
                                  capture_output=True, timeout=5)
            return True
        except Exception:
            return False
    
    async def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute the specified tool."""
        
        if tool_name == "example_ping":
            return await self._ping_tool(**kwargs)
        elif tool_name == "example_info":
            return await self._info_tool()
        else:
            return f"❌ Unknown tool: {tool_name}"
    
    async def _ping_tool(self, target: str, count: int = 4) -> str:
        """
        Example ping implementation.
        
        Args:
            target: Target to ping
            count: Number of ping packets
            
        Returns:
            str: Ping results
        """
        # Validate target
        is_valid, target_type, error = validate_target(target)
        if not is_valid:
            return f"❌ Invalid target: {error}"
        
        # Limit count for safety
        count = min(max(count, 1), 10)
        
        try:
            import subprocess
            
            # Run ping command
            result = await asyncio.create_subprocess_exec(
                'ping', '-c', str(count), target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                output = stdout.decode('utf-8')
                return f"🏠 Ping Results for {target}:\n\n{output}"
            else:
                error_msg = stderr.decode('utf-8')
                return f"❌ Ping failed for {target}:\n{error_msg}"
                
        except Exception as e:
            return f"❌ Error executing ping: {str(e)}"
    
    async def _info_tool(self) -> str:
        """
        Get module information.
        
        Returns:
            str: Module information
        """
        info = f"""📄 Example Module Information

Module: {self.name}
Status: {'Enabled' if self.enabled else 'Disabled'}
Tools: {len(self._tools)}
Config: {self.config.config}

This is an example module that demonstrates:
- Tool registration and execution
- Input validation
- Async tool execution
- Error handling

Use this as a template for creating new security modules."""
        
        return info