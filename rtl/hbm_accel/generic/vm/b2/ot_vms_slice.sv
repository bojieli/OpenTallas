`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM SLICE (el1011-hbm-b2-vm, 2026-10-12): one quadrant's VM = hub + 8 bank tiles + CW stop + CCW stop.  This
// module is glue only (wires between hardened tiles; the die places the tiles): no logic of its own.
// Lane index of a wide group = g*8 + b (lane b <-> bank b).  See ot_vms_bank / ot_vms_hub / ot_vms_cwstop.
module ot_vms_slice #(
    parameter integer NC = 4, parameter integer RG = 2, parameter integer WG = 2,
    parameter integer BMUT = 0, parameter integer HMUT = 0, parameter integer CMUT = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [1:0]           sid,
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
    input  wire [8*281-1:0]     kq,
    output wire [7:0]           kq_cr,
    output wire [7:0]           kq_done,
    input  wire [2222:0]        cw_in,
    output wire                 cw_in_cr,
    output wire [2222:0]        cw_out,
    input  wire                 cw_out_cr,
    input  wire [291:0]         ccw_in,
    output wire [1:0]           ccw_in_cr,
    output wire [291:0]         ccw_out,
    input  wire [1:0]           ccw_out_cr,
    output wire [8*18-1:0]      bank_status,
    output wire [2:0]           hub_status,
    output wire                 mirror_busy
);
    wire [(NC+1)*338-1:0] hcq; wire [(NC+1)*274-1:0] hcr;
    wire [337:0] hq; wire [273:0] hr;
    assign hcq = {hq, cq}; assign cr = hcr[NC*274-1:0]; assign hr = hcr[NC*274 +: 274];
    wire [8*285-1:0] pq; wire [7:0] pq_cr; wire [8*266-1:0] pr;
    wire [289:0] cwi; wire cwi_cr; wire [287:0] cci; wire cci_cr; wire [263:0] cco;
    wire [8*276-1:0] eg, xq; wire [7:0] eg_cr, xq_cr, xq_done;
    wire [287:0] rce; wire rce_cr; wire [2:0] wak; wire wak_cr, ack;
    ot_vms_hub #(.NC(NC), .MUT(HMUT)) u_hub (.clk(clk), .rst_n(rst_n), .sid(sid), .cq(hcq), .cr(hcr), .pq(pq), .pq_cr(pq_cr),
        .pr(pr), .cwi(cwi), .cwi_cr(cwi_cr), .cci(cci), .cci_cr(cci_cr), .cco(cco), .status(hub_status));
    genvar b, g;
    for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [RG*17-1:0] brq; wire [RG-1:0] brq_cr; wire [RG*257-1:0] brr;
        wire [WG*281-1:0] bwq; wire [WG-1:0] bwq_cr, bwq_done;
        for (g = 0; g < RG; g = g + 1) begin : g_r
            assign brq[g*17 +: 17] = rq[(g*8 + b)*17 +: 17];
            assign rq_cr[g*8 + b] = brq_cr[g]; assign rr[(g*8 + b)*257 +: 257] = brr[g*257 +: 257];
        end
        for (g = 0; g < WG; g = g + 1) begin : g_w
            assign bwq[g*281 +: 281] = wq[(g*8 + b)*281 +: 281];
            assign wq_cr[g*8 + b] = bwq_cr[g]; assign wq_done[g*8 + b] = bwq_done[g];
        end
        ot_vms_bank #(.RG(RG), .WG(WG), .MUT(BMUT)) u_bank (.clk(clk), .rst_n(rst_n), .bid(3'(b)), .sid(sid),
            .rq(brq), .rq_cr(brq_cr), .rr(brr), .wq(bwq), .wq_cr(bwq_cr), .wq_done(bwq_done),
            .dq(dq[b*281 +: 281]), .dq_done(dq_done[b]), .kq(kq[b*281 +: 281]), .kq_cr(kq_cr[b]), .kq_done(kq_done[b]),
            .xq(xq[b*276 +: 276]), .xq_cr(xq_cr[b]), .xq_done(xq_done[b]), .eg(eg[b*276 +: 276]), .eg_cr(eg_cr[b]),
            .pq(pq[b*285 +: 285]), .pq_cr(pq_cr[b]), .pr(pr[b*266 +: 266]), .status(bank_status[b*18 +: 18]));
    end
    ot_vms_cwstop #(.MUT(CMUT)) u_cw (.clk(clk), .rst_n(rst_n), .sid(sid), .cw_in(cw_in), .cw_in_cr(cw_in_cr),
        .cw_out(cw_out), .cw_out_cr(cw_out_cr), .cwi(cwi), .cwi_cr(cwi_cr), .eg(eg), .eg_cr(eg_cr), .xq(xq), .xq_cr(xq_cr),
        .xq_done(xq_done), .rce(rce), .rce_cr(rce_cr), .wak(wak), .wak_cr(wak_cr), .ack_in(ack), .mirror_busy(mirror_busy));
    ot_vms_ccwstop u_ccw (.clk(clk), .rst_n(rst_n), .sid(sid), .ccw_in(ccw_in), .ccw_in_cr(ccw_in_cr), .ccw_out(ccw_out),
        .ccw_out_cr(ccw_out_cr), .cci(cci), .cci_cr(cci_cr), .cco(cco), .wak(wak), .wak_cr(wak_cr), .ack_out(ack),
        .rce(rce), .rce_cr(rce_cr), .hq(hq), .hr(hr));
endmodule
`default_nettype wire
