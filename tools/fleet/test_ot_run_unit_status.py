"""FLOW-OPS-1300 item 14: `ot-run --status TARGET` reports that one job (queued / running / done rc / died / missing) with a stable exit status."""
import importlib.machinery, importlib.util, json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
_l = importlib.machinery.SourceFileLoader("ot_run_unit_status", str(HERE / "ot-run"))
M = importlib.util.module_from_spec(importlib.util.spec_from_loader(_l.name, _l))
_l.exec_module(M)


def _rec(d, name, **kw):
    r = dict(schema="opentallas.ot_status.v1", kind="run", name=name, unit="", host="h1", pid=11, pid_start=5, lane="L",
             cmd="--mem 8 --job kv3_pv_v6_a5 -- bash x", log="/x.log", t_start=1795315600, state="running", rc=None, t_end=None)
    r.update(kw)
    (d / (name + ".json")).write_text(json.dumps(r))


def test_states_and_exit_codes(tmp_path):
    _rec(tmp_path, "otrun-h1-11", unit="oth-a-1")
    _rec(tmp_path, "otrun-h1-12", pid=12)
    _rec(tmp_path, "otrun-h1-13", pid=13, unit="oth-a-3", state="done", rc=0)
    _rec(tmp_path, "otrun-h1-14", pid=14, unit="oth-a-4", state="done", rc=2, cmd="--job zz_unique_job")
    _rec(tmp_path, "otrun-h1-15", pid=15, unit="oth-a-5")
    live = lambda r: r["pid"] in (11, 12)
    assert M.unit_status("oth-a-1", str(tmp_path), live)[0] == 75
    c, ln = M.unit_status("otrun-h1-11", str(tmp_path), live)
    assert c == 75 and ln.startswith("RUNNING") and "unit=oth-a-1" in ln
    c, ln = M.unit_status("otrun-h1-12", str(tmp_path), live)
    assert c == 76 and ln.startswith("QUEUED")
    assert M.unit_status("oth-a-3", str(tmp_path), live)[0] == 0
    c, ln = M.unit_status("zz_unique_job", str(tmp_path), live)
    assert c == 2 and ln.startswith("DONE rc=2")
    c, ln = M.unit_status("oth-a-5", str(tmp_path), live)
    assert c == 71 and ln.startswith("DIED")
    c, ln = M.unit_status("oth-nope", str(tmp_path), live)
    assert c == 66 and ln.startswith("MISSING")


def test_cli_status_unit_is_not_the_fleet_table(tmp_path):
    sd = tmp_path / "st"
    sd.mkdir()
    _rec(sd, "otrun-h1-21", pid=21, unit="oth-b-1", state="done", rc=3)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "OT_STATUS_DIR": str(sd)}
    r = subprocess.run([sys.executable, "-I", str(HERE / "ot-run"), "--status", "oth-b-1"], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 3, (r.stdout, r.stderr)
    assert r.stdout.startswith("DONE rc=3") and len(r.stdout.splitlines()) == 1
    r = subprocess.run([sys.executable, "-I", str(HERE / "ot-run"), "--status", "oth-missing"], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 66 and r.stdout.startswith("MISSING")
