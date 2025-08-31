import os
import subprocess
import json
import re
import math
import logging
from processors import Processor

class HevcScaleProcessor(Processor):
    """
    Processor to scale video files using HEVC encoding.
    """
    def __init__(self, config, debug=False):
        super().__init__(config, debug)
        self.logger = logging.getLogger(__name__)

    def _get_output_path(self, input_path, processing_params):
        """
        Generates the output file path for the scaled video.
        """
        if 'output_file_extension' in self.config:
            output_extension = self.config['output_file_extension']
        else:
            output_extension = os.path.splitext(input_path)[1]
        
        output_parent_folder = self.config.get('output_parent_folder', 'outbox')
        input_path_prefix = processing_params.get('input_path_prefix', '')
        
        # Ensure the output path is correctly formed using the prefix and base filename
        base_filename = os.path.basename(input_path)
        output_folder = os.path.join(output_parent_folder, input_path_prefix)
        output_file_name = f"{os.path.splitext(base_filename)[0]}{output_extension}"
        output_path = os.path.join(output_folder, output_file_name)

        os.makedirs(output_folder, exist_ok=True)
        
        if self.debug:
            print(f"DEBUG: Generated output path: {output_path}")

        return output_path

    def process(self, input_path, task_id, db, **kwargs):
        """
        Processes a video file by scaling it to a specified height.
        """
        if self.debug:
            print(f"DEBUG: Starting HEVC scaling process for '{input_path}' to height {kwargs.get('height')}.")

        output_path = self._get_output_path(input_path, kwargs)
        
        if self.debug:
            print(f"DEBUG: Generated output path: {output_path}")

        ffmpeg_cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale=-2:{kwargs.get("height")}',
            '-c:v', 'libx265',
            '-crf', '28',
            '-preset', 'fast',
            '-c:a', 'copy',
            output_path
        ]
        
        if self.debug:
            print(f"DEBUG: FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
        try:
            db.update_task_status(task_id, 'processing')
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            total_duration_secs = self._get_media_duration(input_path)
            
            for line in process.stdout:
                progress = self._parse_progress(line, total_duration_secs)
                if progress is not None:
                    db.update_task_progress(task_id, progress)

            process.wait()

            if process.returncode == 0:
                db.update_task_status(task_id, 'completed')
                if self.debug:
                    print(f"DEBUG: FFmpeg process for '{input_path}' completed successfully.")
            else:
                db.update_task_status(task_id, 'failed')
                print(f"Error: FFmpeg process for '{input_path}' failed with return code {process.returncode}.")

        except FileNotFoundError:
            db.update_task_status(task_id, 'failed')
            print("Error: ffmpeg command not found. Please ensure FFmpeg is installed and in your system's PATH.")
        except Exception as e:
            db.update_task_status(task_id, 'failed')
            print(f"An unrecoverable error occurred during FFmpeg processing: {e}")

    def _get_media_duration(self, file_path):
        """
        Gets the duration of a media file in seconds using ffprobe.
        """
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        try:
            output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.DEVNULL)
            return float(output)
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            self.logger.warning("Could not get media duration with ffprobe. Progress will not be reported.")
            return None
            
    def _parse_progress(self, line, total_duration_secs):
        """
        Parses FFmpeg output to get the current processing progress.
        """
        if total_duration_secs is None:
            return None

        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = int(time_match.group(3))
            current_time_secs = hours * 3600 + minutes * 60 + seconds
            progress = math.floor((current_time_secs / total_duration_secs) * 100)
            return max(0, min(100, progress))
            
        return None

