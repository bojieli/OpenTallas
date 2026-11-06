`timescale 1ns/1ps
module tb_fp;
 parameter integer MUT_FP=0, SEED=1, N=200000;
 reg clk=0,rst_n=0,start=0,flush_slot=0,publish_slot=0;
 reg [7:0] cfg_g=0,cfg_gbase=0,cfg_rank=0; reg [3:0] in_slot=0,in_v=0; reg [2179:0] in_flit=0;
 wire ov0,ov1,f0,f1; wire [544:0] of0,of1; reg f0_d; integer seed,i,l,errs=0,faults=0,dupv=0;
 ot_hgi_coll_argmax_static #(.MAX_GROUP(192)) g(.clk(clk),.rst_n(rst_n),.start(start),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),
  .cfg_rank(cfg_rank),.in_slot(in_slot),.in_v(in_v),.in_flit(in_flit),.flush_slot(flush_slot),.publish_slot(publish_slot),
  .out_v(ov0),.out_flit(of0),.fault(f0));
 ot_hgi_coll_argmax_static_fp #(.MAX_GROUP(192),.MUT_FP(MUT_FP)) n(.clk(clk),.rst_n(rst_n),.start(start),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),
  .cfg_rank(cfg_rank),.in_slot(in_slot),.in_v(in_v),.in_flit(in_flit),.flush_slot(flush_slot),.publish_slot(publish_slot),
  .out_v(ov1),.out_flit(of1),.fault(f1));
 always #1 clk=~clk;
 always @(posedge clk or negedge rst_n) if(!rst_n) f0_d<=0; else f0_d<=f0;
 integer ph,gsz,base,k;
 initial begin
  seed=SEED; seed=$urandom(seed);
  repeat(3)@(negedge clk); rst_n=1;
  for(i=0;i<N;i=i+1)begin
   @(negedge clk);
   // occasional reset so the sticky fault is exercised many times
   if($urandom%48==0)begin rst_n=0; @(negedge clk); rst_n=1; end
   start=($urandom%64==0); flush_slot=($urandom%40==0); publish_slot=($urandom%40==0);
   gsz=$urandom%8; cfg_g=(gsz==0)?1:(gsz==1)?2:(gsz==2)?4:(gsz==3)?8:(gsz==4)?96:(gsz==5)?192:$urandom;
   cfg_gbase=($urandom%4==0)?$urandom:($urandom%16); cfg_rank=$urandom;
   in_v=($urandom%3==0)?4'b0:$urandom; in_slot=($urandom%50==0)?$urandom:in_v;
   for(l=0;l<4;l=l+1)begin
    in_flit[l*545+:512]={16{$urandom}};
    in_flit[l*545+512+:16]=($urandom%30==0)?$urandom:16'd0;
    // small source range -> many duplicates, sometimes out of range
    in_flit[l*545+528+:8]=($urandom%20==0)?$urandom:(n.gbase_q+($urandom%6));
    in_flit[l*545+536+:8]=$urandom;
    in_flit[l*545+544]=($urandom%25!=0);
   end
  end
  $display("TB_FP MUT_FP=%0d N=%0d errs=%0d fault_rises=%0d", MUT_FP, N, errs, faults);
  $finish;
 end
 always @(posedge clk) if(rst_n) begin
  #0.1;
  if(ov0!==ov1 || of0!==of1 || f1!==f0_d) begin errs=errs+1; if(errs<5) $display("MISMATCH t=%0t ov %b/%b fault_d %b fp %b",$time,ov0,ov1,f0_d,f1); end
 end
 always @(posedge f0) faults=faults+1;
endmodule
