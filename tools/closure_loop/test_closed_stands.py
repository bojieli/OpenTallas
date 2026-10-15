"""CLOSED STANDS submit gate (owner 2026-10-12 19:00 "M5 cap narrowed"; gate 2026-10-13): a block with a CLOSED,
published job takes a new route only with a verified "reroute_reason" (die_window, slot_change, param_change,
rtl_change, evidence_gap); loop successors of a job that is not CLOSED are exempt."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="closedstands_"))
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "ref_tile")]
import closed_stands as CS  # noqa: E402
import closure_loop as cl  # noqa: E402
import textbook_lint as TL  # noqa: E402

KIT = ("TOP=ot_t\nSRCS='rtl/t/ot_t.sv rtl/t/ot_t_leaf.sv'\nPARAMS=(--param W={w} --param D=4)\nFW={fw}\nFH=64.8\n"
       "PINS=(--pin-region '^(d)(\\[|$)=left')\nPIN_H='M4'\nPIN_V='{pv}'\nRLAYERS='{rl}'\n")


class Repo:
    """a fake object store: {commit: {path: text}}"""
    def __init__(self):
        self.c = {}

    def put(self, commit, kit="physical/ref_tile/t", w=512, fw=17.28, pv="M5", rl="M2 M5", rtl="module ot_t; endmodule",
            leaf="module ot_t_leaf; endmodule"):
        self.c[commit] = {f"{kit}/kit.env": KIT.format(w=w, fw=fw, pv=pv, rl=rl), "rtl/t/ot_t.sv": rtl,
                          "rtl/t/ot_t_leaf.sv": leaf, "results/arch/cuts.json": "{}"}
        return self

    def show(self, commit, path):
        return self.c.get(commit, {}).get(path)

    def blob(self, commit, path):
        if commit not in self.c:
            return None
        if path == "":
            return "tree-" + commit
        t = self.c[commit].get(path)
        return None if t is None else hashlib.sha1(t.encode()).hexdigest()


def spec(name="t-v2-bbbbbbbbb", commit="bbbbbbbbb", kit="physical/ref_tile/t", block="ot_t", **kw):
    s = {"name": name, "block": block, "ref_tile": True, "source": {"branch": "claude/x", "commit": commit},
         "stages": {"route": {"cmd": f"bash tools/ref_tile/ref_route.sh {kit}/kit.env L R"}}}
    s.update(kw)
    return s


GOOD_BENCH = {"bench_gold": {"expect": "pass", "ok": True}, "bench_mut": {"expect": "fail", "ok": True}}
GOOD_METRICS = {"ss_ps": 12.0, "ff_ps": 3.0, "drc": 0}


def hist(name="t-v1-aaaaaaaaa", status="CLOSED", commit="aaaaaaaaa", publish=True, benches=GOOD_BENCH,
         metrics=GOOD_METRICS, t="01:00", **kw):
    j = dict(name=name, status=status, spec=spec(name, commit), finished_at=f"2026-10-12T{t}:00-07:00", events=[],
             benches=dict(benches), metrics=dict(metrics), commit_full=commit * 4)
    if publish:
        j["publish"] = {"branch_commit": "f" * 40, "files": 9, "merge": "AUTO-MERGED into main 123456789"}
    j.update(kw)
    return j


class Gate(unittest.TestCase):
    def setUp(self):
        # aaaaaaaaa: the closed commit; bbbbbbbbb: same RTL, kit re-capped; ccccccccc: RTL changed; ddddddddd: W changed
        self.r = Repo().put("aaaaaaaaa", pv="M7", rl="M2 M7").put("bbbbbbbbb").put("ccccccccc", rtl="module ot_t; wire x; endmodule")
        self.r.put("ddddddddd", w=1024).put("eeeeeeeee", fw=34.56)
        self.r.c["a" * 36] = self.r.c["aaaaaaaaa"]

    def run_(self, sp, jobs=None, exists=lambda p: p == "results/arch/cuts.json", counts=None):
        return CS.check(sp, sp["name"], jobs if jobs is not None else [hist()], self.r.show, self.r.blob,
                        closure_counts=counts, bench_gap=cl.bench_evidence_gap, exists=exists)

    # ---------------------------------------------------------------- when the gate does not apply
    def test_constants(self):
        self.assertEqual(TL.CLOSED_STANDS_KINDS, ("die_window", "slot_change", "param_change", "rtl_change", "evidence_gap",
                                                  "pin_register", "native_launch"))
        self.assertEqual(TL.DIE_WINDOW_CUT_MIN, 0.6)

    def test_new_block_and_unclosed_history_pass(self):
        self.assertEqual(self.run_(spec(), [])["verdict"], "NA")
        self.assertEqual(self.run_(spec(), [hist(status="NEEDS_RTL"), hist("u", status="RUNNING")])["verdict"], "NA")
        other = hist("o-v1-aaaaaaaaa")
        other["spec"]["block"] = "ot_other"
        self.assertEqual(self.run_(spec(), [other])["verdict"], "NA")

    def test_unpublished_or_revoked_closure_does_not_stand(self):
        self.assertEqual(self.run_(spec(), [hist(publish=False)])["verdict"], "NA")
        self.assertEqual(self.run_(spec(), counts=lambda j: False)["verdict"], "NA")

    def test_no_route_stage_is_not_a_route(self):
        s = spec()
        s["stages"] = {"bench": [{"name": "gold", "cmd": "x", "expect": "pass"}]}
        self.assertEqual(self.run_(s)["verdict"], "NA")

    def test_other_parameter_set_is_another_block(self):
        r = self.run_(spec(commit="ddddddddd"))
        self.assertEqual(r["verdict"], "NA")
        self.assertIn("parameter set", r["message"])

    def test_unreadable_parameters_count_as_the_same_block(self):
        s = spec(commit="bbbbbbbbb", kit="physical/ref_tile/missing")
        self.assertEqual(self.run_(s)["verdict"], "REFUSE")

    # ---------------------------------------------------------------- refusal without a reason
    def test_m5_reroute_of_a_closed_tile_is_refused(self):
        r = self.run_(spec())
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertEqual(r["closed"], ["t-v1-aaaaaaaaa"])
        self.assertEqual(r["facts"]["rtl"], "same")
        for needle in ("t-v1-aaaaaaaaa", "reroute_reason", "bind the missing bench", "re-export its view",
                       "wrap the closed view under the contract slot name", "RTL vs the closed commit same"):
            self.assertIn(needle, r["message"])

    def test_malformed_reason_is_refused(self):
        for bad in ("die_window", {"kind": "because"}, {}, [], True):
            self.assertEqual(self.run_(spec(reroute_reason=bad))["verdict"], "REFUSE", bad)

    # ---------------------------------------------------------------- die_window
    def test_die_window(self):
        ok = {"kind": "die_window", "slot": "qfd_sp:ot_t", "cut": 0.71, "source": "results/arch/cuts.json"}
        r = self.run_(spec(reroute_reason=ok))
        self.assertEqual((r["verdict"], r["kind"]), ("PASS", "die_window"))
        self.assertIn("0.71", r["message"])
        grt = dict(ok, grt_overflow=312)
        del grt["cut"]
        self.assertEqual(self.run_(spec(reroute_reason=grt))["verdict"], "PASS")
        self.assertEqual(self.run_(spec(reroute_reason=dict(grt, grt_overflow=[0, 0, 10, 10])))["verdict"], "PASS")
        for bad, why in ((dict(ok, cut=0.6), "not above 0.6"), (dict(ok, cut=0.41), "not above 0.6"),
                         (dict(ok, cut="high"), "measured figure"), (dict(ok, cut=True), "measured figure"),
                         (dict(grt, grt_overflow=0), "measured figure"), (dict(ok, slot=""), "\"slot\""),
                         ({k: v for k, v in ok.items() if k != "source"}, "\"source\""),
                         (dict(ok, source="results/arch/nope.json"), "does not exist")):
            r = self.run_(spec(reroute_reason=bad))
            self.assertEqual(r["verdict"], "REFUSE", bad)
            self.assertIn(why, r["message"])

    # ---------------------------------------------------------------- slot_change
    def test_slot_change(self):
        rr = {"kind": "slot_change", "contract": "results/arch/hier_contract_1012/qwen_rom_tp8.json v5"}
        r = self.run_(spec(commit="eeeeeeeee", reroute_reason=rr))                  # outline 34.56 != 17.28
        self.assertEqual((r["verdict"], r["kind"]), ("PASS", "slot_change"))
        r = self.run_(spec(commit="eeeeeeeee", reroute_reason={"kind": "slot_change"},
                           slot_change_request="el1011-qwen-tp8.log VM SLOT CHANGE REQUEST"))
        self.assertEqual(r["verdict"], "PASS")                                      # the spec's own request line
        r = self.run_(spec(commit="eeeeeeeee", reroute_reason={"kind": "slot_change"}))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("SLOT CHANGE REQUEST", r["message"])

    def test_slot_change_with_the_closed_outline_and_pin_faces_is_refused(self):
        self.r.put("bbbbbbbbb", pv="M7", rl="M2 M5")       # only the route layer cap moved: not a slot change
        r = self.run_(spec(reroute_reason={"kind": "slot_change", "contract": "qwen_rom_tp8.json v5"}))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("die_window, not slot_change", r["message"])

    # ---------------------------------------------------------------- pin_register
    def test_pin_register(self):
        ok = {"kind": "pin_register", "source": "results/arch/cuts.json", "cell": "dsfd_su_t_ctl", "pair_cost_ps": 766.1,
              "fix": "kit recipe 2: pin flops and hold stages FIRM at the pins"}
        r = self.run_(spec(reroute_reason=ok))
        self.assertEqual((r["verdict"], r["kind"]), ("PASS", "pin_register"))
        for k in ("source", "cell", "fix", "pair_cost_ps"):
            self.assertEqual(self.run_(spec(reroute_reason={a: b for a, b in ok.items() if a != k}))["verdict"], "REFUSE", k)
        r = self.run_(spec(reroute_reason=dict(ok, pair_cost_ps=640.0)))            # closes a hop within its reach
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("closed view stands", r["message"])
        tile = {a: b for a, b in ok.items() if a != "pair_cost_ps"}
        r = self.run_(spec(reroute_reason=dict(tile, launch_ps=331.4)))              # view launch > 220: tile defect
        self.assertEqual(r["verdict"], "PASS")
        self.assertIn("tile defect", r["message"])
        self.assertEqual(self.run_(spec(reroute_reason=dict(tile, capture_ps=197.9)))["verdict"], "PASS")
        self.assertEqual(self.run_(spec(reroute_reason=dict(tile, launch_ps=210.0, capture_ps=150.0)))["verdict"], "REFUSE")
        self.assertEqual(self.run_(spec(reroute_reason=dict(tile, launch_ps=331.4, fix="x")))["verdict"], "REFUSE")
        r = self.run_(spec(reroute_reason=dict(ok, source="results/arch/missing.json")))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("does not exist", r["message"])

    # ---------------------------------------------------------------- native_launch
    def test_native_launch(self):
        kd = "physical/ref_tile/t"
        stage = "source /src/physical/common_flow/pin_reg_split.tcl\n"
        for c in ("bbbbbbbbb", "ccccccccc", "eeeeeeeee"):                          # the re-kit: recipe-2 output stage
            self.r.c[c][f"{kd}/kit.env"] += "EXTRA=(--orfs-var OT_KEEP_PIN_REGS=1)\nRECIPE=2\n"
            self.r.c[c][f"{kd}/pre_gpl.tcl"] = stage
        ok = {"kind": "native_launch", "source": "results/arch/cuts.json", "cell": "ot_t", "launch_ps": 331.4}
        r = self.run_(spec(reroute_reason=ok))
        self.assertEqual((r["verdict"], r["kind"]), ("PASS", "native_launch"), r["message"])
        for k in ("source", "cell", "launch_ps"):
            self.assertEqual(self.run_(spec(reroute_reason={a: b for a, b in ok.items() if a != k}))["verdict"], "REFUSE", k)
        r = self.run_(spec(reroute_reason=dict(ok, launch_ps=210.0)))               # within the budget: the view stands
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("capture-only", r["message"])
        r = self.run_(spec(commit="ccccccccc", reroute_reason=ok))                  # RTL changed: not a re-kit
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("rtl_change", r["message"])
        r = self.run_(spec(commit="eeeeeeeee", reroute_reason=ok))                  # outline moved: slot_change
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("FW", r["message"])
        self.r.c["bbbbbbbbb"][f"{kd}/pre_gpl.tcl"] = "source /src/x/io_flop_at_pins.tcl\n"
        r = self.run_(spec(reroute_reason=ok))                                      # same output stage as before
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("repeats the launch miss", r["message"])
        self.r.c["bbbbbbbbb"][f"{kd}/pre_gpl.tcl"] = stage
        self.r.c["aaaaaaaaa"][f"{kd}/pre_gpl.tcl"] = stage                          # the closed kit already had it
        r = self.run_(spec(reroute_reason=ok))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("another cause", r["message"])
        pad = stage + "source /src/physical/dsrom_window_source/leaf_iohold.tcl\n"
        self.r.c["bbbbbbbbb"][f"{kd}/pre_gpl.tcl"] = pad                            # re-kit adds the output hold pad
        r = self.run_(spec(reroute_reason=ok))
        self.assertEqual((r["verdict"], r["kind"]), ("PASS", "native_launch"), r["message"])
        self.r.c["aaaaaaaaa"][f"{kd}/pre_gpl.tcl"] = pad                            # closed kit already had the pad too
        r = self.run_(spec(reroute_reason=ok))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("another cause", r["message"])

    # ---------------------------------------------------------------- param_change
    def test_param_change(self):
        rr = {"kind": "param_change", "params": {"W": "512 -> 1024"}}
        r = self.run_(spec(reroute_reason=rr))                                      # same PARAMS in both kits
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("equals that of closed", r["message"])
        unreadable = spec(kit="physical/ref_tile/missing", reroute_reason=rr)       # cannot be read: the list stands
        self.assertEqual(self.run_(unreadable)["verdict"], "PASS")
        self.assertEqual(self.run_(spec(kit="physical/ref_tile/missing", reroute_reason={"kind": "param_change"}))["verdict"],
                         "REFUSE")

    # ---------------------------------------------------------------- rtl_change
    def test_rtl_change_is_verified(self):
        rr = {"kind": "rtl_change"}
        r = self.run_(spec(commit="ccccccccc", reroute_reason=rr))
        self.assertEqual((r["verdict"], r["kind"]), ("PASS", "rtl_change"))
        self.assertIn("1 of 2 RTL source file(s) differ", r["message"])
        self.assertIn("(verified)", r["message"])
        r = self.run_(spec(reroute_reason=rr))                                      # bbbbbbbbb: RTL byte-identical
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("rtl_change claimed, but the RTL is the same", r["message"])
        r = self.run_(spec(commit="aaaaaaaaa", reroute_reason=rr))                  # the closed commit itself
        self.assertEqual(r["verdict"], "REFUSE")

    def test_rtl_change_against_every_closed_job(self):
        jobs = [hist(), hist("t-v3-ccccccccc", commit="ccccccccc", t="03:00")]
        r = self.run_(spec(name="t-v4-ccccccccc", commit="ccccccccc", reroute_reason={"kind": "rtl_change"}), jobs)
        self.assertEqual(r["verdict"], "REFUSE")                                    # equals the second closure
        self.assertEqual(r["facts"]["closed_job"], "t-v3-ccccccccc")

    def test_rtl_same_content_under_a_snapshot_path(self):
        c = dict(self.r.c["bbbbbbbbb"])
        c["physical/ref_tile/t/kit.env"] = c["physical/ref_tile/t/kit.env"].replace(
            "rtl/t/ot_t.sv rtl/t/ot_t_leaf.sv", "snap/ot_t.sv snap/ot_t_leaf.sv")
        c["snap/ot_t.sv"], c["snap/ot_t_leaf.sv"] = c["rtl/t/ot_t.sv"], c["rtl/t/ot_t_leaf.sv"]
        self.r.c["bbbbbbbbb"] = c
        self.assertEqual(self.run_(spec(reroute_reason={"kind": "rtl_change"}))["verdict"], "REFUSE")

    def test_rtl_change_unverifiable(self):
        r = self.run_(spec(kit="physical/ref_tile/missing", reroute_reason={"kind": "rtl_change"}))
        self.assertEqual(r["verdict"], "REFUSE")                                    # the new job's RTL is unknown
        self.assertIn("rtl_boundary", r["message"])
        gone = hist(commit="999999999")                                             # closed commit not in the store
        r = self.run_(spec(commit="ccccccccc", reroute_reason={"kind": "rtl_change"}), [gone])
        self.assertEqual(r["verdict"], "PASS")
        self.assertIn("not verifiable", r["message"])

    # ---------------------------------------------------------------- evidence_gap
    def test_evidence_gap(self):
        rr = {"kind": "evidence_gap", "why_route": "the closed run directory was deleted: no ODB to re-export from"}
        lint_only = hist(benches={"bench_lint": {"expect": "pass", "ok": True}})
        r = self.run_(spec(reroute_reason=rr), [lint_only])
        self.assertEqual((r["verdict"], r["kind"]), ("PASS", "evidence_gap"))
        self.assertEqual(self.run_(spec(reroute_reason=rr), [hist(metrics={"drc": 0})])["verdict"], "PASS")
        self.assertEqual(self.run_(spec(reroute_reason=rr), [hist(benches={})])["verdict"], "PASS")
        r = self.run_(spec(reroute_reason=rr))                                      # the closed job is complete
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("has a behavioural bench + mutant and a routed verdict", r["message"])
        r = self.run_(spec(reroute_reason={"kind": "evidence_gap", "why_route": "needed"}), [lint_only])
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("neither needs a route", r["message"])
        r = self.run_(spec(reroute_reason=rr), [lint_only, hist("t-v0-aaaaaaaaa", t="00:30")])
        self.assertEqual(r["verdict"], "REFUSE")                                    # another closure holds the evidence

    # ---------------------------------------------------------------- loop successors
    def test_successor_of_an_unclosed_job_is_exempt(self):
        par = hist("t-v2-bbbbbbbbb", status="NEEDS_RTL", commit="bbbbbbbbb", t="02:00",
                   auto_react={"g": ["t-v2-bbbbbbbbb-arg1", "t-v2-bbbbbbbbb-arg2"], "h": "t-v2-bbbbbbbbb-arh"})
        for nm, cls in (("t-v2-bbbbbbbbb-arg1", "g1"), ("t-v2-bbbbbbbbb-arh", "h")):
            s = spec(nm, auto_react_parent="t-v2-bbbbbbbbb", auto_react_class=cls)
            self.assertEqual(self.run_(s, [hist(), par])["verdict"], "EXEMPT", nm)
        forged = spec("t-v9-bbbbbbbbb", auto_react_parent="t-v2-bbbbbbbbb", auto_react_class="g1")
        self.assertEqual(self.run_(forged, [hist(), par])["verdict"], "REFUSE")     # the parent's record does not list it
        self.assertEqual(self.run_(spec("t-v2-bbbbbbbbb-hs"), [hist(), par])["verdict"], "EXEMPT")
        self.assertEqual(self.run_(spec("t-v2-bbbbbbbbb-ls", submit_lint={"requeued_from": "t-v2-bbbbbbbbb"}),
                                   [hist(), par])["verdict"], "EXEMPT")

    def test_successor_of_a_closed_job_is_not_exempt(self):
        self.assertEqual(self.run_(spec("t-v1-aaaaaaaaa-hs", commit="aaaaaaaaa"))["verdict"], "REFUSE")
        par = hist(auto_react={"h": "t-v1-aaaaaaaaa-arh"})
        s = spec("t-v1-aaaaaaaaa-arh", commit="aaaaaaaaa", auto_react_parent="t-v1-aaaaaaaaa", auto_react_class="h")
        self.assertEqual(self.run_(s, [par])["verdict"], "REFUSE")


class Submit(unittest.TestCase):
    """the loop hook: REFUSED / WARN / off, the record on the job, and `validate`"""
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.repo = Repo().put("aaaaaaaaa").put("bbbbbbbbb").put("ccccccccc", rtl="module ot_t; wire x; endmodule")
        self.repo.c["a" * 36] = self.repo.c["aaaaaaaaa"]
        git = type("G", (), {"show": staticmethod(self.repo.show), "blob": staticmethod(self.repo.blob)})
        self.p = [patch.object(cl, "ledger", lambda *a, **k: None), patch.object(cl, "log", lambda *a, **k: None),
                  patch.object(cl, "STATE", self.state), patch.object(cl.submit_lint, "Git", lambda repo: git),
                  patch.object(cl, "revoked_closures", lambda: (set(), set()))]
        [p.start() for p in self.p]

    def tearDown(self):
        [p.stop() for p in self.p]

    def job(self, **kw):
        sp = spec(**kw)
        return dict(name=sp["name"], spec=sp, status="QUEUED", events=[])

    def test_refused_with_the_instruction(self):
        j = self.job()
        cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual(j["status"], "REFUSED")
        self.assertTrue(j["reason"].startswith("SUBMIT_LINT CLOSED_STANDS: ot_t is CLOSED with a published view"))
        self.assertIn("re-export its view", j["reason"])
        self.assertEqual(j["submit_checks"]["closed_stands"]["verdict"], "REFUSE")
        self.assertEqual(j["submit_checks"]["closed_stands"]["closed"], ["t-v1-aaaaaaaaa"])

    def test_verified_reason_is_admitted_and_recorded(self):
        j = self.job(commit="ccccccccc", reroute_reason={"kind": "rtl_change"})
        cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual((j["submit_checks"]["closed_stands"]["verdict"], j["submit_checks"]["closed_stands"]["kind"]),
                         ("PASS", "rtl_change"))
        self.assertTrue(any("CLOSED-STANDS PASS" in e for e in j["events"]))

    def test_new_block_leaves_no_record(self):
        j = self.job()
        cl.closed_stands_at_submit(j, [])
        self.assertEqual((j["status"], j.get("submit_checks")), ("QUEUED", None))

    def test_revoked_closure_does_not_stand(self):
        with patch.object(cl, "revoked_closures", lambda: ({"t-v1-aaaaaaaaa"}, set())):
            j = self.job()
            cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual(j["status"], "QUEUED")

    def test_modes(self):
        (self.state / "ref_gate.json").write_text(json.dumps({"closed_stands": "warn"}))
        j = self.job()
        cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual((j["status"], j["submit_checks"]["closed_stands"]["verdict"]), ("QUEUED", "WARN"))
        (self.state / "ref_gate.json").write_text(json.dumps({"closed_stands": "off"}))
        j = self.job()
        cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual((j["status"], j.get("submit_checks")), ("QUEUED", None))

    def test_gate_error_never_blocks(self):
        with patch.object(cl, "revoked_closures", side_effect=RuntimeError("boom")):
            j = self.job()
            cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual(j["status"], "QUEUED")
        self.assertTrue(any("closed-stands gate skipped" in e for e in j["events"]))

    def test_source_file_resolution(self):
        rr = {"kind": "die_window", "slot": "qfd:ot_t", "cut": 0.8, "source": "results/arch/cuts.json"}   # on the job's commit
        j = self.job(reroute_reason=rr)
        cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual(j["status"], "QUEUED")
        j = self.job(reroute_reason=dict(rr, source="/nonexistent/cuts.json"))
        cl.closed_stands_at_submit(j, [hist()])
        self.assertEqual(j["status"], "REFUSED")

    def test_ref_tile_job_spec_carries_the_reason(self):
        import ref_tile as RT
        rr = {"kind": "die_window", "slot": "qfd:ot_t", "cut": 0.8, "source": "x.json"}
        src = Path(RT.__file__).read_text()
        self.assertIn('spec["reroute_reason"] = rr', src)
        import importlib.util
        m = importlib.util.spec_from_file_location("reroute_batch", HERE.parent / "ref_tile" / "reroute_batch.py")
        rb = importlib.util.module_from_spec(m)
        m.loader.exec_module(rb)
        got = rb.reroute_reason("ot_t", [{"src": "c.json", "path": "/d/c.json", "ax": "x", "pos": 5, "win": [0, 9],
                                          "util": 0.7, "frees": "M6"}])
        self.assertEqual((got["kind"], got["slot"], got["cut"], got["source"]), ("die_window", "ot_t", 0.7, "/d/c.json"))
        got = rb.reroute_reason("ot_t", [{"src": "g.rpt", "path": "/d/g.rpt", "grt_overflow": [0, 0, 1, 1], "layer": "M6"}])
        self.assertEqual((got["grt_overflow"], got["source"]), ([0, 0, 1, 1], "/d/g.rpt"))
        del rr


if __name__ == "__main__":
    unittest.main()
