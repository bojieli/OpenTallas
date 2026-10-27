"""Canary checkers survive source-worktree retirement and do not reuse imported tools."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import canary as C


def test_face_cover_loads_exact_requested_guard(tmp_path):
    net = tmp_path / "n.v"
    net.write_text("module top; endmodule")
    for name, verdict in [("good", "PASS"), ("mutant", "FAIL")]:
        tools = tmp_path / name
        tools.mkdir()
        (tools / "face_guard.py").write_text(
            "def guard(*a, **kw): return dict(top='top',verdict='" + verdict + "',checked=1,ok=1,fail_counts={},fails={})\n"
            "def parse(*a): return {'top': type('Top', (), {'ports': []})()}\n")
        assert C.face_cover(net, None, die_plan_dir=tools)["verdict"] == verdict


def test_submit_pins_checker_from_source():
    source = (HERE / "canary.py").read_text()
    assert '(src / "tools" / "die_plan" / "face_guard.py").read_bytes()' in source
    assert 'run / "checker_tools" / "die_plan"' in source
