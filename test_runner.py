import time
import os
import argparse
import json
import logging
import sys

# Add the src directory to the system path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import all core components for testing
from database import Database
from file_monitor import FileMonitor
from media_controller import MediaController
from processor_loader import load_processors

def setup_logging(debug_mode):
    """Sets up basic logging configuration."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Set logger for this script
    logger = logging.getLogger("TestRunner")
    if debug_mode:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    return logger

def print_database_contents(db, logger):
    """Prints all records from the tasks table for debugging."""
    logger.info("--- Printing all tasks from the database ---")
    tasks = db.get_all_tasks()
    if not tasks:
        logger.info("No tasks found in the database.")
        return

    logger.info("ID | Input Path | Processor | Status | Progress | Output Files | Created At")
    logger.info("-" * 100)
    for task in tasks:
        task_id, file_path, processor, status, progress, output_files, created_at = task
        logger.info(f"{task_id} | {file_path} | {processor} | {status} | {progress}% | {output_files} | {created_at}")
    logger.info("-" * 100)

def test_file_monitor(config, logger):
    """Tests the FileMonitor component independently."""
    logger.info("--- Starting FileMonitor Test ---")
    
    # Initialize Database
    try:
        db = Database(config=config, debug=True)
        db.initialize_database()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return

    logger.info("--- Database Contents BEFORE Test ---")
    print_database_contents(db, logger)

    # Initialize FileMonitor
    try:
        file_monitor = FileMonitor(config=config, db=db, debug=True)
        file_monitor.check_for_new_files()
        logger.info("FileMonitor test completed. Check logs for new tasks.")
    except Exception as e:
        logger.error(f"Error running FileMonitor test: {e}")

    logger.info("--- Database Contents AFTER Test ---")
    print_database_contents(db, logger)
        
    db.close()
    logger.info("--- FileMonitor Test Finished ---")

def test_processor_loading(config, logger):
    """Tests the processor loading functionality."""
    logger.info("--- Starting Processor Loading Test ---")
    try:
        # We don't need a DB connection here, just the config
        processors = load_processors(config, db=None, debug=True)
        
        if 'HEVC Scaler' in processors:
            logger.info("Processor 'HEVC Scaler' loaded successfully.")
            logger.info(f"Loaded processors: {list(processors.keys())}")
        else:
            logger.error("Processor 'HEVC Scaler' was not found after loading.")
            logger.debug(f"Processors dictionary: {processors}")

    except Exception as e:
        logger.error(f"Error during processor loading test: {e}")
    finally:
        logger.info("--- Processor Loading Test Finished ---")

def test_hevc_scaler(config, logger):
    """Tests the HEVC Scaler processor with hardcoded inputs."""
    logger.info("--- Starting HEVC Scaler Test ---")

    # Initialize a temporary database
    try:
        db = Database(config=config, debug=True)
        db.initialize_database()
    except Exception as e:
        logger.error(f"Error initializing database for HEVC Scaler test: {e}")
        return

    # Initialize HEVC Scaler processor
    try:
        # Get the processor class
        processor_class = load_processors(config, db, True)
        # Instantiate the class with required arguments
        hevc_scaler = processor_class.get("HEVC Scaler")
        
        # Hardcoded inputs to simulate a task from the MediaController
        input_file = os.path.join(os.path.dirname(__file__), 'tests', 'sample_video.mp4')
        task_id = 1
        params = ["360"]

        # Create a mock video file for testing
        mock_video_path = os.path.join(os.path.dirname(__file__), 'tests', 'sample_video.mp4')
        os.makedirs(os.path.dirname(mock_video_path), exist_ok=True)
        # Create a tiny mock video using ffmpeg
        os.system(f"ffmpeg -f lavfi -i testsrc=size=1280x720:rate=1 -t 5 -c:v libx264 -pix_fmt yuv420p {mock_video_path}")

        logger.info(f"Testing HEVC Scaler with file: {input_file}")
        
        # Call the process method directly
        output_files = hevc_scaler.process(input_file, task_id, params)

        # Check if output files were returned
        if output_files:
            logger.info("HEVC Scaler test completed successfully.")
            logger.info(f"Generated output files: {output_files}")
        else:
            logger.error("HEVC Scaler test failed: No output files were returned.")
        
    except Exception as e:
        logger.error(f"Error running HEVC Scaler test: {e}")
    
    db.close()
    logger.info("--- HEVC Scaler Test Finished ---")


def test_media_controller(config, logger):
    """Tests the MediaController component independently."""
    logger.info("--- Starting MediaController Test ---")
    
    # Initialize Database
    try:
        db = Database(config=config, debug=True)
        db.initialize_database()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return
        
    logger.info("--- Database Contents BEFORE Test ---")
    print_database_contents(db, logger)

    # Initialize MediaController
    try:
        media_controller = MediaController(config=config, db=db, debug=True)
        media_controller.process_pending_tasks()
        logger.info("MediaController test completed. Check logs for updated tasks.")
    except Exception as e:
        logger.error(f"Error running MediaController test: {e}")

    logger.info("--- Database Contents AFTER Test ---")
    print_database_contents(db, logger)
        
    db.close()
    logger.info("--- MediaController Test Finished ---")

def main():
    """Main function to run the test suite."""
    parser = argparse.ArgumentParser(description="Run tests for media processor components.")
    parser.add_argument('test_component', type=str, choices=['file_monitor', 'media_controller', 'processor_loading', 'hevc_scaler'],
                        help='The component to test.')
    parser.add_argument('--config_path', type=str, default='config/config.json',
                        help='Path to the configuration file.')
    args = parser.parse_args()

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

    logger = setup_logging(debug_mode=True)

    if args.test_component == 'file_monitor':
        test_file_monitor(config, logger)
    elif args.test_component == 'media_controller':
        test_media_controller(config, logger)
    elif args.test_component == 'processor_loading':
        test_processor_loading(config, logger)
    elif args.test_component == 'hevc_scaler':
        test_hevc_scaler(config, logger)
    
if __name__ == "__main__":
    main()
