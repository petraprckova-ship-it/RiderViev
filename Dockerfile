# Dockerfile pro Person Tracker

FROM python:3.11-slim

# Metadata
LABEL maintainer="Person Tracker Team"
LABEL description="Person Tracker - Yahboom Rider robot application"

# Nastavení working directory
WORKDIR /app

# Instalace systémových závislostí
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    python3-gi \
    && rm -rf /var/lib/apt/lists/*

# Kopírování requirements
COPY requirements.txt .

# Instalace Python závislostí
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování aplikace
COPY . .

# Vytvoření directory pro modely
RUN mkdir -p models logs

# Env variables
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=xcb

# Exponování portů
EXPOSE 5555 5556

# Entrypoint
CMD ["python", "main.py"]
