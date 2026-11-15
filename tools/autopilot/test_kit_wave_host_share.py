"""KW-FIX-46 11-12: cfg host_share weights gen-host choice (COORD: epyc9 drains epyc7/8 waiters first)"""
import unittest
import kit_wave as K


def cfg(share=None):
    c = {"dies": {"s81": {"gen_host": "epyc8", "gen_hosts": ["epyc8", "epyc9"]}}, "_hub": "intel2",
         "_otrun_status": {"epyc8": {"admit": 400, "cores": 96, "load": 40, "wait_gb": 0},
                           "epyc9": {"admit": 300, "cores": 96, "load": 40, "wait_gb": 0}}}
    if share is not None:
        c["host_share"] = share
    return c


class HostShare(unittest.TestCase):
    def test_default_one(self):
        self.assertEqual(K.host_share({}, "x"), 1.0)
        self.assertEqual(K.host_share({"host_share": {"x": "bad"}}, "x"), 1.0)

    def test_share_flips_pick(self):
        c = cfg()
        base = K.pick_gen_host(c, "s81")
        c2 = cfg({"epyc9": 3.0})
        self.assertEqual(base, "epyc8")
        self.assertEqual(K.pick_gen_host(c2, "s81"), "epyc9")


class NoLoadCapPick(unittest.TestCase):
    def test_load_hold_off_skips_capped(self):
        c = {"load_hold": False, "dies": {"hbm": {"gen_host": "epyc8", "gen_hosts": ["epyc8", "epyc9"]}}, "_hub": "intel2",
             "_otrun_status": {"epyc8": {"admit": 2000, "cores": 96, "load": 148, "wait_gb": 0},
                               "epyc9": {"admit": 300, "cores": 96, "load": 25, "wait_gb": 0}}}
        self.assertEqual(K.pick_gen_host(c, "hbm"), "epyc9")


if __name__ == "__main__":
    unittest.main()
