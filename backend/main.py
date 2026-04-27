import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv()

from backend.app_graph import app_graph
from database.database import SessionLocal, engine
from database.models import Base
from database.crud import save_document #get_document_by_filename
from states.loaders.json_utils import make_json_serializable

import logging
from backend.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DocSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("visuals", exist_ok=True)

app.mount("/visuals", StaticFiles(directory="visuals"), name="visuals")
app.mount("/uploaded_docs", StaticFiles(directory="uploaded_docs"), name="uploaded_docs")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/process/")
async def process_file(
    file: UploadFile,
    user_query: str = Form(""),
    mode: str = Form("summary"), # Default to summary, but graph will decide
    db: Session = Depends(get_db)
):
    filename = file.filename
    file_path = Path(UPLOAD_DIR) / filename

    '''
    existing_doc = get_document_by_filename(db, filename)
    if existing_doc:
        return JSONResponse(content={
            "summary": existing_doc.summary,
            "rag_response": existing_doc.rag_response,
            "entities": existing_doc.entities,
            "visuals": existing_doc.visuals,
            "extracted_images": existing_doc.extracted_images,
            "image_descriptions": existing_doc.image_descriptions,
            "extracted_tables": existing_doc.extracted_tables,
            "image_insights": existing_doc.image_insights
        })
    '''


    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    logger.info("Received file: %s", filename)
    logger.info("User query: %s", user_query)
    logger.info("Processing mode: %s", mode)

    # --- SESSION CLEANUP ---
    # User requested to remove old extracted images/charts when a new file is uploaded.
    # We keep the current file, but wipe everything else in visuals/ and unrelated docs.
    try:
        # Clear visuals directory
        visuals_dir = Path("visuals")
        if visuals_dir.exists():
            shutil.rmtree(visuals_dir)
        os.makedirs(visuals_dir, exist_ok=True)

        # Clear ChromaDB directory (Fresh start for every upload)
        chroma_dir = Path("chroma_db")
        if chroma_dir.exists():
            try:
                shutil.rmtree(chroma_dir)
                logger.info("Cleared old ChromaDB storage.")
            except Exception as e:
                logger.warning("Could not clear ChromaDB: %s", e)
        
        # Optional: Clear other uploaded docs?
        # Ideally we only keep the current one.
        for existing_file in Path(UPLOAD_DIR).iterdir():
            if existing_file.name != filename:
                try:
                    if existing_file.is_file():
                        os.remove(existing_file)
                    elif existing_file.is_dir():
                        shutil.rmtree(existing_file)
                except Exception as e:
                    logger.warning("Cleanup warning: %s", e)
                    
    except Exception as e:
        logger.warning("Session cleanup failed: %s", e)

    logger.info("Invoking app_graph for %s...", filename)
    try:
        state = app_graph.invoke({
            "folder_path": UPLOAD_DIR,
            "filename": filename,
            "use_rag": mode.lower() == "rag",
            "user_query": user_query
        })
        logger.info("Graph invocation complete for %s.", filename)
    except Exception as e:
        logger.error("Graph invocation failed: %s", e)
        return JSONResponse(status_code=500, content={"error": f"Graph processing failed: {str(e)}"})


    summary = state.get("summary", "")
    rag_response = state.get("rag_response", "")
    entities = state.get("entities", [])
    visuals = state.get("visuals", {})

    extracted_images = state.get("extracted_images", [])
    image_descriptions = state.get("image_descriptions", [])
    extracted_tables = state.get("extracted_tables", [])
    image_insights = state.get("image_insights", [])

    save_document(
        db,
        filename=filename,
        summary=summary,
        user_query=user_query,
        rag_response=rag_response,
        entities=entities,
        visuals=visuals,
        extracted_images=extracted_images,
        image_descriptions=image_descriptions,
        extracted_tables=extracted_tables,
        image_insights=image_insights,
    )


    return JSONResponse(content=make_json_serializable({
        "summary": summary,
        "rag_response": rag_response,
        "entities": entities,
        "visuals": visuals,
        "extracted_images": extracted_images,
        "image_descriptions": image_descriptions,
        "extracted_tables": extracted_tables,
        "image_insights": image_insights
    }))
