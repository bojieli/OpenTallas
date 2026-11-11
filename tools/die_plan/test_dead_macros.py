"""dead_macros: plan macros whose every output is unloaded in the bound kit RTL (DIE-HBM-97/HBM-SM-MPL 11-11)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dead_macros as D  # noqa: E402

LIB = """library (m_tt) { cell (m_pe) { is_macro_cell : true;
  pin (clk) { direction : input; }
  bus (bm) { bus_type : b; direction : input; }
  bus (rout) { bus_type : b; direction : output; }
  pin (bout) { direction : output; }
} }"""

TILE = """
module tile (input wire clk, input wire [7:0] bm, output wire [7:0] rout, output wire bout, output wire [7:0] gout);
    assign gout = bm;
`ifdef COMPACT
    m_pe_compact
`else
    m_pe
`endif
`ifndef SYNTHESIS
        #(.W(8))
`endif
        u_pte (.clk(clk), .bm(bm), .rout(rout), .bout(bout));
endmodule
module tile_seed #(parameter integer W = 8) (input wire clk, input wire [7:0] bm, output wire [7:0] rout,
                                              output wire bout, output wire [7:0] gout);
    tile #(
        .W(W)
    ) u_seed (
        .clk(clk), .bm(bm), .rout(rout), .bout(bout), .gout(gout)
    );
endmodule
"""


def bound(c0_rout_reader="", extra=""):
    return f"""
module q_bound (input wire clk, input wire [7:0] bm, output wire [7:0] y, output wire [7:0] z);
    wire [7:0] w_c0_rout;  // dangling chain end
    wire w_c0_bout;
    wire [7:0] w_c1_rout;
    wire w_c1_bout;
    wire [7:0] w_c0_g, w_c1_g;
    // as-built a.g_c[0].u_t
    tile_seed #(.W(8)) u_c0 (.clk(clk), .bm(bm), .rout(w_c0_rout), .bout(w_c0_bout), .gout(w_c0_g));
    tile u_c1 (.clk(clk), .bm(bm), .rout(w_c1_rout), .bout(w_c1_bout), .gout(w_c1_g));
    assign y = w_c1_rout ^ {{8{{w_c1_bout}}}};
    assign z = w_c0_g ^ w_c1_g;
    {c0_rout_reader}
{extra}
endmodule
module q (input wire clk, input wire [7:0] bm, output wire [7:0] y, output wire [7:0] z);
    q_bound u_bound (.clk(clk), .bm(bm), .y(y), .z(z));
endmodule
"""


def mods(b):
    return D.module_index([TILE, b])


OUTS = D.lib_outputs(LIB)


def test_lib_outputs():
    assert OUTS == ["bout", "rout"]
    assert D.lib_outputs("library (x) { cell (y) { area : 1; } }") is None


def test_chain_end_macro_dead_through_seed_wrapper_and_ifdef_master():
    m = mods(bound())
    assert D.dead_reason(m, "q", "u_bound.u_c0.u_seed.u_pte", OUTS).startswith("all 2 output(s)")


def test_loaded_macro_live():
    m = mods(bound())
    assert D.dead_reason(m, "q", "u_bound.u_c1.u_pte", OUTS) is None


def test_one_read_output_keeps_macro():
    m = mods(bound("assign z2 = w_c0_bout;"))
    assert D.dead_reason(m, "q", "u_bound.u_c0.u_seed.u_pte", OUTS) is None


def test_slice_read_keeps_macro():
    m = mods(bound("wire [3:0] s = w_c0_rout[3:0];"))
    assert D.dead_reason(m, "q", "u_bound.u_c0.u_seed.u_pte", OUTS) is None


def test_generate_scope_and_unknown_path_not_proven():
    m = mods(bound())
    assert D.dead_reason(m, "q", "u_bound.g_c[0].u_t.u_pte", OUTS) is None
    assert D.dead_reason(m, "q", "u_bound.u_nope.u_pte", OUTS) is None
    assert D.dead_reason(m, "q", "u_bound.u_c0.u_seed.u_pte", None) is None
    assert D.dead_reason(m, "q", "u_bound.u_c0.u_seed.u_pte", ["missing_pin"]) is None


def test_keep_attribute_and_top_port_keep_macro():
    t = TILE.replace("        u_pte (", "        (* keep *) u_pte (", 1)
    assert D.dead_reason(D.module_index([t, bound()]), "q", "u_bound.u_c0.u_seed.u_pte", OUTS) is None
    top_port = TILE + """
module q2 (input wire clk, input wire [7:0] bm, output wire [7:0] rout, output wire bout, output wire [7:0] gout);
    tile u_t (.clk(clk), .bm(bm), .rout(rout), .bout(bout), .gout(gout));
endmodule
"""
    assert D.dead_reason(D.module_index([top_port]), "q2", "u_t.u_pte", OUTS) is None


def _plan(tmp_path, b):
    rtl = tmp_path / "q.sv"
    rtl.write_text(TILE + b)
    fl = tmp_path / "q.f"
    fl.write_text(str(rtl) + "\n")
    lib = tmp_path / "m_pe_tt.lib"
    lib.write_text(LIB)
    hc = [{"inst": "u_c0_pte", "module": "m_pe", "physical_inst": "u_bound.u_c0.u_seed.u_pte", "lib": str(lib)},
          {"inst": "u_c1_pte", "module": "m_pe", "physical_inst": "u_bound.u_c1.u_pte", "lib": str(lib)}]
    taps = [{"name": "u_c0_pte", "kind": "core"}, {"name": "u_c1_pte", "kind": "core"}, {"name": "g0", "kind": "grid"}]
    raw = {"partition_types": {"q": {"module": "q", "hard_cores": hc, "clock": {"taps": taps}},
                               "other": {"module": "o", "hard_cores": [dict(hc[0])], "clock": {"taps": [dict(taps[0])]}}}}
    return raw, {"q": str(fl)}


def lib_text(c):
    return Path(c["lib"]).read_text() if c.get("lib") else None


def test_project_drops_dead_core_and_tap_only_in_that_type(tmp_path):
    raw, kr = _plan(tmp_path, bound())
    before = json.dumps(raw, sort_keys=True)
    out, rec = D.project(raw, kr, lib_text)
    assert json.dumps(raw, sort_keys=True) == before                  # plan of record untouched
    q = out["partition_types"]["q"]
    assert [c["inst"] for c in q["hard_cores"]] == ["u_c1_pte"]
    assert [x["name"] for x in q["clock"]["taps"]] == ["u_c1_pte", "g0"]
    assert out["partition_types"]["other"] == raw["partition_types"]["other"]   # not a kit-rtl type
    assert [r["inst"] for r in rec["q"]["removed"]] == ["u_c0_pte"] and rec["q"]["schema"] == D.SCHEMA


def test_project_no_dead_macro_returns_same_plan(tmp_path, monkeypatch):
    raw, kr = _plan(tmp_path, bound("assign z2 = w_c0_bout;"))
    out, rec = D.project(raw, kr, lib_text)
    assert out is raw and rec == {}
    raw, kr = _plan(tmp_path, bound())
    monkeypatch.setenv("OT_DEAD_MACROS", "0")
    out, rec = D.project(raw, kr, lib_text)
    assert out is raw and rec == {}
    assert D.project(raw, None, lib_text) == (raw, {})
