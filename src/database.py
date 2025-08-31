import sqlite3
import os
import json

class Database:
    """
    Manages the SQLite database for storing media processing tasks and their status.
    """
    def __init__(self, config_path, debug=False):
        self.config = self._load_config(config_path)
        self.debug = debug
        self.db_path = self._get_db_path()
        self.conn = None
        
    def _load_config(self, config_path):
        """Loads configuration from the specified file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading configuration: {e}")
            return {}
        
    def _get_db_path(self):
        """Constructs the database file path from configuration."""
        db_path = self.config.get('database_path')
        if db_path:
            return db_path
        
        # Fallback to default if not specified in config
        db_file = self.config.get('database_file', 'progress.db')
        db_folder = self.config.get('database_folder', 'data')
        
        # Ensure the directory exists
        os.makedirs(db_folder, exist_ok=True)
        return os.path.join(db_folder, db_file)

    def initialize_database(self):
        """Initializes the database connection and creates the tasks table if it doesn't exist."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    processor TEXT NOT NULL,
                    processing_params TEXT,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            if self.debug:
                print(f"DEBUG: Database path: {self.db_path}")
                print("DEBUG: Database initialized and 'tasks' table is ready.")
            return True
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
            return False

    def add_task(self, file_path, processor_name, processing_params):
        """Adds a new task to the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (file_path, processor, processing_params, status)
                VALUES (?, ?, ?, 'pending')
            ''', (file_path, processor_name, processing_params))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding task: {e}")
            return None

    def get_pending_tasks(self):
        """Fetches all tasks with a 'pending' or 'processing' status."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, file_path, processor, processing_params, status FROM tasks
                WHERE status IN ('pending', 'processing')
                ORDER BY created_at
            ''')
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error fetching pending tasks: {e}")
            return []

    def update_task_status(self, task_id, status):
        """Updates the status of a task."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (status, task_id))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating task status for task {task_id}: {e}")

    def update_task_progress(self, task_id, progress):
        """Updates the progress of a task."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE tasks SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (progress, task_id))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating task progress for task {task_id}: {e}")

    def is_task_recorded(self, file_path):
        """
        Checks if a file path already exists in the tasks table, regardless of its status.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE file_path = ?', (file_path,))
            return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            print(f"Error checking for existing task for '{file_path}': {e}")
            return False
            
    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            if self.debug:
                print("DEBUG: Database connection closed.")

