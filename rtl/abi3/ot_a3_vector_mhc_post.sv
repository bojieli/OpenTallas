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
    wire [33:0] branch_product = ot_fp32_rne_pkg::fp32_mul_rne(
        post_rd_data, decoded_branch[31:0]
    );
    wire [33:0] residual_product = ot_fp32_rne_pkg::fp32_mul_rne(
        comb_rd_data, decoded_residual[31:0]
    );
    wire [33:0] pair_01 =
        ot_fp32_rne_pkg::fp32_add_rne(products[0], products[1]);
    wire [33:0] pair_23 =
        ot_fp32_rne_pkg::fp32_add_rne(products[2], products[3]);
    wire [33:0] residual_sum =
        ot_fp32_rne_pkg::fp32_add_rne(reduce_left, reduce_right);
    wire [33:0] combined =
        ot_fp32_rne_pkg::fp32_add_rne(branch_product_value, residual_total);
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(combined[31:0]);

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

                S_BRANCH: begin
                    if ((decoded_branch[33:32] != 0) || !post_finite) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (branch_product[33:32] != 0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        branch_product_value <= branch_product[31:0];
                        source <= 0;
                        state <= S_RESID_ISSUE;
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
                    end else if (residual_product[33:32] != 0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        products[source] <= residual_product[31:0];
                        if (source == LAST_STREAM) begin
                            state <= S_REDUCE_1;
                        end else begin
                            source <= source + 1;
                            state <= S_RESID_ISSUE;
                        end
                    end
                end

                S_REDUCE_1: begin
                    if ((pair_01[33:32] != 0) || (pair_23[33:32] != 0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        reduce_left <= pair_01[31:0];
                        reduce_right <= pair_23[31:0];
                        state <= S_REDUCE_2;
                    end
                end

                S_REDUCE_2: begin
                    if (residual_sum[33:32] != 0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        residual_total <= residual_sum[31:0];
                        state <= S_COMBINE;
                    end
                end

                S_COMBINE: begin
                    if ((combined[33:32] != 0) ||
                        (narrowed[18:17] != 0)) begin
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
