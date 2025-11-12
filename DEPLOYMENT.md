# AutoDevOS Server Deployment Guide

## Quick Start

### Local Development

1. **Start the server:**

   ```bash
   ./start_server.sh
   ```

   Or manually:

   ```bash
   source venv/bin/activate
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test the server:**

   ```bash
   # Health check
   curl http://localhost:8000/health

   # Generate an app
   python test_api.py
   ```

3. **Access API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t autodevos-server -f docker/Dockerfile.server .

# Run the container
docker run -d \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key_here \
  -v $(pwd)/output:/app/output \
  --name autodevos \
  autodevos-server

# Check logs
docker logs -f autodevos

# Stop the container
docker stop autodevos
```

### Using Docker Compose

```bash
# Start the service
docker-compose -f docker/docker-compose.server.yml up -d

# View logs
docker-compose -f docker/docker-compose.server.yml logs -f

# Stop the service
docker-compose -f docker/docker-compose.server.yml down
```

## Production Deployment

### Option 1: Deploy on Cloud Run (GCP)

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/autodevos-server

# Deploy to Cloud Run
gcloud run deploy autodevos-server \
  --image gcr.io/PROJECT_ID/autodevos-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key \
  --memory 2Gi \
  --timeout 600s
```

### Option 2: Deploy on AWS ECS/Fargate

1. **Push to ECR:**

   ```bash
   aws ecr create-repository --repository-name autodevos-server

   docker tag autodevos-server:latest \
     AWS_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/autodevos-server:latest

   docker push AWS_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/autodevos-server:latest
   ```

2. **Create ECS Task Definition** (see AWS console or use Terraform)

3. **Create ECS Service** with Application Load Balancer

### Option 3: Deploy on Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autodevos-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: autodevos-server
  template:
    metadata:
      labels:
        app: autodevos-server
    spec:
      containers:
        - name: autodevos
          image: autodevos-server:latest
          ports:
            - containerPort: 8000
          env:
            - name: GEMINI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: autodevos-secrets
                  key: gemini-api-key
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: autodevos-service
spec:
  selector:
    app: autodevos-server
  ports:
    - port: 80
      targetPort: 8000
  type: LoadBalancer
```

Deploy:

```bash
kubectl apply -f deployment.yaml
```

### Option 4: Deploy on VPS (DigitalOcean, Linode, etc.)

1. **Install dependencies:**

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv nginx
   ```

2. **Clone and setup:**

   ```bash
   git clone YOUR_REPO
   cd autodevos-dev
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create systemd service:**

   ```bash
   sudo nano /etc/systemd/system/autodevos.service
   ```

   ```ini
   [Unit]
   Description=AutoDevOS FastAPI Server
   After=network.target

   [Service]
   Type=simple
   User=YOUR_USER
   WorkingDirectory=/path/to/autodevos-dev
   Environment="PATH=/path/to/autodevos-dev/venv/bin"
   EnvironmentFile=/path/to/autodevos-dev/.env
   ExecStart=/path/to/autodevos-dev/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

4. **Start the service:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable autodevos
   sudo systemctl start autodevos
   sudo systemctl status autodevos
   ```

5. **Setup Nginx as reverse proxy:**

   ```bash
   sudo nano /etc/nginx/sites-available/autodevos
   ```

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 600s;
       }
   }
   ```

   ```bash
   sudo ln -s /etc/nginx/sites-available/autodevos /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

6. **Setup SSL with Let's Encrypt:**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## Environment Variables for Production

Create a `.env` file or set environment variables:

```bash
# Required
GEMINI_API_KEY=your_google_api_key

# Optional
HOST=0.0.0.0
PORT=8000
MAX_PARALLEL_TASKS=4
USE_DYNAMIC_PLANNING=false
LOG_LEVEL=info
DEBUG=false
```

## Security Best Practices

1. **API Key Management:**

   - Never commit `.env` files
   - Use secret management services (AWS Secrets Manager, GCP Secret Manager, etc.)
   - Rotate API keys regularly

2. **Rate Limiting:**
   Consider adding rate limiting middleware:

   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

   @app.post('/generate')
   @limiter.limit("10/hour")
   async def generate(request: Request, gen_request: GenerateRequest):
       ...
   ```

3. **Authentication:**
   Add API key authentication:

   ```python
   from fastapi import Security, HTTPException
   from fastapi.security import APIKeyHeader

   api_key_header = APIKeyHeader(name="X-API-Key")

   async def verify_api_key(api_key: str = Security(api_key_header)):
       if api_key != os.getenv("API_KEY"):
           raise HTTPException(status_code=403, detail="Invalid API key")
       return api_key
   ```

4. **HTTPS:**
   Always use HTTPS in production with valid SSL certificates

5. **CORS:**
   Configure CORS appropriately:

   ```python
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-frontend.com"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

## Monitoring and Logging

### Application Monitoring

1. **Add Prometheus metrics:**

   ```bash
   pip install prometheus-fastapi-instrumentator
   ```

   ```python
   from prometheus_fastapi_instrumentator import Instrumentator

   Instrumentator().instrument(app).expose(app)
   ```

2. **Add structured logging:**

   ```python
   import logging
   import json

   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('app.log'),
           logging.StreamHandler()
       ]
   )
   ```

3. **Add Sentry for error tracking:**

   ```bash
   pip install sentry-sdk
   ```

   ```python
   import sentry_sdk

   sentry_sdk.init(
       dsn="your-sentry-dsn",
       traces_sample_rate=1.0,
   )
   ```

## Performance Optimization

1. **Use gunicorn with multiple workers:**

   ```bash
   pip install gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **Enable response compression:**

   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```

3. **Add caching for static responses**

4. **Use async/await consistently**

## Troubleshooting

### Server won't start

- Check if port 8000 is available: `lsof -i :8000`
- Verify dependencies: `pip list | grep fastapi`
- Check logs: `tail -f app.log`

### Import errors

- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
- Check Python version: `python --version` (requires 3.11+)

### Generation fails

- Verify GEMINI_API_KEY is set correctly
- Check API quota/limits
- Review logs for specific errors

### High memory usage

- Reduce MAX_PARALLEL_TASKS
- Implement request queuing
- Consider using Celery for background tasks

## Backup and Recovery

1. **Backup generated artifacts:**

   ```bash
   tar -czf backup-$(date +%Y%m%d).tar.gz output/
   ```

2. **Database backups** (if you add a database later)

3. **Configuration backups:**
   ```bash
   cp .env .env.backup
   ```

## Scaling

For high-load scenarios:

1. **Horizontal scaling:** Deploy multiple instances behind a load balancer
2. **Queue system:** Use Celery + Redis for async task processing
3. **Caching:** Add Redis for response caching
4. **CDN:** Use CloudFlare or similar for static assets

## Support

For issues or questions:

- Check logs: `docker logs autodevos` or `tail -f app.log`
- Review API docs: http://your-server:8000/docs
- GitHub Issues: YOUR_REPO_URL/issues
