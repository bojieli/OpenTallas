`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 VM lane group as a CHAIN (hgi-unitrate 2026-10-10, hbm-phys / lead decision): one shared 32-lane bus per group
// runs VM face -> station 0 -> station 1 -> ... (R25GQ: lgW = VM -> SU -> SFU -> HC, lgE = VM -> CP -> quant).
//   ot_hgi_vm_lanehead   at the VM face: grants the bus per BURST (round robin over the K request bits that ride up the
//                        chain), passes the merged lane requests to the VM and broadcasts credits / responses / grant down;
//   ot_hgi_vm_lanestation in each client block (ID = its slot): one register stage each way on every chain signal
//                        (request bits / lane requests up; grant / credits / responses down); its local client ORs its
//                        request bit into slot ID and, only while granted, its lane requests into the up bus; credits and
//                        responses go to the local client only while it owns the bus.
// A burst holds the bus from grant to release (the client releases only when its credits are home and its responses /
// write dones landed), so lanes of two clients never mix and no response needs a tag.  Each station adds one edge each
// way to the credit loop: LQ (the client's credits = the VM lane queue depth) >= 2 x (stations to the VM + relays) + 8.
// Direction-generic: a read group has REQW 16 ({v, sector}) / RSPW 257 ({v, data}); a write group REQW 280 / RSPW 1 (done).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_vm_lanestation #(
    parameter integer K = 3,              // stations on the chain (request / grant bits)
    parameter integer ID = 0,             // this station's slot
    parameter integer REQW = 16,
    parameter integer RSPW = 257,
    parameter integer TAP = 1             // 0: a pure relay stage (no client)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // toward the VM (up)
    output reg  [K-1:0]         up_req,
    output reg  [32*REQW-1:0]   up_q,
    input  wire [K-1:0]         up_gnt,
    input  wire [31:0]          up_cr,
    input  wire [32*RSPW-1:0]   up_rsp,
    // away from the VM (down: the next station)
    input  wire [K-1:0]         dn_req,
    input  wire [32*REQW-1:0]   dn_q,
    output reg  [K-1:0]         dn_gnt,
    output reg  [31:0]          dn_cr,
    output reg  [32*RSPW-1:0]   dn_rsp,
    // the local client (unit ports rg_req / rg_gnt, wrq / wrq_cr / wrr, or the write side)
    input  wire                 l_req,
    output wire                 l_gnt,
    input  wire [32*REQW-1:0]   l_q,
    output reg  [31:0]          l_cr,
    output reg  [32*RSPW-1:0]   l_rsp
);
    reg own;                                           // this station's grant, registered here (the down copy's edge)
    // RELEASE HANDSHAKE (hgi-1010 b, the c17 chain hang): a client that drops its request and raises it again before the
    // head saw the drop still sees its OLD grant; the head then re-picks round robin and may hand the bus to another
    // station while this client sends (its lane requests dropped by the station, its credits never return: hang).  So a
    // released grant stays hidden (l_gnt 0) until this station has seen the head take it away (the head always drops the
    // grant for one edge before it picks again).
    reg rel, l_req_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rel <= 1'b0; l_req_q <= 1'b0; end
        else begin
            l_req_q <= l_req;
            if (TAP != 0 && own && l_req_q && !l_req) rel <= 1'b1;   // the client released its burst
            else if (!up_gnt[ID]) rel <= 1'b0;                         // the head took the grant away
        end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            up_req <= '0; up_q <= '0; dn_gnt <= '0; dn_cr <= '0; dn_rsp <= '0; l_cr <= '0; l_rsp <= '0; own <= 1'b0;
        end else begin
            up_req <= dn_req | ((TAP != 0 && l_req) ? (K'(1) << ID) : '0);
            up_q <= dn_q | ((TAP != 0 && own) ? l_q : '0);
            dn_gnt <= up_gnt; dn_cr <= up_cr; dn_rsp <= up_rsp;
            own <= (TAP != 0) && up_gnt[ID];
            l_cr <= (TAP != 0 && up_gnt[ID]) ? up_cr : 32'd0;
            for (integer l = 0; l < 32; l = l + 1)
                l_rsp[l*RSPW +: RSPW] <= (TAP != 0 && up_gnt[ID]) ? up_rsp[l*RSPW +: RSPW] : {RSPW{1'b0}};
        end
    assign l_gnt = own && !rel;
endmodule

module ot_hgi_vm_lanehead #(
    parameter integer K = 3,
    parameter integer REQW = 16,
    parameter integer RSPW = 257,
    parameter integer MUT = 0             // bench mutant: 1 the grant moves every 64 edges even while its owner holds it
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // the chain (first station's up side)
    input  wire [K-1:0]         c_req,
    input  wire [32*REQW-1:0]   c_q,
    output reg  [K-1:0]         c_gnt,
    output reg  [31:0]          c_cr,
    output reg  [32*RSPW-1:0]   c_rsp,
    // the VM unit's group (rq / rq_cr / rr or w2q / w2q_cr / w2q_done)
    output reg  [32*REQW-1:0]   g_q,
    input  wire [31:0]          g_cr,
    input  wire [32*RSPW-1:0]   g_rsp
);
    reg [$clog2(K > 1 ? K : 2)-1:0] rr_ptr; reg [5:0] age;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_gnt <= '0; rr_ptr <= '0; age <= '0; g_q <= '0; c_cr <= '0; c_rsp <= '0; end
        else begin
            age <= age + 6'd1;
            g_q <= c_q; c_cr <= g_cr; c_rsp <= g_rsp;
            if (c_gnt != '0 && ((c_gnt & c_req) == '0 || (MUT == 1 && age == 6'd63)))
                c_gnt <= '0;                               // a released (or, MUT 1, a timed-out) grant: one dead edge first
            else if (c_gnt == '0) begin : pick
                reg [K-1:0] ng; integer q;
                ng = '0;
                for (integer i = 0; i < K; i = i + 1) begin
                    q = (rr_ptr + 1 + i) % K;
                    if (ng == '0 && c_req[q] && !(MUT == 1 && c_gnt[q])) ng[q] = 1'b1;
                end
                c_gnt <= ng;
                for (integer i = 0; i < K; i = i + 1) if (ng[i]) rr_ptr <= i[$clog2(K > 1 ? K : 2)-1:0];
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_vm_die: the VM block body with its lane groups as the die sees them (hgi-unitrate 2026-10-10, for the hgi_vm view)
//   packet clients (NC), the DMA wide write port (WP 32 WDIRECT), and the wide lane groups:
//     read  group 0 = chain lgW (VM -> SU -> SFU -> HC), read group 1 = chain lgE (VM -> CP [SM x-load] -> ATT -> quant [FUSED]
//           -> HC_ENG (hfd_hc_eng, the one-pass FUSED HC engine; hbm-phys 2026-10-11)),
//           read group 2 = the DMA unit (DMA.STORE source reads, a dedicated client)
//     write group 0 = lgW, 1 = lgE, 2 = the hardware ROW_GATHER sink (coll, a dedicated client: c's hgi_vmw2_coll)
//   each chain's head (ot_hgi_vm_lanehead, K = 3 slots) sits here at the VM face; the stations are in the client blocks.
//   die bundles: *_up = {req[K], lanes} toward the VM; *_dn = {gnt[K], credits 32, responses} away from it.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_vm_die #(
    parameter integer NC = 9,
    parameter integer LQ = 32,             // every lane client's credits (power of two; >= the longest chain's round trip)
    parameter integer K = 3,               // lgW slots: 0 SU, 1 SFU, 2 HC
    parameter integer KE = 4,              // lgE slots (hbm-phys 2026-10-11): 0 CP (SM x-load), 1 ATT, 2 quant (FUSED), 3 HC_ENG
    parameter integer AP = 1               // the HC weight aperture route (ot_hgi_vm_unit AP): DMA lanes 281 b, ap_* to hfd_hc
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [NC*338-1:0]        cq,
    output wire [NC*274-1:0]        cr,
    output wire [18:0]              status,
    input  wire [32*(280+AP)-1:0]   wq,         // the DMA front's wide write lanes ({v, ap, sector 15, data, mask} with AP)
    output wire [31:0]              wq_done,
    output wire [31:0]              wq_rdy,     // AP: per-lane stop to the DMA front (aperture queue near full)
    output wire [8*278-1:0]         ap_q,       // AP: to hfd_hc's 8 weight aperture lanes (lane k = bank k; d's HC HSRC = 1)
    input  wire [7:0]               ap_cr,
    input  wire [7:0]               ap_done,
    input  wire [K+32*16-1:0]       lgw_r_up,   // {req K, lanes 32 x 16}
    output wire [K+32+32*257-1:0]   lgw_r_dn,   // {gnt K, credits 32, responses 32 x 257}
    input  wire [K+32*280-1:0]      lgw_w_up,
    output wire [K+32+32-1:0]       lgw_w_dn,   // {gnt K, credits 32, dones 32}
    input  wire [KE+32*16-1:0]      lge_r_up,
    output wire [KE+32+32*257-1:0]  lge_r_dn,
    input  wire [KE+32*280-1:0]     lge_w_up,
    output wire [KE+32+32-1:0]      lge_w_dn,
    input  wire [1+32*280-1:0]      coll_w_up,  // c's hgi_vmw2_coll: {c_req, 32 x 280}
    output wire [1+32+32-1:0]       coll_w_dn,  // c's hgi_vmw2_coll_r: {c_gnt, credits 32, dones 32}
    input  wire [1+32*16-1:0]       dma_r_up,   // DMA.STORE source reads: {c_req, 32 x {v, sector 15}} (hgi_vmr2_dma)
    output wire [1+32+32*257-1:0]   dma_r_dn    // {c_gnt, credits 32, responses 32 x {v, data 256}} (hgi_vmr2_dma_r)
);
    wire [96*16-1:0] rq; wire [95:0] rq_cr; wire [96*257-1:0] rr;
    wire [96*280-1:0] w2q; wire [95:0] w2_cr, w2_done;
    ot_hgi_vm_unit #(.NC(NC), .WP(32), .WDIRECT(1), .RP(96), .W2(96), .LQ(LQ), .AP(AP)) u_vmu (.clk(clk), .rst_n(rst_n), .cq(cq),
        .cr(cr), .status(status), .wq(wq), .wq_done(wq_done), .wq_rdy(wq_rdy), .ap_q(ap_q), .ap_cr(ap_cr), .ap_done(ap_done), .rq(rq), .rq_cr(rq_cr), .rr(rr), .w2q(w2q), .w2q_cr(w2_cr), .w2q_done(w2_done));
    // read chains
    ot_hgi_vm_lanehead #(.K(K), .REQW(16), .RSPW(257)) u_hrw (.clk(clk), .rst_n(rst_n), .c_req(lgw_r_up[32*16 +: K]), .c_q(lgw_r_up[0 +: 32*16]),
        .c_gnt(lgw_r_dn[32+32*257 +: K]), .c_cr(lgw_r_dn[32*257 +: 32]), .c_rsp(lgw_r_dn[0 +: 32*257]),
        .g_q(rq[0 +: 32*16]), .g_cr(rq_cr[0 +: 32]), .g_rsp(rr[0 +: 32*257]));
    ot_hgi_vm_lanehead #(.K(KE), .REQW(16), .RSPW(257)) u_hre (.clk(clk), .rst_n(rst_n), .c_req(lge_r_up[32*16 +: KE]), .c_q(lge_r_up[0 +: 32*16]),
        .c_gnt(lge_r_dn[32+32*257 +: KE]), .c_cr(lge_r_dn[32*257 +: 32]), .c_rsp(lge_r_dn[0 +: 32*257]),
        .g_q(rq[32*16 +: 32*16]), .g_cr(rq_cr[32 +: 32]), .g_rsp(rr[32*257 +: 32*257]));
    ot_hgi_vm_lanehead #(.K(1), .REQW(16), .RSPW(257)) u_hrd (.clk(clk), .rst_n(rst_n), .c_req(dma_r_up[32*16 +: 1]), .c_q(dma_r_up[0 +: 32*16]),
        .c_gnt(dma_r_dn[32+32*257 +: 1]), .c_cr(dma_r_dn[32*257 +: 32]), .c_rsp(dma_r_dn[0 +: 32*257]),
        .g_q(rq[64*16 +: 32*16]), .g_cr(rq_cr[64 +: 32]), .g_rsp(rr[64*257 +: 32*257]));
    // write chains + the coll sink
    ot_hgi_vm_lanehead #(.K(K), .REQW(280), .RSPW(1)) u_hww (.clk(clk), .rst_n(rst_n), .c_req(lgw_w_up[32*280 +: K]), .c_q(lgw_w_up[0 +: 32*280]),
        .c_gnt(lgw_w_dn[64 +: K]), .c_cr(lgw_w_dn[32 +: 32]), .c_rsp(lgw_w_dn[0 +: 32]),
        .g_q(w2q[0 +: 32*280]), .g_cr(w2_cr[0 +: 32]), .g_rsp(w2_done[0 +: 32]));
    ot_hgi_vm_lanehead #(.K(KE), .REQW(280), .RSPW(1)) u_hwe (.clk(clk), .rst_n(rst_n), .c_req(lge_w_up[32*280 +: KE]), .c_q(lge_w_up[0 +: 32*280]),
        .c_gnt(lge_w_dn[64 +: KE]), .c_cr(lge_w_dn[32 +: 32]), .c_rsp(lge_w_dn[0 +: 32]),
        .g_q(w2q[32*280 +: 32*280]), .g_cr(w2_cr[32 +: 32]), .g_rsp(w2_done[32 +: 32]));
    ot_hgi_vm_lanehead #(.K(1), .REQW(280), .RSPW(1)) u_hwc (.clk(clk), .rst_n(rst_n), .c_req(coll_w_up[32*280 +: 1]), .c_q(coll_w_up[0 +: 32*280]),
        .c_gnt(coll_w_dn[64 +: 1]), .c_cr(coll_w_dn[32 +: 32]), .c_rsp(coll_w_dn[0 +: 32]),
        .g_q(w2q[64*280 +: 32*280]), .g_cr(w2_cr[64 +: 32]), .g_rsp(w2_done[64 +: 32]));
endmodule
`default_nettype wire
