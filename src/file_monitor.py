import os
import json
import logging
import time
import sqlite3

class FileMonitor:
    def __init__(self, config, db, debug=False):
        self.config = config
        self.db = db
        self.debug = debug
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        self.input_parent_folder = self.config.get('input_parent_folder')
        self.processors = self.config.get('processors')
        self.logger.debug(f"FileMonitor initialized. Monitoring '{self.input_parent_folder}'.")

    def _get_processor_config(self, input_path):
        """
        Determines the correct processor configuration based on the file's sub-folder.
        Returns the processor dictionary from config and the sub-path suffix.
        """
        sub_path = os.path.dirname(input_path).replace(self.input_parent_folder, '').strip(os.path.sep)
        
        for proc in self.processors:
            if sub_path.startswith(proc['input_path']):
                return proc, sub_path.replace(proc['input_path'], '').strip(os.path.sep)
        return None, None
        
    def _get_processor_params(self, input_path_suffix):
        """
        Extracts processing parameters from the input path suffix.
        Returns a list of strings from the sub-folder names.
        """
        return input_path_suffix.split(os.path.sep)

    def check_for_new_files(self):
        """
        Scans the input folder for new media files and adds them to the database.
        """
        self.logger.debug("Starting file scan...")
        
        # Check if the input parent folder exists
        if not os.path.exists(self.input_parent_folder):
            self.logger.error(f"Input parent folder not found: {self.input_parent_folder}. Skipping scan.")
            return

        for root, dirs, files in os.walk(self.input_parent_folder):
            self.logger.debug(f"Scanning folder: {root}")
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # Check if file has already been recorded in the database
                if self.db.is_task_recorded(file_path):
                    self.logger.debug(f"Skipping '{file_path}': already recorded.")
                    continue
                
                # Check if file is a media file based on extension
                if not any(file_path.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.mov', '.mp3', '.flac']):
                    continue
                
                # Find the correct processor and params
                processor_config, input_path_suffix = self._get_processor_config(file_path)
                
                if processor_config:
                    processor_name = processor_config['name']
                    # Get processor-specific params from the sub-path
                    params = self._get_processor_params(input_path_suffix)
                    self.logger.debug(f"get_processor_params returned params:{params}")
                    # Add task to the database
                    if self.db.add_task(file_path, processor_name, params):
                        self.logger.info(f"Task added for '{file_path}' with processor '{processor_name}'.")

