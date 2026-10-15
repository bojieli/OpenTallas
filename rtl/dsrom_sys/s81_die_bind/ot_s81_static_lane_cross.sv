`timescale 1ns/1ps
`default_nettype none
// Equal-frequency, epoch-related clock crossing. The compiler delivers the two
// reset releases on corresponding clock epochs: first active source edge 0 and
// first active destination edge 0. Neither side may pause its clock. Phase is
// EPOCH_SHIFT states the fixed source epoch number of destination edge zero.
// It is a compile-time constant, never trained or changed from traffic. Phase is
// fixed by die clock delivery; OFFSET>=2 leaves at least a full period to capture.
// Every source edge writes a slot, including bubbles. Every destination edge
// consumes its assigned slot after OFFSET epochs. No occupancy/ready/credit state.
// A slot's epoch identity is an assertion only: a fault never changes the calendar.
// Output edge j is source edge j-OFFSET+EPOCH_SHIFT, once j>=OFFSET. A reset epoch slip is a
// fault; the compiler must restart the schedule, never silently re-align traffic.
module ot_s81_static_lane_cross #(
    parameter integer W=1101, DEPTH=8, OFFSET=4, EPOCH_SHIFT=0,
    parameter integer AW=$clog2(DEPTH)
)(
    input wire w_ck, w_rst_n,
    input wire [W-1:0] i,
    input wire r_ck, r_rst_n,
    output reg [W-1:0] o,
    output reg fault
);
    reg [W-1:0] bank [0:DEPTH-1];
    reg [AW:0] identity [0:DEPTH-1];
    reg [AW:0] wc, rc;
    reg [AW:0] warm;
    // Observe the source epoch through a Gray synchronizer. This checks the
    // specified epoch relationship; it never places or changes either pointer.
    wire [AW:0] wg=wc^(wc>>1);
    (* async_reg="true" *) reg [AW:0] wg1,wg2,wg3;
    wire [AW:0] epoch_expected=rc-2+EPOCH_SHIFT;
    wire [AW:0] epoch_gray=epoch_expected^(epoch_expected>>1);
    always @(posedge r_ck) begin wg1<=wg; wg2<=wg1; wg3<=wg2; end
`ifdef OT_S81_STATIC_CROSS_MUT_OFFSET
    wire [AW:0] expected = rc-OFFSET+EPOCH_SHIFT-1;
`else
    wire [AW:0] expected = rc-OFFSET+EPOCH_SHIFT;
`endif
    always @(posedge w_ck or negedge w_rst_n)
        if (!w_rst_n) wc <= 0;
        else begin
            bank[wc[AW-1:0]] <= i;
            identity[wc[AW-1:0]] <= wc;
            wc <= wc+1'b1;
        end
    always @(posedge r_ck or negedge r_rst_n)
        if (!r_rst_n) begin rc<=0; warm<=0; o<=0; fault<=0; end
        else begin
            rc <= rc+1'b1;
            if (warm < OFFSET) begin warm<=warm+1'b1; o<=0; end
            else begin
                o <= bank[expected[AW-1:0]];
                if (identity[expected[AW-1:0]] != expected || wg3 != epoch_gray) fault<=1;
            end
        end
`ifndef SYNTHESIS
    initial if (W<1 || DEPTH<4 || (DEPTH & (DEPTH-1))!=0 || OFFSET<2 || OFFSET>DEPTH-2)
        $fatal(1,"static crossing requires power-of-two depth and 2 <= offset <= depth-2");
`endif
endmodule
`default_nettype wire
