"""The compact CLI must retain live work and make historical evidence recoverable."""
import argparse
import contextlib
import io
import unittest

import status_report as report


NOW = 1792029600.0
TERMINAL = {"CLOSED", "NEEDS_RTL", "CANCELLED", "INVALID", "REFUSED"}


def job(name, state, hours, block=None, params=None):
    when = report.dt.datetime.fromtimestamp(NOW - hours * 3600, report.dt.timezone.utc).isoformat()
    return dict(name=name, status=state, created=when, finished_at=when,
                spec=dict(block=block or name, params=params or {}, owner="Test:Qwen"))


def options(*args):
    parser = argparse.ArgumentParser()
    report.add_arguments(parser)
    return parser.parse_args(args)


class CompactStatus(unittest.TestCase):
    def test_keeps_all_active_even_old_and_over_limit(self):
        jobs = [job(f"live{i}", "RUNNING", 100) for i in range(30)]
        jobs += [job(f"done{i}", "CLOSED", i / 10) for i in range(30)]
        active, recent, _ = report.select_jobs(jobs, options(), TERMINAL, NOW)
        self.assertEqual(len(active), 30)
        self.assertEqual(len(recent), 20)
        self.assertEqual(recent[0]["name"], "done0")

    def test_suppresses_old_and_earlier_attempts_not_parameter_variants(self):
        jobs = [job("old", "NEEDS_RTL", 50), job("bad", "NEEDS_RTL", 2, "leaf"),
                job("good", "CLOSED", 1, "leaf"), job("cancel", "CANCELLED", 0.1, "leaf"),
                job("other-param", "NEEDS_RTL", 1, "leaf", {"WIDTH": 32}),
                job("prior", "NEEDS_RTL", 2, "routing"), job("live", "RUNNING", 1, "routing")]
        active, recent, _ = report.select_jobs(jobs, options(), TERMINAL, NOW)
        self.assertEqual([j["name"] for j in active], ["live"])
        self.assertEqual({j["name"] for j in recent}, {"good", "other-param"})

    def test_submission_order_wins_over_late_old_completion(self):
        old = job("older", "NEEDS_RTL", 2, "leaf")
        old["finished_at"] = job("unused", "CLOSED", 0.1)["finished_at"]
        new = job("newer", "CLOSED", 1, "leaf")
        _, recent, _ = report.select_jobs([old, new], options(), TERMINAL, NOW)
        self.assertEqual([j["name"] for j in recent], ["newer"])

    def test_history_active_and_filter(self):
        jobs = [job("old", "CANCELLED", 100), job("live", "RUNNING", 100), job("x", "CLOSED", 1)]
        self.assertEqual(report.select_jobs(jobs, options("--all"), TERMINAL, NOW)[0], jobs)
        active, recent, _ = report.select_jobs(jobs, options("--active"), TERMINAL, NOW)
        self.assertEqual([j["name"] for j in active], ["live"])
        self.assertEqual(recent, [])
        self.assertEqual(len(report.select_jobs(jobs, options("--all", "--filter", "QWEN"), TERMINAL, NOW)[0]), 3)
        self.assertEqual(len(report.select_jobs(jobs, options("--all", "--filter", "old"), TERMINAL, NOW)[0]), 1)

    def test_timezones_missing_dates_and_zero_limit(self):
        dated = job("utc", "CLOSED", 24)
        missing = job("missing", "CLOSED", 0)
        missing.pop("created"); missing.pop("finished_at")
        _, recent, _ = report.select_jobs([dated, missing], options(), TERMINAL, NOW)
        self.assertEqual([j["name"] for j in recent], ["utc"])
        self.assertEqual(report.select_jobs([dated], options("--limit", "0"), TERMINAL, NOW)[1], [])
        self.assertEqual(report.timestamp({"updated": "2026-10-14T18:00:00-07:00"}, "updated"),
                         report.timestamp({"updated": "2026-10-15T01:00:00Z"}, "updated"))

    def test_empty_output_and_invalid_arguments(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            report.print_status([], options(), TERMINAL, lambda host: "-")
        self.assertIn("Active jobs (0):", out.getvalue())
        self.assertIn("status --all", out.getvalue())
        for args in (("--limit", "-1"), ("--recent-hours", "nan"), ("--all", "--active")):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                options(*args)


if __name__ == "__main__":
    unittest.main()
