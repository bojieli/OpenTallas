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
//
// KV-RETIRE 10-19 (owner 09:39 "HOLD128 is no proof for 180-edge paths"; codex/kv-fault-reset-1019 4b2f0b411 proposed a
// 273-edge sink depth that the 8-bit hold counter WRAPS: HOLD=273 loaded HOLD[7:0]-1 = 16).  Counter widths are now sized
// from the parameters at elaboration, never truncated:
//   IW = max(9, clog2(IGNORE+1))  ign counts 0..IGNORE (an IGNORE > 511 with the old 9 bits never went live)
//   HW = max(8, clog2(HOLD))      hold loads HOLD-1 exactly (HOLD >= 1)
//   DW (parameter, default 8)     strap / calendar counter width, so dly >= 256 can be strapped (D - d_r of a 273 tree)
// With the default parameters (IGNORE 255, HOLD 128, DW 8) every width and value is bit-identical to the original.
// MUT 4 (bench negative control): the legacy truncation -- hold loads HOLD[7:0]-1, ign compares in 9 bits.
module qkd_rst_region #(parameter integer IGNORE=255, parameter integer HOLD=128, parameter integer MUT=0,
                        parameter integer DW=8) (
  input  wire          ck,
  input  wire          por_n,
  input  wire          a,          // the relayed host reset level (die name a / b as a relay stage)
  input  wire [DW-1:0] dly,
  output reg           b);
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
  reg [IW-1:0] ign; reg a_q; reg [DW-1:0] cnt; reg rel; reg [HW-1:0] hold;
  wire live = (MUT == 1) ? 1'b1 : (MUT == 4 ? (32'(ign[8:0]) >= 32'(IGNORE)) : (ign >= IGN_TC));
  always @(posedge ck or negedge pr_n) begin
    if (!pr_n) begin ign <= 0; a_q <= 1'b0; cnt <= 0; rel <= 1'b0; hold <= 0; b <= 1'b0; end
    else begin
      if (!live) ign <= ign + 1'b1;
      a_q <= live ? a : 1'b0;
      if (hold != 0) hold <= hold - 1'b1;
      if (!a_q) begin                                   // asserted (or not yet live): low, restart the calendar
        if (b) hold <= HOLD_LD;
        b <= 1'b0; rel <= 1'b0; cnt <= 0;
      end else if (!rel) begin
        if (cnt == ((MUT == 2) ? {DW{1'b0}} : dly) && hold == 0) begin b <= 1'b1; rel <= 1'b1; end
        else if (cnt != dly) cnt <= cnt + 1'b1;
      end
    end
  end
endmodule
