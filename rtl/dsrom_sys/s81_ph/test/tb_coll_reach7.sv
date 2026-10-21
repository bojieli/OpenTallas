`timescale 1ns/1ps
// S81-TILES-E 10-20 COLL s7 (REACH = 1) lane-pair scoreboard: the safe4 pair (reference, cycle-identical to P1 by
// tb_coll_safe4_boundary) and the safe7 pair (forwarded relay hops: rx landing +1, RX_STAGES 3->5, reverse frame relay
// +2, core landing +1) run the SAME channel impairments as tb_coll_safe4_boundary (CRC corruption windows -> NAK /
// go-back-N replay, lane blackouts -> gearbox re-hunt / relock / ACK timeouts, core-side backpressure, one mid-run stream
// reset).  The relays change latency, so the check is transactional per pair: every word delivered on li of side j is
// exactly the next word sent on lo of side 1-j in the current reset epoch (in order, exactly once, bit-exact), each core
// credit model stays inside 0..8, both pairs end with the same fault flags, and the safe7 pair delivers >= 97% of the
// reference words.  With +define+OT_COLL_REACH8 the DUT pair is safe8 (REACH = 2: + endpoint RX FIFO write landing).  Prints the mean lo->li latency of both pairs (the added cycles, for the schedule ledger).
module tb_coll_reach7;
 parameter integer NCYC=40000;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg [31:0] rng=32'h8117c055;
 reg [1:0] lv[0:1], ret[0:1];
 reg [552:0] ld[0:1][0:1];
 reg [511:0] imp[0:1]; reg [1:0] rxv=2'b11;
 wire [511:0] tx[0:1][0:1];
 wire cr[0:1][0:1],ov[0:1][0:1];
 wire [552:0] od[0:1][0:1];
 wire [2:0] flt[0:1][0:1];
 genvar v;
 generate for(v=0;v<2;v=v+1) begin:variant
  if(v==0) begin:ref4
   dsfd_coll_lane_w_safe4 w(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][1]^imp[1],rxv[1]}),.tx(tx[v][0]),
    .lo_v(lv[v][0]),.lo_r(cr[v][0]),.lo_d(ld[v][0]),.li_v(ov[v][0]),.li_r(ret[v][0]),.li_d(od[v][0]),.flt(flt[v][0]));
   dsfd_coll_lane_e_safe4 e(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][0]^imp[0],rxv[0]}),.tx(tx[v][1]),
    .lo_v(lv[v][1]),.lo_r(cr[v][1]),.lo_d(ld[v][1]),.li_v(ov[v][1]),.li_r(ret[v][1]),.li_d(od[v][1]),.flt(flt[v][1]));
  end else begin:dut7
`ifdef OT_COLL_REACH8
   dsfd_coll_lane_w_safe8 w(
`else
   dsfd_coll_lane_w_safe7 w(
`endif
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][1]^imp[1],rxv[1]}),.tx(tx[v][0]),
    .lo_v(lv[v][0]),.lo_r(cr[v][0]),.lo_d(ld[v][0]),.li_v(ov[v][0]),.li_r(ret[v][0]),.li_d(od[v][0]),.flt(flt[v][0]));
`ifdef OT_COLL_REACH8
   dsfd_coll_lane_e_safe8 e(
`else
   dsfd_coll_lane_e_safe7 e(
`endif
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][0]^imp[0],rxv[0]}),.tx(tx[v][1]),
    .lo_v(lv[v][1]),.lo_r(cr[v][1]),.lo_d(ld[v][1]),.li_v(ov[v][1]),.li_r(ret[v][1]),.li_d(od[v][1]),.flt(flt[v][1]));
  end
 end endgenerate
 function automatic [552:0] word(input integer side, input integer ep, input integer k);
  reg [31:0] h; integer b; begin
   h=32'h9e3779b9*(k+1) ^ (side*32'h85ebca6b) ^ (ep*32'hc2b2ae35);
   for(b=0;b<553;b=b+1) begin word[b]=h[b%32]^h[(b/32+k)%32]; if(b%32==31) h=h^(h<<13)^(h>>7); end
  end endfunction
 integer c=0,err=0,ep=0,i,j,b;
 integer credits[0:1][0:1],pending[0:1][0:1],sk[0:1][0:1],rk[0:1][0:1],sent[0:1],got[0:1];
 longint lat[0:1]; integer tsend[0:1][0:1][0:4095];
 initial for(i=0;i<2;i=i+1) for(j=0;j<2;j=j+1) begin credits[i][j]=8;pending[i][j]=0;sk[i][j]=0;rk[i][j]=0;ld[i][j]=0;lv[i]=0;ret[i]=0;sent[i]=0;got[i]=0;lat[i]=0; end
 always @(negedge clk) begin
  c=c+1;
  for(i=0;i<2;i=i+1) for(j=0;j<2;j=j+1) begin
   if(!rst_n) begin credits[i][j]=8;pending[i][j]=0;sk[i][j]=0;rk[i][j]=0; end
   else begin
    // the word on li of side j (sampled this cycle) came from lo of side 1-j
    if(ov[i][j]) begin
     if(od[i][j]!==word(1-j,ep,rk[i][j])) begin err=err+1; if(err<8)$display("COLL_REACH7_DATA_ERR variant=%0d cycle=%0d side=%0d word=%0d",i,c,j,rk[i][j]); end
     if(rk[i][j]>=sk[i][1-j]) begin err=err+1; if(err<8)$display("COLL_REACH7_DUP_ERR variant=%0d cycle=%0d side=%0d word=%0d sent=%0d",i,c,j,rk[i][j],sk[i][1-j]); end
     lat[i]=lat[i]+(c-tsend[i][1-j][rk[i][j]%4096]);
     rk[i][j]=rk[i][j]+1; got[i]=got[i]+1;
    end
    credits[i][j]=credits[i][j]+int'(cr[i][j])-int'(lv[i][j]);
    pending[i][j]=pending[i][j]+int'(ov[i][j])-int'(ret[i][j]);
    if(lv[i][j]) begin tsend[i][j][sk[i][j]%4096]=c-1; sk[i][j]=sk[i][j]+1; sent[i]=sent[i]+1; end
    if(credits[i][j]<0||credits[i][j]>8||pending[i][j]<0||pending[i][j]>8)begin err=err+1;if(err<8)$display("COLL_CREDIT_MODEL_ERR variant=%0d cycle=%0d side=%0d credits=%0d pending=%0d",i,c,j,credits[i][j],pending[i][j]);end
   end
  end
  rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
  if(rst_n && (c>=3500&&c<3513)) ep=ep+1;   // stream reset: a new epoch (in-flight words are dropped by both pairs)
  rst_n=!(c<8||(c>=3500&&c<3513));
  imp[0]=0; imp[1]=0; rxv=2'b11;
  if((c>=6000&&c<6006)||(c>=15000&&c<15002)||(c>=26000&&c<26040)) imp[0]={rng,rng[15:0],8'h0,4'h0} << 64;
  if((c>=9000&&c<9003)||(c>=21000&&c<21010)) imp[1]={rng[7:0],rng} << 200;
  if(c>=11000&&c<11300) rxv[0]=0;
  if(c>=18000&&c<20200) rxv[1]=0;
  if(c>=30000&&c<30007) rxv=2'b00;
  for(i=0;i<2;i=i+1) for(j=0;j<2;j=j+1) begin
   lv[i][j]=rst_n&&(c>40)&&(c<3500||c>3545)&&credits[i][j]>0&&rng[j];
   ret[i][j]=rst_n&&pending[i][j]>0&&(c%800>=200);
   ld[i][j]=word(j,ep,sk[i][j]);
  end
  if(c==NCYC)begin
   $display("COLL_REACH7_STATS ref4 sent=%0d received=%0d mean_latency=%0d.%02d | safe7 sent=%0d received=%0d mean_latency=%0d.%02d | faults ref4=%b/%b safe7=%b/%b | naks=%0d/%0d replays=%0d/%0d timeouts=%0d/%0d",
    sent[0],got[0],lat[0]/(got[0]>0?got[0]:1),(lat[0]*100/(got[0]>0?got[0]:1))%100,
    sent[1],got[1],lat[1]/(got[1]>0?got[1]:1),(lat[1]*100/(got[1]>0?got[1]:1))%100,
    flt[0][0],flt[0][1],flt[1][0],flt[1][1],
    variant[1].dut7.w.u.u_ep.st_naks, variant[1].dut7.e.u.u_ep.st_naks,
    variant[1].dut7.w.u.u_ep.st_replays, variant[1].dut7.e.u.u_ep.st_replays,
    variant[1].dut7.w.u.u_ep.st_timeouts, variant[1].dut7.e.u.u_ep.st_timeouts);
   if(err==0&&sent[0]>1000&&got[0]>800&&got[1]*100>=got[0]*97&&flt[1][0]===flt[0][0]&&flt[1][1]===flt[0][1])
    $display("COLL_REACH7 PASS received=%0d/%0d errors=0",got[1],got[0]);
   else $display("COLL_REACH7 FAIL errors=%0d received=%0d/%0d faults=%b/%b vs %b/%b",err,got[1],got[0],flt[1][0],flt[1][1],flt[0][0],flt[0][1]);
   $finish;
  end
 end
endmodule
