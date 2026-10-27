import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

import engine
import project_context as context
from request_state import RequestCancelled, request_scope
from test_request_flow import gui_functions


class ProjectTests(unittest.TestCase):
    def test_evidence_is_allowlisted_and_missing_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('Documented intention: test shop')
            (root / '.env').write_text('PRIVATE_SECRET')
            with patch.object(context, 'GAME_ROOT', root):
                prompt = context.project_prompt(context.GAME, 'CLAUDE', 'ideas?')
            self.assertIn('test shop', prompt)
            self.assertIn('British humour', prompt)
            self.assertIn('unavailable', prompt)
            self.assertIn('not proof of implementation', prompt)
            self.assertNotIn('PRIVATE_SECRET', prompt)
            self.assertNotIn('test shop', context.project_prompt('General', 'ATLAS', 'q'))

    def test_symlink_cannot_escape_evidence_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game = root / 'game'
            game.mkdir()
            secret = root / 'secret'
            secret.write_text('DO_NOT_SEND')
            (game / 'README.md').symlink_to(secret)
            with patch.object(context, 'GAME_ROOT', game):
                self.assertNotIn('DO_NOT_SEND', context.project_prompt(context.GAME, 'ATLAS', 'q'))

    def test_persistent_full_sessions_are_separate(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(Path, 'home', return_value=Path(directory)):
            council = {'atlas': 'idea', 'atlas_review': 'review', 'final': 'recommendation'}
            context.save_session(context.GAME, 'private question', council)
            self.assertIn('private question', context.read_history(context.GAME))
            self.assertIn('pending human approval', context.read_history(context.GAME))
            self.assertIn('atlas_review', context.read_history(context.GAME))
            self.assertNotIn('private question', context.read_history('General'))
            self.assertNotEqual(context.history_path('a/b'), context.history_path('a_b'))

    def test_game_roles_reach_every_round_and_judge(self):
        with patch.object(engine, 'configuration'), patch.object(engine, 'project_prompt',
                side_effect=lambda project, provider, q: f'{project}: {provider} ROLE\n'), \
                patch.object(engine, 'ask_model', return_value='idea') as ask:
            result = engine.run_council('question', context.GAME)
        self.assertIn('final', result)
        self.assertEqual(ask.call_count, 7)
        for call in ask.call_args_list:
            self.assertIn(f'{context.GAME}: {call.args[0]} ROLE', call.args[1])

    def test_teacher_conversations_are_separate(self):
        with patch.object(engine, 'ask_atlas', return_value='lesson') as ask:
            try:
                engine.ask_teacher('PRIVATE_LESSON', context.GAME)
                engine.ask_teacher('other lesson', 'Pip')
                self.assertNotIn('PRIVATE_LESSON', ask.call_args.args[0])
            finally:
                engine.teacher_histories.pop(context.GAME, None)
                engine.teacher_histories.pop('Pip', None)

    def test_cancelled_council_is_not_archived(self):
        env = gui_functions()
        from unittest.mock import Mock, ANY
        env['archive_result'] = Mock()
        request = env['requests'].start('q', 'Original', 'COUNCIL')
        env['requests'].cancel()
        env['completed'].put((request, {'final': 'late'}, None))
        env['poll_results']()
        env['archive_result'].assert_not_called()

    def test_worker_routes_original_project(self):
        env = gui_functions()
        from unittest.mock import Mock, ANY
        env.update(request_scope=request_scope, RequestCancelled=RequestCancelled,
                   run_council=Mock(return_value={'final': 'idea'}),
                   ask_atlas=Mock(), ask_claude=Mock(), ask_grok=Mock(), ask_teacher=Mock())
        request = env['requests'].start('q', 'Original', 'COUNCIL')
        env['run_selected_mode'](request)
        env['run_council'].assert_called_once_with('q', project='Original', progress=ANY)
        callback = env['run_council'].call_args.kwargs['progress']
        callback({'stage': 'atlas'})
        self.assertEqual(env['council_progress'].get_nowait(), (request, {'stage': 'atlas'}))


if __name__ == '__main__':
    unittest.main()
