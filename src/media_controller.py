import os
import importlib.util
import json
import logging
import sys

from database import Database

class MediaController:
    """
    Manages the overall media processing workflow, including loading processors
    and orchestrating tasks.
    """
    def __init__(self, config_path, db, debug=False):
        self.config_path = config_path
        self.db = db
        self.debug = debug
        self.config = self._load_config()
        self.processors = self._load_processors()
        if self.debug:
            print(f"DEBUG: MediaController initialized successfully.")
    
    def _load_config(self):
        """Loads configuration from the specified file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading configuration: {e}")
            return {}

    def _load_processors(self):
        """
        Dynamically loads processor classes from the 'src/processors' directory.
        """
        processors = {}
        processors_config = self.config.get('processors', [])
        
        if self.debug:
            print("DEBUG: Loading processors...")

        base_path = os.path.join(os.path.dirname(__file__), 'processors')
        sys_path_added = False
        if base_path not in sys.path:
            sys.path.insert(0, base_path)
            sys_path_added = True

        for proc_info in processors_config:
            module_name = proc_info['processor']
            try:
                # The module name is expected to be 'hevc_scale_processor', etc.
                module = importlib.import_module(module_name)
                
                # Derive class name from module name (e.g., 'hevc_scale_processor' -> 'HevcScaleProcessor')
                class_name = ''.join(word.capitalize() for word in module_name.split('_'))
                
                ProcessorClass = getattr(module, class_name)
                processors[proc_info['name']] = ProcessorClass(self.config, debug=self.debug)
                if self.debug:
                    print(f"DEBUG: Processor '{proc_info['name']}' loaded successfully.")
            except (ImportError, AttributeError, KeyError) as e:
                print(f"Error loading processor '{proc_info.get('name')}': {e}")
        
        if sys_path_added:
            sys.path.remove(base_path)

        return processors

    def process_pending_tasks(self):
        """
        Processes tasks that are in the 'pending' status.
        """
        if self.debug:
            print("DEBUG: Checking for pending tasks to process...")
        
        pending_tasks = self.db.get_pending_tasks()
        if self.debug:
            print(f"DEBUG: Found {len(pending_tasks)} pending tasks.")

        for task in pending_tasks:
            try:
                task_id, file_path, processor_name, processing_params, _ = task
                if self.debug:
                    print(f"DEBUG: Starting processing for task {task_id} on file '{file_path}'...")
                    print(f"DEBUG: Raw processing_params from DB: {processing_params}")

                if processor_name in self.processors:
                    processor = self.processors[processor_name]
                    
                    # Convert the processing_params JSON string back to a dictionary
                    params = json.loads(processing_params)
                    
                    if self.debug:
                        print(f"DEBUG: Deserialized params for processor: {params}")

                    processor.process(
                        input_path=file_path, 
                        task_id=task_id, 
                        db=self.db, 
                        **params
                    )
                else:
                    print(f"Error: Processor '{processor_name}' not found. Skipping task {task_id}.")
            except Exception as e:
                if 'task_id' in locals():
                    self.db.update_task_status(task_id, 'failed')
                print(f"An unrecoverable error occurred in the processing loop: {e}")
                logging.exception("An unrecoverable error occurred during processing.")

