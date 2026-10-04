import re,json,hashlib
import numpy as np
from .config import ROOT
PATTERNS={
 'reasoning':[r'\bwhy\b',r'\bjustify\b',r'\banaly[sz]e\b',r'\bevaluate\b',r'\binfer\b',r'\bprove\b',r'\bexplain\b',r'\bderive\b'],
 'requirements':[r'\bcompare\b',r'\bcontrast\b',r'advantages and disadvantages',r'\btrade.?offs?\b',r'\bthen\b',r'\bprovided that\b',r'\bsubject to\b'],
 'technical':[r'\b(?:sql|java|python|algorithm|database|neural|transformer|rag|embedding|encryption|complexity|recursion|llms?|architecture|fine.tuning|retrieval)\b',r'\bmachine learning\b',r'\b(?:medicine|legal|finance|engineering)\b'],
 'recency':[r'\b(?:latest|recent|current|currently|today|newest|updated)\b',r'\bthis (?:year|month|week)\b',r'\bwho (?:is|holds)\b.*\b(?:ceo|president|minister|position)\b'],
 'sources':[r'\b(?:cite|citations|sources|evidence)\b',r'https?://',r'\baccording to\b',r'\bprovided (?:document|corpus|notes)\b'],
 'creative':[r'\b(?:poem|story|creative|lyrics|fiction)\b'],
 'calculation':[r'\b(?:calculate|compute|solve)\b',r'\d\s*[+*/=]\s*\d'],
}
def preprocess(query):
    if not isinstance(query,str) or not query.strip(): raise ValueError('Enter a non-empty query')
    if len(query)>12000: raise ValueError('Query exceeds 12,000 characters; split it into smaller requests')
    return query,re.sub(r'\s+',' ',query).strip()

def features(query):
    _,norm=preprocess(query);s=norm.lower()
    hits={k:[p for p in ps if re.search(p,s)] for k,ps in PATTERNS.items()}
    words=len(re.findall(r'\b\w+\b',norm))
    count=re.search(r'\b(?:give|list|provide|write)\s+(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b',s)
    nums={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
    requested=(nums.get(count[1]) or int(count[1])) if count and count[1].isdigit() else (nums[count[1]] if count else None)
    f={'length':min(words/100,1),'reasoning':min(len(hits['reasoning'])/3,1),
       'requirements':min((len(hits['requirements'])+max(0,(requested or 1)-1)/2)/3,1),
       'technical':min(len(hits['technical'])/2,1),
       'recency':bool(hits['recency']),'sources':bool(hits['sources']),
       'creative':bool(hits['creative']),'calculation':bool(hits['calculation']),
       'code':bool(re.search(r'```|\b(?:code|debug|implement)\b',s)),
       'requested_count':requested,'word_count':words,'matches':hits}
    return f

class SemanticAnalyzer:
    def __init__(self,cfg,encoder=None):
        self.cfg=cfg
        self.examples=json.loads((ROOT/'data/prototypes.json').read_text(encoding='utf-8'))
        self.prototype_hash=hashlib.sha256(json.dumps(self.examples,sort_keys=True).encode()).hexdigest()
        if encoder is None:
            from sentence_transformers import SentenceTransformer
            self.model=SentenceTransformer(cfg['embedding_model'],revision=cfg.get('embedding_revision'),device='cpu')
            self.encode=self._encode
        else:
            self.model=None;self.encode=encoder
        self.names=list(self.examples)
        self.centroids=np.array([self.encode(v).mean(axis=0) for v in self.examples.values()])
        self.centroids/=np.maximum(np.linalg.norm(self.centroids,axis=1,keepdims=True),1e-12)
    def _encode(self,texts):
        # Tokenizer-aware chunking: do not silently truncate long input at 256 wordpieces.
        result=[];tok=self.model.tokenizer
        for text in texts:
            ids=tok.encode(text,add_special_tokens=False)
            chunks=[tok.decode(ids[i:i+220],skip_special_tokens=True) for i in range(0,len(ids),220)] or ['']
            a=self.model.encode(chunks,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False).mean(axis=0)
            result.append(a/max(np.linalg.norm(a),1e-12))
        return np.array(result)
    def analyze(self,query):
        v=self.encode([query])[0];scores=self.centroids@v
        order=np.argsort(scores);margin=float(scores[order[-1]]-scores[order[-2]])
        return {'similarities':dict(zip(self.names,map(float,scores))),
                'task':self.names[int(order[-1])], 'margin':margin,
                'uncertain':bool(max(scores)<self.cfg['semantic_min_similarity'] or margin<self.cfg['semantic_uncertain_margin']),
                'prototype_hash':self.prototype_hash}

def analyze(query,semantic,cfg):
    original,normalized=preprocess(query);f=features(normalized);s=semantic.analyze(normalized)
    cc=cfg['complexity'];h=sum(f[k]*v for k,v in cc['weights'].items())
    # Positive cosine weights are normalized, not interpreted as probabilities.
    pos={k:max(0,v) for k,v in s['similarities'].items()};total=sum(pos.values())
    sem=sum(pos[k]*cc['task_scores'][k] for k in pos)/total if total else 0.5
    score=float(np.clip(cc['handcrafted_mix']*h+(1-cc['handcrafted_mix'])*sem,0,1))
    level='Simple' if score<cc['low'] else ('Complex' if score>=cc['high'] else 'Moderate')
    retrieval=f['recency'] or f['sources']
    verify=retrieval or score>=cfg['verification_complexity'] or f['calculation'] or f['code'] or f['requested_count'] is not None
    context=[1.,f['length'],f['reasoning'],f['requirements'],f['technical'],float(f['recency']),float(f['sources']),float(f['code']),float(f['calculation']),score]+list(s['similarities'].values())
    return {'original':original,'normalized':normalized,'features':f,'semantic':s,'complexity':score,'complexity_level':level,
            'handcrafted_score':h,'semantic_score':sem,'retrieval_required':bool(retrieval),'verification_required':bool(verify),'context':context}
