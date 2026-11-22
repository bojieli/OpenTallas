"""FLOW-FLEET-R2 S1: bin/utf8_guard.py + post.sh / coord-commit.sh refuse invalid UTF-8 (0x94 in COORD.md skipped autopilot steps for ~1 h)."""
import os
import subprocess
from pathlib import Path

BIN = Path(__file__).resolve().parents[2] / "bin"
G = BIN / "utf8_guard.py"


def guard(*a, inp=b""):
    return subprocess.run(["python3", "-I", str(G), *a], input=inp, capture_output=True)


def test_text_mode():
    assert guard("--text", inp="ok café".encode()).returncode == 0
    r = guard("--text", inp=b"bad \x94 byte")
    assert r.returncode == 1 and b"0x94" in r.stderr and b"line 1" in r.stderr


def _repo(tmp_path):
    g = lambda *a: subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    g("init", "-q"); g("config", "user.email", "a@b"); g("config", "user.name", "t")
    (tmp_path / "a.md").write_bytes(b"old \x94 line\nsecond\n")        # a bad byte already in history must not block unrelated appends
    g("add", "a.md"); g("commit", "-qm", "x")
    return tmp_path


def test_files_mode_checks_only_added_lines(tmp_path):
    r = _repo(tmp_path)
    with open(r / "a.md", "ab") as f:
        f.write(b"fine new line\n")
    assert guard("--files", str(r), "a.md").returncode == 0
    with open(r / "a.md", "ab") as f:
        f.write(b"new \x94 bad\n")
    x = guard("--files", str(r), "a.md")
    assert x.returncode == 1 and b"a.md" in x.stderr and b"0x94" in x.stderr
    (r / "n.tsv").write_bytes(b"a\t\xff\n")                             # untracked: whole file
    assert guard("--files", str(r), "n.tsv").returncode == 1
    (r / "b.bin").write_bytes(b"\xff\xfe")                              # not a text extension
    assert guard("--files", str(r), "b.bin").returncode == 0


def test_post_sh_refuses_bad_text(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/coord-commit.sh").write_text("#!/bin/bash\nexit 0\n")
    (tmp_path / "bin/utf8_guard.py").write_bytes(G.read_bytes())
    env = dict(os.environ, COORD_DIR=str(tmp_path))
    r = subprocess.run(["bash", str(BIN / "post.sh"), "L", b"READY bad \x94 x"], env=env, capture_output=True)
    assert r.returncode != 0 and b"invalid UTF-8" in r.stderr and not (tmp_path / "lanes/posts/L.md").exists()
    r = subprocess.run(["bash", str(BIN / "post.sh"), "L", "READY good café"], env=env, capture_output=True)
    assert r.returncode == 0 and (tmp_path / "lanes/posts/L.md").exists()
