import importlib.machinery
import os
import pathlib
import sys

P = str(pathlib.Path(__file__).with_name("ot-push-main"))


def _load():
    ld = importlib.machinery.SourceFileLoader("opm_basetemp", P)
    m = type(sys)("opm_basetemp")
    m.__file__ = P
    ld.exec_module(m) if hasattr(ld, "exec_module") else None
    return ld.load_module()


def test_each_gate_run_gets_its_own_pytest_basetemp_and_tmpdir(monkeypatch, tmp_path):
    """P-PUSH-GATE-FLAKE: two overlapping gate runs must not share /tmp/pytest-of-<user>"""
    m = _load()
    seen = []
    monkeypatch.setattr(m, "widen_for", lambda *_a, **_k: False)
    monkeypatch.setattr(m, "xdist_workers", lambda *_a, **_k: 0)
    monkeypatch.setattr(m, "test_sources", lambda t: [])
    monkeypatch.setattr(m.S, "run", lambda *a, **k: type("R", (), {"returncode": 0})())

    def fake_once(cmd, timeout):
        bt = cmd[cmd.index("--basetemp") + 1]
        seen.append((bt, os.environ.get("TMPDIR")))
        assert os.path.isdir(os.path.dirname(bt))
        return 0, ""

    monkeypatch.setattr(m, "run_tests_once", fake_once)
    monkeypatch.setenv("OT_PUSH_TMPROOT", str(tmp_path))
    old = os.environ.get("TMPDIR")
    assert m.run_tests(["tools/x/test_a.py"], 60) == 0 and m.run_tests(["tools/x/test_a.py"], 60) == 0
    assert seen[0][0] != seen[1][0] and seen[0][1] != seen[1][1]
    assert all(str(tmp_path) in bt and bt.startswith(tmpd) for bt, tmpd in seen)
    assert not [p for p in tmp_path.iterdir()]            # each run removed its own temp dir
    assert os.environ.get("TMPDIR") == old                  # and restored TMPDIR
