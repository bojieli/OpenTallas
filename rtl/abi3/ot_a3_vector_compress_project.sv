`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.COMPRESS / COMPRESS_PROJECT datapath (aux0 == 0).
//
// BF16 hidden rows are projected by independent BF16 KV and gate matrices.
// Each dot product walks the reduction dimension in ascending order and keeps
// a binary32 accumulator.  The FP32 output is packed in the frozen
// [row, plane, column] order: the complete KV plane precedes the gate plane
// for each row.  Other COMPRESS sub-cases remain fail-closed.
//
// A complete input preflight and a private output buffer make the operation
// atomic with respect to every detected operand or arithmetic fault.
// ---------------------------------------------------------------------------
module ot_a3_vector_compress_project #(
    parameter [15:0] MAX_ROWS = 16'd8,
    parameter [15:0] MAX_COLS = 16'd16,
    parameter [15:0] MAX_DEPTH = 16'd64,
    parameter integer MAX_OUTPUTS = MAX_ROWS * MAX_COLS * 2
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [15:0] cfg_depth,
    input  wire [31:0] cfg_count,
    input  wire [15:0] cfg_aux0,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_hidden_base,
    input  wire [31:0] cfg_kv_base,
    input  wire [31:0] cfg_gate_base,
    input  wire [31:0] cfg_out_base,

    output reg         h_rd_en,
    output reg  [31:0] h_rd_addr,
    input  wire [31:0] h_rd_data,
    output reg         kv_rd_en,
    output reg  [31:0] kv_rd_addr,
    input  wire [31:0] kv_rd_data,
    output reg         gate_rd_en,
    output reg  [31:0] gate_rd_addr,
    input  wire [31:0] gate_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] work_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [15:0] COMPRESS_PROJECT = 16'd0;

    localparam [3:0] S_IDLE       = 4'd0;
    localparam [3:0] S_SCAN_ISSUE = 4'd1;
    localparam [3:0] S_SCAN_WAIT  = 4'd2;
    localparam [3:0] S_SCAN_CHECK = 4'd3;
    localparam [3:0] S_DOT_ISSUE  = 4'd4;
    localparam [3:0] S_DOT_WAIT   = 4'd5;
    localparam [3:0] S_DOT_STEP   = 4'd6;
    localparam [3:0] S_COMMIT     = 4'd7;
    //: The pipelined multiply-accumulate's wait state. Routed at a 4 ns target this
    //: engine came back at 239.7 MHz -- below the 276.9 MHz design limiter and the
    //: last measured rung of ot_a3_engine_array -- and its worst path ran
    //: kv_rd_data[12], an INPUT PORT, through the operand decode and the FUSED
    //: bf16-by-bf16-into-fp32 product-add to result_buffer[209][29]: 119 cells,
    //: missing the target by 0.172 ns. The store address was already moved off this
    //: path; what is left is the arithmetic.
    localparam [3:0] S_DOT_PIPE   = 4'd9;
    localparam [3:0] S_DONE       = 4'd8;

    reg [3:0] state;
    reg [1:0] scan_kind;
    reg [31:0] index;
    reg [15:0] row;
    reg        plane;
    reg [15:0] col;
    reg [15:0] depth_index;
    reg [31:0] accumulator;
    reg [31:0] result_buffer [0:MAX_OUTPUTS-1];

    wire [31:0] hidden_elements =
        {16'b0, cfg_rows} * {16'b0, cfg_depth};
    wire [31:0] matrix_elements =
        {16'b0, cfg_cols} * {16'b0, cfg_depth};
    wire [31:0] scan_limit = (scan_kind == 0)
                           ? hidden_elements : matrix_elements;

    wire [33:0] decoded_hidden =
        ot_a3_format_pkg::decode_bf16(h_rd_data[15:0]);
    wire [33:0] decoded_kv =
        ot_a3_format_pkg::decode_bf16(kv_rd_data[15:0]);
    wire [33:0] decoded_gate =
        ot_a3_format_pkg::decode_bf16(gate_rd_data[15:0]);
    wire [33:0] decoded_weight = plane ? decoded_gate : decoded_kv;
    wire [15:0] weight_code = plane
        ? gate_rd_data[15:0] : kv_rd_data[15:0];
    //: rtl/proto/ot_mac_bf16_fp32_pipe.sv is the same RN(a*b+c) in five stages and
    //: is qualified bit-identical to ot_fp32_rne_pkg's fused product-add, error
    //: codes included -- 0 none, 1 nonfinite input, 2 a finite exact result outside
    //: binary32, which this engine reports as ERR_OPERAND_NONFINITE and
    //: ERR_ACCUMULATE_RANGE exactly as the one-cycle form did. So this is a latency
    //: change and not a numeric one.
    //:
    //: THE COST, STATED: five cycles per reduction index instead of one, so a depth
    //: step goes from three cycles to seven. Two of the three were always memory --
    //: issue and wait -- so the arithmetic was a third of the loop and is now
    //: five sevenths. An interleaved form over two columns would pay nothing at all,
    //: because a chain issuing every six cycles needs its own result only after
    //: five; it is not done here because it reorders the operand refusals, and the
    //: order in which this engine refuses is part of what it publishes.
    reg         mac_valid;
    reg  [15:0] mac_a, mac_b;
    reg  [31:0] mac_c;
    wire [31:0] mac_y;
    wire [1:0]  mac_err;
    wire        mac_done;
    ot_mac_bf16_fp32_pipe product_add (
        .clk(clk), .rst_n(rst_n), .valid_in(mac_valid),
        .a(mac_a), .b(mac_b), .c(mac_c),
        .y(mac_y), .err(mac_err), .valid_out(mac_done)
    );

    //: THE STORE'S ADDRESS IS NOT THE PRODUCT-ADD'S WORK.  The routed critical path ran
    //: kv_rd_data[12] to result_buffer[59][29] -- 110 cell arcs holding the operand
    //: decode, the FUSED bf16 product-add AND the buffer index, which is
    //: ``row * cfg_cols * 2 + (plane ? cfg_cols : 0) + col``: a 32-bit multiply and two
    //: adds sharing the cycle with the multiply-accumulate.  The block came back at
    //: 232.3 MHz not met.
    //:
    //: The index depends only on row, col and plane, which are registers that hold
    //: still for the whole cfg_depth-long accumulation, so it is computed one cycle
    //: ahead instead.  Three cycles separate a change of col, row or plane from the
    //: store that uses it -- S_DOT_ISSUE, S_DOT_WAIT, S_DOT_STEP -- so the registered
    //: value is current even at cfg_depth == 1, and the address written is the same
    //: address.
    reg [31:0] store_index_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) store_index_q <= 32'b0;
        else store_index_q <=
            ({16'b0, row} * {16'b0, cfg_cols} * 2) +
            (plane ? {16'b0, cfg_cols} : 32'b0) + {16'b0, col};

    wire configuration_supported =
        (cfg_aux0 == COMPRESS_PROJECT) &&
        (cfg_dtype_a == FMT_BF16) && (cfg_dtype_b == FMT_BF16) &&
        (cfg_rows != 0) && (cfg_rows <= MAX_ROWS) &&
        (cfg_cols != 0) && (cfg_cols <= MAX_COLS) &&
        (cfg_depth != 0) && (cfg_depth <= MAX_DEPTH) &&
        (cfg_count == ({16'b0, cfg_rows} * {16'b0, cfg_cols} * 2));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mac_valid <= 1'b0;
            mac_a <= 16'b0; mac_b <= 16'b0; mac_c <= 32'b0;
            state <= S_IDLE;
            scan_kind <= 0;
            index <= 0;
            row <= 0;
            plane <= 0;
            col <= 0;
            depth_index <= 0;
            accumulator <= 0;
            h_rd_en <= 1'b0;
            h_rd_addr <= 0;
            kv_rd_en <= 1'b0;
            kv_rd_addr <= 0;
            gate_rd_en <= 1'b0;
            gate_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
            work_count <= 0;
        end else begin
            //: One cycle of valid_in: the unit latches on it and holding it
            //: would issue a second product-add.
            mac_valid <= 1'b0;
            done <= 1'b0;
            h_rd_en <= 1'b0;
            kv_rd_en <= 1'b0;
            gate_rd_en <= 1'b0;
            out_we <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        work_count <= 0;
                        scan_kind <= 0;
                        index <= 0;
                        row <= 0;
                        plane <= 0;
                        col <= 0;
                        depth_index <= 0;
                        accumulator <= 0;
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
                        h_rd_en <= 1'b1;
                        h_rd_addr <= cfg_hidden_base + index;
                    end else if (scan_kind == 1) begin
                        kv_rd_en <= 1'b1;
                        kv_rd_addr <= cfg_kv_base + index;
                    end else begin
                        gate_rd_en <= 1'b1;
                        gate_rd_addr <= cfg_gate_base + index;
                    end
                    state <= S_SCAN_WAIT;
                end

                S_SCAN_WAIT: state <= S_SCAN_CHECK;

                S_SCAN_CHECK: begin
                    if (((scan_kind == 0) &&
                         (decoded_hidden[33:32] != 0)) ||
                        ((scan_kind == 1) && (decoded_kv[33:32] != 0)) ||
                        ((scan_kind == 2) && (decoded_gate[33:32] != 0))) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (index + 1 == scan_limit) begin
                        index <= 0;
                        if (scan_kind == 2) begin
                            row <= 0;
                            plane <= 0;
                            col <= 0;
                            depth_index <= 0;
                            accumulator <= 0;
                            state <= S_DOT_ISSUE;
                        end else begin
                            scan_kind <= scan_kind + 1;
                            state <= S_SCAN_ISSUE;
                        end
                    end else begin
                        index <= index + 1;
                        state <= S_SCAN_ISSUE;
                    end
                end

                S_DOT_ISSUE: begin
                    h_rd_en <= 1'b1;
                    h_rd_addr <= cfg_hidden_base +
                        ({16'b0, row} * {16'b0, cfg_depth}) +
                        {16'b0, depth_index};
                    if (!plane) begin
                        kv_rd_en <= 1'b1;
                        kv_rd_addr <= cfg_kv_base +
                            ({16'b0, col} * {16'b0, cfg_depth}) +
                            {16'b0, depth_index};
                    end else begin
                        gate_rd_en <= 1'b1;
                        gate_rd_addr <= cfg_gate_base +
                            ({16'b0, col} * {16'b0, cfg_depth}) +
                            {16'b0, depth_index};
                    end
                    state <= S_DOT_WAIT;
                end

                S_DOT_WAIT: state <= S_DOT_STEP;

                //: The operand check stays HERE, ahead of the unit, so a nonfinite
                //: operand is refused before it is issued and the refusal order is
                //: the one this engine always had.
                S_DOT_STEP: begin
                    if ((decoded_hidden[33:32] != 0) ||
                        (decoded_weight[33:32] != 0)) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else begin
                        mac_a <= h_rd_data[15:0];
                        mac_b <= weight_code;
                        mac_c <= accumulator;
                        mac_valid <= 1'b1;
                        state <= S_DOT_PIPE;
                    end
                end

                S_DOT_PIPE: begin
                    if (!mac_done) begin
                        //: waiting; the unit is five stages deep
                    end else if (mac_err != 2'd0) begin
                        error_code <= (mac_err == 2'd1)
                                      ? ERR_OPERAND_NONFINITE
                                      : ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else if (depth_index + 1 < cfg_depth) begin
                        accumulator <= mac_y;
                        depth_index <= depth_index + 1;
                        state <= S_DOT_ISSUE;
                    end else begin
                        // Frozen projection_order: kv_then_gate.  The index is
                        // the registered one, computed a cycle ahead.
                        result_buffer[store_index_q] <= mac_y;
                        accumulator <= 0;
                        depth_index <= 0;
                        if (col + 1 < cfg_cols) begin
                            col <= col + 1;
                            state <= S_DOT_ISSUE;
                        end else if (!plane) begin
                            col <= 0;
                            plane <= 1'b1;
                            state <= S_DOT_ISSUE;
                        end else if (row + 1 < cfg_rows) begin
                            row <= row + 1;
                            plane <= 1'b0;
                            col <= 0;
                            state <= S_DOT_ISSUE;
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
