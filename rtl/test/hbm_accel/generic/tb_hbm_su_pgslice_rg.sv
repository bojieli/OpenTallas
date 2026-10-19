`timescale 1ps/1ps
`default_nettype none
// TW-HBM-PGLG 2026-10-19: REGION (landed) LIGHT slice ot_hbm_su_static_pgslice_rg against the flat strapped master
// ot_hbm_su_static_pgslice_lg (bench tb_hbm_su_pgslice_lg_strap proved strapped == parameterised), in the d4g die
// configuration (+define+OT_HARD_CHILDREN +define+OT_SU_SYNC_RST: KIND0 r2 leaves, CLOSED bank6_clock banks; PIN_REG 1,
// MLAT 4, ALAT 3, LEAF 1, FETCH 2, MULTIRATE 1, COLLPORT 1, RF_LOCAL 1, RSYNC 1, STRAP 1), serial 4 / stream 3 quanta.
// Region roots ck_r0..3 = the serial clock (one lattice; the landing rings make the result independent of the phase).
//  LOCKSTEP under random traffic on every input, NRST resets, P0 = (Q0 G2, PRETREE 1), P1 = (Q3 G3, PRETREE 0).
//  The DUT gets the compiler re-timed calendar: red_sel, tree_cmd and rf_dsec (RF class 5) RT serial edges later.
//  Every output equals the flat slice's at a FIXED offset:
//    serial: slice_x, inj_q, tree_o +RT; fault +RT+1          stream: s_rq (VM read request), lg_rq, far_rr, far_w_done,
//    lg_fault +0; s_wq (VM write, the tap's local side) +SWQ stream edges (= RT + alignment serial edges at 3:4).
//  Class check: a wrong-class strap latches the DUT fault (ref clean).
// MUT (DUT only, must FAIL): 1 fill early; 2 drain group flip; 4 RF select early; 10 delivery order; 11 strap g ignored;
//  20 outer chain relay missing; 21 drain delay line short; 22 R2 inbound unlanded.
module tb_hbm_su_pgslice_rg;
 parameter integer MUT=0, NRST=2, EDGES=1200, LK=1;
 localparam integer A=LK+1, RT=(2*A+1)+2*A+1, SWQ=((RT+2)/3)*4;    // RT 10, VM write 12 serial = 16 stream edges
 localparam integer TS=1200, TP=900, T0=600;
 reg sclk=0, pclk=0;
 initial begin #(T0); forever begin sclk=1; #(TS/2); sclk=0; #(TS/2); end end
 initial begin #(T0); forever begin pclk=1; #(TP/2); pclk=0; #(TP/2); end end
 reg por=0, brst=0, active=0;
 reg [1741:0] control; reg [59:0] vmr; reg [77:0] vmw; reg [127:0] rfw; reg [35:0] rfc; reg [255:0] rfd; reg [11:0] rsel;
 reg [11:0] tcmd;
 reg [1:0] dwv; reg [17:0] dwr; reg [1023:0] dwd;
 reg [513:0] lgrr; reg [1:0] lgwd, lgr, lgw, injrd; reg [33:0] farrq; reg [561:0] farwq; reg [159:0] inja;
 reg [3:0] pos0={2'd0,2'd2}, pos1={2'd3,2'd3};
 function automatic [1023:0] rnd1024(input integer dummy); integer i; begin
  for(i=0;i<32;i=i+1) rnd1024[i*32+:32]=$urandom; end endfunction
 task automatic quiet; begin
  control=0; vmr=0; vmw=0; rfw=0; rfc=0; rfd=0; rsel=0; tcmd=0; dwv=0; dwr=0; dwd=0;
  lgrr=0; lgwd=0; lgr=0; lgw=0; injrd=0; farrq=0; farwq=0; inja=0; end endtask
 initial quiet;
 always @(negedge sclk) if(active) begin
  control={rnd1024(0),rnd1024(0)}; vmr={$urandom,$urandom}; vmw={$urandom,$urandom,$urandom};
  rfw={$urandom,$urandom,$urandom,$urandom}; rfc={$urandom,$urandom}; rfd=rnd1024(0); rsel=$urandom; tcmd=$urandom;
  dwv=$urandom; dwr=$urandom; dwd=rnd1024(0);
 end
 always @(negedge pclk) if(active) begin
  lgrr={rnd1024(0)}; lgwd=$urandom; lgr=$urandom; lgw=$urandom; injrd=$urandom; inja={$urandom,$urandom,$urandom,$urandom,$urandom};
  farrq={$urandom,$urandom}; farwq=rnd1024(0);
 end
 // compiler re-timing of the DUT calendar: red_sel / tree_cmd / rf_dsec RT serial edges later
 reg [11:0] dl_rsel [0:RT-1]; reg [11:0] dl_tcmd [0:RT-1]; reg [255:0] dl_rfd [0:RT-1]; integer di;
 initial for(di=0;di<RT;di=di+1) begin dl_rsel[di]=0; dl_tcmd[di]=0; dl_rfd[di]=0; end
 always @(posedge sclk) begin
  #2; for(di=RT-1;di>0;di=di-1) begin dl_rsel[di]=dl_rsel[di-1]; dl_tcmd[di]=dl_tcmd[di-1]; dl_rfd[di]=dl_rfd[di-1]; end
  dl_rsel[0]=rsel; dl_tcmd[0]=tcmd; dl_rfd[0]=rfd;
 end
 wire [11:0] rsel_d=dl_rsel[RT-1], tcmd_d=dl_tcmd[RT-1]; wire [255:0] rfd_d=dl_rfd[RT-1];
 `define PGF(NAME,PS,PT) \
 wire [31:0] NAME``_sx; wire [66:0] NAME``_to; wire [1023:0] NAME``_iq; wire NAME``_f, NAME``_lf; wire [33:0] NAME``_rq; \
 wire [561:0] NAME``_wq; wire [513:0] NAME``_frr; wire [1:0] NAME``_fwd; \
 ot_hbm_su_static_pgslice_lg #(.QID(1),.G(2),.MLAT(4),.ALAT(3),.LEAF(1),.FETCH_EXTRA_EDGES(2),.MULTIRATE(1),.COLLPORT(1), \
  .RF_LOCAL(1),.PIN_REG(1),.RSYNC(1),.STRAP(1),.PRETREE(PT),.MUT(0)) NAME( \
  .pg_clk(pclk),.clk_lane({256{sclk}}),.clk_insert({128{sclk}}),.rst_lane_n({32{por}}),.clk_bcast({4{sclk}}), \
  .rst_bcast_n({4{por}}),.clk_bank({32{sclk}}),.clk_bank_macro({192{sclk}}),.clk_ctl(sclk),.clk_side({6{sclk}}), \
  .rst_n(por),.pos(PS),.bridge_rst_n(brst),.control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_bword(rfw),.rf_bcmd(rfc), \
  .rf_dsec(rfd),.red_sel(rsel),.slice_x(NAME``_sx),.tree_cmd(tcmd),.tree_o(NAME``_to),.inj_rd(injrd),.inj_addr(inja), \
  .inj_q(NAME``_iq),.dw_v(dwv),.dw_row(dwr),.dw_d(dwd),.fault(NAME``_f),.lg_rq(NAME``_rq),.lg_wq(NAME``_wq),.lg_rr(lgrr), \
  .lg_w_done(lgwd),.lg_read(lgr),.lg_write(lgw),.far_rq(farrq),.far_wq(farwq),.far_rr(NAME``_frr),.far_w_done(NAME``_fwd), \
  .lg_fault(NAME``_lf));
 `define PGR(NAME,PS,PT,MM) \
 wire [31:0] NAME``_sx; wire [66:0] NAME``_to; wire [1023:0] NAME``_iq; wire NAME``_f, NAME``_lf; wire [33:0] NAME``_rq; \
 wire [561:0] NAME``_wq; wire [513:0] NAME``_frr; wire [1:0] NAME``_fwd; \
 ot_hbm_su_static_pgslice_rg #(.QID(1),.G(2),.MLAT(4),.ALAT(3),.LEAF(1),.FETCH_EXTRA_EDGES(2),.MULTIRATE(1),.COLLPORT(1), \
  .RF_LOCAL(1),.PIN_REG(1),.RSYNC(1),.STRAP(1),.PRETREE(PT),.MUT(MM)) NAME( \
  .clk_ctl(sclk),.ck_r0(sclk),.ck_r1(sclk),.ck_r2(sclk),.ck_r3(sclk),.pg_clk(pclk), \
  .rst_n(por),.pos(PS),.bridge_rst_n(brst),.control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_bword(rfw),.rf_bcmd(rfc), \
  .rf_dsec(rfd_d),.red_sel(rsel_d),.slice_x(NAME``_sx),.tree_cmd(tcmd_d),.tree_o(NAME``_to),.inj_rd(injrd),.inj_addr(inja), \
  .inj_q(NAME``_iq),.dw_v(dwv),.dw_row(dwr),.dw_d(dwd),.fault(NAME``_f),.lg_rq(NAME``_rq),.lg_wq(NAME``_wq),.lg_rr(lgrr), \
  .lg_w_done(lgwd),.lg_read(lgr),.lg_write(lgw),.far_rq(farrq),.far_wq(farwq),.far_rr(NAME``_frr),.far_w_done(NAME``_fwd), \
  .lg_fault(NAME``_lf));
 `PGF(ref0,pos0,1)
 `PGR(dut0,pos0,1,MUT)
 wire [33:0] ref0_srq=ref0.s_rq, dut0_srq=dut0.u_stream.s_rq; wire [561:0] ref0_swq=ref0.s_wq, dut0_swq=dut0.u_stream.s_wq;
 `ifdef PG_RG_P1
 `PGF(ref1,pos1,0)
 `PGR(dut1,pos1,0,MUT)
 wire [33:0] ref1_srq=ref1.s_rq, dut1_srq=dut1.u_stream.s_rq; wire [561:0] ref1_swq=ref1.s_wq, dut1_swq=dut1.u_stream.s_wq;
 `else
 // one position by default (Verilator memory: 2 instances x 64 hard-child models); +define+PG_RG_P1 adds (Q3 G3, PRETREE 0)
 wire [31:0] ref1_sx=ref0_sx, dut1_sx=dut0_sx; wire [66:0] ref1_to=ref0_to, dut1_to=dut0_to;
 wire [1023:0] ref1_iq=ref0_iq, dut1_iq=dut0_iq; wire ref1_f=ref0_f, dut1_f=dut0_f, ref1_lf=ref0_lf, dut1_lf=dut0_lf;
 wire [33:0] ref1_rq=ref0_rq, dut1_rq=dut0_rq; wire [513:0] ref1_frr=ref0_frr, dut1_frr=dut0_frr;
 wire [1:0] ref1_fwd=ref0_fwd, dut1_fwd=dut0_fwd;
 wire [33:0] ref1_srq=ref0_srq, dut1_srq=dut0_srq; wire [561:0] ref1_swq=ref0_swq, dut1_swq=dut0_swq;
 `endif
 // ---------------------------------------------------------------- history of the reference + fixed-offset compare
 localparam integer HN=64;
 wire [1123:0] sr_ref0={ref0_sx,ref0_iq,ref0_to}, sr_dut0={dut0_sx,dut0_iq,dut0_to};
 wire [1123:0] sr_ref1={ref1_sx,ref1_iq,ref1_to}, sr_dut1={dut1_sx,dut1_iq,dut1_to};
 wire [584:0] p0_ref0={ref0_rq,ref0_srq,ref0_frr,ref0_fwd,ref0_lf}, p0_dut0={dut0_rq,dut0_srq,dut0_frr,dut0_fwd,dut0_lf};
 wire [584:0] p0_ref1={ref1_rq,ref1_srq,ref1_frr,ref1_fwd,ref1_lf}, p0_dut1={dut1_rq,dut1_srq,dut1_frr,dut1_fwd,dut1_lf};
 reg [1123:0] hs0 [0:HN-1], hs1 [0:HN-1]; reg hf0 [0:HN-1], hf1 [0:HN-1]; reg hsv [0:HN-1];
 reg [584:0] hp0 [0:HN-1], hp1 [0:HN-1]; reg [561:0] hw0 [0:HN-1], hw1 [0:HN-1]; reg hpv [0:HN-1];
 integer ks=0, kp=0, checks=0, errors=0, data_seen=0, wq_seen=0, ref_faults=0, e_ser=0, e_flt=0, e_str=0, e_wq=0;
 reg cmp=0;                     // reference samples inside the compare window
 reg cmpd=0;                    // DUT side may be compared (cleared at the reset assertion)
 task automatic mism(input [8*24-1:0] what, input integer p); begin
  errors=errors+1; if(errors<10) $display("LOCKSTEP MISMATCH %0s P%0d t=%0t ks=%0d kp=%0d", what, p, $time, ks, kp); end endtask
 always @(posedge sclk) begin
  #1;
  hs0[ks%HN]=sr_ref0; hs1[ks%HN]=sr_ref1; hf0[ks%HN]=ref0_f; hf1[ks%HN]=ref1_f; hsv[ks%HN]=cmp;
  if(cmp && (|ref0_sx || |ref0_iq || |ref1_sx)) data_seen=data_seen+1;
  if(cmp && ref0_f) ref_faults=ref_faults+1;
  if(cmpd && ks>=RT+1) begin
   if(hsv[(ks-RT)%HN]) begin
    checks=checks+2;
    if(sr_dut0!==hs0[(ks-RT)%HN]) begin e_ser=e_ser+1; mism("serial(sx/iq/to)",0); end
    if(sr_dut1!==hs1[(ks-RT)%HN]) begin e_ser=e_ser+1; mism("serial(sx/iq/to)",1); end
   end
   if(hsv[(ks-RT-1)%HN]) begin
    checks=checks+2;
    if(dut0_f!==hf0[(ks-RT-1)%HN]) begin e_flt=e_flt+1; mism("fault",0); end
    if(dut1_f!==hf1[(ks-RT-1)%HN]) begin e_flt=e_flt+1; mism("fault",1); end
   end
  end
  ks=ks+1;
 end
 always @(posedge pclk) begin
  #1;
  hp0[kp%HN]=p0_ref0; hp1[kp%HN]=p0_ref1; hw0[kp%HN]=ref0_swq; hw1[kp%HN]=ref1_swq; hpv[kp%HN]=cmp;
  if(cmp && (ref0_swq[280] || ref0_swq[561])) wq_seen=wq_seen+1;
  if(cmpd && kp>=SWQ) begin
   if(hpv[kp%HN]) begin
    checks=checks+2;
    if(p0_dut0!==p0_ref0) begin e_str=e_str+1; mism("stream(rq/far/lg_fault)",0); end
    if(p0_dut1!==p0_ref1) begin e_str=e_str+1; mism("stream(rq/far/lg_fault)",1); end
   end
   if(hpv[(kp-SWQ)%HN]) begin
    checks=checks+2;
    if(dut0_swq!==hw0[(kp-SWQ)%HN]) begin e_wq=e_wq+1; mism("s_wq (VM write)",0); end
    if(dut1_swq!==hw1[(kp-SWQ)%HN]) begin e_wq=e_wq+1; mism("s_wq (VM write)",1); end
   end
  end
  kp=kp+1;
 end
 integer r, k, class_ok=0;
 initial begin
  if(!$value$plusargs("NRST=%d", r)) r=NRST;
  $display("PGSLICE_RG bench MUT=%0d LK=%0d RT=%0d SWQ=%0d EDGES=%0d", MUT, LK, RT, SWQ, EDGES);
  repeat(5) @(negedge sclk);
  por=1; repeat(3) @(negedge sclk); por=0;
  for(k=0;k<r;k=k+1) begin
   repeat(16+k) @(negedge sclk);                       // reset window > the deepest pad (RT+1): no stale pad state
   por=1; repeat(2) @(negedge pclk); brst=1;
   repeat(12) @(negedge sclk);
   cmp=1; cmpd=1; active=1;
   repeat(EDGES) @(negedge sclk);
   active=0; quiet;
   repeat(48) @(negedge sclk);                         // drain the in-flight calendar (lanes, fill, landings)
   cmp=0; repeat(RT+4) @(negedge sclk); cmpd=0;
   por=0; brst=0;
  end
  repeat(16) @(negedge sclk); por=1; repeat(2) @(negedge pclk); brst=1; repeat(40) @(negedge sclk);
  if(dut0_f!==1'b0 || ref0_f!==1'b0) $display("CLASS PRECHECK: quiet fault dut0/ref0 %b/%b", dut0_f, ref0_f);
  else begin
   pos0={2'd0,2'd0}; repeat(RT+6) @(negedge sclk);
   if(dut0_f===1'b1) class_ok=1;
   else $display("CLASS CHECK FAIL: wrong-class strap fault dut0 %b", dut0_f);
  end
  $display("PGSLICE_RG errors serial=%0d fault=%0d stream=%0d vm_write=%0d", e_ser, e_flt, e_str, e_wq);
  if(errors==0 && class_ok && checks>8*r*EDGES && data_seen>r*EDGES/4 && wq_seen>0)
   $display("PGSLICE_RG PASS checks=%0d resets=%0d data_edges=%0d vm_writes=%0d ref_fault_edges=%0d", checks, r, data_seen, wq_seen, ref_faults);
  else $display("PGSLICE_RG FAIL errors=%0d class_ok=%0d checks=%0d data_edges=%0d vm_writes=%0d", errors, class_ok, checks, data_seen, wq_seen);
  $finish;
 end
endmodule
`default_nettype wire
