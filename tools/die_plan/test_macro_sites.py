"""QC-SUST-MACRO-1119 (FABLE-CLOSURE lever 4): QC st macros are sited by connectivity, not on the quarter-height grid.
The fixture is the slw_st_b / slw_st_a geometry measured on the N46C wave kits: outline 622.08 x 1339.2, core input leaf
(311.04, 669.6), st_a u_r0 / cl_b_tw_data_i hard cores; the old grid left macros 450-740 um from these partners."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import macro_sites as MS  # noqa: E402

W, H = 622.08, 1339.2


def place(tn, t, macros):
    """the add_macro_sites placer in small: nearest free 8.64 site (halo 4.32) to each macro's target"""
    occ, out = [], {}
    for inst, size in macros:
        px, py = MS.target(tn, t, inst, size); w, h = size; best = None
        for i in range(-60, 61):
            for j in range(-60, 61):
                x, y = round((px + i * 8.64) / 8.64) * 8.64, round((py + j * 8.64) / 8.64) * 8.64
                a = [x - 4.32, y - 4.32, x + w + 4.32, y + h + 4.32]
                if a[0] < 8.64 or a[1] < 8.64 or a[2] > W - 8.64 or a[3] > H - 8.64:
                    continue
                if any(a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3] for b in occ):
                    continue
                k = (abs(i) + abs(j), abs(i), abs(j))
                if best is None or k < best[0]:
                    best = (k, x, y, a)
        assert best, inst
        occ.append(best[3]); out[inst] = [best[1], best[2]]
    return out


def st_b():
    t = {"outline_um": [W, H], "hard_cores": [],
         "internal_stations": [{"conn": "bus:x_st_a_i", "capture": "core", "leaf_um": [311.04, 669.6]},
                               {"conn": "bus:x_hc1_i", "capture": "core", "leaf_um": [311.04, 669.6]},
                               {"conn": "bus:x_st_b_o", "capture": "face flop", "leaf_um": [600.0, 1300.0]}]}
    macros = [(f"u_bound.u_u_r{r}.u_{m}.u_m.g_bank[0].u_m", [43.2, 25.92]) for r in (4, 5, 6, 7) for m in ("sks", "skn", "hb", "h9", "sw")]
    return t, macros


def test_st_b_macros_within_reach_of_core_leaf():
    t, macros = st_b(); got = place("slw_st_b_v2__x", t, macros)
    worst = max(MS.worst_gap("slw_st_b_v2__x", t, n, got[n], s) for n, s in macros)
    assert worst <= MS.REACH_UM, worst


def test_old_quarter_height_grid_was_out_of_reach():
    # the replaced rule: u_r4 / u_r7 rows at (k + .5) * H / 4 - 26 are far from the leaf
    t, _ = st_b(); size = [43.2, 25.92]
    for k in (0, 3):
        y = (k + .5) * H / 4 - 26
        assert MS.worst_gap("slw_st_b_v2__x", t, "u_bound.u_u_r4.u_sks.u_m", [264.0, y], size) > MS.REACH_UM


def test_st_a_banks_next_to_read_and_write_partners():
    t = {"outline_um": [W, H], "internal_stations": [],
         "hard_cores": [{"inst": "u_r0", "origin_um": [267.85, 77.39], "outline_um": [162.0, 162.0]},
                        {"inst": "cl_b_tw_data_i", "origin_um": [561.61, 276.49], "outline_um": [45.36, 186.19]}]}
    macros = [(f"u_bound.u_u_btab.u_bt.u_core.g_btb[{k}].u_m", [94.82, 41.07]) for k in range(4)]
    got = place("slw_st_a_v2__x", t, macros)
    for n, s in macros:
        assert MS.worst_gap("slw_st_a_v2__x", t, n, got[n], s) <= MS.REACH_UM
    # old row rule g_btb[3] at y = 3.5 * H / 4 - 20.52 was ~740 um from u_r0
    assert MS.worst_gap("slw_st_a_v2__x", t, macros[3][0], [453.6, 3.5 * H / 4 - 20.52], macros[3][1]) > MS.REACH_UM


def test_no_partner_is_an_error_not_a_grid():
    with pytest.raises(ValueError):
        MS.partners("slw_st_b_v2__x", {"outline_um": [W, H], "internal_stations": []}, "u_bound.u_u_r4.u_sks.u_m")


def test_generator_uses_connectivity_for_st():
    src = (ROOT / "tools/die_plan/qc_add_macro_sites.py").read_text()
    st = src[src.index("def desires"):src.index("elif tn in ('coll_s'")]
    assert "MS.target(" in st and "H/4" not in st
