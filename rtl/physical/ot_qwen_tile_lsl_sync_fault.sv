// MODE3 LSL physical successor proposal. Not selected by any release bind/spec.
// Input reset is a synchronous wavefront signal. The kept landing adds one boot edge.
// Data body/parameters and data edges are unchanged after the explicit boot guard.
// Fault outputs register locally (+1 fault edge), permitting real registered face pins.
module ot_qwen_tile_lsl_sync_fault (
    input wire clk, rst_n, v_d, first_d,
    input wire [3:0] split_d,
    input wire [255:0] w_d,
    input wire [127:0] x_d,
    output wire [63:0] t_out,
    output reg [7:0] lfault,
    output reg tfault
);
    (* keep = "true", dont_touch = "true" *) reg rs_q;
    always @(posedge clk) rs_q <= rst_n;
    wire [7:0] lf_raw;
    wire tf_raw;
    ot_qwen_w12_lane_slice #(.G(4), .NPL(2), .IL(8), .MUL_LAT(8), .ACC_LAT(7), .TREE_LAT(7), .LRST(3), .ANR(1), .TMUT(0)) u_ls (
        .clk(clk), .rst_n(rs_q), .v_d(v_d), .first_d(first_d), .split_d(split_d), .w_d(w_d), .x_d(x_d),
        .t_out(t_out), .lfault(lf_raw), .tfault(tf_raw));
    always @(posedge clk)
        if (!rs_q) begin lfault <= 0; tfault <= 0; end
        else begin lfault <= lf_raw; tfault <= tf_raw; end
endmodule
