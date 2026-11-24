"""FLOW-21 11-01 (COORD 08:2x): kit-wave PLACE as a detached service released by the fresh PLACE receipt while the
async pre-route LEC proof owner keeps running; terminal rc / lost client / resume / sync fallback"""
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import kit_wave as KW

# FLEET-WATCH-R8 11-21: run_item re-picks the spec hosts from the LIVE ~/coord kit_wave.json gen_hosts (repick_stage_hosts); the fixture hosts must not depend on it
# KW-REPICK-PIN 11-24: patched for this module only (a module-level assignment replaced it for every later test in the process: test_repick_hosts failed)
_REPICK_PATCH = patch.object(KW, "repick_stage_hosts", lambda sp, cfg_path=None, **_kw: sp)


def setUpModule():
    _REPICK_PATCH.start()


def tearDownModule():
    _REPICK_PATCH.stop()

RECEIPT = {"path": "/w/gen/T/physical_completion/dpkit-T-1.json", "run_id": "dpkit-T-1", "proof_owner": "dpkit-T-1",
           "proof_pending": True, "checkpoint": {"path": "run/results/asap7/x/base/3_place.odb", "size": 9, "mtime_ns": 1}}


class Fake:
    def __init__(self, d, async_ok=True, receipt=True, client_rc=None, active=True):
        self.d, self.calls = Path(d), []
        self.async_ok, self.receipt, self.client_rc, self.active = async_ok, receipt, client_rc, active

    def __call__(self, argv, **kw):
        s = " ".join(argv)
        self.calls.append(s)
        out, rc = "", 0
        if "KW_GEOM_TOOLS_OK" in s:
            out = re.search(r"KW_GEOM_TOOLS_OK [0-9a-f]{16}", s).group(0) + "\n"
        elif "KW_ASYNC_OK" in s:
            out = "KW_ASYNC_OK\n" if self.async_ok else "KW_ASYNC_NO\n"
        elif argv[0] == "systemd-run":
            if self.client_rc is not None:
                (self.d / "place.live.log").write_text(f"KW_PLACE_START 1 u\nKW_PLACE_RC={self.client_rc}\n")
        elif argv[:3] == ["systemctl", "--user", "is-active"]:
            out = "active\n" if self.active else "inactive\n"
        elif "KW_PLACE_RECEIPT" in s or "physical_completion" in s:
            out = ("KW_PLACE_RECEIPT " + json.dumps(RECEIPT) + "\n") if self.receipt else ""
        elif "run_kit.sh" in s:
            out = "ot-run: RAN on epyc2 (unit oth-1): exit 0\n"
        elif "3_place.odb" in s:
            out = "/w/gen/T/run/results/asap7/x/base/3_place.odb\nNumber of cells: 1000\n" + ("LAYOUT_PNG\n" if "layout_review" in s else "")
        elif "layout_review" in s:                     # KW-FIX-45 required place render (place_render_probe)
            out = "LAYOUT_PNG\n"
        elif "geom_check.sh" in s:
            out = "AP_AUTO_GEOM AUTO-GEOM PASS T fill=ok(0.5)\n"
        return SimpleNamespace(returncode=rc, stdout=out, stderr="")


def spec(d, gen_host="intel1"):
    sp = {"die": "s81", "item": "T", "event": "e", "plan": "/p/plan.json", "gen_host": gen_host, "src": "/src",
          "root": "/w0", "work": "/w", "kit_rtl": {}, "gen_args": [], "preflight_args": [], "hosts": ["intel1", "intel2", "epyc2"],
          "hub": "intel2", "place_prefer": [], "place_mem_gb": 48, "place_threads": 8, "geom_mem_gb": 24,
          "gen_mem_gb": 16, "bind_mem_gb": 24, "ot_run": "ot-run"}
    p = Path(d) / "spec.json"
    p.write_text(json.dumps(sp))
    return p


class PlaceAsync(unittest.TestCase):
    def go(self, d, fake, gen_host="intel1"):
        real, poll = KW.subprocess.run, KW.PLACE_POLL_S
        KW.subprocess.run, KW.PLACE_POLL_S = fake, 0
        try:
            rc = KW.run_item(spec(d, gen_host))
        finally:
            KW.subprocess.run, KW.PLACE_POLL_S = real, poll
        return rc, json.loads((Path(d) / "result.json").read_text())

    def test_receipt_releases_worker_while_proof_runs(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(d)
            rc, res = self.go(d, f)
            self.assertEqual((rc, res["verdict"]), (0, "PASS"))
            self.assertEqual(res["ran_on"], "intel1")
            self.assertEqual(res["place_receipt"]["proof_owner"], "dpkit-T-1")
            run = [c for c in f.calls if c.startswith("systemd-run")]
            self.assertEqual(len(run), 1)
            # KW-FIX-4 11-03: unpinned + staged kit/runner, so ot-run may SPILL it (outputs copied back to the gen host)
            self.assertNotIn("--hosts", run[0])
            self.assertIn("--dir /w/gen/T --stage /w/gen/T --stage /w/gen/run_kit.sh ", run[0])
            self.assertIn(" place 48 8", run[0])
            self.assertFalse([c for c in f.calls if "rsync" in c and ("epyc2:" in c or "pull" in c)])
            self.assertFalse([c for c in f.calls if "ssh -o BatchMode=yes -o ControlPath=none intel1 rm" in c])
            svc = json.loads((Path(d) / "place_service.json").read_text())
            self.assertEqual((svc["launch"], svc["receipt"]["run_id"]), ("launched", "dpkit-T-1"))
            # GEOM ran after the receipt, on the gen host copy
            self.assertTrue(any("geom_check.sh" in c for c in f.calls))

    def test_event_env_reaches_detached_place(self):
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ", {"OT_RUN_EVENT_ENV": "events/c9.env"}):
            f = Fake(d)
            rc, _ = self.go(d, f)

        self.assertEqual(rc, 0)
        run = [c for c in f.calls if c.startswith("systemd-run")]
        self.assertEqual(len(run), 1)
        self.assertIn(f"--setenv=OT_RUN_EVENT_ENV={Path.cwd() / 'events/c9.env'}", run[0])

    def test_private_place_stops_before_geometry_probe(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(d)
            p = spec(d)
            sp = json.loads(p.read_text())
            sp.update(private={"wave_env": {}}, goal="place")
            p.write_text(json.dumps(sp))
            with patch.object(KW, "private_spec_stale", return_value=""), patch.object(KW, "PLACE_POLL_S", 0), patch.object(KW.subprocess, "run", f):
                rc = KW.run_item(p)
            res = json.loads((Path(d) / "result.json").read_text())
            self.assertEqual((rc, res["verdict"], res["stage"]), (0, "PASS", "place"))
            self.assertEqual(res["evidence"], "intel1:/w/gen/T/run/results/asap7/x/base/3_place.odb")
            self.assertFalse(any("geom_check.sh" in c or "signoff_chain" in c for c in f.calls))

    def test_place_spill_false_keeps_gen_host_pin(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(d)
            real, poll = KW.subprocess.run, KW.PLACE_POLL_S
            KW.subprocess.run, KW.PLACE_POLL_S = f, 0
            try:
                p = spec(d)
                sp = json.loads(p.read_text()); sp["place_spill"] = False; p.write_text(json.dumps(sp))
                rc = KW.run_item(p)
            finally:
                KW.subprocess.run, KW.PLACE_POLL_S = real, poll
            run = [c for c in f.calls if c.startswith("systemd-run")]
            self.assertEqual(rc, 0)
            self.assertIn("--hosts intel1 ", run[0])
            self.assertNotIn("--stage", run[0])

    def test_terminal_client_rc_is_the_place_result(self):
        with tempfile.TemporaryDirectory() as d:
            rc, res = self.go(d, Fake(d, receipt=False, client_rc=5))
            self.assertEqual((rc, res["verdict"], res["stage"]), (1, "FAIL", "place"))

    def test_lost_client_fails_without_duplicate_launch(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(d, receipt=False, active=False)
            rc, res = self.go(d, f)
            self.assertEqual(res["verdict"], "FAIL")
            self.assertIn("KW_PLACE_LOST", res["tail"])
            self.assertEqual(len([c for c in f.calls if c.startswith("systemd-run")]), 1)

    def test_restarted_worker_resumes_without_destructive_prep(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "place_service.json").write_text(json.dumps(
                {"unit": "kwp-x", "argv": ["ot-run"], "kit": "/w/gen/T", "host": "intel1", "started": 1.0,
                 "log": str(Path(d) / "place.live.log"), "launch": "launched"}))
            f = Fake(d)
            rc, res = self.go(d, f)
            self.assertEqual(res["verdict"], "PASS")
            self.assertFalse([c for c in f.calls if "rm -rf" in c or "gen.py" in c or c.startswith("systemd-run")])

    def test_runner_without_phase_receipts_keeps_sync_place(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(d, async_ok=False)
            rc, res = self.go(d, f)
            self.assertEqual(res["verdict"], "PASS")
            self.assertFalse([c for c in f.calls if c.startswith("systemd-run")])
            self.assertTrue(any(c.startswith("ot-run") and "run_kit.sh" in c and " place " in c for c in f.calls))
            self.assertFalse(res["place_async"])


class CancelVolume(unittest.TestCase):
    def test_cancel_also_stops_waiting_place_service(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "place_service.json").write_text(json.dumps({"unit": "kwp-abc"}))
            calls = []
            AP = SimpleNamespace(DRY=False, sh=lambda argv, timeout=None: calls.append(argv) or (0, "", ""),
                                 log=lambda *a: None)
            cfg = {"dies": {"s81": {"pilot_queue": True}}}
            st = {"items": {"p": {"die": "s81", "item": "A", "status": "FAIL", "class": "PLAN", "updated": 10.0},
                            "v": {"die": "s81", "item": "B", "status": "RUNNING", "volume": "C", "started": 1.0,
                                  "unit": "kw-b", "dir": d}}}
            real = (KW.pilot_queue_mode, KW.pilot_classes_state, KW.pilot_key)
            KW.pilot_queue_mode = lambda dd, c=None: True
            KW.pilot_classes_state = lambda dd, die, s: (set(), None)
            KW.pilot_key = lambda dd, die, item, kind="type": "C"
            try:
                n = KW.cancel_class_volume(AP, cfg, st, {})
            finally:
                KW.pilot_queue_mode, KW.pilot_classes_state, KW.pilot_key = real
            self.assertEqual(n, 1)
            self.assertIn(["systemctl", "--user", "stop", "kwp-abc"], calls)


if __name__ == "__main__":
    unittest.main()
