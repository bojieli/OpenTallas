`timescale 1ns/1ps
`default_nettype none
// Real SW VM slice composition. The COLL adapter's extra packet clients and write group stay
// inside this parent; the die sees narrow credit streams and the exact native B2 slice interface.
module ot_vms_slice_coll_sw #(
    parameter integer PHYSICAL_RING = 1,
    parameter integer NC = 1, RG = 2, WG = 2,
    parameter [RG*4-1:0] RRS = {RG{4'd3}}, parameter [WG*4-1:0] WRS = {WG{4'd3}},
    parameter integer CRD = 16, TCRD = 8, COLL_WRS = 3, MUT = 0,
    parameter integer BMUT = 0, HMUT = 0, CMUT = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [4:0]           clk_coll_rx,
    input  wire [12:0]          clk_vm_child,
    input wire [3:0] rgx_t_v,
    input wire [159:0] rgx_t_addr,
    input wire [2047:0] rgx_t_data,
    input wire rgx_t_vm,
    output wire [3:0] rgx_f_cr,
    input wire tkw_t_v,
    input wire [567:0] tkw_t_d,
    output wire tkw_f_cr,
    output wire coll_fault,
    output wire [651:0] coll_xw,
    input wire [1:0] coll_xwa,
    input  wire [NC*338-1:0]    cq,
    output wire [NC*274-1:0]    cr,
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
    wire [5*338-1:0] coll_cq; wire [5*274-1:0] coll_cr;
    wire [8*281-1:0] coll_wq; wire [7:0] coll_wcr, coll_wdone;
    wire [(NC+5)*274-1:0] all_cr; wire [(WG+1)*8-1:0] all_wcr, all_wdone;
    assign cr = all_cr[NC*274-1:0]; assign coll_cr = all_cr[NC*274 +: 5*274];
    assign wq_cr = all_wcr[WG*8-1:0]; assign wq_done = all_wdone[WG*8-1:0];
    assign coll_wcr = all_wcr[WG*8 +: 8]; assign coll_wdone = all_wdone[WG*8 +: 8];
    ot_hgi_coll_b2_vmport #(.CRD(CRD), .TCRD(TCRD), .WCRD(4+2*COLL_WRS), .MUT(MUT)) u_coll (
        .clk(clk), .rst_n(rst_n), .clk_rx(clk_coll_rx), .sid(2'd0),
        .rgx_t_v(rgx_t_v), .rgx_t_addr(rgx_t_addr), .rgx_t_data(rgx_t_data), .rgx_t_vm(rgx_t_vm), .rgx_f_cr(rgx_f_cr),
        .tkw_t_v(tkw_t_v), .tkw_t_d(tkw_t_d), .tkw_f_cr(tkw_f_cr), .fault(coll_fault),
        .cq(coll_cq), .cr(coll_cr), .wq(coll_wq), .wq_cr(coll_wcr), .wq_done(coll_wdone), .xw(coll_xw), .xwa(coll_xwa));
    ot_vms_slice_clocked #(.PHYSICAL_RING(PHYSICAL_RING),.NC(NC+5), .RG(RG), .WG(WG+1), .RRS(RRS), .WRS({4'(COLL_WRS),WRS}),
        .BMUT(BMUT), .HMUT(HMUT), .CMUT(CMUT)) u_slice (.child_clk(clk_vm_child), .rst_n(rst_n), .sid(2'd0),
        .cq({coll_cq,cq}), .cr(all_cr), .rq(rq), .rq_cr(rq_cr), .rr(rr), .wq({coll_wq,wq}), .wq_cr(all_wcr), .wq_done(all_wdone), .dq(dq), .dq_done(dq_done), .vcb(vcb), .vcb_cr(vcb_cr), .kq_done(kq_done), .cw_in(cw_in), .cw_in_cr(cw_in_cr), .cw_out(cw_out), .cw_out_cr(cw_out_cr), .ccw_in(ccw_in), .ccw_in_cr(ccw_in_cr), .ccw_out(ccw_out), .ccw_out_cr(ccw_out_cr), .bank_status(bank_status), .hub_status(hub_status), .mirror_busy(mirror_busy));
endmodule
`default_nettype wire
