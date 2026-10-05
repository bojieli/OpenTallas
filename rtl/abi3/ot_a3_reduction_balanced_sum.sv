`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The canonical NUM-6.1 balanced tree over a power-of-two lane block.
//
// ATTENTION.SPARSE's softmax denominator is this sum and no other. Its reference
// (``runtime/tensor_accelerator/sparse_attention.py::_balanced_sum``) folds the
// trailing axis in place, halving it each level:
//
//     while width > 1:
//         level = level.reshape(..., width // 2, 2)
//         level = np.add(level[..., 0], level[..., 1])
//         width //= 2
//
// so lane pairs (0,1), (2,3), ... meet at level 0, their sums pair at level 1,
// and six levels reduce the frozen 64-lane source block. EVERY ADDITION IS ONE
// BINARY32 RNE ROUNDING and the ASSOCIATION IS PART OF THE CONTRACT: a
// left-to-right fold of the same 64 values is a different number, which is why
// ot_a3_reduction_ordered_sum refuses PAIRWISE_TREE rather than approximating it
// and why this is a separate block instead of a mode of that one.
//
// A SHORT FINAL BLOCK IS THE CALLER'S ZERO PAD, not this block's problem. The
// reference zero-extends to the full width before summing and says why that is
// exact: adding +0 to a nonnegative binary32 partial leaves it alone. This block
// therefore always folds LANES values and the caller supplies +0 where a lane is
// padding -- which also means a caller that supplies -0 instead gets a different
// answer at the one place binary32 addition notices, so it must not.
//
// ONE ADDER, NOT LANES-1 OF THEM. A 64-lane spatial tree is 63 instances of
// ot_fp32_add_rne_pipe; the sum is needed once per (row, head) per source block,
// not once per cycle, so the tree is walked sequentially through a single adder
// instead. That is LANES-1 adds at the adder's own latency -- 63 x 6 = 378
// cycles at LANES=64 -- against 63 adders' worth of area, and the association is
// identical either way. A caller that needs the throughput can raise ADDERS;
// a caller that needs the area cannot get it back from a spatial tree.
// ---------------------------------------------------------------------------
module ot_a3_reduction_balanced_sum #(
    //: Power of two. The shipped sparse-attention source block is 64.
    parameter integer LANES = 64
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    //: Lane values, little-lane-first, already zero-padded by the caller.
    input  wire [LANES*32-1:0] lanes,

    output reg         busy,
    output reg         done,
    output reg  [31:0] total,
    output reg  [1:0]  error_code,
    output reg  [31:0] add_count
);
    localparam integer LEVELS = $clog2(LANES);

    localparam [1:0] E_NONE = 2'd0;

    integer i;

    //: The working rank. Level l holds LANES >> l live values in [0, width).
    reg [31:0] node [0:LANES-1];
    reg [31:0] width;
    reg [31:0] pair;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_ISSUE = 3'd1;
    localparam [2:0] S_WAIT  = 3'd2;
    localparam [2:0] S_LEVEL = 3'd3;
    localparam [2:0] S_DONE  = 3'd4;
    reg [2:0] state;

    reg         add_valid_in;
    reg  [31:0] add_a, add_b;
    wire [31:0] add_y;
    wire [1:0]  add_err;
    wire        add_valid_out;

    ot_fp32_add_rne_pipe fold (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid_in),
        .a(add_a), .b(add_b),
        .y(add_y), .err(add_err), .valid_out(add_valid_out)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            width <= 32'd0; pair <= 32'd0;
            busy <= 1'b0; done <= 1'b0;
            total <= 32'd0; error_code <= E_NONE; add_count <= 32'd0;
            add_valid_in <= 1'b0; add_a <= 32'd0; add_b <= 32'd0;
            for (i = 0; i < LANES; i = i + 1) node[i] <= 32'd0;
        end else begin
            add_valid_in <= 1'b0;
            done <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        for (i = 0; i < LANES; i = i + 1)
                            node[i] <= lanes[i*32 +: 32];
                        width <= LANES[31:0];
                        pair <= 32'd0;
                        add_count <= 32'd0;
                        error_code <= E_NONE;
                        busy <= 1'b1;
                        state <= S_ISSUE;
                    end
                end

                //: Pair ``pair`` of this level: lanes 2*pair and 2*pair+1.
                S_ISSUE: begin
                    add_valid_in <= 1'b1;
                    add_a <= node[(pair * 32'd2) % LANES];
                    add_b <= node[(pair * 32'd2 + 32'd1) % LANES];
                    state <= S_WAIT;
                end

                S_WAIT: begin
                    if (add_valid_out) begin
                        //: In place, at the pair's own index -- which is exactly
                        //: what the reference's reshape-and-add does.
                        node[pair % LANES] <= add_y;
                        add_count <= add_count + 32'd1;
                        if (add_err != 2'd0 && error_code == E_NONE)
                            error_code <= add_err;
                        if (pair + 32'd1 >= (width >> 1)) begin
                            pair <= 32'd0;
                            state <= S_LEVEL;
                        end else begin
                            pair <= pair + 32'd1;
                            state <= S_ISSUE;
                        end
                    end
                end

                S_LEVEL: begin
                    width <= width >> 1;
                    if ((width >> 1) <= 32'd1) begin
                        total <= node[0];
                        busy <= 1'b0; done <= 1'b1;
                        state <= S_DONE;
                    end else begin
                        state <= S_ISSUE;
                    end
                end

                S_DONE: state <= S_IDLE;
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
