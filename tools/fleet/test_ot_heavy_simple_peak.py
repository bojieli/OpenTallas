"""SIMPLE_PEAK (ADMIT-TUNE-1 11-14, COORD): admit on the expected PEAK of the job (p90 of completed runs of its class, else the request)
and subtract the expected remaining growth of the running jobs; not the request, not the current RSS."""
import contextlib, importlib.machinery, importlib.util, io, os, pathlib, tempfile, unittest
from unittest.mock import patch

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_peak", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile_peak", loader))
loader.exec_module(R)
HIST = {"route": [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 40.0], "few": [30.0, 31.0]}


class Peak(unittest.TestCase):
    def test_expected_peak_is_the_p90_capped_at_the_request(self):
        self.assertEqual(R.expected_peak("route", 48, HIST), 40.0)          # index int(0.9 * 10) = 9
        self.assertEqual(R.expected_peak("route", 30, HIST), 30.0)          # a job cannot exceed its MemoryMax
        self.assertEqual(R.expected_peak("few", 48, HIST), 48.0)            # < 3 completed runs: the request
        self.assertEqual(R.expected_peak("never", 48, HIST), 48.0)

    def test_reserve_counts_only_remaining_growth_scaled_by_frac(self):
        units = [("u1", 48.0, "route", 5.0), ("u2", 48.0, "route", 45.0), ("u3", 48.0, "never", 8.0)]
        self.assertAlmostEqual(R.peak_reserve(units, HIST, 1.0), (40 - 5) + 0 + (48 - 8))
        self.assertAlmostEqual(R.peak_reserve(units, HIST, 0.1), 7.5)

    def test_peak_history_uses_completed_runs_only(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("t\tu\trun_kit.sh:route\t48\t20.0\t100\t0\nt\tu\trun_kit.sh:route\t48\t99.0\t100\t137\nbad\n")
        self.assertEqual(R.peak_history(f.name), {"run_kit.sh:route": [20.0]})

    def gate(self, avail, units, cls="route", mem=48, conf=None):
        env = dict({"SIMPLE_ADMIT": "1", "SIMPLE_PEAK": "1", "INV_HEADROOM_GB": "16", "PEAK_GROWTH_FRAC": "0.1", "SIMPLE_FRESH_S": "0"}, **(conf or {}))
        d = tempfile.mkdtemp()
        with patch.dict(os.environ, env), patch.object(R, "D", d), patch.object(R, "classify", return_value=cls), \
                patch.object(R, "sizes", return_value={}), patch.object(R, "meminfo", return_value=(1000.0, float(avail))), \
                patch.object(R, "peak_history", return_value=HIST), patch.object(R, "running_units_light", return_value=units), \
                patch.object(R, "read_units", side_effect=AssertionError("slow read_units")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                R.gate_locked(48, ["x"])
        return out.getvalue()

    def test_admits_when_free_covers_expected_peak_after_growth(self):
        units = [("u%d" % i, 48.0, "route", 5.0) for i in range(10)]      # growth 10 x 35 x 0.1 = 35
        self.assertTrue(self.gate(16 + 35 + 40, units).startswith("OK 40 "))
        self.assertTrue(self.gate(16 + 35 + 39, units).startswith("NO 40 "))

    def test_unknown_class_is_charged_its_request(self):
        self.assertTrue(self.gate(16 + 48, [], cls="never").startswith("OK 48 "))
        self.assertTrue(self.gate(16 + 47, [], cls="never").startswith("NO 48 "))

    def test_off_by_default_keeps_the_simple_rule(self):
        self.assertIn("SIMPLE_ADMIT:", self.gate(100, [], conf={"SIMPLE_PEAK": "0"}))


class SmallLane(unittest.TestCase):
    def test_small_job_admitted_above_half_headroom_and_floor(self):
        ok, why = R.small_lane(4, 80.0, 2, 64.0, 8.0, 6.0, 36.0)
        self.assertTrue(ok, why)
        self.assertFalse(R.small_lane(4, 39.0, 0, 64.0, 8.0, 6.0, 36.0)[0])        # 39 - 4 = 35 < max(32, 36)
        self.assertTrue(R.small_lane(4, 40.0, 0, 64.0, 8.0, 6.0, 36.0)[0])         # 40 - 4 = 36

    def test_cap_and_size_limit(self):
        self.assertFalse(R.small_lane(4, 500.0, 6, 64.0, 8.0, 6.0, 36.0)[0])       # 6 small jobs already running
        self.assertFalse(R.small_lane(9, 500.0, 0, 64.0, 8.0, 6.0, 36.0)[0])       # 9 GB is a route-class job
        self.assertFalse(R.small_lane(4, 500.0, 0, 64.0, 0.0, 6.0, 36.0)[0])       # lane off

    def test_gate_uses_the_lane_before_the_peak_arithmetic(self):
        import contextlib, io
        env = {"SIMPLE_ADMIT": "1", "SIMPLE_PEAK": "1", "INV_HEADROOM_GB": "64", "PEAK_GROWTH_FRAC": "0.05", "SIMPLE_FRESH_S": "0", "SMALL_JOB_GB": "8", "SMALL_JOB_MAX": "6", "SMALL_FLOOR_GB": "36"}
        units = [("u%d" % i, 48.0, "route", 5.0) for i in range(10)]               # growth reserve far above free: a route job would be held
        d = tempfile.mkdtemp()
        with patch.dict(os.environ, env), patch.object(R, "D", d), patch.object(R, "classify", return_value="gen"), patch.object(R, "sizes", return_value={}), \
                patch.object(R, "meminfo", return_value=(1000.0, 60.0)), patch.object(R, "peak_history", return_value=HIST), \
                patch.object(R, "running_units_light", return_value=units), patch.object(R, "read_units", side_effect=AssertionError("slow")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                R.gate_locked(4, ["x"])
            self.assertTrue(out.getvalue().startswith("OK 4 gen | SMALL_JOB lane"), out.getvalue())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                R.gate_locked(48, ["x"])
            self.assertTrue(out.getvalue().startswith("NO "), out.getvalue())


class PlanPrio(unittest.TestCase):
    def test_plan_like(self):
        self.assertTrue(R.plan_like(["bash", "/x/s81-b3-clk/chainR92.sh"]))
        self.assertTrue(R.plan_like(["python3", "bind.py", "--strict-bind"]))
        self.assertTrue(R.plan_like(["bash", "run_g0.sh"], "/x/qc/g0/run"))
        self.assertTrue(R.plan_like(["x"], "", ["OT_HEAVY_PRIO=plan"]))
        self.assertTrue(R.plan_like(["x"], "", ["OT_HEAVY_PRIO=die"]))
        self.assertFalse(R.plan_like(["bash", "run_kit.sh", "route"], "/srv/x/tl-colh9"))
        self.assertTrue(R.plan_like(["bash", "/x/eco_w.sh"]) and R.plan_like(["python3", "eco_loop.py", "run"]) and R.plan_like(["t", "late_eco", "--from", "grt"]))   # LATEECO_1114

    def gate(self, avail, argv, running=0, waiting=(), mem=120, cls="chainR92.sh", env=None):
        import contextlib, io
        e = {"SIMPLE_ADMIT": "1", "SIMPLE_PEAK": "1", "PLAN_PRIO": "1", "INV_HEADROOM_GB": "64", "PEAK_GROWTH_FRAC": "0.05", "SIMPLE_FRESH_S": "0",
             "SMALL_JOB_GB": "8", "SMALL_FLOOR_GB": "36", "PLAN_MAX_RUNNING": "1", "PLAN_HOLD_MAX_S": "7200"}
        d = tempfile.mkdtemp()
        with patch.dict(os.environ, dict(e, **(env or {}))), patch.object(R, "D", d), patch.object(R, "classify", return_value=cls), \
                patch.object(R, "sizes", return_value={}), patch.object(R, "meminfo", return_value=(1000.0, float(avail))), \
                patch.object(R, "peak_history", return_value={}), patch.object(R, "running_units_light", return_value=[("u%d" % i, 48.0, "route", 5.0) for i in range(30)]), \
                patch.object(R, "plan_census", return_value=(running, list(waiting))):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                R.gate_locked(mem, argv)
        return out.getvalue()

    def test_plan_job_ignores_the_growth_reserve_but_needs_free_memory(self):
        a = ["bash", "chainR92.sh"]
        self.assertTrue(self.gate(156, a).startswith("OK 120 chainR92.sh | PLAN_PRIO"))        # 156 - 120 = 36 = floor
        self.assertFalse(self.gate(155, a).startswith("OK "))

    def test_at_most_one_plan_job_runs_per_host(self):
        self.assertFalse(self.gate(500, ["bash", "chainR92.sh"], running=1).startswith("OK 120 chainR92.sh | PLAN_PRIO"))

    def test_route_is_held_while_a_plan_job_waits_but_not_past_the_hold_limit(self):
        r = ["bash", "run_kit.sh", "route"]
        self.assertTrue(self.gate(500, r, waiting=[600], mem=48, cls="route").startswith("NO 48 route | PLAN-FIRST"))
        self.assertNotIn("PLAN-FIRST", self.gate(500, r, waiting=[8000], mem=48, cls="route"))
        self.assertNotIn("PLAN-FIRST", self.gate(500, r, waiting=[300], mem=48, cls="route", env={"PLAN_DRAIN_S": "600"}))      # PLAN_DRAIN_S: 5 min does not drain yet
        self.assertTrue(self.gate(500, r, waiting=[900], mem=48, cls="route", env={"PLAN_DRAIN_S": "600"}).startswith("NO 48 route | PLAN-FIRST"))
        self.assertNotIn("PLAN-FIRST", self.gate(500, r, waiting=[600], mem=4, cls="gen"))          # small jobs are never held


    def test_older_plan_waiter_goes_first(self):
        self.assertTrue(R.older_plan_waiting(100.0, [5000.0]))
        self.assertFalse(R.older_plan_waiting(5000.0, [100.0]))
        self.assertFalse(R.older_plan_waiting(100.0, [120.0]))                    # within the 30 s margin
        self.assertFalse(R.older_plan_waiting(100.0, []))


    def test_waiter_pid_climbs_past_the_timeout_wrapper(self):
        # gate process 500 -> `timeout 30` 400 -> waiting ot-heavy bash 300 -> ssh session 200 (the self-hold bug: getppid() was 400, age 0)
        stat = {500: "500 (python3) S 400 ", 400: "400 (timeout) S 300 ", 300: "300 (bash) S 200 ", 200: "200 (sshd) S 1 "}
        cmd = {400: "timeout\0" "30\0" "x\0" "y\0", 300: "/bin/bash\0/usr/local/bin/ot-heavy\0--mem\0" "60\0--tag\0t\0--\0true\0", 200: "sshd\0"}
        def fake_rd(path):
            pid = int(path.split("/")[2])
            return stat.get(pid, "") if path.endswith("/stat") else cmd.get(pid, "")
        with patch.object(R, "rd", side_effect=fake_rd):
            self.assertEqual(R.waiter_pid(500), 300)
        # the command substitution forks a subshell with the SAME command line: the topmost match (the real waiter) must win
        stat2 = {500: "500 (python3) S 450 ", 450: "450 (timeout) S 310 ", 310: "310 (bash) S 300 ", 300: "300 (bash) S 200 ", 200: "200 (sshd) S 1 "}
        olh = "/bin/bash\0/usr/local/bin/ot-heavy\0--mem\0" "60\0--tag\0t\0--\0true\0"
        cmd2 = {450: "timeout\0" "30\0" "x\0" "y\0", 310: olh, 300: olh, 200: "sshd\0"}
        with patch.object(R, "rd", side_effect=lambda path: (stat2 if path.endswith("/stat") else cmd2).get(int(path.split("/")[2]), "")):
            self.assertEqual(R.waiter_pid(500), 300)
        with patch.object(R, "rd", return_value=""):
            self.assertEqual(R.waiter_pid(500), 0)


    def test_early_admit_after_the_drain_uses_half_the_headroom(self):
        import contextlib, io
        e = {"SIMPLE_ADMIT": "1", "SIMPLE_PEAK": "1", "PLAN_PRIO": "1", "INV_HEADROOM_GB": "48", "PEAK_GROWTH_FRAC": "0", "SIMPLE_FRESH_S": "0", "SMALL_JOB_GB": "8",
             "SMALL_FLOOR_GB": "36", "PLAN_MAX_RUNNING": "1", "PLAN_HOLD_MAX_S": "86400", "PLAN_EARLY_S": "5400"}
        d = tempfile.mkdtemp()
        def run(avail, my_age):
            with patch.dict(os.environ, e), patch.object(R, "D", d), patch.object(R, "classify", return_value="chainR92.sh"), patch.object(R, "sizes", return_value={}), \
                    patch.object(R, "meminfo", return_value=(1000.0, float(avail))), patch.object(R, "peak_history", return_value={}), \
                    patch.object(R, "running_units_light", return_value=[]), patch.object(R, "plan_census", return_value=(0, [])), patch.object(R, "waiter_pid", return_value=4242), \
                    patch.object(R, "rd", side_effect=lambda p: f"{10000 + my_age} 0" if p == "/proc/uptime" else ("4242 (bash) S 1 " + " ".join(["0"] * 17) + " 10000" if p.endswith("/stat") else "")), \
                    patch.object(R.os, "sysconf", return_value=1):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    R.gate_locked(96, ["bash", "chainR92.sh"])
            return out.getvalue()
        # 96 GB job, floor max(24, 36) = 36: needs avail 132; early after 90 min: floor 36 - 24 = 12 -> avail 108
        self.assertFalse(run(110, 600).startswith("OK "))                     # 10 min old: normal rule
        self.assertTrue(run(110, 6000).startswith("OK 96 chainR92.sh | PLAN_PRIO EARLY"))
        self.assertFalse(run(107, 6000).startswith("OK "))                    # shortfall above half the headroom

    def test_admit_marker_counts_as_a_running_plan_job(self):
        d = tempfile.mkdtemp()
        with patch.object(R, "D", d):
            self.assertEqual(R.plan_census(0)[0], 0)
            open(os.path.join(d, f"plan.admit.{os.getppid()}"), "w").write("1")        # a live pid with no scope yet
            self.assertEqual(R.plan_census(0)[0], 1)
            self.assertEqual(R.plan_census(os.getppid())[0], 0)                          # the admitted job itself is not counted against itself


class Fallback(unittest.TestCase):
    def test_no_history_uses_a_share_of_the_request_only_for_running_jobs(self):
        self.assertEqual(R.expected_peak("never", 48, HIST), 48.0)                       # a NEW job without history is charged its request
        self.assertEqual(R.expected_peak("never", 48, HIST, fallback=0.5), 24.0)
        self.assertEqual(R.expected_peak("route", 48, HIST, fallback=0.5), 40.0)         # history wins when present

    def test_reserve_uses_the_fallback_for_unknown_classes(self):
        units = [("u", 48.0, "never", 8.0)]
        self.assertAlmostEqual(R.peak_reserve(units, HIST, 1.0), 40.0)
        self.assertAlmostEqual(R.peak_reserve(units, HIST, 1.0, fallback=0.5), 16.0)


if __name__ == "__main__":
    unittest.main()
