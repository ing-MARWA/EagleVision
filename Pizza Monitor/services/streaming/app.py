from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import pika
import json
import cv2
import numpy as np
import os
import logging
from datetime import datetime
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class StreamingManager:
    def __init__(self, db_config, rabbitmq_host, rabbitmq_port):
        self.db_config = db_config
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.db_conn = None
        self.channel = None
        self.connection = None
        
        # Cache for latest detections
        self.latest_detections = {}
        self.video_violations = {}
        
        self.connect_db()
        self.connect_rabbitmq()
        self.start_consumer_thread()
    
    def connect_db(self):
        """Connect to PostgreSQL"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.db_conn = psycopg2.connect(**self.db_config)
                logger.info("✅ Connected to PostgreSQL")
                return
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"⚠️ DB connection failed, retrying... ({retry_count}/{max_retries})")
                    time.sleep(2)
                else:
                    logger.error(f"❌ Failed to connect to DB after {max_retries} attempts: {e}")
                    raise
    
    def connect_rabbitmq(self):
        """Connect to RabbitMQ"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                credentials = pika.PlainCredentials('guest', 'guest')
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=self.rabbitmq_host, port=self.rabbitmq_port, credentials=credentials)
                )
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange='detection_results', exchange_type='topic', durable=True)
                
                # Create queue for results
                queue_result = self.channel.queue_declare(queue='streaming_results_queue', durable=True)
                self.channel.queue_bind(exchange='detection_results', queue='streaming_results_queue', routing_key='detections')
                
                logger.info("✅ Connected to RabbitMQ for streaming")
                return
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"⚠️ RabbitMQ connection failed, retrying... ({retry_count}/{max_retries})")
                    time.sleep(2)
                else:
                    logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
                    raise
    
    def process_detection(self, ch, method, properties, body):
        """Process detection results"""
        try:
            message = json.loads(body)
            video_name = message['video_name']
            
            self.latest_detections[video_name] = message
            
            violation_count = message['violation_count']
            if video_name not in self.video_violations:
                self.video_violations[video_name] = 0
            self.video_violations[video_name] += violation_count
            
            if violation_count > 0:
                logger.info(f"⚠️ Violation in {video_name}, total violations: {self.video_violations[video_name]}")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"❌ Error processing detection: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start_consumer_thread(self):
        """Start RabbitMQ consumer in background thread"""
        def consume():
            try:
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(
                    queue='streaming_results_queue',
                    on_message_callback=self.process_detection
                )
                logger.info("📨 Started consuming detection results")
                self.channel.start_consuming()
            except Exception as e:
                logger.error(f"❌ Consumer error: {e}")
        
        consumer_thread = threading.Thread(target=consume, daemon=True)
        consumer_thread.start()
    
    def get_violation_count_from_db(self, video_name):
        """Get violation count from database"""
        try:
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                'SELECT COUNT(*) as total FROM violations WHERE video_name = %s',
                (video_name,)
            )
            result = cursor.fetchone()
            cursor.close()
            return result['total'] if result else 0
        except Exception as e:
            logger.error(f"❌ Error querying violations: {e}")
            return 0
    
    def get_violations_from_db(self, video_name, limit=100):
        """Get violations from database"""
        try:
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT id, video_name, frame_id, timestamp, violation_type, 
                       bounding_boxes, detected_objects, frame_path, created_at
                FROM violations 
                WHERE video_name = %s
                ORDER BY frame_id DESC
                LIMIT %s
            ''', (video_name, limit))
            violations = cursor.fetchall()
            cursor.close()
            return violations if violations else []
        except Exception as e:
            logger.error(f"❌ Error querying violations: {e}")
            return []


try:
    manager = StreamingManager(
        db_config={
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'pizza_user'),
            'password': os.getenv('DB_PASSWORD', 'pizza_pass'),
            'database': os.getenv('DB_NAME', 'pizza_violations')
        },
        rabbitmq_host=os.getenv('RABBITMQ_HOST', 'localhost'),
        rabbitmq_port=int(os.getenv('RABBITMQ_PORT', 5672))
    )
    logger.info("✅ Streaming Manager initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Streaming Manager: {e}")

# REST API Endpoints

@app.route('/api/violations/<video_name>', methods=['GET'])
def get_violations(video_name):
    """Get violations for a specific video"""
    try:
        count = manager.get_violation_count_from_db(video_name)
        violations = manager.get_violations_from_db(video_name, limit=100)
        
        return jsonify({
            'video_name': video_name,
            'total_violations': count,
            'violations': violations
        }), 200
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/violations-list', methods=['GET'])
def get_all_violations():
    """Get all violations"""
    try:
        cursor = manager.db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT DISTINCT video_name, COUNT(*) as violation_count
            FROM violations
            GROUP BY video_name
            ORDER BY violation_count DESC
        ''')
        results = cursor.fetchall()
        cursor.close()
        
        return jsonify({
            'videos': results,
            'total_videos_with_violations': len(results)
        }), 200
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/latest-detection/<video_name>', methods=['GET'])
def get_latest_detection(video_name):
    """Get latest detection for video"""
    try:
        if video_name in manager.latest_detections:
            return jsonify(manager.latest_detections[video_name]), 200
        return jsonify({'error': 'No detections found'}), 404
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video-summary/<video_name>', methods=['GET'])
def get_video_summary(video_name):
    """Get summary for a video"""
    try:
        violation_count = manager.get_violation_count_from_db(video_name)
        
        cursor = manager.db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT MIN(timestamp) as first_violation, MAX(timestamp) as last_violation
            FROM violations
            WHERE video_name = %s
        ''', (video_name,))
        result = cursor.fetchone()
        cursor.close()
        
        return jsonify({
            'video_name': video_name,
            'total_violations': violation_count,
            'first_violation_at': result['first_violation'] if result else None,
            'last_violation_at': result['last_violation'] if result else None
        }), 200
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/violation-details/<int:violation_id>', methods=['GET'])
def get_violation_details(violation_id):
    """Get detailed information about a violation"""
    try:
        cursor = manager.db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT * FROM violations WHERE id = %s
        ''', (violation_id,))
        violation = cursor.fetchone()
        cursor.close()
        
        if not violation:
            return jsonify({'error': 'Violation not found'}), 404
        
        return jsonify(violation), 200
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'streaming'}), 200

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get overall statistics"""
    try:
        cursor = manager.db_conn.cursor(cursor_factory=RealDictCursor)
        
        # Total violations
        cursor.execute('SELECT COUNT(*) as total FROM violations')
        total_violations = cursor.fetchone()['total']
        
        # Videos with violations
        cursor.execute('SELECT COUNT(DISTINCT video_name) as total FROM violations')
        videos_with_violations = cursor.fetchone()['total']
        
        # Violation types
        cursor.execute('SELECT violation_type, COUNT(*) as count FROM violations GROUP BY violation_type')
        violation_types = cursor.fetchall()
        
        cursor.close()
        
        return jsonify({
            'total_violations': total_violations,
            'videos_with_violations': videos_with_violations,
            'violation_types': violation_types
        }), 200
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("🚀 Streaming Service Starting...")
    app.run(host='0.0.0.0', port=5000, debug=False)