`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION MODEL (default-off; selected only by the HBM_STREAM REAL_MEM die
// rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream.sv).  One HBM3E stack (32 pseudo-
// channels) behind the near-HBM STREAMING controller ot_hbm_r14_stream_stack (RTL, WR_EN = 1),
// for the KV service ot_qwen_rt_kv_stream_service.  It replaces ot_qwen_hbm_model_ack (FR-FCFS,
// REFab) of the REAL_MEM runtime with:
//
//   * the controller clock: HBM CK/2 = 976.5625 MHz (1.024 ns), derived from the core clock by a
//     phase accumulator (CORE_FS / CTL_FS); hclk rises on a core falling edge, so the controller
//     samples core-domain registers half a core cycle after they change.  Every crossing pays a
//     two-flop synchroniser in the receiving domain: descriptor and go (toggle + 2 controller
//     flops), landing FIFO entries and write-done (2 core flops), landing credits (2 controller
//     flops on the pop count), write requests (2 controller flops).
//   * the DRAM: the picosecond bank/timing CHECKER of rtl/test/model_ready_hbm_r14/
//     tb_hbm_stream_bw.sv (ot_hdc_hbm_model.sv timing, JESD238 refresh, tRFCpb, tRREFD) extracted
//     as this module, extended with write commands: tRCD (write), tCCD_S/L, tRTW, write-to-read
//     (CWL + BL8 + tWTR_S/L), write recovery before PRE (CWL + BL8 + tWR).  Any violation, an
//     overdue refresh or a landing-credit overflow is a FAULT (the run fails).
//   * the KV map (stream order = position order, the order attention consumes):
//       layer n's window is DRAM row n of every bank of every PC (positions < 2048: 1 MiB);
//       stream sector s (stack order) = {g[6:0], r[7:0]}, g = 16-position tile, r < 128: K of
//       head r[6], dim pair r[5:0]; r >= 128: V of head r[6], position g*16 + r[5:2], dim pair
//       r[1:0]; PC = s[6:2], bank = {s[14:12], s[1:0]}, column = s[11:7] (the bench's map).
//     In the window's logical sectors (ot_qwen_rt_kv_fill_service LAYOUT) the map is the bit
//     permutation  lsec = {r[7], r[6], 2'b00, g, r[5:0]}.  The backing store `mem` keeps the
//     LOGICAL layout of ot_qwen_hbm_model_ack (layer n at sector n * 2^17, public), so the host
//     preload and token check are unchanged; the timing uses the physical map.
//   * landing: per PC a FIFO of CRED sectors (the controller's credits); each beat is presented
//     with its layer-relative logical sector and row, popped by the service (one per PC a cycle).
//   * writes: per PC a buffer of WBUF sectors; the controller's queue takes (bank, column); on the
//     WR command the sector enters the array and a tagged write-done returns at
//     WR + CWL + BL8 + response path (RSP), then crosses to the core.
// ---------------------------------------------------------------------------
module ot_qwen_hbm_stream_ack #(
    parameter integer NPC       = 32,
    parameter integer MEM_WORDS = 3 * 131072,
    parameter integer TAGW      = 9,
    parameter integer CRED      = 32,
    parameter integer PHASE     = 0,
    parameter integer WQ        = 4,
    parameter integer WBUF      = 16,          // power of two
    parameter integer CORE_FS   = 833333,      // core clock period (fs): 1.2 GHz
    parameter integer CTL_FS    = 1024000      // controller clock period (fs): HBM CK/2
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // descriptor (notice) and go, core domain
    input  wire                 d_v,
    output wire                 d_rdy,
    input  wire [18:0]          d_row,
    input  wire [10:0]          d_n,
    input  wire                 go,
    // landing, core domain
    output reg  [NPC-1:0]       l_v,
    output reg  [NPC*17-1:0]    l_sec,
    output reg  [NPC*8-1:0]     l_row,
    output reg  [NPC*256-1:0]   l_data,
    input  wire [NPC-1:0]       l_pop,
    // writes, core domain
    input  wire [NPC-1:0]       w_v,
    input  wire [NPC*24-1:0]    w_sec,
    input  wire [NPC*256-1:0]   w_data,
    input  wire [NPC*TAGW-1:0]  w_tag,
    output reg  [NPC-1:0]       w_room,
    output reg  [NPC-1:0]       wd_v,
    output reg  [NPC*TAGW-1:0]  wd_tag,
    output reg                  fault,
    output reg  [15:0]          fault_code
);
    localparam integer LR = 64;                  // return / landing ring depth (> CRED)
    localparam integer CYC = 1024;               // ps per controller cycle
    localparam longint BURST=1024, TCCDL=2560, CL=12500, CWL=6250, RCD=19375, RCDW=9375, RP=16250, RAS=28125,
                       RTP=5625, WR=20625, WTRS=4375, WTRL=6250, RTW=9948, RRDS=2500, RRDL=3125, FAW=15000,
                       RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;

    // backing store, LOGICAL sector layout (as ot_qwen_hbm_model_ack); public for the host preload
    reg [255:0] mem [0:MEM_WORDS-1] /*verilator public_flat_rw*/;

    function automatic [16:0] s2l(input [14:0] s);
        s2l = {s[7], s[6], 2'b00, s[14:8], s[5:0]};
    endfunction
    function automatic [14:0] l2s(input [16:0] l);
        l2s = {l[12:6], l[16], l[15], l[5:0]};
    endfunction

    // ---- controller clock ---------------------------------------------------------------
    // free-running (also through reset, so the controller domain sees its reset on a clock edge)
    reg [31:0] acc = 0; reg tick_q = 1'b0;
    always @(posedge clk)
        if (acc + CORE_FS >= CTL_FS) begin acc <= acc + CORE_FS - CTL_FS; tick_q <= 1'b1; end
        else begin acc <= acc + CORE_FS; tick_q <= 1'b0; end
    wire hclk = ~clk & tick_q;

    // ---- the streaming controller -------------------------------------------------------
    reg  desc_v_q, go_q; reg [18:0] dq_row; reg [10:0] dq_n;
    wire desc_r, sfault;
    wire [31:0] row_v, col_v, col_we, busy, wr_r;
    wire [95:0] row_op; wire [159:0] row_bank, col_bank, col_col; wire [607:0] row_row;
    reg  [95:0] cred_ret;
    reg  [31:0] wr_v_q; reg [159:0] wr_bank_q, wr_col_q;
    ot_hbm_r14_stream_stack #(.ENABLE(1), .REF_MODE(1), .CRED(CRED), .PHASE(PHASE), .WR_EN(1), .WQ(WQ)) u_ctl (
        .clk(hclk), .rst_n(rst_n), .desc_v(desc_v_q), .desc_r(desc_r), .desc_row(dq_row), .desc_n(dq_n),
        .go(go_q), .next_posted(1'b0), .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row),
        .col_v(col_v), .col_bank(col_bank), .col_col(col_col), .cred_ret(cred_ret), .busy(busy), .fault(sfault),
        .wr_v(wr_v_q), .wr_bank(wr_bank_q), .wr_col(wr_col_q), .wr_r(wr_r), .col_we(col_we));

    // ---- shared state (each variable written by ONE clock domain) ---------------------------
    longint ccyc;                       // core cycles (core domain)
    longint hcyc;                       // controller cycles (controller domain)
    // landing ring (written: controller domain; read pointer: core domain)
    reg [255:0] ld_data [0:NPC-1][0:LR-1];
    reg [16:0]  ld_sec  [0:NPC-1][0:LR-1];
    reg [7:0]   ld_row  [0:NPC-1][0:LR-1];
    longint     ld_vis  [0:NPC-1][0:LR-1];
    integer     ld_w [0:NPC-1], ld_r [0:NPC-1];
    // write buffer (written: core; hand-off and completion pointers: controller)
    reg [23:0]      wb_sec  [0:NPC-1][0:WBUF-1];
    reg [255:0]     wb_data [0:NPC-1][0:WBUF-1];
    reg [TAGW-1:0]  wb_tag  [0:NPC-1][0:WBUF-1];
    longint         wb_vis  [0:NPC-1][0:WBUF-1];  // controller cycle from which it is visible there
    integer         wb_w [0:NPC-1], wb_h [0:NPC-1], wb_c [0:NPC-1];
    // write-done ring (written: controller; read pointer: core)
    reg [TAGW-1:0]  ak_tag [0:NPC-1][0:LR-1];
    longint         ak_vis [0:NPC-1][0:LR-1];
    integer         ak_w [0:NPC-1], ak_r [0:NPC-1];
    longint         pops [0:NPC-1];               // landing pops (core); its count crosses as credits
    reg d_tog, g_tog, a_tog;                       // core: descriptor / go toggles; controller: accept toggle
    reg [18:0] d_row_c; reg [10:0] d_n_c;
    reg h_fault; reg [15:0] h_code;                // controller-domain faults

    // ---- core domain ------------------------------------------------------------------------
    reg a1, a2, a_seen, d_pend, dr1, dr2;
    integer p, k;
    bit trace_c = 1'b0;
    initial trace_c = $test$plusargs("hbm_trace");
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ccyc <= 0; d_tog <= 0; g_tog <= 0; a1 <= 0; a2 <= 0; a_seen <= 0; d_pend <= 0; dr1 <= 0; dr2 <= 0;
            l_v <= 0; wd_v <= 0; w_room <= 0; fault <= 0; fault_code <= 0;
            for (p = 0; p < NPC; p = p + 1) begin ld_r[p] = 0; wb_w[p] = 0; ak_r[p] = 0; pops[p] = 0; end
        end else begin
            ccyc <= ccyc + 1;
            a1 <= a_tog; a2 <= a1; dr1 <= desc_r; dr2 <= dr1;
            if (a2 != a_seen) begin a_seen <= a2; d_pend <= 1'b0; end
            if (d_v) begin
                if (!d_rdy) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                d_row_c <= d_row; d_n_c <= d_n; d_tog <= ~d_tog; d_pend <= 1'b1;
            end
            if (go) g_tog <= ~g_tog;
            for (p = 0; p < NPC; p = p + 1) begin
                // landing: the presented head was taken?
                if (l_v[p] && l_pop[p]) begin ld_r[p] = ld_r[p] + 1; pops[p] = pops[p] + 1; end
                else if (l_pop[p]) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
                if (ld_w[p] - ld_r[p] > CRED) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
                k = ld_r[p] % LR;
                l_v[p] <= (ld_w[p] != ld_r[p]) && ld_vis[p][k] <= ccyc + 1;
                l_data[p*256 +: 256] <= ld_data[p][k]; l_sec[p*17 +: 17] <= ld_sec[p][k]; l_row[p*8 +: 8] <= ld_row[p][k];
                // write-done: presented heads are always taken
                if (wd_v[p]) ak_r[p] = ak_r[p] + 1;
                k = ak_r[p] % LR;
                wd_v[p] <= (ak_w[p] != ak_r[p]) && ak_vis[p][k] <= ccyc + 1;
                wd_tag[p*TAGW +: TAGW] <= ak_tag[p][k];
                // writes in
                if (w_v[p]) begin
                    if (trace_c) $display("HBMTRACE PUSH c=%0d pc=%0d sec=%0d", ccyc, p, w_sec[p*24 +: 24]);
                    if (wb_w[p] - wb_c[p] >= WBUF || (l2s(w_sec[p*24 +: 17]) >> 2) % 32 != p || w_sec[p*24 + 13 +: 2] != 0) begin
                        fault <= 1'b1; fault_code[3] <= 1'b1;
                    end
                    k = wb_w[p] % WBUF;
                    wb_sec[p][k] = w_sec[p*24 +: 24]; wb_data[p][k] = w_data[p*256 +: 256]; wb_tag[p][k] = w_tag[p*TAGW +: TAGW];
                    wb_vis[p][k] = hcyc + 2;
                    wb_w[p] = wb_w[p] + 1;
                end
                w_room[p] <= (WBUF - (wb_w[p] - wb_c[p])) >= 3;
            end
            if (h_fault) begin fault <= 1'b1; fault_code <= fault_code | h_code; end
        end
    end
    assign d_rdy = !d_pend && dr2;

    // ---- controller domain: synchronisers, checker, returns -------------------------------
    reg d1, d2, d_seen, g1, g2, g_seen, go_req;
    longint pc1 [0:NPC-1], pc2 [0:NPC-1], pprev [0:NPC-1];
    // DRAM state / checker (ps)
    longint now;
    bit     b_open [0:31][0:31]; int b_row [0:31][0:31];
    longint b_act [0:31][0:31], b_pre [0:31][0:31], b_rd [0:31][0:31], b_wr [0:31][0:31], b_ref_end [0:31][0:31];
    longint p_last_act [0:31], p_last_rd [0:31], p_last_wr [0:31], p_last_col [0:31], p_last_ref [0:31], p_last_refpb_any [0:31];
    int     p_wr_bg [0:31];
    longint p_act_bg [0:31][0:3], p_col_bg [0:31][0:3], p_faw [0:31][0:3];
    bit [31:0] p_round [0:31];
    longint viol /*verilator public_flat_rw*/, n_act /*verilator public_flat_rw*/, n_rd /*verilator public_flat_rw*/,
            n_wr /*verilator public_flat_rw*/, n_ref /*verilator public_flat_rw*/, n_pre, max_land /*verilator public_flat_rw*/;
    // return queues (controller cycle due)
    longint rq_due [0:NPC-1][0:LR-1]; reg [255:0] rq_dat [0:NPC-1][0:LR-1]; reg [16:0] rq_sec [0:NPC-1][0:LR-1];
    reg [7:0] rq_row [0:NPC-1][0:LR-1];
    integer rq_w [0:NPC-1], rq_r [0:NPC-1];
    longint aq_due [0:NPC-1][0:LR-1]; reg [TAGW-1:0] aq_tag [0:NPC-1][0:LR-1];
    integer aq_w [0:NPC-1], aq_r [0:NPC-1];
    task automatic v(input string what, input integer pc, input integer bk);
        if (viol < 20) $display("HBM_STREAM VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, pc, bk, what);
        viol++;
        h_fault <= 1'b1; h_code[8] <= 1'b1;
    endtask

    integer q, b, gg;
    bit trace = 1'b0;
    initial trace = $test$plusargs("hbm_trace");
    always @(posedge hclk or negedge rst_n) begin
        if (!rst_n) begin
            hcyc = 0; d1 <= 0; d2 <= 0; d_seen <= 0; g1 <= 0; g2 <= 0; g_seen <= 0; go_req <= 0; a_tog <= 0;
            desc_v_q <= 0; go_q <= 0; cred_ret <= 0; wr_v_q <= 0; h_fault <= 0; h_code <= 0;
            viol = 0; n_act = 0; n_rd = 0; n_wr = 0; n_ref = 0; n_pre = 0; max_land = 0;
            for (q = 0; q < NPC; q = q + 1) begin
                pc1[q] = 0; pc2[q] = 0; pprev[q] = 0; rq_w[q] = 0; rq_r[q] = 0; aq_w[q] = 0; aq_r[q] = 0;
                ld_w[q] = 0; ak_w[q] = 0; wb_h[q] = 0; wb_c[q] = 0;
                p_last_act[q] = -1000000; p_last_rd[q] = -1000000; p_last_wr[q] = -1000000; p_last_col[q] = -1000000;
                p_last_refpb_any[q] = -1000000; p_round[q] = 0; p_wr_bg[q] = 0;
                begin : ph
                    automatic int P = 118;                                       // REFpb period (cycles), as the RTL
                    automatic int base = (PHASE + (q * P) / 32) % P;
                    p_last_ref[q] = longint'(base + ((base + P + q) % 2)) * CYC;
                end
                for (gg = 0; gg < 4; gg = gg + 1) begin p_act_bg[q][gg] = -1000000; p_col_bg[q][gg] = -1000000; p_faw[q][gg] = -1000000; end
                for (b = 0; b < 32; b = b + 1) begin
                    b_open[q][b] = 0; b_act[q][b] = -1000000; b_pre[q][b] = -1000000; b_rd[q][b] = -1000000;
                    b_wr[q][b] = -1000000; b_ref_end[q][b] = 0; b_row[q][b] = 0;
                end
            end
        end else begin
            now = hcyc * CYC;
            // -- descriptor / go crossings
            d1 <= d_tog; d2 <= d1; g1 <= g_tog; g2 <= g1;
            if (desc_v_q && desc_r) begin desc_v_q <= 1'b0; a_tog <= ~a_tog; end
            else if (!desc_v_q && d2 != d_seen) begin desc_v_q <= 1'b1; d_seen <= d2; dq_row <= d_row_c; dq_n <= d_n_c; end
            if (g2 != g_seen) begin g_seen <= g2; go_req <= 1'b1; end
            go_q <= 1'b0;
            if ((go_req || g2 != g_seen) && busy[0] && !go_q) begin go_q <= 1'b1; go_req <= 1'b0; end
            if (sfault) begin h_fault <= 1'b1; h_code[9] <= 1'b1; end
            // -- commands issued this cycle (sampled at the edge, as the bench)
            for (q = 0; q < NPC; q = q + 1) begin
                if (row_v[q]) begin
                    automatic int op = row_op[q*3 +: 3], bk = row_bank[q*5 +: 5], rw = row_row[q*19 +: 19], g = bk & 3;
                    case (op)
                        1: begin // ACT
                            n_act++;
                            if (trace) $display("HBMTRACE ACT h=%0d pc=%0d bank=%0d", hcyc, q, bk);
                            if (b_open[q][bk]) v("ACT to open bank", q, bk);
                            if (now < b_pre[q][bk] + RP) v("tRP", q, bk);
                            if (now < b_act[q][bk] + RAS + RP) v("tRC", q, bk);
                            if (now < p_last_act[q] + RRDS) v("tRRD_S", q, bk);
                            if (now < p_act_bg[q][g] + RRDL) v("tRRD_L", q, bk);
                            if (now < p_faw[q][0] + FAW) v("tFAW", q, bk);
                            if (now < b_ref_end[q][bk]) v("ACT during refresh", q, bk);
                            if (now < p_last_refpb_any[q] + RREFD) v("tRREFD", q, bk);
                            b_open[q][bk] = 1; b_row[q][bk] = rw; b_act[q][bk] = now;
                            p_last_act[q] = now; p_act_bg[q][g] = now;
                            p_faw[q][0] = p_faw[q][1]; p_faw[q][1] = p_faw[q][2]; p_faw[q][2] = p_faw[q][3]; p_faw[q][3] = now;
                        end
                        0: begin // PRE
                            n_pre++;
                            if (!b_open[q][bk]) v("PRE closed bank", q, bk);
                            if (now < b_act[q][bk] + RAS) v("tRAS", q, bk);
                            if (now < b_rd[q][bk] + RTP) v("tRTP", q, bk);
                            if (now < b_wr[q][bk] + CWL + BURST + WR) v("tWR", q, bk);
                            b_open[q][bk] = 0; b_pre[q][bk] = now;
                        end
                        6: begin // REFpb
                            n_ref++;
                            if (b_open[q][bk]) v("REFpb to open bank", q, bk);
                            if (now < b_pre[q][bk] + RP) v("tRP (REFpb)", q, bk);
                            if (now < b_act[q][bk] + RAS + RP) v("tRC (REFpb)", q, bk);
                            if (now < b_ref_end[q][bk]) v("REFpb during refresh", q, bk);
                            if (now < p_last_act[q] + RREFD) v("tRREFD (REFpb after ACT)", q, bk);
                            if (now < p_last_refpb_any[q] + RREFD) v("tRREFD (REFpb after REFpb)", q, bk);
                            if (p_round[q][bk]) v("REFpb bank twice in one round", q, bk);
                            p_round[q][bk] = 1; if (&p_round[q]) p_round[q] = 0;
                            if (now - p_last_ref[q] > REFI / 32) v("REFpb late", q, bk);
                            p_last_ref[q] = now; p_last_refpb_any[q] = now;
                            b_ref_end[q][bk] = now + RFCPB;
                        end
                        default: v("row op not used by this controller", q, bk);
                    endcase
                end
                if (now - p_last_ref[q] > REFI / 32) begin v("refresh overdue", q, 0); p_last_ref[q] = now; end
                if (col_v[q]) begin
                    automatic int bk = col_bank[q*5 +: 5], cl = col_col[q*5 +: 5], g = bk & 3;
                    automatic logic [14:0] s = {3'(bk >> 2), 5'(cl), 5'(q), 2'(bk & 3)};
                    automatic logic [16:0] ls = s2l(s);
                    automatic longint a = longint'(b_row[q][bk]) * 131072 + ls;
                    if (!b_open[q][bk]) v(col_we[q] ? "WR closed bank" : "RD closed bank", q, bk);
                    if (now < b_act[q][bk] + (col_we[q] ? RCDW : RCD)) v("tRCD", q, bk);
                    if (now < p_last_col[q] + BURST) v("tCCD_S", q, bk);
                    if (now < p_col_bg[q][g] + TCCDL) v("tCCD_L", q, bk);
                    if (now < b_ref_end[q][bk]) v("column command during refresh", q, bk);
                    if (b_row[q][bk] * 131072 >= MEM_WORDS) v("row beyond the backing store", q, bk);
                    p_last_col[q] = now; p_col_bg[q][g] = now;
                    if (!col_we[q]) begin
                        if (now < p_last_wr[q] + CWL + BURST + ((p_wr_bg[q] == g) ? WTRL : WTRS)) v("tWTR", q, bk);
                        n_rd++;
                        p_last_rd[q] = now; b_rd[q][bk] = now;
                        k = rq_w[q] % LR;
                        rq_due[q][k] = (now + CL + BURST + RSP + CYC - 1) / CYC;
                        rq_dat[q][k] = (a < MEM_WORDS) ? mem[a] : 256'd0;
                        rq_sec[q][k] = ls; rq_row[q][k] = 8'(b_row[q][bk]);
                        rq_w[q] = rq_w[q] + 1;
                    end else begin
                        if (now < p_last_rd[q] + RTW) v("tRTW", q, bk);
                        n_wr++;
                        p_last_wr[q] = now; p_wr_bg[q] = g; b_wr[q][bk] = now;
                        // the write is the buffer's oldest handed-off sector of this PC
                        k = wb_c[q] % WBUF;
                        if (trace) $display("HBMTRACE WR h=%0d c=%0d pc=%0d bank=%0d sec=%0d", hcyc, ccyc, q, bk, a);
                        if (wb_c[q] == wb_h[q] || wb_sec[q][k] != 24'(a)) begin
                            v("WR does not match the oldest queued write", q, bk);
                        end else begin
                            mem[a] = wb_data[q][k];
                            gg = aq_w[q] % LR;
                            aq_due[q][gg] = (now + CWL + BURST + RSP + CYC - 1) / CYC;
                            aq_tag[q][gg] = wb_tag[q][k];
                            aq_w[q] = aq_w[q] + 1;
                        end
                        wb_c[q] = wb_c[q] + 1;
                    end
                end
            end
            for (gg = 0; gg < 16; gg = gg + 1) if (row_v[2*gg] && row_v[2*gg+1]) v("two row commands on one channel slot", 2*gg, 0);
            // -- returns land / write-done leaves (crosses to the core: visible two core edges later)
            for (q = 0; q < NPC; q = q + 1) begin
                while (rq_r[q] != rq_w[q] && rq_due[q][rq_r[q] % LR] <= hcyc) begin
                    k = rq_r[q] % LR; gg = ld_w[q] % LR;
                    ld_data[q][gg] = rq_dat[q][k]; ld_sec[q][gg] = rq_sec[q][k]; ld_row[q][gg] = rq_row[q][k];
                    ld_vis[q][gg] = ccyc + 2;
                    ld_w[q] = ld_w[q] + 1; rq_r[q] = rq_r[q] + 1;
                    if (ld_w[q] - ld_r[q] > max_land) max_land = ld_w[q] - ld_r[q];
                end
                while (aq_r[q] != aq_w[q] && aq_due[q][aq_r[q] % LR] <= hcyc) begin
                    k = aq_r[q] % LR; gg = ak_w[q] % LR;
                    ak_tag[q][gg] = aq_tag[q][k]; ak_vis[q][gg] = ccyc + 2;
                    ak_w[q] = ak_w[q] + 1; aq_r[q] = aq_r[q] + 1;
                end
                // credits: the core's pop count through two controller flops
                pc2[q] = pc1[q]; pc1[q] = pops[q];
                cred_ret[q*3 +: 3] <= 3'(pc2[q] - pprev[q]);
                if (pc2[q] - pprev[q] > 7) begin h_fault <= 1'b1; h_code[10] <= 1'b1; end
                pprev[q] = pc2[q];
                // write hand-off to the controller queue (visible two controller edges after the push)
                if (wr_v_q[q] && wr_r[q]) begin
                    if (trace) $display("HBMTRACE HAND h=%0d c=%0d pc=%0d", hcyc, ccyc, q);
                    wb_h[q] = wb_h[q] + 1;
                end
                k = wb_h[q] % WBUF;
                begin
                    automatic logic [14:0] s = l2s(wb_sec[q][k][16:0]);
                    wr_v_q[q] <= (wb_h[q] != wb_w[q]) && wb_vis[q][k] <= hcyc + 1;
                    wr_bank_q[q*5 +: 5] <= {s[14:12], s[1:0]};
                    wr_col_q[q*5 +: 5] <= s[11:7];
                end
            end
            hcyc = hcyc + 1;
        end
    end
endmodule
