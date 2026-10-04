import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
os.environ.update(FREE_TIER_CONFIRMED='true',GEMINI_API_KEY='test-only',GROQ_API_KEY='test-only')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
import test_pipeline
from aai.storage import Store
from aai.providers import Gateway
from streamlit.testing.v1 import AppTest
with tempfile.TemporaryDirectory() as d:
    store=Store(Path(d)/'ui.sqlite')
    with patch('aai.storage.Store',lambda *a:store),patch('aai.pipeline.SemanticAnalyzer',lambda *a:test_pipeline.Semantic()),patch('aai.pipeline.Retriever',lambda *a:test_pipeline.Retrieval()),patch('aai.pipeline.Gateway',lambda cfg,s:Gateway(cfg,s,test_pipeline.Transport())):
        at=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
        at.text_area[0].input('What is a tree?')
        at.button[0].click().run(timeout=30)
        assert len(at.exception)==0,[e.message for e in at.exception]
        assert at.session_state['last_run']['status']=='completed'
        at.sidebar.selectbox[0].select('Online Adaptive').run()
        at.sidebar.checkbox[0].check().run()
        at.text_area[0].input('What is a tree?');at.button[0].click().run(timeout=30)
        assert at.session_state['last_run']['learning_enabled']
        at.slider[0].set_value(.9);at.slider[1].set_value(.9);at.slider[2].set_value(.9)
        buttons=[b for b in at.button if 'Save feedback' in b.label]
        assert buttons
        buttons[0].click().run(timeout=30)
        assert len(at.exception)==0,[e.message for e in at.exception]
        assert at.session_state['last_run']['reward'] is not None
        print('UI submission, online feedback, report, and history passed with mocked APIs.')
