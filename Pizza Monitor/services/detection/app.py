"""
Pizza Scooper Violation Detection Service
Improved logic: hand + ROI + scooper check
"""
import os
import sys
import base64

os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
os.environ['DISPLAY'] = ''
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


logger.info("🔧 Registering custom YOLO modules...")
try:
    from custom_modules import register_custom_modules
    if register_custom_modules():
        logger.info("✅ Custom modules registered successfully")
    else:
        logger.error("❌ Failed to register custom modules")
        sys.exit(1)
except Exception as e:
    logger.error(f"❌ Error in module registration: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)


from datetime import datetime
import time
import json
import cv2
import numpy as np
import pika
import psycopg2
from psycopg2.extras import RealDictCursor
from ultralytics import YOLO


ROIS = [
     (48, 34, 55, 36)
    
]

def boxes_overlap(boxA, boxB, iou_threshold=0.1):
    """
    Check if bounding box A overlaps B (IoU or simple overlap).
    """
    xa1, ya1, xa2, ya2 = boxA
    xb1, yb1, xb2, yb2 = boxB

    x_left   = max(xa1, xb1)
    y_top    = max(ya1, yb1)
    x_right  = min(xa2, xb2)
    y_bottom = min(ya2, yb2)

    if x_right < x_left or y_bottom < y_top:
        return False

    inter_area = (x_right - x_left) * (y_bottom - y_top)
    if inter_area <= 0:
        return False

   
    return True


def is_in_roi(bbox, rois):
    """Return True if bbox overlaps with any defined ROI."""
    return any(boxes_overlap(bbox, roi) for roi in rois)



class ViolationDetector:
    def __init__(self, db_config, rabbitmq_host, rabbitmq_port, model_path):
        self.db_config = db_config
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port

        logger.info(f"Checking model path: {model_path}")
        if not os.path.exists(model_path):
            logger.error(f"❌ Model file not found at: {model_path}")
            raise FileNotFoundError(f"Model file not found: {model_path}")

        logger.info(f"Loading YOLO model from: {model_path}")
        try:
            self.model = YOLO(model_path)
            self.model_loaded = True
            logger.info("✅ Model loaded successfully!")
            logger.info(f"Model classes: {self.model.names}")
        except Exception as e:
            logger.error(f"❌ Model loading failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.model = None
            self.model_loaded = False

        self.connection = None
        self.channel = None
        self.db_conn = None

    def connect_db(self):
        """Connect to PostgreSQL database"""
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.db_conn = psycopg2.connect(
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    user=self.db_config['user'],
                    password=self.db_config['password'],
                    database=self.db_config['database']
                )
                self.db_conn.autocommit = True
                logger.info("✅ Connected to PostgreSQL database")
                return
            except Exception as e:
                retry_count += 1
                time.sleep(2)

    def connect_rabbitmq(self):
        """Connect to RabbitMQ"""
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                credentials = pika.PlainCredentials('guest', 'guest')
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.rabbitmq_host,
                        port=self.rabbitmq_port,
                        credentials=credentials
                    )
                )
                self.channel = self.connection.channel()

               
                self.channel.exchange_declare(
                    exchange='detection_results',
                    exchange_type='topic',
                    durable=True
                )

                
                self.channel.queue_declare(queue='detection_queue', durable=True)
                self.channel.queue_bind(
                    exchange='detection_exchange',
                    queue='detection_queue',
                    routing_key='frame'
                )

                logger.info("✅ Connected to RabbitMQ and bound to frame messages")
                return

            except Exception as e:
                retry_count += 1
                time.sleep(2)

    def process_frame(self, ch, method, properties, body):
        """Process a frame from RabbitMQ"""
        try:
            message = json.loads(body)
            frame_b64 = message.get('frame')
            video_name = message.get('video_name')
            frame_id = message.get('frame_id')
            timestamp = message.get('timestamp')

            if frame_b64 is None:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            frame_bytes = base64.b64decode(frame_b64)
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

            if frame is None:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            
            results = self.model(frame, conf=0.3, iou=0.45)

            detections = []
            for result in results:
                for box in result.boxes:
                    detections.append({
                        'class': self.model.names[int(box.cls[0])],
                        'confidence': float(box.conf[0]),
                        'bbox': box.xyxy[0].tolist()
                    })

            
            hands   = [d for d in detections if d['class'] == 'hand']
            scoops = [d for d in detections if d['class'] == 'scooper']
            pizzas = [d for d in detections if d['class'] == 'pizza']
            
            violation_count = 0
            violation_bboxes = []

            for hand in hands:
                hb = hand['bbox']
                if is_in_roi(hb, ROIS):
                    # check if hand has scooper
                    holding_scooper = any(boxes_overlap(hb, s['bbox']) for s in scoops)
                    if not holding_scooper:
                        for pizza in pizzas:
                            if boxes_overlap(hb, pizza['bbox']):
                                violation_count += 1
                                violation_bboxes.append({
                                    'hand': hb,
                                    'pizza': pizza['bbox']
                                })
                                break

            # Save to DB if violation
            if violation_count > 0:
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    INSERT INTO violations
                    (video_name, frame_id, timestamp, violation_type, bounding_boxes,
                     detected_objects, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    video_name,
                    frame_id,
                    timestamp,
                    'hand_no_scooper',
                    json.dumps(violation_bboxes),
                    json.dumps([d['class'] for d in detections]),
                    json.dumps([d['confidence'] for d in detections])
                ))
                cursor.close()
                logger.info(f"⚠️ Violation detected in {video_name}, frame {frame_id}")

            # Publish results
            result_message = {
                'video_name': video_name,
                'frame_id': frame_id,
                'timestamp': datetime.now().isoformat(),
                'detections': detections,
                'violation_count': violation_count
            }

            self.channel.basic_publish(
                exchange='detection_results',
                routing_key='detections',
                body=json.dumps(result_message),
                properties=pika.BasicProperties(delivery_mode=2)
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue='detection_queue',
            on_message_callback=self.process_frame,
            auto_ack=False
        )
        logger.info("📥 Started consuming frames")
        self.channel.start_consuming()



if __name__ == '__main__':
    db_config = {
        'host': os.getenv('DB_HOST', 'db'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'pizza_user'),
        'password': os.getenv('DB_PASSWORD', 'pizza_pass'),
        'database': os.getenv('DB_NAME', 'pizza_violations')
    }

    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
    model_path = os.getenv("MODEL_PATH", "/models/yolo12m-v2.pt")

    detector = ViolationDetector(db_config, rabbitmq_host, rabbitmq_port, model_path)
    detector.connect_db()
    detector.connect_rabbitmq()
    detector.start_consuming()
