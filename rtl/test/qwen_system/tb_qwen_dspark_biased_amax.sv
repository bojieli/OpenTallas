`timescale 1ns/1ps
module tb_qwen_dspark_biased_amax;
 parameter integer MUT=0;
 reg clk=0,rst=0,iv=0,last=0,orr=0;
 always #0.555555 clk=~clk; // native SU serial domain 0.9GHz
 reg [2047:0] logits;reg [17:0] base;reg [1:0] rank;reg [63:0] id;
 wire ready,ov,fault;wire [17:0] tok;wire [31:0] val;wire [63:0] oid;
 ot_qwen_dspark_biased_amax #(.ENABLE(1),.MUT_TIE(MUT)) dut(
  .clk(clk),.rst_n(rst),.i_v(iv),.i_r(ready),.i_logits(logits),.i_base(base),.i_rank(rank),.i_id(id),.i_last(last),
  .o_v(ov),.o_r(orr),.o_token(tok),.o_value(val),.o_id(oid),.fault(fault));
 task automatic reset;
  begin @(negedge clk);rst=0;iv=0;orr=0;repeat(3)@(negedge clk);rst=1;repeat(3)@(negedge clk);end
 endtask
 integer r,b,l,c,t,transactions=0;
 reg [17:0] expected;reg [31:0] ev;
 initial begin
  reset();
  for(r=0;r<4;r=r+1)for(c=0;c<2;c=c+1)begin
   rank=2'(r);id=64'h1234567800000000+64'(r*2+c);
   expected=18'(r*37984+(c==0?17:0));ev=c==0?32'h3f800000:32'h80000000;
   for(b=0;b<594;b=b+1)begin
    @(negedge clk);if(!ready)$fatal(1,"not ready before row finish");
    if(b%17==0)begin iv=0;repeat(2)@(negedge clk);end
    iv=1;base=18'(64*b);last=b==593;
    for(l=0;l<64;l=l+1)begin
     if(c==0)logits[l*32+:32]=((64*b+l)==17||(64*b+l)==37983)?32'h3f800000:32'h3e800000+32'((64*b+l)%1234);
     else logits[l*32+:32]=(l%2==0)?32'h80000000:32'b0;
     if(64*b+l>=37984)logits[l*32+:32]=32'h7fc12345; // invalidtail must not leak
    end
   end
   @(negedge clk);iv=0;t=0;while(!ov&&t<20)begin @(negedge clk);t=t+1;end
   if(!ov||fault||tok!==expected||val!==ev||oid!==id)$fatal(1,"exact/tie/full18bit id failure rank=%0d case=%0d tok=%0d want=%0d",r,c,tok,expected);
   repeat(7)begin @(negedge clk);if(!ov||tok!==expected||oid!==id||ready)$fatal(1,"output backpressure/identity unstable");end
   orr=1;@(negedge clk);orr=0;transactions=transactions+1;
  end
  reset();rank=0;id=1;iv=1;base=1;last=0;logits=0;@(negedge clk);iv=0;@(negedge clk);
  if(!fault||ready)$fatal(1,"malformed ordinal not blocked");
  reset();rank=0;id=1;iv=1;base=0;last=0;logits=0;logits[31:0]=32'h7fc00001;@(negedge clk);iv=0;@(negedge clk);
  if(!fault||ov)$fatal(1,"NaN not blocked");
  reset();rank=0;id=1;iv=1;base=0;last=0;logits=0;@(negedge clk);base=64;id=2;@(negedge clk);iv=0;@(negedge clk);
  if(!fault||ready)$fatal(1,"cohort identity substitution not blocked");
  $display("QWEN_NATIVE_AMAX_PASS rows=%0d values=%0d full18bit_rank3=1 signedzero_ties=1 tailmask=1 stalled_identity=1 negative_shape_NaN_ID=1",transactions,transactions*37984);
  $finish;
 end
endmodule
