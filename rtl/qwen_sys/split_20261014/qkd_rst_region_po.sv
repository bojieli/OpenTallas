`timescale 1ns/1ps
// KV-BIND4 10-19: qkd_rst_region with a DEDICATED output launch register (b_pin).  The original drives the output pin b
// from the same flop the core reads back (`if (b) hold <= HOLD_LD`), so the pin net also carries internal loads: in the
// CLOSED qkd_rst_region_pr_h273 view (qkd_rst_region_pr_h273-h1-a11f46db5) the pin launch measured 223.8 ps TT > the
// 220 ps native budget (check_rst_pin_view FAIL -> HOLD128 bound, health reset contract UNPROVEN).  Here the core keeps
// its own b_int for feedback and a KEPT twin b_pin with byte-identical next-state logic drives only the pin
// (register duplication, 0 cycles: b_pin == b_int on every edge).  Body otherwise = qkd_rst_region (sized counters).
// MUT 5 (bench negative control): b_pin is registered FROM b_int (one extra edge) -> calendar mismatch.
module qkd_rst_region_po #(parameter integer IGNORE=255, parameter integer HOLD=128, parameter integer MUT=0,
                        parameter integer DW=8) (
  input  wire          ck,
  input  wire          por_n,
  input  wire          a,          // the relayed host reset level (die name a / b as a relay stage)
  input  wire [DW-1:0] dly,
  output wire          b);
  localparam integer IW = ($clog2(IGNORE + 1) > 9) ? $clog2(IGNORE + 1) : 9;
  localparam integer HW = ($clog2(HOLD) > 8) ? $clog2(HOLD) : 8;
  localparam [HW-1:0] HOLD_LD = (MUT == 4) ? HW'(HOLD[7:0] - 8'd1) : HW'(HOLD - 1);
  localparam [IW-1:0] IGN_TC  = IW'(IGNORE);
  generate if (HOLD < 1 || IGNORE < 0 || IGNORE >= (1 << IW) || HOLD > (1 << HW) || DW < 8) begin : g_bad
    initial $fatal(1, "qkd_rst_region: HOLD %0d IGNORE %0d DW %0d not representable", HOLD, IGNORE, DW);
  end endgenerate
  reg [1:0] ps;
  always @(posedge ck or negedge por_n) if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
  wire pr_n = ps[1];
  reg b_int; (* keep *) reg b_pin;
  assign b = b_pin;
  reg [IW-1:0] ign; reg a_q; reg [DW-1:0] cnt; reg rel; reg [HW-1:0] hold;
  wire live = (MUT == 1) ? 1'b1 : (MUT == 4 ? (32'(ign[8:0]) >= 32'(IGNORE)) : (ign >= IGN_TC));
  always @(posedge ck or negedge pr_n) begin
    if (!pr_n) begin ign <= 0; a_q <= 1'b0; cnt <= 0; rel <= 1'b0; hold <= 0; b_int <= 1'b0; b_pin <= 1'b0; end
    else begin
      if (!live) ign <= ign + 1'b1;
      a_q <= live ? a : 1'b0;
      if (hold != 0) hold <= hold - 1'b1;
      if (!a_q) begin                                   // asserted (or not yet live): low, restart the calendar
        if (b_int) hold <= HOLD_LD;
        b_int <= 1'b0; if (MUT != 5) b_pin <= 1'b0; rel <= 1'b0; cnt <= 0;
      end else if (!rel) begin
        if (cnt == ((MUT == 2) ? {DW{1'b0}} : dly) && hold == 0) begin b_int <= 1'b1; if (MUT != 5) b_pin <= 1'b1; rel <= 1'b1; end
        else if (cnt != dly) cnt <= cnt + 1'b1;
      end
      if (MUT == 5) b_pin <= b_int;
    end
  end
endmodule
