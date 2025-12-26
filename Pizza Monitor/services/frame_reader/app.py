# services/frame_reader/app.py
import cv2
import pika
import json
import os
import time
import base64
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FrameReader:
    def __init__(self, rabbitmq_host, rabbitmq_port):
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.connection = None
        self.channel = None
        
    def connect_rabbitmq(self):
        """Connect to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials('guest', 'guest')
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.rabbitmq_host, port=self.rabbitmq_port, credentials=credentials)
            )
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange='detection_exchange', exchange_type='topic', durable=True)
            logger.info("✅ Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            raise
    
    def publish_frame(self, frame, frame_id, video_name, timestamp):
        """Publish frame to RabbitMQ"""
        try:
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            message = {
                'frame_id': frame_id,
                'video_name': video_name,
                'timestamp': timestamp,
                'frame': frame_base64,
                'height': frame.shape[0],
                'width': frame.shape[1]
            }
            
            # Save frame temporarily
            frame_path = f"/tmp/frames/{video_name}_{frame_id}.jpg"
            os.makedirs("/tmp/frames", exist_ok=True)
            cv2.imwrite(frame_path, frame)
            
            frame_msg = {'frame_path': frame_path, **message}
            self.channel.basic_publish(
                exchange='detection_exchange',
                routing_key='frame',
                body=json.dumps(frame_msg),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            return frame_path
        except Exception as e:
            logger.error(f"❌ Error publishing frame: {e}")
    
    def read_video(self, video_path, max_fps=5):
        """Read video and publish frames"""
        logger.info(f"📹 Reading video: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"❌ Cannot open video: {video_path}")
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"📊 Video Info: {frame_width}x{frame_height} @ {fps} FPS, {total_frames} frames")
        
        frame_skip = max(1, int(fps / max_fps))
        frame_id = 0
        video_name = Path(video_path).stem
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_id += 1
                if frame_id % frame_skip == 0:
                    timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
                    self.publish_frame(frame, frame_id, video_name, timestamp)
                    logger.info(f"📤 Published frame {frame_id} from {video_name}")
                
                time.sleep(0.001)  
        finally:
            cap.release()
            logger.info(f"✅ Video processing complete: {video_path}")
    
    def process_all_videos(self, video_dir):
        """Process all video files in directory"""
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(Path(video_dir).glob(f'*{ext}'))
        
        logger.info(f"🎬 Found {len(video_files)} video files")
        
        if len(video_files) == 0:
            logger.warning(f"⚠️ No video files found in {video_dir}")
            logger.warning(f"⚠️ Waiting for videos...")
            # Keep running even if no videos
            while True:
                time.sleep(10)
        
        for video_file in sorted(video_files):
            logger.info(f"▶️ Processing: {video_file.name}")
            self.read_video(str(video_file))
            time.sleep(2)  
        
        logger.info("✅ All videos processed")

if __name__ == '__main__':
    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
    rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
    video_path = os.getenv('VIDEO_PATH', './videos')
    
    logger.info("🚀 Frame Reader Service Starting...")
    
    reader = FrameReader(rabbitmq_host, rabbitmq_port)
    reader.connect_rabbitmq()
    
    logger.info(f"📂 Looking for videos in: {video_path}")
   
    reader.process_all_videos(video_path)