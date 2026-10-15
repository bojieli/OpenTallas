`timescale 1ns/1ps
module tb_qwen_xcontext_wrap;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,drained=0,req=0,re=0,ack=0;
 reg [95:0] key=0;reg [31:0] version=0;reg [15:0] rt=0,at=0;
 wire ready,fire;wire [15:0] token;wire [95:0] fa;wire [31:0] fv;
 integer n;
 ot_qwen_xcontext_protocol #(.DEPTH(2),.ROOTS(1),.MUT_REUSE(MUT)) dut(
 .base_clk(clk),.rst_n(rst),.flush(1'b0),.transport_flushed(drained),
 .req_v(req),.req_addr(key),.req_ib(379'd0),.req_version(version),.req_epoch(21'd0),.req_mask(4'hf),.req_phase(4'd0),.req_ready(ready),.req_token(token),
 .return_event(re),.return_token(rt),.return_root(5'd0),.return_data(128'd0),.fill_fire(fire),.fill_addr(fa),.fill_version(fv),
 .ack_event(ack),.ack_token(at),.ack_root(5'd0),.ib_offer(1'b0),.ib_offer_data(379'd0),.core_step(1'b0),.core_ready(1'b0));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 initial begin
  tick();rst=1;drained=1;tick();drained=0;
  req=1;key=96'h123456;version=1;tick();req=0; // token0 remains live throughout wrap
  for(n=1;n<65536;n=n+1)begin
   if(!ready || token!==16'(n))$fatal(1,"unexpected token/credit before wrap n=%0d",n);
   req=1;key=96'(n);version=32'(n);tick();req=0;
   re=1;rt=16'(n);#1;if(!fire || fa!==96'(n) || fv!==32'(n))$fatal(1,"wrap context lost");tick();re=0;
   ack=1;at=16'(n);tick();ack=0;
  end
  if(token!==0 || ready)$fatal(1,"live token reused after16bit wrap");
  re=1;rt=0;#1;if(!fire || fa!==96'h123456 || fv!==1)$fatal(1,"held context corrupted at wrap");tick();re=0;
  ack=1;at=0;tick();ack=0;
  if(!ready || token!==0)$fatal(1,"drained token not reusable");
  req=1;key=96'hfedcba;version=32'hdeadbeef;tick();req=0;re=1;rt=0;
  #1;if(!fire || fa!==96'hfedcba || fv!==32'hdeadbeef)$fatal(1,"new context failed after drained reuse");tick();
  $display("PASS full16bit token wrap transactions65537 held_entry1 no_reuse_until_ACK1");$finish;
 end
endmodule
