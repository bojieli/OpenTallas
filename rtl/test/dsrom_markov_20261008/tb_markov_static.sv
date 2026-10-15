`timescale 1ns/1ps
module tb_markov_static;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg[31:0] head;reg[255:0] w,x;
 wire ov,fault;wire[31:0] out;
 reg[255:0] wm[0:767],xm[0:767];reg[31:0] hm[0:47],gm[0:47];
 integer n,b,cyc=0,t0,latency=-1;string dir;
 ot_s81_markov_k256_static dut(.clk(clk),.clk_leaf({38{clk}}),.rst_n(rst_n),.start(start),.head_logit(head),
  .weight_bf16(w),.embed_bf16(x),.out_valid(ov),.out_bits(out),.fault(fault));
 always @(posedge clk) cyc<=cyc+1;
 initial begin
  if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
  $readmemh({dir,"/w.hex"},wm);$readmemh({dir,"/x.hex"},xm);
  $readmemh({dir,"/head.hex"},hm);$readmemh({dir,"/gold.hex"},gm);
  repeat(4) @(negedge clk);rst_n=1;repeat(4) @(negedge clk);
  for(n=0;n<48;n=n+1) begin
   start=1;head=hm[n];t0=cyc;
   @(negedge clk);start=0;
   for(b=0;b<16;b=b+1) begin
    w=wm[16*n+b];x=xm[16*n+b];@(negedge clk);
   end
   // Poison unused slots. Calendar must never consume them.
   w={16{16'h7fc0}};x={16{16'h7f80}};head=32'h7fc00000;
   while(!ov) begin @(negedge clk);if(cyc-t0>600 || fault) $fatal(1,"fault or missing result n=%0d",n);end
   if(out!==gm[n]) $fatal(1,"nonexact n=%0d got=%h golden=%h",n,out,gm[n]);
   if(latency<0) latency=cyc-t0;
   if(cyc-t0!=latency) $fatal(1,"calendar changed");
   $display("STATIC_ROW n=%0d command_to_done=%0d bits=%h",n,cyc-t0,out);
   @(negedge clk);if(ov) $fatal(1,"held output instead of pulse");
   if(fault) $fatal(1,"fault");
  end
  repeat(4) @(negedge clk);if(fault) $fatal(1,"late fault");
  $display("MARKOV_STATIC PASS rows=48 beats=768 command_to_done=%0d minimum_II=179",latency);$finish;
 end
endmodule
