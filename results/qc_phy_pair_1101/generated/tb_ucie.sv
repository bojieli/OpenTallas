`timescale 1ns/1fs
module tb_pair;
localparam FW=1043, LAT=4, UP=16;
reg mission_clk=0;
always #0.4165 mission_clk=~mission_clk;
reg rst_n=0;
reg tv0=0,tv1=0;
reg [FW-1:0] td0=0,td1=0;
wire up0,up1,rv0,rv1;
wire [FW-1:0] rd0,rd1;
wire lclk0,lclk1;wire clk=lclk0;
ot_qfd_ucie_x64_phy u0 (.clk(clk),.rst_n(rst_n),.tx_up(up0),.tx_v(tv0),.tx_flit(td0),.rx_v(rv0),.rx_flit(rd0),.lclk(lclk0));
ot_qfd_ucie_x64_phy u1 (.clk(clk),.rst_n(rst_n),.tx_up(up1),.tx_v(tv1),.tx_flit(td1),.rx_v(rv1),.rx_flit(rd1),.lclk(lclk1));
integer corrupt=0;
initial corrupt=$test$plusargs("MUT_PAYLOAD");
assign u0.far_v=u1.link_v;
assign u0.far_flit=u1.link_flit ^ ((corrupt && u1.link_v) ? {{(FW-1){1'b0}},1'b1} : {FW{1'b0}});
assign u1.far_v=u0.link_v;
assign u1.far_flit=u0.link_flit;
reg [FW:0] history0[0:LAT-1], history1[0:LAT-1];
reg [FW:0] last_tx0=0,last_tx1=0;
integer edges=0,accepted0=0,accepted1=0,delivered0=0,delivered1=0,resets=0;
integer drive=0,k;
realtime last_edge=0,last_mission=0;
function automatic [FW-1:0] payload(input integer n,input integer peer);
 integer b;
 begin
  for(b=0;b<FW;b=b+1) payload[b]=((n*17+b*13+peer*67)>>(b%5))&1;
  payload[n%FW]=~payload[n%FW];
 end
endfunction
always @(posedge mission_clk) begin
 if(last_mission!=0 && $rtoi(($realtime-last_mission)*1000+0.5)!=833) $fatal(1,"MISSION_PERIOD");
 last_mission=$realtime;
end
always @(posedge clk or negedge rst_n) begin
 if(!rst_n)begin
  edges=0; last_tx0=0;last_tx1=0;
  for(k=0;k<LAT;k=k+1)begin history0[k]=0;history1[k]=0;end
  #0.000001;
  if({up0,up1,rv0,rv1,u0.link_v,u1.link_v}!==0 || rd0!==0 || rd1!==0 || u0.link_flit!==0 || u1.link_flit!==0)
   $fatal(1,"ASYNC_RESET_FLUSH");
 end else begin
  if(last_edge!=0 && $rtoi(($realtime-last_edge)*1000+0.5)!=1000) $fatal(1,"PHY_PERIOD");
  edges=edges+1;
  for(k=LAT-1;k>0;k=k-1)begin history0[k]=history0[k-1];history1[k]=history1[k-1];end
  history0[0]={tv0,td0};history1[0]={tv1,td1};
  last_tx0={tv0,td0};last_tx1={tv1,td1};
  if(tv0)accepted0=accepted0+1;
  if(tv1)accepted1=accepted1+1;
  #0.000001;
  if({rv0,rd0}!==history1[LAT-1] || {rv1,rd1}!==history0[LAT-1])
   $fatal(1,"PEER_PAYLOAD_OR_LATENCY cycle=%0d LAT=%0d",edges,LAT);
  if(up0!==(edges>UP) || up1!==(edges>UP)) $fatal(1,"TX_UP_EDGE");
  if({u0.link_v,u0.link_flit}!==last_tx0 || {u1.link_v,u1.link_flit}!==last_tx1) $fatal(1,"TX_CAPTURE");
  if(rv0)delivered0=delivered0+1;
  if(rv1)delivered1=delivered1+1;
 end
 last_edge=$realtime;
end
always @(negedge clk) begin
 if(rst_n)begin
  drive=drive+1;
  // Bursts, gaps and independent direction payloads, all 1043/597 bits checked.
  tv0=(drive%7!=0);tv1=(drive%5<3);
  td0=payload(drive,0);td1=payload(drive,1);
  #0.000001;
  if({u0.link_v,u0.link_flit}!==last_tx0 || {u1.link_v,u1.link_flit}!==last_tx1)
   $fatal(1,"UNREGISTERED_TX_BETWEEN_EDGES");
 end
end
initial begin
 #0.000001; // explicit initial reset event even in two-state simulators
 rst_n=1;#0.000001;rst_n=0;
 repeat(4)@(negedge clk);#0.01;rst_n=1;
 repeat(LAT+70)@(negedge clk);
 #0.1;rst_n=0;resets=resets+1; // asynchronous mid-traffic flush on both peers
 repeat(4)@(negedge clk);#0.01;rst_n=1;
 repeat(LAT+300)@(negedge clk);
 #0.1;rst_n=0;resets=resets+1;
 #0.000002; // let async NBA flush and its assertion complete before $finish
 if(accepted0<250 || accepted1<180 || delivered0<150 || delivered1<200 || resets!=2)
  $fatal(1,"INSUFFICIENT_ACTIVE_COVERAGE");
 $display("PHY_PAIR_PASS FW=%0d LAT=%0d period_ps=1000 mission_ps=833 accepted=%0d/%0d delivered=%0d/%0d async_resets=%0d",FW,LAT,accepted0,accepted1,delivered0,delivered1,resets);
 $finish;
end
initial begin #100000;$fatal(1,"BOUNDED_DIAGNOSTIC_TIMEOUT");end
endmodule
