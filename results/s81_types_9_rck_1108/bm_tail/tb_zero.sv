`timescale 1ns/1ps
module tb;
reg clk=0; always #0.4165 clk=~clk;
reg rs_n=0, ld=0; reg [299:0] S=0;
wire [159:0] la,lb;wire [149:0] oa,ob;wire [4:0] La,Lb;wire aa,ab;wire [3:0] da,db;
wire [45:0] ldloc={46{ld}};
wire [45:0] ldnew=ldloc ^ (`ifdef RXS_CTL_MUT (46'd1<<17) `else 46'd0 `endif);
ot_s81_kp4_bm_ref #(.NG(8)) a(clk,rs_n,{8{ld}},S,la,oa,La,aa,da);
ot_s81_kp4_bm #(.NG(46),.THC(1)) b(clk,rs_n,ldnew,S,lb,ob,Lb,ab,db);
integer c,j,checks=0,errors=0,frames=0,zero_loads=0,tail_ones=0;
initial begin
for(c=0;c<4000;c=c+1) begin
 @(negedge clk);
 rs_n=(c%700)>=5;ld=rs_n && ((c%700-8)%30==0);
 for(j=0;j<10;j=j+1) S[j*30+:30]=$urandom;
 if(ld && ((c/30)%3==0))begin S[9:0]=0;zero_loads++;end
 if(ld && ((c/30)%11==0))S=0;
 @(posedge clk);#0.001;
 if(c%700>40)begin
 checks=checks+1;
 if(b.th_last===1'b1)tail_ones++;
 if(a.th[45][0]!==b.th_last)errors++;
 if({da,aa,La}!=={db,ab,Lb}) errors=errors+1;
 if(da[0])begin frames=frames+1;if({la,oa}!=={lb,ob}) errors=errors+1;end
 end
end
$display("BM_TAIL zero_loads=%0d tail_ones=%0d",zero_loads,tail_ones);
$display("BM_TAIL checks=%0d frames=%0d errors=%0d",checks,frames,errors);
if(errors||frames<50||zero_loads<20||tail_ones<20)$fatal(1,"BM_TAIL FAILED");
$finish;
end
endmodule
