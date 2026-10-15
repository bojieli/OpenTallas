`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_sm_kv_line: KV row lines -> BF16 operand beats of the SM's BF16 (tc) columns, for ATTENTION ON THE SM ENGINES
// (H-SM-ATT 2026-10-15, owner-adopted option B: ATT.QK / ATT.PV run on the SM matvec datapath, the dedicated ATT tiles
// are retired).  Arithmetic contract: tools/hgi_sim/lib.py att_qk / att_pv (csum8) == tools/hdc_golden_v41.py dots().
//
// KV ROW LAYOUT IN HBM (4 lines of 136 B per row, CHUNK-POSITION-MAJOR, written by the KV writer with this permutation):
//   line i (0..3) holds the two operand beats t = 2i + h (h = 0, 1); beat t lane j (0..63) = head dim 8j + t, so lane j
//   holds golden chunk j (dims 8j .. 8j+7) and the beat index is the position inside the chunk (tc column semantics).
//   SM-KV8 (window rows: E4M3 code x 2^(e - 127), UE8M0 e per 32 dims; tools/hdc_golden_v41.py qdq_fp8):
//       bits [8(64h + j) +: 8] = E4M3 code of dim 8j + 2i + h;  lane j's block is j/4 for every beat.
//       line 0 bits [1024 + 8b +: 8] = e of block b (0..7), line 1 = blocks 8..15; lines 2, 3 spare bits zero.
//   SM-KV4 (compressed rows: E2M1 code x E4M3 scale per 16 dims; qdq_fp4_e4m3):
//       bits [4(64h + j) +: 4] = E2M1 code of dim 8j + 2i + h;  lane j's block is j/2 for every beat.
//       bits [512 + 8b +: 8] = E4M3 scale of block b (0..31), in EVERY line (the converter latches line 0's copy).
// Every dequantised element is exact in BF16 (KV8: 4 significant bits; KV4: <= 6), so the SM's exact BF16 x BF16 -> FP32
// products equal the golden's products of the BF16-stored qdq values.
//
// ORDER.  Rows arrive row-major (row r lines 0..3, rows in list order: the SM streams its own HBM stack's rows through its
// KV descriptor port).  Rows are grouped in WAVES of up to 8 (the 8 slots of the tc column's circulating FP32 ring):
//   cfg_qk = 1 (QK): a wave's beats leave t-major, slot-minor: (t0 s0) (t0 s1) .. (t0 s7) (t1 s0) ..  -- slot s = row s
//            of the wave, step t: the BF16 matvec issue order (score of row s = csum8 over its 512 dims, tree in column).
//   cfg_qk = 0 (PV): row-major, beat-minor: row s beats 0..7 -- slot b = beat b (64 dims each), step = token.
// A wave is emitted only when its 8 rows (4 lines each) are in the WAVE BUFFER (two waves, 2 x 64x512 1R1W macros =
// real mapped SRAM), because a QK beat needs line t/2 of all rows of the wave and every KV8 beat needs both scale lines.
// The writer fills one wave while the reader drains the other: 32 lines in per 64 beats out (input 0.5 line / cycle).
//
// HEAD DIM 128 (cfg_h128, Qwen3 GQA on HBM; KV = per-element FP8 E4M3, the writer stores UE8M0 127 = scale 1):
//   SM-KV8-128 row = ONE line: byte [16t + j] (t 0..7, j 0..15) = E4M3 code of dim 8j + t; bytes 128..131 = UE8M0 of the
//   4 blocks of 32 dims (lane j's block j/4).
//   QK (4 ROWS A BEAT): ring slot s of a wave holds rows 4s..4s+3, lanes 16q + j = row 4s + q, dim 8j + t: each SM sub-row
//      (leaf q) scores its own row and the back end's 4-leaf combine is bypassed.  The wave buffer is written TRANSPOSED
//      BY STEP: line r goes to the 8 banks at once (bank t <- the line's 16 bytes of step t, 128-bit segment r % 4, word
//      r / 4), so a beat reads one bank word.  Waves of 32 rows, beats t-major.
//   PV: a row's line gives 2 beats (half h = bytes 64h .. 64h+63: lane j = dim 8 (j % 16) + 4h + j / 16).
// Faults (sticky, fail closed where the golden value would not be a normal number): KV8 NaN code (S.1111.111), e = 255,
// a non-zero dequantised value outside the BF16 normal range; KV4 negative or NaN scale; a beat requested while idle.
// Mutants (bench negative controls): MUT 1 = KV8 lane j uses block j/2 (wrong scale); MUT 2 = wrong beat half (beat t reads
// the codes of beat t ^ 1); MUT 3 = KV4 E2M1 subnormal code read as normal.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_sm_kv_line #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          cfg_v,          // new op (only while !busy)
    input  wire          cfg_qk,
    input  wire          cfg_kv4,        // legacy: all rows KV4 (same as cfg_n8 = 0)
    input  wire [12:0]   cfg_n8,         // rows 0 .. cfg_n8-1 of the op are SM-KV8, the rest SM-KV4 (one QK op over window + top-k rows)
    input  wire          cfg_h128,       // head dim 128 (SM-KV8-128 rows, one line each); requires cfg_kv4 = 0
    input  wire [12:0]   cfg_rows,       // rows of this op on this SM (>= 1)
    input  wire          s_valid,
    output wire          s_ready,
    input  wire [1087:0] s_data,
    output wire          m_valid,
    input  wire          m_ready,
    output wire [1023:0] m_data,         // 64 BF16 lanes
    output wire [2:0]    m_slot,         // QK: ring slot of the wave; PV: row (token) of the wave
    output wire [2:0]    m_step,         // QK: beat (position in chunk); PV: beat of the row
    output wire          m_wend,         // last beat of its wave
    output wire          m_last,         // last beat of the op
    output wire          busy,
    output reg           fault
);
    // ---------------- op state ----------------
    reg act, qk, kv4, h128; reg [12:0] n8, wri;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin act <= 1'b0; qk <= 1'b0; kv4 <= 1'b0; h128 <= 1'b0; n8 <= 13'd0; end
        else if (cfg_v && !act) begin act <= 1'b1; qk <= cfg_qk; kv4 <= cfg_kv4 && !cfg_h128; h128 <= cfg_h128;
            n8 <= cfg_h128 ? cfg_rows : (cfg_kv4 ? 13'd0 : cfg_n8); end
        else if (act && op_done) act <= 1'b0;
    wire tq = h128 && qk;                // transposed-by-step wave buffer (4 rows a beat)
    // ---------------- write side ----------------
    reg       wb;                        // wave buffer being written
    reg [4:0] wr;                        // row in wave
    reg [1:0] wl;                        // line in row
    reg [5:0] wn;                        // rows of the wave being written
    reg [1:0] full;                      // wave buffer complete, not yet drained
    reg [5:0] fn [0:1];                  // rows of each full wave
    reg [1:0] flast;                     // the wave is the op's last
    reg [255:0] sc [0:15];               // 512-dim row scales [wave*8 + row]: KV8 bytes 0..15, KV4 bytes 0..31
    reg [31:0]  sc1 [0:63];              // 128-dim row scales [wave*32 + row]: 4 UE8M0 bytes
    reg [15:0]  rf;                      // row format of the 512-dim rows [wave*8 + row]: 1 = SM-KV4
    wire        wf4 = (wri >= n8);       // format of the row being written
    reg [12:0] wleft;
    wire [12:0] wleft_m1 = wleft - 13'd1;
    wire [12:0] wcap = tq ? 13'd32 : 13'd8;
    assign s_ready = act && (wleft != 13'd0) && !full[wb];
    wire wacc = s_valid && s_ready;
    wire wrow_end = wacc && (h128 || wl == 2'd3);
    wire wwave_end = wrow_end && ({1'b0, wr} == wn - 6'd1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wb <= 1'b0; wr <= 5'd0; wl <= 2'd0; wn <= 6'd0; wleft <= 13'd0; full <= 2'b00; flast <= 2'b00; wri <= 13'd0;
        end else begin
            if (cfg_v && !act) begin
                wb <= 1'b0; wr <= 5'd0; wl <= 2'd0; wleft <= cfg_rows; wri <= 13'd0;
                wn <= (cfg_rows > ((cfg_h128 && cfg_qk) ? 13'd32 : 13'd8)) ? ((cfg_h128 && cfg_qk) ? 6'd32 : 6'd8) : cfg_rows[5:0];
            end else if (wacc) begin
                wl <= wl + 2'd1;
                if (wrow_end) begin
                    wl <= 2'd0;
                    wr <= wr + 5'd1;
                    wleft <= wleft - 13'd1;
                    wri <= wri + 13'd1;
                end
                if (wwave_end) begin
                    wr <= 5'd0; wb <= ~wb;
                    fn[wb] <= wn;
                    flast[wb] <= (wleft == 13'd1);
                    wn <= (wleft_m1 > wcap) ? wcap[5:0] : wleft_m1[5:0];
                end
            end
            if (wwave_end) full[wb] <= 1'b1;
            if (rwave_end) full[rb] <= 1'b0;
        end
    end
    always @(posedge clk)
        if (wacc) begin
            if (!h128 && !wf4 && wl == 2'd0) sc[{wb, wr[2:0]}][63:0]   <= s_data[1087:1024];
            if (!h128 && !wf4 && wl == 2'd1) sc[{wb, wr[2:0]}][127:64] <= s_data[1087:1024];
            if (!h128 && wf4 && wl == 2'd0)  sc[{wb, wr[2:0]}]         <= s_data[767:512];
            if (!h128 && wl == 2'd0)         rf[{wb, wr[2:0]}]         <= wf4;
            if (h128) sc1[{wb, wr}] <= s_data[1055:1024];
        end
    // ---------------- wave buffer: eight 64x512 1R1W macros ----------------
    //   row-major modes: bank 0 / 1 = line bits 0..511 / 512..1023 at {wave, row, line}
    //   tq: bank t = the 16 step-t bytes of 4 rows at {0, 0, wave, slot}, segment row % 4 (masked write)
    reg  [5:0] raddr;
    reg        rce;
    wire [4095:0] rdat;
    genvar k;
    generate for (k = 0; k < 8; k = k + 1) begin : g_bank
        wire        we = wacc && (tq || k < 2);
        wire [5:0]  wa = tq ? {2'b00, wb, wr[4:2]} : {wb, wr[2:0], wl};
        wire [511:0] wd = tq ? {4{s_data[128*k +: 128]}} : s_data[512*(k % 2) +: 512];
        wire [511:0] wm = tq ? ({384'd0, {128{1'b1}}} << (128 * wr[1:0])) : {512{1'b1}};
        ot_sram_1r1w_64x512_m1_r2c2 u_b (.clk(clk), .r_ce_in(rce), .r_addr_in(raddr), .rd_out(rdat[512*k +: 512]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    end endgenerate
    // ---------------- read side ----------------
    reg       rb;                        // wave buffer being read
    reg [2:0] rs, rt;                    // QK: slot, step; PV: row, beat
    reg [2:0] inflight;                  // reads issued, not yet in the FIFO
    reg [2:0] fcnt;                      // output FIFO occupancy (depth 4)
    wire [5:0] rn = fn[rb];
    wire [3:0] nsl = tq ? 4'((rn + 6'd3) >> 2) : rn[3:0];   // ring slots of the wave (QK) / rows (PV)
    wire [2:0] bmax = qk ? 3'd7 : (h128 ? 3'd1 : 3'd7);
    wire rlast_beat = (rt == bmax) && ({1'b0, rs} == nsl - 4'd1);
    wire can_rd = act && full[rb] && ({1'b0, inflight} + {1'b0, fcnt} < 4'd4);
    wire rwave_end = can_rd && rlast_beat;
    wire op_done_rd = rwave_end && flast[rb];
    reg  op_drain;
    wire op_done = op_drain && (inflight == 3'd0) && (fcnt == 3'd0);
    assign busy = act;
    reg       p1_v, p1_h, p1_last, p1_we, p1_k4;
    reg [2:0] p1_s, p1_t;
    reg [5:0] p1_n;
    reg [255:0] p1_sc;
    reg [127:0] p1_sc1;                  // tq: the 4 rows' scales; h128 PV: row scale in [31:0]
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rb <= 1'b0; rs <= 3'd0; rt <= 3'd0; rce <= 1'b0; p1_v <= 1'b0; op_drain <= 1'b0;
        end else begin
            rce <= can_rd;
            p1_v <= can_rd;
            if (cfg_v && !act) begin rb <= 1'b0; rs <= 3'd0; rt <= 3'd0; op_drain <= 1'b0; end
            else if (can_rd) begin
                if (op_done_rd) op_drain <= 1'b1;
                if (qk) begin                             // t-major: step outer, slot inner
                    if ({1'b0, rs} == nsl - 4'd1) begin rs <= 3'd0; rt <= rt + 3'd1; end
                    else rs <= rs + 3'd1;
                end else begin                            // row-major: row outer, beat inner (PV)
                    if (rt == bmax) begin rt <= 3'd0; rs <= rs + 3'd1; end
                    else rt <= rt + 3'd1;
                end
                if (rwave_end) begin rb <= ~rb; rs <= 3'd0; rt <= 3'd0; end
            end else if (op_done) op_drain <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (can_rd) raddr <= tq ? {2'b00, rb, rs} : (h128 ? {rb, rs, 2'b00} : {rb, rs, rt[2:1]});
        p1_h <= (MUT == 2) ? ~(h128 ? rt[0] : rt[0]) : rt[0];
        p1_s <= rs; p1_t <= rt; p1_n <= rn; p1_last <= op_done_rd; p1_we <= rlast_beat;
        p1_sc <= sc[{rb, rs}]; p1_k4 <= rf[{rb, rs}];
        p1_sc1 <= tq ? {sc1[{rb, rs, 2'd3}], sc1[{rb, rs, 2'd2}], sc1[{rb, rs, 2'd1}], sc1[{rb, rs, 2'd0}]}
                     : {96'd0, sc1[{rb, 2'b00, rs}]};
    end
    reg       p2_v, p2_h, p2_last, p2_we, p2_k4;
    reg [2:0] p2_s, p2_t;
    reg [5:0] p2_n;
    reg [255:0] p2_sc;
    reg [127:0] p2_sc1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p2_v <= 1'b0; else p2_v <= p1_v;
    always @(posedge clk) begin
        p2_h <= p1_h; p2_s <= p1_s; p2_t <= p1_t; p2_n <= p1_n; p2_last <= p1_last; p2_we <= p1_we;
        p2_sc <= p1_sc; p2_sc1 <= p1_sc1; p2_k4 <= p1_k4;
    end
    // ---------------- dequantisation (64 lanes) ----------------
    function automatic [16:0] dq8(input [7:0] c, input [7:0] e);   // {fault, bf16}
        reg [3:0] E4; reg [2:0] M; reg [9:0] ex; reg [6:0] man; integer L;
        begin
            E4 = c[6:3]; M = c[2:0];
            if (c[6:0] == 7'd0) dq8 = 17'd0;
            else begin
                if (E4 != 4'd0) begin ex = {6'd0, E4} + {2'd0, e} - 10'd7; man = {M, 4'd0}; end
                else begin
                    L = M[2] ? 2 : (M[1] ? 1 : 0);
                    ex = {2'd0, e} + L[9:0] - 10'd9;          // value M x 2^-9 x 2^(e-127): lead at bit L
                    man = 7'(({4'd0, M} << (7 - L)) & 7'h7f);
                end
                // normal BF16 needs 1 <= ex <= 254 (ex computed as unsigned 10-bit: negative wraps above 254)
                dq8 = {(c[6:0] == 7'h7f) || (e == 8'hff) || (ex == 10'd0) || (ex > 10'd254), c[7], ex[7:0], man};
            end
        end
    endfunction
    function automatic [16:0] dq4(input [3:0] n, input [7:0] s);   // {fault, bf16}
        reg [1:0] Ea; reg [1:0] sa; reg [3:0] Eb; reg [3:0] sb; reg [5:0] P; reg [9:0] ex; reg [6:0] man; integer L;
        begin
            if (s[7] || s[6:0] == 7'h7f) dq4 = {1'b1, 16'd0};
            else if (n[2:0] == 3'd0 || s[6:0] == 7'd0) dq4 = 17'd0;
            else begin
                Ea = (n[2:1] == 2'd0) ? 2'd1 : n[2:1];
                sa = (MUT == 3) ? {1'b1, n[0]} : {(n[2:1] != 2'd0), n[0]};
                Eb = (s[6:3] == 4'd0) ? 4'd1 : s[6:3];
                sb = {(s[6:3] != 4'd0), s[2:0]};
                P = sa * sb;
                L = P[5] ? 5 : P[4] ? 4 : P[3] ? 3 : P[2] ? 2 : P[1] ? 1 : 0;
                ex = 10'd115 + {8'd0, Ea} + {6'd0, Eb} + L[9:0];
                man = 7'(({1'b0, P} << (7 - L)) & 7'h7f);
                dq4 = {1'b0, n[3], ex[7:0], man};
            end
        end
    endfunction
    wire [511:0] tqd = rdat[512*p2_t +: 512];         // tq: the step's bank word (4 rows x 16 codes)
    wire [1023:0] bf;
    wire [63:0]   lf;
    genvar j;
    generate for (j = 0; j < 64; j = j + 1) begin : g_lane
        localparam integer B8 = (MUT == 1) ? (j / 2) % 16 : j / 4;
        localparam integer Q = j / 16, JJ = j % 16;
        wire [7:0] c8 = p2_h ? rdat[512 + 8*j +: 8] : rdat[8*j +: 8];
        wire [3:0] c4 = p2_h ? rdat[256 + 4*j +: 4] : rdat[4*j +: 4];
        wire [16:0] r8 = dq8(c8, p2_sc[8*B8 +: 8]);
        wire [16:0] r4 = dq4(c4, p2_sc[8*(j/2) +: 8]);
        // head dim 128
        wire        qv = ({p2_s, 2'b00} + Q) < {1'b0, p2_n};          // tq: row 4s + q exists
        wire [16:0] rq = dq8(tqd[128*Q + 8*JJ +: 8], p2_sc1[32*Q + 8*(JJ/4) +: 8]);
        wire [16:0] rp = dq8(c8, p2_sc1[8*(JJ/4) +: 8]);
        assign bf[16*j +: 16] = tq ? (qv ? rq[15:0] : 16'd0) : h128 ? rp[15:0] : p2_k4 ? r4[15:0] : r8[15:0];
        assign lf[j] = tq ? (qv && rq[16]) : h128 ? rp[16] : p2_k4 ? r4[16] : r8[16];
    end endgenerate
    // ---------------- output FIFO (4 entries: the read pipeline is 2 deep, so 4 sustain one beat a cycle) ----------------
    reg [1023:0] fd [0:3];
    reg [7:0]    ff [0:3];                // {last, wend, step, slot}
    reg [1:0]    fh, ft;
    wire pop = m_valid && m_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fcnt <= 3'd0; fh <= 2'd0; ft <= 2'd0; inflight <= 3'd0; fault <= 1'b0; end
        else begin
            fcnt <= fcnt + {2'b0, p2_v} - {2'b0, pop};
            inflight <= inflight + {2'b0, can_rd} - {2'b0, p2_v};
            if (p2_v) ft <= ft + 2'd1;
            if (pop) fh <= fh + 2'd1;
            if (p2_v && |lf) fault <= 1'b1;
        end
    end
    always @(posedge clk)
        if (p2_v) begin fd[ft] <= bf; ff[ft] <= {p2_last, p2_we, p2_t, p2_s}; end
    assign m_valid = (fcnt != 3'd0);
    assign m_data = fd[fh];
    assign {m_last, m_wend, m_step, m_slot} = ff[fh];
endmodule
`default_nettype wire
