`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One TENSOR contraction lane under bf16_bf16_fp32_sequential_rne_v1.
//
// The lane walks [M,K] x [N,K]^T in ascending output order and, for every
// output element, accumulates its own K products in strictly ascending K.
// That is the whole numeric content of the contract:
//
//   * both operands widen to binary32 exactly (ot_a3_format_pkg);
//   * a block-scaled operand is multiplied by its decoded E8M0 scale, one
//     binary32 round-to-nearest-even multiply per element, before the product;
//   * the product is one binary32 RNE multiply, and exact zero is
//     canonicalised positive before it enters the accumulator;
//   * the accumulation is one binary32 RNE add per reduction index, in
//     ascending K, starting from +0.0;
//   * the output is one RNE conversion of the finished accumulator to BF16,
//     saturating to the largest finite BF16 code and counting that.
//
// Adding +0.0 as the first operand is not a deviation: the first product is
// canonicalised, so +0.0 + p == p for every p the accumulator can start with.
//
// Everything fails closed.  A nonfinite BF16 operand, a reserved E4M3FN or
// E8M0 encoding, a product that leaves the binary32 range, a scale application
// that leaves it and an accumulation that leaves it each stop the lane with a
// distinct error and write no output element.
//
// THE E8M0 SCALE ADDRESS IS NOT DIVIDED ANY MORE, AND THAT WAS THIS LANE'S CLOCK.
// Routed on ASAP7 at a 3.4 ns target the lane came back at 64.7 MHz -- the slowest
// block in the ABI 3.0 datapath by a factor of four -- and the worst path ran
// cfg_block_rows_b[15] to t_rd_addr[31] through 590 cells of which 724 were OA21
// and AO21: the shape of a restoring divide. scale_index() below performs THREE
// 32-bit divisions and a multiply, and S_ISSUE called it TWICE, so six divisions
// shared one cycle with the address adds.
//
// None of the three quotients has to be divided per element, which is the same
// observation ot_a3_lane_pipelined already acts on:
//
//   * ``k / block`` is a counter that wraps at ``block`` and increments on the
//     wrap. k advances by one per reduction index, so the counter is exact for
//     ANY block -- this lane keeps no divisibility restriction.
//   * ``row / rows_per_block`` and ``col / rows_per_block`` are the same shape,
//     wrapping at rows_per_block and adding a stride on the wrap.
//   * ``depth / block`` -- the stride -- needs no divider EITHER. Advance the k
//     counter once more at the end of a k loop and it holds exactly
//     ``depth / block``, because the loop performed depth-1 advances and this is
//     the depth'th. It is latched on the first S_STORE, which is strictly before
//     row or column can first advance, so the stride is always current when a
//     wrap needs it.
//
// So the issue path carries two 32-bit adds where it carried six divisions, a
// multiply and two adds, and NOTHING about the latency changes: no admission
// state, no extra cycle, the first lane-op still issues one cycle after start and
// the rate is still one multiply-accumulate every five cycles. scale_index() is
// kept as the CONTRACT the counters must reproduce, and
// rtl/test/tb_a3_mac_lane_scale_index_equiv.sv checks the lane's emitted addresses
// against it element by element rather than asserting they agree.
//
// Reduction is one multiply-accumulate every five cycles by construction --
// address, memory latency, scale, multiply, accumulate.  That is a
// control-sequencing choice made to keep one binary32 operation per pipeline
// stage; it is not a throughput claim, no result bit depends on it, and it is
// not a rate any cycle model may read.
// ---------------------------------------------------------------------------
module ot_a3_mac_lane (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [15:0] cfg_rows,          // M
    input  wire [15:0] cfg_cols,          // N
    input  wire [15:0] cfg_depth,         // K
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire        cfg_scale_a,
    input  wire        cfg_scale_b,
    input  wire [15:0] cfg_block_a,       // scale_block_elements, operand A
    input  wire [15:0] cfg_block_b,
    input  wire [15:0] cfg_block_rows_a,  // scale_block_rows, operand A
    input  wire [15:0] cfg_block_rows_b,
    input  wire [31:0] cfg_scale_a_base,
    input  wire [31:0] cfg_scale_b_base,
    input  wire [31:0] cfg_out_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output reg         b_rd_en,
    output reg  [31:0] b_rd_addr,
    input  wire [31:0] b_rd_data,
    output reg         s_rd_en,
    output reg  [31:0] s_rd_addr,
    input  wire [31:0] s_rd_data,
    output reg         t_rd_en,
    output reg  [31:0] t_rd_addr,
    input  wire [31:0] t_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] mac_count
);
    // Package constants are re-declared as local parameters, and package
    // functions are called through their scope, rather than being pulled in
    // with a wildcard import.  Two reasons, both found the hard way.  Icarus 11
    // does not resolve a wildcard-imported identifier that appears only inside
    // a module-instance port connection -- it silently creates an implicit net
    // of that name, which then shadows the constant for the whole module.  And
    // the pinned Yosys 0.68 Verilog frontend rejects ``import`` outright, in
    // the header and in the body, so a wildcard import is a block that cannot
    // be synthesised or routed at all.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SELECT_NONFINITE = ot_a3_engine_pkg::ERR_SELECT_NONFINITE;
    localparam [7:0] ERR_SCALE_RANGE = ot_a3_engine_pkg::ERR_SCALE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [3:0] S_IDLE   = 4'd0;
    localparam [3:0] S_ISSUE  = 4'd1;
    // The operand memories answer one cycle after the address is driven, so a
    // read issued in S_ISSUE is not readable until the cycle after S_WAIT.
    localparam [3:0] S_WAIT   = 4'd7;
    localparam [3:0] S_SCALE  = 4'd2;
    localparam [3:0] S_MUL    = 4'd3;
    localparam [3:0] S_ACC    = 4'd4;
    localparam [3:0] S_STORE  = 4'd5;
    localparam [3:0] S_DONE   = 4'd6;
    //: One wait state per pipelined unit. Routed at a 3.4 ns target with the scale
    //: address computed by counters this lane came back at 158.9 MHz, and its worst
    //: path then ran acc[23] to k[2] through 256 cells: the combinational
    //: fp32_add_rne(acc, product) feeding the loop counter. The three binary32
    //: operations it performs per reduction index -- two scale multiplies, the
    //: product, the accumulate -- are the remaining wall, and they are the same wall
    //: ot_a3_vector_add, ot_a3_vector_mhc_post and ot_a3_vector_compress_project
    //: each cleared today by substituting a five-stage pipe for a combinational cone.
    //:
    //: THE CYCLE COST FALLS ON NOTHING THE SHIPPED MODELS RUN. ot_a3_engine_array
    //: routes a descriptor to ot_a3_mac_lane_pipe unless it declares a dtype pair or
    //: a scale object that lane does not claim, and all 272 TENSOR.MATMUL operators
    //: in the shipped V4.1 HBM cell are claimed -- 26 BF16 x BF16 and 246 involving
    //: FP8_E4M3FN. So a reduction index here costs 20 cycles instead of 5 on paths no
    //: shipped model takes, and the design clock stops being held at 158.9 MHz by a
    //: lane that executes none of them.
    localparam [3:0] S_SCALE_PIPE = 4'd8;
    localparam [3:0] S_MUL_PIPE   = 4'd9;
    localparam [3:0] S_ACC_PIPE   = 4'd10;

    reg [3:0]  state;
    reg [15:0] row;
    reg [15:0] col;
    reg [15:0] k;
    reg [31:0] acc;
    reg [31:0] value_a;
    reg [31:0] value_b;
    reg [31:0] product;

    wire [33:0] decoded_a = ot_a3_format_pkg::decode_element(cfg_dtype_a, a_rd_data);
    wire [33:0] decoded_b = ot_a3_format_pkg::decode_element(cfg_dtype_b, b_rd_data);
    wire [33:0] decoded_scale_a = ot_a3_format_pkg::decode_e8m0(s_rd_data[7:0]);
    wire [33:0] decoded_scale_b = ot_a3_format_pkg::decode_e8m0(t_rd_data[7:0]);
    //: TWO PIPELINED MULTIPLIERS AND ONE PIPELINED ADDER. The two scale multiplies
    //: are independent and share one valid_in so they retire together; the product
    //: reuses the first of them, because the scales and the product never happen in
    //: the same state. rtl/proto/ot_fp32_mul_rne_pipe.sv and
    //: rtl/proto/ot_fp32_add_rne_pipe.sv are qualified bit-identical to the
    //: ot_fp32_rne_pkg functions they replace, including the two places that
    //: authority is deliberately not IEEE-754 -- (-0) + (-0) is +0 and every zero
    //: result is canonical +0 -- so this is a latency change and not a numeric one.
    reg         mul_valid;
    reg  [31:0] mul_a_x, mul_a_y, mul_b_x, mul_b_y;
    wire [31:0] mul_a_out, mul_b_out;
    wire [1:0]  mul_a_err, mul_b_err;
    wire        mul_a_done, mul_b_done;
    ot_fp32_mul_rne_pipe multiplier_a (
        .clk(clk), .rst_n(rst_n), .valid_in(mul_valid),
        .a(mul_a_x), .b(mul_a_y),
        .y(mul_a_out), .err(mul_a_err), .valid_out(mul_a_done)
    );
    ot_fp32_mul_rne_pipe multiplier_b (
        .clk(clk), .rst_n(rst_n), .valid_in(mul_valid),
        .a(mul_b_x), .b(mul_b_y),
        .y(mul_b_out), .err(mul_b_err), .valid_out(mul_b_done)
    );

    reg         add_valid;
    reg  [31:0] add_x, add_y;
    wire [31:0] add_out;
    wire [1:0]  add_err;
    wire        add_done;
    ot_fp32_add_rne_pipe accumulator_add (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid),
        .a(add_x), .b(add_y),
        .y(add_out), .err(add_err), .valid_out(add_done)
    );

    //: The narrowing reads the accumulator, which is a register, so it stands alone
    //: in S_STORE's cycle exactly as it did before.
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(acc);

    //: The three quotients of A15's scale index, as counters. Widths: a stride is
    //: depth/block <= 65535 and it is added at most 65535 times, so the running
    //: scale offset needs 32 bits -- the same width scale_index() returns.
    reg [15:0] k_mod_a, k_mod_b;
    reg [31:0] k_scale_a, k_scale_b;
    reg [15:0] row_mod_a, col_mod_b;
    reg [31:0] row_scale_a, col_scale_b;
    reg [31:0] cpr_a, cpr_b;          //: depth / block, the codes-per-row stride
    reg        cpr_valid;

    //: A view that declares no scale object carries no block size, so one is
    //: substituted rather than dividing by zero -- exactly as scale_index() does,
    //: and the address it produces is never read in that case.
    wire [15:0] elements_per_block_a = (cfg_block_a == 16'd0) ? 16'd1 : cfg_block_a;
    wire [15:0] elements_per_block_b = (cfg_block_b == 16'd0) ? 16'd1 : cfg_block_b;
    wire [15:0] rows_per_block_a =
        (cfg_block_rows_a == 16'd0) ? 16'd1 : cfg_block_rows_a;
    wire [15:0] rows_per_block_b =
        (cfg_block_rows_b == 16'd0) ? 16'd1 : cfg_block_rows_b;

    //: One advance of the k counter: wrap at the block size, carry into the
    //: quotient. Used per reduction index AND once more at the end of a k loop,
    //: where the carried quotient is depth/block.
    wire        k_a_wraps = (k_mod_a + 16'd1 == elements_per_block_a);
    wire [15:0] k_mod_a_next = k_a_wraps ? 16'd0 : (k_mod_a + 16'd1);
    wire [31:0] k_scale_a_next = k_a_wraps ? (k_scale_a + 32'd1) : k_scale_a;
    wire        k_b_wraps = (k_mod_b + 16'd1 == elements_per_block_b);
    wire [15:0] k_mod_b_next = k_b_wraps ? 16'd0 : (k_mod_b + 16'd1);
    wire [31:0] k_scale_b_next = k_b_wraps ? (k_scale_b + 32'd1) : k_scale_b;

    //: The stride to use THIS cycle: the latched one once it exists, and
    //: otherwise the value the final k advance is producing right now -- which
    //: matters when cfg_cols is one, because then the first S_STORE both latches
    //: the stride and advances the row.
    wire [31:0] cpr_a_now = cpr_valid ? cpr_a : k_scale_a_next;
    wire [31:0] cpr_b_now = cpr_valid ? cpr_b : k_scale_b_next;

    // Amendment A15: the E8M0 code for element (row, column) of a view over
    // ``depth`` columns is
    //     (row / block_rows) * (depth / block) + (column / block)
    // and amendment A8 is the block_rows = 1 case of exactly that.
    //: KEPT AS THE CONTRACT, not called on the issue path any more: the counters
    //: above must reproduce this element by element, and
    //: rtl/test/tb_a3_mac_lane_scale_index_equiv.sv checks that they do.
    function automatic [31:0] scale_index;
        input [15:0] element_row;
        input [15:0] element_column;
        input [15:0] depth;
        input [15:0] block;
        input [15:0] block_rows;
        reg [15:0] rows_per_block;
        reg [15:0] elements_per_block;
        begin
            rows_per_block = (block_rows == 16'd0) ? 16'd1 : block_rows;
            // A view that declares no scale object carries no block size, so
            // one is substituted here rather than dividing by zero: the
            // address it produces is never read in that case.
            elements_per_block = (block == 16'd0) ? 16'd1 : block;
            scale_index = ({16'b0, element_row} / {16'b0, rows_per_block}) *
                          ({16'b0, depth} / {16'b0, elements_per_block}) +
                          ({16'b0, element_column} / {16'b0, elements_per_block});
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 32'b0;
            saturation_count <= 32'b0;
            mac_count <= 32'b0;
            a_rd_en <= 1'b0;
            b_rd_en <= 1'b0;
            s_rd_en <= 1'b0;
            t_rd_en <= 1'b0;
            out_we <= 1'b0;
            a_rd_addr <= 32'b0;
            b_rd_addr <= 32'b0;
            s_rd_addr <= 32'b0;
            t_rd_addr <= 32'b0;
            out_addr <= 32'b0;
            out_data <= 32'b0;
            row <= 16'b0;
            col <= 16'b0;
            k <= 16'b0;
            acc <= 32'b0;
            value_a <= 32'b0;
            value_b <= 32'b0;
            product <= 32'b0;
            k_mod_a <= 16'b0; k_mod_b <= 16'b0;
            k_scale_a <= 32'b0; k_scale_b <= 32'b0;
            row_mod_a <= 16'b0; col_mod_b <= 16'b0;
            row_scale_a <= 32'b0; col_scale_b <= 32'b0;
            cpr_a <= 32'b0; cpr_b <= 32'b0; cpr_valid <= 1'b0;
            mul_valid <= 1'b0; add_valid <= 1'b0;
            mul_a_x <= 32'b0; mul_a_y <= 32'b0;
            mul_b_x <= 32'b0; mul_b_y <= 32'b0;
            add_x <= 32'b0; add_y <= 32'b0;
        end else begin
            done <= 1'b0;
            //: One cycle of valid_in per issue: the units latch on
            //: it and holding it would issue a second operation.
            mul_valid <= 1'b0;
            add_valid <= 1'b0;
            out_we <= 1'b0;
            a_rd_en <= 1'b0;
            b_rd_en <= 1'b0;
            s_rd_en <= 1'b0;
            t_rd_en <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 32'b0;
                        saturation_count <= 32'b0;
                        mac_count <= 32'b0;
                        row <= 16'b0;
                        col <= 16'b0;
                        k <= 16'b0;
                        acc <= 32'b0;
                        //: Every quotient counter restarts with the operation.
                        k_mod_a <= 16'b0; k_mod_b <= 16'b0;
                        k_scale_a <= 32'b0; k_scale_b <= 32'b0;
                        row_mod_a <= 16'b0; col_mod_b <= 16'b0;
                        row_scale_a <= 32'b0; col_scale_b <= 32'b0;
                        cpr_valid <= 1'b0;
                        if ((cfg_rows == 0) || (cfg_cols == 0) ||
                            (cfg_depth == 0)) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_ISSUE;
                        end
                    end
                end

                S_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= cfg_a_base +
                                 ({16'b0, row} * {16'b0, cfg_depth}) +
                                 {16'b0, k};
                    b_rd_en <= 1'b1;
                    b_rd_addr <= cfg_b_base +
                                 ({16'b0, col} * {16'b0, cfg_depth}) +
                                 {16'b0, k};
                    s_rd_en <= 1'b1;
                    s_rd_addr <= cfg_scale_a_base + row_scale_a + k_scale_a;
                    t_rd_en <= 1'b1;
                    t_rd_addr <= cfg_scale_b_base + col_scale_b + k_scale_b;
                    state <= S_WAIT;
                end

                S_WAIT: begin
                    state <= S_SCALE;
                end

                //: Every operand check stays HERE, ahead of the units, so a
                //: nonfinite operand or scale is refused before anything is issued
                //: and the refusal order is the one this lane always had.
                S_SCALE: begin
                    if (decoded_a[33:32] != 2'd0 || decoded_b[33:32] != 2'd0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if ((cfg_scale_a && decoded_scale_a[33:32] != 2'd0) ||
                                 (cfg_scale_b && decoded_scale_b[33:32] != 2'd0)) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else begin
                        //: Both scale multiplies on one valid_in, so they retire
                        //: together and the ERR_SCALE_RANGE test below sees both --
                        //: which is what the one-cycle form tested.
                        mul_a_x <= decoded_a[31:0]; mul_a_y <= decoded_scale_a[31:0];
                        mul_b_x <= decoded_b[31:0]; mul_b_y <= decoded_scale_b[31:0];
                        mul_valid <= 1'b1;
                        //: The unscaled operands are held, because a view that
                        //: declares no scale object takes them unchanged.
                        value_a <= decoded_a[31:0];
                        value_b <= decoded_b[31:0];
                        state <= S_SCALE_PIPE;
                    end
                end

                S_SCALE_PIPE: begin
                    if (mul_a_done && mul_b_done) begin
                        if ((cfg_scale_a && mul_a_err != 2'd0) ||
                            (cfg_scale_b && mul_b_err != 2'd0)) begin
                            error_code <= ERR_SCALE_RANGE;
                            state <= S_DONE;
                        end else begin
                            if (cfg_scale_a) value_a <= mul_a_out;
                            if (cfg_scale_b) value_b <= mul_b_out;
                            state <= S_MUL;
                        end
                    end
                end

                //: The product reuses the first multiplier: the scales and the
                //: product never happen in the same state.
                S_MUL: begin
                    mul_a_x <= value_a; mul_a_y <= value_b;
                    mul_b_x <= 32'b0;   mul_b_y <= 32'b0;
                    mul_valid <= 1'b1;
                    state <= S_MUL_PIPE;
                end

                S_MUL_PIPE: begin
                    if (mul_a_done) begin
                        if (mul_a_err != 2'd0) begin
                            error_code <= ERR_PRODUCT_RANGE;
                            state <= S_DONE;
                        end else begin
                            // Canonicalise exact zero before it reaches the
                            // accumulator, as the contract requires.
                            product <= (mul_a_out[30:0] == 31'b0)
                                       ? 32'b0 : mul_a_out;
                            state <= S_ACC;
                        end
                    end
                end

                S_ACC: begin
                    add_x <= acc; add_y <= product;
                    add_valid <= 1'b1;
                    state <= S_ACC_PIPE;
                end

                S_ACC_PIPE: begin
                    if (!add_done) begin
                        //: waiting; the adder is five stages deep
                    end else if (add_err != 2'd0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        acc <= add_out;
                        mac_count <= mac_count + 32'd1;
                        if (k + 16'd1 == cfg_depth) begin
                            state <= S_STORE;
                        end else begin
                            k <= k + 16'd1;
                            //: k / block, one advance per reduction index.
                            k_mod_a <= k_mod_a_next;
                            k_scale_a <= k_scale_a_next;
                            k_mod_b <= k_mod_b_next;
                            k_scale_b <= k_scale_b_next;
                            state <= S_ISSUE;
                        end
                    end
                end

                S_STORE: begin
                    if (narrowed[18:17] != 2'd0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base +
                                    ({16'b0, row} * {16'b0, cfg_cols}) +
                                    {16'b0, col};
                        out_data <= {16'b0, narrowed[15:0]};
                        out_count <= out_count + 32'd1;
                        if (narrowed[16])
                            saturation_count <= saturation_count + 32'd1;
                        acc <= 32'b0;
                        k <= 16'b0;
                        //: THE DEPTH'TH ADVANCE. The k loop performed depth-1 of
                        //: them, so this one carries k_scale to exactly
                        //: depth / block -- the stride a row or column wrap adds.
                        //: Latched once; the counters themselves restart for the
                        //: next output element.
                        if (!cpr_valid) begin
                            cpr_a <= k_scale_a_next;
                            cpr_b <= k_scale_b_next;
                            cpr_valid <= 1'b1;
                        end
                        k_mod_a <= 16'b0; k_scale_a <= 32'b0;
                        k_mod_b <= 16'b0; k_scale_b <= 32'b0;
                        if (col + 16'd1 == cfg_cols) begin
                            col <= 16'b0;
                            //: Side B indexes on the COLUMN, which restarts with
                            //: every row, so its counter restarts with it.
                            col_mod_b <= 16'b0;
                            col_scale_b <= 32'b0;
                            if (row + 16'd1 == cfg_rows) begin
                                state <= S_DONE;
                            end else begin
                                row <= row + 16'd1;
                                //: row / rows_per_block, adding the stride on the
                                //: wrap.
                                if (row_mod_a + 16'd1 == rows_per_block_a) begin
                                    row_mod_a <= 16'd0;
                                    row_scale_a <= row_scale_a + cpr_a_now;
                                end else begin
                                    row_mod_a <= row_mod_a + 16'd1;
                                end
                                state <= S_ISSUE;
                            end
                        end else begin
                            col <= col + 16'd1;
                            if (col_mod_b + 16'd1 == rows_per_block_b) begin
                                col_mod_b <= 16'd0;
                                col_scale_b <= col_scale_b + cpr_b_now;
                            end else begin
                                col_mod_b <= col_mod_b + 16'd1;
                            end
                            state <= S_ISSUE;
                        end
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
