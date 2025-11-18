import configparser

from pathlib import Path
from process.embedding import Embedder
from process.QD_client import QDrantDB
from openai import OpenAI
from agent.prompt_db import RAG_USER_PROMPT

class RAG_Pipeline:
    def __init__(self):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        config_path= BASE_DIR / "../.config/creds.env"
        self.config= configparser.ConfigParser()
        self.config.read(config_path)

        self.client= OpenAI(api_key= self.config["AGENT"]["KEY"])
        self.embedder= Embedder()
        self.db= QDrantDB()

    def retrieve(self, query: str, top_k= 5):
        query_vec= self.embedder.encode([query])[0]
        print(query_vec)
        return self.db.search(query_vec= query_vec, top_k= top_k)
    
    def answer(self, query: str):
        results= self.retrieve(query= query, top_k= 5)

        print(results)

        context= "\n\n".join([
            f"{r.payload.get('text', '')}" for r in results
        ])

        user_input= RAG_USER_PROMPT\
            .replace("{{context}}", context)\
            .replace("{{query}}", query)
        
        print(user_input)

        completion= self.client.chat.completions.create(
            model= f"{self.config['AGENT']['MODEL']}",
            messages= [
                {"role": "user", "content": user_input}
            ]
        )

        return completion.choices[0].message.content