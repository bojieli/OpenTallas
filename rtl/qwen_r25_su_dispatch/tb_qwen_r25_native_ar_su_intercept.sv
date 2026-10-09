`timescale 1ps/1fs
module tb_qwen_r25_native_ar_su_intercept #(parameter TOKEN=131072,FIRST_POS=524288,MUT=0);
 localparam SAME=(TOKEN==151935);
 reg clk=0;always #417 clk=~clk;
 reg rst_n=0,job_v=0;wire job_rdy,hr_v,busy,identity_fault,intercept_fault;
 wire [74:0] hr_d;wire [2:0] last_status;wire [31:0] st_tokens,st_hq_stall;
 reg [1:0] cmd_we=0;reg [15:0] cmd_addr=0;reg [127:0] cmd_wdata=0;
 wire [31:0] sm_launch_v;wire [63:0] sm_launch_pc;wire [147:0] sm_launch_owner;
 reg [31:0] sm_done=0,sm_fault=0,res_v=0;reg [1023:0] res_data=0;
 wire native_req_v,native_complete_rdy;wire [31:0] native_req_pc;
 wire [73:0] native_req_owner;reg native_complete_v=0;reg [73:0] native_complete_owner=0;
 wire native_req_rdy=!native_complete_v&&native_wait==0;
 integer native_wait=0,native_calls=0,sm_calls=0,records=0,h;
 integer sm_wait[0:1];reg [17:0] sm_result[0:1];
 ot_qwen_r25_native_ar_su_intercept #(.ENABLE(1)) dut(
  .clk(clk),.rst_n(rst_n),.post_en(1'b1),.external_fault(1'b0),
  .job_v(job_v),.job_rdy(job_rdy),.job_id(32'hfedcba98),.job_tok(18'(TOKEN)),
  .job_eos(18'd0),.job_pos(20'(FIRST_POS)),.job_ngen(20'd2),.job_eos_en(1'b0),
  .job_maxpos(21'd1048576),.job_generation(4'd9),.host_stop(1'b0),
  .hr_v(hr_v),.hr_rdy(1'b1),.hr_d(hr_d),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),
  .sm_launch_v(sm_launch_v),.sm_launch_pc(sm_launch_pc),.sm_launch_owner(sm_launch_owner),
  .sm_done(sm_done),.sm_fault(sm_fault),.res_v(res_v),.res_data(res_data),
  .native_req_v(native_req_v),.native_req_rdy(native_req_rdy),.native_req_pc(native_req_pc),
  .native_req_owner(native_req_owner),.native_complete_v(native_complete_v),
  .native_complete_rdy(native_complete_rdy),.native_complete_owner(native_complete_owner),
  .native_fault(1'b0),.busy(busy),.last_status(last_status),.st_tokens(st_tokens),
  .st_hq_stall(st_hq_stall),.identity_fault(identity_fault),.intercept_fault(intercept_fault));
 always @(posedge clk)if(rst_n)begin
  sm_done<=0;res_v<=0;
  if(native_complete_v&&native_complete_rdy)native_complete_v<=0;
  if(native_wait>0)begin
   native_wait<=native_wait-1;
   if(native_wait==1)native_complete_v<=1;
  end
  if(native_req_v&&native_req_rdy)begin
   if(native_req_pc!==32'h53550000||native_req_owner!=={20'(FIRST_POS+native_calls),18'(TOKEN+(SAME?0:native_calls)),4'd9,32'hfedcba98})
    $fatal(1,"actual CP owner or source-defined entry lost");
   native_complete_owner<=native_req_owner^(MUT?(74'd1<<53):74'd0);
   native_wait<=6;native_calls=native_calls+1;
  end
  for(h=0;h<2;h=h+1)begin
   if(|sm_launch_v[h*16+:16])begin
    if(sm_launch_v[h*16+:16]!=16'hffff||sm_launch_pc[h*32+:32]!=32'habc123)
     $fatal(1,"SU CP entry leaked to ordinary SM");
    if(sm_launch_owner[h*74+:74]!=={20'(FIRST_POS+records),18'(TOKEN+(SAME?0:records)),4'd9,32'hfedcba98})$fatal(1,"ordinary SM owner changed");
    sm_result[h]<=18'(TOKEN+(SAME?0:records+1));sm_wait[h]<=3+h;sm_calls=sm_calls+1;
   end else if(sm_wait[h]>0)begin
    sm_wait[h]<=sm_wait[h]-1;
    if(sm_wait[h]==2)begin res_v[h*16]<=1;res_data[h*512+:32]<=sm_result[h];end
    if(sm_wait[h]==1)sm_done[h*16+:16]<=16'hffff;
   end
  end
  if(hr_v&&!MUT)begin
   if(hr_d[17:0]!==TOKEN+(SAME?0:records+1)||hr_d[18+:21]!==FIRST_POS+records+1||hr_d[39+:32]!==32'hfedcba98)
    $fatal(1,"actual AR token record corrupt");
   records=records+1;
  end
 end
 initial begin
  sm_wait[0]=0;sm_wait[1]=0;repeat(5)@(negedge clk);rst_n=1;
  // The south half has one real NOP before SU, so actual CP launch pulses stagger.
  @(negedge clk);cmd_we=3;cmd_addr=0;cmd_wdata={64'd0,64'h1ffff00053550000};
  @(negedge clk);cmd_addr={8'd1,8'd1};cmd_wdata={64'h1ffff00053550000,64'h1ffff00000abc123};
  @(negedge clk);cmd_addr={8'd2,8'd2};cmd_wdata={64'h1ffff00000abc123,64'h2000000000000000};
  @(negedge clk);cmd_addr={8'd3,8'd3};cmd_wdata={64'h2000000000000000,64'h2000000000000000};
  @(negedge clk);cmd_we=0;job_v=1;@(negedge clk);job_v=0;
  if(MUT)begin
   wait(intercept_fault);repeat(3)@(negedge clk);
   if(native_calls!=1||sm_calls!=0||dut.cp_done)$fatal(1,"foreign native completion admitted");
   $display("PASS_QWEN_REAL_CP_SU_INTERCEPT_FOREIGN_OWNER_FENCE");$finish;
  end
  wait(records==2);repeat(4)@(negedge clk);
  if(busy||identity_fault||intercept_fault||native_calls!=2||sm_calls!=4||st_tokens!=2)
   $fatal(1,"actual CP/SU AR counter or completion mismatch");
  $display("PASS_QWEN_REAL_CP_SU_INTERCEPT TOKEN%0d POS%0d native_calls%0d SMcalls%0d records%0d",TOKEN,FIRST_POS,native_calls,sm_calls,records);
  $finish;
 end
 initial begin repeat(10000)@(posedge clk);$fatal(1,"bounded synthetic provider did not complete actual CP");end
endmodule
