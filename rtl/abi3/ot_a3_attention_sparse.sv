// ATTENTION.SPARSE: the whole operator, composed from its qualified parts.
//
// ``_execute_tile`` in runtime/tensor_accelerator/sparse_attention.py is the
// authority for the composition, and this sequencer is its loop nest:
//
//   for head:
//     for block in ascending 64-slot source blocks:
//       gather      -- ot_a3_attention_kv_index     (index -> lane validity)
//       QK          -- ot_a3_attention_qk_walk      (ascending head_dim)
//       online max, -- ot_a3_attention_denominator  (which itself composes
//       rescale,       ot_a3_attention_softmax_block and
//       block sum      ot_a3_reduction_balanced_sum)
//       AV          -- ot_a3_attention_av_walk      (rescale, ascending slot)
//     sink, divide, narrow -- ot_a3_attention_epilogue
//
// Every numeric decision therefore lives in a part that was qualified against
// the reference on its own, and what this file adds is only the order they run
// in and the values handed between them. That is deliberate: the ordering is
// what a composition can get wrong, and it is checkable end to end.
//
// ONE READ PORT SERVES EVERYTHING. The QK walk issues its query reads in
// S_QHOLD and its KV reads in S_WALK, never in the same cycle, and the AV walk
// reads KV only while the QK walk is idle -- so the five views this operator
// binds are reachable through a single muxed port rather than five.
//
// THE PADDED TAIL IS RUN, NOT SKIPPED. A source block shorter than 64 slots
// still walks all 64 lanes: the reference's own masking drives an invalid lane's
// offset to -inf, its probability to exactly zero, and a zero-weighted
// product-add leaves the accumulator alone -- so the tail is numerically inert
// rather than approximated, and the padding never reaches an address, because
// the walks substitute the contract's zero element for an invalid lane. The
// operator's counters still separate the two, which is what
// ``counter_scope: logical_source_work_separates_valid_kv_reads_from_padding``
// asks for.
module ot_a3_attention_sparse #(
    //: The source block is frozen at 64 slots by the numeric contract
    //: (``block_size``/``group_size``), not by this implementation.
    parameter integer LANES         = 64,
    parameter integer CHANNELS_MAX  = 512,
    parameter integer HEADS_MAX     = 128,
    parameter integer KV_ROWS_MAX   = 65536
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,

    //: The five views an ATTENTION_SPARSE descriptor binds: query, KV, window
    //: indices, attention sink, and the output row.
    input  wire [31:0] cfg_query_base,
    input  wire [31:0] cfg_kv_base,
    input  wire [31:0] cfg_index_base,
    input  wire [31:0] cfg_sink_base,
    input  wire [31:0] cfg_out_base,

    //: The descriptor's span. ``sparse_attention_bf16_codes`` takes
    //: ``[span, heads, head_dim]`` queries and ``[span, slots]`` indices, and a
    //: shipped instance's iteration domain carries five tokens, so the row loop
    //: is part of the operator rather than the caller's.
    input  wire [31:0] cfg_rows,
    input  wire [31:0] cfg_heads,
    input  wire [31:0] cfg_head_dim,
    input  wire [31:0] cfg_slots,
    input  wire [31:0] cfg_kv_rows,
    input  wire [31:0] cfg_scale_code,

    //: THE SINK HAS ITS OWN PORT, and the other three inputs share one.
    //:
    //: Query, KV and the window indices are all results an earlier operator
    //: wrote, and they reach this engine through one muxed read because the
    //: three never want it at once: the QK walk issues its query reads and its
    //: KV reads in different states, and the AV walk reads only while the QK
    //: walk is idle. A select, not an arbiter -- and an arbiter would be a
    //: latent stall the walks have no back-pressure input to absorb.
    //:
    //: The sink is the one operand that is not such a result: it is a
    //: CHECKPOINT tensor, named ``layers.<n>.attn.attn_sink`` with no producing
    //: operator. ROUTE.BIASED_TOPK's bias -- ``ffn.gate.bias``, a checkpoint
    //: operand of exactly the same kind -- is read on the bridge's SECOND
    //: operand port rather than muxed onto the first, so this engine matches
    //: that shape.
    //:
    //: Not because the bank differs: both of the bridge's operand ports assert
    //: reads_result for these families, and only TENSOR.MATMUL reads the weight
    //: store, so a checkpoint operand is staged into the result bank like any
    //: other. Splitting the port is about matching the precedent that already
    //: carries a checkpoint operand, not about reaching a different store.
    output reg         mem_rd_en,
    output reg  [31:0] mem_rd_addr,
    input  wire [31:0] mem_rd_data,
    output reg         sink_rd_en,
    output reg  [31:0] sink_rd_addr,
    input  wire [31:0] sink_rd_data,
    output wire        mem_we,
    output wire [31:0] mem_wr_addr,
    output wire [31:0] mem_wr_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg         nonfinite,

    //: Separated the way the descriptor's counter scope asks for.
    output reg  [31:0] valid_row_reads,
    output reg  [31:0] padding_lanes_seen,
    output reg  [31:0] rows_emitted,
    output reg  [31:0] saturation_count
);
    localparam integer LANE_IX = $clog2(LANES);

    localparam [4:0] S_IDLE    = 5'd0;
    localparam [4:0] S_IDXRD   = 5'd1;
    localparam [4:0] S_KVIDX   = 5'd2;
    localparam [4:0] S_QK      = 5'd3;
    localparam [4:0] S_DEN     = 5'd4;
    localparam [4:0] S_AV      = 5'd5;
    localparam [4:0] S_NEXTBLK = 5'd6;
    localparam [4:0] S_SINKRD  = 5'd7;
    localparam [4:0] S_EPI     = 5'd8;
    localparam [4:0] S_NEXTHD  = 5'd9;
    localparam [4:0] S_NEXTROW = 5'd10;
    localparam [4:0] S_DONE    = 5'd11;

    reg [4:0]  state;
    reg [31:0] row, head, block, blocks_total, slot_cursor;
    reg [1:0]  rdphase;
    reg [31:0] idx [0:LANES-1];
    reg [31:0] sink_code;
    reg        pulse_kvidx, pulse_qk, pulse_av, pulse_epi, den_valid;
    integer i;

    // -- index gather ---------------------------------------------------------
    reg  [LANES*32-1:0] index_bus;
    wire [LANES-1:0]    lane_valid;
    wire [31:0]         live_count;
    wire                kvidx_done;
    wire [7:0]          kvidx_err;
    ot_a3_attention_kv_index #(.SLOTS(LANES)) gather (
        .clk(clk), .rst_n(rst_n), .start(pulse_kvidx),
        .cfg_kv_rows(cfg_kv_rows), .indices(index_bus),
        .busy(), .done(kvidx_done), .lane_valid(lane_valid),
        .live_count(live_count), .error_code(kvidx_err)
    );

    //: ``gather = np.where(lane_valid, block_indices, 0)`` -- an invalid slot is
    //: addressed at row zero and then contributes a zero element, so it never
    //: reaches an out-of-range row.
    reg [LANES*32-1:0] lane_row;
    always @(*) begin
        for (i = 0; i < LANES; i = i + 1)
            lane_row[i*32 +: 32] = lane_valid[i] ? idx[i] : 32'd0;
    end

    // -- QK ------------------------------------------------------------------
    wire                qk_q_en, qk_kv_en;
    wire [31:0]         qk_q_addr, qk_kv_addr;
    wire                qk_done;
    wire [LANES*32-1:0] scores;
    wire [7:0]          qk_err;
    wire [31:0]         qk_macs;
    ot_a3_attention_qk_walk #(.LANES(LANES)) qk (
        .clk(clk), .rst_n(rst_n), .start(pulse_qk),
        .cfg_head_dim(cfg_head_dim),
        .cfg_q_base(cfg_query_base
                    + (row * cfg_heads + head) * cfg_head_dim),
        .cfg_kv_stride(cfg_head_dim), .cfg_kv_base(cfg_kv_base),
        .cfg_scale_code(cfg_scale_code),
        .lane_valid(lane_valid), .lane_row(lane_row),
        .q_rd_en(qk_q_en), .q_rd_addr(qk_q_addr), .q_rd_data(mem_rd_data),
        .kv_rd_en(qk_kv_en), .kv_rd_addr(qk_kv_addr), .kv_rd_data(mem_rd_data),
        .busy(), .done(qk_done), .scores(scores),
        .error_code(qk_err), .mac_count(qk_macs)
    );

    // -- online max, rescale, denominator ------------------------------------
    wire                den_ready, den_done;
    wire [31:0]         running_max, running_sums, block_rescale;
    wire [LANES*32-1:0] block_probabilities;
    wire [7:0]          den_err;
    ot_a3_attention_denominator #(.LANES(LANES)) online (
        .clk(clk), .rst_n(rst_n),
        .block_valid(den_valid), .block_first(block == 32'd0),
        .lane_valid(lane_valid), .scores(scores),
        .block_ready(den_ready), .running_max(running_max),
        .running_sums(running_sums), .block_rescale(block_rescale),
        .block_probabilities(block_probabilities),
        .block_done(den_done), .busy(), .error_code(den_err),
        .blocks_retired()
    );

    //: ``probability_rounding: binary32_to_bf16_rne_once_before_av`` -- ONCE,
    //: here, on the way into the AV walk, through the same narrowing the
    //: epilogue uses and the same one the reference's _narrow was checked
    //: against.
    reg [LANES*16-1:0] lane_prob;
    reg                prob_nonfinite;
    reg [18:0]         narrowed_probability;
    always @(*) begin
        prob_nonfinite = 1'b0;
        for (i = 0; i < LANES; i = i + 1) begin
            narrowed_probability = ot_fp32_rne_pkg::fp32_to_bf16_rne(
                block_probabilities[i*32 +: 32]);
            lane_prob[i*16 +: 16] = narrowed_probability[15:0];
            if (narrowed_probability[18:17] != 2'd0) prob_nonfinite = 1'b1;
        end
    end

    // -- AV ------------------------------------------------------------------
    wire        av_kv_en, av_done, av_nonfinite;
    wire [31:0] av_kv_addr, av_macs;
    wire [7:0]  av_err;
    //: PASSED STRAIGHT THROUGH, NOT MUXED ON THE ENABLE. The epilogue raises
    //: acc_rd_en for one cycle and captures the data on the cycle AFTER that, so
    //: gating the address on the enable feeds it channel zero every time. Its
    //: own address register holds between reads, which is all the hold needed.
    wire [31:0] acc_rd_addr_q = epi_acc_addr;
    wire [31:0] acc_rd_data;
    ot_a3_attention_av_walk #(
        .CHANNELS_MAX(CHANNELS_MAX), .LANES_MAX(LANES)
    ) accumulate (
        .clk(clk), .rst_n(rst_n), .start(pulse_av),
        .cfg_clear(block == 32'd0), .cfg_channels(cfg_head_dim),
        .cfg_lanes(LANES[31:0]), .cfg_rescale_code(block_rescale),
        .cfg_kv_base(cfg_kv_base), .cfg_kv_stride(cfg_head_dim),
        .lane_valid(lane_valid), .lane_row(lane_row), .lane_prob(lane_prob),
        .kv_rd_en(av_kv_en), .kv_rd_addr(av_kv_addr), .kv_rd_data(mem_rd_data),
        .out_rd_addr(acc_rd_addr_q), .out_rd_data(acc_rd_data),
        .busy(), .done(av_done), .error_code(av_err),
        .nonfinite(av_nonfinite), .mac_count(av_macs)
    );

    // -- the closing stage ----------------------------------------------------
    wire        epi_acc_en, epi_done;
    wire [31:0] epi_acc_addr;
    wire [7:0]  epi_err;
    wire [31:0] epi_out_count, epi_sat;
    ot_a3_attention_epilogue epilogue (
        .clk(clk), .rst_n(rst_n), .start(pulse_epi),
        .cfg_width(cfg_head_dim), .cfg_acc_base(32'd0),
        .cfg_out_base(cfg_out_base
                      + (row * cfg_heads + head) * cfg_head_dim),
        .cfg_final_max(running_max), .cfg_final_sums(running_sums),
        .cfg_sink_code(sink_code),
        .acc_rd_en(epi_acc_en), .acc_rd_addr(epi_acc_addr),
        .acc_rd_data(acc_rd_data),
        .out_we(mem_we), .out_addr(mem_wr_addr), .out_data(mem_wr_data),
        .busy(), .done(epi_done), .error_code(epi_err),
        .sink_exp(), .final_denominator(),
        .out_count(epi_out_count), .saturation_count(epi_sat)
    );

    // -- the one read port ----------------------------------------------------
    //: The three consumers are in disjoint states, so this is a select, not an
    //: arbiter -- and an arbiter here would be a latent stall the walks have no
    //: back-pressure input to absorb.
    always @(*) begin
        if (state == S_QK && qk_q_en) begin
            mem_rd_en = 1'b1; mem_rd_addr = qk_q_addr;
        end else if (state == S_QK && qk_kv_en) begin
            mem_rd_en = 1'b1; mem_rd_addr = qk_kv_addr;
        end else if (state == S_AV && av_kv_en) begin
            mem_rd_en = 1'b1; mem_rd_addr = av_kv_addr;
        end else if (state == S_IDXRD && rdphase == 2'd1
                     && (block * LANES[31:0] + slot_cursor < cfg_slots)) begin
            //: A SLOT PAST THE DESCRIPTOR'S COUNT IS NOT READ AT ALL. The index
            //: view is cfg_slots wide, so issuing the remaining reads of a
            //: partial block addresses whatever the placement table put after
            //: it. The value was already discarded in favour of the contract's
            //: implicit -1; suppressing the address as well is what keeps the
            //: operator inside the view it was bound to.
            mem_rd_en = 1'b1;
            mem_rd_addr = cfg_index_base + row * cfg_slots
                        + block * LANES[31:0] + slot_cursor;
        end else begin
            mem_rd_en = 1'b0; mem_rd_addr = 32'd0;
        end
    end

    //: ceil(cfg_slots / LANES), with the tail block's absent slots implicitly
    //: padded -- ``tail_padding: implicit_negative_one_to_64_slot_block``.
    wire [31:0] blocks_needed = (cfg_slots + LANES[31:0] - 32'd1) / LANES[31:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; busy <= 1'b0; done <= 1'b0;
            error_code <= ot_a3_engine_pkg::ERR_NONE; nonfinite <= 1'b0;
            sink_rd_en <= 1'b0; sink_rd_addr <= 32'd0;
            row <= 32'd0; head <= 32'd0; block <= 32'd0; blocks_total <= 32'd0;
            slot_cursor <= 32'd0; rdphase <= 2'd0; sink_code <= 32'd0;
            pulse_kvidx <= 1'b0; pulse_qk <= 1'b0; pulse_av <= 1'b0;
            pulse_epi <= 1'b0; den_valid <= 1'b0;
            valid_row_reads <= 32'd0; padding_lanes_seen <= 32'd0;
            rows_emitted <= 32'd0; saturation_count <= 32'd0;
            index_bus <= {(LANES*32){1'b0}};
            for (i = 0; i < LANES; i = i + 1) idx[i] <= 32'd0;
        end else begin
            done <= 1'b0;
            sink_rd_en <= 1'b0;
            pulse_kvidx <= 1'b0; pulse_qk <= 1'b0; pulse_av <= 1'b0;
            pulse_epi <= 1'b0; den_valid <= 1'b0;
            if (av_nonfinite || prob_nonfinite) nonfinite <= 1'b1;

            case (state)
                S_IDLE: if (start) begin
                    if (cfg_rows == 32'd0 ||
                        cfg_heads == 32'd0 || cfg_heads > HEADS_MAX[31:0] ||
                        cfg_head_dim == 32'd0 ||
                        cfg_head_dim > CHANNELS_MAX[31:0] ||
                        cfg_slots == 32'd0 ||
                        cfg_kv_rows == 32'd0 ||
                        cfg_kv_rows > KV_ROWS_MAX[31:0]) begin
                        error_code <= ot_a3_engine_pkg::ERR_SHAPE;
                        done <= 1'b1; busy <= 1'b0;
                    end else begin
                        error_code <= ot_a3_engine_pkg::ERR_NONE;
                        busy <= 1'b1; nonfinite <= 1'b0;
                        row <= 32'd0; head <= 32'd0; block <= 32'd0;
                        blocks_total <= blocks_needed;
                        valid_row_reads <= 32'd0;
                        padding_lanes_seen <= 32'd0;
                        rows_emitted <= 32'd0; saturation_count <= 32'd0;
                        slot_cursor <= 32'd0; rdphase <= 2'd0;
                        state <= S_IDXRD;
                    end
                end

                //: One index word per slot of this block. Slots past cfg_slots
                //: are not read at all -- they are the contract's implicit -1.
                S_IDXRD: begin
                    if (rdphase == 2'd0) begin
                        rdphase <= 2'd1;
                    end else if (rdphase == 2'd1) begin
                        rdphase <= 2'd2;
                    end else begin
                        //: A slot past the descriptor's count is the
                        //: contract's implicit -1, not whatever the view holds
                        //: at that address.
                        idx[slot_cursor[LANE_IX-1:0]] <=
                            (block * LANES[31:0] + slot_cursor < cfg_slots)
                                ? mem_rd_data : 32'hFFFF_FFFF;
                        rdphase <= 2'd0;
                        if (slot_cursor + 32'd1 >= LANES[31:0]) begin
                            slot_cursor <= 32'd0;
                            state <= S_KVIDX;
                        end else begin
                            slot_cursor <= slot_cursor + 32'd1;
                        end
                    end
                end

                S_KVIDX: begin
                    for (i = 0; i < LANES; i = i + 1)
                        index_bus[i*32 +: 32] <= idx[i];
                    pulse_kvidx <= 1'b1;
                    state <= S_QK;
                    rdphase <= 2'd0;
                end

                S_QK: begin
                    if (rdphase == 2'd0) begin
                        //: kv_index settles first; its validity mask is an
                        //: input to the walk's very first address.
                        if (kvidx_done) begin
                            if (kvidx_err != 8'h00) begin
                                error_code <= kvidx_err;
                                state <= S_DONE;
                            end else begin
                                valid_row_reads <= valid_row_reads + live_count;
                                padding_lanes_seen <= padding_lanes_seen
                                                    + (LANES[31:0] - live_count);
                                pulse_qk <= 1'b1;
                                rdphase <= 2'd1;
                            end
                        end
                    end else if (qk_done) begin
                        if (qk_err != 8'h00) begin
                            error_code <= qk_err;
                            state <= S_DONE;
                        end else begin
                            state <= S_DEN;
                            rdphase <= 2'd0;
                        end
                    end
                end

                S_DEN: begin
                    if (rdphase == 2'd0) begin
                        if (den_ready) begin
                            den_valid <= 1'b1;
                            rdphase <= 2'd1;
                        end
                    end else if (den_done) begin
                        if (den_err != 8'h00) begin
                            error_code <= den_err;
                            state <= S_DONE;
                        end else begin
                            state <= S_AV;
                            rdphase <= 2'd0;
                        end
                    end
                end

                S_AV: begin
                    if (rdphase == 2'd0) begin
                        pulse_av <= 1'b1;
                        rdphase <= 2'd1;
                    end else if (av_done) begin
                        if (av_err != 8'h00) begin
                            error_code <= av_err;
                            state <= S_DONE;
                        end else begin
                            state <= S_NEXTBLK;
                        end
                    end
                end

                S_NEXTBLK: begin
                    rdphase <= 2'd0;
                    if (block + 32'd1 >= blocks_total) begin
                        state <= S_SINKRD;
                    end else begin
                        block <= block + 32'd1;
                        slot_cursor <= 32'd0;
                        state <= S_IDXRD;
                    end
                end

                S_SINKRD: begin
                    if (rdphase == 2'd0) begin
                        sink_rd_en <= 1'b1;
                        sink_rd_addr <= cfg_sink_base + head;
                        rdphase <= 2'd1;
                    end else if (rdphase == 2'd1) begin
                        rdphase <= 2'd2;
                    end else begin
                        sink_code <= sink_rd_data;
                        rdphase <= 2'd0;
                        state <= S_EPI;
                    end
                end

                S_EPI: begin
                    if (rdphase == 2'd0) begin
                        pulse_epi <= 1'b1;
                        rdphase <= 2'd1;
                    end else if (epi_done) begin
                        if (epi_err != 8'h00) begin
                            error_code <= epi_err;
                            state <= S_DONE;
                        end else begin
                            rows_emitted <= rows_emitted + epi_out_count;
                            saturation_count <= saturation_count + epi_sat;
                            state <= S_NEXTHD;
                        end
                    end
                end

                S_NEXTHD: begin
                    rdphase <= 2'd0;
                    if (head + 32'd1 >= cfg_heads) begin
                        state <= S_NEXTROW;
                    end else begin
                        head <= head + 32'd1;
                        block <= 32'd0;
                        slot_cursor <= 32'd0;
                        state <= S_IDXRD;
                    end
                end

                //: Every row restarts the online loop from its first block, so
                //: the running maximum and the denominator carry nothing across
                //: a row boundary -- block_first does that, driven off `block`.
                S_NEXTROW: begin
                    if (row + 32'd1 >= cfg_rows) begin
                        state <= S_DONE;
                    end else begin
                        row <= row + 32'd1;
                        head <= 32'd0;
                        block <= 32'd0;
                        slot_cursor <= 32'd0;
                        state <= S_IDXRD;
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
