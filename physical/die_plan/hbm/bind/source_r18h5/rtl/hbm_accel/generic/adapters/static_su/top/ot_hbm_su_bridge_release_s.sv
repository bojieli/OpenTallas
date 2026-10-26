`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_su_bridge_release_s (RBH-SFUS 10-18): single-clock (SERIAL) form of ot_hbm_su_bridge_release for the hard
// leaf subr_<q>.  Same contract (tools/hbm_static/su_multirate_top_contract.json): bridge_rst_n must deassert after the
// last stream edge before the common edge E0 (E0-3q) and before E0, so every bridge phase counter sees E0 first.
// Why (routed r1-cd685d69e of the two-clock form: NEEDS_RTL, FF hold -71.6 ps on b_s(serial) -> s1(stream)): on the
// 3:4 lattice a serial->stream flop pair always has a 0-ps (common-edge) hold relation and a 1q (278 ps) setup relation,
// which the tile's distinct-entry reserve (setup 150 / hold 100 ps) cannot both meet; a stream negedge capture gives
// 0.5q (139 ps) on both and fails setup (gate r2 probe: -83 ps).  Here every flop is on clk_serial, so the tile has no
// internal crossing; the release is taken from a serial NEGEDGE flop at E0-2q:
//   serial posedge E0-12q  b_s  <= prog_busy   (pin register; busy rises after the start sample E0-16q)
//   serial posedge E0-8q   s1   <= b_s
//   serial posedge E0-4q   s2   <= s1; rise = s1 && !s2 (pre-edge) -> arm (sticky)
//   serial NEGEDGE E0-2q   bridge_rst_n <= arm  -- inside [E0-3q, E0): recovery 2q to E0 (both domains), removal 1q
//                          to the stream edge E0-3q and 2q to the serial edge E0-4q.
//   Release = start sample S + 14q (was S + 13q; same window, same first edge E0 for both bridge domains).
// Later programme starts must keep the epoch: a later rise must arm at a serial edge whose phase (0 at E0, mod 3
// serial edges) equals the first one's (2); otherwise FAULT (sticky).  No ready, credit or stall.
// Pins: prog_busy -> b_s (pin flop); bridge_rst_n (negedge flop) and fault are register outputs; rst_n async clears.
// MUT (bench only): 1 = release one serial period early (negedge E0-6q), 2 = one serial period late (negedge E0+2q).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_bridge_release_s #(parameter integer MUT=0)(
 input wire clk_serial,           // serial (900 MHz) root: the SU programme / pgp_<q> clock
 input wire rst_n,                // serial-domain power-on release
 input wire prog_busy,            // pgp_<q>.busy (serial)
 output reg bridge_rst_n,         // to ot_hbm_su_static_pgslice.bridge_rst_n / sucx_<q>.rst_n (async active-low)
 output reg fault
);
 reg b_s,s1,s2,s3,arm,released;
 reg [1:0] ph;                     // pre-edge value at serial edge E0+4q*m is m mod 3
 localparam [1:0] START_PH=2'd2;   // a rise arms at E0'-4q: m = -1 = 2 mod 3
 wire rise=s1&&!s2;
 wire go=(MUT==1)?(b_s&&!s1):(MUT==2)?(s2&&!s3):rise;
 always @(posedge clk_serial or negedge rst_n)
  if(!rst_n)begin
   b_s<=1'b0;s1<=1'b0;s2<=1'b0;s3<=1'b0;arm<=1'b0;released<=1'b0;ph<=2'd0;fault<=1'b0;
  end else begin
   b_s<=prog_busy; s1<=b_s; s2<=s1; s3<=s2;
   if(!released)begin
    if(go)begin released<=1'b1; arm<=1'b1; ph<=2'd0; end
   end else begin
    ph<=(ph==2'd2)?2'd0:ph+2'd1;
    if(rise && ph!=START_PH) fault<=1'b1;
   end
  end
 always @(negedge clk_serial or negedge rst_n)
  if(!rst_n) bridge_rst_n<=1'b0; else bridge_rst_n<=arm;
endmodule
`default_nettype wire
