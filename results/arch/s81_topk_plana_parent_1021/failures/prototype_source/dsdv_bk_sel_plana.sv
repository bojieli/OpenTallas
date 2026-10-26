`timescale 1ns/1ps
// Opt-in Plan A: seven D2/K1 links each way add14edges. New control needs closure.
module dsdv_bk_sel_plana #(parameter integer MUT=0)(
 input wire[38:0]ck_region,input wire rst_n,input wire[7:0]tap_k,sink_k,input wire[2:0]ik,ek,
 input wire[7:0]uid,input wire eg_n,input wire[275:0]vi_s,vi_n,output wire[275:0]vo_n,vo_s,output wire fault);
 wire[38:0]reset_local;genvar ri;
 generate for(ri=0;ri<39;ri=ri+1)begin:g_reset
 ot_pl_pad #(.W(1),.N(4))u_reset(.ck(ck_region[ri]),.d(rst_n),.q(reset_local[ri]));end endgenerate
 wire[275:0]vi_s_face,vi_n_face,vi_s_core,vi_n_core,vo_s_core,vo_n_core;wire unused_s,unused_n;
 dsfd_dvrly_276_SN u_rs(.ck(ck_region[37]),.rs(reset_local[37]),.i(vi_s),.o(vi_s_face),.ck_o(unused_s));
 dsfd_dvrly_276_NS u_rn(.ck(ck_region[38]),.rs(reset_local[38]),.i(vi_n),.o(vi_n_face),.ck_o(unused_n));
 wire[2059:0]lane_core;wire[513:0]vd;
 dsdv_bk_g u_g(.clk(ck_region[0]),.rst_n(reset_local[0]),.tap_k(tap_k),.sink_k(sink_k),.ik(ik),.ek(ek),.uid(uid),.eg_n(eg_n),
 .vi_s(vi_s_core),.vi_n(vi_n_core),.vo_s(vo_s_core),.vo_n(vo_n_core),
 .ln0(lane_core[0+:515]),.ln1(lane_core[515+:515]),.ln2(lane_core[1030+:515]),.ln3(lane_core[1545+:515]),.vd(vd),.fault(fault));
 wire[263:0]tc;wire[3:0]tcr;wire[3459:0]fs;wire[1415:0]fo;
 dsdv_bksel_c_plana u_c(.ck(ck_region[0]),.rst(reset_local[0]),.f_s_s(fs[0+:1730]),.f_s_n(fs[1730+:1730]),
 .f_o_s(fo[0+:708]),.f_o_n(fo[708+:708]),.t_c_s(tc[0+:132]),.t_c_n(tc[132+:132]),.t_cr_s(tcr[1:0]),.t_cr_n(tcr[3:2]),.vd(vd));
 wire[514:0]lane_q0;wire[65:0]cmd_q0;wire cr_q0;wire[864:0]status_q0;wire[353:0]selected_q0;
 wire[581:0]q0_cmd_d[0:7];assign q0_cmd_d[0]={lane_core[0+:515],tc[0+:66],tcr[0]};assign {lane_q0,cmd_q0,cr_q0}=q0_cmd_d[7];
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 1)?0:1),.BYPASS((MUT==1)&&1)) q0_cmd_h0(.ck_w(ck_region[0]),.ck_r(ck_region[6]),.rs_w(reset_local[0]),.rs_r(reset_local[6]),.i(q0_cmd_d[0]),.o(q0_cmd_d[1]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_cmd_h1(.ck_w(ck_region[6]),.ck_r(ck_region[5]),.rs_w(reset_local[6]),.rs_r(reset_local[5]),.i(q0_cmd_d[1]),.o(q0_cmd_d[2]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_cmd_h2(.ck_w(ck_region[5]),.ck_r(ck_region[4]),.rs_w(reset_local[5]),.rs_r(reset_local[4]),.i(q0_cmd_d[2]),.o(q0_cmd_d[3]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_cmd_h3(.ck_w(ck_region[4]),.ck_r(ck_region[3]),.rs_w(reset_local[4]),.rs_r(reset_local[3]),.i(q0_cmd_d[3]),.o(q0_cmd_d[4]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_cmd_h4(.ck_w(ck_region[3]),.ck_r(ck_region[2]),.rs_w(reset_local[3]),.rs_r(reset_local[2]),.i(q0_cmd_d[4]),.o(q0_cmd_d[5]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_cmd_h5(.ck_w(ck_region[2]),.ck_r(ck_region[1]),.rs_w(reset_local[2]),.rs_r(reset_local[1]),.i(q0_cmd_d[5]),.o(q0_cmd_d[6]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_cmd_h6(.ck_w(ck_region[1]),.ck_r(ck_region[9]),.rs_w(reset_local[1]),.rs_r(reset_local[9]),.i(q0_cmd_d[6]),.o(q0_cmd_d[7]));
 wire[864:0]q0_status_d[0:7];assign q0_status_d[0]=status_q0;assign fs[0+:865]=q0_status_d[7];
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_status_h0(.ck_w(ck_region[9]),.ck_r(ck_region[1]),.rs_w(reset_local[9]),.rs_r(reset_local[1]),.i(q0_status_d[0]),.o(q0_status_d[1]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_status_h1(.ck_w(ck_region[1]),.ck_r(ck_region[2]),.rs_w(reset_local[1]),.rs_r(reset_local[2]),.i(q0_status_d[1]),.o(q0_status_d[2]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_status_h2(.ck_w(ck_region[2]),.ck_r(ck_region[3]),.rs_w(reset_local[2]),.rs_r(reset_local[3]),.i(q0_status_d[2]),.o(q0_status_d[3]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_status_h3(.ck_w(ck_region[3]),.ck_r(ck_region[4]),.rs_w(reset_local[3]),.rs_r(reset_local[4]),.i(q0_status_d[3]),.o(q0_status_d[4]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_status_h4(.ck_w(ck_region[4]),.ck_r(ck_region[5]),.rs_w(reset_local[4]),.rs_r(reset_local[5]),.i(q0_status_d[4]),.o(q0_status_d[5]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_status_h5(.ck_w(ck_region[5]),.ck_r(ck_region[6]),.rs_w(reset_local[5]),.rs_r(reset_local[6]),.i(q0_status_d[5]),.o(q0_status_d[6]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_status_h6(.ck_w(ck_region[6]),.ck_r(ck_region[0]),.rs_w(reset_local[6]),.rs_r(reset_local[0]),.i(q0_status_d[6]),.o(q0_status_d[7]));
 wire[353:0]q0_selected_d[0:7];assign q0_selected_d[0]=selected_q0;assign fo[0+:354]=q0_selected_d[7];
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_selected_h0(.ck_w(ck_region[9]),.ck_r(ck_region[7]),.rs_w(reset_local[9]),.rs_r(reset_local[7]),.i(q0_selected_d[0]),.o(q0_selected_d[1]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_selected_h1(.ck_w(ck_region[7]),.ck_r(ck_region[8]),.rs_w(reset_local[7]),.rs_r(reset_local[8]),.i(q0_selected_d[1]),.o(q0_selected_d[2]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_selected_h2(.ck_w(ck_region[8]),.ck_r(ck_region[3]),.rs_w(reset_local[8]),.rs_r(reset_local[3]),.i(q0_selected_d[2]),.o(q0_selected_d[3]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_selected_h3(.ck_w(ck_region[3]),.ck_r(ck_region[4]),.rs_w(reset_local[3]),.rs_r(reset_local[4]),.i(q0_selected_d[3]),.o(q0_selected_d[4]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_selected_h4(.ck_w(ck_region[4]),.ck_r(ck_region[5]),.rs_w(reset_local[4]),.rs_r(reset_local[5]),.i(q0_selected_d[4]),.o(q0_selected_d[5]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_selected_h5(.ck_w(ck_region[5]),.ck_r(ck_region[6]),.rs_w(reset_local[5]),.rs_r(reset_local[6]),.i(q0_selected_d[5]),.o(q0_selected_d[6]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q0_selected_h6(.ck_w(ck_region[6]),.ck_r(ck_region[0]),.rs_w(reset_local[6]),.rs_r(reset_local[0]),.i(q0_selected_d[6]),.o(q0_selected_d[7]));
 dsdv_bksel_q u_q0(.ck(ck_region[9]),.rst(reset_local[9]),.lane(lane_q0),.f_c(cmd_q0),.f_cr(cr_q0),.t_s(status_q0),.t_o(selected_q0));
 wire[514:0]lane_q1;wire[65:0]cmd_q1;wire cr_q1;wire[864:0]status_q1;wire[353:0]selected_q1;
 wire[581:0]q1_cmd_d[0:7];assign q1_cmd_d[0]={lane_core[515+:515],tc[66+:66],tcr[1]};assign {lane_q1,cmd_q1,cr_q1}=q1_cmd_d[7];
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_cmd_h0(.ck_w(ck_region[0]),.ck_r(ck_region[15]),.rs_w(reset_local[0]),.rs_r(reset_local[15]),.i(q1_cmd_d[0]),.o(q1_cmd_d[1]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_cmd_h1(.ck_w(ck_region[15]),.ck_r(ck_region[14]),.rs_w(reset_local[15]),.rs_r(reset_local[14]),.i(q1_cmd_d[1]),.o(q1_cmd_d[2]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_cmd_h2(.ck_w(ck_region[14]),.ck_r(ck_region[13]),.rs_w(reset_local[14]),.rs_r(reset_local[13]),.i(q1_cmd_d[2]),.o(q1_cmd_d[3]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_cmd_h3(.ck_w(ck_region[13]),.ck_r(ck_region[12]),.rs_w(reset_local[13]),.rs_r(reset_local[12]),.i(q1_cmd_d[3]),.o(q1_cmd_d[4]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_cmd_h4(.ck_w(ck_region[12]),.ck_r(ck_region[11]),.rs_w(reset_local[12]),.rs_r(reset_local[11]),.i(q1_cmd_d[4]),.o(q1_cmd_d[5]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_cmd_h5(.ck_w(ck_region[11]),.ck_r(ck_region[10]),.rs_w(reset_local[11]),.rs_r(reset_local[10]),.i(q1_cmd_d[5]),.o(q1_cmd_d[6]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_cmd_h6(.ck_w(ck_region[10]),.ck_r(ck_region[18]),.rs_w(reset_local[10]),.rs_r(reset_local[18]),.i(q1_cmd_d[6]),.o(q1_cmd_d[7]));
 wire[864:0]q1_status_d[0:7];assign q1_status_d[0]=status_q1;assign fs[865+:865]=q1_status_d[7];
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_status_h0(.ck_w(ck_region[18]),.ck_r(ck_region[10]),.rs_w(reset_local[18]),.rs_r(reset_local[10]),.i(q1_status_d[0]),.o(q1_status_d[1]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_status_h1(.ck_w(ck_region[10]),.ck_r(ck_region[11]),.rs_w(reset_local[10]),.rs_r(reset_local[11]),.i(q1_status_d[1]),.o(q1_status_d[2]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_status_h2(.ck_w(ck_region[11]),.ck_r(ck_region[12]),.rs_w(reset_local[11]),.rs_r(reset_local[12]),.i(q1_status_d[2]),.o(q1_status_d[3]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_status_h3(.ck_w(ck_region[12]),.ck_r(ck_region[13]),.rs_w(reset_local[12]),.rs_r(reset_local[13]),.i(q1_status_d[3]),.o(q1_status_d[4]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_status_h4(.ck_w(ck_region[13]),.ck_r(ck_region[14]),.rs_w(reset_local[13]),.rs_r(reset_local[14]),.i(q1_status_d[4]),.o(q1_status_d[5]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_status_h5(.ck_w(ck_region[14]),.ck_r(ck_region[15]),.rs_w(reset_local[14]),.rs_r(reset_local[15]),.i(q1_status_d[5]),.o(q1_status_d[6]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_status_h6(.ck_w(ck_region[15]),.ck_r(ck_region[0]),.rs_w(reset_local[15]),.rs_r(reset_local[0]),.i(q1_status_d[6]),.o(q1_status_d[7]));
 wire[353:0]q1_selected_d[0:7];assign q1_selected_d[0]=selected_q1;assign fo[354+:354]=q1_selected_d[7];
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_selected_h0(.ck_w(ck_region[18]),.ck_r(ck_region[16]),.rs_w(reset_local[18]),.rs_r(reset_local[16]),.i(q1_selected_d[0]),.o(q1_selected_d[1]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_selected_h1(.ck_w(ck_region[16]),.ck_r(ck_region[17]),.rs_w(reset_local[16]),.rs_r(reset_local[17]),.i(q1_selected_d[1]),.o(q1_selected_d[2]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_selected_h2(.ck_w(ck_region[17]),.ck_r(ck_region[12]),.rs_w(reset_local[17]),.rs_r(reset_local[12]),.i(q1_selected_d[2]),.o(q1_selected_d[3]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_selected_h3(.ck_w(ck_region[12]),.ck_r(ck_region[13]),.rs_w(reset_local[12]),.rs_r(reset_local[13]),.i(q1_selected_d[3]),.o(q1_selected_d[4]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_selected_h4(.ck_w(ck_region[13]),.ck_r(ck_region[14]),.rs_w(reset_local[13]),.rs_r(reset_local[14]),.i(q1_selected_d[4]),.o(q1_selected_d[5]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_selected_h5(.ck_w(ck_region[14]),.ck_r(ck_region[15]),.rs_w(reset_local[14]),.rs_r(reset_local[15]),.i(q1_selected_d[5]),.o(q1_selected_d[6]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q1_selected_h6(.ck_w(ck_region[15]),.ck_r(ck_region[0]),.rs_w(reset_local[15]),.rs_r(reset_local[0]),.i(q1_selected_d[6]),.o(q1_selected_d[7]));
 dsdv_bksel_q u_q1(.ck(ck_region[18]),.rst(reset_local[18]),.lane(lane_q1),.f_c(cmd_q1),.f_cr(cr_q1),.t_s(status_q1),.t_o(selected_q1));
 wire[514:0]lane_q2;wire[65:0]cmd_q2;wire cr_q2;wire[864:0]status_q2;wire[353:0]selected_q2;
 wire[581:0]q2_cmd_d[0:7];assign q2_cmd_d[0]={lane_core[1030+:515],tc[132+:66],tcr[2]};assign {lane_q2,cmd_q2,cr_q2}=q2_cmd_d[7];
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_cmd_h0(.ck_w(ck_region[0]),.ck_r(ck_region[24]),.rs_w(reset_local[0]),.rs_r(reset_local[24]),.i(q2_cmd_d[0]),.o(q2_cmd_d[1]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_cmd_h1(.ck_w(ck_region[24]),.ck_r(ck_region[23]),.rs_w(reset_local[24]),.rs_r(reset_local[23]),.i(q2_cmd_d[1]),.o(q2_cmd_d[2]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_cmd_h2(.ck_w(ck_region[23]),.ck_r(ck_region[22]),.rs_w(reset_local[23]),.rs_r(reset_local[22]),.i(q2_cmd_d[2]),.o(q2_cmd_d[3]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_cmd_h3(.ck_w(ck_region[22]),.ck_r(ck_region[21]),.rs_w(reset_local[22]),.rs_r(reset_local[21]),.i(q2_cmd_d[3]),.o(q2_cmd_d[4]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_cmd_h4(.ck_w(ck_region[21]),.ck_r(ck_region[20]),.rs_w(reset_local[21]),.rs_r(reset_local[20]),.i(q2_cmd_d[4]),.o(q2_cmd_d[5]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_cmd_h5(.ck_w(ck_region[20]),.ck_r(ck_region[19]),.rs_w(reset_local[20]),.rs_r(reset_local[19]),.i(q2_cmd_d[5]),.o(q2_cmd_d[6]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_cmd_h6(.ck_w(ck_region[19]),.ck_r(ck_region[27]),.rs_w(reset_local[19]),.rs_r(reset_local[27]),.i(q2_cmd_d[6]),.o(q2_cmd_d[7]));
 wire[864:0]q2_status_d[0:7];assign q2_status_d[0]=status_q2;assign fs[1730+:865]=q2_status_d[7];
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_status_h0(.ck_w(ck_region[27]),.ck_r(ck_region[19]),.rs_w(reset_local[27]),.rs_r(reset_local[19]),.i(q2_status_d[0]),.o(q2_status_d[1]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_status_h1(.ck_w(ck_region[19]),.ck_r(ck_region[20]),.rs_w(reset_local[19]),.rs_r(reset_local[20]),.i(q2_status_d[1]),.o(q2_status_d[2]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_status_h2(.ck_w(ck_region[20]),.ck_r(ck_region[21]),.rs_w(reset_local[20]),.rs_r(reset_local[21]),.i(q2_status_d[2]),.o(q2_status_d[3]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_status_h3(.ck_w(ck_region[21]),.ck_r(ck_region[22]),.rs_w(reset_local[21]),.rs_r(reset_local[22]),.i(q2_status_d[3]),.o(q2_status_d[4]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_status_h4(.ck_w(ck_region[22]),.ck_r(ck_region[23]),.rs_w(reset_local[22]),.rs_r(reset_local[23]),.i(q2_status_d[4]),.o(q2_status_d[5]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_status_h5(.ck_w(ck_region[23]),.ck_r(ck_region[24]),.rs_w(reset_local[23]),.rs_r(reset_local[24]),.i(q2_status_d[5]),.o(q2_status_d[6]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_status_h6(.ck_w(ck_region[24]),.ck_r(ck_region[0]),.rs_w(reset_local[24]),.rs_r(reset_local[0]),.i(q2_status_d[6]),.o(q2_status_d[7]));
 wire[353:0]q2_selected_d[0:7];assign q2_selected_d[0]=selected_q2;assign fo[708+:354]=q2_selected_d[7];
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_selected_h0(.ck_w(ck_region[27]),.ck_r(ck_region[25]),.rs_w(reset_local[27]),.rs_r(reset_local[25]),.i(q2_selected_d[0]),.o(q2_selected_d[1]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_selected_h1(.ck_w(ck_region[25]),.ck_r(ck_region[26]),.rs_w(reset_local[25]),.rs_r(reset_local[26]),.i(q2_selected_d[1]),.o(q2_selected_d[2]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_selected_h2(.ck_w(ck_region[26]),.ck_r(ck_region[21]),.rs_w(reset_local[26]),.rs_r(reset_local[21]),.i(q2_selected_d[2]),.o(q2_selected_d[3]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_selected_h3(.ck_w(ck_region[21]),.ck_r(ck_region[22]),.rs_w(reset_local[21]),.rs_r(reset_local[22]),.i(q2_selected_d[3]),.o(q2_selected_d[4]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_selected_h4(.ck_w(ck_region[22]),.ck_r(ck_region[23]),.rs_w(reset_local[22]),.rs_r(reset_local[23]),.i(q2_selected_d[4]),.o(q2_selected_d[5]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_selected_h5(.ck_w(ck_region[23]),.ck_r(ck_region[24]),.rs_w(reset_local[23]),.rs_r(reset_local[24]),.i(q2_selected_d[5]),.o(q2_selected_d[6]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q2_selected_h6(.ck_w(ck_region[24]),.ck_r(ck_region[0]),.rs_w(reset_local[24]),.rs_r(reset_local[0]),.i(q2_selected_d[6]),.o(q2_selected_d[7]));
 dsdv_bksel_q u_q2(.ck(ck_region[27]),.rst(reset_local[27]),.lane(lane_q2),.f_c(cmd_q2),.f_cr(cr_q2),.t_s(status_q2),.t_o(selected_q2));
 wire[514:0]lane_q3;wire[65:0]cmd_q3;wire cr_q3;wire[864:0]status_q3;wire[353:0]selected_q3;
 wire[581:0]q3_cmd_d[0:7];assign q3_cmd_d[0]={lane_core[1545+:515],tc[198+:66],tcr[3]};assign {lane_q3,cmd_q3,cr_q3}=q3_cmd_d[7];
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_cmd_h0(.ck_w(ck_region[0]),.ck_r(ck_region[33]),.rs_w(reset_local[0]),.rs_r(reset_local[33]),.i(q3_cmd_d[0]),.o(q3_cmd_d[1]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_cmd_h1(.ck_w(ck_region[33]),.ck_r(ck_region[32]),.rs_w(reset_local[33]),.rs_r(reset_local[32]),.i(q3_cmd_d[1]),.o(q3_cmd_d[2]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_cmd_h2(.ck_w(ck_region[32]),.ck_r(ck_region[31]),.rs_w(reset_local[32]),.rs_r(reset_local[31]),.i(q3_cmd_d[2]),.o(q3_cmd_d[3]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_cmd_h3(.ck_w(ck_region[31]),.ck_r(ck_region[30]),.rs_w(reset_local[31]),.rs_r(reset_local[30]),.i(q3_cmd_d[3]),.o(q3_cmd_d[4]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_cmd_h4(.ck_w(ck_region[30]),.ck_r(ck_region[29]),.rs_w(reset_local[30]),.rs_r(reset_local[29]),.i(q3_cmd_d[4]),.o(q3_cmd_d[5]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_cmd_h5(.ck_w(ck_region[29]),.ck_r(ck_region[28]),.rs_w(reset_local[29]),.rs_r(reset_local[28]),.i(q3_cmd_d[5]),.o(q3_cmd_d[6]));
 dsdv_bk_plana_land #(.W(582),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_cmd_h6(.ck_w(ck_region[28]),.ck_r(ck_region[36]),.rs_w(reset_local[28]),.rs_r(reset_local[36]),.i(q3_cmd_d[6]),.o(q3_cmd_d[7]));
 wire[864:0]q3_status_d[0:7];assign q3_status_d[0]=status_q3;assign fs[2595+:865]=q3_status_d[7];
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_status_h0(.ck_w(ck_region[36]),.ck_r(ck_region[28]),.rs_w(reset_local[36]),.rs_r(reset_local[28]),.i(q3_status_d[0]),.o(q3_status_d[1]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_status_h1(.ck_w(ck_region[28]),.ck_r(ck_region[29]),.rs_w(reset_local[28]),.rs_r(reset_local[29]),.i(q3_status_d[1]),.o(q3_status_d[2]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_status_h2(.ck_w(ck_region[29]),.ck_r(ck_region[30]),.rs_w(reset_local[29]),.rs_r(reset_local[30]),.i(q3_status_d[2]),.o(q3_status_d[3]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_status_h3(.ck_w(ck_region[30]),.ck_r(ck_region[31]),.rs_w(reset_local[30]),.rs_r(reset_local[31]),.i(q3_status_d[3]),.o(q3_status_d[4]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_status_h4(.ck_w(ck_region[31]),.ck_r(ck_region[32]),.rs_w(reset_local[31]),.rs_r(reset_local[32]),.i(q3_status_d[4]),.o(q3_status_d[5]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_status_h5(.ck_w(ck_region[32]),.ck_r(ck_region[33]),.rs_w(reset_local[32]),.rs_r(reset_local[33]),.i(q3_status_d[5]),.o(q3_status_d[6]));
 dsdv_bk_plana_land #(.W(865),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_status_h6(.ck_w(ck_region[33]),.ck_r(ck_region[0]),.rs_w(reset_local[33]),.rs_r(reset_local[0]),.i(q3_status_d[6]),.o(q3_status_d[7]));
 wire[353:0]q3_selected_d[0:7];assign q3_selected_d[0]=selected_q3;assign fo[1062+:354]=q3_selected_d[7];
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_selected_h0(.ck_w(ck_region[36]),.ck_r(ck_region[34]),.rs_w(reset_local[36]),.rs_r(reset_local[34]),.i(q3_selected_d[0]),.o(q3_selected_d[1]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_selected_h1(.ck_w(ck_region[34]),.ck_r(ck_region[35]),.rs_w(reset_local[34]),.rs_r(reset_local[35]),.i(q3_selected_d[1]),.o(q3_selected_d[2]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_selected_h2(.ck_w(ck_region[35]),.ck_r(ck_region[30]),.rs_w(reset_local[35]),.rs_r(reset_local[30]),.i(q3_selected_d[2]),.o(q3_selected_d[3]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_selected_h3(.ck_w(ck_region[30]),.ck_r(ck_region[31]),.rs_w(reset_local[30]),.rs_r(reset_local[31]),.i(q3_selected_d[3]),.o(q3_selected_d[4]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_selected_h4(.ck_w(ck_region[31]),.ck_r(ck_region[32]),.rs_w(reset_local[31]),.rs_r(reset_local[32]),.i(q3_selected_d[4]),.o(q3_selected_d[5]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_selected_h5(.ck_w(ck_region[32]),.ck_r(ck_region[33]),.rs_w(reset_local[32]),.rs_r(reset_local[33]),.i(q3_selected_d[5]),.o(q3_selected_d[6]));
 dsdv_bk_plana_land #(.W(354),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) q3_selected_h6(.ck_w(ck_region[33]),.ck_r(ck_region[0]),.rs_w(reset_local[33]),.rs_r(reset_local[0]),.i(q3_selected_d[6]),.o(q3_selected_d[7]));
 dsdv_bksel_q u_q3(.ck(ck_region[36]),.rst(reset_local[36]),.lane(lane_q3),.f_c(cmd_q3),.f_cr(cr_q3),.t_s(status_q3),.t_o(selected_q3));
 wire[275:0]rung_s_in_d[0:7];assign rung_s_in_d[0]=vi_s_face;assign vi_s_core=rung_s_in_d[7];
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_in_h0(.ck_w(ck_region[37]),.ck_r(ck_region[7]),.rs_w(reset_local[37]),.rs_r(reset_local[7]),.i(rung_s_in_d[0]),.o(rung_s_in_d[1]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_in_h1(.ck_w(ck_region[7]),.ck_r(ck_region[8]),.rs_w(reset_local[7]),.rs_r(reset_local[8]),.i(rung_s_in_d[1]),.o(rung_s_in_d[2]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_in_h2(.ck_w(ck_region[8]),.ck_r(ck_region[3]),.rs_w(reset_local[8]),.rs_r(reset_local[3]),.i(rung_s_in_d[2]),.o(rung_s_in_d[3]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_in_h3(.ck_w(ck_region[3]),.ck_r(ck_region[4]),.rs_w(reset_local[3]),.rs_r(reset_local[4]),.i(rung_s_in_d[3]),.o(rung_s_in_d[4]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_in_h4(.ck_w(ck_region[4]),.ck_r(ck_region[5]),.rs_w(reset_local[4]),.rs_r(reset_local[5]),.i(rung_s_in_d[4]),.o(rung_s_in_d[5]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_in_h5(.ck_w(ck_region[5]),.ck_r(ck_region[6]),.rs_w(reset_local[5]),.rs_r(reset_local[6]),.i(rung_s_in_d[5]),.o(rung_s_in_d[6]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_in_h6(.ck_w(ck_region[6]),.ck_r(ck_region[0]),.rs_w(reset_local[6]),.rs_r(reset_local[0]),.i(rung_s_in_d[6]),.o(rung_s_in_d[7]));
 wire[275:0]rung_s_out_d[0:7];assign rung_s_out_d[0]=vo_s_core;assign vo_s=rung_s_out_d[7];
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_out_h0(.ck_w(ck_region[0]),.ck_r(ck_region[6]),.rs_w(reset_local[0]),.rs_r(reset_local[6]),.i(rung_s_out_d[0]),.o(rung_s_out_d[1]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_out_h1(.ck_w(ck_region[6]),.ck_r(ck_region[5]),.rs_w(reset_local[6]),.rs_r(reset_local[5]),.i(rung_s_out_d[1]),.o(rung_s_out_d[2]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_out_h2(.ck_w(ck_region[5]),.ck_r(ck_region[4]),.rs_w(reset_local[5]),.rs_r(reset_local[4]),.i(rung_s_out_d[2]),.o(rung_s_out_d[3]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_out_h3(.ck_w(ck_region[4]),.ck_r(ck_region[3]),.rs_w(reset_local[4]),.rs_r(reset_local[3]),.i(rung_s_out_d[3]),.o(rung_s_out_d[4]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_out_h4(.ck_w(ck_region[3]),.ck_r(ck_region[8]),.rs_w(reset_local[3]),.rs_r(reset_local[8]),.i(rung_s_out_d[4]),.o(rung_s_out_d[5]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_out_h5(.ck_w(ck_region[8]),.ck_r(ck_region[7]),.rs_w(reset_local[8]),.rs_r(reset_local[7]),.i(rung_s_out_d[5]),.o(rung_s_out_d[6]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_s_out_h6(.ck_w(ck_region[7]),.ck_r(ck_region[37]),.rs_w(reset_local[7]),.rs_r(reset_local[37]),.i(rung_s_out_d[6]),.o(rung_s_out_d[7]));
 wire[275:0]rung_n_in_d[0:7];assign rung_n_in_d[0]=vi_n_face;assign vi_n_core=rung_n_in_d[7];
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_in_h0(.ck_w(ck_region[38]),.ck_r(ck_region[34]),.rs_w(reset_local[38]),.rs_r(reset_local[34]),.i(rung_n_in_d[0]),.o(rung_n_in_d[1]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_in_h1(.ck_w(ck_region[34]),.ck_r(ck_region[35]),.rs_w(reset_local[34]),.rs_r(reset_local[35]),.i(rung_n_in_d[1]),.o(rung_n_in_d[2]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_in_h2(.ck_w(ck_region[35]),.ck_r(ck_region[30]),.rs_w(reset_local[35]),.rs_r(reset_local[30]),.i(rung_n_in_d[2]),.o(rung_n_in_d[3]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_in_h3(.ck_w(ck_region[30]),.ck_r(ck_region[31]),.rs_w(reset_local[30]),.rs_r(reset_local[31]),.i(rung_n_in_d[3]),.o(rung_n_in_d[4]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_in_h4(.ck_w(ck_region[31]),.ck_r(ck_region[32]),.rs_w(reset_local[31]),.rs_r(reset_local[32]),.i(rung_n_in_d[4]),.o(rung_n_in_d[5]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_in_h5(.ck_w(ck_region[32]),.ck_r(ck_region[33]),.rs_w(reset_local[32]),.rs_r(reset_local[33]),.i(rung_n_in_d[5]),.o(rung_n_in_d[6]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_in_h6(.ck_w(ck_region[33]),.ck_r(ck_region[0]),.rs_w(reset_local[33]),.rs_r(reset_local[0]),.i(rung_n_in_d[6]),.o(rung_n_in_d[7]));
 wire[275:0]rung_n_out_d[0:7];assign rung_n_out_d[0]=vo_n_core;assign vo_n=rung_n_out_d[7];
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_out_h0(.ck_w(ck_region[0]),.ck_r(ck_region[33]),.rs_w(reset_local[0]),.rs_r(reset_local[33]),.i(rung_n_out_d[0]),.o(rung_n_out_d[1]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_out_h1(.ck_w(ck_region[33]),.ck_r(ck_region[32]),.rs_w(reset_local[33]),.rs_r(reset_local[32]),.i(rung_n_out_d[1]),.o(rung_n_out_d[2]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_out_h2(.ck_w(ck_region[32]),.ck_r(ck_region[31]),.rs_w(reset_local[32]),.rs_r(reset_local[31]),.i(rung_n_out_d[2]),.o(rung_n_out_d[3]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_out_h3(.ck_w(ck_region[31]),.ck_r(ck_region[30]),.rs_w(reset_local[31]),.rs_r(reset_local[30]),.i(rung_n_out_d[3]),.o(rung_n_out_d[4]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_out_h4(.ck_w(ck_region[30]),.ck_r(ck_region[35]),.rs_w(reset_local[30]),.rs_r(reset_local[35]),.i(rung_n_out_d[4]),.o(rung_n_out_d[5]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_out_h5(.ck_w(ck_region[35]),.ck_r(ck_region[34]),.rs_w(reset_local[35]),.rs_r(reset_local[34]),.i(rung_n_out_d[5]),.o(rung_n_out_d[6]));
 dsdv_bk_plana_land #(.W(276),.K((MUT==2 && 0)?0:1),.BYPASS((MUT==1)&&0)) rung_n_out_h6(.ck_w(ck_region[34]),.ck_r(ck_region[38]),.rs_w(reset_local[34]),.rs_r(reset_local[38]),.i(rung_n_out_d[6]),.o(rung_n_out_d[7]));
endmodule

// Existing bounded <=24-bit local landing rings, D2/K1, no datapath reset.
module dsdv_bk_plana_land #(parameter integer W=24,K=1,BYPASS=0)(
 input wire ck_w,ck_r,rs_w,rs_r,input wire[W-1:0]i,output wire[W-1:0]o);
 wire[2*W-1:0]bank;wire[3:0]epo;wire[2*((W+23)/24)-1:0]vld;wire[W-1:0]landed;
 ot_pl_land_chunk_w #(.W(W),.D(2),.CHUNK_BITS(24))u_w(.ck(ck_w),.rsi(rs_w),.i(i),.bank(bank),.epo(epo),.vld(vld));
 ot_pl_land_chunk_r #(.W(W),.D(2),.K(K),.CHUNK_BITS(24))u_r(.ck(ck_r),.rsi(rs_r),.bank(bank),.epo(epo),.vld(vld),.o(landed));
 assign o=BYPASS?i:landed;
endmodule
module dsdv_bksel_c_plana(input wire ck,rst,input wire[1729:0]f_s_s,f_s_n,input wire[707:0]f_o_s,f_o_n,
 output wire[131:0]t_c_s,t_c_n,output wire[1:0]t_cr_s,t_cr_n,output wire[513:0]vd);
 wire[263:0]tc;wire[3:0]cr;wire vf;
 dsfd_selt_c #(.SEARCH_PIPE(1),.DM(4),.PACE(2),.MRG_PIPE(1),.RQPIPE(1),.SLAT(4),.XDX(15))u_c(
 .ck(ck),.rst(rst),.f_s({f_s_n,f_s_s}),.f_o({f_o_n,f_o_s}),.t_c(tc),.t_cr(cr),.vd(vd),.vf(vf));
 assign {t_c_n,t_c_s}=tc;assign {t_cr_n,t_cr_s}=cr;
endmodule
