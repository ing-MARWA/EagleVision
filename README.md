# EagleVision

# 🍕 PIZZA-MONITOR: Real-Time Pizza Scooper Violation Detection

A microservices-based computer vision system that detects pizza handling violations in real-time video streams. The system uses advanced YOLO12m deep learning models to identify when hands touch pizza without using a scooper tool.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [API Documentation](#api-documentation)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)

## 🎯 Overview

PIZZA-MONITOR is a production-ready microservices architecture designed to:

1. **Read video files** from a designated directory
2. **Extract frames** and publish them to a message queue
3. **Detect objects** (hands, pizza, scooper) using YOLO12m
4. **Identify violations** when hands touch pizza without a scooper
5. **Store violations** in a PostgreSQL database
6. **Stream results** via REST API
7. **Visualize findings** through a web frontend

### Key Violation Logic
A violation is detected when:
- A **hand** is detected in a Region of Interest (ROI)
- The hand is **NOT holding a scooper**
- The hand is **overlapping with pizza**

## ✨ Features

- **Real-time Detection**: Process video frames with sub-second latency
- **Scalable Architecture**: Horizontally scalable detection services
- **Message Queue Integration**: Robust inter-service communication via RabbitMQ
- **Database Persistence**: Complete violation history with metadata
- **REST API**: Full-featured API for querying violations
- **Web Dashboard**: Live monitoring interface
- **Custom YOLO Modules**: Support for latest YOLO12m architecture
- **Docker Containerization**: Complete container orchestration
- **Health Checks**: Built-in service health monitoring
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

## 🏗️ Architecture

The system follows a **microservices architecture** with the following components:

```
┌─────────────────┐
│  Frame Reader   │ (Video Input)
└────────┬────────┘
         │
         │ Frames (RabbitMQ)
         ↓
┌──────────────────────┐
│  Detection Service   │ (YOLO12m)
└────────┬─────────────┘
         │
         │ Results (RabbitMQ)
         ↓
┌─────────────────────┐
│  Streaming Service  │ (REST API)
└────────┬────────────┘
         │
         ├─→ PostgreSQL (Storage)
         │
         ↓
┌─────────────────┐
│     Frontend    │ (Web UI)
└─────────────────┘
```

For detailed architecture information, see [ARCHITECTURE.md](./ARCHITECTURE.md)

## 📦 Prerequisites

- **Docker**: v20.10+
- **Docker Compose**: v1.29+
- **System Resources**:
  - CPU: 4+ cores recommended
  - RAM: 8GB minimum, 16GB recommended
  - Storage: 30GB+ for models and database
- **NVIDIA GPU** (optional): For accelerated inference with CUDA

## 🚀 Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/pizza-monitor.git
cd pizza-monitor
```

### 2. Project Structure
```
pizza-monitor/
├── services/
│   ├── db/
│   │   └── init.sql                 # Database schema
│   ├── detection/
│   │   ├── app.py                   # Violation detector
│   │   ├── custom_modules.py        # YOLO12m custom modules
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── test_docker.py          # Docker verification
│   ├── frame_reader/
│   │   ├── app.py                   # Video frame extractor
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── streaming/
│   │   ├── app.py                   # REST API server
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/
│       ├── public/
│       │   └── index.html           # Web dashboard
│       ├── Dockerfile
│       └── nginx.conf
├── models/
│   └── yolo12m-v2.pt               # YOLO12m model
├── videos/
│   ├── 1.mp4
│   ├── 2.mp4
│   └── 3.mp4
└── docker-compose.yaml
```

### 3. Download YOLO Model

```bash
mkdir -p models
# Download yolo12m-v2.pt to models/ directory
# (~500MB file)
cd models
wget https://path-to-model/yolo12m-v2.pt  # or use your model source
cd ..
```

### 4. Prepare Videos

```bash
mkdir -p videos
# Copy your video files to videos/ directory
cp /path/to/your/videos/*.mp4 videos/
```

### 5. Build and Start Services

```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 6. Verify Services are Running

```bash
# Check container status
docker-compose ps

# Should output:
# NAME              STATUS
# pizza_rabbitmq    Up (healthy)
# pizza_db          Up (healthy)
# pizza_detection   Up
# pizza_streaming   Up
# pizza_frontend    Up
# pizza_frame_reader Up
```

## ⚙️ Configuration

### Environment Variables

Create or modify environment variables in `docker-compose.yaml`:

```yaml
environment:
  # RabbitMQ Configuration
  RABBITMQ_HOST: rabbitmq
  RABBITMQ_PORT: 5672

  # Database Configuration
  DB_HOST: db
  DB_PORT: 5432
  DB_USER: pizza_user
  DB_PASSWORD: pizza_pass
  DB_NAME: pizza_violations

  # Model Configuration
  MODEL_PATH: /models/yolo12m-v2.pt
  
  # Detection Parameters
  CONF_THRESHOLD: 0.3    # Confidence threshold (0.0-1.0)
  IOU_THRESHOLD: 0.45    # IoU threshold for NMS
```

### ROI Configuration

Edit ROI zones in `services/detection/app.py`:

```python
ROIS = [
    (48, 34, 55, 36),  # [x1, y1, x2, y2] in normalized coordinates
    # Add more ROIs as needed
]
```

### Database Connection

PostgreSQL credentials are set in `docker-compose.yaml`. To change:

```yaml
db:
  environment:
    POSTGRES_USER: your_user
    POSTGRES_PASSWORD: your_password
    POSTGRES_DB: your_database
```

## 🎬 Running the System

### Start All Services
```bash
docker-compose up -d
```

### Monitor Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f detection
docker-compose logs -f streaming
docker-compose logs -f frame_reader
```

### Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | Web Dashboard |
| Streaming API | http://localhost:5000 | REST API |
| RabbitMQ UI | http://localhost:15672 | Message Queue Management |
| PostgreSQL | localhost:5432 | Database Access |

### Process Videos

Videos in the `./videos` directory are automatically processed by the frame_reader service. Violations are:
1. Detected in real-time
2. Stored in PostgreSQL
3. Available via REST API
4. Displayed in the web dashboard

### Stop Services
```bash
docker-compose down

# Stop and remove volumes (warning: deletes data)
docker-compose down -v
```

## 🔌 API Documentation

### Get All Violations by Video

```http
GET /api/violations/<video_name>
```

**Response:**
```json
{
  "video_name": "1",
  "total_violations": 5,
  "violations": [
    {
      "id": 1,
      "video_name": "1",
      "frame_id": 150,
      "timestamp": 5000,
      "violation_type": "hand_no_scooper",
      "bounding_boxes": [...],
      "detected_objects": ["hand", "pizza"],
      "created_at": "2024-01-15T10:30:45.123Z"
    }
  ]
}
```

### Get All Videos with Violations

```http
GET /api/violations-list
```

**Response:**
```json
{
  "videos": [
    {"video_name": "1", "violation_count": 5},
    {"video_name": "2", "violation_count": 3}
  ],
  "total_videos_with_violations": 2
}
```

### Get Latest Detection

```http
GET /api/latest-detection/<video_name>
```

**Response:**
```json
{
  "video_name": "1",
  "frame_id": 250,
  "timestamp": "2024-01-15T10:30:45Z",
  "detections": [
    {
      "class": "hand",
      "confidence": 0.95,
      "bbox": [100, 150, 200, 300]
    }
  ],
  "violation_count": 0
}
```

### Get Video Summary

```http
GET /api/video-summary/<video_name>
```

### Get Statistics

```http
GET /api/statistics
```

**Response:**
```json
{
  "total_violations": 12,
  "videos_with_violations": 2,
  "violation_types": [
    {"violation_type": "hand_no_scooper", "count": 12}
  ]
}
```

### Health Check

```http
GET /api/health
```

## 🔍 Monitoring & Troubleshooting

### Check Service Health

```bash
# All services
docker-compose ps

# Specific service logs
docker-compose logs detection --tail=100

# Real-time log streaming
docker-compose logs -f streaming
```

### Common Issues

#### Issue: Detection service crashes on startup
**Solution**: Verify YOLO model file exists and is readable
```bash
ls -lh models/yolo12m-v2.pt
docker-compose logs detection
```

#### Issue: Database connection errors
**Solution**: Wait for PostgreSQL to be healthy
```bash
docker-compose logs db
# Check if container is running
docker-compose ps db
```

#### Issue: RabbitMQ connection timeouts
**Solution**: Verify RabbitMQ is healthy
```bash
docker-compose logs rabbitmq
# Check connectivity
docker exec pizza_detection ping rabbitmq
```

#### Issue: No violations detected
**Solution**: 
1. Check ROI configuration
2. Verify detection confidence thresholds
3. Review detection logs for object classes found
4. Ensure videos are being read: `docker-compose logs frame_reader`

### Database Queries

Access PostgreSQL directly:
```bash
docker exec -it pizza_db psql -U pizza_user -d pizza_violations

# View all violations
SELECT * FROM violations;

# Count violations per video
SELECT video_name, COUNT(*) FROM violations GROUP BY video_name;

# Get violation timeline
SELECT timestamp, video_name, violation_type FROM violations ORDER BY timestamp;
```

### Performance Monitoring

Monitor resource usage:
```bash
docker stats

# Watch CPU/Memory per service
docker stats --no-stream
```

## 📁 Project Structure Details

### Detection Service (`services/detection/`)
- **app.py**: Main violation detection logic
  - ROI checking
  - Hand + Pizza + Scooper intersection logic
  - Database persistence
- **custom_modules.py**: YOLO12m neural network modules
  - A2C2f (Attention block)
  - C3k2 (Bottleneck variant)
  - Custom registration system

### Frame Reader Service (`services/frame_reader/`)
- **app.py**: Video processing
  - Frame extraction
  - JPEG encoding
  - RabbitMQ publishing

### Streaming Service (`services/streaming/`)
- **app.py**: REST API endpoints
  - Violation queries
  - Real-time detection streaming
  - Statistics aggregation

### Database (`services/db/`)
- **init.sql**: PostgreSQL schema
  - Violations table with indices
  - JSON fields for flexible data storage

### Frontend (`services/frontend/`)
- **index.html**: Live monitoring dashboard
- **nginx.conf**: Reverse proxy configuration

## 🛠️ Technologies Used

| Component | Technology | Version |
|-----------|-----------|---------|
| ML Model | YOLOv12m | Custom v2 |
| Deep Learning | PyTorch | 2.9.0+ |
| Message Queue | RabbitMQ | 3.12 |
| Database | PostgreSQL | 15 |
| API Framework | Flask | 3.0.0 |
| Web Server | Nginx | Latest |
| Container | Docker | 20.10+ |
| Orchestration | Docker Compose | 1.29+ |
| Video Processing | OpenCV | 4.8.0+ |
| Language | Python | 3.10 |

## 📊 Performance Metrics

### Expected Performance

| Metric | Value |
|--------|-------|
| Video Processing Rate | 5-30 FPS (configurable) |
| Detection Latency | 50-200ms per frame |
| Memory Usage | ~3GB per detection service |
| Database Write Throughput | 100+ violations/second |
| API Response Time | <100ms |

### Scalability

- **Horizontal Scaling**: Deploy multiple detection containers with load balancing
- **Vertical Scaling**: Increase CPU/GPU and RAM for faster inference
- **Database**: PostgreSQL can handle millions of violation records

## 🔐 Security Notes

- Change default RabbitMQ credentials in production
- Use strong database passwords
- Implement API authentication
- Use HTTPS/TLS for frontend
- Restrict database access to trusted networks

## 📝 Logging

All services output structured logs:

```
2024-01-15 10:30:45,123 - detection - INFO - ⚠️ Violation detected in video_1, frame 150
2024-01-15 10:30:46,456 - streaming - INFO - 📊 Fetched 5 violations for video_1
2024-01-15 10:30:47,789 - frame_reader - INFO - 📤 Published frame 200 from video_1
```

## 🤝 Contributing

1. Follow PEP 8 for Python code
2. Test Docker images locally before pushing
3. Update documentation for any configuration changes
4. Add logging for new features

## 📄 License

This project is provided as-is for educational and commercial use.

## 🆘 Support

For issues and questions:
1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Review service logs: `docker-compose logs <service_name>`
3. Verify configuration in `docker-compose.yaml`
4. Check database schema: `services/db/init.sql`

---

**Last Updated**: January 2024
**Version**: 1.0.0
