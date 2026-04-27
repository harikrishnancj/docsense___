from __future__ import annotations

import io
from typing import Any, Dict, List

import fitz  # PyMuPDF
from PIL import Image
from llama_index.core import Document

from states.loaders.utils import (
    analyze_image_with_lvm,
    page_to_pil,
    run_ocr_on_pil,
    save_pil_image,
)

try:
    import camelot  # type: ignore

    _HAS_CAMELOT = True
except Exception:
    camelot = None
    _HAS_CAMELOT = False


def is_valid_table(table_obj, min_rows: int = 2, min_cols: int = 2, min_accuracy: float = 50.0) -> bool:
    """
    Validate if a Camelot table object is actually a valid table.
    
    Args:
        table_obj: Camelot table object
        min_rows: Minimum number of rows required
        min_cols: Minimum number of columns required
        min_accuracy: Minimum parsing accuracy/quality score
    
    Returns:
        True if the table passes validation checks
    """
    try:
        df = table_obj.df
        
        # Check if dataframe is empty
        if df.empty:
            return False
        
        # Check minimum dimensions
        if df.shape[0] < min_rows or df.shape[1] < min_cols:
            return False
        
        # Check parsing accuracy (available in Camelot)
        if hasattr(table_obj, 'parsing_report') and hasattr(table_obj.parsing_report, 'get'):
            accuracy = table_obj.parsing_report.get('accuracy', 0)
            if accuracy < min_accuracy:
                return False
        
        # Check if it's just line-numbered text (common false positive)
        # This happens when one column is just sequential numbers
        first_col = df.iloc[:, 0].astype(str).str.strip()
        if df.shape[1] == 2:  # Two columns
            # Check if first column is just sequential line numbers
            try:
                numbers = first_col.str.replace(r'[^\d]', '', regex=True)
                if all(numbers.str.isdigit()):
                    nums = numbers.astype(int).tolist()
                    # Check if it's sequential (0,1,2,3... or 1,2,3,4...)
                    if nums == list(range(nums[0], nums[0] + len(nums))):
                        return False
            except Exception:
                pass
        
        # Check if most cells are empty (low data density)
        total_cells = df.shape[0] * df.shape[1]
        empty_cells = df.isna().sum().sum() + (df == '').sum().sum()
        if empty_cells / total_cells > 0.7:  # More than 70% empty
            return False
        
        return True
    except Exception as e:
        print(f"Error validating table: {e}")
        return False


def load_pdf(path: str, filename: str, artifacts: Dict[str, List[Any]] | None = None) -> List[Document]:
    docs: List[Document] = []
    try:
        pdf = fitz.open(path)
    except Exception as e:
        print(f"Failed to open PDF {filename}: {e}")
        return docs

    full_text_chunks: List[str] = []
    for page_num in range(len(pdf)):
        try:
            page = pdf[page_num]
            page_text = page.get_text("text") or ""
            if not page_text.strip():
                pil_page = page_to_pil(page)
                if pil_page:
                    ocr_text = run_ocr_on_pil(pil_page)
                    page_text = ocr_text or page_text
            full_text_chunks.append(f"\n--- Page {page_num + 1} ---\n{page_text.strip()}")
        except Exception as e:
            print(f"PDF page read error {filename} page {page_num + 1}: {e}")
            continue

        try:
            images_info = page.get_images(full=True)
            if os.getenv("DISABLE_VISION") == "True":
                print(f"🚫 Vision disabled via .env. Skipping image analysis for page {page_num + 1}.")
                images_info = []
        except Exception:
            images_info = []

        for img_index, img in enumerate(images_info):
            try:
                xref = img[0]
                base = pdf.extract_image(xref)
                image_bytes = base.get("image")
                if not image_bytes:
                    continue
                
                # Check image dimensions to skip tiny icons/bullets
                width = base.get("width", 0)
                height = base.get("height", 0)
                if width < 40 or height < 40:
                    print(f"⏩ Skipping tiny image ({width}x{height}) on page {page_num + 1}")
                    continue

                pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                img_path = save_pil_image(pil_img, f"{filename}_p{page_num + 1}_i{img_index}")
                caption, insights = analyze_image_with_lvm(pil_img)
                ocr_text = run_ocr_on_pil(pil_img)

                if artifacts is not None:
                    artifacts["extracted_images"].append(img_path)
                    artifacts["image_descriptions"].append(caption)
                    artifacts["image_insights"].append(insights)

                docs.append(
                    Document(
                        text=(
                            "[PDF IMAGE]\n"
                            f"Filename:{filename}\nPage:{page_num + 1}\n"
                            f"ImageIndex:{img_index}\nCaption:{caption}\nInsights:{insights}\nOCR:{ocr_text}"
                        ),
                        metadata={
                            "filename": filename,
                            "type": "pdf-image",
                            "page": page_num + 1,
                            "image_index": img_index,
                            "image_path": img_path,
                            "caption": caption,
                            "insights": insights,
                            "ocr": ocr_text,
                        },
                    )
                )
            except Exception as e:
                print(f"Warning: image extraction failed for {filename} page {page_num + 1} img {img_index}: {e}")
                continue

    if _HAS_CAMELOT and camelot:
        try:
            tables_texts = []
            tlist = camelot.read_pdf(path, pages="all", flavor="lattice")
            for t in tlist:
                if not t.df.empty and is_valid_table(t):
                    tables_texts.append((t.df.to_string(), t.df))
            if not tables_texts:
                tlist = camelot.read_pdf(path, pages="all", flavor="stream")
                for t in tlist:
                    if not t.df.empty and is_valid_table(t):
                        tables_texts.append((t.df.to_string(), t.df))
            for idx, (tbl_text, tbl_df) in enumerate(tables_texts):
                # Fix column headers - Camelot often uses numeric indices instead of actual headers
                # If columns are numeric (0, 1, 2...), use first row as headers
                if all(isinstance(col, (int, str)) and str(col).isdigit() for col in tbl_df.columns):
                    # Use first row as column names
                    new_columns = tbl_df.iloc[0].astype(str).str.strip().str.replace('\n', ' ').tolist()
                    tbl_df = tbl_df[1:].reset_index(drop=True)  # Remove header row from data
                    tbl_df.columns = new_columns
                else:
                    # Clean existing column names
                    tbl_df.columns = [str(col).strip().replace('\n', ' ') for col in tbl_df.columns]
                
                # Make column names unique (handle duplicates by adding suffixes)
                cols = list(tbl_df.columns)
                seen = {}
                unique_cols = []
                for col in cols:
                    if col in seen:
                        seen[col] += 1
                        # Handle empty column names
                        if col.strip() == '':
                            unique_cols.append(f"Column_{seen[col]}")
                        else:
                            unique_cols.append(f"{col}_{seen[col]}")
                    else:
                        seen[col] = 0
                        # Handle empty column names
                        if col.strip() == '':
                            unique_cols.append("Column_0")
                        else:
                            unique_cols.append(col)
                tbl_df.columns = unique_cols
                
                docs.append(
                    Document(
                        text=f"[PDF TABLE]\nFilename:{filename}\nTableIndex:{idx}\n{tbl_df.to_string()}",
                        metadata={"filename": filename, "type": "pdf-table", "table_index": idx},
                    )
                )
                if artifacts is not None:
                    artifacts["extracted_tables"].append({
                        "data": tbl_df.to_dict(orient='records'),
                        "columns": tbl_df.columns.tolist(),
                        "source": filename,
                        "table_index": idx,
                        "type": "pdf"
                    })
        except Exception as e:
            print(f"Camelot extraction failed for {filename}: {e}")

    docs.append(
        Document(
            text="".join(full_text_chunks) or "[NO_TEXT]",
            metadata={"filename": filename, "type": "pdf-text"},
        )
    )
    try:
        pdf.close()
    except Exception as e:
        print(f"Warning: Could not close PDF {filename}: {e}")
    return docs
