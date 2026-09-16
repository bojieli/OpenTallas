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
// THE KEY ADD USES THE QUALIFIED PIPELINED MAC.  ``score + bias`` is
// ``RN(bias * 1.0 + score)`` on ot_mac_bf16_fp32_pipe -- exact, because the
// product is -- at five stages and one result per cycle.  A combinational
// ot_fp32_rne_pkg::fp32_add_rne here would cap the block near 155 MHz, which is
// what it did to two reduction engines before they were rebuilt on this MAC.
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

    localparam [15:0] BF16_ONE = 16'h3F80;

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

    //: The key: RN(bias + score) in binary32, or the score alone with no bias.
    wire [33:0] score_wide = ot_a3_format_pkg::decode_bf16(score_rd_data[15:0]);
    wire [15:0] mac_a = cfg_has_bias ? bias_rd_data[15:0] : 16'h0000;
    wire        mac_vin;
    wire [31:0] mac_y;
    wire [1:0]  mac_err;
    wire        mac_vout;

    ot_mac_bf16_fp32_pipe key_add (
        .clk(clk), .rst_n(rst_n), .valid_in(mac_vin),
        .a(mac_a), .b(BF16_ONE), .c(score_wide[31:0]),
        .y(mac_y), .err(mac_err), .valid_out(mac_vout)
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
    assign mac_vin = d_valid;
    //: Refused on the operand rather than the result: the MAC's own ``err``
    //: reports a nonfinite it was GIVEN, but only once the result emerges, and a
    //: nonfinite score with no bias would never reach the multiplier at all.
    wire operand_nonfinite = d_valid &&
        ((score_wide[33:32] != 2'd0) ||
         (cfg_has_bias && (bias_rd_data[14:7] == 8'hff)));

    //: The MAC's own latency carries the id and the unbiased score alongside the
    //: key, so the insertion sees a matched triple.  FIVE registrations --
    //: valid_in -> s1_v -> s2_v -> s3_v -> s4_v -> valid_out -- counted in
    //: ot_mac_bf16_fp32_pipe rather than assumed, and the companion's stage 0 is
    //: loaded on the same edge the MAC samples, so its tail and valid_out align.
    localparam integer MAC_LAT = 5;
    reg [31:0] lat_id    [0:MAC_LAT-1];
    reg [31:0] lat_score [0:MAC_LAT-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < MAC_LAT; i = i + 1) begin
                lat_id[i] <= 32'd0; lat_score[i] <= 32'd0;
            end
        end else begin
            lat_id[0] <= d_id;
            lat_score[0] <= score_rd_data;
            for (i = 0; i < MAC_LAT-1; i = i + 1) begin
                lat_id[i+1] <= lat_id[i];
                lat_score[i+1] <= lat_score[i];
            end
        end
    end
    wire [31:0] cand_id    = lat_id[MAC_LAT-1];
    wire [31:0] cand_score = lat_score[MAC_LAT-1];

    //: Finite IEEE codes compare as unsigned integers under this map.
    function automatic [31:0] monotonic;
        input [31:0] code;
        begin
            monotonic = code[31] ? ~code : (code | 32'h8000_0000);
        end
    endfunction
    wire [31:0] cand_ord = monotonic(mac_y);
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

    //: THE TWO WEIGHT DTYPES DISAGREE ON MINUS ZERO, and in the direction that
    //: is easy to get backwards.  The reference writes
    //: ``narrow(selected, weight_view)``, and runtime/sim/formats.py resolves that
    //: to narrow_bf16_rne for a BF16 view -- which CANONICALISES -0 to +0 -- and
    //: to a plain binary32 cast for an FP32 view, which PRESERVES it:
    //:
    //:     narrow(BF16, -0.0) -> 0x0000        narrow(FP32, -0.0) -> 0x80000000
    //:
    //: So BF16 forces the sign off a zero and FP32 keeps the code, widened by
    //: shift.  Writing the stored code on both paths is wrong on BF16; using
    //: ot_a3_format_pkg::decode_bf16 on both is wrong on FP32.
    wire [15:0] emit_code = top_score[emit_slot[2:0]][15:0];
    wire        emit_zero = (emit_code[14:0] == 15'd0);
    wire [31:0] emit_weight =
        cfg_weight_fp32 ? {emit_code, 16'h0000}
                        : {16'h0000, emit_zero ? 16'h0000 : emit_code};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            grp <= 32'd0; expert <= 32'd0; emit_slot <= 32'd0;
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

            if (mac_vout) begin
                candidates <= candidates + 32'd1;
                if (mac_err != 2'd0)
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
                            state <= S_EMIT;
                        end
                    end else begin
                        drain <= drain + 32'd1;
                    end
                end
                S_EMIT: begin
                    id_we <= 1'b1;
                    id_addr <= cfg_id_out_base + id_row + emit_slot;
                    id_data <= top_id[emit_slot[2:0]];
                    selected_experts <= selected_experts + 32'd1;
                    if (cfg_has_weight_out) begin
                        wgt_we <= 1'b1;
                        wgt_addr <= cfg_weight_out_base + id_row + emit_slot;
                        //: The UNBIASED score, which is the contract's point.
                        wgt_data <= emit_weight;
                    end
                    if (emit_slot + 32'd1 >= cfg_topk)
                        state <= S_NEXT;
                    else
                        emit_slot <= emit_slot + 32'd1;
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
