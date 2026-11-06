module g0(input clk,rst,input [7:0] r,f,output ready,fault);
reg [5:0] rp=0;always @(posedge clk) rp <= {rp[4:0],rst};
wire rst_root_n = rst;
wire rst_rl_0;assign rst_rl_0 = rp[0];
wire rst_rl_1;assign rst_rl_1 = rp[1];
wire rst_rl_2;assign rst_rl_2 = rp[2];
wire rst_rl_3;assign rst_rl_3 = rp[3];
wire rst_rl_4;assign rst_rl_4 = rp[4];
wire rr_t14;assign rr_t14 = rp[5];
wire rst_rl_6;assign rst_rl_6 = rp[0];
wire rst_rl_7;assign rst_rl_7 = rp[1];
wire rst_rl_8;assign rst_rl_8 = rp[2];
wire rst_rl_9;assign rst_rl_9 = rp[3];
wire rst_rl_10;assign rst_rl_10 = rp[4];
wire rr_t15;assign rr_t15 = rp[5];
wire rr_t13;assign rr_t13 = rp[5];
wire rst_rl_13;assign rst_rl_13 = rp[0];
wire rst_rl_14;assign rst_rl_14 = rp[1];
wire rst_rl_15;assign rst_rl_15 = rp[2];
wire rst_rl_16;assign rst_rl_16 = rp[3];
wire rst_rl_17;assign rst_rl_17 = rp[4];
wire rr_t16;assign rr_t16 = rp[5];
wire rst_rl_19;assign rst_rl_19 = rp[4];
wire rr_t0;assign rr_t0 = rp[5];
wire rst_rl_21;assign rst_rl_21 = rp[0];
wire rst_rl_22;assign rst_rl_22 = rp[1];
wire rst_rl_23;assign rst_rl_23 = rp[2];
wire rst_rl_24;assign rst_rl_24 = rp[3];
wire rst_rl_25;assign rst_rl_25 = rp[4];
wire rr_t17;assign rr_t17 = rp[5];
wire rst_rl_27;assign rst_rl_27 = rp[0];
wire rst_rl_28;assign rst_rl_28 = rp[1];
wire rst_rl_29;assign rst_rl_29 = rp[2];
wire rst_rl_30;assign rst_rl_30 = rp[3];
wire rst_rl_31;assign rst_rl_31 = rp[4];
wire rr_t5;assign rr_t5 = rp[5];
wire rst_rl_33;assign rst_rl_33 = rp[3];
wire rst_rl_34;assign rst_rl_34 = rp[4];
wire rr_t10;assign rr_t10 = rp[5];
wire rst_rl_36;assign rst_rl_36 = rp[0];
wire rst_rl_37;assign rst_rl_37 = rp[1];
wire rst_rl_38;assign rst_rl_38 = rp[2];
wire rst_rl_39;assign rst_rl_39 = rp[3];
wire rst_rl_40;assign rst_rl_40 = rp[4];
wire rr_t7;assign rr_t7 = rp[5];
wire rst_rl_42;assign rst_rl_42 = rp[3];
wire rst_rl_43;assign rst_rl_43 = rp[4];
wire rr_t3;assign rr_t3 = rp[5];
wire rst_rl_45;assign rst_rl_45 = rp[4];
wire rr_t18;assign rr_t18 = rp[5];
wire rst_rl_47;assign rst_rl_47 = rp[4];
wire rr_t1;assign rr_t1 = rp[5];
wire rst_rl_49;assign rst_rl_49 = rp[3];
wire rst_rl_50;assign rst_rl_50 = rp[4];
wire rr_t21;assign rr_t21 = rp[5];
wire rst_rl_52;assign rst_rl_52 = rp[3];
wire rst_rl_53;assign rst_rl_53 = rp[4];
wire rr_t6;assign rr_t6 = rp[5];
wire rst_rl_55;assign rst_rl_55 = rp[3];
wire rst_rl_56;assign rst_rl_56 = rp[4];
wire rr_t19;assign rr_t19 = rp[5];
wire rst_rl_58;assign rst_rl_58 = rp[1];
wire rst_rl_59;assign rst_rl_59 = rp[2];
wire rst_rl_60;assign rst_rl_60 = rp[3];
wire rst_rl_61;assign rst_rl_61 = rp[4];
wire rr_t22;assign rr_t22 = rp[5];
wire rst_rl_63;assign rst_rl_63 = rp[0];
wire rst_rl_64;assign rst_rl_64 = rp[1];
wire rst_rl_65;assign rst_rl_65 = rp[2];
wire rst_rl_66;assign rst_rl_66 = rp[3];
wire rst_rl_67;assign rst_rl_67 = rp[4];
wire rr_t8;assign rr_t8 = rp[5];
wire rst_rl_69;assign rst_rl_69 = rp[4];
wire rr_t2;assign rr_t2 = rp[5];
wire rr_t20;assign rr_t20 = rp[5];
wire rst_rl_72;assign rst_rl_72 = rp[0];
wire rst_rl_73;assign rst_rl_73 = rp[1];
wire rst_rl_74;assign rst_rl_74 = rp[2];
wire rst_rl_75;assign rst_rl_75 = rp[3];
wire rst_rl_76;assign rst_rl_76 = rp[4];
wire rr_t9;assign rr_t9 = rp[5];
wire rr_t4;assign rr_t4 = rp[5];
wire rst_rl_79;assign rst_rl_79 = rp[0];
wire rst_rl_80;assign rst_rl_80 = rp[1];
wire rst_rl_81;assign rst_rl_81 = rp[2];
wire rst_rl_82;assign rst_rl_82 = rp[3];
wire rst_rl_83;assign rst_rl_83 = rp[4];
wire rr_t23;assign rr_t23 = rp[5];
wire rst_rl_85;assign rst_rl_85 = rp[4];
wire rr_t12;assign rr_t12 = rp[5];
wire rr_t11;assign rr_t11 = rp[5];
    wire cland_r_rst_n_t1, cland_f_rst_n_t1;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t1 (
        .clk(clk), .rst_n(rr_t1), .ready_i({r[3]}),
        .fault_i({f[3]}), .ready_o(cland_r_rst_n_t1), .fault_o(cland_f_rst_n_t1));
    wire cland_r_rst_n_t16, cland_f_rst_n_t16;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t16 (
        .clk(clk), .rst_n(rr_t16), .ready_i({r[0]}),
        .fault_i({f[0]}), .ready_o(cland_r_rst_n_t16), .fault_o(cland_f_rst_n_t16));
    wire cland_r_rst_n_t18, cland_f_rst_n_t18;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t18 (
        .clk(clk), .rst_n(rr_t18), .ready_i({r[7]}),
        .fault_i({f[7]}), .ready_o(cland_r_rst_n_t18), .fault_o(cland_f_rst_n_t18));
    wire cland_r_rst_n_t19, cland_f_rst_n_t19;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t19 (
        .clk(clk), .rst_n(rr_t19), .ready_i({r[6]}),
        .fault_i({f[6]}), .ready_o(cland_r_rst_n_t19), .fault_o(cland_f_rst_n_t19));
    wire cland_r_rst_n_t3, cland_f_rst_n_t3;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_n_t3 (
        .clk(clk), .rst_n(rr_t3), .ready_i({r[1], r[2]}),
        .fault_i({f[1], f[2]}), .ready_o(cland_r_rst_n_t3), .fault_o(cland_f_rst_n_t3));
    wire cland_r_rst_n_t4, cland_f_rst_n_t4;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t4 (
        .clk(clk), .rst_n(rr_t4), .ready_i({r[4]}),
        .fault_i({f[4]}), .ready_o(cland_r_rst_n_t4), .fault_o(cland_f_rst_n_t4));
    wire cland_r_rst_n_t9, cland_f_rst_n_t9;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t9 (
        .clk(clk), .rst_n(rr_t9), .ready_i({r[5]}),
        .fault_i({f[5]}), .ready_o(cland_r_rst_n_t9), .fault_o(cland_f_rst_n_t9));
    wire cland_r_rst_rl_17, cland_f_rst_rl_17;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_17 (
        .clk(clk), .rst_n(rst_rl_17), .ready_i({cland_r_rst_n_t16}),
        .fault_i({cland_f_rst_n_t16}), .ready_o(cland_r_rst_rl_17), .fault_o(cland_f_rst_rl_17));
    wire cland_r_rst_rl_43, cland_f_rst_rl_43;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_43 (
        .clk(clk), .rst_n(rst_rl_43), .ready_i({cland_r_rst_n_t3}),
        .fault_i({cland_f_rst_n_t3}), .ready_o(cland_r_rst_rl_43), .fault_o(cland_f_rst_rl_43));
    wire cland_r_rst_rl_45, cland_f_rst_rl_45;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_45 (
        .clk(clk), .rst_n(rst_rl_45), .ready_i({cland_r_rst_n_t18}),
        .fault_i({cland_f_rst_n_t18}), .ready_o(cland_r_rst_rl_45), .fault_o(cland_f_rst_rl_45));
    wire cland_r_rst_rl_47, cland_f_rst_rl_47;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_47 (
        .clk(clk), .rst_n(rst_rl_47), .ready_i({cland_r_rst_n_t1}),
        .fault_i({cland_f_rst_n_t1}), .ready_o(cland_r_rst_rl_47), .fault_o(cland_f_rst_rl_47));
    wire cland_r_rst_rl_56, cland_f_rst_rl_56;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_56 (
        .clk(clk), .rst_n(rst_rl_56), .ready_i({cland_r_rst_n_t19}),
        .fault_i({cland_f_rst_n_t19}), .ready_o(cland_r_rst_rl_56), .fault_o(cland_f_rst_rl_56));
    wire cland_r_rst_rl_76, cland_f_rst_rl_76;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_76 (
        .clk(clk), .rst_n(rst_rl_76), .ready_i({cland_r_rst_n_t4, cland_r_rst_n_t9}),
        .fault_i({cland_f_rst_n_t4, cland_f_rst_n_t9}), .ready_o(cland_r_rst_rl_76), .fault_o(cland_f_rst_rl_76));
    wire cland_r_rst_rl_16, cland_f_rst_rl_16;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_16 (
        .clk(clk), .rst_n(rst_rl_16), .ready_i({cland_r_rst_rl_17}),
        .fault_i({cland_f_rst_rl_17}), .ready_o(cland_r_rst_rl_16), .fault_o(cland_f_rst_rl_16));
    wire cland_r_rst_rl_42, cland_f_rst_rl_42;
    ot_dp_landing_collect #(.N(3)) u_cland_collect_rst_rl_42 (
        .clk(clk), .rst_n(rst_rl_42), .ready_i({cland_r_rst_rl_43, cland_r_rst_rl_45, cland_r_rst_rl_47}),
        .fault_i({cland_f_rst_rl_43, cland_f_rst_rl_45, cland_f_rst_rl_47}), .ready_o(cland_r_rst_rl_42), .fault_o(cland_f_rst_rl_42));
    wire cland_r_rst_rl_55, cland_f_rst_rl_55;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_55 (
        .clk(clk), .rst_n(rst_rl_55), .ready_i({cland_r_rst_rl_56}),
        .fault_i({cland_f_rst_rl_56}), .ready_o(cland_r_rst_rl_55), .fault_o(cland_f_rst_rl_55));
    wire cland_r_rst_rl_75, cland_f_rst_rl_75;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_75 (
        .clk(clk), .rst_n(rst_rl_75), .ready_i({cland_r_rst_rl_76}),
        .fault_i({cland_f_rst_rl_76}), .ready_o(cland_r_rst_rl_75), .fault_o(cland_f_rst_rl_75));
    wire cland_r_rst_rl_15, cland_f_rst_rl_15;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_15 (
        .clk(clk), .rst_n(rst_rl_15), .ready_i({cland_r_rst_rl_16}),
        .fault_i({cland_f_rst_rl_16}), .ready_o(cland_r_rst_rl_15), .fault_o(cland_f_rst_rl_15));
    wire cland_r_rst_rl_38, cland_f_rst_rl_38;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_38 (
        .clk(clk), .rst_n(rst_rl_38), .ready_i({cland_r_rst_rl_42, cland_r_rst_rl_55}),
        .fault_i({cland_f_rst_rl_42, cland_f_rst_rl_55}), .ready_o(cland_r_rst_rl_38), .fault_o(cland_f_rst_rl_38));
    wire cland_r_rst_rl_74, cland_f_rst_rl_74;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_74 (
        .clk(clk), .rst_n(rst_rl_74), .ready_i({cland_r_rst_rl_75}),
        .fault_i({cland_f_rst_rl_75}), .ready_o(cland_r_rst_rl_74), .fault_o(cland_f_rst_rl_74));
    wire cland_r_rst_rl_14, cland_f_rst_rl_14;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_14 (
        .clk(clk), .rst_n(rst_rl_14), .ready_i({cland_r_rst_rl_15}),
        .fault_i({cland_f_rst_rl_15}), .ready_o(cland_r_rst_rl_14), .fault_o(cland_f_rst_rl_14));
    wire cland_r_rst_rl_37, cland_f_rst_rl_37;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_37 (
        .clk(clk), .rst_n(rst_rl_37), .ready_i({cland_r_rst_rl_38}),
        .fault_i({cland_f_rst_rl_38}), .ready_o(cland_r_rst_rl_37), .fault_o(cland_f_rst_rl_37));
    wire cland_r_rst_rl_73, cland_f_rst_rl_73;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_73 (
        .clk(clk), .rst_n(rst_rl_73), .ready_i({cland_r_rst_rl_74}),
        .fault_i({cland_f_rst_rl_74}), .ready_o(cland_r_rst_rl_73), .fault_o(cland_f_rst_rl_73));
    wire cland_r_rst_rl_13, cland_f_rst_rl_13;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_13 (
        .clk(clk), .rst_n(rst_rl_13), .ready_i({cland_r_rst_rl_14}),
        .fault_i({cland_f_rst_rl_14}), .ready_o(cland_r_rst_rl_13), .fault_o(cland_f_rst_rl_13));
    wire cland_r_rst_rl_36, cland_f_rst_rl_36;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_36 (
        .clk(clk), .rst_n(rst_rl_36), .ready_i({cland_r_rst_rl_37}),
        .fault_i({cland_f_rst_rl_37}), .ready_o(cland_r_rst_rl_36), .fault_o(cland_f_rst_rl_36));
    wire cland_r_rst_rl_72, cland_f_rst_rl_72;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_72 (
        .clk(clk), .rst_n(rst_rl_72), .ready_i({cland_r_rst_rl_73}),
        .fault_i({cland_f_rst_rl_73}), .ready_o(cland_r_rst_rl_72), .fault_o(cland_f_rst_rl_72));
    ot_dp_landing_collect #(.N(3)) u_cland_collect_rst_root_n (
        .clk(clk), .rst_n(rst_root_n), .ready_i({cland_r_rst_rl_13, cland_r_rst_rl_36, cland_r_rst_rl_72}),
        .fault_i({cland_f_rst_rl_13, cland_f_rst_rl_36, cland_f_rst_rl_72}), .ready_o(cland_up_ready), .fault_o(cland_up_fault));
assign ready=cland_up_ready;assign fault=cland_up_fault;endmodule
module t0(input clk,rst,input [7:0] r,f,output ready,fault);
reg [5:0] rp=0;always @(posedge clk) rp <= {rp[4:0],rst};
wire rst_root_n = rst;
wire rst_rl_0;assign rst_rl_0 = rp[0];
wire rst_rl_1;assign rst_rl_1 = rp[1];
wire rst_rl_2;assign rst_rl_2 = rp[2];
wire rst_rl_3;assign rst_rl_3 = rp[3];
wire rst_rl_4;assign rst_rl_4 = rp[4];
wire rr_t14;assign rr_t14 = rp[5];
wire rst_rl_6;assign rst_rl_6 = rp[0];
wire rst_rl_7;assign rst_rl_7 = rp[1];
wire rst_rl_8;assign rst_rl_8 = rp[2];
wire rst_rl_9;assign rst_rl_9 = rp[3];
wire rst_rl_10;assign rst_rl_10 = rp[4];
wire rr_t15;assign rr_t15 = rp[5];
wire rst_rl_12;assign rst_rl_12 = rp[0];
wire rst_rl_13;assign rst_rl_13 = rp[1];
wire rst_rl_14;assign rst_rl_14 = rp[2];
wire rst_rl_15;assign rst_rl_15 = rp[3];
wire rst_rl_16;assign rst_rl_16 = rp[4];
wire rr_t16;assign rr_t16 = rp[5];
wire rst_rl_18;assign rst_rl_18 = rp[4];
wire rr_t0;assign rr_t0 = rp[5];
wire rst_rl_20;assign rst_rl_20 = rp[0];
wire rst_rl_21;assign rst_rl_21 = rp[1];
wire rst_rl_22;assign rst_rl_22 = rp[2];
wire rst_rl_23;assign rst_rl_23 = rp[3];
wire rst_rl_24;assign rst_rl_24 = rp[4];
wire rr_t17;assign rr_t17 = rp[5];
wire rst_rl_26;assign rst_rl_26 = rp[0];
wire rst_rl_27;assign rst_rl_27 = rp[1];
wire rst_rl_28;assign rst_rl_28 = rp[2];
wire rst_rl_29;assign rst_rl_29 = rp[3];
wire rst_rl_30;assign rst_rl_30 = rp[4];
wire rr_t1;assign rr_t1 = rp[5];
wire rst_rl_32;assign rst_rl_32 = rp[0];
wire rst_rl_33;assign rst_rl_33 = rp[1];
wire rst_rl_34;assign rst_rl_34 = rp[2];
wire rst_rl_35;assign rst_rl_35 = rp[3];
wire rst_rl_36;assign rst_rl_36 = rp[4];
wire rr_t9;assign rr_t9 = rp[5];
wire rst_rl_38;assign rst_rl_38 = rp[4];
wire rr_t3;assign rr_t3 = rp[5];
wire rst_rl_40;assign rst_rl_40 = rp[0];
wire rst_rl_41;assign rst_rl_41 = rp[1];
wire rst_rl_42;assign rst_rl_42 = rp[2];
wire rst_rl_43;assign rst_rl_43 = rp[3];
wire rst_rl_44;assign rst_rl_44 = rp[4];
wire rr_t10;assign rr_t10 = rp[5];
wire rst_rl_46;assign rst_rl_46 = rp[4];
wire rr_t4;assign rr_t4 = rp[5];
wire rst_rl_48;assign rst_rl_48 = rp[3];
wire rst_rl_49;assign rst_rl_49 = rp[4];
wire rr_t5;assign rr_t5 = rp[5];
wire rst_rl_51;assign rst_rl_51 = rp[0];
wire rst_rl_52;assign rst_rl_52 = rp[1];
wire rst_rl_53;assign rst_rl_53 = rp[2];
wire rst_rl_54;assign rst_rl_54 = rp[3];
wire rst_rl_55;assign rst_rl_55 = rp[4];
wire rr_t7;assign rr_t7 = rp[5];
wire rst_rl_57;assign rst_rl_57 = rp[0];
wire rst_rl_58;assign rst_rl_58 = rp[1];
wire rst_rl_59;assign rst_rl_59 = rp[2];
wire rst_rl_60;assign rst_rl_60 = rp[3];
wire rst_rl_61;assign rst_rl_61 = rp[4];
wire rr_t8;assign rr_t8 = rp[5];
wire rst_rl_63;assign rst_rl_63 = rp[4];
wire rr_t2;assign rr_t2 = rp[5];
wire rst_rl_65;assign rst_rl_65 = rp[4];
wire rr_t21;assign rr_t21 = rp[5];
wire rst_rl_67;assign rst_rl_67 = rp[4];
wire rr_t6;assign rr_t6 = rp[5];
wire rst_rl_69;assign rst_rl_69 = rp[4];
wire rr_t18;assign rr_t18 = rp[5];
wire rst_rl_71;assign rst_rl_71 = rp[4];
wire rr_t19;assign rr_t19 = rp[5];
wire rst_rl_73;assign rst_rl_73 = rp[3];
wire rst_rl_74;assign rst_rl_74 = rp[4];
wire rr_t20;assign rr_t20 = rp[5];
wire rst_rl_76;assign rst_rl_76 = rp[2];
wire rst_rl_77;assign rst_rl_77 = rp[3];
wire rst_rl_78;assign rst_rl_78 = rp[4];
wire rr_t22;assign rr_t22 = rp[5];
wire rst_rl_80;assign rst_rl_80 = rp[0];
wire rst_rl_81;assign rst_rl_81 = rp[1];
wire rst_rl_82;assign rst_rl_82 = rp[2];
wire rst_rl_83;assign rst_rl_83 = rp[3];
wire rst_rl_84;assign rst_rl_84 = rp[4];
wire rr_t13;assign rr_t13 = rp[5];
wire rst_rl_86;assign rst_rl_86 = rp[0];
wire rst_rl_87;assign rst_rl_87 = rp[1];
wire rst_rl_88;assign rst_rl_88 = rp[2];
wire rst_rl_89;assign rst_rl_89 = rp[3];
wire rst_rl_90;assign rst_rl_90 = rp[4];
wire rr_t23;assign rr_t23 = rp[5];
wire rst_rl_92;assign rst_rl_92 = rp[4];
wire rr_t12;assign rr_t12 = rp[5];
wire rr_t11;assign rr_t11 = rp[5];
    wire cland_r_rst_n_t1, cland_f_rst_n_t1;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t1 (
        .clk(clk), .rst_n(rr_t1), .ready_i({r[3]}),
        .fault_i({f[3]}), .ready_o(cland_r_rst_n_t1), .fault_o(cland_f_rst_n_t1));
    wire cland_r_rst_n_t16, cland_f_rst_n_t16;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t16 (
        .clk(clk), .rst_n(rr_t16), .ready_i({r[0]}),
        .fault_i({f[0]}), .ready_o(cland_r_rst_n_t16), .fault_o(cland_f_rst_n_t16));
    wire cland_r_rst_n_t18, cland_f_rst_n_t18;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t18 (
        .clk(clk), .rst_n(rr_t18), .ready_i({r[7]}),
        .fault_i({f[7]}), .ready_o(cland_r_rst_n_t18), .fault_o(cland_f_rst_n_t18));
    wire cland_r_rst_n_t19, cland_f_rst_n_t19;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t19 (
        .clk(clk), .rst_n(rr_t19), .ready_i({r[6]}),
        .fault_i({f[6]}), .ready_o(cland_r_rst_n_t19), .fault_o(cland_f_rst_n_t19));
    wire cland_r_rst_n_t3, cland_f_rst_n_t3;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_n_t3 (
        .clk(clk), .rst_n(rr_t3), .ready_i({r[1], r[2]}),
        .fault_i({f[1], f[2]}), .ready_o(cland_r_rst_n_t3), .fault_o(cland_f_rst_n_t3));
    wire cland_r_rst_n_t4, cland_f_rst_n_t4;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t4 (
        .clk(clk), .rst_n(rr_t4), .ready_i({r[4]}),
        .fault_i({f[4]}), .ready_o(cland_r_rst_n_t4), .fault_o(cland_f_rst_n_t4));
    wire cland_r_rst_n_t9, cland_f_rst_n_t9;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t9 (
        .clk(clk), .rst_n(rr_t9), .ready_i({r[5]}),
        .fault_i({f[5]}), .ready_o(cland_r_rst_n_t9), .fault_o(cland_f_rst_n_t9));
    wire cland_r_rst_rl_16, cland_f_rst_rl_16;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_16 (
        .clk(clk), .rst_n(rst_rl_16), .ready_i({cland_r_rst_n_t16}),
        .fault_i({cland_f_rst_n_t16}), .ready_o(cland_r_rst_rl_16), .fault_o(cland_f_rst_rl_16));
    wire cland_r_rst_rl_30, cland_f_rst_rl_30;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_30 (
        .clk(clk), .rst_n(rst_rl_30), .ready_i({cland_r_rst_n_t1}),
        .fault_i({cland_f_rst_n_t1}), .ready_o(cland_r_rst_rl_30), .fault_o(cland_f_rst_rl_30));
    wire cland_r_rst_rl_36, cland_f_rst_rl_36;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_36 (
        .clk(clk), .rst_n(rst_rl_36), .ready_i({cland_r_rst_n_t9}),
        .fault_i({cland_f_rst_n_t9}), .ready_o(cland_r_rst_rl_36), .fault_o(cland_f_rst_rl_36));
    wire cland_r_rst_rl_38, cland_f_rst_rl_38;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_38 (
        .clk(clk), .rst_n(rst_rl_38), .ready_i({cland_r_rst_n_t3}),
        .fault_i({cland_f_rst_n_t3}), .ready_o(cland_r_rst_rl_38), .fault_o(cland_f_rst_rl_38));
    wire cland_r_rst_rl_46, cland_f_rst_rl_46;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_46 (
        .clk(clk), .rst_n(rst_rl_46), .ready_i({cland_r_rst_n_t4}),
        .fault_i({cland_f_rst_n_t4}), .ready_o(cland_r_rst_rl_46), .fault_o(cland_f_rst_rl_46));
    wire cland_r_rst_rl_69, cland_f_rst_rl_69;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_69 (
        .clk(clk), .rst_n(rst_rl_69), .ready_i({cland_r_rst_n_t18}),
        .fault_i({cland_f_rst_n_t18}), .ready_o(cland_r_rst_rl_69), .fault_o(cland_f_rst_rl_69));
    wire cland_r_rst_rl_71, cland_f_rst_rl_71;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_71 (
        .clk(clk), .rst_n(rst_rl_71), .ready_i({cland_r_rst_n_t19}),
        .fault_i({cland_f_rst_n_t19}), .ready_o(cland_r_rst_rl_71), .fault_o(cland_f_rst_rl_71));
    wire cland_r_rst_rl_15, cland_f_rst_rl_15;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_15 (
        .clk(clk), .rst_n(rst_rl_15), .ready_i({cland_r_rst_rl_16}),
        .fault_i({cland_f_rst_rl_16}), .ready_o(cland_r_rst_rl_15), .fault_o(cland_f_rst_rl_15));
    wire cland_r_rst_rl_29, cland_f_rst_rl_29;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_29 (
        .clk(clk), .rst_n(rst_rl_29), .ready_i({cland_r_rst_rl_30}),
        .fault_i({cland_f_rst_rl_30}), .ready_o(cland_r_rst_rl_29), .fault_o(cland_f_rst_rl_29));
    wire cland_r_rst_rl_35, cland_f_rst_rl_35;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_35 (
        .clk(clk), .rst_n(rst_rl_35), .ready_i({cland_r_rst_rl_36, cland_r_rst_rl_38}),
        .fault_i({cland_f_rst_rl_36, cland_f_rst_rl_38}), .ready_o(cland_r_rst_rl_35), .fault_o(cland_f_rst_rl_35));
    wire cland_r_rst_rl_43, cland_f_rst_rl_43;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_43 (
        .clk(clk), .rst_n(rst_rl_43), .ready_i({cland_r_rst_rl_46}),
        .fault_i({cland_f_rst_rl_46}), .ready_o(cland_r_rst_rl_43), .fault_o(cland_f_rst_rl_43));
    wire cland_r_rst_rl_60, cland_f_rst_rl_60;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_60 (
        .clk(clk), .rst_n(rst_rl_60), .ready_i({cland_r_rst_rl_69, cland_r_rst_rl_71}),
        .fault_i({cland_f_rst_rl_69, cland_f_rst_rl_71}), .ready_o(cland_r_rst_rl_60), .fault_o(cland_f_rst_rl_60));
    wire cland_r_rst_rl_14, cland_f_rst_rl_14;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_14 (
        .clk(clk), .rst_n(rst_rl_14), .ready_i({cland_r_rst_rl_15}),
        .fault_i({cland_f_rst_rl_15}), .ready_o(cland_r_rst_rl_14), .fault_o(cland_f_rst_rl_14));
    wire cland_r_rst_rl_28, cland_f_rst_rl_28;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_28 (
        .clk(clk), .rst_n(rst_rl_28), .ready_i({cland_r_rst_rl_29}),
        .fault_i({cland_f_rst_rl_29}), .ready_o(cland_r_rst_rl_28), .fault_o(cland_f_rst_rl_28));
    wire cland_r_rst_rl_34, cland_f_rst_rl_34;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_34 (
        .clk(clk), .rst_n(rst_rl_34), .ready_i({cland_r_rst_rl_35}),
        .fault_i({cland_f_rst_rl_35}), .ready_o(cland_r_rst_rl_34), .fault_o(cland_f_rst_rl_34));
    wire cland_r_rst_rl_42, cland_f_rst_rl_42;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_42 (
        .clk(clk), .rst_n(rst_rl_42), .ready_i({cland_r_rst_rl_43}),
        .fault_i({cland_f_rst_rl_43}), .ready_o(cland_r_rst_rl_42), .fault_o(cland_f_rst_rl_42));
    wire cland_r_rst_rl_59, cland_f_rst_rl_59;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_59 (
        .clk(clk), .rst_n(rst_rl_59), .ready_i({cland_r_rst_rl_60}),
        .fault_i({cland_f_rst_rl_60}), .ready_o(cland_r_rst_rl_59), .fault_o(cland_f_rst_rl_59));
    wire cland_r_rst_rl_13, cland_f_rst_rl_13;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_13 (
        .clk(clk), .rst_n(rst_rl_13), .ready_i({cland_r_rst_rl_14}),
        .fault_i({cland_f_rst_rl_14}), .ready_o(cland_r_rst_rl_13), .fault_o(cland_f_rst_rl_13));
    wire cland_r_rst_rl_27, cland_f_rst_rl_27;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_27 (
        .clk(clk), .rst_n(rst_rl_27), .ready_i({cland_r_rst_rl_28}),
        .fault_i({cland_f_rst_rl_28}), .ready_o(cland_r_rst_rl_27), .fault_o(cland_f_rst_rl_27));
    wire cland_r_rst_rl_33, cland_f_rst_rl_33;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_33 (
        .clk(clk), .rst_n(rst_rl_33), .ready_i({cland_r_rst_rl_34}),
        .fault_i({cland_f_rst_rl_34}), .ready_o(cland_r_rst_rl_33), .fault_o(cland_f_rst_rl_33));
    wire cland_r_rst_rl_41, cland_f_rst_rl_41;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_41 (
        .clk(clk), .rst_n(rst_rl_41), .ready_i({cland_r_rst_rl_42}),
        .fault_i({cland_f_rst_rl_42}), .ready_o(cland_r_rst_rl_41), .fault_o(cland_f_rst_rl_41));
    wire cland_r_rst_rl_58, cland_f_rst_rl_58;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_58 (
        .clk(clk), .rst_n(rst_rl_58), .ready_i({cland_r_rst_rl_59}),
        .fault_i({cland_f_rst_rl_59}), .ready_o(cland_r_rst_rl_58), .fault_o(cland_f_rst_rl_58));
    wire cland_r_rst_rl_12, cland_f_rst_rl_12;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_12 (
        .clk(clk), .rst_n(rst_rl_12), .ready_i({cland_r_rst_rl_13}),
        .fault_i({cland_f_rst_rl_13}), .ready_o(cland_r_rst_rl_12), .fault_o(cland_f_rst_rl_12));
    wire cland_r_rst_rl_26, cland_f_rst_rl_26;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_26 (
        .clk(clk), .rst_n(rst_rl_26), .ready_i({cland_r_rst_rl_27}),
        .fault_i({cland_f_rst_rl_27}), .ready_o(cland_r_rst_rl_26), .fault_o(cland_f_rst_rl_26));
    wire cland_r_rst_rl_32, cland_f_rst_rl_32;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_32 (
        .clk(clk), .rst_n(rst_rl_32), .ready_i({cland_r_rst_rl_33}),
        .fault_i({cland_f_rst_rl_33}), .ready_o(cland_r_rst_rl_32), .fault_o(cland_f_rst_rl_32));
    wire cland_r_rst_rl_40, cland_f_rst_rl_40;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_40 (
        .clk(clk), .rst_n(rst_rl_40), .ready_i({cland_r_rst_rl_41}),
        .fault_i({cland_f_rst_rl_41}), .ready_o(cland_r_rst_rl_40), .fault_o(cland_f_rst_rl_40));
    wire cland_r_rst_rl_57, cland_f_rst_rl_57;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_57 (
        .clk(clk), .rst_n(rst_rl_57), .ready_i({cland_r_rst_rl_58}),
        .fault_i({cland_f_rst_rl_58}), .ready_o(cland_r_rst_rl_57), .fault_o(cland_f_rst_rl_57));
    ot_dp_landing_collect #(.N(5)) u_cland_collect_rst_root_n (
        .clk(clk), .rst_n(rst_root_n), .ready_i({cland_r_rst_rl_12, cland_r_rst_rl_26, cland_r_rst_rl_32, cland_r_rst_rl_40, cland_r_rst_rl_57}),
        .fault_i({cland_f_rst_rl_12, cland_f_rst_rl_26, cland_f_rst_rl_32, cland_f_rst_rl_40, cland_f_rst_rl_57}), .ready_o(cland_up_ready), .fault_o(cland_up_fault));
assign ready=cland_up_ready;assign fault=cland_up_fault;endmodule
module g1(input clk,rst,input [7:0] r,f,output ready,fault);
reg [5:0] rp=0;always @(posedge clk) rp <= {rp[4:0],rst};
wire rst_root_n = rst;
wire rst_rl_0;assign rst_rl_0 = rp[0];
wire rst_rl_1;assign rst_rl_1 = rp[1];
wire rst_rl_2;assign rst_rl_2 = rp[2];
wire rst_rl_3;assign rst_rl_3 = rp[3];
wire rst_rl_4;assign rst_rl_4 = rp[4];
wire rr_t14;assign rr_t14 = rp[5];
wire rst_rl_6;assign rst_rl_6 = rp[0];
wire rst_rl_7;assign rst_rl_7 = rp[1];
wire rst_rl_8;assign rst_rl_8 = rp[2];
wire rst_rl_9;assign rst_rl_9 = rp[3];
wire rst_rl_10;assign rst_rl_10 = rp[4];
wire rr_t15;assign rr_t15 = rp[5];
wire rr_t13;assign rr_t13 = rp[5];
wire rst_rl_13;assign rst_rl_13 = rp[0];
wire rst_rl_14;assign rst_rl_14 = rp[1];
wire rst_rl_15;assign rst_rl_15 = rp[2];
wire rst_rl_16;assign rst_rl_16 = rp[3];
wire rst_rl_17;assign rst_rl_17 = rp[4];
wire rr_t16;assign rr_t16 = rp[5];
wire rst_rl_19;assign rst_rl_19 = rp[4];
wire rr_t0;assign rr_t0 = rp[5];
wire rst_rl_21;assign rst_rl_21 = rp[0];
wire rst_rl_22;assign rst_rl_22 = rp[1];
wire rst_rl_23;assign rst_rl_23 = rp[2];
wire rst_rl_24;assign rst_rl_24 = rp[3];
wire rst_rl_25;assign rst_rl_25 = rp[4];
wire rr_t17;assign rr_t17 = rp[5];
wire rst_rl_27;assign rst_rl_27 = rp[0];
wire rst_rl_28;assign rst_rl_28 = rp[1];
wire rst_rl_29;assign rst_rl_29 = rp[2];
wire rst_rl_30;assign rst_rl_30 = rp[3];
wire rst_rl_31;assign rst_rl_31 = rp[4];
wire rr_t5;assign rr_t5 = rp[5];
wire rst_rl_33;assign rst_rl_33 = rp[3];
wire rst_rl_34;assign rst_rl_34 = rp[4];
wire rr_t10;assign rr_t10 = rp[5];
wire rst_rl_36;assign rst_rl_36 = rp[0];
wire rst_rl_37;assign rst_rl_37 = rp[1];
wire rst_rl_38;assign rst_rl_38 = rp[2];
wire rst_rl_39;assign rst_rl_39 = rp[3];
wire rst_rl_40;assign rst_rl_40 = rp[4];
wire rr_t7;assign rr_t7 = rp[5];
wire rst_rl_42;assign rst_rl_42 = rp[3];
wire rst_rl_43;assign rst_rl_43 = rp[4];
wire rr_t3;assign rr_t3 = rp[5];
wire rst_rl_45;assign rst_rl_45 = rp[4];
wire rr_t18;assign rr_t18 = rp[5];
wire rst_rl_47;assign rst_rl_47 = rp[4];
wire rr_t1;assign rr_t1 = rp[5];
wire rst_rl_49;assign rst_rl_49 = rp[3];
wire rst_rl_50;assign rst_rl_50 = rp[4];
wire rr_t21;assign rr_t21 = rp[5];
wire rst_rl_52;assign rst_rl_52 = rp[3];
wire rst_rl_53;assign rst_rl_53 = rp[4];
wire rr_t6;assign rr_t6 = rp[5];
wire rst_rl_55;assign rst_rl_55 = rp[1];
wire rst_rl_56;assign rst_rl_56 = rp[2];
wire rst_rl_57;assign rst_rl_57 = rp[3];
wire rst_rl_58;assign rst_rl_58 = rp[4];
wire rr_t22;assign rr_t22 = rp[5];
wire rr_t19;assign rr_t19 = rp[5];
wire rst_rl_61;assign rst_rl_61 = rp[0];
wire rst_rl_62;assign rst_rl_62 = rp[1];
wire rst_rl_63;assign rst_rl_63 = rp[2];
wire rst_rl_64;assign rst_rl_64 = rp[3];
wire rst_rl_65;assign rst_rl_65 = rp[4];
wire rr_t8;assign rr_t8 = rp[5];
wire rst_rl_67;assign rst_rl_67 = rp[4];
wire rr_t2;assign rr_t2 = rp[5];
wire rr_t20;assign rr_t20 = rp[5];
wire rst_rl_70;assign rst_rl_70 = rp[0];
wire rst_rl_71;assign rst_rl_71 = rp[1];
wire rst_rl_72;assign rst_rl_72 = rp[2];
wire rst_rl_73;assign rst_rl_73 = rp[3];
wire rst_rl_74;assign rst_rl_74 = rp[4];
wire rr_t9;assign rr_t9 = rp[5];
wire rr_t4;assign rr_t4 = rp[5];
wire rst_rl_77;assign rst_rl_77 = rp[0];
wire rst_rl_78;assign rst_rl_78 = rp[1];
wire rst_rl_79;assign rst_rl_79 = rp[2];
wire rst_rl_80;assign rst_rl_80 = rp[3];
wire rst_rl_81;assign rst_rl_81 = rp[4];
wire rr_t23;assign rr_t23 = rp[5];
wire rst_rl_83;assign rst_rl_83 = rp[4];
wire rr_t12;assign rr_t12 = rp[5];
wire rr_t11;assign rr_t11 = rp[5];
    wire cland_r_rst_n_t1, cland_f_rst_n_t1;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t1 (
        .clk(clk), .rst_n(rr_t1), .ready_i({r[3]}),
        .fault_i({f[3]}), .ready_o(cland_r_rst_n_t1), .fault_o(cland_f_rst_n_t1));
    wire cland_r_rst_n_t18, cland_f_rst_n_t18;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t18 (
        .clk(clk), .rst_n(rr_t18), .ready_i({r[6]}),
        .fault_i({f[6]}), .ready_o(cland_r_rst_n_t18), .fault_o(cland_f_rst_n_t18));
    wire cland_r_rst_n_t3, cland_f_rst_n_t3;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_n_t3 (
        .clk(clk), .rst_n(rr_t3), .ready_i({r[1], r[2]}),
        .fault_i({f[1], f[2]}), .ready_o(cland_r_rst_n_t3), .fault_o(cland_f_rst_n_t3));
    wire cland_r_rst_n_t4, cland_f_rst_n_t4;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t4 (
        .clk(clk), .rst_n(rr_t4), .ready_i({r[4]}),
        .fault_i({f[4]}), .ready_o(cland_r_rst_n_t4), .fault_o(cland_f_rst_n_t4));
    wire cland_r_rst_n_t9, cland_f_rst_n_t9;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t9 (
        .clk(clk), .rst_n(rr_t9), .ready_i({r[5]}),
        .fault_i({f[5]}), .ready_o(cland_r_rst_n_t9), .fault_o(cland_f_rst_n_t9));
    wire cland_r_rst_rl_43, cland_f_rst_rl_43;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_43 (
        .clk(clk), .rst_n(rst_rl_43), .ready_i({cland_r_rst_n_t3}),
        .fault_i({cland_f_rst_n_t3}), .ready_o(cland_r_rst_rl_43), .fault_o(cland_f_rst_rl_43));
    wire cland_r_rst_rl_45, cland_f_rst_rl_45;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_45 (
        .clk(clk), .rst_n(rst_rl_45), .ready_i({cland_r_rst_n_t18}),
        .fault_i({cland_f_rst_n_t18}), .ready_o(cland_r_rst_rl_45), .fault_o(cland_f_rst_rl_45));
    wire cland_r_rst_rl_47, cland_f_rst_rl_47;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_47 (
        .clk(clk), .rst_n(rst_rl_47), .ready_i({cland_r_rst_n_t1}),
        .fault_i({cland_f_rst_n_t1}), .ready_o(cland_r_rst_rl_47), .fault_o(cland_f_rst_rl_47));
    wire cland_r_rst_rl_74, cland_f_rst_rl_74;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_74 (
        .clk(clk), .rst_n(rst_rl_74), .ready_i({cland_r_rst_n_t4, cland_r_rst_n_t9}),
        .fault_i({cland_f_rst_n_t4, cland_f_rst_n_t9}), .ready_o(cland_r_rst_rl_74), .fault_o(cland_f_rst_rl_74));
    wire cland_r_rst_rl_42, cland_f_rst_rl_42;
    ot_dp_landing_collect #(.N(3)) u_cland_collect_rst_rl_42 (
        .clk(clk), .rst_n(rst_rl_42), .ready_i({cland_r_rst_rl_43, cland_r_rst_rl_45, cland_r_rst_rl_47}),
        .fault_i({cland_f_rst_rl_43, cland_f_rst_rl_45, cland_f_rst_rl_47}), .ready_o(cland_r_rst_rl_42), .fault_o(cland_f_rst_rl_42));
    wire cland_r_rst_rl_73, cland_f_rst_rl_73;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_73 (
        .clk(clk), .rst_n(rst_rl_73), .ready_i({cland_r_rst_rl_74}),
        .fault_i({cland_f_rst_rl_74}), .ready_o(cland_r_rst_rl_73), .fault_o(cland_f_rst_rl_73));
    wire cland_r_rst_rl_38, cland_f_rst_rl_38;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_38 (
        .clk(clk), .rst_n(rst_rl_38), .ready_i({cland_r_rst_rl_42}),
        .fault_i({cland_f_rst_rl_42}), .ready_o(cland_r_rst_rl_38), .fault_o(cland_f_rst_rl_38));
    wire cland_r_rst_rl_72, cland_f_rst_rl_72;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_72 (
        .clk(clk), .rst_n(rst_rl_72), .ready_i({cland_r_rst_rl_73}),
        .fault_i({cland_f_rst_rl_73}), .ready_o(cland_r_rst_rl_72), .fault_o(cland_f_rst_rl_72));
    wire cland_r_rst_rl_37, cland_f_rst_rl_37;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_37 (
        .clk(clk), .rst_n(rst_rl_37), .ready_i({cland_r_rst_rl_38}),
        .fault_i({cland_f_rst_rl_38}), .ready_o(cland_r_rst_rl_37), .fault_o(cland_f_rst_rl_37));
    wire cland_r_rst_rl_71, cland_f_rst_rl_71;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_71 (
        .clk(clk), .rst_n(rst_rl_71), .ready_i({cland_r_rst_rl_72}),
        .fault_i({cland_f_rst_rl_72}), .ready_o(cland_r_rst_rl_71), .fault_o(cland_f_rst_rl_71));
    wire cland_r_rst_rl_36, cland_f_rst_rl_36;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_36 (
        .clk(clk), .rst_n(rst_rl_36), .ready_i({cland_r_rst_rl_37}),
        .fault_i({cland_f_rst_rl_37}), .ready_o(cland_r_rst_rl_36), .fault_o(cland_f_rst_rl_36));
    wire cland_r_rst_rl_70, cland_f_rst_rl_70;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_70 (
        .clk(clk), .rst_n(rst_rl_70), .ready_i({cland_r_rst_rl_71}),
        .fault_i({cland_f_rst_rl_71}), .ready_o(cland_r_rst_rl_70), .fault_o(cland_f_rst_rl_70));
    wire cland_r_rst_root_n, cland_f_rst_root_n;
    ot_dp_landing_collect #(.N(3)) u_cland_collect_rst_root_n (
        .clk(clk), .rst_n(rst_root_n), .ready_i({r[7], cland_r_rst_rl_36, cland_r_rst_rl_70}),
        .fault_i({f[7], cland_f_rst_rl_36, cland_f_rst_rl_70}), .ready_o(cland_r_rst_root_n), .fault_o(cland_f_rst_root_n));
    wire cland_r_rst_rl_13, cland_f_rst_rl_13;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_13 (
        .clk(clk), .rst_n(rst_rl_13), .ready_i({cland_r_rst_root_n}),
        .fault_i({cland_f_rst_root_n}), .ready_o(cland_r_rst_rl_13), .fault_o(cland_f_rst_rl_13));
    wire cland_r_rst_n_t16, cland_f_rst_n_t16;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t16 (
        .clk(clk), .rst_n(rr_t16), .ready_i({r[0]}),
        .fault_i({f[0]}), .ready_o(cland_r_rst_n_t16), .fault_o(cland_f_rst_n_t16));
    wire cland_r_rst_rl_14, cland_f_rst_rl_14;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_14 (
        .clk(clk), .rst_n(rst_rl_14), .ready_i({cland_r_rst_rl_13}),
        .fault_i({cland_f_rst_rl_13}), .ready_o(cland_r_rst_rl_14), .fault_o(cland_f_rst_rl_14));
    wire cland_r_rst_rl_15, cland_f_rst_rl_15;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_15 (
        .clk(clk), .rst_n(rst_rl_15), .ready_i({cland_r_rst_rl_14}),
        .fault_i({cland_f_rst_rl_14}), .ready_o(cland_r_rst_rl_15), .fault_o(cland_f_rst_rl_15));
    wire cland_r_rst_rl_17, cland_f_rst_rl_17;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_17 (
        .clk(clk), .rst_n(rst_rl_17), .ready_i({cland_r_rst_n_t16}),
        .fault_i({cland_f_rst_n_t16}), .ready_o(cland_r_rst_rl_17), .fault_o(cland_f_rst_rl_17));
    wire cland_r_rst_rl_16, cland_f_rst_rl_16;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_16 (
        .clk(clk), .rst_n(rst_rl_16), .ready_i({cland_r_rst_rl_15, cland_r_rst_rl_17}),
        .fault_i({cland_f_rst_rl_15, cland_f_rst_rl_17}), .ready_o(cland_r_rst_rl_16), .fault_o(cland_f_rst_rl_16));
    wire cland_r_rst_rl_19, cland_f_rst_rl_19;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_19 (
        .clk(clk), .rst_n(rst_rl_19), .ready_i({cland_r_rst_rl_16}),
        .fault_i({cland_f_rst_rl_16}), .ready_o(cland_r_rst_rl_19), .fault_o(cland_f_rst_rl_19));
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t0 (
        .clk(clk), .rst_n(rr_t0), .ready_i({cland_r_rst_rl_19}),
        .fault_i({cland_f_rst_rl_19}), .ready_o(cland_up_ready), .fault_o(cland_up_fault));
assign ready=cland_up_ready;assign fault=cland_up_fault;endmodule
module t1(input clk,rst,input [7:0] r,f,output ready,fault);
reg mutant_delay=0;always @(posedge clk) mutant_delay<=r[0];
reg [5:0] rp=0;always @(posedge clk) rp <= {rp[4:0],rst};
wire rst_root_n = rst;
wire rst_rl_0;assign rst_rl_0 = rp[0];
wire rst_rl_1;assign rst_rl_1 = rp[1];
wire rst_rl_2;assign rst_rl_2 = rp[2];
wire rst_rl_3;assign rst_rl_3 = rp[3];
wire rst_rl_4;assign rst_rl_4 = rp[4];
wire rr_t14;assign rr_t14 = rp[5];
wire rst_rl_6;assign rst_rl_6 = rp[0];
wire rst_rl_7;assign rst_rl_7 = rp[1];
wire rst_rl_8;assign rst_rl_8 = rp[2];
wire rst_rl_9;assign rst_rl_9 = rp[3];
wire rst_rl_10;assign rst_rl_10 = rp[4];
wire rr_t15;assign rr_t15 = rp[5];
wire rst_rl_12;assign rst_rl_12 = rp[0];
wire rst_rl_13;assign rst_rl_13 = rp[1];
wire rst_rl_14;assign rst_rl_14 = rp[2];
wire rst_rl_15;assign rst_rl_15 = rp[3];
wire rst_rl_16;assign rst_rl_16 = rp[4];
wire rr_t16;assign rr_t16 = rp[5];
wire rst_rl_18;assign rst_rl_18 = rp[4];
wire rr_t0;assign rr_t0 = rp[5];
wire rst_rl_20;assign rst_rl_20 = rp[0];
wire rst_rl_21;assign rst_rl_21 = rp[1];
wire rst_rl_22;assign rst_rl_22 = rp[2];
wire rst_rl_23;assign rst_rl_23 = rp[3];
wire rst_rl_24;assign rst_rl_24 = rp[4];
wire rr_t17;assign rr_t17 = rp[5];
wire rst_rl_26;assign rst_rl_26 = rp[0];
wire rst_rl_27;assign rst_rl_27 = rp[1];
wire rst_rl_28;assign rst_rl_28 = rp[2];
wire rst_rl_29;assign rst_rl_29 = rp[3];
wire rst_rl_30;assign rst_rl_30 = rp[4];
wire rr_t1;assign rr_t1 = rp[5];
wire rst_rl_32;assign rst_rl_32 = rp[0];
wire rst_rl_33;assign rst_rl_33 = rp[1];
wire rst_rl_34;assign rst_rl_34 = rp[2];
wire rst_rl_35;assign rst_rl_35 = rp[3];
wire rst_rl_36;assign rst_rl_36 = rp[4];
wire rr_t9;assign rr_t9 = rp[5];
wire rst_rl_38;assign rst_rl_38 = rp[4];
wire rr_t3;assign rr_t3 = rp[5];
wire rst_rl_40;assign rst_rl_40 = rp[0];
wire rst_rl_41;assign rst_rl_41 = rp[1];
wire rst_rl_42;assign rst_rl_42 = rp[2];
wire rst_rl_43;assign rst_rl_43 = rp[3];
wire rst_rl_44;assign rst_rl_44 = rp[4];
wire rr_t10;assign rr_t10 = rp[5];
wire rst_rl_46;assign rst_rl_46 = rp[4];
wire rr_t4;assign rr_t4 = rp[5];
wire rst_rl_48;assign rst_rl_48 = rp[3];
wire rst_rl_49;assign rst_rl_49 = rp[4];
wire rr_t5;assign rr_t5 = rp[5];
wire rst_rl_51;assign rst_rl_51 = rp[0];
wire rst_rl_52;assign rst_rl_52 = rp[1];
wire rst_rl_53;assign rst_rl_53 = rp[2];
wire rst_rl_54;assign rst_rl_54 = rp[3];
wire rst_rl_55;assign rst_rl_55 = rp[4];
wire rr_t7;assign rr_t7 = rp[5];
wire rst_rl_57;assign rst_rl_57 = rp[0];
wire rst_rl_58;assign rst_rl_58 = rp[1];
wire rst_rl_59;assign rst_rl_59 = rp[2];
wire rst_rl_60;assign rst_rl_60 = rp[3];
wire rst_rl_61;assign rst_rl_61 = rp[4];
wire rr_t8;assign rr_t8 = rp[5];
wire rst_rl_63;assign rst_rl_63 = rp[4];
wire rr_t2;assign rr_t2 = rp[5];
wire rst_rl_65;assign rst_rl_65 = rp[4];
wire rr_t21;assign rr_t21 = rp[5];
wire rst_rl_67;assign rst_rl_67 = rp[4];
wire rr_t6;assign rr_t6 = rp[5];
wire rst_rl_69;assign rst_rl_69 = rp[4];
wire rr_t18;assign rr_t18 = rp[5];
wire rst_rl_71;assign rst_rl_71 = rp[3];
wire rst_rl_72;assign rst_rl_72 = rp[4];
wire rr_t20;assign rr_t20 = rp[5];
wire rst_rl_74;assign rst_rl_74 = rp[2];
wire rst_rl_75;assign rst_rl_75 = rp[3];
wire rst_rl_76;assign rst_rl_76 = rp[4];
wire rr_t22;assign rr_t22 = rp[5];
wire rr_t19;assign rr_t19 = rp[5];
wire rst_rl_79;assign rst_rl_79 = rp[0];
wire rst_rl_80;assign rst_rl_80 = rp[1];
wire rst_rl_81;assign rst_rl_81 = rp[2];
wire rst_rl_82;assign rst_rl_82 = rp[3];
wire rst_rl_83;assign rst_rl_83 = rp[4];
wire rr_t13;assign rr_t13 = rp[5];
wire rst_rl_85;assign rst_rl_85 = rp[0];
wire rst_rl_86;assign rst_rl_86 = rp[1];
wire rst_rl_87;assign rst_rl_87 = rp[2];
wire rst_rl_88;assign rst_rl_88 = rp[3];
wire rst_rl_89;assign rst_rl_89 = rp[4];
wire rr_t23;assign rr_t23 = rp[5];
wire rst_rl_91;assign rst_rl_91 = rp[4];
wire rr_t12;assign rr_t12 = rp[5];
wire rr_t11;assign rr_t11 = rp[5];
    wire cland_r_rst_n_t1, cland_f_rst_n_t1;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t1 (
        .clk(clk), .rst_n(rr_t1), .ready_i({r[3]}),
        .fault_i({f[3]}), .ready_o(cland_r_rst_n_t1), .fault_o(cland_f_rst_n_t1));
    wire cland_r_rst_n_t18, cland_f_rst_n_t18;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t18 (
        .clk(clk), .rst_n(rr_t18), .ready_i({r[6]}),
        .fault_i({f[6]}), .ready_o(cland_r_rst_n_t18), .fault_o(cland_f_rst_n_t18));
    wire cland_r_rst_n_t3, cland_f_rst_n_t3;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_n_t3 (
        .clk(clk), .rst_n(rr_t3), .ready_i({r[1], r[2]}),
        .fault_i({f[1], f[2]}), .ready_o(cland_r_rst_n_t3), .fault_o(cland_f_rst_n_t3));
    wire cland_r_rst_n_t4, cland_f_rst_n_t4;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t4 (
        .clk(clk), .rst_n(rr_t4), .ready_i({r[4]}),
        .fault_i({f[4]}), .ready_o(cland_r_rst_n_t4), .fault_o(cland_f_rst_n_t4));
    wire cland_r_rst_n_t9, cland_f_rst_n_t9;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t9 (
        .clk(clk), .rst_n(rr_t9), .ready_i({r[5]}),
        .fault_i({f[5]}), .ready_o(cland_r_rst_n_t9), .fault_o(cland_f_rst_n_t9));
    wire cland_r_rst_rl_30, cland_f_rst_rl_30;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_30 (
        .clk(clk), .rst_n(rst_rl_30), .ready_i({cland_r_rst_n_t1}),
        .fault_i({cland_f_rst_n_t1}), .ready_o(cland_r_rst_rl_30), .fault_o(cland_f_rst_rl_30));
    wire cland_r_rst_rl_36, cland_f_rst_rl_36;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_36 (
        .clk(clk), .rst_n(rst_rl_36), .ready_i({cland_r_rst_n_t9}),
        .fault_i({cland_f_rst_n_t9}), .ready_o(cland_r_rst_rl_36), .fault_o(cland_f_rst_rl_36));
    wire cland_r_rst_rl_38, cland_f_rst_rl_38;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_38 (
        .clk(clk), .rst_n(rst_rl_38), .ready_i({cland_r_rst_n_t3}),
        .fault_i({cland_f_rst_n_t3}), .ready_o(cland_r_rst_rl_38), .fault_o(cland_f_rst_rl_38));
    wire cland_r_rst_rl_46, cland_f_rst_rl_46;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_46 (
        .clk(clk), .rst_n(rst_rl_46), .ready_i({cland_r_rst_n_t4}),
        .fault_i({cland_f_rst_n_t4}), .ready_o(cland_r_rst_rl_46), .fault_o(cland_f_rst_rl_46));
    wire cland_r_rst_rl_69, cland_f_rst_rl_69;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_69 (
        .clk(clk), .rst_n(rst_rl_69), .ready_i({cland_r_rst_n_t18}),
        .fault_i({cland_f_rst_n_t18}), .ready_o(cland_r_rst_rl_69), .fault_o(cland_f_rst_rl_69));
    wire cland_r_rst_rl_29, cland_f_rst_rl_29;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_29 (
        .clk(clk), .rst_n(rst_rl_29), .ready_i({cland_r_rst_rl_30}),
        .fault_i({cland_f_rst_rl_30}), .ready_o(cland_r_rst_rl_29), .fault_o(cland_f_rst_rl_29));
    wire cland_r_rst_rl_35, cland_f_rst_rl_35;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_35 (
        .clk(clk), .rst_n(rst_rl_35), .ready_i({cland_r_rst_rl_36, cland_r_rst_rl_38}),
        .fault_i({cland_f_rst_rl_36, cland_f_rst_rl_38}), .ready_o(cland_r_rst_rl_35), .fault_o(cland_f_rst_rl_35));
    wire cland_r_rst_rl_43, cland_f_rst_rl_43;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_43 (
        .clk(clk), .rst_n(rst_rl_43), .ready_i({cland_r_rst_rl_46}),
        .fault_i({cland_f_rst_rl_46}), .ready_o(cland_r_rst_rl_43), .fault_o(cland_f_rst_rl_43));
    wire cland_r_rst_rl_60, cland_f_rst_rl_60;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_60 (
        .clk(clk), .rst_n(rst_rl_60), .ready_i({cland_r_rst_rl_69}),
        .fault_i({cland_f_rst_rl_69}), .ready_o(cland_r_rst_rl_60), .fault_o(cland_f_rst_rl_60));
    wire cland_r_rst_rl_28, cland_f_rst_rl_28;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_28 (
        .clk(clk), .rst_n(rst_rl_28), .ready_i({cland_r_rst_rl_29}),
        .fault_i({cland_f_rst_rl_29}), .ready_o(cland_r_rst_rl_28), .fault_o(cland_f_rst_rl_28));
    wire cland_r_rst_rl_34, cland_f_rst_rl_34;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_34 (
        .clk(clk), .rst_n(rst_rl_34), .ready_i({cland_r_rst_rl_35}),
        .fault_i({cland_f_rst_rl_35}), .ready_o(cland_r_rst_rl_34), .fault_o(cland_f_rst_rl_34));
    wire cland_r_rst_rl_42, cland_f_rst_rl_42;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_42 (
        .clk(clk), .rst_n(rst_rl_42), .ready_i({cland_r_rst_rl_43}),
        .fault_i({cland_f_rst_rl_43}), .ready_o(cland_r_rst_rl_42), .fault_o(cland_f_rst_rl_42));
    wire cland_r_rst_rl_59, cland_f_rst_rl_59;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_59 (
        .clk(clk), .rst_n(rst_rl_59), .ready_i({cland_r_rst_rl_60}),
        .fault_i({cland_f_rst_rl_60}), .ready_o(cland_r_rst_rl_59), .fault_o(cland_f_rst_rl_59));
    wire cland_r_rst_rl_27, cland_f_rst_rl_27;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_27 (
        .clk(clk), .rst_n(rst_rl_27), .ready_i({cland_r_rst_rl_28}),
        .fault_i({cland_f_rst_rl_28}), .ready_o(cland_r_rst_rl_27), .fault_o(cland_f_rst_rl_27));
    wire cland_r_rst_rl_33, cland_f_rst_rl_33;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_33 (
        .clk(clk), .rst_n(rst_rl_33), .ready_i({cland_r_rst_rl_34}),
        .fault_i({cland_f_rst_rl_34}), .ready_o(cland_r_rst_rl_33), .fault_o(cland_f_rst_rl_33));
    wire cland_r_rst_rl_41, cland_f_rst_rl_41;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_41 (
        .clk(clk), .rst_n(rst_rl_41), .ready_i({cland_r_rst_rl_42}),
        .fault_i({cland_f_rst_rl_42}), .ready_o(cland_r_rst_rl_41), .fault_o(cland_f_rst_rl_41));
    wire cland_r_rst_rl_58, cland_f_rst_rl_58;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_58 (
        .clk(clk), .rst_n(rst_rl_58), .ready_i({cland_r_rst_rl_59}),
        .fault_i({cland_f_rst_rl_59}), .ready_o(cland_r_rst_rl_58), .fault_o(cland_f_rst_rl_58));
    wire cland_r_rst_rl_26, cland_f_rst_rl_26;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_26 (
        .clk(clk), .rst_n(rst_rl_26), .ready_i({cland_r_rst_rl_27}),
        .fault_i({cland_f_rst_rl_27}), .ready_o(cland_r_rst_rl_26), .fault_o(cland_f_rst_rl_26));
    wire cland_r_rst_rl_32, cland_f_rst_rl_32;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_32 (
        .clk(clk), .rst_n(rst_rl_32), .ready_i({cland_r_rst_rl_33}),
        .fault_i({cland_f_rst_rl_33}), .ready_o(cland_r_rst_rl_32), .fault_o(cland_f_rst_rl_32));
    wire cland_r_rst_rl_40, cland_f_rst_rl_40;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_40 (
        .clk(clk), .rst_n(rst_rl_40), .ready_i({cland_r_rst_rl_41}),
        .fault_i({cland_f_rst_rl_41}), .ready_o(cland_r_rst_rl_40), .fault_o(cland_f_rst_rl_40));
    wire cland_r_rst_rl_57, cland_f_rst_rl_57;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_57 (
        .clk(clk), .rst_n(rst_rl_57), .ready_i({cland_r_rst_rl_58}),
        .fault_i({cland_f_rst_rl_58}), .ready_o(cland_r_rst_rl_57), .fault_o(cland_f_rst_rl_57));
    wire cland_r_rst_root_n, cland_f_rst_root_n;
    ot_dp_landing_collect #(.N(5)) u_cland_collect_rst_root_n (
        .clk(clk), .rst_n(rst_root_n), .ready_i({r[7], cland_r_rst_rl_26, cland_r_rst_rl_32, cland_r_rst_rl_40, cland_r_rst_rl_57}),
        .fault_i({f[7], cland_f_rst_rl_26, cland_f_rst_rl_32, cland_f_rst_rl_40, cland_f_rst_rl_57}), .ready_o(cland_r_rst_root_n), .fault_o(cland_f_rst_root_n));
    wire cland_r_rst_rl_12, cland_f_rst_rl_12;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_12 (
        .clk(clk), .rst_n(rst_rl_12), .ready_i({cland_r_rst_root_n}),
        .fault_i({cland_f_rst_root_n}), .ready_o(cland_r_rst_rl_12), .fault_o(cland_f_rst_rl_12));
    wire cland_r_rst_n_t16, cland_f_rst_n_t16;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t16 (
        .clk(clk), .rst_n(rr_t16), .ready_i({mutant_delay}),
        .fault_i({f[0]}), .ready_o(cland_r_rst_n_t16), .fault_o(cland_f_rst_n_t16));
    wire cland_r_rst_rl_13, cland_f_rst_rl_13;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_13 (
        .clk(clk), .rst_n(rst_rl_13), .ready_i({cland_r_rst_rl_12}),
        .fault_i({cland_f_rst_rl_12}), .ready_o(cland_r_rst_rl_13), .fault_o(cland_f_rst_rl_13));
    wire cland_r_rst_rl_14, cland_f_rst_rl_14;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_14 (
        .clk(clk), .rst_n(rst_rl_14), .ready_i({cland_r_rst_rl_13}),
        .fault_i({cland_f_rst_rl_13}), .ready_o(cland_r_rst_rl_14), .fault_o(cland_f_rst_rl_14));
    wire cland_r_rst_rl_16, cland_f_rst_rl_16;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_16 (
        .clk(clk), .rst_n(rst_rl_16), .ready_i({cland_r_rst_n_t16}),
        .fault_i({cland_f_rst_n_t16}), .ready_o(cland_r_rst_rl_16), .fault_o(cland_f_rst_rl_16));
    wire cland_r_rst_rl_15, cland_f_rst_rl_15;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_15 (
        .clk(clk), .rst_n(rst_rl_15), .ready_i({cland_r_rst_rl_14, cland_r_rst_rl_16}),
        .fault_i({cland_f_rst_rl_14, cland_f_rst_rl_16}), .ready_o(cland_r_rst_rl_15), .fault_o(cland_f_rst_rl_15));
    wire cland_r_rst_rl_18, cland_f_rst_rl_18;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_18 (
        .clk(clk), .rst_n(rst_rl_18), .ready_i({cland_r_rst_rl_15}),
        .fault_i({cland_f_rst_rl_15}), .ready_o(cland_r_rst_rl_18), .fault_o(cland_f_rst_rl_18));
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t0 (
        .clk(clk), .rst_n(rr_t0), .ready_i({cland_r_rst_rl_18}),
        .fault_i({cland_f_rst_rl_18}), .ready_o(cland_up_ready), .fault_o(cland_up_fault));
assign ready=cland_up_ready;assign fault=cland_up_fault;endmodule
