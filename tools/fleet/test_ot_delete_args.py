"""FLEET-OPS 11-25 (KV-HGI-WGATE: `ot-delete --help` took --help as a path): unknown dash arguments are refused before anything is deleted; -h / --help print usage."""
import importlib.machinery, importlib.util, os, subprocess, sys
from pathlib import Path

P = str(Path(__file__).with_name("ot-delete"))
_l = importlib.machinery.SourceFileLoader("ot_delete_args", P)
D = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_delete_args", _l))
_l.exec_module(D)


class Guard:
    def __init__(self): self.seen = []
    def refuse(self, t, protected=None):
        self.seen.append(t); return None


def run(argv, tmp):
    g = Guard(); gone = []
    rc = D.main(argv, guard=g, rmtree=lambda t: gone.append(t), root_ok=lambda t: False)
    return rc, g.seen, gone


def test_help_prints_usage_and_touches_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for a in ("--help", "-h"):
        rc, seen, gone = run([a], tmp_path)
        assert rc == 0 and seen == [] and gone == []
    assert "ot-delete" in capsys.readouterr().out


def test_unknown_dash_argument_is_refused_before_any_target_is_touched(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    t = tmp_path / "tree"; t.mkdir()
    for argv in (["--hlep"], ["-x", str(t)], [str(t), "--force"], ["--dry", "-r", str(t)]):
        rc, seen, gone = run(argv, tmp_path)
        assert rc == 2 and seen == [] and gone == [] and t.exists(), argv
    assert "unknown option" in capsys.readouterr().err


def test_known_flag_and_double_dash_still_work(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    t = tmp_path / "tree"; t.mkdir()
    dash = tmp_path / "-odd"; dash.mkdir()
    rc, seen, gone = run(["--dry", str(t)], tmp_path)
    assert rc == 0 and seen == [str(t)] and gone == []
    rc, seen, gone = run(["--", "-odd"], tmp_path)
    assert rc == 0 and seen == [str(dash)] and gone == [str(dash)]
    rc, seen, gone = run([str(t)], tmp_path)
    assert gone == [str(t)]


def test_cli_exit_code_for_a_mistyped_flag(tmp_path):
    r = subprocess.run([sys.executable, P, "--hlep"], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2 and "unknown option" in r.stderr
