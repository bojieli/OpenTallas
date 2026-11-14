"""FIX-QCFEED-1: write_phys must hand plan_path to Landings, or count-frame files (feed_*.json) resolve only via cwd."""
import ast
from pathlib import Path


def test_write_phys_passes_plan_path_to_landings():
    tree = ast.parse((Path(__file__).parent / "gen_phys.py").read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "write_phys")
    calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
             and c.func.attr == "Landings"]
    assert calls
    for c in calls:
        assert any(k.arg == "plan_path" for k in c.keywords)
