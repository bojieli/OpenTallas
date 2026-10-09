`timescale 1ps/1fs
module tb_hbm_native_ar_token_join #(parameter QWEN=0,MUT=0);
 localparam TW=QWEN?18:17;
 reg clk=0;always #417 clk=~clk;
 reg rst_n=0,job_v=0,hr_rdy=0,external_fault=0;
 wire job_rdy,hr_v,busy,identity_fault;wire [TW+56:0] hr_d;
 reg [1:0] cmd_we=0;reg [15:0] cmd_addr=0;reg [127:0] cmd_wdata=0;
 wire [31:0] launch_v;wire [63:0] launch_pc;wire [2*TW-1:0] launch_token;
 wire [39:0] launch_pos;reg [31:0] sm_done=0,sm_fault=0,res_v=0;reg [1023:0] res_data=0;
 wire [2:0] status;wire [31:0] st_tokens,st_stall;
 localparam [TW-1:0] FIRST=QWEN?150000:128000;
 ot_hbm_native_ar_token_join #(.ENABLE(1),.QWEN(QWEN)) dut(
 .clk(clk),.rst_n(rst_n),.post_en(1'b1),.external_fault(external_fault),
 .job_v(job_v),.job_rdy(job_rdy),.job_id(32'hfedcba98),.job_tok(FIRST),.job_pos(20'd1234),
 .job_ngen(20'd12),.job_eos({TW{1'b0}}),.job_eos_en(1'b0),.job_maxpos(21'd1048576),.job_generation(4'd9),
 .host_stop(1'b0),.hr_v(hr_v),.hr_rdy(hr_rdy),.hr_d(hr_d),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),
 .launch_v(launch_v),.launch_pc(launch_pc),.launch_token(launch_token),.launch_pos(launch_pos),
 .sm_done(sm_done),.sm_fault(sm_fault),.res_v(res_v),.res_data(res_data),.busy(busy),.last_status(status),
 .st_tokens(st_tokens),.st_hq_stall(st_stall),.identity_fault(identity_fault));
 integer nrec=0,nlaunch=0,stall=500;integer wait_count[0:1];integer k;
 reg [TW-1:0] result[0:1];
 always @(posedge clk) begin
  sm_done<=0;res_v<=0;
  if(stall>0) stall<=stall-1;else hr_rdy<=1;
  for(k=0;k<2;k=k+1) begin
   if(|launch_v[k*16+:16]) begin
    if(launch_v[k*16+:16]!=16'hffff || launch_pc[k*32+:32]!=32'habc123)$fatal(1,"launch ABI");
    result[k]<=launch_token[k*TW+:TW]+1+((MUT && k==1)?1:0);
    wait_count[k]<=3+k;
    nlaunch=nlaunch+1;
   end else if(wait_count[k]>0) begin
    wait_count[k]<=wait_count[k]-1;
    if(wait_count[k]==2) begin res_v[k*16]<=1;res_data[k*512+:32]<=result[k];end
    if(wait_count[k]==1) sm_done[k*16+:16]<=16'hffff;
   end
  end
  if(hr_v && hr_rdy) begin
   if(hr_d[TW-1:0]!==FIRST+nrec+1 || hr_d[TW+:21]!==21'd1235+nrec ||
      hr_d[TW+21+:32]!==32'hfedcba98)$fatal(1,"token/job/position corrupt");
   if(hr_d[TW+56] !== (nrec==11) || hr_d[TW+53+:3] !== ((nrec==11)?3'd2:3'd0))$fatal(1,"terminal record");
   nrec=nrec+1;
  end
 end
 initial begin
  wait_count[0]=0;wait_count[1]=0;
  repeat(5) @(negedge clk);rst_n=1;
  @(negedge clk);cmd_we=3;cmd_addr=0;cmd_wdata={64'h1ffff00000abc123,64'h1ffff00000abc123};
  @(negedge clk);cmd_addr={8'd1,8'd1};cmd_wdata={64'h2000000000000000,64'h2000000000000000};
  @(negedge clk);cmd_we=0;job_v=1;
  @(negedge clk);job_v=0;
  wait(nrec==12);repeat(4) @(negedge clk);
  if(busy || nlaunch!=24 || st_tokens!=12 || st_stall==0)$fatal(1,"runtime counters/backpressure");
  $display("PASS native AR QWEN=%0d records=%0d launches=%0d stalls=%0d",QWEN,nrec,nlaunch,st_stall);$finish;
 end
 initial begin repeat(10000) @(posedge clk);$fatal(1,"watchdog");end
endmodule
