#!/usr/bin/env python3
"""DIE-HBM-89-TGEN 11-07 (HBM q_b000 / q_b000__physical_v1 / q_b001 / q_b001__physical_v1 FAIL @gen 19:0x, 'bus L14_o is
not bound to any leaf port'): the plan-wrapper gen (no kit_rtl) binds a bus only via buses[].leaf / contents[].bind.
The probe lists such unbound buses per type; plan_entry_block keeps those types out of the wave (NEEDS-BIND, no FAIL
row) on a die without kit_rtl; dies with kit_rtl (bound RTL), kind=core items, hard types and the opt-out launch as
before; a gen log with the error classifies as PLAN instead of 'unclassified'."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def probe(plan, **kw):
    with tempfile.TemporaryDirectory() as d:
        pp = Path(d) / "plan.json"
        pp.write_text(json.dumps(plan))
        out = subprocess.run([sys.executable, "-c", KW.PROBE_PLAN, json.dumps(dict(plan=str(pp), **kw))],
                             capture_output=True, text=True, cwd=d)
        return json.loads(out.stdout.split("AP_JSON ", 1)[1])


PLAN = {"partition_types": {
    # HBM d44v form: one reuse content, buses with no leaf and an empty bind (q_b000)
    "q_b000": {"contents": [{"inst": "u_hcb_Q0", "module": "ot_hbm_hc_bankq0_static", "status": "reuse"}],
               "buses": [{"name": "L14_o", "dir": "out", "width": 8}, {"name": "L65_i", "dir": "in", "width": 8}]},
    # bound through buses[].leaf and contents[].bind
    "bound": {"contents": [{"inst": "u", "module": "m", "bind": {"q": "bus:d_o", "clk": "clk"}}],
              "buses": [{"name": "d_i", "dir": "in", "width": 4, "leaf": "u.d"}, {"name": "d_o", "dir": "out", "width": 4}]},
    # one of two buses bound
    "half": {"contents": [{"inst": "u", "module": "m", "bind": {"q": "bus:a_o"}}],
             "buses": [{"name": "a_o", "dir": "out", "width": 1}, {"name": "b_i", "dir": "in", "width": 1}]},
    # pure feedthrough type, no buses (HBM vsN1 / q_mca: gen passes)
    "vsN1": {"contents": [{"inst": "u", "module": "ft"}], "ft_slots": [{"name": "L1x1", "width": 4}]},
    "hardt": {"hard": True, "buses": [{"name": "p_o", "dir": "out", "width": 1}]}}}


class Unbound(unittest.TestCase):
    def setUp(self):
        self.res = probe(PLAN)
        self.d = {"event": "d44v", "_plan_flags": self.res["flags"], "_plan_unbound": self.res["unbound"],
                  "_plan_deps": self.res["deps"]}

    def test_probe_lists_unbound_buses(self):
        self.assertEqual(self.res["probe_v"], KW.PROBE_V)
        self.assertEqual(self.res["unbound"], {"q_b000": ["L14_o", "L65_i"], "half": ["b_i"]})

    def test_no_kit_rtl_blocks_unbound_types_only(self):
        why = KW.plan_entry_block(self.d, "q_b000", "type")
        self.assertTrue(why.startswith("NEEDS-BIND"), why)
        self.assertIn("L14_o", why)
        self.assertTrue(KW.plan_entry_block(self.d, "half", "type").startswith("NEEDS-BIND"))
        self.assertIsNone(KW.plan_entry_block(self.d, "bound", "type"))
        self.assertIsNone(KW.plan_entry_block(self.d, "vsN1", "type"))
        self.assertTrue(KW.plan_entry_block(self.d, "hardt", "type").startswith("plan entry: hard type"))

    def test_kit_rtl_core_and_opt_out_launch(self):
        for kr in ({"mode": "bind", "asbuilt": "a.json"}, {"mode": "script", "script": "k.sh"}):
            self.assertIsNone(KW.plan_entry_block(dict(self.d, kit_rtl=kr), "q_b000", "type"))
        self.assertTrue(KW.plan_entry_block(dict(self.d, kit_rtl={}), "q_b000", "type").startswith("NEEDS-BIND"))
        self.assertIsNone(KW.plan_entry_block(self.d, "q_b000", "core"))
        self.assertIsNone(KW.plan_entry_block(dict(self.d, unbound_launch=True), "q_b000", "type"))
        # a die state without the new probe key (older cached probe / other callers): unchanged behaviour
        self.assertIsNone(KW.plan_entry_block({"event": "e", "_plan_flags": self.res["flags"]}, "q_b000"))

    def test_select_skips_with_reason(self):
        rows = [dict(die="hbm", item=t, kind="type", state="NEEDS-KIT", owner="KIT-WAVE", live_job="none",
                     last_activity="", next_step="", evidence="", default_owner="", replicas="1", members="")
                for t in ("q_b000", "bound", "vsN1")]
        cfg = {"dies": {"hbm": dict(self.d, kinds=["core", "type"])}}
        picked, skip = KW.select(rows, cfg, "hbm", {"items": {}}, plan_types=set(PLAN["partition_types"]))
        self.assertEqual(sorted(r["item"] for r in picked), ["bound", "vsN1"])
        self.assertEqual([v for k, v in skip.items() if k.startswith("NEEDS-BIND")], [["q_b000"]])

    def test_gen_log_classifies_as_plan(self):
        log = ("gen phys: ERROR type q_b000: bus L14_o is not bound to any leaf port (open output)\n"
               "ot-run: RAN on epyc4 (unit oth-ubuntu-658600-1794106684): exit 1\n")
        cls, why = KW.classify("gen", log)
        self.assertEqual(cls, "PLAN")
        self.assertIn("kit_rtl", why)
        self.assertIn("L14_o", why)


if __name__ == "__main__":
    unittest.main()
