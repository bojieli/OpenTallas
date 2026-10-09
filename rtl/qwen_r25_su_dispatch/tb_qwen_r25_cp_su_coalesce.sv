`timescale 1ns/1ps
module tb_qwen_r25_cp_su_coalesce;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;reg [31:0] cp_launch_v=0;reg [63:0] cp_launch_pc=0;
 reg [147:0] cp_launch_owner=0;
 wire [31:0] sm_launch_v,cp_done,cp_fault;wire [63:0] sm_launch_pc;
 wire [147:0] sm_launch_owner;
 reg [31:0] sm_done=0,sm_fault=0;
 wire native_req_v;reg native_req_rdy=0;wire [31:0] native_req_pc;
 wire [73:0] native_req_owner;reg native_complete_v=0;
 wire native_complete_rdy;reg [73:0] native_complete_owner=0;reg native_fault=0;
 wire fault;
 localparam [73:0] OWNER={20'h801ff,18'd151935,4'ha,32'h12345678};
 ot_qwen_r25_cp_su_coalesce #(.ENABLE(1)) dut(.*);
 integer entry,cases=0;
 task reset;
  begin
   @(negedge clk);rst_n=0;cp_launch_v=0;sm_done=0;sm_fault=0;
   native_req_rdy=0;native_complete_v=0;native_fault=0;
   repeat(2)@(negedge clk);rst_n=1;
  end
 endtask
 task half(input integer h,input [31:0] pc,input [73:0] owner,input [15:0] mask);
  begin
   @(negedge clk);cp_launch_pc[h*32+:32]=pc;
   cp_launch_owner[h*74+:74]=owner;cp_launch_v[h*16+:16]=mask;
   @(negedge clk);cp_launch_v=0;
  end
 endtask
 task expect_fault;
  begin
   repeat(2)@(negedge clk);
   if(!fault||native_req_v||cp_done)$fatal(1,"invalid native invocation admitted");
   cases=cases+1;
  end
 endtask
 initial begin
  reset();
  cp_launch_pc={32'h1234,32'h5678};cp_launch_owner={OWNER,OWNER};cp_launch_v=32'h12345678;
  sm_done=32'h87654321;sm_fault=32'h01000000;#0.01;
  if(sm_launch_v!==cp_launch_v||sm_launch_pc!==cp_launch_pc||sm_launch_owner!==cp_launch_owner||
     cp_done!==sm_done||cp_fault!==sm_fault||native_req_v||fault)$fatal(1,"ordinary SM path changed");
  cases=cases+1;
  for(entry=0;entry<6;entry=entry+1)begin
   reset();half(entry%2,32'h53550000+entry,OWNER,entry%2?16'ha50f:16'h1357);
   repeat(3)begin @(negedge clk);if(native_req_v||cp_done||fault)$fatal(1,"one half fabricated launch/completion");end
   half(1-entry%2,32'h53550000+entry,OWNER,entry%2?16'h1357:16'ha50f);
   sm_done=32'hffffffff;
   repeat(5)begin
    @(negedge clk);
    if(!native_req_v||native_req_pc!==32'h53550000+entry||native_req_owner!==OWNER||cp_done||fault)
     $fatal(1,"matched request hold or pending completion changed");
   end
   sm_done=0;native_req_rdy=1;@(negedge clk);native_req_rdy=0;
   if(native_req_v||cp_done||!native_complete_rdy)$fatal(1,"accepted native request duplicated or fabricated done");
   // A provider's actual completion, rather than readiness, releases original masks.
   native_complete_owner=OWNER;#0.01;
   if(!native_complete_rdy)$fatal(1,"native completion not ready");
   native_complete_v=1;#0.01;if(cp_done!==32'ha50f1357)$fatal(1,"original CP masks lost");
   @(negedge clk);native_complete_v=0;
   if(cp_done||native_req_v||fault)$fatal(1,"completion repeated");
   cases=cases+1;
  end
  reset();half(0,32'h53550000,OWNER,16'hffff);half(1,32'h53550000,OWNER^(74'd1<<73),16'hffff);expect_fault();
  reset();half(0,32'h53550000,OWNER,16'hffff);half(1,32'h53550001,OWNER,16'hffff);expect_fault();
  reset();half(0,32'h53550006,OWNER,16'hffff);expect_fault();
  reset();half(0,32'h53550000,OWNER,16'hffff);half(0,32'h53550000,OWNER,16'hffff);expect_fault();
  reset();native_complete_owner=OWNER;native_complete_v=1;expect_fault();
  reset();half(0,32'h53550000,OWNER,16'hffff);half(1,32'h53550000,OWNER,16'hffff);
  native_req_rdy=1;@(negedge clk);native_req_rdy=0;
  native_complete_owner=OWNER^(74'd1<<53);native_complete_v=1;expect_fault();
  reset();half(0,32'h53550000,OWNER,16'h0f0f);half(1,32'h53550000,OWNER,16'hf0f0);
  native_fault=1;#0.01;if(cp_done||cp_fault!==32'hf0f00f0f||!fault)$fatal(1,"actual native fault fanback");cases=cases+1;
  $display("PASS_QWEN_AR_CP_COALESCE cases%0d native_entries6 owner74 original_masks staggered stalled_request real_completion no_fabricated_done negatives",cases);
  $finish;
 end
endmodule
