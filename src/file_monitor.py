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
        # NEW: Dictionary to store file status for staleness checks
        self.file_status = {}
        # NEW: Get staleness check count from config
        self.staleness_check_count = self.config.get('staleness_check_count', 3)
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
        Scans the input folder for new media files and adds them to the database
        only after they are considered stable.
        """
        self.logger.debug("Starting file scan...")
        
        # Check if the input parent folder exists
        if not os.path.exists(self.input_parent_folder):
            self.logger.error(f"Input parent folder not found: {self.input_parent_folder}. Skipping scan.")
            return

        # NEW: Create a set of files found in the current scan
        current_files = set()

        for root, dirs, files in os.walk(self.input_parent_folder):
            self.logger.debug(f"Scanning folder: {root}")
            for filename in files:
                file_path = os.path.join(root, filename)
                current_files.add(file_path)

                # Skip if file has already been recorded in the database
                if self.db.is_task_recorded(file_path):
                    self.logger.debug(f"Skipping '{file_path}': already recorded.")
                    continue
                
                # Check if file is a media file based on extension
                if not any(file_path.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.mov', '.mp3', '.flac']):
                    continue
                
                # NEW: Get current file size
                try:
                    current_size = os.path.getsize(file_path)
                except FileNotFoundError:
                    self.logger.debug(f"File '{file_path}' disappeared before size could be checked. Skipping.")
                    continue
                
                # Check file staleness
                if file_path in self.file_status:
                    # File is already being monitored
                    previous_size, counter = self.file_status[file_path]
                    if current_size == previous_size:
                        # Size is stable, increment counter
                        self.file_status[file_path] = (current_size, counter + 1)
                        self.logger.debug(f"File '{file_path}' is stable. Count: {counter + 1}/{self.staleness_check_count}")
                    else:
                        # Size changed, reset counter
                        self.file_status[file_path] = (current_size, 1)
                        self.logger.debug(f"File '{file_path}' size changed. Resetting count.")
                else:
                    # New file, start monitoring
                    self.file_status[file_path] = (current_size, 1)
                    self.logger.debug(f"New file '{file_path}' detected. Starting staleness check.")

                # Check if the file is now considered stable
                if self.file_status.get(file_path, (0, 0))[1] >= self.staleness_check_count:
                    processor_config, input_path_suffix = self._get_processor_config(file_path)
                    if processor_config:
                        processor_name = processor_config['name']
                        params = self._get_processor_params(input_path_suffix)
                        self.logger.debug(f"Adding task for '{file_path}' with processor '{processor_name}'.")
                        if self.db.add_task(file_path, processor_name, params):
                            self.logger.info(f"Task added for '{file_path}' with processor '{processor_name}'.")
                            # Remove file from monitoring once added to DB
                            del self.file_status[file_path]
                    else:
                        self.logger.warning(f"No processor found for path: {file_path}. Skipping and removing from check.")
                        # Stop monitoring this file
                        del self.file_status[file_path]

        # NEW: Remove files from monitoring that are no longer present
        files_to_remove = [p for p in self.file_status if p not in current_files]
        for p in files_to_remove:
            self.logger.debug(f"File '{p}' removed from monitoring as it no longer exists.")
            del self.file_status[p]
