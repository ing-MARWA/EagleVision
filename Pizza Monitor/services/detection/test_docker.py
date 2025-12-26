"""
Test script for Docker environment
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 50)
print("Testing custom modules in Docker...")
print("=" * 50)

# Check current directory
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Directory contents:")
for item in os.listdir('.'):
    logger.info(f"  {item}")

# Set environment variable to prevent OpenCV from loading GUI libs
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'


try:
    
    import custom_modules
    if custom_modules.register_custom_modules():
        logger.info("✅ Custom modules registered successfully")
    else:
        logger.error("❌ Failed to register custom modules")
        sys.exit(1)
except Exception as e:
    logger.error(f"❌ Error registering custom modules: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)


model_path = os.getenv('MODEL_PATH', '/models/yolo12m-v2.pt')
logger.info(f"Model path: {model_path}")


if os.path.exists(model_path):
    logger.info(f"✅ Model file found: {model_path}")
    logger.info(f"Model size: {os.path.getsize(model_path) / (1024*1024):.2f} MB")
else:
    logger.error(f"❌ Model file not found: {model_path}")
    
    
    logger.info("Root directory contents:")
    for item in os.listdir('/'):
        logger.info(f"  /{item}")
    
    
    if os.path.exists('/models'):
        logger.info("Contents of /models:")
        for item in os.listdir('/models'):
            logger.info(f"  /models/{item}")
    else:
        logger.error("❌ /models directory does not exist")
    
    sys.exit(1)


try:
    
    from ultralytics import YOLO
    logger.info("Loading model...")
    model = YOLO(model_path)
    logger.info(f"✅ Model loaded successfully!")
    logger.info(f"Model classes: {model.names}")
    
   
    import numpy as np
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    results = model(test_image, verbose=False)
    
    if results and hasattr(results[0], 'boxes'):
        logger.info(f"✅ Test inference successful! Detected {len(results[0].boxes)} objects")
    else:
        logger.info("✅ Test inference completed (no objects detected)")
        
except Exception as e:
    logger.error(f"❌ Model loading or inference failed: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)

logger.info("🎉 All Docker tests passed!")