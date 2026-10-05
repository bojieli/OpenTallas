`timescale 1ns/1ps
// ot_chip_v41x_karb_qh -- ot_chip_v41x_karb_qn with REGISTERED HEADS (W18, 1.2 GHz sign-off).
//
// Same contract as ot_chip_v41x_karb_qn: FIFO order, DEPTH entries, in_rdy = fewer than DEPTH held (a flop
// compare), a push into an empty queue is visible on the next cycle.  The queue's output comes from two
// head registers read round-robin (out_d = head[rp], rp a flop), backed by a DEPTH-entry qn.  A pop only
// clears its head's valid bit and flips rp; the freed head is refilled on the NEXT cycle (from the backing
// queue, or straight from the input when the backing queue is empty), so neither the head write enable nor
// the backing queue's read depends on the consumer's pop.  In the pipelined K slice / region the path
// "queue head -> arbitration -> pop -> 580-bit head reload" was the SS critical path at 0.833 ns.
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
    localparam integer CW = $clog2(DEPTH + 1);
    reg  [W-1:0] h0, h1;
    reg          v0, v1, rp, wp;          // head valid bits, head read / fill pointers
    reg  [CW-1:0] cnt;                    // entries held (heads + backing)
    wire         b_in_rdy, b_v;
    wire [W-1:0] b_d;
    wire pop  = out_v && out_rdy;
    wire push = in_v && in_rdy;
    wire slot_free = wp ? !v1 : !v0;      // the next head slot to fill is empty (flops only)
    wire from_b    = slot_free && b_v;
    wire from_in   = slot_free && !b_v && push;
    wire b_push    = push && !from_in;
    assign in_rdy = (cnt != CW'(DEPTH));
    assign out_v  = rp ? v1 : v0;
    assign out_d  = rp ? h1 : h0;
    ot_chip_v41x_karb_qn #(.W(W), .DEPTH(DEPTH)) u_b (
        .clk(clk), .rst_n(rst_n), .in_v(b_push), .in_rdy(b_in_rdy), .in_d(in_d),
        .out_v(b_v), .out_rdy(from_b), .out_d(b_d));
    wire fill = from_b || from_in;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v0 <= 1'b0; v1 <= 1'b0; rp <= 1'b0; wp <= 1'b0; cnt <= '0; end
        else begin
            if (fill) begin if (wp) v1 <= 1'b1; else v0 <= 1'b1; wp <= !wp; end
            if (pop)  begin if (rp) v1 <= 1'b0; else v0 <= 1'b0; rp <= !rp; end
            cnt <= cnt + CW'(push) - CW'(pop);
        end
    always @(posedge clk) if (fill) begin
        if (wp) h1 <= from_b ? b_d : in_d;
        else    h0 <= from_b ? b_d : in_d;
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && b_push && !b_in_rdy)
        $error("ot_chip_v41x_karb_qh: backing queue overflow");
`endif
endmodule
