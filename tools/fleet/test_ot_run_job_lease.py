"""JOB-LEASE (FLOW-OPS-R2 11-22): an ot-run client leases its --dir, the scratch trees its command names and its rt/<sha>, renews them and
releases them on exit, so ot_delete_guard keeps a live job's inputs."""
import importlib.machinery, importlib.util, os, pathlib, sys
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_job_lease", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_job_lease", l)); l.exec_module(RUN)
sys.path.insert(0, str(H))
import ot_lease  # noqa: E402


def test_lease_paths_cover_dir_trees_stage_and_rt(tmp_path, monkeypatch):
    root = tmp_path / "srv" / "opentallas-scratch2" / "claude"
    kit = root / "lane" / "k" / "gen" / "T"; kit.mkdir(parents=True)
    script = root / "lane" / "k" / "gen" / "run_kit.sh"; script.write_text("x")
    tree = root / "lane" / "tree"; tree.mkdir()
    monkeypatch.setattr(RUN, "SCRATCH_RE", __import__("re").compile(r"^(" + str(tmp_path) + r"/srv/opentallas-scratch[^/]*/claude/[^/]+)(/|$)"))
    # the command scan only looks at /srv/opentallas-scratch* text: check it on the real prefix shape, with existence faked
    monkeypatch.setattr(RUN.os.path, "isdir", lambda x: x.endswith(("/T", "/tree", "/gen")))
    monkeypatch.setattr(RUN.os.path, "isfile", lambda x: x.endswith(".sh"))
    monkeypatch.setattr(RUN, "SCRATCH_RE", __import__("re").compile(r"^(/srv/opentallas-scratch[^/]*/claude/[^/]+)(/|$)"))
    cmd = ["bash", "-c", "bash /srv/opentallas-scratch2/claude/lane/k/gen/run_kit.sh /srv/opentallas-scratch2/claude/lane/k/gen/T route; ls /srv/opentallas-scratch2/claude/lane/tree"]
    got = RUN.lease_paths("/srv/opentallas-scratch2/claude/lane/k", cmd, ["/srv/opentallas-scratch3/claude/lane/in"],
                          real="/srv/opentallas-scratch2/claude/rt/0123456789ab/tools/fleet/ot-run", env={"OT_LEASE_PATHS": "/srv/opentallas-scratch2/claude/other/t:/etc"})
    assert got[0] == "/srv/opentallas-scratch2/claude/lane/k"
    for want in ("/srv/opentallas-scratch3/claude/lane/in", "/srv/opentallas-scratch2/claude/other/t", "/srv/opentallas-scratch2/claude/lane/k/gen",
                 "/srv/opentallas-scratch2/claude/lane/k/gen/T", "/srv/opentallas-scratch2/claude/lane/tree", "/srv/opentallas-scratch2/claude/rt/0123456789ab"):
        assert want in got, (want, got)
    assert "/etc" not in got and "/srv/opentallas-scratch2/claude" not in got and len(got) == len(set(got))


def test_leases_taken_renewed_released(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_LEASE_DIR", str(tmp_path / "leases"))
    monkeypatch.delenv("OT_RUN_NO_LEASE", raising=False)
    paths = ["/srv/opentallas-scratch2/claude/lane/k", "/srv/opentallas-scratch2/claude/rt/0123456789ab"]
    stop = RUN.start_leases(paths, "L/ot-run-h-1", take=ot_lease.take, release=ot_lease.release)
    live = ot_lease.leases()
    assert sorted(r["path"] for r in live) == sorted(paths)
    assert ot_lease.covering("/srv/opentallas-scratch2/claude/lane/k/run/results", live)       # the guard keeps what the job writes
    assert ot_lease.covering("/srv/opentallas-scratch2/claude/rt/0123456789ab/tools", live)
    stop(); stop()
    assert ot_lease.leases() == []
    monkeypatch.setenv("OT_RUN_NO_LEASE", "1")
    assert RUN.start_leases(paths, "x", take=ot_lease.take, release=ot_lease.release) is None and ot_lease.leases() == []
