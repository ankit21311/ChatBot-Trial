# TinyLlama Chatbot - Docker Deployment

A Flask-based chatbot using TinyLlama model with Docker support for easy deployment.

## Quick Start

### Development Mode
```bash
# Build and run with development settings
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### Production Mode
```bash
# Build and run with production settings (Gunicorn)
docker-compose -f docker-compose.prod.yml up --build

# Or run in detached mode
docker-compose -f docker-compose.prod.yml up -d --build
```

The application will be available at `http://localhost:5000`

## Configuration

You can customize the model and settings by modifying environment variables in the docker-compose files:

- `GGUF_REPO`: HuggingFace repository for the model
- `GGUF_FILE`: Specific model file to download
- `N_CTX`: Context window size (default: 2048)
- `N_GPU_LAYERS`: Number of layers to run on GPU (default: 0, set >0 for CUDA)

## GPU Support

To enable GPU acceleration:

1. Install NVIDIA Docker runtime
2. Update `N_GPU_LAYERS` environment variable to a value > 0
3. Add GPU support to docker-compose:

```yaml
services:
  chatbot:
    # ... other config
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Deployment Options

### Local Development
- Use `docker-compose.yml` for development with hot reload
- Includes debug mode and development-friendly settings

### Production Deployment
- Use `docker-compose.prod.yml` for production
- Includes Gunicorn WSGI server
- Non-root user for security
- Resource limits and health checks

### Cloud Deployment

#### Docker Hub
```bash
# Build and tag
docker build -f Dockerfile.prod -t your-username/tinyllama-chatbot .

# Push to Docker Hub
docker push your-username/tinyllama-chatbot

# Run from Docker Hub
docker run -p 5000:5000 your-username/tinyllama-chatbot
```

#### Cloud Platforms
- **AWS ECS/Fargate**: Use the production Docker image
- **Google Cloud Run**: Supports containerized deployments
- **Azure Container Instances**: Direct Docker deployment
- **Railway/Render**: Git-based deployment with Dockerfile

## Storage

The application uses a Docker volume (`model_cache`) to persist downloaded models between container restarts. This prevents re-downloading the model every time the container starts.

## Health Checks

Both configurations include health checks that verify the application is responding correctly. The health check endpoint is the root path (`/`).

## Troubleshooting

### Model Download Issues
- Ensure you have internet connectivity
- Check if the HuggingFace repository and file names are correct
- Monitor logs: `docker-compose logs -f chatbot`

### Memory Issues
- The TinyLlama model requires ~2GB RAM minimum
- Adjust memory limits in docker-compose files if needed
- Consider using a smaller model for resource-constrained environments

### Port Conflicts
- Change the host port in docker-compose files if 5000 is already in use
- Example: `"8080:5000"` to use port 8080 instead

## Stopping the Application

```bash
# Development
docker-compose down

# Production
docker-compose -f docker-compose.prod.yml down

# Remove volumes (this will delete cached models)
docker-compose down -v
```