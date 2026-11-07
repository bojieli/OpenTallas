"""ca_ring_land_slots: rings declared from the kit's RTL (DIE-KV-88 11-07)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G
RTL = """
ot_dp_clk_landing_cas #(.W(33), .DEPTH(4), .WFALL(1)) u_cland_a (
 .fclk(f), .t_rst_n(cland_fstart_in_a), .clk(clk), .rst_n(s), .strap_k(k), .d(a),
 .ready(r), .fault(x));
ot_dp_clk_landing_ca #(.W(2), .DEPTH(8)) u_cland_b (.t_rst_n(cland_fstart_in_b), .d(b), .clk(clk));
ot_dp_clk_landing_cas #(.W(3), .DEPTH(4)) u_cland_c (.t_rst_n(sc), .d({c0,c1}), .clk(clk));
ot_dp_clk_landing_cas #(.W(3), .DEPTH(4)) u_cland_u (.t_rst_n(su), .d(unplanned), .clk(clk));
ot_dp_landing_origin_s #(.PADW(1)) u_cland_origin (.clk(clk), .rst_raw_n(q), .p_start(cland_tstart_in), .start(st));
"""
def test_declares(tmp_path):
    (tmp_path / "t.sv").write_text(RTL)
    r = G.ca_ring_land_slots(tmp_path, {"a", "b", "c0", "c1"})
    assert r == {"a": {"D": 4, "form": "hold_mux"}, "cland_fstart_in_a": {"form": "ring_start", "ring": "a"},
                 "b": {"D": 8, "form": "hold_mux"}, "cland_fstart_in_b": {"form": "ring_start", "ring": "b"},
                 "cland_tstart_in": {"form": "origin_start", "origin": "u_cland_origin"}}
def test_none(tmp_path):
    (tmp_path / "t.sv").write_text("module m; endmodule\n")
    assert G.ca_ring_land_slots(tmp_path, {"a"}) == {}
