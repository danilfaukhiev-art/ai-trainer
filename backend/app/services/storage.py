"""
Storage service stub — S3 will be added in Phase 2.
For now saves files locally inside the container.
"""
import os
import uuid
from datetime import datetime
from fastapi import UploadFile

UPLOAD_DIR = "/tmp/ai_trainer_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class StorageService:
    async def upload_progress_photo(
        self, user_id: str, file: UploadFile, photo_type: str
    ) -> str:
        ext = (file.filename or "jpg").rsplit(".", 1)[-1]
        key = f"users/{user_id}/progress_photos/{datetime.today().date()}_{photo_type}_{uuid.uuid4().hex[:8]}.{ext}"
        path = os.path.join(UPLOAD_DIR, key.replace("/", "_"))
        data = await file.read()
        with open(path, "wb") as f:
            f.write(data)
        return key

    async def upload_technique_video(
        self, user_id: str, file: UploadFile, exercise_name: str
    ) -> str:
        ext = (file.filename or "mp4").rsplit(".", 1)[-1]
        key = f"users/{user_id}/videos/{uuid.uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_DIR, key.replace("/", "_"))
        data = await file.read()
        with open(path, "wb") as f:
            f.write(data)
        return key

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/uploads/{key}"

    async def download_to_bytes(self, key: str) -> bytes:
        path = os.path.join(UPLOAD_DIR, key.replace("/", "_"))
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str):
        path = os.path.join(UPLOAD_DIR, key.replace("/", "_"))
        if os.path.exists(path):
            os.remove(path)
