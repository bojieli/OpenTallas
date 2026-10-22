`timescale 1ns/1ps
module comb4_tb; integer count=0; integer i,j,k;
reg [1:0] a0;
wire p0,o0;
AND2x2_ASAP7_75t_R p_0(.Y(p0),.A(a0[0]),.B(a0[1]));
official_AND2x2_ASAP7_75t_R o_0(.Y(o0),.A(a0[0]),.B(a0[1]));
reg [2:0] a1;
wire p1,o1;
AND3x1_ASAP7_75t_R p_1(.Y(p1),.A(a1[0]),.B(a1[1]),.C(a1[2]));
official_AND3x1_ASAP7_75t_R o_1(.Y(o1),.A(a1[0]),.B(a1[1]),.C(a1[2]));
reg [3:0] a2;
wire p2,o2;
AND4x1_ASAP7_75t_R p_2(.Y(p2),.A(a2[0]),.B(a2[1]),.C(a2[2]),.D(a2[3]));
official_AND4x1_ASAP7_75t_R o_2(.Y(o2),.A(a2[0]),.B(a2[1]),.C(a2[2]),.D(a2[3]));
reg [4:0] a3;
wire p3,o3;
AND5x1_ASAP7_75t_R p_3(.Y(p3),.A(a3[0]),.B(a3[1]),.C(a3[2]),.D(a3[3]),.E(a3[4]));
official_AND5x1_ASAP7_75t_R o_3(.Y(o3),.A(a3[0]),.B(a3[1]),.C(a3[2]),.D(a3[3]),.E(a3[4]));
reg [2:0] a4;
wire p4,o4;
AO21x1_ASAP7_75t_R p_4(.Y(p4),.A1(a4[0]),.A2(a4[1]),.B(a4[2]));
official_AO21x1_ASAP7_75t_R o_4(.Y(o4),.A1(a4[0]),.A2(a4[1]),.B(a4[2]));
reg [4:0] a5;
wire p5,o5;
AO221x1_ASAP7_75t_R p_5(.Y(p5),.A1(a5[0]),.A2(a5[1]),.B1(a5[2]),.B2(a5[3]),.C(a5[4]));
official_AO221x1_ASAP7_75t_R o_5(.Y(o5),.A1(a5[0]),.A2(a5[1]),.B1(a5[2]),.B2(a5[3]),.C(a5[4]));
reg [5:0] a6;
wire p6,o6;
AO222x2_ASAP7_75t_R p_6(.Y(p6),.A1(a6[0]),.A2(a6[1]),.B1(a6[2]),.B2(a6[3]),.C1(a6[4]),.C2(a6[5]));
official_AO222x2_ASAP7_75t_R o_6(.Y(o6),.A1(a6[0]),.A2(a6[1]),.B1(a6[2]),.B2(a6[3]),.C1(a6[4]),.C2(a6[5]));
reg [3:0] a7;
wire p7,o7;
AO22x1_ASAP7_75t_R p_7(.Y(p7),.A1(a7[0]),.A2(a7[1]),.B1(a7[2]),.B2(a7[3]));
official_AO22x1_ASAP7_75t_R o_7(.Y(o7),.A1(a7[0]),.A2(a7[1]),.B1(a7[2]),.B2(a7[3]));
reg [3:0] a8;
wire p8,o8;
AO31x2_ASAP7_75t_R p_8(.Y(p8),.A1(a8[0]),.A2(a8[1]),.A3(a8[2]),.B(a8[3]));
official_AO31x2_ASAP7_75t_R o_8(.Y(o8),.A1(a8[0]),.A2(a8[1]),.A3(a8[2]),.B(a8[3]));
reg [4:0] a9;
wire p9,o9;
AO32x1_ASAP7_75t_R p_9(.Y(p9),.A1(a9[0]),.A2(a9[1]),.A3(a9[2]),.B1(a9[3]),.B2(a9[4]));
official_AO32x1_ASAP7_75t_R o_9(.Y(o9),.A1(a9[0]),.A2(a9[1]),.A3(a9[2]),.B1(a9[3]),.B2(a9[4]));
reg [3:0] a10;
wire p10,o10;
AOI211x1_ASAP7_75t_R p_10(.Y(p10),.A1(a10[0]),.A2(a10[1]),.B(a10[2]),.C(a10[3]));
official_AOI211x1_ASAP7_75t_R o_10(.Y(o10),.A1(a10[0]),.A2(a10[1]),.B(a10[2]),.C(a10[3]));
reg [2:0] a11;
wire p11,o11;
AOI21x1_ASAP7_75t_R p_11(.Y(p11),.A1(a11[0]),.A2(a11[1]),.B(a11[2]));
official_AOI21x1_ASAP7_75t_R o_11(.Y(o11),.A1(a11[0]),.A2(a11[1]),.B(a11[2]));
reg [4:0] a12;
wire p12,o12;
AOI221x1_ASAP7_75t_R p_12(.Y(p12),.A1(a12[0]),.A2(a12[1]),.B1(a12[2]),.B2(a12[3]),.C(a12[4]));
official_AOI221x1_ASAP7_75t_R o_12(.Y(o12),.A1(a12[0]),.A2(a12[1]),.B1(a12[2]),.B2(a12[3]),.C(a12[4]));
reg [0:0] a13;
wire p13,o13;
BUFx12f_ASAP7_75t_R p_13(.Y(p13),.A(a13[0]));
official_BUFx12f_ASAP7_75t_R o_13(.Y(o13),.A(a13[0]));
reg [0:0] a14;
wire p14,o14;
BUFx2_ASAP7_75t_R p_14(.Y(p14),.A(a14[0]));
official_BUFx2_ASAP7_75t_R o_14(.Y(o14),.A(a14[0]));
reg [0:0] a15;
wire p15,o15;
BUFx3_ASAP7_75t_R p_15(.Y(p15),.A(a15[0]));
official_BUFx3_ASAP7_75t_R o_15(.Y(o15),.A(a15[0]));
reg [0:0] a16;
wire p16,o16;
BUFx4f_ASAP7_75t_R p_16(.Y(p16),.A(a16[0]));
official_BUFx4f_ASAP7_75t_R o_16(.Y(o16),.A(a16[0]));
reg [0:0] a17;
wire p17,o17;
BUFx5_ASAP7_75t_R p_17(.Y(p17),.A(a17[0]));
official_BUFx5_ASAP7_75t_R o_17(.Y(o17),.A(a17[0]));
reg [0:0] a18;
wire p18,o18;
BUFx6f_ASAP7_75t_R p_18(.Y(p18),.A(a18[0]));
official_BUFx6f_ASAP7_75t_R o_18(.Y(o18),.A(a18[0]));
reg [0:0] a19;
wire p19,o19;
BUFx8_ASAP7_75t_R p_19(.Y(p19),.A(a19[0]));
official_BUFx8_ASAP7_75t_R o_19(.Y(o19),.A(a19[0]));
reg [0:0] a20;
wire p20,o20;
INVx1_ASAP7_75t_R p_20(.Y(p20),.A(a20[0]));
official_INVx1_ASAP7_75t_R o_20(.Y(o20),.A(a20[0]));
reg [2:0] a21;
wire p21,o21;
MAJx2_ASAP7_75t_R p_21(.Y(p21),.A(a21[0]),.B(a21[1]),.C(a21[2]));
official_MAJx2_ASAP7_75t_R o_21(.Y(o21),.A(a21[0]),.B(a21[1]),.C(a21[2]));
reg [1:0] a22;
wire p22,o22;
NAND2x1_ASAP7_75t_R p_22(.Y(p22),.A(a22[0]),.B(a22[1]));
official_NAND2x1_ASAP7_75t_R o_22(.Y(o22),.A(a22[0]),.B(a22[1]));
reg [2:0] a23;
wire p23,o23;
NAND3x1_ASAP7_75t_R p_23(.Y(p23),.A(a23[0]),.B(a23[1]),.C(a23[2]));
official_NAND3x1_ASAP7_75t_R o_23(.Y(o23),.A(a23[0]),.B(a23[1]),.C(a23[2]));
reg [1:0] a24;
wire p24,o24;
NOR2x1_ASAP7_75t_R p_24(.Y(p24),.A(a24[0]),.B(a24[1]));
official_NOR2x1_ASAP7_75t_R o_24(.Y(o24),.A(a24[0]),.B(a24[1]));
reg [3:0] a25;
wire p25,o25;
OA211x2_ASAP7_75t_R p_25(.Y(p25),.A1(a25[0]),.A2(a25[1]),.B(a25[2]),.C(a25[3]));
official_OA211x2_ASAP7_75t_R o_25(.Y(o25),.A1(a25[0]),.A2(a25[1]),.B(a25[2]),.C(a25[3]));
reg [2:0] a26;
wire p26,o26;
OA21x2_ASAP7_75t_R p_26(.Y(p26),.A1(a26[0]),.A2(a26[1]),.B(a26[2]));
official_OA21x2_ASAP7_75t_R o_26(.Y(o26),.A1(a26[0]),.A2(a26[1]),.B(a26[2]));
reg [5:0] a27;
wire p27,o27;
OA222x2_ASAP7_75t_R p_27(.Y(p27),.A1(a27[0]),.A2(a27[1]),.B1(a27[2]),.B2(a27[3]),.C1(a27[4]),.C2(a27[5]));
official_OA222x2_ASAP7_75t_R o_27(.Y(o27),.A1(a27[0]),.A2(a27[1]),.B1(a27[2]),.B2(a27[3]),.C1(a27[4]),.C2(a27[5]));
reg [3:0] a28;
wire p28,o28;
OA22x2_ASAP7_75t_R p_28(.Y(p28),.A1(a28[0]),.A2(a28[1]),.B1(a28[2]),.B2(a28[3]));
official_OA22x2_ASAP7_75t_R o_28(.Y(o28),.A1(a28[0]),.A2(a28[1]),.B1(a28[2]),.B2(a28[3]));
reg [3:0] a29;
wire p29,o29;
OA31x2_ASAP7_75t_R p_29(.Y(p29),.A1(a29[0]),.A2(a29[1]),.A3(a29[2]),.B1(a29[3]));
official_OA31x2_ASAP7_75t_R o_29(.Y(o29),.A1(a29[0]),.A2(a29[1]),.A3(a29[2]),.B1(a29[3]));
reg [2:0] a30;
wire p30,o30;
OAI21x1_ASAP7_75t_R p_30(.Y(p30),.A1(a30[0]),.A2(a30[1]),.B(a30[2]));
official_OAI21x1_ASAP7_75t_R o_30(.Y(o30),.A1(a30[0]),.A2(a30[1]),.B(a30[2]));
reg [3:0] a31;
wire p31,o31;
OAI22x1_ASAP7_75t_R p_31(.Y(p31),.A1(a31[0]),.A2(a31[1]),.B1(a31[2]),.B2(a31[3]));
official_OAI22x1_ASAP7_75t_R o_31(.Y(o31),.A1(a31[0]),.A2(a31[1]),.B1(a31[2]),.B2(a31[3]));
reg [1:0] a32;
wire p32,o32;
OR2x2_ASAP7_75t_R p_32(.Y(p32),.A(a32[0]),.B(a32[1]));
official_OR2x2_ASAP7_75t_R o_32(.Y(o32),.A(a32[0]),.B(a32[1]));
reg [2:0] a33;
wire p33,o33;
OR3x1_ASAP7_75t_R p_33(.Y(p33),.A(a33[0]),.B(a33[1]),.C(a33[2]));
official_OR3x1_ASAP7_75t_R o_33(.Y(o33),.A(a33[0]),.B(a33[1]),.C(a33[2]));
reg [3:0] a34;
wire p34,o34;
OR4x1_ASAP7_75t_R p_34(.Y(p34),.A(a34[0]),.B(a34[1]),.C(a34[2]),.D(a34[3]));
official_OR4x1_ASAP7_75t_R o_34(.Y(o34),.A(a34[0]),.B(a34[1]),.C(a34[2]),.D(a34[3]));
wire p35,o35;
TIEHIx1_ASAP7_75t_R p_35(.H(p35));
official_TIEHIx1_ASAP7_75t_R o_35(.H(o35));
wire p36,o36;
TIELOx1_ASAP7_75t_R p_36(.L(p36));
official_TIELOx1_ASAP7_75t_R o_36(.L(o36));
reg [1:0] a37;
wire p37,o37;
XNOR2x2_ASAP7_75t_R p_37(.Y(p37),.A(a37[0]),.B(a37[1]));
official_XNOR2x2_ASAP7_75t_R o_37(.Y(o37),.A(a37[0]),.B(a37[1]));
reg [1:0] a38;
wire p38,o38;
XOR2x2_ASAP7_75t_R p_38(.Y(p38),.A(a38[0]),.B(a38[1]));
official_XOR2x2_ASAP7_75t_R o_38(.Y(o38),.A(a38[0]),.B(a38[1]));
function logic val(input integer x);case(x) 0:val=0;1:val=1;2:val=1'bx;3:val=1'bz;endcase endfunction
integer mismatches=0;initial begin
for(i=0;i<16;i=i+1)begin
a0[0]=val((i/1)%4);
a0[1]=val((i/4)%4);
#1;if(p0!==o0)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AND2x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p0,o0);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a1[0]=val((i/1)%4);
a1[1]=val((i/4)%4);
a1[2]=val((i/16)%4);
#1;if(p1!==o1)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AND3x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p1,o1);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a2[0]=val((i/1)%4);
a2[1]=val((i/4)%4);
a2[2]=val((i/16)%4);
a2[3]=val((i/64)%4);
#1;if(p2!==o2)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AND4x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p2,o2);end count=count+1;end
for(i=0;i<1024;i=i+1)begin
a3[0]=val((i/1)%4);
a3[1]=val((i/4)%4);
a3[2]=val((i/16)%4);
a3[3]=val((i/64)%4);
a3[4]=val((i/256)%4);
#1;if(p3!==o3)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AND5x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p3,o3);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a4[0]=val((i/1)%4);
a4[1]=val((i/4)%4);
a4[2]=val((i/16)%4);
#1;if(p4!==o4)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AO21x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p4,o4);end count=count+1;end
for(i=0;i<1024;i=i+1)begin
a5[0]=val((i/1)%4);
a5[1]=val((i/4)%4);
a5[2]=val((i/16)%4);
a5[3]=val((i/64)%4);
a5[4]=val((i/256)%4);
#1;if(p5!==o5)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AO221x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p5,o5);end count=count+1;end
for(i=0;i<4096;i=i+1)begin
a6[0]=val((i/1)%4);
a6[1]=val((i/4)%4);
a6[2]=val((i/16)%4);
a6[3]=val((i/64)%4);
a6[4]=val((i/256)%4);
a6[5]=val((i/1024)%4);
#1;if(p6!==o6)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AO222x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p6,o6);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a7[0]=val((i/1)%4);
a7[1]=val((i/4)%4);
a7[2]=val((i/16)%4);
a7[3]=val((i/64)%4);
#1;if(p7!==o7)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AO22x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p7,o7);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a8[0]=val((i/1)%4);
a8[1]=val((i/4)%4);
a8[2]=val((i/16)%4);
a8[3]=val((i/64)%4);
#1;if(p8!==o8)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AO31x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p8,o8);end count=count+1;end
for(i=0;i<1024;i=i+1)begin
a9[0]=val((i/1)%4);
a9[1]=val((i/4)%4);
a9[2]=val((i/16)%4);
a9[3]=val((i/64)%4);
a9[4]=val((i/256)%4);
#1;if(p9!==o9)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AO32x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p9,o9);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a10[0]=val((i/1)%4);
a10[1]=val((i/4)%4);
a10[2]=val((i/16)%4);
a10[3]=val((i/64)%4);
#1;if(p10!==o10)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AOI211x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p10,o10);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a11[0]=val((i/1)%4);
a11[1]=val((i/4)%4);
a11[2]=val((i/16)%4);
#1;if(p11!==o11)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AOI21x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p11,o11);end count=count+1;end
for(i=0;i<1024;i=i+1)begin
a12[0]=val((i/1)%4);
a12[1]=val((i/4)%4);
a12[2]=val((i/16)%4);
a12[3]=val((i/64)%4);
a12[4]=val((i/256)%4);
#1;if(p12!==o12)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE AOI221x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p12,o12);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a13[0]=val((i/1)%4);
#1;if(p13!==o13)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE BUFx12f_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p13,o13);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a14[0]=val((i/1)%4);
#1;if(p14!==o14)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE BUFx2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p14,o14);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a15[0]=val((i/1)%4);
#1;if(p15!==o15)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE BUFx3_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p15,o15);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a16[0]=val((i/1)%4);
#1;if(p16!==o16)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE BUFx4f_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p16,o16);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a17[0]=val((i/1)%4);
#1;if(p17!==o17)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE BUFx5_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p17,o17);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a18[0]=val((i/1)%4);
#1;if(p18!==o18)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE BUFx6f_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p18,o18);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a19[0]=val((i/1)%4);
#1;if(p19!==o19)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE BUFx8_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p19,o19);end count=count+1;end
for(i=0;i<4;i=i+1)begin
a20[0]=val((i/1)%4);
#1;if(p20!==o20)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE INVx1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p20,o20);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a21[0]=val((i/1)%4);
a21[1]=val((i/4)%4);
a21[2]=val((i/16)%4);
#1;if(p21!==o21)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE MAJx2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p21,o21);end count=count+1;end
for(i=0;i<16;i=i+1)begin
a22[0]=val((i/1)%4);
a22[1]=val((i/4)%4);
#1;if(p22!==o22)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE NAND2x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p22,o22);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a23[0]=val((i/1)%4);
a23[1]=val((i/4)%4);
a23[2]=val((i/16)%4);
#1;if(p23!==o23)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE NAND3x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p23,o23);end count=count+1;end
for(i=0;i<16;i=i+1)begin
a24[0]=val((i/1)%4);
a24[1]=val((i/4)%4);
#1;if(p24!==o24)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE NOR2x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p24,o24);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a25[0]=val((i/1)%4);
a25[1]=val((i/4)%4);
a25[2]=val((i/16)%4);
a25[3]=val((i/64)%4);
#1;if(p25!==o25)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OA211x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p25,o25);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a26[0]=val((i/1)%4);
a26[1]=val((i/4)%4);
a26[2]=val((i/16)%4);
#1;if(p26!==o26)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OA21x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p26,o26);end count=count+1;end
for(i=0;i<4096;i=i+1)begin
a27[0]=val((i/1)%4);
a27[1]=val((i/4)%4);
a27[2]=val((i/16)%4);
a27[3]=val((i/64)%4);
a27[4]=val((i/256)%4);
a27[5]=val((i/1024)%4);
#1;if(p27!==o27)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OA222x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p27,o27);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a28[0]=val((i/1)%4);
a28[1]=val((i/4)%4);
a28[2]=val((i/16)%4);
a28[3]=val((i/64)%4);
#1;if(p28!==o28)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OA22x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p28,o28);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a29[0]=val((i/1)%4);
a29[1]=val((i/4)%4);
a29[2]=val((i/16)%4);
a29[3]=val((i/64)%4);
#1;if(p29!==o29)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OA31x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p29,o29);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a30[0]=val((i/1)%4);
a30[1]=val((i/4)%4);
a30[2]=val((i/16)%4);
#1;if(p30!==o30)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OAI21x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p30,o30);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a31[0]=val((i/1)%4);
a31[1]=val((i/4)%4);
a31[2]=val((i/16)%4);
a31[3]=val((i/64)%4);
#1;if(p31!==o31)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OAI22x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p31,o31);end count=count+1;end
for(i=0;i<16;i=i+1)begin
a32[0]=val((i/1)%4);
a32[1]=val((i/4)%4);
#1;if(p32!==o32)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OR2x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p32,o32);end count=count+1;end
for(i=0;i<64;i=i+1)begin
a33[0]=val((i/1)%4);
a33[1]=val((i/4)%4);
a33[2]=val((i/16)%4);
#1;if(p33!==o33)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OR3x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p33,o33);end count=count+1;end
for(i=0;i<256;i=i+1)begin
a34[0]=val((i/1)%4);
a34[1]=val((i/4)%4);
a34[2]=val((i/16)%4);
a34[3]=val((i/64)%4);
#1;if(p34!==o34)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE OR4x1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p34,o34);end count=count+1;end
for(i=0;i<1;i=i+1)begin
#1;if(p35!==o35)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE TIEHIx1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p35,o35);end count=count+1;end
for(i=0;i<1;i=i+1)begin
#1;if(p36!==o36)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE TIELOx1_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p36,o36);end count=count+1;end
for(i=0;i<16;i=i+1)begin
a37[0]=val((i/1)%4);
a37[1]=val((i/4)%4);
#1;if(p37!==o37)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE XNOR2x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p37,o37);end count=count+1;end
for(i=0;i<16;i=i+1)begin
a38[0]=val((i/1)%4);
a38[1]=val((i/4)%4);
#1;if(p38!==o38)begin mismatches=mismatches+1;if(mismatches<20)$display("COMB4_COUNTEREXAMPLE XOR2x2_ASAP7_75t_R tuple=%0d projection=%b official=%b",i,p38,o38);end count=count+1;end
$display("COMB4_RESULT checks=%0d mismatches=%0d",count,mismatches);if(mismatches)$fatal(1,"COMB4_REJECTED");$finish;end endmodule
