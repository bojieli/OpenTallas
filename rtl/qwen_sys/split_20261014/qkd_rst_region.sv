`timescale 1ns/1ps
// kvsys v1.4.3 regional reset root (Q-KVSYS-DIE 2026-10-15, coordinator: "regional roots with local synchronisers and a
// static reset-release calendar per region, so no single relay chain spans the die").
//
// The HOST's active-low reset level (die_rst_n / hbm_rst_n / host_rst_n / link_rst_n) reaches each die region over a
// registered relay chain of depth d_r (relays carry no reset, so the chain output is UNDEFINED until it has flushed).
// This root drives the region's own local relay tree (depth L_r < RELAY_FLUSH):
//   * power-on: the package POR (por_n, async assert, two-flop synchronised release) holds rst_o LOW, independent of the
//     chain, so the region is in reset from the first core clock (the local tree flushes within L_r cycles);
//   * the chain input is IGNORED for IGNORE core cycles after POR release (>= every chain depth d_r: the generator checks
//     d_r <= IGNORE), so an unflushed relay value can never release the region;
//   * release calendar: a rising rst_i (the host released) releases rst_o exactly dly + 1 cycles later; the generator
//     straps dly = D - d_r (D = the largest chain depth of this reset root), so every region of one root releases on the
//     same core cycle (host release + D + 2) and each load L_r cycles after that (recorded per load);
//   * a falling rst_i (host re-assert) drops rst_o on the next edge; rst_o then stays low for at least HOLD cycles so the
//     local relays flush the asserted level before any later release.
// Static schedule: no ready / credit; dly is a die strap (tie cells).
module qkd_rst_region #(parameter integer IGNORE=255, parameter integer HOLD=128, parameter integer MUT=0) (
  input  wire       ck,
  input  wire       por_n,
  input  wire       a,          // the relayed host reset level (die name a / b as a relay stage)
  input  wire [7:0] dly,
  output reg        b);
  reg [1:0] ps;
  always @(posedge ck or negedge por_n) if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
  wire pr_n = ps[1];
  reg [8:0] ign; reg a_q; reg [7:0] cnt; reg rel; reg [7:0] hold;
  wire live = (MUT == 1) ? 1'b1 : (ign >= IGNORE);
  always @(posedge ck or negedge pr_n) begin
    if (!pr_n) begin ign <= 0; a_q <= 1'b0; cnt <= 0; rel <= 1'b0; hold <= 0; b <= 1'b0; end
    else begin
      if (!live) ign <= ign + 9'd1;
      a_q <= live ? a : 1'b0;
      if (hold != 0) hold <= hold - 8'd1;
      if (!a_q) begin                                   // asserted (or not yet live): low, restart the calendar
        if (b) hold <= HOLD[7:0] - 8'd1;
        b <= 1'b0; rel <= 1'b0; cnt <= 0;
      end else if (!rel) begin
        if (cnt == ((MUT == 2) ? 8'd0 : dly) && hold == 0) begin b <= 1'b1; rel <= 1'b1; end
        else if (cnt != dly) cnt <= cnt + 8'd1;
      end
    end
  end
endmodule
