`timescale 1ns/1ps
module tb_no3_composition;
 parameter integer MUT=0;
 reg clk_sm=0;always #5 clk_sm=~clk_sm;
 reg por_n=0,release_held=1,in_v=0,release_r=0;
 reg[2062:0] in_data=0;reg[191:0] in_owner=0;reg[72:0] in_frame=0;
 reg[2:0] out_r=0,ACK_v=0;reg[575:0] ACK_owner=0;reg[218:0] ACK_frame=0;
 wire g_in_r,a_in_r,g_release_v,a_release_v,g_fclk,a_fclk,g_drained,a_drained,g_paused,a_paused,g_fault,a_fault;
 wire[2:0] g_out_v,a_out_v;wire[6188:0]g_out_data,a_out_data;wire[575:0]g_out_owner,a_out_owner;wire[218:0]g_out_frame,a_out_frame;
 wire[191:0]g_release_owner,a_release_owner;wire[72:0]g_release_frame,a_release_frame;
 ot_hbm_native_frame_station_rb #(.ENABLE(1),.NO(3),.REL_REG(1),.SAFE(1),.GRANT_SEAT(1),.HIER(1)) gold(
 .clk_sm(clk_sm),.por_n(por_n),.release_held(release_held),.in_v(in_v),.in_r(g_in_r),.in_data(in_data),.in_owner(in_owner),.in_frame(in_frame),
 .out_v(g_out_v),.out_r(out_r),.out_data(g_out_data),.out_owner(g_out_owner),.out_frame(g_out_frame),.ACK_v(ACK_v),.ACK_owner(ACK_owner),.ACK_frame(ACK_frame),
 .release_v(g_release_v),.release_r(release_r),.release_owner(g_release_owner),.release_frame(g_release_frame),.fclk_o(g_fclk),.drained(g_drained),.paused(g_paused),.fault(g_fault));
 ot_hbm_native_no3_composition_1014 #(.MUT(MUT)) actual(
 .clk_sm(clk_sm),.por_n(por_n),.release_held(release_held),.in_v(in_v),.in_r(a_in_r),.in_data(in_data),.in_owner(in_owner),.in_frame(in_frame),
 .out_v(a_out_v),.out_r(out_r),.out_data(a_out_data),.out_owner(a_out_owner),.out_frame(a_out_frame),.ACK_v(ACK_v),.ACK_owner(ACK_owner),.ACK_frame(ACK_frame),
 .release_v(a_release_v),.release_r(release_r),.release_owner(a_release_owner),.release_frame(a_release_frame),.fclk_observe(a_fclk),.drained(a_drained),.paused(a_paused),.fault(a_fault));
 integer cycles=0,frames=0,branches=0,releases=0,j,k,t;reg[2:0]seen=0,pending_ack=0;reg taken;
 task check;
 begin
 if({g_in_r,g_out_v,g_release_v,g_drained,g_paused,g_fault}!=={a_in_r,a_out_v,a_release_v,a_drained,a_paused,a_fault})$fatal(1,"NO3_COMPOSITION_CONTROL_MISMATCH cycle=%0d",cycles);
 if(g_fclk!==a_fclk)$fatal(1,"NO3_COMPOSITION_OBSERVATION_WAVEFORM_MISMATCH");
 for(k=0;k<3;k=k+1)if(g_out_v[k])begin
 if(g_out_data[k*2063+:2063]!==a_out_data[k*2063+:2063]||g_out_owner[k*192+:192]!==a_out_owner[k*192+:192]||g_out_frame[k*73+:73]!==a_out_frame[k*73+:73])$fatal(1,"NO3_COMPOSITION_PAYLOAD_MISMATCH branch=%0d",k);
 end
 if(g_release_v&&(g_release_owner!==a_release_owner||g_release_frame!==a_release_frame))$fatal(1,"NO3_COMPOSITION_RELEASE_MISMATCH");
 end endtask
 task step;
 begin @(posedge clk_sm);#1;cycles=cycles+1;check();if(cycles>10000)$fatal(1,"NO3_COMPOSITION_WATCHDOG frame=%0d accepted=%0d branches=%0d seen=%b C=%h cv=%b active=%b sent=%b acked=%b ACKq=%b Aout=%b Ainr=%b Aempty=%b busy=%b Pempty=%b Rready=%b Rempty=%b release_r=%b fault=%b",t,frames,branches,seen,gold.held.C_q,gold.held.cv,gold.held.active,gold.held.sent,gold.held.acked,gold.held.ackv_q,gold.held.A_out_v,gold.held.A_in_r,gold.held.A_empty,gold.held.busy,gold.held.P_empty,gold.held.R_in_r,gold.held.R_empty,release_r,g_fault);end
 endtask
 initial begin
 repeat(5)step();@(negedge clk_sm);por_n=1;repeat(20)step();
 for(t=0;t<8;t=t+1)begin
  @(negedge clk_sm);in_frame=t+1;in_owner={6{32'h6513a842 ^ t}};
  for(j=0;j<2063;j=j+1)in_data[j]=((j*13+t*31)>>(j%9))&1;
  seen=0;pending_ack=0;ACK_v=0;taken=0;in_v=1;release_r=0;
  while(!taken)begin
   @(posedge clk_sm);taken=in_v&&g_in_r;#1;cycles=cycles+1;check();
  end
  @(negedge clk_sm);in_v=0;
  while(seen!=7)begin
   @(negedge clk_sm);out_r=0;
   for(j=0;j<3;j=j+1)if(g_out_v[j]&&!seen[j]&&(cycles%5<3))begin
    if(g_out_data[j*2063+:2063]!==in_data||g_out_owner[j*192+:192]!==in_owner||g_out_frame[j*73+:73]!==in_frame)$fatal(1,"NO3_COMPOSITION_OBSERVED_WORD_MISMATCH");
    out_r[j]=1;seen[j]=1;branches=branches+1;
   end
   step();
   if(g_fault)$fatal(1,"NO3_COMPOSITION_UNEXPECTED_FAULT frame=%0d",t);
  end
  @(negedge clk_sm);out_r=0;
  repeat(4)step();
  @(negedge clk_sm);ACK_v=7;ACK_owner={3{in_owner}};ACK_frame={3{in_frame}};
  step();@(negedge clk_sm);ACK_v=0;
  while(!g_release_v)begin step();if(g_fault)$fatal(1,"NO3_COMPOSITION_UNEXPECTED_FAULT release frame=%0d",t);end
  if(seen!=7)$fatal(1,"NO3_COMPOSITION_MISSING_BRANCH");
  if(g_release_owner!==in_owner||g_release_frame!==in_frame)$fatal(1,"NO3_COMPOSITION_RELEASE_CONTENT");
  repeat(5)step();@(negedge clk_sm);ACK_v=0;pending_ack=0;release_r=1;
  step();@(negedge clk_sm);release_r=0;
  while(g_release_v)step();releases=releases+1;frames=frames+1;repeat(20)step();
 end
 if(frames!=8||branches!=24||releases!=8)$fatal(1,"NO3_COMPOSITION_COUNTS");
 $display("NO3_COMPOSITION PASS frames=%0d branches=%0d releases=%0d payload_bits=2063 cycles=%0d six_actual_masters=1 observation_no_capture=1",frames,branches,releases,cycles);$finish;
 end
 initial begin #200000;$fatal(1,"NO3_COMPOSITION_TIMEOUT frames=%0d branches=%0d release=%b fault=%b",frames,branches,g_release_v,g_fault);end
endmodule
