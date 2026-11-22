"""FLOW-FLEET-R1 11-22 (COORD: waiters hit the 1 h / 12 h tool caps and missed events): ot-wait --durable = a detached watcher + a re-attachable
foreground; an end that happened while nobody was attached is reported on the next identical call."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import ot_status as S  # noqa: E402

WAIT = str(HERE / "ot-wait")


def run(tmp, *args):
    e = dict(os.environ, OT_STATUS_DIR=str(tmp / "st"), OT_STATUS_POST="0", OT_WAIT_DURABLE_DIR=str(tmp / "dur"), OT_WAIT_LEDGER=str(tmp / "w.tsv"))
    e.pop("OT_LANE", None)
    return subprocess.run([sys.executable, "-I", WAIT, *args], capture_output=True, text=True, env=e, timeout=60)


def rec(tmp, name, **kw):
    (tmp / "st").mkdir(exist_ok=True)
    r = dict(schema=S.SCHEMA, kind="run", name=name, unit="", host=S.host(), pid=os.getpid(), pid_start=S.pid_start(os.getpid()), lane="L", cmd="x",
             log="/l", t_start=1, state="running", rc=None, t_end=None)
    r.update(kw)
    (tmp / "st" / (name + ".json")).write_text(json.dumps(r))


def test_timeout_rearms_and_the_end_is_kept_for_the_next_call(tmp_path):
    rec(tmp_path, "otrun-h-9")                         # running: its client (this pytest process) is alive
    p = run(tmp_path, "--durable", "otrun-h-9", "--timeout", "2", "--poll", "0.2")
    assert p.returncode == 75 and "REARM" in p.stdout
    rec(tmp_path, "otrun-h-9", state="done", rc=3, t_end=5, unit="oth-x")     # ends while nobody is attached
    deadline = time.time() + 30
    while time.time() < deadline:
        outs = list((tmp_path / "dur").glob("*.out"))
        if outs and "OT_WAIT_RC=" in outs[0].read_text():
            break
        time.sleep(0.3)
    p = run(tmp_path, "--durable", "otrun-h-9", "--timeout", "5", "--poll", "0.2")
    assert p.returncode == 3 and p.stdout.startswith("DIED rc=3")


def test_watcher_argv_drops_durable_and_timeout():
    from importlib.machinery import SourceFileLoader
    W = SourceFileLoader("ot_wait_mod", WAIT).load_module()
    assert W.durable_argv(["--durable", "x", "--timeout", "30", "--poll=2", "--timeout=4"]) == ["x", "--poll=2"]
