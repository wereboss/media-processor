import os
import subprocess
import logging
import re
from datetime import datetime

from processors import Processor

class HevcScaleProcessor(Processor):
    """
    Processor to scale HEVC video files to a specified height.
    """
    def __init__(self, config, debug=False):
        super().__init__(config, debug)

    def _get_output_path(self, input_path, output_path, output_file_extension):
        """
        Constructs the output file path based on the configuration.
        """
        # Ensure the output directory exists
        output_parent_folder = self.config.get('output_parent_folder')
        
        output_dir = os.path.join(output_parent_folder, output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        file_name = os.path.basename(input_path)
        base_name, _ = os.path.splitext(file_name)

        output_file_name = f"{base_name}.{output_file_extension}"
        
        return os.path.join(output_dir, output_file_name)

    def _get_video_duration(self, input_path):
        """
        Gets the duration of the video in seconds using ffprobe.
        """
        try:
            command = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return float(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error getting video duration: {e}")
            return None

    def process(self, input_path, task_id, db, **kwargs):
        """
        Processes a media file by scaling its height.
        """
        if self.debug:
            print(f"DEBUG: Starting HEVC scaling process for '{input_path}' to height {kwargs.get('height')}.")

        height = kwargs.get('height')
        output_path = kwargs.get('output_path')
        output_file_extension = kwargs.get('output_file_extension')
        
        # Check if the height is valid
        if not height or not isinstance(height, int):
            print(f"Error: Invalid height parameter '{height}'. Skipping task.")
            db.update_task_status(task_id, 'failed')
            return

        # Build the output path
        output_file_path = self._get_output_path(input_path, output_path, output_file_extension)

        if self.debug:
            print(f"DEBUG: Final height value for FFmpeg: {height}")
            print(f"DEBUG: Final output path for FFmpeg: {output_file_path}")

        # FFmpeg command to scale height while maintaining aspect ratio and using HEVC codec
        command = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale=-2:{height}',
            '-c:v', 'libx265',
            '-crf', '28',
            '-preset', 'fast',
            '-c:a', 'copy',
            output_file_path
        ]

        if self.debug:
            print(f"DEBUG: FFmpeg command: {' '.join(command)}")

        total_duration = self._get_video_duration(input_path)
        if not total_duration:
            print(f"Error: Could not determine video duration. Skipping progress tracking.")
            db.update_task_status(task_id, 'failed')
            return

        try:
            # Use subprocess to run the command and capture output
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Regex to find the time and speed in FFmpeg's output
            time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2}).(\d{2})')

            while True:
                line = process.stderr.readline()
                if not line:
                    break
                
                # Search for the time pattern to calculate progress
                match = time_pattern.search(line)
                if match:
                    hours, minutes, seconds, hundredths = match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(hundredths) / 100
                    
                    progress = (current_time / total_duration) * 100
                    
                    if self.debug:
                        print(f"DEBUG: Calculated progress: {progress:.2f}%")
                    
                    db.update_task_progress(task_id, progress)

            return_code = process.wait()

            if return_code == 0:
                print(f"FFmpeg process for '{input_path}' completed successfully.")
                db.update_task_status(task_id, 'completed')
            else:
                print(f"Error: FFmpeg process for '{input_path}' failed with return code {return_code}.")
                db.update_task_status(task_id, 'failed')

        except FileNotFoundError:
            print("Error: FFmpeg or FFprobe not found. Please ensure they are installed and in your system's PATH.")
            db.update_task_status(task_id, 'failed')
        except Exception as e:
            print(f"FFmpeg processing failed: {e}")
            db.update_task_status(task_id, 'failed')

