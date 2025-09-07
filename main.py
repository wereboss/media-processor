import time
import os
import argparse
import json
import logging
import sys

# Add the src directory to the system path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from file_monitor import FileMonitor
from media_controller import MediaController
from database import Database

def setup_logging(debug_mode):
    """Sets up basic logging configuration."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """Main function to run the application."""
    parser = argparse.ArgumentParser(description="Monitor a folder and process media files.")
    parser.add_argument('config_path', type=str, help='Path to the configuration file (e.g., config/config.json)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    # Setup logging first
    setup_logging(args.debug)
    logger = logging.getLogger("main")
    logger.debug("Debug mode is enabled.")

    # Load configuration
    try:
        with open(args.config_path, 'r') as f:
            config = json.load(f)
        logger.debug("Configuration loaded successfully.")
    except FileNotFoundError:
        logger.error(f"Error: Configuration file not found at {args.config_path}")
        return
    except json.JSONDecodeError:
        logger.error(f"Error: Invalid JSON in configuration file at {args.config_path}")
        return

    # Initialize Database
    try:
        db = Database(config, debug=args.debug)
        if not db.initialize_database():
            logger.error("Unrecoverable error during initialization: Could not initialize database.")
            return
    except Exception as e:
        logger.error(f"Unrecoverable error during initialization: {e}")
        return
    
    # Initialize components
    try:
        # Pass the config dictionary directly to the FileMonitor
        file_monitor = FileMonitor(config=config, db=db, debug=args.debug)
        media_controller = MediaController(config=config, db=db, debug=args.debug)
    except Exception as e:
        logger.error(f"Unrecoverable error during initialization: {e}")
        return

    logger.info("Application started. Monitoring for new files and processing tasks...")
    
    # Main loop
    try:
        while True:
            file_monitor.check_for_new_files()
            media_controller.process_pending_tasks()
            file_monitor.purge_completed_inputs()
            time.sleep(config.get('monitoring_interval', 5))
    except KeyboardInterrupt:
        logger.info("Application stopped by user.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
