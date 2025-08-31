import os
import json
from abc import ABC, abstractmethod

class Processor(ABC):
    """
    Abstract base class for all media processors.
    Defines a common interface for processing tasks.
    """
    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug

    def _get_output_path(self, input_path):
        """
        Generates the output file path based on the input path and configured output directory.
        """
        base_name = os.path.basename(input_path)
        processor_config = self.config.get('processor_config', {})
        output_parent_folder = self.config.get('output_parent_folder')

        output_file_extension = processor_config.get('output_file_extension')
        if not output_file_extension:
            # Fallback to the original extension if not specified
            output_file_extension = os.path.splitext(base_name)[1]
            if self.debug:
                print(f"DEBUG: Using original file extension '{output_file_extension}' as no specific output extension was configured.")

        # Construct the output path
        output_name = os.path.splitext(base_name)[0] + output_file_extension
        output_path = os.path.join(output_parent_folder, output_name)

        if self.debug:
            print(f"DEBUG: Generated output path: {output_path}")

        return output_path

    @abstractmethod
    def process(self, input_path, **kwargs):
        """
        Abstract method to be implemented by all concrete processor classes.
        This method should handle the media processing.
        """
        pass

