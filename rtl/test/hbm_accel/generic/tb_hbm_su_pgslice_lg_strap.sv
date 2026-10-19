`timescale 1ps/1ps
`default_nettype none
// OWN-PGLG 2026-10-18: position-strapped LIGHT pgslice_lg master (kit hbm_su_pgslice_lg_light_d4g) against the
// per-position parameterised slices, in the hard-children cluster configuration of the d4g die (+define+OT_HARD_CHILDREN
// +define+OT_SU_SYNC_RST: KIND0 r2 lane leaves, CLOSED bank6_clock banks, regional sync reset relay; PIN_REG 1, MLAT 4,
// ALAT 3, LEAF 1, FETCH 2, MULTIRATE 1, COLLPORT 1, RF_LOCAL 1, RSYNC 1), serial 4 / stream 3 quanta on one lattice.
//  (1) LOCKSTEP: for positions P0 = (QID 0, G 2) [B39 no-op on] and P1 = (QID 3, G 3), the strapped master (STRAP 1,
//      structure parameters QID 1 / G 2, pos = {qid,g}) equals ot_hbm_su_static_pgslice_lg #(QID,G) on every output bit
//      (slice_x, inj_q, fault, lg_rq, lg_wq, far_rr, far_w_done, lg_fault) at every serial and stream edge outside the
//      reset windows, under random traffic on every input, NRST resets.
//  (2) CLASS CHECK: after a reset with quiet inputs, a strap of another structure class (P0 pos -> {0,0} = Q0G0)
//      latches the DUT fault while the reference stays clean.
// MUT (passed to the strapped DUTs only, must FAIL): 1 fill registered early; 2 drain group select flipped;
//      10 delivery word order reversed; 11 strap g ignored (G parameter used).
module tb_hbm_su_pgslice_lg_strap;
 parameter integer MUT=0, NRST=2, EDGES=1200;
 localparam integer TS=1200, TP=900, T0=600;    // posedges: serial T0+TS*k, stream T0+TP*m (lattice q=300)
 reg sclk=0, pclk=0;
 initial begin #(T0); forever begin sclk=1; #(TS/2); sclk=0; #(TS/2); end end
 initial begin #(T0); forever begin pclk=1; #(TP/2); pclk=0; #(TP/2); end end
 reg por=0, brst=0, active=0;
 reg [1741:0] control; reg [59:0] vmr; reg [77:0] vmw; reg [127:0] rfw; reg [35:0] rfc; reg [255:0] rfd; reg [11:0] rsel;
 reg [1:0] dwv; reg [17:0] dwr; reg [1023:0] dwd;
 reg [513:0] lgrr; reg [1:0] lgwd, lgr, lgw, injrd; reg [33:0] farrq; reg [561:0] farwq; reg [159:0] inja;
 reg [3:0] pos0={2'd0,2'd2}, pos1={2'd3,2'd3};
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
 `define PGS(NAME,QQ,GG,ST,PS,MM) \
 wire [31:0] NAME``_sx; wire [1023:0] NAME``_iq; wire NAME``_f, NAME``_lf; wire [33:0] NAME``_rq; wire [561:0] NAME``_wq; \
 wire [513:0] NAME``_frr; wire [1:0] NAME``_fwd; \
 ot_hbm_su_static_pgslice_lg #(.QID(QQ),.G(GG),.MLAT(4),.ALAT(3),.LEAF(1),.FETCH_EXTRA_EDGES(2),.MULTIRATE(1),.COLLPORT(1), \
  .RF_LOCAL(1),.PIN_REG(1),.RSYNC(1),.STRAP(ST),.MUT(MM)) NAME( \
  .pg_clk(pclk),.clk_lane({256{sclk}}),.clk_insert({128{sclk}}),.rst_lane_n({32{por}}),.clk_bcast({4{sclk}}), \
  .rst_bcast_n({4{por}}),.clk_bank({32{sclk}}),.clk_bank_macro({192{sclk}}),.clk_ctl(sclk),.clk_side({6{sclk}}), \
  .rst_n(por),.pos(PS),.bridge_rst_n(brst),.control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_bword(rfw),.rf_bcmd(rfc), \
  .rf_dsec(rfd),.red_sel(rsel),.slice_x(NAME``_sx),.inj_rd(injrd),.inj_addr(inja),.inj_q(NAME``_iq),.dw_v(dwv), \
  .dw_row(dwr),.dw_d(dwd),.fault(NAME``_f),.lg_rq(NAME``_rq),.lg_wq(NAME``_wq),.lg_rr(lgrr),.lg_w_done(lgwd), \
  .lg_read(lgr),.lg_write(lgw),.far_rq(farrq),.far_wq(farwq),.far_rr(NAME``_frr),.far_w_done(NAME``_fwd), \
  .lg_fault(NAME``_lf));
 `PGS(dut0,1,2,1,pos0,MUT)
 `PGS(ref0,0,2,0,4'b0010,0)
 `PGS(dut1,1,2,1,pos1,MUT)
 `PGS(ref1,3,3,0,4'b1111,0)
 wire [2196:0] o_dut0={dut0_sx,dut0_iq,dut0_f,dut0_rq,dut0_wq,dut0_frr,dut0_fwd,dut0_lf};
 wire [2196:0] o_ref0={ref0_sx,ref0_iq,ref0_f,ref0_rq,ref0_wq,ref0_frr,ref0_fwd,ref0_lf};
 wire [2196:0] o_dut1={dut1_sx,dut1_iq,dut1_f,dut1_rq,dut1_wq,dut1_frr,dut1_fwd,dut1_lf};
 wire [2196:0] o_ref1={ref1_sx,ref1_iq,ref1_f,ref1_rq,ref1_wq,ref1_frr,ref1_fwd,ref1_lf};
 integer checks=0, errors=0, cmp=0, faults_seen=0, data_seen=0;
 always @(posedge sclk or posedge pclk) if(cmp) begin
  #1; checks=checks+2;
  if(ref0_f) faults_seen=faults_seen+1;
  if(|ref1_sx || |ref1_iq || |ref1_rq) data_seen=data_seen+1;
  if(o_dut0!==o_ref0) begin errors=errors+1; if(errors<6) $display("LOCKSTEP MISMATCH P0 t=%0t fault %b/%b lg_fault %b/%b", $time, dut0_f, ref0_f, dut0_lf, ref0_lf); end
  if(o_dut1!==o_ref1) begin errors=errors+1; if(errors<6) $display("LOCKSTEP MISMATCH P1 t=%0t fault %b/%b lg_fault %b/%b", $time, dut1_f, ref1_f, dut1_lf, ref1_lf); end
 end
 integer r, k, class_ok=0;
 initial begin
  if(!$value$plusargs("NRST=%d", r)) r=NRST;
  repeat(5) @(negedge sclk);
  por=1; repeat(3) @(negedge sclk); por=0;              // first power-on assertion (clears the X state)
  for(k=0;k<r;k=k+1) begin
   repeat(6+k) @(negedge sclk);
   por=1; repeat(2) @(negedge pclk); brst=1;
   repeat(12) @(negedge sclk);
   cmp=1; active=1;
   repeat(EDGES) @(negedge sclk);
   active=0; quiet; cmp=0; @(negedge sclk);
   por=0; brst=0;
  end
  // (2) class check: quiet reset, then a wrong-class strap on the P0 master
  repeat(6) @(negedge sclk); por=1; repeat(2) @(negedge pclk); brst=1; repeat(40) @(negedge sclk);
  if(dut0_f!==1'b0 || ref0_f!==1'b0) $display("CLASS PRECHECK: quiet fault dut0/ref0 %b/%b", dut0_f, ref0_f);
  else begin
   pos0={2'd0,2'd0}; repeat(4) @(negedge sclk);
   if(dut0_f===1'b1 && ref0_f===1'b0) class_ok=1;
   else $display("CLASS CHECK FAIL: wrong-class strap fault dut0/ref0 %b/%b", dut0_f, ref0_f);
  end
  if(errors==0 && class_ok && checks>2*r*EDGES) $display("PGSLICE_LG_STRAP PASS checks=%0d resets=%0d ref_fault_edges=%0d data_edges=%0d", checks, r, faults_seen, data_seen);
  else $display("PGSLICE_LG_STRAP FAIL errors=%0d class_ok=%0d checks=%0d", errors, class_ok, checks);
  $finish;
 end
endmodule
`default_nettype wire
