"""FLOW-OPS-0900 (FABLE-FLOW-0745 g): ot-run refuses a malformed submission at parse time (exit 64, no unit, no DIED post)."""
import importlib.machinery
import importlib.util
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
_l = importlib.machinery.SourceFileLoader("ot_run_argv_guard", str(HERE / "ot-run"))
M = importlib.util.module_from_spec(importlib.util.spec_from_loader(_l.name, _l))
_l.exec_module(M)


def test_empty_dir_from_unset_variable_is_refused():
    # TAP-GRID-R3 07:26: `--dir $D -- bash dump.sh` with D unset -> the parser saw `--dir -- bash`
    assert "empty or a flag" in M.argv_refusal(["--mem", "8", "--dir", "--", "bash", "/srv/opentallas-scratch2/claude/x/dump.sh"])
    assert M.argv_refusal(["--mem", "8", "--dir", "", "--", "bash", "x.sh"])
    assert M.argv_refusal(["--mem", "8", "--dir=", "--", "true"])


def test_run_kit_fan_out_over_empty_kit_is_refused():
    r = M.argv_refusal(["--mem", "36", "--dir", "/srv/opentallas-scratch2/claude/L/run", "--", "bash", "/srv/opentallas-scratch2/claude/L/run_kit.sh", "", "route"])
    assert "run_kit.sh kit argument" in r
    assert M.argv_refusal(["--mem", "36", "--dir", "/srv/a", "--", "bash", "/srv/a/gen/run_kit_r.sh", "route", "36"])


def test_well_formed_and_maintenance_calls_pass():
    assert M.argv_refusal(["--mem", "36", "--dir", "/srv/opentallas-scratch2/claude/L/k", "--", "bash", "/srv/opentallas-scratch2/claude/L/k/run_kit.sh",
                           "/srv/opentallas-scratch2/claude/L/k", "route", "36", "8"]) == ""
    assert M.argv_refusal(["--mem", "4", "--", "python3", "-c", "print(1)"]) == ""          # no --dir at all: unchanged
    assert M.argv_refusal(["--cancel", "oth-x"]) == ""
    assert M.argv_refusal(["--status"]) == ""
    assert M.argv_refusal(["--mem", "4", "--dir", "/srv/a", "--", "bash", "-c", "echo --dir"]) == ""   # words after -- are the command


def test_cli_exits_64_with_not_run_line_and_no_status_record(tmp_path):
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "OT_LANE": "TEST-ARGV-GUARD"}
    r = subprocess.run([sys.executable, "-I", str(HERE / "ot-run"), "--mem", "8", "--dir", "--", "bash", "x.sh"], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 64
    assert "NOT-RUN ARGV-GUARD" in r.stderr
    assert not list(tmp_path.rglob("*status*"))
