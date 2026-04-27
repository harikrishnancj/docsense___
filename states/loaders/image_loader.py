from __future__ import annotations

from typing import Any, Dict, List

from PIL import Image
from llama_index.core import Document

from states.loaders.utils import analyze_image_with_lvm, run_ocr_on_pil, save_pil_image


def load_image(path: str, filename: str, artifacts: Dict[str, List[Any]] | None = None) -> List[Document]:
    try:
        pil_img = Image.open(path).convert("RGB")
        img_path = save_pil_image(pil_img, filename)

        # Try OCR first - this is the primary source of document text
        ocr_text = run_ocr_on_pil(pil_img)

        # If OCR fails or returns empty, use vision analysis as fallback
        if not ocr_text or len(ocr_text.split()) < 5:
            print("⚠️ OCR produced minimal text, using vision analysis fallback...")
            caption, insights = analyze_image_with_lvm(pil_img)
        else:
            # OCR succeeded - use vision for summary only
            caption, insights = analyze_image_with_lvm(pil_img)

        if artifacts is not None:
            artifacts["extracted_images"].append(img_path)
            artifacts["image_descriptions"].append(caption)
            artifacts["image_insights"].append(insights)

        # Build document with OCR as primary content
        content_parts = [f"[IMAGE Document]\nFilename: {filename}"]
        if ocr_text:
            content_parts.append(f"[OCR TEXT]\n{ocr_text}")
        if caption:
            content_parts.append(f"[AI SUMMARY]\n{caption}")
        if insights:
            content_parts.append(f"[AI INSIGHTS]\n{insights}")

        document_text = "\n".join(content_parts)
        print(f"📝 Document text length: {len(document_text)} chars")

        return [
            Document(
                text=document_text,
                metadata={"filename": filename, "type": "image", "image_path": img_path},
            )
        ]
    except Exception as e:
        print(f"Failed to load image {filename}: {e}")
        return []

