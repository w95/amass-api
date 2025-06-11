# Amass API

Amass API is a Flask-based web application designed to interact with OWASP Amass, enabling domain enumeration via a simple REST API. This API can be used by cybersecurity professionals to automate the discovery of subdomains during penetration testing, saving time and effort compared to manual methods. It provides options for recursive enumeration and brute-forcing subdomains, with results saved in a structured format.

## Features

- **Async Task Processing**: Queue-based system that processes one task at a time
- **SQLite Database**: Persistent storage for all tasks and results
- **Task Management**: Create, monitor, and retrieve task status and results
- **Queue Monitoring**: View current queue status and active tasks
- **Flexible Execution**: Support for both synchronous and asynchronous task execution
- **Domain URL Support**: Extract domains from full URLs or use direct domain input
- **Docker Persistence**: SQLite database and results persist across container restarts
- **RESTful API**: Clean REST endpoints for all operations

## Prerequisites

- Docker
- Docker Compose

## Installation

### Using Docker Compose

You can use the prebuilt Docker image from Docker Hub to quickly deploy the API:
```bash
docker pull enrikenur/amass-api
```

Follow these steps to set up the application:

1. Clone the repository:
   ```bash
   git clone https://github.com/w95/amass-api
   cd amass-api
   ```
2. Build and start the application using Docker Compose:
   ```bash
   docker-compose up --build
   ```
3. Once running, access the API at `http://localhost:5000`.

## API Endpoints

### Health Check

#### `GET /`
Check if the API is running.

**Response:**
```json
{
  "status": "ok"
}
```

### Task Management

#### `POST /task`
Create a new enumeration task (synchronous or asynchronous).

**Request Body (JSON):**

| Parameter           | Type    | Required | Description                                                    |
| ------------------- | ------- | -------- | -------------------------------------------------------------- |
| `domain`            | String  | Yes      | The target domain or URL for enumeration.                     |
| `brute`             | Boolean | No       | Enable brute-forcing of subdomains. Default: `false`.         |
| `min_for_recursive` | Integer | No       | Minimum number of findings to trigger recursion. Default: `2`. |
| `async`             | Boolean | No       | Run task asynchronously. Default: `false`.                    |

**Example Requests:**

Synchronous task:
```bash
curl -X POST http://localhost:5000/task \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "brute": true}'
```

Asynchronous task:
```bash
curl -X POST http://localhost:5000/task \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "brute": true, "async": true}'
```

**Response:**
- **Sync Success**:
  ```json
  {
    "status": "success",
    "message": "Amass enumeration completed.",
    "task_id": "uuid-task-id",
    "domain": "example.com",
    "output": ["subdomain1.example.com", "subdomain2.example.com"]
  }
  ```
- **Async Success**:
  ```json
  {
    "status": "success",
    "message": "Task queued successfully",
    "task_id": "uuid-task-id",
    "domain": "example.com",
    "async": true
  }
  ```

#### `GET /task/{task_id}`
Get the status and results of a specific task.

**Example:**
```bash
curl http://localhost:5000/task/uuid-task-id
```

**Response:**
```json
{
  "task_id": "uuid-task-id",
  "domain": "example.com",
  "status": "completed",
  "created_at": "2025-06-12T02:30:00",
  "started_at": "2025-06-12T02:30:05",
  "completed_at": "2025-06-12T02:31:20",
  "brute": true,
  "min_for_recursive": 2,
  "async": true,
  "output": ["subdomain1.example.com", "subdomain2.example.com"]
}
```

**Task Status Values:**
- `pending` - Task is queued
- `running` - Task is currently executing
- `completed` - Task finished successfully
- `failed` - Task failed (check `error_message`)

### Queue Management

#### `GET /queue`
View the current queue status.

**Example:**
```bash
curl http://localhost:5000/queue
```

**Response:**
```json
{
  "status": "success",
  "queue_size": 2,
  "current_task": "uuid-of-running-task",
  "worker_active": true
}
```

#### `GET /tasks`
List all tasks with their basic information.

**Example:**
```bash
curl http://localhost:5000/tasks
```

**Response:**
```json
{
  "status": "success",
  "total": 5,
  "tasks": [
    {
      "id": "uuid-task-1",
      "domain": "example.com",
      "status": "completed",
      "created_at": "2025-06-12T02:30:00",
      "brute": true,
      "async": true
    }
  ]
}
```

## Data Persistence

The API uses SQLite for persistent data storage:

- **Database**: `./data/amass_tasks.db` (persisted via Docker volume)
- **Results**: `./results/` directory (persisted via Docker volume)
- **Task History**: All tasks, their parameters, status, and results are stored
- **Queue State**: Tasks survive container restarts

## Development

### Local Development

For local development without Docker:

1. Install dependencies:
   ```bash
   pip3.10 install -r requirements.txt
   ```

2. Create necessary directories:
   ```bash
   mkdir -p data results
   ```

3. Run the application:
   ```bash
   python3.10 app.py
   ```

The API will be available at `http://localhost:5000`.

### Database Schema

The SQLite database contains a `tasks` table with the following structure:

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,                -- UUID task identifier
    domain TEXT NOT NULL,               -- Target domain
    brute BOOLEAN NOT NULL DEFAULT FALSE,          -- Brute force enabled
    min_for_recursive INTEGER DEFAULT 2,           -- Minimum for recursion
    async BOOLEAN NOT NULL DEFAULT FALSE,          -- Async execution
    status TEXT NOT NULL DEFAULT 'pending',        -- Task status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    result TEXT NULL,                   -- Amass output
    error_message TEXT NULL,            -- Error details if failed
    output_file TEXT NULL               -- Path to output file
);
```

## Usage Examples

### Complete Workflow Example

1. **Check API health:**
   ```bash
   curl http://localhost:5000/
   ```

2. **Queue an async task:**
   ```bash
   curl -X POST http://localhost:5000/task \
     -H "Content-Type: application/json" \
     -d '{"domain": "example.com", "brute": true, "async": true}'
   ```

3. **Check queue status:**
   ```bash
   curl http://localhost:5000/queue
   ```

4. **Monitor task progress:**
   ```bash
   curl http://localhost:5000/task/your-task-id
   ```

5. **List all tasks:**
   ```bash
   curl http://localhost:5000/tasks
   ```

## Error Handling

The API provides detailed error messages for various scenarios:

- **400 Bad Request**: Missing required parameters
- **404 Not Found**: Task ID not found
- **500 Internal Server Error**: Amass execution failed or other server errors

All error responses follow this format:
```json
{
  "status": "error",
  "message": "Error description"
}
```

## License

This project is licensed under the MIT License. See `LICENSE` for more details.

## Acknowledgments

- [OWASP Amass](https://github.com/OWASP/Amass) for providing the enumeration tool.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.
