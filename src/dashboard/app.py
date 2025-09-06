import json
import sqlite3
import os
import threading
from flask import Flask, jsonify, render_template

# Lock for thread-safe database access
DB_LOCK = threading.Lock()

def get_db_connection(db_path):
    """Establishes and returns a new database connection."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_tasks(db_path):
    """Fetches all tasks from the database."""
    with DB_LOCK:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
        tasks = cursor.fetchall()
        conn.close()
    return tasks

def load_config(config_path):
    """Loads configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

app = Flask(__name__, template_folder='templates')
app.config['CONFIG'] = load_config('config.json')

if not app.config['CONFIG']:
    raise FileNotFoundError("Dashboard config.json not found.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tasks')
def api_tasks():
    db_path = app.config['CONFIG']['database_path']
    try:
        tasks = get_tasks(db_path)
        task_list = []
        for task in tasks:
            task_dict = dict(task)
            # Ensure output_files is a list
            if isinstance(task_dict.get('output_files'), str):
                try:
                    task_dict['output_files'] = json.loads(task_dict['output_files'])
                except json.JSONDecodeError:
                    task_dict['output_files'] = []
            else:
                task_dict['output_files'] = []

            task_list.append(task_dict)
        return jsonify(task_list)
    except sqlite3.Error as e:
        print(f"Database error while getting all tasks: {e}")
        return jsonify({"error": "Database error"}), 500

if __name__ == '__main__':
    app.run(host=app.config['CONFIG']['host'], port=app.config['CONFIG']['port'])

