`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VECTOR (STREAM) UNIT of the re-specified DeepSeek-V4.1-Flash decode die
// (docs/ARCH_SPEC_V41.md section 6 item 2).  It implements the op set of
// ot_hdc_v41_stream / tools/hdc_program_v41.Machine.su, and it sums under
// R-ARITH (chunk8).  Its parameters:
//
//   N   light lanes: elements a cycle of a linear op (mul, add, max, BF16)
//   M   SFU lanes: lanes 0 .. M-1 also carry exp, sigmoid / SiLU and the IEEE
//       divider (M1 A'/B), so an op of those classes issues M elements a cycle
//   LV  the reducer's time levels: a reduced segment spans at most 2^LV vectors
//
// Lane 0 also carries the scalar side pipe: rsqrt, sqrt, sqrt(softplus) and the
// Engram gate, one element a cycle.  The die's spec is N = 1,024, M = 256 at
// 1.034 GHz.
//
// ELEMENT SEMANTICS.  Those of Machine.su for every field (A..D sources,
// gather, pair mode, PRE / M1 / M2 / Q / AD / S / E1 / E2 / RND, the element
// writes, KV and transposed-KV).  An op's element results do not depend on how
// they are laid onto lanes, so `su_vec` is not an input: the unit picks the
// layout itself.
//
// REDUCTIONS (R-ARITH).  Every reduction is tools/hdc_golden_v41.csum:
//   * SUM and SEQ: csum of out (or out*out) per segment (outer index).  SEQ is
//     its own sequential sum from +0 whenever a segment has <= 8 elements, and
//     the ISA's SEQ ops all do.
//   * MAX: the maximum on ordered keys.
//   * red_whole and red_tree: csum over the whole op in (o, i) order.  This is
//     R-ARITH's split_sum, which the golden defines as csum.  A layout that
//     flattens (below) runs as one row.  Otherwise the rows must hold whole
//     chunks (ni a multiple of 8, else it faults): each vector is one aligned
//     block of 2^tz elements of a row (2^tz the largest power of two dividing
//     ni, capped at the vector width), and all the op's vectors form one
//     segment.  hc_post (a broadcast A, a per-row B) is such an op.
//   * red_rnd rounds a result to BF16.
// Results go to r_base + o * r_so through NR = N/8 result slots.
//
// LAYOUT.  An op of no x ni elements is laid out as follows.
//   * An op with no per-segment reduction FLATTENS when every stream is
//     contiguous across rows (x_so = ni * x_si; half streams x_so = ni/2 *
//     x_si) and nothing needs the outer index (gather, transposed KV).  It
//     then runs as one row of no*ni elements.
//   * Vector width VW: N, or M for the SFU classes, or 1 for the scalar
//     classes.
//   * Slot size S = min(VW, pow2ceil(max(ni, 8 if reducing else 1))).  A
//     vector holds VW/S rows, one per slot ("packed"), when ni <= S.
//     Otherwise a row spans ceil(ni/S) vectors of S = VW ("spanning").
//   * Lane l of a vector takes element (o + l/S, i + l mod S).  Packed
//     reductions write VW/S results a vector; this needs r_so to be a power
//     of two, and otherwise a vector holds one row.
//
// PIPELINE DEPTHS (emit -> element write; ot_hdc_v41x_vec_lane):
//   fetch dF = 3 (5 gathered), PRE 1, M1 3 (18 divide), M2 3, AD 3,
//   S 0 | exp 49 | sigmoid, silu 70 | rsqrt 37 | sqrt 31 | sqrt(softplus) 161 |
//   gate 103, E1 3, E2 3, OUT 1.  A linear op takes 20 cycles.
// Reducer (ot_hdc_v41x_vec_red): a result leaves 26 + 3*log2(S/8)
// (+ 3*ceil(log2 vectors) when spanning) cycles after the vector retires.
//
// ORDER WITHOUT DRAINS (the checkpoint rule).  Ops overlap in the pipeline.
// Elements must leave each variable-depth stage in emit order: the fetch, M1
// and S (so also the writes), the reducer's time input (spanning ops) and its
// result port (reducing ops).  For each checkpoint X the controller keeps
// cp_X, the remaining depth of the last vector emitted.  An op's first vector
// may go only when its own depth d_X >= cp_X for every X.  So an op waits
// only for a deeper op ahead of it, and only by the depth difference.
// Vectors retire in emit order.
//
// ---------------------------------------------------------------------------
// VECTOR CHAINING PROTOCOL (producer -> consumer, vector credits).  Shared by
// the stream unit and the units that feed it or read from it (ME / QE output
// buffers, attention, indexer, weight engines).
//
// A PRODUCER numbers the ops it starts: seq, 8 bits, from 0, one per op.  It
// publishes four registered signals:
//   cr_seq   seq of the latest op that started writing
//   cr_cnt   vectors of op cr_seq written so far (its own vector unit);
//            monotone while cr_seq holds
//   cr_dseq  seq of the latest op whose vectors are ALL written; ops complete
//            in seq order; 8'hFF after reset
//   cr_rseq  (the stream unit) seq of the latest REDUCING op whose results
//            are all written; reducing ops complete their results in order
// "Written" means that a read issued in the next cycle returns the new value.
//
// A CONSUMER op carries ch_src, ch_seq (the producer op it reads), ch_lead
// and ch_mul (Q8.8: producer vectors per consumer vector).  Its vector v (0,
// 1, ...) needs need(v) = ch_lead + floor(v * ch_mul / 256) producer vectors.
// It may emit vector v when
//   done(ch_seq)  = (cr_dseq - ch_seq) mod 256 < 128, or
//   cr_seq == ch_seq && cr_cnt >= need(v).
// The program generator derives lead and mul from the two ops' address
// orders: vector v must read only what the first need(v) producer vectors
// wrote.
//   ch_src = 0  none
//          = 1  SELF: this unit's op ch_seq -- vector credits while it is the
//                     previous op, else done(ch_seq) on cr_dseq
//          = 2  SELF_RES: this unit's reducing op ch_seq has written its
//                         results (cr_rseq)
//          = 3  EXT: the producer on the x_* ports
// A consumer re-checks per vector, so it runs one vector behind the producer
// at the producer's rate.  The cost is one cycle from a producer's write to
// the consumer's emit of the vector that reads it.
// If the producer starts a newer op before the consumer finishes, cr_seq moves
// on; the consumer then waits for done(ch_seq).  It only waits, it never
// reads early.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vec #(
    parameter integer N  = 64,          // light lanes (elements a cycle), a power of two >= 8
    parameter integer M  = 16,          // SFU lanes, a power of two, 8 <= M <= N
    parameter integer LV = 6,           // reducer time levels
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer KVT_SH = 9
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    // ---- instruction (DYN already added to the bases and counts)
    input  wire [NW-1:0]     i_nout, i_nin,
    input  wire [1:0]        i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi, i_aibase,
    input  wire [1:0]        i_aind,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_bhalf,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire              i_cpair,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire              i_arnd, i_arelu, i_amin, i_cclip,
    input  wire [2:0]        i_m1,
    input  wire [1:0]        i_m2,
    input  wire [2:0]        i_qm, i_ad, i_sfu, i_e1,
    input  wire [1:0]        i_e2,
    input  wire              i_rnd,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase, i_oso, i_osi, i_orow,
    input  wire [1:0]        i_red,
    input  wire              i_redsq, i_redwhole, i_redtree, i_redrnd,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2, i_imm3,
    // ---- chaining (see the protocol above)
    input  wire [1:0]        i_ch_src,
    input  wire [7:0]        i_ch_seq,
    input  wire [15:0]       i_ch_lead,
    input  wire [15:0]       i_ch_mul,
    input  wire [7:0]        x_seq, x_dseq,
    input  wire [15:0]       x_cnt,
    output reg  [7:0]        cr_seq, cr_dseq, cr_rseq,
    output wire [15:0]       cr_cnt,
    // ---- per lane: gather-index read, operand reads {D, C, B, A} (address + source; the memory returns the word)
    output wire [N-1:0]      vi_re,
    output wire [N*AW-1:0]   vi_addr,
    input  wire [N*32-1:0]   vi_q,
    output wire [4*N*AW-1:0] rd_addr,
    output wire [4*N-1:0]    rd_re,
    output wire [8*N-1:0]    rd_src,        // per stream: 0 vector memory, 1 / 2 constant ROM lo / hi word, 3 BF16 weight ROM
    input  wire [4*N*32-1:0] rd_q,          // the selected word (the weight ROM's BF16 element in bits 31:16)
    // ---- per lane: element writes
    output wire [N-1:0]      vm_we,
    output wire [N*AW-1:0]   vm_waddr,
    output wire [N*32-1:0]   vm_wdata,
    output wire [N-1:0]      kv_we,
    output wire [N*AW-1:0]   kv_waddr,
    output wire [N*32-1:0]   kv_wdata,
    // ---- reduction results (to the vector memory)
    output wire [N/8-1:0]    res_we,
    output wire [N/8*AW-1:0] res_addr,
    output wire [N/8*32-1:0] res_data,
    // ---- status
    output reg               fault,          // an arithmetic refusal or a configuration the unit cannot run
    output reg               order_fault,    // an internal ordering violation (never, by construction)
    output reg  [15:0]       emitted,        // vectors emitted since reset (bench)
    output reg               retire_o,       // a vector retired this cycle (bench)
    output wire              dbg_emit,       // this cycle: a vector of op dbg_eseq is emitted
    output wire [7:0]        dbg_eseq,
    output wire              dbg_ret,        // this cycle: a vector of op dbg_rseq retires (writes)
    output wire [7:0]        dbg_rseq,
    output wire              dbg_res,        // this cycle: results of op dbg_sseq are written
    output wire [7:0]        dbg_sseq
);
    localparam integer LN = $clog2(N);
    localparam integer LM = $clog2(M);
    localparam integer NR = N / 8;
    localparam integer CW = 24;
    localparam [1:0] IND_NONE = 0, IND_I = 1, IND_O = 2;
    localparam [1:0] DST_NONE = 0, DST_KVT = 3;
    localparam [2:0] M1_DIVB = 4, M1_DIVIMM = 5;
    localparam [2:0] QM_ALT_NP = 3, QM_ALT_PN = 4;
    localparam [2:0] SFU_NONE = 0, SFU_EXP = 1, SFU_RSQRT = 2, SFU_SQRT = 3, SFU_SIGM = 4, SFU_SILU = 5,
                     SFU_SPSQRT = 6, SFU_EGATE = 7;
    localparam [1:0] RED_NONE = 0, RED_MAX = 2;
    localparam [1:0] CH_NONE = 0, CH_SELF = 1, CH_RES = 2, CH_EXT = 3;

    function automatic [4:0] log2c(input [31:0] x);     // ceil(log2 x), x >= 1
        integer b;
        begin
            log2c = 0;
            for (b = 0; b < 32; b = b + 1) if ((32'd1 << b) < x) log2c = b + 1;
        end
    endfunction
    function automatic [4:0] log2f(input [31:0] x);     // floor(log2 x), x >= 1
        integer b;
        begin
            log2f = 0;
            for (b = 0; b < 32; b = b + 1) if (x[b]) log2f = b;
        end
    endfunction
    function automatic [4:0] tzero(input [CW-1:0] x);   // trailing zeros (x > 0)
        integer b;
        begin
            tzero = 0;
            for (b = CW - 1; b >= 0; b = b - 1) if (x[b]) tzero = b;
        end
    endfunction
    function automatic pow2(input [AW-1:0] x);
        pow2 = (x != 0) && ((x & (x - 1)) == 0);
    endfunction
    function automatic [7:0] sfu_d(input [2:0] s);
        case (s)
            SFU_EXP: sfu_d = 49;
            SFU_SIGM, SFU_SILU: sfu_d = 70;
            SFU_RSQRT: sfu_d = 37;
            SFU_SQRT: sfu_d = 31;
            SFU_SPSQRT: sfu_d = 161;
            SFU_EGATE: sfu_d = 103;
            default: sfu_d = 0;
        endcase
    endfunction

    // =========================================================================================
    // Set-up: accepted op -> S1 (flatten test) -> S2 (layout, depths, offset terms) -> lanes'
    // offset bank -> pending, ready to start
    // =========================================================================================
    reg  [1:0]  pst;                     // 0 empty, 1 S1, 2 S2 done (lanes load), 3 ready
    assign ready = (pst == 2'd0);
    wire accept = go && ready;
    // raw fields
    reg [NW-1:0] q_nout, q_nin;
    reg [1:0]    q_asrc, q_bsrc, q_csrc, q_dsrc, q_aind, q_dst, q_red, q_m2, q_e2;
    reg [AW-1:0] q_abase, q_aso, q_asi, q_aibase, q_bbase, q_bso, q_bsi, q_cbase, q_cso, q_csi,
                 q_dbase, q_dso, q_dsi, q_obase, q_oso, q_osi, q_orow, q_rbase, q_rso;
    reg          q_bhalf, q_cpair, q_arnd, q_arelu, q_amin, q_cclip, q_rnd, q_redsq, q_redwhole, q_redtree, q_redrnd;
    reg [2:0]    q_m1, q_qm, q_ad, q_sfu, q_e1;
    reg [31:0]   q_imm1, q_imm2, q_imm3;
    reg [1:0]    q_chsrc;
    reg [7:0]    q_chseq, q_seq, seq_ctr;
    reg [15:0]   q_chlead, q_chmul;
    reg          q_bank, nbank;
    always @(posedge clk) if (accept) begin
        q_nout <= i_nout; q_nin <= i_nin;
        q_asrc <= i_asrc; q_bsrc <= i_bsrc; q_csrc <= i_csrc; q_dsrc <= i_dsrc; q_aind <= i_aind; q_dst <= i_dst;
        q_red <= i_red; q_m2 <= i_m2; q_e2 <= i_e2;
        q_abase <= i_abase; q_aso <= i_aso; q_asi <= i_asi; q_aibase <= i_aibase;
        q_bbase <= i_bbase; q_bso <= i_bso; q_bsi <= i_bsi; q_cbase <= i_cbase; q_cso <= i_cso; q_csi <= i_csi;
        q_dbase <= i_dbase; q_dso <= i_dso; q_dsi <= i_dsi; q_obase <= i_obase; q_oso <= i_oso; q_osi <= i_osi;
        q_orow <= i_orow; q_rbase <= i_rbase; q_rso <= i_rso;
        q_bhalf <= i_bhalf; q_cpair <= i_cpair; q_arnd <= i_arnd; q_arelu <= i_arelu; q_amin <= i_amin;
        q_cclip <= i_cclip; q_rnd <= i_rnd; q_redsq <= i_redsq; q_redwhole <= i_redwhole; q_redtree <= i_redtree;
        q_redrnd <= i_redrnd;
        q_m1 <= i_m1; q_qm <= i_qm; q_ad <= i_ad; q_sfu <= i_sfu; q_e1 <= i_e1;
        q_imm1 <= i_imm1; q_imm2 <= i_imm2; q_imm3 <= i_imm3;
        q_chsrc <= i_ch_src; q_chseq <= i_ch_seq; q_chlead <= i_ch_lead; q_chmul <= i_ch_mul;
        q_seq <= seq_ctr; q_bank <= nbank;
    end

    // ---- S1: flatten test ------------------------------------------------------------------------
    wire [AW-1:0] ni_a = q_nin;
    wire [AW-1:0] ni_h = q_nin >> 1;
    wire s1_even = !q_nin[0];
    wire s1_cand = (q_red == RED_NONE) || q_redwhole || q_redtree;
    wire s1_ok = (q_aind == IND_NONE) && (q_dst != DST_KVT) &&
                 (s1_even || !(q_bhalf || q_qm == QM_ALT_NP || q_qm == QM_ALT_PN)) &&
                 (q_aso == ni_a * q_asi) &&
                 (q_bso == (q_bhalf ? ni_h : ni_a) * q_bsi) &&
                 (q_cpair || q_cso == ni_a * q_csi) &&
                 (q_dso == (q_bhalf ? ni_h : ni_a) * q_dsi) &&
                 (q_dst == DST_NONE || q_oso == ni_a * q_osi);
    reg          s_flat, s_wnf, s_flatbad;
    reg [CW-1:0] s_ni, s_no;
    always @(posedge clk) if (pst == 2'd1) begin
        s_flat <= s1_cand && s1_ok;
        // a whole-op reduction whose layout does not flatten: rows of whole 8-element chunks
        s_wnf <= (q_redwhole || q_redtree) && q_red != RED_NONE && !s1_ok && q_nout > 1;
        s_flatbad <= (q_redwhole || q_redtree) && q_red != RED_NONE && !s1_ok && q_nout > 1 && (q_nin[2:0] != 3'd0);
        s_ni <= (s1_cand && s1_ok) ? q_nout * q_nin : q_nin;
        s_no <= (s1_cand && s1_ok) ? 1 : q_nout;
    end

    // ---- S2: layout, depths, offset terms ---------------------------------------------------------
    wire scalar_c = (q_sfu == SFU_RSQRT || q_sfu == SFU_SQRT || q_sfu == SFU_SPSQRT || q_sfu == SFU_EGATE);
    wire sfu_c = (q_sfu == SFU_EXP || q_sfu == SFU_SIGM || q_sfu == SFU_SILU || q_m1 == M1_DIVB || q_m1 == M1_DIVIMM);
    wire [3:0] c_lvw = scalar_c ? 4'd0 : sfu_c ? LM[3:0] : LN[3:0];
    wire red_on = (q_red != RED_NONE);
    // slot size: pow2ceil(max(ni, 8 if reducing)); a whole-op reduction over unflattened rows takes the
    // largest power of two dividing ni, so a vector never straddles a row and every vector is an
    // aligned block of the op's element order
    wire [4:0] c_tz = tzero(s_ni);
    wire [4:0] c_lsz = s_wnf ? c_tz : log2c((s_ni > (red_on ? 8 : 1)) ? s_ni : (red_on ? 8 : 1));
    wire [3:0] c_ls = (c_lsz > c_lvw) ? c_lvw : c_lsz[3:0];
    wire c_packed = !s_wnf && (s_ni <= (1 << c_ls));
    wire c_rpow = pow2(q_rso);
    wire [3:0] c_nsh = (c_packed && (!red_on || c_rpow)) ? (c_lvw - c_ls) : 4'd0;
    wire [CW-1:0] c_nvs = s_wnf ? s_no * (s_ni >> c_ls) : (s_ni + (1 << c_ls) - 1) >> c_ls;
    wire [4:0] c_L = log2c(c_nvs);
    wire c_span = red_on && !c_packed;
    wire c_gather = (q_aind != IND_NONE);
    wire [AW-1:0] c_gstr = (q_aind == IND_I) ? q_asi : q_aso;
    wire c_div = (q_m1 == M1_DIVB || q_m1 == M1_DIVIMM);
    wire [9:0] c_dF = c_gather ? 10'd5 : 10'd3;
    wire [9:0] c_dM = c_dF + 10'd1 + (c_div ? 10'd18 : 10'd3);
    wire [9:0] c_dS = c_dM + 10'd6 + {2'd0, sfu_d(q_sfu)};
    wire [9:0] c_lt = red_on ? {6'd0, c_ls} - 10'd3 : 10'd0;
    wire [9:0] c_dT = c_dS + 10'd7 + 10'd25 + 10'd3 * c_lt;
    wire [9:0] c_dR = c_dT + 10'd1 + (c_span ? 10'd3 * {5'd0, c_L} : 10'd0);
    wire c_bad = (red_on && scalar_c) || s_flatbad || (c_span && c_L > LV) || (c_gather && !pow2(c_gstr));
    // offset terms: stream s (A, B, C, D, O), bit k of the lane index
    wire [AW-1:0] so_s [0:4];
    wire [AW-1:0] si_s [0:4];
    assign so_s[0] = q_aso; assign so_s[1] = q_bso; assign so_s[2] = q_cso; assign so_s[3] = q_dso; assign so_s[4] = q_oso;
    assign si_s[0] = q_asi; assign si_s[1] = q_bsi; assign si_s[2] = q_csi; assign si_s[3] = q_dsi; assign si_s[4] = q_osi;
    reg [5*LN*AW-1:0] c_terms;
    reg [5*AW-1:0]    c_istep, c_ostep;
    integer s, kk;
    always @(*) begin
        for (s = 0; s < 5; s = s + 1) begin
            // stream s's lane offset = d_i * si (or (d_i >> 1) * si for a half stream) + d_o * so
            for (kk = 0; kk < LN; kk = kk + 1) begin
                if (kk < c_ls) begin
                    if (s == 0 && q_aind == IND_I) c_terms[(s*LN + kk)*AW +: AW] = 0;
                    else if ((s == 1 || s == 3) && q_bhalf) c_terms[(s*LN + kk)*AW +: AW] = (kk == 0) ? 0 : si_s[s] << (kk - 1);
                    else c_terms[(s*LN + kk)*AW +: AW] = si_s[s] << kk;
                end else begin
                    if (s == 0 && q_aind == IND_O) c_terms[(s*LN + kk)*AW +: AW] = 0;
                    else c_terms[(s*LN + kk)*AW +: AW] = so_s[s] << (kk - c_ls);
                end
            end
            c_ostep[s*AW +: AW] = (s == 0 && q_aind == IND_O) ? 0 : so_s[s] << c_nsh;
            c_istep[s*AW +: AW] = (s == 0 && q_aind == IND_I) ? 0 :
                                  ((s == 1 || s == 3) && q_bhalf) ? ((c_ls == 0) ? 0 : si_s[s] << (c_ls - 1)) :
                                  si_s[s] << c_ls;
        end
    end
    // registered set-up results (the pending op)
    reg [CW-1:0]      p_no, p_ni;
    reg [3:0]         p_ls, p_lvw, p_nsh, p_lt;
    reg [2:0]         p_L;
    reg               p_packed, p_span, p_bad, p_gather, p_wnf;
    reg [4:0]         p_gsh, p_rsh;
    reg [9:0]         p_dF, p_dM, p_dS, p_dT, p_dR;
    reg [5*LN*AW-1:0] p_terms;
    reg [5*AW-1:0]    p_istep, p_ostep;
    reg [AW-1:0]      p_rstep;
    reg s2_go;
    always @(posedge clk) if (s2_go) begin
        p_no <= s_no; p_ni <= s_ni; p_ls <= c_ls; p_lvw <= c_lvw; p_nsh <= c_nsh; p_lt <= c_lt[3:0];
        p_L <= (c_L > 7) ? 3'd7 : c_L[2:0];
        p_packed <= c_packed; p_span <= c_span; p_bad <= c_bad; p_gather <= c_gather;
        p_gsh <= log2f(c_gstr); p_rsh <= log2f(q_rso);
        p_dF <= c_dF; p_dM <= c_dM; p_dS <= c_dS; p_dT <= c_dT; p_dR <= c_dR;
        p_terms <= c_terms; p_istep <= c_istep; p_ostep <= c_ostep; p_rstep <= s_wnf ? {AW{1'b0}} : q_rso << c_nsh;
        p_wnf <= s_wnf;
    end

    // =========================================================================================
    // Active op and the vector loop
    // =========================================================================================
    reg              a_v;                // an op is emitting
    reg              a_started;
    reg [CW-1:0]     a_no, a_ni, o_v, i_v;
    reg [3:0]        a_ls, a_lvw, a_nsh, a_lt;
    reg [2:0]        a_L;
    reg              a_packed, a_span, a_gather, a_bank, a_wnf;
    reg [4:0]        a_gsh, a_rsh;
    reg [9:0]        a_dF, a_dM, a_dS, a_dT, a_dR;
    reg [5*AW-1:0]   a_istep, a_ostep, row, vb;
    reg [AW-1:0]     a_rstep, rrow, krow;
    reg [1:0]        a_asrc, a_bsrc, a_csrc, a_dsrc, a_aind, a_dst, a_red, a_m2, a_e2, a_chsrc;
    reg              a_bhalf, a_cpair, a_arnd, a_arelu, a_amin, a_cclip, a_rnd, a_redsq, a_redrnd;
    reg [2:0]        a_m1, a_qm, a_ad, a_sfu, a_e1;
    reg [31:0]       a_imm1, a_imm2, a_imm3;
    reg [AW-1:0]     a_obase, a_aibase;
    reg [7:0]        a_seq, a_chseq;
    reg [15:0]       a_chlead, a_chmul, a_mark, a_nv;
    reg [23:0]       a_acc;
    reg [AW-1:0]     a_istep_h1, a_istep_h3;
    // previous op (SELF_VEC chaining)
    reg              pv_v;
    reg [15:0]       pv_mark, pv_nv;
    reg [7:0]        pv_seq;
    // counters
    reg [15:0]       e_tot, r_tot;
    reg [9:0]        cpF, cpM, cpS, cpT, cpR;
    reg [7:0]        rseq_r;

    // position of the vector, its end
    wire [CW-1:0] S_sz = 1 << a_ls;
    wire [CW-1:0] nslot = 1 << a_nsh;
    wire wrap = a_packed || (i_v + S_sz >= a_ni);                    // the vector ends its row(s)
    wire last_v = wrap && (o_v + nslot >= a_no);
    // first-vector checkpoints
    wire ck_ok = (a_dF >= cpF) && (a_dM >= cpM) && (a_dS >= cpS) &&
                 (a_red == RED_NONE || a_dR >= cpR) && (!a_span || a_dT >= cpT);
    // chaining
    wire [15:0] need = a_chlead + a_acc[23:8];
    wire [15:0] pv_cnt = r_tot - pv_mark;
    wire        pv_neg = pv_cnt[15];
    wire [7:0]  ds = cr_dseq - a_chseq;
    wire        pv_ok  = !ds[7] || (pv_v && pv_seq == a_chseq && !pv_neg && pv_cnt >= need);
    wire [7:0]  dx = x_dseq - a_chseq;
    wire [7:0]  dr = cr_rseq - a_chseq;
    wire ch_ok = (a_chsrc == CH_NONE) ? 1'b1 :
                 (a_chsrc == CH_SELF) ? pv_ok :
                 (a_chsrc == CH_RES)  ? !dr[7] :
                 (!dx[7] || (x_seq == a_chseq && x_cnt >= need));
    wire emit = a_v && (a_started || ck_ok) && ch_ok;
    wire promote = (pst == 2'd3) && (!a_v || (emit && last_v));

    // set-up state
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pst <= 2'd0; seq_ctr <= 8'd0; nbank <= 1'b0; s2_go <= 1'b0; end
        else begin
            s2_go <= 1'b0;
            if (accept) begin pst <= 2'd1; seq_ctr <= seq_ctr + 8'd1; nbank <= ~nbank; end
            else if (pst == 2'd1) begin pst <= 2'd2; s2_go <= 1'b1; end
            else if (pst == 2'd2 && !s2_go) pst <= 2'd3;       // lanes load the bank in this cycle
            else if (promote) pst <= 2'd0;
        end
    end
    // (pst 2 takes two cycles: S2 registers p_*, then the lanes load their offsets from p_terms)
    wire lane_ld = (pst == 2'd2) && !s2_go;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_v <= 1'b0; a_started <= 1'b0; pv_v <= 1'b0; e_tot <= 0; r_tot <= 0;
            cpF <= 0; cpM <= 0; cpS <= 0; cpT <= 0; cpR <= 0;
        end else begin
            e_tot <= e_tot + (emit ? 16'd1 : 16'd0);
            r_tot <= r_tot + (retire ? 16'd1 : 16'd0);
            cpF <= emit ? a_dF : (cpF != 0) ? cpF - 10'd1 : 10'd0;
            cpM <= emit ? a_dM : (cpM != 0) ? cpM - 10'd1 : 10'd0;
            cpS <= emit ? a_dS : (cpS != 0) ? cpS - 10'd1 : 10'd0;
            cpT <= (emit && a_span) ? a_dT : (cpT != 0) ? cpT - 10'd1 : 10'd0;
            cpR <= (emit && a_red != RED_NONE) ? a_dR : (cpR != 0) ? cpR - 10'd1 : 10'd0;
            if (emit && !a_started) a_started <= 1'b1;
            if (emit && last_v) begin
                pv_v <= 1'b1; pv_mark <= a_started ? a_mark : e_tot; pv_nv <= a_nv + 16'd1; pv_seq <= a_seq;
            end
            if (promote) begin a_v <= 1'b1; a_started <= 1'b0; end
            else if (emit && last_v) a_v <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (promote) begin
            a_no <= p_no; a_ni <= p_ni; o_v <= 0; i_v <= 0;
            a_ls <= p_ls; a_lvw <= p_lvw; a_nsh <= p_nsh; a_lt <= p_lt; a_L <= p_L;
            a_packed <= p_packed; a_span <= p_span; a_gather <= p_gather; a_bank <= q_bank; a_wnf <= p_wnf;
            a_gsh <= p_gsh; a_rsh <= p_rsh;
            a_dF <= p_dF; a_dM <= p_dM; a_dS <= p_dS; a_dT <= p_dT; a_dR <= p_dR;
            a_istep <= p_istep; a_ostep <= p_ostep; a_rstep <= p_rstep;
            row <= {q_obase, q_dbase, q_cbase, q_bbase, q_abase};
            vb  <= {q_obase, q_dbase, q_cbase, q_bbase, q_abase};
            rrow <= q_rbase; krow <= q_orow;
            a_asrc <= q_asrc; a_bsrc <= q_bsrc; a_csrc <= q_csrc; a_dsrc <= q_dsrc; a_aind <= q_aind;
            a_dst <= q_dst; a_red <= q_red; a_m2 <= q_m2; a_e2 <= q_e2; a_chsrc <= q_chsrc;
            a_bhalf <= q_bhalf; a_cpair <= q_cpair; a_arnd <= q_arnd; a_arelu <= q_arelu; a_amin <= q_amin;
            a_cclip <= q_cclip; a_rnd <= q_rnd; a_redsq <= q_redsq; a_redrnd <= q_redrnd;
            a_m1 <= q_m1; a_qm <= q_qm; a_ad <= q_ad; a_sfu <= q_sfu; a_e1 <= q_e1;
            a_imm1 <= q_imm1; a_imm2 <= q_imm2; a_imm3 <= q_imm3;
            a_obase <= q_obase; a_aibase <= q_aibase;
            a_seq <= q_seq; a_chseq <= q_chseq; a_chlead <= q_chlead; a_chmul <= q_chmul;
            a_nv <= 0; a_acc <= 0;
        end else if (emit) begin
            if (!a_started) a_mark <= e_tot;
            a_nv <= a_nv + 16'd1;
            a_acc <= a_acc + {8'd0, a_chmul};
            if (wrap) begin
                o_v <= o_v + nslot; i_v <= 0;
                row <= row + a_ostep;
                vb <= row + a_ostep;
                rrow <= rrow + a_rstep;
                krow <= krow + nslot[AW-1:0];
            end else begin
                i_v <= i_v + S_sz;
                // a half stream (B, D in pair mode) at slot size 1 moves on after an odd index
                vb[0 +: AW] <= vb[0 +: AW] + a_istep[0 +: AW];
                vb[AW +: AW] <= vb[AW +: AW] + ((a_bhalf && a_ls == 0) ? (i_v[0] ? a_istep_h1 : {AW{1'b0}})
                                                                        : a_istep[AW +: AW]);
                vb[2*AW +: AW] <= vb[2*AW +: AW] + a_istep[2*AW +: AW];
                vb[3*AW +: AW] <= vb[3*AW +: AW] + ((a_bhalf && a_ls == 0) ? (i_v[0] ? a_istep_h3 : {AW{1'b0}})
                                                                          : a_istep[3*AW +: AW]);
                vb[4*AW +: AW] <= vb[4*AW +: AW] + a_istep[4*AW +: AW];
            end
        end
    end
    // a half stream's inner stride at slot size 1 (its term is 0; it moves by si every other index)
    always @(posedge clk) if (promote) begin a_istep_h1 <= q_bsi; a_istep_h3 <= q_dsi; end

    // published chaining state
    reg [7:0]  lst_seq;
    reg [15:0] lst_mark;
    wire [15:0] lst_cnt = r_tot - lst_mark;
    assign cr_cnt = lst_cnt[15] ? 16'd0 : lst_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin lst_seq <= 8'hFF; lst_mark <= 0; cr_seq <= 8'hFF; end
        else begin
            if (emit && !a_started) begin lst_seq <= a_seq; lst_mark <= e_tot; end
            cr_seq <= (emit && !a_started) ? a_seq : lst_seq;
        end
    end

    // =========================================================================================
    // Control pipe: one control word a vector, through the lanes' stage structure
    // =========================================================================================
    // datapath fields
    localparam integer WD = 8 + 4 + 32 + 3 + 32 + 2 + 3 + 3 + 32 + 3 + 3 + 2 + 1 + 2;       // 130
    // retire meta: seq, lastv, red, sq, redrnd, lt, L, span, seglast, nres, rbase, rsh, lastres
    localparam integer WR = 8 + 1 + 2 + 1 + 1 + 4 + 3 + 1 + 1 + 8 + AW + 5 + 1;
    localparam integer WC = WD + WR;
    wire [CW-1:0] rem_rows = a_no - o_v;
    wire [7:0] nres = !a_packed ? 8'd1 : (rem_rows < nslot) ? rem_rows[7:0] : nslot[7:0];
    wire [WC-1:0] cw0 = {a_dsrc, a_csrc, a_bsrc, a_asrc,
                         a_arnd, a_arelu, a_amin, a_cclip, a_imm3,
                         a_m1, a_imm1, a_m2, a_qm, a_ad, a_imm2, a_sfu, a_e1, a_e2, a_rnd, a_dst,
                         a_seq, last_v, a_red, a_redsq, a_redrnd, a_lt, a_L, a_span, a_wnf ? last_v : wrap, nres, rrow, a_rsh,
                         last_v && (a_red != RED_NONE)};
    // F-line: depth 3 or 5
    wire [WC-1:0] cwx;
    wire          vx, col_f, bz_f, bz_m, bz_s;
    ot_hdc_v41x_ins #(.W(WC), .K(2), .DEPTHS({16'd5, 16'd3}), .DMAX(5)) u_cf (.clk(clk), .rst_n(rst_n),
        .v(emit), .sel({a_gather, !a_gather}), .d(cw0), .vo(vx), .q(cwx), .coll(col_f), .busy(bz_f));
    `define CW_SRCS(w)  w[WC-1 -: 8]
    `define CW_ARND(w)  w[WC-9]
    `define CW_ARELU(w) w[WC-10]
    `define CW_AMIN(w)  w[WC-11]
    `define CW_CCLIP(w) w[WC-12]
    `define CW_IMM3(w)  w[WC-13 -: 32]
    `define CW_M1(w)    w[WC-45 -: 3]
    `define CW_IMM1(w)  w[WC-48 -: 32]
    `define CW_M2(w)    w[WC-80 -: 2]
    `define CW_QM(w)    w[WC-82 -: 3]
    `define CW_AD(w)    w[WC-85 -: 3]
    `define CW_IMM2(w)  w[WC-88 -: 32]
    `define CW_SFU(w)   w[WC-120 -: 3]
    `define CW_E1(w)    w[WC-123 -: 3]
    `define CW_E2(w)    w[WC-126 -: 2]
    `define CW_RND(w)   w[WC-128]
    `define CW_DST(w)   w[WC-129 -: 2]
    // PRE -> M1 inputs
    reg  [WC-1:0] cwp;
    reg           vp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vp <= 1'b0; else vp <= vx;
    end
    always @(posedge clk) cwp <= cwx;
    wire p_div = (`CW_M1(cwp) == M1_DIVB) || (`CW_M1(cwp) == M1_DIVIMM);
    // M1-line: 3 or 18
    wire [WC-1:0] cwm;
    wire          vm, col_m;
    ot_hdc_v41x_ins #(.W(WC), .K(2), .DEPTHS({16'd18, 16'd3}), .DMAX(18)) u_cm (.clk(clk), .rst_n(rst_n),
        .v(vp), .sel({p_div, !p_div}), .d(cwp), .vo(vm), .q(cwm), .coll(col_m), .busy(bz_m));
    // AD in (+3), S in (+6)
    wire [WC-1:0] cwa, cwi;
    wire [6:0]    vml;
    ot_hdc_delay #(.W(WC), .D(3)) u_ca (.clk(clk), .rst_n(rst_n), .d(cwm), .q(cwa));
    ot_hdc_delay #(.W(WC), .D(3)) u_ci (.clk(clk), .rst_n(rst_n), .d(cwa), .q(cwi));
    ot_hdc_vline #(.D(6)) u_vml (.clk(clk), .rst_n(rst_n), .v(vm), .vd(vml));
    wire vi = vml[6];
    wire [2:0] i_s = `CW_SFU(cwi);
    wire [6:0] s_sel = {i_s == SFU_EGATE, i_s == SFU_SPSQRT, i_s == SFU_SQRT, i_s == SFU_RSQRT,
                        i_s == SFU_SIGM || i_s == SFU_SILU, i_s == SFU_EXP, i_s == SFU_NONE};
    wire [WC-1:0] cws;
    wire          vs, col_s;
    ot_hdc_v41x_ins #(.W(WC), .K(7), .DEPTHS({16'd103, 16'd161, 16'd31, 16'd37, 16'd70, 16'd49, 16'd0}),
                      .DMAX(161)) u_cs (.clk(clk), .rst_n(rst_n), .v(vi), .sel(s_sel), .d(cwi), .vo(vs), .q(cws),
                      .coll(col_s), .busy(bz_s));
    // E2 in (+3), OUT in (+6), retire (+7)
    wire [WC-1:0] cwe, cwo, cwr;
    wire [7:0]    vsl;
    ot_hdc_delay #(.W(WC), .D(3)) u_ce (.clk(clk), .rst_n(rst_n), .d(cws), .q(cwe));
    ot_hdc_delay #(.W(WC), .D(3)) u_co (.clk(clk), .rst_n(rst_n), .d(cwe), .q(cwo));
    ot_hdc_delay #(.W(WC), .D(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(cwo), .q(cwr));
    ot_hdc_vline #(.D(7)) u_vsl (.clk(clk), .rst_n(rst_n), .v(vs), .vd(vsl));
    wire retire = vsl[7];
    // retire meta
    wire [WR-1:0] rm = cwr[WR-1:0];
    wire [7:0]  r_seq   = rm[WR-1 -: 8];
    wire        r_lastv = rm[WR-9];
    wire [1:0]  r_red   = rm[WR-10 -: 2];
    wire        r_sq    = rm[WR-12];
    wire        r_rnd   = rm[WR-13];
    wire [3:0]  r_lt    = rm[WR-14 -: 4];
    wire [2:0]  r_L     = rm[WR-18 -: 3];
    wire        r_span  = rm[WR-21];
    wire        r_wrap  = rm[WR-22];
    wire [7:0]  r_nres  = rm[WR-23 -: 8];
    wire [AW-1:0] r_rbase = rm[WR-31 -: AW];
    wire [4:0]  r_rsh   = rm[5:1];
    wire        r_lastres = rm[0];

    // =========================================================================================
    // Lanes
    // =========================================================================================
    wire [N-1:0]    l_fault, l_coll, l_rov;
    wire [N*32-1:0] l_rox;
    wire            side_v;
    wire [31:0]     side_x, side_y;
    wire            side_f;
    wire [N-1:0]    l_sv;
    wire [N*32-1:0] l_sx;
    genvar l;
    generate for (l = 0; l < N; l = l + 1) begin : g_lane
        ot_hdc_v41x_vec_lane #(.AW(AW), .CW(CW), .LN(LN), .LANE(l), .KIND((l == 0) ? 2 : (l < M) ? 1 : 0),
                               .KVT_SH(KVT_SH)) u_lane (
            .clk(clk), .rst_n(rst_n),
            .ld(lane_ld), .ld_bank(q_bank), .ld_c(p_terms),
            .emit(emit), .bank(a_bank), .o_v(o_v), .i_v(i_v), .no(a_no), .ni(a_ni), .ls(a_ls), .lvw(a_ls + a_nsh),
            .vb(vb), .krow(krow), .obase(a_obase), .aibase(a_aibase), .aind(a_aind), .gsh(a_gsh),
            .cpair(a_cpair), .dst(a_dst), .srcs({a_dsrc, a_csrc, a_bsrc, a_asrc}),
            .vi_re(vi_re[l]), .vi_addr(vi_addr[l*AW +: AW]), .vi_q(vi_q[l*32 +: 32]),
            .rd_addr(rd_addr[4*l*AW +: 4*AW]), .rd_re(rd_re[4*l +: 4]), .rd_src(rd_src[8*l +: 8]),
            .rd_q(rd_q[4*l*32 +: 4*32]),
            .cx_srcs(`CW_SRCS(cwx)), .cx_arnd(`CW_ARND(cwx)), .cx_arelu(`CW_ARELU(cwx)), .cx_amin(`CW_AMIN(cwx)),
            .cx_cclip(`CW_CCLIP(cwx)), .cx_imm3(`CW_IMM3(cwx)),
            .cp_m1(`CW_M1(cwp)), .cp_imm1(`CW_IMM1(cwp)),
            .cm_m1(`CW_M1(cwm)), .cm_m2(`CW_M2(cwm)), .cm_qm(`CW_QM(cwm)), .cm_imm1(`CW_IMM1(cwm)),
            .ca_ad(`CW_AD(cwa)), .ca_imm2(`CW_IMM2(cwa)),
            .ci_sfu(`CW_SFU(cwi)),
            .cs_sfu(`CW_SFU(cws)), .cs_e1(`CW_E1(cws)), .cs_imm2(`CW_IMM2(cws)),
            .ce_e2(`CW_E2(cwe)), .ce_imm1(`CW_IMM1(cwe)),
            .co_rnd(`CW_RND(cwo)), .co_dst(`CW_DST(cwo)),
            .side_v(l_sv[l]), .side_x(l_sx[l*32 +: 32]), .side_y(side_y),
            .vm_we(vm_we[l]), .vm_waddr(vm_waddr[l*AW +: AW]), .vm_wdata(vm_wdata[l*32 +: 32]),
            .kv_we(kv_we[l]), .kv_waddr(kv_waddr[l*AW +: AW]), .kv_wdata(kv_wdata[l*32 +: 32]),
            .ro_v(l_rov[l]), .ro_x(l_rox[l*32 +: 32]), .fault(l_fault[l]), .coll(l_coll[l]));
    end endgenerate
    assign side_v = l_sv[0];
    assign side_x = l_sx[31:0];
    ot_hdc_v41x_vec_side u_side (.clk(clk), .rst_n(rst_n), .v(side_v), .fn(`CW_SFU(cwi)), .x(side_x),
                                 .fn_out(`CW_SFU(cws)), .y(side_y), .fault(side_f));

    // =========================================================================================
    // Reducer
    // =========================================================================================
    wire [7:0] red_seq;
    wire       red_lastres, red_ev, red_busy, red_f;
    ot_hdc_v41x_vec_red #(.N(N), .LV(LV), .AW(AW), .MW(9)) u_red (.clk(clk), .rst_n(rst_n),
        .v_in(retire && r_red != RED_NONE), .x_in(l_rox), .live_in(l_rov), .mx_in(r_red == RED_MAX),
        .sq_in(r_sq), .lt_in(r_lt), .span_in(r_span), .l_in(r_L), .last_in(r_wrap), .nres_in(r_nres),
        .rnd_in(r_rnd), .rbase_in(r_rbase), .rsh_in(r_rsh), .meta_in({r_seq, r_lastres}),
        .o_we(res_we), .o_addr(res_addr), .o_data(res_data), .o_meta({red_seq, red_lastres}), .o_ev(red_ev),
        .busy(red_busy), .fault(red_f));

    assign dbg_emit = emit;
    assign dbg_eseq = a_seq;
    assign dbg_ret = retire;
    assign dbg_rseq = r_seq;
    assign dbg_res = red_ev;
    assign dbg_sseq = red_seq;
    // published completion
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cr_dseq <= 8'hFF; cr_rseq <= 8'hFF; emitted <= 0; retire_o <= 1'b0; end
        else begin
            if (retire && r_lastv) cr_dseq <= r_seq;
            if (red_ev && red_lastres) cr_rseq <= red_seq;
            emitted <= emitted + (emit ? 16'd1 : 16'd0);
            retire_o <= retire;
        end
    end

    // =========================================================================================
    // Status
    // =========================================================================================
    wire pipe_live = bz_f || vp || bz_m || (|vml) || bz_s || (|vsl);
    wire idle_c = (pst == 2'd0) && !a_v && !pipe_live && !red_busy;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; order_fault <= 1'b0; end
        else begin
            idle <= idle_c && !accept;
            fault <= (|l_fault) || side_f || red_f || (promote && p_bad);
            order_fault <= (|l_coll) || col_f || col_m || col_s;
        end
    end
    `undef CW_SRCS
    `undef CW_ARND
    `undef CW_ARELU
    `undef CW_AMIN
    `undef CW_CCLIP
    `undef CW_IMM3
    `undef CW_M1
    `undef CW_IMM1
    `undef CW_M2
    `undef CW_QM
    `undef CW_AD
    `undef CW_IMM2
    `undef CW_SFU
    `undef CW_E1
    `undef CW_E2
    `undef CW_RND
    `undef CW_DST
endmodule
