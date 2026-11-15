"""REPO-STATE-1: tools/repo_size_guard.py rejects new large/generated files outside the allowlist."""
import os, subprocess as S, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tools" / "repo_size_guard.py"


def git(d, *a):
    S.run(["git", *a], cwd=d, check=True, capture_output=True,
          env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))


def guard(d, *a):
    return S.run([sys.executable, "-I", str(GUARD), *a], cwd=d, capture_output=True, text=True)


def repo():
    d = Path(tempfile.mkdtemp())
    git(d, "init", "-q", "-b", "main")
    (d / "README").write_text("x\n")
    git(d, "add", "."); git(d, "commit", "-qm", "base")
    return d


def test_small_source_passes():
    d = repo()
    (d / "tools").mkdir(); (d / "tools/a.py").write_text("print(1)\n")
    (d / "rtl").mkdir(); (d / "rtl/m.sv").write_text("module m; endmodule\n")
    git(d, "add", "."); git(d, "commit", "-qm", "c")
    r = guard(d, "--range", "HEAD~1..HEAD", "--allowlist", str(d / "none"))
    assert r.returncode == 0, r.stdout


def test_large_and_generated_rejected_and_allowlist():
    d = repo()
    (d / "results").mkdir()
    (d / "results/big.bin").write_bytes(os.urandom(6_000_000))
    (d / "results/x.odb").write_bytes(b"odb")
    (d / "results/n.v").write_text("wire a;\n" * 200_000)              # 1.6 MB netlist
    (d / "results/small.json").write_text("{}\n")
    git(d, "add", "."); git(d, "commit", "-qm", "c")
    r = guard(d, "--range", "HEAD~1..HEAD", "--allowlist", str(d / "none"))
    assert r.returncode == 1
    for p in ("results/big.bin", "results/x.odb", "results/n.v"):
        assert f"REJECT {p}" in r.stdout
    assert "small.json" not in r.stdout
    (d / "allow.txt").write_text("# reviewed\nresults/*.odb\nresults/big.bin\nresults/n.v\n")
    assert guard(d, "--range", "HEAD~1..HEAD", "--allowlist", str(d / "allow.txt")).returncode == 0


def test_staged_mode():
    d = repo()
    (d / "chip.gds.gz").write_bytes(b"g")
    git(d, "add", ".")
    r = guard(d, "--staged", "--allowlist", str(d / "none"))
    assert r.returncode == 1 and "REJECT chip.gds.gz" in r.stdout


def test_hard_cap_ignores_allowlist():
    d = repo()
    (d / "plan.json").write_bytes(b"x" * 2_000_000)
    git(d, "add", "."); git(d, "commit", "-qm", "c")
    (d / "allow.txt").write_text("plan.json\n")
    assert guard(d, "--range", "HEAD~1..HEAD", "--allowlist", str(d / "allow.txt")).returncode == 0
    r = guard(d, "--range", "HEAD~1..HEAD", "--allowlist", str(d / "allow.txt"), "--hard-mb", "1")
    assert r.returncode == 1 and "hard cap" in r.stdout
