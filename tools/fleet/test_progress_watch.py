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
        self.assertIn("4 eligible rows", f[0]["text"])

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
        g = "2026-11-19 10:30:00 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/it PLAN: x @route: y"
        self.assertFalse([x for x in P.detect(self.ev(f % 0, g), D(2026, 11, 19, 10, 40)) if x["cls"] == "NO-ADVANCE"])

    def test_stuck_state_needs_no_successor(self):
        row = {"die": "s81", "item": "i", "status": "CANCELLED", "class": "SUPERSEDED", "plan_current": "yes", "updated": "2026-11-19 09:00"}
        now = D(2026, 11, 19, 10, 30)
        self.assertEqual(len([f for f in P.detect([], now, {"rows": [row]}) if f["cls"] == "STUCK-STATE"]), 1)
        succ = dict(row, status="RUNNING", **{"class": ""})
        self.assertFalse([f for f in P.detect([], now, {"rows": [row, succ]}) if f["cls"] == "STUCK-STATE"])
        self.assertFalse([f for f in P.detect([], D(2026, 11, 19, 9, 30), {"rows": [row]}) if f["cls"] == "STUCK-STATE"])

    def test_dedup_one_per_die_class_hour(self):
        f = [{"die": "s81", "cls": "NO-PROGRESS", "state": "alert", "text": "t"}]
        now = D(2026, 11, 19, 12, 0)
        self.assertTrue(P.dedup(f, {}, now))
        self.assertFalse(P.dedup(f, {("s81", "NO-PROGRESS"): D(2026, 11, 19, 11, 30)}, now))
        self.assertTrue(P.dedup(f, {("s81", "NO-PROGRESS"): D(2026, 11, 19, 10, 30)}, now))


if __name__ == "__main__":
    unittest.main()
