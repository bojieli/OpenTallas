"""CANCEL-STOP-1119: ot-run --cancel also stops the started job (ot-heavy-stop --match <its --dir>) on the client's hosts."""
import importlib.machinery, importlib.util, pathlib, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_cancel_stop", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_cancel_stop", l)); l.exec_module(RUN)


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
    assert RUN.cancel("bind_", False) == 2 and killed == []
    assert "REFUSED" in capsys.readouterr().out
    monkeypatch.setattr(RUN, "stop_started", lambda t: None)
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    assert RUN.cancel("bind_a", False) == 0 and killed == [1]                                  # one exact job: fine


def test_the_exact_container_of_a_cancelled_job_is_stopped_by_name_after_the_scope_step():
    """CANCEL-CONTAINER-1120: ot-heavy-stop found 0 scopes for a sealed QC route job and its container ran on; the exact dpkit container(s) are stopped by name too"""
    calls = []
    RUN.stop_started([("epyc10", "otrun-hub-3010423-", 3010423)], path="/srv/opentallas-scratch2/claude/kw43/items/cbn_q00/gen/cbn_q00",
                     run=lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(stdout="containers stopped: dpkit-cbn_q00-2769332\n" if "docker stop" in cmd[-1] else "ot-heavy-stop: 0 scope(s) stopped\n", stderr=""))[1])
    assert [c[-1].split()[0] for c in calls] == ["ot-heavy-stop", "names=$(ps"]
    cmd = calls[1][-1]
    assert "grep -F -e otrun-hub-3010423- -e '-v /srv/opentallas-scratch2/claude/kw43/items/cbn_q00/gen/cbn_q00:'" in cmd
    assert "docker stop -t 30" in cmd and "grep -v grep" not in cmd and "dpkit-[A-Za-z0-9_.-]*" in cmd and "docker rm" not in cmd and "docker ps" not in cmd


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
    assert sorted(x for x in stopped if x) == ["stop -t 30 dpkit-bymount-7", "stop -t 30 dpkit-cbn_q00-2769332"] and "dpkit-keep-1" not in out
    assert "dpkit-cbn_q00-2769332" in out
