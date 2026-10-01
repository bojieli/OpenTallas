`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One pseudo-channel slice of the PIPELINED local K arbitration
// (ot_chip_v41x_hbm_karb_pipe): ot_chip_v41x_karb_slice plus
//   * a KQ-entry K request queue fed by the region tap (credit-guaranteed room:
//     the stack endpoint holds this queue's KQ credits); its head is the
//     slice's K requester; a pop (PHY handshake) is reported as k_pop, which
//     the region registers and returns to the endpoint as a credit;
//   * a credited K response send: a K response is taken from the PHY only
//     while the slice holds a credit of its region-side response queue (RQ
//     entries), and goes there unbuffered; credits return from the region.
// Every path to or from the region is register-to-register.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_pslice #(
    parameter integer AW    = 28,
    parameter integer TAGW  = 16,
    parameter integer LENW  = 4,
    parameter integer BEATW = 4,
    parameter integer DW    = 256,
    parameter integer KQ    = 4,
    parameter integer RQ    = 3,
    parameter bit     K_RD_FENCE = 1'b1,
    // W18b (root 2026-10-01): register the K response at the slice boundary (+1 response cycle), so a hardened
    // slice's ks_* leave from flops and the region's path starts at the macro pin
    parameter bit     KSREG = 1'b1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 b_v,
    output wire                 b_rdy,
    input  wire [AW-1:0]        b_addr,
    input  wire [LENW-1:0]      b_len,
    input  wire [TAGW-1:0]      b_tag,
    input  wire                 b_we,
    input  wire [DW-1:0]        b_wdata,
    input  wire [DW/8-1:0]      b_wstrb,
    output wire                 b_wr_done,
    output wire                 b_rsp_v,
    input  wire                 b_rsp_rdy,
    output wire [TAGW-1:0]      b_rsp_tag,
    output wire [BEATW-1:0]     b_rsp_beat,
    output wire [DW-1:0]        b_rsp_data,
    // K request from the region tap
    input  wire                 kin_v,
    input  wire [AW-1:0]        kin_addr,
    input  wire [LENW-1:0]      kin_len,
    input  wire [TAGW-1:0]      kin_tag,
    input  wire                 kin_we,
    input  wire [DW-1:0]        kin_wdata,
    input  wire [DW/8-1:0]      kin_wstrb,
    output wire                 k_pop,
    output wire                 k_wr_done,
    // K response to the region's queue
    output wire                 ks_v,
    output wire [TAGW-1:0]      ks_tag,
    output wire [BEATW-1:0]     ks_beat,
    output wire [DW-1:0]        ks_data,
    input  wire                 ks_cr,
    // the pseudo-channel
    output wire                 h_v,
    input  wire                 h_rdy,
    output wire [AW-1:0]        h_addr,
    output wire [LENW-1:0]      h_len,
    output wire [TAGW:0]        h_tag,
    output wire                 h_we,
    output wire [DW-1:0]        h_wdata,
    output wire [DW/8-1:0]      h_wstrb,
    input  wire                 h_wr_done,
    input  wire                 r_v,
    output wire                 r_rdy,
    input  wire [TAGW:0]        r_tag,
    input  wire [BEATW-1:0]     r_beat,
    input  wire [DW-1:0]        r_data,
    output wire                 b_grant,
    output wire                 contend
);
    localparam integer QW = AW + LENW + TAGW + 1 + DW + DW / 8;
    localparam integer CW = $clog2(RQ + 1);
    wire          q_v, q_rdy; wire [QW-1:0] q_d;
    wire [AW-1:0] k_addr; wire [LENW-1:0] k_len; wire [TAGW-1:0] k_tag; wire k_we;
    wire [DW-1:0] k_wdata; wire [DW/8-1:0] k_wstrb;
    assign {k_addr, k_len, k_tag, k_we, k_wdata, k_wstrb} = q_d;
    ot_chip_v41x_karb_qh #(.W(QW), .DEPTH(KQ)) u_kq (   // W18: registered head (1.2 GHz SS)
        .clk(clk), .rst_n(rst_n), .in_v(kin_v), .in_rdy(q_rdy),
        .in_d({kin_addr, kin_len, kin_tag, kin_we, kin_wdata, kin_wstrb}),
        .out_v(q_v), .out_rdy(k_pop), .out_d(q_d));
    reg [CW-1:0] cred;
    wire krv;
    wire [TAGW-1:0] kt; wire [BEATW-1:0] kb; wire [DW-1:0] kd;
    ot_chip_v41x_karb_slice #(.AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
                              .K_RD_FENCE(K_RD_FENCE)) u_s (
        .clk(clk), .rst_n(rst_n),
        .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag), .b_we(b_we),
        .b_wdata(b_wdata), .b_wstrb(b_wstrb), .b_wr_done(b_wr_done),
        .b_rsp_v(b_rsp_v), .b_rsp_rdy(b_rsp_rdy), .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat),
        .b_rsp_data(b_rsp_data),
        .k_v(q_v), .k_take(k_pop), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we),
        .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done),
        .k_rsp_v(krv), .k_rsp_rdy(cred != 0), .k_rsp_tag(kt), .k_rsp_beat(kb), .k_rsp_data(kd),
        .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
        .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done),
        .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data),
        .b_grant(b_grant), .contend(contend));
    wire ks_go = krv && cred != 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cred <= CW'(RQ);
        else cred <= cred - CW'(ks_go) + CW'(ks_cr);
    generate if (KSREG) begin : g_ksr
        reg ksv_r; reg [TAGW-1:0] kst_r; reg [BEATW-1:0] ksb_r; reg [DW-1:0] ksd_r;
        always @(posedge clk or negedge rst_n) if (!rst_n) ksv_r <= 1'b0; else ksv_r <= ks_go;
        always @(posedge clk) if (ks_go) begin kst_r <= kt; ksb_r <= kb; ksd_r <= kd; end
        assign ks_v = ksv_r;
        assign {ks_tag, ks_beat, ks_data} = {kst_r, ksb_r, ksd_r};
    end else begin : g_ksc
        assign ks_v = ks_go;
        assign {ks_tag, ks_beat, ks_data} = {kt, kb, kd};
    end endgenerate
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && kin_v && !q_rdy)
        $error("ot_chip_v41x_karb_pslice: K request arrived without a credit");
`endif
endmodule
