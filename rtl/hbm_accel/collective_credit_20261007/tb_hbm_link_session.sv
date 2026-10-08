`timescale 1ns/1ps
module tb_hbm_link_session;
 import ot_hbm_credit_secded_pkg::*;
 reg clk=0,cs=0,cl=0;always #5 clk=~clk;always #7 cs=~cs;always #3 cl=~cl;
 reg por=1,restart=0;wire restart_ready,running,cf;
 wire[1:0] cv,cr,av,ar,af,pq,pr,admit,launch,rn,pn,ss,ls;
 wire[71:0]cw;wire[143:0]aw;wire[47:0]se,le;
 reg[1:0]quiet=3,debt0=3,dataempty=3,ctlempty=3;
 reg[1:0]phyq=0,phyr=0;wire[1:0]creditseen;
 reg phy_q_allow=0,phy_r_allow=0,credit_allow=1;
 reg[1:0] link_seen=0,stream_seen=0;
 integer streams0=0,streams1=0,links0=0,links1=0,i;
 ot_hbm_link_session_coordinator #(.ENABLE(1)) coordinator(clk,por,restart,restart_ready,cv,cr,cw,av,ar,aw,running,cf);
 wire credit_rf,credit_sf,grant_v,grant_r,sgv,sgr,sav,sar,rav,rar;
 wire [71:0] grant_w,sgw,saw,raw;
 wire [1:0]credit_obs_fault;wire credit_fifo_fault0,credit_fifo_fault1;
 ot_hbm_credit_rx #(.ENABLE(1)) credit_rx(cs,rn[1],ss[1],se[47:24],1'b0,,grant_v,grant_r,grant_w,rav,rar,raw,credit_rf);
 ot_hbm_credit_source #(.ENABLE(1)) credit_source(cl,pn[0],ls[0],le[23:0],1'b0,,sgv,sgr,sgw,sav,sar,saw,credit_sf);
 ot_hbm_link_management_cdc #(.ENABLE(1)) grant_cdc(cs,rn[1],grant_v,grant_r,grant_w,cl,pn[0],sgv,sgr,sgw,,,credit_fifo_fault0);
 wire gated_ar;
 assign sar=gated_ar&&credit_allow;
 ot_hbm_link_management_cdc #(.ENABLE(1)) ack_cdc(cl,pn[0],sav&&credit_allow,gated_ar,saw,cs,rn[1],rav,rar,raw,,,credit_fifo_fault1);
 ot_hbm_initial_credit_ack_observer #(.ENABLE(1)) source_observer(cl,pn[0],le[23:0],sav,sar,saw,creditseen[0],credit_obs_fault[0]);
 ot_hbm_initial_credit_ack_observer #(.ENABLE(1)) receiver_observer(cs,rn[1],se[47:24],rav,rar,raw,creditseen[1],credit_obs_fault[1]);
 genvar x;generate for(x=0;x<2;x=x+1)begin:g
  wire ac=x==0?cs:cl;wire ctrl_rst,agent_rst;
  wire acv,acr,aav,aar;wire[71:0]acw,aaw;wire f0,f1;
  ot_hbm_collective_reset_entry #(.ENABLE(1)) management_resets(clk,ac,por,por,ctrl_rst,agent_rst);
  ot_hbm_link_management_cdc #(.ENABLE(1)) commands(clk,ctrl_rst,cv[x],cr[x],cw,ac,agent_rst,acv,acr,acw,,,f0);
  ot_hbm_link_management_cdc #(.ENABLE(1)) acknowledgments(ac,agent_rst,aav,aar,aaw,clk,ctrl_rst,av[x],ar[x],aw[x*72+:72],,,f1);
  ot_hbm_link_session_agent #(.ENABLE(1)) agent(ac,cs,cl,por,acv,acr,acw,aav,aar,aaw,
   quiet[x],quiet[x],debt0[x],dataempty[x],ctlempty[x],phyq[x],phyr[x],creditseen[x],
   pq[x],pr[x],admit[x],launch[x],rn[x],pn[x],ss[x],ls[x],se[x*24+:24],le[x*24+:24],af[x]);
  always @(posedge cs or negedge rn[x])begin
   if(!rn[x])stream_seen[x]<=0;
   else if(ss[x])stream_seen[x]<=1;
  end
  always @(posedge cl or negedge pn[x])begin
   if(!pn[x])link_seen[x]<=0;
   else if(ls[x])link_seen[x]<=1;
  end
 end endgenerate
 // External PHY emulator only acknowledges explicit requests, never inferred time.
 always @(posedge clk)begin
  if(por)begin phyq<=0;phyr<=0;end
  else begin
   if(phy_q_allow)phyq<=pq;
   if(phy_r_allow)phyr<=pr;

  end
 end
 always @(posedge cs)begin if(ss[0])streams0=streams0+1;if(ss[1])streams1=streams1+1;end
 always @(posedge cl)begin if(ls[0])links0=links0+1;if(ls[1])links1=links1+1;end
 task step;begin @(posedge clk);#1;end endtask
 task waitrun;begin
  i=0;while(!running&&i<300)begin step;i=i+1;if(cf||af||credit_rf||credit_sf||credit_obs_fault||credit_fifo_fault0||credit_fifo_fault1)$fatal(1,"provider fault");end
  if(!running||admit!=3)$fatal(1,"run timeout");
 end endtask
 task init;begin
  @(negedge clk);por=1;restart=0;quiet=3;debt0=3;dataempty=3;ctlempty=3;phy_q_allow=1;phy_r_allow=1;credit_allow=1;
  repeat(4)step;@(negedge clk);por=0;
 end endtask
 initial begin
  repeat(4)step;@(negedge clk);por=0;
  repeat(20)step;if(running||admit||pr)$fatal(1,"invented PHY quiescence");
  phy_q_allow=1;wait(pr==3);repeat(20)step;
  if(running||pr!=3||rn||pn)$fatal(1,"invented PHY reset ACK");
  credit_allow=0;phy_r_allow=1;repeat(35)step;
  if(running||admit)$fatal(1,"invented initial grant ACK");
  credit_allow=1;waitrun;
  if(se!={24'd1,24'd1}||le!={24'd1,24'd1})$fatal(1,"first epoch");
  if(streams0!=1||streams1!=1||links0!=1||links1!=1)$fatal(1,"start duplicate");
  // Reserved flits drain before launch gate closes; no new admission permitted.
  @(negedge clk);debt0=0;dataempty=0;ctlempty=0;restart=1;step;@(negedge clk);restart=0;
  wait(admit==0&&launch==3);repeat(4)step;if(admit||launch!=3||pr||!rn||!pn)$fatal(1,"drain launch semantics");
  debt0=3;repeat(6)step;if(pr)$fatal(1,"omitted dataflight fence");
  dataempty=3;repeat(6)step;if(pr)$fatal(1,"omitted controlflight fence");
  ctlempty=3;waitrun;
  if(se!={24'd2,24'd2}||le!={24'd2,24'd2})$fatal(1,"successor epoch");
  if(streams0!=2||streams1!=2||links0!=2||links1!=2)$fatal(1,"successor pulse count");
  // Correctable control state stalls then repairs. UE stops reset release/launch.
  @(negedge clk);coordinator.state_q=coordinator.state_q^72'd1;
  #1;if(running||cv||ar)$fatal(1,"coordinator CE release");step;
  if(cf||!running)$fatal(1,"coordinator CE repair");
  @(negedge clk);g[0].agent.state_q=g[0].agent.state_q^72'd1;
  #1;if(admit[0]||launch[0])$fatal(1,"agent CE release");repeat(4)step;
  if(af||!admit[0])$fatal(1,"agent CE repair");
  @(negedge clk);g[0].agent.state_q=g[0].agent.state_q^72'd3;repeat(4)step;
  if(!af[0]||admit[0]||launch[0]||rn[0]||pn[0])$fatal(1,"agent UE quarantine");
  // Sequence/epoch cannot wrap even under forced near-limit state.
  init;waitrun;@(negedge clk);coordinator.state_q=encode64({24'hffffff,24'd5,8'd2,8'h0f});step;
  if(!cf||running||cv)$fatal(1,"epoch wrap");
  init;waitrun;@(negedge clk);coordinator.state_q=encode64({24'd1,24'hffffff,8'd5,8'h0f});restart=1;step;
  if(!cf||running||cv)$fatal(1,"seq wrap");
  $display("PASS cold-link provider: two epochs, independent clocks, PHY ACK fences, debt/data/control fences, start once, initialACK gate, CE/UE, no wrap, actual managementCDC, real credit startupACK observers");$finish;
 end
 initial begin #1000000;$fatal(1,"testbench watchdog");end
endmodule
