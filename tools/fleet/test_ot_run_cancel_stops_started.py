"""CANCEL-STOP-1119: ot-run --cancel also stops the started job (ot-heavy-stop --match <its --dir>) on the client's hosts."""
import importlib.machinery, importlib.util, pathlib, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_cancel_stop", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_cancel_stop", l)); l.exec_module(RUN)
RUN.HEAD_STOP = "/nonexistent/ot-heavy-stop"   # HEADSTOP-1124: these tests pin the host-side command text; test_ot_run_head_stop.py covers the inline head copy


def test_targets_are_the_clients_own_tag_never_the_lane_dir():
    hit = {111: (["--mem", "48", "--hosts", "epyc2,epyc7", "--dir", "/srv/x/lane", "--", "bash", "bind.sh"], "/srv/x/lane"),
           222: (["--mem", "48", "--hosts", "epyc2", "--dir", "/srv/x/lane", "--", "bash", "proof.sh"], "/srv/x/lane")}
    got = RUN.stop_targets({111: hit[111]}, "bind", ["epyc8"], node="hub")
    assert got == [("epyc2", "otrun-hub-111-", 111), ("epyc7", "otrun-hub-111-", 111)]      # nothing names /srv/x/lane or pid 222: the proof kit is not matched
    assert all("lane" not in t for _, t, _p in got)


def test_stop_started_runs_ot_heavy_stop_over_ssh():
    calls = []
    RUN.stop_started([("epyc2", "/x/kit one", 1)], run=lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(stdout="ot-heavy-stop: 1 scope(s) stopped\n", stderr=""))[1])
    assert calls[0][-2] == "epyc2" and calls[0][-1] == "ot-heavy-stop --match '/x/kit one'"


def test_a_prefix_matching_two_clients_is_refused_without_all(monkeypatch, capsys):
    cl = {1: (["--hosts", "epyc2", "--dir", "/srv/x/lane", "--", "bash", "bind_a.sh"], "/srv/x/lane"), 2: (["--hosts", "epyc2", "--dir", "/srv/x/lane", "--", "bash", "bind_b.sh"], "/srv/x/lane")}
    monkeypatch.setattr(RUN, "clients", lambda: cl)
    killed = []
    monkeypatch.setattr(RUN.os, "kill", lambda p, s: killed.append(p))
    assert RUN.cancel("bind_", False) == 1 and killed == []                                   # CANCEL-EXACT-1122: a prefix matches nothing
    assert RUN.cancel("/srv/x/lane", False) == 2 and killed == []                             # one exact dir, two clients: refused without --all-dirs
    assert "REFUSED" in capsys.readouterr().out
    monkeypatch.setattr(RUN, "stop_started", lambda t, **k: None)
    monkeypatch.setattr(RUN, "stop_by_path", lambda paths, **k: [])
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    assert RUN.cancel("bind_a.sh", False) == 0 and killed == [1]                              # one exact job: fine


def test_the_exact_container_of_a_cancelled_job_is_stopped_by_name_after_the_scope_step():
    """CANCEL-CONTAINER-1120: ot-heavy-stop found 0 scopes for a sealed QC route job and its container ran on; the exact dpkit container(s) are stopped by name too"""
    calls = []
    RUN.stop_started([("epyc10", "otrun-hub-3010423-", 3010423)], path="/srv/opentallas-scratch2/claude/kw43/items/cbn_q00/gen/cbn_q00",
                     run=lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(stdout="containers stopped: dpkit-cbn_q00-2769332\n" if "docker stop" in cmd[-1] else "ot-heavy-stop: 0 scope(s) stopped\n", stderr=""))[1])
    assert [c[-1].split()[0] for c in calls] == ["ot-heavy-stop", "names=$(ps"]
    cmd = calls[1][-1]
    assert "grep -F -e otrun-hub-3010423- -e '-v /srv/opentallas-scratch2/claude/kw43/items/cbn_q00/gen/cbn_q00:'" in cmd
    assert "docker stop -t 30" in cmd and "grep -v grep" not in cmd and "dpkit-[A-Za-z0-9_.-]*" in cmd and "docker rm" not in cmd and "docker ps -a" not in cmd


def test_the_container_stop_command_selects_only_the_named_job(tmp_path):
    """run the generated command against a fake ps / docker: only the container whose docker-run line carries the tag or the exact kit mount is stopped"""
    import os, subprocess
    fake = tmp_path / "bin"; fake.mkdir()
    (fake / "ps").write_text("#!/bin/bash\ncat <<'E'\n/usr/bin/docker run --rm --name dpkit-keep-1 --cpus=8 -v /srv/x/lane/other:/work img\n"
                             "/bin/bash /usr/local/lib/ot-heavy/bin/docker run --rm --name dpkit-cbn_q00-2769332 -e TAG=otrun-hub-3010423-1795 -v /srv/x/lane/kit:/work img bash -lc if grep -q x /work/y; then :; fi\n"
                             "/usr/bin/docker run --rm --name dpkit-bymount-7 -v /srv/x/lane/exact/gen/t:/work img\nE\n")
    (fake / "docker").write_text("#!/bin/bash\necho \"$@\" >> " + str(tmp_path / "stopped") + "\n")
    for f in fake.iterdir():
        f.chmod(0o755)
    out = subprocess.run(["bash", "-c", RUN.container_stop_cmd("otrun-hub-3010423-", "/srv/x/lane/exact/gen/t")], capture_output=True, text=True, env=dict(os.environ, PATH=str(fake) + ":" + os.environ["PATH"])).stdout
    stopped = (tmp_path / "stopped").read_text().split("\n")
    stopped = [x for x in stopped if x.startswith("stop")]
    assert sorted(x for x in stopped if x) == ["stop -t 30 dpkit-bymount-7", "stop -t 30 dpkit-cbn_q00-2769332"] and "dpkit-keep-1" not in out
    assert "dpkit-cbn_q00-2769332" in out


def test_a_moved_job_is_found_and_stopped_on_the_host_where_it_runs(capsys):
    """CANCEL-MOVED-1120 (CANCEL-UNSIGNABLE-1120: REHOST / spill moved 7 of 11 jobs off the client's --hosts): the client named epyc2, the container runs on epyc9; the fleet pass stops it there and confirms"""
    calls = []

    def run(cmd, **k):
        calls.append(cmd)
        host = cmd[-2] if cmd[0] == "ssh" else "local"
        text = cmd[-1]
        if "docker stop" in text:
            out = "containers stopped: dpkit-moved-7\n" if host == "epyc9" else "containers stopped: none\n"
        else:
            out = "ot-heavy-stop: 0 scope(s) stopped\n"
        return types.SimpleNamespace(stdout=out, stderr="")
    got = RUN.stop_started([("epyc2", "otrun-hub-555-", 555)], run=run, path="/srv/x/items/t7/attempt_3/gen/t7", fleet=["epyc2", "intel1", "epyc9", "epyc10"])
    out = capsys.readouterr().out
    assert ("epyc9", "containers stopped: dpkit-moved-7") in got
    assert "epyc9 (moved job, not in the client's --hosts): containers stopped: dpkit-moved-7" in out
    stop_hosts = [c[-2] for c in calls if c[0] == "ssh" and "docker stop" in c[-1]]
    assert stop_hosts == ["epyc2", "intel1", "epyc9", "epyc10"]            # client host first, then every other fleet host once; the client host is not asked twice
    assert "no running container" not in out


def test_nothing_anywhere_is_said_and_a_container_that_survives_is_reported(capsys):
    RUN.stop_started([("epyc2", "otrun-hub-555-", 555)], fleet=["epyc2", "epyc9"], path=None,
                     run=lambda cmd, **k: types.SimpleNamespace(stdout="containers stopped: none\n" if "docker stop" in cmd[-1] else "x\n", stderr=""))
    assert "no running container of this job found on any fleet host" in capsys.readouterr().out
    cmd = RUN.container_stop_cmd("otrun-hub-555-", "/srv/x/k")
    assert "STILL RUNNING after docker stop" in cmd and "docker ps -q -f name=^$n$" in cmd


def test_cancel_passes_the_whole_fleet_and_the_local_host_runs_without_ssh(monkeypatch):
    seen = {}
    orig = RUN.stop_started
    monkeypatch.setattr(RUN, "clients", lambda: {9: (["--hosts", "epyc2", "--dir", "/srv/x/lane", "--", "bash", "k.sh"], "/srv/x/lane")})
    monkeypatch.setattr(RUN.os, "kill", lambda p, s: None)
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "stop_started", lambda t, **k: seen.update(k))
    assert RUN.cancel("k.sh", False) == 0 and seen["fleet"] == list(RUN.HOSTS) and "localhost" in seen["fleet"]
    calls = []
    orig([("epyc2", "otrun-hub-1-", 1)], fleet=["localhost"], run=lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(stdout="containers stopped: none\n", stderr=""))[1])
    assert any(c[0] == "bash" and "docker stop" in c[-1] for c in calls)                   # localhost: direct, no ssh


def test_cancel_never_matches_a_substring_of_a_bystander_waiter(monkeypatch):
    """CANCEL-EXACT-1122 (FABLE-FLOW-2200 item 4): 3 bystander waiters died because their bash -c text contained the selector"""
    unit = "oth-ubuntu-1-2"
    cl = {5: (["--dir", "/srv/x/a", "--", "bash", "-c", f"until ot-wait {unit}; do sleep 9; done"], "/srv/x/a"),
          6: (["--dir", "/srv/x/b", "--", "bash", "job.sh"], "/srv/x/b")}
    monkeypatch.setattr(RUN, "clients", lambda: cl)
    killed = []
    monkeypatch.setattr(RUN.os, "kill", lambda p, s: killed.append(p))
    monkeypatch.setattr(RUN, "cancel_unit", lambda s: 1)
    for sel in (unit, "job", "/srv/x", "ot-wait", "x/b"):
        RUN.cancel(sel, False)
    assert killed == []
    monkeypatch.setattr(RUN, "stop_started", lambda t, **k: None)
    monkeypatch.setattr(RUN, "stop_by_path", lambda paths, **k: [])
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    assert RUN.cancel("6", False) == 0 and killed == [6]
    assert RUN.cancel("/srv/x/a/", False) == 0 and killed == [6, 5]
