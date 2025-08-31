import os
import json
import logging
import importlib.util

class MediaController:
    """
    Manages and orchestrates media processing tasks.
    """
    def __init__(self, config_path, db, debug=False):
        self.config_path = config_path
        self.debug = debug
        self.db = db
        self.config = self._load_config()
        self.processors = self._load_processors()
        if self.debug:
            print("DEBUG: MediaController initialized successfully.")
    
    def _load_config(self):
        """Loads configuration from the specified file."""
        if self.debug:
            print(f"DEBUG: Loading configuration from '{self.config_path}'")
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
        if self.debug:
            print("DEBUG: Loading processors...")
        processors = {}
        processor_config = self.config.get('processors', [])
        
        for proc in processor_config:
            processor_name = proc.get('name')
            module_name = proc.get('processor')
            
            try:
                # Dynamically load the module based on its file path
                processor_file = os.path.join(os.path.dirname(__file__), 'processors', f"{module_name}.py")
                spec = importlib.util.spec_from_file_location(module_name, processor_file)
                processor_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(processor_module)

                # Get the class name from the module name (e.g., 'hevc_scale_processor' -> 'HevcScaleProcessor')
                class_name = ''.join(word.capitalize() for word in module_name.split('_'))
                ProcessorClass = getattr(processor_module, class_name)
                
                # Instantiate the processor and store it
                processors[processor_name] = ProcessorClass(self.config, debug=self.debug)
                if self.debug:
                    print(f"DEBUG: Processor '{processor_name}' loaded successfully.")
            
            except Exception as e:
                print(f"Error loading processor '{processor_name}': {e}")
        
        return processors

    def process_pending_tasks(self):
        """
        Retrieves and processes all pending tasks from the database.
        """
        if self.debug:
            print("DEBUG: Checking for pending tasks to process...")
        
        pending_tasks = self.db.get_pending_tasks()
        if self.debug:
            print(f"DEBUG: Found {len(pending_tasks)} pending tasks.")
            
        for task in pending_tasks:
            task_id, file_path, processor_name, processing_params, status = task
            if self.debug:
                print(f"DEBUG: Starting processing for task {task_id} on file '{file_path}'...")
            
            if processor_name in self.processors:
                processor = self.processors[processor_name]
                try:
                    processor.process(file_path, task_id, db=self.db, **json.loads(processing_params))
                    if self.debug:
                        print(f"DEBUG: Task {task_id} completed successfully.")
                except Exception as e:
                    print(f"An unrecoverable error occurred during processing of task {task_id}: {e}")
            else:
                print(f"Error: Processor '{processor_name}' not found. Skipping task {task_id}.")

