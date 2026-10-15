module tb_qwen_xdelivery_init_bank;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,begin_v=0,fenced_clear=0,init_ack=0;
 reg [15:0] begin_context=16'h789a;reg [31:0] begin_version=32'hc1234567;reg [1:0] participant_mask=3;
 reg [1:0] issue_v=0,retire_v=0,seal_v=0;wire [1:0] issue_ready,retire_ready;
 reg [79:0] issue_seq=0,retire_seq=0;
 reg [31:0] issue_context={2{16'h789a}},retire_context={2{16'h789a}},seal_context={2{16'h789a}};
 reg [63:0] issue_version={2{32'hc1234567}},retire_version={2{32'hc1234567}},seal_version={2{32'hc1234567}};
 wire [1:0] init_participants;wire drained,fault,begin_ready,init_v;wire [15:0] init_context;wire [31:0] init_version;
 ot_qwen_xdelivery_ack_vector_init #(.ENABLE(1),.N(2)) dut(.*);
 task step;begin @(posedge clk);#1;@(negedge clk);end endtask
 initial begin
 step;rst_n=1;step;if(init_v||!begin_ready)$fatal(1,"receipt before actual bank BEGIN");
 begin_v=1;step;begin_v=0;
 if(!init_v||init_context!=16'h789a||init_version!=32'hc1234567||init_participants!=3||issue_ready!=3)$fatal(1,"receipt not actual initialized bank state");
 begin_context=0;begin_version=0;
 repeat(8)begin step;if(!init_v||init_context!=16'h789a||init_version!=32'hc1234567||begin_ready)$fatal(1,"receipt not retained until ACK");end
 init_ack=1;step;init_ack=0;if(init_v)$fatal(1,"receipt ACK did not consume");
 issue_v=3;step;issue_v=0;retire_v=3;step;retire_v=0;seal_v=3;step;seal_v=0;if(!drained||fault||!begin_ready)$fatal(1,"actual bank query/retire/seal failed");
 fenced_clear=1;step;fenced_clear=0;begin_v=1;issue_v=1;step;begin_v=0;issue_v=0;if(!fault||init_v)$fatal(1,"receipt certified BEGIN/event collision");
 fenced_clear=1;step;fenced_clear=0;if(init_v||fault)$fatal(1,"fenced reset did not clear receipt");
 $display("PASS actual vector-bank initialization receipt, retained identity, ACK, query retirement and collision suppression");$finish;
 end
endmodule
