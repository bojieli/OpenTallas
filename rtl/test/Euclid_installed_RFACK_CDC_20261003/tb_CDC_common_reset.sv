`timescale 1ps/1fs
// Actual default-width bridge leaf. Opaque data, never interpreted as RF ACK.
module tb_CDC_common_reset;
 reg src_clk=0,fast_clk=0,dst_clk=0,rst_n=0;
 always #3 src_clk=~src_clk;always #2 fast_clk=~fast_clk;always #5 dst_clk=~dst_clk;
 reg iv=0,ore=0;reg [470:0] id=0;wire ir,ov;wire [470:0] od;
 integer accepts=0,delivers=0;
 ot_hbm_r14_clock_bridge #(.WIDTH(471)) bridge(.*);
 always @(posedge src_clk)if(rst_n&&iv&&ir)accepts=accepts+1;
 always @(posedge dst_clk)if(rst_n&&ov&&ore)delivers=delivers+1;
 task send(input [470:0] data);
  begin @(negedge src_clk);id=data;iv=1;do @(posedge src_clk);while(!ir);@(negedge src_clk);iv=0;end
 endtask
 initial begin
  #21;rst_n=1;send({471{1'b1}});wait(ov);@(negedge dst_clk);
  repeat(4)begin if(!ov||od!=={471{1'b1}})$fatal(1,"FAIL_CDC_HELD_DATA");@(negedge dst_clk);end
  // Common source/fast/destination reset discards the held opaque packet.
  rst_n=0;#1;if(ov||ir)$fatal(1,"FAIL_CDC_RESET_NOT_QUIET");
  #31;rst_n=1;repeat(80)begin @(negedge fast_clk);if(ov)$fatal(1,"FAIL_OLD_PACKET_AFTER_COMMON_RESET");end
  send(471'h123456789abcdef);wait(ov);@(negedge dst_clk);
  if(od!==471'h123456789abcdef)$fatal(1,"FAIL_CDC_NEW_PACKET_BITS");
  repeat(4)begin @(negedge dst_clk);if(!ov||od!==471'h123456789abcdef)$fatal(1,"FAIL_CDC_HOLD_AFTER_RESET");end
  ore=1;@(negedge dst_clk);ore=0;repeat(20)@(negedge fast_clk);
  if(ov||accepts!=2||delivers!=1)$fatal(1,"FAIL_CDC_CONDITIONAL_COUNTS");
  $display("PASS_CDC_OPAQUE_COMMON_RESET accepted=2 reset_aborted=1 delivered=1; NO_RF_ACK_IDENTITY_OR_COMMON_CLOCK_LATENCY_CREDIT");$finish;
 end
endmodule
