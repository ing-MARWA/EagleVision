# 📚 PIZZA-MONITOR: Complete Documentation Index

## Quick Navigation

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Documentation Structure](#documentation-structure)
- [API Reference](#api-reference)
- [Deployment Guide](#deployment-guide)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Overview

**PIZZA-MONITOR** is a production-ready microservices architecture for real-time pizza scooper violation detection using computer vision. The system processes video streams, detects violations, and provides a REST API with a web dashboard for monitoring.

### System Capabilities

- **Real-time Processing**: 5+ frames per second (configurable)
- **Scalable**: Horizontally scale detection services
- **Persistent**: PostgreSQL storage of all violations
- **Resilient**: Built-in retry mechanisms and health checks
- **Observable**: Comprehensive logging and API endpoints

---

## Getting Started

### 1. Quick Start (5 minutes)

```bash
# Clone and setup
git clone <repo>
cd pizza-monitor

# Ensure YOLO model exists
mkdir -p models
# Copy yolo12m-v2.pt to models/ directory

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Verify Installation

```bash
# Check all services are healthy
docker-compose ps

# View logs
docker-compose logs -f

# Test API
curl http://localhost:5000/api/health
```

### 3. Process Videos

```bash
# Place videos in ./videos directory
cp your_video.mp4 ./videos/

# Frame reader automatically detects and processes
docker-compose logs frame_reader

# Check results via API
curl http://localhost:5000/api/violations-list
```

### 4. View Dashboard

```
Open browser: http://localhost:3000
```

---

## Documentation Structure

### Core Documentation

#### 1. **README.md** ✅ (Start Here)
   - Project overview and features
   - Installation instructions
   - Configuration guide
   - API endpoint documentation
   - Troubleshooting common issues
   - Technology stack
   
   **Best for**: Getting up and running quickly

#### 2. **ARCHITECTURE.md** ✅ (Deep Dive)
   - Microservices design principles
   - Detailed service descriptions
   - Communication patterns
   - Data flow and transformations
   - Database design
   - Scalability strategies
   - Security considerations
   
   **Best for**: Understanding system design

#### 3. **SYSTEM_DIAGRAMS.md** ✅ (Visual Reference)
   - High-level architecture diagram
   - Message flow visualization
   - Data structure representations
   - Service dependencies
   - Container networking
   - Video processing pipeline
   - Error handling flows
   - Performance monitoring
   
   **Best for**: Visual learners, presentations

#### 4. **API_REFERENCE.md** (Optional)
   - Complete REST API documentation
   - Request/response examples
   - Query parameters
   - Error codes and messages
   - Rate limiting (if applicable)
   
   **Create this when**: Building client applications

## File Organization

```
PIZZA-MONITOR/
├── README.md                          ← START HERE
├── ARCHITECTURE.md                    ← System Design
├── SYSTEM_DIAGRAMS.md                 ← Visual Guides
├── DOCUMENTATION.md                   ← Documentry
│
├── services/
│   ├── db/
│   │   └── init.sql                   ← Database Schema
│   ├── detection/
│   │   ├── app.py                     ← Core Logic
│   │   ├── custom_modules.py          ← YOLO12m Models
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── test_docker.py
│   ├── frame_reader/
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── streaming/
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/
│       ├── public/index.html
│       ├── Dockerfile
│       └── nginx.conf
│
├── models/
│   └── yolo12m-v2.pt                  ← YOLO Model (500MB)
│
├── videos/                            ← Input Videos
│   ├── Sah w b3dha ghalt.mp4 
│   ├── Sah w b3dha ghalt (2).mp4 
│   └── Sah w b3dha ghalt (3).mp4 
│
└── docker-compose.yaml                ← Orchestration
```

---

## API Reference

### Base URL
```
http://localhost:5000/api
```

### Authentication
Currently none (add JWT in production)

### Endpoints Summary

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|----------------|
| `/health` | GET | Service health | <1ms |
| `/violations/<video>` | GET | Get violations for video | 10-50ms |
| `/violations-list` | GET | List all videos | 50-100ms |
| `/latest-detection/<video>` | GET | Latest detection | <1ms (cache) |
| `/video-summary/<video>` | GET | Violation summary | 20-100ms |
| `/violation-details/<id>` | GET | Specific violation | 10-20ms |
| `/statistics` | GET | Overall stats | 50-100ms |

### Detailed Endpoint Documentation

#### GET /api/health
Health check endpoint

**Request:**
```bash
curl http://localhost:5000/api/health
```

**Response (200):**
```json
{
  "status": "healthy",
  "service": "streaming"
}
```

#### GET /api/violations/<video_name>
Get all violations for a specific video

**Request:**
```bash
curl http://localhost:5000/api/violations/video_1?limit=100
```

**Response (200):**
```json
{
  "video_name": "video_1",
  "total_violations": 5,
  "violations": [
    {
      "id": 1,
      "video_name": "video_1",
      "frame_id": 150,
      "timestamp": 5000,
      "violation_type": "hand_no_scooper",
      "bounding_boxes": {
        "hand": [100, 150, 200, 300],
        "pizza": [120, 160, 280, 320]
      },
      "detected_objects": ["hand", "pizza", "scooper"],
      "confidence": [0.95, 0.92, 0.87],
      "created_at": "2025-12-26T10:30:45.123Z"
    }
  ]
}
```

**Response (404):**
```json
{
  "error": "Video not found"
}
```

#### GET /api/violations-list
Get list of all videos with violations

**Request:**
```bash
curl http://localhost:5000/api/violations-list
```

**Response (200):**
```json
{
  "videos": [
    {
      "video_name": "video_1",
      "violation_count": 5
    },
    {
      "video_name": "video_2",
      "violation_count": 3
    }
  ],
  "total_videos_with_violations": 2
}
```

#### GET /api/latest-detection/<video_name>
Get latest detection for a video (from cache)

**Request:**
```bash
curl http://localhost:5000/api/latest-detection/video_1
```

**Response (200):**
```json
{
  "video_name": "video_1",
  "frame_id": 250,
  "timestamp": "2025-12-26T10:30:45.123Z",
  "detections": [
    {
      "class": "hand",
      "confidence": 0.95,
      "bbox": [100, 150, 200, 300]
    },
    {
      "class": "pizza",
      "confidence": 0.92,
      "bbox": [120, 160, 280, 320]
    },
    {
      "class": "scooper",
      "confidence": 0.87,
      "bbox": [250, 140, 300, 220]
    }
  ],
  "violation_count": 0
}
```

#### GET /api/statistics
Get system-wide statistics

**Request:**
```bash
curl http://localhost:5000/api/statistics
```

**Response (200):**
```json
{
  "total_violations": 12,
  "videos_with_violations": 2,
  "violation_types": [
    {
      "violation_type": "hand_no_scooper",
      "count": 12
    }
  ]
}
```

---

## Deployment Guide

### Development Environment

```bash
# Start all services locally
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Staging Environment (Single Server)

```bash
# Build images
docker-compose -f docker-compose.yml build

# Use production docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Backup database
docker exec pizza_db pg_dump -U pizza_user pizza_violations > backup.sql
```

### Production Deployment

**Kubernetes (Recommended)**

```yaml
# kubernetes/detection-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pizza-detection
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pizza-detection
  template:
    metadata:
      labels:
        app: pizza-detection
    spec:
      containers:
      - name: detection
        image: registry.company.com/pizza-detection:v1.0
        resources:
          requests:
            cpu: 2
            memory: 4Gi
          limits:
            cpu: 4
            memory: 8Gi
        env:
        - name: MODEL_PATH
          value: /models/yolo12m-v2.pt
        volumeMounts:
        - name: models
          mountPath: /models
          readOnly: true
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: yolo-model-pvc
```

---

## Troubleshooting

### Common Issues

#### 1. Detection Service Crashes on Startup

**Symptoms:**
```
pizza_detection | Error: Model file not found at /models/yolo12m-v2.pt
pizza_detection exited with code 1
```

**Solution:**
```bash
# Check if model exists
ls -lh models/yolo12m-v2.pt

# Copy model to correct location
cp yolo12m-v2.pt models/

# Verify
docker-compose ps

# Restart service
docker-compose up -d detection
```

#### 2. No Violations Detected

**Symptoms:**
```json
{
  "total_violations": 0
}
```

**Checklist:**
1. Check ROI configuration in `services/detection/app.py`
2. Verify confidence thresholds (default: 0.3)
3. Check if videos are being read: `docker-compose logs frame_reader`
4. Monitor detection logs: `docker-compose logs detection | grep "class"`
5. Verify frames are being published to RabbitMQ

**Debug Steps:**
```bash
# 1. Check RabbitMQ queue
docker exec pizza_rabbitmq rabbitmqctl list_queues name messages consumers

# 2. View detection logs
docker-compose logs detection --tail=100

# 3. Test model loading
docker exec pizza_detection python test_docker.py

# 4. Check frame reader
docker-compose logs frame_reader
```

#### 3. Database Connection Errors

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check database status
docker-compose ps db

# View database logs
docker-compose logs db

# Wait for database to be ready (health check)
docker-compose logs db | grep "ready to accept"

# Reinitialize database
docker-compose down
docker volume rm pizza_db_data
docker-compose up -d db
```

#### 4. High Memory Usage

**Symptoms:**
```bash
docker stats
# pizza_detection using 7GB+ memory
```

**Solution:**
```python
# services/detection/app.py
# Limit batch processing, use streaming approach

# Or scale horizontally
docker-compose scale detection=3
```

#### 5. Slow API Response Times

**Symptoms:**
```bash
curl -w "@curl-format.txt" http://localhost:5000/api/violations/video_1
# time_total: 2000ms
```

**Solution:**
```bash
# Check database performance
docker exec pizza_db psql -U pizza_user -d pizza_violations \
  -c "SELECT * FROM violations LIMIT 1 OFFSET 100000"

# Create additional indices if needed
docker exec pizza_db psql -U pizza_user -d pizza_violations \
  -c "CREATE INDEX idx_violations_created_at ON violations(created_at)"

# Check API container CPU/memory
docker stats pizza_streaming
```

---

## Advanced Topics

### Custom Model Deployment

To use a different YOLO model:

1. **Obtain model file** (e.g., `yolo12l-custom.pt`)

2. **Place in models/ directory**
   ```bash
   cp yolo12l-custom.pt models/
   ```

3. **Update environment variable**
   ```yaml
   # docker-compose.yaml
   environment:
     MODEL_PATH: /models/yolo12m-v2.pt
   ```

4. **Verify custom modules** (if using custom YOLO modules)
   ```python
   # services/detection/custom_modules.py
   # Register any custom modules needed
   ```

### ROI Configuration

Adjust regions of interest for violation detection:

```python
# services/detection/app.py
ROIS = [
    (x1, y1, x2, y2),  # Region 1 (normalized coordinates)
    (x1, y1, x2, y2),  # Region 2
]
```

### Confidence Threshold Tuning

```python
# services/detection/app.py
results = self.model(frame, conf=0.3, iou=0.45)

# Lower conf (e.g., 0.2): More detections, more false positives
# Higher conf (e.g., 0.5): Fewer detections, fewer false positives
```

### Multi-GPU Deployment

For GPU acceleration with multiple GPUs:

```dockerfile
# services/detection/Dockerfile
FROM nvidia/cuda:12.1-runtime-ubuntu22.04

# Install CUDA-enabled PyTorch
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

```python
# services/detection/app.py
# Auto-detect and use GPU if available
device = 'cuda' if torch.cuda.is_available() else 'cpu'
self.model = YOLO(model_path).to(device)
```

### Database Backup & Recovery

```bash
# Backup
docker exec pizza_db pg_dump -U pizza_user pizza_violations > backup.sql

# Backup to compressed format
docker exec pizza_db pg_dump -U pizza_user pizza_violations | gzip > backup.sql.gz

# Restore from backup
docker exec -i pizza_db psql -U pizza_user pizza_violations < backup.sql

# Restore from compressed
gunzip < backup.sql.gz | docker exec -i pizza_db psql -U pizza_user pizza_violations
```

### Log Aggregation

For production monitoring:

```yaml
# docker-compose.yaml (add ELK stack)
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
  environment:
    discovery.type: single-node

logstash:
  image: docker.elastic.co/logstash/logstash:8.0.0
  
kibana:
  image: docker.elastic.co/kibana/kibana:8.0.0
```

---

## Performance Tuning

### Frame Processing Rate

```yaml
# services/frame_reader/app.py
max_fps = 5  # Reduce for fewer frames, increase for more processing

# At 5 FPS: ~100 frames/min per video
# At 10 FPS: ~200 frames/min per video
# At 30 FPS: ~600 frames/min per video (intensive)
```

### JPEG Quality

```python
# services/frame_reader/app.py
_, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

# 80: Good balance of size and quality
# 90: Higher quality, larger file
# 60: Lower quality, smaller file
```

### Database Connection Pooling

```python
# services/streaming/app.py
from psycopg2.pool import SimpleConnectionPool

pool = SimpleConnectionPool(
    5,   # Min connections
    20,  # Max connections
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)
```

---

## Support & Resources

### Useful Commands

```bash
# View all containers
docker-compose ps

# View logs for specific service
docker-compose logs detection

# Real-time logs
docker-compose logs -f

# Access database
docker exec -it pizza_db psql -U pizza_user pizza_violations

# Access RabbitMQ management console
http://localhost:15672
# Username: guest
# Password: guest

# Monitor resources
docker stats

# Rebuild a specific service
docker-compose build detection
docker-compose up -d detection
```

### Documentation Links

- **OpenCV**: https://docs.opencv.org/
- **YOLOv8**: https://docs.ultralytics.com/
- **PyTorch**: https://pytorch.org/docs/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **RabbitMQ**: https://www.rabbitmq.com/documentation.html
- **Flask**: https://flask.palletsprojects.com/
- **Docker**: https://docs.docker.com/
- **Docker Compose**: https://docs.docker.com/compose/

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | December 2025 | Initial release |

---

## License

This project is provided as-is for educational and commercial use.

---

**Last Updated**: December 2025
**Maintained By**: Development Team
**Contact**: support@CV.com
