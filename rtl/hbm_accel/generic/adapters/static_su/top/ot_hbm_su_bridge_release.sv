`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SU multirate bridge epoch release (H-NETLIST 2026-10-15). One per quadrant (SW/SE/NW/NE), driving bridge_rst_n of the
// four port-group slices of that SU quarter (ot_hbm_su_static_pgslice MULTIRATE=1 -> ot_hbm_su_multirate_bridge).
//
// Contract (tools/hbm_static/su_multirate_top_contract.json, tb_hbm_su_native_multirate_top.sv): serial 900 MHz and
// stream 1200 MHz share one 2500/9 ps quantum lattice; a common epoch is 12 quanta = 3 serial = 4 stream edges. The
// serial SU programme (ot_hbm_su_programme) samples start at serial edge E0-4 (4 serial edges before common edge E0;
// its first command is consumed at E0) and bridge_rst_n must be released AFTER the last stream edge before E0 and
// BEFORE E0, so every bridge phase counter (serial and stream) sees E0 as its first edge.
//
// Function (quantum q = 2500/9 ps; E0 = common edge; programme start sampled at serial edge E0-16q):
//   serial  b_s  <= prog_busy                      busy rises after E0-16q, captured at serial edge E0-12q (a COMMON
//                                                  epoch edge: the launch is phase-aligned with the stream lattice)
//   stream  s1   <= b_s                            first stream edge after the common launch: E0-9q (one full stream
//                                                  period after the launch edge; single toggle, compiler-fixed)
//   stream  s2   <= s1                             E0-6q
//   stream  bridge_rst_n <= 1 on s2 && !s3          E0-3q: deasserts at the last stream edge before E0
//   so both domains' first edge after release is E0 (serial recovery 3q = 833 ps; stream one full period).
// The release is sticky (until rst_n): the bridge phase counters run free afterwards, so every later programme start
// must also be epoch-aligned. That is checked here: every later busy rise must reach s2 when the stream phase counter
// (0 at E0, mod 4) equals the phase of the first release edge; otherwise FAULT (sticky). No ready, credit or stall:
// the fault never moves the release or any programme edge.
// Pins: prog_busy is registered at its pin (b_s); bridge_rst_n and fault are register outputs.
// Fixed latency: start sample S -> release = S + 13q (serial S+1 capture, stream +3 edges), always before E0 = S + 16q.
// MUT (bench only): 1 = release one stream edge early (rel <= s1), 2 = release one stream edge late (extra stage).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_bridge_release #(parameter integer MUT=0)(
 input wire clk_serial,           // serial (900 MHz) root: same domain as the SU programme / slice clk_ctl
 input wire clk_stream,           // stream (1200 MHz) root: same domain as the slice pg_clk
 input wire rst_n,                // serial-domain power-on release
 input wire rst_stream_n,         // stream-domain power-on release
 input wire prog_busy,            // ot_hbm_su_programme.busy (serial)
 output reg bridge_rst_n,         // to ot_hbm_su_static_pgslice.bridge_rst_n (async active-low bridge reset)
 output reg fault
);
 reg b_s;
 always @(posedge clk_serial or negedge rst_n) if(!rst_n) b_s<=1'b0; else b_s<=prog_busy;
 reg s1,s2,s3,s4,released;
 reg [1:0] ph;                        // pre-edge value at stream edge E0+3q*m is m mod 4 (0 at E0)
 localparam [1:0] START_PH=2'd3;      // a busy rise reaches s2 (s2 && !s3) at E0'-3q: m = -1 = 3 mod 4
 wire rise=s2&&!s3;
 wire go=(MUT==1)?(s1&&!s2):(MUT==2)?(s3&&!s4):rise;
 always @(posedge clk_stream or negedge rst_stream_n)
  if(!rst_stream_n)begin
   s1<=1'b0;s2<=1'b0;s3<=1'b0;s4<=1'b0;released<=1'b0;ph<=2'd0;bridge_rst_n<=1'b0;fault<=1'b0;
  end else begin
   s1<=b_s; s2<=s1; s3<=s2; s4<=s3;
   if(!released)begin
    if(go)begin released<=1'b1; bridge_rst_n<=1'b1; ph<=2'd0; end
   end else begin
    ph<=ph+2'd1;
    if(rise && ph!=START_PH) fault<=1'b1;   // a later programme start must keep the first start's epoch phase
   end
  end
endmodule
`default_nettype wire
