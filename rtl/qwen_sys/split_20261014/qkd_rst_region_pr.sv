`timescale 1ns/1ps
// Opt-in regional reset root for a physically constant delay strap. Capture
// every strap bit at the pin; the original core and its release calendar stay
// unchanged. The strap is stable before POR release and throughout operation.
// IGNORE startup clocks ensure capture completes before the core uses it.
// KV-RETIRE 10-19: DW (default 8 = unchanged) widens the strap with the core's calendar counter.
module qkd_rst_region_pr #(parameter integer IGNORE=255, parameter integer HOLD=128,
                           parameter integer MUT=0, parameter integer DW=8) (
  input wire ck, por_n, a,
  input wire [DW-1:0] dly,
  output wire b
);
  (* keep *) reg [DW-1:0] dly_pin;
  always @(posedge ck) dly_pin <= (MUT == 3) ? (dly ^ {{(DW-1){1'b0}}, 1'b1}) : dly;
  qkd_rst_region #(.IGNORE(IGNORE), .HOLD(HOLD), .MUT(MUT < 3 ? MUT : 0), .DW(DW)) u_core (
    .ck(ck), .por_n(por_n), .a(a), .dly(dly_pin), .b(b)
  );
endmodule
