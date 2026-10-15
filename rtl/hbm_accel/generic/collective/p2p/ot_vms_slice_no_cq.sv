`timescale 1ns/1ps
`default_nettype none
// Real zero-local-client slice. No scalar CQ ports; native ring replay remains active.
module ot_vms_slice_no_cq #(
    parameter integer PHYSICAL_RING = 1,
    parameter integer RG = 2, parameter integer WG = 2,
    // relay stages each way between each wide lane group's farthest client and the slice face (die contract relay count;
    // SPEC v0.8 D-B2-12): every lane of group g gets 4 + 2 x RRS/WRS[g] credits (ot_vms_bank).  Default 3 = the local
    // lane group's far station (slice -> SU -> SFU -> HC); the bank tile is hardened at its defaults, which must match.
    parameter [RG*4-1:0] RRS = {RG{4'd3}}, parameter [WG*4-1:0] WRS = {WG{4'd3}},
    parameter integer BMUT = 0, parameter integer HMUT = 0, parameter integer CMUT = 0
) (
    input  wire [12:0]          child_clk,
    input  wire                 rst_n,
    input  wire [1:0]           sid,
    input  wire [RG*8*17-1:0]   rq,
    output wire [RG*8-1:0]      rq_cr,
    output wire [RG*8*257-1:0]  rr,
    input  wire [WG*8*281-1:0]  wq,
    output wire [WG*8-1:0]      wq_cr,
    output wire [WG*8-1:0]      wq_done,
    input  wire [8*281-1:0]     dq,
    output wire [7:0]           dq_done,
    input  wire [2129:0]        vcb,
    output wire                 vcb_cr,
    output wire [7:0]           kq_done,
    input  wire [2223:0]        cw_in,
    output wire [1:0]           cw_in_cr,
    output wire [2223:0]        cw_out,
    input  wire [1:0]           cw_out_cr,
    input  wire [2223:0]        ccw_in,
    output wire [1:0]           ccw_in_cr,
    output wire [2223:0]        ccw_out,
    input  wire [1:0]           ccw_out_cr,
    output wire [8*18-1:0]      bank_status,
    output wire [2:0]           hub_status,
    output wire [1:0]           mirror_busy
);
    ot_vms_slice_clocked #(.PHYSICAL_RING(PHYSICAL_RING),.NC(0),.RG(RG),.WG(WG),.RRS(RRS),.WRS(WRS),
        .BMUT(BMUT),.HMUT(HMUT),.CMUT(CMUT)) u_slice(
        .cq(1'b0),.cr(),
        .child_clk(child_clk),
        .rst_n(rst_n),
        .sid(sid),
        .rq(rq),
        .rq_cr(rq_cr),
        .rr(rr),
        .wq(wq),
        .wq_cr(wq_cr),
        .wq_done(wq_done),
        .dq(dq),
        .dq_done(dq_done),
        .vcb(vcb),
        .vcb_cr(vcb_cr),
        .kq_done(kq_done),
        .cw_in(cw_in),
        .cw_in_cr(cw_in_cr),
        .cw_out(cw_out),
        .cw_out_cr(cw_out_cr),
        .ccw_in(ccw_in),
        .ccw_in_cr(ccw_in_cr),
        .ccw_out(ccw_out),
        .ccw_out_cr(ccw_out_cr),
        .bank_status(bank_status),
        .hub_status(hub_status),
        .mirror_busy(mirror_busy));
endmodule
`default_nettype wire
