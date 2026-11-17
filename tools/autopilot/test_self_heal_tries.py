import json, os, tempfile, unittest
import kit_wave as KW


class Log:
    def __init__(self): self.l = []
    def log(self, m): self.l.append(m)


class Tries(unittest.TestCase):
    def setUp(self):
        self.f = tempfile.mktemp(suffix=".json"); os.environ["OT_SELF_HEAL_STATE"] = self.f

    def test_stops_after_two_tries_and_logs_once(self):
        t, ap = {}, Log()
        for _ in range(2):
            self.assertFalse(KW.heal_blocked(t, "k")); KW.heal_count(t, "k")
        self.assertTrue(KW.heal_blocked(t, "k"))
        KW.heal_stop_note(ap, t, "k", "X"); KW.heal_stop_note(ap, t, "k", "X")
        self.assertEqual(len(ap.l), 1); self.assertIn("STOPPED after 2", ap.l[0])
        self.assertTrue(KW.heal_blocked(t, "k"))

    def test_state_persists_and_healed_key_resets(self):
        t = {"a": 2, "b": 1}
        KW.heal_tries_save(t)
        t2 = KW.heal_tries_load(); self.assertEqual(t2, t)
        KW.heal_prune(t2, {"a"}); self.assertEqual(t2, {"a": 2})
        KW.heal_tries_save(t2); self.assertEqual(KW.heal_tries_load(), {"a": 2})

    def test_sync_item_inputs_gives_up_after_two_ticks(self):
        cfg = {"_item_incomplete": {"epyc8": {"s81": {"it1": "/srv/opentallas-scratch2/claude/x/f.json missing"}},
                                    "epyc10": {"s81": {}}},
               "dies": {"s81": {"gen_hosts": ["epyc8", "epyc10"]}}}
        ap, calls = Log(), []
        run = lambda argv, inp=None: (calls.append(1), 0)[1]
        for _ in range(4):
            KW.sync_item_inputs(ap, cfg, run=run)
        self.assertEqual(len(calls), 2)                              # tick 3 and 4 do nothing
        self.assertTrue(any("STOPPED" in m for m in ap.l))
