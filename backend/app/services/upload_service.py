import logging
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Optional

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.attachment import Attachment
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_DOC_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_CODE_EXTENSIONS = {
    ".js", ".ts", ".tsx", ".jsx", ".py", ".go", ".java", ".rs",
    ".html", ".css", ".json", ".yaml", ".yml", ".md", ".sql",
}
ALLOWED_ARCHIVE_TYPES = {"application/zip", "application/x-zip-compressed"}

SAFE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
    '.pdf', '.txt', '.md', '.json', '.csv', '.zip',
    '.py', '.js', '.ts', '.html', '.css', '.docx', '.xlsx',
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_DOC_SIZE = 20 * 1024 * 1024
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024


class UploadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_file(self, filename: str, content_type: str, size: int) -> str | None:
        if content_type in ALLOWED_IMAGE_TYPES:
            if size > MAX_IMAGE_SIZE:
                return f"图片文件不能超过 {MAX_IMAGE_SIZE // 1024 // 1024}MB"
        elif content_type in ALLOWED_DOC_TYPES:
            if size > MAX_DOC_SIZE:
                return f"文档文件不能超过 {MAX_DOC_SIZE // 1024 // 1024}MB"
        elif content_type in ALLOWED_ARCHIVE_TYPES:
            if size > MAX_ARCHIVE_SIZE:
                return f"压缩包不能超过 {MAX_ARCHIVE_SIZE // 1024 // 1024}MB"
        else:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ALLOWED_CODE_EXTENSIONS:
                return f"不支持的文件类型: {content_type}"
            if size > 5 * 1024 * 1024:
                return "代码文件不能超过 5MB"
        return None

    def _get_file_category(self, content_type: str, filename: str) -> str:
        if content_type in ALLOWED_IMAGE_TYPES:
            return "image"
        if content_type in ALLOWED_DOC_TYPES:
            return "document"
        if content_type in ALLOWED_ARCHIVE_TYPES:
            return "archive"
        ext = os.path.splitext(filename)[1].lower()
        if ext in ALLOWED_CODE_EXTENSIONS:
            return "code"
        return "other"

    def _generate_safe_filename(self, filename: str, content_type: str) -> str:
        ext_from_mime = mimetypes.guess_extension(content_type) or ""
        if ext_from_mime not in SAFE_EXTENSIONS:
            ext_from_mime = ""

        orig_ext = PurePosixPath(filename).suffix.lower()
        if not ext_from_mime and orig_ext in SAFE_EXTENSIONS:
            ext_from_mime = orig_ext

        return f"{uuid.uuid4().hex}{ext_from_mime}"

    async def upload_file(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        message_id: str | None = None,
        task_id: str | None = None,
    ) -> Attachment:
        error = self._validate_file(filename, content_type, len(content))
        if error:
            raise ValueError(error)

        file_id = uuid.uuid4()
        category = self._get_file_category(content_type, filename)
        date_path = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        stored_name = self._generate_safe_filename(filename, content_type)

        if settings.oss_enabled:
            storage_url = await self._upload_to_oss(
                f"chat-uploads/{date_path}/{stored_name}", content, content_type
            )
        else:
            local_dir = os.path.join(settings.upload_dir, date_path)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, stored_name)
            async with aiofiles.open(local_path, "wb") as f:
                await f.write(content)
            storage_url = f"/uploads/{date_path}/{stored_name}"

        ocr_text = ""
        extracted_text = ""
        thumbnail_url = ""

        if category == "image" and content_type != "image/gif":
            ocr_text = await self._extract_ocr_text(content, content_type)
            thumbnail_url = await self._generate_thumbnail(
                content, content_type, date_path, f"thumb_{stored_name}"
            )

        if category == "document":
            extracted_text = await self._extract_document_text(content, filename)

        if category == "code":
            try:
                extracted_text = content.decode("utf-8", errors="replace")[:5000]
            except Exception:
                extracted_text = ""

        attachment = Attachment(
            id=file_id,
            message_id=uuid.UUID(message_id) if message_id else None,
            task_id=uuid.UUID(task_id) if task_id else None,
            filename=filename,
            mime_type=content_type,
            size_bytes=len(content),
            storage_url=storage_url,
            ocr_text=ocr_text,
            extracted_text=extracted_text,
            thumbnail_url=thumbnail_url,
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        return attachment

    async def _upload_to_oss(self, key: str, content: bytes, content_type: str) -> str:
        try:
            import oss2
            auth = oss2.Auth(settings.oss_access_key, settings.oss_secret_key)
            bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)
            bucket.put_object(key, content, headers={"Content-Type": content_type})
            return f"https://{settings.oss_bucket}.{settings.oss_endpoint}/{key}"
        except Exception as e:
            logger.error(f"OSS upload failed: {e}")
            raise

    async def _extract_ocr_text(self, content: bytes, content_type: str) -> str:
        try:
            import base64
            import httpx

            b64 = base64.b64encode(content).decode()

            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "提取图片中的所有文字，直接输出内容，不要任何说明。"},
                    {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{b64}"}}
                ]
            }]

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.llm_api_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={"model": settings.llm_model, "messages": messages, "max_tokens": 2000}
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
        return ""

    async def _generate_thumbnail(
        self, content: bytes, content_type: str, date_path: str, thumb_name: str
    ) -> str:
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(content))
            img.thumbnail((300, 300))
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=80)
            thumb_content = buf.getvalue()

            if settings.oss_enabled:
                return await self._upload_to_oss(
                    f"thumbnails/{date_path}/{thumb_name}.webp",
                    thumb_content,
                    "image/webp",
                )
            else:
                local_dir = os.path.join(settings.upload_dir, "thumbnails", date_path)
                os.makedirs(local_dir, exist_ok=True)
                local_path = os.path.join(local_dir, f"{thumb_name}.webp")
                async with aiofiles.open(local_path, "wb") as f:
                    await f.write(thumb_content)
                return f"/uploads/thumbnails/{date_path}/{thumb_name}.webp"
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")
            return ""

    async def _extract_document_text(self, content: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext in (".txt", ".md"):
                return content.decode("utf-8", errors="replace")[:5000]
            elif ext == ".pdf":
                import pdfplumber
                import io
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    text = "\n".join(p.extract_text() or "" for p in pdf.pages[:10])
                    return text[:5000]
            elif ext == ".docx":
                import docx
                import io
                doc = docx.Document(io.BytesIO(content))
                text = "\n".join(p.text for p in doc.paragraphs)
                return text[:5000]
        except Exception as e:
            logger.warning(f"Document extraction failed: {e}")
        return ""

    async def get_attachment(self, attachment_id: str) -> Attachment | None:
        result = await self.db.execute(
            select(Attachment).where(Attachment.id == uuid.UUID(attachment_id))
        )
        return result.scalar_one_or_none()

    async def get_attachments_for_message(self, message_id: str) -> list[Attachment]:
        result = await self.db.execute(
            select(Attachment).where(Attachment.message_id == uuid.UUID(message_id))
        )
        return list(result.scalars().all())
