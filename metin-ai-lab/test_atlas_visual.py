"""Verify animation lifecycle without requiring a graphical display."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from atlas_visual import AtlasVisual
from test_request_flow import gui_functions


class AtlasVisualTests(unittest.TestCase):
    def visual(self, state='ready'):
        # Use the real animation methods with a headless Canvas stand-in.
        visual = SimpleNamespace(state=lambda: state, angle=20, timer=None,
                                 closed=False, motion=True, arcs=[1, 2, 3],
                                 dot=4, label=5, itemconfigure=Mock(),
                                 coords=Mock(), after=Mock(return_value='timer'),
                                 after_cancel=Mock())
        visual.tick = lambda: AtlasVisual.tick(visual)
        return visual

    def test_thinking_moves_faster_and_uses_single_timer(self):
        ready, thinking = self.visual(), self.visual('thinking')
        ready.tick(); thinking.tick()
        self.assertGreater(thinking.angle, ready.angle)
        thinking.after.assert_called_once_with(40, thinking.tick)
        self.assertEqual(thinking.timer, 'timer')

    def test_kill_and_cancel_stop_rotation(self):
        for state, label in [('killed', 'STOPPED'), ('cancelled', 'STOPPING')]:
            visual = self.visual(state)
            visual.tick()
            self.assertEqual(visual.angle, 20)
            self.assertEqual(visual.itemconfigure.call_args.kwargs['text'], label)

    def test_reduced_motion_and_shutdown(self):
        visual = self.visual('thinking')
        AtlasVisual.set_motion(visual, False)
        visual.tick()
        self.assertEqual(visual.angle, 20)
        AtlasVisual.stop(visual)
        visual.after_cancel.assert_called_once_with('timer')
        visual.after.reset_mock()
        visual.tick()
        visual.after.assert_not_called()

    def test_status_tracks_real_request_and_kill_state(self):
        env = gui_functions()
        state = env['atlas_visual_state']
        self.assertEqual(state(), 'ready')
        request = env['requests'].start('q', 'Original', 'ATLAS')
        self.assertEqual(state(), 'thinking')
        env['requests'].cancel()
        self.assertEqual(state(), 'cancelled')
        env['safety_manager'].killed = True
        self.assertEqual(state(), 'killed')
        env['safety_manager'].killed = False
        self.assertEqual(state(), 'cancelled')
        env['requests'].finish(request)
        self.assertEqual(state(), 'ready')

if __name__ == '__main__':
    unittest.main()
