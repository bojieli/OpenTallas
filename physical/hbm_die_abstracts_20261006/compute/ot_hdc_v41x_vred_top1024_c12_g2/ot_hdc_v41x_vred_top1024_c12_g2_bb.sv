// Physical macro symbol only. Link the accompanying actual retained LEF
// and SS/FF timing libraries. Use real engine RTL for functional simulation.
// Fixed hardened ABI; no shape parameters or guessed pins/clock/protection.
(* blackbox, keep_hierarchy *) module ot_hdc_v41x_vred_top1024_c12_g2 (
 inout wire VDD,
 inout wire VSS,
 output wire busy,
 input wire clk,
 output wire fault,
 input wire [2:0] l_in,
 input wire last_in,
 input wire [3:0] lt_in,
 input wire [7679:0] lv_in,
 input wire [8:0] meta_in,
 input wire mx_in,
 input wire [7:0] nres_in,
 output wire [3071:0] o_addr,
 output wire [4095:0] o_data,
 output wire o_ev,
 output wire [8:0] o_meta,
 output wire [127:0] o_we,
 input wire [23:0] rbase_in,
 input wire rnd_in,
 input wire [4:0] rsh_in,
 input wire rst_n,
 input wire [15:0] sfault_in,
 input wire span_in,
 input wire v_in
);
endmodule
