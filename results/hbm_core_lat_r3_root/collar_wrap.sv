`default_nettype none
// HBM-CORE-LAT-R3 (2026-10-27): plan-pin wrapper of ot_hbm_static_cfg_collar_idx256r for the B2o superset-face pin table
// (planS2 cores/ot_hbm_static_cfg_collar_idx256r__108x108__root_u_col_idx.json).  The only instance (root u_col_idx)
// binds pin_select {c_done: c_done__W}; unused_pins [c_done] (registered by the face shell, unread; never tied).
// clk_in: XSER=0 elaboration has no clk_in flop (one core clock domain, AGENTS.md 16/16a; plan merged_clock_ports
// [clk, clk_in] = one tap); the pin stays in the table, unloaded.  Wires only, 0 cycles.
module ot_hbm_static_cfg_collar_idx256r (
    input  wire clk, clk_in, rst_n,
    input  wire [7:0] tgt,
    input  wire cfg_v,
    input  wire [7:0] cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire desc_v,
    input  wire launch_v,
    input  wire [1:0] c_busy,
    input  wire c_done,
    input  wire c_done__W,
    input  wire [4:0] c_fault,
    output wire [0:0] pw_we,
    output wire [7:0] pw_addr,
    output wire [255:0] pw_data,
    output wire [768:0] prm,
    output wire start_v,
    output wire [1:0] go,
    output wire [220:0] rec,
    output wire ready, active, fault
);
    ot_hbm_static_cfg_collar_idx256r__rtl #(.PAGE_W(1), .NS(1), .NPR(6), .NREC(8), .NGO(2), .NB(2), .NF(5), .XSER(0),
                                            .FAN32(1)) u_rtl (
        .clk(clk), .clk_in(clk_in), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .launch_v(launch_v), .c_busy(c_busy), .c_done(c_done__W), .c_fault(c_fault),
        .pw_we(pw_we), .pw_addr(pw_addr), .pw_data(pw_data), .prm(prm), .start_v(start_v), .go(go), .rec(rec),
        .ready(ready), .active(active), .fault(fault));
endmodule
`default_nettype wire
