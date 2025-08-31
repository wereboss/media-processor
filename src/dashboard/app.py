import os
import json
import sqlite3
from flask import Flask, jsonify, render_template

app = Flask(__name__)
config = {}
db_path = ""
# A simple in-memory cache to store task info
# This is a simple solution for this example to reduce database queries.
# For production, a more robust caching solution like Redis would be ideal.
task_cache = {}

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return render_template('index.html')

@app.route('/api/tasks')
def get_tasks():
    """API endpoint to get all tasks from the database."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_path, status, progress, updated_at FROM tasks ORDER BY updated_at DESC")
        tasks = cursor.fetchall()
        
        # Convert rows to a list of dictionaries for JSON serialization
        tasks_list = [dict(task) for task in tasks]
        return jsonify(tasks_list)
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"error": "Failed to retrieve tasks"}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Load configuration from the JSON file
    config_file_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
        db_path = config.get('database_path', 'progress.db')
        host = config.get('host', '127.0.0.1')
        port = config.get('port', 5000)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_file_path}")
        exit()
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file at {config_file_path}")
        exit()
    
    # Run the Flask app
    app.run(debug=True, host=host, port=port)

