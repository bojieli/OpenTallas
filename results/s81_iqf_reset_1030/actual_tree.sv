module actual_iqf_reset(input wire clk,arst_n, output wire t5,t12,t13,t14,short14);
wire rst_n_t0;
wire rst_n_t1;
wire rst_n_t10;
wire rst_n_t11;
wire rst_n_t12;
wire rst_n_t13;
wire rst_n_t14;
wire rst_n_t15;
wire rst_n_t2;
wire rst_n_t3;
wire rst_n_t4;
wire rst_n_t5;
wire rst_n_t6;
wire rst_n_t7;
wire rst_n_t8;
wire rst_n_t9;
wire rst_rl_0;
wire rst_rl_1;
wire rst_rl_11;
wire rst_rl_13;
wire rst_rl_14;
wire rst_rl_17;
wire rst_rl_18;
wire rst_rl_2;
wire rst_rl_20;
wire rst_rl_21;
wire rst_rl_22;
wire rst_rl_23;
wire rst_rl_25;
wire rst_rl_26;
wire rst_rl_28;
wire rst_rl_3;
wire rst_rl_31;
wire rst_rl_33;
wire rst_rl_34;
wire rst_rl_37;
wire rst_rl_38;
wire rst_rl_5;
wire rst_rl_6;
wire rst_rl_8;
wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (die reset tree)
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // pad tap 14 depth 1 @ (901.8, 1073.5)
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // tap tap 14 depth 2 @ (901.8, 1073.5)
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // pad tap 14 depth 3 @ (901.8, 1073.5)
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // pad tap 14 depth 4 @ (901.8, 1073.5)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t14));  // pad tap 14 depth 5 @ (901.8, 1073.5)
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_1), .q(rst_rl_5));  // tap tap 10 depth 3 @ (901.8, 766.8)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));  // pad tap 10 depth 4 @ (901.8, 766.8)
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_n_t10));  // pad tap 10 depth 5 @ (901.8, 766.8)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_5), .q(rst_rl_8));  // tap tap 9 depth 4 @ (541.1, 766.8)
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_n_t9));  // pad tap 9 depth 5 @ (541.1, 766.8)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_8), .q(rst_n_t8));  // tap tap 8 depth 5 @ (180.4, 766.8)
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_5), .q(rst_rl_11));  // pad tap 11 depth 4 @ (1262.5, 766.8)
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_n_t11));  // tap tap 11 depth 5 @ (1262.5, 766.8)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_1), .q(rst_rl_13));  // pad tap 13 depth 3 @ (541.1, 1073.5)
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // tap tap 13 depth 4 @ (541.1, 1073.5)
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t13));  // pad tap 13 depth 5 @ (541.1, 1073.5)
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_14), .q(rst_n_t12));  // tap tap 12 depth 5 @ (180.4, 1073.5)
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_1), .q(rst_rl_17));  // pad tap 15 depth 3 @ (1262.5, 1073.5)
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // pad tap 15 depth 4 @ (1262.5, 1073.5)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t15));  // tap tap 15 depth 5 @ (1262.5, 1073.5)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_root_n), .q(rst_rl_20));  // wire tap None depth 1 @ (901.8, 839.1)
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));  // tap tap 6 depth 2 @ (901.8, 460.1)
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // pad tap 6 depth 3 @ (901.8, 460.1)
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // pad tap 6 depth 4 @ (901.8, 460.1)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t6));  // pad tap 6 depth 5 @ (901.8, 460.1)
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_21), .q(rst_rl_25));  // tap tap 2 depth 3 @ (901.8, 153.4)
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // pad tap 2 depth 4 @ (901.8, 153.4)
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t2));  // pad tap 2 depth 5 @ (901.8, 153.4)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_25), .q(rst_rl_28));  // tap tap 1 depth 4 @ (541.1, 153.4)
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_n_t1));  // pad tap 1 depth 5 @ (541.1, 153.4)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_28), .q(rst_n_t0));  // tap tap 0 depth 5 @ (180.4, 153.4)
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_25), .q(rst_rl_31));  // pad tap 3 depth 4 @ (1262.5, 153.4)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t3));  // tap tap 3 depth 5 @ (1262.5, 153.4)
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_21), .q(rst_rl_33));  // pad tap 5 depth 3 @ (541.1, 460.1)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // tap tap 5 depth 4 @ (541.1, 460.1)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t5));  // pad tap 5 depth 5 @ (541.1, 460.1)
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_34), .q(rst_n_t4));  // tap tap 4 depth 5 @ (180.4, 460.1)
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_21), .q(rst_rl_37));  // pad tap 7 depth 3 @ (1262.5, 460.1)
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // pad tap 7 depth 4 @ (1262.5, 460.1)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t7));  // tap tap 7 depth 5 @ (1262.5, 460.1)
assign t5=rst_n_t5,t12=rst_n_t12,t13=rst_n_t13,t14=rst_n_t14,short14=rst_rl_3;
endmodule
