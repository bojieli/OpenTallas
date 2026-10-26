"""INPROCESS-SYNC: stale/missing tools/ref_tile + hier_contract files follow main; daemon-only edits stay (ROOT 2026-10-15)."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as cl  # noqa: E402


def _g(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True).stdout.strip()


def test_sync_stale_and_missing_keep_daemon_only(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tools/ref_tile").mkdir(parents=True)
    _g(tmp_path, "init", "-q", str(repo)); _g(repo, "config", "user.email", "t@t"); _g(repo, "config", "user.name", "t")
    (repo / "tools/ref_tile/a.py").write_text("v1\n"); (repo / "tools/ref_tile/b.py").write_text("b1\n")
    _g(repo, "add", "."); _g(repo, "commit", "-qm", "1")
    (repo / "tools/ref_tile/a.py").write_text("v2\n"); (repo / "tools/ref_tile/c.py").write_text("c\n")
    _g(repo, "add", "."); _g(repo, "commit", "-qm", "2")
    head = _g(repo, "rev-parse", "HEAD")
    daemon = tmp_path / "daemon"
    (daemon / "tools/closure_loop").mkdir(parents=True); (daemon / "tools/ref_tile").mkdir(parents=True)
    (daemon / "tools/ref_tile/a.py").write_text("v1\n")            # older main version -> synced
    (daemon / "tools/ref_tile/b.py").write_text("daemon edit\n")   # daemon-only -> kept
    with patch.object(cl, "REPO", repo), patch.object(cl, "HERE", daemon / "tools/closure_loop"), \
            patch.object(cl, "log", lambda *a: None), patch.dict(cl._OVL, {"hist": {}}):
        got = cl.inprocess_stale_sync(head)
    assert sorted(got) == ["tools/ref_tile/a.py", "tools/ref_tile/c.py"]
    assert (daemon / "tools/ref_tile/a.py").read_text() == "v2\n"
    assert (daemon / "tools/ref_tile/c.py").read_text() == "c\n"
    assert (daemon / "tools/ref_tile/b.py").read_text() == "daemon edit\n"
    assert cl._RESTART["why"] is None                               # nothing of the fixture is imported


def test_restart_waits_for_background_work():
    class F:
        def __init__(self, done):
            self._d = done

        def done(self):
            return self._d
    with patch.dict(cl._RESTART, {"why": "x"}), patch.object(cl, "log", lambda *a: None), \
            patch.object(cl, "_HOUSE_FUTURE", F(False)), patch.object(cl, "_RECOVERY_FUTURE", None):
        assert cl.restart_if_requested() is False
    with patch.dict(cl._RESTART, {"why": "x"}), patch.object(cl, "log", lambda *a: None), \
            patch.object(cl, "_HOUSE_FUTURE", F(True)), patch.object(cl, "_RECOVERY_FUTURE", None):
        try:
            cl.restart_if_requested()
            raise AssertionError("expected SystemExit")
        except SystemExit as ex:
            assert ex.code == 0


def test_ref_gate_modules_reimport(tmp_path):
    import types
    fake_root = tmp_path / "d"
    (fake_root / "tools/ref_tile").mkdir(parents=True)
    (fake_root / "tools/closure_loop").mkdir(parents=True)
    (fake_root / "tools/ref_tile/pre_route_gate.py").write_text("V = 1\n")
    with patch.object(cl, "HERE", fake_root / "tools/closure_loop"), patch.object(cl, "log", lambda *a: None), \
            patch.dict(cl._INPROC, {"gen": 0, "loaded_gen": 0}):
        sys.modules.pop("pre_route_gate", None)
        m = cl.ref_gate_modules()
        assert m.V == 1
        (fake_root / "tools/ref_tile/pre_route_gate.py").write_text("V = 2  # regenerated generator\n")
        assert cl.ref_gate_modules().V == 1          # no sync generation change: the loaded module stays
        cl._INPROC["gen"] += 1
        assert cl.ref_gate_modules().V == 2          # after an INPROCESS-SYNC the module is re-imported
        sys.modules.pop("pre_route_gate", None)
        sys.path.remove(str(fake_root / "tools/ref_tile"))
