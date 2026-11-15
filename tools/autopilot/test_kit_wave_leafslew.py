"""KW-FIX-17 11-05 (COORD 16:4x): LEAFSLEW signature -> one auto class retry with the clk_leaf_repeat post-CTS hook"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import kit_wave as KW

POS = """SO_PATH_BEGIN DRV
max slew

Pin                                    Limit    Slew   Slack
------------------------------------------------------------
_18679_/D                             320.00  525.88 -205.88 (VIOLATED)
clkbuf_leaf_115_ot_dtap_net_0/A       320.00  397.94  -77.94 (VIOLATED)
ot_dtap_3_iso/A                       320.00  563.10 -243.10 (VIOLATED)
u_core/q[3]$_DFF_P_/CLK               320.00  331.00  -11.00 (VIOLATED)

max capacitance

Pin                                    Limit     Cap   Slack
------------------------------------------------------------
clkbuf_9_0_0_clk/Y                     40.00   61.00  -21.00 (VIOLATED)
"""
NEG = """max slew

Pin                                    Limit    Slew   Slack
------------------------------------------------------------
_4533_/B                              320.00  561.15 -241.15 (VIOLATED)
place6236/A                           320.00  523.34 -203.34 (VIOLATED)
"""


class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self, out):
        self.out, self.calls, self.logs = out, [], []

    def sh(self, argv, timeout=0, input=None):
        self.calls.append(argv)
        return self.out.pop(0) if isinstance(self.out, list) else self.out

    def log(self, x):
        self.logs.append(x)


class Parse(unittest.TestCase):
    def test_positive(self):
        sig = KW.leafslew_parse(POS)
        self.assertEqual(sig["pins"], 3)                 # cap table row and the data pin never count
        self.assertEqual((sig["worst_ps"], sig["worst_pin"]), (563.1, "ot_dtap_3_iso/A"))

    def test_negative(self):
        self.assertEqual(KW.leafslew_parse(NEG)["pins"], 0)
        self.assertEqual(KW.leafslew_parse("")["pins"], 0)

    def test_grep_form(self):                            # the remote read sends only headers + VIOLATED rows
        g = "\n".join(l for l in POS.splitlines() if l.startswith("Pin") or "VIOLATED" in l)
        self.assertEqual(KW.leafslew_parse(g)["pins"], 3)

    def test_hier_clock_cell(self):
        t = "Pin Limit Slew Slack\nu_a/clkbuf_1_0_0_clk/A 320.00 400.00 -80.00 (VIOLATED)\n"
        self.assertEqual(KW.leafslew_parse(t)["pins"], 1)


class Release(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        (self.d / "spec.json").write_text(json.dumps({"src_sha": "abc123"}))
        self.cfg = {"dies": {"hbm": {"event": "e", "retry": []}}}
        self.key = KW.item_key("hbm", "e", "t1", "b" * 12)
        self.st = {"items": {self.key: self.rec()}}

    def rec(self, **kw):
        r = dict(die="hbm", item="t1", event="e", attempt=3, status="ENQUEUED", q_status="FAIL", q_id="j1",
                 q_signoff="/k/signoff/signoff.json", q_hosts=["localhost", "epyc4"], dir=str(self.d), updated=1.0)
        r.update(kw)
        return r

    def tick(self, out=(0, POS + "KW_LEAFSLEW_READ\n", "")):
        ap = AP(out)
        n = {}
        KW.leafslew_step(ap, self.cfg, self.st, n, "intel2")
        return ap, n

    def test_release_once(self):
        ap, n = self.tick()
        self.assertIn("t1@3", self.cfg["dies"]["hbm"]["retry"])
        self.assertEqual(self.cfg["dies"]["hbm"]["retry_fix"]["t1@3"], KW.LEAFSLEW_NOTE)
        self.assertIn("LEAFSLEW", n["hbm"][0])
        self.assertEqual(ap.calls[0][:2], ["bash", "-c"])          # ran_on localhost = the hub: no ssh
        self.assertIn("/k/signoff/tt/sta.log", ap.calls[0][2])
        self.assertEqual(self.st["items"][self.key]["leafslew"]["pins"], 3)
        ap2, n2 = self.tick()                                        # judged once: no re-read, no second notice
        self.assertEqual((ap2.calls, n2), ([], {}))
        # the next tick's fresh config is re-released until the hooked attempt launches
        self.cfg = {"dies": {"hbm": {"event": "e"}}}
        self.tick()
        self.assertIn("t1@3", self.cfg["dies"]["hbm"]["retry"])
        # the selector now relaunches it
        rows = [dict(die="hbm", item="t1", kind="type", state="NEEDS-KIT", owner="KIT-WAVE", live_job="none",
                     last_activity="", next_step="", evidence="", default_owner="", replicas="1", members="")]
        picks, _ = KW.select(rows, self.cfg, "hbm", self.st, {"t1": "b" * 12})
        self.assertEqual([p["item"] for p in picks], ["t1"])

    def test_launch_claims_and_no_loop(self):
        self.tick()
        k, form = KW.leafslew_launch(self.cfg, self.st, "hbm", "t1", self.st["items"][self.key], 4)
        self.assertTrue(k)
        self.assertEqual((form["attempt"], form["pins"]), (3, 3))
        self.st["leafslew"][k]["hooked_attempt"] = 4                 # launch() does this once the unit is on record
        # the hooked attempt fails the same way: judged, but never auto-released again
        self.st["items"][self.key] = self.rec(attempt=4, leafslew_form=form)
        self.cfg = {"dies": {"hbm": {"event": "e"}}}
        _, n = self.tick()
        self.assertEqual(self.cfg["dies"]["hbm"].get("retry") or [], [])
        self.assertEqual(n, {})
        self.assertEqual(len(self.st["leafslew"]), 1)
        # a later (COORD) relaunch of a hooked item keeps the hook
        k2, f2 = KW.leafslew_launch(self.cfg, self.st, "hbm", "t1", self.st["items"][self.key], 5)
        self.assertIsNone(k2)
        self.assertEqual(f2["carried_from"], 4)

    def test_same_src_once(self):
        self.tick()
        e = next(iter(self.st["leafslew"].values()))
        e["hooked_attempt"] = 4
        self.st["items"][self.key] = self.rec(attempt=4)                # same source, no form recorded
        self.cfg = {"dies": {"hbm": {"event": "e"}}}
        self.tick()
        self.assertEqual(self.cfg["dies"]["hbm"].get("retry") or [], [])

    def test_plan_owned_tree_no_retry_goes_to_plan(self):            # KW-FIX-25, COORD 22:1x (5)
        ap, n = self.tick((0, POS + "KW_LEAF_OPTOUT\nKW_LEAFSLEW_READ\n", ""))
        self.assertIn("OT_CLK_LEAF_REPEAT", ap.calls[0][2])
        self.assertIn("/k/config.mk", ap.calls[0][2])
        self.assertEqual(self.cfg["dies"]["hbm"]["retry"], [])
        self.assertEqual(self.st.get("leafslew"), {})
        self.assertIn("PLAN FIX", n["hbm"][0])
        rec = self.st["items"][self.key]
        self.assertEqual(rec["q_class"], "PLAN")
        # a later re-read of the same queue row keeps the route; another status or an unrouted row is untouched
        self.assertEqual(KW.leafslew_plan_route(rec, "FAIL", "TIMING", "x")[0], "PLAN")
        self.assertEqual(KW.leafslew_plan_route(rec, "SIGNED", "", "x"), ("", "x"))
        self.assertEqual(KW.leafslew_plan_route({}, "FAIL", "TIMING", "x"), ("TIMING", "x"))
        ap2, n2 = self.tick()                                        # judged once
        self.assertEqual((ap2.calls, n2), ([], {}))

    def test_optout_pattern_on_real_config_lines(self):
        with tempfile.TemporaryDirectory() as td:
            cm = Path(td) / "config.mk"
            for line, hit in (("export OT_CLK_LEAF_REPEAT = 0", 0), ("  override export OT_CLK_LEAF_REPEAT := 0 # plan", 0),
                              ("export OT_CLK_LEAF_REPEAT = 1", 1), ("export OT_CLK_LEAF_REPEAT = 01", 1),
                              ("# export OT_CLK_LEAF_REPEAT = 0", 1), ("export OT_CLK_LEAF_GRT = 0", 1)):
                cm.write_text(line + "\n")
                self.assertEqual(subprocess.run(["grep", "-Eqs", KW.LEAF_OPTOUT_RE, str(cm)]).returncode, hit, line)

    def test_negative_no_release(self):
        _, n = self.tick((0, NEG + "KW_LEAFSLEW_READ\n", ""))
        self.assertEqual(self.cfg["dies"]["hbm"]["retry"], [])
        self.assertEqual(self.st["items"][self.key]["leafslew"]["pins"], 0)

    def test_unreadable_fail_soft(self):
        for i in range(KW.LEAFSLEW_TRIES):
            ap, n = self.tick((0, "KW_LEAFSLEW_NOLOG\n", ""))
            self.assertEqual(len(ap.calls), 2)                       # hub, then the kit host over ssh
        self.assertIn("ssh", ap.calls[1])
        self.assertEqual(self.st["items"][self.key]["leafslew"]["pins"], 0)
        self.assertEqual(self.cfg["dies"]["hbm"]["retry"], [])
        ap, _ = self.tick()
        self.assertEqual(ap.calls, [])                               # given up: no more reads

    def test_opt_out(self):
        self.cfg["dies"]["hbm"]["leafslew_auto"] = False
        ap, n = self.tick()
        self.assertEqual((ap.calls, n, self.cfg["dies"]["hbm"]["retry"]), ([], {}, []))
        self.assertEqual(KW.leafslew_launch(self.cfg, self.st, "hbm", "t1", {"leafslew_form": {"a": 1}}, 4), (None, None))

    def test_opt_out_global(self):
        self.cfg["leafslew_auto"] = False
        ap, _ = self.tick()
        self.assertEqual(ap.calls, [])

    def test_follow_queue_records_signoff(self):
        rec = dict(die="hbm", item="t1", status="ENQUEUED", kit="epyc4:/k")
        st = {"items": {"x": rec}}
        job = dict(id="j1", kit="epyc4:/k", status="DONE-NEAR-MISS", kind="routed", ran_on="localhost",
                   signoff=dict(path="/k/signoff/signoff.json", fails=["drv"], tt_wns=5.0, ff_wns=1.0), updated=1)
        (self.d / "state.json").write_text(json.dumps({"jobs": {"j1": job}}))
        KW.follow_queue(st, str(self.d), {})
        self.assertEqual((rec["q_status"], rec["q_signoff"], rec["q_hosts"]),
                         ("FAIL", "/k/signoff/signoff.json", ["localhost", "epyc4"]))


@unittest.skipUnless(shutil.which("make"), "make absent")
class Patch(unittest.TestCase):
    def kit(self, cfg_text):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        k = Path(td.name)
        (k / "config.mk").write_text(cfg_text)
        (k / KW.LEAFSLEW_TCL).write_text("# hook\n")
        (k / "Makefile").write_text("include config.mk\nshow:\n\t@echo \"P=$$POST_CTS_TCL N=$$OT_CLR_NEXT_TCL\"\n")
        return k

    def patch(self, k):
        return subprocess.run(["bash", "-c", KW.leafslew_patch_cmd(str(k), {"pins": 3, "worst_ps": 563.1})],
                              capture_output=True, text=True)

    def show(self, k):
        return subprocess.run(["make", "-s", "-C", str(k), "show"], capture_output=True, text=True).stdout.strip()

    def test_chains_existing_hook(self):
        k = self.kit("export POST_CTS_TCL = /work/tap_balance.tcl\noverride export POST_CTS_TCL = /work/post_cts_setup.tcl\n")
        p = self.patch(k)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.show(k), "P=/work/clk_leaf_repeat.tcl N=/work/post_cts_setup.tcl")
        self.assertEqual(json.loads((k / "LEAFSLEW_FORM.json").read_text())["trigger"]["pins"], 3)
        self.patch(k)                                                # idempotent (stage rerun)
        self.assertEqual((k / "config.mk").read_text().count("KW-FIX-17 LEAFSLEW"), 1)

    def test_no_existing_hook(self):
        k = self.kit("export DESIGN_NAME = x\n")
        self.assertEqual(self.patch(k).returncode, 0)
        self.assertEqual(self.show(k), "P=/work/clk_leaf_repeat.tcl N=")

    def test_kit_already_hooked(self):
        txt = "override export POST_CTS_TCL = /work/clk_leaf_repeat.tcl\nexport OT_CLR_NEXT_TCL = /work/post_cts_setup.tcl\n"
        k = self.kit(txt)
        p = self.patch(k)
        self.assertIn("already hooked", p.stdout)
        self.assertEqual((k / "config.mk").read_text(), txt)

    def test_missing_config_fails(self):
        k = self.kit("")
        os.remove(k / "config.mk")
        self.assertNotEqual(self.patch(k).returncode, 0)


class Hook(unittest.TestCase):
    def test_repo_hook_present_and_guarded(self):
        p = Path(__file__).resolve().parents[2] / "physical" / "common_flow" / KW.LEAFSLEW_TCL
        t = p.read_text()
        self.assertIn("HBM-CTS-LEAFSLEW", t)
        self.assertIn("KW-FIX-17", t)
        self.assertIn('ne "clk_leaf_repeat.tcl"', t)                 # no self-recursion through OT_CLR_NEXT_TCL


class Items(unittest.TestCase):
    """COORD 11-05 17:4x: die option leafslew_items {glob: {OT_CLK_LEAF_*: v}} builds matching items with the hook (branch rule)"""
    BR = {"OT_CLK_LEAF_SLEW_PS": 60, "OT_CLK_LEAF_MAX_FANOUT": 12}

    def cfg(self, items=None):
        return {"dies": {"s81": {"event": "e", "leafslew_items": items if items is not None else {"slice_station__*": self.BR}}}}

    def test_match_without_signature_any_attempt(self):
        for att in (1, 2, 7):
            k, f = KW.leafslew_launch(self.cfg(), {}, "s81", "slice_station__t47", {}, att)
            self.assertIsNone(k)
            self.assertEqual(f, {"by": "leafslew_items", "env": {"OT_CLK_LEAF_MAX_FANOUT": "12", "OT_CLK_LEAF_SLEW_PS": "60"}})
        self.assertEqual(KW.leafslew_launch(self.cfg(), {}, "s81", "col_h9_r0", {}, 2), (None, None))
        self.assertIsNone(KW.leafslew_item_env(self.cfg(), "s81", "col_h9_r0"))

    def test_env_rides_on_signature_and_carried_forms(self):
        st = {"leafslew": {"x": {"die": "s81", "item": "slice_station__t48", "attempt": 3, "pins": 2}}}
        k, f = KW.leafslew_launch(self.cfg(), st, "s81", "slice_station__t48", {}, 4)
        self.assertEqual((k, f["pins"], f["env"]["OT_CLK_LEAF_SLEW_PS"]), ("x", 2, "60"))
        k, f = KW.leafslew_launch(self.cfg({}), {}, "s81", "slice_station__t48", {"attempt": 4, "leafslew_form": dict(f)}, 5)
        self.assertEqual(f["carried_from"], 4)
        self.assertNotIn("env", f)                                   # rule removed: the carried hook keeps tool defaults

    def test_empty_env_is_hook_with_defaults_and_opt_out_wins(self):
        self.assertEqual(KW.leafslew_launch(self.cfg({"slice_*": {}}), {}, "s81", "slice_station__t1", {}, 1)[1],
                         {"by": "leafslew_items", "env": {}})
        c = self.cfg(); c["dies"]["s81"]["leafslew_auto"] = False
        self.assertEqual(KW.leafslew_launch(c, {}, "s81", "slice_station__t1", {}, 2), (None, None))

    def test_bad_env_raises(self):
        with self.assertRaises(ValueError):
            KW.leafslew_item_env(self.cfg({"*": {"OT_HOLD_STOP_PS": "-300"}}), "s81", "a")
        with self.assertRaises(ValueError):
            KW.leafslew_item_env(self.cfg({"*": {"OT_CLK_LEAF_SLEW_PS": "60; rm"}}), "s81", "a")

    def test_patch_writes_env(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        k = Path(td.name)
        (k / "config.mk").write_text("export POST_CTS_TCL = /work/post_cts_setup.tcl\n")
        (k / KW.LEAFSLEW_TCL).write_text("# hook\n")
        (k / "Makefile").write_text("include config.mk\nshow:\n\t@echo \"P=$$POST_CTS_TCL S=$$OT_CLK_LEAF_SLEW_PS F=$$OT_CLK_LEAF_MAX_FANOUT\"\n")
        form = {"by": "leafslew_items", "env": {"OT_CLK_LEAF_SLEW_PS": "60", "OT_CLK_LEAF_MAX_FANOUT": "12"}}
        p = subprocess.run(["bash", "-c", KW.leafslew_patch_cmd(str(k), form)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = subprocess.run(["make", "-s", "-C", str(k), "show"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "P=/work/clk_leaf_repeat.tcl S=60 F=12")


if __name__ == "__main__":
    unittest.main()
