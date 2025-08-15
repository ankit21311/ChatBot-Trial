# Production Deployment Guide

## Security Features Implemented

### 1. CORS Configuration
- ✅ **Restricted Origins**: No longer allows `*` (all origins)
- ✅ **Environment-based**: Uses `ALLOWED_ORIGINS` environment variable
- ✅ **Method Restrictions**: Only allows POST for chat endpoints
- ✅ **Header Controls**: Restricts allowed headers
- ✅ **Preflight Caching**: 1-hour cache for preflight requests

### 2. Security Headers
- ✅ **X-Content-Type-Options**: Prevents MIME sniffing
- ✅ **X-Frame-Options**: Prevents clickjacking
- ✅ **X-XSS-Protection**: XSS protection
- ✅ **Referrer-Policy**: Controls referrer information
- ✅ **HSTS**: HTTP Strict Transport Security (HTTPS only)

### 3. Session Security
- ✅ **Secure Cookies**: HTTPS-only in production
- ✅ **HttpOnly**: Prevents XSS cookie access
- ✅ **SameSite**: CSRF protection
- ✅ **Random Secret Key**: Cryptographically secure session key

### 4. Rate Limiting
- ✅ **Request Limits**: 20 requests per minute per IP
- ✅ **IP-based Tracking**: Uses X-Forwarded-For header
- ✅ **Automatic Cleanup**: Removes old rate limit entries

### 5. Input Validation
- ✅ **Length Limits**: Max 1000 characters
- ✅ **Content Filtering**: Blocks script tags and JavaScript
- ✅ **Type Validation**: Ensures string input
- ✅ **XSS Prevention**: Basic pattern matching

## Environment Variables for Production

### Required Variables
```bash
# Security (REQUIRED)
SECRET_KEY=your-super-secret-key-here-64-characters-minimum
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Flask Environment
FLASK_ENV=production

# Model Configuration (Optional - defaults to TinyLlama)
GGUF_REPO=TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
GGUF_FILE=tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
N_CTX=2048
N_GPU_LAYERS=0
```

### Generate Secure Secret Key
```bash
# Python method
python -c "import secrets; print(secrets.token_hex(32))"

# OpenSSL method
openssl rand -hex 32
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

#### Development
```bash
docker-compose up --build
```

#### Production
```bash
# Set environment variables first
export SECRET_KEY="your-generated-secret-key"
export ALLOWED_ORIGINS="https://yourdomain.com"
export FLASK_ENV="production"

# Deploy
docker-compose -f docker-compose.prod.yml up -d --build
```

### Option 2: Direct Python with Gunicorn

#### Install Gunicorn
```bash
pip install gunicorn
```

#### Run with Gunicorn
```bash
# Set environment variables
export SECRET_KEY="your-secret-key"
export ALLOWED_ORIGINS="https://yourdomain.com"
export FLASK_ENV="production"

# Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
```

### Option 3: Behind Reverse Proxy (Nginx)

#### Nginx Configuration
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for AI responses
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }
}
```

## Production Checklist

### Before Deployment
- [ ] Set `SECRET_KEY` environment variable
- [ ] Set `ALLOWED_ORIGINS` to your domain(s)
- [ ] Set `FLASK_ENV=production`
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up reverse proxy (Nginx/Apache)
- [ ] Configure firewall rules
- [ ] Set up monitoring/logging

### Security Verification
- [ ] Test CORS with your domain
- [ ] Verify rate limiting works
- [ ] Check security headers in browser dev tools
- [ ] Test input validation with malicious inputs
- [ ] Verify HTTPS redirects work
- [ ] Test session security

### Performance Optimization
- [ ] Configure appropriate worker processes
- [ ] Set up model caching
- [ ] Monitor memory usage
- [ ] Set up health checks
- [ ] Configure log rotation

## Monitoring and Logging

### Health Check Endpoint
The application includes a health check at `/` that returns the chat interface.

### Docker Health Check
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Log Monitoring
Monitor these log patterns:
- Rate limit exceeded: `429` status codes
- Validation errors: `400` status codes with validation messages
- Model loading: `Model loaded successfully`
- Security violations: Input validation failures

## Scaling Considerations

### Horizontal Scaling
- Use Redis for session storage instead of Flask sessions
- Implement proper rate limiting with Redis
- Use load balancer with sticky sessions

### Vertical Scaling
- Increase memory for larger models
- Use GPU acceleration (`N_GPU_LAYERS > 0`)
- Optimize worker processes based on CPU cores

## Security Best Practices

1. **Always use HTTPS in production**
2. **Keep dependencies updated**
3. **Monitor for security vulnerabilities**
4. **Implement proper logging and monitoring**
5. **Regular security audits**
6. **Backup and disaster recovery plans**
7. **Network segmentation**
8. **Regular penetration testing**

## Troubleshooting

### Common Issues
1. **CORS errors**: Check `ALLOWED_ORIGINS` matches your domain exactly
2. **Rate limiting**: Increase limits or implement Redis-based limiting
3. **Memory issues**: Use smaller model or increase container memory
4. **Session issues**: Verify `SECRET_KEY` is set and consistent

### Debug Mode
Never use debug mode in production. If needed for troubleshooting:
```bash
# Temporarily enable debug (NOT for production traffic)
export FLASK_DEBUG=True
```