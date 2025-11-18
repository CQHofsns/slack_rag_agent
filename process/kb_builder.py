import os
from typing import List, Dict

class KBBuilder:
    def __init__(self, kb_dir= "../data/knowledge_base"):
        self.kb_dir= kb_dir
        os.makedirs(kb_dir, exist_ok= True)

    def write_md(self, filename: str, sections: List[Dict]):
        """
        sections = [
           { "title": "Architecture", "content": "..."}
        ]
        """
        out= []
        for sec in sections:
            out.append(f"# {sec["title"]}")
            out.append(sec["content"])
            out.append("\n")

        path= os.path.join(self.kb_dir, filename)
        with open(path, "w", encoding= "utf-8") as f:
            f.write("\n".join(out))

        return path