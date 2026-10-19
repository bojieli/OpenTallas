`timescale 1ns/1ps
`default_nettype none
// TW3-PGSTREAM 2026-10-19: lockstep of the one-root split ot_hbm_su_static_pg_stream_split (= pg_stream_q + pg_stream_s
// abutted over the banked seam) against the CURRENT two-root ot_hbm_su_static_pg_stream (IJ_REG 1, d4g STRAP/RSYNC/
// MULTIRATE/COLLPORT form), same parameters and stimulus, 3:4 clocks on the common epoch (q = 278 ps, serial 1112 ps,
// stream 834 ps).
//   serial edges: su_rr equal on the same edge; ij_v/ij_row/ij_bad at DUT edge k+1 == REF edge k (+1 serial, H-D4G);
//                 pg_fault at DUT k+2 == REF k (+2, synchroniser of a sticky flag).
//   stream edges: lg_rq, lg_wq, far_rr, far_w_done, lg_fault equal on the same edge.
//   seam calendar: every bank the readers select (request banks at active stream edges, return banks at the staging
//                 serial edge, inject banks at every serial edge) must be stable >= WSU[g] before the read and must not be
//                 rewritten < WHO[g] after it; the measured minimum windows are printed per group.
//   HBM-PGSTREAM-B 10-19: per-group windows = EXACTLY the seam_windows the merged tile's gate / route SDC declares
//                 (physical/ref_tile/hbm_su_pg_stream_b_1019 spec): request 4q / 2q, return 2q / 4q, inject 3q / 7q
//                 (was one 2q floor for all groups). The request read is taken from the bridge's actual read point
//                 (rd_v / rd_b), so MUT 12 (request bank read one stream edge early into a pre-stage, functionally equal)
//                 fails by window only: the bench guards the windows the SDC relies on.
// Stimulus: two reset epochs (both resets released 100 ps before a coincident edge); per epoch 60 serial edges of zero
// traffic (no faults), then random serial (vmr_cmd, su_wq) and stream (LG returns, far, inject) inputs -> the sticky
// faults rise mid-run, so the fault offset is exercised.
module tb_hbm_su_pg_stream_regional;
 parameter integer SAFE_COPY=1,QID=1, G=2, READ_RETURN=10, WRITE_RETURN=7, MUT=0, EDGES=1500, FAULT_REG=0;
 localparam integer Q=278;
 localparam integer WSU [0:2] = '{4*Q, 2*Q, 3*Q};   // setup windows: request, return, inject (= seam_windows setup_q)
 localparam integer WHO [0:2] = '{2*Q, 4*Q, 7*Q};   // rewrite-after-read windows (= seam_windows hold_q)
 reg clk_ctl=0, pg_clk=0, rst_n=0, brst_n=0;
 wire [3:0] pos = {2'(QID), 2'(G)};
 reg [59:0] vmr; reg [561:0] suwq; reg [513:0] lgrr; reg [1:0] lgwd, lgr, lgw, injrd; reg [33:0] farrq; reg [561:0] farwq;
 reg [159:0] inja;
 reg traffic=0, fault_only=0;
 `define PGS_PORTS(N) \
  wire [513:0] N``_surr; wire [3:0] N``_ijv; wire [35:0] N``_ijrow; wire N``_ijbad, N``_pgf; wire [33:0] N``_lgrq; \
  wire [561:0] N``_lgwq; wire [513:0] N``_farrr; wire [1:0] N``_farwd; wire N``_lgf;
 `PGS_PORTS(r)
 `PGS_PORTS(d)
 `define PGS_CONN(N) \
  .clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(rst_n),.bridge_rst_n(brst_n),.pos(pos),.vmr_cmd(vmr),.su_wq(suwq), \
  .su_rr(N``_surr),.ij_v(N``_ijv),.ij_row(N``_ijrow),.ij_bad(N``_ijbad),.pg_fault(N``_pgf),.inj_rd(injrd),.inj_addr(inja), \
  .lg_rq(N``_lgrq),.lg_wq(N``_lgwq),.lg_rr(lgrr),.lg_w_done(lgwd),.lg_read(lgr),.lg_write(lgw),.far_rq(farrq), \
  .far_wq(farwq),.far_rr(N``_farrr),.far_w_done(N``_farwd),.lg_fault(N``_lgf)
 ot_hbm_su_static_pg_stream #(.QID(QID),.G(G),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MULTIRATE(1),
  .COLLPORT(1),.RSYNC(1),.STRAP(1),.IJ_REG(1)) ref_i(`PGS_CONN(r));
 ot_hbm_su_static_pg_stream_split_regional #(.SAFE_COPY(SAFE_COPY),.QID(QID),.G(G),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT),
  .STRAP(1),.FAULT_REG(FAULT_REG)) dut(`PGS_CONN(d));
 // ---------------------------------------------------------------- clocks (coincident every 3 serial / 4 stream edges)
 localparam realtime T0 = 10.008;   // first coincident edge (12q multiple)
 initial begin #(T0); forever begin pg_clk=1; #0.417; pg_clk=0; #0.417; end end
 initial begin #(T0); forever begin clk_ctl=1; #0.556; clk_ctl=0; #0.556; end end
 // ---------------------------------------------------------------- stimulus
 function automatic [511:0] rnd512(input integer dummy);
  for(integer i=0;i<16;i=i+1) rnd512[32*i+:32]=$urandom;
 endfunction
 task automatic zero_in; begin
  vmr=0; suwq=0; lgrr=0; lgwd=0; lgr=0; lgw=0; injrd=0; inja=0; farrq=0; farwq=0; end endtask
 initial zero_in();
 always @(posedge clk_ctl) begin
  #0.1;
  if(traffic) begin
   vmr={$urandom,$urandom}; suwq={$urandom,$urandom,rnd512(0)};
  end else begin vmr=0; suwq=0; end
 end
 always @(posedge pg_clk) begin
  #0.05;
  if(traffic) begin
   lgrr={$urandom,rnd512(0)}; lgwd=$urandom; lgr=$urandom; lgw=$urandom; farrq={$urandom,$urandom};
   farwq={$urandom,$urandom,rnd512(0)}; injrd=$urandom; inja={$urandom,$urandom,$urandom,$urandom,$urandom};
  end else begin lgrr=0; lgwd=0; lgr=0; lgw=0; farrq=0; farwq=0; injrd=0; inja=0; end
 end
 // ---------------------------------------------------------------- compare
 integer errors=0, checks=0, sk=0, chk=0, wchecks=0;
 reg [40:0] rij_h [0:2]; reg rpgf_h [0:2];
 reg pgf_source_ref=0;
 reg [1:0] pgf_sync_ref=0;
 // Independent source-publication + two-stage capture reference. Fault
 // reporting adds one stream publication edge; the data calendar is unchanged.
 always @(posedge pg_clk) begin
  if(!dut.u_s.leaf_rst_n) pgf_source_ref<=0;
  else pgf_source_ref <= (|dut.u_s.leaf_fault)||(|dut.u_s.bridge_fault);
 end
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n) pgf_sync_ref<=0;
  else pgf_sync_ref<={pgf_sync_ref[0],pgf_source_ref};
 task automatic err(input [8*24-1:0] what); begin
  errors=errors+1;
  if(errors<=8) $display("MISMATCH %0s t=%0t sk=%0d", what, $time, sk);
 end endtask
 integer cov_rr=0, cov_ij=0, cov_bad=0, cov_lg=0;
 always @(posedge clk_ctl) begin
  // An independent bridge reset must not clear a still-asserted leaf fault.
  // The source publication resets only with its stream-domain leaf reset.
  if(FAULT_REG!=0 && fault_only) begin
   checks=checks+1;
   if(d_pgf!==pgf_sync_ref[1]) err("pg_fault bridge reset");
  end
  if(chk) begin
   checks=checks+1;
   if(r_surr[256]||r_surr[513]) cov_rr=cov_rr+1;
   if(|r_ijv) cov_ij=cov_ij+1;
   if(r_ijbad) cov_bad=cov_bad+1;
   if(d_surr!==r_surr) err("su_rr");
   if({d_ijbad,d_ijrow,d_ijv}!==rij_h[0]) err("ij (+1 serial)");
   if(FAULT_REG!=0) begin
    if(d_pgf!==pgf_sync_ref[1]) err("pg_fault registered CDC");
   end else if(d_pgf!==rpgf_h[1]) err("pg_fault (+2 serial)");
  end
  rij_h[0]<={r_ijbad,r_ijrow,r_ijv}; rpgf_h[0]<=r_pgf; rpgf_h[1]<=rpgf_h[0];
  sk=sk+1;
 end
 always @(posedge pg_clk) if(chk) begin
  checks=checks+1;
  if(r_lgrq[16]||r_lgrq[33]) cov_lg=cov_lg+1;
  if(d_lgrq!==r_lgrq) err("lg_rq");
  if(d_lgwq!==r_lgwq) err("lg_wq");
  if(d_farrr!==r_farrr) err("far_rr");
  if(d_farwd!==r_farwd) err("far_w_done");
  if(d_lgf!==r_lgf) err("lg_fault");
 end
 // ---------------------------------------------------------------- seam calendar windows
 // groups: 0 request banks (q->s), 1 return banks (s->q), 2 inject banks (s->q)
 realtime tchg [0:2][0:2]; realtime trd [0:2][0:2]; realtime wsu [0:2]; realtime who [0:2];
 integer werr=0;
 initial for(integer g=0;g<3;g=g+1) begin wsu[g]=1e9; who[g]=1e9; for(integer b=0;b<3;b=b+1) begin tchg[g][b]=-1e9; trd[g][b]=-1e9; end end
 task automatic wchg(input integer g, input integer b); begin
  if(chk && $realtime-trd[g][b] < who[g]) who[g]=$realtime-trd[g][b];
  if(chk && $realtime-trd[g][b] < WHO[g]*1.0e-3-1e-6) begin werr=werr+1;
   if(werr<=6) $display("WINDOW hold group %0d bank %0d rewritten %0.3f ns after its read t=%0t", g, b, $realtime-trd[g][b], $time); end
  tchg[g][b]=$realtime;
 end endtask
 task automatic wrd(input integer g, input integer b); begin
  wchecks=wchecks+1;
  if($realtime-tchg[g][b] < wsu[g]) wsu[g]=$realtime-tchg[g][b];
  if($realtime-tchg[g][b] < WSU[g]*1.0e-3-1e-6) begin werr=werr+1;
   if(werr<=6) $display("WINDOW setup group %0d bank %0d read %0.3f ns after its write t=%0t", g, b, $realtime-tchg[g][b], $time); end
  trd[g][b]=$realtime;
 end endtask
 always @({dut.rq_b0,dut.wq_b0}) wchg(0,0);
 always @({dut.rq_b1,dut.wq_b1}) wchg(0,1);
 always @(dut.rr_b0) wchg(1,0);
 always @(dut.rr_b1) wchg(1,1);
 always @(dut.ijb0) wchg(2,0);
 always @(dut.ijb1) wchg(2,1);
 always @(dut.ijb2) wchg(2,2);
 always @(posedge pg_clk) if(chk && dut.u_s.g_leaf[0].u_bs.rd_v) wrd(0, dut.u_s.g_leaf[0].u_bs.rd_b);
 always @(posedge clk_ctl) if(chk) begin
  wrd(1, dut.u_q.g_br[0].u_bq.rsel);
  wrd(2, dut.u_q.ib);
 end
 // ---------------------------------------------------------------- sequence
 realtime tc;
 initial begin
  #(T0+1.0);
  for(integer ep=0; ep<2; ep=ep+1) begin
   chk=0; traffic=0; rst_n=0; brst_n=0;
   // release 100 ps before a coincident edge (12q = 3.336 ns lattice from T0), >= 6 epochs after assertion
   tc = T0 + 3.336*($floor(($realtime - T0)/3.336) + 7);
   #(tc - 0.1 - $realtime); rst_n=1; brst_n=1;
   repeat(30) @(posedge clk_ctl);
   chk=1;
   repeat(30) @(posedge clk_ctl);
   traffic=1;
   repeat(EDGES) @(posedge clk_ctl);
   traffic=0;
   repeat(8) @(posedge clk_ctl);
  end
  chk=0;
  if(FAULT_REG!=0) begin
   fault_only=1;
   @(negedge pg_clk); brst_n=0;
   repeat(8) @(posedge clk_ctl);
   brst_n=1;
   repeat(8) @(posedge clk_ctl);
   fault_only=0;
  end
  $display("windows (ns): request setup %0.3f hold %0.3f | return setup %0.3f hold %0.3f | inject setup %0.3f hold %0.3f",
           wsu[0], who[0], wsu[1], who[1], wsu[2], who[2]);
  $display("ref faults pg=%0d lg=%0d (sticky; raised during traffic); coverage: serial fill returns %0d, inject hits %0d (conflicts %0d), LG near requests %0d",
           r_pgf, r_lgf, cov_rr, cov_ij, cov_bad, cov_lg);
  if(errors==0 && werr==0) $display("PG_STREAM_SPLIT PASS checks=%0d windows=%0d MUT=%0d RR=%0d/%0d", checks, wchecks, MUT, READ_RETURN, WRITE_RETURN);
  else $display("PG_STREAM_SPLIT FAIL errors=%0d window_errors=%0d MUT=%0d", errors, werr, MUT);
  $finish;
 end
endmodule
`default_nettype wire
