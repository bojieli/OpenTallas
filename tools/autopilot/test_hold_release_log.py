import tempfile
import unittest
import kit_wave as KW


class AP:
    DRY = False

    def __init__(self):
        self.logs = []

    def log(self, m):
        self.logs.append(m)


class Once(unittest.TestCase):
    def test_one_line_per_key_change(self):
        d, ap = tempfile.mkdtemp(), AP()
        e = [("s81", "k1", "proof ok"), ("s81", "k2", "tree ready")]
        self.assertEqual(KW.log_hold_releases(ap, d, e, "release_on met", reset=True), 2)
        for _ in range(5):                                        # the next ticks: same release, no new line
            self.assertEqual(KW.log_hold_releases(ap, d, e, "release_on met", reset=True), 0)
        self.assertEqual(len(ap.logs), 2)
        self.assertEqual(KW.log_hold_releases(ap, d, [("s81", "k1", "proof ok v2")], "release_on met", reset=True), 1)   # the condition changed
        self.assertEqual(KW.log_hold_releases(ap, d, e, "release_on met", reset=True), 2)       # k2 left and returned: logs again; k1 old cond is new again
        self.assertEqual(KW.log_hold_releases(ap, d, e, "release terms met"), 0)

    def test_second_call_of_a_tick_keeps_the_first_calls_keys(self):
        d, ap = tempfile.mkdtemp(), AP()
        KW.log_hold_releases(ap, d, [("a", "k", "c")], "x", reset=True)
        KW.log_hold_releases(ap, d, [("b", "k", "c")], "y")                      # no reset: a/k/c stays known
        self.assertEqual(KW.log_hold_releases(ap, d, [("a", "k", "c")], "x"), 0)
