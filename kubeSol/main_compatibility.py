# kubeSol/main_compatibility.py
"""
KubeSol Compatibility Entry Point

This module provides backward compatibility by checking for environment variables
or command line arguments to determine whether to use the legacy system or the
new plugin-based system.
"""

import os
import sys
import argparse

def main():
    """
    Main entry point that chooses between legacy and plugin-based systems.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="KubeSol - SQL-like interface for Kubernetes")
    parser.add_argument(
        "--system", 
        choices=["legacy", "plugin"], 
        default=None,
        help="Choose which system to use (legacy or plugin)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug output"
    )
    
    args, unknown = parser.parse_known_args()
    
    # Determine which system to use
    use_plugin_system = False
    
    # Check command line argument first
    if args.system == "plugin":
        use_plugin_system = True
    elif args.system == "legacy":
        use_plugin_system = False
    else:
        # Check environment variable
        system_env = os.environ.get("KUBESOL_SYSTEM", "").lower()
        if system_env == "plugin":
            use_plugin_system = True
        elif system_env == "legacy":
            use_plugin_system = False
        else:
            # Default behavior: try plugin system first, fallback to legacy
            use_plugin_system = True
    
    if args.debug:
        system_name = "plugin-based" if use_plugin_system else "legacy"
        print(f"🔍 Using {system_name} system")
    
    if use_plugin_system:
        try:
            from kubeSol.main_plugin_system import main as plugin_main
            plugin_main()
        except ImportError as e:
            print(f"⚠️ Plugin system not available: {e}")
            print("   Falling back to legacy system...")
            from kubeSol.main import main as legacy_main
            legacy_main()
        except Exception as e:
            print(f"❌ Error in plugin system: {e}")
            print("   Falling back to legacy system...")
            from kubeSol.main import main as legacy_main
            legacy_main()
    else:
        from kubeSol.main import main as legacy_main
        legacy_main()

if __name__ == "__main__":
    main()