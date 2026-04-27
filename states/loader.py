

from __future__ import annotations

import os
import tempfile
import zipfile
from typing import Any, Dict, Iterable, List

from langsmith import traceable
from llama_index.core import Document
import pandas as pd

from states.doc_state import DocState
from states.loaders.docx_loader import load_docx
from states.loaders.image_loader import load_image
from states.loaders.pdf_loader import load_pdf
from states.loaders.pptx_loader import load_pptx
from states.loaders.txt_loader import load_txt
from states.loaders.json_utils import make_json_serializable


@traceable(name="loader")
def Loader(state: DocState) -> DocState:

    folder = state.folder_path or "uploaded_docs"
    os.makedirs(folder, exist_ok=True)

    artifacts: Dict[str, List[Any]] = {
        "extracted_images": [],
        "image_descriptions": [],
        "image_insights": [],
        "extracted_tables": [],
    }
    all_docs: List[Document] = []

    for file in sorted(os.listdir(folder)):
        full_path = os.path.join(folder, file)
        if os.path.isdir(full_path):
            continue

        lower = file.lower()
        try:
            if lower.endswith(".pdf"):
                docs = load_pdf(full_path, file, artifacts)
            elif lower.endswith(".docx"):
                docs = load_docx(full_path, file, artifacts)
            elif lower.endswith((".pptx", ".ppt")):
                docs = load_pptx(full_path, file, artifacts)
            elif lower.endswith(".txt"):
                docs = load_txt(full_path, file)
            elif lower.endswith((".csv", ".xls", ".xlsx")):
                # LIGHTWEIGHT LOADING FOR STRUCTURED DATA
                # Don't convert to long strings for indexing; SQL graph handles that.
                # Just get first 50 rows for the 'Sheets' UI tab preview.
                try:
                    df = pd.read_csv(full_path) if lower.endswith(".csv") else pd.read_excel(full_path)
                    if not df.empty:
                        artifacts["extracted_tables"].append({
                            "data": make_json_serializable(df.head(50).to_dict(orient='records')),
                            "columns": df.columns.tolist(),
                            "source": file,
                            "type": "structured_preview"
                        })
                except Exception as e:
                    print(f"Preview failed for {file}: {e}")
                docs = [] # Skip creation of Document object to save memory/context
            elif lower.endswith((".png", ".jpg", ".jpeg")):
                docs = load_image(full_path, file, artifacts)
            else:
                docs = load_txt(full_path, file)
        except Exception as e:
            print(f"Error processing {file}: {e}")
            docs = []
        
        all_docs.extend(docs)

    state.documents = all_docs
    state.extracted_images = artifacts["extracted_images"]
    state.image_descriptions = artifacts["image_descriptions"]
    state.image_insights = artifacts["image_insights"]
    state.extracted_tables = artifacts["extracted_tables"]
    if not state.folder_path:
        state.folder_path = folder

    return state
