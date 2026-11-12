#!/usr/bin/env python3
"""KW-FIX-45 11-12: phase split (phase 1 S81/HEAD/QC/KV first, HBM behind; cores and a 96-thread share exempt; release switch)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

def rows(die, n, kind="type", prefix="t"):
    return [(die, {"item": f"{prefix}{i}", "kind": kind}) for i in range(n)]

CFG = {"phase_split": {"enabled": True, "low_dies": ["hbm"], "reserved_threads": 16, "priority_items": ["CORES-*"]}}

class T(unittest.TestCase):
    def test_hbm_waits_while_phase1_has_picks(self):
        pd = [rows("s81", 5), rows("hbm", 6)]
        out, note = kw.phase_split_apply(CFG, {"items": {}}, pd)
        self.assertEqual(len(out[0]), 5)
        self.assertEqual(len(out[1]), 2)                  # reserved 16 threads / 8 per row = 2 type rows of the guaranteed share
        self.assertIn("4 hbm type rows wait", note)

    def test_share_counts_inflight(self):
        st = {"items": {"a": {"die": "hbm", "status": "RUNNING"}, "b": {"die": "hbm", "status": "RUNNING"}}}
        out, _ = kw.phase_split_apply(CFG, st, [rows("qwen_kvsys", 3), rows("hbm", 4)])
        self.assertEqual(len(out[1]), 0)

    def test_cores_exempt(self):
        pd = [rows("s81", 3), rows("hbm", 3, kind="core", prefix="x") + rows("hbm", 2, prefix="CORES-")]
        out, _ = kw.phase_split_apply(dict(CFG, phase_split=dict(CFG["phase_split"], reserved_threads=0)), {"items": {}}, pd)
        self.assertEqual(len(out[1]), 5)

    def test_hbm_runs_when_phase1_idle(self):
        out, note = kw.phase_split_apply(CFG, {"items": {}}, [rows("s81", 0), rows("hbm", 6)])
        self.assertEqual(len(out[1]), 6); self.assertEqual(note, "")

    def test_waiting_phase1_rows_block_hbm_type_rows(self):
        cfg = dict(CFG, dies={"hbm": {"hosts": ["epyc8", "epyc9"], "gen_hosts": ["epyc9"]}})
        cfg["phase_split"] = dict(CFG["phase_split"], reserved_threads=0)
        # no phase-1 picks this tick, but 3 phase-1 rows already wait on epyc9: hbm type rows stay held, cores run
        pd = [rows("s81", 0), rows("hbm", 4) + rows("hbm", 1, kind="core", prefix="c")]
        out, note = kw.phase_split_apply(cfg, {"items": {}}, pd, waiting={"epyc9": 3})
        self.assertEqual([r["item"] for _, r in out[1]], ["c0"])
        self.assertIn("3 phase-1 waiters", note)
        # waiters on a host the hbm die cannot use do not block
        out, _ = kw.phase_split_apply(cfg, {"items": {}}, [rows("s81", 0), rows("hbm", 4)], waiting={"epyc2": 9})
        self.assertEqual(len(out[1]), 4)
        out, _ = kw.phase_split_apply(cfg, {"items": {}}, [rows("s81", 0), rows("hbm", 4)], waiting={})
        self.assertEqual(len(out[1]), 4)

    def test_release_switch(self):
        for ps in ({"enabled": True, "release": True}, {"enabled": True, "phase1_done_pct": 91}, {"enabled": False}):
            out, _ = kw.phase_split_apply({"phase_split": ps}, {"items": {}}, [rows("s81", 5), rows("hbm", 6)])
            self.assertEqual(len(out[1]), 6)
        out, _ = kw.phase_split_apply({"phase_split": {"enabled": True, "phase1_done_pct": 89, "reserved_threads": 0}}, {"items": {}}, [rows("s81", 5), rows("hbm", 6)])
        self.assertEqual(len(out[1]), 0)

if __name__ == "__main__":
    unittest.main()
