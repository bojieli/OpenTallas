"""CANARY-SPILL-1122 (COORD 21:0x/22:0x): the 20:45 canaries on 345ac19b04b spilled, the copy-back left gen/ root-owned, the harness could not
write route_canary.sh into it and the route job ran 'No such file' (exit 127); every flow stage was NOT RUN and baseline.py called it a
REGRESSION.  A generated run whose flow never started is INFRA (no evidence: neither a release nor a regression)."""
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import baseline as B  # noqa: E402

LOG_127 = """CANARY_GEN rc=0
CANARY_LINT PASS implicit=0 undriven=0 errors=0
ot-run: RAN on epyc8 (unit u1): exit 0
cp: cannot create regular file '/x/gen/route_canary.sh': Permission denied
bash: /x/gen/route_canary.sh: No such file or directory
ot-run: RAN on epyc10 (unit u2): exit 127
"""


def run_dir(tmp_path, log, generated=True):
    r = tmp_path / "run"
    r.mkdir(parents=True)
    (r / "otrun.log").write_text(log)
    if generated:
        (r / "GENERATED").write_text("")
    (r / "canary.json").write_text(json.dumps({"die": "qwen_compute", "item": "coll_ftm", "verdict": "FAIL", "stages": {}}))
    return r


def test_flow_never_started_is_infra_not_regression(tmp_path):
    r = run_dir(tmp_path, LOG_127)
    v = B.verdict(r, tmp_path / "root", seed=False)
    assert v["verdict"] == "INFRA" and "never started" in v["why"] and "exit 127" in v["why"]
    assert not (tmp_path / "root").exists() or not list((tmp_path / "root").rglob("*.json"))     # never seeds a baseline


def test_started_flow_or_gen_failure_is_judged_as_before(tmp_path):
    assert B.flow_not_started(run_dir(tmp_path / "a", LOG_127 + "CANARY_FLOW_RC 0\n")) == ""
    assert B.flow_not_started(run_dir(tmp_path / "b", "CANARY_GEN rc=1\n", generated=False)) == ""


def test_gate_treats_infra_as_no_evidence():
    sys.path.insert(0, str(HERE.parent / "autopilot"))
    import canary_gate as G
    assert "INFRA" not in G.RELEASE


def test_spill_owner_command_is_valid_and_noop_without_root_files(tmp_path):
    l = importlib.machinery.SourceFileLoader("otr_own", str(HERE.parent / "fleet" / "ot-run"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("otr_own", l)); l.exec_module(m)
    d = tmp_path / "lane dir"; (d / "gen").mkdir(parents=True); (d / "gen" / "f").write_text("x")
    sh = m.spill_owner_sh([str(d), str(tmp_path / "missing")])
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
    assert r.returncode == 0 and (d / "gen" / "f").read_text() == "x"
    assert "--from=0:0" in sh and "-uid 0" in sh
