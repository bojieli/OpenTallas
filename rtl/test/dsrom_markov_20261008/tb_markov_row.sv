`timescale 1ns/1ps
module tb_markov_row;
 parameter integer PINREG=0;
 parameter integer MUTANT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,iv=0,ordy=0;
 reg [31:0] head;
 reg [255:0] w,x;
 wire sr,ir,ov,fault;
 wire [31:0] out;
 reg [255:0] wm[0:767],xm[0:767];
 reg [31:0] hm[0:47],gm[0:47];
 integer n,b,c,cyc=0,t0,stall;
 string dir;
 ot_dsrom_markov_row #(.MUTANT_FOLD(MUTANT),.PINREG(PINREG)) dut(.clk(clk),.rst_n(rst_n),.start(start),.start_ready(sr),
  .head_logit(head),.in_valid(iv),.in_ready(ir),.weight_bf16(w),.embed_bf16(x),
  .out_valid(ov),.out_ready(ordy),.out_bits(out),.fault(fault));
 always @(posedge clk) cyc<=cyc+1;
 initial begin
  if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
  $readmemh({dir,"/w.hex"},wm);$readmemh({dir,"/x.hex"},xm);
  $readmemh({dir,"/head.hex"},hm);$readmemh({dir,"/gold.hex"},gm);
  repeat(4) @(negedge clk);rst_n=1;
  for(n=0;n<48;n=n+1) begin
   @(negedge clk);if(!sr) $fatal(1,"not idle");start=1;head=hm[n];t0=cyc;
   @(negedge clk);start=0;
   for(b=0;b<16;b=b+1) begin
    if(n%3==1 && b%3==0) begin iv=0;if(PINREG==2) begin w={16{16'h7fc0}};x={16{16'h7f80}};end repeat(2) @(negedge clk);end
    if(!ir) $fatal(1,"unexpected input stall");iv=1;w=wm[n*16+b];x=xm[n*16+b];
    @(negedge clk);
   end
   iv=0;
   while(!ov) begin @(negedge clk);if(cyc-t0>600 || fault) $fatal(1,"fault or missing result n=%0d",n);end
   if(out!==gm[n]) $fatal(1,"nonexact n=%0d got=%h golden=%h",n,out,gm[n]);
   for(stall=0;stall<7;stall=stall+1) begin
    @(negedge clk);if(PINREG==2) begin w=~w;x=~x;end if(!ov || out!==gm[n] || sr) $fatal(1,"output changed under stall");
   end
   $display("ROW n=%0d cycles=%0d bits=%h",n,cyc-t0,out);
   ordy=1;@(negedge clk);ordy=0;
  end
  if(fault) $fatal(1,"fault");$display("PASS released256 48 rows separate Markov join bubbles backpressure");$finish;
 end
endmodule
