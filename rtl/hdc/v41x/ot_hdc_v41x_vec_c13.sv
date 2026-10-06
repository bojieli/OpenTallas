// Default-OFF mandatory controller successor; original c12 remains byte-identical.
`timescale 1ns/1ps
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_vec.sv for the c12
// build.  New parameters, whose defaults are the original unit cycle for cycle:
//   OPR    operand registers in every lane at M1, AD and E1 and the gather word register
//          (rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv): M1 / AD / E1 one deeper, a gather fetch one deeper
//   DDIV   the divider depth (21: the DS ROM kit's ot_dsrom_fdiv_f12): M1 divide, sigmoid, softplus, gate
//   SIDEX  the side pipe's port registers (3, or 4 with lane 0's side_y register): rsqrt, sqrt, sqrt(softplus),
//          gate SIDEX deeper
//   CAPR   the lanes' memory-word port register before the capture logic: every fetch one deeper
//   FSQ    the side / softplus square roots are ot_hdc_fsqrt_c12 (same depth)
//   RPAD, RSL, RTAP, ROUT  the reducer's added registers (rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv: padding, slice
//          boundary, tap, OUT input): every result RPAD + RSL + RTAP + ROUT deeper; RSLICE its slice width (physical only)
//   CTL12  the controller at 1.2 GHz (the routed N = 64 vehicle missed by 1.3-1.65 ns): the op set-up runs over
//          more stages (the stride products in two halves, the layout, the depths; +3 cycles a set-up, +5 for a
//          whole-op reduction that does not flatten), and the vector loop decides from REGISTERED conditions,
//          each computed one cycle ahead from the next-cycle state: the row-end / last-vector flags (with the next
//          position precomputed), the first-vector checkpoints, and the chaining credits.  Internal credits
//          (SELF, SELF_RES) are exact next-cycle values; the external producer's x_* are sampled one cycle
//          earlier (a credit seen stays true: written data stays written), so an op waiting on x_* may start one
//          cycle later.  Nothing else moves; the element results are unchanged.
// The checkpoint depths, the control pipe and sfu_d (now 10 bits: sqrt(softplus) exceeds 255 at MLAT 6 / ALAT 6)
// follow them.  Nothing else changes.
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
// OUT OF RANGE IS REFUSED, NOT COMPUTED.  An operand outside an operator's
// domain raises `fault`; the word written for it is unspecified and must not be
// read.  rsqrt of +0 or -0 is one such case: the golden gives NaN (and the
// campaign reference refuses the op), while the RTL raises fault and writes
// 0x601AB3D4 (4.46e19) for +0 and 0x201AB3D4 for -0.  Programs never issue it:
// the RMSNorm operands are mean-square + eps > 0.
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
// PIPELINE DEPTHS (emit -> element write; ot_hdc_v41x_vec_lane), with no wire stages:
//   broadcast 1, fetch 3 (5 gathered), PRE 1, M1 3 (19 divide), M2 3, AD 3,
//   S 0 | exp 49 | sigmoid, silu 71 | rsqrt 37 | sqrt 31 | sqrt(softplus) 162 |
//   gate 104, E1 3, E2 3, OUT 1.  A linear op takes 21 cycles.
// Reducer (ot_hdc_v41x_vec_red): a result leaves 26 + 3*log2(S/8)
// (+ 3*ceil(log2 vectors) when spanning) cycles after the vector retires.
// MLAT = 4 (the LAT-4 multiplier, W11 serial domain at 0.9 GHz): M1, M2, E1 and E2 are 4 deep, exp 56,
//   sigmoid / silu 78, rsqrt 46, sqrt(softplus) 180, gate 111 (divide 19, sqrt 31 and AD 3 unchanged);
//   a linear op takes 25 cycles and the reducer's square is 4 deep (27 + ...).
// ALAT (FP add latency, 3 or 4 with the input-cut adder; W11 serial domain): AD is ALAT deep, every add of the
//   SFU chains, and every reducer step (CHAIN 7 ALAT, TREE / TIME ALAT a level).  Depths at MLAT / ALAT:
//   linear 6 + 4 MLAT + ALAT (21 at 3 / 3, 30 at MLAT 5 / ALAT 4); tools/rtl_hdc_v41x_vec_campaign.set_mlat.
//
// WIRE STAGES (BCAST_STAGES, RET_STAGES; 0 and 0 are the unit as it was, cycle for
// cycle).  At N = 1,024 the lanes span millimetres of the hub, so the controller
// cannot drive them from one register.  BCAST_STAGES register stages form the
// pipelined broadcast tree: the lanes take the vector fields (position, bases,
// bank, layout, sources), the op-set-up offset loads (ld, ld_bank, ld_c) and the
// control word of the vector (op selects, immediates, emit / bank / retire meta)
// from its leaf, and the control pipe the lanes read starts at the leaf (one copy
// per lane tile physically; one copy here, identical contents).  The tree's LAST
// stage is inside each lane (ot_hdc_v41x_vec_lane LEAF = 1): it registers the
// lane's partial addresses (position, transposed-KV row, base + offset of every
// stream), so the lane's first stage is one add / compare level; the offset
// loads go from the tree's stage before it into a three-cycle sum (308 leaf + 604
// load flops a lane).  RET_STAGES
// register stages carry every write back to the vector memory: the element
// writes (vm_*, kv_*) and the reducer's results (res_*).  Every vector crosses
// both, so every depth grows by BCAST_STAGES + RET_STAGES and nothing reorders:
//   * the checkpoints compare depths of ops that all cross the same stages, so
//     cp_X and d_X are unchanged (both would gain the same constant);
//   * the published chaining state (cr_seq / cr_cnt / cr_dseq / cr_rseq) counts
//     writes when they LAND, RET_STAGES after they leave the lanes, so "written"
//     keeps its meaning for every consumer;
//   * this unit's own consumers (ch_src SELF / SELF_RES) read BCAST_STAGES after
//     their emit, so their credits may lead the landing by BCAST_STAGES: they
//     use the retire / result events delayed by max(0, RET_STAGES -
//     BCAST_STAGES), which keeps the 0-stage margin between a write landing and
//     the read of it;
//   * idle waits for both stage lines to drain.
//
// ORDER WITHOUT DRAINS (the checkpoint rule).  Ops overlap in the pipeline.
// Elements must leave each variable-depth stage in emit order: the fetch, M1
// and S (so also the writes), the reducer's tap -- one multiplexer shared by
// packed results and spanning items, so every reducing op arms T and a
// spanning op checks it -- and its result port (reducing ops; a packed op's
// R check covers T).  For each checkpoint X the controller keeps
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
    parameter integer LV = 6,           // reducer time levels, 1..7 (l_in is 3 bits; elaboration fails otherwise)
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer KVT_SH = 9,
    parameter integer BCAST_STAGES = 0, // register stages of the pipelined controller -> lane broadcast tree
    parameter integer RET_STAGES = 0,   // register stages of the lane / reducer -> vector-memory write path
    parameter integer MLAT = 3,         // multiplier latency (ot_hdc_qmul_lat): 3, 4 or 5 (W11 serial domain)
    parameter integer ALAT = 3,         // FP add latency (ot_hdc_qadd_lat): 3, or 4 (input cut); ALAT <= MLAT
    parameter integer OPR = 0,          // c12: lane operand registers (M1, AD, E1) and gather word register
    parameter integer DDIV = 19,        // c12: divider depth (21: ot_dsrom_fdiv_f12)
    parameter integer SIDEX = 0,        // c12: side pipe port registers (0 or 3)
    parameter integer FSQ = 0,          // c12: ot_hdc_fsqrt_c12 in the side pipe
    parameter integer RPAD = 0,         // c12 reducer: padding register
    parameter integer CAPR = 0,         // c12: lane memory-word port register (every fetch CAPR deeper)
    parameter integer RSL = 0,          // c12 reducer: slice-boundary register
    parameter integer RTAP = 0,         // c12 reducer: tap register
    parameter integer ROUT = 0,         // c12 reducer: OUT input register
    parameter integer RSLICE = 64,      // c12 reducer: lanes a slice
    parameter integer CTL13 = 0,        // mandatory registered controller closure, opt-in
    parameter integer CTL12 = 0         // c12 controller: pipelined set-up, registered emit-loop conditions
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
    // LV is bounded by the 3-bit TIME-level field (l_in): an LV above 7 would let an 8-level segment pass
    // the controller's c_L > LV check and be clamped to 7 levels, a silently wrong sum.  Fail closed at
    // elaboration: the trap instantiates a module that does not exist, which Verilator (even under
    // -Wno-fatal), Icarus and Yosys (hierarchy -check, as synth runs it) all reject.
    generate if (LV < 1 || LV > 7) begin : g_lv_out_of_range
        ot_hdc_v41x_vec_LV_must_be_1_to_7 u_trap ();
    end endgenerate

    localparam integer LN = $clog2(N);
    localparam integer LM = $clog2(M);
    localparam integer NR = N / 8;
    localparam integer CW = 24;
    // this unit's own consumers read BCAST_STAGES after their emit: their credits lead the landing by that much
    localparam integer DI = (RET_STAGES > BCAST_STAGES) ? RET_STAGES - BCAST_STAGES : 0;
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
    // S-stage depths (ot_hdc_v41x_vec_lane / _side): exp 7 MLAT + 8 ALAT + 4, sigmoid exp + ALAT + 19, rsqrt
    // 1 + 9 MLAT + 3 ALAT, sqrt 31, sqrt(softplus) exp + 11 MLAT + 10 ALAT + 50, gate 33 + sigmoid
    localparam integer D_EXP = 7 * MLAT + 8 * ALAT + 4, D_SIG = D_EXP + ALAT + DDIV,
                       D_RSQ = 1 + 9 * MLAT + 3 * ALAT + SIDEX, D_SQRT = 31 + SIDEX,
                       D_SP = D_EXP + 11 * MLAT + 10 * ALAT + 31 + DDIV + SIDEX, D_EG = 33 + D_SIG + SIDEX;
    localparam [15:0] H_A = ALAT;
    localparam [15:0] H_R = ALAT;                        // a reducer TREE / TIME level
    localparam [15:0] H_F5 = 5 + OPR + CAPR, H_F3 = 3 + CAPR, H_MD = DDIV + OPR, H_MM = MLAT + OPR;   // gather fetch, M1 divide / multiply
    localparam [15:0] H_M = MLAT, H_EXP = D_EXP, H_SIG = D_SIG, H_RSQ = D_RSQ, H_SQRT = D_SQRT, H_SP = D_SP,
                      H_EG = D_EG;
    function automatic [9:0] sfu_d(input [2:0] s);
        case (s)
            SFU_EXP: sfu_d = D_EXP;
            SFU_SIGM, SFU_SILU: sfu_d = D_SIG;
            SFU_RSQRT: sfu_d = D_RSQ;
            SFU_SQRT: sfu_d = D_SQRT;
            SFU_SPSQRT: sfu_d = D_SP;
            SFU_EGATE: sfu_d = D_EG;
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
    generate if (CTL13 == 0) begin : g_raw_legacy
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

    end else begin : g_raw_cut
        (* keep *) reg [127:0] accept_bank;
        always @(posedge clk or negedge rst_n) if (!rst_n) accept_bank <= 0; else accept_bank <= {128{accept}};
        always @(posedge clk) if (accept) begin q_seq <= seq_ctr; q_bank <= nbank; end
        reg [NW-1:0] raw_q_nout;
        always @(posedge clk) raw_q_nout <= i_nout;
        always @(posedge clk) if (accept_bank[0]) q_nout <= raw_q_nout;
        reg [NW-1:0] raw_q_nin;
        always @(posedge clk) raw_q_nin <= i_nin;
        always @(posedge clk) if (accept_bank[1]) q_nin <= raw_q_nin;
        reg [1:0] raw_q_asrc;
        always @(posedge clk) raw_q_asrc <= i_asrc;
        always @(posedge clk) if (accept_bank[2]) q_asrc <= raw_q_asrc;
        reg [1:0] raw_q_bsrc;
        always @(posedge clk) raw_q_bsrc <= i_bsrc;
        always @(posedge clk) if (accept_bank[3]) q_bsrc <= raw_q_bsrc;
        reg [1:0] raw_q_csrc;
        always @(posedge clk) raw_q_csrc <= i_csrc;
        always @(posedge clk) if (accept_bank[4]) q_csrc <= raw_q_csrc;
        reg [1:0] raw_q_dsrc;
        always @(posedge clk) raw_q_dsrc <= i_dsrc;
        always @(posedge clk) if (accept_bank[5]) q_dsrc <= raw_q_dsrc;
        reg [1:0] raw_q_aind;
        always @(posedge clk) raw_q_aind <= i_aind;
        always @(posedge clk) if (accept_bank[6]) q_aind <= raw_q_aind;
        reg [1:0] raw_q_dst;
        always @(posedge clk) raw_q_dst <= i_dst;
        always @(posedge clk) if (accept_bank[7]) q_dst <= raw_q_dst;
        reg [1:0] raw_q_red;
        always @(posedge clk) raw_q_red <= i_red;
        always @(posedge clk) if (accept_bank[8]) q_red <= raw_q_red;
        reg [1:0] raw_q_m2;
        always @(posedge clk) raw_q_m2 <= i_m2;
        always @(posedge clk) if (accept_bank[9]) q_m2 <= raw_q_m2;
        reg [1:0] raw_q_e2;
        always @(posedge clk) raw_q_e2 <= i_e2;
        always @(posedge clk) if (accept_bank[10]) q_e2 <= raw_q_e2;
        reg [AW-1:0] raw_q_abase;
        always @(posedge clk) raw_q_abase <= i_abase;
        always @(posedge clk) if (accept_bank[11]) q_abase <= raw_q_abase;
        reg [AW-1:0] raw_q_aso;
        always @(posedge clk) raw_q_aso <= i_aso;
        always @(posedge clk) if (accept_bank[12]) q_aso <= raw_q_aso;
        reg [AW-1:0] raw_q_asi;
        always @(posedge clk) raw_q_asi <= i_asi;
        always @(posedge clk) if (accept_bank[13]) q_asi <= raw_q_asi;
        reg [AW-1:0] raw_q_aibase;
        always @(posedge clk) raw_q_aibase <= i_aibase;
        always @(posedge clk) if (accept_bank[14]) q_aibase <= raw_q_aibase;
        reg [AW-1:0] raw_q_bbase;
        always @(posedge clk) raw_q_bbase <= i_bbase;
        always @(posedge clk) if (accept_bank[15]) q_bbase <= raw_q_bbase;
        reg [AW-1:0] raw_q_bso;
        always @(posedge clk) raw_q_bso <= i_bso;
        always @(posedge clk) if (accept_bank[16]) q_bso <= raw_q_bso;
        reg [AW-1:0] raw_q_bsi;
        always @(posedge clk) raw_q_bsi <= i_bsi;
        always @(posedge clk) if (accept_bank[17]) q_bsi <= raw_q_bsi;
        reg [AW-1:0] raw_q_cbase;
        always @(posedge clk) raw_q_cbase <= i_cbase;
        always @(posedge clk) if (accept_bank[18]) q_cbase <= raw_q_cbase;
        reg [AW-1:0] raw_q_cso;
        always @(posedge clk) raw_q_cso <= i_cso;
        always @(posedge clk) if (accept_bank[19]) q_cso <= raw_q_cso;
        reg [AW-1:0] raw_q_csi;
        always @(posedge clk) raw_q_csi <= i_csi;
        always @(posedge clk) if (accept_bank[20]) q_csi <= raw_q_csi;
        reg [AW-1:0] raw_q_dbase;
        always @(posedge clk) raw_q_dbase <= i_dbase;
        always @(posedge clk) if (accept_bank[21]) q_dbase <= raw_q_dbase;
        reg [AW-1:0] raw_q_dso;
        always @(posedge clk) raw_q_dso <= i_dso;
        always @(posedge clk) if (accept_bank[22]) q_dso <= raw_q_dso;
        reg [AW-1:0] raw_q_dsi;
        always @(posedge clk) raw_q_dsi <= i_dsi;
        always @(posedge clk) if (accept_bank[23]) q_dsi <= raw_q_dsi;
        reg [AW-1:0] raw_q_obase;
        always @(posedge clk) raw_q_obase <= i_obase;
        always @(posedge clk) if (accept_bank[24]) q_obase <= raw_q_obase;
        reg [AW-1:0] raw_q_oso;
        always @(posedge clk) raw_q_oso <= i_oso;
        always @(posedge clk) if (accept_bank[25]) q_oso <= raw_q_oso;
        reg [AW-1:0] raw_q_osi;
        always @(posedge clk) raw_q_osi <= i_osi;
        always @(posedge clk) if (accept_bank[26]) q_osi <= raw_q_osi;
        reg [AW-1:0] raw_q_orow;
        always @(posedge clk) raw_q_orow <= i_orow;
        always @(posedge clk) if (accept_bank[27]) q_orow <= raw_q_orow;
        reg [AW-1:0] raw_q_rbase;
        always @(posedge clk) raw_q_rbase <= i_rbase;
        always @(posedge clk) if (accept_bank[28]) q_rbase <= raw_q_rbase;
        reg [AW-1:0] raw_q_rso;
        always @(posedge clk) raw_q_rso <= i_rso;
        always @(posedge clk) if (accept_bank[29]) q_rso <= raw_q_rso;
        reg  raw_q_bhalf;
        always @(posedge clk) raw_q_bhalf <= i_bhalf;
        always @(posedge clk) if (accept_bank[30]) q_bhalf <= raw_q_bhalf;
        reg  raw_q_cpair;
        always @(posedge clk) raw_q_cpair <= i_cpair;
        always @(posedge clk) if (accept_bank[31]) q_cpair <= raw_q_cpair;
        reg  raw_q_arnd;
        always @(posedge clk) raw_q_arnd <= i_arnd;
        always @(posedge clk) if (accept_bank[32]) q_arnd <= raw_q_arnd;
        reg  raw_q_arelu;
        always @(posedge clk) raw_q_arelu <= i_arelu;
        always @(posedge clk) if (accept_bank[33]) q_arelu <= raw_q_arelu;
        reg  raw_q_amin;
        always @(posedge clk) raw_q_amin <= i_amin;
        always @(posedge clk) if (accept_bank[34]) q_amin <= raw_q_amin;
        reg  raw_q_cclip;
        always @(posedge clk) raw_q_cclip <= i_cclip;
        always @(posedge clk) if (accept_bank[35]) q_cclip <= raw_q_cclip;
        reg  raw_q_rnd;
        always @(posedge clk) raw_q_rnd <= i_rnd;
        always @(posedge clk) if (accept_bank[36]) q_rnd <= raw_q_rnd;
        reg  raw_q_redsq;
        always @(posedge clk) raw_q_redsq <= i_redsq;
        always @(posedge clk) if (accept_bank[37]) q_redsq <= raw_q_redsq;
        reg  raw_q_redwhole;
        always @(posedge clk) raw_q_redwhole <= i_redwhole;
        always @(posedge clk) if (accept_bank[38]) q_redwhole <= raw_q_redwhole;
        reg  raw_q_redtree;
        always @(posedge clk) raw_q_redtree <= i_redtree;
        always @(posedge clk) if (accept_bank[39]) q_redtree <= raw_q_redtree;
        reg  raw_q_redrnd;
        always @(posedge clk) raw_q_redrnd <= i_redrnd;
        always @(posedge clk) if (accept_bank[40]) q_redrnd <= raw_q_redrnd;
        reg [2:0] raw_q_m1;
        always @(posedge clk) raw_q_m1 <= i_m1;
        always @(posedge clk) if (accept_bank[41]) q_m1 <= raw_q_m1;
        reg [2:0] raw_q_qm;
        always @(posedge clk) raw_q_qm <= i_qm;
        always @(posedge clk) if (accept_bank[42]) q_qm <= raw_q_qm;
        reg [2:0] raw_q_ad;
        always @(posedge clk) raw_q_ad <= i_ad;
        always @(posedge clk) if (accept_bank[43]) q_ad <= raw_q_ad;
        reg [2:0] raw_q_sfu;
        always @(posedge clk) raw_q_sfu <= i_sfu;
        always @(posedge clk) if (accept_bank[44]) q_sfu <= raw_q_sfu;
        reg [2:0] raw_q_e1;
        always @(posedge clk) raw_q_e1 <= i_e1;
        always @(posedge clk) if (accept_bank[45]) q_e1 <= raw_q_e1;
        reg [31:0] raw_q_imm1;
        always @(posedge clk) raw_q_imm1 <= i_imm1;
        always @(posedge clk) if (accept_bank[46]) q_imm1 <= raw_q_imm1;
        reg [31:0] raw_q_imm2;
        always @(posedge clk) raw_q_imm2 <= i_imm2;
        always @(posedge clk) if (accept_bank[47]) q_imm2 <= raw_q_imm2;
        reg [31:0] raw_q_imm3;
        always @(posedge clk) raw_q_imm3 <= i_imm3;
        always @(posedge clk) if (accept_bank[48]) q_imm3 <= raw_q_imm3;
        reg [1:0] raw_q_chsrc;
        always @(posedge clk) raw_q_chsrc <= i_ch_src;
        always @(posedge clk) if (accept_bank[49]) q_chsrc <= raw_q_chsrc;
        reg [7:0] raw_q_chseq;
        always @(posedge clk) raw_q_chseq <= i_ch_seq;
        always @(posedge clk) if (accept_bank[50]) q_chseq <= raw_q_chseq;
        reg [15:0] raw_q_chlead;
        always @(posedge clk) raw_q_chlead <= i_ch_lead;
        always @(posedge clk) if (accept_bank[51]) q_chlead <= raw_q_chlead;
        reg [15:0] raw_q_chmul;
        always @(posedge clk) raw_q_chmul <= i_ch_mul;
        always @(posedge clk) if (accept_bank[52]) q_chmul <= raw_q_chmul;
    end endgenerate

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
    reg [3:0]    sst;                    // CTL12: the set-up's sub-step while pst == 1
    // CTL12 stage A: the stride products (mod 2^AW) in two halves of the 16-bit count, registered
    reg [AW-1:0] pl_a, pl_b, pl_c, pl_d, pl_o, pl_n;
    reg [AW-9:0] ph_a, ph_b, ph_c, ph_d, ph_o, ph_n;
    wire [AW-1:0] f_h = q_bhalf ? ni_h : ni_a;
    wire [AW-1:0] ctl_product [0:5];
    generate if (CTL13 != 0) begin : g_stride_cut
        ot_hdc_su_ctl_mul16 #(.W(AW)) u_mul0 (.clk(clk), .a(ni_a[15:0]), .b(q_asi), .y(ctl_product[0]));
        ot_hdc_su_ctl_mul16 #(.W(AW)) u_mul1 (.clk(clk), .a(f_h[15:0]), .b(q_bsi), .y(ctl_product[1]));
        ot_hdc_su_ctl_mul16 #(.W(AW)) u_mul2 (.clk(clk), .a(ni_a[15:0]), .b(q_csi), .y(ctl_product[2]));
        ot_hdc_su_ctl_mul16 #(.W(AW)) u_mul3 (.clk(clk), .a(f_h[15:0]), .b(q_dsi), .y(ctl_product[3]));
        ot_hdc_su_ctl_mul16 #(.W(AW)) u_mul4 (.clk(clk), .a(ni_a[15:0]), .b(q_osi), .y(ctl_product[4]));
        ot_hdc_su_ctl_mul16 #(.W(AW)) u_mul5 (.clk(clk), .a(q_nin), .b({{(AW-NW){1'b0}},q_nout}), .y(ctl_product[5]));
        always @(posedge clk) if (pst == 2'd1 && sst == 4'd3) begin
            pl_a <= ctl_product[0]; ph_a <= 0;
            pl_b <= ctl_product[1]; ph_b <= 0;
            pl_c <= ctl_product[2]; ph_c <= 0;
            pl_d <= ctl_product[3]; ph_d <= 0;
            pl_o <= ctl_product[4]; ph_o <= 0;
            pl_n <= ctl_product[5]; ph_n <= 0;
        end
    end else begin : g_stride_legacy
    always @(posedge clk) if (pst == 2'd1 && sst == 3'd0) begin
        pl_a <= ni_a[7:0] * q_asi; ph_a <= ni_a[15:8] * q_asi[AW-9:0];
        pl_b <= f_h[7:0] * q_bsi;  ph_b <= f_h[15:8] * q_bsi[AW-9:0];
        pl_c <= ni_a[7:0] * q_csi; ph_c <= ni_a[15:8] * q_csi[AW-9:0];
        pl_d <= f_h[7:0] * q_dsi;  ph_d <= f_h[15:8] * q_dsi[AW-9:0];
        pl_o <= ni_a[7:0] * q_osi; ph_o <= ni_a[15:8] * q_osi[AW-9:0];
        pl_n <= q_nout * q_nin[7:0]; ph_n <= q_nout * q_nin[15:8];
    end

    end endgenerate
    wire [AW-1:0] pr_a = pl_a + {ph_a, 8'd0}, pr_b = pl_b + {ph_b, 8'd0}, pr_c = pl_c + {ph_c, 8'd0},
                  pr_d = pl_d + {ph_d, 8'd0}, pr_o = pl_o + {ph_o, 8'd0}, pr_n = pl_n + {ph_n, 8'd0};
    wire s1_okp = (q_aind == IND_NONE) && (q_dst != DST_KVT) &&
                  (s1_even || !(q_bhalf || q_qm == QM_ALT_NP || q_qm == QM_ALT_PN)) &&
                  (q_aso == pr_a) && (q_bso == pr_b) && (q_cpair || q_cso == pr_c) && (q_dso == pr_d) &&
                  (q_dst == DST_NONE || q_oso == pr_o);
    reg [4:0] ctl_stride_equal;
    always @(posedge clk) if (CTL13 != 0 && pst == 2'd1 && sst == 4'd4)
        ctl_stride_equal <= {q_oso == pr_o, q_dso == pr_d, q_cso == pr_c, q_bso == pr_b, q_aso == pr_a};
    wire ctl_flat_ok = (q_aind == IND_NONE) && (q_dst != DST_KVT) &&
        (s1_even || !(q_bhalf || q_qm == QM_ALT_NP || q_qm == QM_ALT_PN)) &&
        ctl_stride_equal[0] && ctl_stride_equal[1] && (q_cpair || ctl_stride_equal[2]) &&
        ctl_stride_equal[3] && (q_dst == DST_NONE || ctl_stride_equal[4]);
    wire s1_okx = (CTL13 != 0) ? ctl_flat_ok : (CTL12 != 0) ? s1_okp : s1_ok;
    wire [CW-1:0] s1_nn = (CTL12 != 0) ? pr_n : q_nout * q_nin;
    wire s1_ld = (CTL12 != 0) ? (pst == 2'd1 && sst == ((CTL13 != 0) ? 4'd5 : 4'd1)) : (pst == 2'd1);
    always @(posedge clk) if (s1_ld) begin
        s_flat <= s1_cand && s1_okx;
        // a whole-op reduction whose layout does not flatten: rows of whole 8-element chunks
        s_wnf <= (q_redwhole || q_redtree) && q_red != RED_NONE && !s1_okx && q_nout > 1;
        s_flatbad <= (q_redwhole || q_redtree) && q_red != RED_NONE && !s1_okx && q_nout > 1 && (q_nin[2:0] != 3'd0);
        s_ni <= (s1_cand && s1_okx) ? s1_nn : q_nin;
        s_no <= (s1_cand && s1_okx) ? 1 : q_nout;
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
    wire [3:0] x_ls = (c_lsz > c_lvw) ? c_lvw : c_lsz[3:0];
    // CTL12 stages C (slot size), D (layout and the first depths), E / F (a non-flattening whole-op
    // reduction's vector count s_no * (s_ni >> ls), in two halves of s_no)
    reg  [3:0] r_ls, r_nsh;
    reg        r_packed;
    reg  [CW-1:0] r_nvs, r_sh;
    reg  [9:0] r_dF, r_dM, r_dS, r_lt2;
    reg  [CW-1:0] r_wl;
    reg  [CW-9:0] r_wh;
    wire [3:0] c_ls = (CTL12 != 0) ? r_ls : x_ls;
    wire x_packed = !s_wnf && (s_ni <= (1 << c_ls));
    wire c_packed = (CTL12 != 0) ? r_packed : x_packed;
    wire c_rpow = pow2(q_rso);
    wire [3:0] x_nsh = (x_packed && (!red_on || c_rpow)) ? (c_lvw - c_ls) : 4'd0;
    wire [3:0] c_nsh = (CTL12 != 0) ? r_nsh : x_nsh;
    wire [CW-1:0] x_nvs = s_wnf ? s_no * (s_ni >> c_ls) : (s_ni + (1 << c_ls) - 1) >> c_ls;
    wire [CW-1:0] c_nvs = (CTL12 != 0) ? r_nvs : x_nvs;
    wire [4:0] c_L = log2c(c_nvs);
    wire c_span = red_on && !c_packed;
    wire c_gather = (q_aind != IND_NONE);
    wire [AW-1:0] c_gstr = (q_aind == IND_I) ? q_asi : q_aso;
    wire c_div = (q_m1 == M1_DIVB || q_m1 == M1_DIVIMM);
    wire [9:0] x_dF = c_gather ? 10'd6 + OPR + CAPR : 10'd4 + CAPR;       // broadcast register + fetch
    wire [9:0] x_dM = x_dF + 10'd1 + OPR + (c_div ? DDIV : H_M[9:0]);
    wire [9:0] x_dS = x_dM + H_M[9:0] + H_A[9:0] + OPR + sfu_d(q_sfu);
    wire [9:0] x_lt = red_on ? {6'd0, c_ls} - 10'd3 : 10'd0;
    wire [9:0] c_dF = (CTL12 != 0) ? r_dF : x_dF;
    wire [9:0] c_dM = (CTL12 != 0) ? r_dM : x_dM;
    wire [9:0] c_dS = (CTL12 != 0) ? r_dS : x_dS;
    wire [9:0] c_lt = (CTL12 != 0) ? r_lt2 : x_lt;
    always @(posedge clk) begin
        if (pst == 2'd1 && sst == ((CTL13 != 0) ? 4'd6 : 4'd2)) r_ls <= x_ls;
        if (pst == 2'd1 && sst == ((CTL13 != 0) ? 4'd7 : 4'd3)) begin
            r_packed <= x_packed; r_nsh <= x_nsh; r_sh <= s_ni >> c_ls;
            r_nvs <= (s_ni + (1 << c_ls) - 1) >> c_ls;          // replaced below for a non-flattening reduction
            r_dF <= x_dF; r_dM <= x_dM; r_dS <= x_dS; r_lt2 <= x_lt;
        end
        if (CTL13 == 0 && pst == 2'd1 && sst == 4'd4) begin r_wl <= s_no[7:0] * r_sh; r_wh <= s_no[15:8] * r_sh[CW-9:0]; end
        if (CTL13 == 0 && pst == 2'd1 && sst == 4'd5) r_nvs <= r_wl + {r_wh, 8'd0};
        if (CTL13 != 0 && pst == 2'd1 && sst == 4'd10) r_nvs <= ctl_whole_product;
    end
    wire [CW-1:0] ctl_whole_product;
    generate if (CTL13 != 0) begin : g_whole_cut
        ot_hdc_su_ctl_mul16 #(.W(CW)) u_mul (.clk(clk), .a(s_no[15:0]), .b(r_sh), .y(ctl_whole_product));
    end else begin : g_whole_unused
        assign ctl_whole_product = 0;
    end endgenerate
    // retire (E1, E2, OUT: 2 MLAT + 1), then the reducer to its tap (IN 1, SQ MLAT, CHAIN 7 ALAT, TREE ALAT lt)
    wire [9:0] c_dT = c_dS + (H_M[9:0] << 1) + OPR + 10'd1 + 10'd1 + H_M[9:0] + 10'd7 * H_A[9:0] + RPAD + RSL + RTAP + ROUT
                      + H_R[9:0] * c_lt;
    wire [9:0] c_dR = c_dT + 10'd1 + (c_span ? H_R[9:0] * {5'd0, c_L} : 10'd0);
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
    // The offset bank's barrel/selection logic is captured in the already
    // priced layout sub-step. The final pending boundary sees only local data.
    reg [5*LN*AW-1:0] ctl_terms;
    reg [5*AW-1:0] ctl_istep, ctl_ostep;
    wire [5*AW-1:0] ctl_ostep_candidate;
    generate if(CTL13 != 0) begin : g_offset_cut
        genvar k,part;
        for(k=0;k<5;k=k+1) begin : g_stream
            assign ctl_ostep_candidate[k*AW+:AW]=(k==0 && q_aind==IND_O)?0:so_s[k]<<x_nsh;
            always @(posedge clk) if(ctl_setup_bank[7][90+k])
                ctl_istep[k*AW+:AW]<=c_istep[k*AW+:AW];
            always @(posedge clk) if(ctl_setup_bank[7][95+k])
                ctl_ostep[k*AW+:AW]<=ctl_ostep_candidate[k*AW+:AW];
        end
        for(part=0;part<5*LN;part=part+1) begin : g_term
            always @(posedge clk) if(ctl_setup_bank[7][32+part])
                ctl_terms[part*AW+:AW]<=c_terms[part*AW+:AW];
        end
    end else begin : g_unused_offset_cut
        assign ctl_ostep_candidate=0;
    end endgenerate
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
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[0] : s2_go) p_no <= s_no;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[1] : s2_go) p_ni <= s_ni;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[2] : s2_go) p_ls <= c_ls;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[3] : s2_go) p_lvw <= c_lvw;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[4] : s2_go) p_nsh <= c_nsh;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[5] : s2_go) p_lt <= c_lt[3:0];
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[6] : s2_go) p_L <= (c_L > 7) ? 3'd7 : c_L[2:0];
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[7] : s2_go) p_packed <= c_packed;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[8] : s2_go) p_span <= c_span;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[9] : s2_go) p_bad <= c_bad;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[10] : s2_go) p_gather <= c_gather;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[11] : s2_go) p_gsh <= log2f(c_gstr);
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[12] : s2_go) p_rsh <= log2f(q_rso);
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[13] : s2_go) p_dF <= c_dF;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[14] : s2_go) p_dM <= c_dM;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[15] : s2_go) p_dS <= c_dS;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[16] : s2_go) p_dT <= c_dT;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[17] : s2_go) p_dR <= c_dR;
    wire [5*LN*AW-1:0] ctl_next_p_terms = (CTL13 != 0) ? ctl_terms : c_terms;
    generate if(CTL13 != 0) begin : g_cut_p_terms
        genvar part;
        for(part=0;part<(5*LN*AW+23)/24;part=part+1) begin : g_part
            localparam integer BW=(5*LN*AW-part*24<24)?5*LN*AW-part*24:24;
            always @(posedge clk) if(ctl_s2_bank[32+part]) p_terms[part*24+:BW]<=ctl_next_p_terms[part*24+:BW];
        end
    end else begin : g_legacy_p_terms
        always @(posedge clk) if(s2_go) p_terms<=ctl_next_p_terms;
    end endgenerate
    wire [5*AW-1:0] ctl_next_p_istep = (CTL13 != 0) ? ctl_istep : c_istep;
    generate if(CTL13 != 0) begin : g_cut_p_istep
        genvar part;
        for(part=0;part<(5*AW+23)/24;part=part+1) begin : g_part
            localparam integer BW=(5*AW-part*24<24)?5*AW-part*24:24;
            always @(posedge clk) if(ctl_s2_bank[90+part]) p_istep[part*24+:BW]<=ctl_next_p_istep[part*24+:BW];
        end
    end else begin : g_legacy_p_istep
        always @(posedge clk) if(s2_go) p_istep<=ctl_next_p_istep;
    end endgenerate
    wire [5*AW-1:0] ctl_next_p_ostep = (CTL13 != 0) ? ctl_ostep : c_ostep;
    generate if(CTL13 != 0) begin : g_cut_p_ostep
        genvar part;
        for(part=0;part<(5*AW+23)/24;part=part+1) begin : g_part
            localparam integer BW=(5*AW-part*24<24)?5*AW-part*24:24;
            always @(posedge clk) if(ctl_s2_bank[95+part]) p_ostep[part*24+:BW]<=ctl_next_p_ostep[part*24+:BW];
        end
    end else begin : g_legacy_p_ostep
        always @(posedge clk) if(s2_go) p_ostep<=ctl_next_p_ostep;
    end endgenerate
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[21] : s2_go) p_rstep <= s_wnf ? {AW{1'b0}} : q_rso << c_nsh;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_s2_bank[22] : s2_go) p_wnf <= s_wnf;

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
    reg [15:0]       e_tot, r_tot;       // r_tot: vectors whose writes this unit's consumers may read (DI)
    reg [15:0]       rp_tot;             // vectors whose writes have landed (published)
    reg [7:0]        i_dseq, i_rseq;     // cr_dseq / cr_rseq at the internal credit timing (DI)
    wire             ret_i, ret_p, res_i, res_p;
    wire [7:0]       ret_i_seq, ret_p_seq, res_i_seq, res_p_seq;
    wire             ret_i_last, ret_p_last, res_i_last, res_p_last;
    reg [9:0]        cpF, cpM, cpS, cpT, cpR;
    reg [7:0]        rseq_r;

    // position of the vector, its end
    wire [CW-1:0] S_sz = 1 << a_ls;
    wire [CW-1:0] nslot = 1 << a_nsh;
    wire wrap_c = a_packed || (ctl_iv_step >= a_ni);                  // the vector ends its row(s)
    wire last_c = wrap_c && (ctl_ov_step >= a_no);
    reg  wrap_r, olast_r, ck_r, ch_r;   // CTL12: the conditions of the current vector, registered
    wire wrap = (CTL12 != 0) ? wrap_r : wrap_c;
    wire last_v = (CTL12 != 0) ? (wrap_r && olast_r) : last_c;
    // first-vector checkpoints
    wire ck_c = (a_dF >= cpF) && (a_dM >= cpM) && (a_dS >= cpS) &&
                (a_red == RED_NONE || a_dR >= cpR) && (!a_span || a_dT >= cpT);
    wire ck_ok = (CTL12 != 0) ? ck_r : ck_c;
    // chaining
    wire [15:0] need = ctl_need;
    wire [15:0] pv_cnt = r_tot - pv_mark;
    wire        pv_neg = pv_cnt[15];
    wire [7:0]  ds = i_dseq - a_chseq;
    wire        pv_ok  = !ds[7] || (pv_v && pv_seq == a_chseq && !pv_neg && pv_cnt >= need);
    wire [7:0]  dx = x_dseq - a_chseq;
    wire [7:0]  dr = i_rseq - a_chseq;
    wire ch_c = (a_chsrc == CH_NONE) ? 1'b1 :
                (a_chsrc == CH_SELF) ? pv_ok :
                (a_chsrc == CH_RES)  ? !dr[7] :
                (!dx[7] || (x_seq == a_chseq && x_cnt >= need));
    wire ch_ok = (CTL12 != 0) ? ch_r : ch_c;
    wire emit_c = a_v && (a_started || ck_ok) && ch_ok;
    (* keep *) reg [127:0] ctl_emit_bank, ctl_promote_bank;
    wire emit = (CTL13 != 0) ? ctl_emit_bank[0] : emit_c;
    wire promote_c = (pst == 2'd3) && (!a_v || (emit && last_v));
    wire promote = (CTL13 != 0) ? ctl_promote_bank[0] : promote_c;

    // ---- CTL12: the next cycle's conditions, registered ------------------------------------------
    // The row-end / last-vector flags of the current vector (with the next position i_v + S, ctl_ov_step kept
    // in registers), the first-vector checkpoints and the chaining credits, each computed from the state the
    // next cycle will hold (promote / emit select among precomputed candidates), so `emit` is a few gates.
    reg  [CW-1:0] iv1_r, ov1_r;
    reg           a_wrap0, p_wrap0, p_olast0;
    always @(posedge clk) if (pst == 2'd2 && !s2_go) begin     // the lane-load cycle
        p_wrap0 <= p_packed || ((1 << p_ls) >= p_ni);
        p_olast0 <= ((1 << p_nsh) >= p_no);
    end
    wire [CW-1:0] iv2 = ctl_iv2;
    wire [CW-1:0] ov2 = ctl_ov2;
    always @(posedge clk) begin
        if (promote) begin
            iv1_r <= 1 << p_ls; ov1_r <= 1 << p_nsh; wrap_r <= p_wrap0; olast_r <= p_olast0; a_wrap0 <= p_wrap0;
        end else if (emit) begin
            if (wrap_r) begin iv1_r <= S_sz; ov1_r <= ov2; wrap_r <= a_wrap0; olast_r <= (ov2 >= a_no); end
            else begin iv1_r <= iv2; wrap_r <= a_packed || (iv2 >= a_ni); end
        end
    end
    // checkpoints: the counters' next values
    wire [9:0] n_cpF = emit ? a_dF : (cpF != 0) ? cpF - 10'd1 : 10'd0;
    wire [9:0] n_cpM = emit ? a_dM : (cpM != 0) ? cpM - 10'd1 : 10'd0;
    wire [9:0] n_cpS = emit ? a_dS : (cpS != 0) ? cpS - 10'd1 : 10'd0;
    wire [9:0] n_cpT = (emit && a_red != RED_NONE) ? a_dT : (cpT != 0) ? cpT - 10'd1 : 10'd0;
    wire [9:0] n_cpR = (emit && a_red != RED_NONE) ? a_dR : (cpR != 0) ? cpR - 10'd1 : 10'd0;
    wire ck_prom = (p_dF >= n_cpF) && (p_dM >= n_cpM) && (p_dS >= n_cpS) &&
                   (q_red == RED_NONE || p_dR >= n_cpR) && (!p_span || p_dT >= n_cpT);
    wire ck_hold = (a_dF >= n_cpF) && (a_dM >= n_cpM) && (a_dS >= n_cpS) &&
                   (a_red == RED_NONE || a_dR >= n_cpR) && (!a_span || a_dT >= n_cpT);
    // chaining: next-cycle internal credit state (exact) and the external producer's state now
    wire [15:0] n_rtot = ctl_rtot;
    wire [7:0]  n_idseq = (ret_i && ret_i_last) ? ret_i_seq : i_dseq;
    wire [7:0]  n_irseq = (res_i && res_i_last) ? res_i_seq : i_rseq;
    wire [15:0] pvm_e = a_started ? a_mark : e_tot;          // pv_mark after this op's last emit
    function automatic chf(input [1:0] src, input [7:0] cseq, input [15:0] nd, input pvv, input [7:0] pvs,
                           input [15:0] pvm, input [15:0] rt, input [7:0] dsq, input [7:0] rsq);
        reg [15:0] cnt;
        reg [7:0] d_s, d_r, d_x;
        begin
            cnt = rt - pvm;
            d_s = dsq - cseq; d_r = rsq - cseq; d_x = x_dseq - cseq;
            chf = (src == CH_NONE) ? 1'b1 :
                  (src == CH_SELF) ? (!d_s[7] || (pvv && pvs == cseq && !cnt[15] && cnt >= nd)) :
                  (src == CH_RES)  ? !d_r[7] :
                  (!d_x[7] || (x_seq == cseq && x_cnt >= nd));
        end
    endfunction
    wire [23:0] acc_e = ctl_acc_e;
    wire [15:0] need_e = ctl_need_e;
    wire ch_prom_a = chf(q_chsrc, q_chseq, q_chlead, 1'b1, a_seq, pvm_e, n_rtot, n_idseq, n_irseq);
    wire ch_prom_i = chf(q_chsrc, q_chseq, q_chlead, pv_v, pv_seq, pv_mark, n_rtot, n_idseq, n_irseq);
    wire ch_emit = chf(a_chsrc, a_chseq, need_e, pv_v, pv_seq, pv_mark, n_rtot, n_idseq, n_irseq);
    wire ch_hold = chf(a_chsrc, a_chseq, need, pv_v, pv_seq, pv_mark, n_rtot, n_idseq, n_irseq);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ck_r <= 1'b0; ch_r <= 1'b0; end
        else begin
            ck_r <= promote ? ck_prom : ck_hold;
            ch_r <= promote ? (a_v ? ch_prom_a : ch_prom_i) : emit ? ch_emit : ch_hold;
        end
    end

    // Registered local flags are computed from the exact next state. They do
    // not defer a vector or change the internal/published credit relation.
    wire ctl_setup_done = pst == 2'd1 &&
        (CTL12 == 0 || (sst == ((CTL13 != 0) ? 4'd7 : 4'd3) && !s_wnf) ||
         sst == ((CTL13 != 0) ? 4'd10 : 4'd5));
    wire [1:0] ctl_next_pst = accept ? 2'd1 : ctl_setup_done ? 2'd2 :
        (pst == 2'd2 && !s2_go) ? 2'd3 : promote ? 2'd0 : pst;
    wire [3:0] ctl_next_sst = accept ? 4'd0 : pst == 2'd1 ? sst + 4'd1 : sst;
    wire ctl_next_av = promote || (a_v && !(emit && last_v));
    wire ctl_next_started = !promote && (a_started || emit);
    wire ctl_next_ck = promote ? ck_prom : ck_hold;
    wire ctl_next_ch = promote ? (a_v ? ch_prom_a : ch_prom_i) : emit ? ch_emit : ch_hold;
    wire ctl_next_wrap = promote ? p_wrap0 : emit ? (wrap_r ? a_wrap0 : a_packed || (iv2 >= a_ni)) : wrap_r;
    wire ctl_next_olast = promote ? p_olast0 : (emit && wrap_r) ? (ov2 >= a_no) : olast_r;
    wire ctl_next_emit = ctl_next_av && (ctl_next_started || ctl_next_ck) && ctl_next_ch;
    wire ctl_next_promote = (ctl_next_pst == 2'd3) &&
        (!ctl_next_av || (ctl_next_emit && ctl_next_wrap && ctl_next_olast));
    (* keep *) reg [127:0] ctl_setup_bank [0:10];
    (* keep *) reg [127:0] ctl_s2_bank;
    integer ctl_phase;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ctl_emit_bank <= 0; ctl_promote_bank <= 0; ctl_s2_bank <= 0;
            for(ctl_phase=0;ctl_phase<=10;ctl_phase=ctl_phase+1) ctl_setup_bank[ctl_phase]<=0;
        end else begin
            ctl_emit_bank <= {128{ctl_next_emit}};
            ctl_promote_bank <= {128{ctl_next_promote}};
            ctl_s2_bank <= {128{ctl_setup_done}};
            for(ctl_phase=0;ctl_phase<=10;ctl_phase=ctl_phase+1)
                ctl_setup_bank[ctl_phase] <= {128{ctl_next_pst == 2'd1 && ctl_next_sst == ctl_phase}};
        end
    end
    // set-up state
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pst <= 2'd0; sst <= 4'd0; seq_ctr <= 8'd0; nbank <= 1'b0; s2_go <= 1'b0; end
        else begin
            s2_go <= 1'b0;
            if (accept) begin pst <= 2'd1; sst <= 4'd0; seq_ctr <= seq_ctr + 8'd1; nbank <= ~nbank; end
            else if (pst == 2'd1 && (CTL12 == 0 || (sst == ((CTL13 != 0) ? 4'd7 : 4'd3) && !s_wnf) || sst == ((CTL13 != 0) ? 4'd10 : 4'd5))) begin
                pst <= 2'd2; s2_go <= 1'b1;
            end
            else if (pst == 2'd1) sst <= sst + 4'd1;
            else if (pst == 2'd2 && !s2_go) pst <= 2'd3;       // lanes load the bank in this cycle
            else if (promote) pst <= 2'd0;
        end
    end
    // (pst 2 takes two cycles: S2 registers p_*, then the lanes load their offsets from p_terms)
    wire lane_ld = (pst == 2'd2) && !s2_go;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_v <= 1'b0; a_started <= 1'b0; pv_v <= 1'b0; e_tot <= 0; r_tot <= 0; rp_tot <= 0;
            cpF <= 0; cpM <= 0; cpS <= 0; cpT <= 0; cpR <= 0;
        end else begin
            e_tot <= e_tot + (emit ? 16'd1 : 16'd0);
            r_tot <= ctl_rtot;
            rp_tot <= rp_tot + (ret_p ? 16'd1 : 16'd0);
            cpF <= emit ? a_dF : (cpF != 0) ? cpF - 10'd1 : 10'd0;
            cpM <= emit ? a_dM : (cpM != 0) ? cpM - 10'd1 : 10'd0;
            cpS <= emit ? a_dS : (cpS != 0) ? cpS - 10'd1 : 10'd0;
            // T is the reducer's tap (one multiplexer for packed results and spanning items): every
            // reducing op arms it, so a spanning op never reaches the tap before an older packed result
            cpT <= (emit && a_red != RED_NONE) ? a_dT : (cpT != 0) ? cpT - 10'd1 : 10'd0;
            cpR <= (emit && a_red != RED_NONE) ? a_dR : (cpR != 0) ? cpR - 10'd1 : 10'd0;
            if (emit && !a_started) a_started <= 1'b1;
            if (emit && last_v) begin
                pv_v <= 1'b1; pv_mark <= a_started ? a_mark : e_tot; pv_nv <= a_nv + 16'd1; pv_seq <= a_seq;
            end
            if (promote) begin a_v <= 1'b1; a_started <= 1'b0; end
            else if (emit && last_v) a_v <= 1'b0;
        end
    end
    wire [5*AW-1:0] ctl_row_next;
    wire [AW-1:0] ctl_rrow_next;
    generate if(CTL13 != 0) begin : g_address_prefix
        ot_hdc_ksadd_k #(.W(5*AW)) u_row(.a(row),.b(a_ostep),.cin(1'b0),.s(ctl_row_next),.cout());
        ot_hdc_ksadd_k #(.W(AW)) u_rrow(.a(rrow),.b(a_rstep),.cin(1'b0),.s(ctl_rrow_next),.cout());
    end else begin : g_address_legacy
        assign ctl_row_next=row+a_ostep;assign ctl_rrow_next=rrow+a_rstep;
    end endgenerate
    generate if(CTL13==0) begin : g_dynamic_legacy
    always @(posedge clk) begin
        if (promote) begin
            a_no <= p_no; a_ni <= p_ni; o_v <= 0; i_v <= 0;
                
                
             
                
              
            row <= {q_obase, q_dbase, q_cbase, q_bbase, q_abase};
            vb  <= {q_obase, q_dbase, q_cbase, q_bbase, q_abase};
            rrow <= q_rbase; krow <= q_orow;
                
                
                
               
                
              
             
               
            a_nv <= 0; a_acc <= 0;
        end else if (emit) begin
            if (!a_started) a_mark <= e_tot;
            a_nv <= a_nv + 16'd1;
            a_acc <= ctl_acc_e;
            if (wrap) begin
                o_v <= ctl_ov_step; i_v <= 0;
                row <= ctl_row_next;
                vb <= ctl_row_next;
                rrow <= ctl_rrow_next;
                krow <= ctl_krow;
            end else begin
                i_v <= ctl_iv_step;
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
    end else begin : g_dynamic_local
        always @(posedge clk) if(ctl_promote_bank[80]) a_no<=p_no;
        always @(posedge clk) if(ctl_promote_bank[81]) a_ni<=p_ni;
        always @(posedge clk) begin
            if(ctl_promote_bank[82]) i_v<=0;
            else if(ctl_emit_bank[82]) i_v<=wrap?0:ctl_iv_step;
        end
        always @(posedge clk) begin
            if(ctl_promote_bank[83]) o_v<=0;
            else if(ctl_emit_bank[83]&&wrap) o_v<=ctl_ov_step;
        end
        always @(posedge clk) begin
            if(ctl_promote_bank[84]) a_nv<=0;
            else if(ctl_emit_bank[84]) a_nv<=a_nv+16'd1;
        end
        always @(posedge clk) begin
            if(ctl_promote_bank[85]) a_acc<=0;
            else if(ctl_emit_bank[85]) a_acc<=ctl_acc_e;
        end
        always @(posedge clk) if(ctl_emit_bank[86]&&!a_started) a_mark<=e_tot;
        always @(posedge clk) begin
            if(ctl_promote_bank[87]) rrow<=q_rbase;
            else if(ctl_emit_bank[87]&&wrap) rrow<=ctl_rrow_next;
        end
        always @(posedge clk) begin
            if(ctl_promote_bank[88]) krow<=q_orow;
            else if(ctl_emit_bank[88]&&wrap) krow<=ctl_krow;
        end
        wire [5*AW-1:0] initial_base={q_obase,q_dbase,q_cbase,q_bbase,q_abase};
        genvar part;
        for(part=0;part<5;part=part+1) begin : g_address_word
            wire [AW-1:0] inner_step=(part==1 && a_bhalf && a_ls==0)?(i_v[0]?a_istep_h1:0):
                (part==3 && a_bhalf && a_ls==0)?(i_v[0]?a_istep_h3:0):a_istep[part*AW+:AW];
            wire [AW-1:0] vb_next;
            ot_hdc_ksadd_k #(.W(AW)) u_inner(.a(vb[part*AW+:AW]),.b(inner_step),.cin(1'b0),.s(vb_next),.cout());
            always @(posedge clk) begin
                if(ctl_promote_bank[90+part]) row[part*AW+:AW]<=initial_base[part*AW+:AW];
                else if(ctl_emit_bank[90+part]&&wrap) row[part*AW+:AW]<=ctl_row_next[part*AW+:AW];
            end
            always @(posedge clk) begin
                if(ctl_promote_bank[95+part]) vb[part*AW+:AW]<=initial_base[part*AW+:AW];
                else if(ctl_emit_bank[95+part]) vb[part*AW+:AW]<=wrap?ctl_row_next[part*AW+:AW]:vb_next;
            end
        end
    end endgenerate
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[1] : promote) a_ls <= p_ls;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[2] : promote) a_lvw <= p_lvw;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[3] : promote) a_nsh <= p_nsh;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[4] : promote) a_lt <= p_lt;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[5] : promote) a_L <= p_L;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[6] : promote) a_packed <= p_packed;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[7] : promote) a_span <= p_span;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[8] : promote) a_gather <= p_gather;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[9] : promote) a_bank <= q_bank;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[10] : promote) a_wnf <= p_wnf;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[11] : promote) a_gsh <= p_gsh;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[12] : promote) a_rsh <= p_rsh;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[13] : promote) a_dF <= p_dF;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[14] : promote) a_dM <= p_dM;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[15] : promote) a_dS <= p_dS;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[16] : promote) a_dT <= p_dT;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[17] : promote) a_dR <= p_dR;
    generate if(CTL13 != 0) begin : g_promote_a_istep
        genvar part;
        for(part=0;part<5;part=part+1) begin : g_part
            always @(posedge clk) if(ctl_promote_bank[64+part]) a_istep[part*AW+:AW]<=p_istep[part*AW+:AW];
        end
    end else begin : g_legacy_promote_a_istep
        always @(posedge clk) if(promote) a_istep<=p_istep;
    end endgenerate
    generate if(CTL13 != 0) begin : g_promote_a_ostep
        genvar part;
        for(part=0;part<5;part=part+1) begin : g_part
            always @(posedge clk) if(ctl_promote_bank[69+part]) a_ostep[part*AW+:AW]<=p_ostep[part*AW+:AW];
        end
    end else begin : g_legacy_promote_a_ostep
        always @(posedge clk) if(promote) a_ostep<=p_ostep;
    end endgenerate
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[20] : promote) a_rstep <= p_rstep;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[21] : promote) a_asrc <= q_asrc;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[22] : promote) a_bsrc <= q_bsrc;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[23] : promote) a_csrc <= q_csrc;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[24] : promote) a_dsrc <= q_dsrc;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[25] : promote) a_aind <= q_aind;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[26] : promote) a_dst <= q_dst;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[27] : promote) a_red <= q_red;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[28] : promote) a_m2 <= q_m2;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[29] : promote) a_e2 <= q_e2;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[30] : promote) a_chsrc <= q_chsrc;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[31] : promote) a_bhalf <= q_bhalf;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[32] : promote) a_cpair <= q_cpair;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[33] : promote) a_arnd <= q_arnd;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[34] : promote) a_arelu <= q_arelu;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[35] : promote) a_amin <= q_amin;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[36] : promote) a_cclip <= q_cclip;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[37] : promote) a_rnd <= q_rnd;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[38] : promote) a_redsq <= q_redsq;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[39] : promote) a_redrnd <= q_redrnd;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[40] : promote) a_m1 <= q_m1;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[41] : promote) a_qm <= q_qm;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[42] : promote) a_ad <= q_ad;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[43] : promote) a_sfu <= q_sfu;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[44] : promote) a_e1 <= q_e1;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[45] : promote) a_imm1 <= q_imm1;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[46] : promote) a_imm2 <= q_imm2;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[47] : promote) a_imm3 <= q_imm3;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[48] : promote) a_obase <= q_obase;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[49] : promote) a_aibase <= q_aibase;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[50] : promote) a_seq <= q_seq;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[51] : promote) a_chseq <= q_chseq;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[52] : promote) a_chlead <= q_chlead;
    always @(posedge clk) if ((CTL13 != 0) ? ctl_promote_bank[53] : promote) a_chmul <= q_chmul;
    // a half stream's inner stride at slot size 1 (its term is 0; it moves by si every other index)
    always @(posedge clk) if((CTL13 != 0)?ctl_promote_bank[100]:promote) a_istep_h1<=q_bsi;
    always @(posedge clk) if((CTL13 != 0)?ctl_promote_bank[101]:promote) a_istep_h3<=q_dsi;

    // published chaining state
    reg [7:0]  lst_seq;
    reg [15:0] lst_mark;
    wire [15:0] lst_cnt = rp_tot - lst_mark;
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
    // BROADCAST register: every lane input of the emitted vector (and its control word) is registered once
    // in the controller, so the lanes see no combinational path from the emit decision.  At the die's width
    // this is the register each 64-lane tile takes its copy from.  It adds one cycle to every depth.
    reg              b_emit, b_bank, b_gather, b_cpair;
    reg [CW-1:0]     b_ov, b_iv, b_no, b_ni;
    reg [3:0]        b_ls, b_lvw;
    reg [5*AW-1:0]   b_vb;
    reg [AW-1:0]     b_krow, b_obase, b_aibase;
    reg [1:0]        b_aind, b_dst;
    reg [4:0]        b_gsh;
    reg [7:0]        b_srcs;
    reg [WC-1:0]     b_cw;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) b_emit <= 1'b0; else b_emit <= emit;
    end
    always @(posedge clk) begin
        b_bank <= a_bank; b_gather <= a_gather; b_cpair <= a_cpair; b_ov <= o_v; b_iv <= i_v; b_no <= a_no;
        b_ni <= a_ni; b_ls <= a_ls; b_lvw <= a_ls + a_nsh; b_vb <= vb; b_krow <= krow; b_obase <= a_obase;
        b_aibase <= a_aibase; b_aind <= a_aind; b_dst <= a_dst; b_gsh <= a_gsh;
        b_srcs <= {a_dsrc, a_csrc, a_bsrc, a_asrc}; b_cw <= cw0;
    end
    // BROADCAST TREE: BCAST_STAGES register stages from the broadcast register to the lanes' leaf register.
    // Everything that travels to the lanes crosses it together: the vector, its control word (the control
    // pipe below starts at the leaf) and the op set-up's offset loads, so the lanes see the same sequence as
    // with no stages, BCAST_STAGES cycles later.  The first BCAST_STAGES - 1 stages are the tree (tr_*, here);
    // the LAST stage is each lane's own leaf register (ot_hdc_v41x_vec_lane LEAF = 1), which holds the lane's
    // partial addresses instead of the raw fields.  The control pipe takes the same last stage here (t_*).
    localparam integer WB = 3 + 4 * CW + 8 + 8 * AW + 4 + 5 + 8 + WC;
    localparam integer WL = 1 + 5 * LN * AW;
    localparam integer BT = (BCAST_STAGES > 0) ? BCAST_STAGES - 1 : 0;     // stages outside the lanes
    wire [WB-1:0]    b_bus = {b_bank, b_gather, b_cpair, b_ov, b_iv, b_no, b_ni, b_ls, b_lvw, b_vb, b_krow, b_obase,
                              b_aibase, b_aind, b_dst, b_gsh, b_srcs, b_cw};
    wire [WB-1:0]    tr_bus;
    wire [WL-1:0]    tr_lbus;
    wire             tr_emit, tr_ld, t_emit, t_gather, bt_live;
    wire             tr_bank, tr_gather, tr_cpair;
    wire [CW-1:0]    tr_ov, tr_iv, tr_no, tr_ni;
    wire [3:0]       tr_ls, tr_lvw;
    wire [5*AW-1:0]  tr_vb;
    wire [AW-1:0]    tr_krow, tr_obase, tr_aibase;
    wire [1:0]       tr_aind, tr_dst;
    wire [4:0]       tr_gsh;
    wire [7:0]       tr_srcs;
    wire [WC-1:0]    tr_cw, t_cw;
    wire             tr_ldbank;
    wire [5*LN*AW-1:0] tr_ldc;
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(WB), .D(BT)) u_bt (.clk(clk), .rst_n(rst_n), .d(b_bus), .q(tr_bus));
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(WL), .D(BT)) u_bl (.clk(clk), .rst_n(rst_n), .d({q_bank, p_terms}), .q(tr_lbus));
    assign {tr_bank, tr_gather, tr_cpair, tr_ov, tr_iv, tr_no, tr_ni, tr_ls, tr_lvw, tr_vb, tr_krow, tr_obase, tr_aibase, tr_aind,
            tr_dst, tr_gsh, tr_srcs, tr_cw} = tr_bus;
    assign {tr_ldbank, tr_ldc} = tr_lbus;
    generate if (BCAST_STAGES == 0) begin : g_bt0
        assign {tr_emit, tr_ld} = {b_emit, lane_ld};
        assign {t_emit, t_gather, t_cw} = {b_emit, b_gather, b_cw};
        assign bt_live = 1'b0;
    end else begin : g_bt
        reg [BCAST_STAGES-1:0] bt_e, bt_l;      // valid of every stage, the leaf's included
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin bt_e <= {BCAST_STAGES{1'b0}}; bt_l <= {BCAST_STAGES{1'b0}}; end
            else begin
                bt_e <= (bt_e << 1) | {{(BCAST_STAGES-1){1'b0}}, b_emit};
                bt_l <= (bt_l << 1) | {{(BCAST_STAGES-1){1'b0}}, lane_ld};
            end
        end
        assign tr_emit = (BCAST_STAGES > 1) ? bt_e[BT > 0 ? BT - 1 : 0] : b_emit;
        assign tr_ld   = (BCAST_STAGES > 1) ? bt_l[BT > 0 ? BT - 1 : 0] : lane_ld;
        assign t_emit = bt_e[BCAST_STAGES-1];
        reg          t_g;
        reg [WC-1:0] t_c;
        always @(posedge clk) begin t_g <= tr_gather; t_c <= tr_cw; end
        assign t_gather = t_g;
        assign t_cw = t_c;
        assign bt_live = |{bt_e, bt_l};
    end endgenerate
    // F-line: depth 3 or 5
    wire [WC-1:0] cwx;
    wire          vx, col_f, bz_f, bz_m, bz_s;
    ot_hdc_su_ctl_insert #(.LOCAL(CTL13), .W(WC), .K(2), .DEPTHS({H_F5, H_F3}), .DMAX(5 + OPR + CAPR)) u_cf (.clk(clk), .rst_n(rst_n),
        .v(t_emit), .sel({t_gather, !t_gather}), .d(t_cw), .vo(vx), .q(cwx), .coll(col_f), .busy(bz_f));
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
    // M1-line: 3 or 19
    wire [WC-1:0] cwm;
    wire          vm, col_m;
    ot_hdc_su_ctl_insert #(.LOCAL(CTL13), .W(WC), .K(2), .DEPTHS({H_MD, H_MM}), .DMAX(DDIV + OPR)) u_cm (.clk(clk), .rst_n(rst_n),
        .v(vp), .sel({p_div, !p_div}), .d(cwp), .vo(vm), .q(cwm), .coll(col_m), .busy(bz_m));
    // AD in (+MLAT: M2), S in (+MLAT + ALAT: AD)
    wire [WC-1:0] cwa, cwi;
    wire [MLAT+ALAT+OPR:0] vml;
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(WC), .D(MLAT)) u_ca (.clk(clk), .rst_n(rst_n), .d(cwm), .q(cwa));
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(WC), .D(ALAT + OPR)) u_ci (.clk(clk), .rst_n(rst_n), .d(cwa), .q(cwi));
    ot_hdc_vline #(.D(MLAT + ALAT + OPR)) u_vml (.clk(clk), .rst_n(rst_n), .v(vm), .vd(vml));
    wire vi = vml[MLAT + ALAT + OPR];
    wire [2:0] i_s = `CW_SFU(cwi);
    wire [6:0] s_sel = {i_s == SFU_EGATE, i_s == SFU_SPSQRT, i_s == SFU_SQRT, i_s == SFU_RSQRT,
                        i_s == SFU_SIGM || i_s == SFU_SILU, i_s == SFU_EXP, i_s == SFU_NONE};
    wire [WC-1:0] cws;
    wire          vs, col_s;
    ot_hdc_su_ctl_insert #(.LOCAL(CTL13), .W(WC), .K(7), .DEPTHS({H_EG, H_SP, H_SQRT, H_RSQ, H_SIG, H_EXP, 16'd0}),
                      .DMAX(D_SP)) u_cs (.clk(clk), .rst_n(rst_n), .v(vi), .sel(s_sel), .d(cwi), .vo(vs), .q(cws),
                      .coll(col_s), .busy(bz_s));
    // E2 in (+MLAT: E1), OUT in (+2 MLAT), retire (+2 MLAT + 1)
    wire [WC-1:0] cwe, cwo, cwr;
    wire [2*MLAT+1+OPR:0] vsl;
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(WC), .D(MLAT + OPR)) u_ce (.clk(clk), .rst_n(rst_n), .d(cws), .q(cwe));
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(WC), .D(MLAT)) u_co (.clk(clk), .rst_n(rst_n), .d(cwe), .q(cwo));
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(WC), .D(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(cwo), .q(cwr));
    ot_hdc_vline #(.D(2 * MLAT + 1 + OPR)) u_vsl (.clk(clk), .rst_n(rst_n), .v(vs), .vd(vsl));
    wire retire = vsl[2 * MLAT + 1 + OPR];
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
    wire [N-1:0]    l_vm_we, l_kv_we;
    wire [N*AW-1:0] l_vm_waddr, l_kv_waddr;
    wire [N*32-1:0] l_vm_wdata, l_kv_wdata;
    genvar l;
    generate for (l = 0; l < N; l = l + 1) begin : g_lane
        ot_hdc_v41x_vec_lane #(.AW(AW), .CW(CW), .LN(LN), .KIND((l == 0) ? 2 : (l < M) ? 1 : 0),
                               .KVT_SH(KVT_SH), .LEAF((BCAST_STAGES > 0) ? 1 : 0), .MLAT(MLAT), .ALAT(ALAT),
                               .OPR(OPR), .DDIV(DDIV), .SIDEX(SIDEX), .CAPR(CAPR)) u_lane (
            .clk(clk), .rst_n(rst_n), .lane_id(l[10:0]),
            .ld(tr_ld), .ld_bank(tr_ldbank), .ld_c(tr_ldc),
            .emit(tr_emit), .bank(tr_bank), .o_v(tr_ov), .i_v(tr_iv), .no(tr_no), .ni(tr_ni), .ls(tr_ls), .lvw(tr_lvw),
            .vb(tr_vb), .krow(tr_krow), .obase(tr_obase), .aibase(tr_aibase), .aind(tr_aind), .gsh(tr_gsh),
            .cpair(tr_cpair), .dst(tr_dst), .srcs(tr_srcs),
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
            .vm_we(l_vm_we[l]), .vm_waddr(l_vm_waddr[l*AW +: AW]), .vm_wdata(l_vm_wdata[l*32 +: 32]),
            .kv_we(l_kv_we[l]), .kv_waddr(l_kv_waddr[l*AW +: AW]), .kv_wdata(l_kv_wdata[l*32 +: 32]),
            .ro_v(l_rov[l]), .ro_x(l_rox[l*32 +: 32]), .fault(l_fault[l]), .coll(l_coll[l]));
    end endgenerate
    assign side_v = l_sv[0];
    assign side_x = l_sx[31:0];
    ot_hdc_v41x_vec_side #(.MLAT(MLAT), .ALAT(ALAT), .DDIV(DDIV), .SIDEX(SIDEX), .FSQ(FSQ)) u_side (.clk(clk), .rst_n(rst_n), .v(side_v), .fn(`CW_SFU(cwi)), .x(side_x),
                                 .fn_out(`CW_SFU(cws)), .y(side_y), .fault(side_f));

    // =========================================================================================
    // Reducer
    // =========================================================================================
    wire [7:0] red_seq;
    wire       red_lastres, red_ev, red_busy, red_f;
    wire [NR-1:0]    l_res_we;
    wire [NR*AW-1:0] l_res_addr;
    wire [NR*32-1:0] l_res_data;
    ot_hdc_v41x_vec_red #(.N(N), .LV(LV), .AW(AW), .MW(9), .MLAT(MLAT), .ALAT(ALAT), .RPAD(RPAD), .RSL(RSL),
                          .RTAP(RTAP), .ROUT(ROUT), .SL(RSLICE)) u_red (.clk(clk), .rst_n(rst_n),
        .v_in(retire && r_red != RED_NONE), .x_in(l_rox), .live_in(l_rov), .mx_in(r_red == RED_MAX),
        .sq_in(r_sq), .lt_in(r_lt), .span_in(r_span), .l_in(r_L), .last_in(r_wrap), .nres_in(r_nres),
        .rnd_in(r_rnd), .rbase_in(r_rbase), .rsh_in(r_rsh), .meta_in({r_seq, r_lastres}),
        .o_we(l_res_we), .o_addr(l_res_addr), .o_data(l_res_data), .o_meta({red_seq, red_lastres}), .o_ev(red_ev),
        .busy(red_busy), .fault(red_f));

    // =========================================================================================
    // RETURN: RET_STAGES register stages from the lanes and the reducer to the vector memory.  The
    // write events travel beside them: at RET_STAGES (the write lands: published state, the bench trace)
    // and at DI (this unit's own consumers, which read BCAST_STAGES after their emit)
    // =========================================================================================
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(2 * N), .D(RET_STAGES), .RESET(1)) u_rwe (.clk(clk), .rst_n(rst_n),
        .d({l_vm_we, l_kv_we}), .q({vm_we, kv_we}));
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(N * (2 * AW + 64)), .D(RET_STAGES)) u_rwd (.clk(clk), .rst_n(rst_n),
        .d({l_vm_waddr, l_vm_wdata, l_kv_waddr, l_kv_wdata}), .q({vm_waddr, vm_wdata, kv_waddr, kv_wdata}));
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(NR), .D(RET_STAGES), .RESET(1)) u_rre (.clk(clk), .rst_n(rst_n), .d(l_res_we), .q(res_we));
    ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(NR * (AW + 32)), .D(RET_STAGES)) u_rrd (.clk(clk), .rst_n(rst_n),
        .d({l_res_addr, l_res_data}), .q({res_addr, res_data}));
    wire rt_live;
    generate if (RET_STAGES == 0) begin : g_rt0
        assign {ret_p, ret_p_seq, ret_p_last} = {retire, r_seq, r_lastv};
        assign {res_p, res_p_seq, res_p_last} = {red_ev, red_seq, red_lastres};
        assign rt_live = 1'b0;
    end else begin : g_rt
        reg [RET_STAGES-1:0] rt_v, rs_v;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin rt_v <= {RET_STAGES{1'b0}}; rs_v <= {RET_STAGES{1'b0}}; end
            else begin
                rt_v <= (rt_v << 1) | {{(RET_STAGES-1){1'b0}}, retire};
                rs_v <= (rs_v << 1) | {{(RET_STAGES-1){1'b0}}, red_ev};
            end
        end
        wire [8:0] rt_m, rs_m;
        ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(9), .D(RET_STAGES)) u_rtm (.clk(clk), .rst_n(rst_n), .d({r_seq, r_lastv}), .q(rt_m));
        ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(9), .D(RET_STAGES)) u_rsm (.clk(clk), .rst_n(rst_n), .d({red_seq, red_lastres}), .q(rs_m));
        assign {ret_p, ret_p_seq, ret_p_last} = {rt_v[RET_STAGES-1], rt_m};
        assign {res_p, res_p_seq, res_p_last} = {rs_v[RET_STAGES-1], rs_m};
        assign rt_live = |{rt_v, rs_v};
    end endgenerate
    generate if (DI == 0) begin : g_di0
        assign {ret_i, ret_i_seq, ret_i_last} = {retire, r_seq, r_lastv};
        assign {res_i, res_i_seq, res_i_last} = {red_ev, red_seq, red_lastres};
    end else begin : g_di
        wire [9:0] di_r, di_s;
        ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(1), .D(DI), .RESET(1)) u_dirv (.clk(clk), .rst_n(rst_n), .d(retire), .q(di_r[9]));
        ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(9), .D(DI)) u_dirm (.clk(clk), .rst_n(rst_n), .d({r_seq, r_lastv}), .q(di_r[8:0]));
        ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(1), .D(DI), .RESET(1)) u_disv (.clk(clk), .rst_n(rst_n), .d(red_ev), .q(di_s[9]));
        ot_hdc_su_ctl_delay #(.LOCAL(CTL13), .W(9), .D(DI)) u_dism (.clk(clk), .rst_n(rst_n), .d({red_seq, red_lastres}), .q(di_s[8:0]));
        assign {ret_i, ret_i_seq, ret_i_last} = di_r;
        assign {res_i, res_i_seq, res_i_last} = di_s;
    end endgenerate

    assign dbg_emit = emit;
    assign dbg_eseq = a_seq;
    assign dbg_ret = ret_p;             // the trace records writes when they land
    assign dbg_rseq = ret_p_seq;
    assign dbg_res = res_p;
    assign dbg_sseq = res_p_seq;
    // published completion (writes landed) and the internal credit copies
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cr_dseq <= 8'hFF; cr_rseq <= 8'hFF; i_dseq <= 8'hFF; i_rseq <= 8'hFF; emitted <= 0; retire_o <= 1'b0;
        end else begin
            if (ret_p && ret_p_last) cr_dseq <= ret_p_seq;
            if (res_p && res_p_last) cr_rseq <= res_p_seq;
            if (ret_i && ret_i_last) i_dseq <= ret_i_seq;
            if (res_i && res_i_last) i_rseq <= res_i_seq;
            emitted <= emitted + (emit ? 16'd1 : 16'd0);
            retire_o <= ret_p;
        end
    end

    // =========================================================================================
    // Status
    // =========================================================================================
    wire pipe_live = b_emit || bt_live || rt_live || bz_f || vp || bz_m || (|vml) || bz_s || (|vsl);
    wire idle_c = (pst == 2'd0) && !a_v && !pipe_live && !red_busy;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; order_fault <= 1'b0; end
        else begin
            idle <= idle_c && !accept;
            fault <= (|l_fault) || side_f || red_f || (promote && p_bad);
            order_fault <= (|l_coll) || col_f || col_m || col_s;
        end
    end
    wire [CW-1:0] ctl_iv_step;
    generate if(CTL13 != 0) begin : g_ctl_iv_step
        ot_hdc_ksadd_k #(.W(CW)) u(.a(i_v),.b(S_sz),.cin(1'b0),.s(ctl_iv_step),.cout());
    end else begin : g_ctl_iv_step_legacy
        assign ctl_iv_step=i_v + S_sz;
    end endgenerate
    wire [CW-1:0] ctl_ov_step;
    generate if(CTL13 != 0) begin : g_ctl_ov_step
        ot_hdc_ksadd_k #(.W(CW)) u(.a(o_v),.b(nslot),.cin(1'b0),.s(ctl_ov_step),.cout());
    end else begin : g_ctl_ov_step_legacy
        assign ctl_ov_step=o_v + nslot;
    end endgenerate
    wire [CW-1:0] ctl_iv2;
    generate if(CTL13 != 0) begin : g_ctl_iv2
        ot_hdc_ksadd_k #(.W(CW)) u(.a(iv1_r),.b(S_sz),.cin(1'b0),.s(ctl_iv2),.cout());
    end else begin : g_ctl_iv2_legacy
        assign ctl_iv2=iv1_r + S_sz;
    end endgenerate
    wire [CW-1:0] ctl_ov2;
    generate if(CTL13 != 0) begin : g_ctl_ov2
        ot_hdc_ksadd_k #(.W(CW)) u(.a(ov1_r),.b(nslot),.cin(1'b0),.s(ctl_ov2),.cout());
    end else begin : g_ctl_ov2_legacy
        assign ctl_ov2=ov1_r + nslot;
    end endgenerate
    wire [24-1:0] ctl_acc_e;
    generate if(CTL13 != 0) begin : g_ctl_acc_e
        ot_hdc_ksadd_k #(.W(24)) u(.a(a_acc),.b({8'd0, a_chmul}),.cin(1'b0),.s(ctl_acc_e),.cout());
    end else begin : g_ctl_acc_e_legacy
        assign ctl_acc_e=a_acc + {8'd0, a_chmul};
    end endgenerate
    wire [16-1:0] ctl_need;
    generate if(CTL13 != 0) begin : g_ctl_need
        ot_hdc_ksadd_k #(.W(16)) u(.a(a_chlead),.b(a_acc[23:8]),.cin(1'b0),.s(ctl_need),.cout());
    end else begin : g_ctl_need_legacy
        assign ctl_need=a_chlead + a_acc[23:8];
    end endgenerate
    wire [16-1:0] ctl_need_e;
    generate if(CTL13 != 0) begin : g_ctl_need_e
        ot_hdc_ksadd_k #(.W(16)) u(.a(a_chlead),.b(acc_e[23:8]),.cin(1'b0),.s(ctl_need_e),.cout());
    end else begin : g_ctl_need_e_legacy
        assign ctl_need_e=a_chlead + acc_e[23:8];
    end endgenerate
    wire [16-1:0] ctl_rtot;
    generate if(CTL13 != 0) begin : g_ctl_rtot
        ot_hdc_ksadd_k #(.W(16)) u(.a(r_tot),.b((ret_i ? 16'd1 : 16'd0)),.cin(1'b0),.s(ctl_rtot),.cout());
    end else begin : g_ctl_rtot_legacy
        assign ctl_rtot=r_tot + (ret_i ? 16'd1 : 16'd0);
    end endgenerate
    wire [AW-1:0] ctl_krow;
    generate if(CTL13 != 0) begin : g_ctl_krow
        ot_hdc_ksadd_k #(.W(AW)) u(.a(krow),.b(nslot[AW-1:0]),.cin(1'b0),.s(ctl_krow),.cout());
    end else begin : g_ctl_krow_legacy
        assign ctl_krow=krow + nslot[AW-1:0];
    end endgenerate
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
