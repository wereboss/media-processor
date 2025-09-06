import os
import json
from abc import ABC, abstractmethod

class Processor(ABC):
    """
    Base class for all media processors.
    """
    def __init__(self, config, db, debug=False):
        self.config = config
        self.db = db
        self.debug = debug
        self.processor_config = self._load_processor_config()

    def _load_processor_config(self):
        """
        Loads the specific configuration for the processor from the main config file.
        Returns a dictionary with the processor's configuration.
        """
        processor_name = self.__class__.__name__
        for proc in self.config.get('processors', []):
            if proc['processor'] == self.__module__.split('.')[-1]:
                return proc
        raise ValueError(f"Processor configuration for '{processor_name}' not found.")

    def _get_output_path(self, input_path, output_path_suffix, output_extension):
        """
        Constructs the output file path based on the input path and configured outputs.
        """
        # Get the output parent folder from the main config
        output_parent_folder = self.config.get('output_parent_folder')
        if not output_parent_folder:
            raise ValueError("Output parent folder is not configured.")

        # Get the filename from the input path
        filename = os.path.splitext(os.path.basename(input_path))[0]

        # Construct the output folder path
        output_folder = os.path.join(output_parent_folder, output_path_suffix)
        os.makedirs(output_folder, exist_ok=True)

        # Construct the final output path
        output_filename = f"{filename}.{output_extension}"
        return os.path.join(output_folder, output_filename)

    @abstractmethod
    def process(self, input_path, task_id, params):
        """
        Processes a single media file.
        
        Args:
            input_path (str): The path to the input media file.
            task_id (int): The ID of the task in the database.
            params (list): A list of strings containing instructions from the folder path.
        """
        pass

