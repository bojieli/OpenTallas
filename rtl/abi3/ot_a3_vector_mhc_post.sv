`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.MHC / HYPER_CONNECT_POST datapath (aux0 == 1).
//
// The covered frozen profile has four residual streams.  For each destination
// stream and hidden element it forms post[dest] * branch, then the balanced
// residual tree
//
//   (comb[0][dest] * residual[0] + comb[1][dest] * residual[1])
// + (comb[2][dest] * residual[2] + comb[3][dest] * residual[3]),
//
// adds the branch product and crosses one BF16 boundary.  The source/dest
// order of the combination matrix is architectural.  PRE and HEAD need
// correctly-rounded nonlinear arithmetic and remain fail-closed.
// ---------------------------------------------------------------------------
module ot_a3_vector_mhc_post #(
    parameter [15:0] MAX_SITES = 16'd4,
    parameter integer MULTIPLIER = 4,
    parameter [15:0] MAX_HIDDEN = 16'd32,
    parameter integer MAX_OUTPUTS = MAX_SITES * MULTIPLIER * MAX_HIDDEN
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [15:0] cfg_sites,
    input  wire [15:0] cfg_hidden,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_multiplier,
    input  wire [15:0] cfg_aux0,
    input  wire [15:0] cfg_aux2,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_branch_base,
    input  wire [31:0] cfg_residual_base,
    input  wire [31:0] cfg_post_base,
    input  wire [31:0] cfg_comb_base,
    input  wire [31:0] cfg_out_base,

    output reg         branch_rd_en,
    output reg  [31:0] branch_rd_addr,
    input  wire [31:0] branch_rd_data,
    output reg         residual_rd_en,
    output reg  [31:0] residual_rd_addr,
    input  wire [31:0] residual_rd_data,
    output reg         post_rd_en,
    output reg  [31:0] post_rd_addr,
    input  wire [31:0] post_rd_data,
    output reg         comb_rd_en,
    output reg  [31:0] comb_rd_addr,
    input  wire [31:0] comb_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] work_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [15:0] HC_POST = 16'd1;
    localparam [1:0] LAST_STREAM = 2'd3;

    localparam [4:0] S_IDLE          = 5'd0;
    localparam [4:0] S_SCAN_ISSUE    = 5'd1;
    localparam [4:0] S_SCAN_WAIT     = 5'd2;
    localparam [4:0] S_SCAN_CHECK    = 5'd3;
    localparam [4:0] S_BRANCH_ISSUE  = 5'd4;
    localparam [4:0] S_BRANCH_WAIT   = 5'd5;
    localparam [4:0] S_BRANCH        = 5'd6;
    localparam [4:0] S_RESID_ISSUE   = 5'd7;
    localparam [4:0] S_RESID_WAIT    = 5'd8;
    localparam [4:0] S_RESID         = 5'd9;
    localparam [4:0] S_REDUCE_1      = 5'd10;
    localparam [4:0] S_REDUCE_2      = 5'd11;
    localparam [4:0] S_COMBINE       = 5'd12;
    localparam [4:0] S_COMMIT        = 5'd13;
    //: One wait state per pipelined unit. Every arithmetic cone in this engine was
    //: combinational and the routed evidence is what that cost: 151.2 MHz at a
    //: 3.4 ns target, 98,875 cells, the slowest member of ot_a3_engine_array and
    //: below the 276.9 MHz design limiter. The worst path ran residual_total[25] to
    //: result_buffer[359][10] -- ONE binary32 add and the BF16 narrowing sharing a
    //: cycle -- and a general binary32 RNE add alone is about 6.6 ns on ASAP7.
    //:
    //: ot_a3_vector_add is the precedent and the number to expect: the same swap
    //: took it from 154.9 MHz not met with 9,601 cells to 674.1 MHz CLOSED with
    //: 4,907 -- 4.35x the frequency at HALF the cells, because a five-stage pipe
    //: maps to less logic than one combinational cone of the same arithmetic.
    localparam [4:0] S_BRANCH_PIPE   = 5'd14;
    localparam [4:0] S_RESID_PIPE    = 5'd15;
    localparam [4:0] S_REDUCE_1_PIPE = 5'd16;
    localparam [4:0] S_REDUCE_2_PIPE = 5'd17;
    localparam [4:0] S_COMBINE_PIPE  = 5'd18;
    //: The narrowing and the buffer write, separate from S_COMMIT which
    //: is this engine's output DRAIN and was always a distinct state.
    localparam [4:0] S_NARROW        = 5'd19;
    localparam [4:0] S_DONE          = 5'd14;

    reg [4:0] state;
    reg [2:0] scan_kind;
    reg [31:0] index;
    reg [15:0] site;
    reg [1:0] destination;
    reg [15:0] hidden_index;
    reg [1:0] source;
    reg [31:0] branch_product_value;
    reg [31:0] reduce_left;
    reg [31:0] reduce_right;
    reg [31:0] residual_total;
    //: The final sum, registered, so the BF16 narrowing does not share its cone.
    reg [31:0] combined;
    reg [31:0] pending_saturation_count;
    reg [31:0] products [0:MULTIPLIER-1];
    reg [31:0] result_buffer [0:MAX_OUTPUTS-1];

    wire [31:0] branch_elements =
        {16'b0, cfg_sites} * {16'b0, cfg_hidden};
    wire [31:0] residual_elements = branch_elements * MULTIPLIER;
    wire [31:0] post_elements = {16'b0, cfg_sites} * MULTIPLIER;
    wire [31:0] comb_elements =
        {16'b0, cfg_sites} * MULTIPLIER * MULTIPLIER;
    wire [31:0] scan_limit = (scan_kind == 0) ? branch_elements
                               : (scan_kind == 1) ? residual_elements
                               : (scan_kind == 2) ? post_elements
                               : comb_elements;

    wire [33:0] decoded_branch =
        ot_a3_format_pkg::decode_bf16(branch_rd_data[15:0]);
    wire [33:0] decoded_residual =
        ot_a3_format_pkg::decode_bf16(residual_rd_data[15:0]);
    wire post_finite = post_rd_data[30:23] != 8'hff;
    wire comb_finite = comb_rd_data[30:23] != 8'hff;
    //: ONE PIPELINED MULTIPLIER, two pipelined adders. The multiplier serves the
    //: branch product and each of the four residual products, which happen in
    //: different states and never overlap. The two adders serve the reduction's
    //: independent pair, and the left one is reused for the two dependent adds
    //: after it -- rtl/proto/ot_fp32_mul_rne_pipe.sv and
    //: rtl/proto/ot_fp32_add_rne_pipe.sv are both qualified bit-identical to the
    //: ot_fp32_rne_pkg functions they replace, including the two places that
    //: authority is deliberately not IEEE-754: (-0) + (-0) is +0 and every zero
    //: result is canonical +0. So this is a latency change and not a numeric one.
    reg         mul_valid;
    reg  [31:0] mul_a, mul_b;
    wire [31:0] mul_y;
    wire [1:0]  mul_err;
    wire        mul_done;
    ot_fp32_mul_rne_pipe multiplier (
        .clk(clk), .rst_n(rst_n), .valid_in(mul_valid),
        .a(mul_a), .b(mul_b),
        .y(mul_y), .err(mul_err), .valid_out(mul_done)
    );

    reg         add_valid;
    reg  [31:0] add_l_a, add_l_b, add_r_a, add_r_b;
    wire [31:0] add_l_y, add_r_y;
    wire [1:0]  add_l_err, add_r_err;
    wire        add_l_done, add_r_done;
    ot_fp32_add_rne_pipe adder_left (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid),
        .a(add_l_a), .b(add_l_b),
        .y(add_l_y), .err(add_l_err), .valid_out(add_l_done)
    );
    ot_fp32_add_rne_pipe adder_right (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid),
        .a(add_r_a), .b(add_r_b),
        .y(add_r_y), .err(add_r_err), .valid_out(add_r_done)
    );

    //: The narrowing now sits alone in its cycle, because ``combined`` is a
    //: register: it was sharing the add's cone, which is where the worst path ended.
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(combined);

    wire configuration_supported =
        (cfg_aux0 == HC_POST) && (cfg_aux2 == 16'd4) &&
        (cfg_multiplier == MULTIPLIER) &&
        (cfg_dtype_a == FMT_BF16) && (cfg_dtype_b == FMT_BF16) &&
        (cfg_sites != 0) && (cfg_sites <= MAX_SITES) &&
        (cfg_hidden != 0) && (cfg_hidden <= MAX_HIDDEN) &&
        (cfg_count == ({16'b0, cfg_sites} * MULTIPLIER *
                       {16'b0, cfg_hidden}));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            mul_valid <= 1'b0; add_valid <= 1'b0;
            mul_a <= 32'b0; mul_b <= 32'b0;
            add_l_a <= 32'b0; add_l_b <= 32'b0;
            add_r_a <= 32'b0; add_r_b <= 32'b0;
            combined <= 32'b0;
            scan_kind <= 0;
            index <= 0;
            site <= 0;
            destination <= 0;
            hidden_index <= 0;
            source <= 0;
            branch_product_value <= 0;
            reduce_left <= 0;
            reduce_right <= 0;
            residual_total <= 0;
            branch_rd_en <= 1'b0;
            branch_rd_addr <= 0;
            residual_rd_en <= 1'b0;
            residual_rd_addr <= 0;
            post_rd_en <= 1'b0;
            post_rd_addr <= 0;
            comb_rd_en <= 1'b0;
            comb_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
            work_count <= 0;
            saturation_count <= 0;
            pending_saturation_count <= 0;
        end else begin
            //: Both units latch on one cycle of valid_in; holding it would
            //: issue a second operation. Done is never tested in the same
            //: condition as a start here, because these are fixed-latency pipes
            //: with no busy line -- the wait state only tests valid_out.
            mul_valid <= 1'b0;
            add_valid <= 1'b0;
            done <= 1'b0;
            branch_rd_en <= 1'b0;
            residual_rd_en <= 1'b0;
            post_rd_en <= 1'b0;
            comb_rd_en <= 1'b0;
            out_we <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        work_count <= 0;
                        saturation_count <= 0;
                        pending_saturation_count <= 0;
                        scan_kind <= 0;
                        index <= 0;
                        site <= 0;
                        destination <= 0;
                        hidden_index <= 0;
                        source <= 0;
                        if (!configuration_supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_SCAN_ISSUE;
                        end
                    end
                end

                S_SCAN_ISSUE: begin
                    if (scan_kind == 0) begin
                        branch_rd_en <= 1'b1;
                        branch_rd_addr <= cfg_branch_base + index;
                    end else if (scan_kind == 1) begin
                        residual_rd_en <= 1'b1;
                        residual_rd_addr <= cfg_residual_base + index;
                    end else if (scan_kind == 2) begin
                        post_rd_en <= 1'b1;
                        post_rd_addr <= cfg_post_base + index;
                    end else begin
                        comb_rd_en <= 1'b1;
                        comb_rd_addr <= cfg_comb_base + index;
                    end
                    state <= S_SCAN_WAIT;
                end

                S_SCAN_WAIT: state <= S_SCAN_CHECK;

                S_SCAN_CHECK: begin
                    if (((scan_kind == 0) &&
                         (decoded_branch[33:32] != 0)) ||
                        ((scan_kind == 1) &&
                         (decoded_residual[33:32] != 0)) ||
                        ((scan_kind == 2) && !post_finite) ||
                        ((scan_kind == 3) && !comb_finite)) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (index + 1 == scan_limit) begin
                        index <= 0;
                        if (scan_kind == 3) begin
                            site <= 0;
                            destination <= 0;
                            hidden_index <= 0;
                            source <= 0;
                            state <= S_BRANCH_ISSUE;
                        end else begin
                            scan_kind <= scan_kind + 1;
                            state <= S_SCAN_ISSUE;
                        end
                    end else begin
                        index <= index + 1;
                        state <= S_SCAN_ISSUE;
                    end
                end

                S_BRANCH_ISSUE: begin
                    branch_rd_en <= 1'b1;
                    branch_rd_addr <= cfg_branch_base +
                        ({16'b0, site} * {16'b0, cfg_hidden}) +
                        {16'b0, hidden_index};
                    post_rd_en <= 1'b1;
                    post_rd_addr <= cfg_post_base +
                        ({16'b0, site} * MULTIPLIER) +
                        {30'b0, destination};
                    state <= S_BRANCH_WAIT;
                end

                S_BRANCH_WAIT: state <= S_BRANCH;

                //: The operand check stays HERE, ahead of the multiplier, so a
                //: nonfinite operand is refused before it is issued and the refusal
                //: order is the one this engine always had.
                S_BRANCH: begin
                    if ((decoded_branch[33:32] != 0) || !post_finite) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else begin
                        mul_a <= post_rd_data;
                        mul_b <= decoded_branch[31:0];
                        mul_valid <= 1'b1;
                        state <= S_BRANCH_PIPE;
                    end
                end

                S_BRANCH_PIPE: begin
                    if (mul_done) begin
                        //: err 1 is a nonfinite operand, excluded above; err 2 is a
                        //: product outside binary32, this engine's
                        //: ERR_PRODUCT_RANGE.
                        if (mul_err != 2'd0) begin
                            error_code <= (mul_err == 2'd1)
                                          ? ERR_OPERAND_NONFINITE
                                          : ERR_PRODUCT_RANGE;
                            state <= S_DONE;
                        end else begin
                            branch_product_value <= mul_y;
                            source <= 0;
                            state <= S_RESID_ISSUE;
                        end
                    end
                end

                S_RESID_ISSUE: begin
                    residual_rd_en <= 1'b1;
                    residual_rd_addr <= cfg_residual_base +
                        ({16'b0, site} * MULTIPLIER *
                         {16'b0, cfg_hidden}) +
                        (source * {16'b0, cfg_hidden}) +
                        {16'b0, hidden_index};
                    comb_rd_en <= 1'b1;
                    // Architectural order is comb[source][destination].
                    comb_rd_addr <= cfg_comb_base +
                        ({16'b0, site} * MULTIPLIER * MULTIPLIER) +
                        ({30'b0, source} * MULTIPLIER) +
                        {30'b0, destination};
                    state <= S_RESID_WAIT;
                end

                S_RESID_WAIT: state <= S_RESID;

                S_RESID: begin
                    if ((decoded_residual[33:32] != 0) || !comb_finite) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else begin
                        mul_a <= comb_rd_data;
                        mul_b <= decoded_residual[31:0];
                        mul_valid <= 1'b1;
                        state <= S_RESID_PIPE;
                    end
                end

                S_RESID_PIPE: begin
                    if (mul_done) begin
                        if (mul_err != 2'd0) begin
                            error_code <= (mul_err == 2'd1)
                                          ? ERR_OPERAND_NONFINITE
                                          : ERR_PRODUCT_RANGE;
                            state <= S_DONE;
                        end else begin
                            products[source] <= mul_y;
                            if (source == LAST_STREAM) begin
                                state <= S_REDUCE_1;
                            end else begin
                                source <= source + 1;
                                state <= S_RESID_ISSUE;
                            end
                        end
                    end
                end

                //: The independent pair, both adders issued on the same cycle so
                //: they retire together -- same LATENCY, same valid_in.
                S_REDUCE_1: begin
                    add_l_a <= products[0]; add_l_b <= products[1];
                    add_r_a <= products[2]; add_r_b <= products[3];
                    add_valid <= 1'b1;
                    state <= S_REDUCE_1_PIPE;
                end

                S_REDUCE_1_PIPE: begin
                    if (add_l_done && add_r_done) begin
                        //: Either endpoint leaving binary32 is this engine's
                        //: ERR_ACCUMULATE_RANGE, and both are tested together
                        //: exactly as the one-cycle form tested pair_01 and pair_23.
                        if (add_l_err != 2'd0 || add_r_err != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end else begin
                            reduce_left <= add_l_y;
                            reduce_right <= add_r_y;
                            state <= S_REDUCE_2;
                        end
                    end
                end

                S_REDUCE_2: begin
                    //: The left adder again; the right one is idle from here and its
                    //: result is ignored, which is why both are issued together.
                    add_l_a <= reduce_left; add_l_b <= reduce_right;
                    add_r_a <= 32'b0; add_r_b <= 32'b0;
                    add_valid <= 1'b1;
                    state <= S_REDUCE_2_PIPE;
                end

                S_REDUCE_2_PIPE: begin
                    if (add_l_done) begin
                        if (add_l_err != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end else begin
                            residual_total <= add_l_y;
                            state <= S_COMBINE;
                        end
                    end
                end

                S_COMBINE: begin
                    add_l_a <= branch_product_value; add_l_b <= residual_total;
                    add_r_a <= 32'b0; add_r_b <= 32'b0;
                    add_valid <= 1'b1;
                    state <= S_COMBINE_PIPE;
                end

                S_COMBINE_PIPE: begin
                    if (add_l_done) begin
                        if (add_l_err != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end else begin
                            combined <= add_l_y;
                            state <= S_NARROW;
                        end
                    end
                end

                //: The narrowing and the store, with ``combined`` a register: the
                //: one-cycle form did the final add, the narrowing, the range check
                //: and the buffer write together, and that cone was the worst path.
                S_NARROW: begin
                    if (narrowed[18:17] != 0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        if (narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + 1;
                        result_buffer[
                            ({16'b0, site} * MULTIPLIER *
                             {16'b0, cfg_hidden}) +
                            (destination * {16'b0, cfg_hidden}) +
                            {16'b0, hidden_index}
                        ] <= {16'b0, narrowed[15:0]};
                        if (hidden_index + 1 < cfg_hidden) begin
                            hidden_index <= hidden_index + 1;
                            state <= S_BRANCH_ISSUE;
                        end else if (destination != LAST_STREAM) begin
                            hidden_index <= 0;
                            destination <= destination + 1;
                            state <= S_BRANCH_ISSUE;
                        end else if (site + 1 < cfg_sites) begin
                            hidden_index <= 0;
                            destination <= 0;
                            site <= site + 1;
                            state <= S_BRANCH_ISSUE;
                        end else begin
                            index <= 0;
                            state <= S_COMMIT;
                        end
                    end
                end

                S_COMMIT: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + index;
                    out_data <= result_buffer[index];
                    out_count <= out_count + 1;
                    work_count <= work_count + 1;
                    if (index + 1 == cfg_count) begin
                        saturation_count <= pending_saturation_count;
                        state <= S_DONE;
                    end else begin
                        index <= index + 1;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase
        end
    end
endmodule
