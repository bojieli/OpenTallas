`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_mtp_seed_ctl (mtp-lead 2026-10-09): production controller / collector of the DS-V4.1 ROM MTP seed
// projection dsrom_mtp_seed_projection_full15360 (mtp.0.main_proj: 5120 x 15360 FP8 + UE8M0 block scales; the
// draft input is the HC mean of layers 37/38/39, 3 x 5120 BF16).
//
// The native q-element (ot_v41_rom_elem_q_qxpq_w10 NB 2, selected QS5f parameters) is a separately hardened
// block; this controller drives it through registered pins (e_*) and owns everything the element lacks:
//
//   1. activation intake: 240 beats of 64 BF16 lanes (in_xa: lanes 0..31, in_xb: lanes 32..63) -> two
//      ot_hdc_actquant FP8 quantisers (one 32-value block each per cycle) -> 480 blocks of {256-b codes,
//      10-b UE8 exponent}, held for every row pair of the token in 4 real SRAMs (ot_sram_1r1w_128x256,
//      bank {i[3], i[0]}, address {i[8:4], i[2:1]}: the two blocks a quantiser cycle writes and the two
//      blocks a stream beat reads (i, i + 8) are always in different banks) + 480 x 10 exponent flops;
//   2. the K segmentation the 13-bit native field descriptor needs: K = 15360 runs as four aligned phases
//      K = 4096 / 4096 / 4096 / 3072 (128 / 128 / 128 / 96 beats); per (row pair, phase) the 25 config words
//      come from the generated descriptor ot_dsrom_mtp_seed_desc with the row pair's ROM offset added to
//      word 0 [41:29] (segment base address) and word 16 [19:6] (PP first word index): rp * WPR
//      (the generator asserts this form for every row pair it emits);
//   3. the element's own fences, at its pins: bank_free && sh_free before config, F_CFG cycles after the
//      last config word, sh_free && !walking, F_GO cycles, go, stream beat 0 exactly 5 cycles after go,
//      wait both partials and !busy, F_DRAIN quiet cycles (the registered pins add one cycle each way, so
//      F_CFG / F_GO default 8 where the pin-level bench used 6);
//   4. the ORDERED reduction: per row the four FP32 phase roots join as (r0 + r1) + (r2 + r3) on one
//      ot_v41_fadd (LAT 8), serially, row 0 then row 1 -- the balanced order the released golden's chunk8
//      tree has at 4096-aligned split points (a three-way 5120 split or a sequential join is NOT exact);
//      the join of row pair rp overlaps the phases of rp + 1 (root double buffer);
//   5. BF16 rounding once (RNE) of the full FP32 root, emitted with the FP32 root (before main_norm).
//
// MUT_JOIN = 1 (bench mutant only): sequential ((r0 + r1) + r2) + r3 -- must FAIL the exact gate.
// Faults (sticky, out_fault): [0] element fault / perr / wrong prow-pseg-pnseg, [1] FP32 join err,
// [2] protocol (unexpected or duplicate partial, beat outside intake, quantiser valid skew), [3] quantiser fault.
// Cycle cost (RP row pairs, measured by the gate): quantise ~253, then per row pair 4 phases, join hidden
// except after the last row pair.
// ---------------------------------------------------------------------------
module ot_dsrom_mtp_seed_ctl #(
    parameter integer RP = 8,            // row pairs per native NB2 element (ROM 4096 deep: 8 x 480 words)
    parameter integer WPR = 480,         // ROM words per row pair (sum of the four phases' beats)
    parameter integer ROW0 = 0,          // first output row of this element
    parameter integer F_CFG = 8,
    parameter integer F_GO = 8,
    parameter integer F_DRAIN = 32,
    parameter integer MUT_JOIN = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // activation: one token = exactly 240 beats, sent only after out_x_rdy (level: ready for a token)
    input  wire          in_x_v,
    input  wire [511:0]  in_xa_bf16,
    input  wire [511:0]  in_xb_bf16,
    output reg           out_x_rdy,
    // projection rows
    output reg           out_y_v,
    output reg  [15:0]   out_y_row,
    output reg  [15:0]   out_y_bf16,
    output reg  [31:0]   out_y_root,
    output reg           out_done,
    output reg           out_busy,
    output reg  [3:0]    out_fault,
    // native element (registered both ways)
    output reg           e_cfg_v,
    output reg  [4:0]    e_cfg_a,
    output reg  [47:0]   e_cfg_d,
    output reg           e_go,
    output wire [1:0]    e_go_tag,
    output reg           e_xs_v,
    output reg  [7:0]    e_xs_p,
    output reg  [2:0]    e_xs_b,
    output reg  [1:0]    e_xs_sv,
    output reg  [255:0]  e_xs_q0,
    output reg  [9:0]    e_xs_e0,
    output reg  [255:0]  e_xs_q1,
    output reg  [9:0]    e_xs_e1,
    output wire [2:0]    e_xs_pos,
    input  wire          e_walking,
    input  wire          e_bank_free,
    input  wire          e_sh_free,
    input  wire [1:0]    e_pv,
    input  wire [63:0]   e_pval,
    input  wire [31:0]   e_prow,
    input  wire [9:0]    e_pseg,
    input  wire [9:0]    e_pnseg,
    input  wire [1:0]    e_perr,
    input  wire [5:0]    e_ppos,
    input  wire          e_busy,
    input  wire          e_fault
);
    assign e_go_tag = 2'd0;
    assign e_xs_pos = 3'd0;

    // ---------------- input pin registers ----------------
    reg         r_x_v;
    reg [511:0] r_xa, r_xb;
    reg         r_walking, r_bank_free, r_sh_free, r_busy, r_efault;
    reg [1:0]   r_pv, r_perr;
    reg [63:0]  r_pval;
    reg [31:0]  r_prow;
    reg [9:0]   r_pseg, r_pnseg;
    always @(posedge clk) begin
        r_xa <= in_xa_bf16; r_xb <= in_xb_bf16;
        r_pval <= e_pval; r_prow <= e_prow; r_pseg <= e_pseg; r_pnseg <= e_pnseg;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            r_x_v <= 1'b0; r_walking <= 1'b0; r_bank_free <= 1'b0; r_sh_free <= 1'b0; r_busy <= 1'b0;
            r_efault <= 1'b0; r_pv <= 2'b0; r_perr <= 2'b0;
        end else begin
            r_x_v <= in_x_v; r_walking <= e_walking; r_bank_free <= e_bank_free; r_sh_free <= e_sh_free;
            r_busy <= e_busy; r_efault <= e_fault; r_pv <= e_pv; r_perr <= e_perr;
        end

    // ---------------- control state ----------------
    localparam [3:0] S_IDLE = 4'd0, S_QIN = 4'd1, S_QWAIT = 4'd2, S_WFREE = 4'd3, S_CFG = 4'd4, S_F1 = 4'd5,
                     S_WSH = 4'd6, S_F2 = 4'd7, S_GO = 4'd8, S_PRE = 4'd9, S_STRM = 4'd10, S_DRAIN = 4'd11,
                     S_QUIET = 4'd12, S_HAND = 4'd13, S_FIN = 4'd14;
    reg [3:0]  st;
    reg [7:0]  nin;            // beats received (0..240)
    reg [8:0]  nq;             // quantised blocks written (0..480)
    reg [1:0]  ph;
    reg [3:0]  rp;
    reg [5:0]  cnt;
    reg [6:0]  k;              // stream beat within the phase
    reg [1:0]  hit;            // partial received per row in this phase
    reg [3:0]  fault;

    // ---------------- activation quantisers + buffer ----------------
    wire [1023:0] xa32, xb32;
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_lane
        assign xa32[32*gl +: 32] = {r_xa[16*gl +: 16], 16'h0};
        assign xb32[32*gl +: 32] = {r_xb[16*gl +: 16], 16'h0};
    end endgenerate
    wire       x_take = r_x_v && (st == S_IDLE || st == S_QIN) && nin != 8'd240;
    wire [1:0] aqv, aqf;
    wire [255:0] aq0, aq1;
    wire [9:0] ae0, ae1;
    wire [511:0] ay0_unused, ay1_unused;
    ot_hdc_actquant u_q0 (.clk(clk), .rst_n(rst_n), .v(x_take), .fp4(1'b0), .x(xa32), .vo(aqv[0]), .q(aq0),
                          .e(ae0), .y(ay0_unused), .fault(aqf[0]));
    ot_hdc_actquant u_q1 (.clk(clk), .rst_n(rst_n), .v(x_take), .fp4(1'b0), .x(xb32), .vo(aqv[1]), .q(aq1),
                          .e(ae1), .y(ay1_unused), .fault(aqf[1]));
    wire q_wr = aqv[0] && nq != 9'd480;
    // writes: block nq (even) -> bank {nq[3],0}, nq + 1 -> bank {nq[3],1}, address {nq[8:4], nq[2:1]}
    wire [6:0] w_addr = {nq[8:4], nq[2:1]};
    reg  [9:0] ebuf [0:479];
    always @(posedge clk) if (q_wr) begin ebuf[nq] <= ae0; ebuf[nq + 9'd1] <= ae1; end

    // ---------------- descriptor + stream pipeline ----------------
    wire [47:0] d_cfg;
    wire [13:0] d_strm;
    wire [8:0]  d_kblk;
    wire [6:0]  d_nbeat;
    ot_dsrom_mtp_seed_desc u_desc (.ph(ph), .a(cnt[4:0]), .k(k), .cfg(d_cfg), .strm(d_strm), .kblk(d_kblk),
                                   .nbeat(d_nbeat));
    wire [12:0] rp_base = rp * WPR;
    reg  [47:0] cfg_word;
    always @* begin
        cfg_word = d_cfg;
        if (cnt[4:0] == 5'd0)  cfg_word[41:29] = d_cfg[41:29] + rp_base;
        if (cnt[4:0] == 5'd16) cfg_word[19:6]  = d_cfg[19:6] + {1'b0, rp_base};
    end
    // stage 1: stream word; stage 2: SRAM read + exponent read; stage 3: element pin register
    reg        s1_v, s2_v;
    reg [13:0] s1_w, s2_w;
    reg [8:0]  s1_i;
    reg        s2_par;
    reg [9:0]  s2_e0, s2_e1;
    wire [8:0] i0 = s1_i;                       // block of q0; q1 = i0 + 8 (i0[3] == 0)
    wire [6:0] r_addr = {i0[8:4], i0[2:1]};
    wire [255:0] bank_q [0:3];
    genvar gb;
    generate for (gb = 0; gb < 4; gb = gb + 1) begin : g_bank
        // bank gb = {i[3], i[0]}
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(s1_v), .r_addr_in(r_addr), .rd_out(bank_q[gb]),
            .w_ce_in(q_wr && (nq[3] == gb[1])), .w_addr_in(w_addr), .wd_in(gb[0] ? aq1 : aq0),
            .w_mask_in({256{1'b1}}), .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(16'd0));
    end endgenerate

    // ---------------- root double buffer + ordered join ----------------
    reg [31:0] proot [0:7];                    // phase roots of the row pair in flight: [2*ph + j]
    reg [31:0] jroot [0:7];                    // roots handed to the join
    reg        jbusy;
    reg [3:0]  jrp;
    reg        jrow;
    reg [1:0]  jstep;
    reg        jwait;
    reg [31:0] t0, t1;
    reg        fa_v;
    reg [31:0] fa_a, fa_b;
    wire       fa_vo;
    wire [31:0] fa_y;
    wire [1:0] fa_err;
    ot_v41_fadd u_join (.clk(clk), .rst_n(rst_n), .valid_in(fa_v), .a(fa_a), .b(fa_b), .y(fa_y), .err(fa_err),
                        .valid_out(fa_vo));
    wire [32:0] bf_sum = {1'b0, fa_y} + 33'h7FFF + {32'h0, fa_y[16]};

    integer qi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; nin <= 0; nq <= 0; ph <= 0; rp <= 0; cnt <= 0; k <= 0; hit <= 0; fault <= 0;
            out_x_rdy <= 1'b0; out_done <= 1'b0; out_busy <= 1'b0; out_fault <= 0;
            e_cfg_v <= 1'b0; e_cfg_a <= 0; e_cfg_d <= 0; e_go <= 1'b0;
            e_xs_v <= 1'b0; e_xs_p <= 0; e_xs_b <= 0; e_xs_sv <= 0; e_xs_e0 <= 0; e_xs_e1 <= 0;
            s1_v <= 1'b0; s2_v <= 1'b0; s1_w <= 0; s2_w <= 0; s1_i <= 0; s2_par <= 0; s2_e0 <= 0; s2_e1 <= 0;
            jbusy <= 1'b0; jrp <= 0; jrow <= 0; jstep <= 0; jwait <= 1'b0; fa_v <= 1'b0; fa_a <= 0; fa_b <= 0;
            t0 <= 0; t1 <= 0; out_y_v <= 1'b0; out_y_row <= 0; out_y_bf16 <= 0; out_y_root <= 0;
        end else begin
            out_done <= 1'b0; e_cfg_v <= 1'b0; e_go <= 1'b0; fa_v <= 1'b0; out_y_v <= 1'b0;
            out_x_rdy <= (st == S_IDLE);
            out_busy <= (st != S_IDLE) || jbusy;
            out_fault <= fault;
            // ---- intake ----
            if (r_x_v && !x_take) fault[2] <= 1'b1;
            if (x_take) nin <= nin + 8'd1;
            if (aqv[0] != aqv[1]) fault[2] <= 1'b1;
            if (|(aqf & aqv)) fault[3] <= 1'b1;
            if (q_wr) nq <= nq + 9'd2;
            // ---- partials ----
            if (|r_pv) begin
                if (!(st == S_STRM || st == S_DRAIN) || |(r_pv & hit)) fault[2] <= 1'b1;
                for (qi = 0; qi < 2; qi = qi + 1) if (r_pv[qi]) begin
                    proot[2 * ph + qi] <= r_pval[32 * qi +: 32];
                    if (r_perr[qi] || r_prow[16 * qi +: 16] != qi || r_pseg[5 * qi +: 5] != 5'd0 ||
                        r_pnseg[5 * qi +: 5] != 5'd1) fault[0] <= 1'b1;
                end
                hit <= hit | r_pv;
            end
            if (r_efault) fault[0] <= 1'b1;
            // ---- stream pipeline ----
            s1_v <= (st == S_STRM);
            if (st == S_STRM) begin
                s1_w <= d_strm;
                s1_i <= d_kblk + {d_strm[8:1], 4'b0} + {6'b0, d_strm[11:9]};
            end
            s2_v <= s1_v; s2_w <= s1_w; s2_par <= i0[0];
            if (s1_v) begin s2_e0 <= ebuf[i0]; s2_e1 <= ebuf[i0 + 9'd8]; end
            e_xs_v <= s2_v && s2_w[0];
            if (s2_v) begin
                e_xs_p <= s2_w[8:1]; e_xs_b <= s2_w[11:9]; e_xs_sv <= s2_w[13:12];
                e_xs_e0 <= s2_e0; e_xs_e1 <= s2_e1;
            end
            // ---- sequencer ----
            case (st)
                S_IDLE: if (x_take) st <= S_QIN;
                S_QIN:  if (nin == 8'd240) st <= S_QWAIT;
                S_QWAIT: if (nq == 9'd480) begin st <= S_WFREE; ph <= 0; rp <= 0; end
                S_WFREE: if (r_bank_free && r_sh_free) begin st <= S_CFG; cnt <= 0; end
                S_CFG: begin
                    e_cfg_v <= 1'b1; e_cfg_a <= cnt[4:0]; e_cfg_d <= cfg_word;
                    if (cnt == 6'd24) begin st <= S_F1; cnt <= F_CFG[5:0]; end else cnt <= cnt + 6'd1;
                end
                S_F1: if (cnt == 0) st <= S_WSH; else cnt <= cnt - 6'd1;
                S_WSH: if (r_sh_free && !r_walking) begin st <= S_F2; cnt <= F_GO[5:0]; end
                S_F2: if (cnt == 0) st <= S_GO; else cnt <= cnt - 6'd1;
                S_GO: begin e_go <= 1'b1; st <= S_PRE; cnt <= 6'd1; hit <= 2'b00; end
                S_PRE: if (cnt == 0) begin st <= S_STRM; k <= 0; end else cnt <= cnt - 6'd1;
                S_STRM: if (k == d_nbeat - 7'd1) st <= S_DRAIN; else k <= k + 7'd1;
                S_DRAIN: if (hit == 2'b11 && !r_busy && !s1_v && !s2_v) begin st <= S_QUIET; cnt <= F_DRAIN[5:0]; end
                S_QUIET: if (cnt == 0) begin
                        if (ph == 2'd3) st <= S_HAND; else begin ph <= ph + 2'd1; st <= S_WFREE; end
                    end else cnt <= cnt - 6'd1;
                S_HAND: if (!jbusy) begin
                        for (qi = 0; qi < 8; qi = qi + 1) jroot[qi] <= proot[qi];
                        jbusy <= 1'b1; jrp <= rp; jrow <= 1'b0; jstep <= 0; jwait <= 1'b0;
                        ph <= 0;
                        if (rp == RP - 1) st <= S_FIN; else begin rp <= rp + 4'd1; st <= S_WFREE; end
                    end
                S_FIN: if (!jbusy) begin
                        st <= S_IDLE; out_done <= 1'b1; nin <= 0; nq <= 0; rp <= 0;
                    end
                default: st <= S_IDLE;
            endcase
            // ---- ordered join: per row (r0 + r1) + (r2 + r3), serial ----
            if (jbusy && !jwait) begin
                fa_v <= 1'b1; jwait <= 1'b1;
                case (jstep)
                    2'd0: begin fa_a <= jroot[{2'd0, jrow}]; fa_b <= jroot[{2'd1, jrow}]; end
                    2'd1: if (MUT_JOIN != 0) begin fa_a <= t0; fa_b <= jroot[{2'd2, jrow}]; end
                          else begin fa_a <= jroot[{2'd2, jrow}]; fa_b <= jroot[{2'd3, jrow}]; end
                    default: if (MUT_JOIN != 0) begin fa_a <= t1; fa_b <= jroot[{2'd3, jrow}]; end
                             else begin fa_a <= t0; fa_b <= t1; end
                endcase
            end
            if (fa_vo) begin
                if (fa_err != 2'd0) fault[1] <= 1'b1;
                jwait <= 1'b0;
                if (jstep == 2'd0) begin t0 <= fa_y; jstep <= 2'd1; end
                else if (jstep == 2'd1) begin t1 <= fa_y; jstep <= 2'd2; end
                else begin
                    out_y_v <= 1'b1; out_y_row <= ROW0 + {jrp, 1'b0} + jrow; out_y_root <= fa_y;
                    out_y_bf16 <= bf_sum[31:16];
                    jstep <= 2'd0;
                    if (jrow) jbusy <= 1'b0; else jrow <= 1'b1;
                end
            end
        end
    end
    // data part of the element stream register (no reset: qualified by e_xs_v)
    always @(posedge clk) if (s2_v) begin
        e_xs_q0 <= s2_par ? bank_q[1] : bank_q[0];
        e_xs_q1 <= s2_par ? bank_q[3] : bank_q[2];
    end
endmodule
