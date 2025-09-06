import os
import json
import logging
from importlib import import_module

def load_processors(config, db, debug=False):
    """
    Dynamically loads processor classes based on the configuration file.

    Args:
        config (dict): The application configuration dictionary.
        db (Database): The shared database instance.
        debug (bool): Flag to enable debug logging.

    Returns:
        dict: A dictionary of loaded processor instances.
    """
    loaded_processors = {}
    logger = logging.getLogger('ProcessorLoader')
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    for proc in config.get('processors', []):
        try:
            module_name = proc['processor']
            # Corrected logic to derive class name from module name
            class_name_parts = [x.capitalize() for x in module_name.split('_')]
            class_name = "".join(class_name_parts)
            
            # The full module path is relative to the directory on the system path (which is the project root)
            module = import_module(f"src.processors.{module_name}")
            ProcessorClass = getattr(module, class_name)
            
            loaded_processors[proc['name']] = ProcessorClass(config=config, db=db, debug=debug)
            logger.debug(f"Processor '{proc['name']}' loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading processor '{proc['name']}': {e}")
            
    return loaded_processors

