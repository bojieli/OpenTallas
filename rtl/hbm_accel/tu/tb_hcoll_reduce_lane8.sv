`timescale 1ns/1ps
module tb_hcoll_reduce_lane8;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rn=0,v=0;reg[255:0]ops;reg[15:0]ix;
 wire rv;wire[31:0]y;wire[15:0]yi;wire[1:0]err;
 reg[31:0]gold[0:255];integer checked=0;
 ot_hcoll_reduce_lane8 #(.MUT(MUT))dut(.clk(clk),.rst_n(rn),.valid(v),.operands(ops),.index(ix),.reply_v(rv),.reply(y),.reply_index(yi),.reply_err(err));
 always @(posedge clk)if(rv)begin
  if(y!==gold[yi]||err!==0)$fatal(1,"REDUCE_LANE FAIL ordered numeric index=%0d y=%h expected=%h",yi,y,gold[yi]);
  checked=checked+1;
 end
 initial begin
  repeat(8)@(negedge clk);rn=1;repeat(8)@(negedge clk);
  for(integer n=0;n<256;n=n+1)begin
   v=(n%7!=2);ix=n;
   for(integer c=0;c<8;c=c+1)ops[32*c+:32]={1'(n%2),8'(127+c),23'd0};
   if(n%3==0)ops[0+:32]=32'h80000000;
   gold[n]={(n%2!=0)?1'b1:1'b0, (n%3==0)?31'h437e0000:31'h437f0000};
   @(negedge clk);
  end
  v=0;repeat(32)@(negedge clk);
  if(checked!=219)$fatal(1,"REDUCE_LANE FAIL reply count=%0d",checked);
  $display("REDUCE_LANE PASS orderedFP32 replies=%0d",checked);$finish;
 end
endmodule
