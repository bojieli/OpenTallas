`timescale 1ns/1ps
// ELEM-GAPS/QC 10-18: the Qwen compute-die reset-tree repeater masters (qfd_rst_rep = PAD 0, qfd_rst_rep_p8 = PAD 8)
// exactly as tools/qwen_split/gen_relay_rtl.py emits them for the die (module lines byte-identical; the bench checks it).
module qfd_rst_rep (input wire clk, input wire d, output wire q0, output wire q1);
    ot_qwen_rst_rep #(.PAD(0)) u_rep (.clk(clk), .d(d), .q0(q0), .q1(q1));
endmodule
module qfd_rst_rep_p8 (input wire clk, input wire d, output wire q0, output wire q1);
    ot_qwen_rst_rep #(.PAD(8)) u_rep (.clk(clk), .d(d), .q0(q0), .q1(q1));
endmodule
