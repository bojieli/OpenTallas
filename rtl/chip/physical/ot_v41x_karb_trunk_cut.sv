`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical cut of the local K arbitration partition's longest root-to-region
// trunk (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md, step 5): the stack
// endpoint (ot_chip_v41x_karb_stack_ep, one region served) and one region's K
// queues (ot_chip_v41x_karb_region_kq), both in the adopted RTL, joined by the
// trunk.  tools/v41x_karb_local_pnr.py places the K port at the endpoint end
// and the region's slice-facing ports at the far end, so the routed trunk has
// the full stack-centre-to-outer-region length.  Parameter-free top.
// ---------------------------------------------------------------------------
module ot_v41x_karb_trunk_cut (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          k_v,
    output wire          k_rdy,
    input  wire [29:0]   k_addr,
    input  wire [3:0]    k_len,
    input  wire [15:0]   k_tag,
    input  wire          k_we,
    input  wire [255:0]  k_wdata,
    input  wire [31:0]   k_wstrb,
    output wire          k_wr_done,
    output wire          k_rsp_v,
    input  wire          k_rsp_rdy,
    output wire [15:0]   k_rsp_tag,
    output wire [3:0]    k_rsp_beat,
    output wire [255:0]  k_rsp_data,
    output wire [31:0]   k_grants,
    output wire [31:0]   b_grants,
    output wire [31:0]   contended,
    output wire [3:0]    s_kv,
    input  wire [3:0]    s_take,
    output wire [29:0]   s_addr,
    output wire [3:0]    s_len,
    output wire [15:0]   s_tag,
    output wire          s_we,
    output wire [255:0]  s_wdata,
    output wire [31:0]   s_wstrb,
    input  wire [3:0]    s_krv,
    output wire [3:0]    s_krdy,
    input  wire [63:0]   s_rtag,
    input  wire [15:0]   s_rbeat,
    input  wire [1023:0] s_rdata,
    input  wire [3:0]    s_kwd,
    input  wire [3:0]    s_bg,
    input  wire [3:0]    s_ct
);
    localparam integer RW = 16 + 4 + 256;
    wire rq_v, rq_rdy, rs_v, rs_cr, r_kwd; wire [1:0] rq_lpc; wire [29:0] rq_addr; wire [3:0] rq_len;
    wire [15:0] rq_tag; wire rq_we; wire [255:0] rq_wdata; wire [31:0] rq_wstrb; wire [RW-1:0] rs_d;
    wire [2:0] r_bg, r_ct;
    ot_chip_v41x_karb_stack_ep #(.NPC(32), .AW(30), .NREG(1)) u_ep (
        .clk(clk), .rst_n(rst_n),
        .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we),
        .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done),
        .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_tag(k_rsp_tag), .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data),
        .rq_v(rq_v), .rq_rdy(rq_rdy), .rq_lpc(rq_lpc), .rq_addr(rq_addr), .rq_len(rq_len), .rq_tag(rq_tag),
        .rq_we(rq_we), .rq_wdata(rq_wdata), .rq_wstrb(rq_wstrb),
        .rs_v(rs_v), .rs_d(rs_d), .rs_cr(rs_cr), .r_kwd(r_kwd), .r_bg(r_bg), .r_ct(r_ct),
        .k_grants(k_grants), .b_grants(b_grants), .contended(contended));
    ot_chip_v41x_karb_region_kq #(.AW(30)) u_kq (
        .clk(clk), .rst_n(rst_n),
        .kq_v(rq_v), .kq_rdy(rq_rdy), .kq_lpc(rq_lpc), .kq_addr(rq_addr), .kq_len(rq_len), .kq_tag(rq_tag),
        .kq_we(rq_we), .kq_wdata(rq_wdata), .kq_wstrb(rq_wstrb),
        .ks_v(rs_v), .ks_tag(rs_d[RW-1 -: 16]), .ks_beat(rs_d[256 +: 4]), .ks_data(rs_d[255:0]), .ks_cr(rs_cr),
        .k_wr_done(r_kwd), .b_grant_n(r_bg), .contend_n(r_ct),
        .s_kv(s_kv), .s_take(s_take), .s_addr(s_addr), .s_len(s_len), .s_tag(s_tag), .s_we(s_we),
        .s_wdata(s_wdata), .s_wstrb(s_wstrb), .s_krv(s_krv), .s_krdy(s_krdy), .s_rtag(s_rtag),
        .s_rbeat(s_rbeat), .s_rdata(s_rdata), .s_kwd(s_kwd), .s_bg(s_bg), .s_ct(s_ct));
endmodule
