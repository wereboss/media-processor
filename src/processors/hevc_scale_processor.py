import subprocess
import os
import re
import json
import logging
from . import Processor

class HevcScaleProcessor(Processor):
    def __init__(self, config, db, debug=False):
        super().__init__(config, db, debug)
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.debug("HevcScaleProcessor initialized.")

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

        # Retrieve parameters from the dictionary
        height = params[0]
        output_path_suffix = self.processor_config.get('output_path')
        output_extension = self.processor_config.get('output_file_extension')
        
        # Ensure mandatory parameters are provided
        if not height:
            raise ValueError("Height parameter is missing from processing params.")
        if not output_path_suffix:
            raise ValueError("Output path prefix is missing from processing params.")
        if not output_extension:
            raise ValueError("Output file extension is missing from processing params.")
        
        # Construct the output path and command
        output_path = self._get_output_path(input_path, output_path_suffix, output_extension)
        self.logger.debug(f"Final output path for FFmpeg: {output_path}")

        command = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale=-2:{height}',
            '-c:v', 'libx265',
            '-crf', '28',
            '-preset', 'fast',
            '-c:a', 'copy',
            output_path
        ]
        
        # Run FFmpeg and report progress
        duration = self._get_video_duration(input_path)
        
        self.logger.debug(f"FFmpeg command: {' '.join(command)}")

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in iter(process.stderr.readline, ''):
                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                if time_match and duration:
                    h, m, s, cs = map(int, time_match.groups())
                    current_time = h * 3600 + m * 60 + s + cs / 100
                    progress = (current_time / duration) * 100
                    self.logger.debug(f"Calculated progress: {progress:.2f}%")
                    self.db.update_task_progress(task_id, progress)

            process.wait()
            
            if process.returncode != 0:
                stdout, stderr = process.communicate()
                self.logger.error(f"FFmpeg process for '{input_path}' failed with return code {process.returncode}.")
                self.logger.error(f"STDOUT: {stdout}")
                self.logger.error(f"STDERR: {stderr}")
                return None
            
            self.logger.info(f"FFmpeg process for '{input_path}' completed successfully.")
            return [output_path]
            
        except FileNotFoundError:
            self.logger.error(f"FFmpeg or FFprobe not found. Please ensure they are installed and in your system's PATH.")
            return None
        except Exception as e:
            self.logger.error(f"FFmpeg processing failed: {e}")
            return None

