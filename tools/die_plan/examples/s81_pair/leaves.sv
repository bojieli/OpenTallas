`timescale 1ns/1ps
`default_nettype none
// Abutment-proof leaves (TOPDOWN-PLAN step 4): two S81-frame-sized partitions, fa (west) and fb (east).
// fa: din (die IO, 64) + r (70, from fb) -> x (276 = the S81 frame x bundle width) to fb.
// fb: x (276) + z (64, die IO through fa's ft slot fz) -> r (70) back to fa, dout (64, die IO).
module s81p_a_core (input wire clk, input wire [63:0] din, input wire [69:0] r, output reg [275:0] x);
    always @(posedge clk) x <= {din[19:0], din, din ^ r[63:0], din + {58'd0, r[69:64]}, din ^ {din[31:0], din[63:32]}};
endmodule
module s81p_b_core (input wire clk, input wire [275:0] x, input wire [63:0] z, input wire x_ep,
                    output reg [69:0] r, output reg [63:0] dout);
    always @(posedge clk) begin
        r    <= x[69:0] ^ x[275:206];
        dout <= x_ep ? (x[63:0] + x[127:64] + z) : 64'd0;
    end
endmodule
`default_nettype wire
