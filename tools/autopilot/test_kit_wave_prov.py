#!/usr/bin/env python3
"""KW-PROV-1 (COORD 2026-11-03 17:50 (C)): WAIT-DEP types launch on PROVISIONAL child views (latest routed DRC-clean
abstract, else the plan-contract abstract), the kit is marked PROVISIONAL and never counted until an STA-only re-sign
on the signed child libs.  Default ON for every die (die option prov_view false = the old WAIT-DEP hold)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW  # noqa: E402
import autopilot as AP  # noqa: E402

PV = HERE / "prov_view.py"
DIE = "qwen_kvsys"
EV = "event28w_c"


def cfg(**over):
    d = {"enabled": True, "event": EV, "gate": {"g0c": "PASS", "bind": "PASS", "clock": "PASS"}, "plan": "/p/plan.json",
         "gen_host": "intel1", "src": "/srv/wt/kw", "src_sha": "620077f42", "owner_lane": "DIE-KV-43",
         "_plan_flags": {"kv3_pc": "noview", "kv3_pv": "planned", "kv3_hg": "hard"}}
    d.update(over)
    return {"enabled": True, "max_inflight": 40, "max_launch_per_tick": 6, "dies": {DIE: d}}


OWN = """die\titem\tkind\tstate\towner\tlive_job\tlast_activity\tnext_step\tevidence\tdefault_owner\treplicas\tmembers
qwen_kvsys\tkv3_pc\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t2518m\tkit it\t\tKV-PLAN\t1\t
"""


class Option(unittest.TestCase):
    def test_default_on_and_opt_out(self):
        d = cfg()["dies"][DIE]
        self.assertTrue(KW.prov_on(d))
        self.assertTrue(KW.prov_item(d, "kv3_pc"))
        self.assertTrue(KW.prov_item(d, "kv3_pv"))
        self.assertFalse(KW.prov_item(d, "kv3_hg"))
        self.assertIsNone(KW.plan_entry_block(d, "kv3_pc"))
        self.assertIsNone(KW.plan_entry_block(d, "kv3_pv"))
        d0 = dict(d, prov_view=False)
        self.assertFalse(KW.prov_item(d0, "kv3_pc"))
        self.assertTrue(KW.plan_entry_block(d0, "kv3_pc").startswith("WAIT-DEP"))
        # planned_core_flat keeps its flat build (no provisional view)
        self.assertFalse(KW.prov_item(dict(d, planned_core_flat=True), "kv3_pv"))

    def test_classify_prov_fail_is_plan_not_waitdep(self):
        cls, why = KW.classify("prov_views", "PROV_FAIL x\nPROVISIONAL view FAIL (KW-PROV-1): no provisional abstract")
        self.assertEqual(cls, "PLAN")
        self.assertFalse(why.startswith("WAIT-DEP"))


class Select(unittest.TestCase):
    def setUp(self):
        self.rows = KW.parse_owners(OWN)
        self.plan = {"kv3_pc": "b1"}
        self.key = KW.item_key(DIE, EV, "kv3_pc", "b1")
        self.rec = {"die": DIE, "item": "kv3_pc", "kind": "type", "attempt": 1, "status": "FAIL", "class": "PLAN",
                    "reason": "WAIT-DEP child view (lef/lib) missing in the plan @gen: ValueError"}

    def picked(self, c, st):
        picks, skip = KW.select(self.rows, c, DIE, st, self.plan)
        return [p["item"] for p in picks], skip

    def test_waitdep_relaunches_once_on_provisional_views(self):
        p, _ = self.picked(cfg(), {"items": {self.key: dict(self.rec)}})
        self.assertEqual(p, ["kv3_pc"])
        # the provisional attempt failed again: no blind retry
        p, skip = self.picked(cfg(), {"items": {self.key: dict(self.rec, provisional={"m": "contract"})}})
        self.assertEqual(p, [])
        self.assertTrue(any("no blind retry" in k for k in skip))
        # opt-out: the old hold
        p, _ = self.picked(cfg(prov_view=False), {"items": {self.key: dict(self.rec)}})
        self.assertEqual(p, [])

    def test_signed_child_resigns_not_rebuilds(self):
        old = dict(self.rec, status="ENQUEUED", q_status="WAIT-PARENT", provisional={"m": "contract"}, prov_key="k1")
        st = {"items": {KW.item_key(DIE, EV, "kv3_pc", "b0"): old}}
        c = cfg(_prov_keys={"kv3_pc": "k1"})
        c["dies"][DIE]["_plan_flags"] = {}                    # child now bound: the type is plain again (new block b1)
        p, skip = self.picked(c, st)
        self.assertEqual(p, [])
        self.assertTrue(any(k.startswith("PROV-RESIGN") for k in skip))
        # the type itself changed (prov_key differs) -> normal rebuild
        p, _ = self.picked(cfg(_prov_keys={"kv3_pc": "k2"}, _plan_flags={}), st)
        self.assertEqual(p, ["kv3_pc"])
        # a re-sign that found a changed abstract releases the rebuild
        old["prov_resign"] = {"status": "RE-ROUTE"}
        p, _ = self.picked(c, st)
        self.assertEqual(p, ["kv3_pc"])

    def test_resign_due(self):
        rec = dict(self.rec, status="ENQUEUED", q_status="WAIT-PARENT", provisional={"m": "routed"}, prov_key="k1",
                   kit="intel1:/k/K", q_id="j1")
        st = {"items": {self.key: rec}}
        c = cfg(_prov_keys={"kv3_pc": "k1"}, _plan_dir="/p", _prov_bound={})
        self.assertEqual(KW.prov_resign_due(c, st, {}), [])
        c["dies"][DIE]["_prov_bound"] = {"m": {"lef": "v/m.lef", "lib": "/abs/m_tt.lib"}}
        due = KW.prov_resign_due(c, st, {"j1": {"ran_on": "epyc4"}})
        self.assertEqual(len(due), 1)
        _, _, ch, host, kp = due[0]
        self.assertEqual((host, kp), ("epyc4", "/k/K"))
        self.assertEqual(ch["m"], {"lef": "/p/v/m.lef", "tt": "/abs/m_tt.lib", "ff": "/abs/m_ff.lib"})
        rec["prov_resign"] = {"status": "RUNNING"}
        self.assertEqual(KW.prov_resign_due(c, st, {}), [])


class Sources(unittest.TestCase):
    def test_routed_drc_clean_newest_first(self):
        so = lambda p, drc: {"path": p + "/signoff/signoff.json", "base": p + "/run/base", "drc": drc}
        jobs = {
            "a": {"id": "a", "die": DIE, "type": "m", "finished": 10, "kit": "intel1:/k/a", "signoff": so("/k/a", 0)},
            "b": {"id": "b", "die": DIE, "type": "m", "finished": 20, "kit": "intel2:/k/b", "ran_on": "epyc4",
                  "signoff": so("/k/b", 0)},
            "c": {"id": "c", "die": DIE, "type": "m", "finished": 30, "kit": "intel1:/k/c", "signoff": so("/k/c", 3)},
            "d": {"id": "d", "die": "s81", "type": "m", "finished": 40, "kit": "intel1:/k/d", "signoff": so("/k/d", 0)},
            "e": {"id": "e", "die": DIE, "type": "n__v0123456789ab", "finished": 5, "kit": "localhost:/k/e",
                  "signoff": so("/k/e", 0)}}
        out = KW.prov_sources(jobs, DIE, ["m", "n", "z"], {}, "intel2")
        self.assertEqual([c["job"] for c in out["m"]], ["b", "a"])
        self.assertEqual(out["m"][0]["host"], "epyc4")
        self.assertEqual(out["m"][0]["dir"], "/k/b/signoff")
        self.assertEqual(out["n"][0]["host"], "intel2")                  # localhost = the hub
        self.assertEqual(out["z"], [])
        pinned = KW.prov_sources(jobs, DIE, ["z"], {"prov_view_sources": {"z": {"host": "h", "dir": "/x"}}}, "intel2")
        self.assertEqual(pinned["z"][0]["dir"], "/x")


def probe(plan):
    with tempfile.TemporaryDirectory() as d:
        pp = Path(d) / "plan.json"
        pp.write_text(json.dumps(plan))
        out = subprocess.run([sys.executable, "-c", KW.PROBE_PLAN, json.dumps({"plan": str(pp)})],
                             capture_output=True, text=True, cwd=d)
        return json.loads(out.stdout.split("AP_JSON ", 1)[1])


class Probe(unittest.TestCase):
    def test_prov_deps_bound_and_key(self):
        t = {"hard_cores": [{"inst": "u0", "module": "m"}, {"inst": "u1", "module": "s", "lef": "s.lef", "lib": "s_tt.lib"}],
             "contents": [{"inst": "r", "module": "rom", "lef": "rom.lef"}]}
        a = probe({"partition_types": {"T": t}})
        self.assertEqual(a["prov_deps"], {"T": ["m", "rom"]})
        self.assertEqual(a["bound"], {"s": {"lef": "s.lef", "lib": "s_tt.lib"}})
        t2 = json.loads(json.dumps(t))
        t2["hard_cores"][0].update(lef="m.lef", lib="m_tt.lib")
        t2["contents"][0]["lib"] = "rom_tt.lib"
        b = probe({"partition_types": {"T": t2}})
        self.assertEqual(b["prov_deps"], {})
        self.assertEqual(a["prov_keys"]["T"], b["prov_keys"]["T"])         # only child views changed
        t2["cells"] = 5
        self.assertNotEqual(a["prov_keys"]["T"], probe({"partition_types": {"T": t2}})["prov_keys"]["T"])


PINS = [{"name": "clk", "layer": "M5", "x": 1.0, "y": 0.0, "dir": "in"},
        {"name": "d_i[0]", "layer": "M4", "x": 0.0, "y": 2.0, "dir": "in"},
        {"name": "d_i[1]", "layer": "M4", "x": 0.0, "y": 3.0, "dir": "in"},
        {"name": "q_o", "layer": "M4", "x": 10.0, "y": 4.0, "dir": "out"}]


def mkplan(root, extra_pins=None):
    root = Path(root)
    (root / "pins").mkdir(parents=True, exist_ok=True)
    (root / "pins" / "child.json").write_text(json.dumps(PINS + (extra_pins or [])))
    plan = {"die": {"name": "kv", "period_ps": 833},
            "partition_types": {
                "T": {"hard_cores": [{"inst": "u0", "module": "child", "outline_um": [10.0, 8.0],
                                      "pins_file": "pins/child.json", "obs_max": "M6"}]},
                "U": {"hard_cores": [{"inst": "u0", "module": "child"}]}}}
    (root / "plan.json").write_text(json.dumps(plan))
    return root / "plan.json"


def pv(*args):
    p = subprocess.run([sys.executable, "-I", str(PV)] + [str(a) for a in args], capture_output=True, text=True)
    js = next((json.loads(ln[10:]) for ln in p.stdout.splitlines() if ln.startswith("PROV_JSON ")), None)
    return p.returncode, js, p.stdout + p.stderr


class Make(unittest.TestCase):
    def test_contract_overlay_marker_then_routed(self):
        with tempfile.TemporaryDirectory() as t:
            plan = mkplan(Path(t) / "pd")
            out = Path(t) / "w1"
            rc, js, txt = pv("make", "--plan", plan, "--type", "T", "--out", out)
            self.assertEqual(rc, 0, txt)
            self.assertEqual(js["children"], {"child": "contract"})
            lef = (out / "views/child/child.lef").read_text()
            self.assertIn("MACRO child", lef)
            self.assertRegex(lef, r"SIZE 10(\.0+)? BY 8(\.0+)?")
            for n in ("clk", "d_i[0]", "q_o", "VDD", "VSS"):
                self.assertIn(f"PIN {n}", lef)
            tt = (out / "views/child/child_tt.lib").read_text()
            self.assertIn("cell (child)", tt.replace("cell(child)", "cell (child)"))
            self.assertIn("max_clock_tree_path", tt)
            self.assertTrue((out / "views/child/child_ff.lib").is_file())
            ov = json.loads(Path(js["overlay_plan"]).read_text())
            hc = ov["partition_types"]["T"]["hard_cores"][0]
            self.assertEqual(hc["lib"], str(out / "views/child/child_tt.lib"))
            self.assertEqual(hc["lef"], str(out / "views/child/child.lef"))
            self.assertNotIn("lef", ov["partition_types"]["U"]["hard_cores"][0])   # only type T changes
            self.assertTrue((Path(js["overlay_plan"]).parent / "pins").is_symlink())
            mk = json.loads((out / "provisional_views.json").read_text())
            self.assertEqual((mk["schema"], mk["status"]), ("opentallas.provisional_views.v1", "PROVISIONAL"))
            self.assertFalse(mk["children"]["child"]["final"])
            # routed candidate: accepted when it matches the plan (use the contract views as a 'routed' abstract)
            r = Path(t) / "routed/child"
            good, bad = r / "c0", r / "c1"
            for c in (good, bad):
                c.mkdir(parents=True)
                for f in ("child.lef", "child_tt.lib", "child_ff.lib"):
                    (c / f).write_text((out / "views/child" / f).read_text())
            (good / "meta.json").write_text(json.dumps({"job": "jgood", "drc": 0}))
            (bad / "meta.json").write_text(json.dumps({"job": "jbad"}))
            (bad / "child.lef").write_text((bad / "child.lef").read_text().replace("PIN q_o", "PIN q_x"))
            rc, js, txt = pv("make", "--plan", plan, "--type", "T", "--out", Path(t) / "w2", "--routed", Path(t) / "routed")
            self.assertEqual(rc, 0, txt)
            self.assertEqual(js["children"], {"child": "routed"})
            mk = json.loads((Path(t) / "w2/provisional_views.json").read_text())
            self.assertEqual(mk["children"]["child"]["job"], "jgood")
            # only the bad candidate: rejected -> contract, and the attempt is recorded
            import shutil
            shutil.rmtree(good)
            rc, js, txt = pv("make", "--plan", plan, "--type", "T", "--out", Path(t) / "w3", "--routed", Path(t) / "routed")
            self.assertEqual(rc, 0, txt)
            self.assertEqual(js["children"], {"child": "contract"})
            mk = json.loads((Path(t) / "w3/provisional_views.json").read_text())
            self.assertTrue(any("jbad" in x for x in mk["children"]["child"]["routed_tried"]))

    def test_vector_clock_port_and_name_rules(self):
        sys.path.insert(0, str(HERE))
        import prov_view as P
        self.assertTrue(P.is_clock("ck[0]") and P.is_clock("clk") and not P.is_clock("d_i[0]"))
        self.assertEqual((P.name_dir("ft_ck_i_0"), P.name_dir("ft_ck_o_1"), P.name_dir("pc__ki_15[3]")),
                         ("INPUT", "OUTPUT", None))
        pins = [{"name": "ck[0]"}, {"name": "d_i[0]"}, {"name": "q_o"}]
        lib = P.contract_lib("c", "tt", 1, 1, pins, {"ck[0]": "INPUT", "d_i[0]": "INPUT", "q_o": "OUTPUT"},
                             {"ck[0]": (50.0, 40.0)}, 833)
        ck = lib.split("bus (ck)", 1)[1].split("    }", 1)[0]
        self.assertIn("clock : true", ck)
        self.assertIn("max_clock_tree_path", ck)
        self.assertIn('related_pin : "ck"', lib)
        self.assertIn('values ("116.6000")', lib)                 # setup = 0.2 T - L = 166.6 - 50
        hdr = "module m #(parameter P = 1) (input wire clk, (* keep *) output reg [3:0] q, output y);\nendmodule"
        self.assertEqual(P.module_ports(hdr), {"clk": "input", "q": "output", "y": "output"})

    def test_no_direction_fails(self):
        with tempfile.TemporaryDirectory() as t:
            plan = mkplan(Path(t) / "pd", [{"name": "mystery", "layer": "M4", "x": 5.0, "y": 0.0}])
            rc, js, txt = pv("make", "--plan", plan, "--type", "T", "--out", Path(t) / "w")
            self.assertEqual(rc, 3, txt)
            self.assertFalse(js["ok"])
            self.assertIn("PROV_FAIL", txt)


SIGNOFF_STUB = """import argparse, json, os
a = argparse.ArgumentParser(); a.add_argument('cmd'); a.add_argument('--run-dir'); a.add_argument('--kit')
a.add_argument('--out'); a.add_argument('--image'); a.add_argument('--corners'); x = a.parse_args()
os.makedirs(x.out); json.dump({'verdict': 'SIGNED', 'checks': {'drc': {'count': 0}}, 'pg': 'PASS'},
                               open(os.path.join(x.out, 'signoff.json'), 'w'))
"""


class Resign(unittest.TestCase):
    def kit(self, t):
        plan = mkplan(Path(t) / "pd")
        out = Path(t) / "w"
        rc, js, txt = pv("make", "--plan", plan, "--type", "T", "--out", out)
        self.assertEqual(rc, 0, txt)
        K = Path(t) / "K"
        (K / "macros").mkdir(parents=True)
        (K / "run").mkdir()
        for f in ("child.lef", "child_tt.lib", "child_ff.lib"):
            (K / "macros" / f).write_text((out / "views/child" / f).read_text())
        (K / "provisional_views.json").write_text((out / "provisional_views.json").read_text())
        (K / "signoff.py").write_text(SIGNOFF_STUB)
        sig = Path(t) / "signed"
        sig.mkdir()
        for f in ("child.lef", "child_tt.lib", "child_ff.lib"):
            (sig / f).write_text((out / "views/child" / f).read_text().replace("Provisional", "Signed"))
        (sig / "child_tt.lib").write_text((sig / "child_tt.lib").read_text() + "\n/* signed */\n")
        return K, sig

    def test_final_and_sta_resign(self):
        with tempfile.TemporaryDirectory() as t:
            K, sig = self.kit(t)
            spec = f"child={sig}/child.lef,{sig}/child_tt.lib,{sig}/child_ff.lib"
            rc, _, txt = pv("resign", "--kit", K, "--child", spec, "--dry-run")
            self.assertEqual(rc, 0, txt)
            self.assertIn("DRY ok", txt)
            rc, _, txt = pv("resign", "--kit", K, "--child", spec)
            self.assertEqual(rc, 0, txt)
            mk = json.loads((K / "provisional_views.json").read_text())
            self.assertEqual(mk["status"], "FINAL")
            self.assertTrue(mk["children"]["child"]["final"])
            self.assertIn("/* signed */", (K / "macros/child_tt.lib").read_text())
            self.assertTrue((K / "macros/child_tt.lib.prov").is_file())
            self.assertEqual(len(list(K.glob("signoff_resign_*/signoff.json"))), 1)

    def test_changed_abstract_reroute(self):
        with tempfile.TemporaryDirectory() as t:
            K, sig = self.kit(t)
            (sig / "child.lef").write_text((sig / "child.lef").read_text().replace("PIN q_o", "PIN q_z"))
            before = (K / "macros/child_tt.lib").read_text()
            rc, _, txt = pv("resign", "--kit", K, "--child", f"child={sig}/child.lef,{sig}/child_tt.lib,{sig}/child_ff.lib")
            self.assertEqual(rc, 4, txt)
            self.assertIn("REROUTE", txt)
            self.assertEqual((K / "macros/child_tt.lib").read_text(), before)
            self.assertEqual(json.loads((K / "provisional_views.json").read_text())["resign"]["status"], "RE-ROUTE")


def classify_probe(K):
    p = subprocess.run([sys.executable, "-c", AP.PROBE_CLASSIFY, json.dumps({"kit": str(K), "since": 0})],
                       capture_output=True, text=True)
    return json.loads(p.stdout.split("AP_JSON ", 1)[1])


class AutopilotGuard(unittest.TestCase):
    def test_provisional_signed_waits_parent_until_final(self):
        with tempfile.TemporaryDirectory() as t:
            K = Path(t) / "K"
            (K / "signoff").mkdir(parents=True)
            (K / "macros").mkdir()
            (K / "signoff/signoff.json").write_text(json.dumps({"verdict": "SIGNED", "local_verdict": "SIGNED",
                                                                "checks": {"drc": {"count": 0}}}))
            lib = K / "macros/m_tt.lib"
            lib.write_text("library (m) {}")
            mk = {"schema": "opentallas.provisional_views.v1", "status": "PROVISIONAL",
                  "children": {"m": {"source": "contract", "final": False}}}
            (K / "provisional_views.json").write_text(json.dumps(mk))
            so = classify_probe(K)["signoff"]
            self.assertEqual((so["verdict"], so["local_verdict"], so["release_qualified"]),
                             ("LOCAL_PASS_NEEDS_PARENT", "SIGNED", False))
            self.assertIn("provisional_child_view", so["reasons"][-1])
            cls, _, why = AP.classify({"signoff": so}, {})
            self.assertEqual(cls, "WAIT-PARENT")
            self.assertIn("KW-PROV-1", why)
            # FINAL marker but the sign-off predates the final libs: still provisional
            import hashlib
            h = hashlib.sha256(lib.read_bytes()).hexdigest()
            mk.update(status="FINAL", children={"m": {"source": "contract", "final": True, "final_sha256": {"m_tt.lib": h}}})
            (K / "provisional_views.json").write_text(json.dumps(mk))
            old = time.time() - 100
            os.utime(K / "signoff/signoff.json", (old, old))
            self.assertEqual(classify_probe(K)["signoff"]["verdict"], "LOCAL_PASS_NEEDS_PARENT")
            # the STA-only re-sign record newer than the final libs: counted
            (K / "signoff_resign_1").mkdir()
            (K / "signoff_resign_1/signoff.json").write_text(json.dumps({"verdict": "SIGNED", "local_verdict": "SIGNED"}))
            self.assertEqual(classify_probe(K)["signoff"]["verdict"], "SIGNED")
            # a lib swapped after the re-sign (sha mismatch): provisional again
            lib.write_text("library (m) { changed }")
            self.assertEqual(classify_probe(K)["signoff"]["verdict"], "LOCAL_PASS_NEEDS_PARENT")

    def test_no_marker_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            K = Path(t) / "K"
            (K / "signoff").mkdir(parents=True)
            (K / "signoff/signoff.json").write_text(json.dumps({"verdict": "SIGNED"}))
            self.assertEqual(classify_probe(K)["signoff"]["verdict"], "SIGNED")


class Stages(unittest.TestCase):
    def test_reason_prefixed(self):
        with tempfile.TemporaryDirectory() as t:
            st = {"items": {"k": {"die": DIE, "item": "kv3_pc", "event": EV, "status": "ENQUEUED", "q_stage": "queue",
                                  "q_status": "WAIT-PARENT", "q_reason": "x", "provisional": {"m": "routed", "n": "contract"},
                                  "updated": time.time()}}}
            KW.write_stages(st, t, cfg())
            txt = Path(t, KW.STAGES_FILE).read_text()
            self.assertIn("PROVISIONAL[m:routed,n:contract]", txt)


if __name__ == "__main__":
    unittest.main()
