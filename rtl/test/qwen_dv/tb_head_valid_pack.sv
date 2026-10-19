`timescale 1ns/1ps
module tb_head_valid_pack;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,v=0,clear=0;reg[2:0] cls=0;
 wire[7:0] boot,epoch;
 qfd_dv_head_valid_guards #(.LIMIT(136)) u_g(clk,rst_n,clear,boot,epoch);
 wire v11,v5,v4,v10,v126;
 wire[1:0] q11,q5,q4,q10;
 qfd_dv_head_sram_delay #(.W(2),.D(11)) u_11(clk,rst_n,{v,v},q11);
 qfd_dv_head_sram_delay #(.W(2),.D(5)) u_5(clk,rst_n,{v,v},q5);
 qfd_dv_head_sram_delay #(.W(2),.D(4)) u_4(clk,rst_n,{v,v},q4);
 qfd_dv_head_sram_delay #(.W(2),.D(10)) u_10(clk,rst_n,{(v&&!clear),v},q10);
 wire small4;qfd_dv_head_small_valid_ring #(.D(4)) u_small(clk,rst_n,v,small4);
 reg[6:0] wp=0,rp=0;reg cap;
 integer dsel=126;
 always @*case(cls)1:dsel=75;2:dsel=47;3:dsel=62;default:dsel=126;endcase
 always @(posedge clk or negedge rst_n)if(!rst_n)begin wp<=0;rp<=0;end else begin wp<=wp+1'b1;rp<=wp+7'd3-dsel[6:0];end
 wire[63:0] rq;
 ot_sram_1r1w2c_128x64_m1 u_tls(.wclk(clk),.rclk(clk),.r_ce_in(1'b1),.r_addr_in(rp),.rd_out(rq),.w_ce_in(1'b1),.w_addr_in(wp),.wd_in({63'b0,q10[1]}),.w_mask_in(64'b1));
 always @(posedge clk)cap<=rq[0];
 reg[135:0] refline=0;reg[10:0] r11=0;reg[4:0] r5=0;reg[3:0] r4=0;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin refline<=0;r11<=0;r5<=0;r4<=0;end else begin
 if(clear)refline<=0;else refline<={refline[134:0],v};
 r11<={r11[9:0],v};r5<={r5[3:0],v};r4<={r4[2:0],v};end
 integer n,depth,checks=0;reg expected,actual;
 initial begin
 for(n=0;n<6000;n=n+1)begin
 @(negedge clk);
 depth=(cls==0)?10:10+dsel;
 expected=refline[depth-1];actual=(epoch>=depth)&&((cls==0)?q10[1]:cap);
 if(rst_n)begin
 if(expected!==actual)$fatal(1,"HEAD_VALID_PACK_FAIL n=%0d cls=%0d epoch=%0d depth=%0d expected=%b actual=%b",n,cls,epoch,depth,expected,actual);
 if((q11[1]&&(boot>=11))!==r11[10] || (q5[1]&&(boot>=5))!==r5[4] || (q4[1]&&(boot>=4))!==r4[3] || (small4&&(boot>=4))!==r4[3])$fatal(1,"HEAD_VALID_FIXED_FAIL n=%0d",n);
 checks=checks+5;end
 // Deliberately fill with ones, reset dirty history, then alternate classes.
 rst_n=!(n<3 || (n>=1200 && n<1203) || (n>=3900 && n<3905));
 v=(n<1000)?1'b1:($urandom_range(0,7)>2);
 clear=(n%197==196)||(n%431==430);
 if(clear)cls=(cls==4)?0:cls+1;
 end
 $display("HEAD_VALID_PACK_PASS checks=%0d dirtyresets=2 classes=5",checks);$finish;
 end
endmodule
