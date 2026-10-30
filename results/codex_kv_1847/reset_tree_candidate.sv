    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 31 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
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
    (* keep = 1 *) wire rst_n_t19;
    (* keep = 1 *) wire rst_n_t20;
    (* keep = 1 *) wire rst_n_t21;
    (* keep = 1 *) wire rst_n_t22;
    (* keep = 1 *) wire rst_n_t23;
    (* keep = 1 *) wire rst_n_t24;
    (* keep = 1 *) wire rst_n_t25;
    (* keep = 1 *) wire rst_n_t26;
    (* keep = 1 *) wire rst_n_t27;
    (* keep = 1 *) wire rst_n_t28;
    (* keep = 1 *) wire rst_n_t29;
    (* keep = 1 *) wire rst_n_t30;
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t20 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw tap tap 3 depth 1 @ (799.2, 17.3)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run tap tap 3 depth 1 @ (799.2, 17.3)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 3 depth 2 @ (799.2, 17.3)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 3 depth 2 @ (799.2, 17.3)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 3 depth 3 @ (799.2, 17.3)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 3 depth 3 @ (799.2, 17.3)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 3 depth 4 @ (799.2, 17.3)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 3 depth 4 @ (799.2, 17.3)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t3));  // boot pad tap 3 depth 5 @ (799.2, 17.3)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_0), .q(rst_rl_5));  // raw pad tap 25 depth 2 @ (769.0, 233.3)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_5));  // run pad tap 25 depth 2 @ (769.0, 233.3)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));  // raw tap tap 25 depth 3 @ (769.0, 233.3)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(rn_rst_rl_5), .q(rn_rst_rl_6));  // run tap tap 25 depth 3 @ (769.0, 233.3)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 25 depth 4 @ (769.0, 233.3)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 25 depth 4 @ (769.0, 233.3)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_n_t25));  // boot pad tap 25 depth 5 @ (769.0, 233.3)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_6), .q(rst_rl_9));  // raw wire tap None depth 4 @ (769.0, 596.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_9));  // run wire tap None depth 4 @ (769.0, 596.2)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_n_t22));  // boot tap tap 22 depth 5 @ (769.0, 959.0)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_6), .q(rst_rl_11));  // raw wire tap None depth 4 @ (397.4, 233.3)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_11));  // run wire tap None depth 4 @ (397.4, 233.3)
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_n_t19));  // boot tap tap 19 depth 5 @ (388.8, 596.2)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_0), .q(rst_rl_13));  // raw wire tap None depth 2 @ (421.2, 17.3)
    wire rn_rst_rl_13;
    ot_dp_rrelay u_srl_13 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_13));  // run wire tap None depth 2 @ (421.2, 17.3)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // raw tap tap 1 depth 3 @ (43.2, 17.3)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_13), .q(rn_rst_rl_14));  // run tap tap 1 depth 3 @ (43.2, 17.3)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // raw pad tap 1 depth 4 @ (43.2, 17.3)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_15));  // run pad tap 1 depth 4 @ (43.2, 17.3)
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_n_t1));  // boot pad tap 1 depth 5 @ (43.2, 17.3)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_14), .q(rst_rl_17));  // raw tap tap 14 depth 4 @ (17.3, 367.2)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_17));  // run tap tap 14 depth 4 @ (17.3, 367.2)
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_n_t14));  // boot pad tap 14 depth 5 @ (17.3, 367.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_17), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (17.3, 734.4)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_14), .q(rst_rl_20));  // raw pad tap 28 depth 4 @ (77.8, 164.2)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_20));  // run pad tap 28 depth 4 @ (77.8, 164.2)
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t28));  // boot tap tap 28 depth 5 @ (77.8, 164.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_0), .q(rst_rl_22));  // raw wire tap None depth 2 @ (430.9, 17.3)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_22));  // run wire tap None depth 2 @ (430.9, 17.3)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw wire tap None depth 3 @ (216.0, 170.6)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run wire tap None depth 3 @ (216.0, 170.6)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // raw wire tap None depth 4 @ (216.0, 538.9)
    wire rn_rst_rl_24;
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_24));  // run wire tap None depth 4 @ (216.0, 538.9)
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_n_t27));  // boot tap tap 27 depth 5 @ (216.0, 907.2)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_root_n), .q(rst_rl_26));  // raw pad tap 4 depth 1 @ (950.4, 21.6)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(run_root), .q(rn_rst_rl_26));  // run pad tap 4 depth 1 @ (950.4, 21.6)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // raw pad tap 4 depth 2 @ (950.4, 21.6)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_26), .q(rn_rst_rl_27));  // run pad tap 4 depth 2 @ (950.4, 21.6)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // raw pad tap 4 depth 3 @ (950.4, 21.6)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_27), .q(rn_rst_rl_28));  // run pad tap 4 depth 3 @ (950.4, 21.6)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw pad tap 4 depth 4 @ (950.4, 21.6)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run pad tap 4 depth 4 @ (950.4, 21.6)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (950.4, 21.6)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_root_n), .q(rst_rl_31));  // raw tap tap 5 depth 1 @ (1328.4, 21.6)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(run_root), .q(rn_rst_rl_31));  // run tap tap 5 depth 1 @ (1328.4, 21.6)
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_rl_32));  // raw pad tap 5 depth 2 @ (1328.4, 21.6)
    wire rn_rst_rl_32;
    ot_dp_rrelay u_srl_32 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_32));  // run pad tap 5 depth 2 @ (1328.4, 21.6)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));  // raw pad tap 5 depth 3 @ (1328.4, 21.6)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_32), .q(rn_rst_rl_33));  // run pad tap 5 depth 3 @ (1328.4, 21.6)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // raw pad tap 5 depth 4 @ (1328.4, 21.6)
    wire rn_rst_rl_34;
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(rn_rst_rl_33), .q(rn_rst_rl_34));  // run pad tap 5 depth 4 @ (1328.4, 21.6)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t5));  // boot pad tap 5 depth 5 @ (1328.4, 21.6)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_31), .q(rst_rl_36));  // raw pad tap 8 depth 2 @ (1468.8, 32.4)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_36));  // run pad tap 8 depth 2 @ (1468.8, 32.4)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 8 depth 3 @ (1468.8, 32.4)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 8 depth 3 @ (1468.8, 32.4)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw pad tap 8 depth 4 @ (1468.8, 32.4)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run pad tap 8 depth 4 @ (1468.8, 32.4)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t8));  // boot tap tap 8 depth 5 @ (1468.8, 32.4)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_31), .q(rst_rl_40));  // raw tap tap 9 depth 2 @ (1620.0, 32.4)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_40));  // run tap tap 9 depth 2 @ (1620.0, 32.4)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 9 depth 3 @ (1620.0, 32.4)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 9 depth 3 @ (1620.0, 32.4)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // raw pad tap 9 depth 4 @ (1620.0, 32.4)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_41), .q(rn_rst_rl_42));  // run pad tap 9 depth 4 @ (1620.0, 32.4)
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1620.0, 32.4)
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_40), .q(rst_rl_44));  // raw pad tap 11 depth 3 @ (1868.4, 43.2)
    wire rn_rst_rl_44;
    ot_dp_rrelay u_srl_44 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_44));  // run pad tap 11 depth 3 @ (1868.4, 43.2)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_rl_45));  // raw pad tap 11 depth 4 @ (1868.4, 43.2)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(rn_rst_rl_44), .q(rn_rst_rl_45));  // run pad tap 11 depth 4 @ (1868.4, 43.2)
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_n_t11));  // boot tap tap 11 depth 5 @ (1868.4, 43.2)
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_40), .q(rst_rl_47));  // raw tap tap 12 depth 3 @ (1879.2, 151.2)
    wire rn_rst_rl_47;
    ot_dp_rrelay u_srl_47 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_47));  // run tap tap 12 depth 3 @ (1879.2, 151.2)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));  // raw pad tap 12 depth 4 @ (1879.2, 151.2)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_47), .q(rn_rst_rl_48));  // run pad tap 12 depth 4 @ (1879.2, 151.2)
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_n_t12));  // boot pad tap 12 depth 5 @ (1879.2, 151.2)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_47), .q(rst_rl_50));  // raw tap tap 0 depth 4 @ (1883.5, 520.0)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(rn_rst_rl_47), .q(rn_rst_rl_50));  // run tap tap 0 depth 4 @ (1883.5, 520.0)
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_n_t0));  // boot pad tap 0 depth 5 @ (1883.5, 520.0)
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_50), .q(rst_n_t18));  // boot tap tap 18 depth 5 @ (1883.5, 864.0)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_40), .q(rst_rl_53));  // raw pad tap None depth 3 @ (1633.0, 368.3)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_53));  // run pad tap None depth 3 @ (1633.0, 368.3)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));  // raw wire tap None depth 4 @ (1633.0, 368.3)
    wire rn_rst_rl_54;
    ot_dp_rrelay u_srl_54 (.clk(clk), .d(rn_rst_rl_53), .q(rn_rst_rl_54));  // run wire tap None depth 4 @ (1633.0, 368.3)
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_n_t21));  // boot tap tap 21 depth 5 @ (1633.0, 717.1)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_31), .q(rst_rl_56));  // raw pad tap None depth 2 @ (1701.0, 21.6)
    wire rn_rst_rl_56;
    ot_dp_rrelay u_srl_56 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_56));  // run pad tap None depth 2 @ (1701.0, 21.6)
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));  // raw pad tap None depth 3 @ (1701.0, 21.6)
    wire rn_rst_rl_57;
    ot_dp_rrelay u_srl_57 (.clk(clk), .d(rn_rst_rl_56), .q(rn_rst_rl_57));  // run pad tap None depth 3 @ (1701.0, 21.6)
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_rl_58));  // raw wire tap None depth 4 @ (1701.0, 21.6)
    wire rn_rst_rl_58;
    ot_dp_rrelay u_srl_58 (.clk(clk), .d(rn_rst_rl_57), .q(rn_rst_rl_58));  // run wire tap None depth 4 @ (1701.0, 21.6)
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_n_t13));  // boot tap tap 13 depth 5 @ (1879.2, 216.0)
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_31), .q(rst_rl_60));  // raw pad tap None depth 2 @ (1702.1, 27.0)
    wire rn_rst_rl_60;
    ot_dp_rrelay u_srl_60 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_60));  // run pad tap None depth 2 @ (1702.1, 27.0)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));  // raw pad tap None depth 3 @ (1702.1, 27.0)
    wire rn_rst_rl_61;
    ot_dp_rrelay u_srl_61 (.clk(clk), .d(rn_rst_rl_60), .q(rn_rst_rl_61));  // run pad tap None depth 3 @ (1702.1, 27.0)
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));  // raw wire tap None depth 4 @ (1702.1, 27.0)
    wire rn_rst_rl_62;
    ot_dp_rrelay u_srl_62 (.clk(clk), .d(rn_rst_rl_61), .q(rn_rst_rl_62));  // run wire tap None depth 4 @ (1702.1, 27.0)
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_n_t24));  // boot tap tap 24 depth 5 @ (1702.1, 406.1)
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_31), .q(rst_rl_64));  // raw pad tap None depth 2 @ (1529.3, 200.2)
    wire rn_rst_rl_64;
    ot_dp_rrelay u_srl_64 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_64));  // run pad tap None depth 2 @ (1529.3, 200.2)
    wire rst_rl_65;
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_rl_65));  // raw wire tap None depth 3 @ (1529.3, 200.2)
    wire rn_rst_rl_65;
    ot_dp_rrelay u_srl_65 (.clk(clk), .d(rn_rst_rl_64), .q(rn_rst_rl_65));  // run wire tap None depth 3 @ (1529.3, 200.2)
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_65), .q(rst_rl_66));  // raw wire tap None depth 4 @ (1529.3, 579.6)
    wire rn_rst_rl_66;
    ot_dp_rrelay u_srl_66 (.clk(clk), .d(rn_rst_rl_65), .q(rn_rst_rl_66));  // run wire tap None depth 4 @ (1529.3, 579.6)
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_n_t26));  // boot tap tap 26 depth 5 @ (1529.3, 959.0)
    wire rst_rl_68;
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_root_n), .q(rst_rl_68));  // raw pad tap None depth 1 @ (1419.5, 8.6)
    wire rn_rst_rl_68;
    ot_dp_rrelay u_srl_68 (.clk(clk), .d(run_root), .q(rn_rst_rl_68));  // run pad tap None depth 1 @ (1419.5, 8.6)
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_68), .q(rst_rl_69));  // raw pad tap None depth 2 @ (1419.5, 8.6)
    wire rn_rst_rl_69;
    ot_dp_rrelay u_srl_69 (.clk(clk), .d(rn_rst_rl_68), .q(rn_rst_rl_69));  // run pad tap None depth 2 @ (1419.5, 8.6)
    wire rst_rl_70;
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_rl_70));  // raw pad tap None depth 3 @ (1419.5, 8.6)
    wire rn_rst_rl_70;
    ot_dp_rrelay u_srl_70 (.clk(clk), .d(rn_rst_rl_69), .q(rn_rst_rl_70));  // run pad tap None depth 3 @ (1419.5, 8.6)
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_70), .q(rst_rl_71));  // raw wire tap None depth 4 @ (1419.5, 8.6)
    wire rn_rst_rl_71;
    ot_dp_rrelay u_srl_71 (.clk(clk), .d(rn_rst_rl_70), .q(rn_rst_rl_71));  // run wire tap None depth 4 @ (1419.5, 8.6)
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1717.2, 21.6)
    wire rst_rl_73;
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_root_n), .q(rst_rl_73));  // raw pad tap None depth 1 @ (1149.1, 282.2)
    wire rn_rst_rl_73;
    ot_dp_rrelay u_srl_73 (.clk(clk), .d(run_root), .q(rn_rst_rl_73));  // run pad tap None depth 1 @ (1149.1, 282.2)
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_73), .q(rst_rl_74));  // raw pad tap None depth 2 @ (1149.1, 282.2)
    wire rn_rst_rl_74;
    ot_dp_rrelay u_srl_74 (.clk(clk), .d(rn_rst_rl_73), .q(rn_rst_rl_74));  // run pad tap None depth 2 @ (1149.1, 282.2)
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_rl_75));  // raw wire tap None depth 3 @ (1149.1, 282.2)
    wire rn_rst_rl_75;
    ot_dp_rrelay u_srl_75 (.clk(clk), .d(rn_rst_rl_74), .q(rn_rst_rl_75));  // run wire tap None depth 3 @ (1149.1, 282.2)
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_rl_76));  // raw tap tap 20 depth 4 @ (1149.1, 596.2)
    wire rn_rst_rl_76;
    ot_dp_rrelay u_srl_76 (.clk(clk), .d(rn_rst_rl_75), .q(rn_rst_rl_76));  // run tap tap 20 depth 4 @ (1149.1, 596.2)
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_n_t20));  // boot pad tap 20 depth 5 @ (1149.1, 596.2)
    wire start_t20;
    ot_dp_rgate u_rrl_77_g (.clk(clk), .d(rst_rl_76), .run(rn_rst_rl_76), .q(start_t20));  // gated pad tap 20 depth 5 @ (1149.1, 596.2)
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_76), .q(rst_n_t30));  // boot tap tap 30 depth 5 @ (1149.1, 734.4)
    wire rst_rl_79;
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_root_n), .q(rst_rl_79));  // raw pad tap None depth 1 @ (1457.3, 8.6)
    wire rn_rst_rl_79;
    ot_dp_rrelay u_srl_79 (.clk(clk), .d(run_root), .q(rn_rst_rl_79));  // run pad tap None depth 1 @ (1457.3, 8.6)
    wire rst_rl_80;
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_79), .q(rst_rl_80));  // raw wire tap None depth 2 @ (1457.3, 8.6)
    wire rn_rst_rl_80;
    ot_dp_rrelay u_srl_80 (.clk(clk), .d(rn_rst_rl_79), .q(rn_rst_rl_80));  // run wire tap None depth 2 @ (1457.3, 8.6)
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_rl_80), .q(rst_rl_81));  // raw tap tap 7 depth 3 @ (1792.8, 21.6)
    wire rn_rst_rl_81;
    ot_dp_rrelay u_srl_81 (.clk(clk), .d(rn_rst_rl_80), .q(rn_rst_rl_81));  // run tap tap 7 depth 3 @ (1792.8, 21.6)
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));  // raw pad tap 7 depth 4 @ (1792.8, 21.6)
    wire rn_rst_rl_82;
    ot_dp_rrelay u_srl_82 (.clk(clk), .d(rn_rst_rl_81), .q(rn_rst_rl_82));  // run pad tap 7 depth 4 @ (1792.8, 21.6)
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_n_t7));  // boot pad tap 7 depth 5 @ (1792.8, 21.6)
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_rl_81), .q(rst_rl_84));  // raw wire tap None depth 4 @ (1883.5, 278.6)
    wire rn_rst_rl_84;
    ot_dp_rrelay u_srl_84 (.clk(clk), .d(rn_rst_rl_81), .q(rn_rst_rl_84));  // run wire tap None depth 4 @ (1883.5, 278.6)
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1883.5, 626.4)
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_81), .q(rst_rl_86));  // raw wire tap None depth 4 @ (1883.5, 300.2)
    wire rn_rst_rl_86;
    ot_dp_rrelay u_srl_86 (.clk(clk), .d(rn_rst_rl_81), .q(rn_rst_rl_86));  // run wire tap None depth 4 @ (1883.5, 300.2)
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1883.5, 669.6)
    wire rst_rl_88;
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_root_n), .q(rst_rl_88));  // raw wire tap None depth 1 @ (755.2, 8.6)
    wire rn_rst_rl_88;
    ot_dp_rrelay u_srl_88 (.clk(clk), .d(run_root), .q(rn_rst_rl_88));  // run wire tap None depth 1 @ (755.2, 8.6)
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_rl_88), .q(rst_rl_89));  // raw tap tap 2 depth 2 @ (410.4, 17.3)
    wire rn_rst_rl_89;
    ot_dp_rrelay u_srl_89 (.clk(clk), .d(rn_rst_rl_88), .q(rn_rst_rl_89));  // run tap tap 2 depth 2 @ (410.4, 17.3)
    wire rst_rl_90;
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_rl_90));  // raw pad tap 2 depth 3 @ (410.4, 17.3)
    wire rn_rst_rl_90;
    ot_dp_rrelay u_srl_90 (.clk(clk), .d(rn_rst_rl_89), .q(rn_rst_rl_90));  // run pad tap 2 depth 3 @ (410.4, 17.3)
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_90), .q(rst_rl_91));  // raw pad tap 2 depth 4 @ (410.4, 17.3)
    wire rn_rst_rl_91;
    ot_dp_rrelay u_srl_91 (.clk(clk), .d(rn_rst_rl_90), .q(rn_rst_rl_91));  // run pad tap 2 depth 4 @ (410.4, 17.3)
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_n_t2));  // boot pad tap 2 depth 5 @ (410.4, 17.3)
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_89), .q(rst_rl_93));  // raw wire tap None depth 3 @ (112.3, 51.8)
    wire rn_rst_rl_93;
    ot_dp_rrelay u_srl_93 (.clk(clk), .d(rn_rst_rl_89), .q(rn_rst_rl_93));  // run wire tap None depth 3 @ (112.3, 51.8)
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));  // raw wire tap None depth 4 @ (112.3, 384.5)
    wire rn_rst_rl_94;
    ot_dp_rrelay u_srl_94 (.clk(clk), .d(rn_rst_rl_93), .q(rn_rst_rl_94));  // run wire tap None depth 4 @ (112.3, 384.5)
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_n_t23));  // boot tap tap 23 depth 5 @ (112.3, 717.1)
    wire rst_rl_96;
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_root_n), .q(rst_rl_96));  // raw pad tap None depth 1 @ (1484.3, 8.6)
    wire rn_rst_rl_96;
    ot_dp_rrelay u_srl_96 (.clk(clk), .d(run_root), .q(rn_rst_rl_96));  // run pad tap None depth 1 @ (1484.3, 8.6)
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_96), .q(rst_rl_97));  // raw wire tap None depth 2 @ (1484.3, 8.6)
    wire rn_rst_rl_97;
    ot_dp_rrelay u_srl_97 (.clk(clk), .d(rn_rst_rl_96), .q(rn_rst_rl_97));  // run wire tap None depth 2 @ (1484.3, 8.6)
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));  // raw tap tap 10 depth 3 @ (1836.0, 32.4)
    wire rn_rst_rl_98;
    ot_dp_rrelay u_srl_98 (.clk(clk), .d(rn_rst_rl_97), .q(rn_rst_rl_98));  // run tap tap 10 depth 3 @ (1836.0, 32.4)
    wire rst_rl_99;
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_rl_99));  // raw pad tap 10 depth 4 @ (1836.0, 32.4)
    wire rn_rst_rl_99;
    ot_dp_rrelay u_srl_99 (.clk(clk), .d(rn_rst_rl_98), .q(rn_rst_rl_99));  // run pad tap 10 depth 4 @ (1836.0, 32.4)
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_99), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1836.0, 32.4)
    wire rst_rl_101;
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_98), .q(rst_rl_101));  // raw wire tap None depth 4 @ (1874.9, 346.7)
    wire rn_rst_rl_101;
    ot_dp_rrelay u_srl_101 (.clk(clk), .d(rn_rst_rl_98), .q(rn_rst_rl_101));  // run wire tap None depth 4 @ (1874.9, 346.7)
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_101), .q(rst_n_t29));  // boot tap tap 29 depth 5 @ (1874.9, 699.8)
