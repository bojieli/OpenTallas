module dsfd_hrow_r15 (ck,
    rn,
    i,
    o);
 input ck;
 input rn;
 input [14:0] i;
 output [14:0] o;

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
 wire net1;
 wire net;
 wire ot_inhold_n00000;
 wire ot_ihdrv_n00000;
 wire ot_inhold_n00001;
 wire ot_ihdrv_n00001;
 wire ot_inhold_n00002;
 wire ot_ihdrv_n00002;
 wire ot_inhold_n00003;
 wire ot_ihdrv_n00003;
 wire ot_inhold_n00004;
 wire ot_ihdrv_n00004;
 wire ot_inhold_n00005;
 wire ot_ihdrv_n00005;
 wire ot_inhold_n00006;
 wire ot_ihdrv_n00006;
 wire ot_inhold_n00007;
 wire ot_ihdrv_n00007;
 wire ot_inhold_n00008;
 wire ot_ihdrv_n00008;
 wire ot_inhold_n00009;
 wire ot_ihdrv_n00009;
 wire ot_inhold_n00010;
 wire ot_ihdrv_n00010;
 wire ot_inhold_n00011;
 wire ot_ihdrv_n00011;
 wire ot_inhold_n00012;
 wire ot_ihdrv_n00012;
 wire ot_inhold_n00013;
 wire ot_ihdrv_n00013;
 wire ot_inhold_n00014;
 wire ot_ihdrv_n00014;
 wire ot_outhold_p00000;
 wire ot_outhold_n00000_0;
 wire ot_outhold_n00000_1;
 wire ot_outhold_p00001;
 wire ot_outhold_n00001_0;
 wire ot_outhold_n00001_1;
 wire ot_outhold_p00002;
 wire ot_outhold_n00002_0;
 wire ot_outhold_n00002_1;
 wire ot_outhold_p00003;
 wire ot_outhold_n00003_0;
 wire ot_outhold_n00003_1;
 wire ot_outhold_p00004;
 wire ot_outhold_n00004_0;
 wire ot_outhold_n00004_1;
 wire ot_outhold_p00005;
 wire ot_outhold_n00005_0;
 wire ot_outhold_n00005_1;
 wire ot_outhold_p00006;
 wire ot_outhold_n00006_0;
 wire ot_outhold_n00006_1;
 wire ot_outhold_p00007;
 wire ot_outhold_n00007_0;
 wire ot_outhold_n00007_1;
 wire ot_outhold_p00008;
 wire ot_outhold_n00008_0;
 wire ot_outhold_n00008_1;
 wire ot_outhold_p00009;
 wire ot_outhold_n00009_0;
 wire ot_outhold_n00009_1;
 wire ot_outhold_p00010;
 wire ot_outhold_n00010_0;
 wire ot_outhold_n00010_1;
 wire ot_outhold_p00011;
 wire ot_outhold_n00011_0;
 wire ot_outhold_n00011_1;
 wire ot_outhold_p00012;
 wire ot_outhold_n00012_0;
 wire ot_outhold_n00012_1;
 wire ot_outhold_p00013;
 wire ot_outhold_n00013_0;
 wire ot_outhold_n00013_1;
 wire ot_outhold_p00014;
 wire ot_outhold_n00014_0;
 wire ot_outhold_n00014_1;
 wire \o[0]2 ;
 wire \o[10]3 ;
 wire \o[11]4 ;
 wire \o[12]5 ;
 wire \o[13]6 ;
 wire \o[14]7 ;
 wire \o[1]8 ;
 wire \o[2]9 ;
 wire \o[3]10 ;
 wire \o[4]11 ;
 wire \o[5]12 ;
 wire \o[6]13 ;
 wire \o[7]14 ;
 wire \o[8]15 ;
 wire \o[9]16 ;
 wire clknet_0_ck;
 wire clknet_1_0__leaf_ck;
 wire clknet_1_1__leaf_ck;
 wire net17;
 wire net18;
 wire net19;
 wire net20;

 INVx3_ASAP7_75t_R _16_ (.A(_14_),
    .Y(o[0]));
 INVx3_ASAP7_75t_R _17_ (.A(_00_),
    .Y(o[12]));
 INVx3_ASAP7_75t_R _18_ (.A(_01_),
    .Y(o[13]));
 INVx3_ASAP7_75t_R _19_ (.A(_02_),
    .Y(o[11]));
 INVx3_ASAP7_75t_R _20_ (.A(_03_),
    .Y(o[10]));
 INVx3_ASAP7_75t_R _21_ (.A(_04_),
    .Y(o[9]));
 INVx3_ASAP7_75t_R _22_ (.A(_05_),
    .Y(o[8]));
 INVx3_ASAP7_75t_R _23_ (.A(_06_),
    .Y(o[7]));
 INVx3_ASAP7_75t_R _24_ (.A(_07_),
    .Y(o[6]));
 INVx3_ASAP7_75t_R _25_ (.A(_08_),
    .Y(o[5]));
 INVx3_ASAP7_75t_R _26_ (.A(_09_),
    .Y(o[4]));
 INVx3_ASAP7_75t_R _27_ (.A(_10_),
    .Y(o[3]));
 INVx3_ASAP7_75t_R _28_ (.A(_11_),
    .Y(o[2]));
 INVx3_ASAP7_75t_R _29_ (.A(_12_),
    .Y(o[1]));
 INVx3_ASAP7_75t_R _30_ (.A(_13_),
    .Y(o[14]));
 BUFx8_ASAP7_75t_R clkbuf_0_ck (.A(ck),
    .Y(clknet_0_ck));
 BUFx8_ASAP7_75t_R clkbuf_1_0__f_ck (.A(clknet_0_ck),
    .Y(clknet_1_0__leaf_ck));
 BUFx8_ASAP7_75t_R clkbuf_1_1__f_ck (.A(clknet_0_ck),
    .Y(clknet_1_1__leaf_ck));
 INVx2_ASAP7_75t_R clkload0 (.A(clknet_1_0__leaf_ck));
 BUFx2_ASAP7_75t_R hold18 (.A(net19),
    .Y(net17));
 BUFx2_ASAP7_75t_R hold19 (.A(net1),
    .Y(net18));
 BUFx2_ASAP7_75t_R hold20 (.A(rn),
    .Y(net19));
 BUFx2_ASAP7_75t_R hold21 (.A(net17),
    .Y(net20));
 BUFx2_ASAP7_75t_R input2 (.A(net20),
    .Y(net1));
 DFFASRHQNx1_ASAP7_75t_R \o[0]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_ck),
    .D(ot_ihdrv_n00000),
    .QN(_14_),
    .RESETN(net18),
    .SETN(net));
 TIEHIx1_ASAP7_75t_R \o[0]$_DFF_PN0__1  (.H(net));
 DFFHQNx1_ASAP7_75t_R \o[10]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00001),
    .QN(_03_));
 DFFHQNx1_ASAP7_75t_R \o[11]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00002),
    .QN(_02_));
 DFFHQNx1_ASAP7_75t_R \o[12]$_DFF_P_  (.CLK(clknet_1_0__leaf_ck),
    .D(ot_ihdrv_n00003),
    .QN(_00_));
 DFFHQNx1_ASAP7_75t_R \o[13]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00004),
    .QN(_01_));
 DFFHQNx1_ASAP7_75t_R \o[14]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00005),
    .QN(_13_));
 DFFHQNx1_ASAP7_75t_R \o[1]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00006),
    .QN(_12_));
 DFFHQNx1_ASAP7_75t_R \o[2]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00007),
    .QN(_11_));
 DFFHQNx1_ASAP7_75t_R \o[3]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00008),
    .QN(_10_));
 DFFHQNx1_ASAP7_75t_R \o[4]$_DFF_P_  (.CLK(clknet_1_0__leaf_ck),
    .D(ot_ihdrv_n00009),
    .QN(_09_));
 DFFHQNx1_ASAP7_75t_R \o[5]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00010),
    .QN(_08_));
 DFFHQNx1_ASAP7_75t_R \o[6]$_DFF_P_  (.CLK(clknet_1_0__leaf_ck),
    .D(ot_ihdrv_n00011),
    .QN(_07_));
 DFFHQNx1_ASAP7_75t_R \o[7]$_DFF_P_  (.CLK(clknet_1_1__leaf_ck),
    .D(ot_ihdrv_n00012),
    .QN(_06_));
 DFFHQNx1_ASAP7_75t_R \o[8]$_DFF_P_  (.CLK(clknet_1_0__leaf_ck),
    .D(ot_ihdrv_n00013),
    .QN(_05_));
 DFFHQNx1_ASAP7_75t_R \o[9]$_DFF_P_  (.CLK(clknet_1_0__leaf_ck),
    .D(ot_ihdrv_n00014),
    .QN(_04_));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00000 (.A(ot_inhold_n00000),
    .Y(ot_ihdrv_n00000));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00001 (.A(ot_inhold_n00001),
    .Y(ot_ihdrv_n00001));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00002 (.A(ot_inhold_n00002),
    .Y(ot_ihdrv_n00002));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00003 (.A(ot_inhold_n00003),
    .Y(ot_ihdrv_n00003));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00004 (.A(ot_inhold_n00004),
    .Y(ot_ihdrv_n00004));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00005 (.A(ot_inhold_n00005),
    .Y(ot_ihdrv_n00005));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00006 (.A(ot_inhold_n00006),
    .Y(ot_ihdrv_n00006));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00007 (.A(ot_inhold_n00007),
    .Y(ot_ihdrv_n00007));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00008 (.A(ot_inhold_n00008),
    .Y(ot_ihdrv_n00008));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00009 (.A(ot_inhold_n00009),
    .Y(ot_ihdrv_n00009));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00010 (.A(ot_inhold_n00010),
    .Y(ot_ihdrv_n00010));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00011 (.A(ot_inhold_n00011),
    .Y(ot_ihdrv_n00011));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00012 (.A(ot_inhold_n00012),
    .Y(ot_ihdrv_n00012));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00013 (.A(ot_inhold_n00013),
    .Y(ot_ihdrv_n00013));
 BUFx4f_ASAP7_75t_R ot_ihdrv_00014 (.A(ot_inhold_n00014),
    .Y(ot_ihdrv_n00014));
 HB4xp67_ASAP7_75t_R ot_inhold_00000 (.A(i[0]),
    .Y(ot_inhold_n00000));
 HB4xp67_ASAP7_75t_R ot_inhold_00001 (.A(i[10]),
    .Y(ot_inhold_n00001));
 HB4xp67_ASAP7_75t_R ot_inhold_00002 (.A(i[11]),
    .Y(ot_inhold_n00002));
 HB4xp67_ASAP7_75t_R ot_inhold_00003 (.A(i[12]),
    .Y(ot_inhold_n00003));
 HB4xp67_ASAP7_75t_R ot_inhold_00004 (.A(i[13]),
    .Y(ot_inhold_n00004));
 HB4xp67_ASAP7_75t_R ot_inhold_00005 (.A(i[14]),
    .Y(ot_inhold_n00005));
 HB4xp67_ASAP7_75t_R ot_inhold_00006 (.A(i[1]),
    .Y(ot_inhold_n00006));
 HB4xp67_ASAP7_75t_R ot_inhold_00007 (.A(i[2]),
    .Y(ot_inhold_n00007));
 HB4xp67_ASAP7_75t_R ot_inhold_00008 (.A(i[3]),
    .Y(ot_inhold_n00008));
 HB4xp67_ASAP7_75t_R ot_inhold_00009 (.A(i[4]),
    .Y(ot_inhold_n00009));
 HB4xp67_ASAP7_75t_R ot_inhold_00010 (.A(i[5]),
    .Y(ot_inhold_n00010));
 HB4xp67_ASAP7_75t_R ot_inhold_00011 (.A(i[6]),
    .Y(ot_inhold_n00011));
 HB4xp67_ASAP7_75t_R ot_inhold_00012 (.A(i[7]),
    .Y(ot_inhold_n00012));
 HB4xp67_ASAP7_75t_R ot_inhold_00013 (.A(i[8]),
    .Y(ot_inhold_n00013));
 HB4xp67_ASAP7_75t_R ot_inhold_00014 (.A(i[9]),
    .Y(ot_inhold_n00014));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00000_0 (.A(o[0]),
    .Y(ot_outhold_n00000_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00000_2 (.A(ot_outhold_n00000_1),
    .Y(ot_outhold_p00000));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00001_0 (.A(o[10]),
    .Y(ot_outhold_n00001_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00001_2 (.A(ot_outhold_n00001_1),
    .Y(ot_outhold_p00001));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00002_0 (.A(o[11]),
    .Y(ot_outhold_n00002_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00002_2 (.A(ot_outhold_n00002_1),
    .Y(ot_outhold_p00002));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00003_0 (.A(o[12]),
    .Y(ot_outhold_n00003_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00003_2 (.A(ot_outhold_n00003_1),
    .Y(ot_outhold_p00003));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00004_0 (.A(o[13]),
    .Y(ot_outhold_n00004_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00004_2 (.A(ot_outhold_n00004_1),
    .Y(ot_outhold_p00004));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00005_0 (.A(o[14]),
    .Y(ot_outhold_n00005_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00005_2 (.A(ot_outhold_n00005_1),
    .Y(ot_outhold_p00005));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00006_0 (.A(o[1]),
    .Y(ot_outhold_n00006_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00006_2 (.A(ot_outhold_n00006_1),
    .Y(ot_outhold_p00006));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00007_0 (.A(o[2]),
    .Y(ot_outhold_n00007_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00007_2 (.A(ot_outhold_n00007_1),
    .Y(ot_outhold_p00007));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00008_0 (.A(o[3]),
    .Y(ot_outhold_n00008_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00008_2 (.A(ot_outhold_n00008_1),
    .Y(ot_outhold_p00008));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00009_0 (.A(o[4]),
    .Y(ot_outhold_n00009_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00009_2 (.A(ot_outhold_n00009_1),
    .Y(ot_outhold_p00009));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00010_0 (.A(o[5]),
    .Y(ot_outhold_n00010_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00010_2 (.A(ot_outhold_n00010_1),
    .Y(ot_outhold_p00010));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00011_0 (.A(o[6]),
    .Y(ot_outhold_n00011_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00011_2 (.A(ot_outhold_n00011_1),
    .Y(ot_outhold_p00011));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00012_0 (.A(o[7]),
    .Y(ot_outhold_n00012_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00012_2 (.A(ot_outhold_n00012_1),
    .Y(ot_outhold_p00012));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00013_0 (.A(o[8]),
    .Y(ot_outhold_n00013_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00013_2 (.A(ot_outhold_n00013_1),
    .Y(ot_outhold_p00013));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00014_0 (.A(o[9]),
    .Y(ot_outhold_n00014_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00014_2 (.A(ot_outhold_n00014_1),
    .Y(ot_outhold_p00014));
 HB4xp67_ASAP7_75t_R ot_outhold_00000_1 (.A(ot_outhold_n00000_0),
    .Y(ot_outhold_n00000_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00001_1 (.A(ot_outhold_n00001_0),
    .Y(ot_outhold_n00001_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00002_1 (.A(ot_outhold_n00002_0),
    .Y(ot_outhold_n00002_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00003_1 (.A(ot_outhold_n00003_0),
    .Y(ot_outhold_n00003_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00004_1 (.A(ot_outhold_n00004_0),
    .Y(ot_outhold_n00004_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00005_1 (.A(ot_outhold_n00005_0),
    .Y(ot_outhold_n00005_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00006_1 (.A(ot_outhold_n00006_0),
    .Y(ot_outhold_n00006_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00007_1 (.A(ot_outhold_n00007_0),
    .Y(ot_outhold_n00007_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00008_1 (.A(ot_outhold_n00008_0),
    .Y(ot_outhold_n00008_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00009_1 (.A(ot_outhold_n00009_0),
    .Y(ot_outhold_n00009_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00010_1 (.A(ot_outhold_n00010_0),
    .Y(ot_outhold_n00010_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00011_1 (.A(ot_outhold_n00011_0),
    .Y(ot_outhold_n00011_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00012_1 (.A(ot_outhold_n00012_0),
    .Y(ot_outhold_n00012_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00013_1 (.A(ot_outhold_n00013_0),
    .Y(ot_outhold_n00013_1));
 HB4xp67_ASAP7_75t_R ot_outhold_00014_1 (.A(ot_outhold_n00014_0),
    .Y(ot_outhold_n00014_1));
 BUFx2_ASAP7_75t_R output10 (.A(ot_outhold_p00007),
    .Y(\o[2]9 ));
 BUFx2_ASAP7_75t_R output11 (.A(ot_outhold_p00008),
    .Y(\o[3]10 ));
 BUFx2_ASAP7_75t_R output12 (.A(ot_outhold_p00009),
    .Y(\o[4]11 ));
 BUFx2_ASAP7_75t_R output13 (.A(ot_outhold_p00010),
    .Y(\o[5]12 ));
 BUFx2_ASAP7_75t_R output14 (.A(ot_outhold_p00011),
    .Y(\o[6]13 ));
 BUFx2_ASAP7_75t_R output15 (.A(ot_outhold_p00012),
    .Y(\o[7]14 ));
 BUFx2_ASAP7_75t_R output16 (.A(ot_outhold_p00013),
    .Y(\o[8]15 ));
 BUFx2_ASAP7_75t_R output17 (.A(ot_outhold_p00014),
    .Y(\o[9]16 ));
 BUFx2_ASAP7_75t_R output3 (.A(ot_outhold_p00000),
    .Y(\o[0]2 ));
 BUFx2_ASAP7_75t_R output4 (.A(ot_outhold_p00001),
    .Y(\o[10]3 ));
 BUFx2_ASAP7_75t_R output5 (.A(ot_outhold_p00002),
    .Y(\o[11]4 ));
 BUFx2_ASAP7_75t_R output6 (.A(ot_outhold_p00003),
    .Y(\o[12]5 ));
 BUFx2_ASAP7_75t_R output7 (.A(ot_outhold_p00004),
    .Y(\o[13]6 ));
 BUFx2_ASAP7_75t_R output8 (.A(ot_outhold_p00005),
    .Y(\o[14]7 ));
 BUFx2_ASAP7_75t_R output9 (.A(ot_outhold_p00006),
    .Y(\o[1]8 ));
 assign o[0] = \o[0]2 ;
 assign o[10] = \o[10]3 ;
 assign o[11] = \o[11]4 ;
 assign o[12] = \o[12]5 ;
 assign o[13] = \o[13]6 ;
 assign o[14] = \o[14]7 ;
 assign o[1] = \o[1]8 ;
 assign o[2] = \o[2]9 ;
 assign o[3] = \o[3]10 ;
 assign o[4] = \o[4]11 ;
 assign o[5] = \o[5]12 ;
 assign o[6] = \o[6]13 ;
 assign o[7] = \o[7]14 ;
 assign o[8] = \o[8]15 ;
 assign o[9] = \o[9]16 ;
endmodule
