`timescale 1ns/1ps
// Actual eight compact upper leaves and seven registered selector forks.
// Fixed reduced-tree boundary stimulus; independent REF composition.  This
// fixture qualifies only this boundary, never controller/issuer/VM calibration.
module tb_b2_selector_boundary;
reg clk=0,rst_n=0;always #1 clk=~clk;
reg [3:0] ctl=0;wire [3:0] s1[0:1],s2[0:3],s3[0:7];
qfd_static_selector_fork4 root(clk,rst_n,ctl,s1[0],s1[1]);
for(genvar i=0;i<2;i=i+1)begin:l1
 qfd_static_selector_fork4 f(clk,rst_n,s1[i],s2[2*i],s2[2*i+1]);
end
for(genvar i=0;i<4;i=i+1)begin:l2
 qfd_static_selector_fork4 f(clk,rst_n,s2[i],s3[2*i],s3[2*i+1]);
end
reg [3:0] refctl[0:2];reg [3:0] mutant_ctl[0:7];
reg [383:0] words[0:7],wp[0:7][0:2];reg pv=0,pvp[0:2];
integer tick=0,mut=0,sel_only=0,checks=0,errors=0;integer valid_count[0:7],nonzero[0:7],distinct[0:7];
reg [191:0] first[0:7];wire [191:0] ry[0:7],dy[0:7];wire [7:0]rv,dv,ru,du,rf,df;
always @(posedge clk)begin
 refctl[0]<=ctl;refctl[1]<=refctl[0];refctl[2]<=refctl[1];
 pvp[0]<=pv;pvp[1]<=pvp[0];pvp[2]<=pvp[1];
 for(integer b=0;b<8;b=b+1)begin
  wp[b][0]<=words[b];wp[b][1]<=wp[b][0];wp[b][2]<=wp[b][1];mutant_ctl[b]<=s3[b];
 end
end
for(genvar b=0;b<8;b=b+1)begin:bank
 wire[3:0] dc=(mut==b+1)?(sel_only?{s3[b][3:2],mutant_ctl[b][1:0]}:mutant_ctl[b]):s3[b];
 qfd_band_upper_b2_l2_s4 ref_leaf(.clk(clk),.rst_n(rst_n),.pw(wp[b][2]),.pw_v({6{pvp[2]}}),.lf(6'd0),
  .sel_e(refctl[2][1:0]),.tv_e(refctl[2][3:2]),.tt_ty(ry[b]),.tt_use(ru[b]),.tt_v(rv[b]),.fault(rf[b]));
 qfd_band_upper_b2_l2_s4 dut_leaf(.clk(clk),.rst_n(rst_n),.pw(wp[b][2]),.pw_v({6{pvp[2]}}),.lf(6'd0),
  .sel_e(dc[1:0]),.tv_e(dc[3:2]),.tt_ty(dy[b]),.tt_use(du[b]),.tt_v(dv[b]),.fault(df[b]));
end
// Finite positive FP32, unique at every bank, frame, lane and half input.
function automatic [31:0] payload(input integer t,b,k);
 payload={1'b0,8'd120,23'(1+t*4096+b*256+k*8)};
endfunction
always @(negedge clk)if(rst_n)begin
 tick=tick+1;
 for(integer b=0;b<8;b=b+1)begin
  if(tick>20)begin
   checks=checks+1;
   if(rv[b]!==dv[b]||ru[b]!==du[b]||(rv[b]&&ry[b]!==dy[b])||rf[b]||df[b])begin
    if(errors<8)$display("MISMATCH bank%0d tick%0d rv%0d dv%0d rf%0d df%0d",b,tick,rv[b],dv[b],rf[b],df[b]);errors=errors+1;
   end
   if(rv[b])begin
    valid_count[b]=valid_count[b]+1;
    if(ry[b]!=0)nonzero[b]=nonzero[b]+1;
    if(valid_count[b]==1)first[b]=ry[b];else if(ry[b]!=first[b])distinct[b]=distinct[b]+1;
   end
  end
 end
end
initial begin
 void'($value$plusargs("MUT_BANK=%d",mut));void'($value$plusargs("SEL_ONLY=%d",sel_only));
 for(integer b=0;b<8;b=b+1)begin valid_count[b]=0;nonzero[b]=0;distinct[b]=0;words[b]=0;end
 repeat(8)@(negedge clk);#0.01;rst_n=1;
 repeat(40)@(negedge clk);
 for(integer frame=0;frame<16;frame=frame+1)begin
  // Each level's valid precedes its sum select by TREE_LAT=7 edges.
  // The next level launches eight edges after the first. pw arrives one
  // edge after the first valid. These are the native reduced-tree pin ages.
  #0.01;ctl=4'b0100;
  @(negedge clk);#0.01;ctl[2]=0;pv=1;
  for(integer b=0;b<8;b=b+1)for(integer k=0;k<12;k=k+1)words[b][32*k+:32]=payload(frame,b,k);
  @(negedge clk);#0.01;pv=0;
  repeat(5)@(negedge clk);#0.01;ctl[0]=1;
  @(negedge clk);#0.01;ctl[0]=0;ctl[3]=1;
  @(negedge clk);#0.01;ctl[3]=0;
  repeat(6)@(negedge clk);#0.01;ctl[1]=(frame%2);
  @(negedge clk);#0.01;ctl[1]=0;
  repeat(17)@(negedge clk);
 end
 repeat(60)@(negedge clk);#0.01;
 for(integer b=0;b<8;b=b+1)begin
  $display("COVER bank%0d valid%0d nonzero%0d distinct%0d",b,valid_count[b],nonzero[b],distinct[b]);
  if(valid_count[b]!=16||nonzero[b]!=16||distinct[b]<15)begin $display("FAIL vacuous bank%0d",b);errors=errors+1;end
 end
 if(errors)$fatal(1,"FAIL selector boundary errors%0d",errors);
 $display("PASS selector boundary eight banks checks%0d",checks);$finish;
end
endmodule
