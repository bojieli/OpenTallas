`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MTP rollback exactness bench (stream mtp-rollback, 2026-10-08).  Stimulus and expectations from
// tools/mtp_rollback_bench.py (golden-structured reference rolled back by hdc_golden_v41.Model.truncate).
//
// A toy decode model with V4.1's state dataflow (window rows, Engram n-gram history, ratio-2 compressor
// open group + pooled rows + index keys + indexer, ratio-1 source, three DSpark window caches) runs
// prefill and then multi-step greedy speculative decode with forced drafts (accept counts 0 .. g).
// EVERY state word lives in the hardware under test and the rollback is ONLY the commit pointer from
// ot_mtp_commit (n = q + 2 + a; next anchor q_next) -- nothing in this bench rebuilds or restores state.
// The bench computes its own targets, ot_hdc_accept decides a, the bench feeds its own bonus forward, and
// at every step it checks: the drafter's DSpark window reads, t_0 .. t_g, a, and digests of every
// committed state (per-layer window, the compressor's committed open group, the Engram history, the
// DSpark windows, compressed rows + index keys).
//
// Backends:
//   default       DS ROM units: ot_mtp_pos_ring (window, ORDER 0; DSpark window, ORDER 1),
//                 ot_mtp_cmp_slot_ring (L2 open group), ot_mtp_hist_ring (Engram history); compressed rows
//                 and index keys linear by group (HBM rows; dead-row safe by construction)
//   HBM_BACKEND   DS-V4.1 HBM accelerator: ot_dshbm_spec_state (every address; +SPEC_F: the 1.2 GHz successor
//                 ot_dshbm_spec_state_f_token_edge, TOKEN_EDGE_FIX = 1), 4 x ot_hbm_accel_dskv_wb_spec (one a
//                 stack, the real per-token window + DSpark row writer into a sector DRAM model) and
//                 ot_hbm_accel_dswin_rd (the window read stream, driven by spec-state WIN_RD / DSK_RD answers)
// Prints MISMATCH lines and one RESULT line.
// ---------------------------------------------------------------------------
module tb_mtp_rollback;
    parameter integer W = 128;
    parameter integer WRR = 256;          // ROM window ring slots
    parameter integer DRR = 256;          // ROM DSpark window ring slots
    parameter integer TAGCHK = 1;
    parameter integer MUT_OPEN_REG = 0;
    parameter integer MUT_APPEND = 0;
    parameter integer MUT_OFF = 0;
    parameter integer WINSL = 256;        // HBM writer + read stream window slots (as built 128)
    parameter integer SSR = 16;           // HBM spec-state compressor slot ring
    parameter integer STR = 16;           // HBM spec-state token ring
    parameter integer MUT_SHRELOAD = 0;
    parameter integer SH_LOCK = 1;        // MR-6 guard in the writer (0 = as built)   // HBM mutant: reload the index-key block shadow when a key opens a block
    parameter STIM = "stim.txt";
    parameter integer MAXCYC = 200000000;   // watchdog
    localparam integer NL = 4, NST = 3, NG = 4, GM = 5, PMAX_ROM = GM + 1, PMAX_HBM = 8;
    localparam [31:0] PADV = 32'hFFFF_FFFF;

    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;

    function automatic [31:0] mix(input [31:0] a, input [31:0] b);
        reg [31:0] x;
        begin
            x = a ^ (b + 32'h9E3779B9 + (a << 6) + (a >> 2));
            x = x * 32'h85EBCA6B;
            mix = x ^ (x >> 13);
        end
    endfunction

    // ---------------- accept + commit (shared) ----------------
    reg        acc_start_v = 0, tokx_v = 0, amax_v = 0, acc_v = 0;
    reg [16:0] start_tok = 0, tokx_tok = 0, amax_tok = 0;
    reg [2:0]  tokx_slot = 0, amax_slot = 0, acc_g = 0;
    wire       acc_done, acc_any;
    wire [2:0] acc_a;
    wire [3:0] n_emit;
    wire [16:0] bonus;
    ot_hdc_accept #(.NSLOT(8), .NW(17)) u_acc (.clk(clk), .rst_n(rst_n), .start_v(acc_start_v), .start_tok(start_tok),
        .tokx_v(tokx_v), .tokx_slot(tokx_slot), .tokx_tok(tokx_tok), .amax_v(amax_v), .amax_slot(amax_slot),
        .amax_tok(amax_tok), .acc_v(acc_v), .acc_g(acc_g), .stok(), .ttok(), .acc_done(acc_done), .acc_any(acc_any),
        .acc_a(acc_a), .n_emit(n_emit), .bonus(bonus));
    reg        pass_v = 0, pre_v = 0;
    reg [31:0] pass_q = 0, pre_n = 0;
    reg [3:0]  pass_g = 0;
    wire       n_set, squash_v, cm_err;
    wire [31:0] n_val, q_next, squash_from, squash_to;
    wire [7:0] epoch;
    ot_mtp_commit #(.MUT_OFF(MUT_OFF)) u_cm (.clk(clk), .rst_n(rst_n), .pass_v(pass_v), .pass_q(pass_q),
        .pass_g(pass_g), .acc_done(acc_done), .acc_a({1'b0, acc_a}), .pre_v(pre_v), .pre_n(pre_n), .n_set(n_set),
        .n_val(n_val), .q_next(q_next), .squash_v(squash_v), .squash_from(squash_from), .squash_to(squash_to),
        .epoch(epoch), .err(cm_err));

    integer mism = 0, corrupt = 0, corrupt_seen = 0, steps = 0;
    task automatic tick; begin @(posedge clk); #1; end endtask

`ifndef HBM_BACKEND
    // ======================= DS ROM backend =======================
    reg        w_wr_v = 0, w_rd_v = 0; reg [1:0] w_wr_ring = 0, w_rd_ring = 0;
    reg [31:0] w_wr_pos = 0, w_wr_data = 0, w_rd_pos = 0;
    wire       w_rd_ready, w_o_v, w_o_last, w_err; wire [31:0] w_o_data, w_o_pos;
    ot_mtp_pos_ring #(.NRING(NL), .R(WRR), .W(W), .PMAX(PMAX_ROM), .DW(32), .ORDER(0), .TAGCHK(TAGCHK)) u_win (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .wr_v(w_wr_v), .wr_ring(w_wr_ring), .wr_pos(w_wr_pos),
        .wr_data(w_wr_data), .rd_v(w_rd_v), .rd_ready(w_rd_ready), .rd_ring(w_rd_ring), .rd_pos(w_rd_pos),
        .o_v(w_o_v), .o_data(w_o_data), .o_pos(w_o_pos), .o_last(w_o_last), .err(w_err));
    reg        d_wr_v = 0, d_rd_v = 0; reg [1:0] d_wr_ring = 0, d_rd_ring = 0;
    reg [31:0] d_wr_pos = 0, d_wr_data = 0, d_rd_pos = 0;
    wire       d_rd_ready, d_o_v, d_o_last, d_err; wire [31:0] d_o_data, d_o_pos;
    ot_mtp_pos_ring #(.NRING(NST), .R(DRR), .W(W), .PMAX(PMAX_ROM), .DW(32), .ORDER(1), .TAGCHK(TAGCHK)) u_dsk (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .wr_v(d_wr_v), .wr_ring(d_wr_ring), .wr_pos(d_wr_pos),
        .wr_data(d_wr_data), .rd_v(d_rd_v), .rd_ready(d_rd_ready), .rd_ring(d_rd_ring), .rd_pos(d_rd_pos),
        .o_v(d_o_v), .o_data(d_o_data), .o_pos(d_o_pos), .o_last(d_o_last), .err(d_err));
    reg        c_wr_v = 0, c_op_req = 0; reg [31:0] c_wr_pos = 0, c_wr_data = 0;
    wire       c_g_v, c_op_ready, c_op_v, c_op_last, c_op_empty, c_err; wire [31:0] c_g_idx, c_op_data, c_op_pos;
    wire [63:0] c_g_data;
    ot_mtp_cmp_slot_ring #(.RLOG(1), .SR(8), .PMAX(PMAX_ROM), .DW(32), .MUT_OPEN_REG(MUT_OPEN_REG)) u_cs (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .wr_v(c_wr_v), .wr_pos(c_wr_pos), .wr_data(c_wr_data),
        .g_v(c_g_v), .g_idx(c_g_idx), .g_data(c_g_data), .op_req(c_op_req), .op_ready(c_op_ready), .op_v(c_op_v),
        .op_data(c_op_data), .op_pos(c_op_pos), .op_last(c_op_last), .op_empty(c_op_empty), .err(c_err));
    reg        h_tw_v = 0, h_rd_v = 0; reg [31:0] h_tw_pos = 0, h_rd_pos = 0; reg [16:0] h_tw_tok = 0;
    wire       h_rd_ready, h_v, h_pad, h_last, h_err; wire [16:0] h_tok;
    ot_mtp_hist_ring #(.TR(16), .NG(NG), .TW(17), .PMAX(PMAX_ROM), .MUT_APPEND(MUT_APPEND)) u_hist (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .tw_v(h_tw_v), .tw_pos(h_tw_pos), .tw_tok(h_tw_tok),
        .rd_v(h_rd_v), .rd_ready(h_rd_ready), .rd_pos(h_rd_pos), .h_v(h_v), .h_tok(h_tok), .h_pad(h_pad),
        .h_last(h_last), .err(h_err));
    // compressed rows / index keys: linear by group index (HBM rows), source 0 = L2 (r 2), 1 = L3 (r 1)
    reg [31:0] ckm [0:1][0:8191];
    reg [31:0] ikm [0:1][0:8191];
    wire any_err = w_err | d_err | c_err | h_err | cm_err;

    task automatic st_win_write(input integer L, input [31:0] p, input [31:0] v);
        begin
            if (L < NL) begin w_wr_v = 1; w_wr_ring = L; w_wr_pos = p; w_wr_data = v; end
            else begin d_wr_v = 1; d_wr_ring = L - NL; d_wr_pos = p; d_wr_data = v; end
            tick; w_wr_v = 0; d_wr_v = 0;
        end
    endtask
    task automatic st_win_fold(input integer L, input [31:0] p, inout [31:0] d);
        begin
            w_rd_v = 1; w_rd_ring = L; w_rd_pos = p; tick; w_rd_v = 0;
            forever begin tick; if (w_o_v) begin d = mix(d, w_o_data); if (w_o_last) break; end end
        end
    endtask
    task automatic st_dsk_fold(input integer s, input [31:0] a, inout [31:0] d);
        begin
            d_rd_v = 1; d_rd_ring = s; d_rd_pos = a; tick; d_rd_v = 0;
            forever begin tick; if (d_o_v) begin d = mix(d, d_o_data); if (d_o_last) break; end end
        end
    endtask
    task automatic st_slot_write(input [31:0] p, input [31:0] sv, output reg done, output reg [31:0] pooled);
        begin
            c_wr_v = 1; c_wr_pos = p; c_wr_data = sv; tick; c_wr_v = 0;
            done = c_g_v;
            pooled = mix(mix(32'h77, c_g_data[31:0]), c_g_data[63:32]);
        end
    endtask
    task automatic st_slot_open_fold(input [31:0] n, inout [31:0] d);
        begin
            c_op_req = 1; tick; c_op_req = 0;
            if (!(c_op_v && c_op_empty))
                forever begin if (c_op_v) begin d = mix(d, c_op_data); if (c_op_last) break; end tick; end
        end
    endtask
    task automatic st_ck_write(input integer c, input [31:0] p, input [31:0] latent);
        reg [31:0] g;
        begin g = (c == 0) ? p >> 1 : p; ckm[c][g] = latent; ikm[c][g] = mix(latent, 32'h55); end
    endtask
    task automatic st_ik_fold(input integer c, input [31:0] p, inout [31:0] d);
        integer i, n;
        begin n = (c == 0) ? (p + 1) >> 1 : p + 1; for (i = 0; i < n; i = i + 1) d = mix(d, ikm[c][i]); end
    endtask
    task automatic st_ck_sel(input integer c, input [31:0] sel, output reg [31:0] v);
        begin v = ckm[c][sel]; end
    endtask
    task automatic st_ckik_fold(input integer c, input [31:0] n, inout [31:0] d);
        integer i, m;
        begin
            m = (c == 0) ? n >> 1 : n;
            for (i = 0; i < m; i = i + 1) d = mix(d, ckm[c][i]);
            for (i = 0; i < m; i = i + 1) d = mix(d, ikm[c][i]);
        end
    endtask
    task automatic st_tok_write(input [31:0] p, input [16:0] t);
        begin h_tw_v = 1; h_tw_pos = p; h_tw_tok = t; tick; h_tw_v = 0; end
    endtask
    task automatic st_hist_fold(input [31:0] p, inout [31:0] d);
        begin
            h_rd_v = 1; h_rd_pos = p; tick; h_rd_v = 0;
            forever begin tick; if (h_v) begin d = mix(d, h_pad ? PADV : {15'd0, h_tok}); if (h_last) break; end end
        end
    endtask
`else
    // ======================= DS-V4.1 HBM accelerator backend =======================
    localparam integer SWR = 2 * W;
    reg         s_req_v = 0, s_tw_v = 0;
    reg  [3:0]  s_kind = 0; reg [15:0] s_idx = 0; reg [31:0] s_pos = 0, s_tw_pos = 0; reg [16:0] s_tw_tok = 0;
    wire        s_req_ready, s_a_v, s_a_pad, s_a_last, s_a_err; wire [31:0] s_a_addr, s_n; wire [16:0] s_a_tok;
`ifdef SPEC_F
    ot_dshbm_spec_state_f_token_edge #(.TOKEN_EDGE_FIX(1),
`else
    ot_dshbm_spec_state #(
`endif
        .W(W), .PMAX(PMAX_HBM), .WR(SWR), .SR(SSR), .TR(STR), .NG(NG), .NL(NL), .NST(NST), .NSRC(2),
        .RLOG(8'h01), .CKMAX(1 << 13), .TW(17), .AW(32)) u_ss (
        .clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .n(s_n), .tw_v(s_tw_v), .tw_pos(s_tw_pos),
        .tw_tok(s_tw_tok), .req_v(s_req_v), .req_ready(s_req_ready), .req_kind(s_kind), .req_idx(s_idx),
        .req_pos(s_pos), .a_v(s_a_v), .a_addr(s_a_addr), .a_tok(s_a_tok), .a_pad(s_a_pad), .a_last(s_a_last),
        .a_err(s_a_err));
    // the per-token window / DSpark row writer, one instance a stack
    reg          r_v = 0; reg [5:0] r_slot = 0; reg [19:0] r_pos = 0; reg [4351:0] r_data = 0;
    reg  [1:0]   r_kind = 0; reg r_r2 = 0; reg [6:0] r_die = 0; reg r_sh_v = 0; reg [2:0] r_sh_slot = 0;
    wire [3:0]   r_r, wq_v, fence_ok;
    wire [4:0]   wq_pc [0:3], wq_bank [0:3], wq_col [0:3];
    wire [18:0]  wq_row [0:3];
    wire [255:0] wq_data [0:3];
    reg  [5:0]   ack_n [0:3];
    wire [15:0]  iss [0:3], ackd [0:3];
    bit  [255:0] dram [bit [63:0]];          // key {die, stack, pc, bank, row, col}: one HBM a die
    genvar gs;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : g_wb
        ot_hbm_accel_dskv_wb_spec #(.ENABLE(1), .STACK(gs), .WIN_SLOTS(WINSL), .SH_LOCK(SH_LOCK)) u_wb (
            .clk(clk), .rst_n(rst_n), .die(r_die), .pos(r_pos), .row_v(r_v), .row_kind(r_kind), .row_slot(r_slot),
            .row_r2(r_r2), .row_data(r_data), .row_r(r_r[gs]), .sh_v(r_sh_v), .sh_slot(r_sh_slot), .sh_data(4352'd0),
            .wq_v(wq_v[gs]), .wq_pc(wq_pc[gs]), .wq_bank(wq_bank[gs]), .wq_row(wq_row[gs]), .wq_col(wq_col[gs]),
            .wq_data(wq_data[gs]), .wq_r(1'b1), .ack_n(ack_n[gs]), .issued(iss[gs]), .acked(ackd[gs]),
            .fence_ok(fence_ok[gs]));
        always @(posedge clk) begin
            ack_n[gs] <= (wq_v[gs] ? 6'd1 : 6'd0);
            if (wq_v[gs]) dram[{r_die, 2'(gs), wq_pc[gs], wq_bank[gs], wq_row[gs], wq_col[gs]}] = wq_data[gs];
        end
    end endgenerate
    // the window read stream
    reg          rd_rq_v = 0; reg [31:0] rd_rq_addr = 0;
    wire         rd_rq_r, sa_v, sa_last; wire [1:0] sa_stack; wire [4:0] sa_pc, sa_bank, sa_col, sa_t; wire [18:0] sa_row;
    ot_hbm_accel_dswin_rd #(.WIN_SLOTS(WINSL), .WR(SWR)) u_rd (.clk(clk), .rst_n(rst_n), .rq_v(rd_rq_v),
        .rq_addr(rd_rq_addr), .rq_r(rd_rq_r), .sa_v(sa_v), .sa_stack(sa_stack), .sa_pc(sa_pc), .sa_bank(sa_bank),
        .sa_col(sa_col), .sa_row(sa_row), .sa_t(sa_t), .sa_last(sa_last));
    reg [31:0] slotm [bit [31:0]];
    reg [31:0] ckmm [bit [31:0]];
    reg [31:0] ikmm [bit [31:0]];
    wire any_err = s_a_err | cm_err;
    localparam [3:0] K_WIN_RD = 2, K_DSK_RD = 4, K_SLOT_WR = 5, K_SLOT_RD = 6, K_CK_WR = 7, K_IK_RD = 8, K_CK_SEL = 9,
                     K_TOK_RD = 10;

    // one spec-state request; answers collected (addresses, tokens, pads)
    reg [31:0] qa [$]; reg [16:0] qt [$]; reg qp [$];
    task automatic ss_req(input [3:0] k, input [15:0] idx, input [31:0] p);
        begin
            qa.delete(); qt.delete(); qp.delete();
            while (!s_req_ready) tick;
            s_req_v = 1; s_kind = k; s_idx = idx; s_pos = p; tick; s_req_v = 0;
            forever begin
                if (s_a_v) begin qa.push_back(s_a_addr); qt.push_back(s_a_tok); qp.push_back(s_a_pad); if (s_a_last) break; end
                tick;
            end
        end
    endtask
    // read one window row (spec-state address) through the read stream from the DRAM model
    task automatic row_read(input [31:0] addr, output reg [31:0] v);
        reg [255:0] sec; reg [31:0] w0; integer k; reg first;
        begin
            rd_rq_v = 1; rd_rq_addr = addr; tick; rd_rq_v = 0; first = 1; w0 = 0;
            forever begin
                tick;
                if (sa_v) begin
                    if (dram.exists({7'd0, sa_stack, sa_pc, sa_bank, sa_row, sa_col})) sec = dram[{7'd0, sa_stack, sa_pc, sa_bank, sa_row, sa_col}];
                    else begin sec = '0; corrupt = corrupt + 1; end
                    if (first) begin w0 = sec[31:0]; first = 0; end
                    for (k = 0; k < 8; k = k + 1) if (sec[32*k +: 32] !== w0) corrupt = corrupt + 1;
                    if (sa_last) break;
                end
            end
            v = w0;
        end
    endtask
    task automatic st_win_write(input integer L, input [31:0] p, input [31:0] v);
        integer k;
        begin
            r_v = 1; r_slot = L; r_pos = p[19:0]; r_kind = 0; r_r2 = 0; r_die = 0;
            for (k = 0; k < 136; k = k + 1) r_data[32*k +: 32] = v;
            tick; r_v = 0;
            while (!(&r_r) || !(&fence_ok)) tick;
        end
    endtask
    task automatic st_rows_fold(input [3:0] k, input integer idx, input [31:0] p, inout [31:0] d);
        reg [31:0] a [$]; reg [31:0] v; integer i;
        begin
            ss_req(k, idx, p);
            a = qa;
            if (!(a.size() == 1 && qp[0])) for (i = 0; i < a.size(); i = i + 1) begin row_read(a[i], v); d = mix(d, v); end
        end
    endtask
    task automatic st_win_fold(input integer L, input [31:0] p, inout [31:0] d);
        begin st_rows_fold(K_WIN_RD, L, p, d); end
    endtask
    task automatic st_dsk_fold(input integer s, input [31:0] a, inout [31:0] d);
        begin st_rows_fold(K_DSK_RD, s, a, d); end
    endtask
    task automatic st_slot_write(input [31:0] p, input [31:0] sv, output reg done, output reg [31:0] pooled);
        begin
            ss_req(K_SLOT_WR, 0, p); slotm[qa[0]] = sv;
            done = ((p + 1) & 1) == 0; pooled = 0;
            if (done) begin
                ss_req(K_SLOT_RD, 0, p);
                pooled = 32'h77;
                for (int i = 0; i < qa.size(); i++) pooled = mix(pooled, slotm.exists(qa[i]) ? slotm[qa[i]] : 32'hDEAD);
            end
        end
    endtask
    task automatic st_slot_open_fold(input [31:0] n, inout [31:0] d);
        begin
            if (n & 1) begin
                ss_req(K_SLOT_RD, 0, n - 1);
                for (int i = 0; i < qa.size(); i++) d = mix(d, slotm.exists(qa[i]) ? slotm[qa[i]] : 32'hDEAD);
            end
        end
    endtask
    // index keys go to HBM through the real writer (kind 2, owner die of the key's block, 68-B keys packed in
    // 544-B blocks, whole sectors written from the unit's open-block SHADOW); the scan reads them back by the
    // die-local byte map.  Compressed rows (kind 1, 288 B, no shadow) stay in the address-level model.
    function automatic [6:0] key_die(input [31:0] gi); key_die = 7'((gi >> 3) % 96); endfunction
    task automatic key_write(input integer c, input [31:0] p, input [31:0] gi, input [31:0] v);
        integer k;
        begin
            if (MUT_SHRELOAD && (gi & 7) == 0) begin           // the as-built "load the shadow when a block opens"
                r_sh_v = 1; r_sh_slot = c; tick; r_sh_v = 0;
            end
            r_v = 1; r_slot = c; r_pos = p[19:0]; r_kind = 2; r_r2 = (c == 0); r_die = key_die(gi);
            r_data = '0; for (k = 0; k < 17; k = k + 1) r_data[32*k +: 32] = v;
            tick; r_v = 0;
            while (!(&r_r) || !(&fence_ok)) tick;
        end
    endtask
    task automatic key_read(input integer c, input [31:0] gi, output reg [31:0] v);
        reg [7:0] kb [0:67]; reg [31:0] base, S, j, b, k; reg [63:0] key; reg [255:0] sec; integer x;
        begin
            b = gi >> 3; k = (b / 96) * 8 + (gi & 7); base = 68 * k;
            for (x = 0; x < 68; x = x + 1) begin
                S = (base + x) >> 5; j = S >> 7;
                key = {key_die(gi), S[6:5], S[4:0], j[9:7], j[1:0], 19'(4000 + c * 2 + (j >> 10)), j[6:2]};
                if (dram.exists(key)) sec = dram[key]; else begin sec = '0; corrupt = corrupt + 1; end
                kb[x] = sec[8 * ((base + x) & 31) +: 8];
            end
            v = {kb[3], kb[2], kb[1], kb[0]};
            for (x = 1; x < 17; x = x + 1) if ({kb[4*x+3], kb[4*x+2], kb[4*x+1], kb[4*x]} !== v) corrupt = corrupt + 1;
        end
    endtask
    task automatic st_ck_write(input integer c, input [31:0] p, input [31:0] latent);
        begin
            ss_req(K_CK_WR, c, p); ckmm[qa[0]] = latent;
            key_write(c, p, (c == 0) ? p >> 1 : p, mix(latent, 32'h55));
        end
    endtask
    task automatic st_ik_fold(input integer c, input [31:0] p, inout [31:0] d);
        reg [31:0] v;
        begin
            ss_req(K_IK_RD, c, p);
            if (!(qa.size() == 1 && qp[0])) for (int i = 0; i < qa.size(); i++) begin key_read(c, i, v); d = mix(d, v); end
        end
    endtask
    task automatic st_ck_sel(input integer c, input [31:0] sel, output reg [31:0] v);
        begin ss_req(K_CK_SEL, c, sel); v = ckmm.exists(qa[0]) ? ckmm[qa[0]] : 32'hDEAD; end
    endtask
    task automatic st_ckik_fold(input integer c, input [31:0] n, inout [31:0] d);
        reg [31:0] a [$];
        begin
            if (((c == 0) ? n >> 1 : n) > 0) begin
                ss_req(K_IK_RD, c, n - 1); a = qa;
                for (int i = 0; i < a.size(); i++) begin ss_req(K_CK_SEL, c, i); d = mix(d, ckmm.exists(qa[0]) ? ckmm[qa[0]] : 32'hDEAD); end
                for (int i = 0; i < a.size(); i++) begin reg [31:0] v; key_read(c, i, v); d = mix(d, v); end
            end
        end
    endtask
    task automatic st_tok_write(input [31:0] p, input [16:0] t);
        begin s_tw_v = 1; s_tw_pos = p; s_tw_tok = t; tick; s_tw_v = 0; end
    endtask
    task automatic st_hist_fold(input [31:0] p, inout [31:0] d);
        begin
            ss_req(K_TOK_RD, 0, p);
            for (int i = 0; i < qt.size(); i++) d = mix(d, qp[i] ? PADV : {15'd0, qt[i]});
        end
    endtask
`endif

    // ---------------- the toy V4.1 position, layer by layer ----------------
    reg [31:0] hh [0:7];
    task automatic layer_op(input integer L, input integer j, input [31:0] p);
        reg [31:0] h, row, sv, latent, d, v, n; reg have;
        begin
            h = hh[j];
            if (L == 1) st_hist_fold(p, h);
            row = mix(h, 32'h100 + L);
            st_win_write(L, p, row);
            st_win_fold(L, p, h);
            if (L >= 2) begin
                sv = mix(h, 32'h200 + L);
                if (L == 3) begin latent = sv; have = 1; end
                else st_slot_write(p, sv, have, latent);
                if (have) st_ck_write(L - 2, p, latent);
                n = (L == 2) ? (p + 1) >> 1 : p + 1;
                if (n > 0) begin
                    d = h; st_ik_fold(L - 2, p, d);
                    st_ck_sel(L - 2, d % n, v);
                    h = mix(d, v);
                end
            end
            hh[j] = h;
        end
    endtask

    initial begin
        #(MAXCYC * 10);
        $display("RESULT FAIL steps=%0d mism=%0d err=%0d corrupt=%0d cycles=%0d timeout=1", steps, mism, any_err, corrupt, MAXCYC);
        $finish;
    end
    // ---------------- driver ----------------
    integer fd, rc, kind, ek, g, j, L, s, nexp, mprint = 0;
    reg [31:0] q, ystim, y, prev_bonus, qown, nown, dexp [0:2], aexp, texp [0:7], sexp [0:10], dd, sg [0:10];
    reg [16:0] drafts [0:7], toks [0:7];
    reg [31:0] t; reg started;
    string     tagc;
    task automatic fail(input string what, input [31:0] got, input [31:0] exp);
        begin
            mism = mism + 1;
            if (mprint < 20) begin
                $display("MISMATCH step=%0d %s got=%h exp=%h", steps, what, got, exp); mprint = mprint + 1;
            end
        end
    endtask

    initial begin
        fd = $fopen(STIM, "r");
        if (fd == 0) begin $display("RESULT NO_STIM"); $finish; end
        repeat (3) tick; rst_n = 1; repeat (2) tick;
`ifdef HBM_BACKEND
        for (s = 0; s < 2; s = s + 1) begin r_sh_v = 1; r_sh_slot = s; tick; end   // bring-up: empty key blocks
        r_sh_v = 0; tick;
`endif
        started = 0; prev_bonus = 0; qown = 32'hFFFF_FFFF;
        forever begin
            rc = $fscanf(fd, " %s", tagc);
            if (rc != 1 || tagc == "X") break;
            // P kind q y g d1..dg
            rc = $fscanf(fd, " %d %h %h %d", kind, q, ystim, g);
            for (j = 0; j < g; j = j + 1) rc = $fscanf(fd, " %h", drafts[j]);
            rc = $fscanf(fd, " E %d %h %h %h %d", ek, dexp[0], dexp[1], dexp[2], aexp);
            for (j = 0; j <= g; j = j + 1) rc = $fscanf(fd, " %h", texp[j]);
            rc = $fscanf(fd, " S");
            for (j = 0; j < 11; j = j + 1) rc = $fscanf(fd, " %h", sexp[j]);
            // the pass: prefill takes the stimulus token and anchor; a spec pass runs from the hardware's own
            // next anchor (ot_mtp_commit q_next) with the hardware's own bonus as the pending token
            if (kind == 1) begin
                y = prev_bonus; qown = q_next;
                if (y !== ystim) fail("pending_token", y, ystim);
                if (qown !== q) fail("anchor", qown, q);
            end else begin y = ystim; qown = q; end
            toks[0] = y[16:0];
            for (j = 0; j < g; j = j + 1) toks[j + 1] = drafts[j];
            pass_v = 1; pass_q = qown; pass_g = g; acc_start_v = 1; start_tok = y[16:0]; tick; pass_v = 0; acc_start_v = 0;
            for (j = 1; j <= g; j = j + 1) begin tokx_v = 1; tokx_slot = j; tokx_tok = drafts[j - 1]; tick; end
            tokx_v = 0;
            for (j = 0; j <= g; j = j + 1) st_tok_write(qown + 1 + j, toks[j]);
            // drafter side: the three DSpark window caches at the anchor, ring-slot order
            if (kind == 1) for (s = 0; s < NST; s = s + 1) begin
                dd = 32'h5151 + s; st_dsk_fold(s, qown, dd);
                if (dd !== dexp[s]) fail($sformatf("draft_dsk_read_s%0d", s), dd, dexp[s]);
            end
            // verify pass, layer-major
            for (j = 0; j <= g; j = j + 1) hh[j] = mix(32'h1234, {15'd0, toks[j]});
            for (L = 0; L < NL; L = L + 1)
                for (j = 0; j <= g; j = j + 1) layer_op(L, j, qown + 1 + j);
            for (j = 0; j <= g; j = j + 1) begin
                t = (hh[j] >> 8) & 32'hFFF;
                if (t !== texp[j]) fail($sformatf("target_t%0d", j), t, texp[j]);
                amax_v = 1; amax_slot = j; amax_tok = t[16:0]; tick; amax_v = 0;
                for (s = 0; s < NST; s = s + 1) st_win_write(NL + s, qown + 1 + j, mix(hh[j], 32'h400 + s));
            end
            acc_v = 1; acc_g = g; tick; acc_v = 0;
            while (!acc_done) tick;
            if ({29'd0, acc_a} !== aexp) fail("accept_a", {29'd0, acc_a}, aexp);
            prev_bonus = {15'd0, bonus};
            tick; tick; tick;                         // commit broadcast reaches every ring
            nown = n_val;
            if (nown != qown + 2 + {29'd0, acc_a}) fail("commit_n", nown, qown + 2 + {29'd0, acc_a});
            if (nown == 0) begin steps = steps + 1; break; end
            // committed-state digests (positions 0 .. n-1)
            for (L = 0; L < NL; L = L + 1) begin sg[L] = 32'h3000 + L; st_win_fold(L, nown - 1, sg[L]); end
            sg[4] = 32'h3102; st_slot_open_fold(nown, sg[4]);
            sg[5] = 32'h3200; st_hist_fold(nown - 1, sg[5]);
            for (s = 0; s < NST; s = s + 1) begin sg[6 + s] = 32'h3300 + s; st_dsk_fold(s, nown - 1, sg[6 + s]); end
            for (s = 0; s < 2; s = s + 1) begin sg[9 + s] = 32'h3400 + s + 2; st_ckik_fold(s, nown, sg[9 + s]); end
            for (j = 0; j < 11; j = j + 1) if (sg[j] !== sexp[j]) fail($sformatf("state_digest_%0d", j), sg[j], sexp[j]);
            if (corrupt != corrupt_seen) begin fail("corrupt_state_words", corrupt - corrupt_seen, 0); corrupt_seen = corrupt; end
            steps = steps + 1;
            if (mism > 40) break;
        end
        $display("RESULT %s steps=%0d mism=%0d err=%0d corrupt=%0d cycles=%0d",
                 (mism == 0 && !any_err && corrupt == 0 && tagc == "X") ? "PASS" : "FAIL", steps, mism, any_err, corrupt,
                 $time / 10);
        $finish;
    end
endmodule
