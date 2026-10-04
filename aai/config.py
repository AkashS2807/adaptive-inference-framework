import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load_config(path=None):
    c=json.loads(Path(path or ROOT/'configs/settings.json').read_text(encoding='utf-8'))
    w=c['complexity']['weights']
    if any(v<0 for v in w.values()) or abs(sum(w.values())-1)>1e-6: raise ValueError('Feature weights must be nonnegative and sum to one')
    if not 0<=c['complexity']['handcrafted_mix']<=1: raise ValueError('Invalid mixture')
    if not 0<=c['complexity']['low']<c['complexity']['high']<=1: raise ValueError('Invalid thresholds')
    if len(c['models'])!=3: raise ValueError('Exactly three tiers required')
    if not 0<c['quota_headroom']<=1: raise ValueError('Invalid quota headroom')
    c['hash']=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
    return c

def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT/'.env')
    except ImportError:
        pass
