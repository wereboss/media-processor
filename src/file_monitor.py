import os
import json
import logging

class FileMonitor:
    """
    Monitors a specified folder for new media files and adds them to the database for processing.
    """
    def __init__(self, config_path, db, debug=False):
        self.config = self._load_config(config_path)
        self.db = db
        self.debug = debug
        self.input_parent_folder = self.config.get('input_parent_folder')
        self.processors = self.config.get('processors', [])
        
        if self.debug:
            print(f"DEBUG: FileMonitor initialized. Monitoring '{self.input_parent_folder}'.")

    def _load_config(self, config_path):
        """Loads configuration from the specified file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading configuration: {e}")
            return {}

    def _determine_processing_params(self, folder_path):
        """
        Determines processor and parameters based on the folder path.
        Returns a tuple of (processor_name, processing_params) or (None, None).
        """
        relative_path = os.path.relpath(folder_path, self.input_parent_folder)
        path_parts = relative_path.split(os.sep)

        for proc_info in self.processors:
            input_path_prefix = proc_info.get('input_path')
            
            if relative_path.startswith(input_path_prefix):
                processing_params = {}
                
                # Check for height in the path
                try:
                    # Find the part of the path that contains the height
                    height_part = path_parts[path_parts.index(input_path_prefix.split(os.sep)[-1]) + 1]
                    if height_part.isdigit():
                        processing_params['height'] = int(height_part)
                except (ValueError, IndexError):
                    pass
                
                # We need to pass the output_path as well
                processing_params['output_path'] = proc_info.get('output_path')
                
                # We need to pass the output_file_extension as well
                processing_params['output_file_extension'] = proc_info.get('output_file_extension')
                
                processing_params['input_path_prefix'] = input_path_prefix
                return proc_info['name'], processing_params
        
        return None, None
    
    def check_for_new_files(self):
        """Scans the input folders for new files and adds them to the database."""
        if self.debug:
            print("DEBUG: Starting file scan...")

        for root, _, files in os.walk(self.input_parent_folder):
            if self.debug:
                print(f"DEBUG: Scanning folder: {root}")

            processor_name, processing_params = self._determine_processing_params(root)

            if processor_name:
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    # Check the database for any previous record of this file, regardless of status
                    if not self.db.is_task_recorded(file_path):
                        # Convert params to JSON string for database storage
                        params_json = json.dumps(processing_params)
                        task_id = self.db.add_task(file_path, processor_name, params_json)
                        if self.debug:
                            print(f"DEBUG: Task added for '{file_path}' with processor '{processor_name}'.")

