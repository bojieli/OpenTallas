"""core_islands.site: SRAM-aware equal-load in-core islands within the entry maze limit (MASTER-PLAN, QC-SU-LAT)."""
import core_islands as CI


def _geo():
    # 200 x 200 core, centre entry, one SRAM wall west of the entry; sinks in 4 corner clusters
    sinks = [(x + dx, y + dy) for x, y in ((20, 20), (20, 180), (180, 20), (180, 180))
             for dx in range(0, 10, 2) for dy in range(0, 10, 2)]
    return dict(core_um=[0, 0, 200, 200], entry_um=[100, 100], sinks=sinks,
                macros=[dict(name="m", rect_um=[60, 40, 90, 160], ck_um=None)])


def test_site_legal_equal_load_within_entry_limit():
    r = CI.site(_geo(), k=4, max_entry_um=110.0)
    assert r["verdict"] == "PASS" and r["entry_maze_um"]["max"] <= 110.0
    assert sorted(q["load_frac"] for q in r["islands"]) == [0.25] * 4
    for q in r["islands"]:
        x0, y0, x1, y1 = q["rect_um"]
        assert not (x0 < 92.2 and x1 > 57.8 and y0 < 162.2 and y1 > 37.8), q      # clears SRAM + halo
        assert abs(x0 / 4.32 - round(x0 / 4.32)) < 1e-6
    c = [tuple(q["centre_um"]) for q in r["islands"]]
    assert len(set(c)) == 4 and r["floor_entry_to_sink_maze_um"] <= r["equal_path_um"]


def test_site_refuses_when_no_site_reachable():
    g = _geo()
    import pytest
    with pytest.raises(ValueError, match="legal island sites"):
        CI.site(g, k=4, max_entry_um=2.0)
