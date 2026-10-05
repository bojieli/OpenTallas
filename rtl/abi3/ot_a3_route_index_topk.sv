// ROUTE.INDEX_TOPK: DeepSeek V4's compressed-index selection.
//
// ``index_topk_indices`` and ``stable_topk_bf16`` in
// runtime/reference/selection.py are the authority, and between them they say
// exactly three things:
//
//   * mask every compression group that is not complete at this query to
//     negative infinity -- ``causal_mask:
//     compressed_group_completed_before_position``;
//   * select k of them by (rank, value, -index) descending, which is
//     ``TIE_POLICY = score_descending_then_logical_index_ascending``;
//   * emit each selection plus the view offset, or -1 where the selection
//     landed on a masked slot.
//
// THE WHOLE ORDERING IS ONE UNSIGNED INTEGER COMPARISON, which is what makes
// this tractable. A BF16 code maps monotonically to 16 unsigned bits, and
// appending the COMPLEMENTED logical index makes a smaller index the larger key
// -- exactly the reference's ``-index`` term. So the key is
//
//     {monotone(score), ~index}
//
// and "top k by the reference's policy" is "largest k keys", with no separate
// tie handling anywhere.
//
// ALL ZEROS COLLAPSE FIRST. The map sends 0x8000 (negative zero) above 0x0000,
// but the reference's key is the exact VALUE, where the two zeros are equal and
// the tie falls to the index. Mapping them apart reverses that tie, so a zero
// of either sign becomes positive zero before the map -- the same correction
// ot_a3_route_biased_topk needed at 32 bits.
//
// THE SELECTION IS A SYSTOLIC SORTED-INSERTION ARRAY, one candidate per cycle
// for however many candidates the descriptor declares -- up to 49,152 at the
// shipped span of 196,608 tokens over a compression ratio of four. TOPK_MAX
// cells each hold one key of a descending-sorted list; a cell shifts, takes the
// arriving key, or holds, decided by its own comparison and its left
// neighbour's:
//
//     gt[i] && gt[i-1]  -> a[i] <= a[i-1]   the key belongs further left
//     gt[i] && !gt[i-1] -> a[i] <= key      this is its place
//     !gt[i]            -> a[i] unchanged
//
// The list stays sorted, so gt is monotone falling and exactly one cell sees
// the insert pattern. Throughput is one candidate per cycle regardless of k,
// against a sort of the whole candidate set, and the emitted order is the
// array's own order -- already the reference's.
module ot_a3_route_index_topk #(
    parameter integer TOPK_MAX = 512,
    //: 16 bits index up to 65,535 candidates, which covers the shipped
    //: 49,152 with room; the key is the score above the complemented index.
    parameter integer INDEX_BITS = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,

    input  wire [31:0] cfg_candidates,
    input  wire [31:0] cfg_top_k,
    //: How many leading candidates are unmasked. The reference computes this as
    //: (query + 1) / ratio while prefilling and the whole candidate count while
    //: decoding, so the caller resolves it and this engine applies it.
    input  wire [31:0] cfg_valid_count,
    input  wire [31:0] cfg_offset,
    input  wire [31:0] cfg_score_base,
    input  wire [31:0] cfg_out_base,

    output reg         score_rd_en,
    output reg  [31:0] score_rd_addr,
    input  wire [31:0] score_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] selected_count,
    //: The candidates that were actually read, which the descriptor's counters
    //: separate from the masked tail.
    output reg  [31:0] candidates_read
);
    localparam integer KEY_BITS = 16 + INDEX_BITS;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_FILL  = 3'd1;
    localparam [2:0] S_DRAIN = 3'd2;
    localparam [2:0] S_EMIT  = 3'd3;
    localparam [2:0] S_DONE  = 3'd4;

    reg [2:0]  state;
    reg [31:0] cursor, emit_index, emit_count;
    //: THE INDEX TRAVELS WITH THE READ, two stages deep, because the cursor
    //: advances every cycle and the bank answers two cycles after the address
    //: leaves. Taking the live cursor when the score arrives labels every
    //: candidate with the index two ahead of it, which is a correct selection
    //: of the wrong rows -- the leading slots came out exactly two high.
    reg [31:0] rd_index, data_index;
    reg [1:0]  rdphase;
    reg [KEY_BITS-1:0] cells [0:TOPK_MAX-1];
    integer i;

    //: THE KEY IS COMBINATIONAL, derived from whatever the read pipe is
    //: presenting this cycle, and the insertion is gated on that pipe's own
    //: valid. Registering the key into a third stage instead cost two distinct
    //: defects at once: the reset value of the score bus became a spurious
    //: candidate at index zero, and the last real candidate's key was never
    //: formed because the sequencer left the fill state before it arrived.
    //: A read pipe that carries its own valid and its own index has neither.
    reg                 rd_valid, data_valid;
    reg [31:0]          keys_formed;

    wire [15:0] score_code = score_rd_data[15:0];
    //: ANY NONFINITE SCORE IS REFUSED, not just a NaN.
    //: ``index_topk_indices`` validates its scores with ``finite=True``, so an
    //: infinity on the way in is a refusal and not a value to be ordered -- the
    //: only negative infinity in this operator is the one the causal mask
    //: introduces, which never passes through this check.
    wire        score_nonfinite = (score_code[14:7] == 8'hff);
    wire [15:0] score_zeroed = (score_code[14:0] == 15'd0) ? 16'h0000 : score_code;
    wire [15:0] monotone = score_zeroed[15]
        ? ~score_zeroed
        : (score_zeroed | 16'h8000);
    //: A masked candidate is negative infinity, which the map sends to the
    //: bottom -- so masking needs no separate path through the array.
    //:
    //: THE PARTICULAR VALUE DOES NOT MATTER, only that it is below every real
    //: score's. Over all 65,024 finite BF16 codes the map's range is
    //: [0x0080, 0xff7f], so 0x007f and 0x0000 order masked candidates
    //: identically and a mutation swapping them survives -- an equivalence
    //: rather than a gap. 0x007f is kept because it IS the map of the
    //: negative infinity the reference substitutes, so the two read alike.
    //:
    //: The same bound is what makes the cells' initial fill of zero safe: no
    //: real key can be zero, so the N keys of an N-candidate row always occupy
    //: the top N cells and the emit walk never reads a fill value. It is also
    //: why the cell comparison may be > or >= indifferently: every key carries
    //: its own index, so no two keys are ever equal and none equals the fill.
    wire [15:0] monotone_masked =
        (data_index < cfg_valid_count) ? monotone : 16'h007f;

    //: gt[i] for every cell, and the shifted-by-one companion the insert
    //: decision needs. Cell zero's left neighbour is conceptually +infinity, so
    //: its gt[i-1] is zero and it inserts whenever it compares true.
    wire [KEY_BITS-1:0] key = {monotone_masked, ~data_index[INDEX_BITS-1:0]};
    wire                key_live = data_valid && !score_nonfinite;
    reg [TOPK_MAX-1:0] cell_gt;
    always @* begin
        for (i = 0; i < TOPK_MAX; i = i + 1)
            cell_gt[i] = key_live && (key > cells[i]);
    end

    wire [31:0] emit_key_index_raw =
        {{(32-INDEX_BITS){1'b0}}, ~cells[emit_index[$clog2(TOPK_MAX)-1:0]][INDEX_BITS-1:0]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; busy <= 1'b0; done <= 1'b0;
            error_code <= ot_a3_engine_pkg::ERR_NONE;
            selected_count <= 32'd0; candidates_read <= 32'd0;
            cursor <= 32'd0; emit_index <= 32'd0; emit_count <= 32'd0;
            rd_index <= 32'd0; data_index <= 32'd0;
            rdphase <= 2'd0;
            score_rd_en <= 1'b0; score_rd_addr <= 32'd0;
            out_we <= 1'b0; out_addr <= 32'd0; out_data <= 32'd0;
            rd_valid <= 1'b0; data_valid <= 1'b0; keys_formed <= 32'd0;
            for (i = 0; i < TOPK_MAX; i = i + 1) cells[i] <= {KEY_BITS{1'b0}};
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            score_rd_en <= 1'b0;

            //: The insertion itself, independent of the sequencer: whichever
            //: cycle a key is live, every cell acts on it.
            if (key_live) begin
                for (i = 0; i < TOPK_MAX; i = i + 1) begin
                    if (cell_gt[i]) begin
                        if (i == 0) cells[0] <= key;
                        else cells[i] <= cell_gt[i-1] ? cells[i-1] : key;
                    end
                end
            end

            case (state)
                S_IDLE: if (start) begin
                    if (cfg_candidates == 32'd0 ||
                        cfg_top_k == 32'd0 ||
                        cfg_top_k > TOPK_MAX[31:0] ||
                        cfg_valid_count > cfg_candidates ||
                        cfg_candidates > {{(32-INDEX_BITS){1'b0}},
                                          {INDEX_BITS{1'b1}}}) begin
                        error_code <= ot_a3_engine_pkg::ERR_SHAPE;
                        done <= 1'b1;
                        busy <= 1'b0;
                    end else begin
                        error_code <= ot_a3_engine_pkg::ERR_NONE;
                        busy <= 1'b1;
                        //: Every cell starts at the smallest key, so the first
                        //: candidates fill the list without a special case.
                        for (i = 0; i < TOPK_MAX; i = i + 1)
                            cells[i] <= {KEY_BITS{1'b0}};
                        cursor <= 32'd0;
                        rd_index <= 32'd0;
                        data_index <= 32'd0;
                        rd_valid <= 1'b0;
                        data_valid <= 1'b0;
                        keys_formed <= 32'd0;
                        rdphase <= 2'd0;
                        selected_count <= 32'd0;
                        candidates_read <= 32'd0;
                        state <= S_FILL;
                    end
                end

                //: One candidate per cycle. The address leaves, the bank
                //: answers the cycle after, and the key is live the cycle after
                //: that -- so the pipe carries a valid and an index of its own
                //: and the sequencer only has to stop issuing and wait for the
                //: count.
                S_FILL: begin
                    if (cursor < cfg_candidates) begin
                        score_rd_en <= 1'b1;
                        score_rd_addr <= cfg_score_base + cursor;
                        rd_index <= cursor;
                        rd_valid <= 1'b1;
                        cursor <= cursor + 32'd1;
                    end else begin
                        rd_valid <= 1'b0;
                    end
                    data_valid <= rd_valid;
                    data_index <= rd_index;
                    if (data_valid) begin
                        if (score_nonfinite) begin
                            //: The reference raises on a nonfinite score rather
                            //: than ordering it.
                            error_code <= ot_a3_engine_pkg::ERR_SELECT_NONFINITE;
                            busy <= 1'b0;
                            done <= 1'b1;
                            rd_valid <= 1'b0;
                            data_valid <= 1'b0;
                            state <= S_IDLE;
                        end else begin
                            keys_formed <= keys_formed + 32'd1;
                            candidates_read <= candidates_read + 32'd1;
                            if (keys_formed + 32'd1 >= cfg_candidates) begin
                                //: min(top_k, candidates), the reference's own
                                //: selected_count.
                                emit_count <= (cfg_top_k < cfg_candidates)
                                            ? cfg_top_k : cfg_candidates;
                                emit_index <= 32'd0;
                                state <= S_DRAIN;
                            end
                        end
                    end
                end

                //: One cycle for the last key's insertion to land, since the
                //: cells are written by the edge that ends the cycle in which
                //: the key was live.
                S_DRAIN: begin
                    data_valid <= 1'b0;
                    state <= S_EMIT;
                end

                //: The array is already in the reference's order, so emitting
                //: is a walk. A selection that landed on a masked slot becomes
                //: -1 rather than an index the view does not have.
                S_EMIT: begin
                    if (emit_index >= emit_count) begin
                        state <= S_DONE;
                    end else begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base + emit_index;
                        out_data <= (emit_key_index_raw < cfg_valid_count)
                            ? (emit_key_index_raw + cfg_offset)
                            : 32'hffff_ffff;
                        selected_count <= selected_count + 32'd1;
                        emit_index <= emit_index + 32'd1;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
