"""WAVE-PREPNR-1115: bind.py kit-rtl --kit uses os.path.abspath at function level; os must be a MODULE-level import
(the first patch raised NameError in die-source bind.py versions that import os only inside functions)."""
import ast
import sys
from pathlib import Path

DP = Path(__file__).resolve().parents[1] / "tools" / "die_plan"
sys.path.insert(0, str(DP))


def test_bind_has_module_level_os_import():
    tree = ast.parse((DP / "bind.py").read_text())
    top = {a.name for n in tree.body if isinstance(n, ast.Import) for a in n.names}
    assert "os" in top


def test_kit_rtl_kit_arg_name_resolves():
    src = (DP / "bind.py").read_text()
    tree = ast.parse(src)
    top = {a.name for n in tree.body if isinstance(n, ast.Import) for a in n.names}
    users = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "os"]
    assert users and "os" in top
    import bind
    assert hasattr(bind, "os")
