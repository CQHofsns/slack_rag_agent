import os, re, json, hashlib, spacy, underthesea

from pathlib import Path
from langdetect import detect
from PyPDF2 import PdfReader
from docx import Document
from transformers import AutoTokenizer
from typing import List, Dict

class DataChunker:
    def __init__(self, max_tokens= 1024, overlap_ratio= 0.15):
        BASE_DIR= Path(__file__).resolve().parent # Get the current folder
        self.max_tokens= max_tokens
        self.overlap_ratio= overlap_ratio

        print(BASE_DIR / "../.cache/models")

        self.tokenizer= AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path= "jinaai/jina-embeddings-v3",
            cache_dir= BASE_DIR / "../.cache/models"
        )
        self.nlp_en= spacy.load(name= "en_core_web_sm")
        self.nlp_vi= None
    
    def file_text_extractor(self, filepath: str):
        """
        Extract text from PDF, DOCX, or TXT-like files.
        """
        if filepath.endswith(".pdf"):
            pdf= PdfReader(filepath)
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
        elif filepath.endswith(".docx"):
            doc= Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            return open(filepath, encoding= "utf-8", errors= "ignore").read()
        
    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.tokenize(text))
    
    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
    

    def detect_lang(self, text: str) -> str:
        try:
            return detect(text= text)
        except:
            return "vi"
        
    def split_sentences(self, text: str, lang: str) -> List[str]:
        if lang.startswith("en"):
            return [s.text for s in self.nlp_en(text).sents]
        else:
            return underthesea.sent_tokenize(text= text)
        
    def heading_split(self, text: str) -> List[str]:
        parts= re.split(r"\n(?=# )", text)
        return parts if len(parts)> 1 else [text]
    
    def chunk_text(self, text: str) -> List[Dict]:
        lang= self.detect_lang(text= text)
        sections= self.heading_split(text= text)

        all_chunks= []
        for sec in sections:
            sentences= self.split_sentences(text= sec, lang= lang)
            current_group= []
            current_token= 0

            for sent in sentences:
                sent_token_count= self._count_tokens(text= sent)

                if current_token+ sent_token_count> self.max_tokens:
                    chunk_text= " ".join(current_group)
                    all_chunks.append({
                        "id": self._hash(text= chunk_text),
                        "text": chunk_text,
                        "lang": lang
                    })

                    # Overlap handling
                    overlap_n= int(len(current_group)* self.overlap_ratio)
                    current_group= current_group[-overlap_n:]
                    current_token= self._count_tokens(" ".join(current_group))

                current_group.append(sent)
                current_token+= sent_token_count

            if current_group:
                chunk_text= " ".join(current_group)
                all_chunks.append({
                    "id": self._hash(text= chunk_text),
                    "text": chunk_text,
                    "lang": lang
                })

        return all_chunks
                