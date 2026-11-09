#!/usr/bin/env python3
"""KW-RESUME-1 tests: stage fingerprints -> resume step, checkpoint fallbacks, apply/verify/release + resume.json
provenance, nochange refusal, the gen_phys RUN_KIT resume block, and kit_wave.resume_prepare end to end (local host)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import kit_resume as KR  # noqa: E402
import kit_wave as KW  # noqa: E402

BASE = "run/results/asap7/top/base"
LOGS = "run/logs/asap7/top/base"
CONFIG = """export DESIGN_NAME = top
export PLATFORM = asap7
export VERILOG_FILES = /work/rtl/top.v
export SDC_FILE = /work/top.sdc
export DIE_AREA = 0 0 100 100
override export MAKE_TRACKS = /work/make_tracks.tcl
export PLACE_DENSITY = 0.60
export CTS_BUF_DISTANCE = 60
export FASTROUTE_TCL = /work/fastroute.tcl
export DETAILED_ROUTE_END_ITERATION = 30
export OT_HOLD_FF_MARGIN = 10
"""
KIT_FILES = {"config.mk": CONFIG, "rtl/top.v": "module top(input a, output y); assign y = a; endmodule\n",
             "top.sdc": "create_clock -period 1000 [get_ports clk]\n", "make_tracks.tcl": "make_tracks M1\n",
             "fastroute.tcl": "set_global_routing_layer_adjustment M2 0.5\n",
             "lec.py": "# LEC driver\nprint('lec')\n", "hold_gate.tcl": "# hold gate\n"}
RUNNER = "#!/bin/bash\n# OT_STAGE_RESUME_V1 test runner  # KWRS\n$M ${KWRS_C:-cts}\n"
OLD_RUNNER = "#!/bin/bash\n$M cts\n"          # the same runner before stage resume (normalised equal)
STEP_FILES = {"synth": ["1_2_yosys.v", "1_synth.odb", "1_synth.sdc"], "floorplan": ["2_floorplan.odb", "2_floorplan.sdc"],
              "place": ["3_place.odb", "3_place.sdc"], "cts": ["4_cts.odb", "4_cts.sdc"], "grt": ["5_1_grt.odb"]}
BIG = 2 << 20


def make_kit(root, name, runner=RUNNER, files=None, upto="grt", t0=None):
    """a kit dir W/gen/<name> + W/gen/run_kit.sh; run/ complete through `upto` with increasing mtimes"""
    W = Path(root) / name
    K = W / "gen" / "top"
    K.mkdir(parents=True)
    (W / "gen" / "run_kit.sh").write_text(runner)
    for rel, txt in (files or KIT_FILES).items():
        (K / rel).parent.mkdir(parents=True, exist_ok=True)
        (K / rel).write_text(txt)
    t = (t0 or time.time() - 10000)
    for p in K.rglob("*"):
        if p.is_file():
            os.utime(p, (t, t))
    if upto:
        (K / BASE).mkdir(parents=True)
        (K / LOGS).mkdir(parents=True)
        (K / "run/reports/asap7/top/base").mkdir(parents=True)
        (K / "run/reports/asap7/top/base/synth_stat.txt").write_text("Number of cells: 10\n")
        os.utime(K / "run/reports/asap7/top/base/synth_stat.txt", (t + 100, t + 100))
        for i, s in enumerate(KR.STEPS[:KR.IDX[upto] + 1]):
            ts = t + 100 * (i + 1)
            for n in STEP_FILES[s]:
                p = K / BASE / n
                p.write_bytes((s.encode() + b"\n") * (BIG // (len(s) + 1) if n.endswith(".odb") else 8))
                os.utime(p, (ts, ts))
            for lg in KR.STEP_LOGS[s]:
                p = K / LOGS / lg
                p.write_text(f"{s} ok\n")
                os.utime(p, (ts, ts))
            if s == "place":                         # an intermediate of place (numbered, big -> hardlink)
                p = K / BASE / "3_3_place_gp.odb"
                p.write_bytes(b"x" * BIG)
                os.utime(p, (ts - 5, ts - 5))
    return W, K


def man(K, **kw):
    return KR.manifest(str(K), runner=str(Path(K).parent / "run_kit.sh"), **kw)


def fake_image(monkey_created="2026-08-27T00:00:00Z"):
    KR.image_info = lambda image: {"image": image, "id": "sha256:16470cea", "created": monkey_created}


class Fingerprint(unittest.TestCase):
    def setUp(self):
        fake_image()
        self.d = tempfile.mkdtemp()
        self.oW, self.oK = make_kit(self.d, "a1")

    def tearDown(self):
        shutil.rmtree(self.d)

    def new_kit(self, edit=None, runner=RUNNER):
        files = dict(KIT_FILES)
        if edit:
            edit(files)
        W, K = make_kit(self.d, f"a2_{len(os.listdir(self.d))}", runner=runner, files=files, upto=None)
        return man(K, with_checkpoint=False)

    def start(self, edit=None, **kw):
        d = KR.decide(self.new_kit(edit, **kw), man(self.oK))
        return d["decision"], d.get("start"), d

    def test_classification(self):
        m = man(self.oK)
        st = {r: f["stage"] for r, f in m["files"].items()}
        self.assertEqual(st["rtl/top.v"], "synth")
        self.assertEqual(st["make_tracks.tcl"], "floorplan")
        self.assertEqual(st["fastroute.tcl"], "grt")
        self.assertEqual(st["lec.py"], KR.GATE)
        self.assertEqual(m["config"]["PLACE_DENSITY"]["stage"], "place")
        self.assertEqual(m["config"]["OT_HOLD_FF_MARGIN"]["stage"], "grt")
        self.assertEqual(m["checkpoint"]["upto"], "grt")
        self.assertIn(f"{BASE}/4_cts.odb", m["run_files"])

    def test_change_at_each_step(self):
        def cfg(var, val):
            return lambda f: f.__setitem__("config.mk", re.sub(rf"(?m)^(export {var} = ).*$", rf"\g<1>{val}", f["config.mk"]))
        cases = [("synth", lambda f: f.__setitem__("rtl/top.v", f["rtl/top.v"] + "// changed\n")),
                 ("floorplan", lambda f: f.__setitem__("make_tracks.tcl", "make_tracks M2\n")),
                 ("floorplan", cfg("DIE_AREA", "0 0 120 120")),
                 ("place", cfg("PLACE_DENSITY", "0.55")),
                 ("cts", cfg("CTS_BUF_DISTANCE", "50")),
                 ("grt", lambda f: f.__setitem__("fastroute.tcl", "set_global_routing_layer_adjustment M2 0.4\n")),
                 ("grt", cfg("OT_HOLD_FF_MARGIN", "12")),
                 ("route", cfg("DETAILED_ROUTE_END_ITERATION", "40")),
                 ("route", lambda f: f.__setitem__("lec.py", "# LEC driver v2 (hint fix)\nprint('lec')\n"))]
        for want, edit in cases:
            dec, start, d = self.start(edit)
            if want == "synth":
                self.assertEqual(dec, "full", d)
            else:
                self.assertEqual((dec, start), ("resume", want), d)
                self.assertEqual(d["reuse"], list(KR.STEPS[:KR.IDX[want]]))

    def test_new_unknown_file_is_synth(self):
        dec, _, d = self.start(lambda f: f.__setitem__("extra_hook.tcl", "puts hi\n"))
        self.assertEqual(dec, "full", d)

    def test_strap_declaration_reuses_physics_but_sdc_change_does_not(self):
        edit = lambda f: f.__setitem__("straps.json", '{"straps":["strap_r8[0]"]}\n')
        dec, start, d = self.start(edit)
        self.assertEqual((dec, start), ("resume", "route"), d)
        self.assertEqual(d["reuse"], list(KR.STEPS[:KR.IDX["route"]]))
        def changed_sdc(files):
            edit(files)
            files["top.sdc"] += "set_case_analysis 0 [get_ports {strap_r8[0]}]\n"
        self.assertEqual(self.start(changed_sdc)[0], "full")

    def test_nochange_refused_unless_infra(self):
        new = self.new_kit()
        self.assertEqual(KR.decide(new, man(self.oK))["decision"], "nochange")
        d = KR.decide(new, man(self.oK), allow_nochange=True)
        self.assertEqual((d["decision"], d["start"]), ("resume", "route"))

    def test_stopped_attempt_may_rerun_same_inputs(self):
        # KW6-CLASS 11-04: S81 slice_station__t23/t44: volume cancelled mid-run, released, refused for ever
        with tempfile.TemporaryDirectory() as td:
            base = dict(dir=td, attempt=3, status="FAIL", **{"class": "FLOW"})
            self.assertFalse(KW.resume_source(None, base)["allow_nochange"])
            self.assertTrue(KW.resume_source(None, dict(base, status="CANCELLED"))["allow_nochange"])
            self.assertTrue(KW.resume_source(None, dict(base, **{"class": "VOLUME"}))["allow_nochange"])
            (Path(td) / "result.json").write_text(json.dumps({"stage": "resume_nochange", "class": "VOLUME"}))
            self.assertTrue(KW.resume_source(None, base)["allow_nochange"])
            (Path(td) / "result.json").write_text(json.dumps({"stage": "resume_nochange", "class": "FLOW"}))
            self.assertFalse(KW.resume_source(None, base)["allow_nochange"])

    def test_runner_normalisation(self):
        self.assertEqual(KR.runner_norm(RUNNER), OLD_RUNNER)
        shutil.copy(self.oW / "gen/run_kit.sh", self.oW / "gen/run_kit.bak")
        (self.oW / "gen/run_kit.sh").write_text(OLD_RUNNER)       # old attempt built before stage resume
        dec, start, d = self.start(lambda f: f.__setitem__("lec.py", "# v2\n"))
        self.assertEqual((dec, start), ("resume", "route"), d)
        dec, _, d = self.start(lambda f: f.__setitem__("lec.py", "# v2\n"), runner=RUNNER + "echo other flow edit\n")
        self.assertEqual(dec, "full")                             # any other runner change: full rebuild

    def test_runner_without_marker_full(self):
        dec, _, d = self.start(lambda f: f.__setitem__("lec.py", "# v2\n"), runner=OLD_RUNNER)
        self.assertEqual(dec, "full")
        self.assertIn(KR.MARKER, d["why"])

    def test_image_newer_than_checkpoint_full(self):
        fake_image(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())))
        dec, _, d = self.start(lambda f: f.__setitem__("lec.py", "# v2\n"))
        self.assertEqual(dec, "full")
        self.assertIn("image", d["why"])


class Checkpoint(unittest.TestCase):
    def setUp(self):
        fake_image()
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d)

    def lec_fix(self, oK):
        files = dict(KIT_FILES, **{"lec.py": "# v2\n"})
        _, K = make_kit(self.d, "new", files=files, upto=None)
        return KR.decide(man(K, with_checkpoint=False), man(oK))

    def test_missing_checkpoint_full(self):
        _, oK = make_kit(self.d, "a1", upto=None)
        d = self.lec_fix(oK)
        self.assertEqual(d["decision"], "full")
        self.assertIn("no reusable synth checkpoint", d["why"])

    def test_pruned_output_caps_start(self):
        _, oK = make_kit(self.d, "a1")
        os.unlink(oK / BASE / "4_cts.odb")                       # reaper stripped cts
        d = self.lec_fix(oK)
        self.assertEqual((d["decision"], d["start"]), ("resume", "cts"))

    def test_error_log_not_passed(self):
        _, oK = make_kit(self.d, "a1")
        (oK / LOGS / "3_3_place_gp.log").write_text("[ERROR GPL-0305] diverged\n")
        d = self.lec_fix(oK)
        self.assertEqual((d["decision"], d["start"]), ("resume", "place"))

    def test_stale_order_not_complete(self):
        _, oK = make_kit(self.d, "a1")
        t = os.path.getmtime(oK / BASE / "1_synth.odb") - 50
        for n in STEP_FILES["floorplan"]:
            os.utime(oK / BASE / n, (t, t))
        d = self.lec_fix(oK)
        self.assertEqual((d["decision"], d["start"]), ("resume", "floorplan"))

    def test_synth_only_checkpoint_full_when_synth_failed(self):
        _, oK = make_kit(self.d, "a1", upto="synth")
        (oK / LOGS / "1_2_yosys.log").write_text("ERROR: oops\n")
        self.assertEqual(self.lec_fix(oK)["decision"], "full")


class Apply(unittest.TestCase):
    def setUp(self):
        fake_image()
        self.d = tempfile.mkdtemp()
        _, self.oK = make_kit(self.d, "a1")
        _, self.nK = make_kit(self.d, "a2", files=dict(KIT_FILES, **{"config.mk": CONFIG.replace("= 60", "= 50")}), upto=None)
        self.old = man(self.oK)
        self.dec = KR.decide(man(self.nK, with_checkpoint=False), self.old)
        self.meta = {"host": "intel1", "kit": str(self.oK), "attempt": 1, "attempt_dir": "/ap/kit_wave/x/a1",
                     "checkpoint": self.old["checkpoint"], "same_host": True, "relay": None}

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_apply_links_and_provenance(self):
        self.assertEqual(self.dec["start"], "cts")
        rec = KR.apply(str(self.nK), str(self.oK), self.dec, self.meta)
        r = json.loads((self.nK / "resume.json").read_text())
        self.assertEqual(r["start"], "cts")
        self.assertEqual(r["reused_steps"], ["synth", "floorplan", "place"])
        self.assertEqual(r["source"]["kit"], str(self.oK))
        self.assertEqual(r["source"]["attempt"], 1)
        self.assertTrue(all(r["source_checkpoint"][s]["passed"] for s in r["reused_steps"]))
        self.assertTrue(r["changed"])
        modes = {x["rel"]: x["mode"] for x in r["links"]}
        self.assertEqual(modes[f"{BASE}/1_synth.odb"], "link")
        self.assertEqual(modes[f"{BASE}/3_3_place_gp.odb"], "link")
        self.assertEqual(modes[f"{BASE}/3_place.odb"], "copy")             # boundary checkpoint the next step reads
        self.assertNotIn(f"{BASE}/4_cts.odb", modes)
        self.assertEqual(modes["run/reports/asap7/top/base/synth_stat.txt"], "copy")
        self.assertEqual(os.stat(self.nK / BASE / "1_synth.odb").st_ino, os.stat(self.oK / BASE / "1_synth.odb").st_ino)
        self.assertNotEqual(os.stat(self.nK / BASE / "3_place.odb").st_ino, os.stat(self.oK / BASE / "3_place.odb").st_ino)
        self.assertTrue((self.oK / ".keep").exists() and rec["keep_created"])
        self.assertEqual(KR.verify(str(self.nK)), [])
        # a write through a hardlink is detected
        with open(self.nK / BASE / "1_synth.odb", "ab") as f:
            f.write(b"oops")
        self.assertTrue(KR.verify(str(self.nK)))
        self.assertTrue(KR.release(str(self.nK)))
        self.assertFalse((self.oK / ".keep").exists())

    def test_stale_step_markers_dropped(self):
        # COORD 11-05 class fix: a cp -al copy carries .kwrs_done.<ppid>; the old run's steps must not read as done
        for d in (self.nK, self.oK, self.oK / "run"):
            (d / ".kwrs_done.7").write_text("do-floorplan\ndo-place\ndo-cts\ndo-grt\n")
        os.link(self.oK / ".kwrs_done.7", self.nK / ".kwrs_done.8")
        rec = KR.apply(str(self.nK), str(self.oK), self.dec, self.meta)
        self.assertEqual(sorted(os.path.basename(p) for p in rec["markers_dropped"]), [".kwrs_done.7", ".kwrs_done.8"])
        self.assertEqual([p for p in os.listdir(self.nK) if p.startswith(".kwrs_done")], [])
        self.assertFalse((self.nK / "run" / ".kwrs_done.7").exists())        # not carried by link_plan
        self.assertTrue((self.oK / ".kwrs_done.7").exists())                  # source untouched
        self.assertNotIn("run/.kwrs_done.7", {x["rel"] for x in rec["links"]})

    def test_clean_cli_after_cp_al(self):
        cp = Path(self.d) / "copy"
        shutil.copytree(self.oK, cp, copy_function=os.link)
        (self.oK / ".kwrs_done.12").write_text("do-grt\n")
        os.link(self.oK / ".kwrs_done.12", cp / ".kwrs_done.12")
        (cp / "run" / ".kwrs_done.12").write_text("do-cts\n")
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(KR.main(["clean", str(cp)]), 0)
        self.assertIn("KW_RESUME_CLEAN", buf.getvalue())
        self.assertEqual(sorted(json.loads(buf.getvalue().split(" ", 1)[1])["removed"]),
                         sorted([str(cp / ".kwrs_done.12"), str(cp / "run" / ".kwrs_done.12")]))
        self.assertTrue((self.oK / ".kwrs_done.12").exists())
        self.assertEqual(KR.drop_markers(str(cp)), [])

    def test_existing_keep_not_removed(self):
        (self.oK / ".keep").write_text("owner keep\n")
        KR.apply(str(self.nK), str(self.oK), self.dec, self.meta)
        self.assertFalse(KR.release(str(self.nK)))
        self.assertTrue((self.oK / ".keep").exists())

    def test_apply_refuses_changed_source(self):
        with open(self.oK / BASE / "1_synth.odb", "ab") as f:
            f.write(b"more")
        with self.assertRaises(RuntimeError):
            KR.apply(str(self.nK), str(self.oK), self.dec, self.meta)
        self.assertFalse((self.nK / "run").exists())

    def test_apply_refuses_existing_run(self):
        (self.nK / "run").mkdir()
        with self.assertRaises(RuntimeError):
            KR.apply(str(self.nK), str(self.oK), self.dec, self.meta)

    def test_cli_roundtrip(self):
        src = (HERE / "kit_resume.py").read_text()
        dj = Path(self.d) / "dec.json"
        dj.write_text(json.dumps({"decision": self.dec, "source": self.meta}))
        p = subprocess.run([sys.executable, "-", "apply", str(self.nK), "--src", str(self.oK), "--decision", str(dj)],
                           input=src, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("KW_RESUME_APPLIED ", p.stdout)
        p = subprocess.run([sys.executable, "-", "verify", str(self.nK)], input=src, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)


class RunKitBlock(unittest.TestCase):
    """the RUN_KIT resume block: bash syntax, normalisation to the runner without resume, and its variables"""
    @classmethod
    def setUpClass(cls):
        import gen_phys
        cls.rk = gen_phys.RUN_KIT

    def test_marker_and_syntax(self):
        self.assertIn(KR.MARKER, self.rk)
        p = subprocess.run(["bash", "-n"], input=self.rk, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        n = KR.runner_norm(self.rk)
        self.assertNotIn("KWRS", n)
        for s in ("\\$M synth;", "\\$M cts SKIP_CTS_REPAIR_TIMING=1", "\\$M $GOAL;", "\\$M grt;", "\\$MF grt CORNER=BC"):
            self.assertIn(s, n)
            self.assertIn(s, self.rk)                     # make calls unchanged: kwrs_make.sh filters them

    def outer(self, d, start, goal):
        """run the runner's outer resume block (lines up to 'fi  # KWRS') with K=d"""
        lines = self.rk.splitlines()
        a = next(i for i, ln in enumerate(lines) if ln.startswith("RS=0; KWRS_M="))
        b = next(i for i, ln in enumerate(lines) if ln.startswith("fi  # KWRS"))
        if start:
            Path(d, "resume.json").write_text(json.dumps({"start": start, "reused_steps": ["synth"],
                                                           "source": {"host": "h", "kit": "/k"}}))
        sh = "set -u\nK=%s; GOAL=%s\n%s\necho \"V RS=$RS M=[$KWRS_M]\"\n" % (d, goal, "\n".join(lines[a:b + 1]))
        p = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
        return p.returncode, p.stdout

    OUTF = {"do-floorplan": "2_floorplan.odb", "do-place": "3_place.odb", "do-cts": "4_cts.odb", "do-grt": "5_1_grt.odb",
            "do-5_2_route": "5_2_route.odb", "do-5_3_fillcell": "5_3_fillcell.odb", "do-5_route": "5_route.odb",
            "do-5_route.sdc": "5_route.sdc"}

    def fake_make(self, d, rc=0):
        """a make stand-in: prints its command line and, like ORFS, writes each do-* step's stage output (rc 0 only)"""
        base = os.path.join(d, "run", "results", "asap7", "dp_x", "base")
        os.makedirs(base, exist_ok=True)
        fm = os.path.join(d, "fake_make%d.sh" % rc)
        Path(fm).write_text("#!/bin/bash\necho \"$*\"\n[ %d = 0 ] || exit %d\n" % (rc, rc) + "".join(
            'for a in "$@"; do [ "$a" = %s ] && echo x > %s/%s; done\n' % (t, base, f) for t, f in self.OUTF.items()) + "exit 0\n")
        os.chmod(fm, 0o755)
        return fm, base

    def make(self, d, rs, *calls, rc=0):
        """kwrs_make.sh with a fake make (see fake_make): -> the make command lines it would run"""
        fm, _ = self.fake_make(d, rc)
        out = []
        for c in calls:
            p = subprocess.run(["bash", os.path.join(d, "kwrs_make.sh"), str(rs), fm, "DESIGN_CONFIG=/x"] + c.split(),
                               capture_output=True, text=True, env=dict(os.environ, KWRS_DONE=os.path.join(d, "done")))
            out.append((p.returncode, [ln for ln in p.stdout.splitlines() if ln.startswith("DESIGN_CONFIG")]))
        return out

    def test_copied_marker_without_outputs_reruns(self):
        """KW-FIX-30 11-07 (DIE-KV-89 Wi vRL): a kit copied with an older run's done list but no stage outputs must run
        those steps (old runners skipped floorplan + place: 3_place.odb never written)"""
        d = tempfile.mkdtemp()
        try:
            rc, out = self.outer(d, "floorplan", "place")
            self.assertEqual(rc, 0)
            Path(d, "done").write_text("do-floorplan\ndo-place\n")
            self.fake_make(d)
            r = self.make(d, 1, "place")
            self.assertEqual(r[0], (0, ["DESIGN_CONFIG=/x do-floorplan do-place"]))
            r = self.make(d, 1, "place")                    # now done in this kit: outputs exist, skipped
            self.assertEqual(r[0], (0, []))
            _, base = self.fake_make(d)
            os.unlink(os.path.join(base, "3_place.odb"))    # output gone (pruned / partial copy): place runs again
            r = self.make(d, 1, "place")
            self.assertEqual(r[0], (0, ["DESIGN_CONFIG=/x do-place"]))
        finally:
            shutil.rmtree(d)

    def test_failed_step_not_marked(self):
        """a step whose make call fails is not written to the done list, so the next runner re-runs it"""
        d = tempfile.mkdtemp()
        try:
            self.outer(d, "cts", "route")
            r = self.make(d, 3, "cts", rc=2)
            self.assertEqual(r[0], (2, ["DESIGN_CONFIG=/x do-cts"]))
            self.assertNotIn("do-cts", Path(d, "done").read_text().split())
            r = self.make(d, 3, "cts")
            self.assertEqual(r[0], (0, ["DESIGN_CONFIG=/x do-cts"]))
            self.assertIn("do-cts", Path(d, "done").read_text().split())
        finally:
            shutil.rmtree(d)

    def test_done_list_not_keyed_by_ppid(self):
        """$PPID is 1 in every container: the default done list is keyed by resume.json, never by $PPID"""
        rk = self.rk
        a = rk.index("KWRS_MAKE'  # KWRS-BEGIN")
        blk = rk[a:rk.index("KWRS_MAKE\n", a + 20)]
        self.assertNotIn("$PPID", blk)
        self.assertIn("/work/.kwrs_done.r$(cksum < /work/resume.json", blk)
        g = Path(os.path.dirname(os.path.abspath(__file__)), "..", "..", "physical", "common_flow", "grt183_make.sh")
        if g.exists():
            t = g.read_text()
            self.assertNotIn(".kwrs_done.$PPID", t)
            self.assertIn('.kwrs_done.r$(cksum < "$W/resume.json"', t)

    def test_no_resume(self):
        d = tempfile.mkdtemp()
        try:
            rc, out = self.outer(d, None, "route")
            self.assertIn("V RS=0 M=[]", out)
            self.assertFalse(os.path.exists(os.path.join(d, "kwrs_make.sh")))
        finally:
            shutil.rmtree(d)

    def test_make_filter(self):
        d = tempfile.mkdtemp()
        try:
            rc, out = self.outer(d, "place", "place")
            self.assertEqual(rc, 0)
            self.assertIn('M=[M="bash /work/kwrs_make.sh 2 $M"; ]', out)
            r = self.make(d, 2, "synth", "place", "print-BC_LIB_FILES")
            self.assertEqual(r[0], (0, []))
            self.assertEqual(r[1], (0, ["DESIGN_CONFIG=/x do-place"]))
            self.assertEqual(r[2][1], ["DESIGN_CONFIG=/x print-BC_LIB_FILES"])
            os.unlink(os.path.join(d, "done"))
            r = self.make(d, 1, "place")
            self.assertEqual(r[0][1], ["DESIGN_CONFIG=/x do-floorplan do-place"])
            os.unlink(os.path.join(d, "done"))
            # resumed at cts, goal route: cts + tapbal + grt + route + finish as do-* targets
            r = self.make(d, 3, "cts SKIP_CTS_REPAIR_TIMING=1", "run RUN_SCRIPT=/work/tapbal_grt.tcl", "grt CORNER=BC",
                          "route", "do-finish", "cts")
            self.assertEqual([x[1] for x in r], [["DESIGN_CONFIG=/x SKIP_CTS_REPAIR_TIMING=1 do-cts"],
                                                 ["DESIGN_CONFIG=/x RUN_SCRIPT=/work/tapbal_grt.tcl run"],
                                                 ["DESIGN_CONFIG=/x CORNER=BC do-grt"],
                                                 ["DESIGN_CONFIG=/x do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc"],
                                                 ["DESIGN_CONFIG=/x do-finish"], []])       # cts twice: once
            os.unlink(os.path.join(d, "done"))
            # resumed at grt / route: cts and the tapbal pre-pass (writes 4_cts.odb in place) are skipped
            r = self.make(d, 5, "cts", "run RUN_SCRIPT=/work/tapbal_grt.tcl", "grt", "route")
            self.assertEqual([x[1] for x in r], [[], [], [], ["DESIGN_CONFIG=/x do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc"]])
            r = self.make(d, 4, "finish")
            self.assertEqual(r[0][0], 10)                                                  # unknown target: fail closed
        finally:
            shutil.rmtree(d)

    def test_resume_floorplan_goal_route_runs_floorplan_place(self):
        """KW-FIX-22 11-06 (S81-RCK-2 serdes__t4): start=floorplan, goal route: the runner's first stage call is '$M cts';
        it must run do-floorplan do-place do-cts (the old filter ran do-cts alone: ORD-0007 3_place.odb missing)."""
        d = tempfile.mkdtemp()
        try:
            rc, out = self.outer(d, "floorplan", "route")
            self.assertEqual(rc, 0)
            r = self.make(d, 1, "synth", "cts SKIP_CTS_REPAIR_TIMING=1", "grt CORNER=BC", "route", "cts")
            self.assertEqual([x[1] for x in r], [[], ["DESIGN_CONFIG=/x SKIP_CTS_REPAIR_TIMING=1 do-floorplan do-place do-cts"],
                                                 ["DESIGN_CONFIG=/x CORNER=BC do-grt"],
                                                 ["DESIGN_CONFIG=/x do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc"], []])
            os.unlink(os.path.join(d, "done"))
            r = self.make(d, 2, "grt")                       # start place, first call grt: place + cts + grt
            self.assertEqual(r[0][1], ["DESIGN_CONFIG=/x do-place do-cts do-grt"])
            os.unlink(os.path.join(d, "done"))
            r = self.make(d, 1, "route")                     # route alone from floorplan: steps up to cts, never grt
            self.assertEqual(r[0][1], ["DESIGN_CONFIG=/x do-floorplan do-place do-cts do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc"])
        finally:
            shutil.rmtree(d)

    def test_fail_closed(self):
        for start, goal in (("route", "finish"), ("bogus", "route")):
            d = tempfile.mkdtemp()
            try:
                rc, _ = self.outer(d, start, goal)
                self.assertEqual(rc, 10)
                self.assertTrue(os.path.exists(os.path.join(d, "FAIL_PREFLOOR")))
            finally:
                shutil.rmtree(d)


class Prepare(unittest.TestCase):
    """kit_wave.resume_prepare on the local host (gen host == hub): decide + apply, nochange FAIL, missing source"""
    def setUp(self):
        fake_image()
        import kit_wave as KW
        self.KW = KW
        self.d = tempfile.mkdtemp()
        self.oW, self.oK = make_kit(self.d, "a1")

    def tearDown(self):
        shutil.rmtree(self.d)

    def prep(self, files, cands=None, allow=False):
        nW, nK = make_kit(self.d, f"a{len(os.listdir(self.d)) + 1}", files=files, upto=None)
        sp = {"gen_host": "localhost", "hub": "intel2", "work": str(nW), "item": "top",
              "resume_from": {"attempt": 1, "attempt_dir": "/ap/a1", "class": "LEC", "allow_nochange": allow,
                              "gen_end": None, "candidates": cands if cands is not None else [["localhost", str(self.oK)]]}}
        res = {}

        def run(stage, argv, timeout=None, idempotent=False):
            env = dict(os.environ, PATH=os.environ["PATH"])
            p = subprocess.run(argv, capture_output=True, text=True, env=env)
            return p.returncode, p.stdout + p.stderr

        orig = self.KW.kr_cmd
        self.KW.kr_cmd = lambda a: orig(a).replace("python3 - ", f"{sys.executable} - ", 1)
        try:
            rs = self.KW.resume_prepare(sp, str(nK), str(nW / "gen/run_kit.sh"), run, lambda c: ["bash", "-c", c], res)
        finally:
            self.KW.kr_cmd = orig
        return rs, res, nK

    def need_image(self, res):
        if any(c[1] == "image" for c in res["resume"].get("changed") or []):
            self.skipTest("no ORFS image on this host (docker image inspect)")

    def test_resume_applied(self):
        # the ORFS image check runs in the remote manifest (docker inspect): skip when docker is absent
        rs, res, nK = self.prep(dict(KIT_FILES, **{"lec.py": "# v2\n"}))
        self.need_image(res)
        self.assertEqual(rs, "route", res)
        self.assertTrue((nK / "resume.json").exists())
        self.assertEqual(res["resume"]["reuse"], ["synth", "floorplan", "place", "cts", "grt"])
        self.assertIn("stage_fp", res)

    def test_nochange_fail(self):
        rs, res, nK = self.prep(dict(KIT_FILES))
        self.need_image(res)
        self.assertEqual(rs, "nochange")
        self.assertEqual((res["verdict"], res["class"], res["stage"]), ("FAIL", "LEC", "resume_nochange"))

    def test_missing_source_full(self):
        rs, res, nK = self.prep(dict(KIT_FILES, **{"lec.py": "# v2\n"}), cands=[["localhost", "/nonexistent/kit"]])
        self.assertEqual(rs, "")
        self.assertEqual(res["resume"]["decision"], "full")
        self.assertFalse((nK / "run").exists())


class HoldGuardCapTest(unittest.TestCase):
    """FLOW-24 11-03: a GRT log whose only [ERROR] is the HOLD-GUARD-GRT caught chunk cap is a passed stage."""

    def test_caught_cap_is_not_an_error_line(self):
        t = ("[ERROR RSZ-0060] Max buffer count reached.\nTook 5 seconds\n"
             "OT_HOLD_GUARD_GRT chunk 2: hold ws 0.05 (+48.60) tns 0.0 viol 0, +581 buffers (cap 1478), 361 s\n")
        self.assertIsNone(KR.ERR_LINE.search(KR.HOLD_GUARD_CAP_RE.sub("", t)))

    def test_uncaught_cap_still_fails(self):
        t = "[ERROR RSZ-0060] Max buffer count reached.\nmake: *** Error 1\n"
        self.assertIsNotNone(KR.ERR_LINE.search(KR.HOLD_GUARD_CAP_RE.sub("", t)))



class LinkPlanStepLog(unittest.TestCase):
    """KW-FIX-40 11-08: the last reused step's log lands about 2 s after its ODB and must still carry over"""
    def plan(self, log_dt):
        base = "run/results/asap7/d/base"
        logs = "run/logs/asap7/d/base"
        ck = {"base": base, "steps": {"grt": {"end": 1000.0}}}
        files = {f"{base}/5_1_grt.odb": [1 << 21, 1000.0], f"{logs}/5_1_grt.json": [10, 1000.0],
                 f"{logs}/5_1_grt.log": [10, 1000.0 + log_dt], f"{logs}/notes.txt": [10, 1000.0 + log_dt],
                 f"{logs}/5_2_route.log": [10, 1000.0 + log_dt]}
        return {rel: mode for rel, mode in KR.link_plan(ck, "route", files)}

    def test_late_log_of_last_step_kept(self):
        p = self.plan(2.0)
        self.assertEqual(p.get("run/logs/asap7/d/base/5_1_grt.log"), "copy")
        self.assertIn("run/logs/asap7/d/base/5_1_grt.json", p)

    def test_other_late_files_and_later_step_still_dropped(self):
        p = self.plan(2.0)
        self.assertNotIn("run/logs/asap7/d/base/notes.txt", p)
        self.assertNotIn("run/logs/asap7/d/base/5_2_route.log", p)


if __name__ == "__main__":
    unittest.main()


class RunKitChildContext(unittest.TestCase):
    """KW-FIX-30 11-07 (COORD 15:01 (b)): run_kit.sh passes the flow tag and mounts signed child records read-only"""
    def block(self):
        import gen_phys
        lines = gen_phys.RUN_KIT.splitlines()
        a = next(i for i, ln in enumerate(lines) if ln.startswith("FT=${OT_FLOW_TAG:-"))
        b = next(i for i, ln in enumerate(lines) if ln.startswith("[ ${#CHILD_RO[@]} = 0 ]"))
        return "\n".join(lines[a:b + 1])

    def run_block(self, K, env=None):
        sh = "K=%s\n%s\nprintf 'FT=[%%s]\\n' \"$FT\"; for x in \"${CHILD_RO[@]}\"; do printf 'ARG=[%%s]\\n' \"$x\"; done\n" % (K, self.block())
        e = dict(os.environ); e.pop("OT_FLOW_TAG", None); e.update(env or {})
        p = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, env=e)
        self.assertEqual(p.returncode, 0, p.stderr)
        return [ln for ln in p.stdout.splitlines() if ln.startswith(("FT=", "ARG="))]

    def test_tag_and_child_mounts(self):
        d = tempfile.mkdtemp()
        try:
            K = Path(d, "kit"); (K / "macros").mkdir(parents=True)
            rec = Path(d, "child_rec"); (rec / "signoff").mkdir(parents=True)
            (rec / "signoff" / "signoff.json").write_text("{}")
            lecd = Path(d, "lecs", "c1"); lecd.mkdir(parents=True); (lecd / "lec.json").write_text("{}")
            (rec / "PROVENANCE.json").write_text(json.dumps({"kind": "resign", "lec": str(lecd / "lec.json")}))
            (K / "macros" / "c1.provenance.json").write_text(json.dumps({"export": {"signoff": str(rec / "signoff" / "signoff.json")}}))
            (K / "macros" / "inner.provenance.json").write_text(json.dumps({"export": {"signoff": "own/signoff/signoff.json"}}))
            (K / "macros" / "own" / "signoff").mkdir(parents=True)
            (K / "macros" / "bad.provenance.json").write_text("not json")
            self.assertEqual(self.run_block(K), ["FT=[]", "ARG=[-v]", "ARG=[%s:%s:ro]" % (rec, rec),
                                                 "ARG=[-v]", "ARG=[%s:%s:ro]" % (lecd, lecd)])
            (K / "flow_tag").write_text("flow-20261107-ea-hbm\n")
            self.assertEqual(self.run_block(K)[0], "FT=[flow-20261107-ea-hbm]")
            self.assertEqual(self.run_block(K, {"OT_FLOW_TAG": "flow-x"})[0], "FT=[flow-x]")   # host env wins
            shutil.rmtree(K / "macros")
            self.assertEqual(self.run_block(K)[1:], [])                                         # no sidecar: no mount
        finally:
            shutil.rmtree(d)

    def test_docker_run_carries_mounts_and_tag(self):
        import gen_phys
        self.assertIn('-v "$K":/work "${CHILD_RO[@]}" -e OT_FLOW_TAG="$FT" \\\n  -e HUID=', gen_phys.RUN_KIT)
        p = subprocess.run(["bash", "-n"], input=gen_phys.RUN_KIT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
