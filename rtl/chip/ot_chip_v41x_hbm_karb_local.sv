`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Local (per-PC) K arbitration of one HBM3E stack: the opt-in replacement for
// the monolithic ot_chip_v41x_hbm_karb, port-compatible with it
// (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md, Codex 796726ad / main 2bdb0c4a).
//
// NPC slices in NPC/4 regions of four.  pc_of(addr) is the monolithic
// arbiter's global hash (never the NPC4 hash); region = pc[LPC-1:2], local
// index = pc[1:0].  K request: stack ingress queue (2 entries, k_rdy = its
// registered room) -> the addressed region's queue (2 entries) -> the slice.
// Both queues are in order and the ingress head waits for its region, so K
// requests reach every PC in acceptance order.  K response: each region
// captures its lowest-index local PC holding a K response into a 2-entry
// queue; a stack egress queue (2 entries) captures the lowest-index region
// with a queued response.  Uncontended, a K request accepted on edge n can
// first handshake at the PHY on edge n+2, and a response taken from the PHY
// on edge m can first handshake at the consumer on edge m+2: +4 cycles per K
// round trip against the monolithic arbiter.  B adds no pipeline stage.
//
// Semantics relative to the monolithic arbiter (transaction equivalence):
//   * each K and B transaction reaches the same PC with the same payload and
//     tag; per-PC K order is acceptance order; B is untouched;
//   * K responses may reach the consumer in a different cross-PC order (the
//     consumer addresses staging by tag/entry/beat);
//   * K_RD_FENCE = 1: a K read waits for wr_done of every earlier K write on
//     its PC (the proposal's explicit fence);
//   * k_wr_done: OR of the per-PC K completions as before, delayed two
//     registered stages (region, stack); simultaneous events still merge;
//   * response buffering: 2 entries per region plus 3 per region at the
//     endpoint (the proposal's single 2-entry stack queue would need a
//     combinational root -> region -> root pop path across the stack);
//   * k_grants counts K acceptances (now ingress acceptance); b_grants counts
//     B grants two cycles late; contended counts per-PC arbitration conflicts
//     (both requesters eligible on a PC), not the monolithic arbiter's
//     "K presented while B presents on K's PC" cycles.
// ---------------------------------------------------------------------------
module ot_chip_v41x_hbm_karb_local #(
    parameter integer NPC  = 32,
    parameter integer AW   = 28,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter bit     K_RD_FENCE = 1'b1
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
`ifndef SYNTHESIS
    initial if (NPC < 4 || (NPC & (NPC - 1)) != 0)
        $fatal(1, "ot_chip_v41x_hbm_karb_local: NPC must be a power of two >= 4");
`endif
    wire [NREG-1:0] rq_v, rq_rdy, rs_v, rs_cr, r_kwd;
    wire [1:0] rq_lpc; wire [AW-1:0] rq_addr; wire [LENW-1:0] rq_len; wire [TAGW-1:0] rq_tag; wire rq_we;
    wire [DW-1:0] rq_wdata; wire [DW/8-1:0] rq_wstrb;
    wire [NREG*RW-1:0] rs_d; wire [NREG*3-1:0] r_bg, r_ct;
    ot_chip_v41x_karb_stack_ep #(.NPC(NPC), .AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW)) u_ep (
        .clk(clk), .rst_n(rst_n),
        .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we),
        .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done),
        .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_tag(k_rsp_tag), .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data),
        .rq_v(rq_v), .rq_rdy(rq_rdy), .rq_lpc(rq_lpc), .rq_addr(rq_addr), .rq_len(rq_len), .rq_tag(rq_tag),
        .rq_we(rq_we), .rq_wdata(rq_wdata), .rq_wstrb(rq_wstrb),
        .rs_v(rs_v), .rs_d(rs_d), .rs_cr(rs_cr), .r_kwd(r_kwd), .r_bg(r_bg), .r_ct(r_ct),
        .k_grants(k_grants), .b_grants(b_grants), .contended(contended));
    genvar g;
    generate for (g = 0; g < NREG; g = g + 1) begin : g_r
        ot_chip_v41x_karb_region #(.AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
                                   .K_RD_FENCE(K_RD_FENCE)) u_r (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v[g*4 +: 4]), .b_rdy(b_rdy[g*4 +: 4]), .b_addr(b_addr[g*4*AW +: 4*AW]),
            .b_len(b_len[g*4*LENW +: 4*LENW]), .b_tag(b_tag[g*4*TAGW +: 4*TAGW]), .b_we(b_we[g*4 +: 4]),
            .b_wdata(b_wdata[g*4*DW +: 4*DW]), .b_wstrb(b_wstrb[g*4*DW/8 +: 4*DW/8]),
            .b_wr_done(b_wr_done[g*4 +: 4]),
            .b_rsp_v(b_rsp_v[g*4 +: 4]), .b_rsp_rdy(b_rsp_rdy[g*4 +: 4]), .b_rsp_tag(b_rsp_tag[g*4*TAGW +: 4*TAGW]),
            .b_rsp_beat(b_rsp_beat[g*4*BEATW +: 4*BEATW]), .b_rsp_data(b_rsp_data[g*4*DW +: 4*DW]),
            .kq_v(rq_v[g]), .kq_rdy(rq_rdy[g]), .kq_lpc(rq_lpc), .kq_addr(rq_addr), .kq_len(rq_len),
            .kq_tag(rq_tag), .kq_we(rq_we), .kq_wdata(rq_wdata), .kq_wstrb(rq_wstrb),
            .ks_v(rs_v[g]), .ks_tag(rs_d[g*RW + BEATW + DW +: TAGW]), .ks_beat(rs_d[g*RW + DW +: BEATW]),
            .ks_data(rs_d[g*RW +: DW]), .ks_cr(rs_cr[g]),
            .k_wr_done(r_kwd[g]), .b_grant_n(r_bg[g*3 +: 3]), .contend_n(r_ct[g*3 +: 3]),
            .h_v(h_v[g*4 +: 4]), .h_rdy(h_rdy[g*4 +: 4]), .h_addr(h_addr[g*4*AW +: 4*AW]),
            .h_len(h_len[g*4*LENW +: 4*LENW]), .h_tag(h_tag[g*4*(TAGW+1) +: 4*(TAGW+1)]), .h_we(h_we[g*4 +: 4]),
            .h_wdata(h_wdata[g*4*DW +: 4*DW]), .h_wstrb(h_wstrb[g*4*DW/8 +: 4*DW/8]),
            .h_wr_done(h_wr_done[g*4 +: 4]),
            .r_v(r_v[g*4 +: 4]), .r_rdy(r_rdy[g*4 +: 4]), .r_tag(r_tag[g*4*(TAGW+1) +: 4*(TAGW+1)]),
            .r_beat(r_beat[g*4*BEATW +: 4*BEATW]), .r_data(r_data[g*4*DW +: 4*DW]));
    end endgenerate
endmodule
