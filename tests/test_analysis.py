import unittest
from aai.analysis import features,preprocess,analyze
from aai.config import load_config
class FakeSemantic:
 def analyze(self,q): return {'task':'Factual','similarities':{'Factual':0.8,'Reasoning':0.1,'Analytical':0.1,'Creative':0.1,'Technical':0.1},'uncertain':False}
class AnalysisTests(unittest.TestCase):
 def test_preserve(self):
  q='  Explain Java: A != a\n';o,n=preprocess(q);self.assertEqual(o,q);self.assertEqual(n,'Explain Java: A != a')
 def test_empty(self):
  with self.assertRaises(ValueError):preprocess(' ')
 def test_features(self):
  f=features('Compare SQL and NoSQL; give three differences and cite sources.');self.assertEqual(f['requested_count'],3);self.assertTrue(f['sources'])
 def test_recency_separate(self):
  a=analyze('Who is the current CEO of a company?',FakeSemantic(),load_config());self.assertTrue(a['retrieval_required']);self.assertLess(a['complexity'],0.65)
 def test_bounds(self):
  a=analyze('why justify analyze compare contrast java python '*30,FakeSemantic(),load_config());self.assertGreaterEqual(a['complexity'],0);self.assertLessEqual(a['complexity'],1)
