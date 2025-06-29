# core/module_loader.py
"""
Dynamic module loader for the Security MCP Server.
Automatically discovers and loads security modules from the modules directory.
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
import logging
import yaml

from .module_base import SecurityModuleBase, ModuleConfig, ModuleRegistry

class ModuleLoader:
    """
    Loads and manages security modules dynamically.
    
    Discovers modules in the modules directory and loads them based on configuration.
    """
    
    def __init__(self, modules_dir: str = "modules", config_path: str = "config/modules_config.yaml"):
        self.modules_dir = Path(modules_dir)
        self.config_path = Path(config_path)
        self.logger = logging.getLogger("module_loader")
        self.registry = ModuleRegistry()
        self._module_configs = {}
        
        # Load module configurations
        self._load_module_configs()
    
    def _load_module_configs(self):
        """Load module configurations from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self._module_configs = yaml.safe_load(f) or {}
                self.logger.info(f"Loaded module configs from {self.config_path}")
            else:
                self.logger.warning(f"Module config file not found: {self.config_path}")
                self._module_configs = {}
        except Exception as e:
            self.logger.error(f"Failed to load module configs: {str(e)}")
            self._module_configs = {}
    
    def discover_modules(self) -> List[str]:
        """Discover available modules in the modules directory."""
        modules = []
        
        if not self.modules_dir.exists():
            self.logger.warning(f"Modules directory not found: {self.modules_dir}")
            return modules
        
        for file_path in self.modules_dir.glob("*_module.py"):
            if file_path.is_file() and not file_path.name.startswith("__"):
                module_name = file_path.stem.replace("_module", "")
                modules.append(module_name)
                self.logger.debug(f"Discovered module: {module_name}")
        
        self.logger.info(f"Discovered {len(modules)} modules: {modules}")
        return modules
    
    def _get_module_config(self, module_name: str) -> ModuleConfig:
        """Get configuration for a specific module."""
        config_data = self._module_configs.get(module_name, {})
        
        return ModuleConfig(
            name=module_name,
            enabled=config_data.get("enabled", True),
            config=config_data.get("config", {}),
            dependencies=config_data.get("dependencies", [])
        )
    
    def _load_module_class(self, module_name: str) -> Optional[Type[SecurityModuleBase]]:
        """Load a module class from file."""
        try:
            module_file = self.modules_dir / f"{module_name}_module.py"
            
            if not module_file.exists():
                self.logger.error(f"Module file not found: {module_file}")
                return None
            
            # Load module spec
            spec = importlib.util.spec_from_file_location(
                f"modules.{module_name}_module", 
                module_file
            )
            
            if spec is None or spec.loader is None:
                self.logger.error(f"Failed to create spec for module: {module_name}")
                return None
            
            # Import module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the module class
            class_name = f"{module_name.title()}Module"
            
            if not hasattr(module, class_name):
                self.logger.error(f"Module class '{class_name}' not found in {module_file}")
                return None
            
            module_class = getattr(module, class_name)
            
            # Verify it's a subclass of SecurityModuleBase
            if not issubclass(module_class, SecurityModuleBase):
                self.logger.error(f"Module class '{class_name}' is not a subclass of SecurityModuleBase")
                return None
            
            self.logger.debug(f"Successfully loaded module class: {class_name}")
            return module_class
            
        except Exception as e:
            self.logger.error(f"Failed to load module '{module_name}': {str(e)}")
            return None
    
    def load_module(self, module_name: str) -> Optional[SecurityModuleBase]:
        """Load a specific module."""
        try:
            config = self._get_module_config(module_name)
            
            if not config.enabled:
                self.logger.info(f"Module '{module_name}' is disabled in configuration")
                return None
            
            module_class = self._load_module_class(module_name)
            if module_class is None:
                return None
            
            module_instance = module_class(config)
            self.registry.register_module(module_instance)
            
            self.logger.info(f"Successfully loaded module: {module_name}")
            return module_instance
            
        except Exception as e:
            self.logger.error(f"Failed to load module '{module_name}': {str(e)}")
            return None
    
    def load_all_modules(self, enabled_modules: Optional[List[str]] = None) -> int:
        """Load all discovered modules or a specific subset."""
        discovered_modules = self.discover_modules()
        
        if enabled_modules is not None:
            modules_to_load = [m for m in discovered_modules if m in enabled_modules]
        else:
            modules_to_load = discovered_modules
        
        loaded_count = 0
        
        for module_name in modules_to_load:
            if self.load_module(module_name) is not None:
                loaded_count += 1
        
        self.logger.info(f"Loaded {loaded_count}/{len(modules_to_load)} modules")
        return loaded_count
    
    def get_registry(self) -> ModuleRegistry:
        """Get the module registry."""
        return self.registry
    
    def get_loader_status(self) -> Dict[str, Any]:
        """Get loader status information."""
        discovered = self.discover_modules()
        loaded = list(self.registry.modules.keys())
        
        return {
            "modules_directory": str(self.modules_dir),
            "config_file": str(self.config_path),
            "discovered_modules": discovered,
            "loaded_modules": loaded,
            "failed_modules": [m for m in discovered if m not in loaded],
            "registry_status": self.registry.get_status()
        }