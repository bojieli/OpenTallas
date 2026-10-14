// Pin-registered HC lane (stream safe-hbm, 2026-10-08; REVIEW_20261008 row C1, approved design S-C1).
// hfd_hc failed TT on the broadcast chain -> lane macro input pins (bc_0_10 -> u_lane_87: 30 buffers into the lane's
// multiplier front logic; the lane view's outcheck lists 121 inputs that are not register-direct).  This wrapper puts
// one flop at every lane input pin (no logic between the pin and the flop) in front of the unchanged
// ot_dsrom_su_hcpost_lane, so the quarter -> lane path is a pure reg -> pin-flop wire.  rst_n passes a flop too (the
// quarter drives it from a broadcast register).  Outputs are the core's registers.  Cost: +1 cycle on every lane input
// (all inputs move together: the lane is a pure pipeline, so outputs are the core's outputs one cycle later).
// MUTANT 1 (bench negative): c3 bypasses its pin flop (one operand a cycle early).
module ot_dsrom_su_hcpost_lane_pr #(
    parameter integer ML = 5,
    parameter integer AL = 4,
    parameter integer MUTANT = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] r0, r1, r2, r3, y,
    input  wire [31:0] c0, c1, c2, c3, p,
    output wire        vo,
    output wire [31:0] o,
    output wire        fault
);
    reg        rst_q, v_q;
    reg [31:0] r0_q, r1_q, r2_q, r3_q, y_q, c0_q, c1_q, c2_q, c3_q, p_q;
    always @(posedge clk) begin
        rst_q <= rst_n; v_q <= v;
        r0_q <= r0; r1_q <= r1; r2_q <= r2; r3_q <= r3; y_q <= y;
        c0_q <= c0; c1_q <= c1; c2_q <= c2; c3_q <= c3; p_q <= p;
    end
    wire [31:0] c3_in = (MUTANT == 1) ? c3 : c3_q;
    ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u_core (.clk(clk), .rst_n(rst_q), .v(v_q), .r0(r0_q), .r1(r1_q),
        .r2(r2_q), .r3(r3_q), .y(y_q), .c0(c0_q), .c1(c1_q), .c2(c2_q), .c3(c3_in), .p(p_q), .vo(vo), .o(o), .fault(fault));
endmodule
