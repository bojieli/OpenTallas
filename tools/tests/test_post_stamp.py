"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-1000 class 10): post.sh stamps on the Los Angeles clock and corrects a wrong hand-written stamp"""
import os, subprocess, tempfile
from pathlib import Path
POST = Path(__file__).resolve().parents[2] / "bin/post.sh"


def run(text):
    d = Path(tempfile.mkdtemp())
    (d / "bin").mkdir()
    (d / "bin/coord-commit.sh").write_text("#!/bin/bash\nexit 0\n")
    r = subprocess.run(["bash", str(POST), "L", text], env=dict(os.environ, COORD_DIR=str(d)), capture_output=True, text=True)
    return (d / "lanes/posts/L.md").read_text().splitlines()[0], r.stderr


def now(fmt="%Y-%m-%d %H:%M"):
    return subprocess.run(["date", "+" + fmt], env=dict(os.environ, TZ="America/Los_Angeles"), capture_output=True, text=True).stdout.strip()


def test_unstamped_gets_la_stamp():
    line, _ = run("READY x")
    assert line.startswith("- " + now()[:13]) and line.endswith(" READY x") and " PST " in line or " PDT " in line


def test_wrong_hand_stamp_is_replaced():
    line, err = run("- 2026-11-15 18:30 PST READY [A -> B] y")        # UTC clock written as PST
    assert not line.startswith("- 2026-11-15 18:30") and "READY [A -> B] y" in line and "restamped" in err


def test_right_hand_stamp_is_kept():
    stamp = now()
    line, err = run("- %s PST READY z" % stamp)
    assert line == "- %s PST READY z" % stamp and err == ""
