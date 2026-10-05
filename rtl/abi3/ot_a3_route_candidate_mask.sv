`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROUTE.CANDIDATE_MASK (sub-opcode ot_a3_pkg::A3_ROUTE_CANDIDATE_MASK, 0x09).
// AM-E10, the DeepSeek-V4.1-Flash candidate pool.
//
// IR kind: CANDIDATE_MASK(block_ids, block, width) -> mask.
// Numeric contract: candidate_mask_v1.
// Reference: runtime/reference/candidate_pool.py::select_candidate_mask.
//
// WHAT IT DOES.  The candidate source layer reduces index scores to one score
// per block of BLOCK positions (ROUTE.BLOCK_MAX) and a block top-k keeps the
// best ids.  Every later Reindex layer scores only the positions those blocks
// cover.  This block expands the chosen ids back into a per-position mask over
// cfg_width positions, packed WORD_BITS positions to a word, which becomes
// ROUTE.INDEX_TOPK's new slot-3 operand.
//
// POLARITY: A SET BIT ADMITS ITS POSITION.  Bit j of output word w is 1 when
// position w*WORD_BITS + j lies in a chosen block, and the consumer replaces
// the score at every ZERO position with -inf.  Two pinned facts fix this, and
// they agree:
//   * SRC-DSV41-FLASH-MODEL: the Indexer "masks scores to the candidate pool"
//     when 0 <= candidate_source_layer < layer_id -- the pool is what SURVIVES.
//   * The plan's independent checker candidate_pool_bound requires every
//     INDEX_TOPK after the candidate source to carry a mask "whose population
//     is at most 16,384", and 16,384 is exactly 2,048 chosen blocks x 8
//     positions (SRC-DSV41-FLASH-CONFIG).  A population that counted EXCLUDED
//     positions would be cfg_width - 16,384 and would grow with the context;
//     bounded by the pool, the population is the ADMITTED count.
// Plan section 5 row 3 reads "masks scores to -inf inside the candidate
// blocks", which taken literally is the opposite polarity and the opposite of
// its own checker.  It is a sentence about the -inf the operand produces, not
// about the bit: -inf goes OUTSIDE the candidate blocks.  Were the polarity
// inverted here, the pool would be the only part of the context the indexer
// could not see, and the mechanism would select from what the candidate source
// rejected.  obs_population counts admitted positions so a campaign can
// falsify this choice against the bound rather than believe the comment.
//
// PINNED LAST BLOCK (parameter PIN_LAST_BLOCK, default 1).  Block
// ceil(cfg_width/BLOCK) - 1, the one holding the newest position, is admitted
// whether or not an id named it.  Its block maximum was taken over a partly
// filled block whose absent tail is -inf padding, so its score is not
// comparable with a full block's, and the Hierarchical Sparse Indexer is
// applied identically in training and inference, where the current block is
// always visible.  The pin is a parameter only so a campaign can measure what
// the rule is worth; it is not an option the model has.
//
// -INF PADDING / TAIL.  cfg_width need not be a multiple of BLOCK or of
// WORD_BITS.  The last block covers [last*BLOCK, cfg_width) only; positions at
// or above cfg_width do not exist, are never admitted, and are zero in the high
// bits of the final word.  obs_population accounts for the short last block.
//
// IDS ARE A SET.  Order does not matter and a repeated id admits its block
// once, so obs_population is the population of a union.  An ot_a3_pkg::A3_NO_ID
// slot is an empty top-k slot (a block-score vector padded to -inf still
// returns k indices) and is skipped.  Any other id at or above the block count
// of THIS position axis is a fault, not a silent drop.
//
// PIPELINE, STAGES AND INITIATION INTERVAL.
//   Ingest  4 registered stages (operand address -> operand data -> bitmap
//           fetch -> read-modify-write), II = 1 id per cycle.  Two of the four
//           are the operand port's own latency: this block registers
//           id_rd_addr, and the synchronous read answers one cycle after the
//           address is visible.  The set bitmap is a memory, so two ids in one
//           bitmap word are a read-modify-write hazard; one forwarding register
//           resolves it and the II stays 1.
//   Emit    2 registered stages (bitmap fetch -> expand, tail-mask and emit),
//           II = 1 OUTPUT WORD PER CYCLE, with no stall path and no
//           dependence between consecutive words.  out_we is asserted on every
//           cycle of the emit phase: obs_emit_gap_max is 1 on any run that
//           emits two words, which is the II the top measures rather than
//           assumes.
// Nothing walks a vector combinationally.  The widest combinational path in
// the emit loop is a BLOCK-to-1 mux of WORD_BITS bits over a wiring-only
// replication network (see g_cand: every index there is elaboration-constant)
// and one AND with the tail mask.  The only division and multiplication are by
// the elaboration parameters BLOCK and WORD_BITS, and they are confined to the
// three setup cycles, outside every II = 1 loop.
//
// WHY A BITMAP AND NOT A MATERIALISED MASK.  Emitting mask words in ascending
// order from a sparse id list would have to absorb up to WORD_BITS/BLOCK ids in
// one cycle when the chosen blocks are contiguous, which a one-id-per-cycle
// operand port cannot feed.  Turning the ids into one bit per block first makes
// the emit side dense: one bitmap word of WORD_BITS blocks covers exactly BLOCK
// output words for any BLOCK >= 1, so the expander never stalls.  The bitmap is
// also BLOCK times smaller than the mask it produces.
//
// GEOMETRY IS PARAMETERISED, NOT FROZEN.  BLOCK, MAX_WIDTH, MAX_IDS,
// WORD_BITS and PIN_LAST_BLOCK carry the V4.1 values as defaults and nothing
// below compares against a literal: every admission bound is derived from a
// parameter or from an operand field (cfg_width, cfg_id_count, cfg_max_pop),
// and the block count comes from cfg_width, never from an assumed 2,048.  The
// V4.1 pool is 2,048 blocks of 8 over a context of up to 1,048,576 positions;
// this block also elaborates at BLOCK = 1, at a BLOCK that is not a power of
// two, and at any MAX_WIDTH; the campaign runs five elaborations, one of them
// with the pinned-last-block rule off.
// cfg_block exists so a descriptor that carries a block size is CHECKED
// against the elaborated one instead of being silently reinterpreted; zero
// means the descriptor did not carry one.  The expander is elaborated wiring,
// so a different block size is one parameter override, not a source edit --
// and obs_param_block publishes what was elaborated so a checker never has to
// guess.
//
// FAIL-CLOSED AND ATOMIC.  Every refusal is detected before the first out_we:
// the shape checks in setup, an out-of-range id during ingest, the population
// bound at the end of ingest.  A refused run writes no output word, reports
// error_code with an error_detail naming the trap site, and latches the slot
// and the value that caused it.
//
// PORT CONTRACT.  id_rd_data is the word at id_rd_addr one cycle later (a
// synchronous read); the block never stalls on the operand port.  out_we,
// out_addr and out_data are registered.
// ---------------------------------------------------------------------------
module ot_a3_route_candidate_mask #(
    //: Positions per candidate block.  V4.1: 8.
    parameter integer BLOCK = 8,
    //: Largest position axis this elaboration masks.
    //:
    //: 16,384 is the CANDIDATE POOL, which is what this operator masks: 2,048
    //: blocks of 8, and the capability's own max_candidate_positions.  It was
    //: 1,048,576 -- the whole V4.1 CONTEXT -- which over-provisions the set
    //: bitmap by 64x: MAX_BLOCKS/WORD_BITS words of storage, so 4,096 words of
    //: 32 bits rather than 64.  A Reindex layer scores only inside the pool, so
    //: the wider axis was never the one being masked.  Still a parameter: an
    //: instance that must mask a whole context is one override.
    parameter integer MAX_WIDTH = 16384,
    //: Largest chosen-block count.  V4.1 pool: 2,048 blocks.
    parameter integer MAX_IDS = 2048,
    //: Positions per packed mask word.  The machine word, not model geometry;
    //: must be a power of two so a block id splits into word and bit without a
    //: divider in the ingest loop.
    parameter integer WORD_BITS = 32,
    //: The pinned-last-block rule.  1 in the model.
    parameter integer PIN_LAST_BLOCK = 1
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [7:0]  cfg_subop,
    input  wire [31:0] cfg_width,       // positions the mask covers
    input  wire [31:0] cfg_id_count,    // chosen-block ids present at cfg_ids_base
    input  wire [31:0] cfg_block,       // 0 = not carried; else must equal BLOCK
    input  wire [31:0] cfg_max_pop,     // 0 = unbounded; else admitted-position bound
    input  wire [31:0] cfg_ids_base,
    input  wire [31:0] cfg_out_base,

    output reg         id_rd_en,
    output reg  [31:0] id_rd_addr,
    input  wire [31:0] id_rd_data,

    output reg                 out_we,
    output reg  [31:0]         out_addr,
    output reg  [WORD_BITS-1:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [7:0]  error_detail,
    output reg  [31:0] error_slot,
    output reg  [31:0] error_value,

    output reg  [31:0] obs_out_count,      // mask words emitted
    output reg  [31:0] obs_population,     // admitted POSITIONS (polarity witness)
    output reg  [31:0] obs_blocks,         // distinct admitted blocks
    output reg  [31:0] obs_ids_consumed,
    output reg  [31:0] obs_emit_gap_max,   // measured II of the emit loop
    output wire [31:0] obs_param_block,
    output wire [31:0] obs_param_max_width,
    output wire [31:0] obs_param_max_ids,
    output wire [31:0] obs_param_word_bits,
    output wire [31:0] obs_param_pin_last
);
    localparam [7:0] ERR_NONE        = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SHAPE       = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] SUBOP           = ot_a3_pkg::A3_ROUTE_CANDIDATE_MASK;
    localparam [31:0] ABSENT_ID      = ot_a3_pkg::A3_NO_ID;

    //: Numbered trap sites.  A refusal that is only a code cannot be told from
    //: another refusal of the same kind, and the detail is what a campaign
    //: compares.
    localparam [7:0] DET_NONE            = 8'd0;
    localparam [7:0] DET_SUBOP           = 8'd1;
    localparam [7:0] DET_WIDTH_ZERO      = 8'd2;
    localparam [7:0] DET_WIDTH_MAX       = 8'd3;
    localparam [7:0] DET_ID_COUNT_MAX    = 8'd4;
    localparam [7:0] DET_BLOCK_MISMATCH  = 8'd5;
    localparam [7:0] DET_ID_RANGE        = 8'd6;
    localparam [7:0] DET_POPULATION      = 8'd7;

    localparam integer MAX_BLOCKS     = (MAX_WIDTH + BLOCK - 1) / BLOCK;
    localparam integer SET_WORDS      = (MAX_BLOCKS + WORD_BITS - 1) / WORD_BITS;
    localparam integer MAX_MASK_WORDS = (MAX_WIDTH + WORD_BITS - 1) / WORD_BITS;
    localparam integer LOG2_WORD_BITS = (WORD_BITS <= 2) ? 1 : $clog2(WORD_BITS);
    localparam integer SET_AW         = (SET_WORDS <= 1) ? 1 : $clog2(SET_WORDS);
    //: Wide enough for a sub-word index 0..BLOCK-1 and no wider, so the emit
    //: mux compares narrow numbers.
    localparam integer SUB_W          = (BLOCK <= 1) ? 1 : $clog2(BLOCK);

    assign obs_param_block     = BLOCK;
    assign obs_param_max_width = MAX_WIDTH;
    assign obs_param_max_ids   = MAX_IDS;
    assign obs_param_word_bits = WORD_BITS;
    assign obs_param_pin_last  = PIN_LAST_BLOCK;

    initial begin
        if (WORD_BITS != (1 << LOG2_WORD_BITS))
            $fatal(1, "ot_a3_route_candidate_mask: WORD_BITS must be a power of two");
        if (WORD_BITS < 2)
            $fatal(1, "ot_a3_route_candidate_mask: WORD_BITS must be at least 2");
        if (BLOCK < 1)
            $fatal(1, "ot_a3_route_candidate_mask: BLOCK must be at least 1");
        //: The bitmap must cover every block of the widest axis this
        //: elaboration accepts, and one bitmap word must expand to exactly
        //: BLOCK output words -- the invariant the expander is wired from.
        if (SET_WORDS * WORD_BITS < MAX_BLOCKS)
            $fatal(1, "ot_a3_route_candidate_mask: bitmap narrower than MAX_BLOCKS");
        if (SET_WORDS * BLOCK < MAX_MASK_WORDS)
            $fatal(1, "ot_a3_route_candidate_mask: bitmap shorter than the mask");
    end

    // -- the block set: one bit per candidate block ---------------------------
    reg [WORD_BITS-1:0] set_mem [0:SET_WORDS-1];
    //: False until a clear has covered the whole bitmap.  One flip-flop in
    //: place of a reset on every bit of set_mem.
    reg                 set_primed;

    // -- setup registers -----------------------------------------------------
    reg [31:0] r_width, r_id_count, r_max_pop, r_ids_base, r_out_base;
    reg [31:0] r_block_count;     // ceil(width / BLOCK)
    reg [31:0] r_mask_words;      // ceil(width / WORD_BITS)
    reg [31:0] r_set_used;        // ceil(block_count / WORD_BITS)
    reg [31:0] r_grp_used;        // ceil(mask_words / BLOCK)
    reg [31:0] r_clear_words;

    //: WHY THERE IS A SEQUENTIAL DIVIDER HERE.
    //:
    //: ceil(x / BLOCK) was written as a 32-bit `/` because BLOCK is deliberately
    //: allowed to be a non-power-of-two -- WORD_BITS gets a shift, BLOCK cannot.
    //: Two such divides and one 32-bit multiply sat in the setup states, and a
    //: combinational 32-bit divider is a multi-nanosecond path: after the bitmap
    //: was fixed this block still measured 187 MHz on a 5.343 ns path.
    //:
    //: These divisions happen ONCE PER RUN, against an emit loop of thousands of
    //: beats, so ~32 cycles of restoring division is free.  One implementation
    //: rather than a power-of-two fast path beside a general slow one, because a
    //: fast path that every elaboration takes leaves the slow one untested.
    //:
    //: The remainder is not waste either: it IS the last block's length, which
    //: removes the `r_width - (r_block_count - 1) * BLOCK` multiply as well.
    localparam integer DIV_W = 32;
    reg [DIV_W-1:0] dv_n;      // dividend, shifted out most-significant first
    reg [DIV_W-1:0] dv_q;      // quotient
    reg [DIV_W:0]   dv_r;      // remainder, one bit wider so rem+bit cannot wrap
    reg [5:0]       dv_i;      // bits remaining
    //: One comparison and one conditional subtract per cycle; the borrow out of
    //: `dv_r - BLOCK` IS the comparison, so there is no separate compare chain.
    wire [DIV_W:0]  dv_shift = {dv_r[DIV_W-1:0], dv_n[DIV_W-1]};
    wire [DIV_W:0]  dv_diff  = dv_shift - {1'b0, BLOCK[DIV_W-1:0]};
    wire            dv_fits  = !dv_diff[DIV_W];
    reg [31:0] r_last_block;
    reg [31:0] r_tail_len;        // positions in the short last block
    reg [WORD_BITS-1:0] r_tail_mask;
    reg [31:0] r_last_word;

    // -- ingest pipeline -----------------------------------------------------
    reg        i1_valid;
    reg [31:0] i1_slot;
    reg        i1b_valid;
    reg [31:0] i1b_slot;
    reg        i2_valid, i2_skip;
    reg [31:0] i2_slot, i2_id;
    reg [SET_AW-1:0]        i2_widx;
    reg [LOG2_WORD_BITS-1:0] i2_bit;
    reg [WORD_BITS-1:0]     i2_set_q;
    reg        wr_valid;
    reg [SET_AW-1:0]    wr_addr;
    reg [WORD_BITS-1:0] wr_data;
    reg [31:0] ing_issued;   // ids whose read has been issued
    reg [31:0] ing_retired;  // ids that completed the read-modify-write

    // -- emit pipeline -------------------------------------------------------
    reg [31:0] e_word;                 // next output word index to enter stage 1
    reg [31:0] e_grp;                  // bitmap word index for e_word
    reg [SUB_W-1:0] e_sub;             // which of the BLOCK words inside e_grp
    reg        s1_valid;
    reg [31:0] s1_word;
    reg [SUB_W-1:0] s1_sub;
    reg [WORD_BITS-1:0] s1_set_q;
    reg [31:0] emit_gap;

    // -- clear phase ---------------------------------------------------------
    reg [31:0] clr_index;

    localparam [3:0] S_IDLE   = 4'd0;
    localparam [3:0] S_SETUP1 = 4'd1;
    localparam [3:0] S_SETUP2 = 4'd2;
    localparam [3:0] S_SETUP3 = 4'd3;
    localparam [3:0] S_CLEAR  = 4'd4;
    localparam [3:0] S_PIN    = 4'd5;
    localparam [3:0] S_INGEST = 4'd6;
    localparam [3:0] S_BOUND  = 4'd7;
    localparam [3:0] S_EMIT   = 4'd8;
    localparam [3:0] S_DRAIN  = 4'd9;
    localparam [3:0] S_DONE   = 4'd10;
    //: The two ceil-divisions by BLOCK, one sequential divider run twice.
    localparam [3:0] S_DIV1   = 4'd11;
    localparam [3:0] S_DIV2   = 4'd12;
    reg [3:0] state;

    // ----------------------------------------------------------------------
    // The expander.  One bitmap word holds WORD_BITS block bits and therefore
    // covers WORD_BITS*BLOCK positions, which is exactly BLOCK output words for
    // any BLOCK >= 1.  Candidate c is output word c of that group: bit j of it
    // is position c*WORD_BITS + j inside the group, which belongs to block
    // (c*WORD_BITS + j)/BLOCK -- an elaboration constant, so this is wiring and
    // bit replication, with no arithmetic and no dependence on j-1.  The
    // largest index is (BLOCK*WORD_BITS - 1)/BLOCK = WORD_BITS - 1, so the
    // network is exactly the width of one bitmap word.
    // ----------------------------------------------------------------------
    wire [BLOCK*WORD_BITS-1:0] cand_flat;
    genvar gc, gj;
    generate
        for (gc = 0; gc < BLOCK; gc = gc + 1) begin : g_cand
            for (gj = 0; gj < WORD_BITS; gj = gj + 1) begin : g_bit
                assign cand_flat[gc*WORD_BITS + gj] =
                    s1_set_q[(gc*WORD_BITS + gj) / BLOCK];
            end
        end
    endgenerate

    //: A BLOCK-to-1 mux of constant part-selects: no variable shift, no
    //: variable-range select, and nothing here depends on bit j-1.
    reg [WORD_BITS-1:0] expanded;
    integer mux_i;
    always @* begin
        expanded = cand_flat[0 +: WORD_BITS];
        for (mux_i = 0; mux_i < BLOCK; mux_i = mux_i + 1)
            if (s1_sub == mux_i[SUB_W-1:0])
                expanded = cand_flat[mux_i*WORD_BITS +: WORD_BITS];
    end
    wire [WORD_BITS-1:0] emit_word =
        (s1_word == r_last_word) ? (expanded & r_tail_mask) : expanded;

    // -- ingest read-modify-write with one forwarding path -------------------
    wire [WORD_BITS-1:0] i2_cur =
        (wr_valid && (wr_addr == i2_widx)) ? wr_data : i2_set_q;
    wire i2_already = i2_cur[i2_bit];
    wire [WORD_BITS-1:0] i2_next =
        i2_cur | ({{(WORD_BITS-1){1'b0}}, 1'b1} << i2_bit);
    wire [31:0] i2_block_len =
        (i2_id == r_last_block) ? r_tail_len : BLOCK[31:0];
    wire i2_id_bad = (i2_id >= r_block_count);

    integer rst_i;

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            error_detail <= DET_NONE;
            error_slot <= 32'd0;
            error_value <= 32'd0;
            id_rd_en <= 1'b0;
            id_rd_addr <= 32'd0;
            out_we <= 1'b0;
            out_addr <= 32'd0;
            out_data <= {WORD_BITS{1'b0}};
            obs_out_count <= 32'd0;
            obs_population <= 32'd0;
            obs_blocks <= 32'd0;
            obs_ids_consumed <= 32'd0;
            obs_emit_gap_max <= 32'd0;
            i1_valid <= 1'b0;
            i1b_valid <= 1'b0;
            i2_valid <= 1'b0;
            i2_skip <= 1'b0;
            wr_valid <= 1'b0;
            s1_valid <= 1'b0;
            emit_gap <= 32'd0;
            //: SET_MEM TAKES NO RESET.
            //:
            //: Resetting it swept every word, so rst_n drove SET_WORDS *
            //: WORD_BITS flip-flops -- 131,072 at the old default width -- and
            //: that fan-out, not the arithmetic, was the critical path: the
            //: block measured 0.1 MHz over 629,186 cells.  The sweep was also
            //: REDUNDANT: S_CLEAR already zeroes the words a run touches before
            //: S_INGEST reads any of them, so no run ever depended on reset
            //: having done it.  What reset genuinely has to establish is that
            //: the FIRST run cannot read a word no run has written, and one
            //: flag does that: set_primed below makes the first clear cover the
            //: whole bitmap and every later one cover only what was used.
            set_primed <= 1'b0;
            dv_i <= 6'd0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            id_rd_en <= 1'b0;
            case (state)
                // ------------------------------------------------------------
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        error_detail <= DET_NONE;
                        error_slot <= 32'd0;
                        error_value <= 32'd0;
                        obs_out_count <= 32'd0;
                        obs_population <= 32'd0;
                        obs_blocks <= 32'd0;
                        obs_ids_consumed <= 32'd0;
                        obs_emit_gap_max <= 32'd0;
                        emit_gap <= 32'd0;
                        i1_valid <= 1'b0;
                        i1b_valid <= 1'b0;
                        i2_valid <= 1'b0;
                        wr_valid <= 1'b0;
                        s1_valid <= 1'b0;
                        r_width <= cfg_width;
                        r_id_count <= cfg_id_count;
                        r_max_pop <= cfg_max_pop;
                        r_ids_base <= cfg_ids_base;
                        r_out_base <= cfg_out_base;
                        // Shape refusals, every bound from a parameter or an
                        // operand field.
                        if (cfg_subop != SUBOP) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DET_SUBOP;
                            error_value <= {24'd0, cfg_subop};
                            state <= S_DONE;
                        end else if (cfg_width == 32'd0) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DET_WIDTH_ZERO;
                            state <= S_DONE;
                        end else if (cfg_width > MAX_WIDTH[31:0]) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DET_WIDTH_MAX;
                            error_value <= cfg_width;
                            state <= S_DONE;
                        end else if (cfg_id_count > MAX_IDS[31:0]) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DET_ID_COUNT_MAX;
                            error_value <= cfg_id_count;
                            state <= S_DONE;
                        end else if ((cfg_block != 32'd0) &&
                                     (cfg_block != BLOCK[31:0])) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DET_BLOCK_MISMATCH;
                            error_value <= cfg_block;
                            state <= S_DONE;
                        end else begin
                            state <= S_SETUP1;
                        end
                    end
                end
                // -- setup: the shifts here, the divisions in S_DIV1/S_DIV2 ---
                S_SETUP1: begin
                    r_mask_words <= (r_width + WORD_BITS[31:0] - 32'd1) >>
                                    LOG2_WORD_BITS;
                    r_tail_mask <= (r_width[LOG2_WORD_BITS-1:0] == {LOG2_WORD_BITS{1'b0}})
                        ? {WORD_BITS{1'b1}}
                        : ~({WORD_BITS{1'b1}} << r_width[LOG2_WORD_BITS-1:0]);
                    //: width / BLOCK.  The quotient and remainder together give
                    //: both the block count and the tail length.
                    dv_n <= r_width;
                    dv_q <= 32'd0;
                    dv_r <= {(DIV_W+1){1'b0}};
                    dv_i <= DIV_W[5:0];
                    state <= S_DIV1;
                end
                S_DIV1: begin
                    if (dv_i != 6'd0) begin
                        dv_r <= dv_fits ? dv_diff : dv_shift;
                        dv_q <= {dv_q[DIV_W-2:0], dv_fits};
                        dv_n <= {dv_n[DIV_W-2:0], 1'b0};
                        dv_i <= dv_i - 6'd1;
                    end else begin
                        //: ceil, and the last block's length in one step: a zero
                        //: remainder means the axis divides exactly, so the last
                        //: block is full.
                        r_block_count <= dv_q + ((dv_r != 0) ? 32'd1 : 32'd0);
                        r_tail_len <= (dv_r != 0) ? dv_r[31:0] : BLOCK[31:0];
                        //: mask_words / BLOCK, the second and last division.
                        dv_n <= r_mask_words;
                        dv_q <= 32'd0;
                        dv_r <= {(DIV_W+1){1'b0}};
                        dv_i <= DIV_W[5:0];
                        state <= S_DIV2;
                    end
                end
                S_DIV2: begin
                    if (dv_i != 6'd0) begin
                        dv_r <= dv_fits ? dv_diff : dv_shift;
                        dv_q <= {dv_q[DIV_W-2:0], dv_fits};
                        dv_n <= {dv_n[DIV_W-2:0], 1'b0};
                        dv_i <= dv_i - 6'd1;
                    end else begin
                        r_grp_used <= dv_q + ((dv_r != 0) ? 32'd1 : 32'd0);
                        state <= S_SETUP2;
                    end
                end
                S_SETUP2: begin
                    r_set_used <= (r_block_count + WORD_BITS[31:0] - 32'd1) >>
                                  LOG2_WORD_BITS;
                    r_last_block <= r_block_count - 32'd1;
                    r_last_word <= r_mask_words - 32'd1;
                    state <= S_SETUP3;
                end
                S_SETUP3: begin
                    //: Every bitmap word ingest can write and every bitmap word
                    //: emit can read, and not one more: the clear cost is
                    //: ceil(blocks/WORD_BITS), never the whole elaborated
                    //: bitmap.
                    //: Until the bitmap has been covered once, clear all of
                    //: it: a word no run has written holds no defined value,
                    //: and the dedup test reads before it writes.
                    r_clear_words <= !set_primed
                        ? SET_WORDS[31:0]
                        : ((r_set_used > r_grp_used) ? r_set_used : r_grp_used);
                    clr_index <= 32'd0;
                    state <= S_CLEAR;
                end
                // -- clear only the bitmap words this run touches -------------
                S_CLEAR: begin
                    if (clr_index < SET_WORDS[31:0])
                        set_mem[clr_index[SET_AW-1:0]] <= {WORD_BITS{1'b0}};
                    clr_index <= clr_index + 32'd1;
                    if (clr_index + 32'd1 >= r_clear_words) begin
                        set_primed <= 1'b1;
                        ing_issued <= 32'd0;
                        ing_retired <= 32'd0;
                        state <= (PIN_LAST_BLOCK != 0) ? S_PIN : S_INGEST;
                    end
                end
                // -- the pinned last block, before any id ---------------------
                // The bitmap is freshly cleared, so the pin is a write and not
                // a read-modify-write; wr_* is primed so the first ingest id
                // that names the same bitmap word forwards from it.
                S_PIN: begin
                    set_mem[r_last_block[SET_AW+LOG2_WORD_BITS-1:LOG2_WORD_BITS]] <=
                        ({{(WORD_BITS-1){1'b0}}, 1'b1} <<
                         r_last_block[LOG2_WORD_BITS-1:0]);
                    wr_valid <= 1'b1;
                    wr_addr <= r_last_block[SET_AW+LOG2_WORD_BITS-1:LOG2_WORD_BITS];
                    wr_data <= ({{(WORD_BITS-1){1'b0}}, 1'b1} <<
                                r_last_block[LOG2_WORD_BITS-1:0]);
                    obs_population <= r_tail_len;
                    obs_blocks <= 32'd1;
                    state <= S_INGEST;
                end
                // -- ingest: II = 1 id per cycle ------------------------------
                S_INGEST: begin
                    // stage 0: issue the operand read
                    if (ing_issued < r_id_count) begin
                        id_rd_en <= 1'b1;
                        id_rd_addr <= r_ids_base + ing_issued;
                        i1_valid <= 1'b1;
                        i1_slot <= ing_issued;
                        ing_issued <= ing_issued + 32'd1;
                    end else begin
                        i1_valid <= 1'b0;
                    end
                    // stage 1: the address this block registered last cycle is
                    // on the operand port now; the synchronous read answers it
                    // next cycle.
                    i1b_valid <= i1_valid;
                    i1b_slot <= i1_slot;
                    // stage 2: the id word is on id_rd_data; split it and issue
                    // the bitmap read
                    i2_valid <= i1b_valid;
                    if (i1b_valid) begin
                        i2_slot <= i1b_slot;
                        i2_id <= id_rd_data;
                        i2_skip <= (id_rd_data == ABSENT_ID);
                        i2_widx <= id_rd_data[SET_AW+LOG2_WORD_BITS-1:LOG2_WORD_BITS];
                        i2_bit <= id_rd_data[LOG2_WORD_BITS-1:0];
                        i2_set_q <=
                            set_mem[id_rd_data[SET_AW+LOG2_WORD_BITS-1:LOG2_WORD_BITS]];
                    end
                    // stage 3: read-modify-write, with forwarding
                    wr_valid <= 1'b0;
                    if (i2_valid) begin
                        obs_ids_consumed <= obs_ids_consumed + 32'd1;
                        ing_retired <= ing_retired + 32'd1;
                        if (i2_skip) begin
                            // an empty top-k slot admits nothing
                        end else if (i2_id_bad) begin
                            error_code <= ERR_INDEX_RANGE;
                            error_detail <= DET_ID_RANGE;
                            error_slot <= i2_slot;
                            error_value <= i2_id;
                            i1_valid <= 1'b0;
                            i1b_valid <= 1'b0;
                            i2_valid <= 1'b0;
                            state <= S_DONE;
                        end else begin
                            set_mem[i2_widx] <= i2_next;
                            wr_valid <= 1'b1;
                            wr_addr <= i2_widx;
                            wr_data <= i2_next;
                            if (!i2_already) begin
                                obs_blocks <= obs_blocks + 32'd1;
                                obs_population <= obs_population + i2_block_len;
                            end
                        end
                    end
                    //: The exit is guarded by the fault term as well as the
                    //: pipeline-empty term: a refusal on the last id must not be
                    //: overwritten by a later assignment in this same block.
                    if ((ing_issued >= r_id_count) && !i1_valid && !i1b_valid &&
                        !i2_valid && (error_code == ERR_NONE)) begin
                        state <= S_BOUND;
                    end
                end
                // -- the declared population bound, before the first write ----
                S_BOUND: begin
                    if ((r_max_pop != 32'd0) && (obs_population > r_max_pop)) begin
                        error_code <= ERR_SHAPE;
                        error_detail <= DET_POPULATION;
                        error_value <= obs_population;
                        state <= S_DONE;
                    end else begin
                        e_word <= 32'd0;
                        e_grp <= 32'd0;
                        e_sub <= {SUB_W{1'b0}};
                        s1_valid <= 1'b0;
                        emit_gap <= 32'd0;
                        state <= S_EMIT;
                    end
                end
                // -- emit: II = 1 output word per cycle -----------------------
                S_EMIT: begin
                    // stage 1: fetch the bitmap word for e_word and latch the
                    // control that selects the sub-word.
                    if (e_word < r_mask_words) begin
                        s1_valid <= 1'b1;
                        s1_word <= e_word;
                        s1_sub <= e_sub;
                        s1_set_q <= (e_grp < SET_WORDS[31:0])
                                    ? set_mem[e_grp[SET_AW-1:0]]
                                    : {WORD_BITS{1'b0}};
                        e_word <= e_word + 32'd1;
                        if ({{(32-SUB_W){1'b0}}, e_sub} + 32'd1 >= BLOCK[31:0]) begin
                            e_sub <= {SUB_W{1'b0}};
                            e_grp <= e_grp + 32'd1;
                        end else begin
                            e_sub <= e_sub + {{(SUB_W-1){1'b0}}, 1'b1};
                        end
                    end else begin
                        s1_valid <= 1'b0;
                    end
                    // stage 2: expand, tail-mask, emit.  Registered, no stall.
                    if (s1_valid) begin
                        out_we <= 1'b1;
                        out_addr <= r_out_base + s1_word;
                        out_data <= emit_word;
                        obs_out_count <= obs_out_count + 32'd1;
                        if (obs_out_count != 32'd0) begin
                            if (emit_gap + 32'd1 > obs_emit_gap_max)
                                obs_emit_gap_max <= emit_gap + 32'd1;
                        end
                        emit_gap <= 32'd0;
                    end else begin
                        emit_gap <= emit_gap + 32'd1;
                    end
                    if ((e_word >= r_mask_words) && !s1_valid) state <= S_DRAIN;
                end
                S_DRAIN: begin
                    state <= S_DONE;
                end
                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    i1_valid <= 1'b0;
                    i1b_valid <= 1'b0;
                    i2_valid <= 1'b0;
                    s1_valid <= 1'b0;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
