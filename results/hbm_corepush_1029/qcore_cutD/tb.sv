`timescale 1ns/1ps
module tb_qcore_cutD;
 reg clk=0,rst_n=0,vi=0; reg [31:0] a=0,b=0;
 always #1 clk=~clk;
 wire [31:0] yg,yc,yp,yd;wire [1:0] eg,ec,ep,ed;wire vg,vc,vp,vd;
 ot_hdc_fp32_add_n32 #(.LAT(6),.DRST(0)) gold(.clk(clk),.rst_n(rst_n),.valid_in(vi),.a(a),.b(b),.y(yg),.err(eg),.valid_out(vg));
 ot_hdc_fp32_add_n32 #(.LAT(6),.CUTS(11),.DRST(0)) cand(.clk(clk),.rst_n(rst_n),.valid_in(vi),.a(a),.b(b),.y(yc),.err(ec),.valid_out(vc));
 ot_hdc_fp32_add_n32 #(.LAT(7),.CUTS(15),.DRST(0)) phase_mut(.clk(clk),.rst_n(rst_n),.valid_in(vi),.a(a),.b(b),.y(yp),.err(ep),.valid_out(vp));
 ot_hdc_fp32_add_n32 #(.LAT(6),.CUTS(11),.DRST(0)) data_mut(.clk(clk),.rst_n(rst_n),.valid_in(vi),.a(a^32'h00010000),.b(b),.y(yd),.err(ed),.valid_out(vd));
 integer c,checks=0,bad=0,mp=0,md=0,seed=1329;
 reg [31:0] specials[0:15];
 initial begin
  specials[0]=0;specials[1]=32'h80000000;specials[2]=1;specials[3]=32'h007fffff;specials[4]=32'h00800000;specials[5]=32'h3f800000;specials[6]=32'hbf800000;specials[7]=32'h7f7fffff;specials[8]=32'hff7fffff;specials[9]=32'h7f800000;specials[10]=32'hff800000;specials[11]=32'h7fc00001;specials[12]=32'h7f800001;specials[13]=32'h3f000001;specials[14]=32'h3f7fffff;specials[15]=32'h00800001;
  for(c=0;c<100032;c=c+1)begin
   @(negedge clk);
   rst_n=!(c<4 || (c>=35000&&c<35004) || (c>=73000&&c<73004));
   vi=(c%11!=4 && c%13!=0 && c<100000);
   if(c<260)begin a=specials[(c/16)%16];b=specials[c%16];end
   else begin
    a=$random(seed);b=$random(seed);
    case(c%8)
     0:b={~a[31],a[30:0]};
     1:b={a[31],8'd0,a[22:0]};
     2:a={a[31],8'hff,a[22:0]};
     3:a={a[31],8'd0,a[22:0]};
     default:begin end
    endcase
   end
   @(posedge clk);#0.01;
   if(vc!==vg)bad=bad+1;
   if(vg)begin checks=checks+1;if({yc,ec}!={yg,eg})begin if(bad<5)$display("DIFF cycle%0d gold%h/%h cand%h/%h",c,yg,eg,yc,ec);bad=bad+1;end end
   if(vp!==vg || (vg&&({yp,ep}!={yg,eg})))mp=mp+1;
   if(vd!==vg || (vg&&({yd,ed}!={yg,eg})))md=md+1;
  end
  $display("CUTD_RESULT checks=%0d mismatches=%0d phase_control=%0d data_control=%0d",checks,bad,mp,md);
  if(checks<70000||bad!=0||mp==0||md==0)$fatal(1,"CUTD_FAIL");
  $display("CUTD_PASS LAT6 DRST0 no_added_edges");$finish;
 end
endmodule
