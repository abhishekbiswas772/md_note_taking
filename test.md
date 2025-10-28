# Markdown Note Taking Service

A Flask-based API service for storing, managing, and analyzing markdown notes with MinIO object storage.

## Features

- Store markdown notes in MinIO
- Grammar checking with LanguageTool
- Render markdown as styled HTML
- Local backup system

 Detailed error reporting

## Prerequisites

1. **Java Runtime** (for LanguageTool)
   ```bash
   # macOS
   brew install openjdk

   # Ubuntu/Debian
   sudo apt install default-jre
   ```

2. **MinIO Server**
   ```bash
   # macOS
   brew install minio/stable/minio
   minio server ~/minio-data

   # Docker
   docker run -p 9000:9000 -p 9001:9001 \
     -e "MINIO_ROOT_USER=minioadmin" \
     -e "MINIO_ROOT_PASSWORD=minioadmin" \
     quay.io/minio/minio server /data --console-address ":9001"
   ```
