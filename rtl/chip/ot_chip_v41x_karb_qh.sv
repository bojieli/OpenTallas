`timescale 1ns/1ps
// ot_chip_v41x_karb_qh -- ot_chip_v41x_karb_qn with a REGISTERED HEAD (W18, 1.2 GHz sign-off).
//
// Same FIFO order and DEPTH as ot_chip_v41x_karb_qn (in_rdy = not full, a push into an empty queue is visible
// on the next cycle; a push that meets the pop of the last entry is visible one cycle later than in qn),
// but out_v / out_d come straight from flops: the head entry
// lives in its own register, backed by a (DEPTH-1)-entry ot_chip_v41x_karb_qn.  In the pipelined K slice the
// read-pointer head mux of the 4-deep K queue (rp -> 580-bit mux -> k_we -> write-fence -> grant -> the 8-bit
// write-outstanding counters) was the SS critical path at 0.833 ns (-58 ps); with the head registered the
// arbitration starts from a flop.
module ot_chip_v41x_karb_qh #(
    parameter integer W     = 8,
    parameter integer DEPTH = 4          // >= 2
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_v,
    output wire         in_rdy,
    input  wire [W-1:0] in_d,
    output wire         out_v,
    input  wire         out_rdy,
    output wire [W-1:0] out_d
);
    reg          hv;
    reg  [W-1:0] hd;
    wire         b_in_rdy, b_v;
    wire [W-1:0] b_d;
    wire pop  = hv && out_rdy;
    wire push = in_v && in_rdy;
    // the head is (re)loaded when it is empty or popped: from the backing queue if it holds anything, else
    // straight from the input
    wire load     = !hv || pop;
    wire from_b   = load && b_v;
    // an input goes straight to the head only when the head is EMPTY (never on a same-cycle pop), so the
    // backing queue's write enable does not depend on the consumer's pop (the SS critical path in pregion);
    // a push that meets the pop of the last entry lands in the backing queue and reaches the head one cycle
    // later than in ot_chip_v41x_karb_qn (order and capacity unchanged)
    wire from_in  = !hv && !b_v && push;
    wire b_push   = push && !from_in;
    assign in_rdy = !(hv && !b_in_rdy);            // DEPTH entries: the head + DEPTH-1 behind it
    assign out_v  = hv;
    assign out_d  = hd;
    ot_chip_v41x_karb_qn #(.W(W), .DEPTH(DEPTH - 1)) u_b (
        .clk(clk), .rst_n(rst_n), .in_v(b_push), .in_rdy(b_in_rdy), .in_d(in_d),
        .out_v(b_v), .out_rdy(from_b), .out_d(b_d));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) hv <= 1'b0;
        else if (load) hv <= b_v || from_in;
    always @(posedge clk)
        if (from_b) hd <= b_d;
        else if (from_in) hd <= in_d;
endmodule
