`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROUTE.BIASED_TOPK -- DeepSeek's routing gate.
//
// ``input_view_0`` is [groups, experts] scores and ``input_view_1`` the
// per-expert selection bias, [experts] broadcast over the groups or
// [groups, experts].  Selection ranks ``score + bias`` in binary32;
// ``output_view_0`` is the U32 selected expert IDs [groups, k] and
// ``output_view_1``, when bound, the **UNBIASED** scores of those experts.  That
// asymmetry is the whole of the biased-gate contract: the bias steers which
// experts win and never appears in what the reduction later weights by.
//
// TIES GO TO THE LOWER EXPERT ID, and this walk gets that for free.  The
// reference is ``argsort(-keys, kind="stable")``, so an equal key keeps the
// earlier index; the scan visits experts in ascending ID order, so an arriving
// element always has a higher ID than anything already held and must therefore
// lose a tie.  The insertion test is a STRICT greater-than, and that single
// choice is the tie rule -- a >= would silently prefer the later expert.
//
// THE COMPARE IS ON A MONOTONIC INTEGER, NOT A FLOAT UNIT.  For finite IEEE
// binary32, mapping ``c`` to ``c[31] ? ~c : (c | 0x80000000)`` makes unsigned
// integer order agree with float order, negatives included.  Non-finite keys are
// refused before this matters, so the map needs no NaN case and the selection
// needs no floating-point comparator at all.
//
// THE SHIPPED OPERANDS ARE FP32, WHICH THIS FIRST GOT WRONG.  Read off the
// descriptor tables at HEAD, every shipped ROUTE.BIASED_TOPK carries FP32
// scores, an FP32 bias, U32 selected ids and FP32 selected weights -- not the
// BF16 operands this engine was originally built against.  A BF16 operand
// cannot be ruled out for a future deployment, so the width is a config bit and
// both are admitted: a BF16 code is widened BY SHIFT, which is what the
// reference's ``widen`` does and is exact.
//
// THE KEY ADD IS THEREFORE A REAL BINARY32 ADD, on ot_fp32_add_rne_pipe -- five
// stages, one result per cycle, qualified bit-identical to
// ot_fp32_rne_pkg::fp32_add_rne over 898,081 cases.  ot_mac_bf16_fp32_pipe with
// b = BF16 1.0 was the original choice and only works while both operands are
// BF16.  The combinational authority in this position would cap the block near
// 155 MHz, which is what it did to two reduction engines.
//
// FULLY PIPELINED THROUGH THE SCAN: one expert per cycle, with the k-entry
// insertion consuming the MAC's output five cycles behind the read.
// ---------------------------------------------------------------------------
module ot_a3_route_biased_topk #(
    parameter integer MAX_K = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_groups,
    input  wire [31:0] cfg_experts,
    input  wire [31:0] cfg_topk,          //: 1..MAX_K and <= experts
    input  wire        cfg_has_bias,
    //: 1 when the bias is [experts] and broadcasts over every group.
    input  wire        cfg_bias_broadcast,
    //: 0 reads BF16 score and bias codes, 1 reads binary32. The shipped
    //: operators are 1; the BF16 path widens by shift, never by decode_bf16,
    //: because that canonicalises minus zero and the reference's widen does not.
    input  wire        cfg_operand_fp32,
    input  wire [31:0] cfg_score_base,
    input  wire [31:0] cfg_bias_base,
    input  wire [31:0] cfg_id_out_base,
    input  wire        cfg_has_weight_out,
    //: 0 stores the selected score as BF16, 1 widens it to binary32. The
    //: reference writes ``narrow(selected, weight_view)``, and ``selected`` is a
    //: widened BF16, so BF16 narrowing is the identity on the original code and
    //: an FP32 view wants that same code widened -- neither rounds.
    input  wire        cfg_weight_fp32,
    input  wire [31:0] cfg_weight_out_base,

    output reg         score_rd_en,
    output reg  [31:0] score_rd_addr,
    input  wire [31:0] score_rd_data,
    output reg         bias_rd_en,
    output reg  [31:0] bias_rd_addr,
    input  wire [31:0] bias_rd_data,

    output reg         id_we,
    output reg  [31:0] id_addr,
    output reg  [31:0] id_data,
    output reg         wgt_we,
    output reg  [31:0] wgt_addr,
    output reg  [31:0] wgt_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] selected_experts,
    output reg  [31:0] candidates
);
    // Re-declared rather than wildcard-imported: Icarus 11 turns a
    // wildcard-imported name used only in a port connection into an implicit
    // net, and the pinned Yosys 0.68 frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_SCAN  = 3'd1;
    localparam [2:0] S_DRAIN = 3'd2;
    localparam [2:0] S_EMIT  = 3'd3;
    localparam [2:0] S_NEXT  = 3'd4;
    localparam [2:0] S_DONE  = 3'd5;

    integer i;
    genvar  gi;

    reg [2:0]  state;
    reg [31:0] grp;
    reg [31:0] expert;
    reg [31:0] emit_slot;
    //: TWO EMIT PASSES, so the two write ports never fire in the same cycle.
    //: The engine's natural shape is to write an id and its weight together, and
    //: the issue bridge has ONE result write port -- so a caller with one port
    //: can mux the two, and a caller with two loses nothing by the ordering.
    //: Pass 0 writes the U32 ids, pass 1 the unbiased weights.
    reg        emit_pass;
    reg [31:0] score_row;     //: advanced by experts, never grp*experts
    reg [31:0] bias_row;      //: held at 0 while the bias broadcasts
    reg [31:0] id_row;        //: advanced by topk
    reg [31:0] drain;
    reg        fault_nonfinite;

    //: The held top-k, descending. ord is the monotonic integer the compare uses.
    reg [31:0] top_ord  [0:MAX_K-1];
    reg [31:0] top_id   [0:MAX_K-1];
    reg [31:0] top_score[0:MAX_K-1];
    reg [MAX_K-1:0] top_valid;

    wire cfg_bad = (cfg_groups == 32'd0) || (cfg_experts == 32'd0) ||
                   (cfg_topk == 32'd0) || (cfg_topk > MAX_K[31:0]) ||
                   (cfg_topk > cfg_experts);

    //: Widened by SHIFT for BF16, taken as-is for binary32. Exact both ways.
    wire [31:0] score_value = cfg_operand_fp32 ? score_rd_data
                                               : {score_rd_data[15:0], 16'h0000};
    wire [31:0] bias_value = cfg_operand_fp32 ? bias_rd_data
                                              : {bias_rd_data[15:0], 16'h0000};
    wire        score_nonfinite = (score_value[30:23] == 8'hff);
    wire        bias_nonfinite = (bias_value[30:23] == 8'hff);

    //: The key: RN(score + bias), or the score ALONE when there is no bias.
    //: Adding a zero is not a safe stand-in for the no-bias case: the authority
    //: returns +0 for (-0) + (+0), so a -0 score would come back as +0 and sort
    //: above itself. The reference's no-bias path is ``keys = scores.copy()``,
    //: so the adder is bypassed rather than fed an identity.
    wire        add_vin;
    wire [31:0] add_y;
    wire [1:0]  add_err;
    wire        add_vout;

    ot_fp32_add_rne_pipe key_add (
        .clk(clk), .rst_n(rst_n), .valid_in(add_vin),
        .a(score_value), .b(bias_value),
        .y(add_y), .err(add_err), .valid_out(add_vout)
    );

    //: THE ID MUST BE CAPTURED WITH THE ADDRESS, NOT AFTER IT.  ``expert``
    //: advances on the same edge that latches ``score_rd_addr``, so sampling the
    //: counter one stage later names the NEXT expert and every selected id comes
    //: out one too high -- a failure that leaves the scores, the count and the
    //: ordering all correct and is invisible to anything but an id check.
    reg [31:0] rd_id;
    //: One stage, because the memory read is registered: the address is on the
    //: bus during cycle C, so the data is valid during C+1, which is the cycle
    //: this stage's valid marks and the cycle the MAC samples at its end.
    reg        d_valid;
    reg [31:0] d_id;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            d_valid <= 1'b0; d_id <= 32'd0;
        end else begin
            d_valid <= score_rd_en;
            d_id <= rd_id;
        end
    end
    assign add_vin = d_valid & cfg_has_bias;
    //: Refused on the OPERAND, not the result: with no bias the adder is
    //: bypassed entirely, so its ``err`` would never see a nonfinite score.
    wire operand_nonfinite = d_valid &&
        (score_nonfinite || (cfg_has_bias && bias_nonfinite));

    //: The MAC's own latency carries the id and the unbiased score alongside the
    //: key, so the insertion sees a matched triple.  FIVE registrations --
    //: valid_in -> s1_v -> s2_v -> s3_v -> s4_v -> valid_out -- counted in
    //: ot_mac_bf16_fp32_pipe rather than assumed, and the companion's stage 0 is
    //: loaded on the same edge the MAC samples, so its tail and valid_out align.
    localparam integer MAC_LAT = 5;
    reg [31:0] lat_id    [0:MAC_LAT-1];
    reg [31:0] lat_score [0:MAC_LAT-1];
    reg [MAC_LAT-1:0] lat_valid;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lat_valid <= {MAC_LAT{1'b0}};
            for (i = 0; i < MAC_LAT; i = i + 1) begin
                lat_id[i] <= 32'd0; lat_score[i] <= 32'd0;
            end
        end else begin
            lat_valid <= {lat_valid[MAC_LAT-2:0], d_valid};
            lat_id[0] <= d_id;
            lat_score[0] <= score_value;
            for (i = 0; i < MAC_LAT-1; i = i + 1) begin
                lat_id[i+1] <= lat_id[i];
                lat_score[i+1] <= lat_score[i];
            end
        end
    end
    wire [31:0] cand_id    = lat_id[MAC_LAT-1];
    wire [31:0] cand_score = lat_score[MAC_LAT-1];
    //: The candidate is live when the adder retires it, or -- with no bias --
    //: when the companion pipe's own valid reaches the same depth.
    wire        cand_valid = cfg_has_bias ? add_vout : lat_valid[MAC_LAT-1];
    wire [31:0] cand_key   = cfg_has_bias ? add_y : cand_score;
    wire [1:0]  cand_err   = cfg_has_bias ? add_err : 2'd0;

    //: Finite IEEE codes compare as unsigned integers under this map.
    function automatic [31:0] monotonic;
        input [31:0] code;
        begin
            //: EVERY ZERO MAPS TO ONE POINT.  Float comparison holds -0 == +0,
            //: so a map that ordered them apart would rank +0 above -0 and take
            //: the tie away from the lower index -- which is what it did, on
            //: exactly the three signed-zero cases and nowhere else. The MAC
            //: this engine used to add through hid the bug by canonicalising its
            //: own output; bypassing it for the no-bias walk exposed it.
            monotonic = (code[30:0] == 31'd0)
                        ? 32'h8000_0000
                        : (code[31] ? ~code : (code | 32'h8000_0000));
        end
    endfunction
    wire [31:0] cand_ord = monotonic(cand_key);
    //: STRICT greater-than, which is the tie rule: the scan visits ascending
    //: ids, so an equal key must not displace the earlier expert.
    wire [MAX_K-1:0] beats;
    generate
        for (gi = 0; gi < MAX_K; gi = gi + 1) begin : g_cmp
            assign beats[gi] = !top_valid[gi] || (cand_ord > top_ord[gi]);
        end
    endgenerate
    //: WHICH SLOTS EXIST IS CONFIG, NOT DATA.  ``i < cfg_topk`` is invariant for
    //: the whole run, so evaluating eight 32-bit comparisons inside the insertion
    //: cone every cycle buys nothing and lengthens the binding path: the cone is
    //: already compare -> priority encode -> shift mux.  Latched once at start.
    reg [MAX_K-1:0] slot_active;

    //: The first slot it beats; everything from there shifts down one.
    reg [31:0] ins;
    reg        ins_any;
    always @* begin
        ins = 32'd0; ins_any = 1'b0;
        for (i = MAX_K-1; i >= 0; i = i - 1) begin
            if (slot_active[i] && beats[i]) begin
                ins = i[31:0]; ins_any = 1'b1;
            end
        end
    end

    //: THE WEIGHT IS ``narrow(selected, weight_view)``, done by the real
    //: narrowing function rather than by moving code bits around. The two dtypes
    //: disagree on minus zero -- runtime/sim/formats.py resolves narrow(BF16,
    //: -0.0) to 0x0000 because narrow_bf16_rne CANONICALISES, and narrow(FP32,
    //: -0.0) to 0x80000000 because a plain cast PRESERVES -- and calling
    //: ot_fp32_rne_pkg::fp32_to_bf16_rne gets that right for free instead of
    //: needing a hand-written zero rule that was first written backwards.
    wire [31:0] emit_value = top_score[emit_slot[2:0]];
    wire [18:0] emit_narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(emit_value);
    wire [31:0] emit_weight = cfg_weight_fp32 ? emit_value
                                              : {16'h0000, emit_narrowed[15:0]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            grp <= 32'd0; expert <= 32'd0; emit_slot <= 32'd0;
            emit_pass <= 1'b0;
            score_row <= 32'd0; bias_row <= 32'd0; id_row <= 32'd0;
            drain <= 32'd0; fault_nonfinite <= 1'b0; rd_id <= 32'd0;
            score_rd_en <= 1'b0; score_rd_addr <= 32'd0;
            bias_rd_en <= 1'b0; bias_rd_addr <= 32'd0;
            id_we <= 1'b0; id_addr <= 32'd0; id_data <= 32'd0;
            wgt_we <= 1'b0; wgt_addr <= 32'd0; wgt_data <= 32'd0;
            busy <= 1'b0; done <= 1'b0; error_code <= ERR_NONE;
            selected_experts <= 32'd0; candidates <= 32'd0;
            top_valid <= {MAX_K{1'b0}}; slot_active <= {MAX_K{1'b0}};
            for (i = 0; i < MAX_K; i = i + 1) begin
                top_ord[i] <= 32'd0; top_id[i] <= 32'd0; top_score[i] <= 32'd0;
            end
        end else begin
            score_rd_en <= 1'b0;
            bias_rd_en <= 1'b0;
            id_we <= 1'b0;
            wgt_we <= 1'b0;
            done <= 1'b0;

            //: The insertion, five stages behind the read.
            if (operand_nonfinite)
                fault_nonfinite <= 1'b1;

            if (cand_valid) begin
                candidates <= candidates + 32'd1;
                if (cand_err != 2'd0)
                    fault_nonfinite <= 1'b1;
                else if (ins_any) begin
                    for (i = MAX_K-1; i > 0; i = i - 1) begin
                        if ({24'd0, i[7:0]} > ins) begin
                            top_ord[i] <= top_ord[i-1];
                            top_id[i] <= top_id[i-1];
                            top_score[i] <= top_score[i-1];
                            top_valid[i] <= top_valid[i-1];
                        end
                    end
                    top_ord[ins] <= cand_ord;
                    top_id[ins] <= cand_id;
                    top_score[ins] <= cand_score;
                    top_valid[ins] <= 1'b1;
                end
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        grp <= 32'd0; expert <= 32'd0;
                        score_row <= 32'd0; bias_row <= 32'd0; id_row <= 32'd0;
                        selected_experts <= 32'd0; candidates <= 32'd0;
                        fault_nonfinite <= 1'b0;
                        top_valid <= {MAX_K{1'b0}};
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            for (i = 0; i < MAX_K; i = i + 1)
                                slot_active[i] <=
                                    ({24'd0, i[7:0]} < cfg_topk);
                            busy <= 1'b1; state <= S_SCAN;
                        end
                    end
                end
                S_SCAN: begin
                    score_rd_en <= 1'b1;
                    score_rd_addr <= cfg_score_base + score_row + expert;
                    rd_id <= expert;
                    if (cfg_has_bias) begin
                        bias_rd_en <= 1'b1;
                        bias_rd_addr <= cfg_bias_base + bias_row + expert;
                    end
                    if (expert + 32'd1 >= cfg_experts) begin
                        drain <= 32'd0;
                        state <= S_DRAIN;
                    end else begin
                        expert <= expert + 32'd1;
                    end
                end
                //: Read latency plus the MAC's, so every candidate has been
                //: offered to the insertion before the group is emitted.
                S_DRAIN: begin
                    if (drain >= (MAC_LAT[31:0] + 32'd4)) begin
                        if (fault_nonfinite) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            emit_slot <= 32'd0;
                            emit_pass <= 1'b0;
                            state <= S_EMIT;
                        end
                    end else begin
                        drain <= drain + 32'd1;
                    end
                end
                S_EMIT: begin
                    if (!emit_pass) begin
                        id_we <= 1'b1;
                        id_addr <= cfg_id_out_base + id_row + emit_slot;
                        id_data <= top_id[emit_slot[2:0]];
                        selected_experts <= selected_experts + 32'd1;
                    end else begin
                        wgt_we <= 1'b1;
                        wgt_addr <= cfg_weight_out_base + id_row + emit_slot;
                        //: The UNBIASED score, which is the contract's point.
                        wgt_data <= emit_weight;
                    end
                    if (emit_slot + 32'd1 >= cfg_topk) begin
                        emit_slot <= 32'd0;
                        //: The weight pass runs only when a weight view is
                        //: bound; the reference makes output_view_1 optional.
                        if (!emit_pass && cfg_has_weight_out)
                            emit_pass <= 1'b1;
                        else
                            state <= S_NEXT;
                    end else begin
                        emit_slot <= emit_slot + 32'd1;
                    end
                end
                S_NEXT: begin
                    if (grp + 32'd1 >= cfg_groups) begin
                        state <= S_DONE;
                    end else begin
                        grp <= grp + 32'd1;
                        expert <= 32'd0;
                        score_row <= score_row + cfg_experts;
                        if (!cfg_bias_broadcast)
                            bias_row <= bias_row + cfg_experts;
                        id_row <= id_row + cfg_topk;
                        top_valid <= {MAX_K{1'b0}};
                        state <= S_SCAN;
                    end
                end
                S_DONE: begin
                    busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
