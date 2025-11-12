# AutoDevOS FastAPI Server Setup

## Overview

This document explains how to run AutoDevOS as a FastAPI server for API-based application generation.

## Installation

1. **Activate your virtual environment** (if not already activated):

   ```bash
   source venv/bin/activate
   # or if using .venv_pyinstaller
   source .venv_pyinstaller/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

### Option 1: Using the server.py script

```bash
python server.py
```

### Option 2: Using uvicorn directly

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Using fastapi CLI

```bash
fastapi dev main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Health Check

**GET** `/health`

Check if the server is running.

**Response:**

```json
{
  "status": "ok",
  "service": "AutoDevOS"
}
```

### Generate Application

**POST** `/generate`

Generate an application from a natural language prompt.

**Request Body:**

```json
{
  "prompt": "Create a todo app with user authentication",
  "output_dir": "output" // optional, defaults to "output"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Generation complete! 4/4 tasks succeeded",
  "summary": {
    "total": 4,
    "completed": 4,
    "failed": 0
  }
}
```

## Testing the API

### Using curl

**Health Check:**

```bash
curl http://localhost:8000/health
```

**Generate Application:**

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a simple blog application with posts and comments"}'
```

### Using Python requests

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Generate application
response = requests.post(
    "http://localhost:8000/generate",
    json={
        "prompt": "Create a todo app with React frontend and FastAPI backend",
        "output_dir": "my_todo_app"
    }
)
print(response.json())
```

### Using httpie

```bash
# Health check
http GET http://localhost:8000/health

# Generate application
http POST http://localhost:8000/generate \
  prompt="Create a dashboard with charts and data visualization"
```

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

You can configure the server using environment variables:

- `GOOGLE_API_KEY`: Your Google Generative AI API key (required for LLM functionality)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

## Production Deployment

For production deployment, consider:

1. **Using gunicorn with uvicorn workers:**

   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **Using Docker:**

   ```bash
   docker build -t autodevos -f docker/Dockerfile .
   docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key autodevos
   ```

3. **Setting up HTTPS/TLS** with a reverse proxy like nginx or using cloud providers' load balancers

## Troubleshooting

### Import Errors

If you see import errors for fastapi or uvicorn, ensure dependencies are installed:

```bash
pip install fastapi uvicorn pydantic
```

### Port Already in Use

If port 8000 is already in use, specify a different port:

```bash
uvicorn main:app --port 8001
```

### API Key Issues

Ensure your `GOOGLE_API_KEY` environment variable is set:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Monitoring

The server logs all operations. Monitor the logs for:

- Incoming requests
- Generation progress
- Errors and warnings

## Notes

- The server runs asynchronously, allowing concurrent request handling
- Each generation creates artifacts in the specified output directory
- Generation can take several minutes depending on the complexity of the prompt
- The server maintains no state between requests - each generation is independent
