"""
ContextOS Content Extractors.

Provides unified content extraction for PDFs, Word documents, text files,
CSVs, images (OCR), and saved web pages.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Standardized output from any document extractor."""
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    pages: list[str] = field(default_factory=list)
    file_type: str = "text"


class BaseExtractor:
    """Base interface for all content extractors."""

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        raise NotImplementedError


class TextExtractor(BaseExtractor):
    """Extracts raw text files (txt, md, json, etc.)."""

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        content = ""
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                content = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        return ExtractionResult(
            text=content,
            metadata={"filename": path.name, "file_size": path.stat().st_size},
            pages=[content],
            file_type="txt",
        )


class PDFExtractor(BaseExtractor):
    """Extracts text and page-level layout from PDF documents using PyMuPDF (fitz)."""

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        pages_text: list[str] = []
        doc_metadata: dict[str, Any] = {
            "filename": path.name,
            "file_size": path.stat().st_size,
        }

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(path))
            doc_metadata.update(doc.metadata or {})
            doc_metadata["page_count"] = len(doc)

            for page_index in range(len(doc)):
                page = doc[page_index]
                text = page.get_text()
                pages_text.append(text)
            doc.close()
        except ImportError:
            logger.warning("PyMuPDF (fitz) not installed; falling back to basic binary extraction.")
            raw = path.read_bytes()
            pages_text = [raw.decode("latin-1", errors="ignore")]
        except Exception as e:
            logger.error("Error reading PDF %s: %s", path, e)
            pages_text = [f"[Error extracting PDF: {e}]"]

        full_text = "\n\n".join(pages_text)
        return ExtractionResult(
            text=full_text,
            metadata=doc_metadata,
            pages=pages_text,
            file_type="pdf",
        )


class DocxExtractor(BaseExtractor):
    """Extracts text from Microsoft Word .docx files."""

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        paragraphs: list[str] = []
        metadata: dict[str, Any] = {
            "filename": path.name,
            "file_size": path.stat().st_size,
        }

        try:
            import docx

            doc = docx.Document(str(path))
            for p in doc.paragraphs:
                if p.text.strip():
                    paragraphs.append(p.text)
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
        except ImportError:
            logger.warning("python-docx not installed; reading text as fallback.")
            paragraphs = [path.read_text(errors="ignore")]
        except Exception as e:
            logger.error("Error extracting docx %s: %s", path, e)
            paragraphs = [f"[Error extracting DOCX: {e}]"]

        full_text = "\n\n".join(paragraphs)
        return ExtractionResult(
            text=full_text,
            metadata=metadata,
            pages=[full_text],
            file_type="docx",
        )


class CSVExtractor(BaseExtractor):
    """Extracts and formats CSV data for semantic indexing."""

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        rows_text: list[str] = []
        metadata = {"filename": path.name, "file_size": path.stat().st_size}

        try:
            with open(path, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    metadata["columns"] = header
                    for row in reader:
                        pairs = [f"{col}: {val}" for col, val in zip(header, row) if val.strip()]
                        if pairs:
                            rows_text.append(", ".join(pairs))
        except Exception as e:
            logger.error("Error reading CSV %s: %s", path, e)

        full_text = "\n".join(rows_text)
        return ExtractionResult(
            text=full_text,
            metadata=metadata,
            pages=[full_text],
            file_type="csv",
        )


class ImageExtractor(BaseExtractor):
    """Extracts text from images using OCR (PaddleOCR or Tesseract) and EXIF metadata."""

    def __init__(self) -> None:
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            except Exception as e:
                logger.warning("PaddleOCR not available or failed to load: %s", e)
                self._ocr = False
        return self._ocr

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        extracted_text = ""
        metadata: dict[str, Any] = {
            "filename": path.name,
            "file_size": path.stat().st_size,
        }

        # Read basic image properties via PIL
        try:
            from PIL import Image
            with Image.open(path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                exif = getattr(img, "_getexif", lambda: None)()
                if exif:
                    metadata["has_exif"] = True
        except Exception as e:
            logger.debug("Could not read image metadata for %s: %s", path, e)

        # Attempt OCR
        # 1. First attempt native Windows 10/11 OCR (winocr)
        try:
            import winocr
            from PIL import Image
            with Image.open(path) as img:
                res = winocr.recognize_pil_sync(img, "en")
                if res and res.get("text") and res.get("text").strip():
                    extracted_text = res["text"].strip()
                    logger.info("Successfully extracted text from %s using Windows native OCR.", path.name)
        except Exception as e:
            logger.debug("Windows native OCR skipped or failed for %s: %s", path, e)

        # 2. Fallback to PaddleOCR if winocr didn't extract text
        if not extracted_text:
            ocr_engine = self._get_ocr()
            if ocr_engine:
                try:
                    result = ocr_engine.ocr(str(path), cls=True)
                    lines = []
                    if result and result[0]:
                        for line in result[0]:
                            text, conf = line[1]
                            if conf > 0.4:
                                lines.append(text)
                    extracted_text = "\n".join(lines)
                except Exception as e:
                    logger.error("PaddleOCR execution error on %s: %s", path, e)

        # 3. Attempt Vision LLM description (Ollama moondream or llava) for diagrams/architectures
        visual_desc = ""
        try:
            import base64
            import httpx
            with open(path, "rb") as img_f:
                b64_img = base64.b64encode(img_f.read()).decode()
            async with httpx.AsyncClient(timeout=15.0) as client:
                v_resp = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": "moondream:latest",
                        "prompt": "Describe what is depicted in this image, architecture diagram, flowchart, or UI concisely in 2-3 sentences.",
                        "images": [b64_img],
                        "stream": False,
                    },
                )
                if v_resp.status_code == 200:
                    v_json = v_resp.json()
                    visual_desc = v_json.get("response", "").strip()
                    if visual_desc:
                        logger.info("Vision LLM successfully analyzed %s: %s", path.name, visual_desc[:80])
        except Exception as e:
            logger.debug("Vision LLM describe skipped for %s: %s", path, e)

        # Merge visual description with OCR text
        parts = []
        if visual_desc:
            parts.append(f"[Visual Scene / Diagram Analysis: {visual_desc}]")
        if extracted_text and not extracted_text.startswith("[Visual"):
            parts.append(f"[OCR Extracted Text:\n{extracted_text}]")
        
        if parts:
            final_content = "\n\n".join(parts)
        else:
            final_content = f"[Visual screenshot: {path.name}]"

        return ExtractionResult(
            text=final_content,
            metadata=metadata,
            pages=[final_content],
            file_type="image",
        )


class AudioExtractor(BaseExtractor):
    """Extracts spoken transcript from audio and lecture recordings using faster-whisper."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel("tiny.en", device="auto", compute_type="auto")
            except Exception as e:
                logger.warning("Could not load WhisperModel: %s", e)
                self._model = False
        return self._model

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        metadata = {
            "filename": path.name,
            "file_size": path.stat().st_size,
            "file_type": "audio",
        }

        model = self._get_model()
        if not model:
            fallback = f"[Audio recording: {path.name}]"
            return ExtractionResult(text=fallback, metadata=metadata, pages=[fallback], file_type="audio")

        try:
            segments, info = model.transcribe(str(path), beam_size=1)
            transcripts = []
            for seg in segments:
                m, s = divmod(int(seg.start), 60)
                transcripts.append(f"[{m:02d}:{s:02d}] {seg.text.strip()}")
            full_text = "\n".join(transcripts) if transcripts else f"[Audio transcription: {path.name}]"
            metadata["duration_seconds"] = getattr(info, "duration", 0)
            metadata["language"] = getattr(info, "language", "en")
            return ExtractionResult(
                text=full_text,
                metadata=metadata,
                pages=[full_text],
                file_type="audio",
            )
        except Exception as e:
            logger.error("Whisper transcription error for %s: %s", path, e)
            fallback = f"[Audio recording: {path.name}]"
            return ExtractionResult(text=fallback, metadata=metadata, pages=[fallback], file_type="audio")


class WebpageExtractor(BaseExtractor):
    """Extracts structured text and metadata from saved HTML or JSON-payload pages."""

    async def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        metadata = {"filename": path.name, "file_size": path.stat().st_size}

        # Check if saved as JSON from extension
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(content)
                text = data.get("content", "")
                metadata.update(data.get("metadata", {}))
                metadata["title"] = data.get("title", "")
                metadata["url"] = data.get("url", "")
                return ExtractionResult(
                    text=f"{metadata.get('title', '')}\n\n{text}",
                    metadata=metadata,
                    pages=[text],
                    file_type="webpage",
                )
            except Exception:
                pass

        # Basic HTML extraction
        try:
            import re
            # Extract title
            title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else path.stem
            metadata["title"] = title

            # Strip scripts, styles, and tags
            clean_text = re.sub(r"<(script|style).*?</\1>", "", content, flags=re.IGNORECASE | re.DOTALL)
            clean_text = re.sub(r"<[^>]+>", " ", clean_text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            return ExtractionResult(
                text=f"{title}\n\n{clean_text}",
                metadata=metadata,
                pages=[clean_text],
                file_type="webpage",
            )
        except Exception as e:
            logger.error("Error parsing webpage %s: %s", path, e)
            return ExtractionResult(
                text=content,
                metadata=metadata,
                pages=[content],
                file_type="webpage",
            )


class ExtractorRegistry:
    """Factory and registry dispatching files to the appropriate extractor."""

    def __init__(self) -> None:
        self._extractors: dict[str, BaseExtractor] = {
            ".pdf": PDFExtractor(),
            ".txt": TextExtractor(),
            ".md": TextExtractor(),
            ".markdown": TextExtractor(),
            ".docx": DocxExtractor(),
            ".csv": CSVExtractor(),
            ".png": ImageExtractor(),
            ".jpg": ImageExtractor(),
            ".jpeg": ImageExtractor(),
            ".webp": ImageExtractor(),
            ".html": WebpageExtractor(),
            ".htm": WebpageExtractor(),
            ".json": WebpageExtractor(),
            ".mp3": AudioExtractor(),
            ".wav": AudioExtractor(),
            ".m4a": AudioExtractor(),
            ".ogg": AudioExtractor(),
            ".flac": AudioExtractor(),
            ".aac": AudioExtractor(),
        }

    def get_extractor(self, file_path: str | Path) -> Optional[BaseExtractor]:
        ext = Path(file_path).suffix.lower()
        return self._extractors.get(ext)


_registry = ExtractorRegistry()


def get_extractor_for_file(file_path: str | Path) -> Optional[BaseExtractor]:
    return _registry.get_extractor(file_path)
