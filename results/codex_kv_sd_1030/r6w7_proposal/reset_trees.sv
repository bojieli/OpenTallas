module dut0(input wire clk,arst_n,start_i,output wire[21:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 19 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
    wire rst_root_n, run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    (* keep = 1 *) wire rst_n_t0;
    (* keep = 1 *) wire rst_n_t1;
    (* keep = 1 *) wire rst_n_t2;
    (* keep = 1 *) wire rst_n_t3;
    (* keep = 1 *) wire rst_n_t4;
    (* keep = 1 *) wire rst_n_t5;
    (* keep = 1 *) wire rst_n_t6;
    (* keep = 1 *) wire rst_n_t7;
    (* keep = 1 *) wire rst_n_t8;
    (* keep = 1 *) wire rst_n_t9;
    (* keep = 1 *) wire rst_n_t10;
    (* keep = 1 *) wire rst_n_t11;
    (* keep = 1 *) wire rst_n_t12;
    (* keep = 1 *) wire rst_n_t13;
    (* keep = 1 *) wire rst_n_t14;
    (* keep = 1 *) wire rst_n_t15;
    (* keep = 1 *) wire rst_n_t16;
    (* keep = 1 *) wire rst_n_t17;
    (* keep = 1 *) wire rst_n_t18;
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t2 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 2 depth 1 @ (949.9, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 2 depth 1 @ (949.9, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 2 depth 2 @ (949.9, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 2 depth 2 @ (949.9, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw tap tap 2 depth 3 @ (949.9, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run tap tap 2 depth 3 @ (949.9, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 2 depth 4 @ (949.9, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 2 depth 4 @ (949.9, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t2));  // boot pad tap 2 depth 5 @ (949.9, 21.6)
    wire start_t2;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t2));  // gated pad tap 2 depth 5 @ (949.9, 21.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_2), .q(rst_rl_5));  // raw pad tap 1 depth 4 @ (570.7, 21.6)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_5));  // run pad tap 1 depth 4 @ (570.7, 21.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (570.7, 21.6)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_2), .q(rst_rl_7));  // raw wire tap None depth 4 @ (570.2, 21.6)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_7));  // run wire tap None depth 4 @ (570.2, 21.6)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_n_t0));  // boot tap tap 0 depth 5 @ (190.6, 21.6)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_root_n), .q(rst_rl_9));  // raw tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(run_root), .q(rn_rst_rl_9));  // run tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // raw pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_10), .q(rn_rst_rl_11));  // run pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 3 depth 4 @ (1331.0, 21.6)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 3 depth 4 @ (1331.0, 21.6)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_n_t3));  // boot pad tap 3 depth 5 @ (1331.0, 21.6)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_9), .q(rst_rl_14));  // raw pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_14));  // run pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // raw tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_15));  // run tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 10 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 10 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_15), .q(rst_rl_18));  // raw tap tap 13 depth 4 @ (1872.7, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_18));  // run tap tap 13 depth 4 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_18), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1872.7, 400.0)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_9), .q(rst_rl_21));  // raw tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_21;
    ot_dp_rrelay u_srl_21 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_21));  // run tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // raw pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_22));  // run pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw pad tap 11 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run pad tap 11 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1650.0, 30.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_21), .q(rst_rl_25));  // raw pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_25));  // run pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // raw pad tap 5 depth 4 @ (1874.9, 160.0)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_26));  // run pad tap 5 depth 4 @ (1874.9, 160.0)
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1874.9, 160.0)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_21), .q(rst_rl_28));  // raw tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_28));  // run tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw pad tap 14 depth 4 @ (1872.7, 120.0)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run pad tap 14 depth 4 @ (1872.7, 120.0)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t14));  // boot pad tap 14 depth 5 @ (1872.7, 120.0)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_28), .q(rst_rl_31));  // raw wire tap None depth 4 @ (1872.7, 470.0)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_31));  // run wire tap None depth 4 @ (1872.7, 470.0)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t18));  // boot tap tap 18 depth 5 @ (1872.7, 820.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_21), .q(rst_rl_33));  // raw pad tap None depth 3 @ (1872.7, 183.8)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_33));  // run pad tap None depth 3 @ (1872.7, 183.8)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // raw wire tap None depth 4 @ (1872.7, 183.8)
    wire rn_rst_rl_34;
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(rn_rst_rl_33), .q(rn_rst_rl_34));  // run wire tap None depth 4 @ (1872.7, 183.8)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1872.7, 560.0)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_9), .q(rst_rl_36));  // raw pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_36));  // run pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw pad tap 12 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run pad tap 12 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t12));  // boot tap tap 12 depth 5 @ (1690.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_root_n), .q(rst_rl_40));  // raw pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(run_root), .q(rn_rst_rl_40));  // run pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // raw pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_41), .q(rn_rst_rl_42));  // run pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw pad tap 7 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run pad tap 7 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t7));  // boot tap tap 7 depth 5 @ (1150.0, 30.2)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_root_n), .q(rst_rl_45));  // raw pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(run_root), .q(rn_rst_rl_45));  // run pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // raw pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_46));  // run pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));  // raw pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_47;
    ot_dp_rrelay u_srl_47 (.clk(clk), .d(rn_rst_rl_46), .q(rn_rst_rl_47));  // run pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));  // raw pad tap 8 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_47), .q(rn_rst_rl_48));  // run pad tap 8 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_n_t8));  // boot tap tap 8 depth 5 @ (1300.0, 30.2)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_root_n), .q(rst_rl_50));  // raw pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(run_root), .q(rn_rst_rl_50));  // run pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // raw tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_50), .q(rn_rst_rl_51));  // run tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));  // raw pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_52;
    ot_dp_rrelay u_srl_52 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_52));  // run pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));  // raw pad tap 9 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_52), .q(rn_rst_rl_53));  // run pad tap 9 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1450.0, 30.2)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_51), .q(rst_rl_55));  // raw pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rn_rst_rl_55;
    ot_dp_rrelay u_srl_55 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_55));  // run pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // raw pad tap 4 depth 4 @ (1711.2, 21.6)
    wire rn_rst_rl_56;
    ot_dp_rrelay u_srl_56 (.clk(clk), .d(rn_rst_rl_55), .q(rn_rst_rl_56));  // run pad tap 4 depth 4 @ (1711.2, 21.6)
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1711.2, 21.6)
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_51), .q(rst_rl_58));  // raw pad tap None depth 3 @ (1771.2, 30.2)
    wire rn_rst_rl_58;
    ot_dp_rrelay u_srl_58 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_58));  // run pad tap None depth 3 @ (1771.2, 30.2)
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_rl_59));  // raw wire tap None depth 4 @ (1771.2, 30.2)
    wire rn_rst_rl_59;
    ot_dp_rrelay u_srl_59 (.clk(clk), .d(rn_rst_rl_58), .q(rn_rst_rl_59));  // run wire tap None depth 4 @ (1771.2, 30.2)
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1872.7, 250.0)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_51), .q(rst_rl_61));  // raw wire tap None depth 3 @ (1794.9, 30.2)
    wire rn_rst_rl_61;
    ot_dp_rrelay u_srl_61 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_61));  // run wire tap None depth 3 @ (1794.9, 30.2)
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));  // raw wire tap None depth 4 @ (1874.9, 295.1)
    wire rn_rst_rl_62;
    ot_dp_rrelay u_srl_62 (.clk(clk), .d(rn_rst_rl_61), .q(rn_rst_rl_62));  // run wire tap None depth 4 @ (1874.9, 295.1)
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1874.9, 640.0)
wire local0;ot_dp_rrelay copy0(.clk(clk),.d(rst_rl_7),.q(local0));
wire local1;ot_dp_rrelay copy1(.clk(clk),.d(rst_rl_31),.q(local1));
wire local2;ot_dp_rrelay copy2(.clk(clk),.d(rst_rl_31),.q(local2));
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,rst_n_t18,local0,local1,local2};endmodule
module mut0(input wire clk,arst_n,start_i,output wire[21:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 19 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
    wire rst_root_n, run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    (* keep = 1 *) wire rst_n_t0;
    (* keep = 1 *) wire rst_n_t1;
    (* keep = 1 *) wire rst_n_t2;
    (* keep = 1 *) wire rst_n_t3;
    (* keep = 1 *) wire rst_n_t4;
    (* keep = 1 *) wire rst_n_t5;
    (* keep = 1 *) wire rst_n_t6;
    (* keep = 1 *) wire rst_n_t7;
    (* keep = 1 *) wire rst_n_t8;
    (* keep = 1 *) wire rst_n_t9;
    (* keep = 1 *) wire rst_n_t10;
    (* keep = 1 *) wire rst_n_t11;
    (* keep = 1 *) wire rst_n_t12;
    (* keep = 1 *) wire rst_n_t13;
    (* keep = 1 *) wire rst_n_t14;
    (* keep = 1 *) wire rst_n_t15;
    (* keep = 1 *) wire rst_n_t16;
    (* keep = 1 *) wire rst_n_t17;
    (* keep = 1 *) wire rst_n_t18;
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t2 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 2 depth 1 @ (949.9, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 2 depth 1 @ (949.9, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 2 depth 2 @ (949.9, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 2 depth 2 @ (949.9, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw tap tap 2 depth 3 @ (949.9, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run tap tap 2 depth 3 @ (949.9, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 2 depth 4 @ (949.9, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 2 depth 4 @ (949.9, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t2));  // boot pad tap 2 depth 5 @ (949.9, 21.6)
    wire start_t2;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t2));  // gated pad tap 2 depth 5 @ (949.9, 21.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_2), .q(rst_rl_5));  // raw pad tap 1 depth 4 @ (570.7, 21.6)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_5));  // run pad tap 1 depth 4 @ (570.7, 21.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (570.7, 21.6)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_2), .q(rst_rl_7));  // raw wire tap None depth 4 @ (570.2, 21.6)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_7));  // run wire tap None depth 4 @ (570.2, 21.6)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_root_n), .q(rst_n_t0));  // boot tap tap 0 depth 5 @ (190.6, 21.6)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_root_n), .q(rst_rl_9));  // raw tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(run_root), .q(rn_rst_rl_9));  // run tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // raw pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_10), .q(rn_rst_rl_11));  // run pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 3 depth 4 @ (1331.0, 21.6)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 3 depth 4 @ (1331.0, 21.6)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_n_t3));  // boot pad tap 3 depth 5 @ (1331.0, 21.6)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_9), .q(rst_rl_14));  // raw pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_14));  // run pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // raw tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_15));  // run tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 10 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 10 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_15), .q(rst_rl_18));  // raw tap tap 13 depth 4 @ (1872.7, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_18));  // run tap tap 13 depth 4 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_18), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1872.7, 400.0)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_9), .q(rst_rl_21));  // raw tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_21;
    ot_dp_rrelay u_srl_21 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_21));  // run tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // raw pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_22));  // run pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw pad tap 11 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run pad tap 11 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1650.0, 30.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_21), .q(rst_rl_25));  // raw pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_25));  // run pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // raw pad tap 5 depth 4 @ (1874.9, 160.0)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_26));  // run pad tap 5 depth 4 @ (1874.9, 160.0)
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1874.9, 160.0)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_21), .q(rst_rl_28));  // raw tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_28));  // run tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw pad tap 14 depth 4 @ (1872.7, 120.0)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run pad tap 14 depth 4 @ (1872.7, 120.0)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t14));  // boot pad tap 14 depth 5 @ (1872.7, 120.0)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_28), .q(rst_rl_31));  // raw wire tap None depth 4 @ (1872.7, 470.0)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_31));  // run wire tap None depth 4 @ (1872.7, 470.0)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t18));  // boot tap tap 18 depth 5 @ (1872.7, 820.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_21), .q(rst_rl_33));  // raw pad tap None depth 3 @ (1872.7, 183.8)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_33));  // run pad tap None depth 3 @ (1872.7, 183.8)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // raw wire tap None depth 4 @ (1872.7, 183.8)
    wire rn_rst_rl_34;
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(rn_rst_rl_33), .q(rn_rst_rl_34));  // run wire tap None depth 4 @ (1872.7, 183.8)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1872.7, 560.0)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_9), .q(rst_rl_36));  // raw pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_36));  // run pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw pad tap 12 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run pad tap 12 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t12));  // boot tap tap 12 depth 5 @ (1690.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_root_n), .q(rst_rl_40));  // raw pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(run_root), .q(rn_rst_rl_40));  // run pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // raw pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_41), .q(rn_rst_rl_42));  // run pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw pad tap 7 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run pad tap 7 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t7));  // boot tap tap 7 depth 5 @ (1150.0, 30.2)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_root_n), .q(rst_rl_45));  // raw pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(run_root), .q(rn_rst_rl_45));  // run pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // raw pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_46));  // run pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));  // raw pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_47;
    ot_dp_rrelay u_srl_47 (.clk(clk), .d(rn_rst_rl_46), .q(rn_rst_rl_47));  // run pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));  // raw pad tap 8 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_47), .q(rn_rst_rl_48));  // run pad tap 8 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_n_t8));  // boot tap tap 8 depth 5 @ (1300.0, 30.2)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_root_n), .q(rst_rl_50));  // raw pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(run_root), .q(rn_rst_rl_50));  // run pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // raw tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_50), .q(rn_rst_rl_51));  // run tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));  // raw pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_52;
    ot_dp_rrelay u_srl_52 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_52));  // run pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));  // raw pad tap 9 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_52), .q(rn_rst_rl_53));  // run pad tap 9 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1450.0, 30.2)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_51), .q(rst_rl_55));  // raw pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rn_rst_rl_55;
    ot_dp_rrelay u_srl_55 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_55));  // run pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // raw pad tap 4 depth 4 @ (1711.2, 21.6)
    wire rn_rst_rl_56;
    ot_dp_rrelay u_srl_56 (.clk(clk), .d(rn_rst_rl_55), .q(rn_rst_rl_56));  // run pad tap 4 depth 4 @ (1711.2, 21.6)
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1711.2, 21.6)
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_51), .q(rst_rl_58));  // raw pad tap None depth 3 @ (1771.2, 30.2)
    wire rn_rst_rl_58;
    ot_dp_rrelay u_srl_58 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_58));  // run pad tap None depth 3 @ (1771.2, 30.2)
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_rl_59));  // raw wire tap None depth 4 @ (1771.2, 30.2)
    wire rn_rst_rl_59;
    ot_dp_rrelay u_srl_59 (.clk(clk), .d(rn_rst_rl_58), .q(rn_rst_rl_59));  // run wire tap None depth 4 @ (1771.2, 30.2)
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1872.7, 250.0)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_51), .q(rst_rl_61));  // raw wire tap None depth 3 @ (1794.9, 30.2)
    wire rn_rst_rl_61;
    ot_dp_rrelay u_srl_61 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_61));  // run wire tap None depth 3 @ (1794.9, 30.2)
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));  // raw wire tap None depth 4 @ (1874.9, 295.1)
    wire rn_rst_rl_62;
    ot_dp_rrelay u_srl_62 (.clk(clk), .d(rn_rst_rl_61), .q(rn_rst_rl_62));  // run wire tap None depth 4 @ (1874.9, 295.1)
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1874.9, 640.0)
wire local0;ot_dp_rrelay copy0(.clk(clk),.d(rst_rl_7),.q(local0));
wire local1;ot_dp_rrelay copy1(.clk(clk),.d(rst_rl_31),.q(local1));
wire local2;ot_dp_rrelay copy2(.clk(clk),.d(rst_rl_31),.q(local2));
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,rst_n_t18,local0,local1,local2};endmodule
module dut1(input wire clk,arst_n,start_i,output wire[21:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 19 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
    wire rst_root_n, run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    (* keep = 1 *) wire rst_n_t0;
    (* keep = 1 *) wire rst_n_t1;
    (* keep = 1 *) wire rst_n_t2;
    (* keep = 1 *) wire rst_n_t3;
    (* keep = 1 *) wire rst_n_t4;
    (* keep = 1 *) wire rst_n_t5;
    (* keep = 1 *) wire rst_n_t6;
    (* keep = 1 *) wire rst_n_t7;
    (* keep = 1 *) wire rst_n_t8;
    (* keep = 1 *) wire rst_n_t9;
    (* keep = 1 *) wire rst_n_t10;
    (* keep = 1 *) wire rst_n_t11;
    (* keep = 1 *) wire rst_n_t12;
    (* keep = 1 *) wire rst_n_t13;
    (* keep = 1 *) wire rst_n_t14;
    (* keep = 1 *) wire rst_n_t15;
    (* keep = 1 *) wire rst_n_t16;
    (* keep = 1 *) wire rst_n_t17;
    (* keep = 1 *) wire rst_n_t18;
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t2 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 2 depth 1 @ (949.9, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 2 depth 1 @ (949.9, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 2 depth 2 @ (949.9, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 2 depth 2 @ (949.9, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw tap tap 2 depth 3 @ (949.9, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run tap tap 2 depth 3 @ (949.9, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 2 depth 4 @ (949.9, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 2 depth 4 @ (949.9, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t2));  // boot pad tap 2 depth 5 @ (949.9, 21.6)
    wire start_t2;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t2));  // gated pad tap 2 depth 5 @ (949.9, 21.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_2), .q(rst_rl_5));  // raw pad tap 1 depth 4 @ (570.7, 21.6)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_5));  // run pad tap 1 depth 4 @ (570.7, 21.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (570.7, 21.6)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_2), .q(rst_rl_7));  // raw wire tap None depth 4 @ (570.2, 21.6)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_7));  // run wire tap None depth 4 @ (570.2, 21.6)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_n_t0));  // boot tap tap 0 depth 5 @ (190.6, 21.6)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_root_n), .q(rst_rl_9));  // raw tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(run_root), .q(rn_rst_rl_9));  // run tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // raw pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_10), .q(rn_rst_rl_11));  // run pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 3 depth 4 @ (1331.0, 21.6)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 3 depth 4 @ (1331.0, 21.6)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_n_t3));  // boot pad tap 3 depth 5 @ (1331.0, 21.6)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_9), .q(rst_rl_14));  // raw pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_14));  // run pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // raw tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_15));  // run tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 10 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 10 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_15), .q(rst_rl_18));  // raw tap tap 13 depth 4 @ (1872.7, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_18));  // run tap tap 13 depth 4 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_18), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1872.7, 400.0)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_9), .q(rst_rl_21));  // raw tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_21;
    ot_dp_rrelay u_srl_21 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_21));  // run tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // raw pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_22));  // run pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw pad tap 11 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run pad tap 11 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1650.0, 30.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_21), .q(rst_rl_25));  // raw pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_25));  // run pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // raw pad tap 5 depth 4 @ (1874.9, 160.0)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_26));  // run pad tap 5 depth 4 @ (1874.9, 160.0)
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1874.9, 160.0)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_21), .q(rst_rl_28));  // raw tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_28));  // run tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw pad tap 14 depth 4 @ (1872.7, 120.0)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run pad tap 14 depth 4 @ (1872.7, 120.0)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t14));  // boot pad tap 14 depth 5 @ (1872.7, 120.0)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_28), .q(rst_rl_31));  // raw wire tap None depth 4 @ (1872.7, 470.0)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_31));  // run wire tap None depth 4 @ (1872.7, 470.0)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t18));  // boot tap tap 18 depth 5 @ (1872.7, 820.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_21), .q(rst_rl_33));  // raw pad tap None depth 3 @ (1872.7, 183.8)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_33));  // run pad tap None depth 3 @ (1872.7, 183.8)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // raw wire tap None depth 4 @ (1872.7, 183.8)
    wire rn_rst_rl_34;
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(rn_rst_rl_33), .q(rn_rst_rl_34));  // run wire tap None depth 4 @ (1872.7, 183.8)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1872.7, 560.0)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_9), .q(rst_rl_36));  // raw pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_36));  // run pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw pad tap 12 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run pad tap 12 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t12));  // boot tap tap 12 depth 5 @ (1690.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_root_n), .q(rst_rl_40));  // raw pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(run_root), .q(rn_rst_rl_40));  // run pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // raw pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_41), .q(rn_rst_rl_42));  // run pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw pad tap 7 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run pad tap 7 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t7));  // boot tap tap 7 depth 5 @ (1150.0, 30.2)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_root_n), .q(rst_rl_45));  // raw pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(run_root), .q(rn_rst_rl_45));  // run pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // raw pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_46));  // run pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));  // raw pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_47;
    ot_dp_rrelay u_srl_47 (.clk(clk), .d(rn_rst_rl_46), .q(rn_rst_rl_47));  // run pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));  // raw pad tap 8 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_47), .q(rn_rst_rl_48));  // run pad tap 8 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_n_t8));  // boot tap tap 8 depth 5 @ (1300.0, 30.2)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_root_n), .q(rst_rl_50));  // raw pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(run_root), .q(rn_rst_rl_50));  // run pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // raw tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_50), .q(rn_rst_rl_51));  // run tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));  // raw pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_52;
    ot_dp_rrelay u_srl_52 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_52));  // run pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));  // raw pad tap 9 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_52), .q(rn_rst_rl_53));  // run pad tap 9 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1450.0, 30.2)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_51), .q(rst_rl_55));  // raw pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rn_rst_rl_55;
    ot_dp_rrelay u_srl_55 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_55));  // run pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // raw pad tap 4 depth 4 @ (1711.2, 21.6)
    wire rn_rst_rl_56;
    ot_dp_rrelay u_srl_56 (.clk(clk), .d(rn_rst_rl_55), .q(rn_rst_rl_56));  // run pad tap 4 depth 4 @ (1711.2, 21.6)
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1711.2, 21.6)
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_51), .q(rst_rl_58));  // raw pad tap None depth 3 @ (1771.2, 30.2)
    wire rn_rst_rl_58;
    ot_dp_rrelay u_srl_58 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_58));  // run pad tap None depth 3 @ (1771.2, 30.2)
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_rl_59));  // raw wire tap None depth 4 @ (1771.2, 30.2)
    wire rn_rst_rl_59;
    ot_dp_rrelay u_srl_59 (.clk(clk), .d(rn_rst_rl_58), .q(rn_rst_rl_59));  // run wire tap None depth 4 @ (1771.2, 30.2)
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1872.7, 250.0)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_51), .q(rst_rl_61));  // raw wire tap None depth 3 @ (1794.9, 30.2)
    wire rn_rst_rl_61;
    ot_dp_rrelay u_srl_61 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_61));  // run wire tap None depth 3 @ (1794.9, 30.2)
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));  // raw wire tap None depth 4 @ (1874.9, 295.1)
    wire rn_rst_rl_62;
    ot_dp_rrelay u_srl_62 (.clk(clk), .d(rn_rst_rl_61), .q(rn_rst_rl_62));  // run wire tap None depth 4 @ (1874.9, 295.1)
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1874.9, 640.0)
wire local0;ot_dp_rrelay copy0(.clk(clk),.d(rst_rl_7),.q(local0));
wire local1;ot_dp_rrelay copy1(.clk(clk),.d(rst_rl_31),.q(local1));
wire local2;ot_dp_rrelay copy2(.clk(clk),.d(rst_rl_31),.q(local2));
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,rst_n_t18,local0,local1,local2};endmodule
module mut1(input wire clk,arst_n,start_i,output wire[21:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 19 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
    wire rst_root_n, run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    (* keep = 1 *) wire rst_n_t0;
    (* keep = 1 *) wire rst_n_t1;
    (* keep = 1 *) wire rst_n_t2;
    (* keep = 1 *) wire rst_n_t3;
    (* keep = 1 *) wire rst_n_t4;
    (* keep = 1 *) wire rst_n_t5;
    (* keep = 1 *) wire rst_n_t6;
    (* keep = 1 *) wire rst_n_t7;
    (* keep = 1 *) wire rst_n_t8;
    (* keep = 1 *) wire rst_n_t9;
    (* keep = 1 *) wire rst_n_t10;
    (* keep = 1 *) wire rst_n_t11;
    (* keep = 1 *) wire rst_n_t12;
    (* keep = 1 *) wire rst_n_t13;
    (* keep = 1 *) wire rst_n_t14;
    (* keep = 1 *) wire rst_n_t15;
    (* keep = 1 *) wire rst_n_t16;
    (* keep = 1 *) wire rst_n_t17;
    (* keep = 1 *) wire rst_n_t18;
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t2 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 2 depth 1 @ (949.9, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 2 depth 1 @ (949.9, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 2 depth 2 @ (949.9, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 2 depth 2 @ (949.9, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw tap tap 2 depth 3 @ (949.9, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run tap tap 2 depth 3 @ (949.9, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 2 depth 4 @ (949.9, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 2 depth 4 @ (949.9, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t2));  // boot pad tap 2 depth 5 @ (949.9, 21.6)
    wire start_t2;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t2));  // gated pad tap 2 depth 5 @ (949.9, 21.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_2), .q(rst_rl_5));  // raw pad tap 1 depth 4 @ (570.7, 21.6)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_5));  // run pad tap 1 depth 4 @ (570.7, 21.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (570.7, 21.6)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_2), .q(rst_rl_7));  // raw wire tap None depth 4 @ (570.2, 21.6)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_7));  // run wire tap None depth 4 @ (570.2, 21.6)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_root_n), .q(rst_n_t0));  // boot tap tap 0 depth 5 @ (190.6, 21.6)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_root_n), .q(rst_rl_9));  // raw tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(run_root), .q(rn_rst_rl_9));  // run tap tap 3 depth 1 @ (1331.0, 21.6)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 3 depth 2 @ (1331.0, 21.6)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // raw pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_10), .q(rn_rst_rl_11));  // run pad tap 3 depth 3 @ (1331.0, 21.6)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 3 depth 4 @ (1331.0, 21.6)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 3 depth 4 @ (1331.0, 21.6)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_n_t3));  // boot pad tap 3 depth 5 @ (1331.0, 21.6)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_9), .q(rst_rl_14));  // raw pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_14));  // run pad tap 10 depth 2 @ (1550.0, 30.2)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // raw tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_15));  // run tap tap 10 depth 3 @ (1550.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 10 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 10 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_15), .q(rst_rl_18));  // raw tap tap 13 depth 4 @ (1872.7, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_18));  // run tap tap 13 depth 4 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1872.7, 30.2)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_18), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1872.7, 400.0)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_9), .q(rst_rl_21));  // raw tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_21;
    ot_dp_rrelay u_srl_21 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_21));  // run tap tap 11 depth 2 @ (1650.0, 30.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // raw pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_22));  // run pad tap 11 depth 3 @ (1650.0, 30.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw pad tap 11 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run pad tap 11 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1650.0, 30.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_21), .q(rst_rl_25));  // raw pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_25));  // run pad tap 5 depth 3 @ (1874.9, 160.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // raw pad tap 5 depth 4 @ (1874.9, 160.0)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_26));  // run pad tap 5 depth 4 @ (1874.9, 160.0)
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1874.9, 160.0)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_21), .q(rst_rl_28));  // raw tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_28));  // run tap tap 14 depth 3 @ (1872.7, 120.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw pad tap 14 depth 4 @ (1872.7, 120.0)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run pad tap 14 depth 4 @ (1872.7, 120.0)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t14));  // boot pad tap 14 depth 5 @ (1872.7, 120.0)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_28), .q(rst_rl_31));  // raw wire tap None depth 4 @ (1872.7, 470.0)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_31));  // run wire tap None depth 4 @ (1872.7, 470.0)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t18));  // boot tap tap 18 depth 5 @ (1872.7, 820.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_21), .q(rst_rl_33));  // raw pad tap None depth 3 @ (1872.7, 183.8)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_33));  // run pad tap None depth 3 @ (1872.7, 183.8)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // raw wire tap None depth 4 @ (1872.7, 183.8)
    wire rn_rst_rl_34;
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(rn_rst_rl_33), .q(rn_rst_rl_34));  // run wire tap None depth 4 @ (1872.7, 183.8)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1872.7, 560.0)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_9), .q(rst_rl_36));  // raw pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_36));  // run pad tap 12 depth 2 @ (1690.0, 30.2)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 12 depth 3 @ (1690.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw pad tap 12 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run pad tap 12 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t12));  // boot tap tap 12 depth 5 @ (1690.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_root_n), .q(rst_rl_40));  // raw pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(run_root), .q(rn_rst_rl_40));  // run pad tap 7 depth 1 @ (1150.0, 30.2)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 7 depth 2 @ (1150.0, 30.2)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // raw pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_41), .q(rn_rst_rl_42));  // run pad tap 7 depth 3 @ (1150.0, 30.2)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw pad tap 7 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run pad tap 7 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t7));  // boot tap tap 7 depth 5 @ (1150.0, 30.2)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_root_n), .q(rst_rl_45));  // raw pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(run_root), .q(rn_rst_rl_45));  // run pad tap 8 depth 1 @ (1300.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // raw pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_46));  // run pad tap 8 depth 2 @ (1300.0, 30.2)
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));  // raw pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_47;
    ot_dp_rrelay u_srl_47 (.clk(clk), .d(rn_rst_rl_46), .q(rn_rst_rl_47));  // run pad tap 8 depth 3 @ (1300.0, 30.2)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));  // raw pad tap 8 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_47), .q(rn_rst_rl_48));  // run pad tap 8 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_n_t8));  // boot tap tap 8 depth 5 @ (1300.0, 30.2)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_root_n), .q(rst_rl_50));  // raw pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(run_root), .q(rn_rst_rl_50));  // run pad tap 9 depth 1 @ (1450.0, 30.2)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // raw tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_50), .q(rn_rst_rl_51));  // run tap tap 9 depth 2 @ (1450.0, 30.2)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));  // raw pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_52;
    ot_dp_rrelay u_srl_52 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_52));  // run pad tap 9 depth 3 @ (1450.0, 30.2)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));  // raw pad tap 9 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_52), .q(rn_rst_rl_53));  // run pad tap 9 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1450.0, 30.2)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_51), .q(rst_rl_55));  // raw pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rn_rst_rl_55;
    ot_dp_rrelay u_srl_55 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_55));  // run pad tap 4 depth 3 @ (1711.2, 21.6)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // raw pad tap 4 depth 4 @ (1711.2, 21.6)
    wire rn_rst_rl_56;
    ot_dp_rrelay u_srl_56 (.clk(clk), .d(rn_rst_rl_55), .q(rn_rst_rl_56));  // run pad tap 4 depth 4 @ (1711.2, 21.6)
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1711.2, 21.6)
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_51), .q(rst_rl_58));  // raw pad tap None depth 3 @ (1771.2, 30.2)
    wire rn_rst_rl_58;
    ot_dp_rrelay u_srl_58 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_58));  // run pad tap None depth 3 @ (1771.2, 30.2)
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_rl_59));  // raw wire tap None depth 4 @ (1771.2, 30.2)
    wire rn_rst_rl_59;
    ot_dp_rrelay u_srl_59 (.clk(clk), .d(rn_rst_rl_58), .q(rn_rst_rl_59));  // run wire tap None depth 4 @ (1771.2, 30.2)
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1872.7, 250.0)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_51), .q(rst_rl_61));  // raw wire tap None depth 3 @ (1794.9, 30.2)
    wire rn_rst_rl_61;
    ot_dp_rrelay u_srl_61 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_61));  // run wire tap None depth 3 @ (1794.9, 30.2)
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));  // raw wire tap None depth 4 @ (1874.9, 295.1)
    wire rn_rst_rl_62;
    ot_dp_rrelay u_srl_62 (.clk(clk), .d(rn_rst_rl_61), .q(rn_rst_rl_62));  // run wire tap None depth 4 @ (1874.9, 295.1)
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1874.9, 640.0)
wire local0;ot_dp_rrelay copy0(.clk(clk),.d(rst_rl_7),.q(local0));
wire local1;ot_dp_rrelay copy1(.clk(clk),.d(rst_rl_31),.q(local1));
wire local2;ot_dp_rrelay copy2(.clk(clk),.d(rst_rl_31),.q(local2));
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,rst_n_t18,local0,local1,local2};endmodule