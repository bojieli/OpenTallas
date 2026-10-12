`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery lever su_norm: the 1.2 GHz binary32 adder with SIX stages, ot_hdc_fp32_add_f12 (rtl/hdc/
// ot_hdc_fp32_f12.sv, unchanged) at CUTS 7'b1101011: decode + exponent differences | magnitude compare |
// alignments + swap | sum + LZC | cancellation shift + round | encode.  The l5x adder (7'b1101010) keeps the
// compare, both alignments and the swap in one stage; routed inside the fused norm pipeline that stage measured
// 764 ps of logic (SS -14 / -33 ps, routes mix1_a / mix1_b), so cut 0 splits it (owner closure procedure: a
// stage after a second miss).  Bit for bit the same function (only register boundaries move; equivalence:
// rtl/test/tb_dsrom_fp32_add_l6.sv against ot_hdc_fp32_add_fast delayed by 3).
// ---------------------------------------------------------------------------
module ot_dsrom_fp32_add_f12_l6 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                 output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_f12 #(.CUTS(7'b1101011)) u (.*);
endmodule
