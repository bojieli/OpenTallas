"""OTRUN-ORPHAN 11-23: (1) killing an ot-run client whose job is admitted stops the remote unit (or exits 79 REMOTE-RUNNING, never a plain failure
while the unit runs on: QC-V4 lost ~2 h when publish_apply's watchdog killed only the intel2 client and the epyc8 bind finished clean); (2) --cancel
finds a job by its ot-heavy unit and by its tag whatever ot-run copy / wrapper started the client."""
import importlib.machinery, importlib.util, json, os, pathlib, signal, subprocess, sys, textwrap, time, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_client_kill", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_client_kill", l)); l.exec_module(RUN)
RUN.HEAD_STOP = "/nonexistent/ot-heavy-stop"   # HEADSTOP-1124: these tests pin the host-side command text; test_ot_run_head_stop.py covers the inline head copy


def fake(stdout):
    calls = []
    def run(argv, **k):
        calls.append(argv)
        return types.SimpleNamespace(stdout=stdout, stderr="", returncode=0)
    return run, calls


def test_stop_remote_unit_stops_unit_and_tag_then_confirms_gone():
    run, calls = fake("ot-heavy-stop: 1 scope(s) stopped\nOT_RUN_UNIT_GONE\n")
    ok, line = RUN.stop_remote_unit("epyc8", "oth-ubuntu-12-34", "otrun-hub-777-123456", run=run)
    assert ok and "1 scope(s) stopped" in line
    sh = calls[0][-1]
    assert calls[0][-2] == "epyc8" and "ot-heavy-stop --unit oth-ubuntu-12-34" in sh and "ot-heavy-stop --tag otrun-hub-777-" in sh and "is-active" in sh


def test_stop_remote_unit_unconfirmed_or_unknown_is_not_ok():
    run, _ = fake("ot-heavy-stop: 0 scope(s) stopped\nOT_RUN_UNIT_ACTIVE\n")
    assert RUN.stop_remote_unit("epyc8", "oth-ubuntu-12-34", "otrun-hub-777-1", run=run)[0] is False
    run, calls = fake("")
    assert RUN.stop_remote_unit("epyc8", "?", "otrun-hub-777-1", run=run)[0] is False and calls == []


DRIVER = textwrap.dedent('''
    import importlib.machinery, importlib.util, subprocess, sys, pathlib
    l = importlib.machinery.SourceFileLoader("drv", sys.argv[1])
    RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("drv", l)); l.exec_module(RUN)
    mark, stop_ok = sys.argv[2], sys.argv[3] == "1"
    real = subprocess.Popen
    # the "ssh": prints the admission line of this client's tag, then runs on like a long remote job
    RUN.subprocess.Popen = lambda argv, stderr=None: real(["bash", "-c", "t=$(echo \\"$0\\" | grep -o 'otrun-[^ ]*' | head -1); "
        "echo \\"ot-heavy: admitted on epyc9 as oth-ubuntu-55-66 after 0 s\\" >&2; echo ready > " + mark + ".ready; sleep 60", argv[-1]], stderr=stderr)
    def stop_remote_unit(host, unit, tag, run=None):
        pathlib.Path(mark + ".stop").write_text(f"{host} {unit} {tag}")
        return stop_ok, "fake stop"
    RUN.stop_remote_unit = stop_remote_unit
    RUN.ticket_touch = lambda *a, **k: None
    if len(sys.argv) > 4 and sys.argv[4] == "lease":     # a --dir lease renewer thread runs beside the client, as in every lane job
        RUN.start_leases(["/srv/x/kit"], "o", take=lambda *a: None, release=lambda *a: None, ttl_h=1)
    print(RUN.run("epyc9", 1, ["true"]))
''')


def drive(tmp_path, sig, stop_ok=True, env=None, lease=False):
    drv = tmp_path / "drv.py"; drv.write_text(DRIVER)
    mark = str(tmp_path / "m")
    e = dict(os.environ, HOME=str(tmp_path), OT_STATUS_DIR=str(tmp_path / "st"), **(env or {}))
    e.pop("OT_RUN_DETACH_ON_SIGNAL", None) if not env else None
    p = subprocess.Popen([sys.executable, "-I", str(drv), str(H / "ot-run"), mark, "1" if stop_ok else "0"] + (["lease"] if lease else []), stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=e)
    for _ in range(200):
        if os.path.exists(mark + ".ready"):
            break
        time.sleep(0.05)
    time.sleep(0.3)                      # the client has read the admission line
    p.send_signal(sig)
    out, err = p.communicate(timeout=60)
    stop = pathlib.Path(mark + ".stop")
    return p.returncode, err, (stop.read_text() if stop.exists() else None)


def test_sigterm_on_an_admitted_client_stops_the_remote_unit(tmp_path):
    rc, err, stop = drive(tmp_path, signal.SIGTERM)
    assert rc == 143 and stop is not None and stop.startswith("epyc9 oth-ubuntu-55-66 otrun-")
    assert "was STOPPED with its client" in err and "REMOTE-RUNNING" not in err


def test_unconfirmed_stop_exits_remote_running_79(tmp_path):
    rc, err, stop = drive(tmp_path, signal.SIGTERM, stop_ok=False)
    assert rc == RUN.REMOTE_RUNNING_EXIT == 79 and stop is not None
    assert "REMOTE-RUNNING epyc9 oth-ubuntu-55-66" in err and "ot-wait oth-ubuntu-55-66" in err


def test_sighup_and_detach_keep_the_unit_and_exit_79(tmp_path):
    rc, err, stop = drive(tmp_path, signal.SIGHUP)
    assert rc == 79 and stop is None and "REMOTE-RUNNING epyc9 oth-ubuntu-55-66" in err
    (tmp_path / "m.ready").unlink()
    rc, err, stop = drive(tmp_path, signal.SIGTERM, env={"OT_RUN_DETACH_ON_SIGNAL": "1"})
    assert rc == 79 and stop is None


def test_every_client_entry_point_is_a_client_but_not_other_ot_run_tools():
    for x in ("/srv/x/rt/current/tools/fleet/ot-run", "/home/u/.local/lib/kw44/ot-run", "/home/u/.local/lib/fleet/kw44-seal-ap/ot-run-sealed",
              "/x/ot-run-ap", "/x/ot-run.bak-kw44-e6gone-1109", "/x/ot-run.1123"):
        assert RUN.is_client_exe(x), x
    for x in ("/x/ot-run-lane-declare", "/x/ot-runner", "/x/not-ot-run", "/usr/bin/python3"):
        assert not RUN.is_client_exe(x), x


def test_client_matches_its_own_tag_and_status_name_only():
    node = os.uname().nodename
    rest = ["--mem", "4", "--dir", "/srv/x/lane", "--", "bash", "a.sh"]
    for sub in (f"otrun-{node}-4242-", f"otrun-{node}-4242-987654", f"otrun-{node}-4242"):
        assert RUN.client_matches(sub, 4242, rest, "/srv/x/lane"), sub
    for sub in (f"otrun-{node}-424-", f"otrun-{node}-42420-1", "otrun-otherhost-4242-", f"otrun-{node}-4242-x"):
        assert not RUN.client_matches(sub, 4242, rest, "/srv/x/lane"), sub


def test_a_sealed_job_client_matches_its_kit_dir_not_the_shared_jobs_root(tmp_path):
    kit = "/srv/opentallas-scratch2/claude/kw/items/coll_core/gen/coll_core"
    spec = tmp_path / "sealed-x.json"
    spec.write_text(json.dumps({"name": "coll_core-place", "root": "/srv/opentallas-scratch2/claude/ot-jobs",
                                "work": {"at": kit, "seed": [{"path": kit + "/"}]}, "return": {"to": kit, "paths": ["."]}}))
    rest = ["--mem", "48", "--hosts", "intel1", "--job", str(spec), "--dir", "/srv/opentallas-scratch2/claude/ot-jobs", "--", "python3", "-c", "x"]
    assert RUN.client_matches(kit, 9, rest, "/srv/opentallas-scratch2/claude/ot-jobs")
    assert RUN.client_matches(kit + "/", 9, rest, "/srv/opentallas-scratch2/claude/ot-jobs")
    assert not RUN.client_matches("/srv/opentallas-scratch2/claude/kw/items/other", 9, rest, "/srv/opentallas-scratch2/claude/ot-jobs")
    assert not RUN.client_matches(kit, 9, rest[:4] + [str(tmp_path / "missing.json")] + rest[5:], "/srv/opentallas-scratch2/claude/ot-jobs")


def test_unit_clients_and_tag_units_read_the_status_records(tmp_path):
    st = tmp_path / "st"; st.mkdir()
    (st / "a.json").write_text(json.dumps({"name": "otrun-hub-11", "pid": 11, "unit": "oth-ubuntu-1-2", "state": "running"}))
    (st / "b.json").write_text(json.dumps({"name": "otrun-hub-12", "pid": 12, "unit": "oth-ubuntu-3-4", "state": "running"}))
    assert RUN.unit_clients("oth-ubuntu-1-2", d=str(st), alive=lambda r: True) == [11]
    assert RUN.unit_clients("oth-ubuntu-1-2", d=str(st), alive=lambda r: False) == []
    assert RUN.unit_clients("oth-ubuntu-1", d=str(st), alive=lambda r: True) == []
    assert RUN.tag_units("otrun-hub-11-", d=str(st)) == ["oth-ubuntu-1-2"]
    assert RUN.tag_units("otrun-hub-11-55", d=str(st)) == ["oth-ubuntu-1-2"]
    assert RUN.tag_units("otrun-hub-1-", d=str(st)) == []


def test_cancel_by_unit_signals_the_client_that_recorded_it(monkeypatch):
    cl = {11: (["--mem", "4", "--dir", "/srv/x/a", "--", "bash", "bind.sh"], "/srv/x/a"), 12: (["--mem", "4", "--dir", "/srv/x/b", "--", "bash", "p.sh"], "/srv/x/b")}
    monkeypatch.setattr(RUN, "clients", lambda: cl)
    monkeypatch.setattr(RUN, "unit_clients", lambda u: [11] if u == "oth-ubuntu-1-2" else [])
    killed, units = [], []
    monkeypatch.setattr(RUN.os, "kill", lambda p, s: killed.append(p))
    monkeypatch.setattr(RUN, "stop_started", lambda t, **k: None)
    monkeypatch.setattr(RUN, "stop_by_path", lambda paths, **k: [])
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "note_cancel_reason", lambda *a, **k: None)
    monkeypatch.setattr(RUN, "cancel_unit", lambda sub, **k: (units.append(sub), 0)[1])
    assert RUN.cancel("oth-ubuntu-1-2", False) == 0 and killed == [11] and units == ["oth-ubuntu-1-2"]


def test_cancel_by_tag_without_client_also_stops_the_recorded_unit(monkeypatch):
    monkeypatch.setattr(RUN, "tag_units", lambda t: ["oth-ubuntu-7-8"])
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    run, calls = fake("ot-heavy-stop: 1 scope(s) stopped\n")
    assert RUN.cancel_unit("otrun-hub-77-", run=run, fleet=["epyc9"]) == 0
    assert [c[-1] for c in calls] == ["ot-heavy-stop --tag otrun-hub-77-", "ot-heavy-stop --unit oth-ubuntu-7-8"]


def test_a_wrappers_inner_client_is_found_below_it():
    me, parent = os.getpid(), os.getppid()
    cl = {me: (["--", "x"], None), 1: (["--", "y"], None)}
    assert list(RUN.descendant_clients({parent}, cl)) == [me]
    assert RUN.descendant_clients({me}, cl) == {}


def test_a_lease_thread_does_not_swallow_the_kill(tmp_path):
    """measured on epyc11 11-23: with the --dir lease renewer running, `kill` reached that thread, SIGTERM's default action ended the client silently
    and the admitted unit ran on; helper threads now block the signals so run()'s watcher takes them"""
    rc, err, stop = drive(tmp_path, signal.SIGTERM, lease=True)
    assert rc == 143 and stop is not None and "was STOPPED with its client" in err
