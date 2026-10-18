`timescale 1ns/1ps
// Opt-in regional reset root for a physically constant delay strap. Capture
// every strap bit at the pin; the original core and its release calendar stay
// unchanged. The strap is stable before POR release and throughout operation.
// IGNORE startup clocks ensure capture completes before the core uses it.
module qkd_rst_region_pr #(parameter integer IGNORE=255, parameter integer HOLD=128,
                           parameter integer MUT=0) (
  input wire ck, por_n, a,
  input wire [7:0] dly,
  output wire b
);
  (* keep *) reg [7:0] dly_pin;
  always @(posedge ck) dly_pin <= (MUT == 3) ? (dly ^ 8'd1) : dly;
  qkd_rst_region #(.IGNORE(IGNORE), .HOLD(HOLD), .MUT(MUT < 3 ? MUT : 0)) u_core (
    .ck(ck), .por_n(por_n), .a(a), .dly(dly_pin), .b(b)
  );
endmodule
