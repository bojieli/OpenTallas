`timescale 1ns/1ps
// HBM-P5-RTLB 10-23: lock-step bench of the coll_q2 over-cap split reduce twin ot_hgi_coll_reduce_static_pr (input pin
// registers + fault register) against the pinned ot_hgi_coll_reduce_static, one stimulus, every edge:
//   out_v / out_flit / fault_cause of the twin at t === pinned at t-1   (documented +1 edge)
//   fault of the twin at t === pinned at t-2                              (+1 input, +1 fault register)
// Stimulus: random strobes / tags / FP32 lane data (moderate exponents) with per-run densities (+DENS=1..4), occasional
// clear; NSEG reset segments (+NSEG=, default 10) of N/NSEG edges each, inputs idle for 4 edges around every reset, so
// the sticky fault rises afresh in every segment (its +2-edge rise is checked each time).  Coverage (publications, loads, adds) required.
// Mutants: -GMUT=1 (in_flit not registered), -GMUT=2 (fault not registered) must FAIL.
module tb_hgi_coll_reduce_static_pr;
 parameter integer MUT=0;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,clear=0,in_v=0,load_v=0,add_read=0,add_issue=0,pub_read=0,pub_bf16=0,pub_release=0,pub_issue=0;
 reg [544:0] in_flit=0; reg [3:0] load_tag=0,read_tag=0,pub_tag_a=0,pub_tag_b=0; reg [32:0] pub_meta=0;
 wire ov_p,ov_s,f_p,f_s; wire [544:0] of_p,of_s; wire [7:0] fc_p,fc_s;
 ot_hgi_coll_reduce_static ref0(.clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),
  .in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),.add_issue(add_issue),
  .pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),.pub_meta(pub_meta),
  .pub_release(pub_release),.pub_issue(pub_issue),.out_v(ov_p),.out_flit(of_p),.fault(f_p),.fault_cause(fc_p));
 ot_hgi_coll_reduce_static_pr #(.MUT(MUT)) dut(.clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),
  .clear(clear),.in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),
  .add_issue(add_issue),.pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),.pub_meta(pub_meta),
  .pub_release(pub_release),.pub_issue(pub_issue),.out_v(ov_s),.out_flit(of_s),.fault(f_s),.fault_cause(fc_s));
 reg ov_d=0,f_d1=0,f_d2=0,f_d2_prev=0; reg [544:0] of_d=0; reg [7:0] fc_d=0;
 always @(posedge clk) begin ov_d<=ov_p; of_d<=of_p; fc_d<=fc_p; f_d1<=f_p; f_d2<=f_d1; end
 integer nseg=10, seg, fr=0; integer seed=1, n=20000, dens=2, cmp=0, checks=0, errors=0, pubs=0, loads=0, adds=0, faults=0, i, l, k;
 always @(posedge clk) if(cmp) begin
  #0.1; checks=checks+1;
  if(ov_s!==ov_d || (ov_d && of_s!==of_d) || fc_s!==fc_d) begin errors=errors+1;
   if(errors<6) $display("REDUCE_PR MISMATCH t=%0t out_v %b/%b fault_cause %h/%h", $time, ov_s, ov_d, fc_s, fc_d); end
  if(f_s!==f_d2) begin errors=errors+1; if(errors<6) $display("REDUCE_PR FAULT MISMATCH t=%0t %b/%b", $time, f_s, f_d2); end
  if(ov_p) pubs=pubs+1; if(f_p) faults=faults+1; if(f_s && !f_d2_prev) fr=fr+1; f_d2_prev=f_s;
 end
 function automatic bit pr(input integer num); pr = ($unsigned($random(seed)) % 16) < num; endfunction
 initial begin
  if($value$plusargs("SEED=%d",k)) seed=k; if($value$plusargs("N=%d",k)) n=k; if($value$plusargs("DENS=%d",k)) dens=k;
  if($value$plusargs("NSEG=%d",k)) nseg=k;
  for(seg=0;seg<nseg;seg=seg+1) begin
  cmp=0; rst_n=0; {clear,in_v,load_v,add_read,add_issue,pub_read,pub_issue,pub_release}=0;
  repeat(4) @(negedge clk); rst_n=1; repeat(4) @(negedge clk); cmp=1;
  for(i=0;i<n/nseg;i=i+1) begin
   clear = pr(1) && pr(2);
   in_v=pr(2*dens); load_v=pr(dens); add_read=pr(dens); add_issue=pr(dens); pub_read=pr(dens); pub_issue=pr(dens);
   pub_release=pr(8); pub_bf16=pr(8);
   load_tag=$random(seed); read_tag=$random(seed); pub_tag_a=$random(seed); pub_tag_b=$random(seed);
   pub_meta={$random(seed),1'b1};
   for(l=0;l<16;l=l+1) in_flit[l*32+:32]={1'($random(seed)),8'(120+($unsigned($random(seed))%14)),23'($random(seed))};
   in_flit[544:512]={$random(seed),1'($random(seed))};
   if(load_v) loads=loads+1; if(add_issue) adds=adds+1;
   @(negedge clk);
  end
  {clear,in_v,load_v,add_read,add_issue,pub_read,pub_issue,pub_release}=0; repeat(40) @(negedge clk);
  end
  if(errors==0 && pubs>50) $display("REDUCE_PR PASS checks=%0d publications=%0d loads=%0d adds=%0d fault_edges=%0d fault_rises=%0d segments=%0d DENS=%0d MUT=%0d",
                                    checks,pubs,loads,adds,faults,fr,nseg,dens,MUT);
  else $display("REDUCE_PR FAIL errors=%0d checks=%0d publications=%0d MUT=%0d", errors, checks, pubs, MUT);
  $finish;
 end
endmodule
