import os
import unittest
from contextlib import ExitStack
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch
import engine
from request_state import request_scope, RequestCancelled


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key', 'ANTHROPIC_API_KEY': 'test-key',
            'XAI_API_KEY': 'test-key', 'AI_TIMEOUT_SECONDS': '15'}, clear=True))
        # Prevent any developer .env from influencing these isolated tests.
        self.stack.enter_context(patch.dict('sys.modules', {'dotenv': None}))
        self.safety = self.stack.enter_context(patch.object(engine, 'safety_manager'))
        self.safety.check_action.return_value = {'allowed': True}
        self.factory = self.stack.enter_context(patch.object(engine, 'make_client'))
        self.client = self.factory.return_value.__enter__.return_value
        self.client.responses.create.return_value = SimpleNamespace(output_text='valid answer')
        engine.teacher_history.clear()
        self.addCleanup(engine.teacher_history.clear)

    def test_missing_key_is_lazy_and_provider_specific(self):
        os.environ.pop('ANTHROPIC_API_KEY')
        self.assertEqual(engine.ask_atlas('question'), 'valid answer')
        with self.assertRaises(engine.ModelError) as caught:
            engine.ask_claude('question')
        self.assertEqual(caught.exception.code, 'configuration')
        self.assertEqual(self.factory.call_count, 1)

    def test_council_preflight_spends_nothing_with_missing_key(self):
        os.environ.pop('XAI_API_KEY')
        result = engine.run_council('question')
        self.assertEqual(result['provider'], 'GROK')
        self.assertNotIn('final', result)
        self.factory.assert_not_called()

    def test_error_stops_council_at_every_stage(self):
        for failed_stage in range(7):
            with self.subTest(stage=failed_stage):
                results = ['answer'] * failed_stage + [engine.ModelError('ATLAS', 'timeout', 'timed out')]
                with patch.object(engine, 'ask_model', side_effect=results) as ask:
                    result = engine.run_council('question')
                self.assertNotIn('final', result)
                self.assertEqual(result['code'], 'timeout')
                self.assertEqual(ask.call_count, failed_stage + 1)

    def test_successful_council_has_seven_calls_and_final(self):
        with patch.object(engine, 'ask_model', side_effect=[f'answer {i}' for i in range(7)]) as ask:
            result = engine.run_council('question')
        self.assertEqual(result['final'], 'answer 6')
        self.assertEqual(ask.call_count, 7)
        self.assertIn('answer 3', ask.call_args.args[1])

    def test_timeout_is_safe_and_teacher_history_unchanged(self):
        self.client.responses.create.side_effect = TimeoutError('secret credential and prompt')
        with self.assertRaises(engine.ModelError) as caught:
            engine.ask_teacher('question')
        self.assertEqual(caught.exception.code, 'timeout')
        self.assertNotIn('secret', str(caught.exception))
        self.assertEqual(engine.teacher_history, [])

    def test_empty_response_is_not_a_success(self):
        for value in [None, '', '  ']:
            self.client.responses.create.return_value = SimpleNamespace(output_text=value)
            with self.assertRaises(engine.ModelError) as caught:
                engine.ask_atlas('question')
            self.assertEqual(caught.exception.code, 'empty_response')

    def test_kill_blocks_client_creation(self):
        self.safety.check_action.return_value = {'allowed': False, 'reason': 'Killed'}
        with self.assertRaises(engine.ModelError) as caught:
            engine.ask_atlas('question')
        self.assertEqual(caught.exception.code, 'blocked')
        self.factory.assert_not_called()

    def test_audit_failure_blocks_network(self):
        self.safety.check_action.side_effect = OSError('disk full')
        with self.assertRaises(engine.ModelError) as caught:
            engine.ask_atlas('question')
        self.assertEqual(caught.exception.code, 'audit')
        self.factory.assert_not_called()

    def test_cancellation_during_provider_does_not_save_teacher_turn(self):
        cancelled = Event()
        def response(**kwargs):
            cancelled.set()
            return SimpleNamespace(output_text='too late')
        self.client.responses.create.side_effect = response
        with self.assertRaises(RequestCancelled), request_scope(cancelled):
            engine.ask_teacher('question')
        self.assertEqual(engine.teacher_history, [])

    def test_timeout_and_model_configuration(self):
        os.environ['ATLAS_MODEL'] = 'configured-model'
        engine.ask_atlas('question')
        self.factory.assert_called_once_with('ATLAS', 'test-key', 15.0)
        self.client.responses.create.assert_called_once_with(model='configured-model', input='question')
        for invalid in ['0', '-1', 'nan', 'inf', 'bad']:
            os.environ['AI_TIMEOUT_SECONDS'] = invalid
            with self.assertRaises(engine.ModelError):
                engine.configuration('ATLAS')

    def test_auth_and_quota_errors_are_classified(self):
        for status, code in [(401, 'authentication'), (403, 'authentication'), (429, 'rate_limit')]:
            error = RuntimeError('sensitive request detail')
            error.status_code = status
            self.client.responses.create.side_effect = error
            with self.assertRaises(engine.ModelError) as caught:
                engine.ask_atlas('question')
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('sensitive', str(caught.exception))

    def test_cli_uses_shared_engine_and_exit_status(self):
        import main
        with patch.object(main, 'run_council', return_value={'error': 'blocked'}) as run, \
                patch('builtins.input', return_value='question'), patch('builtins.print'):
            self.assertEqual(main.main(), 1)
            run.assert_called_once_with('question')

if __name__ == '__main__':
    unittest.main()
