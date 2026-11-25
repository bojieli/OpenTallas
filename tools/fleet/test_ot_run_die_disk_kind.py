"""DIEDISK_KIND_1125 (COORD 11-25): a die-class job with no --disk asks by kind (PRE/check/census/gate 2, compose 5, bind 1.5 x measured peak or 30)."""
import importlib.machinery, importlib.util, json
from pathlib import Path

P = str(Path(__file__).with_name("ot-run"))
_l = importlib.machinery.SourceFileLoader("ot_run_die_disk_kind", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_die_disk_kind", _l))
_l.exec_module(R)


def test_kind_asks():
    pre = ["python3", "-I", "-B", "/x/tools/die_plan/plan_gate_pre.py", "check", "--tree", "/t"]
    assert R.die_job_kind(pre) == "pre" and R.die_disk_ask(pre, True, True) == 2
    assert R.die_disk_ask(["python3", "tools/die_plan/check.py", "p.json"], True, False) == 2
    assert R.die_disk_ask("bash /l/kv/a5t7i1/run_a5t7_gate.sh", True, False) == 2
    assert R.die_disk_ask("python3 /l/a5t6e10/compose3.py", True, False) == 5
    assert R.die_job_kind("bash /l/s81/gate_c9s_bindonly_1124.sh") == "bind"     # a bind-only gate writes the bind


def test_bind_measured_or_30(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"bind": {"peak_gb": 0.91}}))
    assert R.die_disk_ask(["python3", "tools/die_plan/bind.py", "bind", "p.json"], True, False, path=str(f)) == 2
    f.write_text(json.dumps({"bind": {"peak_gb": 12}}))
    assert R.bind_disk_gb(str(f)) == 18
    assert R.bind_disk_gb(str(tmp_path / "missing.json")) == 30
    assert R.bind_disk_gb() <= 30                         # the shipped table is measured


def test_unknown_kind_and_non_die_unchanged():
    assert R.die_disk_ask("bash /l/kv/job_a5t7pins.sh", True, True) == R.DIE_DISK_GB     # --die of an unknown kind keeps the die default
    assert R.die_disk_ask("bash /l/kv/job_a5t7pins.sh", False, False) == 20
    assert R.die_disk_ask(["python3", "tools/die_plan/bind.py", "kit-rtl", "--type", "x"], True, False) == 20
    assert R.die_disk_ask(["python3", "/x/plan_gate_pre.py"], False, False) == 20         # not die class: unchanged


def test_explicit_disk_wins_in_source():
    src = Path(P).read_text()
    assert "disk = disk if disk is not None else die_disk_ask(cmd, PREFER_DIE[0], die)" in src
