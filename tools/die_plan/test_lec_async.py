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
     # like the docker CLI: the exec'd command's stderr is kept, this shell's own "Killed" job notice is not
     CMD=${CMD//\/work/$K}; CMD=${CMD//source \/OpenROAD-flow-scripts\/env.sh/true}; { bash -c "$CMD" 2>&3; } 3>&2 2>/dev/null; exit $?;;
inspect) if [ "$1" != -f ]; then
           [[ "$1" = *-lec ]] && exit 1
           printf '[{"State":{"Running":true},"Mounts":[{"Source":"%s"}]}]\n' "$FAKE_K"
         elif [[ "$*" = *range*Mounts* ]]; then echo "$FAKE_K";
         elif [[ "$*" = *OOMKilled* ]]; then [ -f "$FAKE_K/oomkilled" ] && echo true || echo false;
         else [ -f "$FAKE_K/flow.exited" ] && echo false || echo true; fi;;
top) printf 'PID COMMAND\n123 bash /work/lec_async.sh wait /work\n';;
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
    assert not (k / "FAIL_PREFLOOR").exists() and (k / "lec_async.on").exists()


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
    assert "[ ! -f /work/lec_async.on ] && [ ! -f /work/lec_async.identity ]; then python3 -I /work/lec.py" in t       # OT_LEC_ASYNC=0: inline as before
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


def test_physical_receipt_before_wait_and_later_scope_reuses_owner(tmp_path):
    import json
    k, env = _kit(tmp_path, 0)
    (k / "lec_async.ready").write_text("1\nsleep 3; echo EQ >> /work/lec_run.log\n")
    until = time.time() + 10
    while not (k / "lec_async.identity").exists() and time.time() < until:
        time.sleep(0.05)
    original_pid = (k / "lec_async.pid").read_text()
    owner = subprocess.Popen(["bash", str(TOOL), "wait", str(k), "flowc", "route", "0"], env=env)
    ready = (k / "lec_async.ready").read_bytes()
    dk = tmp_path / "docker"
    subprocess.run(["bash", str(TOOL), "start", str(k), "nextcts", "img", "4", "2", str(dk), "cts"],
                   env=env, check=True)
    assert (k / "lec_async.pid").read_text() == original_pid
    assert (k / "lec_async.ready").read_bytes() == ready
    subprocess.run(["bash", str(TOOL), "wait", str(k), "nextcts", "cts", "0"], env=env, check=True)
    receipt = json.loads((k / "physical_completion/nextcts.json").read_text())
    assert receipt["rc"] == 0 and receipt["goal"] == "cts" and receipt["proof_owner"] == "flowc"
    assert receipt["proof_pending"] and receipt["proof_id"] and receipt["proof_scope"]
    assert owner.poll() is None  # original admitted proof scope still alive/tracked
    subprocess.run(["bash", str(TOOL), "start", str(k), "nextplace", "img", "4", "2", str(dk), "place"],
                   env=env, check=True)
    cp=k/"run/results/asap7/t/base/3_place.odb";cp.parent.mkdir(parents=True);cp.write_bytes(b"fixture")
    subprocess.run(["bash", str(TOOL), "wait", str(k), "nextplace", "place", "0"], env=env, check=True)
    place=json.loads((k/"physical_completion/nextplace.json").read_text())
    assert place["goal"]=="place" and place["checkpoint"]["path"].endswith("3_place.odb")
    assert place["checkpoint"]["size"]==7
    placedone=subprocess.run(["bash",str(TOOL),"finish",str(k),"0","5","nextplace","place"],env=env,capture_output=True,text=True,check=True)
    assert placedone.stdout.strip()=="0"
    done = subprocess.run(["bash", str(TOOL), "finish", str(k), "0", "5", "nextcts", "cts"],
                          env=env, capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "0" and not (k / "lec_async.done").exists()
    owner.wait(timeout=10)
    assert _finish(k, env, 0) == "0"


def test_changed_inputs_do_not_reset_or_duplicate_existing_proof(tmp_path):
    k, env = _kit(tmp_path, 0)
    _ready(k, "1", 0)
    assert _finish(k, env, 0) == "0"
    previous = {n: (k / n).read_bytes() for n in ("lec_async.pid", "lec_async.ready", "lec_async.identity")}
    for filename, content in (("lec.py", "changed proof driver"), ("reset_contract.json", "{}")):
        old = (k / filename).read_bytes() if (k / filename).exists() else None
        (k / filename).write_text(content)
        p = subprocess.run(["bash", str(TOOL), "start", str(k), "different", "img", "4", "2", str(tmp_path / "docker"), "cts"],
                           env=env, capture_output=True, text=True)
        assert p.returncode == 11
        assert {n: (k / n).read_bytes() for n in previous} == previous
        if old is None:(k / filename).unlink()
        else:(k / filename).write_bytes(old)
    # Correspondence discovery remains free to update its output without changing proof inputs.
    (k / "lec").mkdir(exist_ok=True);(k / "lec/hyp.json").write_text("new discovery output")
    p = subprocess.run(["bash", str(TOOL), "start", str(k), "reuse", "img", "4", "2", str(tmp_path / "docker"), "cts"],
                       env=env, capture_output=True, text=True)
    assert p.returncode == 0,p.stderr
    assert (k / "lec_async.pid").read_bytes() == previous["lec_async.pid"]


def test_live_legacy_proof_bootstrap_preserves_markers_and_requires_pinned_inputs(tmp_path):
    import json
    k,env=_kit(tmp_path,0)
    (k/"config.mk").write_text("export DESIGN_NAME = fixture\n")
    (k/"freeze.json").write_text(json.dumps({"source_commit":"a"*40}))
    net=k/"run/results/asap7/t/base/1_2_yosys.v";net.parent.mkdir(parents=True);net.write_text("module t; endmodule")
    import hashlib
    files={n:hashlib.sha256((k/n).read_bytes()).hexdigest() for n in ("config.mk","freeze.json","lec.py")}
    (k/"PROVENANCE.json").write_text(json.dumps(dict(schema="opentallas.kit_provenance.v1",
        provenance=dict(commit="a"*40,dirty=False),files=files)))
    (k/"lec_async.ready").write_text("1\nsleep 3; echo EQ >> /work/lec_run.log\n")
    until=time.time()+10
    while not (k/"lec_async.identity").exists() and time.time()<until:time.sleep(.05)
    original=(k/"lec_async.pid").read_bytes(),(k/"lec_async.ready").read_bytes()
    for f in ("owner","identity","source_identity"):(k/("lec_async."+f)).unlink()
    p=subprocess.run(["bash",str(TOOL),"start",str(k),"freshgrt","img","4","2",str(tmp_path/"docker"),"grt"],
                     env=env,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert (k/"lec_async.pid").read_bytes()==original[0] and (k/"lec_async.ready").read_bytes()==original[1]
    migration=json.loads((k/"lec_async.migration.json").read_text())
    assert migration["owner"]=="flowc" and migration["source_commit"]=="a"*40
    assert json.loads((k/"lec_async.runs/flowc.json").read_text())["goal"]=="proof-owner"
    assert not (k/"physical_completion/flowc.json").exists() # no old physical rc fabricated
    assert _finish(k,env,0)=="0"


def test_reused_proof_refuses_changed_synth_before_physical(tmp_path):
    import json
    k, env = _kit(tmp_path, 0)
    net = k / "net.v"
    net.write_text("module t; endmodule\n")
    (k / "lec_async.ready").write_text("1\necho --netlist /work/net.v\n")
    assert _finish(k, env, 0) == "0"
    original = {n: (k / n).read_bytes() for n in ("lec_async.pid", "lec_async.ready", "lec_async.identity")}
    subprocess.run(["bash", str(TOOL), "start", str(k), "nextcts", "img", "4", "2", str(tmp_path / "docker"), "cts"], env=env, check=True)
    run = json.loads((k / "lec_async.runs/nextcts.json").read_text())
    assert set(run["netlists"]) == {"net.v"}
    net.touch()  # An incremental make with identical bytes is safe.
    args = ["bash", str(TOOL), "check-synth", str(k), "nextcts"]
    assert subprocess.run(args, env=env).returncode == 0
    net.write_text("module t; wire changed; endmodule\n")
    failed = subprocess.run(args, env=env, capture_output=True, text=True)
    assert failed.returncode == 11 and "synth changed reused proof netlist" in failed.stderr
    assert all((k / n).read_bytes() == value for n, value in original.items())
    assert not (k / "lec_async.stop").exists()  # Original proof remains its own valid scope.


def _long_ready(k, tmp_path):
    # The fake docker cannot kill the exec when the container's main process ends, so the LEC watches for that here.
    (k / "lec_async.ready").write_text("1\nuntil [ -f /work/lec_async.abort ]; do sleep 0.1; done; exit 137\n")
    for _ in range(100):
        if (k / "docker_exec.args").exists():
            return
        time.sleep(0.1)
    raise AssertionError("LEC never started")


def _wait(k, env, rc):
    args = ["bash", str(TOOL), "wait", str(k), "flowc", "route", str(rc)]
    return subprocess.run(args, check=True, env=env, capture_output=True, text=True, timeout=30).stdout


def test_plan_stop_aborts_the_proof_without_a_verdict(tmp_path):
    k, env = _kit(tmp_path, 0)
    _long_ready(k, tmp_path)
    assert "LEC aborted" in _wait(k, env, 2)
    assert _finish(k, env, 2) == "2"
    assert (k / "lec_async.done").exists() and not (k / "lec_async.rc").exists()
    assert not (k / "lec_async.stop").exists() and not (k / "FAIL_PREFLOOR").exists()
    assert not (k / "flow.stopped").exists()
    assert not (k / "lec_async.ready").exists() and not (k / "lec_async.identity").exists()


def test_stop_after_place_keeps_the_proof(tmp_path):
    k, env = _kit(tmp_path, 0)
    d = k / "run/results/asap7/x/base"
    d.mkdir(parents=True)
    (d / "3_place.odb").write_text("x")
    _ready(k, "1", 0)
    assert "aborted" not in _wait(k, env, 2)
    assert (k / "lec_async.rc").read_text().strip() == "0" and not (k / "lec_async.abort").exists()
    assert (k / "lec_async.identity").exists()


# KW-FIX-24 11-06 (S81-ENGRR-B5): a LEC killed by a signal is ABORTED, never FAIL_PREFLOOR NOT EQUIVALENT
def _aborted(k, env, pol, run, timeout=30):
    (k / "lec_async.ready").write_text(f"{pol}\n{run}\n")
    t = time.time()
    while not (k / "lec_async.done").exists() and time.time() - t < timeout:
        time.sleep(0.1)
    assert (k / "lec_async.done").exists()
    return _finish(k, env, 0)


def test_sigterm_and_sigkill_are_aborted_not_neq(tmp_path):
    for i, (pol, sig, rc) in enumerate((("nz", "TERM", 143), ("nz", "KILL", 137), ("1", "TERM", 143))):
        d = tmp_path / str(i)
        d.mkdir()
        k, env = _kit(d, 0)
        assert _aborted(k, env, pol, f"echo lec >> /work/lec_run.log; kill -{sig} $$") == "0"    # the flow rc stands
        rec = (k / "lec_async.aborted").read_text()
        assert rec.startswith(f"ABORTED rc={rc} oom=no "), rec
        assert not (k / "FAIL_PREFLOOR").exists() and not (k / "lec_async.stop").exists()
        assert not (k / "flow.stopped").exists() and not (k / "lec_async.rc").exists()
        # no later scope may take it as a finished proof
        assert not (k / "lec_async.ready").exists() and not (k / "lec_async.identity").exists()
        log = (k / "lec_async.log").read_text()
        assert f"aborted by signal (exit {rc}, OOM evidence no)" in log and "NOT EQUIVALENT" not in log


def test_signal_with_oom_evidence_is_recorded_as_oom(tmp_path):
    k, env = _kit(tmp_path, 0)
    assert _aborted(k, env, "nz", "echo 'Killed process 4242 (yosys)' >> /work/lec_run.log; kill -KILL $$") == "0"
    assert (k / "lec_async.aborted").read_text().startswith("ABORTED rc=137 oom=yes ")
    assert not (k / "FAIL_PREFLOOR").exists()
    (tmp_path / "b").mkdir()
    k2, env2 = _kit(tmp_path / "b", 0)
    (k2 / "oomkilled").touch()                                    # docker inspect State.OOMKilled true
    assert _aborted(k2, env2, "1", "kill -KILL $$") == "0"
    assert (k2 / "lec_async.aborted").read_text().startswith("ABORTED rc=137 oom=yes ")


def test_real_neq_exit1_unchanged_under_nz(tmp_path):
    k, env = _kit(tmp_path, 0)
    (k / "lec_async.ready").write_text("nz\necho 'LEC NOT EQUIVALENT: x' >> /work/lec_run.log; exit 1\n")
    t = time.time()
    while not (k / "flow.stopped").exists() and time.time() - t < 30:
        time.sleep(0.1)
    assert _finish(k, env, 137, 5) == "5"
    assert "LEC NOT EQUIVALENT" in (k / "FAIL_PREFLOOR").read_text() and (k / "lec_async.stop").exists()
    assert (k / "lec_async.rc").read_text().strip() == "1" and not (k / "lec_async.aborted").exists()


def test_kit_wave_does_not_read_aborted_lec_as_neq_or_infra():
    import sys
    sys.path.insert(0, str(HERE.parent / "autopilot"))
    import kit_wave
    log = ("LEC_ASYNC 2026-11-06 10:00:00 aborted by signal (exit 137, OOM evidence no): no LEC verdict, "
           "the kit needs a fresh LEC\n[ERROR PDN-0006] bad grid\n")
    cls, why = kit_wave.classify("route", log)
    assert "PDN-0006" in why and "LEC" not in why, (cls, why)
