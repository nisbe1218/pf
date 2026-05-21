from django.test import SimpleTestCase

from .views import _parse_llm_analysis_response


class LlmAnalysisParsingTests(SimpleTestCase):
	def test_truncated_dataset_summary_only_is_hard_fail(self):
		raw = '{"dataset_summary": {"rows": 1'

		parsed = _parse_llm_analysis_response(raw)

		self.assertIsInstance(parsed, dict)
		self.assertEqual(parsed.get('failure_type'), 'hard')
		self.assertFalse(parsed.get('trusted'))
		self.assertLess(parsed.get('domain_score', 1.0), 0.4)
		self.assertEqual(parsed.get('presence_score'), 0.333)
		self.assertEqual(parsed.get('completeness_score'), 0.333)

	def test_incomplete_structured_dataset_summary_only_is_hard_fail(self):
		raw = '{"dataset_summary": {"rows": 50}}'

		parsed = _parse_llm_analysis_response(raw)

		self.assertIsInstance(parsed, dict)
		self.assertEqual(parsed.get('failure_type'), 'hard')
		self.assertFalse(parsed.get('trusted'))
		self.assertEqual(parsed.get('structure_type'), 'object')
		self.assertEqual(parsed.get('presence_score'), 0.333)
		self.assertEqual(parsed.get('completeness_score'), 0.333)
		self.assertLess(parsed.get('domain_score', 1.0), 0.4)

	def test_meaningful_medical_content_passes_gate(self):
		raw = '{"dataset_summary": {"rows": 200, "columns": 8}, "medical_analysis": {"issues": ["x"]}}'

		parsed = _parse_llm_analysis_response(raw)

		self.assertIsInstance(parsed, dict)
		self.assertEqual(parsed.get('failure_type'), 'soft')
		self.assertTrue(parsed.get('trusted'))
		self.assertTrue(parsed.get('domain_gate'))
		self.assertGreaterEqual(parsed.get('domain_score', 0.0), 0.4)
		self.assertEqual(parsed.get('presence_score'), 0.667)
		self.assertEqual(parsed.get('completeness_score'), 0.667)

	def test_array_root_is_not_trusted_without_domain_content(self):
		raw = '[{"a":1}, {"b":2}]'

		parsed = _parse_llm_analysis_response(raw)

		self.assertIsInstance(parsed, dict)
		self.assertEqual(parsed.get('structure_type'), 'array_root')
		self.assertEqual(parsed.get('failure_type'), 'hard')
		self.assertFalse(parsed.get('domain_gate'))
		self.assertEqual(parsed.get('domain_score'), 0.0)
		self.assertIn('results', parsed)
		self.assertEqual(len(parsed['results']), 2)

	def test_noisy_json_with_real_content_stays_trusted(self):
		raw = 'Intro text... {"dataset_summary": {"rows": 10}, "medical_analysis": {"issues": ["x"]}} ... trailing text'

		parsed = _parse_llm_analysis_response(raw)

		self.assertIsInstance(parsed, dict)
		self.assertEqual(parsed.get('failure_type'), 'soft')
		self.assertTrue(parsed.get('domain_gate'))
		self.assertTrue(parsed.get('trusted'))
		self.assertEqual(parsed.get('presence_score'), 0.667)
		self.assertEqual(parsed.get('completeness_score'), 0.667)
		self.assertGreaterEqual(parsed.get('recovery_score', 0.0), 0.6)
