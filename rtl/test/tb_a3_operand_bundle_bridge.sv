`timescale 1ns/1ps
module tb_a3_operand_bundle_bridge;
 reg clk=0,rst_n=0,clear=0,lane_request=0,lane_issue=0;
 reg [127:0] lane_address=0;
 wire lane_credit,service_valid,response_ready;
 wire [191:0] lane_data;
 wire [127:0] service_address;
 reg service_ready=0,response_valid=0;
 reg [191:0] response_data=0;
 ot_a3_operand_bundle_bridge dut(.*);
 always #5 clk=~clk;
 task tick;begin @(posedge clk);#1;end endtask
 initial begin
 tick();@(negedge clk);rst_n=1;lane_request=1;lane_address=128'h1234;
 tick();@(negedge clk);lane_address=128'hffff;
 repeat(3)begin
  if(!service_valid || service_address!==128'h1234 || lane_credit)$fatal(1,"request stability");
  tick();@(negedge clk);
 end
 service_ready=1;tick();@(negedge clk);service_ready=0;
 repeat(4)begin
  if(!response_ready || lane_credit || service_valid)$fatal(1,"response wait");
  tick();@(negedge clk);
 end
 response_valid=1;response_data=192'habc123;tick();@(negedge clk);response_valid=0;
 repeat(3)begin
  if(!lane_credit || response_ready || service_valid)$fatal(1,"reserved bundle lost");
  tick();@(negedge clk);
 end
 lane_issue=1;tick();
 if(lane_data!==0)$fatal(1,"bundle delivered one cycle too early");
 @(negedge clk);lane_issue=0;lane_request=0;
 tick();if(lane_data!==192'habc123 || lane_credit)$fatal(1,"fixed-latency delivery");
 @(negedge clk);lane_request=1;tick();@(negedge clk);
 clear=1;#1;if(service_valid || lane_credit || response_ready)$fatal(1,"clear credits");
 tick();@(negedge clk);clear=0;lane_request=0;tick();
 if(lane_credit || service_valid || lane_data!==0)$fatal(1,"cancelled request survived");
 // Upstream flush contract: no stale response is injected after clear.
 @(negedge clk);rst_n=0;#1;
 if(lane_credit || service_valid || response_ready)$fatal(1,"reset credits");
 $display("PASS bundle bridge request hold, delayed response, reservation hold, delivery timing, clear, reset");$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
