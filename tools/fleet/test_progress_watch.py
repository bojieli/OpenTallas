from pathlib import Path
import pathlib
import sys
import unittest
from datetime import datetime as D

H = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import progress_watch as P

LOG = H / "test_data" / "progress_watch_log_1119.txt"  # the 11-19 kit-wave lines, trimmed (launches kept once per die-minute)


def lines():
    return LOG.read_text().split("\n")


class Replay(unittest.TestCase):
    def test_s81_no_progress_at_1552_and_self_stop_at_1751(self):
        out = P.replay(lines(), D(2026, 11, 19, 15, 30), D(2026, 11, 19, 18, 5), 1)
        np = [t for t, f in out if f["cls"] == "NO-PROGRESS" and f["die"] == "s81"]
        self.assertTrue(np and D(2026, 11, 19, 15, 52) <= np[0] <= D(2026, 11, 19, 15, 54), np[:2])
        ss = [(t, f) for t, f in out if f["cls"] == "SELF-STOP"]
        self.assertTrue(any(D(2026, 11, 19, 17, 51) <= t <= D(2026, 11, 19, 17, 56) for t, f in ss), [t for t, _ in ss])
        # s81 is re-alerted at most once an hour, not every minute
        self.assertTrue(all((b - a).total_seconds() >= 3600 for a, b in zip(np, np[1:])))

    def test_hbm_is_parked_not_alerted(self):
        out = P.replay(lines(), D(2026, 11, 19, 18, 25), D(2026, 11, 19, 19, 50), 5)
        self.assertTrue(any(f["die"] == "hbm" and f["cls"] == "PARKED" for _, f in out))
        self.assertFalse(any(f["die"] == "hbm" and f["state"] == "alert" for _, f in out))


class Rules(unittest.TestCase):
    def ev(self, *ls):
        return P.parse_lines(list(ls))

    def test_eligible_zero_means_no_alert(self):
        e = self.ev("2026-11-19 10:00:00 PST AUTOPILOT: KIT-WAVE LAUNCH s81/a (type, 1 replicas)")
        now = D(2026, 11, 19, 12, 0)
        self.assertTrue(P.detect(e, now))
        self.assertFalse([f for f in P.detect(e, now, {"eligible": {"s81": 0}}) if f["cls"] == "NO-PROGRESS"])
        f = [f for f in P.detect(e, now, {"eligible": {"s81": 4}}) if f["cls"] == "NO-PROGRESS"]
        self.assertIn("4 candidate rows before launch checks", f[0]["text"])

    def test_reports_recent_disk_admission_without_certifying_candidates(self):
        launch = "2026-11-21 07:41:00 PST AUTOPILOT: KIT-WAVE LAUNCH s81_head/old (type, 1 replicas)"
        disk = ("2026-11-21 17:05:33 PST AUTOPILOT: KIT-WAVE LAUNCH-DISK-CAP s81_head/hd_host_e: "
                "disk cap: epyc7: in flight 108 + 9 GB > free 168 - 150")
        events = self.ev(launch, disk)
        state = {"eligible": {"s81_head": 17}}
        message, = P.detect(events, D(2026, 11, 21, 17, 10), state)
        self.assertIn("17 candidate rows before launch checks", message["text"])
        self.assertIn("disk admission blocked hd_host_e", message["text"])
        self.assertIn("epyc7: in flight 108 + 9 GB > free 168 - 150", message["text"])
        later, = P.detect(events, D(2026, 11, 21, 17, 31), state)
        self.assertNotIn("disk admission blocked", later["text"])

    def test_disk_evidence_outlasts_no_launch_count(self):
        launch = "2026-11-21 11:46:00 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_compute/old (type, 1 replicas)"
        disk = ("2026-11-21 17:40:42 PST AUTOPILOT: KIT-WAVE LAUNCH-DISK-CAP qwen_compute/cbf_q00__cl1b5a6458: "
                "disk cap: epyc8: in flight 45 + 9 GB > free 126 - 150")
        blocked = "2026-11-21 17:40:42 PST AUTOPILOT: KIT-WAVE NO-LAUNCH qwen_compute: 19 eligible rows"
        events = self.ev(launch, disk, blocked)
        state = {"eligible": {"qwen_compute": 5}}
        message, = P.detect(events, D(2026, 11, 21, 17, 56), state)
        self.assertIn("5 candidate rows before launch checks", message["text"])
        self.assertIn("disk admission blocked cbf_q00__cl1b5a6458", message["text"])
        expired, = P.detect(events, D(2026, 11, 21, 18, 5, 43), state)
        self.assertNotIn("disk admission blocked", expired["text"])

    def test_self_stop_needs_same_job_within_30_min(self):
        sub = "2026-11-19 10:00:00 PST AUTOPILOT: SUBMIT aaaaaaaaaaaa qwen_compute/x /p"
        rp = "KIT-WAVE REAP qwen_compute/x@2: superseded by attempt 2 of the same item; units ['ap-aaaaaaaaaaaa-a1']"
        near = self.ev(sub, "2026-11-19 10:20:00 PST AUTOPILOT: " + rp)
        far = self.ev(sub, "2026-11-19 11:20:00 PST AUTOPILOT: " + rp)
        now = D(2026, 11, 19, 10, 30)
        self.assertEqual([f["cls"] for f in P.detect(near, now) if f["cls"] == "SELF-STOP"], ["SELF-STOP"])
        self.assertFalse([f for f in P.detect(far, D(2026, 11, 19, 11, 30)) if f["cls"] == "SELF-STOP"])

    def test_no_advance_two_fails_same_stage(self):
        f = "2026-11-19 10:%02d:00 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/it PLAN: x @place: y"
        e = self.ev(f % 0, f % 30)
        self.assertEqual([x["cls"] for x in P.detect(e, D(2026, 11, 19, 10, 40)) if x["cls"] == "NO-ADVANCE"], ["NO-ADVANCE"])
        # a changed input digest between the attempts is not a repeat
        la = "2026-11-19 10:%02d:00 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_compute/it (type, 1 replicas) event-key k%d plan p.json@sha%d src s unit u"
        e2 = self.ev(la % (0, 1, 1), f % 1, la % (20, 2, 2), f % 30)
        self.assertFalse([x for x in P.detect(e2, D(2026, 11, 19, 10, 40)) if x["cls"] == "NO-ADVANCE"])
        e3 = self.ev(la % (0, 1, 1), f % 1, la % (20, 1, 1), f % 30)
        self.assertTrue([x for x in P.detect(e3, D(2026, 11, 19, 10, 40)) if x["cls"] == "NO-ADVANCE"])
        # live: an item with no current-plan row in the stages tsv is ignored
        rows = [{"die": "s81", "item": "z", "plan_current": "yes", "status": "RUNNING"}]
        self.assertFalse([x for x in P.detect(e, D(2026, 11, 19, 10, 40), {"rows": rows}) if x["cls"] == "NO-ADVANCE"])
        g = "2026-11-19 10:30:00 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/it PLAN: x @route: y"
        self.assertFalse([x for x in P.detect(self.ev(f % 0, g), D(2026, 11, 19, 10, 40)) if x["cls"] == "NO-ADVANCE"])

    def test_stuck_state_needs_no_successor(self):
        row = {"die": "s81", "item": "i", "status": "CANCELLED", "class": "SUPERSEDED", "plan_current": "yes", "updated": "2026-11-19 09:00"}
        now = D(2026, 11, 19, 10, 30)
        self.assertEqual(len([f for f in P.detect([], now, {"rows": [row]}) if f["cls"] == "STUCK-STATE"]), 1)
        succ = dict(row, status="RUNNING", **{"class": ""})
        self.assertFalse([f for f in P.detect([], now, {"rows": [row, succ]}) if f["cls"] == "STUCK-STATE"])
        self.assertFalse([f for f in P.detect([], D(2026, 11, 19, 9, 30), {"rows": [row]}) if f["cls"] == "STUCK-STATE"])

    def test_pending_event_needs_matching_live_config_and_wave_marker(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ap = Path(tmp) / "autopilot"
            ap.mkdir()
            (ap / "kit_wave_stages.tsv").write_text("die\titem\tstatus\n")
            (ap / "kit_wave.json").write_text(json.dumps({"dies": {
                "s81": {"event": "j8"},
                "qwen_kvsys": {"event_pending": {"event": "d29"}},
                "s81_head": {"event_pending": {"event": "r18"}},
                "qwen_compute": {"event_pending": {"event": "v4"}},
            }}))
            (ap / "kit_wave_state.json").write_text(json.dumps({"event_pending_log": {
                "s81": "wait:j8",
                "qwen_kvsys": "wait:d29",
                "s81_head": "wait:r17",
                "qwen_compute": "expired:v4",
            }}))
            self.assertEqual(P.load_state(tmp).get("pending_event"), {"qwen_kvsys": "d29"})

    def test_signed_and_deferred_rows_are_not_stuck(self):
        """FLOW-FIX-2045: a CANCELLED/SUPERSEDED row of a type signed on that event, or retired by OWNER r711 (resign-defer), is terminal / waiting on purpose, not stuck"""
        import csv, json, tempfile
        d = Path(tempfile.mkdtemp()); ap = d / "autopilot"; ap.mkdir()
        (ap / "kit_wave.json").write_text(json.dumps({"dies": {"s81": {}}}))
        cols = ("die", "item", "event", "status", "class", "plan_current", "updated", "block_sha")
        rows = [dict(die="s81", item=i, event="E", status="CANCELLED", **{"class": "SUPERSEDED"}, plan_current="yes", updated="2026-11-19 09:00", block_sha="b") for i in ("signed", "deferred", "stuck")]
        with open(ap / "kit_wave_stages.tsv", "w", newline="") as f:
            w = csv.DictWriter(f, cols, delimiter="\t"); w.writeheader(); w.writerows(rows)
        (ap / "kit_wave_state.json").write_text(json.dumps({"items": {
            "a": {"die": "s81", "item": "signed", "event": "E", "q_status": "SIGNED"},
            "b": {"die": "s81", "item": "deferred", "event": "E", "retire": "resign-defer"}}}))
        st = P.load_state(d)
        out = [f for f in P.detect([], D(2026, 11, 19, 10, 30), st) if f["cls"] == "STUCK-STATE"]
        self.assertEqual(len(out), 1); self.assertIn("1 current-plan row", out[0]["text"]); self.assertIn("stuck", out[0]["text"])

    def test_configured_launch_holds_suppress_stuck_until_removed(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ap = Path(tmp) / "autopilot"
            ap.mkdir()
            config = ap / "kit_wave.json"
            def configure(holds):
                config.write_text(json.dumps({"dies": {
                    "qwen_compute": {"hold_items": holds, "route_hold_items": {"open": "route review"}},
                }}))
            (ap / "kit_wave_stages.tsv").write_text(
                "die\titem\tstatus\tclass\tplan_current\tupdated\n"
                + "".join(f"qwen_compute\t{item}\tCANCELLED\tSUPERSEDED\tyes\t2026-11-19 09:00\n"
                          for item in ("exact", "hc3_sibling", "open"))
            )
            configure({"exact": "owner=QC eta=2026-11-19 09:30", "hc3_*": "new form needed"})
            state = P.load_state(tmp)
            self.assertEqual(state["eligible"], {"qwen_compute": 1})
            findings = P.detect([], D(2026, 11, 19, 10, 30), state)
            stuck = next(f for f in findings if f["cls"] == "STUCK-STATE")
            self.assertIn("1 current-plan row", stuck["text"])
            self.assertIn("open", stuck["text"])

            configure({})
            state = P.load_state(tmp)
            self.assertEqual(state["eligible"], {"qwen_compute": 3})
            findings = P.detect([], D(2026, 11, 19, 10, 30), state)
            stuck = next(f for f in findings if f["cls"] == "STUCK-STATE")
            self.assertIn("3 current-plan row", stuck["text"])

    def test_design_watchdog_cancellations_are_not_launch_candidates(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ap = Path(tmp) / "autopilot"
            ap.mkdir()
            (ap / "kit_wave.json").write_text(json.dumps({"dies": {"qwen_kvsys": {}, "s81": {}}}))
            (ap / "kit_wave_stages.tsv").write_text(
                "die\titem\tstatus\tclass\tplan_current\treason\n"
                "qwen_kvsys\thgi\tCANCELLED\tQUEUE-CANCELLED\tyes\t"
                "queue job abcd cancelled: cancelled by DESIGN-FAIL watchdog at 2026-11-23 07:00:04 "
                "(not an OOM kill): CANCEL-DESIGN: GRT-LABEL DESIGN-FAIL: overflow 4392\n"
                "s81\tleaf\tCANCELLED\tQUEUE-CANCELLED\tyes\tqueue job efgh cancelled: host drain\n"
            )
            state = P.load_state(tmp)
        self.assertEqual(state["eligible"], {"qwen_kvsys": 0, "s81": 1})
        alerts = P.detect([], D(2026, 11, 23, 8, 18), state)
        self.assertEqual([row["die"] for row in alerts if row["cls"] == "NO-PROGRESS"], ["s81"])

    def test_dedup_one_per_die_class_hour(self):
        f = [{"die": "s81", "cls": "NO-PROGRESS", "state": "alert", "text": "t"}]
        now = D(2026, 11, 19, 12, 0)
        self.assertTrue(P.dedup(f, {}, now))
        self.assertFalse(P.dedup(f, {("s81", "NO-PROGRESS"): D(2026, 11, 19, 11, 30)}, now))
        self.assertTrue(P.dedup(f, {("s81", "NO-PROGRESS"): D(2026, 11, 19, 10, 30)}, now))


class TickDead(unittest.TestCase):
    def test_tick_dead_after_20_min_without_tick_times(self):
        L = ["2026-11-21 08:47:57 PST AUTOPILOT: TICK-TIMES total=380s load=20s",
             "2026-11-21 08:48:21 PST AUTOPILOT: POLL-TIMES probe_job=3x/2s"]
        ev = P.parse_lines(L)
        self.assertFalse([f for f in P.detect(ev, D(2026, 11, 21, 9, 5)) if f["cls"] == "TICK-DEAD"])
        dead = [f for f in P.detect(ev, D(2026, 11, 21, 9, 10), {"tick_progress": "running tick started 08:47:57, last mark 'after poll_running'"})
                if f["cls"] == "TICK-DEAD"]
        self.assertEqual(len(dead), 1)
        self.assertIn("08:47:57", dead[0]["text"])
        self.assertIn("after poll_running", dead[0]["text"])

    def test_no_tick_lines_at_all_is_not_an_alert(self):
        self.assertFalse([f for f in P.detect([], D(2026, 11, 21, 9, 10)) if f["cls"] == "TICK-DEAD"])


if __name__ == "__main__":
    unittest.main()
