`timescale 1ns/1ps
// S81-COLL bank64 safe3 lane-pair miter: the legacy P1 lane pair (dsfd_coll_lane_w/e GFMT1 EPPIPE2 LCR1 RXSRAM1)
// against the safe3 pair (dsfd_coll_lane_w/e_safe3), each pair looped through its own physical beats with the SAME
// channel impairments: beat corruption windows (CRC errors -> NAK / go-back-N replay), lane blackouts (marker loss ->
// gearbox re-hunt / relock; ACK timeouts), core-side backpressure, two stream resets.  Every cycle compares every
// tile output: tx beat, credit, li valid (+ data when valid), faults.  tf is absent on the safe pair (no consumer).
module tb_coll_safe3_boundary;
 parameter integer NCYC=40000;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg [31:0] rng=32'h8117c055;
 reg [1:0] lv=0,ret=0;
 reg [552:0] ld[0:1];
 // channel impairments, identical for both variants: imp[d] corrupts the beat travelling INTO side 1-d... (index = source side)
 reg [511:0] imp[0:1]; reg [1:0] rxv=2'b11;
 integer crcerr_cycles=0, blackout_cycles=0;
 // coverage (legacy-side protocol statistics; safe3-side bank64 forwarding / suppressed physical collisions)
 integer relocks=0, fifo_fwd=0, rb_fwd=0, crx_fwd=0, gb_fwd=0; reg [1:0] lk_q=0;
 wire [1:0] lk_now={variant[0].legacy.e.u.u_gb.locked, variant[0].legacy.w.u.u_gb.locked};
 always @(posedge clk) begin
  lk_q<=lk_now; if(rst_n) relocks<=relocks+int'(lk_now[0]&&!lk_q[0])+int'(lk_now[1]&&!lk_q[1]);
  if(rst_n && variant[1].safe.w.u.u_ep.g_fifo_safe.u_m.r_en[0] && variant[1].safe.w.u.u_ep.g_fifo_safe.u_m.g_slice[0].hit) fifo_fwd<=fifo_fwd+1;
  if(rst_n && variant[1].safe.w.u.u_ep.g_rb_safe.u_m.r_en[0] && variant[1].safe.w.u.u_ep.g_rb_safe.u_m.g_slice[0].hit) rb_fwd<=rb_fwd+1;
  if(rst_n && (variant[1].safe.w.u.u_ski.u_head.current_hit || variant[1].safe.w.u.u_ski.u_head.previous_hit)) crx_fwd<=crx_fwd+1;
  if(rst_n && (variant[1].safe.w.u.u_gb.u_sf.current_hit || variant[1].safe.w.u.u_gb.u_sf.previous_hit)) gb_fwd<=gb_fwd+1;
 end
 wire [511:0] tx[0:1][0:1];
 wire cr[0:1][0:1],ov[0:1][0:1];
 wire [552:0] od[0:1][0:1];
 wire [2:0] flt[0:1][0:1];
 genvar v;
 generate for(v=0;v<2;v=v+1) begin:variant
  if(v==0) begin:legacy
   dsfd_coll_lane_w #(.GFMT(1),.EPPIPE(2),.LCR(1),.RXSRAM(1)) w(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][1]^imp[1],rxv[1]}),.tx(tx[v][0]),.tf(),
    .lo_v(lv[0]),.lo_r(cr[v][0]),.lo_d(ld[0]),.li_v(ov[v][0]),.li_r(ret[0]),.li_d(od[v][0]),.flt(flt[v][0]));
   dsfd_coll_lane_e #(.GFMT(1),.EPPIPE(2),.LCR(1),.RXSRAM(1)) e(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][0]^imp[0],rxv[0]}),.tx(tx[v][1]),.tf(),
    .lo_v(lv[1]),.lo_r(cr[v][1]),.lo_d(ld[1]),.li_v(ov[v][1]),.li_r(ret[1]),.li_d(od[v][1]),.flt(flt[v][1]));
  end else begin:safe
   dsfd_coll_lane_w_safe3 w(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][1]^imp[1],rxv[1]}),.tx(tx[v][0]),
    .lo_v(lv[0]),.lo_r(cr[v][0]),.lo_d(ld[0]),.li_v(ov[v][0]),.li_r(ret[0]),.li_d(od[v][0]),.flt(flt[v][0]));
   dsfd_coll_lane_e_safe3 e(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][0]^imp[0],rxv[0]}),.tx(tx[v][1]),
    .lo_v(lv[1]),.lo_r(cr[v][1]),.lo_d(ld[1]),.li_v(ov[v][1]),.li_r(ret[1]),.li_d(od[v][1]),.flt(flt[v][1]));
  end
 end endgenerate
 integer c=0,err=0,checks=0,sent=0,got=0,credits[0:1],pending[0:1],j,b;
 initial begin ld[0]=0;ld[1]=0;credits[0]=8;credits[1]=8;pending[0]=0;pending[1]=0;end
 always @(negedge clk) begin
  c=c+1;
  if(c>3) for(j=0;j<2;j=j+1) begin
   checks=checks+1;
   if(cr[0][j]!==cr[1][j] || ov[0][j]!==ov[1][j] ||
      (ov[0][j]&&od[0][j]!==od[1][j]) || flt[0][j]!==flt[1][j] || tx[0][j]!==tx[1][j]) begin
    err=err+1;if(err<8)$display("COLL_SAFE3_BOUNDARY_ERR cycle=%0d side=%0d credit=%b/%b valid=%b/%b fault=%b/%b",c,j,cr[0][j],cr[1][j],ov[0][j],ov[1][j],flt[0][j],flt[1][j]);
   end
  end
  rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
  for(j=0;j<2;j=j+1) begin
   if(!rst_n)begin credits[j]=8;pending[j]=0;end
   else begin
    credits[j]=credits[j]+int'(cr[0][j])-int'(lv[j]);
    pending[j]=pending[j]+int'(ov[0][j])-int'(ret[j]);
    if(lv[j])sent=sent+1;
    if(ov[0][j])got=got+1;
    if(credits[j]<0||credits[j]>8||pending[j]<0||pending[j]>8)begin err=err+1;if(err<8)$display("COLL_CREDIT_MODEL_ERR cycle=%0d side=%0d credits=%0d pending=%0d",c,j,credits[j],pending[j]);end
   end
  end
  rst_n=!(c<8||(c>=3500&&c<3513));
  // impairments: corruption windows flip payload bits (not the marker / idle bits 0/1) of one direction;
  // blackouts drop the lane valid (the receiver loses markers and re-hunts)
  imp[0]=0; imp[1]=0; rxv=2'b11;
  if((c>=6000&&c<6006)||(c>=15000&&c<15002)||(c>=26000&&c<26040)) begin imp[0]={rng,rng[15:0],8'h0,4'h0} << 64; crcerr_cycles=crcerr_cycles+1; end
  if((c>=9000&&c<9003)||(c>=21000&&c<21010)) begin imp[1]={rng[7:0],rng} << 200; crcerr_cycles=crcerr_cycles+1; end
  if(c>=11000&&c<11300) begin rxv[0]=0; blackout_cycles=blackout_cycles+1; end
  if(c>=18000&&c<20200) begin rxv[1]=0; blackout_cycles=blackout_cycles+1; end
  if(c>=30000&&c<30007) begin rxv=2'b00; blackout_cycles=blackout_cycles+1; end
  for(j=0;j<2;j=j+1) begin
   lv[j]=rst_n&&(c>40)&&(c<3500||c>3545)&&credits[j]>0&&rng[j];
   ret[j]=rst_n&&pending[j]>0&&(c%800>=200);
   for(b=0;b<553;b=b+1)ld[j][b]=rng[(b+j)%32]^((b/32+c+j)&1);
  end
  if(c==NCYC)begin
   $display("COLL_SAFE3_COVERAGE naks=%0d/%0d replays=%0d/%0d timeouts=%0d/%0d crc_err=%0d/%0d relocks=%0d fifo_fwd=%0d replay_fwd=%0d credit_rx_fwd=%0d gearbox_fwd=%0d",
    variant[0].legacy.w.u.u_ep.st_naks, variant[0].legacy.e.u.u_ep.st_naks,
    variant[0].legacy.w.u.u_ep.st_replays, variant[0].legacy.e.u.u_ep.st_replays,
    variant[0].legacy.w.u.u_ep.st_timeouts, variant[0].legacy.e.u.u_ep.st_timeouts,
    variant[0].legacy.w.u.u_ep.st_crc_err, variant[0].legacy.e.u.u_ep.st_crc_err, relocks, fifo_fwd, rb_fwd, crx_fwd, gb_fwd);
   if(err==0&&sent>1000&&got>800)
    $display("COLL_SAFE3_BOUNDARY PASS checks=%0d sent=%0d received=%0d resets=2 crcerr_cycles=%0d blackout_cycles=%0d faults=%b/%b",checks,sent,got,crcerr_cycles,blackout_cycles,flt[0][0],flt[0][1]);
   else $display("COLL_SAFE3_BOUNDARY FAIL errors=%0d sent=%0d received=%0d faults=%b/%b",err,sent,got,flt[0][0],flt[0][1]);
   $finish;
  end
 end
endmodule
