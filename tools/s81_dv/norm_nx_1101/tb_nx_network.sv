`timescale 1ps/1fs
module tb_nx_network;
reg clk=0;always #416.5 clk=~clk;reg rst_n=0,go=0;integer cyc=0,mut=0,nr=0,bad=0;reg[15:0]seen=0;string dir;reg[31:0]partials[0:79],eps[0:0];
wire[1103:0]iw[0:15],ie[0:15],oe[0:15],ow[0:15];wire[275:0]iv[0:15],ov[0:15];wire[172:0]wi[0:15],ei[0:15],eo[0:15],wo[0:15];wire[15:0]rbv,xfault,rfault;wire[31:0]rbd[0:15];reg[15:0]sv=0;reg[6:0]si[0:15];
assign iw[0]=1104'd0;
reg[1103:0]p1[0:4];integer j1;always @(posedge clk)begin if(!rst_n)for(j1=0;j1<5;j1++)p1[j1]<=0;else begin p1[0]<=ow[2];for(j1=1;j1<5;j1++)p1[j1]<=p1[j1-1];end end
assign ie[0]=p1[4];
reg[275:0]p2[0:30];integer j2;always @(posedge clk)begin if(!rst_n)for(j2=0;j2<31;j2++)p2[j2]<=0;else begin p2[0]<=ov[1];for(j2=1;j2<31;j2++)p2[j2]<=p2[j2-1];end end
assign iv[0]=p2[30];
assign iw[1]=1104'd0;
reg[1103:0]p4[0:4];integer j4;always @(posedge clk)begin if(!rst_n)for(j4=0;j4<5;j4++)p4[j4]<=0;else begin p4[0]<=ow[3];for(j4=1;j4<5;j4++)p4[j4]<=p4[j4-1];end end
assign ie[1]=p4[4];
reg[275:0]p5[0:35];integer j5;always @(posedge clk)begin if(!rst_n)for(j5=0;j5<36;j5++)p5[j5]<=0;else begin p5[0]<=ov[0];for(j5=1;j5<36;j5++)p5[j5]<=p5[j5-1];end end
assign iv[1]=p5[35];
reg[1103:0]p6[0:4];integer j6;always @(posedge clk)begin if(!rst_n)for(j6=0;j6<5;j6++)p6[j6]<=0;else begin p6[0]<=oe[0];for(j6=1;j6<5;j6++)p6[j6]<=p6[j6-1];end end
assign iw[2]=((mut==2)?p6[3]:p6[4]);
reg[1103:0]p7[0:1];integer j7;always @(posedge clk)begin if(!rst_n)for(j7=0;j7<2;j7++)p7[j7]<=0;else begin p7[0]<=ow[4];for(j7=1;j7<2;j7++)p7[j7]<=p7[j7-1];end end
assign ie[2]=p7[1];
reg[275:0]p8[0:30];integer j8;always @(posedge clk)begin if(!rst_n)for(j8=0;j8<31;j8++)p8[j8]<=0;else begin p8[0]<=ov[3];for(j8=1;j8<31;j8++)p8[j8]<=p8[j8-1];end end
assign iv[2]=p8[30];
reg[1103:0]p9[0:4];integer j9;always @(posedge clk)begin if(!rst_n)for(j9=0;j9<5;j9++)p9[j9]<=0;else begin p9[0]<=oe[1];for(j9=1;j9<5;j9++)p9[j9]<=p9[j9-1];end end
assign iw[3]=p9[4];
reg[1103:0]p10[0:1];integer j10;always @(posedge clk)begin if(!rst_n)for(j10=0;j10<2;j10++)p10[j10]<=0;else begin p10[0]<=ow[5];for(j10=1;j10<2;j10++)p10[j10]<=p10[j10-1];end end
assign ie[3]=p10[1];
reg[275:0]p11[0:34];integer j11;always @(posedge clk)begin if(!rst_n)for(j11=0;j11<35;j11++)p11[j11]<=0;else begin p11[0]<=ov[2];for(j11=1;j11<35;j11++)p11[j11]<=p11[j11-1];end end
assign iv[3]=p11[34];
reg[1103:0]p12[0:1];integer j12;always @(posedge clk)begin if(!rst_n)for(j12=0;j12<2;j12++)p12[j12]<=0;else begin p12[0]<=oe[2];for(j12=1;j12<2;j12++)p12[j12]<=p12[j12-1];end end
assign iw[4]=p12[1];
reg[1103:0]p13[0:4];integer j13;always @(posedge clk)begin if(!rst_n)for(j13=0;j13<5;j13++)p13[j13]<=0;else begin p13[0]<=ow[6];for(j13=1;j13<5;j13++)p13[j13]<=p13[j13-1];end end
assign ie[4]=p13[4];
reg[275:0]p14[0:35];integer j14;always @(posedge clk)begin if(!rst_n)for(j14=0;j14<36;j14++)p14[j14]<=0;else begin p14[0]<=ov[5];for(j14=1;j14<36;j14++)p14[j14]<=p14[j14-1];end end
assign iv[4]=p14[35];
reg[1103:0]p15[0:1];integer j15;always @(posedge clk)begin if(!rst_n)for(j15=0;j15<2;j15++)p15[j15]<=0;else begin p15[0]<=oe[3];for(j15=1;j15<2;j15++)p15[j15]<=p15[j15-1];end end
assign iw[5]=p15[1];
reg[1103:0]p16[0:4];integer j16;always @(posedge clk)begin if(!rst_n)for(j16=0;j16<5;j16++)p16[j16]<=0;else begin p16[0]<=ow[7];for(j16=1;j16<5;j16++)p16[j16]<=p16[j16-1];end end
assign ie[5]=p16[4];
reg[275:0]p17[0:35];integer j17;always @(posedge clk)begin if(!rst_n)for(j17=0;j17<36;j17++)p17[j17]<=0;else begin p17[0]<=ov[4];for(j17=1;j17<36;j17++)p17[j17]<=p17[j17-1];end end
assign iv[5]=p17[35];
reg[1103:0]p18[0:4];integer j18;always @(posedge clk)begin if(!rst_n)for(j18=0;j18<5;j18++)p18[j18]<=0;else begin p18[0]<=oe[4];for(j18=1;j18<5;j18++)p18[j18]<=p18[j18-1];end end
assign iw[6]=p18[4];
reg[1103:0]p19[0:1];integer j19;always @(posedge clk)begin if(!rst_n)for(j19=0;j19<2;j19++)p19[j19]<=0;else begin p19[0]<=ow[8];for(j19=1;j19<2;j19++)p19[j19]<=p19[j19-1];end end
assign ie[6]=p19[1];
assign iv[6]=276'd0;
reg[1103:0]p21[0:4];integer j21;always @(posedge clk)begin if(!rst_n)for(j21=0;j21<5;j21++)p21[j21]<=0;else begin p21[0]<=oe[5];for(j21=1;j21<5;j21++)p21[j21]<=p21[j21-1];end end
assign iw[7]=p21[4];
reg[1103:0]p22[0:1];integer j22;always @(posedge clk)begin if(!rst_n)for(j22=0;j22<2;j22++)p22[j22]<=0;else begin p22[0]<=ow[9];for(j22=1;j22<2;j22++)p22[j22]<=p22[j22-1];end end
assign ie[7]=p22[1];
assign iv[7]=276'd0;
reg[1103:0]p24[0:1];integer j24;always @(posedge clk)begin if(!rst_n)for(j24=0;j24<2;j24++)p24[j24]<=0;else begin p24[0]<=oe[6];for(j24=1;j24<2;j24++)p24[j24]<=p24[j24-1];end end
assign iw[8]=p24[1];
reg[1103:0]p25[0:4];integer j25;always @(posedge clk)begin if(!rst_n)for(j25=0;j25<5;j25++)p25[j25]<=0;else begin p25[0]<=ow[10];for(j25=1;j25<5;j25++)p25[j25]<=p25[j25-1];end end
assign ie[8]=p25[4];
assign iv[8]=276'd0;
reg[1103:0]p27[0:1];integer j27;always @(posedge clk)begin if(!rst_n)for(j27=0;j27<2;j27++)p27[j27]<=0;else begin p27[0]<=oe[7];for(j27=1;j27<2;j27++)p27[j27]<=p27[j27-1];end end
assign iw[9]=p27[1];
reg[1103:0]p28[0:4];integer j28;always @(posedge clk)begin if(!rst_n)for(j28=0;j28<5;j28++)p28[j28]<=0;else begin p28[0]<=ow[11];for(j28=1;j28<5;j28++)p28[j28]<=p28[j28-1];end end
assign ie[9]=p28[4];
assign iv[9]=276'd0;
reg[1103:0]p30[0:4];integer j30;always @(posedge clk)begin if(!rst_n)for(j30=0;j30<5;j30++)p30[j30]<=0;else begin p30[0]<=oe[8];for(j30=1;j30<5;j30++)p30[j30]<=p30[j30-1];end end
assign iw[10]=p30[4];
reg[1103:0]p31[0:1];integer j31;always @(posedge clk)begin if(!rst_n)for(j31=0;j31<2;j31++)p31[j31]<=0;else begin p31[0]<=ow[12];for(j31=1;j31<2;j31++)p31[j31]<=p31[j31-1];end end
assign ie[10]=p31[1];
reg[275:0]p32[0:30];integer j32;always @(posedge clk)begin if(!rst_n)for(j32=0;j32<31;j32++)p32[j32]<=0;else begin p32[0]<=ov[11];for(j32=1;j32<31;j32++)p32[j32]<=p32[j32-1];end end
assign iv[10]=p32[30];
reg[1103:0]p33[0:4];integer j33;always @(posedge clk)begin if(!rst_n)for(j33=0;j33<5;j33++)p33[j33]<=0;else begin p33[0]<=oe[9];for(j33=1;j33<5;j33++)p33[j33]<=p33[j33-1];end end
assign iw[11]=p33[4];
reg[1103:0]p34[0:1];integer j34;always @(posedge clk)begin if(!rst_n)for(j34=0;j34<2;j34++)p34[j34]<=0;else begin p34[0]<=ow[13];for(j34=1;j34<2;j34++)p34[j34]<=p34[j34-1];end end
assign ie[11]=p34[1];
reg[275:0]p35[0:35];integer j35;always @(posedge clk)begin if(!rst_n)for(j35=0;j35<36;j35++)p35[j35]<=0;else begin p35[0]<=ov[10];for(j35=1;j35<36;j35++)p35[j35]<=p35[j35-1];end end
assign iv[11]=p35[35];
reg[1103:0]p36[0:1];integer j36;always @(posedge clk)begin if(!rst_n)for(j36=0;j36<2;j36++)p36[j36]<=0;else begin p36[0]<=oe[10];for(j36=1;j36<2;j36++)p36[j36]<=p36[j36-1];end end
assign iw[12]=p36[1];
reg[1103:0]p37[0:4];integer j37;always @(posedge clk)begin if(!rst_n)for(j37=0;j37<5;j37++)p37[j37]<=0;else begin p37[0]<=ow[14];for(j37=1;j37<5;j37++)p37[j37]<=p37[j37-1];end end
assign ie[12]=p37[4];
assign iv[12]=276'd0;
reg[1103:0]p39[0:1];integer j39;always @(posedge clk)begin if(!rst_n)for(j39=0;j39<2;j39++)p39[j39]<=0;else begin p39[0]<=oe[11];for(j39=1;j39<2;j39++)p39[j39]<=p39[j39-1];end end
assign iw[13]=p39[1];
reg[1103:0]p40[0:4];integer j40;always @(posedge clk)begin if(!rst_n)for(j40=0;j40<5;j40++)p40[j40]<=0;else begin p40[0]<=ow[15];for(j40=1;j40<5;j40++)p40[j40]<=p40[j40-1];end end
assign ie[13]=p40[4];
assign iv[13]=276'd0;
reg[1103:0]p42[0:4];integer j42;always @(posedge clk)begin if(!rst_n)for(j42=0;j42<5;j42++)p42[j42]<=0;else begin p42[0]<=oe[12];for(j42=1;j42<5;j42++)p42[j42]<=p42[j42-1];end end
assign iw[14]=p42[4];
assign ie[14]=1104'd0;
reg[275:0]p44[0:35];integer j44;always @(posedge clk)begin if(!rst_n)for(j44=0;j44<36;j44++)p44[j44]<=0;else begin p44[0]<=ov[15];for(j44=1;j44<36;j44++)p44[j44]<=p44[j44-1];end end
assign iv[14]=p44[35];
reg[1103:0]p45[0:4];integer j45;always @(posedge clk)begin if(!rst_n)for(j45=0;j45<5;j45++)p45[j45]<=0;else begin p45[0]<=oe[13];for(j45=1;j45<5;j45++)p45[j45]<=p45[j45-1];end end
assign iw[15]=p45[4];
assign ie[15]=1104'd0;
reg[275:0]p47[0:35];integer j47;always @(posedge clk)begin if(!rst_n)for(j47=0;j47<36;j47++)p47[j47]<=0;else begin p47[0]<=ov[14];for(j47=1;j47<36;j47++)p47[j47]<=p47[j47-1];end end
assign iv[15]=p47[35];
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf0(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&0==3)?4'd4:4'd0)),.eps(eps[0]),.s_v(sv[0]),.s_i(si[0]),.s(partials[0+int'(si[0])]),.rb_v(rbv[0]),.rb_d(rbd[0]),.fault(xfault[0]),.wi_v(wi[0][172]),.wi_h(wi[0][171:168]),.wi_b(wi[0][167:160]),.wi_d(wi[0][159:0]),.ei_v(ei[0][172]),.ei_h(ei[0][171:168]),.ei_b(ei[0][167:160]),.ei_d(ei[0][159:0]),.eo_v(eo[0][172]),.eo_h(eo[0][171:168]),.eo_b(eo[0][167:160]),.eo_d(eo[0][159:0]),.wo_v(wo[0][172]),.wo_h(wo[0][171:168]),.wo_b(wo[0][167:160]),.wo_d(wo[0][159:0]));
ot_s81sl_rstopt_xo r0(.clk(clk),.rst_n(rst_n),.sid(4'd0),.ri_w(iw[0]),.ri_e(ie[0]),.vi(iv[0]),.ro_e(oe[0]),.ro_w(ow[0]),.vo(ov[0]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[0]),.nx_ei(ei[0]),.nx_eo(eo[0]),.nx_wo(wo[0]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[0]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf1(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&1==3)?4'd4:4'd1)),.eps(eps[0]),.s_v(sv[1]),.s_i(si[1]),.s(partials[5+int'(si[1])]),.rb_v(rbv[1]),.rb_d(rbd[1]),.fault(xfault[1]),.wi_v(wi[1][172]),.wi_h(wi[1][171:168]),.wi_b(wi[1][167:160]),.wi_d(wi[1][159:0]),.ei_v(ei[1][172]),.ei_h(ei[1][171:168]),.ei_b(ei[1][167:160]),.ei_d(ei[1][159:0]),.eo_v(eo[1][172]),.eo_h(eo[1][171:168]),.eo_b(eo[1][167:160]),.eo_d(eo[1][159:0]),.wo_v(wo[1][172]),.wo_h(wo[1][171:168]),.wo_b(wo[1][167:160]),.wo_d(wo[1][159:0]));
ot_s81sl_rstopt_xo r1(.clk(clk),.rst_n(rst_n),.sid(4'd1),.ri_w(iw[1]),.ri_e(ie[1]),.vi(iv[1]),.ro_e(oe[1]),.ro_w(ow[1]),.vo(ov[1]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[1]),.nx_ei(ei[1]),.nx_eo(eo[1]),.nx_wo(wo[1]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[1]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf2(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&2==3)?4'd4:4'd2)),.eps(eps[0]),.s_v(sv[2]),.s_i(si[2]),.s(partials[10+int'(si[2])]),.rb_v(rbv[2]),.rb_d(rbd[2]),.fault(xfault[2]),.wi_v(wi[2][172]),.wi_h(wi[2][171:168]),.wi_b(wi[2][167:160]),.wi_d(wi[2][159:0]),.ei_v(ei[2][172]),.ei_h(ei[2][171:168]),.ei_b(ei[2][167:160]),.ei_d(ei[2][159:0]),.eo_v(eo[2][172]),.eo_h(eo[2][171:168]),.eo_b(eo[2][167:160]),.eo_d(eo[2][159:0]),.wo_v(wo[2][172]),.wo_h(wo[2][171:168]),.wo_b(wo[2][167:160]),.wo_d(wo[2][159:0]));
ot_s81sl_rstopt_xo r2(.clk(clk),.rst_n(rst_n),.sid(4'd2),.ri_w(iw[2]),.ri_e(ie[2]),.vi(iv[2]),.ro_e(oe[2]),.ro_w(ow[2]),.vo(ov[2]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[2]),.nx_ei(ei[2]),.nx_eo(eo[2]),.nx_wo(wo[2]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[2]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf3(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&3==3)?4'd4:4'd3)),.eps(eps[0]),.s_v(sv[3]),.s_i(si[3]),.s(partials[15+int'(si[3])]),.rb_v(rbv[3]),.rb_d(rbd[3]),.fault(xfault[3]),.wi_v(wi[3][172]),.wi_h(wi[3][171:168]),.wi_b(wi[3][167:160]),.wi_d(wi[3][159:0]),.ei_v(ei[3][172]),.ei_h(ei[3][171:168]),.ei_b(ei[3][167:160]),.ei_d(ei[3][159:0]),.eo_v(eo[3][172]),.eo_h(eo[3][171:168]),.eo_b(eo[3][167:160]),.eo_d(eo[3][159:0]),.wo_v(wo[3][172]),.wo_h(wo[3][171:168]),.wo_b(wo[3][167:160]),.wo_d(wo[3][159:0]));
ot_s81sl_rstopt_xo r3(.clk(clk),.rst_n(rst_n),.sid(4'd3),.ri_w(iw[3]),.ri_e(ie[3]),.vi(iv[3]),.ro_e(oe[3]),.ro_w(ow[3]),.vo(ov[3]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[3]),.nx_ei(ei[3]),.nx_eo(eo[3]),.nx_wo(wo[3]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[3]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf4(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&4==3)?4'd4:4'd4)),.eps(eps[0]),.s_v(sv[4]),.s_i(si[4]),.s(partials[20+int'(si[4])]),.rb_v(rbv[4]),.rb_d(rbd[4]),.fault(xfault[4]),.wi_v(wi[4][172]),.wi_h(wi[4][171:168]),.wi_b(wi[4][167:160]),.wi_d(wi[4][159:0]),.ei_v(ei[4][172]),.ei_h(ei[4][171:168]),.ei_b(ei[4][167:160]),.ei_d(ei[4][159:0]),.eo_v(eo[4][172]),.eo_h(eo[4][171:168]),.eo_b(eo[4][167:160]),.eo_d(eo[4][159:0]),.wo_v(wo[4][172]),.wo_h(wo[4][171:168]),.wo_b(wo[4][167:160]),.wo_d(wo[4][159:0]));
ot_s81sl_rstopt_xo r4(.clk(clk),.rst_n(rst_n),.sid(4'd4),.ri_w(iw[4]),.ri_e(ie[4]),.vi(iv[4]),.ro_e(oe[4]),.ro_w(ow[4]),.vo(ov[4]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[4]),.nx_ei(ei[4]),.nx_eo(eo[4]),.nx_wo(wo[4]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[4]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf5(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&5==3)?4'd4:4'd5)),.eps(eps[0]),.s_v(sv[5]),.s_i(si[5]),.s(partials[25+int'(si[5])]),.rb_v(rbv[5]),.rb_d(rbd[5]),.fault(xfault[5]),.wi_v(wi[5][172]),.wi_h(wi[5][171:168]),.wi_b(wi[5][167:160]),.wi_d(wi[5][159:0]),.ei_v(ei[5][172]),.ei_h(ei[5][171:168]),.ei_b(ei[5][167:160]),.ei_d(ei[5][159:0]),.eo_v(eo[5][172]),.eo_h(eo[5][171:168]),.eo_b(eo[5][167:160]),.eo_d(eo[5][159:0]),.wo_v(wo[5][172]),.wo_h(wo[5][171:168]),.wo_b(wo[5][167:160]),.wo_d(wo[5][159:0]));
ot_s81sl_rstopt_xo r5(.clk(clk),.rst_n(rst_n),.sid(4'd5),.ri_w(iw[5]),.ri_e(ie[5]),.vi(iv[5]),.ro_e(oe[5]),.ro_w(ow[5]),.vo(ov[5]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[5]),.nx_ei(ei[5]),.nx_eo(eo[5]),.nx_wo(wo[5]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[5]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf6(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&6==3)?4'd4:4'd6)),.eps(eps[0]),.s_v(sv[6]),.s_i(si[6]),.s(partials[30+int'(si[6])]),.rb_v(rbv[6]),.rb_d(rbd[6]),.fault(xfault[6]),.wi_v(wi[6][172]),.wi_h(wi[6][171:168]),.wi_b(wi[6][167:160]),.wi_d(wi[6][159:0]),.ei_v(ei[6][172]),.ei_h(ei[6][171:168]),.ei_b(ei[6][167:160]),.ei_d(ei[6][159:0]),.eo_v(eo[6][172]),.eo_h(eo[6][171:168]),.eo_b(eo[6][167:160]),.eo_d(eo[6][159:0]),.wo_v(wo[6][172]),.wo_h(wo[6][171:168]),.wo_b(wo[6][167:160]),.wo_d(wo[6][159:0]));
ot_s81sl_rstop r6(.clk(clk),.rst_n(rst_n),.sid(4'd6),.ri_w(iw[6]),.ri_e(ie[6]),.vi(iv[6]),.ro_e(oe[6]),.ro_w(ow[6]),.vo(ov[6]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[6]),.nx_ei(ei[6]),.nx_eo(eo[6]),.nx_wo(wo[6]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[6]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf7(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&7==3)?4'd4:4'd7)),.eps(eps[0]),.s_v(sv[7]),.s_i(si[7]),.s(partials[35+int'(si[7])]),.rb_v(rbv[7]),.rb_d(rbd[7]),.fault(xfault[7]),.wi_v(wi[7][172]),.wi_h(wi[7][171:168]),.wi_b(wi[7][167:160]),.wi_d(wi[7][159:0]),.ei_v(ei[7][172]),.ei_h(ei[7][171:168]),.ei_b(ei[7][167:160]),.ei_d(ei[7][159:0]),.eo_v(eo[7][172]),.eo_h(eo[7][171:168]),.eo_b(eo[7][167:160]),.eo_d(eo[7][159:0]),.wo_v(wo[7][172]),.wo_h(wo[7][171:168]),.wo_b(wo[7][167:160]),.wo_d(wo[7][159:0]));
ot_s81sl_rstop r7(.clk(clk),.rst_n(rst_n),.sid(4'd7),.ri_w(iw[7]),.ri_e(ie[7]),.vi(iv[7]),.ro_e(oe[7]),.ro_w(ow[7]),.vo(ov[7]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[7]),.nx_ei(ei[7]),.nx_eo(eo[7]),.nx_wo(wo[7]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[7]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf8(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&8==3)?4'd4:4'd8)),.eps(eps[0]),.s_v(sv[8]),.s_i(si[8]),.s(partials[40+int'(si[8])]),.rb_v(rbv[8]),.rb_d(rbd[8]),.fault(xfault[8]),.wi_v(wi[8][172]),.wi_h(wi[8][171:168]),.wi_b(wi[8][167:160]),.wi_d(wi[8][159:0]),.ei_v(ei[8][172]),.ei_h(ei[8][171:168]),.ei_b(ei[8][167:160]),.ei_d(ei[8][159:0]),.eo_v(eo[8][172]),.eo_h(eo[8][171:168]),.eo_b(eo[8][167:160]),.eo_d(eo[8][159:0]),.wo_v(wo[8][172]),.wo_h(wo[8][171:168]),.wo_b(wo[8][167:160]),.wo_d(wo[8][159:0]));
ot_s81sl_rstopt_xo r8(.clk(clk),.rst_n(rst_n),.sid(4'd8),.ri_w(iw[8]),.ri_e(ie[8]),.vi(iv[8]),.ro_e(oe[8]),.ro_w(ow[8]),.vo(ov[8]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[8]),.nx_ei(ei[8]),.nx_eo(eo[8]),.nx_wo(wo[8]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[8]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf9(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&9==3)?4'd4:4'd9)),.eps(eps[0]),.s_v(sv[9]),.s_i(si[9]),.s(partials[45+int'(si[9])]),.rb_v(rbv[9]),.rb_d(rbd[9]),.fault(xfault[9]),.wi_v(wi[9][172]),.wi_h(wi[9][171:168]),.wi_b(wi[9][167:160]),.wi_d(wi[9][159:0]),.ei_v(ei[9][172]),.ei_h(ei[9][171:168]),.ei_b(ei[9][167:160]),.ei_d(ei[9][159:0]),.eo_v(eo[9][172]),.eo_h(eo[9][171:168]),.eo_b(eo[9][167:160]),.eo_d(eo[9][159:0]),.wo_v(wo[9][172]),.wo_h(wo[9][171:168]),.wo_b(wo[9][167:160]),.wo_d(wo[9][159:0]));
ot_s81sl_rstopt_xo r9(.clk(clk),.rst_n(rst_n),.sid(4'd9),.ri_w(iw[9]),.ri_e(ie[9]),.vi(iv[9]),.ro_e(oe[9]),.ro_w(ow[9]),.vo(ov[9]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[9]),.nx_ei(ei[9]),.nx_eo(eo[9]),.nx_wo(wo[9]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[9]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf10(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&10==3)?4'd4:4'd10)),.eps(eps[0]),.s_v(sv[10]),.s_i(si[10]),.s(partials[50+int'(si[10])]),.rb_v(rbv[10]),.rb_d(rbd[10]),.fault(xfault[10]),.wi_v(wi[10][172]),.wi_h(wi[10][171:168]),.wi_b(wi[10][167:160]),.wi_d(wi[10][159:0]),.ei_v(ei[10][172]),.ei_h(ei[10][171:168]),.ei_b(ei[10][167:160]),.ei_d(ei[10][159:0]),.eo_v(eo[10][172]),.eo_h(eo[10][171:168]),.eo_b(eo[10][167:160]),.eo_d(eo[10][159:0]),.wo_v(wo[10][172]),.wo_h(wo[10][171:168]),.wo_b(wo[10][167:160]),.wo_d(wo[10][159:0]));
ot_s81sl_rstopt_xo r10(.clk(clk),.rst_n(rst_n),.sid(4'd10),.ri_w(iw[10]),.ri_e(ie[10]),.vi(iv[10]),.ro_e(oe[10]),.ro_w(ow[10]),.vo(ov[10]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[10]),.nx_ei(ei[10]),.nx_eo(eo[10]),.nx_wo(wo[10]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[10]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf11(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&11==3)?4'd4:4'd11)),.eps(eps[0]),.s_v(sv[11]),.s_i(si[11]),.s(partials[55+int'(si[11])]),.rb_v(rbv[11]),.rb_d(rbd[11]),.fault(xfault[11]),.wi_v(wi[11][172]),.wi_h(wi[11][171:168]),.wi_b(wi[11][167:160]),.wi_d(wi[11][159:0]),.ei_v(ei[11][172]),.ei_h(ei[11][171:168]),.ei_b(ei[11][167:160]),.ei_d(ei[11][159:0]),.eo_v(eo[11][172]),.eo_h(eo[11][171:168]),.eo_b(eo[11][167:160]),.eo_d(eo[11][159:0]),.wo_v(wo[11][172]),.wo_h(wo[11][171:168]),.wo_b(wo[11][167:160]),.wo_d(wo[11][159:0]));
ot_s81sl_rstopt_xo r11(.clk(clk),.rst_n(rst_n),.sid(4'd11),.ri_w(iw[11]),.ri_e(ie[11]),.vi(iv[11]),.ro_e(oe[11]),.ro_w(ow[11]),.vo(ov[11]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[11]),.nx_ei(ei[11]),.nx_eo(eo[11]),.nx_wo(wo[11]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[11]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf12(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&12==3)?4'd4:4'd12)),.eps(eps[0]),.s_v(sv[12]),.s_i(si[12]),.s(partials[60+int'(si[12])]),.rb_v(rbv[12]),.rb_d(rbd[12]),.fault(xfault[12]),.wi_v(wi[12][172]),.wi_h(wi[12][171:168]),.wi_b(wi[12][167:160]),.wi_d(wi[12][159:0]),.ei_v(ei[12][172]),.ei_h(ei[12][171:168]),.ei_b(ei[12][167:160]),.ei_d(ei[12][159:0]),.eo_v(eo[12][172]),.eo_h(eo[12][171:168]),.eo_b(eo[12][167:160]),.eo_d(eo[12][159:0]),.wo_v(wo[12][172]),.wo_h(wo[12][171:168]),.wo_b(wo[12][167:160]),.wo_d(wo[12][159:0]));
ot_s81sl_rstopt_xo r12(.clk(clk),.rst_n(rst_n),.sid(4'd12),.ri_w(iw[12]),.ri_e(ie[12]),.vi(iv[12]),.ro_e(oe[12]),.ro_w(ow[12]),.vo(ov[12]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[12]),.nx_ei(ei[12]),.nx_eo(eo[12]),.nx_wo(wo[12]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[12]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf13(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&13==3)?4'd4:4'd13)),.eps(eps[0]),.s_v(sv[13]),.s_i(si[13]),.s(partials[65+int'(si[13])]),.rb_v(rbv[13]),.rb_d(rbd[13]),.fault(xfault[13]),.wi_v(wi[13][172]),.wi_h(wi[13][171:168]),.wi_b(wi[13][167:160]),.wi_d(wi[13][159:0]),.ei_v(ei[13][172]),.ei_h(ei[13][171:168]),.ei_b(ei[13][167:160]),.ei_d(ei[13][159:0]),.eo_v(eo[13][172]),.eo_h(eo[13][171:168]),.eo_b(eo[13][167:160]),.eo_d(eo[13][159:0]),.wo_v(wo[13][172]),.wo_h(wo[13][171:168]),.wo_b(wo[13][167:160]),.wo_d(wo[13][159:0]));
ot_s81sl_rstopt_xo r13(.clk(clk),.rst_n(rst_n),.sid(4'd13),.ri_w(iw[13]),.ri_e(ie[13]),.vi(iv[13]),.ro_e(oe[13]),.ro_w(ow[13]),.vo(ov[13]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[13]),.nx_ei(ei[13]),.nx_eo(eo[13]),.nx_wo(wo[13]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[13]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf14(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&14==3)?4'd4:4'd14)),.eps(eps[0]),.s_v(sv[14]),.s_i(si[14]),.s(partials[70+int'(si[14])]),.rb_v(rbv[14]),.rb_d(rbd[14]),.fault(xfault[14]),.wi_v(wi[14][172]),.wi_h(wi[14][171:168]),.wi_b(wi[14][167:160]),.wi_d(wi[14][159:0]),.ei_v(ei[14][172]),.ei_h(ei[14][171:168]),.ei_b(ei[14][167:160]),.ei_d(ei[14][159:0]),.eo_v(eo[14][172]),.eo_h(eo[14][171:168]),.eo_b(eo[14][167:160]),.eo_d(eo[14][159:0]),.wo_v(wo[14][172]),.wo_h(wo[14][171:168]),.wo_b(wo[14][167:160]),.wo_d(wo[14][159:0]));
ot_s81sl_rstopt_xo r14(.clk(clk),.rst_n(rst_n),.sid(4'd14),.ri_w(iw[14]),.ri_e(ie[14]),.vi(iv[14]),.ro_e(oe[14]),.ro_w(ow[14]),.vo(ov[14]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[14]),.nx_ei(ei[14]),.nx_eo(eo[14]),.nx_wo(wo[14]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[14]));
ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(7)) xf15(.clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(((mut==3&&15==3)?4'd4:4'd15)),.eps(eps[0]),.s_v(sv[15]),.s_i(si[15]),.s(partials[75+int'(si[15])]),.rb_v(rbv[15]),.rb_d(rbd[15]),.fault(xfault[15]),.wi_v(wi[15][172]),.wi_h(wi[15][171:168]),.wi_b(wi[15][167:160]),.wi_d(wi[15][159:0]),.ei_v(ei[15][172]),.ei_h(ei[15][171:168]),.ei_b(ei[15][167:160]),.ei_d(ei[15][159:0]),.eo_v(eo[15][172]),.eo_h(eo[15][171:168]),.eo_b(eo[15][167:160]),.eo_d(eo[15][159:0]),.wo_v(wo[15][172]),.wo_h(wo[15][171:168]),.wo_b(wo[15][167:160]),.wo_d(wo[15][159:0]));
ot_s81sl_rstopt_xo r15(.clk(clk),.rst_n(rst_n),.sid(4'd15),.ri_w(iw[15]),.ri_e(ie[15]),.vi(iv[15]),.ro_e(oe[15]),.ro_w(ow[15]),.vo(ov[15]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[15]),.nx_ei(ei[15]),.nx_eo(eo[15]),.nx_wo(wo[15]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(rfault[15]));
integer k;always @(negedge clk)begin if(cyc==32)rst_n=1;go=(cyc==64);sv=0;
si[0]=0;for(k=0;k<5;k++)if(cyc==465+k)begin sv[0]=1;si[0]=7'(k);end
si[1]=0;for(k=0;k<5;k++)if(cyc==353+k)begin sv[1]=1;si[1]=7'(k);end
si[2]=0;for(k=0;k<5;k++)if(cyc==463+k)begin sv[2]=1;si[2]=7'(k);end
si[3]=0;for(k=0;k<5;k++)if(cyc==344+k)begin sv[3]=1;si[3]=7'(k);end
si[4]=0;for(k=0;k<5;k++)if(cyc==458+k)begin sv[4]=1;si[4]=7'(k);end
si[5]=0;for(k=0;k<5;k++)if(cyc==365+k)begin sv[5]=1;si[5]=7'(k);end
si[6]=0;for(k=0;k<5;k++)if(cyc==455+k)begin sv[6]=1;si[6]=7'(k);end
si[7]=0;for(k=0;k<5;k++)if(cyc==329+k)begin sv[7]=1;si[7]=7'(k);end
si[8]=0;for(k=0;k<5;k++)if(cyc==446+k)begin sv[8]=1;si[8]=7'(k);end
si[9]=0;for(k=0;k<5;k++)if(cyc==356+k)begin sv[9]=1;si[9]=7'(k);end
si[10]=0;for(k=0;k<5;k++)if(cyc==482+k)begin sv[10]=1;si[10]=7'(k);end
si[11]=0;for(k=0;k<5;k++)if(cyc==362+k)begin sv[11]=1;si[11]=7'(k);end
si[12]=0;for(k=0;k<5;k++)if(cyc==494+k)begin sv[12]=1;si[12]=7'(k);end
si[13]=0;for(k=0;k<5;k++)if(cyc==384+k)begin sv[13]=1;si[13]=7'(k);end
si[14]=0;for(k=0;k<5;k++)if(cyc==506+k)begin sv[14]=1;si[14]=7'(k);end
si[15]=0;for(k=0;k<5;k++)if(cyc==383+k)begin sv[15]=1;si[15]=7'(k);end
end
always @(posedge clk)begin cyc=cyc+1;#0.001;
if(rst_n)begin if(rbv[0])begin nr++;if(seen[0]||rbd[0]!==32'h40ca3c85)bad++;seen[0]=1;$display("NX_NET_RSTD sid0 cycle%0d word%08h",cyc,rbd[0]);end
if(xf0.dl_v[0])$display("NX_NET_DL sid0 port0 cycle%0d base%0d",cyc,xf0.dl_b[0+:8]);
if(xf0.dl_v[1])$display("NX_NET_DL sid0 port1 cycle%0d base%0d",cyc,xf0.dl_b[8+:8]);
if(xf0.dl_v[2])$display("NX_NET_DL sid0 port2 cycle%0d base%0d",cyc,xf0.dl_b[16+:8]);
if(xf0.u_f.wr_v&&xf0.u_f.wr_n==1)$display("NX_NET_ROOT sid0 cycle%0d",cyc);
if(oe[0][0]&&oe[0][3:1]==3'd3)$display("NX_NET_WORD sid0 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[0][20:13],oe[0][8:4],oe[0][21+:160]);
if(ow[0][0]&&ow[0][3:1]==3'd3)$display("NX_NET_WORD sid0 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[0][20:13],ow[0][8:4],ow[0][21+:160]);
if(ov[0][0]&&ov[0][3:1]==3'd3)$display("NX_NET_WORD sid0 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[0][20:13],ov[0][8:4],ov[0][21+:160]);
end
if(rst_n)begin if(rbv[1])begin nr++;if(seen[1]||rbd[1]!==32'h40ca3c85)bad++;seen[1]=1;$display("NX_NET_RSTD sid1 cycle%0d word%08h",cyc,rbd[1]);end
if(xf1.dl_v[0])$display("NX_NET_DL sid1 port0 cycle%0d base%0d",cyc,xf1.dl_b[0+:8]);
if(xf1.dl_v[1])$display("NX_NET_DL sid1 port1 cycle%0d base%0d",cyc,xf1.dl_b[8+:8]);
if(xf1.dl_v[2])$display("NX_NET_DL sid1 port2 cycle%0d base%0d",cyc,xf1.dl_b[16+:8]);
if(xf1.u_f.wr_v&&xf1.u_f.wr_n==1)$display("NX_NET_ROOT sid1 cycle%0d",cyc);
if(oe[1][0]&&oe[1][3:1]==3'd3)$display("NX_NET_WORD sid1 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[1][20:13],oe[1][8:4],oe[1][21+:160]);
if(ow[1][0]&&ow[1][3:1]==3'd3)$display("NX_NET_WORD sid1 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[1][20:13],ow[1][8:4],ow[1][21+:160]);
if(ov[1][0]&&ov[1][3:1]==3'd3)$display("NX_NET_WORD sid1 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[1][20:13],ov[1][8:4],ov[1][21+:160]);
end
if(rst_n)begin if(rbv[2])begin nr++;if(seen[2]||rbd[2]!==32'h40ca3c85)bad++;seen[2]=1;$display("NX_NET_RSTD sid2 cycle%0d word%08h",cyc,rbd[2]);end
if(xf2.dl_v[0])$display("NX_NET_DL sid2 port0 cycle%0d base%0d",cyc,xf2.dl_b[0+:8]);
if(xf2.dl_v[1])$display("NX_NET_DL sid2 port1 cycle%0d base%0d",cyc,xf2.dl_b[8+:8]);
if(xf2.dl_v[2])$display("NX_NET_DL sid2 port2 cycle%0d base%0d",cyc,xf2.dl_b[16+:8]);
if(xf2.u_f.wr_v&&xf2.u_f.wr_n==1)$display("NX_NET_ROOT sid2 cycle%0d",cyc);
if(oe[2][0]&&oe[2][3:1]==3'd3)$display("NX_NET_WORD sid2 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[2][20:13],oe[2][8:4],oe[2][21+:160]);
if(ow[2][0]&&ow[2][3:1]==3'd3)$display("NX_NET_WORD sid2 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[2][20:13],ow[2][8:4],ow[2][21+:160]);
if(ov[2][0]&&ov[2][3:1]==3'd3)$display("NX_NET_WORD sid2 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[2][20:13],ov[2][8:4],ov[2][21+:160]);
end
if(rst_n)begin if(rbv[3])begin nr++;if(seen[3]||rbd[3]!==32'h40ca3c85)bad++;seen[3]=1;$display("NX_NET_RSTD sid3 cycle%0d word%08h",cyc,rbd[3]);end
if(xf3.dl_v[0])$display("NX_NET_DL sid3 port0 cycle%0d base%0d",cyc,xf3.dl_b[0+:8]);
if(xf3.dl_v[1])$display("NX_NET_DL sid3 port1 cycle%0d base%0d",cyc,xf3.dl_b[8+:8]);
if(xf3.dl_v[2])$display("NX_NET_DL sid3 port2 cycle%0d base%0d",cyc,xf3.dl_b[16+:8]);
if(xf3.u_f.wr_v&&xf3.u_f.wr_n==1)$display("NX_NET_ROOT sid3 cycle%0d",cyc);
if(oe[3][0]&&oe[3][3:1]==3'd3)$display("NX_NET_WORD sid3 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[3][20:13],oe[3][8:4],oe[3][21+:160]);
if(ow[3][0]&&ow[3][3:1]==3'd3)$display("NX_NET_WORD sid3 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[3][20:13],ow[3][8:4],ow[3][21+:160]);
if(ov[3][0]&&ov[3][3:1]==3'd3)$display("NX_NET_WORD sid3 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[3][20:13],ov[3][8:4],ov[3][21+:160]);
end
if(rst_n)begin if(rbv[4])begin nr++;if(seen[4]||rbd[4]!==32'h40ca3c85)bad++;seen[4]=1;$display("NX_NET_RSTD sid4 cycle%0d word%08h",cyc,rbd[4]);end
if(xf4.dl_v[0])$display("NX_NET_DL sid4 port0 cycle%0d base%0d",cyc,xf4.dl_b[0+:8]);
if(xf4.dl_v[1])$display("NX_NET_DL sid4 port1 cycle%0d base%0d",cyc,xf4.dl_b[8+:8]);
if(xf4.dl_v[2])$display("NX_NET_DL sid4 port2 cycle%0d base%0d",cyc,xf4.dl_b[16+:8]);
if(xf4.u_f.wr_v&&xf4.u_f.wr_n==1)$display("NX_NET_ROOT sid4 cycle%0d",cyc);
if(oe[4][0]&&oe[4][3:1]==3'd3)$display("NX_NET_WORD sid4 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[4][20:13],oe[4][8:4],oe[4][21+:160]);
if(ow[4][0]&&ow[4][3:1]==3'd3)$display("NX_NET_WORD sid4 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[4][20:13],ow[4][8:4],ow[4][21+:160]);
if(ov[4][0]&&ov[4][3:1]==3'd3)$display("NX_NET_WORD sid4 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[4][20:13],ov[4][8:4],ov[4][21+:160]);
end
if(rst_n)begin if(rbv[5])begin nr++;if(seen[5]||rbd[5]!==32'h40ca3c85)bad++;seen[5]=1;$display("NX_NET_RSTD sid5 cycle%0d word%08h",cyc,rbd[5]);end
if(xf5.dl_v[0])$display("NX_NET_DL sid5 port0 cycle%0d base%0d",cyc,xf5.dl_b[0+:8]);
if(xf5.dl_v[1])$display("NX_NET_DL sid5 port1 cycle%0d base%0d",cyc,xf5.dl_b[8+:8]);
if(xf5.dl_v[2])$display("NX_NET_DL sid5 port2 cycle%0d base%0d",cyc,xf5.dl_b[16+:8]);
if(xf5.u_f.wr_v&&xf5.u_f.wr_n==1)$display("NX_NET_ROOT sid5 cycle%0d",cyc);
if(oe[5][0]&&oe[5][3:1]==3'd3)$display("NX_NET_WORD sid5 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[5][20:13],oe[5][8:4],oe[5][21+:160]);
if(ow[5][0]&&ow[5][3:1]==3'd3)$display("NX_NET_WORD sid5 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[5][20:13],ow[5][8:4],ow[5][21+:160]);
if(ov[5][0]&&ov[5][3:1]==3'd3)$display("NX_NET_WORD sid5 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[5][20:13],ov[5][8:4],ov[5][21+:160]);
end
if(rst_n)begin if(rbv[6])begin nr++;if(seen[6]||rbd[6]!==32'h40ca3c85)bad++;seen[6]=1;$display("NX_NET_RSTD sid6 cycle%0d word%08h",cyc,rbd[6]);end
if(xf6.dl_v[0])$display("NX_NET_DL sid6 port0 cycle%0d base%0d",cyc,xf6.dl_b[0+:8]);
if(xf6.dl_v[1])$display("NX_NET_DL sid6 port1 cycle%0d base%0d",cyc,xf6.dl_b[8+:8]);
if(xf6.dl_v[2])$display("NX_NET_DL sid6 port2 cycle%0d base%0d",cyc,xf6.dl_b[16+:8]);
if(xf6.u_f.wr_v&&xf6.u_f.wr_n==1)$display("NX_NET_ROOT sid6 cycle%0d",cyc);
if(oe[6][0]&&oe[6][3:1]==3'd3)$display("NX_NET_WORD sid6 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[6][20:13],oe[6][8:4],oe[6][21+:160]);
if(ow[6][0]&&ow[6][3:1]==3'd3)$display("NX_NET_WORD sid6 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[6][20:13],ow[6][8:4],ow[6][21+:160]);
if(ov[6][0]&&ov[6][3:1]==3'd3)$display("NX_NET_WORD sid6 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[6][20:13],ov[6][8:4],ov[6][21+:160]);
end
if(rst_n)begin if(rbv[7])begin nr++;if(seen[7]||rbd[7]!==32'h40ca3c85)bad++;seen[7]=1;$display("NX_NET_RSTD sid7 cycle%0d word%08h",cyc,rbd[7]);end
if(xf7.dl_v[0])$display("NX_NET_DL sid7 port0 cycle%0d base%0d",cyc,xf7.dl_b[0+:8]);
if(xf7.dl_v[1])$display("NX_NET_DL sid7 port1 cycle%0d base%0d",cyc,xf7.dl_b[8+:8]);
if(xf7.dl_v[2])$display("NX_NET_DL sid7 port2 cycle%0d base%0d",cyc,xf7.dl_b[16+:8]);
if(xf7.u_f.wr_v&&xf7.u_f.wr_n==1)$display("NX_NET_ROOT sid7 cycle%0d",cyc);
if(oe[7][0]&&oe[7][3:1]==3'd3)$display("NX_NET_WORD sid7 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[7][20:13],oe[7][8:4],oe[7][21+:160]);
if(ow[7][0]&&ow[7][3:1]==3'd3)$display("NX_NET_WORD sid7 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[7][20:13],ow[7][8:4],ow[7][21+:160]);
if(ov[7][0]&&ov[7][3:1]==3'd3)$display("NX_NET_WORD sid7 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[7][20:13],ov[7][8:4],ov[7][21+:160]);
end
if(rst_n)begin if(rbv[8])begin nr++;if(seen[8]||rbd[8]!==32'h40ca3c85)bad++;seen[8]=1;$display("NX_NET_RSTD sid8 cycle%0d word%08h",cyc,rbd[8]);end
if(xf8.dl_v[0])$display("NX_NET_DL sid8 port0 cycle%0d base%0d",cyc,xf8.dl_b[0+:8]);
if(xf8.dl_v[1])$display("NX_NET_DL sid8 port1 cycle%0d base%0d",cyc,xf8.dl_b[8+:8]);
if(xf8.dl_v[2])$display("NX_NET_DL sid8 port2 cycle%0d base%0d",cyc,xf8.dl_b[16+:8]);
if(xf8.u_f.wr_v&&xf8.u_f.wr_n==1)$display("NX_NET_ROOT sid8 cycle%0d",cyc);
if(oe[8][0]&&oe[8][3:1]==3'd3)$display("NX_NET_WORD sid8 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[8][20:13],oe[8][8:4],oe[8][21+:160]);
if(ow[8][0]&&ow[8][3:1]==3'd3)$display("NX_NET_WORD sid8 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[8][20:13],ow[8][8:4],ow[8][21+:160]);
if(ov[8][0]&&ov[8][3:1]==3'd3)$display("NX_NET_WORD sid8 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[8][20:13],ov[8][8:4],ov[8][21+:160]);
end
if(rst_n)begin if(rbv[9])begin nr++;if(seen[9]||rbd[9]!==32'h40ca3c85)bad++;seen[9]=1;$display("NX_NET_RSTD sid9 cycle%0d word%08h",cyc,rbd[9]);end
if(xf9.dl_v[0])$display("NX_NET_DL sid9 port0 cycle%0d base%0d",cyc,xf9.dl_b[0+:8]);
if(xf9.dl_v[1])$display("NX_NET_DL sid9 port1 cycle%0d base%0d",cyc,xf9.dl_b[8+:8]);
if(xf9.dl_v[2])$display("NX_NET_DL sid9 port2 cycle%0d base%0d",cyc,xf9.dl_b[16+:8]);
if(xf9.u_f.wr_v&&xf9.u_f.wr_n==1)$display("NX_NET_ROOT sid9 cycle%0d",cyc);
if(oe[9][0]&&oe[9][3:1]==3'd3)$display("NX_NET_WORD sid9 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[9][20:13],oe[9][8:4],oe[9][21+:160]);
if(ow[9][0]&&ow[9][3:1]==3'd3)$display("NX_NET_WORD sid9 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[9][20:13],ow[9][8:4],ow[9][21+:160]);
if(ov[9][0]&&ov[9][3:1]==3'd3)$display("NX_NET_WORD sid9 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[9][20:13],ov[9][8:4],ov[9][21+:160]);
end
if(rst_n)begin if(rbv[10])begin nr++;if(seen[10]||rbd[10]!==32'h40ca3c85)bad++;seen[10]=1;$display("NX_NET_RSTD sid10 cycle%0d word%08h",cyc,rbd[10]);end
if(xf10.dl_v[0])$display("NX_NET_DL sid10 port0 cycle%0d base%0d",cyc,xf10.dl_b[0+:8]);
if(xf10.dl_v[1])$display("NX_NET_DL sid10 port1 cycle%0d base%0d",cyc,xf10.dl_b[8+:8]);
if(xf10.dl_v[2])$display("NX_NET_DL sid10 port2 cycle%0d base%0d",cyc,xf10.dl_b[16+:8]);
if(xf10.u_f.wr_v&&xf10.u_f.wr_n==1)$display("NX_NET_ROOT sid10 cycle%0d",cyc);
if(oe[10][0]&&oe[10][3:1]==3'd3)$display("NX_NET_WORD sid10 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[10][20:13],oe[10][8:4],oe[10][21+:160]);
if(ow[10][0]&&ow[10][3:1]==3'd3)$display("NX_NET_WORD sid10 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[10][20:13],ow[10][8:4],ow[10][21+:160]);
if(ov[10][0]&&ov[10][3:1]==3'd3)$display("NX_NET_WORD sid10 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[10][20:13],ov[10][8:4],ov[10][21+:160]);
end
if(rst_n)begin if(rbv[11])begin nr++;if(seen[11]||rbd[11]!==32'h40ca3c85)bad++;seen[11]=1;$display("NX_NET_RSTD sid11 cycle%0d word%08h",cyc,rbd[11]);end
if(xf11.dl_v[0])$display("NX_NET_DL sid11 port0 cycle%0d base%0d",cyc,xf11.dl_b[0+:8]);
if(xf11.dl_v[1])$display("NX_NET_DL sid11 port1 cycle%0d base%0d",cyc,xf11.dl_b[8+:8]);
if(xf11.dl_v[2])$display("NX_NET_DL sid11 port2 cycle%0d base%0d",cyc,xf11.dl_b[16+:8]);
if(xf11.u_f.wr_v&&xf11.u_f.wr_n==1)$display("NX_NET_ROOT sid11 cycle%0d",cyc);
if(oe[11][0]&&oe[11][3:1]==3'd3)$display("NX_NET_WORD sid11 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[11][20:13],oe[11][8:4],oe[11][21+:160]);
if(ow[11][0]&&ow[11][3:1]==3'd3)$display("NX_NET_WORD sid11 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[11][20:13],ow[11][8:4],ow[11][21+:160]);
if(ov[11][0]&&ov[11][3:1]==3'd3)$display("NX_NET_WORD sid11 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[11][20:13],ov[11][8:4],ov[11][21+:160]);
end
if(rst_n)begin if(rbv[12])begin nr++;if(seen[12]||rbd[12]!==32'h40ca3c85)bad++;seen[12]=1;$display("NX_NET_RSTD sid12 cycle%0d word%08h",cyc,rbd[12]);end
if(xf12.dl_v[0])$display("NX_NET_DL sid12 port0 cycle%0d base%0d",cyc,xf12.dl_b[0+:8]);
if(xf12.dl_v[1])$display("NX_NET_DL sid12 port1 cycle%0d base%0d",cyc,xf12.dl_b[8+:8]);
if(xf12.dl_v[2])$display("NX_NET_DL sid12 port2 cycle%0d base%0d",cyc,xf12.dl_b[16+:8]);
if(xf12.u_f.wr_v&&xf12.u_f.wr_n==1)$display("NX_NET_ROOT sid12 cycle%0d",cyc);
if(oe[12][0]&&oe[12][3:1]==3'd3)$display("NX_NET_WORD sid12 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[12][20:13],oe[12][8:4],oe[12][21+:160]);
if(ow[12][0]&&ow[12][3:1]==3'd3)$display("NX_NET_WORD sid12 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[12][20:13],ow[12][8:4],ow[12][21+:160]);
if(ov[12][0]&&ov[12][3:1]==3'd3)$display("NX_NET_WORD sid12 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[12][20:13],ov[12][8:4],ov[12][21+:160]);
end
if(rst_n)begin if(rbv[13])begin nr++;if(seen[13]||rbd[13]!==32'h40ca3c85)bad++;seen[13]=1;$display("NX_NET_RSTD sid13 cycle%0d word%08h",cyc,rbd[13]);end
if(xf13.dl_v[0])$display("NX_NET_DL sid13 port0 cycle%0d base%0d",cyc,xf13.dl_b[0+:8]);
if(xf13.dl_v[1])$display("NX_NET_DL sid13 port1 cycle%0d base%0d",cyc,xf13.dl_b[8+:8]);
if(xf13.dl_v[2])$display("NX_NET_DL sid13 port2 cycle%0d base%0d",cyc,xf13.dl_b[16+:8]);
if(xf13.u_f.wr_v&&xf13.u_f.wr_n==1)$display("NX_NET_ROOT sid13 cycle%0d",cyc);
if(oe[13][0]&&oe[13][3:1]==3'd3)$display("NX_NET_WORD sid13 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[13][20:13],oe[13][8:4],oe[13][21+:160]);
if(ow[13][0]&&ow[13][3:1]==3'd3)$display("NX_NET_WORD sid13 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[13][20:13],ow[13][8:4],ow[13][21+:160]);
if(ov[13][0]&&ov[13][3:1]==3'd3)$display("NX_NET_WORD sid13 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[13][20:13],ov[13][8:4],ov[13][21+:160]);
end
if(rst_n)begin if(rbv[14])begin nr++;if(seen[14]||rbd[14]!==32'h40ca3c85)bad++;seen[14]=1;$display("NX_NET_RSTD sid14 cycle%0d word%08h",cyc,rbd[14]);end
if(xf14.dl_v[0])$display("NX_NET_DL sid14 port0 cycle%0d base%0d",cyc,xf14.dl_b[0+:8]);
if(xf14.dl_v[1])$display("NX_NET_DL sid14 port1 cycle%0d base%0d",cyc,xf14.dl_b[8+:8]);
if(xf14.dl_v[2])$display("NX_NET_DL sid14 port2 cycle%0d base%0d",cyc,xf14.dl_b[16+:8]);
if(xf14.u_f.wr_v&&xf14.u_f.wr_n==1)$display("NX_NET_ROOT sid14 cycle%0d",cyc);
if(oe[14][0]&&oe[14][3:1]==3'd3)$display("NX_NET_WORD sid14 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[14][20:13],oe[14][8:4],oe[14][21+:160]);
if(ow[14][0]&&ow[14][3:1]==3'd3)$display("NX_NET_WORD sid14 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[14][20:13],ow[14][8:4],ow[14][21+:160]);
if(ov[14][0]&&ov[14][3:1]==3'd3)$display("NX_NET_WORD sid14 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[14][20:13],ov[14][8:4],ov[14][21+:160]);
end
if(rst_n)begin if(rbv[15])begin nr++;if(seen[15]||rbd[15]!==32'h40ca3c85)bad++;seen[15]=1;$display("NX_NET_RSTD sid15 cycle%0d word%08h",cyc,rbd[15]);end
if(xf15.dl_v[0])$display("NX_NET_DL sid15 port0 cycle%0d base%0d",cyc,xf15.dl_b[0+:8]);
if(xf15.dl_v[1])$display("NX_NET_DL sid15 port1 cycle%0d base%0d",cyc,xf15.dl_b[8+:8]);
if(xf15.dl_v[2])$display("NX_NET_DL sid15 port2 cycle%0d base%0d",cyc,xf15.dl_b[16+:8]);
if(xf15.u_f.wr_v&&xf15.u_f.wr_n==1)$display("NX_NET_ROOT sid15 cycle%0d",cyc);
if(oe[15][0]&&oe[15][3:1]==3'd3)$display("NX_NET_WORD sid15 ro_e cycle%0d base%0d hops%0d data%040h",cyc,oe[15][20:13],oe[15][8:4],oe[15][21+:160]);
if(ow[15][0]&&ow[15][3:1]==3'd3)$display("NX_NET_WORD sid15 ro_w cycle%0d base%0d hops%0d data%040h",cyc,ow[15][20:13],ow[15][8:4],ow[15][21+:160]);
if(ov[15][0]&&ov[15][3:1]==3'd3)$display("NX_NET_WORD sid15 vo cycle%0d base%0d hops%0d data%040h",cyc,ov[15][20:13],ov[15][8:4],ov[15][21+:160]);
end
if(cyc==2000)begin $display("NX_NET_RESULT count%0d seen%h bad%0d xf_fault%h r_fault%h mut%0d",nr,seen,bad,xfault,rfault,mut);if(nr==16&&seen==16'hffff&&bad==0&&xfault==0&&rfault==0)$display("NX_NET_PASS");else $fatal(1,"NX_NET_FAIL");$finish;end
end
initial begin if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");void'($value$plusargs("MUT=%d",mut));$readmemh({dir,"/actual_partials80.hex"},partials);$readmemh({dir,"/eps_actual_config.hex"},eps);if(mut==1)partials[0]=partials[0]^32'h80000000;end
endmodule
