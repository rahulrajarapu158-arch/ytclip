FROM python:3.11-slim-bookworm

# Install ffmpeg, yt-dlp, and system deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp (Python package)
RUN pip install --no-cache-dir yt-dlp flask gunicorn

# Copy app code
WORKDIR /app
COPY web/ /app/web/
COPY src/ytclip/ /app/ytclip/
COPY deploy/requirements.txt /app/requirements.txt

# Install app deps
RUN pip install --no-cache-dir -r /app/requirements.txt

# Persistent storage for downloaded clips (HF Spaces supports /data)
RUN mkdir -p /data/ytclip_web

# Expose port (HF Spaces uses 7860)
ENV PORT=7860
EXPOSE 7860

# Run with gunicorn on HF's port
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 2 --timeout 300 'web:app'"]
