import configparser

from openai import OpenAI
from pathlib import Path
from pipelines import orchestrator, rag_pipeline

class SlackMessageHandler:
    def __init__(self):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        config_path= BASE_DIR / "../.config/creds.env"
        self.config= configparser.ConfigParser()
        self.config.read(config_path)

        OPENAI_KEY=self.config["AGENT"]["KEY"]
        
        self.client= OpenAI(api_key= OPENAI_KEY)

        self.rag_pipeline= rag_pipeline.RAG_Pipeline()
        self.orchestrator= orchestrator.Orchestrator()

    def _is_rag_query(self, text: str) -> bool:
        return text.strip().lower().startswith("$search")
    
    def _extract_rag_query(self, text: str) -> str:
        if text.strip().lower().startswith("$search"):
            return text[len("$search"):].strip()
        
        return text

    def process(self, text: str) -> str:
        try:
            new_message_count, new_file_count= self.orchestrator.run_incremental()

            # If user want to use RAG
            if self._is_rag_query(text= text):
                print(">> USING RAG PIPELINE")
                query= self._extract_rag_query(text= text)
                answer= self.rag_pipeline.answer(query= query)

                return (
                    f"Ingestion updated: {new_message_count} messages, {new_file_count} files.\n\n",
                    f"{answer}"
                )
            else:
                print(">> USING CHAT PIPELINE")
                completion= self.client.chat.completions.create(
                    model= f"{self.config['AGENT']['MODEL']}",
                    messages= [
                        {"role": "system", "content": "Bạn là trợ lý của một tổ chức công nghệ"},
                        {"role": "user", "content": text}
                    ],
                )

                answer= completion.choices[0].message.content

                return (
                    f"Ingestion updated: {new_message_count} messages, {new_file_count} files.\n\n",
                    f"{answer}"
                )
        
        except Exception as e:
            return f"Error: {str(e)}"
        