#!/usr/bin/env python3
"""
Security MCP Server - Main Entry Point
Modular security testing framework with Nuclei, Shodan, and LeakCheck integration.

Usage:
    python main.py                    # Load all available modules
    python main.py --modules nuclei   # Load specific modules
    python main.py --debug            # Enable debug logging
    python main.py --status           # Show server status
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.server import SecurityMCPServer
from utils.logger import setup_logging

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Security MCP Server - Modular security testing framework",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--modules', 
        type=str, 
        help='Comma-separated list of modules to load (e.g., nuclei,shodan)'
    )
    
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--status', 
        action='store_true', 
        help='Show server status and exit'
    )
    
    parser.add_argument(
        '--config-dir', 
        type=str, 
        default='config', 
        help='Configuration directory path'
    )
    
    parser.add_argument(
        '--modules-dir', 
        type=str, 
        default='modules', 
        help='Modules directory path'
    )
    
    return parser.parse_args()

async def show_status(server: SecurityMCPServer):
    """Show server and modules status."""
    print("🛡️  Security MCP Server Status")
    print("=" * 40)
    
    # Initialize modules to get status
    await server.initialize_modules()
    
    # Get loader status
    loader_status = server.module_loader.get_loader_status()
    
    print(f"📁 Modules Directory: {loader_status['modules_directory']}")
    print(f"⚙️  Config File: {loader_status['config_file']}")
    print(f"🔍 Discovered Modules: {len(loader_status['discovered_modules'])}")
    print(f"✅ Loaded Modules: {len(loader_status['loaded_modules'])}")
    
    if loader_status['failed_modules']:
        print(f"❌ Failed Modules: {len(loader_status['failed_modules'])}")
    
    print("\n📊 Module Details:")
    registry_status = loader_status['registry_status']
    
    for module_name, module_status in registry_status['modules'].items():
        status_icon = "✅" if module_status['enabled'] and module_status['available'] else "❌"
        print(f"   {status_icon} {module_name}: {module_status['tools_count']} tools")
        
        if not module_status['dependencies_met']:
            print(f"      ⚠️  Missing dependencies")
    
    print(f"\n🔧 Total Tools Available: {registry_status['total_tools']}")

async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    
    # Create server
    server = SecurityMCPServer(
        modules_dir=args.modules_dir,
        config_path=args.config_dir
    )
    
    # Handle status command
    if args.status:
        await show_status(server)
        return
    
    # Parse enabled modules
    enabled_modules = None
    if args.modules:
        enabled_modules = [m.strip() for m in args.modules.split(',')]
        print(f"🎯 Loading specific modules: {enabled_modules}")
    
    try:
        # Initialize modules
        print("🚀 Starting Security MCP Server...")
        loaded_count = await server.initialize_modules(enabled_modules)
        
        if loaded_count == 0:
            print("❌ No modules loaded. Check configuration and dependencies.")
            sys.exit(1)
        
        print(f"✅ {loaded_count} modules loaded successfully")
        print("🎮 Server ready - waiting for MCP client connections...")
        print("📚 Available tools:")
        
        # Show available tools
        tools = server.registry.get_all_tools()
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        print("\n⚠️  SECURITY NOTICE: Only use on authorized systems!")
        print("-" * 50)
        
        # Start MCP server
        await server.run_stdio()
        
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())