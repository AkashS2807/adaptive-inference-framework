"""Retrieval from an explicit, dated local evidence collection, not live web search."""
import json,hashlib
import numpy as np
from .config import ROOT
class Retriever:
    def __init__(self,cfg,semantic,path=None):
        self.cfg=cfg;self.semantic=semantic
        self.docs=json.loads(Path(path).read_text(encoding='utf-8')) if path else json.loads((ROOT/'data/evidence.json').read_text(encoding='utf-8'))
        self.hash=hashlib.sha256(json.dumps(self.docs,sort_keys=True).encode()).hexdigest()
        self.vectors=semantic.encode([d['title']+' '+d['text'] for d in self.docs]) if self.docs else np.zeros((0,1))
    def search(self,query,recency=False):
        if recency:
            return {'status':'fresh_evidence_unavailable','documents':[],'corpus_hash':self.hash,
                    'limitation':'This Phase 1 installation has a local dated corpus, not a live news/search service. Current facts cannot be verified.'}
        if not self.docs: return {'status':'no_evidence','documents':[],'corpus_hash':self.hash}
        scores=self.vectors@self.semantic.encode([query])[0];order=np.argsort(scores)[::-1]
        selected=[];remaining=self.cfg['retrieval']['max_chars']
        for i in order[:self.cfg['retrieval']['top_k']]:
            if scores[i]<self.cfg['retrieval']['min_similarity'] or remaining<=0: continue
            doc={**self.docs[int(i)],'similarity':float(scores[i])};doc['text']=doc['text'][:remaining];remaining-=len(doc['text']);selected.append(doc)
        return {'status':'retrieved' if selected else 'no_evidence','documents':selected,'corpus_hash':self.hash}
from pathlib import Path
