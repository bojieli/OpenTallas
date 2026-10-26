`timescale 1ns/1ps
// HBM-UCIE8 10-20: status CDC child of the UCIe column parent ot_pdie_ucie_col_flat (lp.py child_pin_regions):
//   ck_r side (forwarded pma_rck): sticky "receiving" flag, set by the first valid word r_v from the PMA RX;
//   ck_t side (core clk): 2-flop synchroniser of that flag, st = {live, sticky (st[0] | rate-match fault)}.
//   Same function as the status glue of ot_pdie_ucie (rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv; synchronous resets:
//   the lp regional reset runs).  Only control bits are reset (owner 10-20 09:05).
module ot_ucie_col_sts (
    input  wire       ck_r,
    input  wire       rst_r_n,
    input  wire       r_v,
    input  wire       ck_t,
    input  wire       rst_t_n,
    input  wire       rm_flt,
    output reg  [1:0] st
);
    reg seen;
    always @(posedge ck_r) if (!rst_r_n) seen <= 1'b0; else if (r_v) seen <= 1'b1;
    reg [1:0] lv_s;
    always @(posedge ck_t)
        if (!rst_t_n) begin lv_s <= 2'b00; st <= 2'b00; end
        else begin lv_s <= {lv_s[0], seen}; st <= {lv_s[1], st[0] | rm_flt}; end
endmodule
