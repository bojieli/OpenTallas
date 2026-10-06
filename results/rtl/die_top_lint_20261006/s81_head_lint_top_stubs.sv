// die_top_lint: port-identical REGISTERED STUBS of every placeholder master (generated abstract ports and
// widths; directions from the DIRECTION MODEL in tools/die_top_lint.py; x = conflicting across instances
// -> inout).  Outputs come from flops on the stub clock (ck[0] when the abstract has a clock port).

module dsfd_bf (
    input wire [53:0] cfg,
    input wire [19:0] ka,
    input wire [19:0] kb,
    output wire [1063:0] nv,
    output wire [62:0] r0,
    output wire [62:0] r1,
    input wire [265:0] xai,
    output wire [265:0] xao,
    input wire [265:0] xbi,
    output wire [265:0] xbo
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^cfg, ^ka, ^kb, ^xai, ^xbi};
    reg [1063:0] r_nv_0; always @(posedge lint_clk) r_nv_0 <= {1064{lint_in}}; assign nv[1063:0] = r_nv_0;
    reg [62:0] r_r0_0; always @(posedge lint_clk) r_r0_0 <= {63{lint_in}}; assign r0[62:0] = r_r0_0;
    reg [62:0] r_r1_0; always @(posedge lint_clk) r_r1_0 <= {63{lint_in}}; assign r1[62:0] = r_r1_0;
    reg [265:0] r_xao_0; always @(posedge lint_clk) r_xao_0 <= {266{lint_in}}; assign xao[265:0] = r_xao_0;
    reg [265:0] r_xbo_0; always @(posedge lint_clk) r_xbo_0 <= {266{lint_in}}; assign xbo[265:0] = r_xbo_0;
endmodule

module dsfd_bk_collector (
    input wire [511:0] cNE,
    input wire [511:0] cNW,
    input wire [511:0] cSE,
    input wire [511:0] cSW,
    input wire [2:0] ck,
    output wire [511:0] vm
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^cNE, ^cNW, ^cSE, ^cSW, ^ck};
    reg [511:0] r_vm_0; always @(posedge lint_clk) r_vm_0 <= {512{lint_in}}; assign vm[511:0] = r_vm_0;
endmodule

module dsfd_bk_selector (
    input wire [2:0] ck,
    input wire [511:0] iNE,
    input wire [511:0] iNW,
    input wire [511:0] iSE,
    input wire [511:0] iSW,
    output wire [511:0] vm
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^iNE, ^iNW, ^iSE, ^iSW};
    reg [511:0] r_vm_0; always @(posedge lint_clk) r_vm_0 <= {512{lint_in}}; assign vm[511:0] = r_vm_0;
endmodule

module dsfd_ctrl (
    inout wire [22237:0] phy,
    output wire [8863:0] rd
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^phy};
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [39:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {40{lint_in}}; assign phy[663:624] = r_phy_624;
    reg [0:0] r_phy_666; always @(posedge lint_clk) r_phy_666 <= {1{lint_in}}; assign phy[666:666] = r_phy_666;
    reg [0:0] r_phy_938; always @(posedge lint_clk) r_phy_938 <= {1{lint_in}}; assign phy[938:938] = r_phy_938;
    reg [339:0] r_phy_940; always @(posedge lint_clk) r_phy_940 <= {340{lint_in}}; assign phy[1279:940] = r_phy_940;
    reg [0:0] r_phy_1282; always @(posedge lint_clk) r_phy_1282 <= {1{lint_in}}; assign phy[1282:1282] = r_phy_1282;
    reg [0:0] r_phy_1562; always @(posedge lint_clk) r_phy_1562 <= {1{lint_in}}; assign phy[1562:1562] = r_phy_1562;
    reg [0:0] r_phy_1834; always @(posedge lint_clk) r_phy_1834 <= {1{lint_in}}; assign phy[1834:1834] = r_phy_1834;
    reg [339:0] r_phy_1836; always @(posedge lint_clk) r_phy_1836 <= {340{lint_in}}; assign phy[2175:1836] = r_phy_1836;
    reg [0:0] r_phy_2178; always @(posedge lint_clk) r_phy_2178 <= {1{lint_in}}; assign phy[2178:2178] = r_phy_2178;
    reg [0:0] r_phy_2458; always @(posedge lint_clk) r_phy_2458 <= {1{lint_in}}; assign phy[2458:2458] = r_phy_2458;
    reg [0:0] r_phy_2730; always @(posedge lint_clk) r_phy_2730 <= {1{lint_in}}; assign phy[2730:2730] = r_phy_2730;
    reg [339:0] r_phy_2732; always @(posedge lint_clk) r_phy_2732 <= {340{lint_in}}; assign phy[3071:2732] = r_phy_2732;
    reg [0:0] r_phy_3074; always @(posedge lint_clk) r_phy_3074 <= {1{lint_in}}; assign phy[3074:3074] = r_phy_3074;
    reg [0:0] r_phy_3354; always @(posedge lint_clk) r_phy_3354 <= {1{lint_in}}; assign phy[3354:3354] = r_phy_3354;
    reg [0:0] r_phy_3626; always @(posedge lint_clk) r_phy_3626 <= {1{lint_in}}; assign phy[3626:3626] = r_phy_3626;
    reg [339:0] r_phy_3628; always @(posedge lint_clk) r_phy_3628 <= {340{lint_in}}; assign phy[3967:3628] = r_phy_3628;
    reg [0:0] r_phy_3970; always @(posedge lint_clk) r_phy_3970 <= {1{lint_in}}; assign phy[3970:3970] = r_phy_3970;
    reg [0:0] r_phy_4250; always @(posedge lint_clk) r_phy_4250 <= {1{lint_in}}; assign phy[4250:4250] = r_phy_4250;
    reg [0:0] r_phy_4522; always @(posedge lint_clk) r_phy_4522 <= {1{lint_in}}; assign phy[4522:4522] = r_phy_4522;
    reg [339:0] r_phy_4524; always @(posedge lint_clk) r_phy_4524 <= {340{lint_in}}; assign phy[4863:4524] = r_phy_4524;
    reg [0:0] r_phy_4866; always @(posedge lint_clk) r_phy_4866 <= {1{lint_in}}; assign phy[4866:4866] = r_phy_4866;
    reg [0:0] r_phy_5146; always @(posedge lint_clk) r_phy_5146 <= {1{lint_in}}; assign phy[5146:5146] = r_phy_5146;
    reg [0:0] r_phy_5418; always @(posedge lint_clk) r_phy_5418 <= {1{lint_in}}; assign phy[5418:5418] = r_phy_5418;
    reg [339:0] r_phy_5420; always @(posedge lint_clk) r_phy_5420 <= {340{lint_in}}; assign phy[5759:5420] = r_phy_5420;
    reg [0:0] r_phy_5762; always @(posedge lint_clk) r_phy_5762 <= {1{lint_in}}; assign phy[5762:5762] = r_phy_5762;
    reg [0:0] r_phy_6042; always @(posedge lint_clk) r_phy_6042 <= {1{lint_in}}; assign phy[6042:6042] = r_phy_6042;
    reg [0:0] r_phy_6314; always @(posedge lint_clk) r_phy_6314 <= {1{lint_in}}; assign phy[6314:6314] = r_phy_6314;
    reg [339:0] r_phy_6316; always @(posedge lint_clk) r_phy_6316 <= {340{lint_in}}; assign phy[6655:6316] = r_phy_6316;
    reg [0:0] r_phy_6658; always @(posedge lint_clk) r_phy_6658 <= {1{lint_in}}; assign phy[6658:6658] = r_phy_6658;
    reg [0:0] r_phy_6938; always @(posedge lint_clk) r_phy_6938 <= {1{lint_in}}; assign phy[6938:6938] = r_phy_6938;
    reg [0:0] r_phy_7210; always @(posedge lint_clk) r_phy_7210 <= {1{lint_in}}; assign phy[7210:7210] = r_phy_7210;
    reg [339:0] r_phy_7212; always @(posedge lint_clk) r_phy_7212 <= {340{lint_in}}; assign phy[7551:7212] = r_phy_7212;
    reg [0:0] r_phy_7554; always @(posedge lint_clk) r_phy_7554 <= {1{lint_in}}; assign phy[7554:7554] = r_phy_7554;
    reg [0:0] r_phy_7832; always @(posedge lint_clk) r_phy_7832 <= {1{lint_in}}; assign phy[7832:7832] = r_phy_7832;
    reg [339:0] r_phy_7834; always @(posedge lint_clk) r_phy_7834 <= {340{lint_in}}; assign phy[8173:7834] = r_phy_7834;
    reg [0:0] r_phy_8176; always @(posedge lint_clk) r_phy_8176 <= {1{lint_in}}; assign phy[8176:8176] = r_phy_8176;
    reg [0:0] r_phy_8454; always @(posedge lint_clk) r_phy_8454 <= {1{lint_in}}; assign phy[8454:8454] = r_phy_8454;
    reg [339:0] r_phy_8456; always @(posedge lint_clk) r_phy_8456 <= {340{lint_in}}; assign phy[8795:8456] = r_phy_8456;
    reg [0:0] r_phy_8798; always @(posedge lint_clk) r_phy_8798 <= {1{lint_in}}; assign phy[8798:8798] = r_phy_8798;
    reg [0:0] r_phy_9076; always @(posedge lint_clk) r_phy_9076 <= {1{lint_in}}; assign phy[9076:9076] = r_phy_9076;
    reg [339:0] r_phy_9078; always @(posedge lint_clk) r_phy_9078 <= {340{lint_in}}; assign phy[9417:9078] = r_phy_9078;
    reg [0:0] r_phy_9420; always @(posedge lint_clk) r_phy_9420 <= {1{lint_in}}; assign phy[9420:9420] = r_phy_9420;
    reg [0:0] r_phy_9698; always @(posedge lint_clk) r_phy_9698 <= {1{lint_in}}; assign phy[9698:9698] = r_phy_9698;
    reg [339:0] r_phy_9700; always @(posedge lint_clk) r_phy_9700 <= {340{lint_in}}; assign phy[10039:9700] = r_phy_9700;
    reg [0:0] r_phy_10042; always @(posedge lint_clk) r_phy_10042 <= {1{lint_in}}; assign phy[10042:10042] = r_phy_10042;
    reg [0:0] r_phy_10320; always @(posedge lint_clk) r_phy_10320 <= {1{lint_in}}; assign phy[10320:10320] = r_phy_10320;
    reg [339:0] r_phy_10322; always @(posedge lint_clk) r_phy_10322 <= {340{lint_in}}; assign phy[10661:10322] = r_phy_10322;
    reg [0:0] r_phy_10664; always @(posedge lint_clk) r_phy_10664 <= {1{lint_in}}; assign phy[10664:10664] = r_phy_10664;
    reg [0:0] r_phy_10942; always @(posedge lint_clk) r_phy_10942 <= {1{lint_in}}; assign phy[10942:10942] = r_phy_10942;
    reg [339:0] r_phy_10944; always @(posedge lint_clk) r_phy_10944 <= {340{lint_in}}; assign phy[11283:10944] = r_phy_10944;
    reg [0:0] r_phy_11286; always @(posedge lint_clk) r_phy_11286 <= {1{lint_in}}; assign phy[11286:11286] = r_phy_11286;
    reg [0:0] r_phy_11564; always @(posedge lint_clk) r_phy_11564 <= {1{lint_in}}; assign phy[11564:11564] = r_phy_11564;
    reg [339:0] r_phy_11566; always @(posedge lint_clk) r_phy_11566 <= {340{lint_in}}; assign phy[11905:11566] = r_phy_11566;
    reg [0:0] r_phy_11908; always @(posedge lint_clk) r_phy_11908 <= {1{lint_in}}; assign phy[11908:11908] = r_phy_11908;
    reg [0:0] r_phy_12186; always @(posedge lint_clk) r_phy_12186 <= {1{lint_in}}; assign phy[12186:12186] = r_phy_12186;
    reg [339:0] r_phy_12188; always @(posedge lint_clk) r_phy_12188 <= {340{lint_in}}; assign phy[12527:12188] = r_phy_12188;
    reg [0:0] r_phy_12530; always @(posedge lint_clk) r_phy_12530 <= {1{lint_in}}; assign phy[12530:12530] = r_phy_12530;
    reg [1:0] r_phy_12808; always @(posedge lint_clk) r_phy_12808 <= {2{lint_in}}; assign phy[12809:12808] = r_phy_12808;
    reg [0:0] r_phy_12908; always @(posedge lint_clk) r_phy_12908 <= {1{lint_in}}; assign phy[12908:12908] = r_phy_12908;
    reg [339:0] r_phy_12910; always @(posedge lint_clk) r_phy_12910 <= {340{lint_in}}; assign phy[13249:12910] = r_phy_12910;
    reg [0:0] r_phy_13252; always @(posedge lint_clk) r_phy_13252 <= {1{lint_in}}; assign phy[13252:13252] = r_phy_13252;
    reg [0:0] r_phy_13530; always @(posedge lint_clk) r_phy_13530 <= {1{lint_in}}; assign phy[13530:13530] = r_phy_13530;
    reg [339:0] r_phy_13532; always @(posedge lint_clk) r_phy_13532 <= {340{lint_in}}; assign phy[13871:13532] = r_phy_13532;
    reg [0:0] r_phy_13874; always @(posedge lint_clk) r_phy_13874 <= {1{lint_in}}; assign phy[13874:13874] = r_phy_13874;
    reg [0:0] r_phy_14152; always @(posedge lint_clk) r_phy_14152 <= {1{lint_in}}; assign phy[14152:14152] = r_phy_14152;
    reg [339:0] r_phy_14154; always @(posedge lint_clk) r_phy_14154 <= {340{lint_in}}; assign phy[14493:14154] = r_phy_14154;
    reg [0:0] r_phy_14496; always @(posedge lint_clk) r_phy_14496 <= {1{lint_in}}; assign phy[14496:14496] = r_phy_14496;
    reg [0:0] r_phy_14774; always @(posedge lint_clk) r_phy_14774 <= {1{lint_in}}; assign phy[14774:14774] = r_phy_14774;
    reg [339:0] r_phy_14776; always @(posedge lint_clk) r_phy_14776 <= {340{lint_in}}; assign phy[15115:14776] = r_phy_14776;
    reg [0:0] r_phy_15118; always @(posedge lint_clk) r_phy_15118 <= {1{lint_in}}; assign phy[15118:15118] = r_phy_15118;
    reg [0:0] r_phy_15396; always @(posedge lint_clk) r_phy_15396 <= {1{lint_in}}; assign phy[15396:15396] = r_phy_15396;
    reg [339:0] r_phy_15398; always @(posedge lint_clk) r_phy_15398 <= {340{lint_in}}; assign phy[15737:15398] = r_phy_15398;
    reg [0:0] r_phy_15740; always @(posedge lint_clk) r_phy_15740 <= {1{lint_in}}; assign phy[15740:15740] = r_phy_15740;
    reg [0:0] r_phy_16018; always @(posedge lint_clk) r_phy_16018 <= {1{lint_in}}; assign phy[16018:16018] = r_phy_16018;
    reg [339:0] r_phy_16020; always @(posedge lint_clk) r_phy_16020 <= {340{lint_in}}; assign phy[16359:16020] = r_phy_16020;
    reg [0:0] r_phy_16362; always @(posedge lint_clk) r_phy_16362 <= {1{lint_in}}; assign phy[16362:16362] = r_phy_16362;
    reg [0:0] r_phy_16640; always @(posedge lint_clk) r_phy_16640 <= {1{lint_in}}; assign phy[16640:16640] = r_phy_16640;
    reg [339:0] r_phy_16642; always @(posedge lint_clk) r_phy_16642 <= {340{lint_in}}; assign phy[16981:16642] = r_phy_16642;
    reg [0:0] r_phy_16984; always @(posedge lint_clk) r_phy_16984 <= {1{lint_in}}; assign phy[16984:16984] = r_phy_16984;
    reg [0:0] r_phy_17262; always @(posedge lint_clk) r_phy_17262 <= {1{lint_in}}; assign phy[17262:17262] = r_phy_17262;
    reg [339:0] r_phy_17264; always @(posedge lint_clk) r_phy_17264 <= {340{lint_in}}; assign phy[17603:17264] = r_phy_17264;
    reg [0:0] r_phy_17606; always @(posedge lint_clk) r_phy_17606 <= {1{lint_in}}; assign phy[17606:17606] = r_phy_17606;
    reg [0:0] r_phy_17884; always @(posedge lint_clk) r_phy_17884 <= {1{lint_in}}; assign phy[17884:17884] = r_phy_17884;
    reg [339:0] r_phy_17886; always @(posedge lint_clk) r_phy_17886 <= {340{lint_in}}; assign phy[18225:17886] = r_phy_17886;
    reg [0:0] r_phy_18228; always @(posedge lint_clk) r_phy_18228 <= {1{lint_in}}; assign phy[18228:18228] = r_phy_18228;
    reg [0:0] r_phy_18506; always @(posedge lint_clk) r_phy_18506 <= {1{lint_in}}; assign phy[18506:18506] = r_phy_18506;
    reg [339:0] r_phy_18508; always @(posedge lint_clk) r_phy_18508 <= {340{lint_in}}; assign phy[18847:18508] = r_phy_18508;
    reg [0:0] r_phy_18850; always @(posedge lint_clk) r_phy_18850 <= {1{lint_in}}; assign phy[18850:18850] = r_phy_18850;
    reg [0:0] r_phy_19128; always @(posedge lint_clk) r_phy_19128 <= {1{lint_in}}; assign phy[19128:19128] = r_phy_19128;
    reg [339:0] r_phy_19130; always @(posedge lint_clk) r_phy_19130 <= {340{lint_in}}; assign phy[19469:19130] = r_phy_19130;
    reg [0:0] r_phy_19472; always @(posedge lint_clk) r_phy_19472 <= {1{lint_in}}; assign phy[19472:19472] = r_phy_19472;
    reg [0:0] r_phy_19750; always @(posedge lint_clk) r_phy_19750 <= {1{lint_in}}; assign phy[19750:19750] = r_phy_19750;
    reg [339:0] r_phy_19752; always @(posedge lint_clk) r_phy_19752 <= {340{lint_in}}; assign phy[20091:19752] = r_phy_19752;
    reg [0:0] r_phy_20094; always @(posedge lint_clk) r_phy_20094 <= {1{lint_in}}; assign phy[20094:20094] = r_phy_20094;
    reg [0:0] r_phy_20372; always @(posedge lint_clk) r_phy_20372 <= {1{lint_in}}; assign phy[20372:20372] = r_phy_20372;
    reg [339:0] r_phy_20374; always @(posedge lint_clk) r_phy_20374 <= {340{lint_in}}; assign phy[20713:20374] = r_phy_20374;
    reg [0:0] r_phy_20716; always @(posedge lint_clk) r_phy_20716 <= {1{lint_in}}; assign phy[20716:20716] = r_phy_20716;
    reg [0:0] r_phy_20994; always @(posedge lint_clk) r_phy_20994 <= {1{lint_in}}; assign phy[20994:20994] = r_phy_20994;
    reg [339:0] r_phy_20996; always @(posedge lint_clk) r_phy_20996 <= {340{lint_in}}; assign phy[21335:20996] = r_phy_20996;
    reg [0:0] r_phy_21338; always @(posedge lint_clk) r_phy_21338 <= {1{lint_in}}; assign phy[21338:21338] = r_phy_21338;
    reg [0:0] r_phy_21616; always @(posedge lint_clk) r_phy_21616 <= {1{lint_in}}; assign phy[21616:21616] = r_phy_21616;
    reg [339:0] r_phy_21618; always @(posedge lint_clk) r_phy_21618 <= {340{lint_in}}; assign phy[21957:21618] = r_phy_21618;
    reg [0:0] r_phy_21960; always @(posedge lint_clk) r_phy_21960 <= {1{lint_in}}; assign phy[21960:21960] = r_phy_21960;
    reg [8863:0] r_rd_0; always @(posedge lint_clk) r_rd_0 <= {8864{lint_in}}; assign rd[8863:0] = r_rd_0;
endmodule

module dsfd_fifo (
    input wire [2:0] ck,
    output wire [19:0] k0L,
    output wire [19:0] k0R,
    output wire [19:0] k1L,
    output wire [19:0] k1R,
    output wire [19:0] k2L,
    output wire [19:0] k2R,
    output wire [19:0] k3L,
    output wire [19:0] k3R,
    input wire [65:0] r0,
    input wire [65:0] r1,
    input wire [65:0] r2,
    input wire [65:0] r3,
    input wire [835:0] x,
    output wire [265:0] x0L,
    output wire [265:0] x0R,
    output wire [265:0] x1L,
    output wire [265:0] x1R,
    output wire [265:0] x2L,
    output wire [265:0] x2R,
    output wire [265:0] x3L,
    output wire [265:0] x3R
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^r0, ^r1, ^r2, ^r3, ^x};
    reg [19:0] r_k0L_0; always @(posedge lint_clk) r_k0L_0 <= {20{lint_in}}; assign k0L[19:0] = r_k0L_0;
    reg [19:0] r_k0R_0; always @(posedge lint_clk) r_k0R_0 <= {20{lint_in}}; assign k0R[19:0] = r_k0R_0;
    reg [19:0] r_k1L_0; always @(posedge lint_clk) r_k1L_0 <= {20{lint_in}}; assign k1L[19:0] = r_k1L_0;
    reg [19:0] r_k1R_0; always @(posedge lint_clk) r_k1R_0 <= {20{lint_in}}; assign k1R[19:0] = r_k1R_0;
    reg [19:0] r_k2L_0; always @(posedge lint_clk) r_k2L_0 <= {20{lint_in}}; assign k2L[19:0] = r_k2L_0;
    reg [19:0] r_k2R_0; always @(posedge lint_clk) r_k2R_0 <= {20{lint_in}}; assign k2R[19:0] = r_k2R_0;
    reg [19:0] r_k3L_0; always @(posedge lint_clk) r_k3L_0 <= {20{lint_in}}; assign k3L[19:0] = r_k3L_0;
    reg [19:0] r_k3R_0; always @(posedge lint_clk) r_k3R_0 <= {20{lint_in}}; assign k3R[19:0] = r_k3R_0;
    reg [265:0] r_x0L_0; always @(posedge lint_clk) r_x0L_0 <= {266{lint_in}}; assign x0L[265:0] = r_x0L_0;
    reg [265:0] r_x0R_0; always @(posedge lint_clk) r_x0R_0 <= {266{lint_in}}; assign x0R[265:0] = r_x0R_0;
    reg [265:0] r_x1L_0; always @(posedge lint_clk) r_x1L_0 <= {266{lint_in}}; assign x1L[265:0] = r_x1L_0;
    reg [265:0] r_x1R_0; always @(posedge lint_clk) r_x1R_0 <= {266{lint_in}}; assign x1R[265:0] = r_x1R_0;
    reg [265:0] r_x2L_0; always @(posedge lint_clk) r_x2L_0 <= {266{lint_in}}; assign x2L[265:0] = r_x2L_0;
    reg [265:0] r_x2R_0; always @(posedge lint_clk) r_x2R_0 <= {266{lint_in}}; assign x2R[265:0] = r_x2R_0;
    reg [265:0] r_x3L_0; always @(posedge lint_clk) r_x3L_0 <= {266{lint_in}}; assign x3L[265:0] = r_x3L_0;
    reg [265:0] r_x3R_0; always @(posedge lint_clk) r_x3R_0 <= {266{lint_in}}; assign x3R[265:0] = r_x3R_0;
endmodule

module dsfd_mfifo (
    input wire [1535:0] f,
    input wire [1535:0] h,
    output wire [857:0] hr,
    input wire [571:0] hx
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^f, ^h, ^hx};
    reg [857:0] r_hr_0; always @(posedge lint_clk) r_hr_0 <= {858{lint_in}}; assign hr[857:0] = r_hr_0;
endmodule

module dsfd_nvx (
    input wire [1063:0] nv
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^nv};
endmodule

module dsfd_sp_capture (
    input wire [575:0] f_gather,
    output wire [511:0] t_vm
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^f_gather};
    reg [511:0] r_t_vm_0; always @(posedge lint_clk) r_t_vm_0 <= {512{lint_in}}; assign t_vm[511:0] = r_t_vm_0;
endmodule

module dsfd_sp_collective (
    inout wire [1023:0] lE0,
    inout wire [1023:0] lE1,
    inout wire [1023:0] lE2,
    inout wire [1023:0] lE3,
    inout wire [1023:0] lW0,
    inout wire [1023:0] lW1,
    inout wire [1023:0] lW2,
    inout wire [1023:0] lW3,
    output wire [2:0] pll,
    output wire [511:0] t_vm
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^lE0, ^lE1, ^lE2, ^lE3, ^lW0, ^lW1, ^lW2, ^lW3};
    reg [511:0] r_lE0_0; always @(posedge lint_clk) r_lE0_0 <= {512{lint_in}}; assign lE0[511:0] = r_lE0_0;
    reg [511:0] r_lE1_0; always @(posedge lint_clk) r_lE1_0 <= {512{lint_in}}; assign lE1[511:0] = r_lE1_0;
    reg [511:0] r_lE2_0; always @(posedge lint_clk) r_lE2_0 <= {512{lint_in}}; assign lE2[511:0] = r_lE2_0;
    reg [511:0] r_lE3_0; always @(posedge lint_clk) r_lE3_0 <= {512{lint_in}}; assign lE3[511:0] = r_lE3_0;
    reg [511:0] r_lW0_0; always @(posedge lint_clk) r_lW0_0 <= {512{lint_in}}; assign lW0[511:0] = r_lW0_0;
    reg [511:0] r_lW1_0; always @(posedge lint_clk) r_lW1_0 <= {512{lint_in}}; assign lW1[511:0] = r_lW1_0;
    reg [511:0] r_lW2_0; always @(posedge lint_clk) r_lW2_0 <= {512{lint_in}}; assign lW2[511:0] = r_lW2_0;
    reg [511:0] r_lW3_0; always @(posedge lint_clk) r_lW3_0 <= {512{lint_in}}; assign lW3[511:0] = r_lW3_0;
    reg [2:0] r_pll_0; always @(posedge lint_clk) r_pll_0 <= {3{lint_in}}; assign pll[2:0] = r_pll_0;
    reg [511:0] r_t_vm_0; always @(posedge lint_clk) r_t_vm_0 <= {512{lint_in}}; assign t_vm[511:0] = r_t_vm_0;
endmodule

module dsfd_sp_gather (
    input wire [511:0] f_vm,
    input wire [527:0] rTE0,
    input wire [725:0] rTE1,
    input wire [857:0] rTE2,
    input wire [857:0] rTE3,
    input wire [725:0] rTE4,
    input wire [527:0] rTE5,
    input wire [527:0] rTW0,
    input wire [725:0] rTW1,
    input wire [857:0] rTW2,
    input wire [857:0] rTW3,
    input wire [725:0] rTW4,
    input wire [527:0] rTW5,
    output wire [575:0] t_capture
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^f_vm, ^rTE0, ^rTE1, ^rTE2, ^rTE3, ^rTE4, ^rTE5, ^rTW0, ^rTW1, ^rTW2, ^rTW3, ^rTW4, ^rTW5};
    reg [575:0] r_t_capture_0; always @(posedge lint_clk) r_t_capture_0 <= {576{lint_in}}; assign t_capture[575:0] = r_t_capture_0;
endmodule

module dsfd_sp_hc (
    input wire [2:0] ck,
    input wire [511:0] f_su_n,
    input wire [511:0] f_su_s,
    input wire [1023:0] f_vm
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_su_n, ^f_su_s, ^f_vm};
endmodule

module dsfd_sp_su_n (
    input wire [2:0] ck,
    input wire [1023:0] f_vm,
    output wire [511:0] t_hc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_vm};
    reg [511:0] r_t_hc_0; always @(posedge lint_clk) r_t_hc_0 <= {512{lint_in}}; assign t_hc[511:0] = r_t_hc_0;
endmodule

module dsfd_sp_su_s (
    input wire [2:0] ck,
    input wire [1023:0] f_vm,
    output wire [511:0] t_hc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_vm};
    reg [511:0] r_t_hc_0; always @(posedge lint_clk) r_t_hc_0 <= {512{lint_in}}; assign t_hc[511:0] = r_t_hc_0;
endmodule

module dsfd_sp_vm (
    input wire [511:0] col,
    input wire [511:0] f_capture,
    input wire [511:0] f_collective,
    inout wire [1535:0] sNE,
    inout wire [1535:0] sNW,
    inout wire [1535:0] sSE,
    inout wire [1535:0] sSW,
    input wire [511:0] sel,
    output wire [511:0] t_gather,
    output wire [1023:0] t_hc,
    output wire [1023:0] t_su_n,
    output wire [1023:0] t_su_s,
    output wire [571:0] xroot
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^col, ^f_capture, ^f_collective, ^sNE, ^sNW, ^sSE, ^sSW, ^sel};
    reg [511:0] r_sNE_0; always @(posedge lint_clk) r_sNE_0 <= {512{lint_in}}; assign sNE[511:0] = r_sNE_0;
    reg [511:0] r_sNW_0; always @(posedge lint_clk) r_sNW_0 <= {512{lint_in}}; assign sNW[511:0] = r_sNW_0;
    reg [511:0] r_sSE_0; always @(posedge lint_clk) r_sSE_0 <= {512{lint_in}}; assign sSE[511:0] = r_sSE_0;
    reg [511:0] r_sSW_0; always @(posedge lint_clk) r_sSW_0 <= {512{lint_in}}; assign sSW[511:0] = r_sSW_0;
    reg [511:0] r_t_gather_0; always @(posedge lint_clk) r_t_gather_0 <= {512{lint_in}}; assign t_gather[511:0] = r_t_gather_0;
    reg [1023:0] r_t_hc_0; always @(posedge lint_clk) r_t_hc_0 <= {1024{lint_in}}; assign t_hc[1023:0] = r_t_hc_0;
    reg [1023:0] r_t_su_n_0; always @(posedge lint_clk) r_t_su_n_0 <= {1024{lint_in}}; assign t_su_n[1023:0] = r_t_su_n_0;
    reg [1023:0] r_t_su_s_0; always @(posedge lint_clk) r_t_su_s_0 <= {1024{lint_in}}; assign t_su_s[1023:0] = r_t_su_s_0;
    reg [571:0] r_xroot_0; always @(posedge lint_clk) r_xroot_0 <= {572{lint_in}}; assign xroot[571:0] = r_xroot_0;
endmodule

module dsfd_stn_h (
    input wire [1535:0] e,
    input wire [835:0] t,
    input wire [1535:0] w
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^e, ^t, ^w};
endmodule

module dsfd_stn_l (
    inout wire [1023:0] e,
    inout wire [1023:0] w
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^e, ^w};
endmodule

module dsfd_stn_v (
    input wire [1535:0] a,
    input wire [1535:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
endmodule

module dsfd_svc (
    input wire [2:0] ck,
    output wire [511:0] co,
    inout wire [1535:0] hub,
    output wire [511:0] ix,
    input wire [8863:0] rd
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^hub, ^rd};
    reg [511:0] r_co_0; always @(posedge lint_clk) r_co_0 <= {512{lint_in}}; assign co[511:0] = r_co_0;
    reg [1023:0] r_hub_512; always @(posedge lint_clk) r_hub_512 <= {1024{lint_in}}; assign hub[1535:512] = r_hub_512;
    reg [511:0] r_ix_0; always @(posedge lint_clk) r_ix_0 <= {512{lint_in}}; assign ix[511:0] = r_ix_0;
endmodule
