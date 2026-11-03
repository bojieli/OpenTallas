// DIE-HBM-61/RTL-TAILX 11-03: lockstep of the RE-FORM ot_hbm_hc_tail_rest_core_ce (REFORM=`DUTR, CAP 299 = wave
// wrapper form) against the pre-RE-FORM committed RTL (origin/main 08542fa9d7d, renamed gold_*).
// DECLARED cycle map (cycles.tsv): result_v, sk_in_valid, sk_en_sk exact every edge (+0); result exact every edge
// (+0); sk_in_e exact on every sk_in_valid edge (+0; between sink launches it is internal state, not a contract);
// fault: never earlier than gold and at most FLAG_LAG=3 edges later (unit errors surface after the operand
// register; P3 add errors after the MAX/P3 shift), identical once settled.
// Phase A (clean schedules + directed launch-at-capture) is checked strictly; phase B chaos (relaunch/reset mid
// schedule, which the core itself flags as fault) checks result/sk_in_e only while gold fault == 0.
`timescale 1ns/1ps
`ifndef DUTR
`define DUTR 1
`endif
`ifndef SEED
`define SEED 20261103
`endif
module tb;
reg clk=0,rst_n=0,launch=0; always #5 clk=~clk;
reg [767:0] mixes,bases; reg [95:0] scales;
reg sk_in_ready=1,sk_out_valid=0,sk_fault=0; reg [511:0] sk_y=0;
wire gv,dv,gf,df,ge,de,gs,ds; wire [767:0] gr,dr; wire [511:0] gi,di;
gold_rest_core_ce #(.CAP(299)) gold(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),
  .result_v(gv),.result(gr),.fault(gf),.sk_en_sk(ge),.sk_in_valid(gs),.sk_in_e(gi),.sk_in_ready(sk_in_ready),.sk_out_valid(sk_out_valid),.sk_fault(sk_fault),.sk_y(sk_y));
ot_hbm_hc_tail_rest_core_ce #(.CAP(299),.REFORM(`DUTR)) dut(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),
  .result_v(dv),.result(dr),.fault(df),.sk_en_sk(de),.sk_in_valid(ds),.sk_in_e(di),.sk_in_ready(sk_in_ready),.sk_out_valid(sk_out_valid),.sk_fault(sk_fault),.sk_y(sk_y));
integer seed=`SEED, checks=0, errors=0, masked=0, results=0, nzres=0, skchecks=0, faultlag=0, prio=0, k, f, j;
reg strict=1; reg [3:0] gfh=0;
reg [31:0] tie[0:7]; initial begin tie[0]=32'h0;tie[1]=32'h80000000;tie[2]=32'h3f800000;tie[3]=32'hbf800000;
  tie[4]=32'h7fc00000;tie[5]=32'hffc00000;tie[6]=32'h3f800000;tie[7]=32'h40000000; end
function [31:0] rf(input integer mode); reg [31:0] r; begin r=$random(seed);
  if(mode==0) rf={r[31],8'(8'd118+($unsigned(r[30:23])%20)),r[22:0]}; else if(mode==2) rf=tie[r[2:0]];
  else if(mode==3) rf={r[31],8'(8'd124+($unsigned(r[30:23])%4)),r[22:4],4'd0}; else rf=r; end endfunction
task randin(input integer mode); begin
  for(j=0;j<24;j=j+1) begin mixes[j*32+:32]=rf(mode); bases[j*32+:32]=rf(mode); end
  for(j=0;j<3;j=j+1) scales[j*32+:32]=rf(mode); end endtask
task err(input [8*24-1:0] what); begin errors=errors+1;
  if(errors<6) $display("DIFF %0s t=%0t v%b/%b s%b/%b f%b/%b r_eq=%0d i_eq=%0d",what,$time,gv,dv,gs,ds,gf,df,gr===dr,gi===di); end endtask
always @(negedge clk) begin
  if(!rst_n) gfh=0;
  else begin checks=checks+1;
    if({gv,ge,gs}!=={dv,de,ds}) err("ctl");
    if(gr!==dr) begin if(strict||!gf) err("result"); else masked=masked+1; end
    if(gs) begin skchecks=skchecks+1; if(gi!==di) begin if(strict||!gf) err("sk_in_e"); else masked=masked+1; end end
    if(df&&!gf) err("fault_early");
    if(gfh[3]&&!df) err("fault_late");
    if(gf!==df) faultlag=faultlag+1;
    gfh={gfh[2:0],gf};
    if(gv) begin results=results+1; if(|gr) nzres=nzres+1; end
  end
end
always @(posedge clk) if(gs) sk_y <= {16{rf(0)}} ^ {$random(seed),$random(seed),$random(seed),$random(seed),448'd0};
initial begin
  randin(0); repeat(3) @(negedge clk); #1 rst_n=1;
  // phase A: 50 clean schedules (launch -> sink -> capture -> result), value classes incl. max4 ties / near-equal
  for(f=0;f<50;f=f+1) begin
    randin(f%5==4 ? 1 : f%5==3 ? 2 : f%5==2 ? 3 : 0); launch=1; @(negedge clk); #1 launch=0;
    for(k=0;k<520;k=k+1) begin sk_out_valid=(k>=200); sk_fault=(f==7&&k==300); sk_in_ready=!(f==11&&k<260); @(negedge clk); #1; end
    sk_out_valid=0;
  end
  // phase A2: directed launch on the sink-capture edge (control priority), 8 schedules, then a clean one
  for(f=0;f<8;f=f+1) begin
    randin(f%2 ? 2 : 0); launch=1; @(negedge clk); #1 launch=0; sk_out_valid=1;
    while(!gold.capture_q) begin @(negedge clk); #1; end
    randin(0); launch=1; prio=prio+1; @(negedge clk); #1 launch=0;
    for(k=0;k<520;k=k+1) begin @(negedge clk); #1; end
  end
  sk_out_valid=0;
  // phase B: random chaos (relaunch mid-schedule, resets, sink faults)
  strict=0;
  for(k=0;k<40000;k=k+1) begin @(negedge clk); #1;
    rst_n=($unsigned($random(seed))%997!=0);
    launch=($unsigned($random(seed))%251==0); if(launch) randin($unsigned($random(seed))%4);
    sk_out_valid=($unsigned($random(seed))%3!=0); sk_fault=($unsigned($random(seed))%4001==0);
    sk_in_ready=($unsigned($random(seed))%50!=0);
  end
  $display("TAILX_REFORM checks=%0d errors=%0d masked=%0d results=%0d nonzero=%0d sk_checks=%0d fault_lag_edges=%0d prio=%0d",checks,errors,masked,results,nzres,skchecks,faultlag,prio);
  if(errors!=0||results<58) $fatal(1,"TAILX_REFORM FAIL");
  $display("TAILX_REFORM PASS"); $finish;
end
endmodule
