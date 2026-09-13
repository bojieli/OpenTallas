`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DMA.NGRAM_HASH -- Engram n-gram hash row ids.  ABI 3.0 DMA sub-opcode 0x04
// (ot_a3_pkg::A3_DMA_NGRAM_HASH), IR kind NGRAM_HASH(token_ids, order, head)
// -> row_ids, numeric contract ngram_hash_u32_v1.
//
// FULLY PIPELINED.  LATENCY register stages, INITIATION INTERVAL 1: one n-gram
// row id retired every cycle, indefinitely, with no combinational path
// spanning more than one stage and no path that walks a vector.  LATENCY (an
// accepted beat to its out_valid) is the localparam LATENCY, published on the
// info_pipe_stages port so a bench checks it instead of mirroring it.
//
// THE EXACT INTEGER IDENTITY.  For an n-gram of order n ending at a position,
// a hash head h, per-lookback multipliers m_j, a column prime P and that
// column's row offset:
//
//     t_j    = pad_id when the lookback is blocked, else the compressed id
//     X_n    = (t_0*m_0) XOR (t_1*m_1) XOR ... XOR (t_{n-1}*m_{n-1})
//     row    = (X_n mod P) + offset
//
// The fold is XOR, not addition, and the modulus is the COLUMN's prime, not
// the table's row count: the pinned inference/engram.py
// (SRC-DSV41-FLASH-MODEL, revision dba1be0a40aa45a94ad051997016db3960a90277,
// SHA-256 11f35ecbead8150c35aa002b3d180ef290b05a25afe883a11884f94d476d3897)
// builds each layer's table as (max_ngram_size-1) x n_heads disjoint
// prime-sized bucket ranges, draws the primes in order and never reuses one,
// and adds the prefix-sum offset of the earlier columns.  The released
// 384,006,168 and 384,016,682 row counts are exactly the sums of those 24
// primes per layer -- which is why the row count is NOT the modulus, and why
// every prime, offset, multiplier, pad id and vocabulary bound below is a
// RUN-TIME OPERAND written through the configuration port.
//
// NO FROZEN MODEL GEOMETRY.  Every width, count, order bound, head count and
// table extent is a parameter with the V4.1-Flash value as its default, and
// every value the datapath computes with is an operand:
//
//   * ORDER_MIN/ORDER_MAX 2/4 (engram_max_ngram_size 4), NUM_HEADS 8
//     (engram_n_heads), so NUM_COLS = 3*8 = 24 -- the rows read per module per
//     token, which the plan's traffic model counts independently;
//   * the 24 primes, their offsets, the ORDER_MAX multipliers, the pad id, the
//     compressed-vocabulary extent and the table row count are CONFIGURATION
//     OPERANDS.  The two Engram layers differ in all 24 primes and in every
//     multiplier, so a layer change is a reconfiguration, never a rebuild;
//   * each predicate is derived from an operand: a token id is checked against
//     the configured vocabulary extent, a column against the configured table
//     row count, an order against ORDER_MIN/ORDER_MAX, a product against
//     DIVIDEND_W.  Nothing is compared against a literal model number.
//
// THE MODULAR REDUCTION, which is the whole numeric problem.  The dividend is
// up to DIVIDEND_W = 63 bits (the pinned multipliers are chosen so an
// id x multiplier product cannot leave the positive int64 range) and the
// modulus is a run-time 24-bit prime that is not a power of two, and there are
// 24 distinct moduli per layer.  One combinational divide would close nowhere
// near the frequency of ot_a3_mac_lane_pipe, so this block uses BARRETT
// reduction with a per-column reciprocal DERIVED ON CHIP at configuration
// time, never trusted as an operand:
//
//     np    = bit length of P                     (2 <= np <= MOD_W)
//     mu    = floor(2^(np + DIVIDEND_W) / P)      (DIVIDEND_W+1 .. +2 bits)
//     Xh    = floor(X / 2^(np-1))
//     qhat  = floor(Xh * mu / 2^(DIVIDEND_W+1))
//     r0    = X - qhat*P
//     r     = r0 - k*P  for the largest k in {0,1,2} with r0 >= k*P
//
// qhat <= floor(X/P) always, so r0 >= 0; and r0 < P*X/2^(np+DIVIDEND_W)
// + 2^(np-1) + P <= 1 + P + P, so TWO conditional subtractions are sufficient
// and exact for every X < 2^DIVIDEND_W and every P >= 2, and r0 < 3P.  All
// three bounds are checked in hardware: a borrow at r0, an r0 that does not
// fit the 3P window, or r0 >= 3P (which is exactly the old "r >= P after the
// subtractions") sets the sticky status_bound_error and fails the beat closed.
// Montgomery reduction is NOT usable here -- it needs an odd modulus, and the
// released primes are used as-is with even table extents, so the reciprocal
// path has to handle an arbitrary modulus.
//
// mu comes from one shared restoring divider that runs NUM_COLS times at
// configuration (RECIP_ITERS steps per column plus a bit-length normalisation
// pass, once per layer) and never runs again: the streaming datapath holds
// initiation interval 1 while it is in service.
//
// ---------------------------------------------------------------------------
// PHYSICAL DESIGN, and why this block is shaped the way it is.  An earlier
// revision of this file was functionally identical and closed at 22.8 MHz on
// ASAP7 (critical path 43.80 ns, 14,425 violating paths).  The three causes,
// each MEASURED from the mapped netlist and its OpenSTA report rather than
// guessed, and each fixed structurally here:
//
//   1 RESET FANOUT.  The worst path was rst_n -> INVx1 -> NOR2x1 -> a flop's
//     D mux: four cells, 40.7 ns of them, because ASAP7's RVT sequential cells
//     have no reset pin, so `if (!rst_n)` becomes gate logic on the D input of
//     every flop it covers, and one x1 inverter was driving 5,521 of them.
//     A DELAY LINE DOES NOT NEED A RESET: a beat's result is a function of
//     that beat's own operands.  So reset covers the CONTROL state only --
//     valid bits, refusal codes, order/head, the credit counter, the
//     configuration scalars and state machine, the FIFO occupancy and the
//     output handshake -- and nothing else.  The operand tables need none
//     either: cfg_done gates admission and is only raised after a derivation
//     has written every column.
//
//   1a RESET DISTRIBUTION.  With the datapath resets gone the reset net still
//     carried 496 loads and still owned the critical path at 3.0 ns, because
//     the control state it does cover is a 32-stage delay line.  So rst_n is
//     redistributed as a CHAIN of registered copies, one per region, described
//     at rst_chain_n below.
//
//   1b REGISTER ENABLES, which are the same disease.  With no enable pin and
//     no clock gate to use, `if (en) bank <= value` becomes a feedback mux on
//     every bit of the bank, so a write enable drives as many cells as the
//     bank is WIDE -- and a COMBINATIONAL enable is something the mapper may
//     dissolve into those muxes rather than keep as one shared gate.  That is
//     how `rc_state == RC_STORE` came to drive 1,734 cells (24 columns x 72
//     bits) and a configuration write decode 974.  Every wide bank here is
//     therefore enabled by a REGISTERED one-hot strobe, which the mapper
//     cannot dissolve and which covers one entry's width; the output buffer
//     needs no enable at all (see FIFO_DEPTH).
//
//   2 WIDE ARRAY READS ADDRESSED BY AN INDEX.  A 24-entry x 136-bit column
//     read and a 29-entry x 153-bit FIFO read compile to mux trees whose
//     SELECT nets drove 1,000 to 2,100 cells each.  Both reads are now ONE-HOT
//     AND-OR: the select is a registered one-hot, so a select line drives only
//     as many cells as the read is wide, and the reduction is a $reduce_or
//     tree, not a chain.  The configuration write decode, the derivation's
//     own column read and the FIFO write decode are one-hot for the same
//     reason.
//
//   3 CARRY-PROPAGATE WIDTH.  On ASAP7 a 33-bit add costs 0.89 ns, a 65-bit
//     add 1.53 ns and a 73-bit add 1.60 ns (measured, registered end to end).
//     So no stage here holds more than one carry chain, and no chain is wider
//     than it has to be: the digit-serial multipliers keep a carry-save
//     accumulator and resolve it once, in halves (see ot_a3_ngram_mul_pipe);
//     the Barrett residue correction runs at RED_W = MOD_W+2 bits, which is
//     all the 3P window needs, instead of the full dividend width; the
//     X - qhat*P subtraction is split into its low RED_W bits and a high half
//     that only has to prove it is zero; and the configuration path's
//     bit-length scan, which was a MOD_W-deep priority chain, is now one
//     shift-and-count state.
//
// STAGE MAP (each arrow is one register boundary, ST_* are localparams):
//
//   ST_IN    input capture, order/head predicates
//   ST_SUB   sticky look-back blocking, pad substitution, id-extent predicate
//   ST_MUL1  ORDER_MAX pipelined id x multiplier products (MUL1_STEPS stages)
//   ST_FOLD  XOR fold over the j < order products, DIVIDEND_W extent predicate
//   ST_COL   one-hot column select, from the order and the head
//   ST_TAB   column read: prime, offset, mu, np, column validity
//   ST_SHIFT Xh = X >> (np-1)
//   ST_MUL2  Xh * mu (MUL2_STEPS stages)
//   ST_QH    qhat = (Xh*mu) >> (DIVIDEND_W+1)
//   ST_MUL3  qhat * prime (MUL3_STEPS stages)
//   ST_R0    low RED_W bits of r0 = X - qhat*prime, and their borrow
//   ST_R0H   the high half of that subtraction: it must come out zero
//   ST_RED   r = r0 - k*prime, k in {0,1,2}; bound check
//   +2       row = r + offset into the elastic output buffer, then out_valid
//
// ELASTICITY.  in_valid/in_ready and out_valid/out_ready are both registered
// boundaries.  The datapath itself never stalls -- it is a fixed-length shift
// register -- so admission is credit-controlled: a beat is accepted only while
// the number of beats between in_ready and out_ready is below the output
// buffer depth (FIFO_DEPTH = LATENCY + 2), which is why a consumer may stall
// for any number of cycles without a dropped or duplicated row id, and why
// in_ready stays asserted for an unbroken full-rate burst.
//
// FAIL-CLOSED.  out_refuse is nonzero and out_row is forced to zero rather
// than emitting a row id the model did not ask for:
//
//   1 ORDER_RANGE     in_order outside [ORDER_MIN, ORDER_MAX]
//   2 HEAD_RANGE      in_head >= NUM_HEADS (unreachable when NUM_HEADS is a
//                     power of two, since HEAD_W then admits no such value)
//   3 ID_EXTENT       a used look-back's id >= the configured extent
//   4 PRODUCT_EXTENT  a used product reaches 2^DIVIDEND_W
//   5 COLUMN          the column or the configuration is invalid
//   6 BOUND           the Barrett bound failed (also sticky in status)
//
// SCOPE.  This block computes row ids.  It does not read a row (that is
// TENSOR.EMBED_LOOKUP), gate anything (VECTOR.ENGRAM_GATE), compress a token
// id (the vendor's tokenizer-derived map is upstream data), or decide which
// look-back is blocked (the sequence layer supplies in_blocked; this block only
// applies the pinned STICKY rule to it).
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Digit-serial pipelined unsigned multiplier.  STEPS = ceil(B_W/DIGIT_W) digit
// stages plus TAIL = 2 resolve stages, initiation interval 1, no handshake: it
// is a delay line, so the enclosing block's credit control is the only
// admission gate, and it needs no reset -- a beat's result is a function of
// that beat's own operands, never of what the line held before it.
//
// WHY CARRY-SAVE.  A digit stage that evaluates acc + a*digit as a binary add
// carries a (A_W + DIGIT_W)-bit carry chain, and on ASAP7 a 73-bit
// carry-propagate add costs about 1.6 ns by itself -- which is why the binary
// form of this multiplier measured 161 MHz at A_W=65, B_W=63.  Here the
// accumulator is kept REDUNDANT as (s, c) with acc = s + c, a digit's partial
// products are folded in one carry-save (full-adder) level at a time, and the
// only carry-propagate inside a digit stage is DIGIT_W bits wide: the low
// DIGIT_W bits, which are finished and shifted out.  One binary add of the
// redundant pair remains -- once per multiply instead of once per digit -- and
// the TAIL splits even that into halves.
//
// Step invariant, as in the binary form: acc <= 2**A_W - 1 before a step, so
// s + c < 2**(A_W + DIGIT_W) at every carry-save level, each of s and c fits
// in A_W + DIGIT_W bits, and CS_W = A_W + DIGIT_W + 1 holds both with a bit to
// spare.  Verified against the exact product for (A_W, B_W, DIGIT_W) including
// 48x32x8, 65x63x8, 48x32x1, 17x13x3, 65x63x5 and 33x7x16.
// ---------------------------------------------------------------------------
module ot_a3_ngram_mul_pipe #(
    parameter integer A_W     = 48,
    parameter integer B_W     = 32,
    parameter integer DIGIT_W = 8
) (
    input  wire                clk,
    input  wire [A_W-1:0]      a,
    input  wire [B_W-1:0]      b,
    output wire [A_W+B_W-1:0]  p
);
    localparam integer STEPS = (B_W + DIGIT_W - 1) / DIGIT_W;
    localparam integer LOW_W = STEPS * DIGIT_W;
    //: b padded to a whole number of digits, so a step's digit slice exists
    //: whatever DIGIT_W is set to.
    localparam integer BX_W  = LOW_W;
    localparam integer CS_W  = A_W + DIGIT_W + 1;
    localparam integer RES_W = CS_W + LOW_W;
    //: Halves of the final carry-propagate resolve, so the widest carry chain
    //: in this module is ceil(CS_W/2) bits and not CS_W.
    localparam integer LO_W  = (CS_W + 1) / 2;
    localparam integer HI_W  = CS_W - LO_W;

    reg [A_W-1:0]   a_r   [0:STEPS-1];
    reg [BX_W-1:0]  b_r   [0:STEPS-1];
    reg [CS_W-1:0]  s_r   [0:STEPS-1];
    reg [CS_W-1:0]  c_r   [0:STEPS-1];
    reg [LOW_W-1:0] low_r [0:STEPS-1];

    wire [BX_W-1:0] b_ext = b;

    genvar s, i;
    generate
        for (s = 0; s < STEPS; s = s + 1) begin : g_step
            wire [A_W-1:0]     a_in   = (s == 0) ? a             : a_r[s-1];
            wire [BX_W-1:0]    b_in   = (s == 0) ? b_ext         : b_r[s-1];
            wire [CS_W-1:0]    s_in   = (s == 0) ? {CS_W{1'b0}}  : s_r[s-1];
            wire [CS_W-1:0]    c_in   = (s == 0) ? {CS_W{1'b0}}  : c_r[s-1];
            wire [LOW_W-1:0]   low_in = (s == 0) ? {LOW_W{1'b0}} : low_r[s-1];
            wire [DIGIT_W-1:0] digit  = b_in[DIGIT_W-1:0];

            //: One carry-save level per digit bit: lvl_s[i] + lvl_c[i] is
            //: exactly acc plus the partial products already folded in.
            wire [CS_W-1:0] lvl_s [0:DIGIT_W];
            wire [CS_W-1:0] lvl_c [0:DIGIT_W];
            assign lvl_s[0] = s_in;
            assign lvl_c[0] = c_in;
            for (i = 0; i < DIGIT_W; i = i + 1) begin : g_csa
                wire [CS_W-1:0] wide = a_in;
                wire [CS_W-1:0] term = digit[i] ? (wide << i) : {CS_W{1'b0}};
                assign lvl_s[i+1] = lvl_s[i] ^ lvl_c[i] ^ term;
                assign lvl_c[i+1] = ((lvl_s[i] & lvl_c[i]) | (lvl_s[i] & term) |
                                     (lvl_c[i] & term)) << 1;
            end

            //: The low DIGIT_W bits are finished: resolve them with a DIGIT_W
            //: wide add, shift them out, and fold that add's carry back into
            //: the redundant accumulator as one more carry-save term.
            wire [DIGIT_W:0] low_add   = lvl_s[DIGIT_W][DIGIT_W-1:0] +
                                         lvl_c[DIGIT_W][DIGIT_W-1:0];
            wire [LOW_W-1:0] digit_out = low_add[DIGIT_W-1:0];
            wire [LOW_W-1:0] low_next  = low_in | (digit_out << (s * DIGIT_W));
            wire [CS_W-1:0]  hi_s  = lvl_s[DIGIT_W] >> DIGIT_W;
            wire [CS_W-1:0]  hi_c  = lvl_c[DIGIT_W] >> DIGIT_W;
            wire [CS_W-1:0]  hi_k  = {{(CS_W-1){1'b0}}, low_add[DIGIT_W]};
            wire [CS_W-1:0]  nxt_s = hi_s ^ hi_c ^ hi_k;
            wire [CS_W-1:0]  nxt_c = ((hi_s & hi_c) | (hi_s & hi_k) |
                                      (hi_c & hi_k)) << 1;

            always @(posedge clk) begin
                a_r[s]   <= a_in;
                b_r[s]   <= b_in >> DIGIT_W;
                s_r[s]   <= nxt_s;
                c_r[s]   <= nxt_c;
                low_r[s] <= low_next;
            end
        end
    endgenerate

    // ---- TAIL: resolve s + c, one half per stage ----
    wire [LO_W:0]   tail_lo = {1'b0, s_r[STEPS-1][LO_W-1:0]} +
                              {1'b0, c_r[STEPS-1][LO_W-1:0]};
    wire [HI_W-1:0] tail_hs = s_r[STEPS-1] >> LO_W;
    wire [HI_W-1:0] tail_hc = c_r[STEPS-1] >> LO_W;

    reg [LO_W-1:0]  t1_lo;
    reg             t1_carry;
    reg [HI_W-1:0]  t1_hs;
    reg [HI_W-1:0]  t1_hc;
    reg [LOW_W-1:0] t1_low;
    reg [LO_W-1:0]  t2_lo;
    reg [HI_W-1:0]  t2_hi;
    reg [LOW_W-1:0] t2_low;

    always @(posedge clk) begin
        t1_lo    <= tail_lo[LO_W-1:0];
        t1_carry <= tail_lo[LO_W];
        t1_hs    <= tail_hs;
        t1_hc    <= tail_hc;
        t1_low   <= low_r[STEPS-1];
        t2_lo    <= t1_lo;
        t2_hi    <= t1_hs + t1_hc + {{(HI_W-1){1'b0}}, t1_carry};
        t2_low   <= t1_low;
    end

    wire [RES_W-1:0] acc_final = {t2_hi, t2_lo};
    wire [RES_W-1:0] result    = (acc_final << LOW_W) | t2_low;
    assign p = result[A_W+B_W-1:0];
endmodule


module ot_a3_dma_ngram_hash #(
    //: Compressed token id width.  The ABI carries ids as u32; the V4.1
    //: compressed vocabulary needs 17 bits, and its extent is an operand.
    parameter integer ID_W        = 32,
    //: Per-lookback hash multiplier width.  The released multipliers are odd
    //: and bounded by (2**63-1)/compressed_vocab_size, so 47 bits; 48 is the
    //: default and every product is checked against DIVIDEND_W at run time.
    parameter integer MULT_W      = 48,
    //: Column modulus width.  The released column primes are 24 bits; MOD_W 32
    //: admits a modulus up to 2**32-1, which the campaign exercises.
    parameter integer MOD_W       = 32,
    //: Row id and table-extent width.
    parameter integer ROW_W       = 32,
    //: Exactness window of the fold, from the pinned int64 product bound.
    parameter integer DIVIDEND_W  = 63,
    //: engram_max_ngram_size, and the smallest order the layout has a prime
    //: row for (the first fold is a 2-gram).
    parameter integer ORDER_MAX   = 4,
    parameter integer ORDER_MIN   = 2,
    //: engram_n_heads.
    parameter integer NUM_HEADS   = 8,
    //: Digits per multiplier stage: stage count against carry-save levels.
    parameter integer MUL_DIGIT_W = 8,
    //: Opaque tag returned with the row id, for the caller's ordering.
    parameter integer TAG_W       = 16
) (
    input  wire                        clk,
    input  wire                        rst_n,

    // ---------------- configuration (operands, not constants) -------------
    //: One write per cycle, accepted only while the datapath is drained and no
    //: derivation is running; a write at any other time sets cfg_error.
    input  wire                        cfg_we,
    input  wire [3:0]                  cfg_kind,
    input  wire [15:0]                 cfg_index,
    input  wire [63:0]                 cfg_data,
    //: Derive np and mu for every column, then raise cfg_done.
    input  wire                        cfg_start,
    output reg                         cfg_busy,
    output reg                         cfg_done,
    output reg                         cfg_error,
    output reg  [3:0]                  cfg_error_code,

    // ---------------- n-gram stream ---------------------------------------
    input  wire                        in_valid,
    output wire                        in_ready,
    //: Look-back j at bits [j*ID_W +: ID_W]; j = 0 is the position itself.
    input  wire [ORDER_MAX*ID_W-1:0]   in_ids,
    //: Raw per-lookback blocking (sequence start, or a DEAD span).  The pinned
    //: STICKY rule is applied here, not by the caller.
    input  wire [ORDER_MAX-1:0]        in_blocked,
    input  wire [$clog2(ORDER_MAX+1)-1:0] in_order,
    input  wire [($clog2(NUM_HEADS) > 0 ? $clog2(NUM_HEADS) : 1)-1:0] in_head,
    input  wire [TAG_W-1:0]            in_tag,

    output reg                         out_valid,
    input  wire                        out_ready,
    //: Registered, like out_valid: these are slices of the output buffer's
    //: registered read word, wired out.
    output wire [ROW_W-1:0]            out_row,
    output wire [3:0]                  out_refuse,
    output wire [TAG_W-1:0]            out_tag,
    output wire [$clog2(ORDER_MAX+1)-1:0] out_order,
    output wire [($clog2(NUM_HEADS) > 0 ? $clog2(NUM_HEADS) : 1)-1:0] out_head,
    //: Observability, checked by the bench against the reference: the folded
    //: dividend, and the residue before the column offset is added.
    output wire [DIVIDEND_W-1:0]       out_dividend,
    output wire [MOD_W-1:0]            out_residue,

    // ---------------- status ----------------------------------------------
    output wire [15:0]                 info_pipe_stages,
    output wire [15:0]                 info_num_columns,
    output reg                         status_bound_error
);
    // ---------------- derived geometry ------------------------------------
    localparam integer ORDER_W     = $clog2(ORDER_MAX+1);
    localparam integer HEAD_W      = ($clog2(NUM_HEADS) > 0) ? $clog2(NUM_HEADS) : 1;
    localparam integer NUM_ORDERS  = ORDER_MAX - ORDER_MIN + 1;
    localparam integer NUM_COLS    = NUM_ORDERS * NUM_HEADS;
    localparam integer COL_W       = ($clog2(NUM_COLS) > 0) ? $clog2(NUM_COLS) : 1;
    localparam integer PROD_W      = MULT_W + ID_W;
    localparam integer FOLD_W      = (PROD_W > DIVIDEND_W) ? PROD_W : DIVIDEND_W;
    localparam integer MU_W        = DIVIDEND_W + 2;
    localparam integer QH_W        = DIVIDEND_W + 1;
    localparam integer NP_W        = $clog2(MOD_W+1);
    //: Register stages of one ot_a3_ngram_mul_pipe: ceil(B_W/MUL_DIGIT_W)
    //: digit stages plus MUL_TAIL stages that resolve the carry-save
    //: accumulator.  The module derives its own depth from the same
    //: parameters; if these two ever disagree the data arrives misaligned
    //: against the control delay line and the bench's value checks fail.
    localparam integer MUL_TAIL    = 2;
    localparam integer MUL1_STEPS  = ((ID_W + MUL_DIGIT_W - 1) / MUL_DIGIT_W) + MUL_TAIL;
    localparam integer MUL2_STEPS  = ((DIVIDEND_W + MUL_DIGIT_W - 1) / MUL_DIGIT_W) + MUL_TAIL;
    localparam integer MUL3_STEPS  = ((MOD_W + MUL_DIGIT_W - 1) / MUL_DIGIT_W) + MUL_TAIL;
    localparam integer RECIP_ITERS = MOD_W + DIVIDEND_W + 1;
    localparam integer ITER_W      = $clog2(RECIP_ITERS+1);
    //: Width of the residue correction.  r0 < 3P <= 3*(2**MOD_W - 1), so
    //: MOD_W+2 bits hold every r0 the Barrett bound admits, and an r0 that
    //: does not fit is a bound failure by definition.
    localparam integer RED_W       = MOD_W + 2;
    //: The X - qhat*P subtraction, split at RED_W: the low half produces the
    //: residue window, the high half only has to prove it is zero.
    localparam integer WIDE_W      = ((DIVIDEND_W + 2) > (RED_W + 1)) ?
                                     (DIVIDEND_W + 2) : (RED_W + 1);
    localparam integer SUBHI_W     = WIDE_W - RED_W;
    //: The column operand word, read as one one-hot AND-OR per beat.
    localparam integer TF_PRIME    = 0;
    localparam integer TF_OFFSET   = TF_PRIME + MOD_W;
    localparam integer TF_MU       = TF_OFFSET + ROW_W;
    localparam integer TF_NP       = TF_MU + MU_W;
    localparam integer TF_VALID    = TF_NP + NP_W;
    localparam integer TAB_W       = TF_VALID + 1;
    //: And the derivation's own (prime, offset) read.
    localparam integer RF_PRIME    = 0;
    localparam integer RF_OFFSET   = RF_PRIME + MOD_W;
    localparam integer RCRD_W      = RF_OFFSET + ROW_W;
    localparam integer END_W       = ((MOD_W > ROW_W) ? MOD_W : ROW_W) + 1;

    localparam integer ST_IN    = 1;
    localparam integer ST_SUB   = ST_IN + 1;
    localparam integer ST_MUL1  = ST_SUB + MUL1_STEPS;
    localparam integer ST_FOLD  = ST_MUL1 + 1;
    localparam integer ST_COL   = ST_FOLD + 1;
    localparam integer ST_TAB   = ST_COL + 1;
    localparam integer ST_SHIFT = ST_TAB + 1;
    localparam integer ST_MUL2  = ST_SHIFT + MUL2_STEPS;
    localparam integer ST_QH    = ST_MUL2 + 1;
    localparam integer ST_MUL3  = ST_QH + MUL3_STEPS;
    localparam integer ST_R0    = ST_MUL3 + 1;
    localparam integer ST_R0H   = ST_R0 + 1;
    localparam integer ST_RED   = ST_R0H + 1;
    //: ST_RED, then the buffer write, then the registered output boundary.
    localparam integer LATENCY    = ST_RED + 2;
    //: Admission credit: every beat between in_ready and out_ready.
    localparam integer CREDIT_MAX = LATENCY + 2;
    //: The buffer carries ONE more entry than the credit allows, which makes
    //: the write unconditional: the entry wr_hot points at is rewritten every
    //: cycle and only frozen by wr_hot advancing, which happens on a push.  The
    //: spare entry is what proves the write and the read can never be the same
    //: entry (fifo_count <= credit <= FIFO_DEPTH-1), and it buys the output
    //: buffer out of needing a PAY_W-wide write enable at all.
    localparam integer FIFO_DEPTH = CREDIT_MAX + 1;
    localparam integer CNT_W      = $clog2(FIFO_DEPTH+1);
    localparam integer PAY_W      = ROW_W + 4 + TAG_W + ORDER_W + HEAD_W +
                                    MOD_W + DIVIDEND_W;
    //: Payload field bases, so one concatenation and one extraction cannot
    //: drift apart.
    localparam integer PF_DIV = 0;
    localparam integer PF_RES = PF_DIV + DIVIDEND_W;
    localparam integer PF_HEAD = PF_RES + MOD_W;
    localparam integer PF_ORDER = PF_HEAD + HEAD_W;
    localparam integer PF_TAG = PF_ORDER + ORDER_W;
    localparam integer PF_REF = PF_TAG + TAG_W;
    localparam integer PF_ROW = PF_REF + 4;
    //: Banks of the output buffer.  Each control net of a bank drives one
    //: bank's width, so BANKS trades the fanout of a bank's position,
    //: occupancy and output enable (which falls as 2*PAY_W/BANKS) against the
    //: fanout of push, which every bank's position and occupancy register
    //: listens to (and which rises as 2*BANKS*FIFO_DEPTH).  Measured on ASAP7
    //: at PAY_W=153, FIFO_DEPTH=37: the unbanked form measured 1.64 ns, and
    //: banked, BANKS=2 gives 1.23 ns, 3 gives 1.45 ns and 4 gives 1.90 ns, so
    //: two is the balance point.
    localparam integer BANKS  = 2;
    localparam integer BANK_W = (PAY_W + BANKS - 1) / BANKS;
    localparam integer MEM_W  = BANKS * BANK_W;

    localparam [3:0] RFC_NONE = 4'd0, RFC_ORDER = 4'd1, RFC_HEAD = 4'd2,
                     RFC_ID = 4'd3, RFC_PRODUCT = 4'd4, RFC_COLUMN = 4'd5,
                     RFC_BOUND = 4'd6;
    localparam [3:0] CFG_KIND_ROWS = 4'd0, CFG_KIND_PAD = 4'd1,
                     CFG_KIND_VOCAB = 4'd2, CFG_KIND_MULT = 4'd3,
                     CFG_KIND_PRIME = 4'd4, CFG_KIND_OFFSET = 4'd5;
    localparam [3:0] CE_NONE = 4'd0, CE_WRITE_ACTIVE = 4'd1, CE_KIND = 4'd2,
                     CE_INDEX = 4'd3, CE_SCALAR = 4'd4, CE_COLUMN = 4'd5,
                     CE_RECIP = 4'd6, CE_START_ACTIVE = 4'd7;

    assign info_pipe_stages = LATENCY[15:0];
    assign info_num_columns = NUM_COLS[15:0];

    genvar c, e, i, j, st;

    // =====================================================================
    // RESET DISTRIBUTION.  ASAP7's RVT flops have no reset pin and its clock
    // gates are dont_use, so a reset is gate logic on the D input of every flop
    // it covers: the net carries one load per covered BIT, and a 496-load reset
    // measured 3.0 ns on this block -- its critical path, once the datapath
    // resets were gone.  rst_n therefore arrives as a CHAIN of registered
    // copies, one per region below, each driving about a hundred loads.  They
    // are registers rather than buffers so that nothing -- not opt_merge, not
    // ABC's sequential sweep -- can collapse them back into one net, and they
    // are ANDed with rst_n rather than merely chained so that EVERY copy
    // asserts within one cycle of rst_n going low.
    //
    // Release is staggered by one cycle per copy, and the ORDER is chosen by
    // what a caller may touch first: RST_CFG covers the whole configuration
    // port, which is live in the first cycle after it releases, so it goes
    // first.  Everything downstream of it is safe arbitrarily late, because the
    // streaming side cannot move until cfg_done rises, and cfg_done needs a
    // whole derivation -- thousands of cycles -- after a cfg_start that itself
    // follows the operand writes.  While a region is still held its state reads
    // as its reset value, so an early region never sees a live neighbour's
    // garbage: it sees zero.
    //
    // The only requirement this places on a caller is the usual one for a
    // synchronous reset: hold rst_n low for at least two clock edges.
    // =====================================================================
    localparam integer RST_CFG    = 0;  // the whole configuration port
    localparam integer RST_PIPE   = 1;  // credit, occupancy, valid, status
    localparam integer RST_REF    = 2;  // refusal codes of the delay line
    localparam integer RST_ORD    = 3;  // order of the delay line
    localparam integer RST_HEAD   = 4;  // head of the delay line
    localparam integer RST_BANK   = 5;  // one per output-buffer bank
    localparam integer RST_COPIES = RST_BANK + BANKS;

    reg [RST_COPIES-1:0] rst_chain_n;
    always @(posedge clk)
        rst_chain_n <= rst_n ? {rst_chain_n[RST_COPIES-2:0], 1'b1}
                             : {RST_COPIES{1'b0}};

    // =====================================================================
    // Credit control.  The datapath is a fixed-length shift register, so an
    // accepted beat always reaches the output buffer; admission is gated on a
    // free buffer slot instead of stalling the pipeline, which is what holds
    // the initiation interval at one.
    // =====================================================================
    reg  [CNT_W-1:0] credit;
    wire             in_ready_w;
    wire             accept = in_valid && in_ready_w;
    wire             pop    = out_valid && out_ready;
    wire             pipeline_drained = (credit == {CNT_W{1'b0}});

    // =====================================================================
    // Configuration store.  Everything the datapath computes with lives here
    // and arrives as an operand.  Only the scalars are reset: the per-column
    // tables cannot be observed before cfg_done, which a derivation raises
    // only after it has written every column.
    // =====================================================================
    reg [ROW_W-1:0]  cfg_rows;
    reg [ID_W-1:0]   cfg_pad;
    reg [ID_W-1:0]   cfg_vocab;
    //: One presence bit per scalar operand.  These are reset, the scalars
    //: themselves are not: an unwritten scalar is refused because it was never
    //: written, which is a stronger statement than refusing it because reset
    //: left it at zero -- and it keeps 96 bits out of the reset's fanout.
    reg [2:0]        cfg_seen;
    reg              cfg_scalar_ok;
    reg [MULT_W-1:0] cfg_mult   [0:ORDER_MAX-1];
    reg [MOD_W-1:0]  cfg_prime  [0:NUM_COLS-1];
    reg [ROW_W-1:0]  cfg_offset [0:NUM_COLS-1];
    reg [MU_W-1:0]   cfg_mu     [0:NUM_COLS-1];
    reg [NP_W-1:0]   cfg_np     [0:NUM_COLS-1];
    reg              cfg_colv   [0:NUM_COLS-1];

    // ---- reciprocal derivation state ----
    localparam [2:0] RC_IDLE = 3'd0, RC_WAIT = 3'd1, RC_PREP = 3'd2,
                     RC_NORM = 3'd3, RC_DIV = 3'd4, RC_STORE = 3'd5;

    reg [2:0]            rc_state;
    reg [NUM_COLS-1:0]   rc_hot;
    reg [ITER_W-1:0]     rc_iter;
    reg [ITER_W-1:0]     rc_total;
    reg [MOD_W:0]        rc_rem;
    reg [MU_W-1:0]       rc_q;
    reg [MOD_W-1:0]      rc_prime;
    reg [MOD_W-1:0]      rc_norm;
    reg [END_W-1:0]      rc_end;
    reg [NP_W-1:0]       rc_np;
    reg                  rc_valid;
    //: Registered store strobe: one hot bit, and only in the store cycle, so
    //: the mu/np/valid write enable is never a signal shared by every column.
    reg [NUM_COLS-1:0]   rc_wr_hot;

    //: The derivation reads its column through the same one-hot discipline as
    //: the datapath: a select line drives the width of the read, not a mux
    //: tree level.
    wire [RCRD_W-1:0] rc_word [0:NUM_COLS-1];
    wire [RCRD_W-1:0] rc_rd;
    generate
        for (c = 0; c < NUM_COLS; c = c + 1) begin : g_rc_word
            assign rc_word[c] = {cfg_offset[c], cfg_prime[c]};
        end
        for (i = 0; i < RCRD_W; i = i + 1) begin : g_rc_rd
            wire [NUM_COLS-1:0] bits;
            for (c = 0; c < NUM_COLS; c = c + 1) begin : g_rc_bit
                assign bits[c] = rc_hot[c] && rc_word[c][i];
            end
            assign rc_rd[i] = |bits;
        end
    endgenerate
    wire [MOD_W-1:0] rc_prime_rd  = rc_rd[RF_PRIME  +: MOD_W];
    wire [ROW_W-1:0] rc_offset_rd = rc_rd[RF_OFFSET +: ROW_W];

    wire [MOD_W:0]   rc_rem_shift = {rc_rem[MOD_W-1:0], (rc_iter == {ITER_W{1'b0}})};
    wire [MOD_W:0]   rc_prime_ext = rc_prime;
    //: One restoring-division step is one subtraction: its borrow IS the
    //: comparison, so the step holds a single carry chain.
    wire [MOD_W+1:0] rc_diff      = {1'b0, rc_rem_shift} - {1'b0, rc_prime_ext};
    wire             rc_ge        = ~rc_diff[MOD_W+1];
    wire [END_W-1:0] rc_end_next  = {{(END_W-ROW_W){1'b0}}, rc_offset_rd} +
                                    {{(END_W-MOD_W){1'b0}}, rc_prime_rd};
    wire [END_W-1:0] rc_rows_ext  = cfg_rows;
    wire             rc_last      = rc_hot[NUM_COLS-1];

    // ---- operand table writes: registered one-hot strobes, never reset ----
    //: A write takes effect one cycle after it is accepted, because the strobe
    //: that enables the entry is a REGISTER: an enable is a mux select on every
    //: bit of the entry, and only a registered one is safe from being dissolved
    //: into them.  The refusal of a bad or ill-timed write is still reported in
    //: the cycle of the write itself, below.
    wire cfg_write_ok = cfg_we && !cfg_busy && pipeline_drained;
    wire cfg_wr_prime  = cfg_write_ok && (cfg_kind == CFG_KIND_PRIME);
    wire cfg_wr_offset = cfg_write_ok && (cfg_kind == CFG_KIND_OFFSET);
    wire cfg_wr_mult   = cfg_write_ok && (cfg_kind == CFG_KIND_MULT);

    reg  [63:0]          cfgw_data;
    reg  [NUM_COLS-1:0]  cfgw_prime;
    reg  [NUM_COLS-1:0]  cfgw_offset;
    reg  [ORDER_MAX-1:0] cfgw_mult;
    wire [NUM_COLS-1:0]  cfg_col_hot;
    wire [ORDER_MAX-1:0] cfg_mult_hot;

    generate
        for (c = 0; c < NUM_COLS; c = c + 1) begin : g_cfg_col_hot
            assign cfg_col_hot[c] = (cfg_index == c);
        end
        for (j = 0; j < ORDER_MAX; j = j + 1) begin : g_cfg_mult_hot
            assign cfg_mult_hot[j] = (cfg_index == j);
        end
    endgenerate

    always @(posedge clk) begin
        cfgw_data   <= cfg_data;
        cfgw_prime  <= cfg_wr_prime  ? cfg_col_hot  : {NUM_COLS{1'b0}};
        cfgw_offset <= cfg_wr_offset ? cfg_col_hot  : {NUM_COLS{1'b0}};
        cfgw_mult   <= cfg_wr_mult   ? cfg_mult_hot : {ORDER_MAX{1'b0}};
    end

    generate
        for (c = 0; c < NUM_COLS; c = c + 1) begin : g_col_store
            always @(posedge clk) begin
                if (cfgw_prime[c])  cfg_prime[c]  <= cfgw_data[MOD_W-1:0];
                if (cfgw_offset[c]) cfg_offset[c] <= cfgw_data[ROW_W-1:0];
                if (rc_wr_hot[c]) begin
                    cfg_mu[c]   <= rc_q;
                    cfg_np[c]   <= rc_np;
                    cfg_colv[c] <= rc_valid;
                end
            end
        end
        for (j = 0; j < ORDER_MAX; j = j + 1) begin : g_mult_store
            always @(posedge clk)
                if (cfgw_mult[j]) cfg_mult[j] <= cfgw_data[MULT_W-1:0];
        end
    endgenerate

    // ---- configuration scalars ----
    always @(posedge clk) begin
        if (!rst_chain_n[RST_CFG]) cfg_seen <= 3'b000;
        else if (cfg_write_ok) begin
            case (cfg_kind)
                CFG_KIND_ROWS:  begin cfg_rows  <= cfg_data[ROW_W-1:0]; cfg_seen[0] <= 1'b1; end
                CFG_KIND_PAD:   begin cfg_pad   <= cfg_data[ID_W-1:0];  cfg_seen[1] <= 1'b1; end
                CFG_KIND_VOCAB: begin cfg_vocab <= cfg_data[ID_W-1:0];  cfg_seen[2] <= 1'b1; end
                default: ;
            endcase
        end
    end

    // ---- configuration status and the derivation state machine ----
    always @(posedge clk) begin
        if (!rst_chain_n[RST_CFG]) begin
            cfg_scalar_ok  <= 1'b0;
            cfg_busy       <= 1'b0;
            cfg_done       <= 1'b0;
            cfg_error      <= 1'b0;
            cfg_error_code <= CE_NONE;
            rc_state       <= RC_IDLE;
            rc_hot         <= 1'b1;
            rc_iter        <= {ITER_W{1'b0}};
            rc_total       <= {ITER_W{1'b0}};
            rc_valid       <= 1'b0;
            rc_wr_hot      <= {NUM_COLS{1'b0}};
        end else begin
            rc_wr_hot <= {NUM_COLS{1'b0}};

            // ---- operand writes ----
            if (cfg_we) begin
                if (cfg_busy || !pipeline_drained) begin
                    cfg_error      <= 1'b1;
                    cfg_error_code <= CE_WRITE_ACTIVE;
                end else begin
                    //: A write invalidates the derivation: mu has to be
                    //: re-derived before the datapath may run again.
                    cfg_done <= 1'b0;
                    case (cfg_kind)
                        //: The scalar and table writes themselves are elsewhere
                        //: (each in its own reset region); here only a bad kind
                        //: or an out-of-range index has to be reported.
                        CFG_KIND_ROWS, CFG_KIND_PAD, CFG_KIND_VOCAB: ;
                        CFG_KIND_MULT:
                            if (cfg_index >= ORDER_MAX) begin
                                cfg_error      <= 1'b1;
                                cfg_error_code <= CE_INDEX;
                            end
                        CFG_KIND_PRIME, CFG_KIND_OFFSET:
                            if (cfg_index >= NUM_COLS) begin
                                cfg_error      <= 1'b1;
                                cfg_error_code <= CE_INDEX;
                            end
                        default: begin
                            cfg_error      <= 1'b1;
                            cfg_error_code <= CE_KIND;
                        end
                    endcase
                end
            end

            // ---- per-column reciprocal derivation ----
            case (rc_state)
                RC_IDLE: begin
                    if (cfg_start) begin
                        if (!pipeline_drained) begin
                            cfg_error      <= 1'b1;
                            cfg_error_code <= CE_START_ACTIVE;
                        end else begin
                            cfg_busy       <= 1'b1;
                            cfg_done       <= 1'b0;
                            cfg_error      <= 1'b0;
                            cfg_error_code <= CE_NONE;
                            rc_hot         <= 1'b1;
                            //: One idle cycle, so that an operand write in the
                            //: very cycle of cfg_start -- whose registered
                            //: strobe lands one cycle later -- is still in the
                            //: table before the first column is read.
                            rc_state       <= RC_WAIT;
                            //: Scalar operands are checked once, here.  A bad
                            //: scalar refuses every beat; a bad column refuses
                            //: only the beats that select it.
                            if (!(&cfg_seen) || cfg_vocab == {ID_W{1'b0}} ||
                                cfg_pad >= cfg_vocab ||
                                cfg_rows == {ROW_W{1'b0}}) begin
                                cfg_scalar_ok  <= 1'b0;
                                cfg_error      <= 1'b1;
                                cfg_error_code <= CE_SCALAR;
                            end else begin
                                cfg_scalar_ok <= 1'b1;
                            end
                        end
                    end
                end
                RC_WAIT: rc_state <= RC_PREP;
                RC_PREP: begin
                    //: Latch the column's operands.  The bucket end and the
                    //: bit-length scan are separate cycles, so neither shares a
                    //: stage with the other's carry chain.
                    rc_prime <= rc_prime_rd;
                    rc_norm  <= rc_prime_rd;
                    rc_end   <= rc_end_next;
                    rc_np    <= {NP_W{1'b0}};
                    rc_state <= RC_NORM;
                end
                RC_NORM: begin
                    //: np = bit length of P, one shift and one count per cycle.
                    if (|rc_norm) begin
                        rc_norm <= rc_norm >> 1;
                        rc_np   <= rc_np + 1'b1;
                    end else begin
                        rc_rem   <= {(MOD_W+1){1'b0}};
                        rc_q     <= {MU_W{1'b0}};
                        rc_iter  <= {ITER_W{1'b0}};
                        rc_total <= rc_np + DIVIDEND_W[ITER_W-1:0];
                        //: A column is usable only if its modulus is at least
                        //: two and its bucket range ends inside the configured
                        //: table.
                        if (rc_prime < 2 || rc_end > rc_rows_ext) begin
                            rc_valid       <= 1'b0;
                            cfg_error      <= 1'b1;
                            cfg_error_code <= CE_COLUMN;
                            rc_state       <= RC_STORE;
                            rc_wr_hot      <= rc_hot;
                        end else begin
                            rc_valid <= 1'b1;
                            rc_state <= RC_DIV;
                        end
                    end
                end
                RC_DIV: begin
                    //: One restoring-division step of mu = floor(2**(np +
                    //: DIVIDEND_W) / prime): double the remainder, shift in the
                    //: numerator bit (only the first is one), subtract the
                    //: modulus when it fits, shift the quotient bit in.
                    rc_rem  <= rc_ge ? rc_diff[MOD_W:0] : rc_rem_shift;
                    rc_q    <= {rc_q[MU_W-2:0], rc_ge};
                    rc_iter <= rc_iter + 1'b1;
                    if (rc_iter == rc_total) begin
                        rc_state  <= RC_STORE;
                        rc_wr_hot <= rc_hot;
                    end
                end
                RC_STORE: begin
                    //: mu and np are written to the column's table entry by the
                    //: one-hot store above.  mu must land in
                    //: (2**DIVIDEND_W, 2**(DIVIDEND_W+1)]; a derivation that
                    //: does not is a hardware fault, not a bad operand, and is
                    //: reported as one.
                    if (rc_valid && ~|rc_q[MU_W-1:DIVIDEND_W]) begin
                        cfg_error      <= 1'b1;
                        cfg_error_code <= CE_RECIP;
                    end
                    if (rc_last) begin
                        rc_state <= RC_IDLE;
                        cfg_busy <= 1'b0;
                        cfg_done <= 1'b1;
                    end else begin
                        rc_hot   <= rc_hot << 1;
                        rc_state <= RC_PREP;
                    end
                end
                default: rc_state <= RC_IDLE;
            endcase
        end
    end

    assign in_ready_w = cfg_done && !cfg_busy && (credit < CREDIT_MAX[CNT_W-1:0]);
    assign in_ready   = in_ready_w;

    always @(posedge clk) begin
        if (!rst_chain_n[RST_PIPE]) credit <= {CNT_W{1'b0}};
        else if (accept && !pop) credit <= credit + 1'b1;
        else if (pop && !accept) credit <= credit - 1'b1;
    end

    // =====================================================================
    // Control delay line: one uniform shift over the whole datapath, with the
    // refusal code injected at the stage that can detect each cause.  This is
    // the state reset covers -- the valid bit, the refusal code and the order
    // and head that the predicates read -- because it is the only pipeline
    // state whose value before the first beat is observable.
    // =====================================================================
    reg               v_p     [ST_IN:ST_RED];
    reg [ORDER_W-1:0] order_p [ST_IN:ST_RED];
    reg [HEAD_W-1:0]  head_p  [ST_IN:ST_RED];
    reg [3:0]         ref_p   [ST_IN:ST_RED];
    reg [TAG_W-1:0]   tag_p   [ST_IN:ST_RED];
    wire [3:0]        ref_inject [ST_IN:ST_RED];

    generate
        for (st = ST_IN; st <= ST_RED; st = st + 1) begin : g_control
            //: The first nonzero refusal wins, so a later stage cannot mask the
            //: reason a beat failed.
            wire [3:0] prior = (st == ST_IN) ? RFC_NONE : ref_p[(st == ST_IN) ? ST_IN : st-1];
            //: One always block per reset region, so that no region's reset net
            //: carries the whole line's width.
            always @(posedge clk) begin
                if (!rst_chain_n[RST_PIPE]) v_p[st] <= 1'b0;
                else if (st == ST_IN)       v_p[st] <= accept;
                else                        v_p[st] <= v_p[(st == ST_IN) ? ST_IN : st-1];
            end
            always @(posedge clk) begin
                if (!rst_chain_n[RST_REF]) ref_p[st] <= RFC_NONE;
                else if (st == ST_IN)      ref_p[st] <= ref_inject[ST_IN];
                else                       ref_p[st] <= (prior != RFC_NONE) ? prior
                                                                            : ref_inject[st];
            end
            always @(posedge clk) begin
                if (!rst_chain_n[RST_ORD]) order_p[st] <= {ORDER_W{1'b0}};
                else if (st == ST_IN)      order_p[st] <= in_order;
                else                       order_p[st] <= order_p[(st == ST_IN) ? ST_IN : st-1];
            end
            always @(posedge clk) begin
                if (!rst_chain_n[RST_HEAD]) head_p[st] <= {HEAD_W{1'b0}};
                else if (st == ST_IN)       head_p[st] <= in_head;
                else                        head_p[st] <= head_p[(st == ST_IN) ? ST_IN : st-1];
            end
            //: The tag is opaque payload: it reaches nothing but the beat's own
            //: output word, so it is outside the reset.
            always @(posedge clk) begin
                if (st == ST_IN) tag_p[st] <= in_tag;
                else             tag_p[st] <= tag_p[(st == ST_IN) ? ST_IN : st-1];
            end
        end
    endgenerate

    // ---- ST_IN: capture, order and head predicates ----
    reg [ORDER_MAX*ID_W-1:0] ids_s1;
    reg [ORDER_MAX-1:0]      blocked_s1;
    always @(posedge clk) begin
        ids_s1     <= in_ids;
        blocked_s1 <= in_blocked;
    end
    wire [ORDER_W-1:0] order_min_w = ORDER_MIN[ORDER_W-1:0];
    wire [ORDER_W-1:0] order_max_w = ORDER_MAX[ORDER_W-1:0];
    wire [HEAD_W-1:0]  head_max_w  = NUM_HEADS[HEAD_W-1:0];
    wire order_bad = (in_order < order_min_w) || (in_order > order_max_w);
    //: Unreachable when NUM_HEADS is a power of two, because HEAD_W then admits
    //: no out-of-range value.  It is still checked, because NUM_HEADS is a
    //: parameter and a non-power-of-two head count is legal.
    wire head_bad  = (NUM_HEADS < (1 << HEAD_W)) && (in_head >= head_max_w);
    assign ref_inject[ST_IN] = order_bad ? RFC_ORDER : (head_bad ? RFC_HEAD : RFC_NONE);

    // ---- ST_SUB: sticky look-back blocking, pad substitution, id extent ----
    reg  [ID_W-1:0]      tok_s2  [0:ORDER_MAX-1];
    wire [ID_W-1:0]      tok_sel [0:ORDER_MAX-1];
    wire [ORDER_MAX-1:0] sticky;
    wire [ORDER_MAX-1:0] used_s1;
    wire [ORDER_MAX-1:0] id_bad;
    generate
        for (j = 0; j < ORDER_MAX; j = j + 1) begin : g_sub
            //: Sticky rule of the pinned source: once a look-back is blocked,
            //: every deeper look-back of this position is blocked too.  An
            //: ORDER_MAX-wide prefix OR, not a walk over a vector.
            assign sticky[j]  = |blocked_s1[j:0];
            assign tok_sel[j] = sticky[j] ? cfg_pad : ids_s1[j*ID_W +: ID_W];
            //: Only look-backs the order folds are checked, because only those
            //: can reach the result.
            assign used_s1[j] = (j < order_p[ST_IN]);
            assign id_bad[j]  = used_s1[j] && (tok_sel[j] >= cfg_vocab);
        end
    endgenerate
    assign ref_inject[ST_SUB] = (|id_bad) ? RFC_ID : RFC_NONE;

    integer k;
    always @(posedge clk)
        for (k = 0; k < ORDER_MAX; k = k + 1) tok_s2[k] <= tok_sel[k];

    // ---- ST_SUB+1 .. ST_MUL1: the id x multiplier products ----
    wire [PROD_W-1:0] product [0:ORDER_MAX-1];
    generate
        for (j = 0; j < ORDER_MAX; j = j + 1) begin : g_mul1
            ot_a3_ngram_mul_pipe #(
                .A_W(MULT_W), .B_W(ID_W), .DIGIT_W(MUL_DIGIT_W)
            ) u_mul1 (
                .clk(clk), .a(cfg_mult[j]), .b(tok_s2[j]), .p(product[j])
            );
        end
    endgenerate

    // ---- ST_FOLD: XOR fold over the used products, DIVIDEND_W extent ----
    wire [ORDER_MAX-1:0]  used_m1;
    wire [ORDER_MAX-1:0]  over;
    wire [DIVIDEND_W-1:0] term  [0:ORDER_MAX-1];
    wire [DIVIDEND_W-1:0] chain [0:ORDER_MAX-1];
    generate
        for (j = 0; j < ORDER_MAX; j = j + 1) begin : g_fold
            wire [FOLD_W-1:0] wide = product[j];
            assign used_m1[j] = (j < order_p[ST_MUL1]);
            assign over[j]    = used_m1[j] && (|wide[FOLD_W-1:DIVIDEND_W]);
            assign term[j]    = used_m1[j] ? wide[DIVIDEND_W-1:0] : {DIVIDEND_W{1'b0}};
            //: An ORDER_MAX-term XOR, one register boundary, any ORDER_MAX.
            assign chain[j]   = (j == 0) ? term[0] : (chain[(j == 0) ? 0 : j-1] ^ term[j]);
        end
    endgenerate
    assign ref_inject[ST_FOLD] = (|over) ? RFC_PRODUCT : RFC_NONE;
    wire [DIVIDEND_W-1:0] fold_value = chain[ORDER_MAX-1];

    // ---- ST_COL: the one-hot column select ----
    wire [COL_W:0] col_order = order_p[ST_FOLD] - order_min_w;
    wire [COL_W:0] col_index = col_order * NUM_HEADS + head_p[ST_FOLD];
    //: Everything knowable about the column at this boundary is folded into the
    //: select itself, so an unusable column simply selects nothing and the read
    //: below returns zero.
    wire           col_pass  = cfg_done && cfg_scalar_ok && (col_index < NUM_COLS) &&
                               (ref_p[ST_FOLD] == RFC_NONE);
    wire [NUM_COLS-1:0] col_hot_w;
    generate
        for (c = 0; c < NUM_COLS; c = c + 1) begin : g_col_hot
            assign col_hot_w[c] = col_pass && (col_index == c);
        end
    endgenerate
    reg [NUM_COLS-1:0] col_hot_p;
    always @(posedge clk) col_hot_p <= col_hot_w;

    // ---- ST_TAB: the column read, one-hot AND-OR ----
    wire [TAB_W-1:0] col_word [0:NUM_COLS-1];
    wire [TAB_W-1:0] col_rd;
    generate
        for (c = 0; c < NUM_COLS; c = c + 1) begin : g_col_word
            assign col_word[c] = {cfg_colv[c], cfg_np[c], cfg_mu[c],
                                  cfg_offset[c], cfg_prime[c]};
        end
        for (i = 0; i < TAB_W; i = i + 1) begin : g_col_rd
            wire [NUM_COLS-1:0] bits;
            for (c = 0; c < NUM_COLS; c = c + 1) begin : g_col_bit
                assign bits[c] = col_hot_p[c] && col_word[c][i];
            end
            assign col_rd[i] = |bits;
        end
    endgenerate
    wire [MOD_W-1:0] prime_rd  = col_rd[TF_PRIME  +: MOD_W];
    wire [ROW_W-1:0] offset_rd = col_rd[TF_OFFSET +: ROW_W];
    wire [MU_W-1:0]  mu_rd     = col_rd[TF_MU     +: MU_W];
    wire [NP_W-1:0]  np_rd     = col_rd[TF_NP     +: NP_W];
    wire             col_valid = col_rd[TF_VALID];
    assign ref_inject[ST_TAB] = col_valid ? RFC_NONE : RFC_COLUMN;

    // =====================================================================
    // Barrett reduction datapath.  Every value below is per-beat pipeline
    // state: a delay line, so none of it is reset.
    // =====================================================================
    reg [DIVIDEND_W-1:0] x_p      [ST_FOLD:ST_RED];
    reg [MOD_W-1:0]      prime_p  [ST_TAB:ST_R0H];
    reg [ROW_W-1:0]      offset_p [ST_TAB:ST_RED];
    reg [MU_W-1:0]       mu_p     [ST_TAB:ST_SHIFT];
    reg [NP_W-1:0]       np_m1_p;
    reg [DIVIDEND_W-1:0] xh_p;
    reg [QH_W-1:0]       qh_p;
    reg [RED_W-1:0]      r0_lo_p;
    reg                  r0_borrow_p;
    reg [SUBHI_W-1:0]    x_hi_p;
    reg [SUBHI_W-1:0]    rp_hi_p;
    reg                  rp_over_p;
    reg [RED_W-1:0]      r0_p;
    reg                  r0_bad_p;
    reg [RED_W-1:0]      prime3_p;
    reg [MOD_W-1:0]      r_p;

    wire [MU_W+DIVIDEND_W-1:0] qprod;
    wire [QH_W+MOD_W-1:0]      rprod;

    // ---- ST_R0: the low half of X - qhat*prime ----
    wire [WIDE_W-1:0] x_wide  = x_p[ST_MUL3];
    wire [WIDE_W-1:0] rp_wide = rprod;
    //: qhat*prime cannot leave the dividend window; that it does is a bound
    //: failure, detected here rather than wrapped.
    wire              rp_over = |(rprod >> (DIVIDEND_W + 1));
    wire [RED_W:0]    sub_lo  = {1'b0, x_wide[RED_W-1:0]} - {1'b0, rp_wide[RED_W-1:0]};
    wire [SUBHI_W-1:0] x_hi_w  = x_wide  >> RED_W;
    wire [SUBHI_W-1:0] rp_hi_w = rp_wide >> RED_W;

    // ---- ST_R0H: the high half must come out exactly zero ----
    wire [SUBHI_W:0] sub_hi = {1'b0, x_hi_p} - {1'b0, rp_hi_p} -
                              {{SUBHI_W{1'b0}}, r0_borrow_p};

    // ---- ST_RED: r0 - k*prime, k in {0,1,2}, by three parallel borrows ----
    wire [RED_W:0] r0_ext  = {1'b0, r0_p};
    wire [RED_W:0] p1_ext  = {{(RED_W+1-MOD_W){1'b0}}, prime_p[ST_R0H]};
    wire [RED_W:0] p2_ext  = {{(RED_W-MOD_W){1'b0}}, prime_p[ST_R0H], 1'b0};
    wire [RED_W:0] p3_ext  = {1'b0, prime3_p};
    wire [RED_W:0] d1      = r0_ext - p1_ext;
    wire [RED_W:0] d2      = r0_ext - p2_ext;
    wire [RED_W:0] d3      = r0_ext - p3_ext;
    wire [RED_W-1:0] r_sub = ~d2[RED_W] ? d2[RED_W-1:0] :
                             ~d1[RED_W] ? d1[RED_W-1:0] : r0_p;
    //: r >= prime after the corrections is exactly r0 >= 3*prime, so the bound
    //: check is one more parallel borrow and not a second carry chain behind
    //: the correction.
    wire             bound_bad = ~d3[RED_W];
    wire [MOD_W-1:0] reduced   = r_sub[MOD_W-1:0];

    assign ref_inject[ST_RED] = (v_p[ST_R0H] && (ref_p[ST_R0H] == RFC_NONE) &&
                                 (r0_bad_p || bound_bad)) ? RFC_BOUND : RFC_NONE;

    generate
        for (st = ST_IN; st <= ST_RED; st = st + 1) begin : g_no_inject
            if (st != ST_IN && st != ST_SUB && st != ST_FOLD && st != ST_TAB &&
                st != ST_RED)
                assign ref_inject[st] = RFC_NONE;
        end
    endgenerate

    integer x_i;
    integer p_i;
    always @(posedge clk) begin
        x_p[ST_FOLD] <= fold_value;
        for (x_i = ST_FOLD+1; x_i <= ST_RED; x_i = x_i + 1)
            x_p[x_i] <= x_p[x_i-1];

        prime_p[ST_TAB]  <= col_valid ? prime_rd  : {MOD_W{1'b0}};
        offset_p[ST_TAB] <= col_valid ? offset_rd : {ROW_W{1'b0}};
        mu_p[ST_TAB]     <= col_valid ? mu_rd     : {MU_W{1'b0}};
        //: np only ever indexes the one variable shift below, and it is stored
        //: pre-decremented so the shift stage holds nothing but the shift.
        np_m1_p          <= col_valid ? (np_rd - 1'b1) : {NP_W{1'b0}};
        for (p_i = ST_TAB+1; p_i <= ST_R0H; p_i = p_i + 1)
            prime_p[p_i]  <= prime_p[p_i-1];
        for (p_i = ST_TAB+1; p_i <= ST_RED; p_i = p_i + 1)
            offset_p[p_i] <= offset_p[p_i-1];
        for (p_i = ST_TAB+1; p_i <= ST_SHIFT; p_i = p_i + 1)
            mu_p[p_i] <= mu_p[p_i-1];

        //: The only variable shift in the datapath: Xh = X >> (np-1).
        xh_p <= x_p[ST_TAB] >> np_m1_p;
        //: Fixed shift by DIVIDEND_W+1: wiring, registered here.
        qh_p <= qprod[MU_W+DIVIDEND_W-1:DIVIDEND_W+1];

        r0_lo_p     <= sub_lo[RED_W-1:0];
        r0_borrow_p <= sub_lo[RED_W];
        x_hi_p      <= x_hi_w;
        rp_hi_p     <= rp_hi_w;
        rp_over_p   <= rp_over;

        r0_p     <= r0_lo_p;
        r0_bad_p <= rp_over_p || (|sub_hi);
        prime3_p <= {{(RED_W-MOD_W-1){1'b0}}, prime_p[ST_R0], 1'b0} +
                    {{(RED_W-MOD_W){1'b0}}, prime_p[ST_R0]};

        r_p <= reduced;
    end

    ot_a3_ngram_mul_pipe #(
        .A_W(MU_W), .B_W(DIVIDEND_W), .DIGIT_W(MUL_DIGIT_W)
    ) u_mul2 (
        .clk(clk), .a(mu_p[ST_SHIFT]), .b(xh_p), .p(qprod)
    );

    ot_a3_ngram_mul_pipe #(
        .A_W(QH_W), .B_W(MOD_W), .DIGIT_W(MUL_DIGIT_W)
    ) u_mul3 (
        .clk(clk), .a(qh_p), .b(prime_p[ST_QH]), .p(rprod)
    );

    always @(posedge clk) begin
        if (!rst_chain_n[RST_PIPE]) status_bound_error <= 1'b0;
        else if (ref_inject[ST_RED] == RFC_BOUND) status_bound_error <= 1'b1;
    end

    // =====================================================================
    // Elastic output boundary.  The buffer is addressed by rotating one-hot
    // registers, not by pointers: a pointer bit would drive a mux tree level
    // across the whole payload, a one-hot bit drives the payload width once.
    // =====================================================================
    wire [3:0]      out_ref_w = ref_p[ST_RED];
    wire            refused   = (out_ref_w != RFC_NONE);
    wire [ROW_W:0]  row_sum   = offset_p[ST_RED] + r_p;
    wire [PAY_W-1:0] push_payload = {
        refused ? {ROW_W{1'b0}} : row_sum[ROW_W-1:0],
        out_ref_w,
        tag_p[ST_RED],
        order_p[ST_RED],
        head_p[ST_RED],
        refused ? {MOD_W{1'b0}} : r_p,
        refused ? {DIVIDEND_W{1'b0}} : x_p[ST_RED]
    };

    reg [CNT_W-1:0] fifo_count;
    wire            push     = v_p[ST_RED];
    wire            fifo_pop = (fifo_count != {CNT_W{1'b0}}) &&
                               (!out_valid || out_ready);

    always @(posedge clk) begin
        if (!rst_chain_n[RST_PIPE]) fifo_count <= {CNT_W{1'b0}};
        else if (push && !fifo_pop)      fifo_count <= fifo_count + 1'b1;
        else if (fifo_pop && !push)      fifo_count <= fifo_count - 1'b1;
    end

    //: out_valid is reset because a consumer samples it before the first beat;
    //: the word beside it is only ever read while out_valid is high.
    always @(posedge clk) begin
        if (!rst_chain_n[RST_PIPE]) out_valid <= 1'b0;
        else if (fifo_pop) out_valid <= 1'b1;
        else if (out_ready) out_valid <= 1'b0;
    end

    //: BANKS independent buffers, each holding BANK_W bits of the payload and
    //: each with its OWN position, occupancy and pop.  They are driven by the
    //: same push and the same pop condition, so they stay in lockstep; they
    //: differ only in WHERE in the ring they start, which is what keeps them
    //: distinct registers that no sequential sweep can fold back together --
    //: and being distinct is the whole point, because every control net here
    //: drives one bank's width instead of the whole payload's.  Flat, the
    //: position and the output enable drove 306 cells each and cost 1.54 ns.
    wire [MEM_W-1:0] push_word = push_payload;
    wire [MEM_W-1:0] out_word;

    genvar bk;
    generate
        for (bk = 0; bk < BANKS; bk = bk + 1) begin : g_bank
            reg  [BANK_W-1:0]     mem [0:FIFO_DEPTH-1];
            reg  [FIFO_DEPTH-1:0] wr_hot;
            reg  [FIFO_DEPTH-1:0] rd_hot;
            //: cnt is this bank's occupancy offset by its phase, so that it is
            //: a different value from every other bank's at all times.
            reg  [CNT_W-1:0]      cnt;
            reg  [BANK_W-1:0]     out_slice;

            wire [FIFO_DEPTH-1:0] phase   = {{(FIFO_DEPTH-1){1'b0}}, 1'b1} << bk;
            wire [CNT_W-1:0]      cnt_min = bk[CNT_W-1:0];
            wire bank_pop = (cnt != cnt_min) && (!out_valid || out_ready);
            wire [BANK_W-1:0] slice_in = push_word[bk*BANK_W +: BANK_W];
            wire [BANK_W-1:0] slice_rd;

            //: The write is unconditional: the entry wr_hot points at is
            //: rewritten every cycle and frozen by wr_hot advancing, which only
            //: a push does, so the enable is one registered one-hot bit and not
            //: `push AND position`.  Safe because cnt - phase <= credit <=
            //: FIFO_DEPTH-1, so the write and the read never address the same
            //: entry while that entry is occupied.
            for (e = 0; e < FIFO_DEPTH; e = e + 1) begin : g_wr
                always @(posedge clk)
                    if (wr_hot[e]) mem[e] <= slice_in;
            end

            for (i = 0; i < BANK_W; i = i + 1) begin : g_rd
                wire [FIFO_DEPTH-1:0] bits;
                for (e = 0; e < FIFO_DEPTH; e = e + 1) begin : g_bit
                    assign bits[e] = rd_hot[e] && mem[e][i];
                end
                assign slice_rd[i] = |bits;
            end

            always @(posedge clk) begin
                if (!rst_chain_n[RST_BANK + bk]) begin
                    wr_hot <= phase;
                    rd_hot <= phase;
                    cnt    <= cnt_min;
                end else begin
                    if (push)     wr_hot <= {wr_hot[FIFO_DEPTH-2:0], wr_hot[FIFO_DEPTH-1]};
                    if (bank_pop) rd_hot <= {rd_hot[FIFO_DEPTH-2:0], rd_hot[FIFO_DEPTH-1]};
                    if (push && !bank_pop)      cnt <= cnt + 1'b1;
                    else if (bank_pop && !push) cnt <= cnt - 1'b1;
                end
            end

            always @(posedge clk)
                if (bank_pop) out_slice <= slice_rd;

            assign out_word[bk*BANK_W +: BANK_W] = out_slice;
        end
    endgenerate

    assign out_dividend = out_word[PF_DIV   +: DIVIDEND_W];
    assign out_residue  = out_word[PF_RES   +: MOD_W];
    assign out_head     = out_word[PF_HEAD  +: HEAD_W];
    assign out_order    = out_word[PF_ORDER +: ORDER_W];
    assign out_tag      = out_word[PF_TAG   +: TAG_W];
    assign out_refuse   = out_word[PF_REF   +: 4];
    assign out_row      = out_word[PF_ROW   +: ROW_W];
endmodule
