"""LOOP-AUTO (2026-10-10): auto-react recipes by failure class, the READY_NEXT deep queue, and HOST-DOWN requeue."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="autoreact_"))
import closure_loop as cl  # noqa: E402

HERE = Path(__file__).resolve().parent


def spec(name="j", block="blk", owner="Claude:hbm-forks", **kw):
    s = dict(name=name, block=block, owner=owner, source=dict(branch="main", commit="abcdef123"),
             stages=dict(route=dict(cmd="bash physical/x/route.sh {LABEL}")), verdict=dict(corner_sta="x"))
    s.update(kw)
    return s


def job(name="j", status="NEEDS_RTL", **kw):
    sp = kw.pop("spec", None) or spec(name)
    j = dict(name=name, status=status, spec=sp, created=cl.now_iso(), finished_at=cl.now_iso(), events=[],
             host="h", run=f"/r/{name}", attempt=1, stage_idx=1, benches={}, reason="")
    j.update(kw)
    return j


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "state" / "jobs").mkdir(parents=True)
        self.tk = self.d / "takeover"
        (self.tk / "READY_NEXT").mkdir(parents=True)
        for n in ("hbm-phys-1010.log", "qwen-1010.log", "ds-1010.log", "drive-1010.log", "hgi-1010.log"):
            (self.tk / n).write_text("")
        ps = [patch.object(cl, "STATE", self.d / "state"), patch.object(cl, "DROP", self.d / "drop"),
              patch.object(cl, "TAKEOVER", self.tk), patch.object(cl, "READY_NEXT", self.tk / "READY_NEXT"),
              patch.object(cl, "ledger"), patch.object(cl, "log"), patch.object(cl, "experiment"),
              patch.object(cl, "validate", return_value=[]),
              # class f reads the job's CTS logs over ssh: no macro clock signature unless a test says so
              patch.object(cl, "ssh", lambda h, c, **k: SimpleNamespace(returncode=0, stdout="", stderr=""))]
        for p in ps:
            p.start()
            self.addCleanup(p.stop)
        cl._RN_BAD.clear()

    def run_pass(self, *jobs):
        for j in jobs:
            cl.save_job(j)
        return cl.auto_react(cl.all_jobs())

    def drop(self, name):
        p = self.d / "drop" / f"{name}.json"
        return json.loads(p.read_text()) if p.exists() else None


class OwnerLog(unittest.TestCase):
    def test_mapping(self):
        with tempfile.TemporaryDirectory() as t, patch.object(cl, "TAKEOVER", Path(t)):
            (Path(t) / "hbm-phys-1010.log").write_text("")
            f = lambda o, b="x", n="x": cl.owner_log_path(dict(name=n, spec=dict(owner=o, block=b))).name  # noqa: E731
            self.assertEqual(f("Claude:hbm-phys-1010"), "hbm-phys-1010.log")
            self.assertEqual(f("Claude:hgi-adapters"), "hgi-1010.log")
            self.assertEqual(f("Claude:mtp-lead", "ot_hbm_mtp"), "mtp-wfc-1010.log")
            self.assertEqual(f("Claude:kv-die"), "qwen-1010.log")
            self.assertEqual(f("Claude:redesign-ds"), "ds-1010.log")
            self.assertEqual(f("Claude:x", "ot_s81_bf"), "ds-1010.log")
            self.assertEqual(f("Claude:hbm-forks"), "hbm-phys-1010.log")
            self.assertEqual(f("Claude:other", "misc"), "drive-1010.log")


class ClassA(Base):
    def test_hold_window_reopens_with_keepwires(self):
        j = job(metrics=dict(ss_ps=3.0, ff_ps=-12.0, drc=0), eco=dict(tried=True, out="/r/j/cl/eco", result={}))
        acted = self.run_pass(j)
        self.assertEqual(acted, [("j", "a:in-place")])
        j = cl.load_job("j")
        self.assertEqual((j["status"], j["stage_idx"], j["attempt"]), ("READY", 1, 2))
        self.assertTrue(j["auto_react_keepwires"])
        self.assertEqual(j["eco"], {})
        self.assertEqual(len(j["eco_history"]), 1)
        self.assertEqual(j["auto_react"], {"a": "in-place"})

    def test_outside_window_or_released(self):
        self.assertFalse(cl.ar_hold_window(job(metrics=dict(ss_ps=3.0, ff_ps=-31.0, drc=0))))
        self.assertFalse(cl.ar_hold_window(job(metrics=dict(ss_ps=-1.0, ff_ps=-5.0, drc=0))))
        self.assertFalse(cl.ar_hold_window(job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=2))))
        self.assertFalse(cl.ar_hold_window(job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0), eco=dict(installed="t"))))
        self.assertFalse(cl.ar_hold_window(job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0), eco_history=[dict(keepwires=True)])))
        self.assertFalse(cl.ar_hold_window(job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0), stage_idx=0)))
        j = job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0), deep_released=dict(at="x"))
        self.assertEqual(self.run_pass(j), [("j", "none")])
        self.assertIn("route products released", (self.tk / "hbm-phys-1010.log").read_text())

    def test_second_failure_goes_to_owner_log(self):
        j = job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0), auto_react={"a": "in-place"},
                eco=dict(tried=True, keepwires=True))
        self.assertEqual(self.run_pass(j), [("j", "none")])
        line = (self.tk / "hbm-phys-1010.log").read_text()
        self.assertIn("[loop auto-react] j: NEEDS_RTL", line)
        self.assertIn("structural fix needed", line)

    def test_hold_eco_env_has_keepwires(self):
        j = job(auto_react_keepwires=True, metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        fleet = MagicMock()
        fleet.fits.return_value = (True, "")
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "eco_post_sdcs", return_value=[]), \
                patch.object(cl, "ship_helpers"), patch.object(cl, "launch_stage") as ls, patch.object(cl, "event"):
            self.assertTrue(cl.start_hold_eco(j, fleet, j["metrics"]))
        self.assertIn(" KEEPWIRES=1", ls.call_args[0][2])
        self.assertTrue(j["eco"]["keepwires"])
        j2 = job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "eco_post_sdcs", return_value=[]), \
                patch.object(cl, "ship_helpers"), patch.object(cl, "launch_stage") as ls, patch.object(cl, "event"):
            cl.start_hold_eco(j2, fleet, j2["metrics"])
        self.assertNotIn("KEEPWIRES", ls.call_args[0][2])


class ClassB(Base):
    def test_combo_reopen(self):
        j = job(metrics=dict(ss_ps=-10.0, ff_ps=-4.0, drc=0))
        self.assertEqual(self.run_pass(j), [("j", "b:in-place")])
        j = cl.load_job("j")
        self.assertEqual(j["status"], "READY")
        self.assertNotIn("auto_react_keepwires", j)

    def test_combo_tried(self):
        j = job(metrics=dict(ss_ps=-10.0, ff_ps=-4.0, drc=0), eco=dict(kind="combo", tried=True))
        self.assertEqual(self.run_pass(j), [("j", "none")])


class ClassC(Base):
    def test_pinflop_successor(self):
        sp = spec("hf", pinflop_ref=False)
        j = job("hf", "EARLY_FAIL_HOLD", spec=sp, stage_started="2026-10-10T05:00", rtl_boundary_verdict="PASS")
        self.assertEqual(self.run_pass(j), [("hf", "c:hf-arc")])
        s = self.drop("hf-arc")
        self.assertIs(s["pinflop_ref"], True)
        self.assertEqual(s["source"]["commit"], "abcdef123")
        self.assertEqual((s["auto_react_parent"], s["auto_react_class"]), ("hf", "c"))
        self.assertEqual(s["owner"], sp["owner"])

    def test_old_route_counts_as_not_used(self):
        j = job("hf", "EARLY_FAIL_HOLD", stage_started="2026-10-09T05:00", rtl_boundary_verdict="PASS")
        self.assertFalse(cl.pinflop_used(j))
        self.assertTrue(cl.pinflop_used(dict(j, stage_started="2026-10-10T05:00")))
        self.assertTrue(cl.pinflop_used(dict(j, pinflop_ref_applied=True)))

    def test_no_recipe_when_used_or_unregistered(self):
        j = job("hf", "EARLY_FAIL_HOLD", pinflop_ref_applied=True, rtl_boundary_verdict="PASS")
        self.assertEqual(self.run_pass(j), [("hf", "none")])
        j2 = job("hg", "EARLY_FAIL_HOLD", spec=spec("hg", block="b2"), stage_started="2026-10-09T05:00",
                 events=["2026-10-09T01:00 submit lint PASS (estimate 1 b/um, limit 2); WARN in->out 3 bits"])
        self.assertEqual(self.run_pass(j2), [("hg", "none")])
        self.assertIsNone(self.drop("hg-arc"))
        self.assertIn("RTL boundary WARN", (self.tk / "hbm-phys-1010.log").read_text())

    def test_successor_failing_again(self):
        sp = spec("hf-arc", auto_react_parent="hf", auto_react_class="c")
        j = job("hf-arc", "EARLY_FAIL_HOLD", spec=sp, stage_started="2026-10-09T05:00", rtl_boundary_verdict="PASS")
        self.assertEqual(self.run_pass(j), [("hf-arc", "none")])
        self.assertIn("successor failed again", (self.tk / "hbm-phys-1010.log").read_text())


class ClassD(Base):
    def test_sliver_only(self):
        j = job("fp", "FLOORPLAN_MARGIN", spec=spec("fp", owner="Claude:kv-die"),
                reason="sliver: 2 macro gap(s) < 12 um hold placement rows without a hard placement blockage (a|b gap 3.2 um rows 40 um2)")
        with patch.object(cl, "release_route_key") as rk:
            self.assertEqual(self.run_pass(j), [("fp", "d:fp-ard")])
        rk.assert_called_once()
        self.assertIs(self.drop("fp-ard")["sliver_block"], True)

    def test_mixed_checks(self):
        j = job("fp", "FLOORPLAN_MARGIN", spec=spec("fp", owner="Claude:kv-die"),
                reason="sliver: 2 macro gaps | channel: 1 cut line(s) need more tracks")
        self.assertEqual(self.run_pass(j), [("fp", "none")])
        self.assertIn("['channel', 'sliver']", (self.tk / "qwen-1010.log").read_text())

    def test_launch_env(self):
        from types import SimpleNamespace
        bodies = []

        def fake_ssh(host, c, input=None, **k):
            if input is not None:
                bodies.append(input)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        for extra, want in (({"sliver_block": True}, True), ({}, False)):
            bodies.clear()
            sp = {"name": "t", "block": "b", "route_hold_corners": "keep", "source": {"branch": "main", "commit": "c" * 40},
                  "stages": {}, **extra}
            j = {"name": "t", "run": "/r", "host": "ot-epyc3", "spec": sp, "commit_full": "c" * 40, "attempt": 1,
                 "created": "2026-10-08T19:00:00-07:00"}
            with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "ship_helpers"), patch.object(cl, "is_local", lambda h: False):
                cl.launch_stage(j, {"kind": "route", "key": "route", "threads": 4}, "echo x")
            self.assertEqual("export OT_SLIVER_BLOCK=1" in bodies[0], want)
            self.assertEqual("/r/src/physical/common_flow/$f" in bodies[0], want)
            self.assertIn("-e OT_SLIVER_BLOCK", bodies[0])         # the docker shim passes it into the flow container

    def test_orfs_patch_puts_sliver_before_lint(self):
        import sys
        sys.path.insert(0, str(HERE.parent))
        import orfs_hold_mm as om
        with tempfile.TemporaryDirectory() as t:
            u = Path(t) / "util.tcl"
            u.write_text("# util\n" + om.FPL_ANCHOR + "}\n")
            self.assertEqual(om.patch_fp_lint(Path(t)), "patched")
            self.assertEqual(om.patch_sliver_block(Path(t)), "patched")
            self.assertEqual(om.patch_sliver_block(Path(t)), "already patched")
            txt = u.read_text()
            self.assertLess(txt.index("OT_SLIVER_BLOCK"), txt.index("ot_fp_lint_flow"))


class ClassE(Base):
    def test_drt0073_pinko(self):
        sp = spec("q", stages=dict(route=dict(cmd="R={RUN} bash physical/hbm_accel_die_views/su/route_lane.sh {LABEL} top 1 2")))
        j = job("q", "NEEDS_HUMAN", spec=sp, reason="route crashed twice",
                crashes=[dict(tail="[ERROR DRT-0073] No access point for a2[50]")])
        git = MagicMock()
        git.show.return_value = 'PINKO=1: keepout\n[ "${PINKO:-0}" = 1 ]'
        with patch.object(cl.submit_lint, "Git", return_value=git):
            self.assertEqual(self.run_pass(j), [("q", "e:q-are")])
        self.assertTrue(self.drop("q-are")["stages"]["route"]["cmd"].startswith("export PINKO=1; "))

    def test_drt0073_no_knob(self):
        j = job("q", "NEEDS_HUMAN", reason="x", crashes=[dict(tail="DRT-0073")])
        self.assertEqual(self.run_pass(j), [("q", "none")])
        self.assertIn("DRT-0073 with no pin-variant knob", (self.tk / "hbm-phys-1010.log").read_text())


class Guards(Base):
    def test_once_per_finish_optout_sibling_age(self):
        j = job(metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        self.run_pass(j)
        self.assertEqual(cl.auto_react(cl.all_jobs()), [])                 # READY now; nothing to judge
        k = job("k", spec=spec("k", auto_react=False), metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        self.assertEqual(self.run_pass(k), [])
        self.assertEqual(cl.load_job("k")["status"], "NEEDS_RTL")
        s1 = job("s1", spec=spec("s1", block="bb"), metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        s2 = job("s2", "RUNNING", spec=spec("s2", block="bb"), finished_at=None)
        self.assertEqual(self.run_pass(s1, s2), [])
        old = job("o", spec=spec("o", block="ob"), finished_at="2026-10-01T00:00:00-07:00",
                  metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        self.assertEqual(self.run_pass(old), [])
        hist = job("h0", spec=spec("h0", block="hb"), finished_at=None, metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        self.assertEqual(self.run_pass(hist), [])

    def test_finish_stamps(self):
        j = job(finished_at=None)
        cl.finish(j, "NEEDS_RTL", "r", "t")
        self.assertTrue(j["finished_at"])


class ReadyNext(Base):
    def rn(self, element, specs):
        (self.tk / "READY_NEXT" / f"{element}.json").write_text(json.dumps(specs))

    def test_ingest_after_failure(self):
        self.rn("blk", [dict(spec("blk-v2"), after="blk"), dict(spec("blk-v3"), after="blk")])
        j = job("j", "NEEDS_RTL", metrics=dict(ss_ps=-200.0, ff_ps=5.0, drc=0))
        self.assertEqual(self.run_pass(j), [("j", "none:blk-v2")])
        s = self.drop("blk-v2")
        self.assertNotIn("after", s)
        self.assertIn("after j NEEDS_RTL", s["ready_next_from"])
        rest = json.loads((self.tk / "READY_NEXT" / "blk.json").read_text())
        self.assertEqual([x["name"] for x in rest], ["blk-v3"])
        self.assertTrue((self.tk / "READY_NEXT" / "done" / "blk.blk-v2.json").exists())
        self.assertIn("READY_NEXT ingested blk-v2", (self.tk / "hbm-phys-1010.log").read_text())
        # the dropped spec is pending intake: a second failure of the element does not ingest blk-v3
        k = job("blk-x", "NEEDS_RTL", spec=spec("blk-x"), metrics=dict(ss_ps=-200.0, ff_ps=5.0, drc=0))
        self.assertEqual(self.run_pass(k), [("blk-x", "none")])
        # once blk-v2 exists as a job and fails, blk-v3 goes and the file moves to done/
        (self.d / "drop" / "blk-v2.json").unlink()
        v2 = job("blk-v2", "EARLY_FAIL_SETUP", spec=spec("blk-v2"))
        self.assertEqual(self.run_pass(v2), [("blk-v2", "none:blk-v3")])
        self.assertFalse((self.tk / "READY_NEXT" / "blk.json").exists())
        self.assertEqual(len(list((self.tk / "READY_NEXT" / "done").glob("blk.2*.json"))), 1)

    def test_not_after_auto_react_or_with_live_job(self):
        self.rn("blk", [dict(spec("blk-v2"), after="blk")])
        j = job("j", metrics=dict(ss_ps=3.0, ff_ps=-5.0, drc=0))
        self.assertEqual(self.run_pass(j), [("j", "a:in-place")])
        self.assertIsNone(self.drop("blk-v2"))
        # a live job whose NAME carries the element prefix blocks the ingest
        self.rn("pre", [dict(spec("pre_v9", block="other"), after="pre_")])
        f = job("pre_a", "NEEDS_RTL", spec=spec("pre_a", block="b9"), metrics=dict(ss_ps=-200.0, ff_ps=5.0, drc=0))
        live = job("pre_b", "RUNNING", spec=spec("pre_b", block="b10"), finished_at=None)
        self.assertEqual(self.run_pass(f, live), [("pre_a", "none")])
        self.assertIsNone(self.drop("pre_v9"))

    def test_bad_files_logged_once(self):
        (self.tk / "READY_NEXT" / "bad.json").write_text("{not json")
        self.rn("bad2", [spec("x")])                       # no "after"
        self.rn("bad3", [dict(spec("a"), after="b")] * 3)  # > 2 specs
        with patch.object(cl, "log") as lg:
            self.assertEqual(cl.ready_next_files(), [])
            self.assertEqual(cl.ready_next_files(), [])
        self.assertEqual(sum("READY_NEXT" in str(c) for c in lg.call_args_list), 3)
        with patch.object(cl, "validate", return_value=["missing 'stages'"]):
            self.rn("bad4", [dict(spec("a"), after="b")])
            self.assertEqual(cl.ready_next_files(), [])


class HostDown(unittest.TestCase):
    def setUp(self):
        cl.HOST_DOWN.clear()
        for name in ("ledger", "log", "event"):
            p = patch.object(cl, name)
            p.start()
            self.addCleanup(p.stop)

    def test_state(self):
        cl.note_host("e2", False, now=1000.0)
        cl.note_host("e2", False, now=2000.0)
        self.assertEqual(cl.HOST_DOWN["e2"], 1000.0)
        self.assertFalse(cl.host_down("e2", now=2000.0))
        self.assertTrue(cl.host_down("e2", now=1000.0 + cl.HOST_DOWN_S + 1))
        cl.note_host("e2", True, now=5000.0)
        self.assertFalse(cl.host_down("e2", now=9e9))

    def test_requeue_running_route(self):
        t0 = time.time()
        cl.HOST_DOWN["e2"] = t0 - cl.HOST_DOWN_S - 60
        j = job("r", "RUNNING", host="e2", stage_key="route", stage_tag="route.a1", stage_idx=2, source_synced=True,
                resume=dict(x=1), btrack={"b1": dict(state="done"), "b2": dict(state="running")})
        self.assertTrue(cl.host_down_requeue(j, "route"))
        self.assertEqual((j["status"], j["host"], j["run"], j["stage_idx"], j["attempt"], j["source_synced"]),
                         ("QUEUED", None, None, 0, 2, False))
        self.assertNotIn("stage_tag", j)
        self.assertNotIn("resume", j)
        self.assertEqual(list(j["btrack"]), ["b1"])

    def test_short_outage_and_eco_wait(self):
        t0 = time.time()
        cl.HOST_DOWN["e2"] = t0 - 600
        self.assertFalse(cl.host_down_requeue(job("r", "RUNNING", host="e2"), "route"))
        cl.HOST_DOWN["e2"] = t0 - 2 * 3600
        e = job("e", "ECO", host="e2", eco=dict(tried=True))
        self.assertFalse(cl.host_down_requeue(e, "ECO"))
        cl.HOST_DOWN["e2"] = t0 - cl.HOST_DOWN_ECO_WAIT_S - 60
        self.assertTrue(cl.host_down_requeue(e, "ECO"))
        self.assertEqual(e["status"], "QUEUED")
        self.assertEqual(e["eco"], {})
        self.assertIn("abandoned", e["eco_history"][-1])
        self.assertFalse(cl.host_down_requeue(job("v", "READY", host="e2"), "verdict"))

    def test_poll_failure_notes_host(self):
        with patch.object(cl, "ssh", return_value=MagicMock(returncode=255, stdout="")):
            self.assertEqual(cl.poll_stage(dict(host="e9", run="/r", stage_tag="route.a1")), ("UNREACHABLE", None))
        self.assertIn("e9", cl.HOST_DOWN)
        with patch.object(cl, "ssh", return_value=MagicMock(returncode=0, stdout="RUNNING\n")):
            cl.poll_stage(dict(host="e9", run="/r", stage_tag="route.a1"))
        self.assertNotIn("e9", cl.HOST_DOWN)

    def test_choose_skips_down_host(self):
        f = cl.Fleet()
        hosts = [dict(name="a", cap=64, ram_gb=500), dict(name="b", cap=64, ram_gb=500)]
        cl.HOST_DOWN["a"] = time.time() - cl.HOST_DOWN_S - 60
        with patch.object(cl, "hosts_table", return_value=hosts), \
                patch.object(cl, "host_cfg", side_effect=lambda h: next(x for x in hosts if x["name"] == h)), \
                patch.object(f, "compatible", return_value=True), \
                patch.object(f, "probe", return_value=dict(load1=1.0, mem_gb=400)), \
                patch.object(f, "fits", return_value=(True, "")):
            self.assertEqual(f._choose(dict(threads=4, peak_ram_gb=8)), ("b", None))


if __name__ == "__main__":
    unittest.main()
