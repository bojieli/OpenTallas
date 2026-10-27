module ot_dp_rrelay (input wire clk, input wire d, output reg q); always @(posedge clk) q <= d; endmodule
module ot_dp_rgate (input wire clk, input wire d, input wire run, output reg q); always @(posedge clk) q <= d & run; endmodule
module miter(input wire clk, input wire arst_n, input wire start_i, output wire eq);
    wire rn_rr_t8;
    wire rn_rst_rl_0;
    wire rn_rst_rl_1;
    wire rn_rst_rl_10;
    wire rn_rst_rl_11;
    wire rn_rst_rl_12;
    wire rn_rst_rl_14;
    wire rn_rst_rl_16;
    wire rn_rst_rl_18;
    wire rn_rst_rl_19;
    wire rn_rst_rl_2;
    wire rn_rst_rl_20;
    wire rn_rst_rl_22;
    wire rn_rst_rl_23;
    wire rn_rst_rl_24;
    wire rn_rst_rl_26;
    wire rn_rst_rl_27;
    wire rn_rst_rl_28;
    wire rn_rst_rl_30;
    wire rn_rst_rl_31;
    wire rn_rst_rl_34;
    wire rn_rst_rl_35;
    wire rn_rst_rl_36;
    wire rn_rst_rl_38;
    wire rn_rst_rl_39;
    wire rn_rst_rl_4;
    wire rn_rst_rl_40;
    wire rn_rst_rl_6;
    wire rn_rst_rl_7;
    wire rn_rst_rl_8;
    wire rr_t8;
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t10;
    wire rst_n_t11;
    wire rst_n_t12;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    wire rst_n_t9;
    wire rst_rl_0;
    wire rst_rl_1;
    wire rst_rl_10;
    wire rst_rl_11;
    wire rst_rl_12;
    wire rst_rl_14;
    wire rst_rl_16;
    wire rst_rl_18;
    wire rst_rl_19;
    wire rst_rl_2;
    wire rst_rl_20;
    wire rst_rl_22;
    wire rst_rl_23;
    wire rst_rl_24;
    wire rst_rl_26;
    wire rst_rl_27;
    wire rst_rl_28;
    wire rst_rl_30;
    wire rst_rl_31;
    wire rst_rl_34;
    wire rst_rl_35;
    wire rst_rl_36;
    wire rst_rl_38;
    wire rst_rl_39;
    wire rst_rl_4;
    wire rst_rl_40;
    wire rst_rl_6;
    wire rst_rl_7;
    wire rst_rl_8;
    wire rst_root_n;
    wire run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 3 depth 1 @ (466.6, 631.8)
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 3 depth 1 @ (466.6, 631.8)
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw tap tap 3 depth 2 @ (466.6, 631.8)
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run tap tap 3 depth 2 @ (466.6, 631.8)
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 3 depth 3 @ (466.6, 631.8)
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 3 depth 3 @ (466.6, 631.8)
    ot_dp_rgate u_rrl_3 (.clk(clk), .d(rst_rl_2), .run(rn_rst_rl_2), .q(rst_n_t3));  // gated pad tap 3 depth 4 @ (466.6, 631.8)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_1), .q(rst_rl_4));  // raw wire tap None depth 3 @ (185.8, 539.9)
    ot_dp_rrelay u_srl_4 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_4));  // run wire tap None depth 3 @ (185.8, 539.9)
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rr_t8));  // raw tap tap 8 depth 4 @ (8.2, 502.2)
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_4), .q(rn_rr_t8));  // run tap tap 8 depth 4 @ (8.2, 502.2)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_root_n), .q(rst_rl_6));  // raw pad tap 5 depth 1 @ (466.6, 716.0)
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(run_root), .q(rn_rst_rl_6));  // run pad tap 5 depth 1 @ (466.6, 716.0)
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 5 depth 2 @ (466.6, 716.0)
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 5 depth 2 @ (466.6, 716.0)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // raw pad tap 5 depth 3 @ (466.6, 716.0)
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(rn_rst_rl_7), .q(rn_rst_rl_8));  // run pad tap 5 depth 3 @ (466.6, 716.0)
    ot_dp_rgate u_rrl_9 (.clk(clk), .d(rst_rl_8), .run(rn_rst_rl_8), .q(rst_n_t5));  // gated tap tap 5 depth 4 @ (466.6, 716.0)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_root_n), .q(rst_rl_10));  // raw pad tap 7 depth 1 @ (466.6, 1035.7)
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(run_root), .q(rn_rst_rl_10));  // run pad tap 7 depth 1 @ (466.6, 1035.7)
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // raw tap tap 7 depth 2 @ (466.6, 1035.7)
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_10), .q(rn_rst_rl_11));  // run tap tap 7 depth 2 @ (466.6, 1035.7)
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 7 depth 3 @ (466.6, 1035.7)
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 7 depth 3 @ (466.6, 1035.7)
    ot_dp_rgate u_rrl_13 (.clk(clk), .d(rst_rl_12), .run(rn_rst_rl_12), .q(rst_n_t7));  // gated pad tap 7 depth 4 @ (466.6, 1035.7)
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_11), .q(rst_rl_14));  // raw pad tap 12 depth 3 @ (398.3, 1317.6)
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_14));  // run pad tap 12 depth 3 @ (398.3, 1317.6)
    ot_dp_rgate u_rrl_15 (.clk(clk), .d(rst_rl_14), .run(rn_rst_rl_14), .q(rst_n_t12));  // gated tap tap 12 depth 4 @ (398.3, 1317.6)
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_11), .q(rst_rl_16));  // raw wire tap None depth 3 @ (185.8, 1041.1)
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_16));  // run wire tap None depth 3 @ (185.8, 1041.1)
    ot_dp_rgate u_rrl_17 (.clk(clk), .d(rst_rl_16), .run(rn_rst_rl_16), .q(rst_n_t6));  // gated tap tap 6 depth 4 @ (155.5, 1171.8)
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_root_n), .q(rst_rl_18));  // raw pad tap 11 depth 1 @ (398.3, 997.9)
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(run_root), .q(rn_rst_rl_18));  // run pad tap 11 depth 1 @ (398.3, 997.9)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));  // raw pad tap 11 depth 2 @ (398.3, 997.9)
    ot_dp_rrelay u_srl_19 (.clk(clk), .d(rn_rst_rl_18), .q(rn_rst_rl_19));  // run pad tap 11 depth 2 @ (398.3, 997.9)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));  // raw pad tap 11 depth 3 @ (398.3, 997.9)
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_19), .q(rn_rst_rl_20));  // run pad tap 11 depth 3 @ (398.3, 997.9)
    ot_dp_rgate u_rrl_21 (.clk(clk), .d(rst_rl_20), .run(rn_rst_rl_20), .q(rst_n_t11));  // gated tap tap 11 depth 4 @ (398.3, 997.9)
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_root_n), .q(rst_rl_22));  // raw pad tap None depth 1 @ (609.1, 539.9)
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(run_root), .q(rn_rst_rl_22));  // run pad tap None depth 1 @ (609.1, 539.9)
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw wire tap None depth 2 @ (609.1, 539.9)
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run wire tap None depth 2 @ (609.1, 539.9)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // raw wire tap None depth 3 @ (609.1, 220.2)
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_24));  // run wire tap None depth 3 @ (609.1, 220.2)
    ot_dp_rgate u_rrl_25 (.clk(clk), .d(rst_rl_24), .run(rn_rst_rl_24), .q(rst_n_t1));  // gated tap tap 1 depth 4 @ (466.6, 24.8)
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_root_n), .q(rst_rl_26));  // raw wire tap None depth 1 @ (609.1, 721.4)
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(run_root), .q(rn_rst_rl_26));  // run wire tap None depth 1 @ (609.1, 721.4)
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // raw pad tap 10 depth 2 @ (398.3, 626.4)
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_26), .q(rn_rst_rl_27));  // run pad tap 10 depth 2 @ (398.3, 626.4)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // raw pad tap 10 depth 3 @ (398.3, 626.4)
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_27), .q(rn_rst_rl_28));  // run pad tap 10 depth 3 @ (398.3, 626.4)
    ot_dp_rgate u_rrl_29 (.clk(clk), .d(rst_rl_28), .run(rn_rst_rl_28), .q(rst_n_t10));  // gated tap tap 10 depth 4 @ (398.3, 626.4)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_26), .q(rst_rl_30));  // raw wire tap None depth 2 @ (289.3, 669.3)
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_26), .q(rn_rst_rl_30));  // run wire tap None depth 2 @ (289.3, 669.3)
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));  // raw tap tap 2 depth 3 @ (155.5, 502.2)
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_31));  // run tap tap 2 depth 3 @ (155.5, 502.2)
    ot_dp_rgate u_rrl_32 (.clk(clk), .d(rst_rl_31), .run(rn_rst_rl_31), .q(rst_n_t2));  // gated pad tap 2 depth 4 @ (155.5, 502.2)
    ot_dp_rgate u_rrl_33 (.clk(clk), .d(rst_rl_31), .run(rn_rst_rl_31), .q(rst_n_t0));  // gated tap tap 0 depth 4 @ (155.5, 167.4)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_root_n), .q(rst_rl_34));  // raw pad tap None depth 1 @ (375.8, 721.4)
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(run_root), .q(rn_rst_rl_34));  // run pad tap None depth 1 @ (375.8, 721.4)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_rl_35));  // raw pad tap None depth 2 @ (375.8, 721.4)
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(rn_rst_rl_34), .q(rn_rst_rl_35));  // run pad tap None depth 2 @ (375.8, 721.4)
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));  // raw wire tap None depth 3 @ (375.8, 721.4)
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_35), .q(rn_rst_rl_36));  // run wire tap None depth 3 @ (375.8, 721.4)
    ot_dp_rgate u_rrl_37 (.clk(clk), .d(rst_rl_36), .run(rn_rst_rl_36), .q(rst_n_t4));  // gated tap tap 4 depth 4 @ (155.5, 837.0)
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_root_n), .q(rst_rl_38));  // raw pad tap None depth 1 @ (609.1, 816.4)
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(run_root), .q(rn_rst_rl_38));  // run pad tap None depth 1 @ (609.1, 816.4)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_rl_39));  // raw wire tap None depth 2 @ (609.1, 816.4)
    ot_dp_rrelay u_srl_39 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_39));  // run wire tap None depth 2 @ (609.1, 816.4)
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));  // raw wire tap None depth 3 @ (609.1, 444.9)
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_39), .q(rn_rst_rl_40));  // run wire tap None depth 3 @ (609.1, 444.9)
    ot_dp_rgate u_rrl_41 (.clk(clk), .d(rst_rl_40), .run(rn_rst_rl_40), .q(rst_n_t9));  // gated tap tap 9 depth 4 @ (398.3, 306.7)
    assign eq = (rst_n_t3 == rst_n_t9) & (rst_n_t3 == rst_n_t10) & (rst_n_t3 == rst_n_t11) & (rst_n_t3 == rst_n_t12);
endmodule
