"""File content extraction for LLM Council attachments."""

import base64
import io
import logging
from typing import Dict, Any

from .openrouter import query_model
from .prompts import IMAGE_DESCRIPTION_PROMPT

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 200_000
SUPPORTED_EXTENSIONS = {'txt', 'docx', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}


async def extract_file(file_name: str, file_bytes: bytes, content_type: str) -> Dict[str, Any]:
    """
    Extract text content from an uploaded file.

    Returns dict with keys: extracted_text (str), truncated (bool), file_type (str).
    Raises ValueError for unsupported types.
    """
    ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''

    if ext == 'txt' or 'text/plain' in content_type:
        text = _extract_txt(file_bytes)
        file_type = 'txt'
    elif ext == 'docx' or 'wordprocessingml' in content_type:
        text = _extract_docx(file_bytes)
        file_type = 'docx'
    elif ext == 'pdf' or 'application/pdf' in content_type:
        text = _extract_pdf(file_bytes)
        file_type = 'pdf'
    elif ext in ('png', 'jpg', 'jpeg', 'gif', 'webp') or content_type.startswith('image/'):
        text = await _describe_image(file_bytes, content_type)
        file_type = 'image'
    else:
        raise ValueError(f"Unsupported file type: .{ext}")

    truncated = len(text) > MAX_TEXT_CHARS
    logger.info("extract_file name=%s type=%s chars=%d truncated=%s", file_name, file_type, len(text), truncated)
    return {
        'extracted_text': text[:MAX_TEXT_CHARS],
        'truncated': truncated,
        'file_type': file_type,
    }


def _extract_txt(file_bytes: bytes) -> str:
    return file_bytes.decode('utf-8', errors='replace')


def _extract_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    return '\n\n'.join(page.extract_text() or '' for page in reader.pages[:50])


async def _describe_image(file_bytes: bytes, content_type: str) -> str:
    mime = content_type if content_type.startswith('image/') else 'image/jpeg'
    b64 = base64.b64encode(file_bytes).decode()
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        ]
    }]
    response = await query_model("google/gemini-2.5-flash", messages, timeout=60.0)
    if response and response.get('content'):
        return response['content'].strip()
    return "[Image could not be analyzed — please describe its contents in your question]"
