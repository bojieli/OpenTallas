"""KW-FIX-46 11-12 (COORD ruling by intent): HBM type rows yield only to phase-1 waiters on the same host, within the
CPU share; the gen host is then limited to the calm hosts"""
import unittest
from unittest import mock
import kit_wave as K


def cfg():
    return {"phase_split": {"enabled": True, "low_dies": ["hbm"], "reserved_threads": 96, "thread_per_row": 8},
            "_hub": "intel2",
            "_otrun_status": {"epyc7": {"admit": 400, "cores": 96, "load": 103}, "epyc8": {"admit": 200, "cores": 96, "load": 148},
                              "epyc9": {"admit": 650, "cores": 96, "load": 25}},
            "dies": {"hbm": {"gen_host": "epyc9", "gen_hosts": ["epyc7", "epyc9", "epyc8"]}, "s81": {"gen_host": "epyc8"}}}


def rows(n):
    return [("hbm", {"item": f"t{i}", "kind": "type"}) for i in range(n)]


class PhaseCalm(unittest.TestCase):
    def test_waiters_elsewhere_release_to_calm_host_within_share(self):
        c = cfg()
        with mock.patch.object(K, "volume_started", return_value=False):
            out, note = K.phase_split_apply(c, {"items": {}}, [rows(20)], waiting={"epyc7": 30, "epyc8": 20})
        self.assertEqual(len(out[0]), 12)                 # 96 / 8 rows, none in flight
        self.assertEqual(c["_phase_calm_hosts"]["hbm"], ["epyc9"])
        self.assertEqual(K.gen_hosts(c, "hbm"), ["epyc9"])

    def test_waiting_rows_do_not_use_the_share(self):
        c = cfg()
        st = {"items": {str(i): {"die": "hbm", "status": "RUNNING", "item": f"r{i}"} for i in range(13)}}
        with mock.patch.object(K, "volume_started", return_value=False):
            out, _ = K.phase_split_apply(c, st, [rows(20)], waiting={"epyc7": 3})
        self.assertEqual(len(out[0]), 12)
        with mock.patch.object(K, "volume_started", return_value=True):
            out, _ = K.phase_split_apply(cfg(), st, [rows(20)], waiting={"epyc7": 3})
        self.assertEqual(len(out[0]), 0)                  # 13 x 8 = 104 >= 96 really running

    def test_picks_still_block(self):
        c = cfg()
        out, _ = K.phase_split_apply(c, {"items": {}}, [[("s81", {"item": "a", "kind": "type"})], rows(5)], waiting={})
        self.assertNotIn("hbm", c.get("_phase_calm_hosts") or {})


if __name__ == "__main__":
    unittest.main()
