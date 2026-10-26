"""Synthetic occupancy fixtures; these do not claim to replay C19's lost state."""
import unittest
from types import SimpleNamespace
from qwen_split.relay_collision_receipt import receipt


class ReceiptTests(unittest.TestCase):
    def test_owners_match_guard_order_and_shave(self):
        inst = SimpleNamespace(name='tile', master='m', x=20, y=20, w=10, h=10)
        def p(name, frames):
            return dict(bid=name, bits=288, eps=[['a', 'y'], ['b', 'a']], P0=[0, 0], P1=[50, 50], frames=frames)
        plans = {1:p('old', [(10, 10, 10, 10)]), 2:p('bword_5', [(15, 15, 5, 5)]),
                 3:p('future', [(15, 15, 5, 5)])}
        r = receipt(dict(insts=[inst], die=dict(w=100, h=100)), plans, 2, 0, .1)
        self.assertEqual({x['owner'] for x in r['conflicting_owners']}, {'old', 'tile'})
        self.assertEqual(r['candidate']['rect'], [15, 15, 20.1, 20.1])
        self.assertFalse(r['outside_die'])
        self.assertNotIn('future', {x['owner'] for x in r['nearby_owners']})

    def test_current_frames_before_failure_only(self):
        p = dict(bid='word', bits=1, eps=[], P0=[0,0], P1=[10,10],
                 frames=[(0,0,4,4), (3,3,4,4), (3,3,4,4)])
        r = receipt(dict(insts=[], die=dict(w=5,h=5)), {0:p}, 0, 1, 0)
        self.assertEqual([x['frame'] for x in r['conflicting_owners']], [0])
        self.assertTrue(r['outside_die'])


if __name__ == '__main__':
    unittest.main()
