`timescale 1ns/1ps
`default_nettype none
// Clock-explicit real composition: child clocks are supplied at phi - R, never forwarded by RTL.
// HBM B2 VM SLICE (el1011-hbm-b2-vm, SPEC v0.4, 2026-10-12): one quadrant's VM = hub + 8 bank tiles + CW and CCW ring
// stops (one netlist, dir strap) + ring client + COLL star receiver.  This module is glue only (wires between hardened
// tiles; the die places the tiles): no logic of its own.  Both ring directions are wide (2,224 b + a 2-b per-VC credit);
// the COLL star edge is 2,130 b + a 1-b credit.  mirror_busy = {CCW stop, CW stop} (the consumer ORs them).
// Lane index of a wide group = g*8 + b (lane b <-> bank b); lane credits 4 + 2 x relay stages (RRS / WRS).  See ot_vms_bank / ot_vms_hub / ot_vms_rstop / ot_vms_rcl.
module ot_vms_slice_clocked #(
    parameter integer PHYSICAL_RING = 1,
    parameter integer NC = 4, parameter integer RG = 2, parameter integer WG = 2,
    // relay stages each way between each wide lane group's farthest client and the slice face (die contract relay count;
    // SPEC v0.8 D-B2-12): every lane of group g gets 4 + 2 x RRS/WRS[g] credits (ot_vms_bank).  Default 3 = the local
    // lane group's far station (slice -> SU -> SFU -> HC); the bank tile is hardened at its defaults, which must match.
    parameter [RG*4-1:0] RRS = {RG{4'd3}}, parameter [WG*4-1:0] WRS = {WG{4'd3}},
    parameter integer BMUT = 0, parameter integer HMUT = 0, parameter integer CMUT = 0
) (
    input  wire [12:0]          child_clk,
    input  wire                 rst_n,
    input  wire [1:0]           sid,
    input  wire [((NC>0)?NC*338:1)-1:0] cq,
    output wire [((NC>0)?NC*274:1)-1:0] cr,
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
    wire [(NC+1)*338-1:0] hcq; wire [(NC+1)*274-1:0] hcr;
    wire [337:0] hq; wire [273:0] hr;
    if(NC>0)begin:g_local_clients
        assign hcq={hq,cq};assign cr=hcr[NC*274-1:0];
    end else begin:g_no_local_clients
        // The one-bit empty-interface placeholder carries no functional request.
        // The ring replay client remains real and active at hub client zero.
        assign hcq=hq;assign cr=1'b0;
    end
    assign hr=hcr[NC*274+:274];
    wire [8*285-1:0] pq; wire [7:0] pq_cr; wire [8*266-1:0] pr;
    wire [289:0] cwi, cci; wire cwi_cr, cci_cr; wire [263:0] cco0, cco1;
    wire [8*276-1:0] eg, xq0, xq1; wire [7:0] egc0, egc1, xqc0, xqc1, xqd0, xqd1;
    wire [287:0] rce0, rce1; wire rce0_cr, rce1_cr; wire [265:0] ri0, ri1; wire ri0_cr, ri1_cr;
    wire [2:0] wk01, wk10; wire wk01_cr, wk10_cr; wire ack01, ack10;
    wire [8*281-1:0] kq; wire [7:0] kq_cr; wire [3:0] cb_epoch;
    localparam integer HF = 2, EGC = 1;  // one constant for both sides of each credit link
    ot_vms_hub #(.PHYSICAL_RING(PHYSICAL_RING),.NC(NC), .CWI(HF), .CCI(HF), .MUT(HMUT)) u_hub (.clk(child_clk[0]), .rst_n(rst_n), .sid(sid), .cq(hcq), .cr(hcr), .pq(pq), .pq_cr(pq_cr),
        .pr(pr), .cwi(cwi), .cwi_cr(cwi_cr), .cci(cci), .cci_cr(cci_cr), .cco0(cco0), .cco1(cco1), .status(hub_status));
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
        ot_vms_bank #(.RG(RG), .WG(WG), .RRS(RRS), .WRS(WRS), .EGC(EGC), .MUT(BMUT)) u_bank (.clk(child_clk[b+1]), .rst_n(rst_n), .bid(3'(b)), .sid(sid),
            .rq(brq), .rq_cr(brq_cr), .rr(brr), .wq(bwq), .wq_cr(bwq_cr), .wq_done(bwq_done),
            .dq(dq[b*281 +: 281]), .dq_done(dq_done[b]), .kq(kq[b*281 +: 281]), .kq_cr(kq_cr[b]), .kq_done(kq_done[b]),
            .xq(xq0[b*276 +: 276]), .xq_cr(xqc0[b]), .xq_done(xqd0[b]), .xq2(xq1[b*276 +: 276]), .xq2_cr(xqc1[b]), .xq2_done(xqd1[b]),
            .eg(eg[b*276 +: 276]), .eg_cr({egc1[b], egc0[b]}),
            .pq(pq[b*285 +: 285]), .pq_cr(pq_cr[b]), .pr(pr[b*266 +: 266]), .status(bank_status[b*18 +: 18]));
    end
    ot_vms_rstop #(.PHYSICAL_RING(PHYSICAL_RING),.HF(HF), .EGC(EGC), .MUT(CMUT)) u_cw (.clk(child_clk[9]), .rst_n(rst_n), .sid(sid), .dir(1'b0),
        .l_in(cw_in), .l_in_cr(cw_in_cr), .l_out(cw_out), .l_out_cr(cw_out_cr), .pi(cwi), .pi_cr(cwi_cr),
        .eg(eg), .eg_cr(egc0), .xq(xq0), .xq_cr(xqc0), .xq_done(xqd0), .rce(rce0), .rce_cr(rce0_cr), .ri(ri0), .ri_cr(ri0_cr),
        .wko(wk01), .wko_cr(wk01_cr), .wki(wk10), .wki_cr(wk10_cr), .cco(cco0), .ack_o(ack01), .ack_i(ack10), .mirror_busy(mirror_busy[0]));
    ot_vms_rstop #(.PHYSICAL_RING(PHYSICAL_RING),.HF(HF), .EGC(EGC), .MUT(CMUT)) u_ccw (.clk(child_clk[10]), .rst_n(rst_n), .sid(sid), .dir(1'b1),
        .l_in(ccw_in), .l_in_cr(ccw_in_cr), .l_out(ccw_out), .l_out_cr(ccw_out_cr), .pi(cci), .pi_cr(cci_cr),
        .eg(eg), .eg_cr(egc1), .xq(xq1), .xq_cr(xqc1), .xq_done(xqd1), .rce(rce1), .rce_cr(rce1_cr), .ri(ri1), .ri_cr(ri1_cr),
        .wko(wk10), .wko_cr(wk10_cr), .wki(wk01), .wki_cr(wk01_cr), .cco(cco1), .ack_o(ack10), .ack_i(ack01), .mirror_busy(mirror_busy[1]));
    ot_vms_rcl u_rcl (.clk(child_clk[11]), .rst_n(rst_n), .sid(sid), .rce0(rce0), .rce0_cr(rce0_cr), .rce1(rce1), .rce1_cr(rce1_cr),
        .hq(hq), .hr(hr), .ri0(ri0), .ri0_cr(ri0_cr), .ri1(ri1), .ri1_cr(ri1_cr));
    ot_vms_star u_star (.clk(child_clk[12]), .rst_n(rst_n), .vcb(vcb), .vcb_cr(vcb_cr), .kq(kq), .kq_cr(kq_cr), .epoch(cb_epoch));
endmodule
`default_nettype wire
