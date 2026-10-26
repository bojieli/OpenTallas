`timescale 1ns/1ps
// Full production-width lane pair. The legacy P1 and safe2 variants each have
// their own looped physical beats; every data/fault/credit boundary is compared.
// tf is deliberately absent only on safe2: exact strict9130 has no consumer.
module tb_coll_safe2_boundary;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg [31:0] rng=32'h8117c055;
 reg [1:0] lv=0,ret=0;
 reg [552:0] ld[0:1];
 wire [511:0] tx[0:1][0:1];
 wire cr[0:1][0:1],ov[0:1][0:1];
 wire [552:0] od[0:1][0:1];
 wire [2:0] flt[0:1][0:1];
 genvar v;
 generate for(v=0;v<2;v=v+1) begin:variant
  if(v==0) begin:legacy
   dsfd_coll_lane_w #(.GFMT(1),.EPPIPE(2),.LCR(1),.RXSRAM(1)) w(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][1],1'b1}),.tx(tx[v][0]),.tf(),
    .lo_v(lv[0]),.lo_r(cr[v][0]),.lo_d(ld[0]),.li_v(ov[v][0]),.li_r(ret[0]),.li_d(od[v][0]),.flt(flt[v][0]));
   dsfd_coll_lane_e #(.GFMT(1),.EPPIPE(2),.LCR(1),.RXSRAM(1)) e(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][0],1'b1}),.tx(tx[v][1]),.tf(),
    .lo_v(lv[1]),.lo_r(cr[v][1]),.lo_d(ld[1]),.li_v(ov[v][1]),.li_r(ret[1]),.li_d(od[v][1]),.flt(flt[v][1]));
  end else begin:safe
   dsfd_coll_lane_w_safe2 #(.GFMT(1),.EPPIPE(2),.LCR(1),.RXSRAM(1),.RXLOCAL(1),.EPRX(1),.EPTO(1),.EPMW(1),.TXSAFE(1)) w(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][1],1'b1}),.tx(tx[v][0]),
    .lo_v(lv[0]),.lo_r(cr[v][0]),.lo_d(ld[0]),.li_v(ov[v][0]),.li_r(ret[0]),.li_d(od[v][0]),.flt(flt[v][0]));
   dsfd_coll_lane_e_safe2 #(.GFMT(1),.EPPIPE(2),.LCR(1),.RXSRAM(1),.RXLOCAL(1),.EPRX(1),.EPTO(1),.EPMW(1),.TXSAFE(1)) e(
    .ck(clk),.rs(rst_n),.chb(1'b1),.rx({1'b0,1'b1,tx[v][0],1'b1}),.tx(tx[v][1]),
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
    err=err+1;if(err<8)$display("COLL_BOUNDARY_ERR cycle=%0d side=%0d credit=%b/%b valid=%b/%b fault=%b/%b",c,j,cr[0][j],cr[1][j],ov[0][j],ov[1][j],flt[0][j],flt[1][j]);
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
  for(j=0;j<2;j=j+1) begin
   lv[j]=rst_n&&(c>40)&&(c<3500||c>3545)&&credits[j]>0&&rng[j];
   ret[j]=rst_n&&pending[j]>0&&(c%800>=200);
   for(b=0;b<553;b=b+1)ld[j][b]=rng[(b+j)%32]^((b/32+c+j)&1);
  end
  if(c==14000)begin
   if(err==0&&sent>500&&got>400&&flt[0][0]==0&&flt[0][1]==0)
    $display("COLL_BOUNDARY PASS checks=%0d sent=%0d received=%0d resets=2 tf_consumers=0",checks,sent,got);
   else $display("COLL_BOUNDARY FAIL errors=%0d sent=%0d received=%0d faults=%b/%b",err,sent,got,flt[0][0],flt[0][1]);
   $finish;
  end
 end
endmodule
