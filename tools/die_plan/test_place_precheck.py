"""PLACE-PRECHECK-2330: place_precheck reproduces the kit's own place-stage messages (OVERLAP row/site/core/macro/explicit, KNEE, kit tables,
cone / MPL-0020 on a tiny netlist)."""
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import place_precheck as PP  # noqa: E402

CORE = (4.32, 4.32, 100.0, 100.0)
CELLWH = (1.404, 0.27)


def occ_with(*sites):
    o = PP.Occ(PP._d(CORE[1]))
    for x, y, w, h in sites:
        o.reserve(PP._d(x), PP._d(y), PP._d(w), PP._d(h))
    return o


def row(inst, *sites):
    return (inst, [list(sites)], CELLWH)


def test_clean_row_reserves_its_sites_and_touching_is_not_overlap():
    a = row("u_lpad_a", (10.044, 4.59), (11.448, 4.59))       # touching along x (1.404 wide)
    assert PP.exact_bank_check([a], occ_with(), CORE, []) == []


def test_explicit_ft_reservation_overlap_names_first_site_like_the_kit():
    ft = (10.044, 4.59, 1.404, 0.27)
    f = PP.exact_bank_check([row("u_lpad_rs_s1", (20.304, 4.59), (10.314, 4.59))], occ_with(ft), CORE, [])
    assert len(f) == 1 and f[0]["sub"] == "EXPLICIT"
    assert f[0]["msg"] == "exact packed bank overlaps existing explicit reservation: u_lpad_rs_s1 10.314 4.59"


def test_two_rows_claiming_one_site_second_row_fails():
    a, b = row("u_lpad_rs_s0", (20.304, 4.59)), row("u_lpad_rs_s1", (20.52, 4.59))
    f = PP.exact_bank_check([a, b], occ_with(), CORE, [])
    assert [x["key"] for x in f] == ["u_lpad_rs_s1"] and f[0]["sub"] == "EXPLICIT"


def test_hard_macro_grid_and_core_errors():
    assert PP.exact_bank_check([row("u", (25.92, 31.32))], occ_with(), CORE, [("m0", 25, 31, 40, 32)])[0]["sub"] == "MACRO"
    assert PP.exact_bank_check([row("u", (25.921, 31.32))], occ_with(), CORE, [])[0]["sub"] == "GRID"
    assert PP.exact_bank_check([row("u", (99.9, 4.59))], occ_with(), CORE, [])[0]["sub"] == "CORE"


def test_parse_banks_and_kit_mode(tmp_path):
    assert PP._parse_banks("{{1 2} {3 4}} {{5 6} {7 8}}") == [[(1.0, 2.0), (3.0, 4.0)], [(5.0, 6.0), (7.0, 8.0)]]
    (tmp_path / "config.mk").write_text("export CORE_AREA = 4.32 4.32 100 100\n")
    (tmp_path / "ft_bit_sites.tcl").write_text(textwrap.dedent("""\
        set ff_bit_sites {}
        set ff_bit_site_cells {}
        dict set ff_bit_site_cells {x_ctl_fw} {1.404 0.27}
        dict set ff_bit_sites {x_ctl_fw,1,12} {10.044 4.59}
        """))
    (tmp_path / "istations.tcl").write_text(
        "is_packed_exact_banks {u_lpad_rs_s1} 1 1 {{{10.314 4.59} {20.304 4.59}}} 1.404 0.27 ist:rs_s1 0\n")
    fs, info = PP.check_kit(tmp_path)
    assert info["calls"] == 1 and info["ft_sites"] == 1
    assert fs[0]["msg"].endswith("u_lpad_rs_s1 10.314 4.59")


def test_knee_matches_the_kit_split_and_threshold():
    import istation_knee as K
    w, split = K.knee(900.0, 70.0, 3)             # first leg 900 over j hops, second 70
    assert w > K.KIT_LIMIT_UM and split == 2
    assert K.knee(900.0, 70.0, 4)[0] <= K.KIT_LIMIT_UM


def test_cone_and_mpl0020_on_a_tiny_netlist(tmp_path):
    v = ["module top();"]
    for i in range(3):     # 3 member flops, each driving a private 4-gate chain: cone 12 > 3 x 3 -> not separable at limit 3
        v.append(f"  DFFHQNx1_ASAP7_75t_R \\u_core.r[{i}]  (.CLK(clk), .D(n{i}_0), .QN(n{i}_4));")
        for k in range(4):
            v.append(f"  INVx1_ASAP7_75t_R \\g{i}_{k}  (.A(n{i}_{k}), .Y(n{i}_{k + 1}));")
    v += ["  ot_sram_1r1w_32x64 \\u_mem  (.CE(clk));", "endmodule"]
    nl = tmp_path / "1_2_yosys.v"
    nl.write_text("\n".join(v))
    (tmp_path / "place_regions_data.tcl").write_text("set ::ot_place_regions {\n  {enc {^u_core[.]r} 0.5 {} {} {}}\n}\n")
    (tmp_path / "macro_place.tcl").write_text("place_macro -macro_name {u_mem} -location {1 1} -orientation R0 -exact\n"
                                              "place_macro -macro_name {u_gone\\[2\\].u_mem} -location {1 1} -orientation R0 -exact\n")
    cells, nets = PP.read_netlist(nl)
    assert len(cells) == 3 + 12 + 1
    assert [f["key"] for f in PP.mpl0020(tmp_path, cells)] == ["u_gone[2].u_mem"]
    assert PP.cone_regions(tmp_path, cells, nets, limit=3)[0]["sub"] == "DROP"
    assert PP.cone_regions(tmp_path, cells, nets, limit=8) == []
