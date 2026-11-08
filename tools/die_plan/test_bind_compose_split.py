"""DIE-HBM-92-SU 11-08: compose_split regroups composed cut members under a hard sub-core, exactly or not at all."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
import bind_elab as E
from bind_compose import compose, CompositionError
import bound_macro_paths as BMP

SUB = """
module pair_core (input wire clk, input wire [1:0] a, output wire [1:0] y);
    pair_core__mc u_core (.ck(clk), .ck2({2{clk}}), .a(a), .y(y));
endmodule
module pair_core__mc #(parameter integer L = 5) (input wire ck, input wire [1:0] ck2, input wire [1:0] a,
                                                output wire [1:0] y);
    wire [1:0] n_int;
    wire u_bk__clk; wire [1:0] u_bk__d; wire [1:0] u_bk__q; wire [1:0] u_bk__rr;
    bank u_bk (.clk(u_bk__clk), .d(u_bk__d), .q(u_bk__q), .rr(u_bk__rr));
    wire [1:0] u_ln__clk; wire [1:0] u_ln__x; wire [1:0] u_ln__z;
    lane #(.L(L), .K(1)) u_ln (.clk(u_ln__clk), .x(u_ln__x), .z(u_ln__z));
    assign u_bk__clk = ck;
    assign u_ln__clk[1:0] = ck2[1:0];
    assign u_bk__d[1:0] = a[1:0];
    assign n_int[1:0] = u_bk__q[1:0];
    assign u_ln__x[1:0] = n_int[1:0];
    assign y[1:0] = u_ln__z[1:0];
endmodule
"""


class Rules:
    def part_of(self, p):
        return "hg" if p.startswith("top.") else None


def fixture(tmp_path):
    f = E.Flat()
    f.new(30)
    # nets: 1 clk, 2-3 a0, 4-5 q0 (private), 6-7 y0; 12-13 a1, 14-15 q1, 16-17 y1; 20 glue out
    f.top_ports = {}
    cells = []
    for k, (a, q, y) in enumerate([((2, 3), (4, 5), (6, 7)), ((12, 13), (14, 15), (16, 17))]):
        cells.append(E.Cell(f"top.g_bank[{k}].u_bank", "bank", {}, {"clk": [1], "d": list(a), "q": list(q)},
                            {"clk": "input", "d": "input", "q": "output"}, "leaf"))
        cells.append(E.Cell(f"top.g_lane[{k}].u_lane", "lane", {"L": "4", "K": "1"},
                            {"clk": [1, 1], "x": list(q), "z": list(y)},
                            {"clk": "input", "x": "input", "z": "output"}, "leaf"))
    f.cells = cells
    ep = lambda m, p, i: dict(member="top." + m, port=p, bit=i)
    ports = {"clk": dict(dir="input", bits=[[ep(f"g_bank[{k}].u_bank", "clk", 0) for k in (0, 1)] +
                                            [ep(f"g_lane[{k}].u_lane", "clk", i) for k in (0, 1) for i in (0, 1)]])}
    for k in (0, 1):
        ports[f"a{k}"] = dict(dir="input", bits=[[ep(f"g_bank[{k}].u_bank", "d", i)] for i in (0, 1)])
        ports[f"y{k}"] = dict(dir="output", bits=[[ep(f"g_lane[{k}].u_lane", "z", i)] for i in (0, 1)])
    spec = {"cores": [dict(inst="top.cut", module="cutm", members=[c.path for c in cells], ports=ports)]}
    src = tmp_path / "pair.sv"
    src.write_text(SUB)
    rule = dict(inst=r"top\.cut", suffix="__s", levels=["u_fcore", "u_core"],
                subs=[dict(name="u_p{k}", module="pair_core", sources=[str(src)],
                           roles={"u_core.u_bk": r"\.g_bank\[(\d+)\]\.u_bank$",
                                  "u_core.u_ln": r"\.g_lane\[(\d+)\]\.u_lane$"}, param_diff_ok=["L"])])
    return f, spec, rule


def test_split_nests_members(tmp_path):
    f, spec, rule = fixture(tmp_path)
    sources, rec = compose(f, Rules(), spec, E.Cell, split=[rule])
    (mod, text), = sources
    assert mod == "cutm__s" and f.cells[0].module == "cutm__s"
    assert "cutm__s__fcore u_fcore (" in text and "cutm__s__core u_core (" in text
    assert text.count("pair_core u_p") == 2 and " bank " not in text and " lane " not in text
    assert ".a({a1[1], a1[0]})" in text or ".a({a1[1], a1[0]})" in text.replace("  ", " ")
    s = rec["cores"][0]["split"]["subs"]
    assert [x["inst"] for x in s] == ["u_fcore.u_core.u_p0", "u_fcore.u_core.u_p1"]
    assert s[0]["param_diff"] == {"u_core.u_ln.L": {"asbuilt": 4, "sub_core": 5}} and s[0]["private_bits"] == 2
    assert s[0]["open_ports"] == ["u_core.u_bk.rr"]          # open in the as-built cut, unused in the sub-core


def test_open_port_used_inside_fails(tmp_path):
    f, spec, rule = fixture(tmp_path)
    src = Path(rule["subs"][0]["sources"][0])
    src.write_text(src.read_text().replace("assign n_int[1:0] = u_bk__q[1:0];", "assign n_int[1:0] = u_bk__rr[1:0];"))
    with pytest.raises(CompositionError, match="open in the cut"):
        compose(f, Rules(), spec, E.Cell, split=[rule])


def test_private_net_seen_outside_fails(tmp_path):
    f, spec, rule = fixture(tmp_path)
    f.cells[3].ports["x"] = [4, 5]            # lane 1 reads bank 0's private q
    with pytest.raises(CompositionError, match="private|cut nets|visible outside"):
        compose(f, Rules(), spec, E.Cell, split=[rule])


def test_param_mismatch_fails(tmp_path):
    f, spec, rule = fixture(tmp_path)
    f.cells[1].params["K"] = "2"
    with pytest.raises(CompositionError, match="parameter K"):
        compose(f, Rules(), spec, E.Cell, split=[rule])


def test_split_clock_must_be_one_net(tmp_path):
    f, spec, rule = fixture(tmp_path)
    f.cells[1].ports["clk"] = [1, 9]
    spec["cores"][0]["ports"]["clk"]["bits"][0] = [b for b in spec["cores"][0]["ports"]["clk"]["bits"][0]
                                                  if not (b["member"].endswith("g_lane[0].u_lane") and b["bit"] == 1)]
    spec["cores"][0]["ports"]["ck9"] = dict(dir="input", bits=[[dict(member="top.g_lane[0].u_lane", port="clk", bit=1)]])
    with pytest.raises(CompositionError, match="cut nets"):
        compose(f, Rules(), spec, E.Cell, split=[rule])


def test_no_rule_unchanged(tmp_path):
    f, spec, _ = fixture(tmp_path)
    (mod, text), = compose(f, Rules(), spec, E.Cell)[0]
    assert mod == "cutm" and "u_fcore" not in text


def test_hard_core_leaf_path():
    bound = "    // as-built su_NE2.__cut_pretree\n    cutp__hcsplit u_u_su_Q2_pretree (\n"
    t = {"hard_cores": [dict(inst="u_su_Q2_pretree", module="pt", lef="x.lef")]}
    rows = BMP.resolve_hard_core_leaf(t, bound, {"u_su_Q2_pretree": dict(
        leaves=["su_NE2.__cut_pretree", "su_NW2.__cut_pretree"], inner="u_hc")})
    assert rows == [dict(inst="u_su_Q2_pretree", physical_inst="u_bound.u_u_su_Q2_pretree.u_hc", physical_master="pt",
                         asbuilt="su_NE2.__cut_pretree")]
    assert BMP.resolve_hard_core_leaf(t, bound, {}) == []


def test_dropped_export_tied_and_recorded(tmp_path):
    f, spec, rule = fixture(tmp_path)
    # bank 0's private q[0] also feeds an outside glue load: refused unless declared dropped
    f.cells.append(E.Cell("top.glue", "$and", {}, {"A": [4], "Y": [20]}, {"A": "input", "Y": "output"}, "leaf"))
    spec["cores"][0]["ports"]["q0x"] = dict(dir="output", bits=[[dict(member="top.g_bank[0].u_bank", port="q", bit=0)]])
    with pytest.raises(CompositionError, match="visible outside"):
        compose(f, Rules(), spec, E.Cell, split=[rule])
    f, spec, rule = fixture(tmp_path)
    f.cells.append(E.Cell("top.glue", "$and", {}, {"A": [4], "Y": [20]}, {"A": "input", "Y": "output"}, "leaf"))
    spec["cores"][0]["ports"]["q0x"] = dict(dir="output", bits=[[dict(member="top.g_bank[0].u_bank", port="q", bit=0)]])
    rule["subs"][0]["drop_exports"] = {"u_core.u_bk.q": [0, 0]}
    rule["subs"][0]["drop_reason"] = "dead"
    (mod, text), = compose(f, Rules(), spec, E.Cell, split=[rule])[0]
    assert "1'b0;  // dropped export of u_p0: dead" in text


def test_preprocess_takes_recipe_branch():
    from bind_compose_split import preprocess, SplitError
    src = "module m #(\n`ifdef X\nparameter integer L = 2\n`else\nparameter integer L = 1\n`endif\n) ();\nendmodule\n"
    assert "L = 1" in preprocess(src) and "L = 2" not in preprocess(src)
    assert "L = 2" in preprocess(src, ["X"]) and "L = 1" not in preprocess(src, ["X"])
    with pytest.raises(SplitError, match="unbalanced"):
        preprocess("`ifdef X\n")
    with pytest.raises(SplitError, match="macro use"):
        preprocess("assign a = `W;\n")


EMIT = """
module pair_core__x (input wire clk, input wire [1:0] a, output wire [1:0] y);
    xl u_l (.clk(clk), .a(a), .y(y));
endmodule
"""


def test_emit_module_replaces_reference(tmp_path):
    f, spec, rule = fixture(tmp_path)
    em = tmp_path / "emit.sv"
    em.write_text(EMIT)
    rule["subs"][0].update(emit_module="pair_core__x", emit_sources=[str(em)], emit_proof=dict(log="eq.log"),
                           same_net=[["clk"]])
    sources, rec = compose(f, Rules(), spec, E.Cell, split=[rule])
    (mod, text), = sources
    assert text.count("pair_core__x u_p") == 2 and "pair_core u_p" not in text
    s = rec["cores"][0]["split"]["subs"][0]
    assert s["module"] == "pair_core" and s["emit"] == dict(module="pair_core__x", reference="pair_core", ports=3,
                                                            proof=dict(log="eq.log"))


def test_emit_module_ports_must_equal(tmp_path):
    f, spec, rule = fixture(tmp_path)
    em = tmp_path / "emit.sv"
    em.write_text(EMIT.replace("output wire [1:0] y", "output wire [2:0] y"))
    rule["subs"][0].update(emit_module="pair_core__x", emit_sources=[str(em)])
    with pytest.raises(CompositionError, match="ports differ"):
        compose(f, Rules(), spec, E.Cell, split=[rule])


def test_same_net_group_must_be_one_net(tmp_path):
    f, spec, rule = fixture(tmp_path)
    rule["subs"][0]["same_net"] = [["clk", "a"]]
    with pytest.raises(CompositionError, match="same_net"):
        compose(f, Rules(), spec, E.Cell, split=[rule])
