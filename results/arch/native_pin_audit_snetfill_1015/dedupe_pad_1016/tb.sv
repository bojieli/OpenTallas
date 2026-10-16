`timescale 1ns/1ps
module tb;reg ck,rst_n;integer n;

reg [15:0] p0_di;
wire [15:0] p0_dq, ref_p0_dq;

reg [16:0] p1_di;
wire [16:0] p1_dq, ref_p1_dq;

reg [2047:0] p2_di;
wire [2047:0] p2_dq, ref_p2_dq;

reg [2163:0] p3_di;
wire [2163:0] p3_dq, ref_p3_dq;

reg [2:0] p4_di;
wire [2:0] p4_dq, ref_p4_dq;

reg [3055:0] p5_di;
wire [3055:0] p5_dq, ref_p5_dq;

reg [511:0] p6_di;
wire [511:0] p6_dq, ref_p6_dq;

reg [55:0] p7_di;
wire [55:0] p7_dq, ref_p7_dq;

reg [63:0] p8_di;
wire [63:0] p8_dq, ref_p8_dq;

reg [83:0] p9_di;
wire [83:0] p9_dq, ref_p9_dq;

reg [0:0] p10_di;
wire [0:0] p10_dq, ref_p10_dq;

reg [1023:0] p11_di;
wire [1023:0] p11_dq, ref_p11_dq;

reg [1026:0] p12_di;
wire [1026:0] p12_dq, ref_p12_dq;

reg [11:0] p13_di;
wire [11:0] p13_dq, ref_p13_dq;

reg [15:0] p14_di;
wire [15:0] p14_dq, ref_p14_dq;

reg [16:0] p15_di;
wire [16:0] p15_dq, ref_p15_dq;

reg [2047:0] p16_di;
wire [2047:0] p16_dq, ref_p16_dq;

reg [2:0] p17_di;
wire [2:0] p17_dq, ref_p17_dq;

reg [47:0] p18_di;
wire [47:0] p18_dq, ref_p18_dq;

reg [55:0] p19_di;
wire [55:0] p19_dq, ref_p19_dq;

reg [63:0] p20_di;
wire [63:0] p20_dq, ref_p20_dq;

reg [691:0] p21_di;
wire [691:0] p21_dq, ref_p21_dq;

reg [83:0] p22_di;
wire [83:0] p22_dq, ref_p22_dq;


reg [37:0] p23_i;
wire [37:0] p23_o, ref_p23_o;

reg [511:0] p24_di0;
wire [511:0] p24_do0, ref_p24_do0;
wire [0:0] p24_fo0, ref_p24_fo0;
wire [0:0] p24_fn0, ref_p24_fn0;

reg [513:0] p25_di0;
wire [513:0] p25_do0, ref_p25_do0;
wire [0:0] p25_fo0, ref_p25_fo0;
wire [0:0] p25_fn0, ref_p25_fn0;

reg [537:0] p26_di0;
wire [537:0] p26_do0, ref_p26_do0;
wire [0:0] p26_fo0, ref_p26_fo0;
wire [0:0] p26_fn0, ref_p26_fn0;

reg [511:0] p27_di0;
wire [511:0] p27_do0, ref_p27_do0;
wire [0:0] p27_fo0, ref_p27_fo0;
wire [0:0] p27_fn0, ref_p27_fn0;

reg [513:0] p28_di0;
wire [513:0] p28_do0, ref_p28_do0;
wire [0:0] p28_fo0, ref_p28_fo0;
wire [0:0] p28_fn0, ref_p28_fn0;

reg [537:0] p29_di0;
wire [537:0] p29_do0, ref_p29_do0;
wire [0:0] p29_fo0, ref_p29_fo0;
wire [0:0] p29_fn0, ref_p29_fn0;
dsfd_hstnh_16 ref0 (.ck(ck), .di(p0_di), .dq(ref_p0_dq));
dsfd_hstnh_17 ref1 (.ck(ck), .di(p1_di), .dq(ref_p1_dq));
dsfd_hstnh_2048 ref2 (.ck(ck), .di(p2_di), .dq(ref_p2_dq));
dsfd_hstnh_2164 ref3 (.ck(ck), .di(p3_di), .dq(ref_p3_dq));
dsfd_hstnh_3 ref4 (.ck(ck), .di(p4_di), .dq(ref_p4_dq));
dsfd_hstnh_3056 ref5 (.ck(ck), .di(p5_di), .dq(ref_p5_dq));
dsfd_hstnh_512 ref6 (.ck(ck), .di(p6_di), .dq(ref_p6_dq));
dsfd_hstnh_56 ref7 (.ck(ck), .di(p7_di), .dq(ref_p7_dq));
dsfd_hstnh_64 ref8 (.ck(ck), .di(p8_di), .dq(ref_p8_dq));
dsfd_hstnh_84 ref9 (.ck(ck), .di(p9_di), .dq(ref_p9_dq));
dsfd_hstnv_1 ref10 (.ck(ck), .di(p10_di), .dq(ref_p10_dq));
dsfd_hstnv_1024 ref11 (.ck(ck), .di(p11_di), .dq(ref_p11_dq));
dsfd_hstnv_1027 ref12 (.ck(ck), .di(p12_di), .dq(ref_p12_dq));
dsfd_hstnv_12 ref13 (.ck(ck), .di(p13_di), .dq(ref_p13_dq));
dsfd_hstnv_16 ref14 (.ck(ck), .di(p14_di), .dq(ref_p14_dq));
dsfd_hstnv_17 ref15 (.ck(ck), .di(p15_di), .dq(ref_p15_dq));
dsfd_hstnv_2048 ref16 (.ck(ck), .di(p16_di), .dq(ref_p16_dq));
dsfd_hstnv_3 ref17 (.ck(ck), .di(p17_di), .dq(ref_p17_dq));
dsfd_hstnv_48 ref18 (.ck(ck), .di(p18_di), .dq(ref_p18_dq));
dsfd_hstnv_56 ref19 (.ck(ck), .di(p19_di), .dq(ref_p19_dq));
dsfd_hstnv_64 ref20 (.ck(ck), .di(p20_di), .dq(ref_p20_dq));
dsfd_hstnv_692 ref21 (.ck(ck), .di(p21_di), .dq(ref_p21_dq));
dsfd_hstnv_84 ref22 (.ck(ck), .di(p22_di), .dq(ref_p22_dq));
dsfd_rly_38_WN ref23 (.ck(ck), .rs(rst_n), .i(p23_i), .o(ref_p23_o));
dsfd_stnh_512x1 ref24 (.fi0(ck), .di0(p24_di0), .do0(ref_p24_do0), .fo0(ref_p24_fo0), .fn0(ref_p24_fn0));
dsfd_stnh_514x1 ref25 (.fi0(ck), .di0(p25_di0), .do0(ref_p25_do0), .fo0(ref_p25_fo0), .fn0(ref_p25_fn0));
dsfd_stnh_538x1 ref26 (.fi0(ck), .di0(p26_di0), .do0(ref_p26_do0), .fo0(ref_p26_fo0), .fn0(ref_p26_fn0));
dsfd_stnv_512x1 ref27 (.fi0(ck), .di0(p27_di0), .do0(ref_p27_do0), .fo0(ref_p27_fo0), .fn0(ref_p27_fn0));
dsfd_stnv_514x1 ref28 (.fi0(ck), .di0(p28_di0), .do0(ref_p28_do0), .fo0(ref_p28_fo0), .fn0(ref_p28_fn0));
dsfd_stnv_538x1 ref29 (.fi0(ck), .di0(p29_di0), .do0(ref_p29_do0), .fo0(ref_p29_fo0), .fn0(ref_p29_fn0));
dedupe_die dut (.p0_ck(ck), .p0_di(p0_di), .p0_dq(p0_dq), .p1_ck(ck), .p1_di(p1_di), .p1_dq(p1_dq), .p2_ck(ck), .p2_di(p2_di), .p2_dq(p2_dq), .p3_ck(ck), .p3_di(p3_di), .p3_dq(p3_dq), .p4_ck(ck), .p4_di(p4_di), .p4_dq(p4_dq), .p5_ck(ck), .p5_di(p5_di), .p5_dq(p5_dq), .p6_ck(ck), .p6_di(p6_di), .p6_dq(p6_dq), .p7_ck(ck), .p7_di(p7_di), .p7_dq(p7_dq), .p8_ck(ck), .p8_di(p8_di), .p8_dq(p8_dq), .p9_ck(ck), .p9_di(p9_di), .p9_dq(p9_dq), .p10_ck(ck), .p10_di(p10_di), .p10_dq(p10_dq), .p11_ck(ck), .p11_di(p11_di), .p11_dq(p11_dq), .p12_ck(ck), .p12_di(p12_di), .p12_dq(p12_dq), .p13_ck(ck), .p13_di(p13_di), .p13_dq(p13_dq), .p14_ck(ck), .p14_di(p14_di), .p14_dq(p14_dq), .p15_ck(ck), .p15_di(p15_di), .p15_dq(p15_dq), .p16_ck(ck), .p16_di(p16_di), .p16_dq(p16_dq), .p17_ck(ck), .p17_di(p17_di), .p17_dq(p17_dq), .p18_ck(ck), .p18_di(p18_di), .p18_dq(p18_dq), .p19_ck(ck), .p19_di(p19_di), .p19_dq(p19_dq), .p20_ck(ck), .p20_di(p20_di), .p20_dq(p20_dq), .p21_ck(ck), .p21_di(p21_di), .p21_dq(p21_dq), .p22_ck(ck), .p22_di(p22_di), .p22_dq(p22_dq), .p23_ck(ck), .p23_rs(rst_n), .p23_i(p23_i), .p23_o(p23_o), .p24_fi0(ck), .p24_di0(p24_di0), .p24_do0(p24_do0), .p24_fo0(p24_fo0), .p24_fn0(p24_fn0), .p25_fi0(ck), .p25_di0(p25_di0), .p25_do0(p25_do0), .p25_fo0(p25_fo0), .p25_fn0(p25_fn0), .p26_fi0(ck), .p26_di0(p26_di0), .p26_do0(p26_do0), .p26_fo0(p26_fo0), .p26_fn0(p26_fn0), .p27_fi0(ck), .p27_di0(p27_di0), .p27_do0(p27_do0), .p27_fo0(p27_fo0), .p27_fn0(p27_fn0), .p28_fi0(ck), .p28_di0(p28_di0), .p28_do0(p28_do0), .p28_fo0(p28_fo0), .p28_fn0(p28_fn0), .p29_fi0(ck), .p29_di0(p29_di0), .p29_do0(p29_do0), .p29_fo0(p29_fo0), .p29_fn0(p29_fn0));
initial begin ck=0;rst_n=0; for(n=0;n<2000;n=n+1) begin
p0_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p1_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p2_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p3_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p4_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p5_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p6_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p7_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p8_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p9_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p10_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p11_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p12_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p13_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p14_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p15_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p16_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p17_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p18_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p19_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p20_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p21_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p22_di = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p23_i = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p24_di0 = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p25_di0 = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p26_di0 = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p27_di0 = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p28_di0 = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
p29_di0 = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
#2;ck=1;#1;
if(n>0) begin
if (p0_dq !== ref_p0_dq) $fatal(1,"logical output mismatch dsfd_hstnh_16.dq edge%0d",n);
if (p1_dq !== ref_p1_dq) $fatal(1,"logical output mismatch dsfd_hstnh_17.dq edge%0d",n);
if (p2_dq !== ref_p2_dq) $fatal(1,"logical output mismatch dsfd_hstnh_2048.dq edge%0d",n);
if (p3_dq !== ref_p3_dq) $fatal(1,"logical output mismatch dsfd_hstnh_2164.dq edge%0d",n);
if (p4_dq !== ref_p4_dq) $fatal(1,"logical output mismatch dsfd_hstnh_3.dq edge%0d",n);
if (p5_dq !== ref_p5_dq) $fatal(1,"logical output mismatch dsfd_hstnh_3056.dq edge%0d",n);
if (p6_dq !== ref_p6_dq) $fatal(1,"logical output mismatch dsfd_hstnh_512.dq edge%0d",n);
if (p7_dq !== ref_p7_dq) $fatal(1,"logical output mismatch dsfd_hstnh_56.dq edge%0d",n);
if (p8_dq !== ref_p8_dq) $fatal(1,"logical output mismatch dsfd_hstnh_64.dq edge%0d",n);
if (p9_dq !== ref_p9_dq) $fatal(1,"logical output mismatch dsfd_hstnh_84.dq edge%0d",n);
if (p10_dq !== ref_p10_dq) $fatal(1,"logical output mismatch dsfd_hstnv_1.dq edge%0d",n);
if (p11_dq !== ref_p11_dq) $fatal(1,"logical output mismatch dsfd_hstnv_1024.dq edge%0d",n);
if (p12_dq !== ref_p12_dq) $fatal(1,"logical output mismatch dsfd_hstnv_1027.dq edge%0d",n);
if (p13_dq !== ref_p13_dq) $fatal(1,"logical output mismatch dsfd_hstnv_12.dq edge%0d",n);
if (p14_dq !== ref_p14_dq) $fatal(1,"logical output mismatch dsfd_hstnv_16.dq edge%0d",n);
if (p15_dq !== ref_p15_dq) $fatal(1,"logical output mismatch dsfd_hstnv_17.dq edge%0d",n);
if (p16_dq !== ref_p16_dq) $fatal(1,"logical output mismatch dsfd_hstnv_2048.dq edge%0d",n);
if (p17_dq !== ref_p17_dq) $fatal(1,"logical output mismatch dsfd_hstnv_3.dq edge%0d",n);
if (p18_dq !== ref_p18_dq) $fatal(1,"logical output mismatch dsfd_hstnv_48.dq edge%0d",n);
if (p19_dq !== ref_p19_dq) $fatal(1,"logical output mismatch dsfd_hstnv_56.dq edge%0d",n);
if (p20_dq !== ref_p20_dq) $fatal(1,"logical output mismatch dsfd_hstnv_64.dq edge%0d",n);
if (p21_dq !== ref_p21_dq) $fatal(1,"logical output mismatch dsfd_hstnv_692.dq edge%0d",n);
if (p22_dq !== ref_p22_dq) $fatal(1,"logical output mismatch dsfd_hstnv_84.dq edge%0d",n);
if (p23_o !== ref_p23_o) $fatal(1,"logical output mismatch dsfd_rly_38_WN.o edge%0d",n);
if (p24_do0 !== ref_p24_do0) $fatal(1,"logical output mismatch dsfd_stnh_512x1.do0 edge%0d",n);
if (p24_fo0 !== ref_p24_fo0) $fatal(1,"logical output mismatch dsfd_stnh_512x1.fo0 edge%0d",n);
if (p24_fn0 !== ref_p24_fn0) $fatal(1,"logical output mismatch dsfd_stnh_512x1.fn0 edge%0d",n);
if (p25_do0 !== ref_p25_do0) $fatal(1,"logical output mismatch dsfd_stnh_514x1.do0 edge%0d",n);
if (p25_fo0 !== ref_p25_fo0) $fatal(1,"logical output mismatch dsfd_stnh_514x1.fo0 edge%0d",n);
if (p25_fn0 !== ref_p25_fn0) $fatal(1,"logical output mismatch dsfd_stnh_514x1.fn0 edge%0d",n);
if (p26_do0 !== ref_p26_do0) $fatal(1,"logical output mismatch dsfd_stnh_538x1.do0 edge%0d",n);
if (p26_fo0 !== ref_p26_fo0) $fatal(1,"logical output mismatch dsfd_stnh_538x1.fo0 edge%0d",n);
if (p26_fn0 !== ref_p26_fn0) $fatal(1,"logical output mismatch dsfd_stnh_538x1.fn0 edge%0d",n);
if (p27_do0 !== ref_p27_do0) $fatal(1,"logical output mismatch dsfd_stnv_512x1.do0 edge%0d",n);
if (p27_fo0 !== ref_p27_fo0) $fatal(1,"logical output mismatch dsfd_stnv_512x1.fo0 edge%0d",n);
if (p27_fn0 !== ref_p27_fn0) $fatal(1,"logical output mismatch dsfd_stnv_512x1.fn0 edge%0d",n);
if (p28_do0 !== ref_p28_do0) $fatal(1,"logical output mismatch dsfd_stnv_514x1.do0 edge%0d",n);
if (p28_fo0 !== ref_p28_fo0) $fatal(1,"logical output mismatch dsfd_stnv_514x1.fo0 edge%0d",n);
if (p28_fn0 !== ref_p28_fn0) $fatal(1,"logical output mismatch dsfd_stnv_514x1.fn0 edge%0d",n);
if (p29_do0 !== ref_p29_do0) $fatal(1,"logical output mismatch dsfd_stnv_538x1.do0 edge%0d",n);
if (p29_fo0 !== ref_p29_fo0) $fatal(1,"logical output mismatch dsfd_stnv_538x1.fo0 edge%0d",n);
if (p29_fn0 !== ref_p29_fn0) $fatal(1,"logical output mismatch dsfd_stnv_538x1.fn0 edge%0d",n);
end
#2;ck=0;#1;
if (p0_dq !== ref_p0_dq) $fatal(1,"logical output mismatch dsfd_hstnh_16.dq edge%0d",n);
if (p1_dq !== ref_p1_dq) $fatal(1,"logical output mismatch dsfd_hstnh_17.dq edge%0d",n);
if (p2_dq !== ref_p2_dq) $fatal(1,"logical output mismatch dsfd_hstnh_2048.dq edge%0d",n);
if (p3_dq !== ref_p3_dq) $fatal(1,"logical output mismatch dsfd_hstnh_2164.dq edge%0d",n);
if (p4_dq !== ref_p4_dq) $fatal(1,"logical output mismatch dsfd_hstnh_3.dq edge%0d",n);
if (p5_dq !== ref_p5_dq) $fatal(1,"logical output mismatch dsfd_hstnh_3056.dq edge%0d",n);
if (p6_dq !== ref_p6_dq) $fatal(1,"logical output mismatch dsfd_hstnh_512.dq edge%0d",n);
if (p7_dq !== ref_p7_dq) $fatal(1,"logical output mismatch dsfd_hstnh_56.dq edge%0d",n);
if (p8_dq !== ref_p8_dq) $fatal(1,"logical output mismatch dsfd_hstnh_64.dq edge%0d",n);
if (p9_dq !== ref_p9_dq) $fatal(1,"logical output mismatch dsfd_hstnh_84.dq edge%0d",n);
if (p10_dq !== ref_p10_dq) $fatal(1,"logical output mismatch dsfd_hstnv_1.dq edge%0d",n);
if (p11_dq !== ref_p11_dq) $fatal(1,"logical output mismatch dsfd_hstnv_1024.dq edge%0d",n);
if (p12_dq !== ref_p12_dq) $fatal(1,"logical output mismatch dsfd_hstnv_1027.dq edge%0d",n);
if (p13_dq !== ref_p13_dq) $fatal(1,"logical output mismatch dsfd_hstnv_12.dq edge%0d",n);
if (p14_dq !== ref_p14_dq) $fatal(1,"logical output mismatch dsfd_hstnv_16.dq edge%0d",n);
if (p15_dq !== ref_p15_dq) $fatal(1,"logical output mismatch dsfd_hstnv_17.dq edge%0d",n);
if (p16_dq !== ref_p16_dq) $fatal(1,"logical output mismatch dsfd_hstnv_2048.dq edge%0d",n);
if (p17_dq !== ref_p17_dq) $fatal(1,"logical output mismatch dsfd_hstnv_3.dq edge%0d",n);
if (p18_dq !== ref_p18_dq) $fatal(1,"logical output mismatch dsfd_hstnv_48.dq edge%0d",n);
if (p19_dq !== ref_p19_dq) $fatal(1,"logical output mismatch dsfd_hstnv_56.dq edge%0d",n);
if (p20_dq !== ref_p20_dq) $fatal(1,"logical output mismatch dsfd_hstnv_64.dq edge%0d",n);
if (p21_dq !== ref_p21_dq) $fatal(1,"logical output mismatch dsfd_hstnv_692.dq edge%0d",n);
if (p22_dq !== ref_p22_dq) $fatal(1,"logical output mismatch dsfd_hstnv_84.dq edge%0d",n);
if (p23_o !== ref_p23_o) $fatal(1,"logical output mismatch dsfd_rly_38_WN.o edge%0d",n);
if (p24_do0 !== ref_p24_do0) $fatal(1,"logical output mismatch dsfd_stnh_512x1.do0 edge%0d",n);
if (p24_fo0 !== ref_p24_fo0) $fatal(1,"logical output mismatch dsfd_stnh_512x1.fo0 edge%0d",n);
if (p24_fn0 !== ref_p24_fn0) $fatal(1,"logical output mismatch dsfd_stnh_512x1.fn0 edge%0d",n);
if (p25_do0 !== ref_p25_do0) $fatal(1,"logical output mismatch dsfd_stnh_514x1.do0 edge%0d",n);
if (p25_fo0 !== ref_p25_fo0) $fatal(1,"logical output mismatch dsfd_stnh_514x1.fo0 edge%0d",n);
if (p25_fn0 !== ref_p25_fn0) $fatal(1,"logical output mismatch dsfd_stnh_514x1.fn0 edge%0d",n);
if (p26_do0 !== ref_p26_do0) $fatal(1,"logical output mismatch dsfd_stnh_538x1.do0 edge%0d",n);
if (p26_fo0 !== ref_p26_fo0) $fatal(1,"logical output mismatch dsfd_stnh_538x1.fo0 edge%0d",n);
if (p26_fn0 !== ref_p26_fn0) $fatal(1,"logical output mismatch dsfd_stnh_538x1.fn0 edge%0d",n);
if (p27_do0 !== ref_p27_do0) $fatal(1,"logical output mismatch dsfd_stnv_512x1.do0 edge%0d",n);
if (p27_fo0 !== ref_p27_fo0) $fatal(1,"logical output mismatch dsfd_stnv_512x1.fo0 edge%0d",n);
if (p27_fn0 !== ref_p27_fn0) $fatal(1,"logical output mismatch dsfd_stnv_512x1.fn0 edge%0d",n);
if (p28_do0 !== ref_p28_do0) $fatal(1,"logical output mismatch dsfd_stnv_514x1.do0 edge%0d",n);
if (p28_fo0 !== ref_p28_fo0) $fatal(1,"logical output mismatch dsfd_stnv_514x1.fo0 edge%0d",n);
if (p28_fn0 !== ref_p28_fn0) $fatal(1,"logical output mismatch dsfd_stnv_514x1.fn0 edge%0d",n);
if (p29_do0 !== ref_p29_do0) $fatal(1,"logical output mismatch dsfd_stnv_538x1.do0 edge%0d",n);
if (p29_fo0 !== ref_p29_fo0) $fatal(1,"logical output mismatch dsfd_stnv_538x1.fo0 edge%0d",n);
if (p29_fn0 !== ref_p29_fn0) $fatal(1,"logical output mismatch dsfd_stnv_538x1.fn0 edge%0d",n);
if(n%53==0) begin rst_n=0;#1;end else begin rst_n=1;#1;end
end
$display("DEDUPE_PAD_EXACT PASS 30 mappings 2000 cycles both edges; generated original RTL vs padded standard");$finish;end

endmodule
