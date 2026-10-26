`timescale 1ns/1ps
`default_nettype none
// LG tap FOLD (coordinator 0db 10-17): the two per-bank static LG taps of one VM bank pair g (banks 2g, 2g+1),
// folded into their consumer tile instead of 37.8-um standalone slots. Pure composition of two unchanged
// ot_hbm_vm_lg_static_bank instances (same edges, calendars, fault rule); the return edge is a parameter of
// the consumer tile (RET_PIN=0: SU 10/7, SFU 14/11), so the rret/wret identity straps disappear.
// Records: rq {v,sector16} x2, wq {v,sector16,data256,mask8} x2, rr {v,data256} x2, done x2. fault = OR.
module ot_hbm_vm_lg_pair_tap #(
    parameter integer READ_RETURN=10,
    parameter integer WRITE_RETURN=7,
    parameter integer MUT=0,         // 1: bank-1 write payload mux selects far despite the local calendar
    parameter integer LOCAL_SPLIT=0, // 1: per-face return registers + pin-register-fed calendars (ot_hbm_vm_lg_static_bank)
    parameter integer SPLIT_MUT=0    // bench only (bank 1): see ot_hbm_vm_lg_static_bank
)(
    input  wire clk,rst_n,
    input  wire [33:0]  local_rq,far_rq,
    input  wire [561:0] local_wq,far_wq,
    input  wire [1:0]   local_read,local_write,
    output wire [33:0]  near_rq,
    output wire [561:0] near_wq,
    input  wire [513:0] near_rr,
    input  wire [1:0]   near_w_done,
    output wire [513:0] local_rr,far_rr,
    output wire [1:0]   local_w_done,far_w_done,
    output wire         fault
);
    wire [1:0] f;
    for(genvar b=0;b<2;b=b+1)begin:g_bank
        ot_hbm_vm_lg_static_bank #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(b==1?MUT:0),.RET_PIN(0),.LOCAL_SPLIT(LOCAL_SPLIT),.SPLIT_MUT(b==1?SPLIT_MUT:0)) u_tap(
            .clk(clk),.rst_n(rst_n),.rret(5'd0),.wret(5'd0),
            .local_rq(local_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),
            .local_wq(local_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
            .local_read(local_read[b]),.local_write(local_write[b]),
            .near_rq(near_rq[b*17+:17]),.near_wq(near_wq[b*281+:281]),
            .near_rr(near_rr[b*257+:257]),.near_w_done(near_w_done[b]),
            .local_rr(local_rr[b*257+:257]),.far_rr(far_rr[b*257+:257]),
            .local_w_done(local_w_done[b]),.far_w_done(far_w_done[b]),.fault(f[b]));
    end
    assign fault=|f;
endmodule

// Terminal (outermost, HC) pair: two unchanged ot_hbm_vm_lg_static_bank_term instances; no far ports.
module ot_hbm_vm_lg_pair_tap_term #(
    parameter integer READ_RETURN=18,
    parameter integer WRITE_RETURN=15,
    parameter integer MUT=0          // 1: bank-1 corrupt terminal write payload
)(
    input  wire clk,rst_n,
    input  wire [33:0]  local_rq,
    input  wire [561:0] local_wq,
    input  wire [1:0]   local_read,local_write,
    output wire [33:0]  near_rq,
    output wire [561:0] near_wq,
    input  wire [513:0] near_rr,
    input  wire [1:0]   near_w_done,
    output wire [513:0] local_rr,
    output wire [1:0]   local_w_done,
    output wire         fault
);
    wire [1:0] f;
    for(genvar b=0;b<2;b=b+1)begin:g_bank
        ot_hbm_vm_lg_static_bank_term #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(b==1?MUT:0)) u_tap(
            .clk(clk),.rst_n(rst_n),
            .local_rq(local_rq[b*17+:17]),.local_wq(local_wq[b*281+:281]),
            .local_read(local_read[b]),.local_write(local_write[b]),
            .near_rq(near_rq[b*17+:17]),.near_wq(near_wq[b*281+:281]),
            .near_rr(near_rr[b*257+:257]),.near_w_done(near_w_done[b]),
            .local_rr(local_rr[b*257+:257]),.local_w_done(local_w_done[b]),.fault(f[b]));
    end
    assign fault=|f;
endmodule
`default_nettype wire
