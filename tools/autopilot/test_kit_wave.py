#!/usr/bin/env python3
"""tests for kit_wave.py (no ssh, no ot-run, no systemd: the autopilot host layer is faked)"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

GATE = {"g0c": "PASS", "bind": "PASS", "clock": "PASS", "evidence": "DIE-KV-40 21:07"}


def cfg(**die_over):
    d = {"enabled": True, "event": "event28w_c", "gate": dict(GATE), "plan": "/srv/p/plan_c.json", "gen_host": "intel1",
         "src": "/srv/wt/kw", "src_sha": "620077f42", "owner_lane": "DIE-KV-43"}
    d.update(die_over)
    return {"enabled": True, "max_inflight": 40, "max_launch_per_tick": 6, "dies": {"qwen_kvsys": d}}


OWN = """# OWNERS -- test
die\titem\tkind\tstate\towner\tlive_job\tlast_activity\tnext_step\tevidence\tdefault_owner\treplicas\tmembers
qwen_kvsys\tkv3_hg_v1\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t2518m\tkit it\t\tKV-PLAN\t24\t
qwen_kvsys\tkv3_hub_Eo\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t3606m\tkit it\t\tKV-PLAN\t1\t
qwen_kvsys\tkv3_pc\ttype\tNEEDS-KIT\tKV-KITS-W\tnone\t122m\tkit it\t\tKV-PLAN\t4\t
qwen_kvsys\tkv3_io_cor_v1\ttype\tNEEDS-KIT\tKV-KITS\tot-run pid 1487877 x\t0m\tkit it\t\tKV-PLAN\t1\t
qwen_kvsys\tkv3_phy_v1\ttype\tNEEDS-KIT\tKV-KITS\tnone\t965m\tkit it\t\tKV-PLAN\t28\t
qwen_kvsys\tqkd_hr_cdc_ci\tcore\tNEEDS-KIT\tCODEX\tnone\t961m\tkit it\t\tKV-CORES\t1\t
qwen_kvsys\tkv3_hroot\ttype\tKIT-PLACED\tKV-KITS\tnone\t345m\tenqueue\t\tKV-PLAN\t4\t
qwen_kvsys\tkv3_gone\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t3606m\tkit it\t\tKV-PLAN\t9\t
s81\tslice_x\ttype\tNEEDS-KIT\tS81\tnone\t999m\tkit it\t\tS81\t50\t
"""
PLAN = {"kv3_hg_v1", "kv3_hub_Eo", "kv3_pc", "kv3_io_cor_v1", "kv3_phy_v1", "qkd_hr_cdc_ci", "kv3_hroot"}


class Gate(unittest.TestCase):
    def test_kv_event_gate(self):
        self.assertTrue(KW.gate(cfg(), "qwen_kvsys")[0])
        ok, why = KW.gate(cfg(event="event28b"), "qwen_kvsys")
        self.assertFalse(ok)
        self.assertIn("not a COORD plan of record", why)

    def test_gate_needs_all_checks_pass(self):
        g = dict(GATE, clock="FAIL")
        ok, why = KW.gate(cfg(gate=g), "qwen_kvsys")
        self.assertFalse(ok)
        self.assertIn("clock", why)

    def test_s81_descends(self):
        c = {"dies": {"s81": dict(cfg()["dies"]["qwen_kvsys"], event="abcdef12345")}}
        self.assertFalse(KW.gate(c, "s81")[0])                               # exact only, no git
        self.assertTrue(KW.gate(c, "s81", descends=lambda s, b: True)[0])
        c["dies"]["s81"]["event"] = "1dfae74037a"
        self.assertTrue(KW.gate(c, "s81")[0])
        c["dies"]["s81"]["event"] = "event28w_c"
        self.assertFalse(KW.gate(c, "s81", descends=lambda s, b: True)[0])   # not a commit

    def test_head_events(self):
        c = {"dies": {"s81_head": dict(cfg()["dies"]["qwen_kvsys"], event="src25q2")}}
        self.assertTrue(KW.gate(c, "s81_head")[0])
        c["dies"]["s81_head"]["event"] = "src25q"
        self.assertFalse(KW.gate(c, "s81_head")[0])

    def test_qc_hbm_off_until_coord(self):
        for die in ("qwen_compute", "hbm"):
            c = {"dies": {die: dict(cfg()["dies"]["qwen_kvsys"], event="anything")}}
            ok, why = KW.gate(c, die)
            self.assertFalse(ok)
            self.assertIn("COORD", why)
            c["dies"][die]["coord_enable"] = "COORD 10-30 ruling"
            self.assertTrue(KW.gate(c, die)[0])

    def test_disabled_die(self):
        self.assertFalse(KW.gate(cfg(enabled=False), "qwen_kvsys")[0])


class Stop(unittest.TestCase):
    def test_stop_files(self):
        with tempfile.TemporaryDirectory() as d:
            c = cfg()
            self.assertIsNone(KW.stop_reason(c, "qwen_kvsys", d))
            (Path(d) / "kit_wave.qwen_kvsys.stop").touch()
            self.assertIn("die stop", KW.stop_reason(c, "qwen_kvsys", d))
            (Path(d) / "kit_wave.stop").touch()
            self.assertIn("global stop", KW.stop_reason(c, "qwen_kvsys", d))

    def test_disabled_and_kill(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("disabled", KW.stop_reason(dict(cfg(), enabled=False), "qwen_kvsys", d))
            self.assertIn("kill", KW.stop_reason(cfg(kill="COORD 01:00"), "qwen_kvsys", d))
            self.assertIn("unreadable", KW.stop_reason(KW.load_config("{bad"), "qwen_kvsys", d))
            self.assertIn("disabled", KW.stop_reason(KW.load_config(""), "qwen_kvsys", d))


class Select(unittest.TestCase):
    def test_selection_and_order(self):
        rows = KW.parse_owners(OWN)
        picks, skip = KW.select(rows, cfg(), "qwen_kvsys", {"items": {}}, PLAN)
        self.assertEqual([p["item"] for p in picks], ["kv3_phy_v1", "kv3_hg_v1", "kv3_hub_Eo"])   # replicas desc
        self.assertEqual(skip["live job (another lane)"], ["kv3_io_cor_v1"])
        self.assertIn("kv3_pc", skip["lane activity < 3 h (KV-KITS-W)"])
        self.assertEqual(skip["kind core not in wave"], ["qkd_hr_cdc_ci"])
        self.assertEqual(skip["not in plan of record"], ["kv3_gone"])
        self.assertNotIn("kv3_hroot", [p["item"] for p in picks])          # KIT-PLACED not in take_states

    def test_cores_first_when_enabled(self):
        rows = KW.parse_owners(OWN)
        c = cfg(kinds=["type", "core"])
        picks, _ = KW.select(rows, c, "qwen_kvsys", {"items": {}}, PLAN)
        self.assertEqual(picks[0]["item"], "qkd_hr_cdc_ci")

    def test_no_blind_retry(self):
        rows = KW.parse_owners(OWN)
        k = KW.item_key("qwen_kvsys", "event28w_c", "kv3_phy_v1")
        st = {"items": {k: {"status": "FAIL", "class": "PLAN", "attempt": 1}}}
        picks, skip = KW.select(rows, cfg(), "qwen_kvsys", st, PLAN)
        self.assertNotIn("kv3_phy_v1", [p["item"] for p in picks])
        self.assertTrue(any("no blind retry" in w for w in skip))
        picks, _ = KW.select(rows, cfg(retry=["kv3_phy_v1@1"]), "qwen_kvsys", st, PLAN)
        self.assertIn("kv3_phy_v1", [p["item"] for p in picks])            # COORD released attempt 1
        st["items"][k]["attempt"] = 2
        picks, _ = KW.select(rows, cfg(retry=["kv3_phy_v1@1"]), "qwen_kvsys", st, PLAN)
        self.assertNotIn("kv3_phy_v1", [p["item"] for p in picks])         # attempt 2 failed: not released
        st["items"][k]["status"] = "RUNNING"
        _, skip = KW.select(rows, cfg(), "qwen_kvsys", st, PLAN)
        self.assertEqual(skip["wave item in flight"], ["kv3_phy_v1"])

    def test_plan_classes_expand(self):
        rows = KW.parse_owners(OWN)
        plan = (PLAN - {"kv3_hub_Eo"}) | {"kv3_hub_Eo__cl1", "kv3_hub_Eo__cl2"}
        st = {"items": {KW.item_key("qwen_kvsys", "event28w_c", "kv3_hub_Eo__cl1"): {"status": "RUNNING", "attempt": 1}}}
        picks, _ = KW.select(rows, cfg(), "qwen_kvsys", st, plan)
        self.assertEqual([p["item"] for p in picks if p.get("parent_item")], ["kv3_hub_Eo__cl2"])
        st["items"][KW.item_key("qwen_kvsys", "event28w_c", "kv3_hub_Eo__cl2")] = {"status": "FAIL", "attempt": 1}
        _, skip = KW.select(rows, cfg(), "qwen_kvsys", st, plan)
        self.assertEqual(skip["all plan classes already in the wave"], ["kv3_hub_Eo"])

    def test_new_event_is_new_item(self):
        rows = KW.parse_owners(OWN)
        st = {"items": {KW.item_key("qwen_kvsys", "event28b", "kv3_phy_v1"): {"status": "FAIL", "attempt": 1}}}
        picks, _ = KW.select(rows, cfg(), "qwen_kvsys", st, PLAN)
        self.assertIn("kv3_phy_v1", [p["item"] for p in picks])


STATUS = ("ot-run status: epyc2 admits 713 GB (avail 845, reserve 0, fresh 0, peak 67.2) load 37/128 run 24 root 2% "
          "scratch 187 GB | intel1 admits 30 GB (avail 784) load 58/112 run 35 root 8% scratch 1228 GB | localhost admits "
          "251 GB (avail 533) load 112/112 run 45 root 13% scratch 822 GB | next 16-thread 32 GB job -> epyc2")


class Capacity(unittest.TestCase):
    def test_parse_status(self):
        s = KW.parse_otrun_status(STATUS)
        self.assertEqual(s["epyc2"], {"admit": 713, "load": 37.0, "cores": 128, "run": 24})
        self.assertEqual(s["localhost"]["run"], 45)

    def test_caps(self):
        s = KW.parse_otrun_status(STATUS)
        c = cfg(die_max_inflight=5)
        self.assertEqual(KW.capacity(c, "qwen_kvsys", {"items": {}}, s), 5)
        st = {"items": {str(i): {"status": "RUNNING", "die": "qwen_kvsys"} for i in range(3)}}
        self.assertEqual(KW.capacity(c, "qwen_kvsys", st, s), 2)
        st = {"items": {str(i): {"status": "RUNNING", "die": "s81"} for i in range(38)}}
        self.assertEqual(KW.capacity(c, "qwen_kvsys", st, s), 2)                  # global 40
        self.assertEqual(KW.capacity(c, "qwen_kvsys", {"items": {}}, s, launched_now=6), 0)   # per tick

    def test_no_host_admits(self):
        s = {"epyc2": {"admit": 10, "run": 1}, "localhost": {"admit": 47, "run": 1}}
        self.assertEqual(KW.capacity(cfg(), "qwen_kvsys", {"items": {}}, s), 0)
        self.assertEqual(KW.capacity(cfg(), "qwen_kvsys", {"items": {}}, {}), 0)  # ot-run status unavailable
        s["localhost"]["admit"] = 48                                              # intel2 = hub = localhost
        self.assertGreater(KW.capacity(cfg(), "qwen_kvsys", {"items": {}}, s, hub="intel2"), 0)


class Classify(unittest.TestCase):
    def test_classes(self):
        cases = [
            ("place", "ot-run: NOT RUN (no memory within --max-wait)", "INFRA"),
            ("place", "docker: exit 137 OOMKilled", "INFRA"),
            ("place", "FAIL_PREFLOOR LEC NOT EQUIVALENT (lec/lec.json)", "RTL"),
            ("place", "FACE_GUARD FAIL shared 7645 bits", "PLAN"),
            ("place", "[ERROR ORD-2013] instance u_m LEF master ot_sram_1r1w_32x64_m1 not found", "PLAN"),
            ("gen", "type kv3_sys_SD: local reset tap [388.8, 596.16] is blocked", "PLAN"),
            ("gen", "Traceback (most recent call last):\n  File gen.py\nKeyError: 'x'", "FLOW"),
            ("preflight", "KIT_PREFLIGHT FAIL\nmissing staged file", "FLOW"),
            ("geom", "AP_AUTO_GEOM FAIL fill .0997 channel_h 1.065", "PLAN"),
            ("cells", "512000 cells", "PLAN"),
            ("place", "something odd happened", "FLOW"),
            ("place", "ERROR: Module `ot_x' referenced in module `top' is not part of the design.", "RTL"),
        ]
        for stage, text, want in cases:
            self.assertEqual(KW.classify(stage, text)[0], want, (stage, text))

    def test_reason_carries_stage(self):
        cls, why = KW.classify("gen", "reset tap is blocked")
        self.assertIn("@gen", why)
        self.assertIn(cls, KW.CLASSES)


class GeomVerdict(unittest.TestCase):
    def test_lines(self):
        L = "AP_AUTO_GEOM AUTO-GEOM {} kv3 x KIT-WAVE 3_place {}"
        self.assertEqual(KW.geom_verdict(L.format("PASS", "r2r=ok(300) fill=ok(.2)"))[0], "PASS")
        v, f, tag = KW.geom_verdict(L.format("FAIL", "fill=FAIL(0.0997) empty=FAIL(0.617) r2r=ok(327) grt=ok(0)"))
        self.assertEqual((v, f, tag), ("PASS", ["empty", "fill"], "FILL-EXCEPTION"))
        v, f, tag = KW.geom_verdict(L.format("FAIL", "fill=FAIL(0.0997) channel_h=FAIL(1.065) r2r=ok(3)"))
        self.assertEqual((v, tag), ("FAIL", ""))
        self.assertEqual(KW.geom_verdict(L.format("FAIL", "fill=FAIL(0.1) tap_sinks=NA(None)"))[0], "FAIL")
        self.assertEqual(KW.geom_verdict(L.format("FAIL", "pin_reg=FAIL(9)"))[0], "FAIL")
        self.assertEqual(KW.geom_verdict("AP_AUTO_GEOM_ERROR dump rc 1")[0], "FAIL")


class FakeAP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self, d, cfgtext, active=()):
        self.AP_DIR = Path(d)
        self.REPO = Path(d)
        self.cfgtext = cfgtext
        self.active = set(active)
        self.logs, self.units, self.appends, self.cmds = [], [], [], []

    def read_coord(self, rel):
        return self.cfgtext if rel == "autopilot/kit_wave.json" else ""

    def log(self, m):
        self.logs.append(m)

    def sh(self, cmd, timeout=0, input=None):
        self.cmds.append(cmd)
        if cmd[-1] == "--status":
            return 0, STATUS, ""
        return 0, "", ""

    def rpy(self, host, code, args, timeout=0):
        return {"types": sorted(PLAN), "cores": []}

    def launch_unit(self, unit, logf, argv):
        self.units.append((unit, argv))
        return True

    def unit_active(self, unit):
        return unit in self.active

    def coord_append(self, rel, line):
        self.appends.append((rel, line))


class Step(unittest.TestCase):
    def test_launch_collect_enqueue_and_classify(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            ap = FakeAP(d, json.dumps(cfg(die_max_inflight=2)))
            st = KW.step(ap)
            self.assertEqual(len(ap.units), 2)                                  # per-die cap
            items = {r["item"]: r for r in st["items"].values()}
            self.assertEqual(set(items), {"kv3_phy_v1", "kv3_hg_v1"})
            self.assertTrue(any("KIT-WAVE [qwen_kvsys] -> DIE-KV-43" in a[1] for a in ap.appends))
            # second tick: both units ended; one PASS, one FAIL
            for r in st["items"].values():
                res = ({"verdict": "PASS", "stage": "geom", "kit": "intel1:/k/kv3_phy_v1", "geom_dir": "intel1:/g",
                        "geom_line": "AP_AUTO_GEOM PASS", "cells": 100000, "evidence": "intel1:/g/auto_geom.json"}
                       if r["item"] == "kv3_phy_v1" else
                       {"verdict": "FAIL", "stage": "place", "tail": "FACE_GUARD FAIL 12 bits", "evidence": "intel1:/k"})
                (Path(r["dir"]) / "result.json").write_text(json.dumps(res))
            ap2 = FakeAP(d, json.dumps(cfg(die_max_inflight=2)))
            st = KW.step(ap2)
            items = {}
            for r in st["items"].values():
                items.setdefault(r["item"], r)
            self.assertEqual(items["kv3_phy_v1"]["status"], "ENQUEUED")
            self.assertEqual(items["kv3_hg_v1"]["status"], "FAIL")
            self.assertEqual(items["kv3_hg_v1"]["class"], "PLAN")
            enq = [c for c in ap2.cmds if any("enqueue.py" in x for x in c)]
            self.assertEqual(len(enq), 1)
            self.assertIn("main@620077f42", enq[0])
            self.assertTrue(any(a[0] == "lanes/GEOM-REVIEW.md" for a in ap2.appends))   # 1st PASS sampled (1 in 5)
            self.assertEqual(len(ap2.units), 1)                                 # next pick kv3_hub_Eo; failed not retried
            self.assertIn("kv3hubEo", ap2.units[0][0])

    def test_canary_lifetime_cap_and_type_args(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            c = json.dumps(cfg(max_items_total=2, die_max_inflight=1, type_args={"kv3_phy_v1": ["--gpl-plain", "kv3_phy_v1"]}))
            st = KW.step(FakeAP(d, c))
            (r,) = st["items"].values()
            self.assertIn("--gpl-plain", json.loads((Path(r["dir"]) / "spec.json").read_text())["gen_args"])
            (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "gen", "tail": "is blocked"}))
            st = KW.step(FakeAP(d, c))
            self.assertEqual(len(st["items"]), 2)
            for r in st["items"].values():
                (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "gen", "tail": "is blocked"}))
            ap = FakeAP(d, c)
            st = KW.step(ap)
            self.assertEqual(ap.units, [])                                     # 2 used of 2
            self.assertEqual(len(st["items"]), 2)

    def test_infra_relaunched_once(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            c = json.dumps(cfg(die_max_inflight=1))
            st = KW.step(FakeAP(d, c))
            (r,) = st["items"].values()
            (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "place",
                                                                     "tail": "ot-run: NOT RUN"}))
            ap = FakeAP(d, c)
            st = KW.step(ap)
            (r,) = [x for x in st["items"].values() if x["item"] == "kv3_phy_v1"]
            self.assertEqual(r["attempt"], 2)
            self.assertEqual(r["status"], "RUNNING")
            (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "place",
                                                                     "tail": "ot-run: NOT RUN"}))
            st = KW.step(FakeAP(d, c))
            (r,) = [x for x in st["items"].values() if x["item"] == "kv3_phy_v1"]
            self.assertEqual((r["status"], r["class"], r["attempt"]), ("FAIL", "INFRA", 2))   # once only

    def test_stop_file_blocks_launch_not_collect(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            c = json.dumps(cfg(die_max_inflight=1))
            st = KW.step(FakeAP(d, c))
            (r,) = st["items"].values()
            (Path(d) / "kit_wave.stop").touch()
            (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "gen",
                                                                     "tail": "x is blocked"}))
            ap = FakeAP(d, c)
            st = KW.step(ap)
            self.assertEqual(ap.units, [])
            self.assertEqual(list(st["items"].values())[0]["status"], "FAIL")

    def test_running_unit_not_collected(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            c = json.dumps(cfg(die_max_inflight=1))
            st = KW.step(FakeAP(d, c))
            (r,) = st["items"].values()
            st = KW.step(FakeAP(d, c, active=[r["unit"]]))
            self.assertEqual(list(st["items"].values())[0]["status"], "RUNNING")

    def test_dry_run_launches_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            ap = FakeAP(d, json.dumps(cfg()))
            ap.DRY = True
            KW.step(ap)
            self.assertEqual(ap.units, [])
            self.assertFalse((Path(d) / KW.STATE_FILE).exists())
            self.assertTrue(any("would launch" in m for m in ap.logs))

    def test_no_config_is_inert(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            ap = FakeAP(d, "")
            KW.step(ap)
            self.assertEqual(ap.units, [])


class Overlay(unittest.TestCase):
    def test_overlay(self):
        rows = KW.parse_owners(OWN)
        st = {"items": {"a": {"die": "qwen_kvsys", "item": "kv3_hg_v1", "status": "FAIL", "class": "PLAN",
                              "reason": "face guard", "evidence": "intel1:/k", "updated": time.time()},
                        "b": {"die": "qwen_kvsys", "item": "kv3_hub_Eo", "status": "RUNNING", "unit": "kw-x",
                              "stage": "place", "updated": time.time()}}}
        self.assertEqual(KW.overlay_owners(rows, st), 2)
        r = {x["item"]: x for x in rows}
        self.assertEqual(r["kv3_hg_v1"]["owner"], "KIT-WAVE-1")
        self.assertIn("PLAN", r["kv3_hg_v1"]["next_step"])
        self.assertIn("kw-x", r["kv3_hub_Eo"]["live_job"])


if __name__ == "__main__":
    unittest.main()
