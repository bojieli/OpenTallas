`timescale 1ns/1ps
`default_nettype none
// SFU / HC bank-pair LG leaf WITH its two LG taps folded in (coordinator 0db 10-17: lg_static_bank / _term fold
// into their consumer tile; no separate tap slots). = unchanged ot_hgi_sfu_lg_pair_leaf (one registered edge each
// way between the core's pair slice and the taps) + ot_hbm_vm_lg_pair_tap (TERM=0, SFU level, far ports to the HC
// level) or ot_hbm_vm_lg_pair_tap_term (TERM=1, HC level). Edge counts are those of the discrete composition, so
// the core bridge's READ_RETURN/WRITE_RETURN are unchanged. The taps take the leaf's pin-registered reset
// (cold init holds rst_n >= 2 edges, as the leaf already requires). Removes the 1,112-bit leaf<->tap seam per pair.
module ot_hgi_sfu_lg_pair_tap_leaf #(
    parameter integer READ_RETURN=14,
    parameter integer WRITE_RETURN=11,
    parameter integer MUT=0
)(
    input  wire clk,rst_n,
    input  wire [33:0]  c_rq,
    input  wire [561:0] c_wq,
    output wire [513:0] c_rr,
    output wire [1:0]   c_w_done,
    input  wire [1:0]   local_read,local_write,
    input  wire [33:0]  far_rq,
    input  wire [561:0] far_wq,
    output wire [513:0] far_rr,
    output wire [1:0]   far_w_done,
    output wire [33:0]  near_rq,
    output wire [561:0] near_wq,
    input  wire [513:0] near_rr,
    input  wire [1:0]   near_w_done,
    output wire         fault
);
    wire [33:0] l_rq; wire [561:0] l_wq; wire [513:0] l_rr; wire [1:0] l_done;
    (* keep = "true" *) reg rst_pin; always @(posedge clk) rst_pin <= rst_n;   // one boundary reset register
    ot_hgi_sfu_lg_pair_leaf #(.PIN_RST(0)) u_leaf(.clk(clk),.rst_n(rst_pin),.c_rq(c_rq),.c_wq(c_wq),.c_rr(c_rr),
        .c_w_done(c_w_done),.lg_rq(l_rq),.lg_wq(l_wq),.lg_rr(l_rr),.lg_w_done(l_done));
    ot_hbm_vm_lg_pair_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_tap(
        .clk(clk),.rst_n(rst_pin),.local_rq(l_rq),.far_rq(far_rq),.local_wq(l_wq),.far_wq(far_wq),
        .local_read(local_read),.local_write(local_write),.near_rq(near_rq),.near_wq(near_wq),
        .near_rr(near_rr),.near_w_done(near_w_done),.local_rr(l_rr),.far_rr(far_rr),
        .local_w_done(l_done),.far_w_done(far_w_done),.fault(fault));
endmodule

module ot_hgi_sfu_lg_pair_tap_leaf_term #(
    parameter integer READ_RETURN=18,
    parameter integer WRITE_RETURN=15,
    parameter integer MUT=0
)(
    input  wire clk,rst_n,
    input  wire [33:0]  c_rq,
    input  wire [561:0] c_wq,
    output wire [513:0] c_rr,
    output wire [1:0]   c_w_done,
    input  wire [1:0]   local_read,local_write,
    output wire [33:0]  near_rq,
    output wire [561:0] near_wq,
    input  wire [513:0] near_rr,
    input  wire [1:0]   near_w_done,
    output wire         fault
);
    wire [33:0] l_rq; wire [561:0] l_wq; wire [513:0] l_rr; wire [1:0] l_done;
    (* keep = "true" *) reg rst_pin; always @(posedge clk) rst_pin <= rst_n;   // one boundary reset register
    ot_hgi_sfu_lg_pair_leaf #(.PIN_RST(0)) u_leaf(.clk(clk),.rst_n(rst_pin),.c_rq(c_rq),.c_wq(c_wq),.c_rr(c_rr),
        .c_w_done(c_w_done),.lg_rq(l_rq),.lg_wq(l_wq),.lg_rr(l_rr),.lg_w_done(l_done));
    ot_hbm_vm_lg_pair_tap_term #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_tap(
        .clk(clk),.rst_n(rst_pin),.local_rq(l_rq),.local_wq(l_wq),
        .local_read(local_read),.local_write(local_write),.near_rq(near_rq),.near_wq(near_wq),
        .near_rr(near_rr),.near_w_done(near_w_done),.local_rr(l_rr),.local_w_done(l_done),.fault(fault));
endmodule
`default_nettype wire
