# Deployment Guide

Comprehensive guide for deploying the Autonomous Report Generator to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Configuration](#environment-configuration)
- [Monitoring Setup](#monitoring-setup)
- [Security Considerations](#security-considerations)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Docker** 20.10+ and Docker Compose 2.0+
- **Kubernetes** 1.24+ (for K8s deployment)
- **kubectl** configured with cluster access
- **Python** 3.10+ (for local development)

### Required Services

- **PostgreSQL** 14+ (for persistent storage)
- **Redis** 7+ (for caching)

### API Keys

- OpenAI API key (optional, for GPT models)
- Anthropic API key (optional, for Claude models)

## Docker Deployment

### Quick Start with Docker Compose

1. **Clone repository**:
```bash
git clone https://github.com/yourusername/Autonomous-Report-Generator.git
cd Autonomous-Report-Generator
```

2. **Create environment file**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Set API keys** (in `.env`):
```env
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

4. **Start services**:
```bash
docker-compose up -d
```

5. **Verify deployment**:
```bash
# Check service status
docker-compose ps

# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f api
```

6. **Access services**:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Production Docker Setup

For production, use the production docker-compose file:

```bash
# Production compose file
docker-compose -f docker-compose.prod.yml up -d
```

Production configuration includes:
- Resource limits
- Restart policies
- Health checks
- Volume mounts for persistence
- Network isolation

### Building Custom Image

```bash
# Build image
docker build -t report-generator:1.0.0 .

# Tag for registry
docker tag report-generator:1.0.0 registry.example.com/report-generator:1.0.0

# Push to registry
docker push registry.example.com/report-generator:1.0.0
```

## Kubernetes Deployment

### Prerequisites

1. **Kubernetes cluster** running (GKE, EKS, AKS, or self-managed)
2. **kubectl** configured with cluster access
3. **Container registry** access

### Step 1: Create Namespace

```bash
kubectl create namespace report-generator
kubectl config set-context --current --namespace=report-generator
```

### Step 2: Create Secrets

```bash
# Copy template
cp deployment/kubernetes/secrets.yaml.template deployment/kubernetes/secrets.yaml

# Edit secrets.yaml with actual values
# Then apply
kubectl apply -f deployment/kubernetes/secrets.yaml
```

Or create from command line:

```bash
kubectl create secret generic report-generator-secrets \
  --from-literal=database-url='postgresql+asyncpg://user:password@postgres:5432/reportgen' \
  --from-literal=openai-api-key='sk-your-key' \
  --from-literal=anthropic-api-key='sk-ant-your-key'
```

### Step 3: Apply ConfigMap

```bash
kubectl apply -f deployment/kubernetes/configmap.yaml
```

### Step 4: Create Persistent Volumes

```bash
kubectl apply -f deployment/kubernetes/pvc.yaml
```

### Step 5: Deploy Application

```bash
kubectl apply -f deployment/kubernetes/deployment.yaml
```

### Step 6: Verify Deployment

```bash
# Check pods
kubectl get pods

# Check services
kubectl get services

# Check logs
kubectl logs -f deployment/report-generator-api

# Check health
kubectl get pods -l app=report-generator

# Port forward to test locally
kubectl port-forward svc/report-generator-api 8000:80
```

### Step 7: Access Application

```bash
# Get external IP
kubectl get svc report-generator-api

# Access via LoadBalancer IP
curl http://<EXTERNAL-IP>/health
```

## Environment Configuration

### Required Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Cache
REDIS_URL=redis://host:6379/0

# LLM API Keys
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# Application
LOG_LEVEL=INFO
CACHE_DIR=/app/data/cache
EXPORT_DIR=/app/data/exports
```

### Optional Variables

```env
# Research APIs
WEB_SEARCH_API_KEY=your-key
ACADEMIC_API_KEY=your-key

# Performance
MAX_WORKERS=4
CACHE_TTL=3600
MAX_CACHE_SIZE_MB=500

# Quality
QUALITY_THRESHOLD=75.0

# Security
JWT_SECRET=your-secret-key
ALLOWED_ORIGINS=https://your-domain.com
```

## Monitoring Setup

### Prometheus

Prometheus scrapes metrics from `/health/metrics` endpoint.

Configuration in `deployment/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'report-generator-api'
    metrics_path: '/health/metrics'
    static_configs:
      - targets: ['api:8000']
```

Access Prometheus: http://localhost:9090

### Grafana

1. **Access Grafana**: http://localhost:3000 (admin/admin)

2. **Add Prometheus data source**:
   - Configuration → Data Sources → Add data source
   - Select Prometheus
   - URL: http://prometheus:9090
   - Save & Test

3. **Import dashboards**:
   - Dashboards → Import
   - Upload from `deployment/grafana/dashboards/`

### Key Metrics to Monitor

- **Request Rate**: `rate(http_requests_total[5m])`
- **Error Rate**: `rate(http_errors_total[5m])`
- **Latency**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- **Cache Hit Rate**: `cache_hits / (cache_hits + cache_misses)`
- **Active Reports**: `reports_in_progress`

### Health Checks

Multiple health endpoints available:

- `/health` - Basic health check
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe
- `/health/status` - Detailed status
- `/health/metrics` - Prometheus metrics

## Security Considerations

### API Keys Management

**Never commit API keys to version control!**

Use one of:
- Environment variables
- Kubernetes Secrets
- Secret management services (AWS Secrets Manager, HashiCorp Vault, etc.)

### Network Security

1. **Use HTTPS** in production (configure reverse proxy)
2. **Configure CORS** appropriately:
```python
# In production, specify allowed origins
allow_origins=["https://your-domain.com"]
```

3. **Use firewall rules** to restrict access
4. **Enable rate limiting** to prevent abuse

### Database Security

1. Use strong passwords
2. Enable SSL/TLS connections
3. Restrict network access
4. Regular backups
5. Encryption at rest

### Container Security

1. Run as non-root user
2. Use minimal base images
3. Scan images for vulnerabilities
4. Keep dependencies updated

## Scaling

### Horizontal Pod Autoscaling (Kubernetes)

Already configured in `deployment.yaml`:

```yaml
minReplicas: 3
maxReplicas: 10
metrics:
  - type: Resource
    resource:
      name: cpu
      targetAverageUtilization: 70
```

Monitor scaling:
```bash
kubectl get hpa
```

### Database Scaling

For PostgreSQL:
- Use connection pooling
- Add read replicas for read-heavy workloads
- Consider managed services (RDS, Cloud SQL)

### Cache Scaling

For Redis:
- Use Redis Cluster for horizontal scaling
- Configure persistence (RDB/AOF)
- Consider Redis Sentinel for high availability

## Troubleshooting

### Common Issues

#### API Not Starting

```bash
# Check logs
docker-compose logs api

# Or in Kubernetes
kubectl logs -f deployment/report-generator-api

# Common causes:
# - Missing environment variables
# - Database connection failure
# - Port already in use
```

#### Database Connection Errors

```bash
# Test database connectivity
docker-compose exec api python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://user:pass@db:5432/reportgen')
print(engine.connect())
"

# Check database is running
docker-compose ps db
kubectl get pods -l component=database
```

#### High Memory Usage

```bash
# Check resource usage
docker stats

# Or in Kubernetes
kubectl top pods

# Solutions:
# - Increase memory limits
# - Reduce cache size
# - Enable file cache over memory cache
```

#### Slow Performance

```bash
# Check metrics
curl http://localhost:8000/health/metrics

# Enable debug logging
export LOG_LEVEL=DEBUG

# Check cache hit rate
# Should be > 50%

# Profile slow endpoints
# Use /health/status to check component health
```

### Logs

#### Docker Compose

```bash
# View all logs
docker-compose logs

# Follow specific service
docker-compose logs -f api

# View last 100 lines
docker-compose logs --tail=100 api
```

#### Kubernetes

```bash
# View pod logs
kubectl logs <pod-name>

# Follow logs
kubectl logs -f <pod-name>

# Previous container logs (after crash)
kubectl logs <pod-name> --previous

# Logs from all pods with label
kubectl logs -l app=report-generator --all-containers
```

### Debug Mode

Enable debug mode for detailed logs:

```env
LOG_LEVEL=DEBUG
```

Or in Kubernetes ConfigMap:
```yaml
data:
  log-level: "DEBUG"
```

## Backup and Recovery

### Database Backups

```bash
# Backup PostgreSQL
docker-compose exec db pg_dump -U reportgen reportgen > backup.sql

# Restore
docker-compose exec -T db psql -U reportgen reportgen < backup.sql
```

### Persistent Data

Important directories to backup:
- `/app/data/cache` - Cache files
- `/app/data/exports` - Exported reports
- `/app/logs` - Application logs

## Updating

### Docker

```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose up -d

# Remove old images
docker image prune
```

### Kubernetes

```bash
# Update image
kubectl set image deployment/report-generator-api \
  api=report-generator:1.1.0

# Or apply updated deployment
kubectl apply -f deployment/kubernetes/deployment.yaml

# Check rollout status
kubectl rollout status deployment/report-generator-api

# Rollback if needed
kubectl rollout undo deployment/report-generator-api
```

## Production Checklist

- [ ] Environment variables configured
- [ ] API keys set securely
- [ ] Database backups scheduled
- [ ] HTTPS/TLS configured
- [ ] CORS configured appropriately
- [ ] Resource limits set
- [ ] Health checks working
- [ ] Monitoring enabled
- [ ] Logging configured
- [ ] Alerts configured
- [ ] Documentation updated
- [ ] Performance tested
- [ ] Security scan completed

## Support

For deployment issues:
- Check logs first
- Review health endpoints
- Check GitHub Issues
- Contact support team

---

**Last Updated**: 2024
**Version**: 1.0.0
