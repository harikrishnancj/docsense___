# DocSense 🧠

**DocSense** is an AI-powered document intelligence platform that lets you upload documents and structured data files, then interact with them through natural language. It generates summaries, answers specific questions via RAG (Retrieval-Augmented Generation), extracts tables and images with OCR, runs SQL analytics on spreadsheets, and auto-generates data visualizations — all driven by a local LLM via Ollama.

---

## ✨ Features

| Capability | Description |
|---|---|
| **Smart Summarization** | Automatically generates concise summaries for uploaded documents |
| **RAG Q&A** | Ask specific questions; the system retrieves relevant context using vector search |
| **SQL Analytics** | Upload CSV/Excel files and query them in natural language — auto-generates and executes DuckDB SQL |
| **Data Visualization** | Auto-generates Matplotlib/Seaborn charts from structured data or on user request |
| **OCR & Image Extraction** | Extracts embedded images from PDFs using PaddleOCR/Tesseract and generates AI descriptions |
| **Table Extraction** | Extracts tables from PDFs using Camelot and presents them in the dashboard |
| **Insight Dashboard** | A tabbed frontend panel showing Visuals, Tables, and Scanned images side-by-side |
| **Session Management** | Automatically clears previous session visuals/docs when a new file is uploaded |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (React)                   │
│   Upload → Query → Insight Dashboard (Tabs)          │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP (Axios)
                     ▼
┌──────────────────────────────────────────────────────┐
│               Backend (FastAPI)                       │
│   POST /process/  →  LangGraph App Graph             │
│                                                      │
│  ┌─────────────────────────────────────┐             │
│  │           App Graph (LangGraph)     │             │
│  │  Load → Intent → ┬─ Summary        │             │
│  │                  ├─ Index + RAG     │             │
│  │                  └─ SQL Sub-graph   │             │
│  │            → Chat Node → Tools      │             │
│  └─────────────────────────────────────┘             │
│                                                      │
│  SQL Sub-graph: Prepare → Plan → Execute →           │
│                 Refine (on error) → Visualize →      │
│                 Report                               │
└──────────────────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   SQLite (SQLAlchemy)     Ollama (Local LLM)
   Document History        LangChain + LlamaIndex
```

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** — REST API server
- **LangGraph** — Stateful agent graph orchestration
- **LangChain + LlamaIndex** — LLM chaining and vector indexing
- **Ollama** — Local LLM runtime
- **DuckDB** — In-memory SQL analytics engine
- **SQLAlchemy** — Document history persistence (SQLite)
- **PaddleOCR / Tesseract** — OCR for image text extraction
- **Camelot** — PDF table extraction
- **PyMuPDF / python-docx / python-pptx** — Multi-format document parsing
- **Matplotlib / Seaborn** — Chart generation

### Frontend
- **React 19 + Vite** — SPA framework and build tool
- **Axios** — HTTP client
- **react-markdown + remark-gfm** — Markdown rendering for AI responses
- **lucide-react** — Icon library

---

## 📁 Project Structure

```
DocSense/
├── backend/
│   ├── main.py            # FastAPI app, /process/ endpoint
│   ├── app_graph.py       # Main LangGraph pipeline (load → chat)
│   ├── sql_graph.py       # SQL analytics sub-graph (DuckDB + viz)
│   └── logging_config.py  # Structured logging setup
├── database/
│   ├── database.py        # SQLAlchemy engine & session
│   ├── models.py          # Document ORM model
│   └── crud.py            # DB save/query helpers
├── states/
│   ├── doc_state.py       # Shared LangGraph state definition
│   ├── loader.py          # File loading node (PDF, DOCX, CSV…)
│   ├── indexer.py         # LlamaIndex vector index builder
│   ├── summarizer.py      # LLM summarization node
│   └── visualizer.py      # Chart generation node
├── model/
│   └── model.py           # Ollama LLM model setup
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InsightDashboard.jsx   # Visuals / Tables / Scans tabs
│   │   │   ├── IntelligenceContext.jsx # Chat & response panel
│   │   │   ├── Sidebar.jsx            # File upload & query input
│   │   │   ├── Header.jsx
│   │   │   └── StatusBar.jsx
│   │   ├── api/           # Axios API helpers
│   │   └── App.jsx
│   └── package.json
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- [Ollama](https://ollama.com/) installed and running locally
- Tesseract OCR installed (`tesseract-ocr` package)
- Ghostscript (required for Camelot PDF table extraction)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd DocSense
```

### 2. Set Up the Backend

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Add your Ollama model name or any API keys here
OLLAMA_MODEL=llama3
```

### 4. Start Ollama

Pull and serve your preferred model:

```bash
ollama pull llama3
ollama serve
```

### 5. Run the Backend

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.

### 6. Set Up and Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 🐳 Docker

Build and run the backend using Docker:

```bash
# Build
docker build -t docsense .

# Run
docker run -p 8000:8000 docsense
```

Or use Docker Compose:

```bash
docker-compose up
```

> **Note:** The Docker setup runs only the FastAPI backend. The frontend should still be run locally with `npm run dev`.

---

## 📖 API Reference

### `POST /process/`

Process a document with an optional user query.

**Form fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `file` | File | required | Document to process (PDF, DOCX, PPTX, CSV, XLSX, etc.) |
| `user_query` | string | `""` | Natural language question or instruction |
| `mode` | string | `"summary"` | Processing mode hint (`"summary"` or `"rag"`) |

**Response:**

```json
{
  "summary": "...",
  "rag_response": "...",
  "entities": [...],
  "visuals": { "charts": [...] },
  "extracted_images": [...],
  "image_descriptions": [...],
  "extracted_tables": [...],
  "image_insights": [...]
}
```

---

## 🧩 How It Works

1. **Upload** — A file is uploaded via the frontend sidebar. The backend saves it to `uploaded_docs/`.
2. **Intent Detection** — The LangGraph pipeline detects whether to run summarization, RAG, or SQL analytics based on the file type and query.
3. **Routing:**
   - **CSV/Excel** → SQL Sub-graph (DuckDB query generation, execution, self-healing on errors, optional chart generation)
   - **RAG query** → Build vector index → Retrieve context → LLM answer
   - **Summary request** → Direct LLM summarization
4. **Chat Node** — A final LLM agent synthesizes the response, can call `rag_tool` or `visualizer_tool` as needed.
5. **Insight Dashboard** — The frontend renders charts, tables, and OCR-scanned images in separate tabs.

---

## 📋 Supported File Types

| Format | Processing |
|---|---|
| PDF | Text extraction, OCR, table extraction (Camelot), image extraction |
| DOCX | Full text extraction |
| PPTX | Slide content extraction |
| CSV | SQL analytics via DuckDB |
| XLSX / XLS | SQL analytics via DuckDB |
| Images (PNG, JPG) | OCR via PaddleOCR / Tesseract |

---

## 🛡️ Notes

- All LLM inference runs **locally** via Ollama — no data leaves your machine.
- Each new file upload automatically clears the previous session's visuals and documents.
- SQL queries are auto-generated and self-healed (up to 3 retry attempts) if they fail.
- Document history is stored in a local SQLite database (`test.db`).
#   d o c s e n s e _ _ _  
 