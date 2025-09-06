
# Media Processing and Monitoring System

This project is a robust and modular system for automated media file processing. It is designed to monitor a designated folder, automatically detect new media files, and process them using configurable FFmpeg commands. All task progress is tracked in a local SQLite database and can be monitored via a live web dashboard.

This document serves as a comprehensive guide for the project's MVP (Minimum Viable Product).


## Features



* **Automated File Monitoring:** The system continuously scans a specified input folder for new audio or video files.
* **Dynamic Processing:** Processing instructions (e.g., video scaling, bitrate conversion) are determined by the folder path of the input file, enabling a highly dynamic and extensible workflow.
* **FFmpeg Integration:** Utilizes FFmpeg for all media processing tasks, leveraging a powerful and widely-supported tool.
* **Progress Tracking:** All processing tasks are tracked in a local SQLite database, allowing for persistent storage of progress, status, and metadata.
* **Web Dashboard:** A simple, live-updating web dashboard provides a visual overview of all processing tasks and their current status.
* **Modular Design:** The system is built with a modular architecture, making it easy to add new processing capabilities without modifying the core logic.


## Getting Started


### Prerequisites

You will need the following software installed on your machine to run the project.



* **Python 3.8+:** The core of the application is built in Python.
* **pip:** The Python package installer.
* **FFmpeg & FFprobe:** These command-line tools are essential for all media processing. FFprobe is used to get the duration of media files for progress tracking.


### Installation



1. **Clone the Repository:** \
```
git clone https://github.com/wereboss/media-processor.git \
cd media-processor \
```
2. **Install Python Dependencies:** \
```
pip install Flask \
```


### Folder Structure

Your project should be organized as follows. Create the empty folders as shown below.
```
. \
├── config/ \
│   ├── config.json \
│   └── dashboard/ \
│       └── config.json \
├── src/ \
│   ├── database.py \
│   ├── file_monitor.py \
│   ├── media_controller.py \
│   └── processors/ \
│       ├── __init__.py \
│       └── hevc_scale_processor.py \
├── main.py \
├── README.md \
├── inbox/ \
│   └── video_HEVC_height/ \
│       └── 360/ \
├── outbox/ \
```



* **inbox/**: The main folder where you place new media files to be processed.
* **outbox/**: The folder where processed media files will be saved.


## Configuration


### Processor Configuration

The config/config.json file controls the core processing logic.



* input_parent_folder: The root directory to be monitored for new media files.
* output_parent_folder: The root directory where processed files will be saved.
* database_path: The path for the SQLite database file.
* monitoring_interval: The time in seconds between each scan cycle.
* processors: A list of objects that define each processing capability.
    * name: A user-friendly name for the processor.
    * input_path: The sub-folder path to watch for this specific processor.
    * processor: The name of the Python file containing the processor class.
    * output_path: The output sub-folder for this processor's output.
    * output_file_extension: (Optional) The desired file extension for the output file.
```
{ \
    "input_parent_folder": "inbox", \
    "output_parent_folder": "outbox", \
    "database_path": "data/progress.db", \
    "monitoring_interval": 5, \
    "processors": [ \
        { \
            "name": "HEVC Scaler", \
            "input_path": "video_HEVC_height", \
            "processor": "hevc_scale_processor", \
            "output_path": "video_HEVC", \
            "output_file_extension": "mp4" \
        } \
    ] \
} \
```


### Dashboard Configuration

The src/dashboard/config.json file configures the web dashboard.



* database_path: A relative path from the dashboard folder to the progress.db file.
* host: The host IP address for the Flask server. Use 0.0.0.0 to make it accessible from other machines on the network.
* port: The port number for the Flask server.
```
{ \
    "database_path": "../../data/progress.db", \
    "host": "0.0.0.0", \
    "port": 5000, \
    "refresh_interval_seconds": 3 \
} \
```


## Usage


### To Run the Media Processor

From the project's root directory, run the main.py script with your configuration file.
```
python3 main.py config/config.json --debug \
```


### To Run the Web Dashboard

Navigate to the dashboard directory and run app.py.
```
cd src/dashboard/ \
python3 app.py \
```

You can then access the dashboard by navigating to http://&lt;your-machine-ip>:5000 in your web browser.


## MVP: Version 1.0

This initial version of the project establishes a robust and scalable foundation. It successfully handles the core task of monitoring, processing, and tracking HEVC video scaling. The modular design, database integration, and web dashboard make it a powerful starting point. Future versions can easily expand upon this foundation to add new processors, more complex logic, and a more interactive user interface.