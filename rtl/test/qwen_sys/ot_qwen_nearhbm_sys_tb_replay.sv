`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Near-HBM attention subsystem of the Qwen ROM system (one die: 4 HBM stacks + the hub), with the two system pieces the
// exact-gate bench (rtl/test/nearhbm/ot_qwen_nearhbm_attn_die_tb.sv) models as ideal:
//
//   HUB <-> STACK LINKS   each stack's link is a pair of ot_qwen_d2d_link ends (sequence numbers, CRC-32, ACK/NAK,
//                         go-back-N replay, training) over an ot_qwen_d2d_chan channel of LINK cycles each way, in
//                         place of the bench's LINK-stage delay lines.  Down (hub -> stack): {q beat, M}; up
//                         (stack -> hub): {sideband, P.V beat}.  The near-HBM units have no backpressure, so each link
//                         input has an elastic FIFO of EFD records; an overflow is a fault (never a silent drop).
//   HBM SERVICE CLOCK     the stack engines run on clk (1.2 GHz), the HBM controller on hclk (CK/2 = 976.6 MHz; the
//                         clocks do not share a PLL).  Every engine's request and response crosses in an
//                         ot_async_fifo (Gray pointers) of AFD entries; the request FIFO cannot overflow because an
//                         engine holds at most DQ requests (its row-FIFO credit), and AFD >= DQ.
//
// The HBM (one in-order row server per engine, a byte bucket per stack per hclk cycle, fixed latency) is the harness's
// (rtl/test/qwen_sys/tb_qwen_nearhbm_sys.cpp), on hclk.  Bench-only: nothing in a shipped top instantiates this.
// ---------------------------------------------------------------------------------------------------------------------
// Opt-in successor: fence empty-stack completion records until layer start.
// Empty stacks can complete during link training, before the first layer.
// Without the fence, their queued local maxima cross start and can make the
// hub broadcast M before nonempty stacks have completed their K pass.
module ot_qwen_nearhbm_sys_tb #(
    parameter integer LAYER_START_FENCE = 0,
    // Test-only replay timing; retained fence bench remains byte-identical.
    parameter integer DOWN_FLIP_START = 2000,
    parameter integer UP_FLIP_START = 2500,
    parameter integer HD = 128,
    parameter integer R = 1,
    parameter integer LINK = 45,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,
    parameter integer ZW = 4,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer EFD = 512,
    parameter integer AFD = 64
) (
    input  wire                 clk,
    input  wire                 hclk,
    input  wire                 rst_n,
    input  wire                 hrst_n,
    input  wire                 start,
    input  wire [13:0]          T,
    input  wire                 q_valid,
    input  wire [5:0]           q_beat,
    input  wire [511:0]         q_data,
    // HBM side (hclk)
    output wire [4*R-1:0]       req_valid,
    output wire [4*R-1:0]       req_v,
    output wire [4*R-1:0]       req_g,
    output wire [4*13*R-1:0]    req_t,
    input  wire [4*R-1:0]       rsp_valid,
    input  wire [4*HD*8*R-1:0]  rsp_data,
    output wire                 out_valid,
    output wire                 out_g,
    output wire [5:0]           out_beat,
    output wire [511:0]         out_data,
    output wire [4:0]           fault,
    output wire                 sys_fault,      // link down, elastic-FIFO overflow, async-FIFO overflow
    output wire                 links_up,
    input  wire [31:0]          flip_period,
    output wire [31:0]          crc_errors,
    output wire [31:0]          replays,
    output wire [4*16-1:0]      ev_stack,
    output wire [7:0]           ev_hub
);
    localparam integer PW = 563;
    localparam integer FW = 32 + 1 + 1 + 9 + 1 + 9 + 1 + 1 + 3 + PW;

    wire        mo_valid, mo_g;
    wire [1:0]  mo_hh;
    wire [31:0] mo_data;
    wire [3:0]    si_valid, si_g, si_any, pi_valid, pi_g;
    wire [7:0]    si_type, si_hh;
    wire [15:0]   si_k;
    wire [127:0]  si_data;
    wire [23:0]   pi_beat;
    wire [2047:0] pi_data;
    wire [7:0]    lup, lft, efo;
    wire [8*32-1:0] crc_v, rep_v;
    wire [4*R-1:0] afo;

    // the down record is the same for every stack (q and M are broadcast)
    wire          dn_any = q_valid || mo_valid;
    wire [PW-1:0] dn_rec = {{(PW - 555){1'b0}}, q_valid, q_beat, q_data, mo_valid, mo_g, mo_hh, mo_data};

    reg layer_started;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) layer_started <= 1'b0;
        else if (start) layer_started <= 1'b1;
    end

    genvar s, x;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        // ---------------------------------------------------------------- down: hub end -> stack end
        wire          hd_v, hd_r, hd_ne;
        wire [PW-1:0] hd_d;
        wire [9:0]    hd_n;
        ot_nhb_fifo #(.W(PW), .D(EFD)) u_hdq (.clk(clk), .rst_n(rst_n), .push(dn_any), .din(dn_rec),
                                                .pop(hd_ne && hd_r), .dout(hd_d), .nonempty(hd_ne), .count(hd_n));
        assign efo[2*s] = dn_any && (hd_n == EFD);
        wire [FW-1:0] h_tx, s_tx, h_rx, s_rx;
        wire h_rxv, s_rxv;
        wire          sd_v;
        wire [PW-1:0] sd_rec;
        wire          su_ne, su_r;
        wire [PW-1:0] su_d;
        wire          hu_v;
        wire [PW-1:0] hu_rec;
        integer nf_a, nf_b;
        ot_qwen_d2d_link #(.PW(PW), .S(9), .LRB(7), .TMO(4 * LINK + 32)) u_hub_end (
            .clk(clk), .rst_n(rst_n), .up_valid(hd_ne), .up_ready(hd_r), .up_rec(hd_d), .up_cr(1'b0),
            .dn_valid(hu_v), .dn_rec(hu_rec), .dn_cr(),
            .tx_flit(h_tx), .rx_valid(h_rxv), .rx_flit(h_rx),
            .link_up(lup[2*s]), .link_fault(lft[2*s]), .n_crc_err(crc_v[32*(2*s) +: 32]),
            .n_replay(rep_v[32*(2*s) +: 32]), .n_seq_drop(), .n_sent());
        ot_qwen_d2d_link #(.PW(PW), .S(9), .LRB(7), .TMO(4 * LINK + 32)) u_stack_end (
            .clk(clk), .rst_n(rst_n), .up_valid(su_ne), .up_ready(su_r), .up_rec(su_d), .up_cr(1'b0),
            .dn_valid(sd_v), .dn_rec(sd_rec), .dn_cr(),
            .tx_flit(s_tx), .rx_valid(s_rxv), .rx_flit(s_rx),
            .link_up(lup[2*s+1]), .link_fault(lft[2*s+1]), .n_crc_err(crc_v[32*(2*s+1) +: 32]),
            .n_replay(rep_v[32*(2*s+1) +: 32]), .n_seq_drop(), .n_sent());
        ot_qwen_d2d_chan #(.FW(FW), .LAT(LINK)) u_down (.clk(clk), .rst_n(rst_n), .in_flit(h_tx), .out_valid(s_rxv),
            .out_flit(s_rx), .flip_period(flip_period), .flip_start(DOWN_FLIP_START + 13 * s), .flip_bit(7 + 101 * s), .n_flipped(nf_a));
        ot_qwen_d2d_chan #(.FW(FW), .LAT(LINK)) u_up (.clk(clk), .rst_n(rst_n), .in_flit(s_tx), .out_valid(h_rxv),
            .out_flit(h_rx), .flip_period(flip_period), .flip_start(UP_FLIP_START + 17 * s), .flip_bit(29 + 97 * s), .n_flipped(nf_b));
        // stack side of the down record
        wire        qv_l = sd_v && sd_rec[554];
        wire [5:0]  qb_l = sd_rec[548 +: 6];
        wire [511:0] qd_l = sd_rec[36 +: 512];
        wire        mi_valid = sd_v && sd_rec[35];
        wire        mi_g = sd_rec[34];
        wire [1:0]  mi_hh = sd_rec[32 +: 2];
        wire [31:0] mi_data = sd_rec[0 +: 32];

        // ---------------------------------------------------------------- the stack, its HBM ports through the crossing
        wire so_valid, so_g, so_any, pv_valid, pv_g, f;
        wire [1:0] so_type, so_hh, pv_done;
        wire [3:0] so_k;
        wire [31:0] so_data;
        wire [5:0] pv_beat;
        wire [511:0] pv_data;
        wire [R-1:0] e_req_valid, e_req_v, e_req_g, e_rsp_valid;
        wire [13*R-1:0] e_req_t;
        wire [HD*8*R-1:0] e_rsp_data;
        ot_qwen_nearhbm_attn_stack #(.HD(HD), .S(s), .R(R), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT),
                                     .DQ(DQ), .ZW(ZW), .SCALE(SCALE)) u_stack (
            .clk(clk), .rst_n(rst_n), .start(start), .T(T), .q_valid(qv_l), .q_beat(qb_l), .q_data(qd_l),
            .req_valid(e_req_valid), .req_v(e_req_v), .req_g(e_req_g), .req_t(e_req_t),
            .rsp_valid(e_rsp_valid), .rsp_data(e_rsp_data),
            .mi_valid(mi_valid), .mi_g(mi_g), .mi_hh(mi_hh), .mi_data(mi_data), .so_valid(so_valid),
            .so_type(so_type), .so_g(so_g), .so_hh(so_hh), .so_k(so_k), .so_any(so_any), .so_data(so_data),
            .pv_valid(pv_valid), .pv_g(pv_g), .pv_beat(pv_beat), .pv_data(pv_data), .pv_done(pv_done), .fault(f),
            .ev(ev_stack[16*s +: 16]));
        assign fault[s] = f;
        for (x = 0; x < R; x = x + 1) begin : g_x
            localparam integer I = s * R + x;
            wire rq_wr, rs_wr;
            wire [14:0] rq_q;
            ot_async_fifo #(.WIDTH(15), .DEPTH(AFD)) u_req (
                .wr_clk(clk), .wr_rst_n(rst_n), .wr_valid(e_req_valid[x]), .wr_ready(rq_wr),
                .wr_data({e_req_v[x], e_req_g[x], e_req_t[13*x +: 13]}), .wr_overflow(),
                .rd_clk(hclk), .rd_rst_n(hrst_n), .rd_valid(req_valid[I]), .rd_ready(1'b1), .rd_data(rq_q),
                .rd_underflow());
            assign {req_v[I], req_g[I], req_t[13*I +: 13]} = rq_q;
            ot_async_fifo #(.WIDTH(HD * 8), .DEPTH(AFD)) u_rsp (
                .wr_clk(hclk), .wr_rst_n(hrst_n), .wr_valid(rsp_valid[I]), .wr_ready(rs_wr),
                .wr_data(rsp_data[HD*8*I +: HD*8]), .wr_overflow(),
                .rd_clk(clk), .rd_rst_n(rst_n), .rd_valid(e_rsp_valid[x]), .rd_ready(1'b1),
                .rd_data(e_rsp_data[HD*8*x +: HD*8]), .rd_underflow());
            // a request with no room, or a response with no room, is a fault (sticky, in its own domain)
            reg ovf_c, ovf_h;
            always @(posedge clk or negedge rst_n) if (!rst_n) ovf_c <= 1'b0; else if (e_req_valid[x] && !rq_wr) ovf_c <= 1'b1;
            always @(posedge hclk or negedge hrst_n) if (!hrst_n) ovf_h <= 1'b0; else if (rsp_valid[I] && !rs_wr) ovf_h <= 1'b1;
            assign afo[I] = ovf_c | ovf_h;
        end

        // ---------------------------------------------------------------- up: stack end -> hub end
        wire          up_any = (!LAYER_START_FENCE || layer_started) && (so_valid || pv_valid);
        wire [PW-1:0] up_rec = {so_valid, so_type, so_g, so_hh, so_k, so_any, so_data, pv_valid, pv_g, pv_beat, pv_data};
        wire [9:0]    su_n;
        ot_nhb_fifo #(.W(PW), .D(EFD)) u_suq (.clk(clk), .rst_n(rst_n), .push(up_any), .din(up_rec),
                                                .pop(su_ne && su_r), .dout(su_d), .nonempty(su_ne), .count(su_n));
        assign efo[2*s+1] = up_any && (su_n == EFD);
        // hub side of the up record
        assign si_valid[s] = hu_v && hu_rec[562];
        assign si_type[2*s +: 2] = hu_rec[560 +: 2];
        assign si_g[s] = hu_rec[559];
        assign si_hh[2*s +: 2] = hu_rec[557 +: 2];
        assign si_k[4*s +: 4] = hu_rec[553 +: 4];
        assign si_any[s] = hu_rec[552];
        assign si_data[32*s +: 32] = hu_rec[520 +: 32];
        assign pi_valid[s] = hu_v && hu_rec[519];
        assign pi_g[s] = hu_rec[518];
        assign pi_beat[6*s +: 6] = hu_rec[512 +: 6];
        assign pi_data[512*s +: 512] = hu_rec[0 +: 512];
    end endgenerate

    ot_qwen_nearhbm_attn_hub #(.HD(HD), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .ZW(ZW)) u_hub (
        .clk(clk), .rst_n(rst_n), .start(start), .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh),
        .si_k(si_k), .si_any(si_any), .si_data(si_data), .pi_valid(pi_valid), .pi_g(pi_g), .pi_beat(pi_beat),
        .pi_data(pi_data), .mo_valid(mo_valid), .mo_g(mo_g), .mo_hh(mo_hh), .mo_data(mo_data),
        .out_valid(out_valid), .out_g(out_g), .out_beat(out_beat), .out_data(out_data), .fault(fault[4]),
        .ev(ev_hub));

    // sticky overflow of the elastic FIFOs
    reg efo_s;
    always @(posedge clk or negedge rst_n) if (!rst_n) efo_s <= 1'b0; else if (|efo) efo_s <= 1'b1;
    assign sys_fault = (|lft) | efo_s | (|afo);
    assign links_up = &lup;
    integer k;
    reg [31:0] c_sum, r_sum;
    always @(*) begin
        c_sum = 0; r_sum = 0;
        for (k = 0; k < 8; k = k + 1) begin c_sum = c_sum + crc_v[32*k +: 32]; r_sum = r_sum + rep_v[32*k +: 32]; end
    end
    assign crc_errors = c_sum;
    assign replays = r_sum;
endmodule
