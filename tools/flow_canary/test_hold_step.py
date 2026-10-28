"""FLOW-SHARED-9 (COORD 10-27 19:36 (1)): KV post-route hold step.
  - a hold-step failure is never silently replaced by the plain route: hold_step.json FAILED -> canary stage
    hold_step FAIL -> baseline REGRESSION.
    python3 -m pytest -q tools/flow_canary/test_hold_step.py"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ECO = ROOT / "physical/die_plan/qwen_kvsys/cores/harden/eco"
sys.path[:0] = [str(HERE), str(HERE.parent / "die_plan")]
import baseline as B  # noqa: E402
import canary as C  # noqa: E402


def _stage(tmp_path, run_eco_body):
    eco = tmp_path / "eco"
    eco.mkdir()
    shutil.copy(ECO / "hold_step.sh", eco / "hold_step.sh")
    (eco / "mk_eco.sh").write_text('mkdir -p "$2"; echo "OT_MAX_FANOUT=24" > "$2/variant.env"; '
                                   'echo "{}" > "$2/ECO.json"\n')
    (eco / "run_eco.sh").write_text(run_eco_body)
    kit = tmp_path / "kit"
    (kit / "signoff").mkdir(parents=True)
    (kit / "signoff/signoff.json").write_text(json.dumps({"checks": {"hold_ff": {"wns_ps": -1.9}}}))
    (kit / "max_fanout.tcl").write_text("set_max_fanout 64 [current_design]\n")
    return eco, kit


def _run(eco, kit, tmp_path, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(["bash", str(eco / "hold_step.sh"), str(kit), str(tmp_path)], text=True,
                          capture_output=True, env=e)


def test_hold_step_failure_is_flagged_and_stale_hold_signoff_removed(tmp_path):
    eco, kit = _stage(tmp_path, 'echo "[ERROR DRT-1231] Pin u/y\\$_DFF_PN0_/RESETN does not have access point" '
                                '> "$1/run_eco.log"; echo route_finish_rc=2 > "$1/rc.txt"; exit 2\n')
    (kit / "signoff_hold").mkdir()
    (kit / "signoff_hold/signoff.json").write_text("{}")          # stale result of an earlier hold step
    r = _run(eco, kit, tmp_path)
    assert r.returncode == 2
    assert "HOLD_STEP FAILED" in r.stdout and "DRT-1231" in r.stdout
    hs = json.loads((kit / "hold_step.json").read_text())
    assert hs["status"] == "FAILED" and hs["rc"] == 2 and "DRT-1231" in hs["error"]
    assert not (kit / "signoff_hold").exists()


def test_hold_step_pass_and_not_needed_are_recorded(tmp_path):
    eco, kit = _stage(tmp_path, 'mkdir -p "$1/signoff"; echo "{\\"checks\\": {}}" > "$1/signoff/signoff.json"; exit 0\n')
    r = _run(eco, kit, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads((kit / "hold_step.json").read_text())["status"] == "PASS"
    assert (kit / "signoff_hold/signoff.json").is_file()
    (kit / "signoff/signoff.json").write_text(json.dumps({"checks": {"hold_ff": {"wns_ps": 3.0}}}))
    shutil.rmtree(Path(str(kit) + "_holdeco"))
    assert _run(eco, kit, tmp_path).returncode == 0
    assert json.loads((kit / "hold_step.json").read_text())["status"] == "NOT_NEEDED"


def test_canary_reports_failed_hold_step_and_baseline_regresses(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    (tmp_path / "canary_meta.json").write_text(json.dumps(dict(kit=str(kit), spec=dict(die="qwen_kvsys_core", item="e1"))))
    (kit / "hold_step.json").write_text(json.dumps(dict(status="FAILED", rc=2, error="[ERROR DRT-1231] x")))
    r = C.check_run(tmp_path)
    assert r["stages"]["hold_step"]["verdict"] == "FAIL" and "hold_step" in r["failing"]
    base = {"stages": {}, "contexts": {}}
    cur = {"stages": {"hold_step": "FAIL"}, "contexts": {}}
    v, rows, _ = B.compare(base, cur)
    assert v == "REGRESSION" and any(x["metric"] == "hold_step" for x in rows)
    (kit / "hold_step.json").write_text(json.dumps(dict(status="PASS", rc=0)))
    assert C.check_run(tmp_path)["stages"]["hold_step"]["verdict"] == "PASS"
