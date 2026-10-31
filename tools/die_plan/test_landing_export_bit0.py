"""KV-022 (DIE-KV-37): kit-rtl wrappers declare bound-only one-bit pins as [0:0] vectors, so OpenROAD names the
BTerm "<port>[0]" (CHECKED on kv3_sys_SD 3_place.odb: fclk_out_o_serdes_W_rx_flit[0]).  landing_exports.tcl must look
up that name; scalar ports (the default, no bit0 set) stay byte-identical."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_contract as LC  # noqa: E402
from test_cts0114_fwd import LEGACY, PINS, _P  # noqa: E402

WRAPPER = """module kv3_sys_SD_part (
    input  wire clk,  // clock entry: spine tap 0
    input  wire [523:0] i_host_fdi,  // plan bus
    input  wire [0:0] clk_clk_phy,  // bound-only pin
    output wire [0:0] fclk_out_o,  // bound-only pin
    input  wire [5:0] strap_ca_k_i_host_fdi,  // bound-only pin
    output wire [0:0] fclk_out_cland_up   // bound-only pin
);
endmodule
"""


def test_bit0_ports_lists_only_one_bit_vectors():
    assert LC.bit0_ports(WRAPPER) == {"clk_clk_phy", "fclk_out_o", "fclk_out_cland_up"}
    assert LC.bit0_ports("module m(input wire clk, output wire fclk_out_o);endmodule") == frozenset()


def test_tie_export_resolves_vector_bterm_scalar_source_unchanged():
    s = LC.export_tcl(_P({"landing_contract": {"pins": PINS}, "landing_export_form": "tie"}), "T",
                      LC.bit0_ports(WRAPPER))
    assert "findBTerm {fclk_out_o[0]}" in s and "findBTerm {clk}" in s
    assert s == LEGACY.replace("findBTerm {fclk_out_o}", "findBTerm {fclk_out_o[0]}")


def test_fwd_export_resolves_vector_bterm_keeps_instance_name():
    s = LC.export_tcl(_P({"landing_contract": {"pins": PINS}, "landing_export_form": "fwd_buffer"}), "T",
                      frozenset({"fclk_out_o"}))
    assert "findBTerm {fclk_out_o[0]}" in s and "findBTerm {clk}" in s
    assert "{cland_fwd_fclk_out_o}" in s and "cland_fwd_fclk_out_o[0]" not in s


def test_tie_and_scalar_wrapper_stay_byte_identical():
    P = _P({"landing_contract": {"pins": PINS}, "landing_export_form": "tie"})
    assert LC.export_tcl(P, "T") == LEGACY
    assert LC.export_tcl(P, "T", LC.bit0_ports("module m(input wire clk, output wire fclk_out_o);")) == LEGACY
