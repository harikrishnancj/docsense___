import os
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import TokenTextSplitter
from model.model import model2 # Your OllamaEmbedding
from states.doc_state import DocState

# Directory where ChromaDB will store its data
CHROMA_PATH = "./chroma_db"

def build_index(state: DocState) -> DocState:
    # 1. Initialize Chroma Client (Persistent)
    db = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # 2. Create or Get a Collection (named after the file or a general project)
    # Sanitizing filename for Chroma collection naming rules
    collection_name = "".join(e for e in state.filename if e.isalnum()) if state.filename else "docsense_collection"
    chroma_collection = db.get_or_create_collection(collection_name)
    
    # 3. Set up Vector Store and Storage Context
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 4. Check if we already have indexed this file
    # Chroma manages this internally, but we can check if the collection has data
    if chroma_collection.count() > 0:
        index = VectorStoreIndex.from_vector_store(
            vector_store, 
            embed_model=model2
        )
        print(f"✅ Loaded existing Chroma index for: {state.filename}")
    else:
        # 5. Chunk and Index (The "Manual Split" you had)
        splitter = TokenTextSplitter(chunk_size=256, chunk_overlap=20)
        nodes = splitter.get_nodes_from_documents(state.documents)
        
        # Add metadata (like filename) to every node for better tracking
        for node in nodes:
            node.metadata = {"filename": state.filename}

        index = VectorStoreIndex(
            nodes, 
            storage_context=storage_context,
            embed_model=model2
        )
        print(f"🚀 Built new Chroma index with {len(nodes)} nodes.")
    
    state.index = index
    return state

