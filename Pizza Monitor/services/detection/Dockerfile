FROM python:3.10-slim

WORKDIR /app

# 1. Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Set environment variables for OpenCV
ENV OPENCV_IO_ENABLE_OPENEXR=1
ENV DISPLAY=
ENV QT_QPA_PLATFORM=offscreen


# 3. Copy requirements
COPY requirements.txt .





RUN pip cache purge && \
    pip install --disable-pip-version-check --no-cache-dir -r requirements.txt



# 5. Copy application code
COPY . .

# 6. Ensure model directory exists
RUN mkdir -p /models

CMD ["python", "app.py"]