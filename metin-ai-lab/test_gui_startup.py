"""Opt-in real Tk tests: METIN_GUI_TESTS=1 python3 -m unittest test_gui_startup -v."""
import os
from pathlib import Path
import runpy
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import engine
import project_context as context


@unittest.skipUnless(os.getenv('METIN_GUI_TESTS') == '1', 'requires a real display; set METIN_GUI_TESTS=1')
class GuiStartupTests(unittest.TestCase):
    def test_real_window_menu_event_loop_context_and_history(self):
        original_mainloop = tk.Misc.mainloop
        failures = []
        ticks = []
        with tempfile.TemporaryDirectory() as directory:
            def isolated_history(project):
                return Path(directory) / str(context.PROJECTS.index(project)) / 'ideas.jsonl'

            def instrumented_mainloop(root, *args, **kwargs):
                app = sys._getframe(1).f_globals

                def inspect():
                    try:
                        self.assertTrue(root.winfo_viewable())
                        self.assertEqual(float(root.attributes('-alpha')), 1.0)
                        self.assertIn('METIN AI LAB v0.3', root.title())
                        self.assertEqual(app['title'].cget('text'), 'METIN AI LAB v0.3')
                        menu = app['project_menu']['menu']
                        labels = [menu.entrycget(i, 'label') for i in range(menu.index('end') + 1)]
                        self.assertIn(context.GAME, labels)
                        menu.invoke(labels.index(context.GAME))
                        self.assertEqual(app['selected_project'], context.GAME)
                        self.assertEqual(app['project_var'].get(), context.GAME)
                        self.assertIn('British humour', app['results'].get('1.0', 'end'))
                        with patch.object(engine, 'configuration'), \
                                patch.object(engine, 'project_prompt', side_effect=lambda p, m, q: f'{p} {m} ROLE\n'), \
                                patch.object(engine, 'ask_model', return_value='test idea') as model:
                            request = app['requests'].start('GUI test question', context.GAME, 'COUNCIL')
                            app['run_selected_mode'](request)
                            app['poll_results']()
                        self.assertEqual(model.call_count, 7)
                        for call in model.call_args_list:
                            self.assertIn(context.GAME, call.args[1])
                        self.assertIn('GUI test question', context.read_history(context.GAME))
                        app['show_history']()
                        windows = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
                        self.assertEqual(len(windows), 1)
                        def descendants(widget):
                            for child in widget.winfo_children():
                                yield child
                                yield from descendants(child)
                        history_boxes = [w for w in descendants(windows[0]) if isinstance(w, tk.Text)]
                        self.assertIn('GUI test question', history_boxes[0].get('1.0', 'end'))
                        app['set_project']('General')
                        self.assertNotIn('GUI test question', context.read_history('General'))
                        app['set_mode']('TEACHER')
                        self.assertEqual(app['ask_button'].cget('text'), 'ASK TEACHER')
                        ticks.append('inspected')
                    except BaseException as error:
                        failures.append(error)

                def finish():
                    ticks.append('still running')
                    app['close_app']()

                root.after(150, inspect)
                root.after(900, finish)
                return original_mainloop(root, *args, **kwargs)

            with patch.object(context, 'history_path', side_effect=isolated_history), \
                    patch.object(tk.Misc, 'mainloop', instrumented_mainloop):
                runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
            if failures:
                raise failures[0]
            self.assertEqual(ticks, ['inspected', 'still running'])
            # Re-read disk after the application has exited, using the same project key.
            self.assertIn('test idea', isolated_history(context.GAME).read_text(encoding='utf-8'))
