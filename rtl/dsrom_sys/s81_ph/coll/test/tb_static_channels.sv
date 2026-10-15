`timescale 1ns/1ps
module tb_static_channels;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [4:0] tx_slot=0,rx_slot=0;
 reg [9:0] tx_kind=0,rx_kind=0;
 reg vm_tx_last=0;reg vm_tx_valid=0;reg [2:0] vm_tx_channel=0;
 reg [551:0] vm_tx_payload=0;
 reg [513:0] wfc_tx=0;
 reg host_tx_valid=0;reg [10:0] host_status=0;reg [64:0] host_completion=0;
 wire [4:0] lane_tx_last;wire [4:0] lane_tx_valid;wire [2759:0] lane_tx_payload;
 reg [4:0] lane_rx_last=0;reg [4:0] lane_rx_valid=0;reg [2759:0] lane_rx_payload=0;
 wire vm_rx_last;wire vm_rx_valid;wire [2:0] vm_rx_channel;wire [551:0] vm_rx_payload;
 wire [513:0] wfc_rx;wire [515:0] host_rx;wire fault;
 dsfd_coll_static_channels #(.MUT(MUT)) dut(.*);
 integer c,k,i;reg [551:0] expected;reg [551:0] stim;
 task step;begin @(posedge clk);#1;end endtask
 task clear_inputs;begin
 tx_slot=0;rx_slot=0;tx_kind=0;rx_kind=0;vm_tx_valid=0;wfc_tx=0;
 host_tx_valid=0;lane_rx_valid=0;lane_rx_payload=0;
 end endtask
 task reset;begin @(negedge clk);clear_inputs();rst_n=0;step();@(negedge clk);rst_n=1;end endtask
 initial begin
 reset();
 // All five lane mappings, all payload bits and all three clients.
 for(c=0;c<5;c=c+1) for(k=0;k<3;k=k+1) begin
   clear_inputs();
   for(i=0;i<552;i=i+1) stim[i]=((i*7+c*13+k*11)%17)<8;
   tx_slot[c]=1;rx_slot[c]=1;tx_kind[c*2+:2]=k;rx_kind[c*2+:2]=k;
   vm_tx_last=~stim[551];lane_rx_last[c]=~stim[551];lane_rx_valid[c]=1;lane_rx_payload[c*552+:552]=stim;
   case(k)
   0:begin vm_tx_valid=1;vm_tx_channel=c;vm_tx_payload=stim;expected=stim;end
   1:begin wfc_tx={stim[551],stim[511:0],1'b1};expected={stim[551],39'b0,stim[511:0]};end
   2:begin host_tx_valid=1;host_status=11'h645;host_completion={1'b1,64'hfedcba9876543210};
           expected={1'b1,470'b0,11'h645,5'b0,1'b1,64'hfedcba9876543210};end
   endcase
   step();
   if(fault||lane_tx_valid!==tx_slot||lane_tx_payload[c*552+:552]!==expected) $fatal(1,"tx payload/calendar lane%0d kind%0d",c,k);
   case(k)
   0:if(!vm_rx_valid||vm_rx_channel!==c||vm_rx_payload!==stim||vm_rx_last!==~stim[551]) $fatal(1,"vm receive");
   1:if(wfc_rx!=={~stim[551],stim[511:0],1'b1}) $fatal(1,"WFC receive");
   2:if(host_rx!=={stim[514:0],1'b1}) $fatal(1,"host receive");
   endcase
   @(negedge clk);
 end
 clear_inputs();step();if(lane_tx_valid||vm_rx_valid||wfc_rx[0]||host_rx[0]||fault)$fatal(1,"no stale slots");
 // Simultaneous independent VM, WFC and host uses no demand arbitration.
 @(negedge clk);tx_slot=5'b10101;tx_kind=10'b1000010000;
 vm_tx_valid=1;vm_tx_channel=0;wfc_tx={1'b1,512'h123,1'b1};host_tx_valid=1;
 step();if(fault||lane_tx_valid!==5'b10101)$fatal(1,"concurrent slots");
 // Missing/late beat is fault and never slides into a later slot.
 reset();rx_slot=1;step();if(!fault||vm_rx_valid)$fatal(1,"missing beat");
 @(negedge clk);rx_slot=0;lane_rx_valid=1;step();if(!fault||vm_rx_valid)$fatal(1,"late beat accepted");
 @(negedge clk);clear_inputs();rx_slot=2;lane_rx_valid=2;lane_rx_payload[552+:552]=552'h123;
 step();if(!fault||!vm_rx_valid||vm_rx_channel!=1||vm_rx_payload!=552'h123)$fatal(1,"fault rescheduled subsequent valid slot");
 reset();tx_slot=3;vm_tx_valid=1;step();if(!fault)$fatal(1,"source collision undetected");
 reset();rx_slot=3;lane_rx_valid=3;step();if(!fault)$fatal(1,"sink collision undetected");
 reset();tx_slot=1;step();if(!fault||lane_tx_valid)$fatal(1,"missing source");
 reset();wfc_tx=1;step();if(!fault||lane_tx_valid)$fatal(1,"unscheduled source");
 reset();tx_slot=1;tx_kind=3;step();if(!fault)$fatal(1,"illegal slot");
 $display("PASS static channels: all five physical mappings, 552-bit payloads, WFC514, host516, concurrency and schedule faults");$finish;
 end
endmodule
