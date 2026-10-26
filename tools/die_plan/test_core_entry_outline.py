"""COORD RULING QC-PLAN-F4A (3): hard-core clock entries derive from the CURRENT outline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import master_plan as M  # noqa: E402

H = dict(module="m", outline_um=[250.56, 216.0])


def test_default_is_current_outline_centre():
    assert M.core_entry(H, None) == ((125.28, 108.0), "centre")


def test_entry_bound_to_old_outline_is_stale():
    xy, src = M.core_entry(H, {"m": dict(xy=[129.6, 169.0], outline_um=[259.2, 276.48])})
    assert xy == (125.28, 108.0) and "STALE" in src


def test_entry_bound_to_current_outline_is_used():
    xy, src = M.core_entry(H, {"m": dict(xy=[125.28, 0.019], outline_um=[250.56, 216.0], source="edge pin")})
    assert xy == (125.28, 0.019) and src == "edge pin"


def test_unbound_legacy_entry_unchanged():
    assert M.core_entry(H, {"m": dict(xy=[177.12, 135.0])})[0] == (177.12, 135.0)
