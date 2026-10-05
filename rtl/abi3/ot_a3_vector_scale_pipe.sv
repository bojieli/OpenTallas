`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VECTOR.SCALE, pipelined: one element per cycle.
//
// ``ot_a3_vector_scale`` performs the binary32 multiply COMBINATIONALLY, and on
// ASAP7 that single cone is what sets the ABI 3.0 datapath's clock.  Measured on
// two probes identical but for the construct, both closed:
//
//     combinational  ot_probe_fp32_mul        247.1 MHz  1,462.0 um2
//     pipelined      ot_probe_fp32_mul_pipe   959.0 MHz    678.5 um2
//
// Substituting the pipelined multiplier alone would be a bad trade: its latency
// is five cycles, so a three-cycle-per-element loop becomes eight, and 3.88x the
// clock against 2.67x the cycles is barely a gain.  The win needs the loop
// rebuilt around the pipe rather than stalled on it.
//
// SO THE LOOP IS REBUILT.  Reads issue every cycle, the multiplier accepts an
// element every cycle, and results retire every cycle behind it.  An operation
// of N elements costs N + 7 cycles of arithmetic instead of 3N: the index, the
// operand-nonfinite flags and the saturation decision travel WITH the element
// through the pipe rather than being recomputed at a state boundary.
//
// EQUIVALENCE.  ``ot_fp32_mul_rne_pipe`` documents itself bit-identical to
// ``ot_fp32_rne_pkg::fp32_mul_rne``, including its non-IEEE edges, and its
// ``err`` encoding is the package's own (E_NONE / E_NONFINITE / E_OVERFLOW ==
// FP_ERR_NONE / FP_ERR_NONFINITE / FP_ERR_OVERFLOW).  So the arithmetic this
// module performs is the same arithmetic in a different schedule, and
// ``rtl/test/tb_vector_scale_pipe_equivalence.sv`` requires the two engines to
// agree on every output for every vector rather than taking that on trust.
//
// WHAT IS DELIBERATELY UNCHANGED: results are buffered until the whole operand
// has been computed, so a refusal anywhere leaves the architectural destination
// untouched; the buffer write is not gated by the arithmetic's own range tests,
// which is what kept a NAND2 off the write enable of every buffer flip-flop;
// and the first refusal in program order is the one reported, which an in-order
// pipe preserves for free.
// ---------------------------------------------------------------------------
module ot_a3_vector_scale_pipe #(
    parameter integer MAX_ELEMENTS = 512
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [15:0] cfg_aux0,
    input  wire [31:0] cfg_scale_bits,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire [31:0] cfg_out_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output reg         b_rd_en,
    output reg  [31:0] b_rd_addr,
    input  wire [31:0] b_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [15:0] SCALE_CONSTANT = 16'd0;
    localparam [15:0] SCALE_ELEMENTWISE = 16'd1;

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_RUN    = 3'd1;
    localparam [2:0] S_COMMIT = 3'd2;
    localparam [2:0] S_DRAIN  = 3'd3;
    localparam [2:0] S_DONE   = 3'd4;

    localparam integer INDEX_BITS = $clog2(MAX_ELEMENTS);
    //: ``ot_fp32_mul_rne_pipe``'s valid chain is valid_in -> s1_v -> s2_v ->
    //: s3_v -> s4_v -> valid_out: five registers.
    localparam integer MUL_LATENCY = 5;

    reg [2:0] state;
    //: A refusal abandons the operand with elements still inside the
    //: multiplier.  ``ot_fp32_mul_rne_pipe`` has no flush, so those elements
    //: WILL emerge -- and if the engine has already returned to S_IDLE and been
    //: restarted, they emerge as retires of the NEXT operation.  Measured: the
    //: engine campaign's cases 11 and 13 are refusals, and unflushed they
    //: committed six words each and reported the wrong fault code, because a
    //: stale in-flight element retired first.  S_DRAIN holds the engine until
    //: the pipe is empty.  Two cycles beyond the multiply cover the operand
    //: address and data stages ahead of it.
    reg [3:0] drain_count;
    reg [INDEX_BITS-1:0] issue_index;
    reg issuing;
    reg [INDEX_BITS-1:0] commit_index;
    reg [INDEX_BITS-1:0] pending_saturation_count;
    reg [31:0] result_buffer [0:MAX_ELEMENTS-1];

    reg        elementwise_r;
    reg [31:0] scale_bits_r;
    reg [31:0] a_base_r, b_base_r, out_base_r;
    reg [INDEX_BITS-1:0] count_m1_r;

    // The address is a registered output and the operand memory answers one
    // cycle later, so an element issued at cycle t has its data at t+2.  Two
    // valid stages carry the element across that, and the multiplier's own
    // valid_in/valid_out carries it across the arithmetic.
    reg v_addr, v_data;
    reg [INDEX_BITS-1:0] i_addr, i_data;

    wire [33:0] decoded_a = ot_a3_format_pkg::decode_bf16(a_rd_data[15:0]);
    wire [33:0] decoded_b = ot_a3_format_pkg::decode_bf16(b_rd_data[15:0]);
    wire [31:0] right_value = elementwise_r ? decoded_b[31:0] : scale_bits_r;
    wire        operand_nonfinite =
        (decoded_a[33:32] != 2'b00) ||
        (elementwise_r && (decoded_b[33:32] != 2'b00));

    wire [31:0] product_value;
    wire [1:0]  product_err;
    wire        product_valid;

    ot_fp32_mul_rne_pipe multiply (
        .clk(clk),
        .rst_n(rst_n),
        .valid_in(v_data),
        .a(decoded_a[31:0]),
        .b(right_value),
        .y(product_value),
        .err(product_err),
        .valid_out(product_valid)
    );

    // The index and the operand verdict ride alongside the arithmetic.  Stage
    // MUL_LATENCY-1 is in step with valid_out.
    reg [INDEX_BITS-1:0] idx_pipe [0:MUL_LATENCY-1];
    reg [MUL_LATENCY-1:0] nonfinite_pipe;

    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(product_value);
    wire [INDEX_BITS-1:0] retire_index = idx_pipe[MUL_LATENCY-1];
    wire retire_nonfinite = nonfinite_pipe[MUL_LATENCY-1];
    wire retire_range = (product_err != 2'b00) || (narrowed[18:17] != 2'b00);

    wire scale_is_finite = cfg_scale_bits[30:23] != 8'hff;
    wire supported =
        (cfg_count != 0) && (cfg_count <= MAX_ELEMENTS) &&
        (cfg_dtype_a == FMT_BF16) &&
        ((cfg_aux0 == SCALE_CONSTANT) ||
         ((cfg_aux0 == SCALE_ELEMENTWISE) && (cfg_dtype_b == FMT_BF16)));

    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            drain_count <= 4'd0;
            issue_index <= {INDEX_BITS{1'b0}};
            issuing <= 1'b0;
            commit_index <= {INDEX_BITS{1'b0}};
            pending_saturation_count <= {INDEX_BITS{1'b0}};
            elementwise_r <= 1'b0;
            scale_bits_r <= 0;
            a_base_r <= 0;
            b_base_r <= 0;
            out_base_r <= 0;
            count_m1_r <= {INDEX_BITS{1'b0}};
            v_addr <= 1'b0;
            v_data <= 1'b0;
            i_addr <= {INDEX_BITS{1'b0}};
            i_data <= {INDEX_BITS{1'b0}};
            nonfinite_pipe <= {MUL_LATENCY{1'b0}};
            for (k = 0; k < MUL_LATENCY; k = k + 1)
                idx_pipe[k] <= {INDEX_BITS{1'b0}};
            a_rd_en <= 1'b0;
            a_rd_addr <= 0;
            b_rd_en <= 1'b0;
            b_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
            saturation_count <= 0;
        end else begin
            done <= 1'b0;
            a_rd_en <= 1'b0;
            b_rd_en <= 1'b0;
            out_we <= 1'b0;

            // The operand-address and operand-data valid stages, and the
            // delay line that keeps the element's identity with its product.
            v_addr <= 1'b0;
            v_data <= v_addr;
            i_data <= i_addr;
            idx_pipe[0] <= i_data;
            nonfinite_pipe[0] <= operand_nonfinite;
            for (k = 1; k < MUL_LATENCY; k = k + 1) begin
                idx_pipe[k] <= idx_pipe[k-1];
                nonfinite_pipe[k] <= nonfinite_pipe[k-1];
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        saturation_count <= 0;
                        pending_saturation_count <= {INDEX_BITS{1'b0}};
                        issue_index <= {INDEX_BITS{1'b0}};
                        commit_index <= {INDEX_BITS{1'b0}};
                        elementwise_r <= (cfg_aux0 == SCALE_ELEMENTWISE);
                        scale_bits_r <= cfg_scale_bits;
                        a_base_r <= cfg_a_base;
                        b_base_r <= cfg_b_base;
                        out_base_r <= cfg_out_base;
                        count_m1_r <= cfg_count[INDEX_BITS-1:0] -
                                      {{(INDEX_BITS-1){1'b0}}, 1'b1};
                        if (!supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else if ((cfg_aux0 == SCALE_CONSTANT) &&
                                     !scale_is_finite) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            state <= S_DONE;
                        end else begin
                            issuing <= 1'b1;
                            state <= S_RUN;
                        end
                    end
                end

                S_RUN: begin
                    // Issue one element per cycle until the operand is spent.
                    if (issuing) begin
                        a_rd_en <= 1'b1;
                        a_rd_addr <= a_base_r +
                                     {{(32-INDEX_BITS){1'b0}}, issue_index};
                        if (elementwise_r) begin
                            b_rd_en <= 1'b1;
                            b_rd_addr <= b_base_r +
                                         {{(32-INDEX_BITS){1'b0}}, issue_index};
                        end
                        v_addr <= 1'b1;
                        i_addr <= issue_index;
                        if (issue_index == count_m1_r)
                            issuing <= 1'b0;
                        else
                            issue_index <= issue_index +
                                           {{(INDEX_BITS-1){1'b0}}, 1'b1};
                    end

                    // Retire one element per cycle behind it.  The write is
                    // unconditional, as in the combinational engine: a refused
                    // element leaves the architectural destination untouched
                    // because S_COMMIT never runs.
                    if (product_valid) begin
                        result_buffer[retire_index] <= {16'b0, narrowed[15:0]};
                        if (retire_nonfinite) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            issuing <= 1'b0;
                            drain_count <= MUL_LATENCY + 2;
                            state <= S_DRAIN;
                        end else if (retire_range) begin
                            error_code <= ERR_PRODUCT_RANGE;
                            issuing <= 1'b0;
                            drain_count <= MUL_LATENCY + 2;
                            state <= S_DRAIN;
                        end else begin
                            if (narrowed[16])
                                pending_saturation_count <=
                                    pending_saturation_count +
                                    {{(INDEX_BITS-1){1'b0}}, 1'b1};
                            if (retire_index == count_m1_r)
                                state <= S_COMMIT;
                        end
                    end
                end

                S_DRAIN: begin
                    // Let the abandoned elements fall out of the pipe.  Nothing
                    // is inspected and nothing is committed: the architectural
                    // destination is untouched because S_COMMIT never runs.
                    issuing <= 1'b0;
                    if (drain_count == 4'd0)
                        state <= S_DONE;
                    else
                        drain_count <= drain_count - 4'd1;
                end

                S_COMMIT: begin
                    out_we <= 1'b1;
                    out_addr <= out_base_r +
                                {{(32-INDEX_BITS){1'b0}}, commit_index};
                    out_data <= result_buffer[commit_index];
                    out_count <= out_count + 1;
                    if (commit_index == count_m1_r) begin
                        saturation_count <=
                            {{(32-INDEX_BITS){1'b0}}, pending_saturation_count};
                        state <= S_DONE;
                    end else begin
                        commit_index <= commit_index +
                                        {{(INDEX_BITS-1){1'b0}}, 1'b1};
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    issuing <= 1'b0;
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
