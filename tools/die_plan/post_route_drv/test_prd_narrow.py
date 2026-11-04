"""OT_PRD_NARROW_PINS / OT_ECO_FROM opt-ins are carried through every staging step (DIE-HEAD-59 11-03)."""
from pathlib import Path

H = Path(__file__).resolve().parent


def test_narrow_pins_carried_and_force_ripped():
    hook = (H / "prd_hook.tcl").read_text()
    assert "OT_PRD_NARROW_PINS" in hook and "odb::dbBox_create" in hook and "ot_prd_force_rip" in hook
    assert "::ot_prd_force_rip" in (H / "prd_route_keep.tcl").read_text()
    assert "OT_PRD_NARROW_PINS=%q" in (H / "prd_mk.sh").read_text()
    run = (H / "prd_run.sh").read_text()
    assert '-e "OT_PRD_NARROW_PINS=' in run and "OT_PRD_NARROW_PINS=;" in run and 'OT_PRD_NARROW_PINS="$' in run


def test_eco_from_override():
    assert 'os.environ.get("OT_ECO_FROM")' in (H.parent / "eco_loop.py").read_text()
