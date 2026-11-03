// DIE-HBM-61/RTL-TAILX 11-03: RE-FORM ot_hbm_hc_tail_rest_core_ce (REFORM=1, CAP 299 = wave wrapper form).
// Three instances, same launch/data inputs:
//   gold = pre-RE-FORM committed RTL (origin/main, renamed gold_*);  dut = REFORM 1;  ref = REFORM 1 with the
//   combinational phase/index (REFORM_COMB 1, bench only).  dut and ref get the sink-side inputs delayed by SH.
// DECLARED cycle map (physical/die_plan/hbm/reform_1103/cycles/tailx_rest.tsv), checked in phase A (clean schedules):
//   dut result_v / result / sk_in_valid (t+SH) == gold (t); dut sk_in_e (t+SH) == gold sk_in_e (t) on sk_in_valid;
//   sk_en_sk +0; fault: dut never earlier than gold, and dut fault (t+SH) == gold fault (t) on every result_v.
// dut vs ref: every output, every edge, all phases (A, directed launch-on-capture, chaos B).
`timescale 1ns/1ps
`ifndef SEED
`define SEED 20261103
`endif
`ifndef SH
`define SH 70
`endif
module tb;
localparam integer SH=`SH;
reg clk=0,rst_n=0,launch=0; always #5 clk=~clk;
reg [767:0] mixes,bases; reg [95:0] scales;
reg sk_in_ready=1,sk_out_valid=0,sk_fault=0; reg [511:0] sk_y=0;
reg [514:0] skq [0:SH-1]; wire [514:0] skd=skq[SH-1];
integer q; always @(posedge clk) begin for(q=SH-1;q>0;q=q-1) skq[q]<=skq[q-1]; skq[0]<={sk_in_ready,sk_out_valid,sk_fault,sk_y}; end
wire dr_rdy=skd[514], dr_ov=skd[513], dr_f=skd[512]; wire [511:0] dr_y=skd[511:0];
wire gv,dv,rv,gf,df,rf_,ge,de,re,gs,ds,rs; wire [767:0] gr,dr,rr; wire [511:0] gi,di,ri;
gold_rest_core_ce #(.CAP(299)) gold(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),
  .result_v(gv),.result(gr),.fault(gf),.sk_en_sk(ge),.sk_in_valid(gs),.sk_in_e(gi),.sk_in_ready(sk_in_ready),.sk_out_valid(sk_out_valid),.sk_fault(sk_fault),.sk_y(sk_y));
ot_hbm_hc_tail_rest_core_ce #(.CAP(299)) dut(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),
  .result_v(dv),.result(dr),.fault(df),.sk_en_sk(de),.sk_in_valid(ds),.sk_in_e(di),.sk_in_ready(dr_rdy),.sk_out_valid(dr_ov),.sk_fault(dr_f),.sk_y(dr_y));
ot_hbm_hc_tail_rest_core_ce #(.CAP(299),.REFORM_COMB(1)) rfm(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),
  .result_v(rv),.result(rr),.fault(rf_),.sk_en_sk(re),.sk_in_valid(rs),.sk_in_e(ri),.sk_in_ready(dr_rdy),.sk_out_valid(dr_ov),.sk_fault(dr_f),.sk_y(dr_y));
reg [1+768+1+512+1-1:0] gq [0:SH-1]; wire [1282:0] gd=gq[SH-1];   // {gv,gr,gs,gi,gf} delayed SH
wire gdv=gd[1282]; wire [767:0] gdr=gd[1281:514]; wire gds=gd[513]; wire [511:0] gdi=gd[512:1]; wire gdf=gd[0];
always @(posedge clk) begin for(q=SH-1;q>0;q=q-1) gq[q]<=gq[q-1]; gq[0]<={gv,gr,gs,gi,gf}; end
integer seed=`SEED, checks=0, gerr=0, rerr=0, results=0, nzres=0, skchecks=0, prio=0, k, f, j;
reg gold_on=0;
reg [31:0] tie[0:7]; initial begin tie[0]=32'h0;tie[1]=32'h80000000;tie[2]=32'h3f800000;tie[3]=32'hbf800000;
  tie[4]=32'h7fc00000;tie[5]=32'hffc00000;tie[6]=32'h3f800000;tie[7]=32'h40000000; end
function [31:0] rnd(input integer mode); reg [31:0] r; begin r=$random(seed);
  if(mode==0) rnd={r[31],8'(8'd118+($unsigned(r[30:23])%20)),r[22:0]}; else if(mode==2) rnd=tie[r[2:0]];
  else if(mode==3) rnd={r[31],8'(8'd124+($unsigned(r[30:23])%4)),r[22:4],4'd0}; else rnd=r; end endfunction
task randin(input integer mode); begin
  for(j=0;j<24;j=j+1) begin mixes[j*32+:32]=rnd(mode); bases[j*32+:32]=rnd(mode); end
  for(j=0;j<3;j=j+1) scales[j*32+:32]=rnd(mode); end endtask
task ge_(input [8*16-1:0] w); begin gerr=gerr+1; if(gerr<6) $display("GOLD-DIFF %0s t=%0t",w,$time); end endtask
always @(negedge clk) if(rst_n) begin checks=checks+1;
  if({rv,rr,rf_,re,rs,ri}!=={dv,dr,df,de,ds,di}) begin rerr=rerr+1; if(rerr<6) $display("REF-DIFF t=%0t v%b/%b f%b/%b s%b/%b",$time,rv,dv,rf_,df,rs,ds); end
  if(gold_on) begin
    if({gdv,gds}!=={dv,ds}) ge_("ctl");
    if(gdr!==dr) ge_("result");
    if(ge!==de) ge_("sk_en");
    if(gds) begin skchecks=skchecks+1; if(gdi!==di) ge_("sk_in_e"); end
    if(df&&!gf) ge_("fault_early");
    if(gdv&&(gdf!==df)) ge_("fault_at_result");
    if(gdv) begin results=results+1; if(|gdr) nzres=nzres+1; end
  end
end
always @(posedge clk) if(gs) sk_y <= {16{rnd(0)}} ^ {$random(seed),$random(seed),$random(seed),$random(seed),448'd0};
initial begin
  if(dut.SKL-198!=SH || dut.TE!=dut.u_tail.EREADY || dut.SKL<dut.u_tail.EREADY+1 || (SH%7)!=0) begin
    $display("SCHED SKL=%0d TE=%0d EREADY=%0d SH=%0d",dut.SKL,dut.TE,dut.u_tail.EREADY,SH); $fatal(1,"TAILX_REFORM FAIL schedule constants"); end
  randin(0); repeat(3) @(negedge clk); #1 rst_n=1; repeat(SH+2) @(negedge clk); #1 gold_on=1;
  // phase A: 50 clean schedules, 640-edge spacing (dut L = SKL+SDIV+CAP+2 = 576), value classes incl. max4 ties
  for(f=0;f<50;f=f+1) begin
    randin(f%5==4 ? 1 : f%5==3 ? 2 : f%5==2 ? 3 : 0); launch=1; @(negedge clk); #1 launch=0;
    for(k=0;k<640;k=k+1) begin sk_out_valid=(k>=200); sk_fault=(f==7&&k==300); sk_in_ready=!(f==11&&k<260); @(negedge clk); #1; end
    sk_out_valid=0;
  end
  repeat(SH+2) @(negedge clk); #1 gold_on=0;
  // phase A2 (dut vs ref): launch on the dut sink-capture edge (control priority), 8 schedules
  sk_out_valid=1;
  for(f=0;f<8;f=f+1) begin
    randin(f%2 ? 2 : 0); launch=1; @(negedge clk); #1 launch=0;
    while(!dut.capture_q) begin @(negedge clk); #1; end
    randin(0); launch=1; prio=prio+1; @(negedge clk); #1 launch=0;
    for(k=0;k<640;k=k+1) begin @(negedge clk); #1; end
  end
  // phase B (dut vs ref): random chaos (relaunch mid-schedule, resets, sink faults)
  for(k=0;k<40000;k=k+1) begin @(negedge clk); #1;
    rst_n=($unsigned($random(seed))%997!=0);
    launch=($unsigned($random(seed))%251==0); if(launch) randin($unsigned($random(seed))%4);
    sk_out_valid=($unsigned($random(seed))%3!=0); sk_fault=($unsigned($random(seed))%4001==0);
    sk_in_ready=($unsigned($random(seed))%50!=0);
  end
  $display("TAILX_REFORM checks=%0d gold_errors=%0d ref_errors=%0d results=%0d nonzero=%0d sk_checks=%0d prio=%0d SH=%0d",checks,gerr,rerr,results,nzres,skchecks,prio,SH);
  if(gerr!=0||rerr!=0||results<50) $fatal(1,"TAILX_REFORM FAIL");
  $display("TAILX_REFORM PASS"); $finish;
end
endmodule
