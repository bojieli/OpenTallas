// q13 spec r5 leaf 2 (2026-10-13): the upper tree node of the W12 ROM tile as a hardened leaf: ot_qwen_me_node_w12 at the
// tile's parameters (W 16, one pin register stage on a / b / va, FP32 pair adders TREE_LAT 7 / ANR 1, y / vy registers).
// The leaf sits at the tile's W face so its a / b / va / y / vy pins ARE the tile's n_a / n_b / n_va / n_y / n_vy pins:
// pin -> flop and flop -> pin inside one short local clock tree.  Parameter-free top (as ot_qwen_tile_lsl).
// Data and valid are a pure re-hierarchy; the fault flag gets a pin register here (+1 cycle on the node's sticky-collected
// fault only).
module ot_qwen_tile_node (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  a,
    input  wire [511:0]  b,
    input  wire          va,
    output wire [511:0]  y,
    output wire          vy,
    output wire          fault
);
    wire f;
    ot_qwen_me_node_w12 #(.W(16), .WS(1), .TREE_LAT(7), .ANR(1)) u_n (.clk(clk), .rst_n(rst_n), .a(a), .b(b), .va(va),
        .y(y), .vy(vy), .fault(f));
    (* keep *) reg fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0; else fault_q <= f;
    assign fault = fault_q;
endmodule
