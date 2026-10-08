`timescale 1ns/1ps
// Cross-bank veto bench for ot_hbm_native_frame_station_rb (NO=2).
// 1. Clean transaction: the frame taken at in_v/in_r reaches both branches
//    exactly (out_v/out_r), both ACKs retire it, the held receipt is released.
// 2. Upset: a station control rail (u_pend false rail) is flipped while the
//    station is idle and every bank is healthy. The rail fault reaches no bank
//    verdict, so ONLY the station-wide veto can stop the station. Within
//    VETO_EDGES the station must report fault and from then on never raise
//    in_r, out_v or release_v, although a new frame is offered.
module tb_w2_rb_cross_bank_veto;
 localparam integer VETO_EDGES=6;
 reg clk=0;always #0.4166665 clk=~clk;
 reg por_n=0,in_v=0;reg [2062:0] in_data=0;reg [191:0] in_owner=0;reg [72:0] in_frame=0;
 reg [1:0] out_r=0,ACK_v=0;reg [2*192-1:0] ACK_owner=0;reg [2*73-1:0] ACK_frame=0;reg release_r=0;
 wire in_r,release_v,fclk_o,drained,paused,fault;wire [1:0] out_v;
 wire [2*2063-1:0] out_data;wire [2*192-1:0] out_owner;wire [2*73-1:0] out_frame;
 wire [191:0] release_owner;wire [72:0] release_frame;
 ot_hbm_native_frame_station_rb #(.ENABLE(1),.NO(2)) dut(.clk_sm(clk),.por_n(por_n),.release_held(1'b1),
  .in_v(in_v),.in_r(in_r),.in_data(in_data),.in_owner(in_owner),.in_frame(in_frame),
  .out_v(out_v),.out_r(out_r),.out_data(out_data),.out_owner(out_owner),.out_frame(out_frame),
  .ACK_v(ACK_v),.ACK_owner(ACK_owner),.ACK_frame(ACK_frame),
  .release_v(release_v),.release_r(release_r),.release_owner(release_owner),.release_frame(release_frame),
  .fclk_o(fclk_o),.drained(drained),.paused(paused),.fault(fault));
 integer k,checks=0;reg [1:0] got=0;
 task offer(input [2062:0] d,input [191:0] o,input [72:0] f);
  begin in_data=d;in_owner=o;in_frame=f;in_v=1; end
 endtask
 initial begin
  repeat(4)@(negedge clk);por_n=1;
  for(k=0;k<400&&!drained;k=k+1)@(negedge clk);
  if(!drained||fault)$fatal(1,"cold start");checks++;
  // ---- 1. clean transaction (held valid until learned: one edge after in_r)
  offer({2063{1'b1}}^2063'h1234_5678_9abc,192'hfeed_0001,73'h1_0203);
  for(k=0;k<400&&!in_r;k=k+1)@(negedge clk);
  if(!in_r)$fatal(1,"frame not taken");@(negedge clk);in_v=0;checks++;
  for(k=0;k<600&&got!=2'b11;k=k+1)begin
   @(negedge clk);out_r=0;
   for(integer t=0;t<2;t=t+1)if(out_v[t]&&!got[t])begin
    if(out_data[t*2063+:2063]!==({2063{1'b1}}^2063'h1234_5678_9abc)||out_owner[t*192+:192]!==192'hfeed_0001||
       out_frame[t*73+:73]!==73'h1_0203)$fatal(1,"branch %0d data",t);
    out_r[t]=1;got[t]=1;
   end
  end
  @(negedge clk);out_r=0;
  if(got!=2'b11)$fatal(1,"branches not offered");checks++;
  repeat(4)@(negedge clk);
  ACK_v=2'b11;ACK_owner={2{192'hfeed_0001}};ACK_frame={2{73'h1_0203}};@(negedge clk);ACK_v=0;
  for(k=0;k<400&&!release_v;k=k+1)@(negedge clk);
  if(!release_v||release_owner!==192'hfeed_0001||release_frame!==73'h1_0203)$fatal(1,"release receipt");
  release_r=1;@(negedge clk);release_r=0;checks++;
  for(k=0;k<400&&!drained;k=k+1)@(negedge clk);
  if(!drained||fault)$fatal(1,"drain after clean transaction");checks++;
  // ---- 2. station rail upset while idle, every bank healthy
  dut.held.u_pend.f[0]=~dut.held.u_pend.f[0];
  offer(2063'h5a5a,192'hbeef,73'h7);
  for(k=0;k<VETO_EDGES;k=k+1)@(negedge clk);
  if(!fault)$fatal(1,"rail fault not reported within %0d edges",VETO_EDGES);checks++;
  for(k=0;k<300;k=k+1)begin
   @(negedge clk);
   if(in_r||(|out_v)||release_v)$fatal(1,"VETO: station acted after a station rail fault (edge %0d)",k+VETO_EDGES);
  end
  checks++;
  $display("PASS_W2_RB_CROSS_BANK_VETO checks=%0d veto_edges=%0d",checks,VETO_EDGES);
  $finish;
 end
 initial begin #2000;$fatal(1,"timeout");end
endmodule
