import sqlite3
import os
import json

class Database:
    """
    Manages the SQLite database for media processing tasks.
    """
    def __init__(self, config_path, debug=False):
        self.config_path = config_path
        self.debug = debug
        self.config = self._load_config()
        self.conn = None
        self.cursor = None
        
    def _load_config(self):
        """Loads configuration from the specified file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading configuration: {e}")
            return {}

    def _get_db_path(self):
        """Constructs the database path from the configuration file."""
        return self.config.get('database_path')

    def initialize_database(self):
        """Initializes the database connection and creates the 'tasks' table."""
        db_path = self._get_db_path()
        if not db_path:
            print("Error: 'database_path' not found in configuration.")
            return False
            
        db_folder = os.path.dirname(db_path)
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
        
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            
            # Create tasks table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    processor TEXT NOT NULL,
                    processing_params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP
                )
            ''')
            self.conn.commit()
            
            if self.debug:
                print(f"DEBUG: Database path: {db_path}")
                print("DEBUG: Database initialized and 'tasks' table is ready.")
            
            return True
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

    def is_task_pending_or_processed(self, file_path):
        """
        Checks if a file is already in the database with a pending or processed status.
        """
        self.cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE file_path = ? AND status IN ('pending', 'processed')",
            (file_path,)
        )
        count = self.cursor.fetchone()[0]
        return count > 0

    def add_task(self, file_path, processor, processing_params):
        """Adds a new task to the database with 'pending' status."""
        try:
            self.cursor.execute(
                "INSERT INTO tasks (file_path, processor, processing_params, status) VALUES (?, ?, ?, ?)",
                (file_path, processor, processing_params, 'pending')
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Error adding task: {e}")
            return None

    def get_pending_tasks(self):
        """Retrieves all tasks with 'pending' status."""
        self.cursor.execute(
            "SELECT id, file_path, processor, processing_params, status FROM tasks WHERE status = 'pending'"
        )
        return self.cursor.fetchall()

    def update_task_progress(self, task_id, progress):
        """Updates the progress of a specific task."""
        self.cursor.execute(
            "UPDATE tasks SET progress = ? WHERE id = ?",
            (progress, task_id)
        )
        self.conn.commit()
        
    def update_task_status(self, task_id, status):
        """Updates the status of a specific task."""
        self.cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id)
        )
        self.conn.commit()

