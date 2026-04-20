import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.upload_service import UploadService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    message_id: str | None = Form(None),
    task_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    svc = UploadService(db)

    try:
        attachment = await svc.upload_file(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            message_id=message_id,
            task_id=task_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": str(attachment.id),
        "filename": attachment.filename,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "storage_url": attachment.storage_url,
        "thumbnail_url": attachment.thumbnail_url,
        "ocr_text": attachment.ocr_text[:200] if attachment.ocr_text else "",
        "extracted_text": attachment.extracted_text[:200] if attachment.extracted_text else "",
    }


@router.get("/{attachment_id}")
async def get_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = UploadService(db)
    attachment = await svc.get_attachment(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {
        "id": str(attachment.id),
        "filename": attachment.filename,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "storage_url": attachment.storage_url,
        "thumbnail_url": attachment.thumbnail_url,
        "ocr_text": attachment.ocr_text,
        "extracted_text": attachment.extracted_text,
    }
