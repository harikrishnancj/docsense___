from __future__ import annotations

import base64
import io
import os
import re
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF
from PIL import Image

try:
    from openai import OpenAI

    client = OpenAI()
except Exception:
    client = None

try:
    from paddleocr import PaddleOCR
    print("🔍 Initializing PaddleOCR...")
    # use_angle_cls=True helps with rotated text
    # lang="en" for English, can add "mr" for Marathi if needed
    paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en")
    print("✅ PaddleOCR Ready.")
    _PADDLE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ PaddleOCR initialization skipped: {e}")
    paddle_ocr = None
    _PADDLE_AVAILABLE = False

try:
    import pytesseract

    _PYTESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None
    _PYTESSERACT_AVAILABLE = False


__all__ = [
    "client",
    "EXTRACTED_IMG_DIR",
    "save_pil_image",
    "run_ocr_on_pil",
    "extract_numeric_signals",
    "page_to_pil",
    "analyze_image_with_lvm",
    "_PADDLE_AVAILABLE",
    "_PYTESSERACT_AVAILABLE",
]


EXTRACTED_IMG_DIR = os.path.join("uploaded_docs", "extracted_images")
os.makedirs(EXTRACTED_IMG_DIR, exist_ok=True)

#A PIL Image is an in-memory representation of an image.
def save_pil_image(pil_img: Image.Image, filename_hint: str) -> str:# image extraction
    os.makedirs(EXTRACTED_IMG_DIR, exist_ok=True)
    safe_name = re.sub(r"[^0-9A-Za-z._-]", "_", filename_hint)[:120]
    tmp_path = os.path.join(EXTRACTED_IMG_DIR, f"{safe_name}.png")
    pil_img.save(tmp_path, format="PNG")
    print(f"📸 Saved extracted image: {tmp_path}")
    return tmp_path


def run_ocr_on_pil(pil_img: Image.Image) -> str:
    # Try Tesseract first (often better for documents with clear text)
    if _PYTESSERACT_AVAILABLE and pytesseract:
        print("👁️ Running Tesseract OCR...")
        try:
            text = pytesseract.image_to_string(pil_img)
            print(f"📝 Tesseract found {len(text.split())} words.")
            return text.strip()
        except Exception as e:
            print(f"⚠️ Tesseract OCR failed: {e}")

    # Fallback to PaddleOCR
    if _PADDLE_AVAILABLE and paddle_ocr:
        try:
            import numpy as np
            print("👁️ Running PaddleOCR...")
            arr = np.array(pil_img.convert("RGB"))
            ocr_res = paddle_ocr.ocr(arr)

            # Debug: print raw result structure
            print(f"📝 OCR result type: {type(ocr_res)}, length: {len(ocr_res) if ocr_res else 0}")
            if ocr_res:
                print(f"   First item type: {type(ocr_res[0]) if ocr_res else 'N/A'}")
                if ocr_res and len(ocr_res) > 0:
                    first_page = ocr_res[0]
                    print(f"   First page type: {type(first_page)}, length: {len(first_page)}")
                    if first_page and len(first_page) > 0:
                        print(f"   First line: {first_page[0]}")

            # Extract text - handle different result formats
            texts = []
            if ocr_res:
                for page in ocr_res:
                    for item in page:
                        # PaddleOCR format: [[bbox], (text, confidence)]
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            # item[0] is bbox, item[1] is (text, confidence)
                            if isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
                                texts.append(item[1][0])  # text
                            elif isinstance(item[1], str):
                                texts.append(item[1])  # just text

            print(f"📝 OCR found {len(texts)} text blocks.")
            ocr_text = "\n".join(texts).strip()
            if not ocr_text:
                print("⚠️ PaddleOCR returned empty text")
            return ocr_text
        except Exception as e:
            print(f"⚠️ PaddleOCR failed: {e}")
            import traceback
            traceback.print_exc()

    return ""


def page_to_pil(page: fitz.Page) -> Image.Image | None:
    try:
        pix = page.get_pixmap(alpha=False)
        buf = io.BytesIO(pix.tobytes("png"))
        return Image.open(buf).convert("RGB")
    except Exception:
        return None


import ollama

def analyze_image_with_lvm(pil_image: Image.Image) -> Tuple[str, str]:
    try:
        print("🤖 Analyzing image with Ollama Vision...")
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        # Call local Ollama Qwen3-VL
        response = ollama.chat(
            model='qwen3-vl:235b-cloud',
            messages=[
                {
                    'role': 'user',
                    'content': 'Analyze this image. If it contains document text, extract ALL text verbatim. If no extractable text, provide a one-sentence description and 2-3 bullet points of insights. Separation by a newline.',
                    'images': [img_bytes]
                }
            ]
        )
        
        full_text = response.get('message', {}).get('content', '')
        print("✅ Vision analysis complete.")
        if "\n" in full_text:
            parts = full_text.split("\n", 1)
            caption = parts[0].strip()
            insights = parts[1].strip()
        else:
            caption = full_text
            insights = ""
            
        return caption, insights
    except Exception as e:
        print(f"⚠️ Vision analysis failed: {e}")
        return f"[VisionError] {e}", ""

