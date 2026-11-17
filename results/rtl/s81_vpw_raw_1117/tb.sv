`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
reg sw_v; reg [9:0] sw_a; reg [7:0] sw_m; reg [255:0] sw_d;
reg [1:0] cw_v; reg [23:0] cw_a; reg [63:0] cw_d;
reg x_wv; reg [9:0] x_wa; reg [7:0] x_wm; reg [255:0] xwd;
reg [255:0] xwd_raw; always @(posedge clk) xwd <= xwd_raw;
reg hs_v; reg [9:0] hs_a; reg [255:0] hs_d;
wire [532:0] base, cand, deflt;
`define CONN .clk(clk), .rst_n(rst_n), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .xwd(xwd), .hs_v(hs_v), .hs_a(hs_a), .hs_d(hs_d)
`define OUT(X) .wv(X[532:531]), .wa0(X[530:522]), .wa1(X[521:513]), .wd0(X[512:385]), .wd1(X[384:257]), .wm0(X[256:129]), .wm1(X[128:1]), .wcol(X[0])
ot_s81sl_vpw_base u_b (`CONN, `OUT(base));
ot_s81sl_vpw #(.XR(0)) u_d (`CONN, `OUT(deflt));
`ifdef MUTANT
ot_s81sl_vpw #(.XR(0)) u_c (`CONN, `OUT(cand));
`else
ot_s81sl_vpw #(.XR(1)) u_c (`CONN, `OUT(cand));
`endif

// Full 512x128 bank capacities; synchronous old-data read, masked write.
reg [127:0] b0[0:511],b1[0:511],c0[0:511],c1[0:511];
reg [8:0] ra=0,ra_d=0;
reg [255:0] qb,qc,qb_prev;
integer t,bitn,raw_checks=0;
initial for(t=0;t<512;t=t+1) begin b0[t]=0;b1[t]=0;c0[t]=0;c1[t]=0;end
always @(negedge clk) ra <= (i%4==0) ? sw_a[8:0] : (i%4==1) ? x_wa[8:0] : (i%4==2) ? hs_a[8:0] : cw_a[8:0];
always @(posedge clk) begin
 ra_d <= ra;
 qb <= {b1[ra],b0[ra]};
`ifdef RAW_MUTANT
 qc <= {c1[ra],c0[ra]};
`else
 qc <= {c1[ra_d],c0[ra_d]};
`endif
 if(rst_n) begin
  for(bitn=0;bitn<128;bitn=bitn+1) begin
   if(base[531] && base[129+bitn]) b0[base[530:522]][bitn] <= base[385+bitn];
   if(base[532] && base[1+bitn]) b1[base[521:513]][bitn] <= base[257+bitn];
   if(cand[531] && cand[129+bitn]) c0[cand[530:522]][bitn] <= cand[385+bitn];
   if(cand[532] && cand[1+bitn]) c1[cand[521:513]][bitn] <= cand[257+bitn];
  end
 end
 #2;
 if(i>10 && qc !== qb_prev) $fatal(1,"RAW scheduler mismatch cycle %0d",i);
 if(i>10) raw_checks=raw_checks+1;
 qb_prev=qb;
end
reg [532:0] prev;
integer i,j,checks=0,resets=0;
initial begin
  sw_v=0; cw_v=0; x_wv=0; hs_v=0; sw_a=0;sw_m=0;sw_d=0;cw_a=0;cw_d=0;x_wa=0;x_wm=0;xwd_raw=0;xwd=0;hs_a=0;hs_d=0;
  for (i=0;i<10006;i=i+1) begin
    @(negedge clk);
    rst_n=(i>2); if(!rst_n) resets=resets+1;
    sw_v=$random;cw_v=$random;x_wv=$random;hs_v=$random;
    sw_a=$random;sw_m=$random;cw_a=$random;cw_d={$random,$random};x_wa=$random;x_wm=$random;hs_a=$random;
    for(j=0;j<8;j=j+1) begin sw_d[32*j+:32]=$random; xwd_raw[32*j+:32]=$random;hs_d[32*j+:32]=$random;end
    @(posedge clk); #1;
    if(i>4 && rst_n ) begin
      if(deflt !== base) $fatal(1,"DEFAULT mismatch cycle %0d",i);
      if(cand[532:513] !== prev[532:513] || cand[0] !== prev[0]) $fatal(1,"XR control mismatch cycle %0d",i);
      if(prev[532] && cand[512:385] !== prev[512:385]) $fatal(1,"XR wd0 mismatch cycle %0d",i);
      if(prev[531] && cand[384:257] !== prev[384:257]) $fatal(1,"XR wd1 mismatch cycle %0d",i);
      if(prev[532] && cand[256:129] !== prev[256:129]) $fatal(1,"XR wm0 mismatch cycle %0d",i);
      if(prev[531] && cand[128:1] !== prev[128:1]) $fatal(1,"XR wm1 mismatch cycle %0d",i);
      checks=checks+1;
    end
    prev=base;
  end
  $display("PASS XR write port delay checks=%0d reset_edges=%0d RAW_scheduler_checks=%0d",checks,resets,raw_checks); $finish;
end
endmodule
