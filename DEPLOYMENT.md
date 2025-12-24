# ApexWatch Deployment Guide

## 🚀 Production Deployment

This guide covers deploying ApexWatch to a production environment.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Docker & Docker Compose installed
- Domain name (optional, for HTTPS)
- At least 8GB RAM, 4 CPU cores
- 50GB+ storage

## Step-by-Step Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone and Configure

```bash
# Clone repository
git clone <your-repo-url>
cd ApexWatch

# Create environment file
cp .env.template .env

# Edit configuration
nano .env
```

### 3. Security Configuration

**CRITICAL: Change all default secrets!**

```bash
# Generate strong keys
openssl rand -hex 32  # For ACCESS_KEY
openssl rand -hex 32  # For JWT_SECRET_KEY

# Update .env with generated keys
nano .env
```

Set these in `.env`:
```bash
ACCESS_KEY=<generated-key-1>
JWT_SECRET_KEY=<generated-key-2>
ALCHEMY_API_KEY=<your-alchemy-key>
OPENAI_API_KEY=<your-openai-key>  # Optional
```

### 4. Database Security

Edit `docker-compose.yml` and update:

```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: <strong-password-here>

rabbitmq:
  environment:
    RABBITMQ_DEFAULT_PASS: <strong-password-here>
```

Update corresponding values in `.env`.

### 5. Change Default Admin Password

After first startup, connect to PostgreSQL:

```bash
docker exec -it apexwatch-postgres psql -U postgres -d apexwatch

-- Change admin password (use bcrypt hash)
UPDATE users
SET password_hash = crypt('your-new-password', gen_salt('bf'))
WHERE username = 'admin';

\q
```

### 6. Start Services

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 7. Initialize Ollama

```bash
# Pull LLM model
docker exec -it apexwatch-ollama ollama pull llama3

# Verify
docker exec -it apexwatch-ollama ollama list
```

### 8. Verify Deployment

```bash
# Test all health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Access dashboard
# Open: http://your-server-ip:8501
```

## 🔒 HTTPS Setup (Nginx Reverse Proxy)

### Install Nginx

```bash
sudo apt install nginx certbot python3-certbot-nginx -y
```

### Configure Nginx

Create `/etc/nginx/sites-available/apexwatch`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Dashboard
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Core API
    location /api/core/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Kibana
    location /kibana/ {
        proxy_pass http://localhost:5601/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable and get SSL:

```bash
sudo ln -s /etc/nginx/sites-available/apexwatch /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## 📊 Monitoring Setup

### 1. Set Up Log Rotation

Create `/etc/logrotate.d/apexwatch`:

```
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

### 2. Configure Alerts

Use Kibana to set up alerts:
1. Open http://your-domain.com/kibana
2. Go to Management → Alerts
3. Create alerts for:
   - High error rates
   - Queue size thresholds
   - Service downtime

### 3. Database Monitoring

```bash
# Monitor PostgreSQL
docker exec apexwatch-postgres pg_stat_activity

# Monitor ClickHouse
docker exec apexwatch-clickhouse clickhouse-client --query "SELECT * FROM system.metrics"

# Monitor Redis
docker exec apexwatch-redis redis-cli INFO
```

## 🔄 Backup Strategy

### Automated Backups

Create `/opt/apexwatch/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/apexwatch/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec apexwatch-postgres pg_dump -U postgres apexwatch | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup ClickHouse (export to CSV)
docker exec apexwatch-clickhouse clickhouse-client --query "SELECT * FROM llm_thoughts FORMAT CSV" | gzip > $BACKUP_DIR/clickhouse_thoughts_$DATE.csv.gz

# Backup Redis
docker exec apexwatch-redis redis-cli SAVE
docker cp apexwatch-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Make executable and add to cron:

```bash
chmod +x /opt/apexwatch/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
0 2 * * * /opt/apexwatch/backup.sh >> /var/log/apexwatch-backup.log 2>&1
```

## 🔧 Performance Tuning

### Docker Resource Limits

Edit `docker-compose.yml` to add resource limits:

```yaml
services:
  core:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### PostgreSQL Tuning

Connect to PostgreSQL and optimize:

```sql
-- Increase shared buffers (25% of RAM)
ALTER SYSTEM SET shared_buffers = '2GB';

-- Increase work memory
ALTER SYSTEM SET work_mem = '50MB';

-- Reload configuration
SELECT pg_reload_conf();
```

### Redis Tuning

Edit Redis configuration:

```bash
# Increase maxmemory
docker exec apexwatch-redis redis-cli CONFIG SET maxmemory 2gb
docker exec apexwatch-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### ClickHouse Tuning

```sql
-- Optimize for queries
SET max_memory_usage = 10000000000;
SET max_bytes_before_external_sort = 20000000000;
```

## 🚨 Disaster Recovery

### Service Failure

```bash
# Restart specific service
docker-compose restart core

# Restart all services
docker-compose restart

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Database Corruption

```bash
# Restore PostgreSQL
gunzip -c /opt/apexwatch/backups/postgres_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i apexwatch-postgres psql -U postgres -d apexwatch

# Restore Redis
docker cp /opt/apexwatch/backups/redis_YYYYMMDD_HHMMSS.rdb apexwatch-redis:/data/dump.rdb
docker-compose restart redis
```

### Complete System Restore

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: DATA LOSS)
docker volume rm $(docker volume ls -q | grep apexwatch)

# Restore from backups
# 1. Start services
docker-compose up -d postgres redis clickhouse

# 2. Wait for databases to be ready
sleep 30

# 3. Restore PostgreSQL
gunzip -c /opt/apexwatch/backups/postgres_latest.sql.gz | \
  docker exec -i apexwatch-postgres psql -U postgres -d apexwatch

# 4. Restore Redis
docker cp /opt/apexwatch/backups/redis_latest.rdb apexwatch-redis:/data/dump.rdb
docker-compose restart redis

# 5. Start all services
docker-compose up -d
```

## 🔍 Health Checks

Create `/opt/apexwatch/healthcheck.sh`:

```bash
#!/bin/bash

SERVICES=("core:8000" "wallet-monitor:8001" "exchange-monitor:8002" "news-monitor:8003")
ALERT_EMAIL="admin@yourdomain.com"

for SERVICE in "${SERVICES[@]}"; do
    NAME="${SERVICE%%:*}"
    PORT="${SERVICE##*:}"

    if ! curl -f http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "Service $NAME is DOWN!"
        # Send alert (configure mail server first)
        # echo "Service $NAME is down" | mail -s "ApexWatch Alert" $ALERT_EMAIL

        # Auto-restart
        docker-compose restart $NAME
    fi
done
```

Add to cron (every 5 minutes):

```bash
*/5 * * * * /opt/apexwatch/healthcheck.sh >> /var/log/apexwatch-health.log 2>&1
```

## 📈 Scaling

### Horizontal Scaling

For high-load scenarios:

1. **Deploy Multiple Instances**
```bash
# Scale wallet monitor
docker-compose up -d --scale wallet-monitor=3
```

2. **Use Load Balancer**
Set up Nginx or HAProxy to distribute load

3. **Separate Database Servers**
Move PostgreSQL, Redis, and ClickHouse to dedicated servers

### Vertical Scaling

Increase Docker resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

## 🛡️ Security Best Practices

1. **Firewall Configuration**
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

2. **Network Isolation**
Use Docker networks to isolate services

3. **Regular Updates**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d
```

4. **Access Control**
- Use VPN for administrative access
- Implement IP whitelisting
- Use strong passwords
- Enable 2FA where possible

## 📞 Support

For production issues:
1. Check service logs: `docker-compose logs [service]`
2. Review Kibana for errors
3. Check database connections
4. Verify API keys are valid

---

**Remember:** Always test deployment procedures in a staging environment first!
