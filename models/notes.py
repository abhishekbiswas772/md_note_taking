from extensions import db
import uuid
from datetime import datetime
from sqlalchemy import Index

class Notes(db.Model):
    __tablename__ = "notes_model"
    id = db.Column(db.String(255), primary_key = True, default = lambda: str(uuid.uuid4()), nullable = False)
    minio_object_path = db.Column(db.String(500), nullable = False)
    upload_public_link = db.Column(db.String(255), nullable = False)
    backup_file_link = db.Column(db.String(255), nullable = False)
    backup_metadata = db.Column(db.Text, nullable = False, default = "")
    createdAt = db.Column(db.DateTime, default = datetime.utcnow, nullable = False)
    updatedAt = db.Column(db.DateTime, default = datetime.utcnow, nullable = False, onupdate = datetime.utcnow)

    __table_args__ = (
        Index('idx_notes', 'id'),
    )

    def to_self(self):
        return {
            "id" : self.id,
            "minio_object_path" : self.minio_object_path,
            "upload_public_link" : self.upload_public_link,
            "backup_file_link" : self.backup_file_link,
            "backup_metadata" : self.backup_metadata,
            "createdAt" : self.createdAt.isoformat() if self.createdAt is not None else None,
            "updatedAt" : self.updatedAt.isoformat() if self.updatedAt is not None else None
        }
    