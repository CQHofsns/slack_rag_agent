import os, json, configparser, requests

from pathlib import Path
from slack_sdk import WebClient
from typing import List, Dict, Any

class Ingestion:
    def __init__(self):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        config_path= BASE_DIR / "../.config/creds.env"
        self.message_path= BASE_DIR / "../data/conversation.jsonl"
        self.file_dir= BASE_DIR / "../data/files"
        self.manifest_path= BASE_DIR / "../data/manifest.json"

        os.makedirs(self.file_dir, exist_ok= True)
        
        self.config= configparser.ConfigParser()
        self.config.read(config_path)

        self.client= WebClient(token= self.config["SLACK"]["BOT_USER_OAUTH_TOKEN"])

        self.manifest= self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r", encoding= "utf-8") as f:
                return json.load(f)
            
        return {
            "last_message_ts": "0",
            "processed_file_ids": [],
            "files": {}
        }
    
    def _save_manifest(self):
        with open(self.manifest_path, "w", encoding= "utf-8") as f:
            json.dump(self.manifest, f, indent= 4, ensure_ascii= False)

    def ingest_messages_incremental(self) -> List[Dict]:
        """
        Incremental: fetch messages newer than manifest["last_message_ts"].
        Append to conversations.jsonl and return new message list.
        """

        last_ts= float(self.manifest["last_message_ts"])
        channels= self.client.conversations_list(types= "private_channel")["channels"]

        new_messages= []

        for ch in channels:
            history= self.client.conversations_history(
                channel= ch["id"],
                oldest= str(last_ts),
                limit= 1000
            )

            for msg in history["messages"]:
                ts= float(msg["ts"])
                if ts<= last_ts:
                    continue

                new_messages.append({
                    "channel_id": ch["id"],
                    "channel_name": ch["name"],
                    "channel_type": True if ch["is_private"] else False,
                    "user": msg.get("user"),
                    "text": msg.get("text"),
                    "ts": msg.get("ts"),
                    "thread_ts": msg.get("thread_ts")
                })

                if ts> last_ts:
                    last_ts= ts

        if new_messages:
            with open(self.message_path, "a", encoding= "utf-8") as f:
                for m in new_messages:
                    f.write(json.dumps(m, ensure_ascii= False)+ "\n")

        self.manifest["last_message_ts"]= str(last_ts)
        self._save_manifest()

        return new_messages

    def ingest_messages_full(self) -> List[Dict]:
        """
        Full ingestion: load ALL messages again.
        Overwrites conversation.jsonl.
        """

        channels= self.client.conversations_list(types= "private_channel")["channels"]

        all_messages= []
        for ch in channels:
            history= self.client.conversations_history(channel= ch["id"], limit= 3000)
            for msg in history["messages"]:
                all_messages.append({
                    "channel_id": ch["id"],
                    "channel_name": ch["name"],
                    "channel_type": True if ch["is_private"] else False,
                    "user": msg.get("user"),
                    "text": msg.get("text"),
                    "ts": msg.get("ts")
                })


        with open(self.message_path, "w", encoding= "utf-8") as f:
            for m in all_messages:
                f.write(json.dumps(m, ensure_ascii= False)+ "\n")

        if all_messages:
            latest_ts= max(float(m["ts"]) for m in all_messages)
            self.manifest["last_message_ts"]= str(latest_ts)

        self._save_manifest()

        return all_messages

    def ingest_files_incremental(self) -> List[Dict]:
        """
        Only download and register NEW files not in the manifest.
        """

        processed_ids= set(self.manifest["processed_file_ids"])
        files= self.client.files_list(count= 200)["files"]

        new_files= []

        for f in files:
            file_id= f["id"]
            if file_id in processed_ids:
                continue

            if f["filetype"] in ["pdf", "docx", "txt", "md"]:
                url= f["url_private_download"]
                fname= f["name"]
                output_path= os.path.join(self.file_dir, fname)
                
                headers = {
                    "Authorization": f"Bearer {self.config['SLACK']['BOT_USER_OAUTH_TOKEN']}"
                }
                
                content= requests.get(
                    url= url,
                    headers= headers
                ).content

                with open(output_path, "wb") as out:
                    out.write(content)

                self.manifest["processed_file_ids"].append(file_id)
                self.manifest["files"][file_id]= {
                    "name": fname,
                    "path": output_path,
                    "timestamp": f.get("timestamp"),
                    "user": f.get("user"),
                    "mimetype": f.get("mimetype"),
                    "filetype": f.get("filetype"),
                }

                new_files.append(self.manifest["files"][file_id])

        self._save_manifest()
        return new_files

    def ingest_files_full(self) -> List[Dict]:
        """
        Re-download ALL files and rebuild manifest.
        WARNING: expensive. Use only for first-time initialization.
        """

        files= self.client.files_list(count= 200)["files"]
        manifest_files = {}

        for f in files:
            if f["filetype"] in ["pdf", "docx"]:
                url= f["url_private_download"]
                fname= f["name"]
                headers= {"Authorization": f"Bearer {self.config['SLACK']['BOT_USER_OAUTH_TOKEN']}"}
                content= requests.get(
                    url= url,
                    headers= headers
                ).content
                output_path= os.path.join(self.file_dir, fname)

                with open(output_path, "wb") as out:
                    out.write(content)

                manifest_files[f["id"]]={
                    "name": fname,
                    "path": output_path,
                    "timestamp": f.get("timestamp"),
                    "user": f.get("user"),
                    "mimetype": f.get("mimetype"),
                    "filetype": f.get("filetype"),
                }

        self.manifest["processed_file_ids"]= list(manifest_files.keys())
        self.manifest["files"]= manifest_files
        self._save_manifest()

        return list(manifest_files.values())


