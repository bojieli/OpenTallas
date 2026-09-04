`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact Qwen3-8B layer-zero attention output projection at ABI 3.0 PC41.
//
// The fixed operation is [1,4096] x [4096,4096]^T.  The input and each weight
// are finite BF16 codes, widened exactly to binary32.  Every output walks K in
// strictly ascending order, rounding each product and add to binary32 RNE,
// then rounds the completed accumulator once to BF16 RNE.  This is the exact
// single-lane association selected for bf16_bf16_fp32_blocked_rne_v1 by the
// shipped Qwen program.
//
// Input is buffered once.  The memory interface permits one outstanding read,
// but accepts a replacement request in the same cycle its predecessor returns;
// arbitrary request and response stalls therefore do not change association.
// The complete 4,096-word result is buffered before any output is published.
// A late operand or arithmetic fault consequently produces zero writes.
// ---------------------------------------------------------------------------
module ot_a3_qwen_output_projection (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_input_base,
    input  wire [31:0] cfg_weight_base,
    input  wire [31:0] cfg_output_base,

    output wire        mem_req_valid,
    input  wire        mem_req_ready,
    output wire [31:0] mem_req_addr,
    input  wire        mem_rsp_valid,
    input  wire [31:0] mem_rsp_data,

    output wire        out_valid,
    input  wire        out_ready,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg         failed,
    output reg  [7:0]  error_code,
    output reg  [31:0] memory_read_count,
    output reg  [31:0] input_read_count,
    output reg  [31:0] weight_read_count,
    output reg  [31:0] mac_count,
    output reg  [31:0] output_write_count,
    output reg  [31:0] saturation_count
);
    localparam integer WIDTH = 4096;
    localparam integer WEIGHT_WORDS = WIDTH * WIDTH;

    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_CONFIG = 8'd1;
    localparam [7:0] ERR_INPUT = 8'd2;
    localparam [7:0] ERR_NUMERIC = 8'd3;

    localparam [2:0] S_IDLE = 3'd0;
    localparam [2:0] S_INPUT = 3'd1;
    localparam [2:0] S_WEIGHT = 3'd2;
    localparam [2:0] S_PUBLISH = 3'd3;
    localparam [2:0] S_FINISH = 3'd4;

    reg [2:0] state;
    reg [31:0] input_base_q;
    reg [31:0] weight_base_q;
    reg [31:0] output_base_q;
    reg pending_read_q;
    reg [24:0] request_count_q;
    reg [24:0] response_count_q;
    reg [11:0] publish_index_q;
    reg [31:0] accumulator_q;

    reg [15:0] input_buffer [0:WIDTH-1];
    reg [15:0] output_buffer [0:WIDTH-1];

    wire response_nonfinite = mem_rsp_data[14:7] == 8'hff;
    wire [11:0] weight_depth = response_count_q[11:0];
    wire [11:0] weight_output = response_count_q[23:12];
    wire [31:0] input_fp32 = {input_buffer[weight_depth], 16'd0};
    wire [31:0] weight_fp32 = {mem_rsp_data[15:0], 16'd0};
    wire [33:0] product = ot_fp32_rne_pkg::fp32_mul_rne(
        input_fp32, weight_fp32
    );
    wire [31:0] canonical_product = product[30:0] == 0
        ? 32'd0 : product[31:0];
    wire [33:0] sum = ot_fp32_rne_pkg::fp32_add_rne(
        accumulator_q, canonical_product
    );
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(sum[31:0]);

    wire input_response_fault = response_nonfinite;
    wire weight_response_fault = response_nonfinite ||
        (product[33:32] != 0) || (sum[33:32] != 0) ||
        ((weight_depth == WIDTH-1) && (narrowed[18:17] != 0));
    wire response_fault = state == S_INPUT
        ? input_response_fault
        : state == S_WEIGHT ? weight_response_fault : 1'b0;

    wire response_fire = pending_read_q && mem_rsp_valid;
    wire can_replace = !pending_read_q ||
        (mem_rsp_valid && !response_fault);
    wire request_in_range = state == S_INPUT
        ? request_count_q < WIDTH
        : state == S_WEIGHT ? request_count_q < WEIGHT_WORDS : 1'b0;
    assign mem_req_valid = busy && request_in_range && can_replace;
    assign mem_req_addr = state == S_INPUT
        ? input_base_q + request_count_q
        : weight_base_q + request_count_q;
    wire request_fire = mem_req_valid && mem_req_ready;

    assign out_valid = state == S_PUBLISH;
    assign out_addr = output_base_q + publish_index_q;
    assign out_data = {16'd0, output_buffer[publish_index_q]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            input_base_q <= 0;
            weight_base_q <= 0;
            output_base_q <= 0;
            pending_read_q <= 1'b0;
            request_count_q <= 0;
            response_count_q <= 0;
            publish_index_q <= 0;
            accumulator_q <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            failed <= 1'b0;
            error_code <= ERR_NONE;
            memory_read_count <= 0;
            input_read_count <= 0;
            weight_read_count <= 0;
            mac_count <= 0;
            output_write_count <= 0;
            saturation_count <= 0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        input_base_q <= cfg_input_base;
                        weight_base_q <= cfg_weight_base;
                        output_base_q <= cfg_output_base;
                        pending_read_q <= 1'b0;
                        request_count_q <= 0;
                        response_count_q <= 0;
                        publish_index_q <= 0;
                        accumulator_q <= 0;
                        busy <= 1'b1;
                        failed <= 1'b0;
                        error_code <= ERR_NONE;
                        memory_read_count <= 0;
                        input_read_count <= 0;
                        weight_read_count <= 0;
                        mac_count <= 0;
                        output_write_count <= 0;
                        saturation_count <= 0;
                        if ((cfg_input_base > 32'hffff_f000) ||
                            (cfg_weight_base > 32'hfeff_ffff) ||
                            (cfg_output_base > 32'hffff_f000)) begin
                            failed <= 1'b1;
                            error_code <= ERR_CONFIG;
                            state <= S_FINISH;
                        end else begin
                            state <= S_INPUT;
                        end
                    end
                end

                S_INPUT: begin
                    if (response_fire) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        input_read_count <= input_read_count + 1'b1;
                        if (input_response_fault) begin
                            failed <= 1'b1;
                            error_code <= ERR_INPUT;
                            pending_read_q <= 1'b0;
                            state <= S_FINISH;
                        end else begin
                            input_buffer[response_count_q[11:0]] <=
                                mem_rsp_data[15:0];
                            response_count_q <= response_count_q + 1'b1;
                            pending_read_q <= request_fire;
                            if (response_count_q + 1'b1 == WIDTH) begin
                                request_count_q <= 0;
                                response_count_q <= 0;
                                pending_read_q <= 1'b0;
                                accumulator_q <= 0;
                                state <= S_WEIGHT;
                            end
                        end
                    end else if (request_fire) begin
                        pending_read_q <= 1'b1;
                    end
                    if (request_fire)
                        request_count_q <= request_count_q + 1'b1;
                end

                S_WEIGHT: begin
                    if (response_fire) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        weight_read_count <= weight_read_count + 1'b1;
                        mac_count <= mac_count + 1'b1;
                        if (weight_response_fault) begin
                            failed <= 1'b1;
                            error_code <= response_nonfinite
                                ? ERR_INPUT : ERR_NUMERIC;
                            pending_read_q <= 1'b0;
                            state <= S_FINISH;
                        end else begin
                            response_count_q <= response_count_q + 1'b1;
                            pending_read_q <= request_fire;
                            if (weight_depth == WIDTH-1) begin
                                output_buffer[weight_output] <= narrowed[15:0];
                                saturation_count <= saturation_count + narrowed[16];
                                accumulator_q <= 0;
                            end else begin
                                accumulator_q <= sum[31:0];
                            end
                            if (response_count_q + 1'b1 == WEIGHT_WORDS) begin
                                pending_read_q <= 1'b0;
                                publish_index_q <= 0;
                                state <= S_PUBLISH;
                            end
                        end
                    end else if (request_fire) begin
                        pending_read_q <= 1'b1;
                    end
                    if (request_fire)
                        request_count_q <= request_count_q + 1'b1;
                end

                S_PUBLISH: begin
                    if (out_ready) begin
                        output_write_count <= output_write_count + 1'b1;
                        if (publish_index_q == WIDTH-1)
                            state <= S_FINISH;
                        else
                            publish_index_q <= publish_index_q + 1'b1;
                    end
                end

                S_FINISH: begin
                    pending_read_q <= 1'b0;
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    pending_read_q <= 1'b0;
                    failed <= 1'b1;
                    error_code <= ERR_CONFIG;
                    state <= S_FINISH;
                end
            endcase
        end
    end
endmodule
