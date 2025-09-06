import sqlite3
import os
import json
import logging

class Database:
    def __init__(self, config, debug=False):
        self.debug = debug
        self.config_path = ""
        self.config = config
        self.db_path = self._get_db_path()
        self.conn = None
        self.cursor = None
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            
    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file not found at {self.config_path}")
            return {}
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in configuration file at {self.config_path}")
            return {}

    def _get_db_path(self):
        """Builds the absolute path to the database file."""
        #config_dir = os.path.dirname(self.config_path)
        #relative_db_path = self.config.get('database_path', 'data/progress.db')
        #abs_path = os.path.normpath(os.path.join(config_dir, relative_db_path))
        abs_path = self.config.get('database_path', 'data/progress.db')
        if self.debug:
            logging.debug(f"Database path: {abs_path}")
        return abs_path

    def initialize_database(self):
        """Initializes the database connection and creates the tasks table."""
        try:
            # Create the directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
                if self.debug:
                    logging.debug(f"Created database directory at {db_dir}")

            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Create the tasks table with a new output_files column
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL UNIQUE,
                    processor TEXT NOT NULL,
                    processing_params TEXT,
                    output_files TEXT,
                    status TEXT NOT NULL,
                    progress REAL,
                    start_time TEXT,
                    end_time TEXT,
                    error_message TEXT
                )
            ''')
            self.conn.commit()
            if self.debug:
                logging.debug("Database initialized and 'tasks' table is ready.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Database error during initialization: {e}")
            return False

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

    def add_task(self, file_path, processor, processing_params):
        """Adds a new task to the database."""
        try:
            if self.debug:
                logging.debug(f"Adding task for '{file_path}' with processor '{processor}'.")
            
            status = 'pending'
            
            self.cursor.execute('''
                INSERT INTO tasks (file_path, processor, processing_params, status, progress)
                VALUES (?, ?, ?, ?, ?)
            ''', (file_path, processor, json.dumps(processing_params), status, 0.0))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            if self.debug:
                logging.debug(f"Task for '{file_path}' already exists.")
            return None
        except sqlite3.Error as e:
            logging.error(f"Database error while adding task: {e}")
            return None

    def is_task_recorded(self, file_path):
        """
        Checks if a task with the given file path already exists in the database.
        Returns True if a task exists, False otherwise.
        """
        try:
            self.cursor.execute('''
                SELECT EXISTS(SELECT 1 FROM tasks WHERE file_path = ?)
            ''', (file_path,))
            return self.cursor.fetchone()[0] == 1
        except sqlite3.Error as e:
            logging.error(f"Database error while checking for task: {e}")
            return False

    def get_pending_tasks(self):
        """Retrieves all pending tasks from the database."""
        try:
            self.cursor.execute("SELECT id, file_path, processor, processing_params, status, progress FROM tasks WHERE status = 'pending'")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error while getting pending tasks: {e}")
            return []
            
    def update_task_progress(self, task_id, progress, status=None):
        """Updates the progress and optional status of a task."""
        try:
            if status:
                self.cursor.execute("UPDATE tasks SET progress = ?, status = ? WHERE id = ?", (progress, status, task_id))
            else:
                self.cursor.execute("UPDATE tasks SET progress = ? WHERE id = ?", (progress, task_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error while updating task progress: {e}")

    def get_all_tasks(self):
        """Retrieves all tasks from the database."""
        try:
            self.cursor.execute("SELECT id, file_path, processor, processing_params, output_files, status, progress FROM tasks ORDER BY id DESC")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error while getting all tasks: {e}")
            return []

    def update_task_status(self, task_id, status, error_message=None):
        """Updates the status of a task."""
        try:
            if status == 'completed':
                self.cursor.execute("UPDATE tasks SET status = ?, progress = 100.0, end_time = CURRENT_TIMESTAMP WHERE id = ?", (status, task_id))
            elif status == 'failed':
                self.cursor.execute("UPDATE tasks SET status = ?, end_time = CURRENT_TIMESTAMP, error_message = ? WHERE id = ?", (status, error_message, task_id))
            else:
                self.cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error while updating task status: {e}")
    
    def update_task_output_files(self, task_id, output_files):
        """Updates the output files of a completed task."""
        try:
            self.cursor.execute("UPDATE tasks SET output_files = ? WHERE id = ?", (json.dumps(output_files), task_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error while updating output files: {e}")

