import os
import logging
import json
import time

class FileMonitor:
    """
    Monitors a folder for new media files and adds them as tasks to the database.
    """
    def __init__(self, config_path, db, debug=False):
        self.config_path = config_path
        self.debug = debug
        self.db = db
        self.config = self._load_config()
        self.input_parent_folder = self.config.get('input_parent_folder')
        self.processors_config = self.config.get('processors', [])
        if self.debug:
            print(f"DEBUG: FileMonitor initialized. Monitoring '{self.input_parent_folder}'.")

    def _load_config(self):
        """Loads configuration from the specified file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading configuration: {e}")
            return {}

    def _find_processor_config(self, relative_path):
        """
        Finds the correct processor configuration based on the file's path.
        """
        for proc in self.processors_config:
            if relative_path.startswith(proc['input_path']):
                # Extract processing parameters from the folder structure.
                # Example: "video_HEVC_height/360/input.mp4" -> ["360"]
                # The processor is responsible for interpreting this list.
                
                parts = relative_path.split(os.sep)
                
                # Check if the folder-name matches with any of the parameter-list in the config
                if 'processing_params' in proc:
                    for part in parts:
                        if part in proc['processing_params']:
                            processing_params = {
                                "height": int(part),
                                "input_path_prefix": os.path.normpath(proc['input_path'])
                            }
                            return proc['name'], json.dumps(processing_params)

                # Return the processor name and an empty parameter list if no params are configured
                return proc['name'], json.dumps({"input_path_prefix": os.path.normpath(proc['input_path'])})

        return None, None
        
    def check_for_new_files(self):
        """
        Scans the input folder for new files and adds them to the database.
        """
        if self.debug:
            print("DEBUG: Starting file scan...")

        for root, _, files in os.walk(self.input_parent_folder):
            if self.debug:
                print(f"DEBUG: Scanning folder: {root}")
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Get the relative path from the input parent folder
                relative_path = os.path.relpath(file_path, self.input_parent_folder)
                
                processor_name, processing_params = self._find_processor_config(relative_path)
                
                if processor_name and not self.db.is_task_pending_or_processed(file_path):
                    self.db.add_task(file_path, processor_name, processing_params)
                    if self.debug:
                        print(f"DEBUG: Task added for '{file_path}' with processor '{processor_name}'.")

