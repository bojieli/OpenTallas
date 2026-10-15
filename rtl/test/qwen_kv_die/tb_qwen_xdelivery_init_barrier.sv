module tb_qwen_xdelivery_init_barrier;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,offer_v=0,acquire_ready=0,accept_v=0,source_output_drained=0,release_ready=0,transport_flush_ack=0;
 wire offer_ready,acquire_v,dispatch_v,banks_begin,release_v,flush_req,fault;
 reg [378:0] offer_ib=379'h123;reg offer_mode=0;reg [3:0] offer_participants=4'b1111;
 reg [31:0] acquire_version=32'hc1234567;
 wire [3:0] held_participants;
 wire [378:0] held_ib;wire held_mode;wire [15:0] held_context;wire [31:0] held_version;
 reg [1:0] accept_tile=0;reg [15:0] accept_context=0;reg [31:0] accept_version=32'hc1234567;reg [378:0] accept_ib=379'h123;
 reg [3:0] bank_init_participants=4'b1111;
 reg [1:0] bank_drained=0,bank_init_v=0;wire [1:0] bank_init_ack;reg [31:0] bank_init_context=0;reg [63:0] bank_init_version={2{32'hc1234567}};
 ot_qwen_xdelivery_lifetime_init_ctrl #(.ENABLE(1),.TILES(4),.BANKS(2)) dut(.*);
 task step;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin rst_n=0;offer_v=0;acquire_ready=0;accept_v=0;bank_init_v=0;transport_flush_ack=0;step;rst_n=1;step;transport_flush_ack=1;step;transport_flush_ack=0;end endtask
 task acquire;begin offer_v=1;step;offer_v=0;if(!acquire_v)$fatal(1,"acquire missing");acquire_ready=1;step;acquire_ready=0;if(!banks_begin)$fatal(1,"bank BEGIN missing");end endtask
 integer i;
 initial begin
 reset;acquire;
 for(i=0;i<12;i=i+1)begin if(dispatch_v)$fatal(1,"dispatch before bank initialization");step;end
 bank_init_v=1;step;bank_init_v=0;
 for(i=0;i<8;i=i+1)begin if(dispatch_v)$fatal(1,"dispatch with missing bank receipt");step;end
 bank_init_v=2;step;bank_init_v=0;step;if(!dispatch_v)$fatal(1,"matching receipts did not dispatch");
 accept_v=1;for(i=0;i<4;i=i+1)begin accept_tile=i;step;end accept_v=0;step;
 source_output_drained=1;bank_drained=3;#1;if(!release_v)$fatal(1,"actual drain missing release");release_ready=1;step;release_ready=0;
 reset;acquire;bank_init_context[15:0]=1;bank_init_v=1;step;bank_init_v=0;if(!fault)$fatal(1,"stale initialization context escaped");
 bank_init_context=0;reset;acquire;bank_init_version[31:0]=0;bank_init_v=1;step;bank_init_v=0;if(!fault)$fatal(1,"stale initialization version escaped");
 bank_init_version={2{32'hc1234567}};reset;acquire;bank_init_participants=4'b1110;bank_init_v=1;step;bank_init_v=0;if(!fault)$fatal(1,"wrong initialization participants escaped");
 bank_init_participants=4'b1111;reset;acquire;accept_v=1;step;accept_v=0;if(!fault)$fatal(1,"accept before bank barrier escaped");
 reset;acquire;rst_n=0;step;rst_n=1;step;if(dispatch_v||!flush_req)$fatal(1,"reset discarded transport fence");
 $display("PASS initialization controller delays missing/stale receipts, early accept, reset and full matching cohort");$finish;
 end
endmodule
