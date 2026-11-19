"""FLOW-HEALTH-1 11-19 (COORD): the hub-installed copies (fail_route.py, the coord-guard hooks) are in the ot-tools-drift table"""
import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("otts_copies", str(HERE / "ot-tools-sync"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def sha(b):
    return hashlib.sha256(b).hexdigest()


def test_table_names_fail_route_and_the_guard_hooks():
    m = load()
    pairs = dict(m.INSTALLED_COPIES)
    assert pairs["~/.local/lib/fail-route/fail_route.py"] == "tools/autopilot/fail_route.py"
    assert "tools/fleet/coord-branch-guard/post-checkout" in pairs.values()


def test_same_differs_missing_and_unlisted(tmp_path):
    m = load()
    a, b, c = tmp_path / "a.py", tmp_path / "b.py", tmp_path / "missing.py"
    a.write_bytes(b"x = 1\n")
    b.write_bytes(b"stale\n")
    man = {"tools/autopilot/a.py": sha(b"x = 1\n"), "tools/autopilot/b.py": sha(b"x = 2\n"), "tools/autopilot/c.py": sha(b"c\n")}
    copies = [[str(a), "tools/autopilot/a.py"], [str(b), "tools/autopilot/b.py"], [str(c), "tools/autopilot/c.py"], [str(a), "tools/autopilot/not_shipped.py"]]
    out = m.copies_diffs(man, copies, host="h")
    assert len(out) == 2 and "b.py differs from main tools/autopilot/b.py" in out[0] and "missing.py missing" in out[1]
    assert m.copies_diffs({}, copies) == []


def test_installed_diffs_includes_the_copies(monkeypatch, tmp_path):
    m = load()
    f = tmp_path / "fr.py"
    f.write_bytes(b"old\n")
    monkeypatch.setattr(m, "INSTALLED_COPIES", [[str(f), "tools/autopilot/fail_route.py"]])
    class R:
        stdout = "{}\n"
    out = m.installed_diffs({"tools/autopilot/fail_route.py": sha(b"new\n")}, hosts=[], runner=lambda *a, **k: R())
    assert any("fr.py differs from main tools/autopilot/fail_route.py" in x for x in out)
