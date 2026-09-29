`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Four-PC region of the PIPELINED local K arbitration
// (ot_chip_v41x_hbm_karb_pipe).  Request: the trunk tap (t_*) writes the
// addressed slice's credited K queue directly; the slices' pops leave as a
// registered 4-bit credit return (kcr).  Response: one RQ-entry queue per
// slice (the slices hold its credits); the region sends the lowest-index
// non-empty queue's head into its registered trunk send stage (s_*) while it
// holds one of the endpoint's EPC per-region credits (returned on s_cr).
// Events: registered OR of K write completions and per-cycle B-grant /
// conflict counts.  Every port is a register or lands in one.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_pregion #(
    parameter integer AW    = 28,
    parameter integer TAGW  = 16,
    parameter integer LENW  = 4,
    parameter integer BEATW = 4,
    parameter integer DW    = 256,
    parameter integer KQ    = 4,
    parameter integer RQ    = 3,
    parameter integer EPC   = 4,
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
    // trunk: request tap
    input  wire                  t_v,
    input  wire [1:0]            t_lpc,
    input  wire [AW-1:0]         t_addr,
    input  wire [LENW-1:0]       t_len,
    input  wire [TAGW-1:0]       t_tag,
    input  wire                  t_we,
    input  wire [DW-1:0]         t_wdata,
    input  wire [DW/8-1:0]       t_wstrb,
    output reg  [3:0]            kcr,
    // trunk: response send stage
    output reg                   s_v,
    output reg  [TAGW-1:0]       s_tag,
    output reg  [BEATW-1:0]      s_beat,
    output reg  [DW-1:0]         s_data,
    input  wire                  s_cr,
    // trunk: events
    output reg                   k_wr_done,
    output reg  [2:0]            b_grant_n,
    output reg  [2:0]            contend_n,
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
    localparam integer RW = TAGW + BEATW + DW;
    localparam integer CW = $clog2(EPC + 1);
    wire [3:0] pop, kwd, bg, ct, sv, qv, qpop;
    wire [4*RW-1:0] sd, qd;
    reg  [3:0] qcr;
    reg  [CW-1:0] cred;
    reg  [1:0] sel; reg any;
    integer i;
    always @(*) begin
        sel = 2'd0; any = 1'b0;
        for (i = 3; i >= 0; i = i - 1) if (qv[i]) begin sel = 2'(i); any = 1'b1; end
    end
    wire send = any && cred != 0;
    assign qpop = {4{send}} & (4'b1 << sel);
    genvar p;
    generate for (p = 0; p < 4; p = p + 1) begin : g_s
        wire [TAGW-1:0] st; wire [BEATW-1:0] sb; wire [DW-1:0] sdt;
        assign sd[p*RW +: RW] = {st, sb, sdt};
        ot_chip_v41x_karb_pslice #(.AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW), .KQ(KQ), .RQ(RQ),
                                   .K_RD_FENCE(K_RD_FENCE)) u_s (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v[p]), .b_rdy(b_rdy[p]), .b_addr(b_addr[p*AW +: AW]), .b_len(b_len[p*LENW +: LENW]),
            .b_tag(b_tag[p*TAGW +: TAGW]), .b_we(b_we[p]), .b_wdata(b_wdata[p*DW +: DW]),
            .b_wstrb(b_wstrb[p*DW/8 +: DW/8]), .b_wr_done(b_wr_done[p]),
            .b_rsp_v(b_rsp_v[p]), .b_rsp_rdy(b_rsp_rdy[p]), .b_rsp_tag(b_rsp_tag[p*TAGW +: TAGW]),
            .b_rsp_beat(b_rsp_beat[p*BEATW +: BEATW]), .b_rsp_data(b_rsp_data[p*DW +: DW]),
            .kin_v(t_v && t_lpc == p), .kin_addr(t_addr), .kin_len(t_len), .kin_tag(t_tag), .kin_we(t_we),
            .kin_wdata(t_wdata), .kin_wstrb(t_wstrb), .k_pop(pop[p]), .k_wr_done(kwd[p]),
            .ks_v(sv[p]), .ks_tag(st), .ks_beat(sb), .ks_data(sdt), .ks_cr(qcr[p]),
            .h_v(h_v[p]), .h_rdy(h_rdy[p]), .h_addr(h_addr[p*AW +: AW]), .h_len(h_len[p*LENW +: LENW]),
            .h_tag(h_tag[p*(TAGW+1) +: TAGW+1]), .h_we(h_we[p]), .h_wdata(h_wdata[p*DW +: DW]),
            .h_wstrb(h_wstrb[p*DW/8 +: DW/8]), .h_wr_done(h_wr_done[p]),
            .r_v(r_v[p]), .r_rdy(r_rdy[p]), .r_tag(r_tag[p*(TAGW+1) +: TAGW+1]),
            .r_beat(r_beat[p*BEATW +: BEATW]), .r_data(r_data[p*DW +: DW]),
            .b_grant(bg[p]), .contend(ct[p]));
        wire qrdy;
        ot_chip_v41x_karb_qn #(.W(RW), .DEPTH(RQ)) u_q (
            .clk(clk), .rst_n(rst_n), .in_v(sv[p]), .in_rdy(qrdy), .in_d(sd[p*RW +: RW]),
            .out_v(qv[p]), .out_rdy(qpop[p]), .out_d(qd[p*RW +: RW]));
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_n && sv[p] && !qrdy)
            $error("ot_chip_v41x_karb_pregion: slice %0d sent without a credit", p);
`endif
    end endgenerate
    always @(posedge clk) if (send) {s_tag, s_beat, s_data} <= qd[sel*RW +: RW];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            kcr <= 4'd0; qcr <= 4'd0; s_v <= 1'b0; cred <= CW'(EPC);
            k_wr_done <= 1'b0; b_grant_n <= 3'd0; contend_n <= 3'd0;
        end else begin
            kcr <= pop;
            qcr <= qpop;
            s_v <= send;
            cred <= cred - CW'(send) + CW'(s_cr);
            k_wr_done <= |kwd;
            b_grant_n <= 3'(bg[0]) + 3'(bg[1]) + 3'(bg[2]) + 3'(bg[3]);
            contend_n <= 3'(ct[0]) + 3'(ct[1]) + 3'(ct[2]) + 3'(ct[3]);
        end
endmodule
