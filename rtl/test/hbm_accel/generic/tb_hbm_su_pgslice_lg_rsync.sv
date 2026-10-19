`timescale 1ps/1ps
`default_nettype none
// HBM-SU3 2026-10-17: ot_hbm_su_static_pgslice_lg RSYNC=1 (stream-domain reset synchronisers for the LG taps and the
// two VM bank leaves) against the r8b structure RSYNC=0, die d4f parameters (QID 2, G 0, MLAT 4, ALAT 3, LEAF 1,
// MULTIRATE 1, COLLPORT 1, RF_LOCAL 1), serial 4 / stream 3 quanta on one lattice (common edge every 12 quanta).
//  (1) LOCKSTEP: every output bit (slice_x, inj_q, fault, lg_rq, lg_wq, far_rr, far_w_done, lg_fault) equal (!==) at
//      every serial and stream edge outside the reset windows, under random traffic on every input, NRST resets.
//  (2) RESET EDGES: the tap reset (pg_lg_tap g_rsync.rs[1]) and the leaf reset (pgslice g_pg_rsync.rs[1]) change on the
//      SECOND pg_clk edge strictly after the serial edge that samples the new rst_n, for both assert and release, at
//      every lattice phase; the two synchronisers agree.
// MUT (passed to the DUT's RSYNC_MUT): 1 = r8b one-flop tap reset -> (2) FAILS.
module tb_hbm_su_pgslice_lg_rsync;
 parameter integer MUT=0, NRST=3, EDGES=1500;
 localparam integer TS=1200, TP=900, T0=600;    // posedges: serial T0+TS*k, stream T0+TP*m (lattice q=300)
 reg sclk=0, pclk=0;
 initial begin #(T0); forever begin sclk=1; #(TS/2); sclk=0; #(TS/2); end end
 initial begin #(T0); forever begin pclk=1; #(TP/2); pclk=0; #(TP/2); end end
 reg por=0, brst=0, active=0;
 reg [1741:0] control; reg [59:0] vmr; reg [77:0] vmw; reg [127:0] rfw; reg [35:0] rfc; reg [255:0] rfd; reg [11:0] rsel;
 reg [1:0] dwv; reg [17:0] dwr; reg [1023:0] dwd;
 reg [513:0] lgrr; reg [1:0] lgwd, lgr, lgw, injrd; reg [33:0] farrq; reg [561:0] farwq; reg [159:0] inja;
 function automatic [1023:0] rnd1024(input integer dummy); integer i; begin
  for(i=0;i<32;i=i+1) rnd1024[i*32+:32]=$urandom; end endfunction
 task automatic quiet; begin
  control=0; vmr=0; vmw=0; rfw=0; rfc=0; rfd=0; rsel=0; dwv=0; dwr=0; dwd=0;
  lgrr=0; lgwd=0; lgr=0; lgw=0; injrd=0; farrq=0; farwq=0; inja=0; end endtask
 initial quiet;
 always @(negedge sclk) if(active) begin
  control={rnd1024(0),rnd1024(0)}; vmr={$urandom,$urandom}; vmw={$urandom,$urandom,$urandom};
  rfw={$urandom,$urandom,$urandom,$urandom}; rfc={$urandom,$urandom}; rfd=rnd1024(0); rsel=$urandom;
  dwv=$urandom; dwr=$urandom; dwd=rnd1024(0);
 end
 always @(negedge pclk) if(active) begin
  lgrr={rnd1024(0)}; lgwd=$urandom; lgr=$urandom; lgw=$urandom; injrd=$urandom; inja={$urandom,$urandom,$urandom,$urandom,$urandom};
  farrq={$urandom,$urandom}; farwq=rnd1024(0);
 end
 wire [1031:0] o_unused;
 `define PGS(NAME,RS,RM) \
 wire [31:0] NAME``_sx; wire [1023:0] NAME``_iq; wire NAME``_f, NAME``_lf; wire [33:0] NAME``_rq; wire [561:0] NAME``_wq; \
 wire [513:0] NAME``_frr; wire [1:0] NAME``_fwd; \
 ot_hbm_su_static_pgslice_lg #(.QID(2),.G(0),.MLAT(4),.ALAT(3),.LEAF(1),.MULTIRATE(1),.COLLPORT(1),.RF_LOCAL(1), \
  .RSYNC(RS),.RSYNC_MUT(RM)) NAME( \
  .pg_clk(pclk),.clk_lane({256{sclk}}),.clk_insert({128{sclk}}),.rst_lane_n({32{por}}),.clk_bcast({4{sclk}}), \
  .rst_bcast_n({4{por}}),.clk_bank({32{sclk}}),.clk_bank_macro({192{sclk}}),.clk_ctl(sclk),.clk_side({6{sclk}}), \
  .rst_n(por),.pos({2'd2,2'd0}),.bridge_rst_n(brst),.control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_bword(rfw),.rf_bcmd(rfc), \
  .rf_dsec(rfd),.red_sel(rsel),.slice_x(NAME``_sx),.inj_rd(injrd),.inj_addr(inja),.inj_q(NAME``_iq),.dw_v(dwv), \
  .dw_row(dwr),.dw_d(dwd),.fault(NAME``_f),.lg_rq(NAME``_rq),.lg_wq(NAME``_wq),.lg_rr(lgrr),.lg_w_done(lgwd), \
  .lg_read(lgr),.lg_write(lgw),.far_rq(farrq),.far_wq(farwq),.far_rr(NAME``_frr),.far_w_done(NAME``_fwd), \
  .lg_fault(NAME``_lf));
 `PGS(dut,1,MUT)
 `PGS(ref0,0,0)
 wire [2196:0] o_dut={dut_sx,dut_iq,dut_f,dut_rq,dut_wq,dut_frr,dut_fwd,dut_lf};
 wire [2196:0] o_ref={ref0_sx,ref0_iq,ref0_f,ref0_rq,ref0_wq,ref0_frr,ref0_fwd,ref0_lf};
 integer checks=0, errors=0, cmp=0;
 always @(posedge sclk or posedge pclk) if(cmp) begin
  #1; checks=checks+1;
  if(o_dut!==o_ref) begin errors=errors+1; if(errors<6) $display("LOCKSTEP MISMATCH t=%0t dut/ref fault %b/%b lg_fault %b/%b", $time, dut_f, ref0_f, dut_lf, ref0_lf); end
 end
 // ---- reset edges
 wire tap_r;
 if(MUT==1)begin:g_tm assign tap_r = dut.g_tap.u_tap.g_rmut.lg_rst; end else begin:g_ts assign tap_r = dut.g_tap.u_tap.g_rsync.rs[1]; end
 wire leaf_r = dut.u_slice.g_pg_rsync.rs[1];
 time t_cap; reg want; reg armed=0; reg last_por=1'bx;
 always @(posedge sclk) if(por!==last_por) begin last_por<=por; t_cap=$time; want=por; armed=1; end
 function automatic time exp_edge(input time ts); integer m1; begin
  m1=(ts-T0)/TP+1; exp_edge=T0+TP*(m1+1); end endfunction    // second stream posedge strictly after ts
 always @(tap_r) if(armed && $time>0 && tap_r!==1'bx) begin
  checks=checks+1;
  if(tap_r!==want || $time!=exp_edge(t_cap)) begin errors=errors+1;
   $display("RESET EDGE FAIL tap reset -> %b at t=%0t, want %b at %0t (serial capture %0t)", tap_r, $time, want, exp_edge(t_cap), t_cap); end
 end
 always @(leaf_r) if(armed && $time>0 && leaf_r!==1'bx) begin
  checks=checks+1;
  if(leaf_r!==want || $time!=exp_edge(t_cap)) begin errors=errors+1;
   $display("RESET EDGE FAIL leaf reset -> %b at t=%0t, want %b at %0t", leaf_r, $time, want, exp_edge(t_cap)); end
 end
 integer r, k, phases_seen=0;
 initial begin
  if(!$value$plusargs("NRST=%d", r)) r=NRST;
  repeat(5) @(negedge sclk);
  por=1; repeat(3) @(negedge sclk); por=0;              // first power-on assertion (clears the X state)
  for(k=0;k<r;k=k+1) begin
   repeat(6+k) @(negedge sclk);                          // 6+k: the release capture visits every lattice phase
   por=1; repeat(2) @(negedge pclk); brst=1;
   repeat(8) @(negedge sclk);
   cmp=1; active=1;
   repeat(EDGES) @(negedge sclk);
   active=0; quiet; cmp=0; @(negedge sclk);
   por=0; brst=0;
  end
  repeat(6) @(negedge sclk);
  if(errors==0 && checks>r*EDGES) $display("PGSLICE_LG_RSYNC PASS checks=%0d resets=%0d", checks, r);
  else $display("PGSLICE_LG_RSYNC FAIL errors=%0d checks=%0d", errors, checks);
  $finish;
 end
endmodule
`default_nettype wire
