`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.SCALE datapath.
//
// The covered forms are amendment-A8 aux0 0 (one binary32 constant from the
// numeric profile) and aux0 1 (a same-shape BF16 factor).  Both are BF16 to
// BF16: operands widen exactly, one binary32 RNE multiply is performed, and
// the result crosses one BF16 RNE boundary.  Aux0 2 is the correctly-rounded
// logistic sigmoid and deliberately remains fail-closed.
//
// Results are buffered until every element has been decoded and computed.
// Consequently a nonfinite value or arithmetic refusal at the end of the
// operand leaves the whole architectural destination untouched.
// ---------------------------------------------------------------------------
module ot_a3_vector_scale #(
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

    localparam [2:0] S_IDLE    = 3'd0;
    localparam [2:0] S_ISSUE   = 3'd1;
    localparam [2:0] S_WAIT    = 3'd2;
    localparam [2:0] S_COMPUTE = 3'd3;
    localparam [2:0] S_COMMIT  = 3'd4;
    localparam [2:0] S_DONE    = 3'd5;

    // Element counters are bounded by MAX_ELEMENTS, not by the 32-bit
    // configuration words that carry the count, so they are sized from that
    // bound: a 32-bit index put a 32-bit adder and a 32-bit comparator in
    // series on the issue path for no reachable state.
    // Nine bits for MAX_ELEMENTS = 512: index only ever addresses an existing
    // buffer word, so it needs $clog2(MAX_ELEMENTS) bits, and cfg_count - 1 is
    // in the same range for every admitted count (cfg_count is between 1 and
    // MAX_ELEMENTS, and the truncating subtraction is exact modulo 2 **
    // INDEX_BITS because MAX_ELEMENTS <= 2 ** INDEX_BITS).
    localparam integer INDEX_BITS = $clog2(MAX_ELEMENTS);

    reg [2:0] state;
    reg [INDEX_BITS-1:0] index;
    reg [INDEX_BITS-1:0] pending_saturation_count;
    reg [31:0] result_buffer [0:MAX_ELEMENTS-1];

    // Configuration held for the operation.  It used to be read straight off
    // the input ports on the per-element path, so cfg_aux0 reached the
    // multiplier through a 16-bit comparison and carried the SDC's input
    // delay with it: the measured critical path started at cfg_aux0[4] and
    // spent 1.25 ns decoding the configuration before the first product bit
    // (OpenSTA report_checks on the mapped netlist, ASAP7 TT).  Every one of
    // these inputs must be stable from start to done, which is what the
    // engine array and the engine bench already hold.
    reg        elementwise_r;
    reg [31:0] scale_bits_r;
    reg [31:0] a_base_r, b_base_r, out_base_r;
    reg [INDEX_BITS-1:0] count_m1_r;   // cfg_count - 1; cfg_count >= 1 when admitted

    wire [33:0] decoded_a = ot_a3_format_pkg::decode_bf16(a_rd_data[15:0]);
    wire [33:0] decoded_b = ot_a3_format_pkg::decode_bf16(b_rd_data[15:0]);
    wire [31:0] right_value = elementwise_r ? decoded_b[31:0] : scale_bits_r;
    wire [33:0] product =
        ot_fp32_rne_pkg::fp32_mul_rne(decoded_a[31:0], right_value);
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(product[31:0]);

    wire scale_is_finite = cfg_scale_bits[30:23] != 8'hff;
    wire supported =
        (cfg_count != 0) && (cfg_count <= MAX_ELEMENTS) &&
        (cfg_dtype_a == FMT_BF16) &&
        ((cfg_aux0 == SCALE_CONSTANT) ||
         ((cfg_aux0 == SCALE_ELEMENTWISE) && (cfg_dtype_b == FMT_BF16)));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            index <= {INDEX_BITS{1'b0}};
            pending_saturation_count <= {INDEX_BITS{1'b0}};
            elementwise_r <= 1'b0;
            scale_bits_r <= 0;
            a_base_r <= 0;
            b_base_r <= 0;
            out_base_r <= 0;
            count_m1_r <= {INDEX_BITS{1'b0}};
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
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        saturation_count <= 0;
                        pending_saturation_count <= {INDEX_BITS{1'b0}};
                        index <= {INDEX_BITS{1'b0}};
                        elementwise_r <= (cfg_aux0 == SCALE_ELEMENTWISE);
                        scale_bits_r <= cfg_scale_bits;
                        a_base_r <= cfg_a_base;
                        b_base_r <= cfg_b_base;
                        out_base_r <= cfg_out_base;
                        count_m1_r <= cfg_count[INDEX_BITS-1:0] - {{(INDEX_BITS-1){1'b0}}, 1'b1};
                        if (!supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else if ((cfg_aux0 == SCALE_CONSTANT) &&
                                     !scale_is_finite) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            state <= S_DONE;
                        end else begin
                            state <= S_ISSUE;
                        end
                    end
                end

                S_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= a_base_r + {{(32-INDEX_BITS){1'b0}}, index};
                    if (elementwise_r) begin
                        b_rd_en <= 1'b1;
                        b_rd_addr <= b_base_r + {{(32-INDEX_BITS){1'b0}}, index};
                    end
                    state <= S_WAIT;
                end

                S_WAIT: state <= S_COMPUTE;

                S_COMPUTE: begin
                    // The buffer write is unconditional in this state.  It
                    // used to be gated by the two range tests below, which
                    // sit at the far end of the multiply-and-round chain, so
                    // one NAND2 at the end of that chain drove the write
                    // enable of every one of the MAX_ELEMENTS x 32 buffer
                    // flip-flops: 2.946 ns in that single gate, and 2.082 ns
                    // in the NOR2 behind it, out of a 9.372 ns path
                    // (OpenSTA report_checks on the mapped netlist).  The
                    // enable is now a decode of the state register, so the
                    // fan-out is no longer stacked on top of the arithmetic.
                    // Nothing observable changes: a refused element leaves
                    // the architectural destination untouched because
                    // S_COMMIT never runs, and the next operation rewrites
                    // every buffer word it will later read.
                    result_buffer[index] <= {16'b0, narrowed[15:0]};
                    if ((decoded_a[33:32] != 0) ||
                        (elementwise_r && (decoded_b[33:32] != 0))) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if ((product[33:32] != 0) ||
                                 (narrowed[18:17] != 0)) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        if (narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + {{(INDEX_BITS-1){1'b0}}, 1'b1};
                        if (index == count_m1_r) begin
                            index <= {INDEX_BITS{1'b0}};
                            state <= S_COMMIT;
                        end else begin
                            index <= index + {{(INDEX_BITS-1){1'b0}}, 1'b1};
                            state <= S_ISSUE;
                        end
                    end
                end

                S_COMMIT: begin
                    out_we <= 1'b1;
                    out_addr <= out_base_r + {{(32-INDEX_BITS){1'b0}}, index};
                    out_data <= result_buffer[index];
                    out_count <= out_count + 1;
                    if (index == count_m1_r) begin
                        saturation_count <=
                            {{(32-INDEX_BITS){1'b0}}, pending_saturation_count};
                        state <= S_DONE;
                    end else begin
                        index <= index + {{(INDEX_BITS-1){1'b0}}, 1'b1};
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
