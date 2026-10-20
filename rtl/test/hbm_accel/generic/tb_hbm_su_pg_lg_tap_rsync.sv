`timescale 1ps/1ps
`default_nettype none
// HBM-SU3 2026-10-17: kit-level bench of ot_hbm_su_static_pg_lg_tap (kit hbm_su_pg_lgtap_1017).
//  (1) LOCKSTEP vs the unchanged ot_hbm_vm_lg_pair_tap (10/7): every output bit equal (!==) at every stream and serial
//      edge outside the reset windows, random traffic on every input, NRST resets at every lattice phase.
//  (2) RESET EDGES: the tap reset (g_rsync.rs[1]) changes on the SECOND pg_clk edge strictly after the serial edge that
//      samples the new rst_n (assert and release); serial 4 / stream 3 quanta, common edge every 12 quanta.
// MUT (-> RSYNC_MUT): 1 = r8b one pg_clk flop of the raw serial rst_n -> (2) FAILS.
// The DUT runs LOCAL_SPLIT=1 (its default, NATIVE-FIX3 10-18) against the LOCAL_SPLIT=0 reference: (1) proves 0 added edges.
// SMUT (-> SPLIT_MUT): 1 = split calendar due tap one entry late, 2 = local return copy fed from the near_rr pins -> (1) FAILS.
module tb_hbm_su_pg_lg_tap_rsync;
 parameter integer MUT=0, SMUT=0, NRST=6, EDGES=4000;
 localparam integer TS=1200, TP=900, T0=600;
 reg sclk=0, pclk=0;
 initial begin #(T0); forever begin sclk=1; #(TS/2); sclk=0; #(TS/2); end end
 initial begin #(T0); forever begin pclk=1; #(TP/2); pclk=0; #(TP/2); end end
 reg por=0, active=0, ref_rst=0;
 reg [33:0] lrq, frq; reg [561:0] lwq, fwq; reg [1:0] lrd, lwr, nwd; reg [513:0] nrr;
 // 18 x 32 random bits built in a 576-bit temp (a part-select past bit 561 of the result aborts fleet Icarus 12 vvp, rc 134)
 function automatic [561:0] r562(input integer d); integer i; reg [575:0] t; begin for(i=0;i<18;i=i+1) t[i*32+:32]=$urandom; r562=t[561:0]; end endfunction
 always @(negedge pclk) if(active) begin
  // sparse valids so the calendars and the return checks see both legal and illegal traffic
  lrq=r562(0); frq=r562(0); lwq=r562(0); fwq=r562(0); lrd=$urandom; lwr=$urandom; nwd=$urandom; nrr=r562(0);
 end else begin lrq=0; frq=0; lwq=0; fwq=0; lrd=0; lwr=0; nwd=0; nrr=0; end
 wire [33:0] d_nrq, r_nrq; wire [561:0] d_nwq, r_nwq; wire [513:0] d_lrr, r_lrr, d_frr, r_frr;
 wire [1:0] d_lwd, r_lwd, d_fwd, r_fwd; wire d_f, r_f;
 ot_hbm_su_static_pg_lg_tap #(.READ_RETURN(10),.WRITE_RETURN(7),.RSYNC_MUT(MUT),.SPLIT_MUT(SMUT)) dut(
  .clk_ctl(sclk),.pg_clk(pclk),.rst_n(por),.local_rq(lrq),.far_rq(frq),.local_wq(lwq),.far_wq(fwq),.local_read(lrd),
  .local_write(lwr),.near_rq(d_nrq),.near_wq(d_nwq),.near_rr(nrr),.near_w_done(nwd),.local_rr(d_lrr),.far_rr(d_frr),
  .local_w_done(d_lwd),.far_w_done(d_fwd),.fault(d_f));
 ot_hbm_vm_lg_pair_tap #(.READ_RETURN(10),.WRITE_RETURN(7)) ref0(
  .clk(pclk),.rst_n(ref_rst),.local_rq(lrq),.far_rq(frq),.local_wq(lwq),.far_wq(fwq),.local_read(lrd),
  .local_write(lwr),.near_rq(r_nrq),.near_wq(r_nwq),.near_rr(nrr),.near_w_done(nwd),.local_rr(r_lrr),.far_rr(r_frr),
  .local_w_done(r_lwd),.far_w_done(r_fwd),.fault(r_f));
 wire [2197:0] o_d={d_nrq,d_nwq,d_lrr,d_frr,d_lwd,d_fwd,d_f}, o_r={r_nrq,r_nwq,r_lrr,r_frr,r_lwd,r_fwd,r_f};
 integer checks=0, errors=0, cmp=0, faults=0;
 always @(posedge sclk or posedge pclk) if(cmp) begin
  #1; checks=checks+1; if(d_f) faults=faults+1;
  if(o_d!==o_r) begin errors=errors+1; if(errors<6) $display("LOCKSTEP MISMATCH t=%0t", $time); end
 end
 wire tap_r;
 if(MUT==1)begin:g_tm assign tap_r = dut.g_rmut.lg_rst; end else begin:g_ts assign tap_r = dut.g_rsync.rs[1]; end
 time t_cap; reg want; reg armed=0; reg last_por=1'bx;
 always @(posedge sclk) if(por!==last_por) begin last_por<=por; t_cap=$time; want=por; armed=1; end
 function automatic time exp_edge(input time ts); integer m1; begin m1=(ts-T0)/TP+1; exp_edge=T0+TP*(m1+1); end endfunction
 integer redges=0;
 always @(tap_r) if(armed && tap_r!==1'bx) begin
  checks=checks+1; redges=redges+1;
  if(tap_r!==want || $time!=exp_edge(t_cap)) begin errors=errors+1;
   $display("RESET EDGE FAIL tap reset -> %b at t=%0t, want %b at %0t (serial capture %0t)", tap_r, $time, want, exp_edge(t_cap), t_cap); end
 end
 integer k;
 initial begin
  repeat(3) @(negedge sclk); por=1; repeat(2) @(negedge sclk); por=0;
  for(k=0;k<NRST;k=k+1) begin
   repeat(5+k) @(negedge sclk);
   por=1; @(posedge tap_r); @(negedge pclk); ref_rst=1;      // reference released on the DUT's synchronised edge
   repeat(2) @(negedge sclk); cmp=1; active=1;
   repeat(EDGES) @(negedge pclk);
   active=0; @(negedge pclk); cmp=0; por=0; ref_rst=0;
  end
  repeat(6) @(negedge sclk);
  if(errors==0 && checks>NRST*EDGES && redges>=2*NRST && faults>0) $display("PG_LG_TAP_RSYNC PASS checks=%0d reset_edges=%0d fault_edges=%0d", checks, redges, faults);
  else $display("PG_LG_TAP_RSYNC FAIL errors=%0d checks=%0d reset_edges=%0d fault_edges=%0d", errors, checks, redges, faults);
  $finish;
 end
endmodule
`default_nettype wire
