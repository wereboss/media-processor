import sys
import os
import time
import argparse
import json

# Add the 'src' directory to the system path to allow for package imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from file_monitor import FileMonitor
from media_controller import MediaController
from database import Database

def main():
    """Main function to run the application."""
    parser = argparse.ArgumentParser(description="Monitor a folder and process media files.")
    parser.add_argument('config_path', type=str, help='Path to the configuration file (e.g., config/config.json)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        print("DEBUG: Debug mode is enabled.")

    # Load configuration
    try:
        with open(args.config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {args.config_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file at {args.config_path}")
        return

    # Initialize Database
    try:
        db = Database(args.config_path, debug=args.debug)
        if not db.initialize_database():
            print("Unrecoverable error during initialization: Could not initialize database.")
            return
    except Exception as e:
        print(f"Unrecoverable error during initialization: {e}")
        return
    
    # Initialize components
    try:
        # FileMonitor and MediaController share the same database instance
        file_monitor = FileMonitor(args.config_path, db=db, debug=args.debug)
        media_controller = MediaController(config_path=args.config_path, db=db, debug=args.debug)
    except Exception as e:
        print(f"Unrecoverable error during initialization: {e}")
        return

    print("Application started. Monitoring for new files and processing tasks...")
    
    # Main loop
    try:
        while True:
            file_monitor.check_for_new_files()
            media_controller.process_pending_tasks()
            time.sleep(config.get('monitoring_interval', 5))
    except KeyboardInterrupt:
        print("Application stopped by user.")
    finally:
        db.close()

if __name__ == "__main__":
    main()

