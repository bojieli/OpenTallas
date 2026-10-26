"""Pre-route utilisation gate: macro-dominated tiles are judged on std-cell density over the placeable area."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as RT
import textbook_lint as TL


def test_macro_dominated_tile_passes_on_density():
    # qfd_tt_head_static_h13: 5,827 um2 cells + 26,639 um2 SRAM in 41,608 um2 core (old rule: 78% -> FAIL)
    blocks = [{"w": 26639.0 / 160.0, "h": 160.0}]       # 26,639 um2
    m = RT.util_metrics(5827.0, blocks, 41608.0, 2.16)
    assert abs(m["total_fill"] - (5827 + 26639) / 41608) < 1e-6
    assert 0.30 < m["density"] < 0.50
    assert RT.util_severity(m) == ("INFO", True)


def test_macro_tile_dense_cells_still_fail_and_fill_bound():
    blocks = [{"w": 100.0, "h": 100.0}]
    m = RT.util_metrics(9000.0, blocks, 22000.0, 2.16)     # density ~0.82
    assert RT.util_severity(m)[0] == "FAIL"
    m = RT.util_metrics(1000.0, [{"w": 150.0, "h": 150.0}], 22000.0 - 0.0, 0.0)   # fill 1.05 > 0.90, density low
    assert m["total_fill"] > RT.FILL_MAX and RT.util_severity(m) == ("FAIL", False)


def test_no_macro_kit_never_advises_shrink():
    # OWNER 10-19/10-21: < 40% roomy = INFO (acceptable), 40-60% OK, > 60% WARN (enlarge), > 70% FAIL (unchanged)
    for std, core, want in ((1000.0, 4000.0, ("INFO", False)), (1500.0, 4000.0, ("INFO", False)),
                            (1700.0, 4000.0, ("INFO", True)), (2000.0, 4000.0, ("INFO", True)),
                            (2400.0, 4000.0, ("INFO", True)), (2600.0, 4000.0, ("WARN", False)),
                            (3000.0, 3900.0, ("FAIL", False))):
        m = RT.util_metrics(std, [], core)
        assert m["util"] == std / core and RT.util_severity(m) == want


def _dump(std_n, macro_bbox):
    return {"core": [0, 0, 200, 208], "masters": {"INVx1": {"n": std_n, "w": 0.2, "h": 0.27}},
            "macros": [{"name": "m", "bbox": macro_bbox}] if macro_bbox else []}


def test_textbook_util_macro_density_and_no_macro_identical():
    F, M = {}, {}
    TL.util_findings(_dump(100000, [0, 0, 161, 165.4]), dict(TL.THRESHOLDS), F, M)   # std 5400, macro 26.6k
    assert "util_channel" not in F and M["std_density"] < 0.5 and M["total_fill"] > 0.65
    F, M = {}, {}
    TL.util_findings(_dump(100000, None), dict(TL.THRESHOLDS), F, M)                   # 5400/41600 = 13% < 40%
    assert "util_channel" not in F and "roomy; acceptable" in M["util_note"] and "std_density" not in M
    F, M = {}, {}
    TL.util_findings(_dump(540000, None), dict(TL.THRESHOLDS), F, M)                   # 29160/41600 = 70% > 60%
    assert "enlarge the outline" in F["util_channel"][0]
    assert not any("shrink" in x for x in F["util_channel"] if "never shrink" not in x)
