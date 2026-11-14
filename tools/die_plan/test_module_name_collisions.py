"""Top-level module names of physical/die_plan/s81 must not shadow tools/die_plan: both directories land on sys.path
(tests, run_v4.sh), and an s81 census_cov.py once made check.py's 'import census_cov' fail order-dependently
(AttributeError: no attribute coverage) in test_xdie under xdist."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_s81_modules_do_not_shadow_tools_die_plan():
    tools = {p.name for p in (ROOT / "tools/die_plan").glob("*.py")}
    s81 = {p.name for p in (ROOT / "physical/die_plan/s81").glob("*.py")}
    assert sorted(tools & s81) == []
