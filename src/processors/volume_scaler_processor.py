import os
import re
import json
import subprocess
import logging
import time
from . import Processor

class VolumeScalerProcessor(Processor):
    """
    Processor for increasing the audio volume of a media file.
    """
    def __init__(self, config, db, debug=False):
        super().__init__(config, db, debug)
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.debug("VolumeScalerProcessor initialized.")

    def _get_video_duration(self, input_path):
        """Gets video duration using ffprobe."""
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                   'default=noprint_wrappers=1:nokey=1', input_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            self.logger.error(f"Failed to get video duration for {input_path}: {e}")
            return None

    def process(self, input_path, task_id, params):
        self.logger.debug(f"Received input_path: {input_path}")
        self.logger.debug(f"Received params: {params}")
        
        # Retrieve parameters
        if not params or not params[0]:
            self.db.update_task_status(task_id, 'failed', error_message="Volume scale factor is missing from parameters.")
            return None
        
        try:
            volume_scale = float(params[0])
            if volume_scale <= 0:
                raise ValueError("Volume scale must be greater than 0.")
        except (ValueError, IndexError) as e:
            self.db.update_task_status(task_id, 'failed', error_message=f"Invalid volume scale parameter: {e}")
            return None

        # Get processor-specific configuration
        proc_config = self.processor_config
        output_path_suffix = proc_config.get('output_path')
        output_extension = proc_config.get('output_file_extension')
        
        if not output_path_suffix:
            self.db.update_task_status(task_id, 'failed', error_message="Output path prefix is missing from processor config.")
            return None
        if not output_extension:
            self.db.update_task_status(task_id, 'failed', error_message="Output file extension is missing from processor config.")
            return None

        self.logger.debug(f"Starting volume scaling process for '{input_path}' with a scale of {volume_scale}x.")
        
        # Construct the output path
        output_path = self._get_output_path(input_path, output_path_suffix, output_extension)
        self.logger.debug(f"Final output path for FFmpeg: {output_path}")

        # Delete the output file if it exists to prevent FFmpeg from hanging
        if os.path.exists(output_path):
            self.logger.debug(f"Output file '{output_path}' already exists. Deleting it.")
            os.remove(output_path)
        output_path_db = [output_path]
        
        # Update the database with the processing status and output file path
        self.db.update_task_status(task_id, 'processing')
        self.db.update_task_output_files(task_id, json.dumps(output_path_db))

        # Build FFmpeg command
        command = [
            'ffmpeg',
            '-i', input_path,
            '-af', f"volume={volume_scale}",
            '-c:v', 'copy',
            '-c:a', 'aac',
            output_path
        ]
        
        # Run FFmpeg and report progress
        duration = self._get_video_duration(input_path)
        
        self.logger.debug(f"FFmpeg command: {' '.join(command)}")
        output_lines = []
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in iter(process.stderr.readline, ''):
                output_lines.append(line)
                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                if time_match and duration:
                    h, m, s, cs = map(int, time_match.groups())
                    current_time = h * 3600 + m * 60 + s + cs / 100
                    progress = (current_time / duration) * 100
                    if progress > 100: progress = 99.99
                    self.logger.debug(f"Calculated progress: {progress:.2f}%")
                    self.db.update_task_progress(task_id, progress)

            process.wait()

            if process.returncode != 0:
                stdout, stderr = process.communicate()
                self.logger.error(f"FFmpeg process for '{input_path}' failed with return code {process.returncode}.")
                self.logger.error(f"STDOUT: {stdout}")
                self.logger.error(f"STDERR: {stderr}")
                self.db.update_task_status(task_id, 'failed', error_message=''.join(output_lines))
                return None
            
            self.db.update_task_status(task_id, 'completed')
            self.logger.info(f"FFmpeg process for '{input_path}' completed successfully.")
            return [output_path]
            
        except FileNotFoundError:
            self.logger.error(f"FFmpeg or FFprobe not found. Please ensure they are installed and in your system's PATH.")
            self.db.update_task_status(task_id, 'failed', error_message="FFmpeg or FFprobe not found in PATH.")
            return None
        except Exception as e:
            self.logger.error(f"FFmpeg processing failed: {e}")
            self.db.update_task_status(task_id, 'failed', error_message=str(e))
            return None
