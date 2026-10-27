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
                    events = []
                    result = engine.run_council('question', progress=events.append)
                keys = [key for key, _ in engine.COUNCIL_STAGES]
                self.assertEqual(result['stage'], keys[failed_stage])
                self.assertEqual([result[k] for k in keys[:failed_stage]], ['answer'] * failed_stage)
                self.assertEqual(len(events), failed_stage + 1)
                self.assertEqual(len(events[-1]['answers']), failed_stage)
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

    def claude_response(self, content, reason='end_turn'):
        self.client.messages.create.return_value = SimpleNamespace(
            content=content, stop_reason=reason,
            usage=SimpleNamespace(input_tokens=100, output_tokens=1600))

    def test_claude_parses_all_text_blocks_and_ignores_thinking(self):
        self.claude_response([SimpleNamespace(type='thinking', thinking='PRIVATE'),
                             SimpleNamespace(type='text', text='first'),
                             SimpleNamespace(type='text', text='second')])
        self.assertEqual(engine.ask_claude('PRIVATE PROMPT'), 'first\nsecond')
        kwargs = self.client.messages.create.call_args.kwargs
        self.assertEqual(kwargs['model'], 'claude-sonnet-5')
        self.assertEqual(kwargs['max_tokens'], 1600)
        self.assertEqual(kwargs['thinking'], {'type': 'disabled'})
        self.assertEqual(self.client.messages.create.call_count, 1)

    def test_claude_empty_completed_responses_have_safe_diagnostics(self):
        for blocks in ([], None, [SimpleNamespace(type='text', text='  ')],
                       [SimpleNamespace(type='thinking', thinking='PRIVATE')],
                       [SimpleNamespace(type='PRIVATE', text='PRIVATE')],
                       [SimpleNamespace(type='text', text=None)]):
            with self.subTest(blocks=blocks):
                self.claude_response(blocks)
                with self.assertRaises(engine.ModelError) as caught:
                    engine.ask_claude('PRIVATE PROMPT')
                error = caught.exception
                self.assertEqual(error.code, 'empty_response')
                self.assertEqual(error.diagnostics['stop_reason'], 'end_turn')
                self.assertEqual(error.diagnostics['output_tokens'], 1600)
                self.assertNotIn('PRIVATE', str(error))
                self.assertNotIn('test-key', str(error))

    def test_claude_token_limit_rejects_empty_and_partial_answers_without_retry(self):
        for blocks in ([], [SimpleNamespace(type='thinking', thinking='PRIVATE')],
                       [SimpleNamespace(type='text', text='PRIVATE PARTIAL')]):
            self.client.messages.create.reset_mock()
            self.claude_response(blocks, 'max_tokens')
            with self.assertRaises(engine.ModelError) as caught:
                engine.ask_claude('PRIVATE PROMPT')
            self.assertEqual(caught.exception.code, 'token_limit')
            self.assertIn('CLAUDE_MAX_TOKENS', str(caught.exception))
            self.assertNotIn('PRIVATE', str(caught.exception))
            self.assertEqual(self.client.messages.create.call_count, 1)

    def test_claude_nonfinal_stop_reasons_are_failures(self):
        for reason, code in [('model_context_window_exceeded', 'context_limit'),
                             ('refusal', 'refusal'), ('tool_use', 'incomplete_response'),
                             ('pause_turn', 'incomplete_response'),
                             ('PRIVATE', 'incomplete_response'), (None, 'incomplete_response')]:
            self.claude_response([SimpleNamespace(type='text', text='PRIVATE')], reason)
            with self.assertRaises(engine.ModelError) as caught:
                engine.ask_claude('q')
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('PRIVATE', str(caught.exception))

    def test_claude_custom_budget_and_model_do_not_assume_thinking_support(self):
        os.environ['CLAUDE_MODEL'] = 'claude-sonnet-5-5'
        os.environ['CLAUDE_MAX_TOKENS'] = '2400'
        self.claude_response([SimpleNamespace(type='text', text='answer')])
        self.assertEqual(engine.ask_claude('q'), 'answer')
        kwargs = self.client.messages.create.call_args.kwargs
        self.assertEqual(kwargs['max_tokens'], 2400)
        self.assertEqual(kwargs['model'], 'claude-sonnet-5-5')
        self.assertNotIn('thinking', kwargs)

    def test_claude_invalid_budget_blocks_council_preflight(self):
        for value in ['0', '-1', '128001', '1.5', 'nan', 'PRIVATE']:
            os.environ['CLAUDE_MAX_TOKENS'] = value
            result = engine.run_council('q')
            self.assertEqual(result['code'], 'configuration')
            self.assertNotIn('PRIVATE', result['error'])
        self.factory.assert_not_called()

    def test_claude_http_errors_do_not_expose_response_body(self):
        for status, code in [(400, 'invalid_request'), (404, 'model_not_found')]:
            error = RuntimeError('PRIVATE PROMPT test-key')
            error.status_code = status
            self.client.messages.create.side_effect = error
            with self.assertRaises(engine.ModelError) as caught:
                engine.ask_claude('PRIVATE PROMPT')
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('PRIVATE', str(caught.exception))
            self.assertNotIn('test-key', str(caught.exception))

    def test_claude_token_limit_stops_council_with_diagnostics(self):
        self.claude_response([], 'max_tokens')
        result = engine.run_council('PRIVATE PROMPT')
        self.assertEqual(result['code'], 'token_limit')
        self.assertEqual(result['diagnostics']['stop_reason'], 'max_tokens')
        self.assertNotIn('final', result)
        self.assertNotIn('PRIVATE', str(result))
        self.assertEqual(self.factory.call_count, 2)

    def test_claude_kill_and_cancellation_preserved(self):
        self.safety.check_action.return_value = {'allowed': False, 'reason': 'Killed'}
        with self.assertRaises(engine.ModelError):
            engine.ask_claude('q')
        self.factory.assert_not_called()
        self.safety.check_action.return_value = {'allowed': True}
        event = Event()
        def response(**kwargs):
            event.set()
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='late')], stop_reason='end_turn')
        self.client.messages.create.side_effect = response
        with self.assertRaises(RequestCancelled), request_scope(event):
            engine.ask_claude('q')

    def test_cli_uses_shared_engine_and_exit_status(self):
        import main
        with patch.object(main, 'run_council', return_value={'error': 'blocked'}) as run, \
                patch('builtins.input', return_value='question'), patch('builtins.print'):
            self.assertEqual(main.main(), 1)
            run.assert_called_once_with('question')

if __name__ == '__main__':
    unittest.main()
