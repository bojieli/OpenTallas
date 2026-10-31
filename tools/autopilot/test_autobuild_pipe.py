#!/usr/bin/env python3
"""AUTOBUILD-PIPE-1 (OWNER 12.23): kit-wave FLOW/INFRA fail classes fixed in the tool, and the wave followed past
AUTO-GEOM through the autopilot queue (route -> sign-off -> archive/provenance -> count) with TIMING/ROUTING classes.
Log snippets are the real 10-30 S81 wave evidence (hub kit_wave/<item>/a<n>/*.log)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

PAD = "\n".join(f"    {i} padding traceback frame / ot-run admission chatter" for i in range(200))
NOLIB = ("ot-heavy: admitted on key-cardinal as oth-ubuntu-199367 after 1 s\nTraceback (most recent call last):\n"
         "  File \"gen.py\", line 295, in <module>\n"
         "ValueError: type ot_s81sl_leaf__t24__cl81374cd8: macros have LEF but no timing liberty: u_lf.u_ve.u_m "
         "(ot_s81sl_ve_m), " + ", ".join(f"u_lf.u_x{i} (ot_s81sl_x{i})" for i in range(120)) +
         "\not-run: RAN on intel1 (unit oth-ubuntu-199367-1793424657): exit 1\n")


def classify_log(stage, txt):
    """what collect() does with run_item's fail(): errors extracted from the whole log + the 3000-char tail"""
    return KW.classify(stage, KW.error_lines(txt) + "\n" + txt[-3000:])


class Classes(unittest.TestCase):
    def test_long_gen_log_missing_lib_is_plan_dep_not_unclassified(self):
        self.assertGreater(len(NOLIB.split("ValueError")[1]), 3000)       # the old tail never saw the exception
        self.assertEqual(KW.classify("gen", NOLIB[-3000:])[1][:12], "unclassified")
        cls, why = classify_log("gen", NOLIB)
        self.assertEqual(cls, "PLAN")
        self.assertIn("WAIT-DEP", why)

    def test_serdes_phy_view_is_plan(self):
        for t in ("ValueError: PG domain phy_lk_WN2 (serdes__t2): powered content ['u_phy'] has no macro view (lef/lib) in this kit",
                  "KeyError: 'u_phy'",
                  "ValueError: type serdes__t12: PG domain phy_lk_WS3 holds no macro (a PHY domain powers its PHY macro)"):
            self.assertEqual(classify_log("gen", "Traceback (most recent call last):\n" + t)[0], "PLAN", t)

    def test_kit_rtl_plan_contracts_are_plan(self):
        spare = ("Traceback (most recent call last):\n  File \"<stdin>\", line 12, in <module>\nAssertionError: "
                 "S81_KIT_RTL: constant spare outputs require a plan fix (or a COORD-declared exception)\n"
                 "ot-run: RAN on intel1 (unit x): exit 1")
        sid = ("S81_KIT_RTL: ot_s81sl_leaf__t40__cl86ea32b3: S_u_lf4_u_vq_sid used outside a child parameter port: "
               "parameter [3:0] S_u_lf4_u_vq_sid = 4'b1001\not-run: RAN on intel1 (unit y): exit 1")
        self.assertEqual(classify_log("kit_rtl", spare)[0], "PLAN")
        self.assertEqual(classify_log("kit_rtl", sid)[0], "PLAN")

    def test_preflight_face_guard_is_plan(self):
        self.assertEqual(classify_log("place", "FACE_GUARD FAIL top s81p_slice_station__t47 bits 3869\n" + PAD +
                                      "\nFAIL_PREFLOOR face_guard\not-run: RAN on epyc2 (unit z): exit 1")[0], "PLAN")
        self.assertEqual(KW.classify("place", "FAIL_PREFLOOR face_guard")[0], "PLAN")

    def test_cland_band_is_named_flow(self):
        cls, why = classify_log("place", "Error: global_place.tcl, 5 OT_CLAND no legal nonoverlapping row/site in "
                                         "reserved band for u_bound.u_cland_ft0_i/u_ring.tc\\[1\\]")
        self.assertEqual(cls, "FLOW")
        self.assertIn("pinslot", why)

    def test_ssh_drop_is_infra_only_before_the_command_ran(self):
        drop = ("ot-run: -> intel1\nConnection closed by 185.8.107.41 port 22\nkex_exchange_identification: read: "
                "Connection reset by peer\n")
        self.assertEqual(classify_log("kit_rtl", drop)[0], "INFRA")
        ran = ("ot-run: intel1 SSH probe exit 255: Connection reset by peer\not-run: -> intel2\n"
               "ValueError: type t: macros have LEF but no timing liberty: u (m)\not-run: RAN on intel2 (unit u): exit 1")
        self.assertEqual(classify_log("gen", ran)[0], "PLAN")


class Waivers(unittest.TestCase):
    L = "AP_AUTO_GEOM AUTO-GEOM FAIL {}"

    def test_granted_exception_is_pass_cond_with_ref(self):
        d = {"geom_exceptions": [{"rules": ["partial_face"], "items": ["slice_station__*"], "ref": "COORD 22:2x"},
                                 {"rules": ["clock_reach"], "ref": ""}]}             # no ruling ref: ignored
        w = KW.geom_waivers(d, "slice_station__t24__cl64811a5d", "slice_station__t24")
        self.assertEqual(w, {"partial_face": "COORD 22:2x"})
        self.assertEqual(KW.geom_waivers(d, "col_h9_r0_p1__t1"), {})
        v, f, tag = KW.geom_verdict(self.L.format("partial_face=FAIL(2) fill=FAIL(.01) r2r=ok(3)"), w)
        self.assertEqual((v, f), ("PASS-COND", ["fill", "partial_face"]))
        self.assertIn("COORD 22:2x", tag)
        self.assertEqual(KW.geom_verdict(self.L.format("partial_face=FAIL(2) clock_reach=FAIL(400)"), w)[0], "FAIL")
        self.assertEqual(KW.geom_verdict(self.L.format("partial_face=FAIL(2) tap_sinks=NA(None)"), w)[0], "FAIL")
        self.assertEqual(KW.geom_verdict(self.L.format("fill=FAIL(.01)"), w), ("PASS", ["fill"], "FILL-EXCEPTION"))


def job(status, **kw):
    return dict(dict(id="j1", kit="intel1:/k/t", status=status, updated=1.0), **kw)


class PastGeom(unittest.TestCase):
    def test_queue_classes(self):
        Q = KW.queue_class
        self.assertEqual(Q(job("ARCHIVED", archive="intel2:/a", flow_tag="flow-20261030-a-s81"))[:3], ("count", "SIGNED", ""))
        self.assertEqual(Q(job("RUNNING"))[:3], ("route", "RUNNING", ""))
        self.assertEqual(Q(job("WAIT-PATH-GATE"))[:3], ("queue", "WAIT-PATH-GATE", ""))
        self.assertEqual(Q(job("SIGNED-UNVERSIONED", prov_error="no flow tag"))[2], "FLOW")
        self.assertEqual(Q(job("DONE-CRASH", kind="infra-oom"))[2], "INFRA")
        self.assertEqual(Q(job("DONE-CRASH", kind="tool-segfault"))[2], "FLOW")
        so = {"fails": ["setup_tt"], "tt_wns": -42.0, "ff_wns": 3.0, "drc": 0}
        self.assertEqual(Q(job("DONE-NEAR-MISS", kind="routed", signoff=so))[:3], ("signoff", "FAIL", "TIMING"))
        self.assertEqual(Q(job("REVIEW-STRUCTURAL", kind="routed-not-signed",
                               signoff={"fails": ["drc"], "drc": 300}))[2], "ROUTING")
        self.assertEqual(Q(job("DONE-STRUCTURAL", kind="grt-overflow"))[2], "ROUTING")
        self.assertEqual(Q(job("DONE-STRUCTURAL", kind="post-cts-hold"))[2], "TIMING")
        self.assertEqual(Q(job("DONE-STRUCTURAL", kind="pg-unbound", signoff={"fails": []}))[2], "FLOW")
        self.assertEqual(Q(job("DONE-STRUCTURAL", kind="preflight"))[2], "PLAN")
        self.assertEqual(Q(job("DONE-STRUCTURAL", kind="gate", reasons="RP1_GATE FF hold -12 ps"))[2], "TIMING")
        self.assertEqual(Q(job("REJECTED", error="bad row"))[2], "FLOW")

    def test_follow_queue_rows_and_one_notice(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"k": {"die": "s81", "item": "t", "status": "ENQUEUED", "kit": "intel1:/k/t", "updated": 1,
                                  "evidence": "intel1:/g/auto_geom.json"},
                            "k2": {"die": "s81", "item": "u", "status": "ENQUEUED", "kit": "intel1:/k/u", "updated": 1}}}
            jobs = {"old": job("WITHDRAWN", id="old", updated=0.5),
                    "j1": job("DONE-NEAR-MISS", kind="routed", signoff={"fails": ["hold_ff"], "tt_wns": 5, "ff_wns": -8})}
            (Path(d) / "state.json").write_text(json.dumps({"jobs": jobs}))
            notes = {}
            self.assertEqual(KW.follow_queue(st, d, notes), 1)
            r = st["items"]["k"]
            self.assertEqual((r["q_stage"], r["q_status"], r["q_class"], r["q_id"]), ("signoff", "FAIL", "TIMING", "j1"))
            self.assertEqual(st["items"]["k2"]["q_status"], "QUEUED")
            self.assertEqual(len(notes["s81"]), 1)
            KW.follow_queue(st, d, notes)                                    # unchanged state: no second notice
            self.assertEqual(len(notes["s81"]), 1)
            KW.write_stages(st, d)
            rows = (Path(d) / KW.STAGES_FILE).read_text().splitlines()
            head = rows[0].split("\t")
            row = dict(zip(head, rows[1].split("\t")))
            self.assertEqual((row["stage"], row["status"], row["class"]), ("signoff", "FAIL", "TIMING"))
            self.assertIn("autopilot job j1", row["evidence"])
            self.assertEqual(head[-1], "reason")


class SshRetry(unittest.TestCase):
    def test_transport_drop_retried_design_error_not(self):
        import subprocess
        calls = []

        class P:
            def __init__(self, rc, out):
                self.returncode, self.stdout, self.stderr = rc, out, ""

        def fake_run(argv, **kw):
            calls.append(argv)
            n = len(calls)
            if n == 1:                                                     # mkdir: sshd drops the connection
                return P(255, "kex_exchange_identification: read: Connection reset by peer")
            if n == 2:
                return P(0, "")
            if n == 3:                                                     # gen: ot-run never admitted on intel1
                return P(1, "ot-run: NOT RUN: no host qualifies (intel1: SSH probe exit 255: Connection reset)")
            return P(1, "ValueError: type t: macros have LEF but no timing liberty: u (m)\not-run: RAN on intel1 (unit u): exit 1")
        with tempfile.TemporaryDirectory() as d:
            spec = {"die": "s81", "item": "t", "event": "e", "plan": "/p/plan.json", "gen_host": "intel2", "hub": "intel2",
                    "src": "/src", "root": "/w", "work": "/w/items/t", "kit_rtl": {}, "gen_args": [], "preflight_args": [],
                    "hosts": ["intel2"], "place_prefer": [], "place_mem_gb": 48, "place_threads": 8, "geom_mem_gb": 24,
                    "gen_mem_gb": 16, "bind_mem_gb": 24, "ot_run": "/bin/ot-run", "start_delay_s": 0}
            (Path(d) / "spec.json").write_text(json.dumps(spec))
            old_run, old_sleep = KW.subprocess.run, KW.time.sleep
            KW.subprocess.run, KW.time.sleep = fake_run, lambda s: None
            try:
                self.assertEqual(KW.run_item(str(Path(d) / "spec.json")), 1)
            finally:
                KW.subprocess.run, KW.time.sleep = old_run, old_sleep
            res = json.loads((Path(d) / "result.json").read_text())
            self.assertEqual(len(calls), 4)                                  # mkdir x2, gen x2, no third gen try
            self.assertEqual(res["stage"], "gen")
            self.assertIn("KW_SSH_RETRY", (Path(d) / "mkdir.log").read_text())
            self.assertEqual(KW.classify(res["stage"], res["errors"] + "\n" + res["tail"])[0], "PLAN")


class Probe(unittest.TestCase):
    def test_probe_flags_noview_types(self):
        plan = {"partition_types": {
            "a": {"hard_cores": [{"inst": "u_e0", "module": "rom_e", "lef": "x.lef"}]},
            "b": {"hard_cores": [{"inst": "u_e0", "module": "rom_e", "lef": "x.lef", "lib": "x_tt.lib"}],
                  "contents": [{"inst": "u_phy", "module": "phy"}]},
            "h": {"hard": True, "hard_cores": [{"inst": "u", "lef": "y.lef"}]}}}
        with tempfile.TemporaryDirectory() as d:
            pp = Path(d) / "plan.json"
            pp.write_text(json.dumps(plan))
            import subprocess
            out = subprocess.run([sys.executable, "-c", KW.PROBE_PLAN, json.dumps({"plan": str(pp)})],
                                 capture_output=True, text=True, cwd=d)
            res = json.loads(out.stdout.split("AP_JSON ", 1)[1])
        self.assertEqual(res["flags"], {"a": "noview", "h": "hard"})
        self.assertEqual(res["deps"], {"a": ["rom_e"]})
        d = {"_plan_flags": res["flags"]}
        self.assertIn("WAIT-DEP", KW.plan_entry_block(d, "a"))
        self.assertIsNone(KW.plan_entry_block(d, "b"))


if __name__ == "__main__":
    unittest.main()


class Pinslot(unittest.TestCase):
    def test_pinslot_default_all_and_opt_out(self):
        self.assertEqual(KW.cland_pinslot_arg({}), "all")
        self.assertEqual(KW.cland_pinslot_arg({"cland_pinslot": False}), "")
        self.assertEqual(KW.cland_pinslot_arg({"cland_pinslot": ["slice_station", "hd_turn_b"]}), "slice_station,hd_turn_b")
        c = {"enabled": True, "dies": {"s81": {"event": "e", "plan": "/p", "gen_host": "intel1", "src": "/s"}}}
        self.assertEqual(KW.spec_for(c, "s81", "slice_station__t23", "intel2", "slice_station__t23")["cland_pinslot"], "all")
