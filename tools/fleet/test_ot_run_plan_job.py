"""WAVE-CONFIG 11-16: ot-run plan priority from an explicit marker (--plan-job KIND / job spec "plan_job"), name rule as fallback."""
import importlib.machinery, importlib.util, json, os, pathlib, tempfile, unittest
from unittest.mock import patch

H = pathlib.Path(__file__).parent


def load(name, fn):
    l = importlib.machinery.SourceFileLoader(name, str(H / fn))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, l)); l.exec_module(m)
    return m


RUN = load("ot_run_planjob", "ot-run")
ODD = ["bash", "-c", "cd /x/typekv && python3 -I eco_loop.py r"]


class PlanJob(unittest.TestCase):
    def test_marker_admits_a_command_with_any_name(self):
        for kind in ("bind", "latcheck", "g0"):
            with patch.dict(os.environ, {"OT_RUN_PLAN_JOB": kind}):
                self.assertTrue(RUN.plan_cmd_ok(["bash", "weird_name.sh"]))

    def test_unknown_kind_is_not_a_marker(self):
        with patch.dict(os.environ, {"OT_RUN_PLAN_JOB": "route"}):
            self.assertFalse(RUN.plan_cmd_ok(["bash", "run_kit.sh"]))

    def test_name_rule_is_the_fallback(self):
        env = {k: v for k, v in os.environ.items() if k not in ("OT_RUN_PLAN_JOB", "OT_RUN_PLAN_OK")}
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(RUN.plan_cmd_ok(["bash", "bindB4.sh"]))
            self.assertFalse(RUN.plan_cmd_ok(ODD))

    def test_spec_plan_job(self):
        d = tempfile.mkdtemp()
        for val, want in (("bind", "bind"), ("g0", "g0"), ("route", None), (None, None)):
            p = pathlib.Path(d) / f"s_{val}.json"
            p.write_text(json.dumps({"name": "x", **({"plan_job": val} if val else {})}))
            self.assertEqual(RUN.spec_plan_job(str(p)), want)
        self.assertIsNone(RUN.spec_plan_job(str(pathlib.Path(d) / "missing.json")))

    def test_cli_refuses_a_bad_kind_and_a_type_build_without_marker(self):
        import subprocess
        env = {k: v for k, v in os.environ.items() if k not in ("OT_RUN_PLAN_JOB", "OT_RUN_PLAN_OK", "OT_RUN_PRIO_ENV")}
        r = subprocess.run(["python3", "-I", str(H / "ot-run"), "--mem", "1", "--plan-job", "route", "--", "true"], env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0); self.assertIn("--plan-job takes only", r.stderr + r.stdout)
        r = subprocess.run(["python3", "-I", str(H / "ot-run"), "--mem", "1", "--priority", "plan", "--", "bash", "run_kit.sh"], env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0); self.assertIn("--priority plan is for die-plan", r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
