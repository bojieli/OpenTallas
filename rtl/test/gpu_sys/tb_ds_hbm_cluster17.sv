`timescale 1ps/1ps
// Necessary connected width gate: actual CP -> actual SM UR0 -> RESULT -> CP.
// Four real clock domains and inherited memory/collective components. This is
// NOT DS numerical/full-token evidence; no checkpoint or golden execution.
module tb_ds_hbm_cluster17;
 reg ch=0,cs=0,cm=0,cl=0,por=0;
 always #2000 ch=~ch;
 always begin #416 cs=1;#417 cs=0;end
 always #500 cm=~cm;
 always #450 cl=~cl;
 reg [1:0] cw=0,dv=0,cr=0;
 reg [15:0] ca=0;
 reg [127:0] cd=0;
 reg [33:0] dt=0;
 reg [31:0] dp=0;
 wire [1:0] dr,cv;
 wire [105:0] completion;
 reg [3:0] iw=0;reg [13:0] ia=0;reg [63:0] id=0;
 wire rn,fault;
 ot_ds_hbm_cluster17 #(.ENABLE(1),.MEM_WORDS(1024)) dut(
 .por_n(por),.clk_host(ch),.clk_sm(cs),.clk_mem(cm),.clk_link(cl),
 .cmd_we(cw),.cmd_addr(ca),.cmd_wdata(cd),.db_v(dv),.db_rdy(dr),.db_token(dt),.db_pos(dp),
 .cpl_v(cv),.cpl_rdy(cr),.cpl_data(completion),.im_we(iw),.im_addr(ia),.im_data(id),
 .rst_sm_n(rn),.sys_fault(fault));
 task automatic instruction(input integer pc,input reg [63:0] word);
  @(negedge cs);iw=4'b1111;ia=pc;id=word;
  @(negedge cs);iw=0;
 endtask
 task automatic command(input integer addr,input reg [63:0] word);
  @(negedge cs);cw=3;ca={8'(addr),8'(addr)};cd={word,word};
  @(negedge cs);cw=0;
 endtask
 task automatic run_case(input reg [16:0] token,input integer status);
  wait(dr==3);
  @(negedge cs);dt={token,token};dp={16'd37,16'd37};dv=3;
  @(negedge cs);dv=0;
  wait(cv==3);
  for(integer d=0;d<2;d=d+1) begin
   if(completion[d*53+17+:4]!==4'(status)) $fatal(1,"actual completion status");
   if(status==0 && completion[d*53+:17]!==token) $fatal(1,"token17 truncated");
  end
  if(fault) $fatal(1,"connected cluster fault");
  $display("ACTUAL_CLUSTER17 token=%0d status=%0d PASS",token,status);
  @(negedge cs);cr=3;
  @(negedge cs);cr=0;
 endtask
 initial begin
  #20000 por=1;
  wait(rn);
  instruction(0,64'h3500000000000000); // RESULT actual UR0
  instruction(1,64'h3200000000000000); // EXIT
  command(0,64'h1000300000000000); // LAUNCH both SMs, PC0
  command(1,64'h2000000000000000);
  run_case(17'd65535,0);run_case(17'd65536,0);
  run_case(17'd128799,0);run_case(17'd131071,0);
  instruction(0,64'h2800000000020000); // UMOVI UR0,131072: illegal RESULT17
  instruction(1,64'h3500000000000000);
  instruction(2,64'h3200000000000000);
  run_case(17'd17,3);
  $display("PASS_CONNECTED_COMMAND_SM_TOKEN17 scope=width_only no_full_token_claim");
  $finish;
 end
endmodule
