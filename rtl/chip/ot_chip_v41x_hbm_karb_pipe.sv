`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PIPELINED local (per-PC) K arbitration of one HBM3E stack: opt-in,
// port-compatible with ot_chip_v41x_hbm_karb and ot_chip_v41x_hbm_karb_local.
//
// Why: routed at 0.92 ns / 60 ps (results/physical_abi3/asap7/chip/
// v41x_karb_local), the local partition as proposed (one registered stage each
// way between the stack endpoint and a region, a combinational queue-head /
// pop loop between a region and its four slices) cannot close: an ASAP7
// register-to-register link reaches ~1.1 mm a cycle (0.60 ps/um + 190 ps,
// the express-link fit of tools/chip_assembly/floorplans.wire_delay_model),
// the outer region is 5.25 mm from the stack centre, and the region's
// head -> slice arbitration -> pop loop misses by ~0.5 ns.
//
// Structure: every link is register-to-register and credit-flow-controlled,
// so trunks are plain register chains of HOPS[g] stages (<= 1.0 mm a segment):
//   request   endpoint ingress queue -> dispatch register (a credit of the
//             target PC's KQ-entry slice queue held) -> HOPS[g] registers ->
//             the slice queue (ot_chip_v41x_karb_proot, _pregion, _pslice);
//             pops return credits over the reverse chain;
//   response  slice -> RQ-entry per-slice queue at its region (credited) ->
//             region send register -> HOPS[g]-1 registers -> (2*HOPS[g]+EPC)-entry
//             per-region queue at the endpoint (credited) -> consumer
//             (lowest-index non-empty region).
// Transaction semantics are those of ot_chip_v41x_hbm_karb_local (per-PC K
// order, same PC and payload, optional same-PC fence, k_wr_done / status
// delayed through the chains); only the added latency differs and grows with
// the region's distance.
// ---------------------------------------------------------------------------
module ot_chip_v41x_hbm_karb_pipe #(
    parameter integer NPC  = 32,
    parameter integer AW   = 28,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter bit     K_RD_FENCE = 1'b1,
    parameter integer KQ   = 4,     // K request queue per PC (endpoint credits)
    parameter integer RQ   = 3,     // K response queue per PC at its region (slice credits)
    parameter integer EPC  = 2,     // K response queue per region at the endpoint = 2 * HOPS[g] + EPC entries
    // trunk register stages per region (4 bits each, region 0 in [3:0]); default: 32 PCs along the 12.0 mm
    // PHY edge, endpoint at its centre, region centres 0.75 / 2.25 / 3.75 / 5.25 mm away, <= 1.0 mm a segment
    parameter [4*(NPC/4)-1:0] HOPS = (NPC == 32) ? 32'h64311346 : {(NPC/4){4'd1}}
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [NPC-1:0]       b_v,
    output wire [NPC-1:0]       b_rdy,
    input  wire [NPC*AW-1:0]    b_addr,
    input  wire [NPC*LENW-1:0]  b_len,
    input  wire [NPC*TAGW-1:0]  b_tag,
    input  wire [NPC-1:0]       b_we,
    input  wire [NPC*DW-1:0]    b_wdata,
    input  wire [NPC*DW/8-1:0]  b_wstrb,
    output wire [NPC-1:0]       b_wr_done,
    output wire [NPC-1:0]       b_rsp_v,
    input  wire [NPC-1:0]       b_rsp_rdy,
    output wire [NPC*TAGW-1:0]  b_rsp_tag,
    output wire [NPC*BEATW-1:0] b_rsp_beat,
    output wire [NPC*DW-1:0]    b_rsp_data,
    input  wire                 k_v,
    output wire                 k_rdy,
    input  wire [AW-1:0]        k_addr,
    input  wire [LENW-1:0]      k_len,
    input  wire [TAGW-1:0]      k_tag,
    input  wire                 k_we,
    input  wire [DW-1:0]        k_wdata,
    input  wire [DW/8-1:0]      k_wstrb,
    output wire                 k_wr_done,
    output wire                 k_rsp_v,
    input  wire                 k_rsp_rdy,
    output wire [TAGW-1:0]      k_rsp_tag,
    output wire [BEATW-1:0]     k_rsp_beat,
    output wire [DW-1:0]        k_rsp_data,
    output wire [NPC-1:0]       h_v,
    input  wire [NPC-1:0]       h_rdy,
    output wire [NPC*AW-1:0]    h_addr,
    output wire [NPC*LENW-1:0]  h_len,
    output wire [NPC*(TAGW+1)-1:0] h_tag,
    output wire [NPC-1:0]       h_we,
    output wire [NPC*DW-1:0]    h_wdata,
    output wire [NPC*DW/8-1:0]  h_wstrb,
    input  wire [NPC-1:0]       h_wr_done,
    input  wire [NPC-1:0]       r_v,
    output wire [NPC-1:0]       r_rdy,
    input  wire [NPC*(TAGW+1)-1:0] r_tag,
    input  wire [NPC*BEATW-1:0] r_beat,
    input  wire [NPC*DW-1:0]    r_data,
    output wire [31:0]          k_grants,
    output wire [31:0]          b_grants,
    output wire [31:0]          contended
);
    localparam integer NREG = NPC / 4;
    localparam integer RW   = TAGW + BEATW + DW;
    localparam integer QW   = 2 + AW + LENW + TAGW + 1 + DW + DW / 8;
    // the region -> endpoint credit loop is ~2 * HOPS[g] + 1 cycles: this depth keeps one response per cycle
    function automatic [8*NREG-1:0] epcs();
        integer r;
        for (r = 0; r < NREG; r = r + 1) epcs[r*8 +: 8] = 8'(2 * HOPS[r*4 +: 4] + EPC);
    endfunction
    localparam [8*NREG-1:0] EPCS = epcs();
    wire [NREG-1:0] d_v, s_v, s_cr, r_kwd;
    wire [1:0] d_lpc; wire [AW-1:0] d_addr; wire [LENW-1:0] d_len; wire [TAGW-1:0] d_tag; wire d_we;
    wire [DW-1:0] d_wdata; wire [DW/8-1:0] d_wstrb;
    wire [NPC-1:0] kcr;
    wire [NREG*RW-1:0] s_d; wire [NREG*3-1:0] r_bg, r_ct;
    ot_chip_v41x_karb_proot #(.NPC(NPC), .AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
                              .KQ(KQ), .EPCS(EPCS)) u_ep (
        .clk(clk), .rst_n(rst_n),
        .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we),
        .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done),
        .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_tag(k_rsp_tag), .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data),
        .d_v(d_v), .d_lpc(d_lpc), .d_addr(d_addr), .d_len(d_len), .d_tag(d_tag), .d_we(d_we),
        .d_wdata(d_wdata), .d_wstrb(d_wstrb), .kcr(kcr),
        .s_v(s_v), .s_d(s_d), .s_cr(s_cr), .r_kwd(r_kwd), .r_bg(r_bg), .r_ct(r_ct),
        .k_grants(k_grants), .b_grants(b_grants), .contended(contended));
    genvar g;
    generate for (g = 0; g < NREG; g = g + 1) begin : g_r
        localparam integer H = HOPS[g*4 +: 4];
        // request chain: H registers after the dispatch register
        wire t_v; wire [1:0] t_lpc; wire [AW-1:0] t_addr; wire [LENW-1:0] t_len; wire [TAGW-1:0] t_tag; wire t_we;
        wire [DW-1:0] t_wdata; wire [DW/8-1:0] t_wstrb;
        ot_chip_v41x_karb_pipe #(.W(1 + QW), .V(1), .N(H)) u_rq (
            .clk(clk), .rst_n(rst_n),
            .d({d_lpc, d_addr, d_len, d_tag, d_we, d_wdata, d_wstrb, d_v[g]}),
            .q({t_lpc, t_addr, t_len, t_tag, t_we, t_wdata, t_wstrb, t_v}));
        // reverse chains: H-1 registers after the region's (or endpoint's) own register
        wire [3:0] rkcr; wire rs_v; wire [RW-1:0] rs_d; wire rs_cr; wire rkwd; wire [2:0] rbg, rct;
        ot_chip_v41x_karb_pipe #(.W(4 + 1 + 1 + 3 + 3), .V(4 + 1 + 1 + 3 + 3), .N(H - 1)) u_ev (
            .clk(clk), .rst_n(rst_n), .d({rbg, rct, rkwd, rs_v, rkcr}),
            .q({r_bg[g*3 +: 3], r_ct[g*3 +: 3], r_kwd[g], s_v[g], kcr[g*4 +: 4]}));
        ot_chip_v41x_karb_pipe #(.W(RW), .V(0), .N(H - 1)) u_rd (
            .clk(clk), .rst_n(rst_n), .d(rs_d), .q(s_d[g*RW +: RW]));
        ot_chip_v41x_karb_pipe #(.W(1), .V(1), .N(H - 1)) u_cr (
            .clk(clk), .rst_n(rst_n), .d(s_cr[g]), .q(rs_cr));
        ot_chip_v41x_karb_pregion #(.AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW), .KQ(KQ), .RQ(RQ),
                                    .EPC(EPCS[g*8 +: 8]), .K_RD_FENCE(K_RD_FENCE)) u_r (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v[g*4 +: 4]), .b_rdy(b_rdy[g*4 +: 4]), .b_addr(b_addr[g*4*AW +: 4*AW]),
            .b_len(b_len[g*4*LENW +: 4*LENW]), .b_tag(b_tag[g*4*TAGW +: 4*TAGW]), .b_we(b_we[g*4 +: 4]),
            .b_wdata(b_wdata[g*4*DW +: 4*DW]), .b_wstrb(b_wstrb[g*4*DW/8 +: 4*DW/8]),
            .b_wr_done(b_wr_done[g*4 +: 4]),
            .b_rsp_v(b_rsp_v[g*4 +: 4]), .b_rsp_rdy(b_rsp_rdy[g*4 +: 4]), .b_rsp_tag(b_rsp_tag[g*4*TAGW +: 4*TAGW]),
            .b_rsp_beat(b_rsp_beat[g*4*BEATW +: 4*BEATW]), .b_rsp_data(b_rsp_data[g*4*DW +: 4*DW]),
            .t_v(t_v), .t_lpc(t_lpc), .t_addr(t_addr), .t_len(t_len), .t_tag(t_tag), .t_we(t_we),
            .t_wdata(t_wdata), .t_wstrb(t_wstrb), .kcr(rkcr),
            .s_v(rs_v), .s_tag(rs_d[RW-1 -: TAGW]), .s_beat(rs_d[DW +: BEATW]), .s_data(rs_d[DW-1:0]), .s_cr(rs_cr),
            .k_wr_done(rkwd), .b_grant_n(rbg), .contend_n(rct),
            .h_v(h_v[g*4 +: 4]), .h_rdy(h_rdy[g*4 +: 4]), .h_addr(h_addr[g*4*AW +: 4*AW]),
            .h_len(h_len[g*4*LENW +: 4*LENW]), .h_tag(h_tag[g*4*(TAGW+1) +: 4*(TAGW+1)]), .h_we(h_we[g*4 +: 4]),
            .h_wdata(h_wdata[g*4*DW +: 4*DW]), .h_wstrb(h_wstrb[g*4*DW/8 +: 4*DW/8]),
            .h_wr_done(h_wr_done[g*4 +: 4]),
            .r_v(r_v[g*4 +: 4]), .r_rdy(r_rdy[g*4 +: 4]), .r_tag(r_tag[g*4*(TAGW+1) +: 4*(TAGW+1)]),
            .r_beat(r_beat[g*4*BEATW +: 4*BEATW]), .r_data(r_data[g*4*DW +: 4*DW]));
    end endgenerate
endmodule
