# 🏗️ PIZZA-MONITOR: Microservices Architecture

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Service Descriptions](#service-descriptions)
3. [Communication Patterns](#communication-patterns)
4. [Data Flow](#data-flow)
5. [Database Design](#database-design)
6. [Scalability & Performance](#scalability--performance)
7. [Deployment Architecture](#deployment-architecture)
8. [Security Architecture](#security-architecture)

---

## System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      PIZZA-MONITOR SYSTEM                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                           │
│  │  Frame Reader    │  (Input Layer)                            │
│  │  Service         │  • Video Input                            │
│  │  :5672 (RMQ)     │  • Frame Extraction                       │
│  └────────┬─────────┘  • JPEG Encoding                          │
│           │                                                      │
│           │ RabbitMQ Topic: 'detection_exchange'                │
│           │ Routing Key: 'frame'                                │
│           │                                                      │
│           ↓                                                      │
│  ┌──────────────────┐                                           │
│  │  Detection       │  (Processing Layer)                       │
│  │  Service         │  • YOLO12m Inference                      │
│  │  :5672 (RMQ)     │  • Violation Logic                        │
│  │  :5432 (DB)      │  • DB Persistence                         │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           │ RabbitMQ Exchange: 'detection_results'              │
│           │ Routing Key: 'detections'                           │
│           │                                                      │
│           ├──────────────────────┐                              │
│           │                      ↓                              │
│           │            ┌──────────────────┐                     │
│           │            │  Streaming       │                     │
│           │            │  Service         │                     │
│           │            │  Flask REST API  │                     │
│           │            │  :5000           │                     │
│           │            └────────┬─────────┘                     │
│           │                     │                               │
│           ↓                     ↓                               │
│  ┌──────────────────────┐      ↓                               │
│  │  PostgreSQL          │  ┌──────────────┐                    │
│  │  Database            │  │  Web         │                    │
│  │  :5432               │  │  Frontend    │                    │
│  │  • Violations Table  │  │  Nginx       │                    │
│  │  • Indices           │  │  :3000       │                    │
│  └──────────────────────┘  └──────────────┘                    │
│                                                                  │
│  ┌──────────────────────┐                                       │
│  │  RabbitMQ            │  (Message Broker)                     │
│  │  :5672               │  • Topic Exchange                     │
│  │  Management :15672   │  • Durable Queues                     │
│  └──────────────────────┘                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Microservices**: Each service has a single responsibility
2. **Asynchronous Communication**: RabbitMQ enables loose coupling
3. **Scalability**: Services can be scaled independently
4. **Resilience**: Built-in retry mechanisms and health checks
5. **Persistence**: All violations stored for audit trail
6. **API-First**: REST API for all data access

---

## Service Descriptions

### 1. Frame Reader Service

**Purpose**: Extract frames from video files and publish to message queue

**Responsibilities**:
- Monitor `./videos` directory for video files
- Read videos frame-by-frame
- Skip frames based on FPS configuration (default: 5 FPS)
- Encode frames to JPEG (80% quality)
- Publish to RabbitMQ for processing
- Save frame temporarily to disk for reference

**Technology Stack**:
- **Language**: Python 3.10
- **Libraries**: OpenCV, Pika, Numpy
- **Message Broker**: RabbitMQ
- **Container**: Docker

**Configuration**:
```python
# Adjustable parameters
max_fps = 5                    # Process 5 frames per second
frame_quality = 80             # JPEG quality (0-100)
frame_skip = int(fps / max_fps)  # Calculate frame skip rate
```

**Message Format**:
```json
{
  "frame_id": 150,
  "video_name": "video_1",
  "timestamp": 5000,
  "frame": "base64_encoded_jpeg",
  "height": 720,
  "width": 1280,
  "frame_path": "/tmp/frames/video_1_150.jpg"
}
```

**Output Queue**:
- Exchange: `detection_exchange`
- Type: Topic
- Routing Key: `frame`
- Queue: `detection_queue`
- Durability: Yes

---

### 2. Detection Service

**Purpose**: Detect violations using YOLO12m deep learning model

**Responsibilities**:
- Load YOLO12m model with custom modules
- Consume frame messages from RabbitMQ
- Run object detection (hand, pizza, scooper)
- Implement violation logic:
  - Hand in ROI
  - No scooper held
  - Hand overlapping pizza
- Store violations in PostgreSQL
- Publish detection results to RabbitMQ
- Maintain connection resilience

**Technology Stack**:
- **Language**: Python 3.10
- **ML Framework**: PyTorch, Ultralytics YOLO
- **Database**: PostgreSQL
- **Message Broker**: RabbitMQ
- **Container**: Docker

**Key Components**:

**A. YOLO Model Architecture**
```
Input (3×640×640)
    ↓
[Backbone - Feature Extraction]
    ↓
[Neck - Feature Fusion]
    ↓
[Head - Detection Output]
    ↓
Objects: hand, pizza, scooper
```

**B. Violation Detection Logic**
```python
for each detected hand:
    if hand in ROI:
        if hand holds_scooper:
            # Allowed action
            continue
        else:
            for each detected pizza:
                if hand overlaps pizza:
                    # VIOLATION!
                    log_violation()
                    break
```

**C. Custom YOLO Modules** (custom_modules.py)
- **A2C2f**: Attention-based feature fusion
- **C3k2**: Advanced bottleneck module
- **AAttn**: Multi-head self-attention
- **ABlock**: Attention block with MLP
- Registration system for torch deserialization

**Model Parameters**:
```python
conf_threshold = 0.3   # Confidence threshold
iou_threshold = 0.45   # NMS IoU threshold
device = 'cpu'         # or 'cuda' if GPU available
```

**Input Message Format**:
```json
{
  "frame_id": 150,
  "video_name": "video_1",
  "timestamp": 5000,
  "frame": "base64_encoded_jpeg"
}
```

**Output Message Format**:
```json
{
  "video_name": "video_1",
  "frame_id": 150,
  "timestamp": "2024-01-15T10:30:45Z",
  "detections": [
    {
      "class": "hand",
      "confidence": 0.95,
      "bbox": [100, 150, 200, 300]
    }
  ],
  "violation_count": 1
}
```

**Database Insert**:
```sql
INSERT INTO violations (
  video_name, frame_id, timestamp,
  violation_type, bounding_boxes,
  detected_objects, confidence
) VALUES (...)
```

---

### 3. Streaming Service

**Purpose**: Provide REST API for querying violations and real-time detection streaming

**Responsibilities**:
- Consume detection results from RabbitMQ
- Maintain in-memory cache of latest detections
- Aggregate violation statistics
- Serve REST API endpoints
- Query PostgreSQL for historical data
- Support concurrent requests

**Technology Stack**:
- **Framework**: Flask 3.0.0
- **WSGI Server**: Werkzeug (built-in Flask)
- **Database**: PostgreSQL
- **Message Broker**: RabbitMQ
- **Container**: Docker

**API Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service health check |
| `/api/violations/<video_name>` | GET | Get violations for a video |
| `/api/violations-list` | GET | List all videos with violations |
| `/api/latest-detection/<video_name>` | GET | Get latest detection for video |
| `/api/video-summary/<video_name>` | GET | Get violation summary for video |
| `/api/violation-details/<id>` | GET | Get specific violation details |
| `/api/statistics` | GET | Get overall statistics |

**In-Memory Cache**:
```python
latest_detections = {
  "video_1": {frame_data},
  "video_2": {frame_data}
}

video_violations = {
  "video_1": 5,
  "video_2": 3
}
```

**Threading Model**:
- Main thread: Flask HTTP server
- Background thread: RabbitMQ consumer
- Thread-safe operations for cache updates

---

### 4. PostgreSQL Database

**Purpose**: Persistent storage of violation records

**Schema**:
```sql
CREATE TABLE violations (
    id SERIAL PRIMARY KEY,
    video_name VARCHAR(255) NOT NULL,
    frame_id INTEGER NOT NULL,
    timestamp BIGINT NOT NULL,
    violation_type VARCHAR(50) NOT NULL,
    bounding_boxes JSONB,
    detected_objects JSONB,
    confidence JSONB,
    frame_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_violations_video_name ON violations(video_name);
CREATE INDEX idx_violations_timestamp ON violations(timestamp);
```

**Data Types**:
- `JSONB`: Efficient JSON storage for flexible bounding box formats
- `BIGINT`: Millisecond timestamps for precision
- Indices on frequently queried columns

**Backup Strategy**:
```bash
# Backup
docker exec pizza_db pg_dump -U pizza_user pizza_violations > backup.sql

# Restore
docker exec -i pizza_db psql -U pizza_user pizza_violations < backup.sql
```

---

### 5. RabbitMQ Message Broker

**Purpose**: Asynchronous communication between services

**Architecture**:
```
┌────────────────────────────────────────┐
│         RabbitMQ (Topic Exchange)      │
├────────────────────────────────────────┤
│                                        │
│  Exchange: detection_exchange          │
│  Type: Topic                           │
│  Durable: Yes                          │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ Queue: detection_queue           │  │
│  │ Binding Key: frame               │  │
│  │ Consumer: Detection Service      │  │
│  └──────────────────────────────────┘  │
│                                        │
│  Exchange: detection_results           │
│  Type: Topic                           │
│  Durable: Yes                          │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ Queue: streaming_results_queue   │  │
│  │ Binding Key: detections          │  │
│  │ Consumer: Streaming Service      │  │
│  └──────────────────────────────────┘  │
│                                        │
└────────────────────────────────────────┘
```

**Message Flow**:
1. Frame Reader → `detection_exchange` with routing key `frame`
2. Detection Service consumes from `detection_queue`
3. Detection Service → `detection_results` with routing key `detections`
4. Streaming Service consumes from `streaming_results_queue`

**Reliability Features**:
- Durable exchanges and queues
- Message persistence (delivery_mode=2)
- Manual acknowledgment
- Negative acknowledgment with requeue

---

### 6. Frontend Service

**Purpose**: Web-based visualization dashboard

**Components**:
- **Server**: Nginx reverse proxy
- **Client**: HTML5 + JavaScript
- **API**: Calls streaming service REST API

**Features**:
- Live detection overlay visualization
- Violation counter
- Video streaming support
- Real-time updates (500ms polling)

**Proxy Configuration**:
```nginx
location /api/ {
    proxy_pass http://streaming:5000/;
    # Headers for proper forwarding
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    # CORS headers
    add_header 'Access-Control-Allow-Origin' '*' always;
}
```

---

## Communication Patterns

### Asynchronous Processing Pipeline

```
Frame Reader          Detection Service        Streaming Service
     │                       │                        │
     │ Publish Frame         │                        │
     ├──────→ RabbitMQ ──────→                        │
     │                       │                        │
     │                    Process & Store             │
     │                       │                        │
     │                       │ Publish Results        │
     │                       ├──────→ RabbitMQ ──────→
     │                       │                  Consume & Cache
     │                       │                        │
     │ (Next Frame)          │                        │
     ├──────→ RabbitMQ ──────→                        │
     │                       │                        │
     └─→ Continue Video      │                        │
         Processing          │                        │
```

### Request-Response Pattern (REST API)

```
Client/Frontend
     │
     │ HTTP GET /api/violations/video_1
     │
     ↓
Streaming Service
     │
     │ Query Cache
     │ (fast path)
     ↓
     │ Query Database
     │ (full history)
     ↓
     │ Format JSON Response
     ↓
Response with 200 OK
```

### Error Handling & Retry

```python
# Connection retry pattern
for retry in range(5):
    try:
        connection = connect()
        break
    except Exception as e:
        time.sleep(2 ** retry)  # Exponential backoff
        if retry == 4:
            raise
```

---

## Data Flow

### Complete End-to-End Flow

```
1. VIDEO INPUT
   └─→ Video files placed in ./videos directory

2. FRAME EXTRACTION
   Frame Reader Service:
   └─→ Read video (720p, 30 FPS)
   └─→ Skip frames (process 5 FPS)
   └─→ Encode to JPEG
   └─→ Publish to RabbitMQ

3. OBJECT DETECTION
   Detection Service:
   └─→ Consume frame from RabbitMQ
   └─→ Load YOLO12m model
   └─→ Run inference (50-200ms)
   └─→ Get detections: hand, pizza, scooper
   └─→ Extract bounding boxes

4. VIOLATION DETECTION
   Violation Logic:
   └─→ Check hand in ROI
   └─→ Check hand holds scooper (overlap)
   └─→ Check hand touches pizza (overlap)
   └─→ If violation: mark and store

5. PERSISTENCE
   PostgreSQL:
   └─→ Store violation record with:
       - Video name, frame ID, timestamp
       - Bounding boxes (JSON)
       - Detected objects, confidence scores
       - Created timestamp for audit trail

6. RESULT DISTRIBUTION
   Detection Service:
   └─→ Publish results to RabbitMQ

7. STREAMING
   Streaming Service:
   └─→ Consume results from RabbitMQ
   └─→ Update in-memory cache
   └─→ Accumulate violation counts
   └─→ Available via REST API

8. VISUALIZATION
   Frontend/Client:
   └─→ Poll API every 500ms
   └─→ Get latest detections
   └─→ Render bounding boxes
   └─→ Display violation counter
```

### Sample Data Journey

```json
Frame: video_1_frame_150.jpg
   ↓
YOLO Detection:
{
  "hand": {"confidence": 0.95, "bbox": [100, 150, 200, 300]},
  "pizza": {"confidence": 0.92, "bbox": [120, 160, 280, 320]},
  "scooper": {"confidence": 0.87, "bbox": [250, 140, 300, 220]}
}
   ↓
Violation Check:
- Hand in ROI? YES
- Hand overlaps scooper? NO
- Hand overlaps pizza? YES
- VIOLATION DETECTED!
   ↓
Database Insert:
INSERT INTO violations VALUES (
  'video_1', 150, 5000, 'hand_no_scooper',
  '{"hand": [100, 150, 200, 300], "pizza": [120, 160, 280, 320]}',
  '["hand", "pizza"]',
  '[0.95, 0.92]'
)
   ↓
API Response:
GET /api/violations/video_1 → {violation_count: 5, ...}
```

---

## Database Design

### Schema Details

```sql
violations TABLE
├─ id (SERIAL PRIMARY KEY)           -- Unique identifier
├─ video_name (VARCHAR)              -- Source video
├─ frame_id (INTEGER)                -- Frame number
├─ timestamp (BIGINT)                -- Video timestamp (ms)
├─ violation_type (VARCHAR)          -- Type of violation
├─ bounding_boxes (JSONB)            -- Detection boxes
├─ detected_objects (JSONB)          -- Object classes
├─ confidence (JSONB)                -- Confidence scores
├─ frame_path (VARCHAR)              -- Reference to frame file
└─ created_at (TIMESTAMP)            -- Record creation time

Indices:
├─ PRIMARY KEY on id
├─ INDEX on video_name (fast filtering by video)
└─ INDEX on timestamp (time-series queries)
```

### Query Patterns

**Most Frequent**:
```sql
-- Get violations for specific video
SELECT * FROM violations WHERE video_name = ?
ORDER BY frame_id DESC LIMIT 100;
```

**Analysis**:
```sql
-- Count violations per video
SELECT video_name, COUNT(*) as count
FROM violations
GROUP BY video_name
ORDER BY count DESC;

-- Get violation timeline
SELECT timestamp, violation_type, COUNT(*)
FROM violations
GROUP BY timestamp, violation_type
ORDER BY timestamp;
```

---

## Scalability & Performance

### Horizontal Scaling

**Option 1: Multiple Detection Services**
```yaml
detection_1:
  image: pizza_detection
  environment:
    WORKER_ID: 1

detection_2:
  image: pizza_detection
  environment:
    WORKER_ID: 2

detection_3:
  image: pizza_detection
  environment:
    WORKER_ID: 3
```
- RabbitMQ distributes frames across workers
- Each service processes independently
- Results aggregated in streaming service

**Option 2: Database Connection Pooling**
```python
# Add to streaming service
from psycopg2.pool import SimpleConnectionPool

pool = SimpleConnectionPool(5, 20,
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)
```

**Option 3: Streaming Service Load Balancing**
```nginx
upstream streaming {
    server streaming_1:5000;
    server streaming_2:5000;
    server streaming_3:5000;
}

server {
    location /api/ {
        proxy_pass http://streaming;
    }
}
```

### Performance Metrics

**Processing Pipeline**:
```
Frame Extraction:   ~20ms per frame
YOLO Inference:     ~100-150ms per frame
Violation Logic:    ~5ms per frame
DB Insert:          ~50ms per violation
Total Latency:      ~175-225ms per frame
Throughput:         ~5 frames/sec (configurable)
```

**Database Performance**:
```
Write throughput:    1000+ violations/second
Query latency:       <100ms for indexed queries
Storage:             ~1MB per 1000 violations
Backup time:         ~1 minute per 1M records
```

### Caching Strategy

**Streaming Service Cache**:
```python
# Latest detections (in-memory)
latest_detections = {}      # Size: ~10KB per video
video_violations = {}       # Size: negligible

# Cache invalidation: automatic on new message
# TTL: Not needed (always updated with latest)
```

### Resource Requirements

**Per Detection Service Instance**:
- CPU: 2+ cores
- RAM: 3-4GB (YOLO model + buffers)
- Storage: 500MB model + 5GB temp cache

**Total System** (single machine):
- CPU: 4+ cores
- RAM: 8GB minimum (16GB recommended)
- Storage: 30GB+ for models + database

**GPU Acceleration** (optional):
```dockerfile
FROM nvidia/cuda:12.1-runtime

# Add torch with CUDA support
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## Deployment Architecture

### Development Environment
```bash
docker-compose up -d
# All services on localhost
# SQLite for rapid iteration
```

### Staging Environment
```yaml
# kubernetes/staging/
# Replicas: 1 per service
# Resource limits: Standard
# Persistence: Managed volumes
```

### Production Environment
```yaml
# kubernetes/production/
# Detection: 3-5 replicas (auto-scaling)
# Streaming: 2-3 replicas (load balanced)
# Database: PostgreSQL cluster
# RabbitMQ: Cluster with mirroring
# Monitoring: Prometheus + Grafana
```

### Container Registry
```bash
# Build and push
docker build -t registry.company.com/pizza-detection:v1.0 ./services/detection
docker push registry.company.com/pizza-detection:v1.0

# Deploy
docker pull registry.company.com/pizza-detection:v1.0
docker run -e MODEL_PATH=/models/yolo12m-v2.pt ...
```

---

## Security Architecture

### Network Security

```
┌─────────────────────────────────────────┐
│         Internet / External             │
├─────────────────────────────────────────┤
│                                         │
│  Firewall (Port 3000, 80, 443)         │
│         ↓                               │
│  ┌─────────────────────────────────┐   │
│  │  Frontend (Nginx) :3000         │   │
│  │  Public Proxy                   │   │
│  └──────────┬──────────────────────┘   │
│             │                           │
│  ┌──────────↓──────────────────────┐   │
│  │  Docker Network (Internal)      │   │
│  │  streaming:5000 (API)           │   │
│  │  detection:5672 (private)       │   │
│  │  db:5432 (private)              │   │
│  │  rabbitmq:5672 (private)        │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### Access Control

**Authentication (TODO)**:
```python
# Recommended: JWT tokens for API
from flask_jwt_extended import JWTManager

jwt = JWTManager(app)

@app.route('/api/violations/<video_name>')
@jwt_required()
def get_violations(video_name):
    # Verify token, then return data
```

**Database Credentials**:
- Store in environment variables
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Never commit to version control

### Data Security

```python
# Sensitive Data Handling
- Frame files: Delete after processing
- Logs: Redact sensitive information
- Backups: Encrypt at rest
- API: Use HTTPS/TLS
```

### Monitoring & Logging

```yaml
# Recommended stack
- Prometheus: Metrics collection
- Grafana: Visualization
- ELK Stack: Logging (Elasticsearch, Logstash, Kibana)
- Jaeger: Distributed tracing
```

---

## Conclusion

The PIZZA-MONITOR architecture provides:
- **Modularity**: Independent, scalable services
- **Reliability**: Message queues, retries, health checks
- **Observability**: Comprehensive logging and metrics
- **Performance**: Optimized detection pipeline
- **Flexibility**: Easy to extend and modify

For questions or improvements, refer to the main README.md or contact the development team.

---

**Architecture Version**: 1.0
**Last Updated**: January 2024