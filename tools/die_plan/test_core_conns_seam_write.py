"""DIE-S81-92 r228: seam WRITE sides are traced as wiring to the out face flop (S81 col u_n23 -> u_lpl_17_w -> u_bout)."""
import core_conns_from_bind as C
from test_core_conns_from_bind_bits import plan


def _text(cell, port):
    return f"""module top(input wire [3:0] in_bus, output wire [4:0] out_bus);
wire [3:0] q, w;
HS u_src (.q(q));
{cell} #(.CHUNKS(1), .CHUNK_BITS(24), .W(4)) u_lpl_w (.ck(clk), .rsi(r), .{port}(q), .q(w));
ot_dp_st #(.W(4)) u_bout_out_bus (.clk(clk), .d(w), .q(out_bus[3:0]), .eq(out_bus[4]));
endmodule"""


def test_seam_w_pl_is_zero_stage_wiring(tmp_path):
    r = C.trace(plan(tmp_path), "top", _text("ot_pl_seam_w_pl", "i"))
    row = [x for x in r["paths"] if x["core"] == "src" and x.get("bus") == "out_bus"]
    assert row and row[0]["dir"] == "out"
    assert r["core_conns"]["top"]["src"]["q"] == ["bus:out_bus"]


def test_seam_w_plr_counts_one_register(tmp_path):
    r = C.trace(plan(tmp_path), "top", _text("ot_pl_seam_w_plr", "ir"))
    row = [x for x in r["paths"] if x["core"] == "src" and x.get("bus") == "out_bus"]
    assert row and row[0]["dir"] == "out"


def test_unknown_cell_still_breaks_the_trace(tmp_path):
    r = C.trace(plan(tmp_path), "top", _text("ot_pl_seam_w_other", "i"))
    assert not [x for x in r["paths"] if x["core"] == "src" and x.get("bus") == "out_bus"]
