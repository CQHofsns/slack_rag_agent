import os, json, configparser

from pathlib import Path
from prompt_db import KB_SUMM_AGENT_PROMPT, KB_SUMM_USER_PROMPT
from openai import OpenAI
from process.kb_builder import KBBuilder

class ChannelKBAgent:
    def __init__(self, slack_client, openai_client):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        config_path= BASE_DIR / "../.config/creds.env"
        self.config= configparser.ConfigParser()
        self.config.read(config_path)

        self.slack= slack_client
        self.openai= openai_client
        self.builder= KBBuilder()

    def _summarize(self, messages, files):
        user_input= KB_SUMM_USER_PROMPT\
            .replace("{{conversation}}", messages)\
            .replace("{{files_data}}", files)
        
        summary= self.openai.chat.completions.create(
            model= f"{self.config['AGENT']['MODEL']}",
            messages= [
                {"role": "system", "content": KB_SUMM_AGENT_PROMPT},
                {"role": "user", "content": user_input}
            ]
        ).choices[0].message.content

        return [{
            "title": "Cơ sở Tri Thức",
            "content": summary
        }]
    
    def _upload_to_SlackCanvas(self, channel_id, markdown_path):
        self.slack.file_upload_v2(
            channel= channel_id,
            file= markdown_path,
            initial_comment= "🔄 Cập nhật Tri Thức"
        )
    
    def build_kb_for_channel(self, channel_id, messages, files):
        kb_structure= self._summarize(
            messages= messages,
            files= files
        )

        markdown_path= self.builder.write_md(
            filename= f"{channel_id}_kb.md",
            sections= kb_structure
        )

        self._upload_to_SlackCanvas(
            channel_id= channel_id,
            markdown_path= markdown_path
        )