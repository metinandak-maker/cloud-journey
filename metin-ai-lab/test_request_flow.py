import ast
import queue
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from request_state import RequestState, RequestCancelled, request_scope, cancellable


def gui_functions():
    tree = ast.parse(Path(__file__).with_name('app.py').read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    env = {'tk': SimpleNamespace(END='end'), 'requests': RequestState(),
           'completed': queue.Queue(), 'queue': queue,
           'safety_manager': SimpleNamespace(killed=False),
           'root': Mock(), 'ask_button': Mock(), 'safety_status_label': Mock(),
           'status_label': Mock(), 'results': Mock(), 'question_box': Mock(),
           'selected_mode': 'ATLAS', 'selected_project': 'Other',
           'project_response_cache': {'Original': {}, 'Other': {}},
           'teacher_history': [], 'last_final_answer': ''}
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'app.py', 'exec'), env)
    env['stop_thinking_animation'] = Mock()
    return env


class RequestTests(unittest.TestCase):
    def test_cancelled_provider_does_not_continue_council(self):
        state = RequestState()
        request = state.start('q', 'p', 'COUNCIL')
        later = Mock()
        @cancellable
        def provider():
            state.cancel()
            return 'late answer'
        with self.assertRaises(RequestCancelled):
            with request_scope(request.cancelled):
                provider()
                later()
        later.assert_not_called()

    def test_reset_cannot_revive_cancelled_request(self):
        state = RequestState()
        request = state.start('q', 'p', 'ATLAS')
        state.cancel()
        self.assertTrue(state.busy)
        with self.assertRaises(RuntimeError):
            state.start('new', 'p', 'ATLAS')
        self.assertTrue(request.cancelled.is_set())
        self.assertTrue(state.finish(request))
        newer = state.start('new', 'p', 'ATLAS')
        self.assertFalse(state.finish(request))
        self.assertIs(state.active, newer)

    def test_result_uses_original_project(self):
        e = gui_functions()
        request = e['requests'].start('original', 'Original', 'ATLAS')
        e['completed'].put((request, 'answer', None))
        e['poll_results']()
        self.assertIn('answer', e['project_response_cache']['Original']['ATLAS'])
        self.assertEqual(e['project_response_cache']['Other'], {})
        e['results'].insert.assert_not_called()
        self.assertFalse(e['requests'].busy)

    def test_new_chat_discards_late_answer(self):
        e = gui_functions()
        e['response_cache'] = {}
        request = e['requests'].start('q', 'Original', 'ATLAS')
        e['new_chat']()
        e['results'].reset_mock()
        e['completed'].put((request, 'stale', None))
        e['poll_results']()
        e['results'].insert.assert_not_called()
        self.assertEqual(e['project_response_cache']['Original'], {})

    def test_killed_completion_keeps_ask_disabled(self):
        e = gui_functions()
        request = e['requests'].start('q', 'Original', 'ATLAS')
        e['requests'].cancel()
        e['safety_manager'].killed = True
        e['completed'].put((request, 'late', None))
        e['poll_results']()
        e['ask_button'].config.assert_called_with(state='disabled')

    def test_archive_uses_submitted_question(self):
        e = gui_functions()
        e['archive_result'] = Mock()
        request = e['requests'].start('original question', 'Original', 'COUNCIL')
        answer = dict.fromkeys(['atlas', 'claude', 'grok', 'atlas_review',
                               'claude_review', 'grok_review', 'final'], 'answer')
        e['show_results'](answer, request)
        e['archive_result'].assert_called_once_with('original question', 'answer')
        e['question_box'].get.assert_not_called()

    def test_archive_failure_does_not_lose_answer_or_lock_ui(self):
        e = gui_functions()
        e['archive_result'] = Mock(side_effect=OSError('disk full'))
        request = e['requests'].start('q', 'Original', 'COUNCIL')
        answer = dict.fromkeys(['atlas', 'claude', 'grok', 'atlas_review',
                               'claude_review', 'grok_review', 'final'], 'answer')
        e['completed'].put((request, answer, None))
        e['poll_results']()
        self.assertIn('Archive failed', e['project_response_cache']['Original']['COUNCIL'])
        e['ask_button'].config.assert_called_with(state='normal')

    def test_reset_during_request_keeps_ask_disabled(self):
        e = gui_functions()
        e['requests'].start('q', 'Original', 'ATLAS')
        e['update_safety_ui']()
        e['ask_button'].config.assert_called_with(state='disabled')

if __name__ == '__main__':
    unittest.main()
