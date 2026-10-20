`timescale 1ns/1ps
// HBM-ELEMOWN3/COLLQ3 10-19: lockstep ot_hgi_coll_reduce_static (reference) vs ot_hgi_coll_reduce_split (control +
// 16 hardened ot_hgi_coll_reduce_lane) under weighted random commands; every output, every cycle.  Mutants (each must
// FAIL): -GSMUT_TAG=1 (split control writes back to tag^1), -GSMUT_BF16=1 (split BF16 rounding), +define+OT_COLL_RLANE_MUT_EXT.
module tb_hgi_coll_reduce_split_eq #(parameter integer SMUT_TAG=0,SMUT_BF16=0,CYCLES=200000);
 reg clk=1'b0; always #0.5 clk=~clk;
 reg rst_n=1'b0,clear=0,in_v=0,load_v=0,add_read=0,add_issue=0,pub_read=0,pub_bf16=0,pub_release=0,pub_issue=0;
 reg [544:0] in_flit=0; reg [3:0] load_tag=0,read_tag=0,pub_tag_a=0,pub_tag_b=0; reg [32:0] pub_meta=0;
 wire ro_v,so_v,rf,sf; wire [544:0] ro,so; wire [7:0] rc,sc;
 ot_hgi_coll_reduce_static u_ref(.clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),
  .in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),
  .add_issue(add_issue),.pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),
  .pub_meta(pub_meta),.pub_release(pub_release),.pub_issue(pub_issue),.out_v(ro_v),.out_flit(ro),.fault(rf),.fault_cause(rc));
 ot_hgi_coll_reduce_split #(.MUT_TAG(SMUT_TAG),.MUT_BF16(SMUT_BF16)) u_spl(.clk_control(clk),.clk_state({16{clk}}),
  .clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),
  .in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),
  .add_issue(add_issue),.pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),
  .pub_meta(pub_meta),.pub_release(pub_release),.pub_issue(pub_issue),.out_v(so_v),.out_flit(so),.fault(sf),.fault_cause(sc));
 integer cyc=0,bad=0,nv=0,nadd=0,i;
 reg rd_q=0,pb_q=0;
 always @(posedge clk) begin
  cyc<=cyc+1;
  if(cyc==8) rst_n<=1'b1;
  // weighted random programme: loads / reads (+ issue one edge later) / publishes (+ issue) with mostly legal tags
  load_v<=($random%5==0); load_tag<=$random; read_tag<=$random; pub_tag_a<=$random; pub_tag_b<=$random;
  add_read<=($random%4==0); pub_read<=($random%6==0); pub_bf16<=$random; pub_release<=$random; pub_meta<=$random;
  clear<=($random%997==0);
  for(i=0;i<17;i=i+1) in_flit[i*32+:32]<= ($random%3==0) ? {$random} : {1'b0,8'h7f+($random%8),23'h0}|$random;
  rd_q<=add_read; pb_q<=pub_read; add_issue<=add_read; pub_issue<=pub_read;
  in_v<=$random;
 end
 always @(negedge clk) if(rst_n && cyc>10) begin
  if(ro_v) nv=nv+1; if(add_issue) nadd=nadd+1;
  if({ro_v,ro,rf,rc}!=={so_v,so,sf,sc}) begin bad=bad+1; if(bad<=5) $display("RSPLIT_MISMATCH cyc=%0d ref_v=%b spl_v=%b ref_c=%h spl_c=%h",cyc,ro_v,so_v,rc,sc); end
  if(cyc>=CYCLES) begin
   if(bad==0 && nv>100 && nadd>100) $display("RSPLIT_EQ PASS cycles=%0d publishes=%0d adds=%0d",cyc,nv,nadd);
   else $display("RSPLIT_EQ FAIL mismatches=%0d publishes=%0d adds=%0d",bad,nv,nadd);
   $finish;
  end
 end
endmodule
