#!/usr/bin/env python3
"""WAVE-LONGRUN-1 11-15: fleet list, CPU-time liveness in REAP, adoption re-key / PENDING-PLAN holds, one live attempt per item,
retry of a reap stop that could not reach a host, orphan scopes of replaced attempts."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402
import wave_jobs as WJ  # noqa: E402

CUR, OLD = "a" * 40, "b" * 40
PP = ("PENDING-PLAN 11-15 (OWNER via COORD r50): this S81 type's kit inputs change under the pending plan: no new launch or retry "
      "until adoption. Running attempts finish. Lift = delete this key.")


class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self, active=(), bad_hosts=(), live=None, prog=None):
        self.active, self.bad, self.cmds, self.logs = set(active), set(bad_hosts), [], []
        self.live, self.prog = live or {}, prog or {}
        self.orphan_args = []

    def unit_active(self, u):
        return u in self.active

    def log(self, m):
        self.logs.append(m)

    def sh(self, cmd, timeout=0, input=None):
        self.cmds.append(cmd)
        host = next((h for h in self.bad if h in cmd), None)
        if host:
            return 255, "", "ssh: connect to host %s port 22: Connection timed out" % host
        if input and "# HUNG_PROBE" in input:
            return 0, json.dumps({"HUNG_PROBE": self.prog}) + "\n", ""
        if input and "me = str(os.getpid())" in input:
            return 0, json.dumps(self.live) + "\n", ""
        if input and "ORPHAN_SCAN" not in input and "orphans" in input:
            self.orphan_args.append(json.loads(__import__("ast").literal_eval(input.split("\n")[1].split(" = ",1)[1])[0]))
            return 0, json.dumps({"orphans": [{"unit": "oth-ubuntu-1-1", "why": "attempt 1 older", "age_h": 9.0}]}) + "\n", ""
        return 0, '{"containers": [], "scopes": []}\n', ""


def silent_row(d, name, age_min, log_age_min):
    jd = Path(d) / name
    jd.mkdir()
    (jd / "spec.json").write_text(json.dumps({"work": f"/srv/kw/{name}"}))
    lg = jd / "place.live.log"
    lg.write_text("x")
    old = time.time() - log_age_min * 60
    os.utime(lg, (old, old))
    t = time.time() - age_min * 60
    return dict(die="s81", item=name, kind="type", event="e", attempt=3, status="RUNNING", unit=f"u-{name}", dir=str(jd),
                started=t, updated=t, infra_base=0)


class Fleet(unittest.TestCase):
    def setUp(self):
        self.saved = list(WJ.FLEET)

    def tearDown(self):
        WJ.FLEET[:] = self.saved

    def test_fleet_default_names_the_live_hosts_not_retired_epyc4(self):
        for h in ("epyc7", "epyc8", "epyc9", "epyc10"):
            self.assertIn(h, WJ.FLEET)
        self.assertNotIn("epyc4", WJ.FLEET)

    def test_fleet_from_cfg_drops_retired_and_localhost(self):
        cfg = {"hosts": ["epyc8", "epyc4", "localhost"], "retired_hosts": ["epyc4"], "place_prefer": ["epyc9"],
               "dies": {"s81": {"gen_hosts": ["epyc7", "epyc4"], "hosts": ["epyc10"]}}}
        got = WJ.fleet_from_cfg(cfg, "intel2")
        self.assertEqual(sorted(got), ["epyc10", "epyc7", "epyc8", "epyc9", "intel2"])
        WJ.set_fleet(got)
        self.assertEqual(WJ.FLEET, got)                       # replaced in place: WJ.FLEET readers see it

    def test_empty_config_keeps_default(self):
        self.assertEqual(WJ.fleet_from_cfg({}, "intel2"), list(WJ.FLEET))


class Liveness(unittest.TestCase):
    def setUp(self):
        self.saved = list(WJ.FLEET)
        WJ.set_fleet(["intel2", "epyc9", "epyc4"])

    def tearDown(self):
        WJ.FLEET[:] = self.saved

    def test_one_unreadable_host_does_not_blank_the_probe(self):
        ap = AP(bad_hosts=["epyc4"], live={"/srv/kw/a": [11]})
        got = KW.live_on_fleet(ap, ["/srv/kw/a", "/srv/kw/b"])
        self.assertIsNotNone(got)
        self.assertEqual(got.unreadable, ("epyc4",))
        self.assertTrue(got["/srv/kw/a"])
        self.assertFalse(got.get("/srv/kw/b"))
        self.assertIsNone(KW.live_on_fleet(AP(bad_hosts=["intel2", "epyc9", "epyc4"]), ["/srv/kw/a"], ["epyc9", "epyc4"]))

    def test_not_found_with_an_unreadable_host_is_reported_not_reaped(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": silent_row(d, "a", 900, 600)}}
            ap = AP(active={"u-a"}, bad_hosts=["epyc4"])
            self.assertEqual(KW.reap_dead(ap, {"dies": {"s81": {"event": "e"}}}, st, {}), 0)
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")
            self.assertTrue(any("SILENT" in m and "unreadable: epyc4" in m for m in ap.logs), ap.logs)
            ap = AP(active={"u-a"})                           # every host read, nothing names the root: a zombie, R2
            self.assertEqual(KW.reap_dead(ap, {"dies": {"s81": {"event": "e"}}}, st, {}), 1)
            self.assertIn("REAP-DEAD R2", st["items"]["a"]["reason"])

    def test_cpu_liveness_reaps_flat_cpu_and_spares_a_busy_unit(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {"dies": {"s81": {"event": "e"}}}
            roots = {"a": "/srv/kw/a", "b": "/srv/kw/b"}
            st = {"items": {k: silent_row(d, k, 300, 100) for k in roots}}
            now = time.time()
            ap = AP(active={"u-a", "u-b"}, live={r: [7] for r in roots.values()},
                    prog={"/srv/kw/a": {"log": 0, "cpu": 40.0, "pids": 3, "containers": []},
                          "/srv/kw/b": {"log": 0, "cpu": 40.0, "pids": 3, "containers": []}})
            self.assertEqual(KW.reap_dead(ap, cfg, st, {}, now=now), 0)          # first sight: marks only
            ap.prog["/srv/kw/b"]["cpu"] = 400.0                                  # b keeps burning CPU
            ap.prog["/srv/kw/a"]["cpu"] = 41.0                                   # a: ~0 growth
            self.assertEqual(KW.reap_dead(ap, cfg, st, {}, now=now + 31 * 60), 1)
            self.assertEqual((st["items"]["a"]["status"], st["items"]["a"]["class"]), ("CANCELLED", "HUNG"))
            self.assertIn("DEAD", st["items"]["a"]["reason"] + " ".join(ap.logs))
            self.assertEqual(st["items"]["b"]["status"], "RUNNING")

    def test_hung_judge_dead_window_is_off_without_dead_min(self):
        prog = {"cpu": 10.0, "log": 0}
        h0, w, _ = KW.hung_judge({}, prog, 0, 1000.0, 120)
        h1, _, _ = KW.hung_judge(w, prog, 0, 1000.0 + 3600, 120)
        self.assertFalse(h1)                                  # 60 min < 120: old behaviour
        _, w2, _ = KW.hung_judge({}, prog, 0, 1000.0, 120, dead_min=30)
        h2, _, why = KW.hung_judge(w2, prog, 0, 1000.0 + 1900, 120, dead_min=30)
        self.assertTrue(h2)
        self.assertIn("DEAD", why)


class Adoption(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.stops = []

        def sh(cmd, timeout=None, input=None):
            if input:
                return 0, json.dumps({"containers": [], "scopes": []}), ""
            self.stops.append(cmd[-1])
            return 0, "", ""
        self.AP = type("AP", (), {"DRY": False, "log": self.logs.append, "sh": staticmethod(sh), "HUB_NAME": "intel2"})()
        self.t = Path(tempfile.mkdtemp())
        self.cfg = {"dies": {"d": {"plan": "/p.json", "event": "new", "gen_host": "h",
                                   "hold_items": {"old1": PP, "old2": PP + " | FABLE stop list: running attempts in route finish",
                                                  "keep": PP}}}}
        k = KW.item_key
        self.st = {"plans": {"h:/p.json|new": {"blocks": {"old1": CUR, "old2": CUR, "keep": CUR, "same": CUR}}},
                   "items": {
                       k("d", "new", "old1", OLD): dict(die="d", item="old1", event="oldev", attempt=3, status="RUNNING", unit="u1", block_sha=OLD, stage="place"),
                       k("d", "new", "old2", OLD): dict(die="d", item="old2", event="oldev", attempt=3, status="RUNNING", unit="u2", block_sha=OLD, stage="place"),
                       k("d", "new", "keep", OLD): dict(die="d", item="keep", event="new", attempt=3, status="RUNNING", unit="u3", block_sha=OLD, stage="place"),
                       k("d", "new", "same", CUR): dict(die="d", item="same", event="oldev", attempt=3, status="RUNNING", unit="u4", block_sha=CUR),
                   }}

    def test_pending_plan_hold_protects_by_default(self):
        self.assertEqual(KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t), 0)

    def test_after_adoption_pending_plan_alone_no_longer_protects_old_event_rows(self):
        self.cfg["supersede_pending_plan_holds"] = True
        n = KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t)
        it = self.st["items"]
        self.assertEqual(n, 1)
        self.assertEqual(it[KW.item_key("d", "new", "old1", OLD)]["status"], "CANCELLED")
        self.assertEqual(it[KW.item_key("d", "new", "old2", OLD)]["status"], "RUNNING")     # another clause says running attempts finish
        self.assertEqual(it[KW.item_key("d", "new", "keep", OLD)]["status"], "RUNNING")     # launched on the CURRENT event: still held
        self.assertEqual(it[KW.item_key("d", "new", "same", CUR)]["status"], "RUNNING")     # block unchanged: never cancelled

    def test_rekey_marks_unchanged_live_rows_once(self):
        self.assertEqual(KW.rekey_adopted(self.AP, self.cfg, self.st), 1)
        r = self.st["items"][KW.item_key("d", "new", "same", CUR)]
        self.assertEqual((r["event"], r["event_adopted"]), ("oldev", "new"))
        self.assertEqual(KW.rekey_adopted(self.AP, self.cfg, self.st), 0)
        self.assertEqual(sum("REKEY" in m for m in self.logs), 1)


class OneLiveAttempt(unittest.TestCase):
    def test_live_attempt_elsewhere(self):
        k = KW.item_key
        st = {"items": {k("d", "e", "t", CUR): dict(die="d", item="t", status="FAIL"),
                        k("d", "e", "t", OLD): dict(die="d", item="t", status="RUNNING", attempt=4),
                        k("d", "e", "u", OLD): dict(die="d", item="u", status="ENQUEUED", q_status="RUNNING", attempt=2),
                        k("d", "e", "v", OLD): dict(die="d", item="v", status="ENQUEUED", q_status="QUEUED"),
                        k("d", "e", "w", OLD): dict(die="d", item="w", status="CANCELLED")}}
        self.assertEqual(KW.live_attempt_elsewhere(st, "d", "t", k("d", "e", "t", CUR))["attempt"], 4)
        self.assertIsNone(KW.live_attempt_elsewhere(st, "d", "t", k("d", "e", "t", OLD)))     # that row IS the key
        self.assertEqual(KW.live_attempt_elsewhere(st, "d", "u", k("d", "e", "u", CUR))["attempt"], 2)
        self.assertIsNone(KW.live_attempt_elsewhere(st, "d", "v", k("d", "e", "v", CUR)))     # queued, no compute
        self.assertIsNone(KW.live_attempt_elsewhere(st, "d", "w", k("d", "e", "w", CUR)))

    def test_launch_refuses_while_another_block_runs(self):
        logs = []
        ap = type("AP", (), {"DRY": False, "log": logs.append, "sh": staticmethod(lambda *a, **k: (0, "", "")),
                             "AP_DIR": tempfile.mkdtemp(), "HUB_NAME": "intel2"})()
        cfg = {"dies": {"d": {"event": "e"}}}
        st = {"items": {KW.item_key("d", "e", "t", OLD): dict(die="d", item="t", status="RUNNING", attempt=4, unit="kw-x")}}
        saved = KW.scheduler_current
        KW.scheduler_current = lambda AP: True
        try:
            self.assertIsNone(KW.launch(ap, cfg, st, "d", {"item": "t", "kind": "type", "block_sha": CUR}, "intel2"))
        finally:
            KW.scheduler_current = saved
        self.assertTrue(any("one live attempt per item" in m for m in logs), logs)
        self.assertEqual(len(st["items"]), 1)


class ReapRetry(unittest.TestCase):
    def setUp(self):
        self.saved = list(WJ.FLEET)
        WJ.set_fleet(["intel2", "epyc9"])

    def tearDown(self):
        WJ.FLEET[:] = self.saved

    def test_stop_that_missed_a_host_is_retried_next_tick(self):
        with tempfile.TemporaryDirectory() as d:
            r = silent_row(d, "a", 30, 1)
            r.update(status="CANCELLED", updated=time.time(), kit="epyc9:/srv/kw/a")
            st = {"items": {"k": r}}
            ap = AP(bad_hosts=["epyc9"])
            KW.reap_stale_attempts(ap, {}, st, {}, d)
            self.assertNotIn("reaped", r)                      # epyc9 unreachable: not marked done
            self.assertTrue(any("epyc9 not checked" in m for m in ap.logs))
            ap = AP()
            KW.reap_stale_attempts(ap, {}, st, {}, d)
            self.assertIn("reaped", r)
            ap3 = AP()
            KW.reap_stale_attempts(ap3, {}, st, {}, d)         # done: not repeated
            self.assertFalse(any("KIT-WAVE REAP " in m for m in ap3.logs))


class Orphans(unittest.TestCase):
    def setUp(self):
        self.saved = list(WJ.FLEET)
        WJ.set_fleet(["epyc9"])

    def tearDown(self):
        WJ.FLEET[:] = self.saved

    def test_scan_script_compiles(self):
        compile(WJ.ORPHAN_SCAN, "ORPHAN_SCAN", "exec")

    def test_recent_rows_include_single_attempt_rows(self):
        now = time.time()
        st = {"items": {"x": dict(die="d", event="e", item="t", attempt=1, started=now - 100, status="FAIL"),
                        "y": dict(die="d", event="e", item="t", attempt=2, started=now - 50, status="RUNNING"),
                        "z": dict(die="d", event="e", item="u", attempt=1, started=now - 50, status="RUNNING"),
                        "o": dict(die="d", event="e", item="v", attempt=1, started=now - 99 * 3600, status="FAIL"),
                        "p": dict(die="d", event="e", item="v", attempt=2, started=now - 98 * 3600, status="FAIL")}}
        self.assertEqual(sorted(KW.orphan_rows(st, now)), ["d|e|t", "d|e|u"])         # FABLE-FLOW-0800 B: a FAIL row alone can own an orphan scope; rows older than the window are out

    def test_sweep_logs_would_stop_by_default_and_stops_when_live(self):
        now = time.time()
        st = {"items": {"x": dict(die="d", event="e", item="t", attempt=1, started=now - 100, status="FAIL"),
                        "y": dict(die="d", event="e", item="t", attempt=2, started=now - 50, status="RUNNING")}}
        ap = AP()
        self.assertEqual(KW.orphan_sweep(ap, {"orphan_sweep_live": False}, st), 1)        # the stop is enforced by default since 11-17; false = log only
        self.assertTrue(any("would stop" in m for m in ap.logs))
        self.assertTrue(ap.orphan_args[-1]["dry"])
        ap = AP()
        KW.orphan_sweep(ap, {}, st)
        self.assertFalse(ap.orphan_args[-1]["dry"])
        self.assertTrue(any("stopped" in m for m in ap.logs))
        self.assertEqual(KW.orphan_sweep(AP(), {"orphan_sweep": False}, st), 0)


if __name__ == "__main__":
    unittest.main()
