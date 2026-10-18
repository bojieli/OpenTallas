`timescale 1ns/1ps
`default_nettype none
// SU-level LG pair tap leaf with its own stream-domain reset synchroniser (HBM-SU3 2026-10-17; coordinator 0dg+3:
// "pgslice_lg tap reset needs a real synchroniser"). The hardened child of ot_hbm_su_static_pgslice_lg that sits beside
// the slice's two VM bank leaves on pg_clk: unchanged ot_hbm_vm_lg_pair_tap (SU level, READ_RETURN/WRITE_RETURN 10/7
// as parameters, no rret/wret straps) + a 1-bit serial->stream reset synchroniser.
// Reset: rst_n is the slice's SERIAL power-on reset (die por_serial). r8b pgslice_lg sampled it with ONE pg_clk flop
// (metastable stage consumed as the taps' asynchronous clear). Now: g_rsync.rc (clk_ctl, serial source flop) ->
// g_rsync.rs[0] -> g_rsync.rs[1] (pg_clk), rs[1] = the taps' reset. Stage 1 (rs[0]) drives only stage 2. Admitted by the
// reviewed ref_tile cdc_synchronizers mode (cdc_sync_constraints.py, group "pg_reset"). The pgslice's PG_RSYNC=1 leaves
// use an identical synchroniser of the same rst_n; serial and stream share one fixed-phase PLL lattice, so both
// release on the same pg_clk edge (bench tb_hbm_su_pgslice_lg_rsync checks it).
// Datapath edges unchanged (the tap's calendars, returns and fault rule are the pair tap's).
// RSYNC_MUT (bench only, must FAIL): 1 = the r8b structure (one pg_clk flop of the raw rst_n, no serial source flop).
module ot_hbm_su_static_pg_lg_tap #(
 parameter integer READ_RETURN=10,WRITE_RETURN=7,
 parameter integer RSYNC_MUT=0
)(
 input  wire clk_ctl,             // serial root (source flop of the reset synchroniser only)
 input  wire pg_clk,              // stream root (the slice's VM bank leaf clock): every tap flop
 input  wire rst_n,               // serial power-on reset
 input  wire [33:0]  local_rq,far_rq,
 input  wire [561:0] local_wq,far_wq,
 input  wire [1:0]   local_read,local_write,
 output wire [33:0]  near_rq,
 output wire [561:0] near_wq,
 input  wire [513:0] near_rr,
 input  wire [1:0]   near_w_done,
 output wire [513:0] local_rr,far_rr,
 output wire [1:0]   local_w_done,far_w_done,
 output wire         fault
);
 wire tap_rst_n;
 if(RSYNC_MUT==1)begin:g_rmut
  (* keep = "true" *) reg lg_rst; always @(posedge pg_clk) lg_rst <= rst_n;
  assign tap_rst_n = lg_rst;
 end else begin:g_rsync
  reg rc; reg [1:0] rs;
  always @(posedge clk_ctl) rc <= rst_n;
  always @(posedge pg_clk) rs <= {rs[0], rc};
  assign tap_rst_n = rs[1];
 end
 ot_hbm_vm_lg_pair_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_tap(
  .clk(pg_clk),.rst_n(tap_rst_n),.local_rq(local_rq),.far_rq(far_rq),.local_wq(local_wq),.far_wq(far_wq),
  .local_read(local_read),.local_write(local_write),.near_rq(near_rq),.near_wq(near_wq),.near_rr(near_rr),
  .near_w_done(near_w_done),.local_rr(local_rr),.far_rr(far_rr),.local_w_done(local_w_done),.far_w_done(far_w_done),
  .fault(fault));
endmodule
`default_nettype wire
