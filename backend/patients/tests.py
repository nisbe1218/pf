import pandas as pd

from django.test import SimpleTestCase
from unittest.mock import patch

from .views import _build_deterministic_analysis_fallback, _build_preprocess_audit_event, _compute_final_confidence, _prepare_preprocess_llm_payload, estimate_size, replay_preprocess_pipeline, validate_payload, validate_payload_schema_only


def _build_payload(critical_count=0, high_count=0, suspect_count=0, columns_count=0, filler_size=0):
	payload = {
		'critical_anomalies': [
			{'id': index, 'label': f'critical_{index}', 'details': 'x' * filler_size}
			for index in range(critical_count)
		],
		'high_anomalies': [
			{'id': index, 'label': f'high_{index}', 'details': 'x' * filler_size}
			for index in range(high_count)
		],
		'suspect_columns': [f'column_{index}' for index in range(suspect_count)],
		'technical_profile': {
			'rows': 120,
			'columns': columns_count,
			'missing_cells': 0,
			'missing_pct': 0.0,
			'duplicate_rows': 0,
			'duplicate_pct': 0.0,
			'columns_profile': [
				{
					'column': f'column_{index}',
					'dtype': 'float64',
					'missing_count': 0,
					'missing_pct': 0.0,
					'sample_values': ['1', '2', '3'],
				}
				for index in range(columns_count)
			],
			'numeric_columns_profile': [],
			'categorical_columns_profile': [],
		},
		'missing_data_rate': {f'column_{index}': 0.0 for index in range(columns_count)},
		'statistics': {f'column_{index}': {'mean': index} for index in range(columns_count)},
		'rule_validation': {'status': 'pass', 'summary': 'ok', 'issues': [], 'recommendations': []},
		'rag': {'chunk_count': 2, 'retrieved_chunks_count': 1, 'section_fusion': ['a', 'b'], 'retrieved_chunks': []},
		'global_stats': {'rows': 120, 'anomalies': critical_count + high_count},
	}
	return payload


class PreprocessPayloadSafetyTests(SimpleTestCase):
	def test_small_payload_stays_valid(self):
		payload = _build_payload(critical_count=3, high_count=2, suspect_count=2, columns_count=5)
		prepared = _prepare_preprocess_llm_payload(payload)

		self.assertLessEqual(len(prepared['critical_anomalies']), 15)
		self.assertLessEqual(estimate_size(prepared), 6000)

	def test_wide_dataset_payload_is_reduced(self):
		payload = _build_payload(critical_count=25, high_count=12, suspect_count=8, columns_count=85, filler_size=40)
		prepared = _prepare_preprocess_llm_payload(payload)

		self.assertLessEqual(len(prepared['critical_anomalies']), 15)
		self.assertLessEqual(len(prepared['suspect_columns']), 3)
		self.assertLessEqual(estimate_size(prepared), 6000)

	def test_noisy_payload_is_hard_limited(self):
		payload = _build_payload(critical_count=50, high_count=30, suspect_count=10, columns_count=85, filler_size=120)
		prepared = _prepare_preprocess_llm_payload(payload)

		self.assertLessEqual(len(prepared['critical_anomalies']), 15)
		self.assertLessEqual(len(prepared['high_anomalies']), 5)
		self.assertLessEqual(len(prepared['suspect_columns']), 3)
		self.assertLessEqual(estimate_size(prepared), 6000)

	def test_validation_accepts_unknown_columns(self):
		payload = _build_payload(critical_count=1, high_count=1, suspect_count=1, columns_count=5)
		payload['critical_anomalies'][0]['column'] = 'creatinine_basale'
		payload['critical_anomalies'][0]['value'] = 1.23
		payload['suspect_columns'] = ['sodium_basal', 'unknown_clinical_field']
		payload['dataset_quality_score'] = 42

		self.assertTrue(validate_payload(payload, technical_profile=payload['technical_profile']))
		self.assertEqual(payload['critical_anomalies'][0]['column'], 'creatinine')
		self.assertEqual(payload['suspect_columns'][0], 'sodium')
		self.assertEqual(payload['suspect_columns'][1], 'unknown_clinical_field')

	def test_validation_accepts_basale_column_without_metadata(self):
		payload = _build_payload(critical_count=1, high_count=0, suspect_count=1, columns_count=0)
		payload['critical_anomalies'][0]['column'] = 'creatinine_basale'
		payload['critical_anomalies'][0]['value'] = 2.5
		payload['suspect_columns'] = ['creatinine_basale']
		payload['dataset_quality_score'] = 10

		technical_profile = {}
		self.assertTrue(validate_payload(payload, technical_profile=technical_profile))
		self.assertEqual(payload['critical_anomalies'][0]['column'], 'creatinine')
		self.assertEqual(payload['suspect_columns'][0], 'creatinine')

	def test_schema_only_validation_rejects_missing_required_keys(self):
		with self.assertRaises(ValueError):
			validate_payload_schema_only({'critical_anomalies': [], 'suspect_columns': [], 'dataset_quality_score': 1})

	def test_schema_only_validation_accepts_required_shape(self):
		payload = _build_payload(critical_count=0, high_count=0, suspect_count=0, columns_count=0)
		payload['dataset_quality_score'] = 5
		self.assertTrue(validate_payload_schema_only(payload))

	def test_deterministic_fallback_is_available(self):
		dataframe = pd.DataFrame({'creatinine': [1.1, 1.3], 'potassium': [4.2, 4.4]})
		technical_profile = {
			'missing_pct': 0,
			'duplicate_rows': 0,
			'numeric_columns_profile': [],
		}

		report = _build_deterministic_analysis_fallback(dataframe, technical_profile, 'invalid payload')

		self.assertIn('summary', report)
		self.assertIn('limitations', report)

	def test_final_confidence_decreases_on_noisy_payload(self):
		compact_summary = {
			'critical_anomalies': [{'column': 'creatinine', 'value': 9.9}] * 12,
			'high_anomalies': [{'column': 'potassium', 'value': 7.1}] * 8,
		}
		technical_profile = {
			'missing_pct': 22.5,
			'duplicate_rows': 3,
		}
		issues = [
			{'severity': 'critical', 'column': 'creatinine'},
			{'severity': 'warning', 'column': 'potassium'},
		]

		confidence = _compute_final_confidence(technical_profile, issues=issues, compact_summary=compact_summary)

		self.assertGreaterEqual(confidence['confidence_score'], 0.0)
		self.assertLessEqual(confidence['confidence_score'], 1.0)
		self.assertLess(confidence['confidence_score'], 0.85)
		self.assertIn(confidence['confidence_label'], ['elevee', 'bonne', 'moderee', 'faible'])

	def test_audit_event_includes_pipeline_version(self):
		payload = _build_payload(critical_count=1, high_count=1, suspect_count=1, columns_count=1)
		payload['dataset_quality_score'] = 7
		audit_event = _build_preprocess_audit_event(
			'session-123',
			'final_guard',
			payload,
			payload['technical_profile'],
		)

		self.assertEqual(audit_event['session_id'], 'session-123')
		self.assertIn('pipeline', audit_event)
		self.assertEqual(audit_event['pipeline']['version'], audit_event['pipeline_version'])
		self.assertIn('schema_version', audit_event['pipeline'])

	@patch('patients.views._load_preprocess_session')
	def test_replay_prefers_persisted_session_report(self, mock_load_session):
		mock_load_session.return_value = {
			'id': 'session-abc',
			'report': {
				'summary': {'quality_score': 88},
				'audit_log': [{'session_id': 'session-abc', 'pipeline_version': '2026.05.18-v2'}],
			},
		}

		replayed = replay_preprocess_pipeline({'session_id': 'session-abc'})

		self.assertTrue(replayed['replayed_from_audit'])
		self.assertEqual(replayed['summary']['quality_score'], 88)
		self.assertEqual(replayed['replay_source']['session_id'], 'session-abc')
