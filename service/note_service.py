from typing import Any, Dict
from extensions import db
from helpers.minio_helper import MinioService
import os
import time
import uuid
import tempfile
import shutil
import mimetypes
import json
from io import BytesIO
from models.notes import Notes
import language_tool_python

class NoteTakingService:
    def __init__(self):
        self.db = db
        self.backup_path = "./backups/"
        self.minio_client = MinioService()
        self._tool = None

    @property
    def tool(self):
        if self._tool is None:
            # Use remote LanguageTool API (no Java required)
            self._tool = language_tool_python.LanguageTool('en-US', remote_server='https://api.languagetoolplus.com/v2')
        return self._tool

    class NoteTakingException(Exception):
        pass

    def save_in_filestorage(self, note_path: str) -> Dict[str, Any]:
        if not note_path:
            raise self.NoteTakingException("note_path is empty")

        if not os.path.isfile(note_path):
            raise self.NoteTakingException(f"File not found: {note_path}")

        try:
            os.makedirs(self.backup_path, exist_ok=True)
        except OSError as e:
            raise self.NoteTakingException(f"Unable to create backup directory '{self.backup_path}': {e}")

        base_name = os.path.basename(note_path)
        timestamp = time.strftime("%Y%m%dT%H%M%S")
        unique = uuid.uuid4().hex[:8]
        object_name = f"{timestamp}-{unique}-{base_name}"
        final_backup_path = os.path.join(self.backup_path, object_name)

        temp_fd = None
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(prefix=object_name + ".", dir=self.backup_path)
            temp_fd = os.fdopen(fd, "wb")
            with open(note_path, "rb") as src:
                shutil.copyfileobj(src, temp_fd)
            temp_fd.close()
            temp_fd = None
            try:
                shutil.copystat(note_path, temp_path)
            except Exception:
                pass

            os.replace(temp_path, final_backup_path)
            temp_path = None 
        except Exception as e:
            try:
                if temp_fd is not None:
                    temp_fd.close()
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            raise self.NoteTakingException(f"Failed to save backup file: {e}")
        try:
            size = os.path.getsize(final_backup_path)
        except Exception:
            size = None

        content_type, _ = mimetypes.guess_type(final_backup_path)
        content_type = content_type or "application/octet-stream"
        return {
            "backup_path": os.path.abspath(final_backup_path),
            "original_name": base_name,
            "object_name": object_name,
            "size": size,
            "content_type": content_type,
        }
    

    def upload_to_minio(self, notes_path : str) -> Dict[str, str]:
        if not notes_path:
            raise self.NoteTakingException("notes not found")
        try:
            with open(notes_path, "rb") as f:
                file_stream = BytesIO(f.read())
            object_path = f"notes/{uuid.uuid4()}.md"
            public_url = self.minio_client.upload_to_minio(file_stream=file_stream, file_name=object_path)
            if not public_url:
                raise self.NoteTakingException("failed to upload to object storage")
            return {
                "object_path": object_path,
                "public_url": public_url
            }
        except Exception as e:
            raise self.NoteTakingException(str(e))
    
    def get_markdown_content(self, document_id: str) -> str:
        if not document_id:
            raise self.NoteTakingException("document_id is required")

        try:
            note = Notes.query.filter_by(id=document_id).first()
            if not note:
                raise self.NoteTakingException(f"Note with id {document_id} not found")

            object_path = note.minio_object_path
            if not object_path:
                raise self.NoteTakingException("MinIO object path not found for this note")

            response = self.minio_client.client.get_object(
                bucket_name=self.minio_client.bucket_name,
                object_name=object_path
            )
            md_content = response.read().decode('utf-8')
            response.close()
            response.release_conn()

            return md_content

        except self.NoteTakingException:
            raise
        except Exception as e:
            raise self.NoteTakingException(f"Failed to fetch markdown content: {str(e)}")


    def checks_for_grammers(self, document_id: str) -> Dict[str, Any]:
        if not document_id:
            raise self.NoteTakingException("document_id is required")

        try:
            note = Notes.query.filter_by(id=document_id).first()
            if not note:
                raise self.NoteTakingException(f"Note with id {document_id} not found")

            object_path = note.minio_object_path
            if not object_path:
                raise self.NoteTakingException("MinIO object path not found for this note")

            response = self.minio_client.client.get_object(
                bucket_name=self.minio_client.bucket_name,
                object_name=object_path
            )
            text_content = response.read().decode('utf-8')
            response.close()
            response.release_conn()

            matches = self.tool.check(text_content)

            errors = []
            for match in matches:
                errors.append({
                    "error_id": len(errors) + 1,
                    "type": match.ruleIssueType or "grammar",
                    "category": match.category,
                    "message": match.message,
                    "context": match.context,
                    "offset": match.offset,
                    "length": match.errorLength,
                    "original": text_content[match.offset:match.offset + match.errorLength],
                    "suggestions": match.replacements[:3] if match.replacements else [],
                    "rule": match.ruleId
                })

            corrected_text = language_tool_python.utils.correct(text_content, matches)

            grammar_errors = sum(1 for e in errors if e["type"] in ["grammar", "typographical"])
            spelling_errors = sum(1 for e in errors if e["type"] == "misspelling")
            style_errors = sum(1 for e in errors if e["type"] == "style")

            return {
                "status": "success",
                "note_id": document_id,
                "original_text": text_content,
                "corrected_text": corrected_text,
                "statistics": {
                    "total_errors": len(errors),
                    "grammar_errors": grammar_errors,
                    "spelling_errors": spelling_errors,
                    "style_errors": style_errors
                },
                "errors": errors
            }
        except self.NoteTakingException:
            raise
        except Exception as e:
            raise self.NoteTakingException(f"Grammar check failed: {str(e)}")
    
    def create_note_record(self, notes_path : str) -> Dict[str, Any]:
        if not notes_path:
            raise self.NoteTakingException("Note is not found")

        try:
            backup_metadata = self.save_in_filestorage(note_path=notes_path)
            if not backup_metadata:
                raise self.NoteTakingException("Error in saving metadata")
            backup_url = backup_metadata.get("backup_path")
            minio_data = self.upload_to_minio(notes_path=notes_path)
            notes = Notes(
                minio_object_path = minio_data["object_path"],
                upload_public_link = minio_data["public_url"],
                backup_file_link = backup_url,
                backup_metadata = json.dumps(backup_metadata),
            )
            self.db.session.add(notes)
            self.db.session.commit()
            return {
                "status" : True,
                "document_id" : notes.id,
                "message" : "document saved successfully"
            }
        except Exception as e:
            raise self.NoteTakingException(str(e))