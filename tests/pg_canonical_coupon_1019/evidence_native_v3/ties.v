module ot_pg_canonical_xor16_1019 (clk,
    rst_n,
    a,
    b,
    y);
 input clk;
 input rst_n;
 input [15:0] a;
 input [15:0] b;
 output [15:0] y;

 wire _00_;
 wire _01_;
 wire _02_;
 wire _03_;
 wire _04_;
 wire _05_;
 wire _06_;
 wire _07_;
 wire _08_;
 wire _09_;
 wire _10_;
 wire _11_;
 wire _12_;
 wire _13_;
 wire _14_;
 wire _15_;
 wire _16_;
 wire _17_;
 wire _18_;
 wire _19_;
 wire _20_;
 wire _21_;
 wire _22_;
 wire _23_;
 wire _24_;
 wire _25_;
 wire _26_;
 wire _27_;
 wire _28_;
 wire _29_;
 wire _30_;
 wire _31_;
 wire _32_;
 wire _33_;
 wire _34_;
 wire _35_;
 wire _36_;
 wire _37_;
 wire _38_;
 wire _39_;
 wire _40_;
 wire _41_;
 wire _42_;
 wire _43_;
 wire _44_;
 wire _45_;
 wire _46_;
 wire _47_;
 wire _48_;
 wire _49_;
 wire _50_;
 wire _51_;
 wire _52_;
 wire _53_;
 wire _54_;
 wire _55_;
 wire _56_;
 wire _57_;
 wire _58_;
 wire _59_;
 wire _60_;
 wire _61_;
 wire _62_;
 wire _63_;
 wire _64_;
 wire net50;
 wire reset_a;
 wire reset_b;
 wire reset_first;
 wire \u_reset_a/_0_ ;
 wire net51;
 wire \u_reset_b/_0_ ;
 wire net;
 wire net1;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net32;
 wire net33;
 wire net34;
 wire net35;
 wire net36;
 wire net37;
 wire net38;
 wire net39;
 wire net40;
 wire net41;
 wire net42;
 wire net43;
 wire net44;
 wire net45;
 wire net46;
 wire net47;
 wire net48;
 wire net49;

 INVx1_ASAP7_75t_R _66_ (.A(_64_),
    .Y(reset_first));
 INVx1_ASAP7_75t_R _67_ (.A(_45_),
    .Y(y[14]));
 INVx1_ASAP7_75t_R _68_ (.A(_46_),
    .Y(y[13]));
 INVx1_ASAP7_75t_R _69_ (.A(_47_),
    .Y(y[12]));
 INVx1_ASAP7_75t_R _70_ (.A(_48_),
    .Y(y[11]));
 INVx1_ASAP7_75t_R _71_ (.A(_49_),
    .Y(y[10]));
 INVx1_ASAP7_75t_R _72_ (.A(_50_),
    .Y(y[9]));
 INVx1_ASAP7_75t_R _73_ (.A(_51_),
    .Y(y[8]));
 INVx1_ASAP7_75t_R _74_ (.A(_52_),
    .Y(y[7]));
 INVx1_ASAP7_75t_R _75_ (.A(_53_),
    .Y(y[6]));
 INVx1_ASAP7_75t_R _76_ (.A(_54_),
    .Y(y[5]));
 INVx1_ASAP7_75t_R _77_ (.A(_55_),
    .Y(y[4]));
 INVx1_ASAP7_75t_R _78_ (.A(_56_),
    .Y(y[3]));
 INVx1_ASAP7_75t_R _79_ (.A(_57_),
    .Y(y[2]));
 XOR2x1_ASAP7_75t_R _80_ (.A(_23_),
    .Y(_05_),
    .B(_38_));
 XOR2x1_ASAP7_75t_R _81_ (.A(_24_),
    .Y(_04_),
    .B(_39_));
 XOR2x1_ASAP7_75t_R _82_ (.A(_25_),
    .Y(_03_),
    .B(_40_));
 XOR2x1_ASAP7_75t_R _83_ (.A(_26_),
    .Y(_02_),
    .B(_41_));
 XOR2x1_ASAP7_75t_R _84_ (.A(_27_),
    .Y(_01_),
    .B(_42_));
 XOR2x1_ASAP7_75t_R _85_ (.A(_28_),
    .Y(_15_),
    .B(_43_));
 XOR2x1_ASAP7_75t_R _86_ (.A(_29_),
    .Y(_14_),
    .B(_44_));
 XOR2x1_ASAP7_75t_R _87_ (.A(_30_),
    .Y(_13_),
    .B(_63_));
 XOR2x1_ASAP7_75t_R _88_ (.A(_17_),
    .Y(_12_),
    .B(_31_));
 XOR2x1_ASAP7_75t_R _89_ (.A(_16_),
    .Y(_11_),
    .B(_32_));
 XOR2x1_ASAP7_75t_R _90_ (.A(_18_),
    .Y(_10_),
    .B(_33_));
 XOR2x1_ASAP7_75t_R _91_ (.A(_19_),
    .Y(_09_),
    .B(_34_));
 XOR2x1_ASAP7_75t_R _92_ (.A(_20_),
    .Y(_08_),
    .B(_35_));
 XOR2x1_ASAP7_75t_R _93_ (.A(_21_),
    .Y(_07_),
    .B(_36_));
 XOR2x1_ASAP7_75t_R _94_ (.A(_22_),
    .Y(_00_),
    .B(_37_));
 INVx1_ASAP7_75t_R _95_ (.A(_58_),
    .Y(y[1]));
 INVx1_ASAP7_75t_R _96_ (.A(_59_),
    .Y(y[0]));
 INVx1_ASAP7_75t_R _97_ (.A(_60_),
    .Y(y[15]));
 XOR2x1_ASAP7_75t_R _98_ (.A(_61_),
    .Y(_06_),
    .B(_62_));
 DFFASRHQNx1_ASAP7_75t_R \a_q[0]$_DFF_PN0_  (.CLK(clk),
    .D(a[0]),
    .QN(_37_),
    .RESETN(reset_a),
    .SETN(net));
 TIEHIx1_ASAP7_75t_R \a_q[0]$_DFF_PN0__1  (.H(net));
 DFFASRHQNx1_ASAP7_75t_R \a_q[10]$_DFF_PN0_  (.CLK(clk),
    .D(a[10]),
    .QN(_27_),
    .RESETN(reset_a),
    .SETN(net1));
 TIEHIx1_ASAP7_75t_R \a_q[10]$_DFF_PN0__2  (.H(net1));
 DFFASRHQNx1_ASAP7_75t_R \a_q[11]$_DFF_PN0_  (.CLK(clk),
    .D(a[11]),
    .QN(_26_),
    .RESETN(reset_a),
    .SETN(net2));
 TIEHIx1_ASAP7_75t_R \a_q[11]$_DFF_PN0__3  (.H(net2));
 DFFASRHQNx1_ASAP7_75t_R \a_q[12]$_DFF_PN0_  (.CLK(clk),
    .D(a[12]),
    .QN(_25_),
    .RESETN(reset_a),
    .SETN(net3));
 TIEHIx1_ASAP7_75t_R \a_q[12]$_DFF_PN0__4  (.H(net3));
 DFFASRHQNx1_ASAP7_75t_R \a_q[13]$_DFF_PN0_  (.CLK(clk),
    .D(a[13]),
    .QN(_24_),
    .RESETN(reset_a),
    .SETN(net4));
 TIEHIx1_ASAP7_75t_R \a_q[13]$_DFF_PN0__5  (.H(net4));
 DFFASRHQNx1_ASAP7_75t_R \a_q[14]$_DFF_PN0_  (.CLK(clk),
    .D(a[14]),
    .QN(_23_),
    .RESETN(reset_a),
    .SETN(net5));
 TIEHIx1_ASAP7_75t_R \a_q[14]$_DFF_PN0__6  (.H(net5));
 DFFASRHQNx1_ASAP7_75t_R \a_q[15]$_DFF_PN0_  (.CLK(clk),
    .D(a[15]),
    .QN(_62_),
    .RESETN(reset_a),
    .SETN(net6));
 TIEHIx1_ASAP7_75t_R \a_q[15]$_DFF_PN0__7  (.H(net6));
 DFFASRHQNx1_ASAP7_75t_R \a_q[1]$_DFF_PN0_  (.CLK(clk),
    .D(a[1]),
    .QN(_36_),
    .RESETN(reset_a),
    .SETN(net7));
 TIEHIx1_ASAP7_75t_R \a_q[1]$_DFF_PN0__8  (.H(net7));
 DFFASRHQNx1_ASAP7_75t_R \a_q[2]$_DFF_PN0_  (.CLK(clk),
    .D(a[2]),
    .QN(_35_),
    .RESETN(reset_a),
    .SETN(net8));
 TIEHIx1_ASAP7_75t_R \a_q[2]$_DFF_PN0__9  (.H(net8));
 DFFASRHQNx1_ASAP7_75t_R \a_q[3]$_DFF_PN0_  (.CLK(clk),
    .D(a[3]),
    .QN(_34_),
    .RESETN(reset_a),
    .SETN(net9));
 TIEHIx1_ASAP7_75t_R \a_q[3]$_DFF_PN0__10  (.H(net9));
 DFFASRHQNx1_ASAP7_75t_R \a_q[4]$_DFF_PN0_  (.CLK(clk),
    .D(a[4]),
    .QN(_33_),
    .RESETN(reset_a),
    .SETN(net10));
 TIEHIx1_ASAP7_75t_R \a_q[4]$_DFF_PN0__11  (.H(net10));
 DFFASRHQNx1_ASAP7_75t_R \a_q[5]$_DFF_PN0_  (.CLK(clk),
    .D(a[5]),
    .QN(_32_),
    .RESETN(reset_a),
    .SETN(net11));
 TIEHIx1_ASAP7_75t_R \a_q[5]$_DFF_PN0__12  (.H(net11));
 DFFASRHQNx1_ASAP7_75t_R \a_q[6]$_DFF_PN0_  (.CLK(clk),
    .D(a[6]),
    .QN(_31_),
    .RESETN(reset_a),
    .SETN(net12));
 TIEHIx1_ASAP7_75t_R \a_q[6]$_DFF_PN0__13  (.H(net12));
 DFFASRHQNx1_ASAP7_75t_R \a_q[7]$_DFF_PN0_  (.CLK(clk),
    .D(a[7]),
    .QN(_30_),
    .RESETN(reset_a),
    .SETN(net13));
 TIEHIx1_ASAP7_75t_R \a_q[7]$_DFF_PN0__14  (.H(net13));
 DFFASRHQNx1_ASAP7_75t_R \a_q[8]$_DFF_PN0_  (.CLK(clk),
    .D(a[8]),
    .QN(_29_),
    .RESETN(reset_a),
    .SETN(net14));
 TIEHIx1_ASAP7_75t_R \a_q[8]$_DFF_PN0__15  (.H(net14));
 DFFASRHQNx1_ASAP7_75t_R \a_q[9]$_DFF_PN0_  (.CLK(clk),
    .D(a[9]),
    .QN(_28_),
    .RESETN(reset_a),
    .SETN(net15));
 TIEHIx1_ASAP7_75t_R \a_q[9]$_DFF_PN0__16  (.H(net15));
 DFFASRHQNx1_ASAP7_75t_R \b_q[0]$_DFF_PN0_  (.CLK(clk),
    .D(b[0]),
    .QN(_22_),
    .RESETN(reset_a),
    .SETN(net16));
 TIEHIx1_ASAP7_75t_R \b_q[0]$_DFF_PN0__17  (.H(net16));
 DFFASRHQNx1_ASAP7_75t_R \b_q[10]$_DFF_PN0_  (.CLK(clk),
    .D(b[10]),
    .QN(_42_),
    .RESETN(reset_b),
    .SETN(net17));
 TIEHIx1_ASAP7_75t_R \b_q[10]$_DFF_PN0__18  (.H(net17));
 DFFASRHQNx1_ASAP7_75t_R \b_q[11]$_DFF_PN0_  (.CLK(clk),
    .D(b[11]),
    .QN(_41_),
    .RESETN(reset_b),
    .SETN(net18));
 TIEHIx1_ASAP7_75t_R \b_q[11]$_DFF_PN0__19  (.H(net18));
 DFFASRHQNx1_ASAP7_75t_R \b_q[12]$_DFF_PN0_  (.CLK(clk),
    .D(b[12]),
    .QN(_40_),
    .RESETN(reset_b),
    .SETN(net19));
 TIEHIx1_ASAP7_75t_R \b_q[12]$_DFF_PN0__20  (.H(net19));
 DFFASRHQNx1_ASAP7_75t_R \b_q[13]$_DFF_PN0_  (.CLK(clk),
    .D(b[13]),
    .QN(_39_),
    .RESETN(reset_b),
    .SETN(net20));
 TIEHIx1_ASAP7_75t_R \b_q[13]$_DFF_PN0__21  (.H(net20));
 DFFASRHQNx1_ASAP7_75t_R \b_q[14]$_DFF_PN0_  (.CLK(clk),
    .D(b[14]),
    .QN(_38_),
    .RESETN(reset_b),
    .SETN(net21));
 TIEHIx1_ASAP7_75t_R \b_q[14]$_DFF_PN0__22  (.H(net21));
 DFFASRHQNx1_ASAP7_75t_R \b_q[15]$_DFF_PN0_  (.CLK(clk),
    .D(b[15]),
    .QN(_61_),
    .RESETN(reset_b),
    .SETN(net22));
 TIEHIx1_ASAP7_75t_R \b_q[15]$_DFF_PN0__23  (.H(net22));
 DFFASRHQNx1_ASAP7_75t_R \b_q[1]$_DFF_PN0_  (.CLK(clk),
    .D(b[1]),
    .QN(_21_),
    .RESETN(reset_a),
    .SETN(net23));
 TIEHIx1_ASAP7_75t_R \b_q[1]$_DFF_PN0__24  (.H(net23));
 DFFASRHQNx1_ASAP7_75t_R \b_q[2]$_DFF_PN0_  (.CLK(clk),
    .D(b[2]),
    .QN(_20_),
    .RESETN(reset_a),
    .SETN(net24));
 TIEHIx1_ASAP7_75t_R \b_q[2]$_DFF_PN0__25  (.H(net24));
 DFFASRHQNx1_ASAP7_75t_R \b_q[3]$_DFF_PN0_  (.CLK(clk),
    .D(b[3]),
    .QN(_19_),
    .RESETN(reset_a),
    .SETN(net25));
 TIEHIx1_ASAP7_75t_R \b_q[3]$_DFF_PN0__26  (.H(net25));
 DFFASRHQNx1_ASAP7_75t_R \b_q[4]$_DFF_PN0_  (.CLK(clk),
    .D(b[4]),
    .QN(_18_),
    .RESETN(reset_a),
    .SETN(net26));
 TIEHIx1_ASAP7_75t_R \b_q[4]$_DFF_PN0__27  (.H(net26));
 DFFASRHQNx1_ASAP7_75t_R \b_q[5]$_DFF_PN0_  (.CLK(clk),
    .D(b[5]),
    .QN(_16_),
    .RESETN(reset_a),
    .SETN(net27));
 TIEHIx1_ASAP7_75t_R \b_q[5]$_DFF_PN0__28  (.H(net27));
 DFFASRHQNx1_ASAP7_75t_R \b_q[6]$_DFF_PN0_  (.CLK(clk),
    .D(b[6]),
    .QN(_17_),
    .RESETN(reset_a),
    .SETN(net28));
 TIEHIx1_ASAP7_75t_R \b_q[6]$_DFF_PN0__29  (.H(net28));
 DFFASRHQNx1_ASAP7_75t_R \b_q[7]$_DFF_PN0_  (.CLK(clk),
    .D(b[7]),
    .QN(_63_),
    .RESETN(reset_a),
    .SETN(net29));
 TIEHIx1_ASAP7_75t_R \b_q[7]$_DFF_PN0__30  (.H(net29));
 DFFASRHQNx1_ASAP7_75t_R \b_q[8]$_DFF_PN0_  (.CLK(clk),
    .D(b[8]),
    .QN(_44_),
    .RESETN(reset_b),
    .SETN(net30));
 TIEHIx1_ASAP7_75t_R \b_q[8]$_DFF_PN0__31  (.H(net30));
 DFFASRHQNx1_ASAP7_75t_R \b_q[9]$_DFF_PN0_  (.CLK(clk),
    .D(b[9]),
    .QN(_43_),
    .RESETN(reset_b),
    .SETN(net31));
 TIEHIx1_ASAP7_75t_R \b_q[9]$_DFF_PN0__32  (.H(net31));
 DFFASRHQNx1_ASAP7_75t_R \reset_first$_DFF_PN0_  (.CLK(clk),
    .D(net32),
    .QN(_64_),
    .RESETN(rst_n),
    .SETN(net33));
 TIEHIx1_ASAP7_75t_R \reset_first$_DFF_PN0__33  (.H(net32));
 TIEHIx1_ASAP7_75t_R \reset_first$_DFF_PN0__34  (.H(net33));
 INVx3_ASAP7_75t_R \u_reset_a/_2_  (.A(\u_reset_a/_0_ ),
    .Y(reset_a));
 DFFASRHQNx1_ASAP7_75t_R \u_reset_a/q$_DFF_PN0_  (.CLK(clk),
    .D(reset_first),
    .QN(\u_reset_a/_0_ ),
    .RESETN(rst_n),
    .SETN(net50));
 TIEHIx1_ASAP7_75t_R \u_reset_a/q$_DFF_PN0__51  (.H(net50));
 INVx3_ASAP7_75t_R \u_reset_b/_2_  (.A(\u_reset_b/_0_ ),
    .Y(reset_b));
 DFFASRHQNx1_ASAP7_75t_R \u_reset_b/q$_DFF_PN0_  (.CLK(clk),
    .D(reset_first),
    .QN(\u_reset_b/_0_ ),
    .RESETN(rst_n),
    .SETN(net51));
 TIEHIx1_ASAP7_75t_R \u_reset_b/q$_DFF_PN0__52  (.H(net51));
 DFFASRHQNx1_ASAP7_75t_R \y[0]$_DFF_PN0_  (.CLK(clk),
    .D(_00_),
    .QN(_59_),
    .RESETN(reset_b),
    .SETN(net34));
 TIEHIx1_ASAP7_75t_R \y[0]$_DFF_PN0__35  (.H(net34));
 DFFASRHQNx1_ASAP7_75t_R \y[10]$_DFF_PN0_  (.CLK(clk),
    .D(_01_),
    .QN(_49_),
    .RESETN(reset_b),
    .SETN(net35));
 TIEHIx1_ASAP7_75t_R \y[10]$_DFF_PN0__36  (.H(net35));
 DFFASRHQNx1_ASAP7_75t_R \y[11]$_DFF_PN0_  (.CLK(clk),
    .D(_02_),
    .QN(_48_),
    .RESETN(reset_b),
    .SETN(net36));
 TIEHIx1_ASAP7_75t_R \y[11]$_DFF_PN0__37  (.H(net36));
 DFFASRHQNx1_ASAP7_75t_R \y[12]$_DFF_PN0_  (.CLK(clk),
    .D(_03_),
    .QN(_47_),
    .RESETN(reset_b),
    .SETN(net37));
 TIEHIx1_ASAP7_75t_R \y[12]$_DFF_PN0__38  (.H(net37));
 DFFASRHQNx1_ASAP7_75t_R \y[13]$_DFF_PN0_  (.CLK(clk),
    .D(_04_),
    .QN(_46_),
    .RESETN(reset_b),
    .SETN(net38));
 TIEHIx1_ASAP7_75t_R \y[13]$_DFF_PN0__39  (.H(net38));
 DFFASRHQNx1_ASAP7_75t_R \y[14]$_DFF_PN0_  (.CLK(clk),
    .D(_05_),
    .QN(_45_),
    .RESETN(reset_b),
    .SETN(net39));
 TIEHIx1_ASAP7_75t_R \y[14]$_DFF_PN0__40  (.H(net39));
 DFFASRHQNx1_ASAP7_75t_R \y[15]$_DFF_PN0_  (.CLK(clk),
    .D(_06_),
    .QN(_60_),
    .RESETN(reset_b),
    .SETN(net40));
 TIEHIx1_ASAP7_75t_R \y[15]$_DFF_PN0__41  (.H(net40));
 DFFASRHQNx1_ASAP7_75t_R \y[1]$_DFF_PN0_  (.CLK(clk),
    .D(_07_),
    .QN(_58_),
    .RESETN(reset_b),
    .SETN(net41));
 TIEHIx1_ASAP7_75t_R \y[1]$_DFF_PN0__42  (.H(net41));
 DFFASRHQNx1_ASAP7_75t_R \y[2]$_DFF_PN0_  (.CLK(clk),
    .D(_08_),
    .QN(_57_),
    .RESETN(reset_b),
    .SETN(net42));
 TIEHIx1_ASAP7_75t_R \y[2]$_DFF_PN0__43  (.H(net42));
 DFFASRHQNx1_ASAP7_75t_R \y[3]$_DFF_PN0_  (.CLK(clk),
    .D(_09_),
    .QN(_56_),
    .RESETN(reset_b),
    .SETN(net43));
 TIEHIx1_ASAP7_75t_R \y[3]$_DFF_PN0__44  (.H(net43));
 DFFASRHQNx1_ASAP7_75t_R \y[4]$_DFF_PN0_  (.CLK(clk),
    .D(_10_),
    .QN(_55_),
    .RESETN(reset_b),
    .SETN(net44));
 TIEHIx1_ASAP7_75t_R \y[4]$_DFF_PN0__45  (.H(net44));
 DFFASRHQNx1_ASAP7_75t_R \y[5]$_DFF_PN0_  (.CLK(clk),
    .D(_11_),
    .QN(_54_),
    .RESETN(reset_b),
    .SETN(net45));
 TIEHIx1_ASAP7_75t_R \y[5]$_DFF_PN0__46  (.H(net45));
 DFFASRHQNx1_ASAP7_75t_R \y[6]$_DFF_PN0_  (.CLK(clk),
    .D(_12_),
    .QN(_53_),
    .RESETN(reset_b),
    .SETN(net46));
 TIEHIx1_ASAP7_75t_R \y[6]$_DFF_PN0__47  (.H(net46));
 DFFASRHQNx1_ASAP7_75t_R \y[7]$_DFF_PN0_  (.CLK(clk),
    .D(_13_),
    .QN(_52_),
    .RESETN(reset_b),
    .SETN(net47));
 TIEHIx1_ASAP7_75t_R \y[7]$_DFF_PN0__48  (.H(net47));
 DFFASRHQNx1_ASAP7_75t_R \y[8]$_DFF_PN0_  (.CLK(clk),
    .D(_14_),
    .QN(_51_),
    .RESETN(reset_b),
    .SETN(net48));
 TIEHIx1_ASAP7_75t_R \y[8]$_DFF_PN0__49  (.H(net48));
 DFFASRHQNx1_ASAP7_75t_R \y[9]$_DFF_PN0_  (.CLK(clk),
    .D(_15_),
    .QN(_50_),
    .RESETN(reset_b),
    .SETN(net49));
 TIEHIx1_ASAP7_75t_R \y[9]$_DFF_PN0__50  (.H(net49));
endmodule
