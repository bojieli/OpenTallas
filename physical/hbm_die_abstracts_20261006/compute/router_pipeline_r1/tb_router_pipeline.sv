`timescale 1ns/1ps
module tb_router_pipeline;
 localparam CASES=64,BEATS=24;
 reg clk=0,rst_n=0,in_valid=0,in_last=0;
 reg [511:0] in_vals=0;
 always #0.4165 clk=~clk;
 wire out_valid;wire [53:0] out_ids;
 ot_hbm_router_topk_pipeline #(.ENABLE(1)) dut(.*);
 reg [511:0] data[0:CASES*BEATS-1];reg [53:0] expected[0:CASES-1];
 integer cyc=0,sent=0,checked=0,last_cycle[0:CASES-1];
 integer neg_bank=0,neg_reset=0,c,b,h;
 string dir;
 always @(posedge clk)begin
  #0.001;cyc=cyc+1;
  if(!rst_n)begin
   if(out_valid)$fatal(1,"HELD_RESET_GHOST");
  end else begin
   if(in_valid&&in_last)begin last_cycle[sent]=cyc;sent=sent+1;end
   if(out_valid)begin
    if(checked>=sent)$fatal(1,"UNOWNED_RESULT");
    if(out_ids!==expected[checked])
     $fatal(1,"GOLDEN_BANK_FAIL case=%0d got=%h expected=%h",checked,out_ids,expected[checked]);
    if(cyc-last_cycle[checked]!=28)
     $fatal(1,"PIPELINE_VALID_ALIGNMENT case=%0d delta=%0d",checked,cyc-last_cycle[checked]);
    checked=checked+1;
   end
  end
 end
 task step;begin @(posedge clk);#0.002;end endtask
 task drive(input integer index,input integer last);
  begin @(negedge clk);in_valid=1;in_last=last;in_vals=data[index];step();end
 endtask
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR_REQUIRED");
  $readmemh({dir,"/input.mem"},data);$readmemh({dir,"/expected.mem"},expected);
  neg_bank=$test$plusargs("NEG_BANK");neg_reset=$test$plusargs("NEG_RESET");
  repeat(4)step();@(negedge clk);rst_n=1;
  // Cancel a partial real vector, then hold POR with changing input data.
  for(b=0;b<7;b=b+1)drive(b,0);
  @(negedge clk);rst_n=0;in_valid=1;
  for(h=0;h<7;h=h+1)begin
   @(negedge clk);in_vals=~in_vals;
   if(neg_reset&&h==3)begin
    force dut.g_on.vpipe[25]=1'b1;
    $display("NEGATIVE_HELD_RESET_VALID_FF_INJECTED");
   end
   step();
  end
  @(negedge clk);in_valid=0;in_last=0;rst_n=1;
  repeat(32)step();
  if(out_valid||sent||checked)$fatal(1,"POR_CANCELLED_VECTOR_ESCAPED");
  if(neg_bank)begin
   force dut.g_on.bank=1'b0;
   $display("NEGATIVE_REAL_BANK_PHASE_FORCED");
  end
  for(c=0;c<CASES;c=c+1)for(b=0;b<BEATS;b=b+1)begin
   if(c%3==1&&b%5==2)begin
    @(negedge clk);in_valid=0;in_last=0;in_vals=~in_vals;
    repeat(2)step();
   end
   drive(c*BEATS+b,b==BEATS-1);
  end
  @(negedge clk);in_valid=0;in_last=0;
  repeat(32)step();
  if(checked!=CASES||sent!=CASES)$fatal(1,"RESULT_COUNT sent=%0d checked=%0d",sent,checked);
  if(neg_bank||neg_reset)$fatal(1,"NEGATIVE_NOT_OBSERVED");
  $display("ROUTER_PIPELINE_REAL384_K6_PASS checked=%0d tail=28 II=24 reset_cancel=1 bubbles=1",checked);
  $finish;
 end
endmodule
