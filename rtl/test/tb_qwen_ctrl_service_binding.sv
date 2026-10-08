`timescale 1ns/1ps
module tb_qwen_ctrl_service_binding;
 parameter integer PC=0, NEG=0, BAD=0, GUARD=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cmd_v=0;reg[31:0]cmd=0;reg[2:0]read_credit=0;
 wire cmd_credit,row_v,col_v,col_we,busy,fault;
 wire[2:0]row_op;wire[4:0]row_bank,col_bank,col_col;wire[18:0]row_row;

 reg w_v=0;reg[23:0]w_sec=0;reg[255:0]w_data=0;reg[8:0]w_tag=0;
 wire w_room,sched_v;wire[4:0]sched_bank,sched_col;
 wire sched_take=cmd_v && cmd[31:30]==2;
 wire phy_row_v,phy_col_v,phy_col_we;wire[2:0]phy_row_op;
 wire[4:0]phy_row_bank,phy_col_bank,phy_col_col;wire[18:0]phy_row_row;
 wire[23:0]phy_w_sec;wire[255:0]phy_w_data;wire[8:0]phy_w_tag;
 reg done_v=0;reg[8:0]done_tag=0;wire wd_v;wire[8:0]wd_tag;
 wire stop,quarantine,refresh_req,epoch_ready;reg refresh_ack=0,upstream_quiescent=0,epoch_advance=0;
 wire[4:0]cancel_count;wire[6:0]committed_count;
 ot_qwen_ctrl_write_service_pc #(.ENABLE(1),.PC(PC)) service(.*);
 integer sent=0,acked=0,reads=0,writes=0,dones=0;
 reg faulted=0;
 reg[23:0]first_sec;reg[255:0]first_data=256'h0123456789abcdef;reg[8:0]first_tag=9'h101;
 function automatic[23:0] sector(input[4:0]bank,input[4:0]col);
 reg[14:0]s;begin s={bank[4:2],col,5'(PC),bank[1:0]};sector={7'd7,s[7],s[6],2'b0,s[14:8],s[5:0]};end endfunction
 task fail(input[255:0]msg);begin $display("FAIL binding PC=%0d %s",PC,msg);$fatal(1);end endtask
 always @(posedge clk)if(rst_n)begin
  if(cmd_v)sent=sent+1;
  if(cmd_credit)acked=acked+1;
  if(quarantine)fail("unexpected ledger quarantine");
  if(phy_col_v && !phy_col_we)reads=reads+1;
  if(phy_col_we)begin
   writes=writes+1;
   if(writes!=1 || faulted || phy_w_sec!==first_sec || phy_w_data!==first_data || phy_w_tag!==first_tag)fail("wrong actual accepted WR");
  end
  if(wd_v)begin dones=dones+1;if(!done_v || wd_tag!==first_tag || wd_tag!==done_tag || !faulted)fail("completion custody");end
  if(faulted && (phy_row_v || phy_col_v || w_room || sched_v))fail("work escaped after abort");
 end
 task send(input[31:0]p);begin
  @(negedge clk);while(sent-acked>=8)@(negedge clk);cmd=p;cmd_v=1;
  @(negedge clk);cmd_v=0;
 end endtask
 task enqueue(input[23:0]sec,input[255:0]data,input[8:0]tag);begin
  @(negedge clk);while(!w_room)@(negedge clk);w_sec=sec;w_data=data;w_tag=tag;w_v=1;
  @(negedge clk);w_v=0;
 end endtask
 initial begin
  first_sec=sector(0,0);
  repeat(4)@(negedge clk);rst_n=1;
  send({2'b00,11'd32,19'd7});send({2'b01,30'b0});
  wait(reads==32);
  enqueue(first_sec,first_data,first_tag);
  enqueue(sector(1,0),256'hffffffff,9'h102);
  if(BAD)begin
   wait(sched_v);send({2'b10,20'd0,sched_col,5'(sched_bank^1)});
   repeat(4)@(negedge clk);
   if(!fault || !stop || !refresh_req || writes!=0 || dones!=0)fail("malformed offered WR accepted");
   $display("PASS service malformed WR stopped before scheduler admission PC=%0d",PC);$finish;
  end
  wait(sched_v);send({2'b10,20'd0,sched_col,sched_bank});
  // The second write remains accepted native work but is never handed off.
  wait(writes==1);@(negedge clk);#0.1;
  if(GUARD==1)service.contract_trip=1;
  else if(GUARD==2)service.contract_permit=0;
  else service.controller.trip_seen=1;
  faulted=1;
  repeat(3)@(negedge clk);
  if(!stop || !refresh_req || committed_count!=1 || cancel_count!=1 || dones!=0)fail("abort ownership ledger");
  refresh_ack=1;upstream_quiescent=1;epoch_advance=1;
  repeat(3)@(negedge clk);
  if(epoch_ready || committed_count!=1 || dones!=0)fail("ACK fabricated drain");
  if(NEG)force service.ownership.done_bad=0;
  done_tag=NEG?9'h103:first_tag;done_v=1;
  @(negedge clk);done_v=0;
  repeat(3)@(negedge clk);
  if(committed_count!=0 || dones!=1 || epoch_ready || !refresh_req || !fault)fail("true done drain gate");
  $display("PASS binding PC=%0d accepted_wr=%0d true_done=%0d canceled_unissued=%0d refresh_req=%b epoch_blocked=%b",PC,writes,dones,cancel_count,refresh_req,!epoch_ready);$finish;
 end
 initial begin #100000;fail("watchdog");end
endmodule
