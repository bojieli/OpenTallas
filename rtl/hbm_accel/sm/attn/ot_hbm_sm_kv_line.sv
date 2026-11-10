`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_sm_kv_line: KV row lines -> BF16 operand beats of the SM's BF16 (tc) columns, for ATTENTION ON THE SM ENGINES
// (H-SM-ATT 2026-10-15, owner-adopted option B: ATT.QK / ATT.PV run on the SM matvec datapath, the dedicated ATT tiles
// are retired).  Arithmetic contract: tools/hgi_sim/lib.py att_qk / att_pv (csum8) == tools/hdc_golden_v41.py dots().
//
// KV ROWS IN HBM = THE CANONICAL PACKED ROWS (no writer-side permutation, no byte expansion): rows of an op lie back to
// back in the SM's own stack (window ring segment / top-k list-order store) and arrive as the contiguous 136-B line
// stream of the 64-b KV descriptor port.
//   KV8 (window rows, tools/hdc_golden_v41.py qdq_fp8): 528 B = bytes 0..511 E4M3 codes in dim order, 512..527 UE8M0 e
//       of the 16 blocks of 32 dims (value = code x 2^(e - 127)).
//   KV4 (top-k compressed rows, qdq_fp4_e4m3): 288 B = bytes 0..255 E2M1 codes in dim order (dim 2i low nibble, 2i+1 high,
//       sign bit 3), 256..287 E4M3 scales of the 32 blocks of 16 dims.
//   Rows 0 .. cfg_n8-1 of the op are KV8, the rest KV4 (one QK op covers a SM's window and top-k rows).
// A qword REALIGNER (96 x 64 b) cuts the line stream into rows; each row is written BEAT-MAJOR into the 8 wave banks in
// one edge (bank t word = the 64 codes of dims 8j + t, j = 0..63: lane j holds golden chunk j, beat t its position),
// so every operand beat is one bank word.  Every dequantised element is exact in BF16 (KV8: 4 significant bits;
// KV4: <= 6): the SM's exact BF16 x BF16 -> FP32 products equal the golden's products of the BF16-stored qdq values.
//
// ORDER.  Rows are grouped in WAVES of up to 8 (the 8 slots of the tc column's circulating FP32 ring):
//   cfg_qk = 1 (QK): a wave's beats leave t-major, slot-minor: (t0 s0) (t0 s1) .. (t0 s7) (t1 s0) ..  -- slot s = row s
//            of the wave, step t: the BF16 matvec issue order (score of row s = csum8 over its 512 dims, tree in column).
//   cfg_qk = 0 (PV): row-major, beat-minor: row s beats 0..7 -- slot b = beat b (64 dims: lane j = dim 8j + b), step = token.
// Two waves (8 banks x 16 words of the 8 x 64x512 1R1W macros = real mapped SRAM): the realigner fills one wave while
// the reader drains the other.  Line demand: KV8 3.9 lines / 8 beats, KV4 2.1 lines / 8 beats.
//
// HEAD DIM 128 (cfg_h128, Qwen3 GQA on HBM; KV = per-element FP8 E4M3, no scale: tools/hgi_sim/qwen_compiler.py kv_append
//   fp8_encode, value = the E4M3 code's value):
//   STANDARD 128-B ROW (H-SM-ATT r2 2026-10-15; replaces the 136-B one-row-a-line SM-KV8-128 layout): bytes 0..127 = E4M3
//   codes in dim order, rows back to back in the SM's own stack (a 136-B line carries 1 1/16 rows; 256 rows = 241 lines,
//   not 256).  The same qword realigner cuts the stream into 16-qword rows; the emitted row is permuted once in wires
//   (P[16t + j] = byte 8j + t) and written exactly as the old one-row line was, with the fixed scale UE8M0 127.
//   Row ORDER in the stack is the writer's row-granular address map (no byte permutation): PV streams need rows
//   round-robin over the 4 token streams (stored row 4k + u = token 32u + k of the 128-token block: the DMA append
//   address rotates POS[6:0] left by 2); QK reads the same stored order and the compiler gives each score its position
//   address (inverse rotation) at publication.
//   QK (4 ROWS A BEAT): ring slot s of a wave holds rows 4s..4s+3, lanes 16q + j = row 4s + q, dim 8j + t: each SM sub-row
//      (leaf q) scores its own row and the back end's 4-leaf combine is bypassed.  The wave buffer is written TRANSPOSED
//      BY STEP: line r goes to the 8 banks at once (bank t <- the line's 16 bytes of step t, 128-bit segment r % 4, word
//      r / 4), so a beat reads one bank word.  Waves of 32 rows, beats t-major.
//   PV: a row's line gives 2 beats (half h = bytes 64h .. 64h+63: lane j = dim 8 (j % 16) + 4h + j / 16).
// Faults (sticky, fail closed where the golden value would not be a normal number): KV8 NaN code (S.1111.111), e = 255,
// a non-zero dequantised value outside the BF16 normal range; KV4 negative or NaN scale; a beat requested while idle.
// Mutants (bench negative controls): MUT 1 = KV8 lane j uses block j/2 (wrong scale); MUT 2 = wrong beat (beat t reads
// the codes of beat t ^ 1); MUT 3 = KV4 E2M1 subnormal code read as normal; MUT 4 = head-dim-128 QK beat
// takes its 4 rows in reverse sub-row order.
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
    reg act, qk, kv4; reg [12:0] n8, wri;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin act <= 1'b0; qk <= 1'b0; kv4 <= 1'b0; n8 <= 13'd0; end
        else if (cfg_v && !act) begin act <= 1'b1; qk <= cfg_qk; kv4 <= cfg_kv4 && !cfg_h128;
            n8 <= cfg_h128 ? cfg_rows : (cfg_kv4 ? 13'd0 : cfg_n8); end
        else if (act && op_done) act <= 1'b0;
    // KVPIPE rev3 (DIE-HBM-97 2026-11-10, vD locality read): h128 / wf4 / fill / in_v were single registers whose
    // loads span the whole 734-um core (the bb insert / shift selects over the north strip, the 8 bank controls, the sc
    // writes, the 64 dequantise lanes): rev2 capped STA +92.7 .. +164.7 ps with unplaced RC, against a 100 - 150 ps
    // die-wide placed wire.  rev3 keeps NC = 4 IDENTICAL COPIES, one per bank column c (banks c and c + 4, bb qwords
    // 24c .. 24c + 23, sc bits 64c .. 64c + 63, dequantise lanes 16c .. 16c + 15), each with the same reset, the same
    // configure load and the same next state, so every copy equals the rev2 register in every cycle (sequential
    // equivalence rev2 == rev3: kvpipe/kvline_rev3_eq.ys).  (* keep *) + the kit's SYNTH_CANONICALIZE_TCL hook
    // (physical/common_flow/ot_keep_regs.tcl) stop opt_merge folding the copies; the kit guides copy c into its column
    // (physical/die_plan/hbm_arch_cores/reg_guides/ot_hbm_sm_kv_line.json).  The shared control (wr / wleft / wri / rf /
    // fn / full, the read sequencer, s_ready) uses copy CC = 3 (E face: s_ready, cfg_rows, fault).
    localparam integer NC = 4, CC = 3;
    wire [NC-1:0]   h128_c, wf4_c, emit_c, room_c, tq_c;
    wire            h128 = h128_c[CC];
    wire tq = tq_c[CC];                  // transposed-by-step wave buffer (4 rows a beat)
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
    // KVPIPE (DIE-HBM-97 2026-11-10): the write side is split in two stages (vB placed STA: the realigner path
    // wri >= n8 -> rqw -> emit -> fill_e -> variable insert index was ~45 levels, -690 ps at 833 ps, the same with zero
    // wire RC).  (1) wf4 (= wri >= n8, the format of the row being written) is a register, updated with wri; (2) an
    // accepted line waits one cycle in the input register in_q and is inserted at the REGISTERED fill (before the row
    // shift), so the 96-qword insert is a log shifter on registers and the emit shift is a 4-way mux.  Accept latency
    // +1 cycle (a line accepted at k is in bb at k + 2); s_ready keeps one line of room for the line in flight.
    wire        wf4 = wf4_c[CC];         // format of the row being written (= wri >= n8, registered; copies in g_col)
    reg [12:0] wleft;
    wire [12:0] wleft_m1 = wleft - 13'd1;
    wire [12:0] wcap = tq ? 13'd32 : 13'd8;
    // ---- 512-dim rows: qword realigner ----
    reg  [96*64-1:0] bb;                 // pending bytes of the line stream, oldest at bit 0
    reg  [1087:0]    in_q;
    wire             wgo = act && (wleft != 13'd0) && !full[wb];   // emit = wgo && fill >= rqw (per copy)
    wire             wacc;
    wire [NC*96*64-1:0] ins_dc;          // per column: in_q inserted at that copy's fill
    wire [NC*96-1:0]    ins_mc;
    // the per-column copies: h128 / wf4 / fill (qwords in bb) / in_v (in_q holds an accepted line, inserted this cycle)
    genvar cc;
    generate for (cc = 0; cc < NC; cc = cc + 1) begin : g_col
        (* keep *) reg       h128_r, wf4_r, in_v_r;
        (* keep *) reg [6:0] fill_r;
        wire [6:0] rqw_l = h128_r ? 7'd16 : wf4_r ? 7'd36 : 7'd66;  // qwords of the next row (128 B / KV4 288 B / KV8 528 B)
        wire       emit_l = wgo && (fill_r >= rqw_l);
        // next fill with / without the emit of this cycle, from registers only (emit just selects): vD STA
        wire [7:0] fill_0 = {1'b0, fill_r} + (in_v_r ? 8'd17 : 8'd0);
        wire [7:0] fill_1 = fill_0 - {1'b0, rqw_l};
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin h128_r <= 1'b0; wf4_r <= 1'b0; in_v_r <= 1'b0; fill_r <= 7'd0; end
            else if (cfg_v && !act) begin
                h128_r <= cfg_h128; in_v_r <= 1'b0; fill_r <= 7'd0;
                wf4_r <= cfg_h128 ? (cfg_rows == 13'd0) : (cfg_kv4 || (cfg_n8 == 13'd0));
            end else begin
                fill_r <= emit_l ? fill_1[6:0] : fill_0[6:0];
                in_v_r <= wacc;
                if (emit_l) wf4_r <= (wri + 13'd1 >= n8);
            end
        assign h128_c[cc] = h128_r; assign wf4_c[cc] = wf4_r; assign emit_c[cc] = emit_l;
        assign tq_c[cc] = h128_r && qk;
        assign room_c[cc] = emit_l ? (fill_1 <= 8'd79) : (fill_0 <= 8'd79);  // fill_n + 17 <= 96: the line accepted
                                                                              // now is inserted at fill_n next cycle
        // the insert log shifter of this column (only its 24 qwords are used; synthesis drops the rest)
        assign ins_dc[96*64*cc +: 96*64] = {{(96-17)*64{1'b0}}, in_q} << {fill_r, 6'd0};
        assign ins_mc[96*cc +: 96] = in_v_r ? ({79'd0, 17'h1ffff} << fill_r) : 96'd0;
    end endgenerate
    wire             emit = emit_c[CC];
    assign s_ready = act && (wleft != 13'd0) && room_c[CC];
    assign wacc = s_valid && s_ready;
    wire wrow_end = emit;
    wire wwave_end = wrow_end && ({1'b0, wr} == wn - 6'd1);
    wire [66*64-1:0] row = bb[66*64-1:0];
    // insert in_q at qword fill (fill + 17 <= 96 by the room rule), then shift out the emitted row; qword q uses the
    // copy of its column q / 24
    reg  [96*64-1:0] bb_i, bb_n, ins_d;
    reg  [95:0]      ins_m;
    integer iq, ic;
    always @(*) begin
        for (iq = 0; iq < 96; iq = iq + 1) begin
            ic = iq / 24;
            ins_d[64*iq +: 64] = ins_dc[96*64*ic + 64*iq +: 64];
            ins_m[iq] = ins_mc[96*ic + iq];
            bb_i[64*iq +: 64] = ins_m[iq] ? ins_d[64*iq +: 64] : bb[64*iq +: 64];
        end
        for (iq = 0; iq < 96; iq = iq + 1) begin
            ic = iq / 24;
            bb_n[64*iq +: 64] = !emit_c[ic] ? bb_i[64*iq +: 64] :
                                h128_c[ic] ? ((iq + 16 < 96) ? bb_i[64*(iq + 16) +: 64] : 64'd0) :
                                wf4_c[ic]  ? ((iq + 36 < 96) ? bb_i[64*(iq + 36) +: 64] : 64'd0) :
                                             ((iq + 66 < 96) ? bb_i[64*(iq + 66) +: 64] : 64'd0);
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wb <= 1'b0; wr <= 5'd0; wl <= 2'd0; wn <= 6'd0; wleft <= 13'd0; full <= 2'b00; flast <= 2'b00; wri <= 13'd0;
        end else begin
            if (cfg_v && !act) begin
                wb <= 1'b0; wr <= 5'd0; wl <= 2'd0; wleft <= cfg_rows; wri <= 13'd0;
                wn <= (cfg_rows > ((cfg_h128 && cfg_qk) ? 13'd32 : 13'd8)) ? ((cfg_h128 && cfg_qk) ? 6'd32 : 6'd8) : cfg_rows[5:0];
            end else begin
                if (wrow_end) begin
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
    // row scales: sc bits 64c .. 64c + 63 and sc1 byte c written under copy c (rf: the control copy)
    wire [255:0] sc_wd8 = row[8*256 +: 256], sc_wd4 = {128'd0, row[8*512 +: 128]};
    integer is;
    always @(posedge clk) begin
        bb <= bb_n;
        in_q <= s_data;                  // no enable: in_q is read only when in_v (= accepted last cycle)
        for (is = 0; is < NC; is = is + 1) begin
            if (emit_c[is] && !h128_c[is])
                sc[{wb, wr[2:0]}][64*is +: 64] <= wf4_c[is] ? sc_wd8[64*is +: 64] : sc_wd4[64*is +: 64];
            if (emit_c[is] && h128_c[is]) sc1[{wb, wr}][8*is +: 8] <= 8'd127;
        end
        if (emit && !h128) rf[{wb, wr[2:0]}] <= wf4;
    end
    // ---------------- wave buffer: eight 64x512 1R1W macros ----------------
    //   512-dim rows: bank t word {0, 0, wave, row} = beat t of the row (written from the realigner in one edge)
    //   tq: bank t = the 16 step-t bytes of 4 rows at {0, 0, wave, slot}, segment row % 4 (masked write)
    //   h128 PV: bank 0 / 1 = line bits 0..511 / 512..1023 at {wave, row, 0}
    reg  [5:0] raddr;
    reg        rce;
    wire [4095:0] rdat;
    // head dim 128: the standard row permuted to the step-major byte order (P[16t + j] = code of dim 8j + t)
    wire [1023:0] p128;
    genvar k, jw, pt, pj;
    generate for (pt = 0; pt < 8; pt = pt + 1) begin : g_pt
        for (pj = 0; pj < 16; pj = pj + 1) begin : g_pj
            assign p128[8*(16*pt + pj) +: 8] = row[8*(8*pj + pt) +: 8];
        end
    end endgenerate
    generate for (k = 0; k < 8; k = k + 1) begin : g_bank
        wire [511:0] bw8, bw4;           // beat k of the 512-dim row being emitted, KV8 / KV4
        for (jw = 0; jw < 64; jw = jw + 1) begin : g_w
            assign bw8[8*jw +: 8] = row[8*(8*jw + k) +: 8];
            assign bw4[4*jw +: 4] = row[8*(4*jw + k/2) + 4*(k%2) +: 4];
        end
        assign bw4[511:256] = 256'd0;
        // rev3: bank k uses the copy of its column k % 4
        wire        h128_k = h128_c[k % NC], tq_k = tq_c[k % NC], wf4_k = wf4_c[k % NC], emit_k = emit_c[k % NC];
        wire        we = emit_k && (!h128_k || tq_k || k < 2);
        wire [5:0]  wa = !h128_k ? {2'b00, wb, wr[2:0]} : tq_k ? {2'b00, wb, wr[4:2]} : {wb, wr[2:0], 2'b00};
        wire [511:0] wd = !h128_k ? (wf4_k ? bw4 : bw8) : tq_k ? {4{p128[128*k +: 128]}} : p128[512*(k % 2) +: 512];
        wire [511:0] wm = tq_k ? ({384'd0, {128{1'b1}}} << (128 * wr[1:0])) : {512{1'b1}};
        ot_sram_1r1w_64x512_m1_r2c2 u_b (.clk(clk), .r_ce_in(rce), .r_addr_in(raddr), .rd_out(rdat[512*k +: 512]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    end endgenerate
    // ---------------- read side (KVPIPE: p1 address, p2 bank word selected, p3 registered word + dequantise -> FIFO) --
    reg       rb;                        // wave buffer being read
    reg [2:0] rs, rt;                    // QK: slot, step; PV: row, beat
    reg [2:0] inflight;                  // reads issued, not yet in the FIFO
    reg [2:0] fcnt;                      // output FIFO occupancy (depth 5)
    wire [5:0] rn = fn[rb];
    wire [3:0] nsl = tq ? 4'((rn + 6'd3) >> 2) : rn[3:0];   // ring slots of the wave (QK) / rows (PV)
    wire [2:0] bmax = qk ? 3'd7 : (h128 ? 3'd1 : 3'd7);
    wire rlast_beat = (rt == bmax) && ({1'b0, rs} == nsl - 4'd1);
    wire can_rd = act && full[rb] && ({1'b0, inflight} + {1'b0, fcnt} < 4'd5);
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
    integer ir;
    always @(posedge clk) begin
        if (can_rd) raddr <= h128 && !tq ? {rb, rs, 2'b00} : {2'b00, rb, rs};
        p1_h <= (MUT == 2) ? ~rt[0] : rt[0];
        p1_s <= rs; p1_t <= rt; p1_n <= rn; p1_last <= op_done_rd; p1_we <= rlast_beat;
        p1_sc <= sc[{rb, rs}]; p1_k4 <= rf[{rb, rs}];
        // rev3: scale group q (lanes 16q .. 16q + 15) selected under copy q
        for (ir = 0; ir < NC; ir = ir + 1)
            p1_sc1[32*ir +: 32] <= tq_c[ir] ? sc1[{rb, rs, ir[1:0]}] : (ir == 0) ? sc1[{rb, 2'b00, rs}] : 32'd0;
    end
    // KVPIPE: the scale byte of each lane is selected on the p1 -> p2 edge (p2_ls: one byte a lane), so the dequantiser
    // of a lane reads only its own scale register (vB: one p2_sc1 byte drove 130 loads into dq8).
    reg       p2_v, p2_h, p2_last, p2_we, p2_k4;
    reg [2:0] p2_s, p2_t;
    reg [5:0] p2_n;
    reg [511:0] p2_ls;                   // per-lane scale byte (lane j at [8j +: 8])
    wire [511:0] p1_ls;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p2_v <= 1'b0; else p2_v <= p1_v;
    always @(posedge clk) begin
        p2_h <= p1_h; p2_s <= p1_s; p2_t <= p1_t; p2_n <= p1_n; p2_last <= p1_last; p2_we <= p1_we;
        p2_ls <= p1_ls; p2_k4 <= p1_k4;
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
    wire [2:0]   bsel = (MUT == 2 && !h128) ? (p2_t ^ 3'd1) : p2_t;
    wire [511:0] tqd_2 = rdat[512*bsel +: 512];       // the beat's bank word (512-dim: 64 codes; tq: 4 rows x 16 codes)
    wire [511:0] c8_2 = p2_h ? rdat[1023:512] : rdat[511:0];   // h128 PV: the row half's bank (0 / 1)
    // ---------------- p3: KVPIPE read stage = the selected bank word registered (vC/vD STA: the macro's clock -> rd_out
    // is 364 ps, so bank word + dequantise in one cycle cannot meet 833 ps); dequantise p3 -> FIFO ----------------
    reg          p3_v, p3_last, p3_we, p3_k4;
    reg [2:0]    p3_s, p3_t;
    reg [5:0]    p3_n;
    reg [511:0]  tqd, p3_c8, p3_ls;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p3_v <= 1'b0; else p3_v <= p2_v;
    always @(posedge clk) begin
        tqd <= tqd_2; p3_c8 <= c8_2; p3_ls <= p2_ls; p3_k4 <= p2_k4;
        p3_last <= p2_last; p3_we <= p2_we; p3_t <= p2_t; p3_s <= p2_s; p3_n <= p2_n;
    end
    wire [1023:0] bf;
    wire [63:0]   lf;
    genvar j;
    generate for (j = 0; j < 64; j = j + 1) begin : g_lane
        localparam integer B8 = (MUT == 1) ? (j / 2) % 16 : j / 4;
        localparam integer Q = (MUT == 4) ? 3 - j / 16 : j / 16, JJ = j % 16;   // MUT 4: rows of a 4-row beat reversed
        // rev3: lane j uses the copy of its column j / 16 (lanes sit lane-ordered under their m_data pins)
        wire tq_j = tq_c[j / 16], h128_j = h128_c[j / 16];
        assign p1_ls[8*j +: 8] = tq_j ? p1_sc1[32*Q + 8*(JJ/4) +: 8] : h128_j ? p1_sc1[8*(JJ/4) +: 8]
                               : p1_k4 ? p1_sc[8*(j/2) +: 8] : p1_sc[8*B8 +: 8];
        wire [7:0] ls = p3_ls[8*j +: 8];
        wire [7:0] c8 = p3_c8[8*j +: 8];
        wire [16:0] r8 = dq8(tqd[8*j +: 8], ls);
        wire [16:0] r4 = dq4(tqd[4*j +: 4], ls);
        // head dim 128
        wire        qv = ({p3_s, 2'b00} + Q) < {1'b0, p3_n};          // tq: row 4s + q exists
        wire [16:0] rq = dq8(tqd[128*Q + 8*JJ +: 8], ls);
        wire [16:0] rp = dq8(c8, ls);
        assign bf[16*j +: 16] = tq_j ? (qv ? rq[15:0] : 16'd0) : h128_j ? rp[15:0] : p3_k4 ? r4[15:0] : r8[15:0];
        assign lf[j] = tq_j ? (qv && rq[16]) : h128_j ? rp[16] : p3_k4 ? r4[16] : r8[16];
    end endgenerate
    // ---------------- output FIFO (5 entries: the read pipeline is 3 deep, so 5 sustain one beat a cycle) ----------------
    // entries are plain registers (flat vectors, not an inferred memory: 5 x 1024 bits > SYNTH_MEMORY_MAX_BITS)
    wire [5*1024-1:0] fd;
    wire [5*8-1:0]    ff;                 // {last, wend, step, slot}
    reg [2:0]    fh, ft;
    wire pop = m_valid && m_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fcnt <= 3'd0; fh <= 3'd0; ft <= 3'd0; inflight <= 3'd0; fault <= 1'b0; end
        else begin
            fcnt <= fcnt + {2'b0, p3_v} - {2'b0, pop};
            inflight <= inflight + {2'b0, can_rd} - {2'b0, p3_v};
            if (p3_v) ft <= (ft == 3'd4) ? 3'd0 : ft + 3'd1;
            if (pop) fh <= (fh == 3'd4) ? 3'd0 : fh + 3'd1;
            if (p3_v && |lf) fault <= 1'b1;
        end
    end
    genvar fe;
    generate for (fe = 0; fe < 5; fe = fe + 1) begin : g_fifo
        reg [1023:0] e_d;
        reg [7:0]    e_f;
        always @(posedge clk)
            if (p3_v && ft == fe) begin e_d <= bf; e_f <= {p3_last, p3_we, p3_t, p3_s}; end
        assign fd[1024*fe +: 1024] = e_d;
        assign ff[8*fe +: 8] = e_f;
    end endgenerate
    assign m_valid = (fcnt != 3'd0);
    assign m_data = fd[1024*fh +: 1024];
    assign {m_last, m_wend, m_step, m_slot} = ff[8*fh +: 8];
endmodule
`default_nettype wire
