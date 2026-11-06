`timescale 1ns/1ps
module tb_skid_head;
 parameter integer MUT=0;
 localparam integer W=285;
 reg clk=0,rst_n=0,req_push=0,req_pop=0,in_ok=0;
 reg [W-1:0] in_data=0;
 reg [W-1:0] m[0:1];reg [1:0] ok=0,n=0;reg wp=0,rp=0;
 wire push=req_push&&n!=2;
 wire pop=req_pop&&n!=0&&ok[rp];
 wire [W-1:0] dh;wire dok;wire [1:0] dn;
 ot_svgr_rf1_skid_head #(.W(W),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.push(push),.pop(pop),.in_data(in_data),.in_ok(in_ok),.head_data(dh),.head_ok(dok),.n(dn));
 always #1 clk=~clk;
 always @(posedge clk)if(push)m[wp]<=in_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin n<=0;wp<=0;rp<=0;ok<=0;end
  else begin
   if(push)begin ok[wp]<=in_ok;wp<=~wp;end
   if(pop)rp<=~rp;
   n<=n+2'(push)-2'(pop);
  end
 end
 integer checks=0,full_pop=0,refused=0,both=0,pops=0,pushes=0;
 task tick(input integer command);
  integer k;
  begin
   @(negedge clk);
   req_push=command&1;req_pop=(command>>1)&1;in_ok=(command>>2)&1;
   for(k=0;k<8;k=k+1)in_data[k*32+:32]=$urandom;
   in_data[284:256]=$urandom;
   // Check pre-edge readiness and complete head, including refused heads.
   #0.1;
   if(dn!==n || (n!=0&&(dok!==ok[rp]||dh!==m[rp])))begin
    $display("SKID_HEAD FAIL MUT=%0d check=%0d n=%d/%d ok=%b/%b",MUT,checks,n,dn,ok[rp],dok);$fatal(1,"refinement mismatch");
   end
   checks=checks+1;
   if(n==2&&req_push&&pop)full_pop=full_pop+1;
   if(n!=0&&!ok[rp])refused=refused+1;
   if(push&&pop)both=both+1;
   if(push)pushes=pushes+1;if(pop)pops=pops+1;
   @(posedge clk);#0.1;
   if(dn!==n || (n!=0&&(dok!==ok[rp]||dh!==m[rp])))begin
    $display("SKID_HEAD FAIL MUT=%0d check=%0d n=%d/%d ok=%b/%b",MUT,checks,n,dn,ok[rp],dok);$fatal(1,"refinement mismatch");
   end
  end
 endtask
 integer pattern,j,code,seed=239,k;
 initial begin
  k=$urandom(seed);
  // Every length-six sequence of push-request/pop-request/input-ok commands.
  for(pattern=0;pattern<262144;pattern=pattern+1)begin
   @(negedge clk);rst_n=0;req_push=0;req_pop=0;
   @(negedge clk);rst_n=1;
   code=pattern;
   for(j=0;j<6;j=j+1)begin tick(code&7);code=code>>3;end
  end
  for(j=0;j<20000;j=j+1)begin
   if(j%113==0)begin @(negedge clk);rst_n=0;req_push=0;req_pop=0;@(negedge clk);rst_n=1;end
   tick($urandom);
  end
  if(full_pop==0||refused==0||both==0||pops==0||pushes==0)$fatal(1,"missing transition coverage");
  $display("SKID_HEAD PASS MUT=%0d checks=%0d exhaustive_sequences=262144 random=20000 full_push_blocked_on_pop=%0d refused_head_checks=%0d push_pop=%0d accepted_push=%0d accepted_pop=%0d extra_edges=0",MUT,checks,full_pop,refused,both,pushes,pops);$finish;
 end
endmodule
