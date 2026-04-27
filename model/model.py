from langchain_ollama import ChatOllama
from llama_index.embeddings.ollama import OllamaEmbedding
import os
from dotenv import load_dotenv

load_dotenv()

# LLM (Using the user-specified powerful model)
model1 = ChatOllama(model="nemotron-3-nano:30b-cloud", temperature=0)

# Embeddings (Using the pulled all-minilm model)
model2 = OllamaEmbedding(model_name="nomic-embed-text-v2-moe:latest")