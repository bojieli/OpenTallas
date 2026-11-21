"""FLOW-OPS-1000: git-history-shim puts history searches without a terminal under timeout, nothing else"""
import os
import subprocess
from pathlib import Path

SHIM = Path(__file__).resolve().with_name("git-history-shim")


def run(tmp_path, *args):
    fake = tmp_path / "realgit"
    fake.write_text("#!/bin/bash\necho \"PPID_CMD=$(tr '\\0' ' ' < /proc/$PPID/cmdline)\"\necho ARGS \"$@\"\n")
    fake.chmod(0o755)
    env = dict(os.environ, OT_REAL_GIT=str(fake))
    return subprocess.run([str(SHIM), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env).stdout


def test_history_searches_get_the_timeout(tmp_path):
    for args in (["log", "--all", "--oneline", "-S", "ring_declared"], ["-C", "repo", "log", "-Gfoo"], ["rev-list", "--all"],
                 ["-c", "core.pager=cat", "log", "--pickaxe-regex", "-Sx"]):
        out = run(tmp_path, *args)
        assert "PPID_CMD=timeout -k 30 600" in out, (args, out)
        assert "ARGS " + " ".join(args) in out


def test_other_calls_are_unchanged(tmp_path):
    for args in (["status"], ["log", "--oneline", "-3"], ["-C", "x", "show", "HEAD"], ["grep", "--all-match", "x"], ["commit", "-m", "--all"]):
        out = run(tmp_path, *args)
        assert "timeout" not in out.split("ARGS")[0], (args, out)
        assert "ARGS " + " ".join(args) in out


def test_limit_zero_turns_it_off(tmp_path):
    fake = tmp_path / "realgit"
    out = run(tmp_path, "log", "--all")
    assert "timeout" in out
    env = dict(os.environ, OT_REAL_GIT=str(fake), OT_GIT_SEARCH_TIMEOUT="0")
    out = subprocess.run([str(SHIM), "log", "--all"], stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env).stdout
    assert "timeout" not in out.split("ARGS")[0]
