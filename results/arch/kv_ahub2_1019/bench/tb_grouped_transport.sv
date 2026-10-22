`timescale 1ns/1ps
module tb_grouped_transport;
 parameter integer W=268, MUT=0, INIT_CASE=1;
 // KV-AHUB2 10-19: resets start HIGH and fall at 0.2 ns so every async-reset flop (DUT, predecessor and the
 // reference recurrence) sees a real negedge in BOTH simulators.  Attempt1 declared them =0: Icarus raises no event
 // for a declaration initialiser, so the frozen 4415 predecessor's ot_rst faces stayed X and all 8 four-state runs
 // FAILed predecessor_frontier at cycle 0 (Verilator 2-state randomised them and passed).  No clock edge before 5 ns.
 reg clk=0, tx_rst_n=1,rx_rst_n=1,in_valid=1;
 initial #0.2 begin tx_rst_n=0; rx_rst_n=0; end
 reg [W-1:0] d='1;
 wire [W-1:0] q;
 wire out_valid,accept,pred_accept;
 generate if(W==268) begin:g_cmd
  qkd_ahub_grouped_zh_transport_private #(.ENABLE(1),.MUT_CMD(MUT)) dut(
   .clk(clk),.core_rst_n(tx_rst_n),.child_rst_n(rx_rst_n),
   .command_valid(in_valid),.command_word(d),.child_command(q),
   .command_out_valid(out_valid),.command_accept(accept),
   .return_valid(1'b0),.return_word(68'b0),.core_return(),.return_out_valid(),.return_accept());
  qkd_ahub_zh_transport_private #(.ENABLE(1)) predecessor(
   .clk(clk),.core_rst_n(tx_rst_n),.child_rst_n(rx_rst_n),
   .command_valid(in_valid),.command_word(d),.child_command(),
   .command_out_valid(),.command_accept(pred_accept),
   .return_valid(1'b0),.return_word(68'b0),.core_return(),.return_out_valid(),.return_accept());
 end else begin:g_return
  qkd_ahub_grouped_zh_transport_private #(.ENABLE(1),.MUT_RETURN(MUT)) dut(
   .clk(clk),.child_rst_n(tx_rst_n),.core_rst_n(rx_rst_n),
   .return_valid(in_valid),.return_word(d),.core_return(q),
   .return_out_valid(out_valid),.return_accept(accept),
   .command_valid(1'b0),.command_word(268'b0),.child_command(),.command_out_valid(),.command_accept());
  qkd_ahub_zh_transport_private #(.ENABLE(1)) predecessor(
   .clk(clk),.child_rst_n(tx_rst_n),.core_rst_n(rx_rst_n),
   .return_valid(in_valid),.return_word(d),.core_return(),
   .return_out_valid(),.return_accept(pred_accept),
   .command_valid(1'b0),.command_word(268'b0),.child_command(),.command_out_valid(),.command_accept());
 end endgenerate
 // Reference is the frozen root/leaf recurrence, never DUT ready/valid state.
 reg ta0=1,ta1=1,ra0=1,ra1=1;
 wire tg=tx_rst_n&&ta1,rg=rx_rst_n&&ra1;
 reg ts0=1,ts1=1,tq0=1,tq1=1,rs0=1,rs1=1,rq0=1,rq1=1;
 always @(posedge clk or negedge tx_rst_n)
  if(!tx_rst_n)begin ta0<=0;ta1<=0;end else begin ta0<=1;ta1<=ta0;end
 always @(posedge clk or negedge rx_rst_n)
  if(!rx_rst_n)begin ra0<=0;ra1<=0;end else begin ra0<=1;ra1<=ra0;end
 always @(posedge clk or negedge tg)
  if(!tg)begin ts0<=0;ts1<=0;end else begin ts0<=1;ts1<=ts0;end
 always @(posedge clk or negedge rg)
  if(!rg)begin rs0<=0;rs1<=0;end else begin rs0<=1;rs1<=rs0;end
 always @(posedge clk)begin tq0<=ts1;tq1<=tq0;rq0<=rs1;rq1<=rq0;end
 // Original leaf-only recurrence: exact +2 release comparison.
 reg pts0=1,pts1=1,ptq0=1,ptq1=1,prs0=1,prs1=1,prq0=1,prq1=1;
 always @(posedge clk or negedge tx_rst_n)
  if(!tx_rst_n)begin pts0<=0;pts1<=0;end else begin pts0<=1;pts1<=pts0;end
 always @(posedge clk or negedge rx_rst_n)
  if(!rx_rst_n)begin prs0<=0;prs1<=0;end else begin prs0<=1;prs1<=prs0;end
 always @(posedge clk)begin ptq0<=pts1;ptq1<=ptq0;prq0<=prs1;prq1<=prq0;end
 reg [W-1:0] expected[0:2047];
 bit expected_v[0:2047];
 integer cycle=0,accepted=0,observed=0,discarded=0,drained_tx_reset=0;
 integer first_accept=-1,first_output=-1,pred_first=-1,i,j;
 bit track_first=1;
 reg a_pre,rx_pre,ev;
 function automatic [W-1:0] pattern(input integer n);
  integer b; reg [W-1:0] v;
  begin
   for(b=0;b<W;b=b+1)v[b]=((n*17+b*13+(b/7)*n)>>(b%5))&1;
   if(W==68)v[W-1 -:4]=(n%15)+1;
   pattern=v;
  end
 endfunction
 // The emitted-source hierarchy adapter writes arbitrary OLD Q, including
 // async-reset state AFTER time-zero reset propagation. No state is forced
 // during real clock/reset recurrence. It also checks public authority at .6ns.
 `include "old_q_injection.svh"
 task automatic edge_step(input bit valid_word,input integer tag);
  begin
   in_valid=valid_word;d=pattern(tag);#4;
   a_pre=in_valid&&tg&&rg&&ts1&&tq1&&rs1&&rq1;
   rx_pre=rg&&rs1&&rq1;
   if(accept!==a_pre)$fatal(1,"GROUP_FAIL accept_frontier cycle=%0d got=%b want=%b",cycle,accept,a_pre);
   if(pred_accept !== (in_valid&&tx_rst_n&&rx_rst_n&&pts1&&ptq1&&prs1&&prq1))
    $fatal(1,"GROUP_FAIL predecessor_frontier cycle=%0d",cycle);
   if(track_first && pred_first<0 && pred_accept)pred_first=cycle;
   clk=1;#1;
   if(!rx_pre)begin
    for(j=cycle;j<2048;j=j+1)begin
     if(expected_v[j])discarded=discarded+1;
     expected_v[j]=0;
    end
   end
   if(a_pre)begin
    expected[cycle+4]=d;expected_v[cycle+4]=1;accepted=accepted+1;
    if(first_accept<0)begin
     first_accept=cycle;
     if(pred_first<0 || cycle!=pred_first+2)
      $fatal(1,"GROUP_FAIL release_delta successor=%0d predecessor=%0d",cycle,pred_first);
     track_first=0;
    end
   end
   ev=expected_v[cycle];
   if(out_valid!==ev)$fatal(1,"GROUP_FAIL valid_frontier cycle=%0d got=%b want=%b",cycle,out_valid,ev);
   if(ev)begin
    if(q!==expected[cycle])$fatal(1,"GROUP_FAIL payload cycle=%0d got=%h want=%h",cycle,q,expected[cycle]);
    observed=observed+1;if(!tx_rst_n)drained_tx_reset=drained_tx_reset+1;
    if(first_output<0)first_output=cycle;
   end
   expected_v[cycle]=0;
   #4;clk=0;#1;cycle=cycle+1;
  end
 endtask
 initial begin
  for(i=0;i<2048;i=i+1)expected_v[i]=0;
  #1;
  if(accept!==0 || out_valid!==0)$fatal(1,"GROUP_FAIL raw_authority preedge accept=%b valid=%b",accept,out_valid);
  repeat(8)edge_step(1,900+cycle);
  tx_rst_n=1;repeat(7)edge_step(1,1000+cycle);
  rx_rst_n=1;repeat(48)edge_step(1,2000+cycle);
  tx_rst_n=0;
  #0.1;if(accept!==0)$fatal(1,"GROUP_FAIL raw_authority transmitter");
  repeat(9)edge_step(1,3000+cycle);
  tx_rst_n=1;repeat(23)edge_step(1,4000+cycle);
  rx_rst_n=0;
  #0.1;if(out_valid!==0 || accept!==0)$fatal(1,"GROUP_FAIL raw_authority receiver");
  repeat(8)edge_step(1,5000+cycle);
  tx_rst_n=0;repeat(7)edge_step(0,6000+cycle);
  rx_rst_n=1;repeat(9)edge_step(1,7000+cycle);
  tx_rst_n=1;repeat(80)edge_step((cycle%7)!=0&&(cycle%11)!=0,8000+cycle);
  repeat(24)edge_step(0,9000+cycle);
  repeat(128)edge_step(1,10000+cycle);
  repeat(12)edge_step(0,11000+cycle);
  for(i=cycle;i<2048;i=i+1)if(expected_v[i])$fatal(1,"GROUP_FAIL undrained");
  if(accepted<200 || observed<200 || discarded==0 || drained_tx_reset!=4)
   $fatal(1,"GROUP_FAIL coverage accepted=%0d observed=%0d discarded=%0d txdrain=%0d",accepted,observed,discarded,drained_tx_reset);
  if(observed+discarded!=accepted)$fatal(1,"GROUP_FAIL accounting");
  if(first_output!=first_accept+4)$fatal(1,"GROUP_FAIL latency");
  $display("GROUP_PASS W=%0d MUT=%0d INIT_CASE=%0d edges=%0d accepted=%0d observed=%0d discarded=%0d txdrain=%0d first_accept=%0d predecessor=%0d first_output=%0d",W,MUT,INIT_CASE,cycle,accepted,observed,discarded,drained_tx_reset,first_accept,pred_first,first_output);
  $finish;
 end
endmodule
