import os
import json
import logging
from processor_loader import load_processors

class MediaController:
    """
    Manages the processing of media tasks by loading and invoking
    the correct processor for each pending task.
    """
    def __init__(self, config, db, debug=False):
        self.config = config
        self.db = db
        self.debug = debug
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
            
        self.processors = self._load_processors()
        self.logger.info("MediaController initialized successfully.")

    def _load_processors(self):
        """
        Dynamically loads processor classes based on the configuration,
        using the dedicated processor loader.
        """
        self.logger.debug("Loading processors...")
        return load_processors(self.config, self.db, self.debug)

    def process_pending_tasks(self):
        """
        Retrieves and processes all pending tasks from the database.
        """
        self.logger.info("Checking for pending tasks to process...")
        pending_tasks = self.db.get_pending_tasks()
        
        if not pending_tasks:
            self.logger.info("No pending tasks found.")
            return

        self.logger.info(f"Found {len(pending_tasks)} pending tasks.")
        for task in pending_tasks:
            task_id, file_path, processor_name, processing_params_str, status, output_files = task
            self.logger.info(f"Starting processing for task {task_id} on file '{file_path}'...")
            
            try:
                # Deserialize params from the database
                params = json.loads(processing_params_str)
                self.logger.debug(f"Deserialized params for processor: {params}")

                processor = self.processors.get(processor_name)
                if processor:
                    output_files = processor.process(file_path, task_id, params)

                    if output_files:
                        self.db.update_task_status(task_id, 'completed', output_files)
                        self.logger.info(f"Task {task_id} completed successfully.")
                    else:
                        self.db.update_task_status(task_id, 'failed')
                        self.logger.error(f"Processor '{processor_name}' failed to process the file.")
                else:
                    self.db.update_task_status(task_id, 'failed')
                    self.logger.error(f"Processor '{processor_name}' not found. Skipping task {task_id}.")

            except Exception as e:
                self.db.update_task_status(task_id, 'failed')
                self.logger.error(f"Unrecoverable error during processing of task {task_id}: {e}")

