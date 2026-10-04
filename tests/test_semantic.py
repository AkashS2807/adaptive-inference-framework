import unittest,json
import numpy as np
from aai.analysis import SemanticAnalyzer
from aai.config import load_config
from aai.retrieval import Retriever
class SemanticTests(unittest.TestCase):
    def test_real_centroid_construction_without_download(self):
        def encode(texts):
            values=np.array([[len(t),len(t.split()),1.] for t in texts],dtype=float)
            return values/np.linalg.norm(values,axis=1,keepdims=True)
        s=SemanticAnalyzer(load_config(),encode)
        self.assertEqual(s.centroids.shape,(5,3))
        np.testing.assert_allclose(np.linalg.norm(s.centroids,axis=1),1)
        output=s.analyze('A query');self.assertEqual(len(output['similarities']),5)
    def test_empty_and_recency_evidence(self):
        class S:
            def encode(self,texts):return np.array([[1.,0.] for _ in texts])
        r=Retriever(load_config(),S())
        self.assertEqual(r.search('current',True)['status'],'fresh_evidence_unavailable')
        self.assertTrue(r.search('test')['documents'])
