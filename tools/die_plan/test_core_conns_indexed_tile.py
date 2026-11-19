"""Plan core name -> bound instance (FABLE-FIX-S81-LEAF 11-19).

QC: the plan names a hardened tile u_t02 with the macro master as module, the bound module keeps the logical tile
`qfd_tile_nk_rp2_romleaf_rr u_u_t_0_2`; relay_depth saw no core on 48 QC types.  S81 leaf: u_lf.u_vsw / u_lf.u_vs are
bound as u_u_vsw / u_u_vs and must keep resolving exactly (u_vs must never take u_vsw).
"""
import importlib.util
from pathlib import Path

H = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("ccfb_tile", H / "core_conns_from_bind.py")
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)


def _lef(tmp, mod, pins):
    body = "".join(f"  PIN {n}\n    DIRECTION {d} ;\n  END {n}\n" for n, d in pins)
    (tmp / f"{mod}.lef").write_text(f"MACRO {mod}\n{body}  PIN VDD\n    DIRECTION INOUT ;\n  END VDD\nEND {mod}\n")
    return f"{mod}.lef"


def _qc(tmp):
    lef = _lef(tmp, "tile_a0c", [("n_a[0]", "INPUT"), ("n_a[1]", "INPUT"), ("s_o[0]", "OUTPUT"), ("s_o[1]", "OUTPUT")])
    plan = dict(partition_types=dict(cb=dict(module="cb", hard_cores=[
        dict(inst="u_t02", module="tile_a0c", lef=lef), dict(inst="u_t03", module="tile_a0c", lef=lef)])))
    text = """module cb (input wire clk);
    wire [1:0] w_a; wire [1:0] w_b; wire [1:0] w_c;
    // as-built c16.u_t_0_2
    tile_rr u_u_t_0_2 (
        .ck(clk), .ck_de(clk), .n_a(w_c), .s_o(w_a)
    );
    ot_dp_st #(.W(2)) u_st (.clk(clk), .d(w_a), .q(w_b));
    // as-built c16.u_t_0_3
    tile_rr u_u_t_0_3 (
        .ck(clk), .ck_de(clk), .n_a(w_b), .s_o(w_c)
    );
endmodule
"""
    return plan, text


def test_qc_flattened_tile_is_matched_and_traced(tmp_path):
    plan, text = _qc(tmp_path)
    res = C.trace(plan, "cb", text, str(tmp_path))
    assert res["matched_cores"] == ["u_t02", "u_t03"] and not res["unresolved_cores"]
    assert res["core_insts"] == {"u_t02": ["u_u_t_0_2"], "u_t03": ["u_u_t_0_3"]}
    got = {(p["core"], p["port"], p["partner"], p["stages_existing"]) for p in res["paths"] if p["dir"] == "in" and "partner" in p}
    assert ("u_t03", "n_a", "u_t02.s_o", 1) in got and ("u_t02", "n_a", "u_t03.s_o", 0) in got


def test_indexed_tier_needs_every_lef_pin_and_a_unique_pair(tmp_path):
    plan, text = _qc(tmp_path)
    hcs = plan["partition_types"]["cb"]["hard_cores"]
    _, insts = C.parse(text)
    cut = [(m, i, {k: v for k, v in p.items() if k != "s_o"}, d) for m, i, p, d in insts]     # a pin is missing
    assert C.match_hard_cores(hcs, cut, str(tmp_path))[0] == {}
    two = insts + [("tile_rr", "u_u_t_02", dict(n_a="w_b", s_o="w_c"), None)]                  # two instances fit u_t02
    got, bad = C.match_hard_cores(hcs, two, str(tmp_path))
    assert "u_t02" not in got.values() and got == {"u_u_t_0_3": "u_t03"} and bad
    assert C.match_hard_cores(hcs, insts)[0] == {}        # no readable LEF: nothing is matched by name alone


def test_s81_leaf_vsw_and_vs_resolve_exactly(tmp_path):
    lv = _lef(tmp_path, "ot_s81sl_vs", [("sw_fi", "INPUT"), ("sw_d", "OUTPUT")])
    lw = _lef(tmp_path, "ot_s81sl_vsw", [("i_d", "INPUT"), ("o_f", "OUTPUT")])
    plan = dict(partition_types=dict(lf=dict(module="lf", hard_cores=[
        dict(inst="u_lf.u_vs", module="ot_s81sl_vs", lef=lv), dict(inst="u_lf.u_vsw", module="ot_s81sl_vsw", lef=lw)])))
    text = """module lf (input wire clk);
    wire [0:0] w_f; wire [0:0] w_fq; wire [0:0] w_d;
    ot_s81sl_vsw u_u_vsw (.i_d(w_d), .o_f(w_f));
    ot_dp_st #(.W(1)) u_cst_swr (.clk(clk), .d(w_f), .q(w_fq));
    ot_s81sl_vs u_u_vs (.sw_fi(w_fq), .sw_d(w_d));
endmodule
"""
    res = C.trace(plan, "lf", text, str(tmp_path))
    assert res["core_insts"] == {"u_lf.u_vs": ["u_u_vs"], "u_lf.u_vsw": ["u_u_vsw"]} and not res["ambiguous_cores"]
    got = {(p["core"], p["port"], p["partner"], p["stages_existing"]) for p in res["paths"] if p["dir"] == "in" and "partner" in p}
    assert got == {("u_lf.u_vs", "sw_fi", "u_lf.u_vsw.o_f", 1), ("u_lf.u_vsw", "i_d", "u_lf.u_vs.sw_d", 0)}
