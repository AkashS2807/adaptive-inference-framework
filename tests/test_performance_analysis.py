import unittest
from scripts.analyze_performance import select, summarize


class PerformanceAnalysisTests(unittest.TestCase):
    def test_latest_failure_excludes_entire_pair(self):
        rows = [dict(id=m, created=1, mode=m, metadata={'query_id': 'q'}, status='completed')
                for m in ('formula', 'online', 'hybrid', 'baseline')]
        rows.append(dict(id='retry', created=2, mode='online', metadata={'query_id': 'q'}, status='api_error'))
        latest, paired = select(rows)
        self.assertEqual(len(latest), 4)
        self.assertEqual(paired, [])

    def test_empty_complexity_is_unknown(self):
        result = summarize([])
        self.assertEqual(result['queries'], 0)
        for key in ('mean_total_tokens', 'mean_assistant_quality', 'tier3_generation_share', 'escalation_rate'):
            self.assertIsNone(result[key])
