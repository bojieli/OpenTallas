`timescale 1ps/1fs
module tb_hbm_svc_fault_cdc;
 parameter integer MUT=0;parameter real WR_HALF=512,RD_HALF=416.666667;
 reg wr_clk=0,rd_clk=0,wr_rst_n=0,rd_rst_n=0,src_fault=0;
 always #(WR_HALF)wr_clk=~wr_clk;
 always #(RD_HALF)rd_clk=~rd_clk;
 wire dst_fault,wr_overflow,rd_underflow;
 ot_hbm_svc_fault_cdc #(.MUT(MUT))dut(.*);
 integer checks=0,max_latency=0,latency;
 task automatic wait_fault;
  begin
   latency=0;
   while(dst_fault!==1'b1&&latency<40)begin @(negedge rd_clk);latency=latency+1;end
   if(dst_fault!==1'b1)$fatal(1,"STATUS fault event lost");
   if(latency>max_latency)max_latency=latency;
   repeat(30)begin @(negedge rd_clk);if(dst_fault!==1'b1)$fatal(1,"STATUS not sticky");checks=checks+1;end
  end
 endtask
 task automatic quiet;
  begin repeat(12)begin @(negedge rd_clk);if(dst_fault!==1'b0)$fatal(1,"STATUS phantom event/reset flush");checks=checks+1;end end
 endtask
 always @(negedge wr_clk)if(wr_rst_n&&rd_rst_n&&wr_overflow)$fatal(1,"STATUS unexpected overflow");
 always @(negedge rd_clk)if(wr_rst_n&&rd_rst_n&&rd_underflow)$fatal(1,"STATUS unexpected underflow");
 initial begin
  repeat(3)@(negedge wr_clk);wr_rst_n=1;rd_rst_n=1;
  // Transient error on the first source edge, before FIFO online handshake:
  // the source pending latch must remember it, independent of clock ratio.
  src_fault=1;@(negedge wr_clk);src_fault=0;wait_fault();
  rd_rst_n=0;#(RD_HALF/3);if(dst_fault!==0)$fatal(1,"STATUS destination reset did not clear");
  repeat(3)@(negedge rd_clk);rd_rst_n=1;quiet();
  // A held fault is resent after either interface reset. This catches sender
  // state that incorrectly resets from only its own clock-domain reset.
  @(negedge wr_clk);src_fault=1;wait_fault();
  rd_rst_n=0;repeat(3)@(negedge rd_clk);rd_rst_n=1;wait_fault();
  wr_rst_n=0;repeat(3)@(negedge wr_clk);wr_rst_n=1;wait_fault();
  // Common reset flush followed by a fresh event at an unrelated phase.
  src_fault=0;wr_rst_n=0;rd_rst_n=0;repeat(3)@(negedge wr_clk);
  wr_rst_n=1;rd_rst_n=1;quiet();
  #(WR_HALF/7);src_fault=1;repeat(2)@(negedge wr_clk);src_fault=0;wait_fault();
  $display("PASS STATUS_FIFO MUT=%0d checks=%0d max_fault_latency_rd_edges=%0d wr_period=%0f rd_period=%0f",MUT,checks,max_latency,2*WR_HALF,2*RD_HALF);$finish;
 end
 initial begin #1000000;$fatal(1,"STATUS timeout");end
endmodule
