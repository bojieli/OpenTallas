"""FABLE-FLOW-1900 (E): ot-gate-remote validates its arguments and never runs on the hub or localhost."""
import os, pathlib, subprocess

G = str(pathlib.Path(__file__).with_name("ot-gate-remote"))


def run(host, *a):
    env = dict(os.environ, OT_GATE_HOSTNAME=host, OT_GATE_CHECK_ONLY="1")
    return subprocess.run(["bash", G, *a], capture_output=True, text=True, env=env, timeout=30)


def test_refuses_on_hub_and_localhost():
    for h in ("tolerant-swine", "ubuntu", "intel2", "localhost"):
        r = run(h, "claude/x@abcdef1")
        assert r.returncode == 64 and "REFUSED" in r.stderr, h


def test_help_and_unknown_flags_print_usage_and_do_not_run():
    for a in (("--help",), ("-h",), ("--force", "claude/x@abcdef1"), ()):
        r = run("dear-crayfish", *a)
        assert r.returncode == 2 and "usage: ot-gate-remote" in r.stderr, a


def test_missing_or_bad_branch_sha_is_rejected():
    for a in (("claude/x",), ("main@abcdef1",), ("claude/x@xyz",), ("claude/x@abcdef1", "many"), ("claude/x@abcdef1", "16", "extra")):
        assert run("dear-crayfish", *a).returncode == 2, a


def test_good_arguments_pass_the_check_on_a_build_host():
    assert run("dear-crayfish", "claude/fleet-ops-r-x-1117@efd13f60fdb", "16").returncode == 0
    assert run("epyc2", "claude/a/b@0123456789abcdef0123456789abcdef01234567").returncode == 0


def test_obsolete_gate_ref_refuses_before_slot_setup(tmp_path):
    ssh = tmp_path / "ssh"
    ssh.write_text("#!/bin/sh\nprintf 'REFUSED obsolete exact tip\n'\nexit 2\n")
    ssh.chmod(0o755)
    env = dict(os.environ, OT_GATE_HOSTNAME="key-cardinal", OT_GATE_CHECK_ONLY="0",
               PATH=str(tmp_path) + os.pathsep + os.environ["PATH"])
    result = subprocess.run(["bash", G, "claude/x@abcdef1"], env=env,
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 2
    assert "INFRA gate ref claude/x@abcdef1 (rc 2): REFUSED obsolete exact tip" in result.stdout
    assert "slot" not in result.stdout
