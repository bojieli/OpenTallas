"""QC-STA-HOP 11-25: station_site honours explicit_stage0 (bs[j] = stage j), legacy slots unchanged."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_hop_scan as D

AP, BP = (600.0, 5.0, "E"), (5.0, 1339.0, "N")
CELL = [1.0, 0.0]
BS5 = [[[540.0, 250.0]], [[220.0, 250.0]], [[7.0, 363.0]], [[7.0, 688.0]], [[7.0, 1013.0]]]


def test_explicit_stage0_uses_all_sites():
    s = {"stations": 5, "width": 0, "explicit_stage0": True, "bit_sites_um": BS5, "bit_site_cell_um": CELL}
    pts = [D.station_site(s, j, 0, AP, BP, normal=False) for j in range(5)]
    assert pts == [(540.5, 250.0), (220.5, 250.0), (7.5, 363.0), (7.5, 688.0), (7.5, 1013.0)]
    assert D.station_site(s, 0, 0, AP, BP, normal=True) == (540.5, 250.0)


def test_legacy_mapping_unchanged():
    s = {"stations": 5, "width": 0, "bit_sites_um": BS5[:4], "bit_site_cell_um": CELL}
    assert D.station_site(s, 0, 0, AP, BP, normal=True) == D.input_site(AP)
    assert D.station_site(s, 0, 0, AP, BP, normal=False) == D.input_site(AP)
    assert [D.station_site(s, j, 0, AP, BP) for j in range(1, 5)] == [(540.5, 250.0), (220.5, 250.0), (7.5, 363.0), (7.5, 688.0)]
    # explicit_stage0 without a complete stage-0 table keeps the legacy mapping
    s2 = dict(s, explicit_stage0=True)
    assert D.station_site(s2, 1, 0, AP, BP) == (540.5, 250.0)


def test_mutant_legacy_would_drop_last_stage():
    s = {"stations": 5, "width": 0, "explicit_stage0": True, "bit_sites_um": BS5, "bit_site_cell_um": CELL}
    last = D.station_site(s, 4, 0, AP, BP, normal=False)
    assert D.md(last, D.input_site(BP)) < 405   # build-model last hop
    assert D.md((7.5, 688.0), D.input_site(BP)) > 600   # the phantom the old mapping reported
