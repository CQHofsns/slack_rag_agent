import os, hashlib

from tqdm import tqdm
from pathlib import Path
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct
)

class QDrantDB:
    def __init__(self, collection= "rag_collection"):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        
        self.path= BASE_DIR / "../data/qdrant_storage"
        os.makedirs(self.path, exist_ok= True)

        self.client= QdrantClient(host="localhost", port=6333)
        self.collection= collection

        collection_list= self.client.get_collections().collections
        collection_names= [c.name for c in collection_list]

        if collection not in collection_names:
            self.client.recreate_collection(
                collection_name= self.collection,
                vectors_config= VectorParams(
                    size= 1024,
                    distance= Distance.COSINE
                )
            )

    @staticmethod
    def _make_int_id(s: str) -> int:
        return int(hashlib.md5(s.encode()).hexdigest()[:16], 16)

    def add_documents(self, embeddings: List[List[float]], docs: List[Dict]):
        """
        docs = [ {id: "...", meta: {...}} ]
        """
        points= []
        for embedding, doc in tqdm(zip(embeddings, docs), total= len(docs), desc= "Creating points for upsert QDrantDB"):
            points.append(PointStruct(
                id= self._make_int_id(s= doc["id"]),
                vector= embedding,
                payload= {
                    **doc["meta"],
                    "text":doc["text"]
                }
            ))

        self.client.upsert(collection_name= self.collection, points= points)
    
    def search(self, query_vec, top_k= 5):
        return self.client.search(
            collection_name= self.collection,
            query_vector= query_vec,
            limit= top_k
        )