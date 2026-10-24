`timescale 1ps/1ps
`default_nettype none
// HBM-P5-RTLB 10-23: over-cap split twin ot_hbm_su_static_pgslice_lg_s (PIN_REG 1 plan variant + side split
// side_softplus | side_rest) against the PINNED ot_hbm_su_static_pgslice_lg at PIN_REG 1, same QID/G, RSYNC 1, die d4g
// parameters (MLAT 4, ALAT 3, LEAF 1, MULTIRATE 1, COLLPORT 1, RF_LOCAL 1); derived from tb_hbm_su_pgslice_lg_rsync
// (random traffic on every input, serial 4 / stream 3 quanta lattice, NRST resets x EDGES serial edges).
//  LOCKSTEP: every output bit except the sticky slice fault (slice_x, inj_q, lg_rq, lg_wq, far_rr, far_w_done,
//  lg_fault) equal (!==) at every serial and stream edge: the cut costs 0 data edges.
//  FAULT: the slice's sticky fault may rise at most ONE serial edge later than the pinned one (the side_softplus fault
//  pin register): dut_f -> ref_f, and ref_f at the previous compare edge -> dut_f.
// SMUT (twin's side mutant): 1 = y_sp delayed one edge without re-alignment -> LOCKSTEP FAILS (Q0G0 only).
module tb_hbm_su_pgslice_lg_s;
 parameter integer SMUT=0, QID=0, G=0, NRST=3, EDGES=1500;
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
 `define PGS(NAME,MOD,EXTRA) \
 wire [31:0] NAME``_sx; wire [1023:0] NAME``_iq; wire NAME``_f, NAME``_lf; wire [33:0] NAME``_rq; wire [561:0] NAME``_wq; \
 wire [513:0] NAME``_frr; wire [1:0] NAME``_fwd; \
 MOD #(EXTRA,.QID(QID),.G(G),.MLAT(4),.ALAT(3),.LEAF(1),.MULTIRATE(1),.COLLPORT(1),.RF_LOCAL(1), \
  .PIN_REG(1),.RSYNC(1)) NAME( \
  .pg_clk(pclk),.clk_lane({256{sclk}}),.clk_insert({128{sclk}}),.rst_lane_n({32{por}}),.clk_bcast({4{sclk}}), \
  .rst_bcast_n({4{por}}),.clk_bank({32{sclk}}),.clk_bank_macro({192{sclk}}),.clk_ctl(sclk),.clk_side({6{sclk}}), \
  .rst_n(por),.bridge_rst_n(brst),.control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_bword(rfw),.rf_bcmd(rfc), \
  .rf_dsec(rfd),.red_sel(rsel),.slice_x(NAME``_sx),.inj_rd(injrd),.inj_addr(inja),.inj_q(NAME``_iq),.dw_v(dwv), \
  .dw_row(dwr),.dw_d(dwd),.fault(NAME``_f),.lg_rq(NAME``_rq),.lg_wq(NAME``_wq),.lg_rr(lgrr),.lg_w_done(lgwd), \
  .lg_read(lgr),.lg_write(lgw),.far_rq(farrq),.far_wq(farwq),.far_rr(NAME``_frr),.far_w_done(NAME``_fwd), \
  .lg_fault(NAME``_lf));
 `PGS(dut,ot_hbm_su_static_pgslice_lg_s,.SMUT(SMUT))
 `PGS(ref0,ot_hbm_su_static_pgslice_lg,.MUT(0))
 wire [2195:0] o_dut={dut_sx,dut_iq,dut_rq,dut_wq,dut_frr,dut_fwd,dut_lf};
 wire [2195:0] o_ref={ref0_sx,ref0_iq,ref0_rq,ref0_wq,ref0_frr,ref0_fwd,ref0_lf};
 reg ref_f_prev=0; integer nz=0, fchk=0;
 integer checks=0, errors=0, cmp=0;
 always @(posedge sclk or posedge pclk) if(cmp) begin
  #1; checks=checks+1;
  if(o_dut!==o_ref) begin errors=errors+1; if(errors<6) $display("LOCKSTEP MISMATCH t=%0t slice_x %h/%h", $time, dut_sx, ref0_sx); end
  if(|o_ref) nz=nz+1;
 end
 always @(posedge sclk) if(cmp) begin
  #1; fchk=fchk+1;
  if((dut_f===1'b1 && ref0_f!==1'b1) || (ref_f_prev===1'b1 && dut_f!==1'b1)) begin errors=errors+1;
   if(errors<6) $display("FAULT RELATION FAIL t=%0t dut %b ref %b ref_prev %b", $time, dut_f, ref0_f, ref_f_prev); end
  ref_f_prev=ref0_f;
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
   active=0; quiet; cmp=0; ref_f_prev=0; @(negedge sclk);
   por=0; brst=0;
  end
  repeat(6) @(negedge sclk);
  if(errors==0 && checks>r*EDGES) $display("PGSLICE_LG_S PASS checks=%0d nonzero_out_edges=%0d fault_checks=%0d resets=%0d QID=%0d G=%0d SMUT=%0d", checks, nz, fchk, r, QID, G, SMUT);
  else $display("PGSLICE_LG_S FAIL errors=%0d checks=%0d QID=%0d G=%0d SMUT=%0d", errors, checks, QID, G, SMUT);
  $finish;
 end
endmodule
`default_nettype wire
