`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Four-PC region of the local K arbitration partition
// (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md): the region's K queues
// (ot_chip_v41x_karb_region_kq) and four ot_chip_v41x_karb_slice.  B and H
// stay local to the slices; the region exposes one K trunk.  This is the
// proposal's physical unit.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_region #(
    parameter integer AW      = 28,
    parameter integer TAGW    = 16,
    parameter integer LENW    = 4,
    parameter integer BEATW   = 4,
    parameter integer DW      = 256,
    parameter integer CREDITS = 3,
    parameter bit     K_RD_FENCE = 1'b1
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [3:0]            b_v,
    output wire [3:0]            b_rdy,
    input  wire [4*AW-1:0]       b_addr,
    input  wire [4*LENW-1:0]     b_len,
    input  wire [4*TAGW-1:0]     b_tag,
    input  wire [3:0]            b_we,
    input  wire [4*DW-1:0]       b_wdata,
    input  wire [4*DW/8-1:0]     b_wstrb,
    output wire [3:0]            b_wr_done,
    output wire [3:0]            b_rsp_v,
    input  wire [3:0]            b_rsp_rdy,
    output wire [4*TAGW-1:0]     b_rsp_tag,
    output wire [4*BEATW-1:0]    b_rsp_beat,
    output wire [4*DW-1:0]       b_rsp_data,
    input  wire                  kq_v,
    output wire                  kq_rdy,
    input  wire [1:0]            kq_lpc,
    input  wire [AW-1:0]         kq_addr,
    input  wire [LENW-1:0]       kq_len,
    input  wire [TAGW-1:0]       kq_tag,
    input  wire                  kq_we,
    input  wire [DW-1:0]         kq_wdata,
    input  wire [DW/8-1:0]       kq_wstrb,
    output wire                  ks_v,
    output wire [TAGW-1:0]       ks_tag,
    output wire [BEATW-1:0]      ks_beat,
    output wire [DW-1:0]         ks_data,
    input  wire                  ks_cr,
    output wire                  k_wr_done,
    output wire [2:0]            b_grant_n,
    output wire [2:0]            contend_n,
    output wire [3:0]            h_v,
    input  wire [3:0]            h_rdy,
    output wire [4*AW-1:0]       h_addr,
    output wire [4*LENW-1:0]     h_len,
    output wire [4*(TAGW+1)-1:0] h_tag,
    output wire [3:0]            h_we,
    output wire [4*DW-1:0]       h_wdata,
    output wire [4*DW/8-1:0]     h_wstrb,
    input  wire [3:0]            h_wr_done,
    input  wire [3:0]            r_v,
    output wire [3:0]            r_rdy,
    input  wire [4*(TAGW+1)-1:0] r_tag,
    input  wire [4*BEATW-1:0]    r_beat,
    input  wire [4*DW-1:0]       r_data
);
    wire [3:0] s_kv, s_take, s_krv, s_krdy, s_kwd, s_bg, s_ct;
    wire [AW-1:0] s_addr; wire [LENW-1:0] s_len; wire [TAGW-1:0] s_tag; wire s_we;
    wire [DW-1:0] s_wdata; wire [DW/8-1:0] s_wstrb;
    wire [4*TAGW-1:0] s_rtag; wire [4*BEATW-1:0] s_rbeat; wire [4*DW-1:0] s_rdata;
    ot_chip_v41x_karb_region_kq #(.AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
                                  .CREDITS(CREDITS)) u_kq (
        .clk(clk), .rst_n(rst_n),
        .kq_v(kq_v), .kq_rdy(kq_rdy), .kq_lpc(kq_lpc), .kq_addr(kq_addr), .kq_len(kq_len), .kq_tag(kq_tag),
        .kq_we(kq_we), .kq_wdata(kq_wdata), .kq_wstrb(kq_wstrb),
        .ks_v(ks_v), .ks_tag(ks_tag), .ks_beat(ks_beat), .ks_data(ks_data), .ks_cr(ks_cr),
        .k_wr_done(k_wr_done), .b_grant_n(b_grant_n), .contend_n(contend_n),
        .s_kv(s_kv), .s_take(s_take), .s_addr(s_addr), .s_len(s_len), .s_tag(s_tag), .s_we(s_we),
        .s_wdata(s_wdata), .s_wstrb(s_wstrb),
        .s_krv(s_krv), .s_krdy(s_krdy), .s_rtag(s_rtag), .s_rbeat(s_rbeat), .s_rdata(s_rdata),
        .s_kwd(s_kwd), .s_bg(s_bg), .s_ct(s_ct));
    genvar p;
    generate for (p = 0; p < 4; p = p + 1) begin : g_s
        ot_chip_v41x_karb_slice #(.AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
                                  .K_RD_FENCE(K_RD_FENCE)) u_s (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v[p]), .b_rdy(b_rdy[p]), .b_addr(b_addr[p*AW +: AW]), .b_len(b_len[p*LENW +: LENW]),
            .b_tag(b_tag[p*TAGW +: TAGW]), .b_we(b_we[p]), .b_wdata(b_wdata[p*DW +: DW]),
            .b_wstrb(b_wstrb[p*DW/8 +: DW/8]), .b_wr_done(b_wr_done[p]),
            .b_rsp_v(b_rsp_v[p]), .b_rsp_rdy(b_rsp_rdy[p]), .b_rsp_tag(b_rsp_tag[p*TAGW +: TAGW]),
            .b_rsp_beat(b_rsp_beat[p*BEATW +: BEATW]), .b_rsp_data(b_rsp_data[p*DW +: DW]),
            .k_v(s_kv[p]), .k_take(s_take[p]), .k_addr(s_addr), .k_len(s_len), .k_tag(s_tag),
            .k_we(s_we), .k_wdata(s_wdata), .k_wstrb(s_wstrb), .k_wr_done(s_kwd[p]),
            .k_rsp_v(s_krv[p]), .k_rsp_rdy(s_krdy[p]), .k_rsp_tag(s_rtag[p*TAGW +: TAGW]),
            .k_rsp_beat(s_rbeat[p*BEATW +: BEATW]), .k_rsp_data(s_rdata[p*DW +: DW]),
            .h_v(h_v[p]), .h_rdy(h_rdy[p]), .h_addr(h_addr[p*AW +: AW]), .h_len(h_len[p*LENW +: LENW]),
            .h_tag(h_tag[p*(TAGW+1) +: TAGW+1]), .h_we(h_we[p]), .h_wdata(h_wdata[p*DW +: DW]),
            .h_wstrb(h_wstrb[p*DW/8 +: DW/8]), .h_wr_done(h_wr_done[p]),
            .r_v(r_v[p]), .r_rdy(r_rdy[p]), .r_tag(r_tag[p*(TAGW+1) +: TAGW+1]),
            .r_beat(r_beat[p*BEATW +: BEATW]), .r_data(r_data[p*DW +: DW]),
            .b_grant(s_bg[p]), .contend(s_ct[p]));
    end endgenerate
endmodule
