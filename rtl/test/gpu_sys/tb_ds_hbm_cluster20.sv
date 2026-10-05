`timescale 1ps/1ps
// Necessary connected width gate: actual CP -> actual SM UR0 -> RESULT -> CP.
// Four real clock domains and inherited memory/collective components. This is
// NOT DS numerical/full-token evidence; no checkpoint or golden execution.
module tb_ds_hbm_cluster20;
 reg ch=0,cs=0,cm=0,cl=0,por=0;
 always #2000 ch=~ch;
 always begin #416 cs=1;#417 cs=0;end
 always #500 cm=~cm;
 always #450 cl=~cl;
 reg [1:0] cw=0,dv=0,cr=0;
 reg [15:0] ca=0;
 reg [127:0] cd=0;
 reg [63:0] dt=0;
 reg [63:0] dp=0;reg [63:0] job=0;reg [7:0] generation=0;
 wire [1:0] dr,cv;
 wire [217:0] completion;
 reg [3:0] iw=0;reg [13:0] ia=0;reg [63:0] id=0;
 wire rn,fault;
 ot_ds_hbm_source_entry20 #(.ENABLE(1),.MEM_WORDS(1024)) dut(
 .por_n(por),.clk_host(ch),.clk_sm(cs),.clk_mem(cm),.clk_link(cl),
 .cmd_we(cw),.cmd_addr(ca),.cmd_wdata(cd),.db_v(dv),.db_rdy(dr),.db_token(dt),.db_pos(dp),.db_job(job),.db_generation(generation),
 .cpl_v(cv),.cpl_rdy(cr),.cpl_data(completion),.im_we(iw),.im_addr(ia),.im_data(id),
 .rst_sm_n(rn),.fault(fault));
 task automatic instruction(input integer pc,input reg [63:0] word);
  @(negedge cs);iw=4'b1111;ia=pc;id=word;
  @(negedge cs);iw=0;
 endtask
 task automatic command(input integer addr,input reg [63:0] word);
  @(negedge cs);cw=3;ca={8'(addr),8'(addr)};cd={word,word};
  @(negedge cs);cw=0;
 endtask
 task automatic run_case(input reg [16:0] token,input integer status,input reg [31:0] position);
  wait(dr==3);
  @(negedge cs);dt={{15'b0,token},{15'b0,token}};dp={position,position};job={32'hfedcba98,32'hfedcba98};generation=8'hff;dv=3;
  @(negedge cs);dv=0;
  wait(cv==3);
  for(integer d=0;d<2;d=d+1) begin
   if(completion[d*109+37+:4]!==4'(status)) $fatal(1,"actual completion status");
   if(completion[d*109+17+:20]!==position[19:0] || completion[d*109+77+:32]!==32'hfedcba98 ||
      completion[d*109+73+:4]!==4'hf) $fatal(1,"actual position/job/generation identity");
   if(status==0 && completion[d*109+:17]!==token) $fatal(1,"token17 truncated");
  end
  if(fault) $fatal(1,"connected cluster fault");
  $display("ACTUAL_CLUSTER20 token=%0d status=%0d PASS",token,status);
  @(negedge cs);cr=3;
  @(negedge cs);cr=0;
 endtask
 for(genvar d=0;d<2;d=d+1) begin:g_check_die
  for(genvar k=0;k<2;k=k+1) begin:g_check_sm
   always @(posedge cs) if(cv[d]) begin
    if(dut.u_cluster.g_on.g_die[d].g_sm[k].u_sm.g_on.ur[1] !== dp[d*32+:32])
     $fatal(1,"actual UR1 POS20 narrowed");
   end
  end
 end
 initial begin
  #20000 por=1;
  wait(rn);
  instruction(0,64'h3500000000000000); // RESULT actual UR0
  instruction(1,64'h3200000000000000); // EXIT
  command(0,64'h1000300000000000); // LAUNCH both SMs, PC0
  command(1,64'h2000000000000000);
  run_case(17'd65535,0,20'd65535);run_case(17'd65536,0,20'd65536);
  run_case(17'd128799,0,20'd1048575);run_case(17'd131071,0,20'd1000000);
  instruction(0,64'h2800000000020000); // UMOVI UR0,131072: illegal RESULT17
  instruction(1,64'h3500000000000000);
  instruction(2,64'h3200000000000000);
  run_case(17'd17,3,20'd1048575);
  @(negedge cs);dp={32'd1048576,32'd1048576};dt={32'd128799,32'd128799};dv=3;
  @(negedge cs);dv=0;
  if(!fault || cv!=0 || dr!=0) $fatal(1,"source MAXPOSITION silently narrowed");
  if(dut.u_cluster.g_on.g_die[0].u_cp.st_kernels!=5 || dut.u_cluster.g_on.g_die[1].u_cp.st_kernels!=5)
   $fatal(1,"refused position launched a kernel");
  $display("ACTUAL_SOURCE_MAXPOSITION 1048576 REJECTED_NO_LAUNCH");
  $display("PASS_CONNECTED_COMMAND_SM_TOKEN17_POS20 scope=width_only no_full_token_claim");
  $finish;
 end
endmodule
