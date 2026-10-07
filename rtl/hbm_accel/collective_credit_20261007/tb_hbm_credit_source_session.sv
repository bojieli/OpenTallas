`timescale 1ns/1ps
module tb_hbm_credit_source_session;
 import ot_hbm_credit_secded_pkg::*;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg[23:0]epoch=1;
 reg retire=0,reserve=0;
 wire retire_ready,reserve_ready,gv,gr,av,ar,rf,sf,debt_zero,initial_ack_seen;
 wire[71:0]gw,aw;
 reg gate_g=1,gate_a=1;
 reg override_g=0,override_a=0;reg[71:0]test_g,test_a;
 ot_hbm_credit_rx #(.ENABLE(1)) rx(clk,rst_n,start,epoch,retire,retire_ready,
 gv,gr&&gate_g&&!override_g,gw,(override_a||av)&&gate_a,ar,override_a?test_a:aw,rf);
 ot_hbm_credit_source_session #(.ENABLE(1)) src(clk,rst_n,start,epoch,reserve,reserve_ready,
 (override_g||gv)&&gate_g,gr,override_g?test_g:gw,av,ar&&gate_a&&!override_a,aw,debt_zero,initial_ack_seen,sf);
 wire off_g,off_r,off_a,off_f;
 ot_hbm_credit_source off(clk,rst_n,start,epoch,1'b1,off_r,1'b1,off_g,gw,off_a,1'b1,,off_f);
 integer launches=0,retires=0,peak=0,i,j,b;
 reg accounting=1;
 always @(posedge clk)if(rst_n&&accounting)begin
  if(reserve&&reserve_ready)launches=launches+1;
  if(retire&&retire_ready)retires=retires+1;
  if(launches-retires>peak)peak=launches-retires;
  if(launches-retires>64||retires>launches)$fatal(1,"conservation launched=%0d retired=%0d",launches,retires);
  if(off_g||off_r||off_a||off_f)$fatal(1,"default off");
 end
 task step;begin @(posedge clk);#1;end endtask
 task reset;begin
  @(negedge clk);rst_n=0;start=0;reserve=0;retire=0;override_g=0;override_a=0;gate_g=1;gate_a=1;
  launches=0;retires=0;step;@(negedge clk);rst_n=1;start=1;step;@(negedge clk);start=0;
 end endtask
 task settle;begin repeat(8)step;if(rf||sf)$fatal(1,"unexpected fault");end endtask
 task sendgrant(input[71:0]w);begin
  @(negedge clk);override_g=1;test_g=w;
  while(!gr)step;step;@(negedge clk);override_g=0;repeat(3)step;
 end endtask
 task sendack(input[71:0]w);begin
  @(negedge clk);override_a=1;test_a=w;step;@(negedge clk);override_a=0;repeat(2)step;
 end endtask
 initial begin
  reset;gate_a=0;repeat(5)step;
  if(reserve_ready||!av)$fatal(1,"initial ACK held gating");
  gate_a=1;settle;
  @(negedge clk);reserve=1;repeat(80)step;
  if(launches!=64||reserve_ready)$fatal(1,"64 window exhaustion");
  @(negedge clk);reserve=0;
  sendgrant(encode64({8'h47,epoch,24'd0,8'd64}));
  if(reserve_ready||sf)$fatal(1,"duplicate minted credit");
  sendgrant(encode64({8'h47,24'd0,24'd99,8'd64}));
  sendack(encode64({8'h41,24'd0,24'd99,8'd64}));
  if(sf||rf||reserve_ready)$fatal(1,"stale generation");
  // Multiple retirements while ACK held accumulate and replenish exactly once.
  gate_a=0;@(negedge clk);retire=1;repeat(64)step;@(negedge clk);retire=0;
  if(retires!=64)$fatal(1,"retirement while ACK held");
  gate_a=1;settle;settle;
  @(negedge clk);reserve=1;repeat(80)step;@(negedge clk);reserve=0;
  if(launches!=128||reserve_ready)$fatal(1,"returned window");
  // Flow stalls under alternating link handshake, with randomized retirement.
  reset;settle;@(negedge clk);reserve=1;
  for(i=0;i<1500;i=i+1)begin
   @(negedge clk);retire=(launches>retires)&&(($random&3)!=0);
   gate_g=($random&3)!=0;gate_a=($random&3)!=0;step;
   if(rf||sf)$fatal(1,"random flow fault");
  end
  @(negedge clk);reserve=0;retire=0;gate_g=1;gate_a=1;settle;
  $display("METRIC local_random_flow1500 launched=%0d retired=%0d outstanding=%0d",launches,retires,launches-retires);
  // Scrub cannot lose either source-side observation; wrapper guards effects.
  reset;settle;
  if(!debt_zero||!initial_ack_seen)$fatal(1,"initial grant counted as debt");
  @(negedge clk);src.debt.state_q=src.debt.state_q^72'd1;reserve=1;
  #1;if(reserve_ready||gr||debt_zero)$fatal(1,"debt CE failed to guard effects");
  step;@(negedge clk);reserve=0;settle;
  if(!debt_zero||launches!=0)$fatal(1,"scrub lost reservation observation");
  @(negedge clk);reserve=1;step;@(negedge clk);reserve=0;
  if(debt_zero)$fatal(1,"reservation absent from debt");
  @(negedge clk);retire=1;step;@(negedge clk);retire=0;settle;settle;
  if(!debt_zero)$fatal(1,"returned grant failed to discharge debt");
  @(negedge clk);src.debt.state_q=src.debt.state_q^72'd3;step;
  if(!sf||reserve_ready||gr||debt_zero)$fatal(1,"debt UE failclosed");
  // Changed count duplicate is a fault, never another grant.
  reset;settle;sendgrant(encode64({8'h47,epoch,24'd0,8'd63}));
  if(!sf||reserve_ready)$fatal(1,"changed duplicate not rejected");
  reset;settle;sendgrant(encode64({8'h47,epoch,24'd2,8'd1}));if(!sf)$fatal(1,"sequence skip");
  reset;settle;sendgrant(encode64({8'h47,epoch,24'd1,8'd1}));if(!sf)$fatal(1,"credit overflow");
  reset;settle;sendgrant(encode64({8'h47,epoch,24'd1,8'd0}));if(!sf)$fatal(1,"zero count");
  reset;settle;sendack(encode64({8'h41,epoch,24'd0,8'd63}));if(!rf)$fatal(1,"wrong ACK count");
  // Single codeword-bit faults on incoming initial grant, including parity.
  for(j=0;j<72;j=j+1)begin
   reset;gate_g=0;repeat(2)step;
   test_g=encode64({8'h47,epoch,24'd0,8'd64})^(72'b1<<j);
   @(negedge clk);override_g=1;gate_g=1;step;@(negedge clk);override_g=0;gate_g=0;
   repeat(3)step;if(sf||!reserve_ready)$fatal(1,"message CE %0d",j);
  end
  // Every double-bit pair detected on incoming grant.
  for(i=0;i<72;i=i+1)for(j=i+1;j<72;j=j+1)begin
   reset;gate_g=0;repeat(2)step;
   test_g=encode64({8'h47,epoch,24'd0,8'd64})^(72'b1<<i)^(72'b1<<j);
   @(negedge clk);override_g=1;gate_g=1;step;
   if(!sf||reserve_ready)$fatal(1,"message UE %0d %0d",i,j);
  end
  // All state words and all bit positions: scrub before any permission.
  for(b=0;b<6;b=b+1)for(j=0;j<72;j=j+1)begin
   reset;settle;@(negedge clk);
   case(b)
    0:src.source.control_q=src.source.control_q^(72'b1<<j);
    1:src.source.account_q=src.source.account_q^(72'b1<<j);
    2:src.source.message_q=src.source.message_q^(72'b1<<j);
    3:rx.control_q=rx.control_q^(72'b1<<j);
    4:rx.account_q=rx.account_q^(72'b1<<j);
    5:rx.message_q=rx.message_q^(72'b1<<j);
   endcase
   #1;if(b<3 ? (reserve_ready||gr||av):(retire_ready||gv||ar))$fatal(1,"state CE permission %0d %0d",b,j);
   step;if(sf||rf)$fatal(1,"state CE fault");
   if(!reserve_ready||!retire_ready)$fatal(1,"state CE repair");
  end
  // ACK message CE and UE use identical codec but independent receive control.
  for(j=0;j<72;j=j+1)begin
   reset;gate_a=0;repeat(4)step;
   sendack(encode64({8'h41,epoch,24'd0,8'd64})^(72'b1<<j));
   // sendack preserves gate_a; explicitly transact held message.
   @(negedge clk);override_a=1;test_a=encode64({8'h41,epoch,24'd0,8'd64})^(72'b1<<j);gate_a=1;
   step;@(negedge clk);override_a=0;
   if(rf)$fatal(1,"ACK CE");
  end
  for(j=1;j<72;j=j+1)begin
   reset;gate_a=0;repeat(4)step;
   @(negedge clk);override_a=1;test_a=encode64({8'h41,epoch,24'd0,8'd64})^72'b1^(72'b1<<j);gate_a=1;
   step;if(!rf)$fatal(1,"ACK UE");
  end
  // State CE repairs with permissions suppressed, UE latches fail closed.
  reset;settle;@(negedge clk);src.source.account_q=src.source.account_q^72'd1;
  #1;if(reserve_ready)$fatal(1,"CE permission");step;if(sf||!reserve_ready)$fatal(1,"CE repair");
  @(negedge clk);rx.account_q=rx.account_q^72'd1;
  #1;if(retire_ready||gv||ar)$fatal(1,"RX CE permission");step;if(rf||!retire_ready)$fatal(1,"RX CE repair");
  @(negedge clk);src.source.control_q=src.source.control_q^72'd3;step;if(!sf||reserve_ready)$fatal(1,"state UE");
  reset;settle;@(negedge clk);rx.message_q=rx.message_q^72'd3;step;if(!rf||retire_ready)$fatal(1,"RX state UE");
  reset;settle;@(negedge clk);start=1;step;if(!rf||!sf)$fatal(1,"rearm regrant");
  epoch=2;reset;settle;sendgrant(encode64({8'h47,24'd1,24'd0,8'd64}));
  if(sf||rf)$fatal(1,"old epoch after cold reset");
  $display("PASS source session: window64, flow1500, grant CE72/UE2556, ACK CE72/UE71, state CE432/repair/fault, held ACK, duplicate, stale, reset, defaultoff; peak=%0d",peak);$finish;
 end
 initial begin #2000000;$fatal(1,"testbench watchdog");end
endmodule
