"""FAILFAST-1 (2026-11-11): grt183_make.sh stops the stage on PROGRESS (physical/common_flow/failfast_rules.py as /work/failfast_rules.py):
GRT no progress, DRT no progress, hold structural.  Local, no Docker/OpenROAD.
    python3 -m pytest -q tools/die_plan/test_failfast_kit.py"""
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools/autopilot"))
from test_grt183_kit import calls, fake, kit, run  # noqa: E402
from test_failfast_rules import log_iters, rep  # noqa: E402

FAST = {"OT_GRT_STALL_POLL": "1", "OT_GRT_STALL_KILL_WAIT": "1", "OT_GRT_EARLY_SETTLE_S": "0", "OT_GRT_EARLY_STOP": "off"}
RULES = ROOT / "physical/common_flow/failfast_rules.py"
NS = (5, 10, 15, 20, 25, 30)


def with_rules(tmp_path, cfg=""):
    k, r, l, s = kit(tmp_path, cfg)
    shutil.copyfile(RULES, k / "failfast_rules.py")
    return k, r, l, s


def phase(log_rounds, total, then="sleep 3"):
    """fake-make fragment: rewrite the GRT log and every congestion report (a new round overwrites them)"""
    s = "D=$K/run/reports/asap7/t/base; mkdir -p $D\ncat > $L/5_1_grt.tmp.log <<'EOF'\n" + log_iters(*log_rounds) + "EOF\n"
    for n in NS:
        s += f"cat > $D/congestion-{n}.rpt <<'EOF'\n{rep(total, layer='M5') if total else ''}EOF\n"
    return s + then + "\n"


def test_flat_grt_is_stopped_with_the_class_line(tmp_path):
    k, r, l, s = with_rules(tmp_path)
    t = time.time()
    p = run(k, s, fake(tmp_path, phase([30], 9000) + phase([30, 30], 8800, then="sleep 60")), "grt", env=FAST)
    assert p.returncode == 21, p.stdout + p.stderr
    assert time.time() - t < 45
    line = next(x for x in p.stdout.splitlines() if x.startswith("OT_GRT_NO_PROGRESS"))
    assert "class=GRT_NO_PROGRESS" in line and "M5=8800" in line and "after 60 extra iterations in 2 rounds" in line
    assert "OT_GRT_STOP grt_no_progress: stage rc" in p.stdout and len(calls(k)) == 1          # no fresh-process re-run


def test_converging_grt_runs_on(tmp_path):
    k, r, l, s = with_rules(tmp_path)
    body = phase([30], 60000) + phase([30, 30], 20000) + phase([30, 30, 30], 5000) + phase([30, 30, 30, 30], 400) + \
        phase([30, 30, 30, 30, 30], 0, then="sleep 3; exit 0")
    p = run(k, s, fake(tmp_path, body), "grt", env=FAST)
    assert p.returncode == 0 and "NO_PROGRESS" not in p.stdout and "OT_GRT_STOP" not in p.stdout, p.stdout + p.stderr


def test_high_flat_grt_below_two_rounds_runs_on(tmp_path):
    k, r, l, s = with_rules(tmp_path)
    p = run(k, s, fake(tmp_path, phase([30], 9000, then="sleep 4; exit 0")), "grt", env=FAST)
    assert p.returncode == 0 and "OT_GRT_STOP" not in p.stdout


def test_drt_no_progress(tmp_path):
    k, r, l, s = with_rules(tmp_path)
    lines = "".join("[INFO DRT-0195] Start %dth optimization iteration.\n[INFO DRT-0199]   Number of violations = 40000.\n" % i
                    for i in range(22))
    body = f"cat > $L/5_2_route.tmp.log <<'EOF'\n{lines}EOF\nsleep 60\n"
    p = run(k, s, fake(tmp_path, body), "route", env=FAST)
    assert p.returncode == 21, p.stdout + p.stderr
    assert any(x.startswith("OT_DRT_NO_PROGRESS stage=route class=DRT_NO_PROGRESS") for x in p.stdout.splitlines())
    assert "OT_GRT_STOP drt_no_progress" in p.stdout


def test_hold_structural_at_cts(tmp_path):
    k, r, l, s = with_rules(tmp_path)
    body = ("cat > $L/4_1_cts.log <<'EOF'\nOT_HOLD_GUARD chunk 1: buffer cap 4000 reached (RSZ-0060), continuing\n"
            "OT_HOLD_GUARD chunk 2: buffer cap 4000 reached (RSZ-0060), continuing\nEOF\nsleep 60\n")
    p = run(k, s, fake(tmp_path, body.replace("sleep 60", "sleep 4")), "cts", env=FAST)
    assert p.returncode == 0 and "OT_HOLD_STRUCTURAL" not in p.stdout          # cap clause off by default
    p = run(k, s, fake(tmp_path, body), "cts", env=dict(FAST, OT_FF_HOLD_CAPS="2"))
    assert p.returncode == 21, p.stdout + p.stderr
    assert any(x.startswith("OT_HOLD_STRUCTURAL stage=cts failfast class=HOLD_STRUCTURAL") for x in p.stdout.splitlines())
    assert "OT_GRT_STOP hold_structural" in p.stdout


def test_hold_stall_line_stops(tmp_path):
    k, r, l, s = with_rules(tmp_path)
    body = "echo 'OT_HOLD_STALL NEEDS_RTL (hold repair over 3 h): R2R=9@-101' > $L/5_1_grt.tmp.log\nsleep 60\n"
    p = run(k, s, fake(tmp_path, body), "grt", env=FAST)
    assert p.returncode == 21 and "OT_HOLD_STRUCTURAL stage=grt failfast" in p.stdout


def test_opt_outs_and_no_rules_file(tmp_path):
    hold = ("cat > $L/4_1_cts.log <<'EOF'\nOT_HOLD_GUARD chunk 1: buffer cap 4000 reached (RSZ-0060), continuing\n"
            "OT_HOLD_GUARD chunk 2: buffer cap 4000 reached (RSZ-0060), continuing\nEOF\nsleep 4\n")
    k, r, l, s = with_rules(tmp_path / "env")
    p = run(k, s, fake(tmp_path / "env", hold), "cts", env=dict(FAST, OT_FAILFAST="0", OT_FF_HOLD_CAPS="2"))
    assert p.returncode == 0 and "OT_HOLD_STRUCTURAL" not in p.stdout
    k, r, l, s = with_rules(tmp_path / "cfg", "export OT_FF_HOLD = 0\n")
    p = run(k, s, fake(tmp_path / "cfg", hold), "cts", env=dict(FAST, OT_FF_HOLD_CAPS="2"))
    assert p.returncode == 0 and "OT_HOLD_STRUCTURAL" not in p.stdout
    k, r, l, s = kit(tmp_path / "old")                                          # a kit built before FAILFAST-1: no rules file
    p = run(k, s, fake(tmp_path / "old", hold), "cts", env=dict(FAST, OT_FF_HOLD_CAPS="2"))
    assert p.returncode == 0 and "OT_HOLD_STRUCTURAL" not in p.stdout


def test_kit_builder_copies_the_rules_file(tmp_path):
    import core_flow
    core_flow.stage_grt183(tmp_path)
    assert (tmp_path / "failfast_rules.py").read_bytes() == RULES.read_bytes()
    import kit_resume as KR
    assert KR.is_gate_root("failfast_rules.py")
