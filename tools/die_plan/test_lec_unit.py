"""KW-FIX-24/LECUNIT 11-06 (COORD 19:2x (6)): the async pre-route LEC runs as its OWN admitted unit
(ot-heavy --mem ... -- docker run --name NAME-lec), not docker exec inside the flow container, so a flow OOM no longer
kills an 8-h LEC.  Fake docker + fake ot-heavy on PATH.
    python3 -m pytest -q tools/die_plan/test_lec_unit.py"""
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "lec_async.sh"

FAKE_DOCKER = r'''#!/bin/bash
# fake docker. run: the LEC unit (bash -c CMD with /work -> kit, own process group); stop NAME-lec kills it.
op=$1; shift
case $op in
run) echo "$*" >> "$FAKE_K/docker_run.args"
     while [ $# -gt 0 ]; do case $1 in bash) shift; [ "$1" = -lc ] && shift; CMD=$1; shift;; *) shift;; esac; done
     CMD=${CMD//\/work/$FAKE_K}; CMD=${CMD//source \/OpenROAD-flow-scripts\/env.sh/true}
     # like the docker CLI: no "Killed" job notice of this shell in the log
     { setsid bash -c "$CMD" 2>&3 & echo $! > "$FAKE_K/unit.pid"; wait $!; } 3>&2 2>/dev/null; exit $?;;
exec) echo "$*" >> "$FAKE_K/docker_exec.args"; while [ $# -gt 0 ]; do case $1 in bash) shift; [ "$1" = -lc ] && shift; CMD=$1; shift;; *) shift;; esac; done
     CMD=${CMD//\/work/$FAKE_K}; CMD=${CMD//source \/OpenROAD-flow-scripts\/env.sh/true}; bash -c "$CMD"; exit $?;;
inspect) if [ "$1" != -f ]; then
           [[ "$1" = *-lec ]] && exit 1
           printf '[{"State":{"Running":true},"Mounts":[{"Source":"%s"}]}]\n' "$FAKE_K"
         elif [[ "$*" = *HostConfig.Binds* ]]; then echo "$FAKE_K:/work"; echo "/srv/extra:/extra:ro"
         elif [[ "$*" = *Config.Env* ]]; then printf 'PATH=/usr/bin\nHOSTNAME=abc\nOT_KIT_IR=defer\n'
         elif [[ "$*" = *range*Mounts* ]]; then [[ "${!#}" = *-lec ]] && { [ -f "$FAKE_K/stale_unit" ] && echo "$FAKE_K" || exit 1; }; echo "$FAKE_K"
         elif [[ "$*" = *OOMKilled* ]]; then [[ "${!#}" = *-lec ]] && [ -f "$FAKE_K/oomkilled" ] && echo true || echo false
         else [ -f "$FAKE_K/flow.exited" ] && echo false || echo true; fi;;
stop) echo "${!#}" >> "$FAKE_K/docker_stop.names"
      if [[ "${!#}" = *-lec ]]; then P=$(cat "$FAKE_K/unit.pid" 2>/dev/null); [ -z "$P" ] || kill -KILL -- -"$P" 2>/dev/null
      else touch "$FAKE_K/flow.stopped"; fi;;
rm) echo "$*" >> "$FAKE_K/docker_rm.args";;
top) printf 'PID COMMAND\n123 bash /work/lec_async.sh wait /work\n';;
esac
'''

FAKE_OT_HEAVY = r'''#!/bin/bash
# fake ot-heavy: records its admission request, NOT RUN when K/noadmit, else runs the command
echo "$*" >> "$FAKE_K/ot_heavy.args"
[ -f "$FAKE_K/noadmit" ] && { echo "ot-heavy: NOT RUN" >&2; exit 75; }
while [ $# -gt 0 ] && [ "$1" != -- ]; do shift; done; shift
exec "$@"
'''


def _kit(tmp_path, **extra):
    k = tmp_path / "kit"
    k.mkdir()
    (k / "lec.py").write_text("")
    dk = tmp_path / "docker"
    dk.write_text(FAKE_DOCKER)
    dk.chmod(0o755)
    b = tmp_path / "bin"
    b.mkdir()
    (b / "ot-heavy").write_text(FAKE_OT_HEAVY)
    (b / "ot-heavy").chmod(0o755)
    (k / "lec_async.sh").write_text(TOOL.read_text())
    env = dict(os.environ, OT_LEC_ASYNC_POLL="0.2", FAKE_K=str(k), PATH=f"{b}:{os.environ['PATH']}")
    for v in ("OT_LECUNIT", "OT_LEC_MEM_GB", "OT_LECUNIT_CPUS"):
        env.pop(v, None)
    env.update(extra)
    subprocess.run(["bash", str(TOOL), "start", str(k), "flowc", "img", "4", "2", str(dk)], check=True, env=env)
    return k, env


def _until(p, timeout=30):
    t = time.time()
    while not p() and time.time() - t < timeout:
        time.sleep(0.1)
    return p()


def _finish(k, env, rc, stop=None):
    args = ["bash", str(TOOL), "finish", str(k), str(rc)] + ([str(stop)] if stop is not None else [])
    return subprocess.run(args, check=True, env=env, capture_output=True, text=True, timeout=60).stdout.strip()


def _wait(k, env, rc):
    return subprocess.run(["bash", str(TOOL), "wait", str(k), "flowc", "route", str(rc)], check=True, env=env,
                          capture_output=True, text=True, timeout=30).stdout


def test_lec_runs_in_its_own_admitted_unit(tmp_path):
    k, env = _kit(tmp_path)
    assert (k / "lec_async.mode").read_text().strip() == "unit"
    (k / "lec_async.ready").write_text("1\nsleep 2; echo EQ >> /work/lec_run.log; exit 0\n")
    assert _until(lambda: (k / "docker_run.args").exists())
    t = time.time()
    _wait(k, env, 0)                      # the flow container does not stay alive for its LEC
    assert time.time() - t < 1.5 and not (k / "lec_async.rc").exists()
    assert _finish(k, env, 4) == "4"      # finish on the host waits for the verdict
    assert (k / "lec_async.rc").read_text().strip() == "0"
    assert not (k / "docker_exec.args").exists()
    oh = (k / "ot_heavy.args").read_text()
    assert oh.startswith("--mem 4 -- ") and " run --name flowc-lec " in oh
    run = (k / "docker_run.args").read_text()
    assert "--name flowc-lec" in run and "--memory=4g" in run and " img bash -lc" in run
    assert f"-v {k}:/work" in run and "-v /srv/extra:/extra:ro" in run            # the flow container's binds
    assert "-e OT_KIT_IR=defer" in run and "HOSTNAME" not in run                    # and its environment
    assert not (k / "lec_async.stop").exists() and not (k / "flow.stopped").exists()
    assert (k / "lec_async.unit_rc").read_text().strip() == "0" and not (k / "lec_async.aborted").exists()


def test_lec_mem_override_and_opt_out(tmp_path):
    (tmp_path / "a").mkdir()
    k, env = _kit(tmp_path / "a", OT_LEC_MEM_GB="16")
    (k / "lec_async.ready").write_text("1\nexit 0\n")
    assert _finish(k, env, 0) == "0"
    assert (k / "ot_heavy.args").read_text().startswith("--mem 16 -- ")
    assert "--memory=16g" in (k / "docker_run.args").read_text()
    (tmp_path / "b").mkdir()
    k2, env2 = _kit(tmp_path / "b", OT_LECUNIT="0")             # opt-out: the old docker exec form
    assert (k2 / "lec_async.mode").read_text().strip() == "exec"
    (k2 / "lec_async.ready").write_text("1\nexit 0\n")
    assert _finish(k2, env2, 0) == "0"
    assert "flowc bash -lc" in (k2 / "docker_exec.args").read_text()
    assert not (k2 / "docker_run.args").exists() and not (k2 / "ot_heavy.args").exists()


def test_not_equivalent_stops_the_flow_container(tmp_path):
    k, env = _kit(tmp_path)
    (k / "lec_async.ready").write_text("1\necho 'LEC NOT EQUIVALENT' >> /work/lec_run.log; exit 1\n")
    assert _until(lambda: (k / "flow.stopped").exists())
    assert _finish(k, env, 137, 5) == "5"
    assert "LEC NOT EQUIVALENT" in (k / "FAIL_PREFLOOR").read_text() and (k / "lec_async.stop").exists()
    assert (k / "lec_async.rc").read_text().strip() == "1" and not (k / "lec_async.aborted").exists()
    assert "flowc" in (k / "docker_stop.names").read_text().split()
    assert not (k / "docker_exec.args").exists()


def test_signal_kill_in_unit_is_aborted_with_oom_evidence(tmp_path):
    for i, (pol, oom) in enumerate((("nz", False), ("1", True))):
        d = tmp_path / str(i)
        d.mkdir()
        k, env = _kit(d)
        if oom:
            (k / "oomkilled").touch()                   # docker inspect flowc-lec State.OOMKilled true
        (k / "lec_async.ready").write_text(f"{pol}\necho lec >> /work/lec_run.log; kill -KILL $$\n")
        assert _until(lambda: (k / "lec_async.done").exists())
        assert _finish(k, env, 0) == "0"
        rec = (k / "lec_async.aborted").read_text()
        assert rec.startswith("ABORTED rc=137 oom=%s " % ("yes" if oom else "no")), rec
        assert not (k / "FAIL_PREFLOOR").exists() and not (k / "lec_async.stop").exists()
        assert not (k / "flow.stopped").exists() and not (k / "lec_async.rc").exists()
        assert not (k / "lec_async.ready").exists() and not (k / "lec_async.identity").exists()


def test_unit_that_never_ran_is_aborted_not_neq(tmp_path):
    k, env = _kit(tmp_path)
    (k / "noadmit").touch()
    (k / "lec_async.ready").write_text("nz\nexit 0\n")          # nz policy: an infra rc must still not stop the kit
    assert _until(lambda: (k / "lec_async.done").exists())
    assert _finish(k, env, 0) == "0"
    assert (k / "lec_async.aborted").read_text().startswith("ABORTED rc=75 oom=no ")
    assert not (k / "FAIL_PREFLOOR").exists() and not (k / "lec_async.stop").exists() and not (k / "lec_async.rc").exists()


def test_plan_stop_ends_the_unit_without_a_verdict(tmp_path):
    k, env = _kit(tmp_path)
    (k / "stale_unit").touch()                                  # a stopped leftover of this kit's unit is removed
    (k / "lec_async.ready").write_text("1\nsleep 60; exit 0\n")
    assert _until(lambda: (k / "unit.pid").exists())
    assert "LEC aborted" in _wait(k, env, 2)                    # no place checkpoint: the proof has no reader
    assert _finish(k, env, 2) == "2"
    assert "flowc-lec" in (k / "docker_stop.names").read_text().split()
    assert (k / "lec_async.done").exists() and not (k / "lec_async.rc").exists()
    assert not (k / "lec_async.stop").exists() and not (k / "FAIL_PREFLOOR").exists() and not (k / "flow.stopped").exists()
    assert not (k / "lec_async.ready").exists() and not (k / "lec_async.identity").exists()
    assert "-f flowc-lec" in (k / "docker_rm.args").read_text()
