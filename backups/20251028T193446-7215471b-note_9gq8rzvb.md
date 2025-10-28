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

## Installation

1. Clone and setup:
   ```bash
   cd md_note_taking
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your MinIO credentials
   ```

4. Run the server:
   ```bash
   python app.py
   ```

## API Endpoints

### 1. Create Note
```bash
POST /api/notes/create
Content-Type: application/json

{
  "notes_path": "/path/to/your/note.md"
}
```

### 2. Check Grammar
```bash
GET /api/notes/{document_id}/grammar-check
```

### 3. Render HTML
```bash
GET /api/notes/{document_id}/render
```

## Postman Collection

Import `Note_Taking_API.postman_collection.json` into Postman for testing.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| MINIO_ENDPOINT | MinIO server endpoint | localhost:9000 |
| MINIO_ACCESS_KEY | MinIO access key | minioadmin |
| MINIO_SECRET_KEY | MinIO secret key | minioadmin |
| MINIO_BUCKET_NAME | Bucket name | notes-bucket |
| MINIO_SECURE | Use HTTPS | false |
| DATABASE_URL | Database connection | sqlite:///notes.db |
