`timescale 1ns/1ps
// Exhaustive host token domain on the minimum actual command processor, NSM16.
module tb_qwen_r25_cmdproc18;
reg clk=0; always #1 clk=~clk;
reg rst_n=0, cmd_we=0, db_v=0, cpl_rdy=0;
reg [7:0] cmd_addr=0;
reg [63:0] cmd_wdata=0;
reg [17:0] db_token=0;
reg [19:0] db_pos=0;
reg [31:0] db_job=0;
reg [3:0] db_generation=0;
reg [15:0] sm_done=0, sm_fault=0,res_v=0;
reg [511:0] res_data=0;
wire db_rdy,cpl_v;
wire [15:0] launch_v;
wire [31:0] launch_pc,cpl_job,cpl_cycles,st_kernels,st_busy;
wire [17:0] launch_token,cpl_token;
wire [19:0] launch_pos,cpl_position;
wire [3:0] cpl_status,cpl_generation;
`ifdef SRAM
 ot_qwen_r25_cmdproc18_m #(.ENABLE(1),.NSM(16),.RDREG(2)) dut(.*);
`else
 ot_qwen_r25_cmdproc18 #(.ENABLE(1),.NSM(16)) dut(.*);
`endif
// INT8 embedding row has 4096 bytes, scales have 2 bytes; full 64-bit addresses.
wire [63:0] embed_addr = 64'h100000000 + (64'(launch_token)<<12);
wire [63:0] scale_addr = 64'h200000000 + (64'(launch_token)<<1);
integer token,i,ncycle,launch_count=0,step_cycles,min_cycles=1000,max_cycles=0;
reg [31:0] result_token;
task tick; begin @(posedge clk); #0.1; @(negedge clk); end endtask
task run(input integer tok,input reg [31:0] result,input integer status);
 begin
 db_token=tok;db_pos=20'hfffff;db_job=32'hfedcba98;db_generation=4'hd;db_v=1; tick;db_v=0;
 step_cycles=0;
 while(!cpl_v) begin
  if(launch_v) begin
   launch_count=launch_count+1;
   if(launch_token!==tok || launch_pos!==20'hfffff || launch_pc!==32'h1234 || launch_v!==16'hffff)
    $fatal(1,"LAUNCH_TRUNCATION token=%0d got=%0d",tok,launch_token);
   if(embed_addr !== (64'h100000000+64'(tok)*4096) || scale_addr !== (64'h200000000+64'(tok)*2))
    $fatal(1,"EMBEDDING_ROW_TRUNCATION token=%0d",tok);
   sm_done=16'hffff;res_v=16'h8000;res_data[480+:32]=result;
  end else begin sm_done=0;res_v=0;end
  tick;step_cycles=step_cycles+1;
  if(step_cycles>50)$fatal(1,"component protocol failed to complete");
 end
 sm_done=0;res_v=0;
 if(cpl_status!==status || (status==0 && cpl_token!==result) || cpl_job!==db_job || cpl_generation!==db_generation)
  $fatal(1,"CPL_TRUNCATION token=%0d result=%0d got=%0d status=%0d expected=%0d",tok,result,cpl_token,cpl_status,status);
 if(step_cycles<min_cycles)min_cycles=step_cycles;
 if(step_cycles>max_cycles)max_cycles=step_cycles;
 // Stable token/status/identity with completion backpressure.
 repeat(2)begin tick;if(!cpl_v || (status==0 && cpl_token!==result))$fatal(1,"completion lost under stall");end
 cpl_rdy=1;tick;cpl_rdy=0;
 if(!db_rdy)$fatal(1,"retire not idle");
 end
endtask
initial begin
 tick;tick;rst_n=1;
 cmd_we=1;cmd_addr=0;cmd_wdata=(64'd1<<60)|(64'hffff<<44)|64'h1234;tick;
 cmd_addr=1;cmd_wdata=64'd2<<60;tick;cmd_we=0;
 for(token=0;token<151936;token=token+1)run(token,token,0);
 run(151935,151936,3);run(151935,262144,3);
 // Invalid doorbells must refuse before any launch.
 i=launch_count;run(151936,0,3);run(262143,0,3);
 if(i!==launch_count)$fatal(1,"invalid embedding index launched");
 $display("QWEN_CMDPROC18_PASS exhaustive_tokens=151936 launches=%0d min_cycles=%0d max_cycles=%0d invalid_inputs=2 invalid_results=2 backpressure=2",launch_count,min_cycles,max_cycles);
 $finish;
end
endmodule
