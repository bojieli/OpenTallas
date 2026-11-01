"""lec_async.sh (FLOW-21, COORD 11-01 05:1x): the pre-route LEC runs beside place/CTS/route.
    python3 -m pytest -q tools/die_plan/test_lec_async.py"""
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "lec_async.sh"

FAKE_DOCKER = r'''#!/bin/bash
# fake docker: run -> bash -c CMD with /work mapped to the -v dir; inspect -> running unless K/flow.exited; stop -> marker
op=$1; shift
case $op in
exec) echo "$*" >> "$FAKE_K/docker_exec.args"; K=$FAKE_K; while [ $# -gt 0 ]; do case $1 in -v) K=${2%%:/work}; shift 2;; bash) shift; [ "$1" = -lc ] && shift; CMD=$1; shift;; *) shift;; esac; done
     CMD=${CMD//\/work/$K}; CMD=${CMD//source \/OpenROAD-flow-scripts\/env.sh/true}; bash -c "$CMD"; exit $?;;
inspect) [ -f "$FAKE_K/flow.exited" ] && echo false || echo true;;
stop) touch "$FAKE_K/flow.stopped";;
rm) ;;
esac
'''


def _kit(tmp_path, code):
    k = tmp_path / "kit"
    k.mkdir()
    (k / "lec.py").write_text("")
    dk = tmp_path / "docker"
    dk.write_text(FAKE_DOCKER)
    dk.chmod(0o755)
    (k / "lec_async.sh").write_text(TOOL.read_text())
    env = dict(os.environ, OT_LEC_ASYNC_POLL="0.2", FAKE_K=str(k))
    subprocess.run(["bash", str(TOOL), "start", str(k), "flowc", "img", "4", "2", str(dk)], check=True, env=env)
    assert (k / "lec_async.on").is_file()
    return k, env


def _ready(k, pol, rc):
    (k / "lec_async.ready").write_text(f"{pol}\necho lec >> /work/lec_run.log; exit {rc}\n")


def _finish(k, env, rc, stop=None):
    args = ["bash", str(TOOL), "finish", str(k), str(rc)] + ([str(stop)] if stop is not None else [])
    return subprocess.run(args, check=True, env=env, capture_output=True, text=True, timeout=60).stdout.strip()


def test_equivalent_keeps_flow_rc(tmp_path):
    k, env = _kit(tmp_path, 0)
    _ready(k, "1", 0)
    assert _finish(k, env, 4) == "4"
    assert (k / "lec_async.rc").read_text().strip() == "0"
    args = (k / "docker_exec.args").read_text()
    assert "flowc bash -lc" in args and "--memory" not in args and "-v " not in args
    assert not (k / "lec_async.stop").exists() and not (k / "flow.stopped").exists()
    assert not (k / "FAIL_PREFLOOR").exists() and not (k / "lec_async.on").exists()


def test_not_equivalent_stops_the_route(tmp_path):
    k, env = _kit(tmp_path, 1)
    _ready(k, "1", 1)
    t = time.time()
    while not (k / "flow.stopped").exists() and time.time() - t < 30:      # watcher stops the flow container
        time.sleep(0.1)
    assert (k / "flow.stopped").exists()
    assert _finish(k, env, 137, 3) == "3"
    assert "LEC NOT EQUIVALENT" in (k / "FAIL_PREFLOOR").read_text()


def test_unproven_is_a_warning_and_nz_policy_stops(tmp_path):
    k, env = _kit(tmp_path, 2)
    _ready(k, "1", 2)
    assert _finish(k, env, 0) == "0" and not (k / "flow.stopped").exists()
    (tmp_path / "b").mkdir()
    k2, env2 = _kit(tmp_path / "b", 2)
    _ready(k2, "nz", 2)                                    # legacy_gate: any non-EQUIVALENT stops (unchanged rule)
    assert _finish(k2, env2, 0) == "5" and (k2 / "lec_async.stop").exists()


def test_flow_without_lec_step_aborts_the_watcher(tmp_path):
    k, env = _kit(tmp_path, 0)
    assert _finish(k, env, 6) == "6"                       # e.g. face_guard FAIL before the LEC step
    assert not (k / "lec_async.rc").exists() and (k / "lec_async.done").exists()


def test_every_runner_hands_the_lec_over():
    import sys
    sys.path.insert(0, str(HERE))
    import gen_phys
    t = gen_phys.RUN_KIT
    assert 'lec_async.sh" start' in t and 'lec_async.sh" finish' in t and "lec_async.ready" in t
    assert "bash /work/lec_async.sh wait /work" in t
    assert "[ ! -f /work/lec_async.on ]; then python3 -I /work/lec.py" in t       # OT_LEC_ASYNC=0: inline as before
    root = HERE.parent.parent
    for f in ("physical/die_plan/hbm_arch_cores/run_kit_hbm.sh", "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh"):
        p = root / f
        if p.is_file():
            s = p.read_text()
            assert 'lec_async.sh" start' in s and 'lec_async.sh" finish' in s and "lec_async.ready" in s, f


def test_flow_exit_waits_for_proof_in_shared_container(tmp_path):
    k, env = _kit(tmp_path, 0)
    (k / "lec_async.ready").write_text("1\nsleep 0.5; echo finished > /work/proof.finished\n")
    p = subprocess.run(["bash", str(TOOL), "wait", str(k)], env=env, timeout=60)
    assert p.returncode == 0 and (k / "proof.finished").exists()
    assert _finish(k, env, 0) == "0"
