import numpy as np

from typing import List
from pathlib import Path
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name= "jinaai/jina-embeddings-v3"):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        cache_dir= BASE_DIR / "../.cache/models"
        self.model= SentenceTransformer(
            model_name,
            cache_folder= cache_dir,
            trust_remote_code= True
        )

    def encode(self, texts: List[str]):
        vectors= self.model.encode(
            sentences= texts,
            normalize_embeddings= True,
            convert_to_numpy= True,
            show_progress_bar= False
        )

        return vectors