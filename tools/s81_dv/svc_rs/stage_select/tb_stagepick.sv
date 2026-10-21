`timescale 1ns/1ps
module tb_stagepick;
reg clk=0;always #5 clk=~clk;
reg f=0,b=0,f0=0,b0=0,f1=0,b1=0;reg[1059:0]a=0,z=0;
always @(posedge clk)begin f0<=f;b0<=b;f1<=f0;b1<=b0;end
wire[1059:0]ofill[0:3],oqk[0:3];
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'hff8000000000000000000000000000007f80000000000000007fffffffffffffffffc000000000000000000000000000003fc0000000000000003fffffffffffffffffe000000000000000000000000000001fe0000000000000001ffffffffffffffffff000000000000000000000000000000ff0000000000000000ffffffffffffffff))u_fill0(.clk(clk),.source_select(b),.legacy_select(b1),.bank0(a),.bank1(z),.word_out(ofill[0]));
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'h1ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff))u_qk0(.clk(clk),.source_select(f),.legacy_select(f1),.bank0(a),.bank1(z),.word_out(oqk[0]));
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'hff8000000000000000000000000000007fffffffffffffffffffffffff800000007fc000000000000000000000000000003fffffffffffffffffffffffffc00000003fe000000000000000000000000000001fffffffffffffffffffffffffe00000001ff000000000000000000000000000000ffffffffffffffffffffffffff00000000))u_fill1(.clk(clk),.source_select(b),.legacy_select(b1),.bank0(a),.bank1(z),.word_out(ofill[1]));
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'h3fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe000000000000000000000000000000000000000000000000000000000000000000))u_qk1(.clk(clk),.source_select(f),.legacy_select(f1),.bank0(a),.bank1(z),.word_out(oqk[1]));
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'hff80000000000000007fffffffffffffff800000007fffffff80000000000000007fc0000000000000003fffffffffffffffc00000003fffffffc0000000000000003fe0000000000000001fffffffffffffffe00000001fffffffe0000000000000001ff0000000000000000ffffffffffffffff00000000ffffffff0000000000000000))u_fill2(.clk(clk),.source_select(b),.legacy_select(b1),.bank0(a),.bank1(z),.word_out(ofill[2]));
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'h7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffc000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000))u_qk2(.clk(clk),.source_select(f),.legacy_select(f1),.bank0(a),.bank1(z),.word_out(oqk[2]));
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'hffffffffffffffffff8000000000007f807fffffff8000000000000000000000007fffffffffffffffffc000000000003fc03fffffffc000000000000000000000003fffffffffffffffffe000000000001fe01fffffffe000000000000000000000001ffffffffffffffffff000000000000ff00ffffffff000000000000000000000000))u_fill3(.clk(clk),.source_select(b),.legacy_select(b1),.bank0(a),.bank1(z),.word_out(ofill[3]));
ot_hdc_v41x_stagepick_n32 #(.W(1060),.LIVE(1060'hffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000))u_qk3(.clk(clk),.source_select(f),.legacy_select(f1),.bank0(a),.bank1(z),.word_out(oqk[3]));
integer i,j,checks=0,negative=0;
initial begin
 for(i=0;i<5000;i=i+1)begin
  @(negedge clk);if(i%211==0)begin f=0;b=0;end else if(($urandom%4)==0)begin b=f;f=!f;end
  for(j=0;j<34;j=j+1)begin
   if(j<33)begin a[j*32+:32]=$urandom;z[j*32+:32]=$urandom;end
   else begin a[1059:1056]=4'($urandom);z[1059:1056]=4'($urandom);end
  end
  @(posedge clk);#1;
  if(i>2)for(j=0;j<4;j=j+1)begin
   if(ofill[j] !== (b1?z:a))$fatal(1,"fill mismatch tile%0d",j);
   if(oqk[j] !== (f1?z:a))$fatal(1,"qk mismatch tile%0d",j);
   checks+=2;if((f0?z:a)!==(f1?z:a))negative++;
  end
 end
 if(negative<1000)$fatal(1,"shortstage negative not caught");
 $display("STAGEPICK PASS complete_word_checks=%0d bits_per_word=1060 shortstage_negative=%0d",checks,negative);$finish;
end
endmodule
