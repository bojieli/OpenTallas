module selected_fullsix_cone(input wire clk,rst_n,input wire[1100:0]source_word,output wire[559:0]rt,output wire[3:0]return_landing_fault);
wire ck_cl3S=clk;wire[15:0]u_s_3S_ck_xc={16{clk}};wire[4415:0]xc;reg[1:0]mkq;
always @(posedge clk or negedge rst_n)if(!rst_n)mkq<=0;else mkq<={mkq[0],1'b1};
wire[1103:0]xw4={source_word[1100:565],source_word[0],mkq[1],source_word[564:0],mkq[1]};
generate for(genvar c=0;c<4;c++)begin:head ot_s81sl_rly #(.W(1104),.D(6))u_x(.clk(clk),.d(xw4),.q(xc[1104*c+:1104]));end endgenerate
wire[98:0]land_fault;
  wire [275:0] w_x_f_3L01_l0_src, w_x_f_3L01_l0_dst;
  wire [1:0] nx_f_3L01_l0_fck;
  wire [275:0] w_x_f_3L01_l1_src, w_x_f_3L01_l1_dst;
  wire [1:0] nx_f_3L01_l1_fck;
  wire [275:0] w_x_f_3L01_l2_src, w_x_f_3L01_l2_dst;
  wire [1:0] nx_f_3L01_l2_fck;
  wire [275:0] w_x_f_3L01_l3_src, w_x_f_3L01_l3_dst;
  wire [1:0] nx_f_3L01_l3_fck;
  wire [69:0] w_r_f_3L01_src, w_r_f_3L01_dst;
  wire [1:0] nr_f_3L01_fck;
  wire [275:0] w_x_f_3L02_l0_src, w_x_f_3L02_l0_dst;
  wire [275:0] w_x_f_3L02_l1_src, w_x_f_3L02_l1_dst;
  wire [275:0] w_x_f_3L02_l2_src, w_x_f_3L02_l2_dst;
  wire [275:0] w_x_f_3L02_l3_src, w_x_f_3L02_l3_dst;
  wire [69:0] w_r_f_3L02_src, w_r_f_3L02_dst;
  wire [275:0] w_x_f_3L03_l0_src, w_x_f_3L03_l0_dst;
  wire [1:0] nx_f_3L03_l0_fck;
  wire [275:0] w_x_f_3L03_l1_src, w_x_f_3L03_l1_dst;
  wire [2:0] nx_f_3L03_l1_fck;
  wire [275:0] w_x_f_3L03_l2_src, w_x_f_3L03_l2_dst;
  wire [2:0] nx_f_3L03_l2_fck;
  wire [275:0] w_x_f_3L03_l3_src, w_x_f_3L03_l3_dst;
  wire [2:0] nx_f_3L03_l3_fck;
  wire [69:0] w_r_f_3L03_src, w_r_f_3L03_dst;
  wire [2:0] nr_f_3L03_fck;
  wire [275:0] w_x_f_3R01_l0_src, w_x_f_3R01_l0_dst;
  wire [1:0] nx_f_3R01_l0_fck;
  wire [275:0] w_x_f_3R01_l1_src, w_x_f_3R01_l1_dst;
  wire [1:0] nx_f_3R01_l1_fck;
  wire [275:0] w_x_f_3R01_l2_src, w_x_f_3R01_l2_dst;
  wire [1:0] nx_f_3R01_l2_fck;
  wire [275:0] w_x_f_3R01_l3_src, w_x_f_3R01_l3_dst;
  wire [1:0] nx_f_3R01_l3_fck;
  wire [69:0] w_r_f_3R01_src, w_r_f_3R01_dst;
  wire [1:0] nr_f_3R01_fck;
  wire [275:0] w_x_f_3R02_l0_src, w_x_f_3R02_l0_dst;
  wire [275:0] w_x_f_3R02_l1_src, w_x_f_3R02_l1_dst;
  wire [275:0] w_x_f_3R02_l2_src, w_x_f_3R02_l2_dst;
  wire [275:0] w_x_f_3R02_l3_src, w_x_f_3R02_l3_dst;
  wire [69:0] w_r_f_3R02_src, w_r_f_3R02_dst;
  wire [275:0] w_x_f_3R03_l0_src, w_x_f_3R03_l0_dst;
  wire [2:0] nx_f_3R03_l0_fck;
  wire [275:0] w_x_f_3R03_l1_src, w_x_f_3R03_l1_dst;
  wire [2:0] nx_f_3R03_l1_fck;
  wire [275:0] w_x_f_3R03_l2_src, w_x_f_3R03_l2_dst;
  wire [2:0] nx_f_3R03_l2_fck;
  wire [275:0] w_x_f_3R03_l3_src, w_x_f_3R03_l3_dst;
  wire [2:0] nx_f_3R03_l3_fck;
  wire [69:0] w_r_f_3R03_src, w_r_f_3R03_dst;
  wire [2:0] nr_f_3R03_fck;
  wire [3:0] u_f_3L02_xok;
  wire [3:0] u_f_3R02_xok;
  wire [69:0] w_r_f_3L01_lnd;
  wire [69:0] w_r_f_3L03_lnd;
  wire [69:0] w_r_f_3R01_lnd;
  wire [69:0] w_r_f_3R03_lnd;
  wire [275:0] r_x_f_3L03_l1_0;
  wire [275:0] r_x_f_3L03_l2_0;
  wire [275:0] r_x_f_3L03_l3_0;
  wire [69:0] r_r_f_3L03_0;
  wire [275:0] r_x_f_3R03_l0_0;
  wire [275:0] r_x_f_3R03_l1_0;
  wire [275:0] r_x_f_3R03_l2_0;
  wire [275:0] r_x_f_3R03_l3_0;
  wire [69:0] r_r_f_3R03_0;
wire rs_31_10_2=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_31_19_2=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_12=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_12_3=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_25=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_25_2=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_26=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_26_1=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_26_2=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_26_3=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_33_30_3=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_34_13_2=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_35_12=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_35_25=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_35_26=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_36_12_3=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_36_25_3=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_36_26_3=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_36_30_2=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_38_10_1=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rs_38_19_1=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rsg_rs_31_10_2_cl3S_6=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rsg_rs_34_13_2_cl3S_15=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rsg_rs_34_13_2_cl3S_16=rst_n; // declared logical diagnosticreset only; native regional date NULL
wire rsg_rs_38_10_1_cl3S_0=rst_n; // declared logical diagnosticreset only; native regional date NULL
assign w_x_f_3L01_l0_src=xc[0+:276];
assign w_x_f_3L01_l1_src=xc[276+:276];
assign w_x_f_3L01_l2_src=xc[552+:276];
assign w_x_f_3L01_l3_src=xc[828+:276];
assign w_x_f_3R01_l0_src=xc[1104+:276];
assign w_x_f_3R01_l1_src=xc[1380+:276];
assign w_x_f_3R01_l2_src=xc[1656+:276];
assign w_x_f_3R01_l3_src=xc[1932+:276];
assign w_x_f_3L02_l0_src=xc[2208+:276];
assign w_x_f_3L02_l1_src=xc[2484+:276];
assign w_x_f_3L02_l2_src=xc[2760+:276];
assign w_x_f_3L02_l3_src=xc[3036+:276];
assign w_x_f_3R02_l0_src=xc[3312+:276];
assign w_x_f_3R02_l1_src=xc[3588+:276];
assign w_x_f_3R02_l2_src=xc[3864+:276];
assign w_x_f_3R02_l3_src=xc[4140+:276];
  col_h10_l4 #(.INSTANCE("u_f_3L01")) u_f_3L01 (.clk(ck_cl3S), .cr(ck_cl3S), .cr_s(ck_cl3S), .xk({nx_f_3L01_l3_fck[1], nx_f_3L01_l2_fck[1], nx_f_3L01_l1_fck[1], nx_f_3L01_l0_fck[1]}), .rst_n(rs_31_10_2), .lk(12'h492), .x({w_x_f_3L01_l3_dst[275:0], w_x_f_3L01_l2_dst[275:0], w_x_f_3L01_l1_dst[275:0], w_x_f_3L01_l0_dst[275:0]}), .ret({w_r_f_3L01_src[69:0]}));
  col_h9_MX_l4 #(.INSTANCE("u_f_3L02")) u_f_3L02 (.clk(ck_cl3S), .cr(ck_cl3S), .cr_s(ck_cl3S), .xk({u_s_3S_ck_xc[11], u_s_3S_ck_xc[10], u_s_3S_ck_xc[9], u_s_3S_ck_xc[8]}), .rst_n(rs_31_19_2), .lk(12'h249), .x({w_x_f_3L02_l3_src[275:0], w_x_f_3L02_l2_src[275:0], w_x_f_3L02_l1_src[275:0], w_x_f_3L02_l0_src[275:0]}), .ret({w_r_f_3L02_src[69:0]}), .xo({w_x_f_3L03_l3_src[275:0], w_x_f_3L03_l2_src[275:0], w_x_f_3L03_l1_src[275:0], w_x_f_3L03_l0_src[275:0]}), .xok(u_f_3L02_xok));
  col_h9_l4 #(.INSTANCE("u_f_3L03")) u_f_3L03 (.clk(ck_cl3S), .cr(ck_cl3S), .cr_s(ck_cl3S), .xk({nx_f_3L03_l3_fck[2], nx_f_3L03_l2_fck[2], nx_f_3L03_l1_fck[2], nx_f_3L03_l0_fck[1]}), .rst_n(rs_33_30_3), .lk(12'h492), .x({w_x_f_3L03_l3_dst[275:0], w_x_f_3L03_l2_dst[275:0], w_x_f_3L03_l1_dst[275:0], w_x_f_3L03_l0_dst[275:0]}), .ret({w_r_f_3L03_src[69:0]}));
  col_h10_l4 #(.INSTANCE("u_f_3R01")) u_f_3R01 (.clk(ck_cl3S), .cr(ck_cl3S), .cr_s(ck_cl3S), .xk({nx_f_3R01_l3_fck[1], nx_f_3R01_l2_fck[1], nx_f_3R01_l1_fck[1], nx_f_3R01_l0_fck[1]}), .rst_n(rs_38_10_1), .lk(12'h492), .x({w_x_f_3R01_l3_dst[275:0], w_x_f_3R01_l2_dst[275:0], w_x_f_3R01_l1_dst[275:0], w_x_f_3R01_l0_dst[275:0]}), .ret({w_r_f_3R01_src[69:0]}));
  col_h9_MX_l4 #(.INSTANCE("u_f_3R02")) u_f_3R02 (.clk(ck_cl3S), .cr(ck_cl3S), .cr_s(ck_cl3S), .xk({u_s_3S_ck_xc[15], u_s_3S_ck_xc[14], u_s_3S_ck_xc[13], u_s_3S_ck_xc[12]}), .rst_n(rs_38_19_1), .lk(12'h249), .x({w_x_f_3R02_l3_src[275:0], w_x_f_3R02_l2_src[275:0], w_x_f_3R02_l1_src[275:0], w_x_f_3R02_l0_src[275:0]}), .ret({w_r_f_3R02_src[69:0]}), .xo({w_x_f_3R03_l3_src[275:0], w_x_f_3R03_l2_src[275:0], w_x_f_3R03_l1_src[275:0], w_x_f_3R03_l0_src[275:0]}), .xok(u_f_3R02_xok));
  col_h9_l4 #(.INSTANCE("u_f_3R03")) u_f_3R03 (.clk(ck_cl3S), .cr(ck_cl3S), .cr_s(ck_cl3S), .xk({nx_f_3R03_l3_fck[2], nx_f_3R03_l2_fck[2], nx_f_3R03_l1_fck[2], nx_f_3R03_l0_fck[2]}), .rst_n(rs_36_30_2), .lk(12'h492), .x({w_x_f_3R03_l3_dst[275:0], w_x_f_3R03_l2_dst[275:0], w_x_f_3R03_l1_dst[275:0], w_x_f_3R03_l0_dst[275:0]}), .ret({w_r_f_3R03_src[69:0]}));
  dsfd_dvland_70 ld_r_f_3L01 (.ck_f(nr_f_3L01_fck[1]), .i(w_r_f_3L01_dst), .ck(ck_cl3S), .rs(rs_34_13_2), .k(3'd2), .o(w_r_f_3L01_lnd), .fault(land_fault[95]));
  dsfd_dvland_70 ld_r_f_3L03 (.ck_f(nr_f_3L03_fck[2]), .i(w_r_f_3L03_dst), .ck(ck_cl3S), .rs(rsg_rs_34_13_2_cl3S_15), .k(3'd2), .o(w_r_f_3L03_lnd), .fault(land_fault[96]));
  dsfd_dvland_70 ld_r_f_3R01 (.ck_f(nr_f_3R01_fck[1]), .i(w_r_f_3R01_dst), .ck(ck_cl3S), .rs(rs_34_13_2), .k(3'd2), .o(w_r_f_3R01_lnd), .fault(land_fault[97]));
  dsfd_dvland_70 ld_r_f_3R03 (.ck_f(nr_f_3R03_fck[2]), .i(w_r_f_3R03_dst), .ck(ck_cl3S), .rs(rsg_rs_34_13_2_cl3S_16), .k(3'd2), .o(w_r_f_3R03_lnd), .fault(land_fault[98]));
  dsfd_dvrlyh_276_NS st_x_f_3L01_l0_0 (.i(w_x_f_3L01_l0_src), .o(w_x_f_3L01_l0_dst), .ck(u_s_3S_ck_xc[0]), .ck_o(nx_f_3L01_l0_fck[1]), .rs(rs_33_12));
  dsfd_dvrlyh_276_NS st_x_f_3L01_l1_0 (.i(w_x_f_3L01_l1_src), .o(w_x_f_3L01_l1_dst), .ck(u_s_3S_ck_xc[1]), .ck_o(nx_f_3L01_l1_fck[1]), .rs(rs_33_12));
  dsfd_dvrlyh_276_NS st_x_f_3L01_l2_0 (.i(w_x_f_3L01_l2_src), .o(w_x_f_3L01_l2_dst), .ck(u_s_3S_ck_xc[2]), .ck_o(nx_f_3L01_l2_fck[1]), .rs(rs_33_12_3));
  dsfd_dvrlyh_276_NS st_x_f_3L01_l3_0 (.i(w_x_f_3L01_l3_src), .o(w_x_f_3L01_l3_dst), .ck(u_s_3S_ck_xc[3]), .ck_o(nx_f_3L01_l3_fck[1]), .rs(rs_33_12_3));
  ICGx4_ASAP7_75t_R fwd_r_f_3L01 (.CLK(ck_cl3S), .ENA(rsg_rs_31_10_2_cl3S_6), .SE(1'b0), .GCLK(nr_f_3L01_fck[0]));   // hop 0: clock gate (LANDING-CONTRACT L3) on the source region root
  dsfd_dvrlyh_70_SN st_r_f_3L01_0 (.i(w_r_f_3L01_src), .o(w_r_f_3L01_dst), .ck(nr_f_3L01_fck[0]), .ck_o(nr_f_3L01_fck[1]), .rs(rs_33_12));
  dsfd_dvrlyh_276_SN st_x_f_3L03_l0_0 (.i(w_x_f_3L03_l0_src), .o(w_x_f_3L03_l0_dst), .ck(u_f_3L02_xok[0]), .ck_o(nx_f_3L03_l0_fck[1]), .rs(rs_33_26_1));
  dsfd_dvrlyh_276_SN st_x_f_3L03_l1_0 (.i(w_x_f_3L03_l1_src), .o(r_x_f_3L03_l1_0), .ck(u_f_3L02_xok[1]), .ck_o(nx_f_3L03_l1_fck[1]), .rs(rs_33_25_2));
  dsfd_dvrlyh_276_SN st_x_f_3L03_l1_1 (.i(r_x_f_3L03_l1_0), .o(w_x_f_3L03_l1_dst), .ck(nx_f_3L03_l1_fck[1]), .ck_o(nx_f_3L03_l1_fck[2]), .rs(rs_33_26));
  dsfd_dvrlyh_276_SN st_x_f_3L03_l2_0 (.i(w_x_f_3L03_l2_src), .o(r_x_f_3L03_l2_0), .ck(u_f_3L02_xok[2]), .ck_o(nx_f_3L03_l2_fck[1]), .rs(rs_33_25_2));
  dsfd_dvrlyh_276_SN st_x_f_3L03_l2_1 (.i(r_x_f_3L03_l2_0), .o(w_x_f_3L03_l2_dst), .ck(nx_f_3L03_l2_fck[1]), .ck_o(nx_f_3L03_l2_fck[2]), .rs(rs_33_26_2));
  dsfd_dvrlyh_276_SN st_x_f_3L03_l3_0 (.i(w_x_f_3L03_l3_src), .o(r_x_f_3L03_l3_0), .ck(u_f_3L02_xok[3]), .ck_o(nx_f_3L03_l3_fck[1]), .rs(rs_33_26_3));
  dsfd_dvrlyh_276_SN st_x_f_3L03_l3_1 (.i(r_x_f_3L03_l3_0), .o(w_x_f_3L03_l3_dst), .ck(nx_f_3L03_l3_fck[1]), .ck_o(nx_f_3L03_l3_fck[2]), .rs(rs_33_26_2));
  ICGx4_ASAP7_75t_R fwd_r_f_3L03 (.CLK(ck_cl3S), .ENA(rs_33_30_3), .SE(1'b0), .GCLK(nr_f_3L03_fck[0]));   // hop 0: clock gate (LANDING-CONTRACT L3) on the source region root
  dsfd_dvrlyh_70_NS st_r_f_3L03_0 (.i(w_r_f_3L03_src), .o(r_r_f_3L03_0), .ck(nr_f_3L03_fck[0]), .ck_o(nr_f_3L03_fck[1]), .rs(rs_33_26));
  dsfd_dvrlyh_70_NS st_r_f_3L03_1 (.i(r_r_f_3L03_0), .o(w_r_f_3L03_dst), .ck(nr_f_3L03_fck[1]), .ck_o(nr_f_3L03_fck[2]), .rs(rs_33_25));
  dsfd_dvrlyh_276_NS st_x_f_3R01_l0_0 (.i(w_x_f_3R01_l0_src), .o(w_x_f_3R01_l0_dst), .ck(u_s_3S_ck_xc[4]), .ck_o(nx_f_3R01_l0_fck[1]), .rs(rs_35_12));
  dsfd_dvrlyh_276_NS st_x_f_3R01_l1_0 (.i(w_x_f_3R01_l1_src), .o(w_x_f_3R01_l1_dst), .ck(u_s_3S_ck_xc[5]), .ck_o(nx_f_3R01_l1_fck[1]), .rs(rs_35_12));
  dsfd_dvrlyh_276_NS st_x_f_3R01_l2_0 (.i(w_x_f_3R01_l2_src), .o(w_x_f_3R01_l2_dst), .ck(u_s_3S_ck_xc[6]), .ck_o(nx_f_3R01_l2_fck[1]), .rs(rs_35_12));
  dsfd_dvrlyh_276_NS st_x_f_3R01_l3_0 (.i(w_x_f_3R01_l3_src), .o(w_x_f_3R01_l3_dst), .ck(u_s_3S_ck_xc[7]), .ck_o(nx_f_3R01_l3_fck[1]), .rs(rs_35_12));
  ICGx4_ASAP7_75t_R fwd_r_f_3R01 (.CLK(ck_cl3S), .ENA(rsg_rs_38_10_1_cl3S_0), .SE(1'b0), .GCLK(nr_f_3R01_fck[0]));   // hop 0: clock gate (LANDING-CONTRACT L3) on the source region root
  dsfd_dvrlyh_70_SN st_r_f_3R01_0 (.i(w_r_f_3R01_src), .o(w_r_f_3R01_dst), .ck(nr_f_3R01_fck[0]), .ck_o(nr_f_3R01_fck[1]), .rs(rs_36_12_3));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l0_0 (.i(w_x_f_3R03_l0_src), .o(r_x_f_3R03_l0_0), .ck(u_f_3R02_xok[0]), .ck_o(nx_f_3R03_l0_fck[1]), .rs(rs_35_25));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l0_1 (.i(r_x_f_3R03_l0_0), .o(w_x_f_3R03_l0_dst), .ck(nx_f_3R03_l0_fck[1]), .ck_o(nx_f_3R03_l0_fck[2]), .rs(rs_35_26));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l1_0 (.i(w_x_f_3R03_l1_src), .o(r_x_f_3R03_l1_0), .ck(u_f_3R02_xok[1]), .ck_o(nx_f_3R03_l1_fck[1]), .rs(rs_35_25));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l1_1 (.i(r_x_f_3R03_l1_0), .o(w_x_f_3R03_l1_dst), .ck(nx_f_3R03_l1_fck[1]), .ck_o(nx_f_3R03_l1_fck[2]), .rs(rs_35_26));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l2_0 (.i(w_x_f_3R03_l2_src), .o(r_x_f_3R03_l2_0), .ck(u_f_3R02_xok[2]), .ck_o(nx_f_3R03_l2_fck[1]), .rs(rs_35_25));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l2_1 (.i(r_x_f_3R03_l2_0), .o(w_x_f_3R03_l2_dst), .ck(nx_f_3R03_l2_fck[1]), .ck_o(nx_f_3R03_l2_fck[2]), .rs(rs_35_26));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l3_0 (.i(w_x_f_3R03_l3_src), .o(r_x_f_3R03_l3_0), .ck(u_f_3R02_xok[3]), .ck_o(nx_f_3R03_l3_fck[1]), .rs(rs_35_26));
  dsfd_dvrlyh_276_SN st_x_f_3R03_l3_1 (.i(r_x_f_3R03_l3_0), .o(w_x_f_3R03_l3_dst), .ck(nx_f_3R03_l3_fck[1]), .ck_o(nx_f_3R03_l3_fck[2]), .rs(rs_35_26));
  ICGx4_ASAP7_75t_R fwd_r_f_3R03 (.CLK(ck_cl3S), .ENA(rs_36_30_2), .SE(1'b0), .GCLK(nr_f_3R03_fck[0]));   // hop 0: clock gate (LANDING-CONTRACT L3) on the source region root
  dsfd_dvrlyh_70_NS st_r_f_3R03_0 (.i(w_r_f_3R03_src), .o(r_r_f_3R03_0), .ck(nr_f_3R03_fck[0]), .ck_o(nr_f_3R03_fck[1]), .rs(rs_36_26_3));
  dsfd_dvrlyh_70_NS st_r_f_3R03_1 (.i(r_r_f_3R03_0), .o(w_r_f_3R03_dst), .ck(nr_f_3R03_fck[1]), .ck_o(nr_f_3R03_fck[2]), .rs(rs_36_25_3));
assign rt={140'd0,w_r_f_3R03_lnd,w_r_f_3R02_src,w_r_f_3R01_lnd,w_r_f_3L03_lnd,w_r_f_3L02_src,w_r_f_3L01_lnd};
assign return_landing_fault={land_fault[95],land_fault[96],land_fault[97],land_fault[98]};
endmodule
