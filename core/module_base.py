# core/module_base.py
"""
Base class for all security modules in the MCP server.
Provides common interface and functionality that all modules must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class Tool:
    """Tool definition for MCP protocol"""
    name: str
    description: str
    inputSchema: Dict[str, Any]

@dataclass
class ModuleConfig:
    """Module configuration container"""
    name: str
    enabled: bool
    config: Dict[str, Any]
    dependencies: List[str]

class SecurityModuleBase(ABC):
    """
    Abstract base class for all security modules.
    
    Each security tool (Nuclei, Shodan, etc.) should inherit from this class
    and implement the required methods.
    """
    
    def __init__(self, config: ModuleConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        self.logger = logging.getLogger(f"module.{self.name}")
        self._tools = []
        self._initialize()
    
    def _initialize(self):
        """Initialize the module. Override for custom initialization."""
        self.logger.info(f"Initializing {self.name} module")
        
        # Validate dependencies
        if not self._check_dependencies():
            self.enabled = False
            self.logger.warning(f"Module {self.name} disabled due to missing dependencies")
            return
        
        # Load tools
        try:
            self._tools = self._register_tools()
            self.logger.info(f"Registered {len(self._tools)} tools for {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to register tools for {self.name}: {str(e)}")
            self.enabled = False
    
    @abstractmethod
    def _register_tools(self) -> List[Tool]:
        """
        Register all tools provided by this module.
        
        Returns:
            List[Tool]: List of tool definitions
        """
        pass
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, **kwargs) -> str:
        """
        Execute a specific tool with given parameters.
        
        Args:
            tool_name (str): Name of the tool to execute
            **kwargs: Tool-specific parameters
            
        Returns:
            str: Tool execution result
        """
        pass
    
    @abstractmethod
    def _check_dependencies(self) -> bool:
        """
        Check if all module dependencies are available.
        
        Returns:
            bool: True if all dependencies are met
        """
        pass
    
    def get_tools(self) -> List[Tool]:
        """Get list of tools provided by this module."""
        if not self.enabled:
            return []
        return self._tools
    
    def is_available(self) -> bool:
        """Check if module is available and enabled."""
        return self.enabled and self._check_dependencies()
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get specific tool by name."""
        for tool in self._tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if module provides a specific tool."""
        return self.get_tool(tool_name) is not None
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to default."""
        return self.config.config.get(key, default)
    
    def get_status(self) -> Dict[str, Any]:
        """Get module status information."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "available": self.is_available(),
            "tools_count": len(self._tools),
            "tools": [tool.name for tool in self._tools],
            "dependencies_met": self._check_dependencies()
        }
    
    async def safe_execute_tool(self, tool_name: str, **kwargs) -> str:
        """
        Safely execute a tool with error handling and validation.
        """
        try:
            if not self.is_available():
                return f"❌ Module '{self.name}' is not available"
            
            if not self.has_tool(tool_name):
                return f"❌ Tool '{tool_name}' not found in module '{self.name}'"
            
            self.logger.info(f"Executing tool '{tool_name}' with params: {list(kwargs.keys())}")
            
            result = await self.execute_tool(tool_name, **kwargs)
            
            self.logger.info(f"Tool '{tool_name}' executed successfully")
            return result
            
        except Exception as e:
            error_msg = f"❌ Error executing '{tool_name}' in module '{self.name}': {str(e)}"
            self.logger.error(error_msg)
            return error_msg


class ModuleRegistry:
    """Registry for managing security modules."""
    
    def __init__(self):
        self.modules: Dict[str, SecurityModuleBase] = {}
        self.logger = logging.getLogger("module_registry")
    
    def register_module(self, module: SecurityModuleBase):
        """Register a module in the registry."""
        self.modules[module.name] = module
        self.logger.info(f"Registered module: {module.name}")
    
    def get_module(self, name: str) -> Optional[SecurityModuleBase]:
        """Get module by name."""
        return self.modules.get(name)
    
    def get_all_modules(self) -> List[SecurityModuleBase]:
        """Get all registered modules."""
        return list(self.modules.values())
    
    def get_enabled_modules(self) -> List[SecurityModuleBase]:
        """Get only enabled modules."""
        return [module for module in self.modules.values() if module.enabled]
    
    def get_all_tools(self) -> List[Tool]:
        """Get all tools from all enabled modules."""
        tools = []
        for module in self.get_enabled_modules():
            tools.extend(module.get_tools())
        return tools
    
    def find_tool(self, tool_name: str) -> Optional[SecurityModuleBase]:
        """Find which module provides a specific tool."""
        for module in self.get_enabled_modules():
            if module.has_tool(tool_name):
                return module
        return None
    
    async def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by finding the appropriate module."""
        module = self.find_tool(tool_name)
        if not module:
            return f"❌ Tool '{tool_name}' not found in any enabled module"
        
        return await module.safe_execute_tool(tool_name, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all modules."""
        return {
            "total_modules": len(self.modules),
            "enabled_modules": len(self.get_enabled_modules()),
            "total_tools": len(self.get_all_tools()),
            "modules": {name: module.get_status() for name, module in self.modules.items()}
        }