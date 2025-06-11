import subprocess
import os
import sqlite3
import uuid
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from queue import Queue
from enum import Enum

app = Flask(__name__)

# Swagger API setup
api = Api(app, 
    version='1.0', 
    title='Amass API',
    description='A Flask API for OWASP Amass domain enumeration with async task processing',
    doc='/docs/'
)

# Database configuration
# Use local path when running locally, Docker path when in container
DATABASE_PATH = './data/amass_tasks.db' if not os.path.exists('/app') else '/app/data/amass_tasks.db'

# Task status enum
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Global task queue and worker thread
task_queue = Queue()
current_task = None
task_worker_thread = None

# Swagger models
task_model = api.model('Task', {
    'domain': fields.String(required=True, description='Domain or URL to enumerate'),
    'brute': fields.Boolean(required=False, default=False, description='Enable brute force'),
    'min_for_recursive': fields.Integer(required=False, default=2, description='Minimum for recursive enumeration'),
    'async': fields.Boolean(required=False, default=False, description='Run asynchronously')
})

task_response_model = api.model('TaskResponse', {
    'status': fields.String(description='Response status'),
    'message': fields.String(description='Response message'),
    'task_id': fields.String(description='Unique task identifier'),
    'domain': fields.String(description='Processed domain'),
    'async': fields.Boolean(description='Async flag')
})

task_status_model = api.model('TaskStatus', {
    'task_id': fields.String(description='Task ID'),
    'domain': fields.String(description='Domain'),
    'status': fields.String(description='Task status'),
    'created_at': fields.String(description='Creation timestamp'),
    'started_at': fields.String(description='Start timestamp'),
    'completed_at': fields.String(description='Completion timestamp'),
    'brute': fields.Boolean(description='Brute force enabled'),
    'min_for_recursive': fields.Integer(description='Min for recursive'),
    'async': fields.Boolean(description='Async execution'),
    'output': fields.List(fields.String, description='Task output'),
    'error_message': fields.String(description='Error message if failed')
})

def init_database():
    """Initialize SQLite database with required tables."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            brute BOOLEAN NOT NULL DEFAULT FALSE,
            min_for_recursive INTEGER DEFAULT 2,
            async BOOLEAN NOT NULL DEFAULT FALSE,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP NULL,
            completed_at TIMESTAMP NULL,
            result TEXT NULL,
            error_message TEXT NULL,
            output_file TEXT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def extract_domain(input_string):
    """
    Extract domain from either a domain string or a full URL.
    Examples:
    - 'example.com' -> 'example.com'
    - 'https://example.com/path' -> 'example.com'
    - 'http://subdomain.example.com:8080/path?query=1' -> 'subdomain.example.com'
    """
    # If the input doesn't contain :// it's likely just a domain
    if '://' not in input_string:
        return input_string.strip()
    
    # Parse as URL
    try:
        parsed = urlparse(input_string)
        domain = parsed.netloc
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
            
        return domain.strip()
    except Exception:
        # If parsing fails, return the original input
        return input_string.strip()

def save_task_to_db(task_id, domain, brute=False, min_for_recursive=2, async_task=False):
    """Save a new task to the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO tasks (id, domain, brute, min_for_recursive, async, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (task_id, domain, brute, min_for_recursive, async_task, TaskStatus.PENDING.value))
    
    conn.commit()
    conn.close()

def update_task_status(task_id, status, started_at=None, completed_at=None, result=None, error_message=None, output_file=None):
    """Update task status in the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    update_fields = ["status = ?"]
    values = [status]
    
    if started_at:
        update_fields.append("started_at = ?")
        values.append(started_at)
    
    if completed_at:
        update_fields.append("completed_at = ?")
        values.append(completed_at)
    
    if result:
        update_fields.append("result = ?")
        values.append(result)
    
    if error_message:
        update_fields.append("error_message = ?")
        values.append(error_message)
    
    if output_file:
        update_fields.append("output_file = ?")
        values.append(output_file)
    
    values.append(task_id)
    
    cursor.execute(f'''
        UPDATE tasks SET {", ".join(update_fields)}
        WHERE id = ?
    ''', values)
    
    conn.commit()
    conn.close()

def get_task_from_db(task_id):
    """Get task details from database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))
    return None

def get_all_tasks_from_db():
    """Get all tasks from database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def reset_database():
    """Reset the database by dropping and recreating the tasks table."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Drop the table if it exists
    cursor.execute('DROP TABLE IF EXISTS tasks')
    
    # Recreate the table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            brute BOOLEAN NOT NULL DEFAULT FALSE,
            min_for_recursive INTEGER DEFAULT 2,
            async BOOLEAN NOT NULL DEFAULT FALSE,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP NULL,
            completed_at TIMESTAMP NULL,
            result TEXT NULL,
            error_message TEXT NULL,
            output_file TEXT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def execute_amass_command(task_id, domain, brute=False, min_for_recursive=2):
    """Execute the amass command for a given task."""
    global current_task
    current_task = task_id
    
    # Update task status to running
    update_task_status(task_id, TaskStatus.RUNNING.value, started_at=datetime.now().isoformat())
    
    try:
        # Define output file path (local vs Docker paths)
        results_dir = "./results" if not os.path.exists('/app') else "/results"
        output_file = f"{results_dir}/amass_output_{domain}_{task_id}.txt"
        
        # Build the command
        command = [
            "amass", "enum",
            "-d", domain,
            "-min-for-recursive", str(min_for_recursive),
            "-o", output_file
        ]
        if brute:
            command.append("-brute")
        
        # Execute the command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            update_task_status(
                task_id, 
                TaskStatus.FAILED.value,
                completed_at=datetime.now().isoformat(),
                error_message=f"Command failed: {result.stderr.strip()}"
            )
            return
        
        # Read the output file
        output_list = []
        if os.path.exists(output_file):
            with open(output_file, "r") as f:
                output_list = f.read().strip().split("\n")
        
        # Update task status to completed
        update_task_status(
            task_id,
            TaskStatus.COMPLETED.value,
            completed_at=datetime.now().isoformat(),
            result='\n'.join(output_list),
            output_file=output_file
        )
        
    except Exception as e:
        update_task_status(
            task_id,
            TaskStatus.FAILED.value,
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )
    finally:
        current_task = None

def task_worker():
    """Worker function that processes tasks from the queue."""
    while True:
        try:
            task_data = task_queue.get(timeout=1)
            if task_data is None:  # Shutdown signal
                break
            
            execute_amass_command(
                task_data['task_id'],
                task_data['domain'],
                task_data['brute'],
                task_data['min_for_recursive']
            )
            
            task_queue.task_done()
        except:
            # Timeout or other exception, continue
            pass

def start_task_worker():
    """Start the task worker thread."""
    global task_worker_thread
    if task_worker_thread is None or not task_worker_thread.is_alive():
        task_worker_thread = threading.Thread(target=task_worker, daemon=True)
        task_worker_thread.start()

@api.route('/')
class HealthCheck(Resource):
    @api.doc('health_check')
    def get(self):
        """Health check endpoint"""
        return {"status": "ok"}, 200

@api.route('/task')
class TaskCreate(Resource):
    @api.doc('create_task')
    @api.expect(task_model)
    @api.response(200, 'Task completed successfully')
    @api.response(202, 'Task queued successfully')
    @api.response(400, 'Bad request')
    @api.response(500, 'Internal server error')
    def post(self):
        """Create a new enumeration task (sync or async)"""
        try:
            data = request.json
            domain_input = data.get("domain")
            brute = data.get("brute", False)
            min_for_recursive = data.get("min_for_recursive", 2)
            async_task = data.get("async", False)

            if not domain_input:
                return {"status": "error", "message": "Domain is required"}, 400

            # Extract domain from URL if provided
            domain = extract_domain(domain_input)
            
            if not domain:
                return {"status": "error", "message": "Invalid domain or URL"}, 400

            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Save task to database
            save_task_to_db(task_id, domain, brute, min_for_recursive, async_task)
            
            if async_task:
                # Add task to queue
                task_queue.put({
                    'task_id': task_id,
                    'domain': domain,
                    'brute': brute,
                    'min_for_recursive': min_for_recursive
                })
                
                return {
                    "status": "success",
                    "message": "Task queued successfully",
                    "task_id": task_id,
                    "domain": domain,
                    "async": True
                }, 202
            else:
                # Execute synchronously (original behavior)
                execute_amass_command(task_id, domain, brute, min_for_recursive)
                task_data = get_task_from_db(task_id)
                
                if task_data['status'] == TaskStatus.COMPLETED.value:
                    return {
                        "status": "success",
                        "message": "Amass enumeration completed.",
                        "task_id": task_id,
                        "domain": domain,
                        "output": task_data['result'].split('\n') if task_data['result'] else []
                    }, 200
                else:
                    return {
                        "status": "error",
                        "message": task_data['error_message'] or "Task failed",
                        "task_id": task_id
                    }, 500

        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

@api.route('/task/<string:task_id>')
class TaskStatus(Resource):
    @api.doc('get_task_status')
    @api.response(200, 'Task status retrieved successfully')
    @api.response(404, 'Task not found')
    @api.response(500, 'Internal server error')
    def get(self, task_id):
        """Get the status and results of a specific task"""
        try:
            task_data = get_task_from_db(task_id)
            
            if not task_data:
                return {"status": "error", "message": "Task not found"}, 404
            
            response_data = {
                "task_id": task_data['id'],
                "domain": task_data['domain'],
                "status": task_data['status'],
                "created_at": task_data['created_at'],
                "brute": bool(task_data['brute']),
                "min_for_recursive": task_data['min_for_recursive'],
                "async": bool(task_data['async'])
            }
            
            if task_data['started_at']:
                response_data['started_at'] = task_data['started_at']
            
            if task_data['completed_at']:
                response_data['completed_at'] = task_data['completed_at']
            
            if task_data['status'] == TaskStatus.COMPLETED.value and task_data['result']:
                response_data['output'] = task_data['result'].split('\n')
            
            if task_data['error_message']:
                response_data['error_message'] = task_data['error_message']
            
            return response_data, 200
            
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

@api.route('/queue')
class QueueStatus(Resource):
    @api.doc('get_queue_status')
    def get(self):
        """Get the current queue status"""
        try:
            queue_size = task_queue.qsize()
            
            return {
                "status": "success",
                "queue_size": queue_size,
                "current_task": current_task,
                "worker_active": task_worker_thread is not None and task_worker_thread.is_alive()
            }, 200
            
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

@api.route('/tasks')
class TaskList(Resource):
    @api.doc('get_all_tasks')
    def get(self):
        """Get all tasks"""
        try:
            tasks = get_all_tasks_from_db()
            
            # Convert boolean fields and format output
            for task in tasks:
                task['brute'] = bool(task['brute'])
                task['async'] = bool(task['async'])
                # Don't include full result in list view
                if 'result' in task:
                    del task['result']
            
            return {
                "status": "success",
                "tasks": tasks,
                "total": len(tasks)
            }, 200
            
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

@api.route('/reset')
class DatabaseReset(Resource):
    @api.doc('reset_database')
    @api.response(200, 'Database reset successfully')
    @api.response(500, 'Internal server error')
    def post(self):
        """Reset the database and clear all tasks"""
        try:
            # Clear the task queue
            while not task_queue.empty():
                try:
                    task_queue.get_nowait()
                except:
                    break
            
            # Reset the database
            reset_database()
            
            return {
                "status": "success",
                "message": "Database reset successfully. All tasks have been cleared."
            }, 200
            
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500



if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Ensure the results directory exists (local vs Docker paths)
    results_dir = "./results" if not os.path.exists('/app') else "/results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Start the task worker thread
    start_task_worker()
    
    app.run(host='0.0.0.0', port=5000)

