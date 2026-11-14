#!/usr/bin/env python3
"""tests for kit_wave.py (no ssh, no ot-run, no systemd: the autopilot host layer is faked)"""
import json
import sys
import tempfile
import time
import os
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402
import pytest  # noqa: E402

@pytest.fixture(autouse=True)
def _legacy_signoff_profile(monkeypatch):
    """this module pins the pre-R-MINIMAL gates (OT_SIGNOFF_PROFILE=legacy); R-MINIMAL is covered by
    tools/die_plan/test_signoff_profile.py"""
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")

GATE = {"g0c": "PASS", "bind": "PASS", "clock": "PASS", "evidence": "DIE-KV-40 21:07"}


def cfg(**die_over):
    d = {"enabled": True, "event": "event28w_c", "gate": dict(GATE), "plan": "/srv/p/plan_c.json", "gen_host": "intel1",
         "src": "/srv/wt/kw", "src_sha": "620077f42", "owner_lane": "DIE-KV-43"}
    d.update(die_over)
    return {"enabled": True, "max_inflight": 40, "max_launch_per_tick": 6, "wait_visual": False,   # visual gate: own tests
            "dies": {"qwen_kvsys": d}}


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
    def test_item_inputs_may_name_a_private_src(self):
        # KW-FIX-45 11-11: HBM opsb_group builds from its own cp -al src copy while the die src stays shared
        c = cfg(item_inputs={"kv3_pc": {"src": "/x/private", "src_sha": "abc1234", "queue_src": "b/c@abc1234"}})
        s = KW.spec_for(c, "qwen_kvsys", "kv3_pc", "intel2")
        self.assertEqual((s["src"], s["src_sha"], s["queue_src"]), ("/x/private", "abc1234", "b/c@abc1234"))
        o = KW.spec_for(c, "qwen_kvsys", "kv3_pc_other", "intel2")
        self.assertNotEqual(o["src"], "/x/private")

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

    def test_preflight_args_default_and_explicit_empty(self):
        self.assertEqual(KW.spec_for(cfg(), "qwen_kvsys", "kv3_pc", "intel2")["preflight_args"], ["--contract"])
        self.assertEqual(KW.spec_for(cfg(preflight_args=[]), "qwen_kvsys", "kv3_pc", "intel2")["preflight_args"], [])

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
        c["dies"]["s81_head"]["event"] = "l45"                 # HEAD plan of record 10-30 20:14
        self.assertTrue(KW.gate(c, "s81_head")[0])
        c["dies"]["s81_head"]["event"] = "l46"                 # HEAD plan of record 10-30 21:03
        self.assertTrue(KW.gate(c, "s81_head")[0])
        c["dies"]["s81_head"]["event"] = "l47"                 # HEAD plan of record 10-31 01:43
        self.assertTrue(KW.gate(c, "s81_head")[0])
        for ev in ("l47k", "l47t"):                            # COORD 10-31 04:4x: l47k now, l47t after merge
            c["dies"]["s81_head"]["event"] = ev
            self.assertTrue(KW.gate(c, "s81_head")[0])
        for ev in ("l48w", "l48x", "l48y", "l48z", "l48h0", "l48h1", "l48rf"):   # l48h0 COORD 11-03 00:2x (a); l48h1 DIE-HEAD-56 11-03 04:5x            # COORD 10-31 16:2x l48w; l48x pin fixes; l48y COORD 11-01 01:0x; l48z 11-01 14:0x
            c["dies"]["s81_head"]["event"] = ev
            self.assertTrue(KW.gate(c, "s81_head")[0])
        for ev in ("l48", "l48q"):
            c["dies"]["s81_head"]["event"] = ev
            self.assertFalse(KW.gate(c, "s81_head")[0])
        c["dies"]["s81_head"]["event"] = "l48"
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


def kit_own_hd(KW):
    return KW._own_wave_unit({"owner": "KIT-WAVE-5", "item": "hd_mesh", "live_job":
                              "ap-68bf0d080dcd-a1 68bf0d080dcd; ot-run pid 324465 1105f2/kit-wave/s81_head/l48ub/items/hd_mesh_e/attempt_3/gen/hd_mesh_e (+3)"})


class Select(unittest.TestCase):
    def test_pilot_first_caps_unproven_class(self):
        # OWNER 12.27a: an unproven die x kit class has at most 2 kits in flight; in-flight kits count, none killed
        own = OWN + "".join(f"qwen_kvsys\tkv3_st_t{i}\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t999m\tkit it\t\tKV-PLAN\t1\t\n"
                            for i in range(1, 6))
        rows = KW.parse_owners(own)
        plan = PLAN | {f"kv3_st_t{i}" for i in range(1, 6)}
        picks, skip = KW.select(rows, cfg(), "qwen_kvsys", {"items": {}}, plan)
        st_p = [p["item"] for p in picks if p["item"].startswith("kv3_st")]
        self.assertEqual(st_p, ["kv3_st_t1", "kv3_st_t2"])
        self.assertEqual(len(skip["PILOT-FIRST 12.27a: class qwen_kvsys|type|kv#_st_t# unproven, 2 pilot(s) in flight"]), 3)
        self.assertIn("kv3_hg_v1", [p["item"] for p in picks])                 # other classes still pilot
        run = {"items": {"x": {"die": "qwen_kvsys", "item": "kv3_st_t9", "kind": "type", "status": "RUNNING"}}}
        picks, _ = KW.select(rows, cfg(), "qwen_kvsys", run, plan)
        self.assertEqual([p["item"] for p in picks if p["item"].startswith("kv3_st")], ["kv3_st_t1"])
        run["items"]["y"] = {"die": "qwen_kvsys", "item": "kv3_st_t8", "kind": "type", "status": "ENQUEUED",
                             "q_status": "SIGNED"}
        picks, _ = KW.select(rows, cfg(), "qwen_kvsys", run, plan)               # signed pilot -> volume
        self.assertEqual(len([p for p in picks if p["item"].startswith("kv3_st")]), 5)
        picks, _ = KW.select(rows, cfg(pilot_signed=["qwen_kvsys|type|kv#_st_t#"]), "qwen_kvsys", {"items": {}}, plan)
        self.assertEqual(len([p for p in picks if p["item"].startswith("kv3_st")]), 5)
        picks, _ = KW.select(rows, cfg(pilot_gate=False), "qwen_kvsys", {"items": {}}, plan)
        self.assertEqual(len([p for p in picks if p["item"].startswith("kv3_st")]), 5)

    def test_pilot_key_map(self):
        self.assertEqual(KW.pilot_key({}, "s81", "slice_station__t7__cl362204c4"), "s81|type|slice_station")
        d = {"pilot_classes": [{"class": "s81|type|station", "items": ["slice_station__*"]}]}
        self.assertEqual(KW.pilot_key(d, "s81", "slice_station__t46"), "s81|type|station")

    def test_selection_and_order(self):
        rows = KW.parse_owners(OWN)
        picks, skip = KW.select(rows, cfg(), "qwen_kvsys", {"items": {}}, PLAN)
        self.assertEqual([p["item"] for p in picks], ["kv3_phy_v1", "kv3_hg_v1", "kv3_hub_Eo"])   # replicas desc
        self.assertEqual(skip["live job (another lane)"], ["kv3_io_cor_v1"])
        self.assertIn("kv3_pc", skip["lane activity < 3 h (KV-KITS-W)"])
        self.assertEqual(skip["kind core not in wave"], ["qkd_hr_cdc_ci"])
        self.assertEqual(skip["not in plan of record"], ["kv3_gone"])
        self.assertNotIn("kv3_hroot", [p["item"] for p in picks])          # KIT-PLACED not in take_states

    def test_own_queue_job_on_parent_is_not_a_claim(self):
        own = lambda lj, owner="KIT-WAVE-12": KW._own_wave_unit({"owner": owner, "item": "sle_su_l1", "live_job": lj})
        self.assertTrue(own("ap-7aaad3d48876-a1 7aaad3d48876"))
        self.assertTrue(own("ap-7aaad3d48876-a1 7aaad3d48876; ot-run pid 2830758 36e864/items/sle_su_l1__cl5ea486db/gen/sle_su_l1__cl5ea486db"))
        self.assertFalse(own("ap-7aaad3d48876-a1 7aaad3d48876; ot-run pid 2830758 scratch/lane/run/other_dir"))
        self.assertFalse(own("ap-7aaad3d48876-a1 7aaad3d48876", owner="DIE-QC-75"))
        # KW-FIX-12 11-05: OWNERS folds hd_mesh_e under hd_mesh; its routed wave kit blocked hd_mesh on a new plan block
        self.assertTrue(kit_own_hd(KW))

    def test_own_wave_unit_every_listed_job(self):
        """KW-FIX-35-P 11-08: two (or more) of the wave's own route jobs on a parent are not a claim; one foreign is"""
        own = lambda lj, owner="KIT-WAVE-12": KW._own_wave_unit({"owner": owner, "item": "slw_su_l0", "live_job": lj})
        self.assertTrue(own("ap-0307dbcbc356-a1 0307dbcbc356; ap-5bf91438d5b4-a1 5bf91438d5b4"))
        self.assertTrue(own("ap-16955edce096-a2 16955edce096; ap-4956a79e1387-a1 4956a79e1387 (+2)"))
        self.assertTrue(own("ap-0307dbcbc356-a1 0307dbcbc356; "
                            "ot-run pid 9 36e864/items/slw_su_l0__cl1a1c1f8f/attempt_13/gen/slw_su_l0__cl1a1c1f8f"))
        self.assertFalse(own("ap-0307dbcbc356-a1 0307dbcbc356; ot-run pid 9 scratch/lane/run/other_dir"))
        self.assertFalse(own("ap-0307dbcbc356-a1 0307dbcbc356; ap-5bf91438d5b4-a1 5bf91438d5b4", owner="DIE-QC-75"))
        self.assertFalse(own(""))

    def test_own_wave_unit_on_parent_is_not_a_claim(self):
        # DIE-QC-63/KITS 11-02: overlay_owners puts a sibling class's own wave unit on the parent row; the other
        # classes (new or released retries) must still launch, the in-flight class must not relaunch
        own = OWN + ("qwen_kvsys\tkv3_st\ttype\tNEEDS-KIT\tKIT-WAVE-1\tkit-wave unit kw-x-1 (geom)\t0m\tKIT-WAVE in flight"
                     "\t\tKV-PLAN\t3\t\n")
        rows = KW.parse_owners(own)
        plan = {t: "b" + t[-1] * 12 for t in ("kv3_st__cla", "kv3_st__clb", "kv3_st__clc")}
        st = {"items": {
            KW.item_key("qwen_kvsys", "event28w_c", "kv3_st__cla", plan["kv3_st__cla"]):
                {"status": "RUNNING", "attempt": 1, "item": "kv3_st__cla", "die": "qwen_kvsys"},
            KW.item_key("qwen_kvsys", "event28w_c", "kv3_st__clb", plan["kv3_st__clb"]):
                {"status": "FAIL", "attempt": 1, "item": "kv3_st__clb", "die": "qwen_kvsys"}}}
        c = cfg(pilot_gate=False, retry=["kv3_st__clb@1"])
        picks, skip = KW.select(rows, c, "qwen_kvsys", st, plan)
        got = sorted(p["item"] for p in picks if p["item"].startswith("kv3_st"))
        self.assertEqual(got, ["kv3_st__clb", "kv3_st__clc"])
        self.assertNotIn("kv3_st", skip.get("live job (another lane)", []))
        # ownership.py 'ot-run pid' form of the wave's own job (last 70 chars of the kit dir) is not a claim either
        for lj in ("ot-run pid 3472946 _st__cla/gen/kv3_st__cla", "ot-run pid 1069 9da87/items/kv3_st__cla/attempt_4"):
            rows = KW.parse_owners(own.replace("kit-wave unit kw-x-1 (geom)", lj))
            picks, skip = KW.select(rows, c, "qwen_kvsys", st, plan)
            self.assertNotIn("kv3_st", skip.get("live job (another lane)", []), lj)
        rows = KW.parse_owners(own.replace("kit-wave unit kw-x-1 (geom)", "ot-run pid 9 /srv/other/kv3_pc/run"))
        picks, skip = KW.select(rows, c, "qwen_kvsys", st, plan)
        self.assertIn("kv3_st", skip["live job (another lane)"])
        # a die-owned hold naming one plan class holds that class (not only the parent row)
        picks, skip = KW.select(KW.parse_owners(own), dict(c, dies={"qwen_kvsys": dict(c["dies"]["qwen_kvsys"],
                                hold_items={"kv3_st__clc": "held"})}), "qwen_kvsys", st, plan)
        self.assertEqual(sorted(p["item"] for p in picks if p["item"].startswith("kv3_st")), ["kv3_st__clb"])
        self.assertEqual(skip["die-owned hold: held"], ["kv3_st__clc"])
        # a foreign lane's live job still blocks
        rows = KW.parse_owners(own.replace("KIT-WAVE-1\tkit-wave unit", "KV-KITS\tot-run pid 7"))
        picks, skip = KW.select(rows, c, "qwen_kvsys", st, plan)
        self.assertIn("kv3_st", skip["live job (another lane)"])

    def test_generic_owner_label_is_not_a_type_claim(self):
        # KW-FIX-33 (COORD 11-07 22:53): the die-wide census label HBM-PLAN (fresh last_activity on every HBM type row)
        # does not claim a type row; a specific lane owner still does, and the label still claims a core row
        own = OWN.replace("kv3_pc\ttype\tNEEDS-KIT\tKV-KITS-W\tnone\t122m", "kv3_pc\ttype\tNEEDS-KIT\tHBM-PLAN\tnone\t6m")
        rows = KW.parse_owners(own)
        picks, skip = KW.select(rows, cfg(), "qwen_kvsys", {"items": {}}, PLAN)
        self.assertIn("kv3_pc", [p["item"] for p in picks])
        self.assertFalse(any(k.startswith("lane activity") for k in skip))
        picks, skip = KW.select(rows, cfg(generic_owner_labels=[]), "qwen_kvsys", {"items": {}}, PLAN)
        self.assertNotIn("kv3_pc", [p["item"] for p in picks])
        self.assertIn("kv3_pc", skip["lane activity < 3 h (HBM-PLAN)"])
        rows = KW.parse_owners(OWN)                                          # a specific lane claim holds
        picks, skip = KW.select(rows, cfg(), "qwen_kvsys", {"items": {}}, PLAN)
        self.assertIn("kv3_pc", skip["lane activity < 3 h (KV-KITS-W)"])
        core = OWN.replace("qkd_hr_cdc_ci\tcore\tNEEDS-KIT\tCODEX\tnone\t961m", "qkd_hr_cdc_ci\tcore\tNEEDS-KIT\tHBM-PLAN\tnone\t6m")
        picks, skip = KW.select(KW.parse_owners(core), cfg(kinds=["type", "core"]), "qwen_kvsys", {"items": {}}, PLAN)
        self.assertIn("qkd_hr_cdc_ci", skip["lane activity < 3 h (HBM-PLAN)"])

    def test_wave_runner_lane_lines_are_not_claims(self):
        rows = KW.parse_owners(OWN.replace("kv3_pc\ttype\tNEEDS-KIT\tKV-KITS-W", "kv3_pc\ttype\tNEEDS-KIT\tKIT-WAVE-2"))
        picks, skip = KW.select(rows, cfg(), "qwen_kvsys", {"items": {}}, PLAN)
        self.assertIn("kv3_pc", [p["item"] for p in picks])
        self.assertFalse(any(k.startswith("lane activity") for k in skip))

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

    def test_block_sha_keys_kit(self):
        # OWNER 12.20: same block under a new event = same kit (no regeneration); changed block = new item
        rows = KW.parse_owners(OWN)
        blocks = {t: "a" * 64 for t in PLAN}
        k = KW.item_key("qwen_kvsys", "event28w_c", "kv3_phy_v1", "a" * 64)
        self.assertEqual(k, "qwen_kvsys|kv3_phy_v1|b" + "a" * 12)
        st = {"items": {k: {"status": "ENQUEUED", "attempt": 1}}}
        picks, skip = KW.select(rows, cfg(event="event29"), "qwen_kvsys", st, blocks)
        self.assertNotIn("kv3_phy_v1", [p["item"] for p in picks])
        self.assertEqual(skip["wave kit enqueued"], ["kv3_phy_v1"])
        blocks["kv3_phy_v1"] = "b" * 64
        picks, _ = KW.select(rows, cfg(event="event29"), "qwen_kvsys", st, blocks)
        p = [p for p in picks if p["item"] == "kv3_phy_v1"]
        self.assertEqual(p[0]["block_sha"], "b" * 64)


STATUS = ("ot-run status: epyc2 admits 713 GB (avail 845, reserve 0, fresh 0, peak 67.2) load 37/128 run 24 root 2% "
          "scratch 187 GB | intel1 admits 30 GB (avail 784) load 58/112 run 35 root 8% scratch 1228 GB | localhost admits "
          "251 GB (avail 533) load 112/112 run 45 root 13% scratch 822 GB | next 16-thread 32 GB job -> epyc2")


class RotateDies(unittest.TestCase):
    """KW-FIX-43 11-09: no die is always last in a pass's launch order"""
    ROWS = [("hbm", 1), ("hbm", 2), ("qwen_compute", 3), ("s81", 4)]

    def order(self, n):
        return KW.rotate_dies(self.ROWS, lambda r: r[0], n)

    def test_pass_zero_or_missing_is_sorted(self):
        self.assertEqual(self.order(0), self.ROWS)
        self.assertEqual(self.order(None), self.ROWS)

    def test_every_die_leads_once_per_cycle_and_keeps_its_rows_in_order(self):
        self.assertEqual({self.order(n)[0][0] for n in range(3)}, {"hbm", "qwen_compute", "s81"})
        self.assertEqual(self.order(2), [("s81", 4), ("hbm", 1), ("hbm", 2), ("qwen_compute", 3)])

    def test_one_die_unchanged(self):
        rows = [("s81", 2), ("s81", 1)]
        self.assertEqual(KW.rotate_dies(rows, lambda r: r[0], 7), rows)


class Capacity(unittest.TestCase):
    def test_parse_status(self):
        s = KW.parse_otrun_status(STATUS)
        self.assertEqual(s["epyc2"], {"admit": 713, "load": 37.0, "cores": 128, "run": 24, "scratch_gb": 187})
        self.assertEqual(s["localhost"]["run"], 45)

    def test_parse_status_waiters_and_negative_admit(self):
        # ot-run 10-31: 'waiters n:GB' between load and run, and negative admission on a full host
        s = KW.parse_otrun_status(
            "ot-run status: epyc2 admits -29 GB (avail 193, reserve 0, fresh 47.1, peak 110.9) load 212/128 run 29 root 2% "
            "scratch 141 GB | intel1 admits 163 GB (avail 393, reserve 0, fresh 47.2, peak 118.5) load 185/112 waiters "
            "1:200 GB run 37 root 9% scratch 830 GB | localhost admits 329 GB (avail 479) load 249/112 run 43 root 14% "
            "scratch 731 GB | next 16-thread 32 GB job -> intel1")
        self.assertEqual(s["intel1"], {"admit": 163, "load": 185.0, "cores": 112, "run": 37, "wait_n": 1, "wait_gb": 200,
                                       "scratch_gb": 830})
        self.assertEqual(s["epyc2"]["admit"], -29)
        self.assertEqual(s["localhost"]["run"], 43)

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
    def test_pdn_info_is_no_plan_error_and_error_247_is_infra(self):
        kill = "[INFO PDN-0001] Inserting grid: top\nmake[1]: *** [Makefile:464: do-2_4_floorplan_pdn] Error 247\n"
        self.assertEqual(KW.classify("place", kill)[0], "INFRA")
        self.assertNotEqual(KW.classify("place", "[INFO PDN-0001] Inserting grid: top\n")[0], "PLAN")
        self.assertEqual(KW.classify("place", "Error: pdn.tcl, 7 PDN-0179\n")[0], "PLAN")
        self.assertEqual(KW.classify("place", "[ERROR PDN-0179] no straps\n")[0], "PLAN")

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
            ("place", "Error: floorplan.tcl, 5 OT_NATIVE_CELL_CAP actual standard cell count 541583 above 517000 run cap", "PLAN"),
            ("place", "ot-run: NOT COMPLETED client text\nError: floorplan.tcl, 5 OT_NATIVE_CELL_CAP actual standard cell count 500460 above 400000 run cap\nexit 143", "PLAN"),
            ("bind", "Traceback\nFileNotFoundError: [Errno 2] No such file or directory: 'kv36/x.json'", "FLOW"),
            ("bind", "bind of record not clean\nBIND errors 3", "PLAN"),
            ("bind", '{"errors": 0, "unbound": 0, "undriven": 0, "multiply_bound": 0}\nBIND errors 2', "PLAN"),
            ("gen", "Traceback (most recent call last):\ncore_clock_contract.ContractError: x: internal core CTS requires explicit SIGNED TT/FF mean metadata", "PLAN"),
            ("bind", "Terminated                 python3 tools/die_plan/bind.py", "INFRA"),
            ("kit_rtl", "bind: ERROR kit-rtl col_h9: instances of col_h9 carry different parameters ['#(.P_u_c5_0_INSTANCE(", "PLAN"),
            ("place", "something odd happened", "FLOW"),
            # AUTOBUILD-PIPE-4 10-31: KV core kits ingest_eng (no static SRAM sites) / core_order (unregistered faces)
            ("preflight", "KIT_PREFLIGHT FAIL issues 3\n  - macro_channels: 1 macro master(s) but no staged "
                          "MACRO_PLACEMENT_TCL (None): placement not static, channels/entry not checkable\n"
                          "  - clock_entry_clear: 1 macro master(s) but no staged MACRO_PLACEMENT_TCL (None)", "PLAN"),
            ("place", "DONT_USE_CHECK PASS\nCORE_PREFLIGHT FAIL /work/run/1_2_yosys.v {'shared': 135, "
                      "'feedthrough': 8, 'unregistered': 1}  port_gate PASS", "PLAN"),
            ("place", "Error: Synthesized memory size 8192 exceeds SYNTH_MEMORY_MAX_BITS", "FLOW"),
            ("place", "ERROR: Module `ot_x' referenced in module `top' is not part of the design.", "RTL"),
        ]
        for stage, text, want in cases:
            self.assertEqual(KW.classify(stage, text)[0], want, (stage, text))

    def test_reason_carries_stage(self):
        cls, why = KW.classify("gen", "reset tap is blocked")
        self.assertIn("@gen", why)
        self.assertIn(cls, KW.CLASSES)


CLAND = ("Error: global_place.tcl, 5 OT_CLAND no legal nonoverlapping row/site in reserved band for "
         "u_bound.u_cland_reader_start_ft20_i_4/q$_SDFF_PN0_ (reader-start:ft20_i)")
REFUSED_THEN_RAN = ("ot-heavy: NOT RUN: no memory on dear-crayfish within 599 s (need 0.7 x 29 = 20 GB, admissible 4 GB)\n"
                    "ot-run: NOT RUN on epyc2: ot-heavy exit 75\n"
                    "KW_SSH_RETRY place try 2 (ot-run NOT RUN before the command ran)\n"
                    "ot-run: epyc2 admits\n[INFO GPL-0002] DBU: 1000\n" + CLAND + "\n"
                    "make[1]: *** [Makefile:499: do-3_3_place_gp] Error 1\n"
                    "ot-run: RAN on epyc2 (unit oth-ubuntu-771973-1794291072): exit 2\nKW_PLACE_RC=2\n")


class PreflightAdvisory(unittest.TestCase):
    """KW-FIX-44 11-10 (DIE-KV-97): the --plan-dir preflight's contract advisories reach result.json / the row"""

    def test_receipt_to_summary(self):
        rec = {"verdict": "PASS", "contract_advisory": {
            "macro_pin_grid": {"verdict": "FAIL", "n_errors": 6, "errors": [
                "macro ot_rom_64x32_m2#5 at (302.4, 250.56) R0: 40 signal pin(s) off the make_tracks.tcl track grid"] * 6},
            "macro_channels": {"verdict": "PASS", "errors": []}, "keep_hook": {"verdict": "NA", "errors": []}}}
        adv = KW.preflight_advisory("Warning: ssh chatter\n" + json.dumps(rec) + "\n")
        self.assertEqual(list(adv), ["macro_pin_grid"])
        self.assertEqual(adv["macro_pin_grid"]["n"], 6)
        self.assertEqual(len(adv["macro_pin_grid"]["errors"]), 5)
        line = KW.advisory_line(adv)
        self.assertTrue(line.startswith("macro_pin_grid 6 (macro ot_rom_64x32_m2#5"), line)
        self.assertEqual(KW.advisory_line(KW.preflight_advisory(json.dumps({"contract_advisory": {}}))), "")
        self.assertIn("unread", KW.preflight_advisory("cat: no such file"))
        self.assertIn("unread", KW.advisory_line(KW.preflight_advisory("")))


class FirstRealClassWins(unittest.TestCase):
    """KW43-77 11-10: a NOT RUN try retried by a try that RAN is superseded; the ran try's failure class decides, also
    when reclassify / auto-rejudge re-reads the whole stored stage log"""

    def test_refused_try_then_ran_try_is_the_ran_class(self):
        cls, why = KW.classify("place", REFUSED_THEN_RAN)
        self.assertEqual(cls, "FLOW")
        self.assertIn("OT_CLAND", why)

    def test_not_run_without_a_later_run_stays_infra(self):
        self.assertEqual(KW.classify("place", "ot-run: NOT RUN on epyc2: ot-heavy exit 75\n")[0], "INFRA")
        # a step that ran, then the stage's own try refused: the refusal is the last word
        txt = "ot-run: RAN on epyc2 (unit u1): exit 0\nPROBE OK\not-run: NOT RUN on epyc2: ot-heavy exit 75\n"
        self.assertEqual(KW.classify("place", txt)[0], "INFRA")
        # a ran try that itself died on infra stays INFRA
        self.assertEqual(KW.classify("place", "ot-run: NOT RUN on epyc2: ot-heavy exit 75\n"
                                     "No space left on device\not-run: RAN on epyc2 (unit u2): exit 1\n")[0], "INFRA")

    def test_reclassify_keeps_the_collected_flow_class(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "a25"
            d.mkdir()
            (d / "place.log").write_text(REFUSED_THEN_RAN)
            (d / "result.json").write_text(json.dumps({
                "stage": "place", "verdict": "FAIL", "errors": CLAND + "\nmake[1]: *** Error 1",
                "tail": "ot-run: RAN on epyc2 (unit oth-ubuntu-771973-1794291072): exit 2\nKW_PLACE_RC=2\n"}))
            res = json.loads((d / "result.json").read_text())
            cls, why = KW.classify("place", res["errors"] + "\n" + res["tail"])
            self.assertEqual(cls, "FLOW")
            rec = {"status": "FAIL", "class": cls, "reason": why, "stage": "place", "dir": str(d),
                   "attempt": 25, "infra_base": 22}
            st = {"items": {"qwen_kvsys|kv3_pv_v12|b276d65256f4c": rec}}
            ch = KW.reclassify(st, write=True)
            self.assertEqual([c for c in ch if c[2][0] != "FLOW"], [])
            self.assertEqual(rec["class"], "FLOW")
            self.assertIn("OT_CLAND", rec["reason"])
            self.assertEqual((rec["attempt"], rec["infra_base"]), (25, 22))


class GeomVerdict(unittest.TestCase):
    def test_lines(self):
        L = "AP_AUTO_GEOM AUTO-GEOM {} kv3 x KIT-WAVE 3_place {}"
        self.assertEqual(KW.geom_verdict(L.format("PASS", "r2r=ok(300) fill=ok(.2)"))[0], "PASS")
        v, f, tag = KW.geom_verdict(L.format("FAIL", "fill=FAIL(0.0997) empty=FAIL(0.617) r2r=ok(327) grt=ok(0)"))
        self.assertEqual((v, f, tag), ("PASS", ["empty", "fill"], "FILL-EXCEPTION"))
        v, f, tag = KW.geom_verdict(L.format("FAIL", "fill=FAIL(0.0997) channel_h=FAIL(1.065) r2r=ok(3)"))
        self.assertEqual((v, tag), ("FAIL", ""))
        self.assertEqual(KW.geom_verdict(L.format("FAIL", "fill=FAIL(0.1) tap_sinks=NA(None)"))[0], "FAIL")
        real = ("AP_AUTO_GEOM AUTO-GEOM FAIL geomprobe KIT-WAVE 3_place outline=NA(241.92x241.92) fill=FAIL(0.1494) "
                "empty=FAIL(0.6394) r2r=FAIL(464.56) r2r_count=FAIL(259) aspect=ok(1.0) fill_hi=ok(0.1494) grt=ok(0)")
        self.assertEqual(KW.geom_verdict(real), ("FAIL", ["empty", "fill", "outline", "r2r", "r2r_count"], ""))
        real2 = real.replace(" outline=NA(241.92x241.92)", " outline=ok(241.92x241.92)").replace(
            " r2r=FAIL(464.56) r2r_count=FAIL(259)", " r2r=ok(464.56) r2r_count=ok(0)")
        self.assertEqual(KW.geom_verdict(real2), ("PASS", ["empty", "fill"], "FILL-EXCEPTION"))
        self.assertEqual(KW.geom_verdict(L.format("FAIL", "pin_reg=FAIL(9)"))[0], "FAIL")
        self.assertEqual(KW.geom_verdict("AP_AUTO_GEOM_ERROR dump rc 1")[0], "FAIL")
        # GEOM-111 class E: estimate congestion waived only when the measured GRT is 0 overflow
        v, f, tag = KW.geom_verdict(L.format("FAIL", "fill=FAIL(0.1) col_v=FAIL(1.165) channel_v=FAIL(1.165) grt=ok(0)"))
        self.assertEqual((v, f), ("PASS-COND", ["channel_v", "col_v", "fill"]))
        self.assertIn("GEOM-111 class E", tag)
        self.assertEqual(KW.geom_verdict(L.format("FAIL", "col_v=FAIL(1.05) grt=FAIL(4843)"))[0], "FAIL")
        self.assertEqual(KW.geom_verdict(L.format("FAIL", "channel_h=FAIL(1.004) r2r=FAIL(435) grt=ok(0)"))[0], "FAIL")
        self.assertEqual(KW.geom_verdict(L.format("FAIL", "channel_h=FAIL(1.004) grt=NA(None)"))[0], "FAIL")


class QueueFill(unittest.TestCase):
    """OWNER 11-01 / COORD 05:3x: keep the ot-run queue full; unproven-class volume queued behind its pilots"""
    def test_queue_fill_ignores_admission(self):
        s = {"epyc2": {"admit": -98, "run": 1}, "intel1": {"admit": -58, "run": 1}}
        self.assertEqual(KW.capacity(cfg(), "qwen_kvsys", {"items": {}}, s), 0)
        c = dict(cfg(die_max_inflight=5), queue_fill=True)
        self.assertEqual(KW.capacity(c, "qwen_kvsys", {"items": {}}, s), 5)
        self.assertEqual(KW.capacity(c, "qwen_kvsys", {"items": {}}, {}), 5)    # status down: caps still bound it

    def test_volume_queued_behind_pilots(self):
        own = OWN + "".join(f"qwen_kvsys\tkv3_st_t{i}\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t999m\tkit it\t\tKV-PLAN\t1\t\n"
                            for i in range(1, 6))
        rows = KW.parse_owners(own)
        plan = PLAN | {f"kv3_st_t{i}" for i in range(1, 6)}
        picks, skip = KW.select(rows, cfg(pilot_mode="queue"), "qwen_kvsys", {"items": {}}, plan)
        names = [p["item"] for p in picks]
        vol = [p["item"] for p in picks if p.get("volume")]
        self.assertEqual(vol, ["kv3_st_t3", "kv3_st_t4", "kv3_st_t5"])
        self.assertEqual(names[-3:], vol)                                       # volume after every pilot
        self.assertFalse(any(k.startswith("PILOT-FIRST") for k in skip))
        self.assertEqual({p["volume"] for p in picks if p.get("volume")}, {"qwen_kvsys|type|kv#_st_t#"})

    def test_cancel_queued_volume_on_pilot_fail(self):
        with tempfile.TemporaryDirectory() as d:
            ap = FakeAP(d, "{}")
            c = cfg(pilot_mode="queue")
            cls = "qwen_kvsys|type|kv#_st_t#"
            now = time.time()
            for n in ("q", "r", "s"):
                (Path(d) / n).mkdir()
            (Path(d) / "q" / "place.live.log").write_text("waiting for memory\n")
            (Path(d) / "r" / "place.live.log").write_text("ot-heavy: admitted on intel1 as oth-1 after 5 s\n")
            st = {"items": {
                "p": {"die": "qwen_kvsys", "item": "kv3_st_t1", "status": "FAIL", "class": "PLAN", "updated": now},
                "q": {"die": "qwen_kvsys", "item": "kv3_st_t3", "status": "RUNNING", "volume": cls, "unit": "u3",
                      "dir": str(Path(d) / "q"), "started": now - 60},
                "r": {"die": "qwen_kvsys", "item": "kv3_st_t4", "status": "RUNNING", "volume": cls, "unit": "u4",
                      "dir": str(Path(d) / "r"), "started": now - 60},
                "s": {"die": "qwen_kvsys", "item": "kv3_st_t5", "status": "RUNNING", "volume": cls, "unit": "u5",
                      "dir": str(Path(d) / "s"), "started": now + 60},            # queued after the failure: kept
            }}
            notices = {}
            # KW-FIX-1 11-02: a WAIT-DEP pilot record (child view not signed yet) never stops its class volume
            st["items"]["p"]["reason"] = "WAIT-DEP child view (lef/lib) missing in the plan @gen: ValueError"
            self.assertEqual(KW.cancel_class_volume(ap, c, st, {}), 0)
            st["items"]["p"]["reason"] = "AUTO-GEOM rule FAIL"
            self.assertEqual(KW.cancel_class_volume(ap, c, st, notices), 1)
            self.assertEqual(st["items"]["q"]["status"], "CANCELLED")
            self.assertEqual(st["items"]["r"]["status"], "RUNNING")             # admitted = running, never cancelled
            self.assertEqual(st["items"]["s"]["status"], "RUNNING")
            self.assertIn(["systemctl", "--user", "stop", "u3"], ap.cmds)
            # no pilot_mode queue -> nothing happens
            st["items"]["s"]["started"] = now - 60
            self.assertEqual(KW.cancel_class_volume(ap, cfg(), st, {}), 0)
            # the class signs off -> cancelled volume is pickable again
            st["items"]["z"] = {"die": "qwen_kvsys", "item": "kv3_st_t2", "status": "ENQUEUED", "q_status": "SIGNED"}
            rows = KW.parse_owners(OWN + "qwen_kvsys\tkv3_st_t3\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t999m\tkit it\t\tKV-PLAN\t1\t\n")
            st["items"][KW.item_key("qwen_kvsys", "event28w_c", "kv3_st_t3")] = st["items"].pop("q")
            picks, _ = KW.select(rows, c, "qwen_kvsys", st, PLAN | {"kv3_st_t3"})
            self.assertIn("kv3_st_t3", [p["item"] for p in picks])


class VolumeSrcTest(unittest.TestCase):
    def test_old_src_pilot_fail_does_not_cancel_new_src_volume(self):
        """KW-FIX-4 11-03: a pilot FAIL generated from a superseded src never cancels volume on the current src"""
        with tempfile.TemporaryDirectory() as d:
            ap = FakeAP(d, "{}")
            c = cfg(pilot_mode="queue")
            c["dies"]["qwen_kvsys"]["src_sha"] = "new"
            cls = "qwen_kvsys|type|kv#_st_t#"
            now = time.time()
            for n in ("p", "q"):
                (Path(d) / n).mkdir()
            (Path(d) / "p" / "spec.json").write_text(json.dumps({"src_sha": "old"}))
            (Path(d) / "q" / "place.live.log").write_text("waiting for memory\n")
            st = {"items": {
                "p": {"die": "qwen_kvsys", "item": "kv3_st_t1", "status": "FAIL", "class": "PLAN", "updated": now,
                      "dir": str(Path(d) / "p"), "reason": "OT_RESET_CORE"},
                "q": {"die": "qwen_kvsys", "item": "kv3_st_t3", "status": "RUNNING", "volume": cls, "unit": "u3",
                      "dir": str(Path(d) / "q"), "started": now - 60},
            }}
            self.assertEqual(KW.cancel_class_volume(ap, c, st, {}), 0)
            (Path(d) / "p" / "spec.json").write_text(json.dumps({"src_sha": "new"}))
            self.assertEqual(KW.cancel_class_volume(ap, c, st, {}), 1)


class VolumeGeomTest(unittest.TestCase):
    def test_geom_fail_does_not_cancel_volume(self):
        with tempfile.TemporaryDirectory() as d:
            ap = FakeAP(d, "{}")
            c = cfg(pilot_mode="queue")
            cls = "qwen_kvsys|type|kv#_st_t#"
            now = time.time()
            (Path(d) / "q").mkdir()
            (Path(d) / "q" / "place.live.log").write_text("waiting for memory\n")
            st = {"items": {
                "p": {"die": "qwen_kvsys", "item": "kv3_st_t1", "status": "FAIL", "class": "PLAN", "stage": "geom",
                      "updated": now},
                "q": {"die": "qwen_kvsys", "item": "kv3_st_t3", "status": "RUNNING", "volume": cls, "unit": "u3",
                      "dir": str(Path(d) / "q"), "started": now - 60},
            }}
            self.assertEqual(KW.cancel_class_volume(ap, c, st, {}), 0)
            self.assertEqual(st["items"]["q"]["status"], "RUNNING")
            # a gen-stage pilot FAIL still cancels
            st["items"]["p"]["stage"] = "gen"
            self.assertEqual(KW.cancel_class_volume(ap, c, st, {}), 1)
            # back to a geom-only FAIL: the cancelled volume is pickable again (its reason no longer stands)
            st["items"]["p"]["stage"] = "geom"
            rows = KW.parse_owners(OWN + "qwen_kvsys\tkv3_st_t3\ttype\tNEEDS-KIT\tKV-PLAN\tnone\t999m\tkit it\t\tKV-PLAN\t1\t\n")
            st["items"][KW.item_key("qwen_kvsys", "event28w_c", "kv3_st_t3")] = st["items"].pop("q")
            picks, _ = KW.select(rows, c, "qwen_kvsys", st, PLAN | {"kv3_st_t3"})
            self.assertIn("kv3_st_t3", [p["item"] for p in picks])
            # a standing non-geom pilot FAIL keeps it held
            st["items"]["p"]["stage"] = "gen"
            picks, _ = KW.select(rows, c, "qwen_kvsys", st, PLAN | {"kv3_st_t3"})
            self.assertNotIn("kv3_st_t3", [p["item"] for p in picks])


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
                                                                     "tail": "place: exit 137"}))
            ap = FakeAP(d, c)
            st = KW.step(ap)
            (r,) = [x for x in st["items"].values() if x["item"] == "kv3_phy_v1"]
            self.assertEqual(r["attempt"], 2)
            self.assertEqual(r["status"], "RUNNING")
            (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "place",
                                                                     "tail": "place: exit 137"}))
            st = KW.step(FakeAP(d, c))
            (r,) = [x for x in st["items"].values() if x["item"] == "kv3_phy_v1"]
            self.assertEqual((r["status"], r["attempt"]), ("RUNNING", 3))       # AUTOBUILD-PIPE-1: up to 3 attempts
            (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "place",
                                                                     "tail": "place: exit 137"}))
            st = KW.step(FakeAP(d, c))
            (r,) = [x for x in st["items"].values() if x["item"] == "kv3_phy_v1"]
            self.assertEqual((r["status"], r["class"], r["attempt"]), ("FAIL", "INFRA", 3))   # then stops

    def test_infra_attempts_config_two_is_once(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "OWNERS.tsv").write_text(OWN)
            c = json.dumps(dict(cfg(die_max_inflight=1), infra_attempts=2))
            st = KW.step(FakeAP(d, c))
            for _ in range(2):
                (r,) = [x for x in st["items"].values() if x["item"] == "kv3_phy_v1"]
                (Path(r["dir"]) / "result.json").write_text(json.dumps({"verdict": "FAIL", "stage": "place",
                                                                         "tail": "place: exit 137"}))
                st = KW.step(FakeAP(d, c))
            (r,) = [x for x in st["items"].values() if x["item"] == "kv3_phy_v1"]
            self.assertEqual((r["status"], r["class"], r["attempt"]), ("FAIL", "INFRA", 2))

    def test_legacy_fail_infra_record_relaunched_same_event_only(self):
        rec = {"die": "qwen_kvsys", "item": "x", "event": "event28w_c", "attempt": 2, "status": "FAIL", "class": "INFRA"}
        self.assertTrue(KW.infra_relaunch_due(cfg(), rec))
        self.assertFalse(KW.infra_relaunch_due(cfg(), dict(rec, event="old_event")))
        self.assertFalse(KW.infra_relaunch_due(cfg(), dict(rec, attempt=3)))
        self.assertFalse(KW.infra_relaunch_due(cfg(), dict(rec, **{"class": "FLOW"})))
        self.assertTrue(KW.infra_relaunch_due(cfg(), dict(rec, status="RETRY-INFRA", event="old_event")))

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


class Stages(unittest.TestCase):
    def test_stage_rows(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"k1": {"die": "qwen_kvsys", "item": "kv3_hg_v1", "block_sha": "c" * 64, "plan_sha": "d" * 64,
                                   "status": "ENQUEUED", "stage": "geom", "kit": "/k", "updated": 0},
                            "k2": {"die": "qwen_kvsys", "item": "kv3_pc_v1__cl1", "parent_item": "kv3_pc_v1",
                                   "status": "RUNNING", "stage": "place", "updated": 0}}}
            KW.write_stages(st, d)
            rows = [ln.split("\t") for ln in open(os.path.join(d, KW.STAGES_FILE)).read().splitlines()]
            self.assertEqual(tuple(rows[0]), KW.STAGE_COLS)
            r = dict(zip(rows[0], rows[1]))
            self.assertEqual((r["item"], r["stage"], r["block_sha"], r["plan_sha"]), ("kv3_hg_v1", "queue:route", "c" * 12, "d" * 12))
            self.assertEqual(dict(zip(rows[0], rows[2]))["stage"], "place")
            self.assertEqual(r["plan_current"], "")

    def test_plan_current(self):
        import tempfile
        cfg = {"dies": {"s81": {"gen_host": "h", "plan": "/p.json", "event": "e2"}}}
        cur_b, old_b = "a" * 64, "b" * 64
        st = {"plans": {"h:/p.json|e2": {"blocks": {"t1": cur_b, "t2": cur_b}}},
              "items": {KW.item_key("s81", "e2", "t1", cur_b): {"die": "s81", "item": "t1", "event": "e2", "block_sha": cur_b,
                                                                "status": "FAIL", "updated": 0},
                        KW.item_key("s81", "e1", "t2", old_b): {"die": "s81", "item": "t2", "event": "e1", "block_sha": old_b,
                                                                "status": "FAIL", "updated": 0},
                        "x": {"die": "hbm", "item": "h1", "event": "d1", "status": "FAIL", "updated": 0}}}
        with tempfile.TemporaryDirectory() as d:
            KW.write_stages(st, d, cfg)
            rows = [ln.split("\t") for ln in open(os.path.join(d, KW.STAGES_FILE)).read().splitlines()]
            got = {dict(zip(rows[0], r))["item"]: dict(zip(rows[0], r))["plan_current"] for r in rows[1:]}
            self.assertEqual(got, {"t1": "yes", "t2": "no", "h1": ""})


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


class GeometryOutput(unittest.TestCase):
    def test_verdict_precedes_png_and_runner_footer(self):
        for verdict in ("PASS", "FAIL"):
            line = "AP_AUTO_GEOM AUTO-GEOM " + verdict + " tile fill=ok"
            txt = "AP_AUTO_GEOM_GRT rc 0\n" + line + "\nAP_AUTO_GEOM_PNG /k/auto_geom.png\not-run: RAN on localhost (unit oth-x): exit 1\n"
            self.assertEqual(KW.geom_result_line(txt), line)

    def test_explicit_error_and_missing_verdict(self):
        self.assertEqual(KW.geom_result_line("AP_AUTO_GEOM_ERROR missing ODB\nAP_AUTO_GEOM_PNG /p"), "AP_AUTO_GEOM_ERROR missing ODB")
        self.assertEqual(KW.geom_result_line("AP_AUTO_GEOM_PNG /p\nAP_AUTO_GEOM_GRT rc 0"), "")


class StandingGeomExceptions(unittest.TestCase):
    """KIT-TRIAGE-1/G7 11-01: partial_face (+ aspect with outline=ok) standing exceptions on every die, no config"""
    L = "AP_AUTO_GEOM AUTO-GEOM FAIL x KIT-WAVE e 3_place {}"

    def test_partial_face_any_die(self):
        v, f, tag = KW.geom_verdict(self.L.format("outline=ok(10x10) partial_face=FAIL(2) fill=FAIL(.01) empty=FAIL(.9) r2r=ok(3)"))
        self.assertEqual((v, f), ("PASS-COND", ["empty", "fill", "partial_face"]))
        self.assertTrue(tag.startswith("GEOM-EXCEPTION "), tag)
        self.assertIn("partial_face", tag)
        self.assertIn("22:24", tag)
        self.assertIn("fill/empty", tag)

    def test_aspect_only_with_plan_outline(self):
        ok = self.L.format("outline=ok(587.52x2073.6) aspect=FAIL(3.53) fill=FAIL(.01)")
        self.assertEqual(KW.geom_verdict(ok)[:2], ("PASS-COND", ["aspect", "fill"]))
        self.assertIn("03:35", KW.geom_verdict(ok)[2])
        self.assertEqual(KW.geom_verdict(ok.replace("outline=ok(", "outline=FAIL("))[0], "FAIL")
        self.assertEqual(KW.geom_verdict(ok.replace("outline=ok(", "outline=NA("))[0], "FAIL")   # NA never waived
        self.assertEqual(KW.geom_verdict(self.L.format("aspect=FAIL(3.0)"))[0], "FAIL")             # no outline proof
        self.assertEqual(KW.geom_verdict(ok, standing=False)[0], "FAIL")                          # legacy judge

    def test_other_rules_still_gate(self):
        for extra in ("clock_reach=FAIL(370)", "clock_tap_sinks=FAIL(1600)", "r2r=FAIL(500)", "pin_unreg=FAIL(3)",
                      "grt=FAIL(12)", "grt=NA(None)", "col_v=FAIL(1.2)", "pin_reg_max=FAIL(160)"):
            line = self.L.format(f"outline=ok(1x1) partial_face=FAIL(2) aspect=FAIL(3) fill=FAIL(.01) {extra}")
            self.assertEqual(KW.geom_verdict(line)[0], "FAIL", extra)

    def test_fill_only_unchanged(self):
        self.assertEqual(KW.geom_verdict(self.L.format("fill=FAIL(.01) empty=FAIL(.9)")),
                         ("PASS", ["empty", "fill"], "FILL-EXCEPTION"))

    def test_config_waiver_ref_first(self):
        w = {"pin_reg_p90": ("COORD 13:03", 55.0), "partial_face": "COORD 22:24 S81"}
        v, f, tag = KW.geom_verdict(self.L.format("partial_face=FAIL(2) pin_reg_p90=FAIL(50) fill=FAIL(.01)"), w)
        self.assertEqual(v, "PASS-COND")
        self.assertIn("COORD 22:24 S81", tag)
        self.assertIn("<= 55", tag)
        self.assertEqual(KW.geom_verdict(self.L.format("partial_face=FAIL(2) pin_reg_p90=FAIL(60)"), w)[0], "FAIL")


class RejudgeGeom(unittest.TestCase):
    def test_outline_fill_in(self):
        line = "AUTO-GEOM FAIL x 3_place outline=NA(427.68x246.24) fill=FAIL(.01)"
        l2, note = KW.outline_fill_in(line, [427.68, 246.24], "freeze.json")
        self.assertIn("outline=ok(427.68x246.24)", l2)
        self.assertIn("freeze.json", note)
        self.assertEqual(KW.geom_verdict(l2)[0], "PASS")
        l3, _ = KW.outline_fill_in(line, [400.0, 246.24])
        self.assertIn("outline=FAIL(", l3)
        self.assertEqual(KW.outline_fill_in(line, None), (line, ""))
        only = KW.outline_fill_in("AUTO-GEOM FAIL x 3_place outline=NA(1.0x2.0) r2r=ok(3)", [1.0, 2.0])[0]
        self.assertEqual(KW.geom_verdict(only), ("PASS", [], ""))        # the outline was the only failing rule

    def test_prects_whatif(self):
        self.assertIn("clock_reach=info(", KW.prects_clock_info("AUTO-GEOM FAIL x 3_place clock_reach=FAIL(300)"))
        self.assertIn("clock_reach=FAIL(", KW.prects_clock_info("AUTO-GEOM FAIL x 4_cts clock_reach=FAIL(300)"))
        self.assertEqual(KW.geom_verdict(KW.prects_clock_info("AUTO-GEOM FAIL x 3_place clock_reach=FAIL(300)"))[0], "PASS")

    def test_rows(self):
        # hard-gate semantics (die opt geom_advisory false); the advisory default is test_kit_wave_geomadv.py
        cfg = {"dies": {"d": {"gen_host": "h", "plan": "/p.json", "event": "e2", "geom_advisory": False}}}
        st = {"plans": {"h:/p.json|e2": {"blocks": {"a": "a" * 64, "b": "b" * 64, "c": "c" * 64}}}, "items": {}}

        def rec(item, blk, ev="e2", **kw):
            k = KW.item_key("d", ev, item, blk)
            st["items"][k] = dict(die="d", item=item, attempt=1, event=ev, block_sha=blk, status="FAIL", stage="geom",
                                  **{"class": "PLAN"}, evidence=f"h:/ev/{item}", kit=f"h:/kit/{item}", **kw)
            return k
        ka, kb, kc = rec("a", "a" * 64), rec("b", "0" * 64, ev="e1"), rec("c", "c" * 64)
        lines = {ka: "AUTO-GEOM FAIL a 3_place outline=NA(10.0x20.0) partial_face=FAIL(2) fill=FAIL(.01)",
                 kb: "AUTO-GEOM FAIL b 3_place outline=ok(1x1) partial_face=FAIL(2)",
                 kc: "AUTO-GEOM FAIL c 3_place outline=ok(1x1) partial_face=FAIL(2) clock_reach=FAIL(300)"}
        seen = []

        def probe(h, items):
            seen.append(h)
            return {k: {"line": lines[k], "kit_ok": True, "outline": [10.0, 20.0], "outline_src": "freeze.json"}
                    for k, _, _ in items}
        rows = {r["key"]: r for r in KW.rejudge_rows(cfg, st, probe)}
        self.assertEqual(seen, ["h"])
        self.assertEqual((rows[ka]["old"], rows[ka]["new"], rows[ka]["current"]), ("FAIL", "PASS-COND", True))
        self.assertIn("freeze.json", rows[ka]["note"])
        self.assertEqual((rows[kb]["new"], rows[kb]["current"]), ("PASS-COND", False))
        self.assertEqual((rows[kc]["new"], rows[kc]["whatif"]), ("FAIL", "PASS-COND"))   # no stored metrics
        # COORD 11-01 04:4x: stored metrics 3_place + 0 fixed clock cells -> clock_reach INFO is the verdict itself
        probe2 = lambda h, items: {k: {"line": lines[k], "kit_ok": True, "stage": "placed", "clk_fixed": 0}
                                   for k, _, _ in items}
        self.assertEqual({r["key"]: r for r in KW.rejudge_rows(cfg, st, probe2)}[kc]["new"], "PASS-COND")
        probe3 = lambda h, items: {k: {"line": lines[k], "kit_ok": True, "stage": "placed", "clk_fixed": 3}
                                   for k, _, _ in items}
        self.assertEqual({r["key"]: r for r in KW.rejudge_rows(cfg, st, probe3)}[kc]["new"], "FAIL")


class SignedParamClassKW8(unittest.TestCase):
    def test_named_not_unclassified(self):
        raw = ("OT_SIGNED_PARAM_SERIALIZE ERROR: ot_s81sl_xrt1 top/u_x: .OLAT(0) has no verifiable numeric header default\n"
               "ERROR: TCL interpreter returned an error: child process exited abnormally\n")
        cls, why = KW.classify("place", raw)
        self.assertEqual(cls, "PLAN")
        self.assertIn("signed child parameter", why)



class BindAdvisoryKW8(unittest.TestCase):
    def test_bind_out_sources(self):
        self.assertEqual(KW.bind_out_of({"bind_out": "/b"}), "/b")
        self.assertEqual(KW.bind_out_of({"script": "x"}, "export S81_BIND_OUT=/srv/b\n"), "/srv/b")
        self.assertIsNone(KW.bind_out_of({"script": "x"}, "python3 head_wave_kit_rtl.py"))

    def test_lines(self):
        self.assertIsNone(KW.bind_advisory_line("d", "/b", "/s", "COMMIT abc\n"))
        l = KW.bind_advisory_line("d", "/b", "/s", "COMMIT abcdef0123456\nplan/p.json\n")
        self.assertIn("older than src /s for: plan/p.json", l)
        self.assertIn("not compared", KW.bind_advisory_line("d", "/b", "/s", "NOPROV\n"))
        self.assertIn("not in /s", KW.bind_advisory_line("d", "/b", "/s", "NOCOMMIT abc\n"))

if __name__ == "__main__":
    unittest.main()


class KitClassKey(unittest.TestCase):
    """AUTOBUILD-PIPE-4 10-31 (OWNER 12.27a pilot gate): one class per die x kind x structural family"""

    def test_replicas_and_variants_share_a_class(self):
        c = KW.kit_class
        self.assertEqual(c("s81", "ot_s81sl_leaf__t1"), c("s81", "ot_s81sl_leaf__t24__cl2456157b"))
        self.assertEqual(c("s81", "col_h10_r0_p4__t1"), c("s81", "col_h9_r0_p3__t1__cl0cd90c0e"))
        self.assertEqual(c("s81", "slice_station__t7__cl362204c4"), "s81|type|slice_station")
        self.assertEqual(c("hbm", "ot_hbm_idx_tail_native__v9496b22d4b49", "core"),
                         c("hbm", "ot_hbm_idx_tail_native__vf56d1f72f3f3", "core"))
        self.assertEqual(c("hbm", "ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77", "core"),
                         "hbm|core|ot_hbm_su_static_pgslice_lg__lanes")

    def test_different_structures_stay_apart(self):
        c = KW.kit_class
        self.assertNotEqual(c("hbm", "hnx_rp3lp3h_n", "core"), c("hbm", "hnx_rp3lp3h_s", "core"))
        self.assertNotEqual(c("s81", "svc_hi_dsdv_svc_rs__t1"), c("s81", "svc_lo_dsdv_svc_rs__t1"))
        self.assertNotEqual(c("qwen_kvsys", "kv3_io_ft", "type"), c("qwen_kvsys", "kv3_io_ft", "core"))
        self.assertNotEqual(c("s81", "slice_station__t1"), c("s81_head", "slice_station__t1"))


class GenLintClasses(unittest.TestCase):
    """AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 d): kit_gen_lint FAIL lines -> one class per check"""

    def c(self, line):
        return KW.classify("gen_lint", "GEN_LINT FAIL issues 1 pins_vs_plan=PASS\n  - GEN_LINT FAIL " + line + "\n")[0]

    def test_classes(self):
        self.assertEqual(self.c("rtl_check: Warning: Wire t.\\y is used but has no driver."), "RTL")
        self.assertEqual(self.c("macro_tcl: 1 instantiated macro master(s) ['x'] but no staged MACRO_PLACEMENT_TCL"), "PLAN")
        self.assertEqual(self.c("pins_vs_plan: kit pin set canon sha differs"), "PLAN")
        self.assertEqual(self.c("memory_bits: memory a/b 16 x 514 = 8224 bits > SYNTH_MEMORY_MAX_BITS 8192"), "FLOW")
        self.assertEqual(self.c("clock_export_form: forwarded clock output f uses the tie export form"), "FLOW")


class BoundedGeomWaiver(unittest.TestCase):
    """AUTOBUILD-PIPE-4 10-31 (COORD 02:43): t46 pin_reg_p90 waiver holds only while p90 <= 40"""
    D = {"geom_exceptions": [{"rules": ["pin_reg_p90"], "items": ["slice_station__t46"], "ref": "COORD 02:43",
                              "max": {"pin_reg_p90": 40}}]}

    def line(self, p90, mx=120.0):
        ok = "ok" if mx <= 150 else "FAIL"
        return (f"AP_AUTO_GEOM AUTO-GEOM FAIL t46 pin_reg_p90=FAIL({p90}) pin_reg_max={ok}({mx}) "
                f"fill=FAIL(0.01) r2r=ok(300)")

    def test_bound(self):
        w = KW.geom_waivers(self.D, "slice_station__t46")
        self.assertEqual(w, {"pin_reg_p90": ("COORD 02:43", 40.0)})
        v, _, tag = KW.geom_verdict(self.line(38.2), w)
        self.assertEqual(v, "PASS-COND")
        self.assertIn("<= 40", tag)
        self.assertEqual(KW.geom_verdict(self.line(41.0), w)[0], "FAIL")
        self.assertEqual(KW.geom_verdict(self.line(38.2, 160.0), w)[0], "FAIL")   # max still gates

    def test_unbounded_waiver_unchanged(self):
        w = KW.geom_waivers({"geom_exceptions": [{"rules": ["partial_face"], "ref": "R"}]}, "x")
        self.assertEqual(w, {"partial_face": "R"})
        line = "AP_AUTO_GEOM AUTO-GEOM FAIL x partial_face=FAIL(3) fill=FAIL(0.01)"
        self.assertEqual(KW.geom_verdict(line, w)[:2], ("PASS-COND", ["fill", "partial_face"]))


class PreRouteHoldReason(unittest.TestCase):
    # KIT-TRIAGE-1/G5 11-01: a post-CTS stop has no sign-off record; the reason carries the gate line, never 'TT None'
    def test_no_none_wns_without_signoff(self):
        j = {"status": "DONE-STRUCTURAL", "kind": "post-cts-hold",
             "reasons": "FAIL_POSTCTS FAIL_POSTCTS FF structural hold gate: OT_HOLD_GATE FAIL FF wns_ps -900.00 endpoints 10"}
        stage, st, cls, why = KW.queue_class(j)
        self.assertEqual((stage, st, cls), ("route", "FAIL", "TIMING"))
        self.assertNotIn("None", why)
        self.assertIn("wns_ps -900.00", why)

    def test_signoff_wns_still_shown(self):
        j = {"status": "DONE-STRUCTURAL", "kind": "routed-not-signed", "reasons": "hold_ff",
             "signoff": {"fails": ["hold_ff"], "tt_wns": 3.0, "ff_wns": -4.5}}
        self.assertIn("TT 3.0 FF -4.5 ps", KW.queue_class(j)[3])


class LateEcoClass(unittest.TestCase):
    # KW-ECO-1: a route/sign-off FAIL that went through the late-stage ECO loop names it in the class table
    def test_exhausted_named(self):
        j = {"status": "DONE-NEAR-MISS", "kind": "routed", "reasons": "hold_ff: FAIL",
             "signoff": {"fails": ["hold_ff"], "tt_wns": 3.0, "ff_wns": -4.5},
             "chain": {"eco": {"verdict": "EXHAUSTED", "summary": "late-ECO exhausted (2 it, 900 s): FF -6->-4.5"}}}
        stage, st, cls, why = KW.queue_class(j)
        self.assertEqual((st, cls), ("FAIL", "TIMING"))
        self.assertIn("late-ECO exhausted (2 it", why)

    def test_no_eco_unchanged(self):
        j = {"status": "DONE-NEAR-MISS", "kind": "routed", "reasons": "hold_ff", "signoff": {"fails": ["hold_ff"]}}
        self.assertNotIn("late-ECO", KW.queue_class(j)[3])


class AdoptedPlanAllowlist(unittest.TestCase):
    def test_missing_owned_type_only_when_explicit_and_in_plan(self):
        c = cfg(only_items=["kv3_new", "kv3_missing"], plan_items_from_allowlist=True, pilot_first=False)
        picks, _ = KW.select([], c, "qwen_kvsys", {"items": {}}, {"kv3_new": "a"})
        self.assertEqual([r["item"] for r in picks], ["kv3_new"])
        c["dies"]["qwen_kvsys"]["plan_items_from_allowlist"] = False
        self.assertEqual(KW.select([], c, "qwen_kvsys", {"items": {}}, {"kv3_new": "a"})[0], [])

    def test_plan_core_items_only_named_and_in_plan(self):
        c = cfg(kinds=["core"], only_items=["k_core", "k_type"], plan_core_items=["k_core", "k_gone"], pilot_first=False)
        picks, _ = KW.select([], c, "qwen_kvsys", {"items": {}}, {"k_core": "a", "k_type": "b"})
        self.assertEqual([(r["item"], r["kind"]) for r in picks], [("k_core", "core")])
        c["dies"]["qwen_kvsys"]["plan_core_items"] = []
        self.assertEqual(KW.select([], c, "qwen_kvsys", {"items": {}}, {"k_core": "a"})[0], [])

    def test_allowlist_retains_existing_live_claim(self):
        c = cfg(only_items=["kv3_io_cor_v1"], plan_items_from_allowlist=True)
        picks, skip = KW.select(KW.parse_owners(OWN), c, "qwen_kvsys", {"items": {}}, PLAN)
        self.assertEqual(picks, [])
        self.assertIn("kv3_io_cor_v1", skip["live job (another lane)"])


class ExplicitClassHolds(unittest.TestCase):
    def test_hold_one_measured_class_without_catching_neighbor_family(self):
        c = cfg(hold_items={"kv3_hg_v*": "559k cells; EX cut pending"})
        rows = [dict(KW.parse_owners(OWN)[0], item=n) for n in ("kv3_hg_v1", "kv3_hgi_v1")]
        picks, skip = KW.select(rows, c, "qwen_kvsys", {"items": {}}, {"kv3_hg_v1", "kv3_hgi_v1"})
        self.assertEqual([r["item"] for r in picks], ["kv3_hgi_v1"])
        self.assertEqual(skip["die-owned hold: 559k cells; EX cut pending"], ["kv3_hg_v1"])
