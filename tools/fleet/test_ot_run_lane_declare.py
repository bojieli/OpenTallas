"""KW-FIX-44 ISOLATION step 3: a lane job must declare its inputs (--dir / --stage, or a sealed --job spec).
WARN today, REFUSED (exit 96) from 2026-11-10 12:00 PST.  The mutant: a job reading another lane's dir is refused."""
from importlib.machinery import SourceFileLoader
from pathlib import Path

M = SourceFileLoader("lane_declare", str(Path(__file__).with_name("ot-run-lane-declare"))).load_module()
D = "/srv/opentallas-scratch2/claude/lane-a/run1"
OTHER = "/srv/opentallas-scratch2/claude/lane-b/gen/split_clean.json"


def test_declared_job_passes():
    assert M.check(["--mem", "8", "--dir", D, "--", "bash", "-c", f"cd {D} && make -f {D}/Makefile"]) == []
    assert M.check(["--mem", "8", "--dir", D, "--stage", "/srv/x/lib", "--", "cat", "/srv/x/lib/a.lib"]) == []
    assert M.check(["--mem", "8", "--job", "/tmp/spec.json", "--", "cat", OTHER]) == []        # sealed spec declares
    assert M.check(["--status"]) is None and M.check(["--cancel", "x"]) is None


def test_mutant_undeclared_path_is_named():
    bad = M.check(["--mem", "8", "--dir", D, "--", "bash", "-c", f"cd {D} && python3 tool.py {OTHER}"])
    assert bad == [(OTHER, "command")]


def test_script_contents_are_read_comments_and_globs_are_not(tmp_path, monkeypatch):
    s = tmp_path / "run.sh"
    s.write_text(f"# reads /srv/opentallas-scratch2/claude/comment/x\ncp {OTHER} .\nls /srv/opentallas*/claude/\n")
    monkeypatch.setattr(M, "RX", __import__("re").compile(r"(?:/(?:srv|home|mnt|archive|media)|" + str(tmp_path) +
                                                           r")/[A-Za-z0-9_.+@%=,:-]+(?:/[A-Za-z0-9_.+@%=,:-]+)*"))
    bad = M.check(["--mem", "8", "--dir", str(tmp_path), "--", "bash", str(s)])
    assert bad == [(OTHER, str(s))]


def test_modes(tmp_path, monkeypatch, capsys):
    mf = tmp_path / "mode"
    monkeypatch.setattr(M, "MODE_FILE", str(mf))
    monkeypatch.setattr(M, "LOG", str(tmp_path / "log.tsv"))
    argv = ["--mem", "8", "--dir", D, "--", "cat", OTHER]
    assert M.mode(now=M.ENFORCE_AT - 1) == "warn" and M.mode(now=M.ENFORCE_AT) == "enforce"     # auto (no file)
    mf.write_text("warn\n")
    assert M.main(argv) == 0 and "ISOLATION WARN" in capsys.readouterr().err
    mf.write_text("enforce\n")
    assert M.main(argv) == 96
    err = capsys.readouterr().err
    assert "REFUSED" in err and OTHER in err
    assert M.main(["--mem", "8", "--dir", D, "--", "ls", D]) == 0
    mf.write_text("off\n")
    assert M.main(argv) == 0
    assert (tmp_path / "log.tsv").read_text().count(OTHER) == 2
