import os, json, configparser, glob

from pathlib import Path
from ingestion.get_data_fromSlack import Ingestion
from process.data_chunkning import DataChunker
from process.embedding import Embedder
from process.QD_client import QDrantDB

class Orchestrator:
    def __init__(self):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        config_path= BASE_DIR / "../.config/creds.env"
        self.config= configparser.ConfigParser()
        self.config.read(config_path)

        self.messages_path= BASE_DIR / "../data/conversation.jsonl"
        self.file_dir= BASE_DIR / "../data/files"

        self.ingestor= Ingestion()
        self.embedder= Embedder()
        self.chunker= DataChunker()
        self.qdrant= QDrantDB(collection= "rag_collection")
    
    def _get_conversation_file(self, file_path):
        conversations= ""
        try:
            with open(file= file_path, mode= "r", encoding= "utf-8") as f:
                for line in f:
                    if f"@{self.config['SLACK']['BOT_ID']}" in line["text"] or \
                        line["user"]== f"{self.config['SLACK']['BOT_ID']}":
                    
                        json_object= json.loads(line.strip())
                        conversations+= f"Người dùng {json_object['user']}: {json_object['text']}\n"

            return conversations

        except FileNotFoundError:
            print(f"Error: the file '{file_path}' was not found.")
        except json.JSONDecodeError as je:
            print(f"Error in decoding JSON on line: {line.strip()}. Error: {je}")
        except Exception as e:
            print(f"An expected error occured: {e}")

    def _get_attachment_content(self, file_path):
        all_file_paths= glob.glob(os.path.join(file_path, "*.pdf"))\
            + glob.glob(os.path.join(file_path, "*.docx"))
        
        attachment_file_text= ""

        for file in all_file_paths:
            filename= os.path.basename(file)
            file_content= self.chunker.file_text_extractor(file_path= file)

            attachment_file_text+= f"Tệp: {filename}\nNội dung: {file_content}\n-----"

        return attachment_file_text

    def run_kb_agent_full(self):
        """
        Read all messages (chat) and files data to create new KnowLedge Base (Cơ sở Tri thức)
        """

        # Get all conversations
        conversations= self._get_conversation_file(file_path= self.messages_path)
        attachment_data= self._get_attachment_content(file_path= self.file_dir)

    def run_incremental(self):
        """
        Call on each Slack event when bot is mentioned.
        """

        new_messages= self.ingestor.ingest_messages_incremental()
        new_files= self.ingestor.ingest_files_incremental()

        docs= []

        # Convert all messages into small documents
        # for m in new_messages:
        #     docs.append({
        #         "id": f"msg_{m['ts']}",
        #         "text": m['text'],
        #         "meta": m
        #     })

        # Convert files into document text (File --> Extract --> Chunk --> Docs)
        for f in new_files:
            raw_text= self.chunker.file_text_extractor(filepath= f["path"])
            chunks= self.chunker.chunk_text(text= raw_text)

            for i, chunk in enumerate(chunks):
                docs.append({
                    "id": f"{f['name']}_chunk_{i}",
                    "text": chunk["text"],
                    "meta": f
                })

        
        # Embedding text and QDrant upsert
        if docs:
            texts= [d["text"] for d in docs]
            embeddings= self.embedder.encode(texts= texts)

            self.qdrant.add_documents(
                embeddings= embeddings,
                docs= docs
            )

        return len(new_messages), len(new_files)
    
    def run_full(self):
        print("Fetching all data from channel")
        all_messages= self.ingestor.ingest_messages_full()
        all_files= self.ingestor.ingest_files_full()

        docs= []

        print("Converting messages and files in documents")
        # Convert all messages into small documents
        # for m in all_messages:
        #     docs.append({
        #         "id": f"msg_{m['ts']}",
        #         "text": m['text'],
        #         "meta": m
        #     })

        # Convert files into document text (File --> Extract --> Chunk --> Docs)
        for f in all_files:
            raw_text= self.chunker.file_text_extractor(filepath= f["path"])
            chunks= self.chunker.chunk_text(text= raw_text)

            for i, chunk in enumerate(chunks):
                docs.append({
                    "id": f"{f['name']}_chunk_{i}",
                    "text": chunk["text"],
                    "meta": f
                })
        
        print("Updating QDrant Database")
        # Embedding text and QDrant upsert
        if docs:
            texts= [d["text"] for d in docs]
            embeddings= self.embedder.encode(texts= texts)
            print(texts)
            print(embeddings)

            self.qdrant.add_documents(
                embeddings= embeddings,
                docs= docs
            )

        print("Done")

        return len(all_messages), len(all_files)
    
# Run full upsert
# orchestrator= Orchestrator()
# orchestrator.run_full()