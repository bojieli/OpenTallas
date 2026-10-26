`timescale 1ps/1ps
`default_nettype none
// TOK-HBM-SUV 2026-10-26: SU Q0 slice vehicle lock-step.  DUT = suv_su_asm_<k> (su_slice_vehicle.py: the B2n q_su00+q_su01
// hard cores composed into the slice glue, strap pins tied to die_plan.json values); REF = the unsplit twin
// ot_hbm_su_static_pgslice_lg_s at the plan parameters (QID 0, G 0, d4g MLAT 4 ALAT 3 LEAF 1, MULTIRATE 1, COLLPORT 1,
// RF_LOCAL 1, PIN_REG 1, RSYNC 1, PRETREE 1).  Stimulus = tb_hbm_su_pgslice_lg_s (random traffic on every input incl.
// tree_cmd, serial 4 / stream 3 quanta lattice, NRST power-on resets x EDGES serial edges).  EVERY output bit incl. the
// sticky fault and tree_o must be equal (!==) at every serial and stream edge (the composition is pure wiring: 0 edges).
module tb_suv_slice;
 parameter integer NRST=3, EDGES=1500;
 localparam integer TS=1200, TP=900, T0=600;
 reg sclk=0, pclk=0;
 initial begin #(T0); forever begin sclk=1; #(TS/2); sclk=0; #(TS/2); end end
 initial begin #(T0); forever begin pclk=1; #(TP/2); pclk=0; #(TP/2); end end
 reg por=0, brst=0, active=0;
 reg [1741:0] control; reg [59:0] vmr; reg [77:0] vmw; reg [127:0] rfw; reg [35:0] rfc; reg [255:0] rfd; reg [11:0] rsel;
 reg [1:0] dwv; reg [17:0] dwr; reg [1023:0] dwd; reg [11:0] tcmd;
 reg [513:0] lgrr; reg [1:0] lgwd, lgr, lgw, injrd; reg [33:0] farrq; reg [561:0] farwq; reg [159:0] inja;
 function automatic [1023:0] rnd1024(input integer dummy); integer i; begin
  for(i=0;i<32;i=i+1) rnd1024[i*32+:32]=$urandom; end endfunction
 task automatic quiet; begin
  control=0; vmr=0; vmw=0; rfw=0; rfc=0; rfd=0; rsel=0; dwv=0; dwr=0; dwd=0; tcmd=0;
  lgrr=0; lgwd=0; lgr=0; lgw=0; injrd=0; farrq=0; farwq=0; inja=0; end endtask
 initial quiet;
 always @(negedge sclk) if(active) begin
  control={rnd1024(0),rnd1024(0)}; vmr={$urandom,$urandom}; vmw={$urandom,$urandom,$urandom};
  rfw={$urandom,$urandom,$urandom,$urandom}; rfc={$urandom,$urandom}; rfd=rnd1024(0); rsel=$urandom;
  dwv=$urandom; dwr=$urandom; dwd=rnd1024(0); tcmd=$urandom;
 end
 always @(negedge pclk) if(active) begin
  lgrr={rnd1024(0)}; lgwd=$urandom; lgr=$urandom; lgw=$urandom; injrd=$urandom; inja={$urandom,$urandom,$urandom,$urandom,$urandom};
  farrq={$urandom,$urandom}; farwq=rnd1024(0);
 end
 `define PGS(NAME,MOD,PRM) \
 wire [31:0] NAME``_sx; wire [1023:0] NAME``_iq; wire NAME``_f, NAME``_lf; wire [33:0] NAME``_rq; wire [561:0] NAME``_wq; \
 wire [513:0] NAME``_frr; wire [1:0] NAME``_fwd; wire [66:0] NAME``_to; \
 MOD PRM NAME( \
  .pg_clk(pclk),.clk_lane({256{sclk}}),.clk_insert({128{sclk}}),.rst_lane_n({32{por}}),.clk_bcast({4{sclk}}), \
  .rst_bcast_n({4{por}}),.clk_bank({32{sclk}}),.clk_bank_macro({192{sclk}}),.clk_ctl(sclk),.clk_side({6{sclk}}), \
  .rst_n(por),.bridge_rst_n(brst),.control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_bword(rfw),.rf_bcmd(rfc), \
  .rf_dsec(rfd),.red_sel(rsel),.slice_x(NAME``_sx),.inj_rd(injrd),.inj_addr(inja),.inj_q(NAME``_iq),.dw_v(dwv), \
  .dw_row(dwr),.dw_d(dwd),.fault(NAME``_f),.lg_rq(NAME``_rq),.lg_wq(NAME``_wq),.lg_rr(lgrr),.lg_w_done(lgwd), \
  .lg_read(lgr),.lg_write(lgw),.far_rq(farrq),.far_wq(farwq),.far_rr(NAME``_frr),.far_w_done(NAME``_fwd), \
  .lg_fault(NAME``_lf),.tree_cmd(tcmd),.tree_o(NAME``_to));
 `PGS(dut,`SUV_DUT,)
 `PGS(ref0,ot_hbm_su_static_pgslice_lg_s,#(.SMUT(0),.QID(0),.G(0),.MLAT(4),.ALAT(3),.LEAF(1),.MULTIRATE(1),.COLLPORT(1),.RF_LOCAL(1),.PIN_REG(1),.RSYNC(1),.PRETREE(1)))
 wire [2264:0] o_dut={dut_sx,dut_iq,dut_rq,dut_wq,dut_frr,dut_fwd,dut_lf,dut_f,dut_to};
 wire [2264:0] o_ref={ref0_sx,ref0_iq,ref0_rq,ref0_wq,ref0_frr,ref0_fwd,ref0_lf,ref0_f,ref0_to};
 integer checks=0, errors=0, cmp=0, nz=0, nzt=0, sedges=0, nf=0;
 always @(posedge sclk) if(cmp) sedges=sedges+1;
 always @(posedge sclk or posedge pclk) if(cmp) begin
  #1; checks=checks+1;
  if(o_dut!==o_ref) begin errors=errors+1; if(errors<6) $display("SUV MISMATCH t=%0t slice_x %h/%h fault %b/%b tree_o %h/%h inj_q0 %h/%h", $time, dut_sx, ref0_sx, dut_f, ref0_f, dut_to, ref0_to, dut_iq[31:0], ref0_iq[31:0]); end
  if(|o_ref) nz=nz+1; if(|ref0_to) nzt=nzt+1; if(ref0_f) nf=nf+1;
 end
 integer r, k;
 initial begin
  if(!$value$plusargs("NRST=%d", r)) r=NRST;
  repeat(5) @(negedge sclk);
  por=1; repeat(3) @(negedge sclk); por=0;
  for(k=0;k<r;k=k+1) begin
   repeat(6+k) @(negedge sclk);
   por=1; repeat(2) @(negedge pclk); brst=1;
   repeat(8) @(negedge sclk);
   cmp=1; active=1;
   repeat(EDGES) @(negedge sclk);
   active=0; quiet; cmp=0; @(negedge sclk);
   por=0; brst=0;
  end
  repeat(6) @(negedge sclk);
  if(errors==0 && checks>r*EDGES) $display("SUV_SLICE PASS checks=%0d serial_cycles=%0d nonzero_out_edges=%0d nonzero_tree_o_edges=%0d fault_edges=%0d resets=%0d", checks, sedges, nz, nzt, nf, r);
  else $display("SUV_SLICE FAIL errors=%0d checks=%0d serial_cycles=%0d resets=%0d", errors, checks, sedges, r);
  $finish;
 end
endmodule
`default_nettype wire
