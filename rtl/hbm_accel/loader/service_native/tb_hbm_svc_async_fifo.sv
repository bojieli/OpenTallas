`timescale 1ps/1fs
module tb_hbm_svc_async_fifo;
 parameter integer DEPTH=8;
 parameter real WR_HALF=512,RD_HALF=416.666667;
 reg wr_clk=0,rd_clk=0;always #(WR_HALF)wr_clk=~wr_clk;
 initial begin #137;forever #(RD_HALF)rd_clk=~rd_clk;end
 reg wr_rst_n=0,rd_rst_n=0,enable=0;wire wr_valid,wr_ready,rd_valid,rd_ready;
 wire [283:0] wr_data,rd_data;wire wr_overflow,rd_underflow;
 integer sent=0,received=0,wr_cycle=0,rd_cycle=0,target=0,seed=0,checked=0;
 function automatic [283:0] pattern(input integer s,input integer n);
  integer i;begin
   for(i=0;i<8;i=i+1)pattern[i*32+:32]=32'h9aee4312^(s*32'h9afdd)^(n*32'h124ef)^(i*32'hacbd123);
   pattern[283:256]=28'(s^n);
  end
 endfunction
 assign wr_valid=enable&&wr_ready&&sent<target&&wr_cycle%7!=0;
 assign wr_data=pattern(seed,sent);
 assign rd_ready=enable&&rd_valid&&rd_cycle%5!=0&&rd_cycle%11!=0;
 ot_hbm_svc_async_fifo #(.WIDTH(284),.DEPTH(DEPTH)) dut(.*);
 always @(posedge wr_clk)begin
  wr_cycle=wr_cycle+1;
  if(!(wr_rst_n&&rd_rst_n))sent=0;
  else if(wr_valid&&wr_ready)sent=sent+1;
 end
 always @(posedge rd_clk)begin
  rd_cycle=rd_cycle+1;
  if(!(wr_rst_n&&rd_rst_n))received=0;
  else if(rd_valid&&rd_ready)begin
   if(rd_data!==pattern(seed,received))$fatal(1,"FIFO payload/order mismatch depth%0d ordinal%0d",DEPTH,received);
   received=received+1;checked=checked+1;
  end
  if(enable&&(wr_overflow||rd_underflow))$fatal(1,"FIFO handshake fault");
 end
 task reset_one(input integer side,input integer newseed);
  begin
   enable=0;if(side==0)wr_rst_n=0;else rd_rst_n=0;
   repeat(12)@(negedge wr_clk);repeat(12)@(negedge rd_clk);
   seed=newseed;wr_rst_n=1;rd_rst_n=1;
   repeat(12)@(negedge wr_clk);repeat(12)@(negedge rd_clk);
  end
 endtask
 initial begin
  reset_one(0,1);target=2048;enable=1;wait(received==2048);enable=0;
  // Each interface can asynchronously flush an in-flight transfer train.
  reset_one(0,2);target=4096;enable=1;wait(sent>=200);reset_one(0,3);
  target=2048;enable=1;wait(received==2048);enable=0;
  reset_one(1,4);target=4096;enable=1;wait(sent>=200);reset_one(1,5);
  target=2048;enable=1;wait(received==2048);enable=0;
  $display("PASS HBM_FIFO depth=%0d wr_period_ps=%0f rd_period_ps=%0f checked=%0d resets_both_interfaces=pass wraps=pass",DEPTH,2*WR_HALF,2*RD_HALF,checked);$finish;
 end
 initial begin #100000000;$fatal(1,"FIFO test timeout");end
endmodule
