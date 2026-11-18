"""WAVE-FLOW-R2 11-17 (COORD): the closure loop's route env equals the env written into job.json (the svc split lost 6 core runs: a hand launch from job.json had no
OT_ROUTE_HOLD_CORNERS=mm and failed closed at CTS with 'BC scene unavailable')."""
import json
import shlex
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "ref_tile"))
sys.path.insert(0, str(HERE.parent))
import route_env as RE  # noqa: E402


def test_route_exports_defaults_and_overrides():
    e = RE.route_exports({"route_hold_corners": "mm", "route_hold_margin_ns": 0.05, "route_corner": "TC"}, "route", "2026-11-17T10:00:00", True)
    assert e == {"OT_PG_JOB_STRICT": "1", "HM": "0.05", "OT_ORFS_CORNER": "TC", "OT_ROUTE_HOLD_CORNERS": "mm"}
    assert RE.route_exports({"route_hold_corners": "keep", "route_corner": "keep"}, "route", "2026-11-17T10:00:00") == {"OT_PG_JOB_STRICT": "0", "OT_PG_STRICT": "0", "HM": "0.01"}
    assert RE.route_exports({"macro_cts": False}, "route", "2026-10-01T00:00:00")["OT_CTS_MACRO_CLUSTER"] == "0"
    old = RE.route_exports({}, "route", "2026-10-07T10:00:00")                      # before MM_SINCE: primary hold corners, HM 10 ps
    assert old["OT_ROUTE_HOLD_CORNERS"] == "primary" and old["HM"] == "0.01"
    assert "OT_ROUTE_HOLD_CORNERS" not in RE.route_exports({}, "bench", "2026-11-17T10:00:00")
    assert RE.cmd_prefix({"A": "1", "B": "x y"}) == "export A=1; export B='x y'; "


def test_closure_loop_env_equals_the_job_json_env():
    """closure_loop.launch_stage builds its env text from route_exports(job spec, ...); job.json carries the same dict, as a stage field and as the command prefix"""
    import ref_tile as RT
    import helper_overlay as HO
    ex = HERE.parent / "ref_tile" / "examples" / "nhb_pbst_ref.json"
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    f.write(ex.read_text())
    f.close()
    s = RT.load_spec(f.name)
    job = RT.gen_job(s, RT.kit_dir(s), "0123456789ab", [])
    route = job["stages"]["route"]
    loop_env = RE.route_exports(job, "route", RE.now_iso(), HO.pg_strict(job))       # what closure_loop.launch_stage computes for this job
    assert route["env"] == loop_env and route["env"]["OT_ROUTE_HOLD_CORNERS"] == "mm"
    assert route["cmd"].startswith(RE.cmd_prefix(loop_env))                           # a hand launch of the command carries it
    # the loop's text for these exports is the same shell lines
    text = RE.shell_exports(loop_env)
    for k, v in loop_env.items():
        assert f"export {k}={shlex.quote(v)}\n" in text


def test_closure_loop_uses_the_shared_function_and_constants():
    src = (HERE / "closure_loop.py").read_text()
    assert "RE.route_exports(" in src and "from route_env import HM_DEFAULT_SINCE" in src
    for const in ("HM_DEFAULT_SINCE = ", "MM_SINCE = ", "OPTB_SINCE = ", "HM_MM = "):
        assert "\n" + const not in src                                                # defined once, in route_env.py
