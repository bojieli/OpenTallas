    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 4 to all 15 taps, hops <= 405 um; every tap releases 5 clocks after the LATER of the entry reset release and the entry START
    wire rst_root_n, run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t7;
    wire rst_n_t8;
    wire rst_n_t9;
    wire rst_n_t10;
    wire rst_n_t11;
    wire rst_n_t12;
    wire rst_n_t13;
    wire rst_n_t14;
    // START role mission: consumer taps = registered (reset AND run)
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 5 depth 1 @ (570.2, 943.9)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 5 depth 1 @ (570.2, 943.9)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 5 depth 2 @ (570.2, 943.9)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 5 depth 2 @ (570.2, 943.9)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 5 depth 3 @ (570.2, 943.9)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 5 depth 3 @ (570.2, 943.9)
    ot_dp_rgate u_rrl_3 (.clk(clk), .d(rst_rl_2), .run(rn_rst_rl_2), .q(rst_n_t5));  // gated tap tap 5 depth 4 @ (570.2, 943.9)
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_root_n), .q(rst_rl_4));  // raw wire tap None depth 1 @ (384.3, 954.3)
    wire rn_rst_rl_4;
    ot_dp_rrelay u_srl_4 (.clk(clk), .d(run_root), .q(rn_rst_rl_4));  // run wire tap None depth 1 @ (384.3, 954.3)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));  // raw wire tap None depth 2 @ (375.8, 656.1)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_4), .q(rn_rst_rl_5));  // run wire tap None depth 2 @ (375.8, 656.1)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));  // raw wire tap None depth 3 @ (349.9, 341.3)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(rn_rst_rl_5), .q(rn_rst_rl_6));  // run wire tap None depth 3 @ (349.9, 341.3)
    ot_dp_rgate u_rrl_7 (.clk(clk), .d(rst_rl_6), .run(rn_rst_rl_6), .q(rst_n_t0));  // gated tap tap 0 depth 4 @ (190.1, 181.4)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_root_n), .q(rst_rl_8));  // raw wire tap None depth 1 @ (393.1, 937.5)
    wire rn_rst_rl_8;
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(run_root), .q(rn_rst_rl_8));  // run wire tap None depth 1 @ (393.1, 937.5)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // raw wire tap None depth 2 @ (436.3, 612.4)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_8), .q(rn_rst_rl_9));  // run wire tap None depth 2 @ (436.3, 612.4)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 14 depth 3 @ (711.2, 522.7)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 14 depth 3 @ (711.2, 522.7)
    ot_dp_rgate u_rrl_11 (.clk(clk), .d(rst_rl_10), .run(rn_rst_rl_10), .q(rst_n_t14));  // gated tap tap 14 depth 4 @ (711.2, 522.7)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_9), .q(rst_rl_12));  // raw wire tap None depth 3 @ (479.3, 384.3)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_12));  // run wire tap None depth 3 @ (479.3, 384.3)
    ot_dp_rgate u_rrl_13 (.clk(clk), .d(rst_rl_12), .run(rn_rst_rl_12), .q(rst_n_t1));  // gated tap tap 1 depth 4 @ (570.2, 181.4)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_9), .q(rst_rl_14));  // raw wire tap None depth 3 @ (574.3, 384.3)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_14));  // run wire tap None depth 3 @ (574.3, 384.3)
    ot_dp_rgate u_rrl_15 (.clk(clk), .d(rst_rl_14), .run(rn_rst_rl_14), .q(rst_n_t13));  // gated tap tap 13 depth 4 @ (698.2, 203.0)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_root_n), .q(rst_rl_16));  // raw pad tap None depth 1 @ (393.1, 756.0)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(run_root), .q(rn_rst_rl_16));  // run pad tap None depth 1 @ (393.1, 756.0)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // raw wire tap None depth 2 @ (393.1, 756.0)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_16), .q(rn_rst_rl_17));  // run wire tap None depth 2 @ (393.1, 756.0)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // raw wire tap None depth 3 @ (178.4, 656.1)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_18));  // run wire tap None depth 3 @ (178.4, 656.1)
    ot_dp_rgate u_rrl_19 (.clk(clk), .d(rst_rl_18), .run(rn_rst_rl_18), .q(rst_n_t2));  // gated tap tap 2 depth 4 @ (146.9, 544.3)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_17), .q(rst_rl_20));  // raw wire tap None depth 3 @ (384.4, 436.3)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_20));  // run wire tap None depth 3 @ (384.4, 436.3)
    ot_dp_rgate u_rrl_21 (.clk(clk), .d(rst_rl_20), .run(rn_rst_rl_20), .q(rst_n_t11));  // gated tap tap 11 depth 4 @ (499.5, 203.0)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_root_n), .q(rst_rl_22));  // raw pad tap None depth 1 @ (436.3, 750.6)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(run_root), .q(rn_rst_rl_22));  // run pad tap None depth 1 @ (436.3, 750.6)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw pad tap None depth 2 @ (436.3, 750.6)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run pad tap None depth 2 @ (436.3, 750.6)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // raw wire tap None depth 3 @ (436.3, 750.6)
    wire rn_rst_rl_24;
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_24));  // run wire tap None depth 3 @ (436.3, 750.6)
    ot_dp_rgate u_rrl_25 (.clk(clk), .d(rst_rl_24), .run(rn_rst_rl_24), .q(rst_n_t3));  // gated tap tap 3 depth 4 @ (570.2, 544.3)
    ot_dp_rgate u_rrl_26 (.clk(clk), .d(rst_rl_24), .run(rn_rst_rl_24), .q(rst_n_t12));  // gated tap tap 12 depth 4 @ (573.0, 522.7)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_root_n), .q(rst_rl_27));  // raw pad tap None depth 1 @ (384.5, 1032.5)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(run_root), .q(rn_rst_rl_27));  // run pad tap None depth 1 @ (384.5, 1032.5)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // raw pad tap None depth 2 @ (384.5, 1032.5)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_27), .q(rn_rst_rl_28));  // run pad tap None depth 2 @ (384.5, 1032.5)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw wire tap None depth 3 @ (384.5, 1032.5)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run wire tap None depth 3 @ (384.5, 1032.5)
    ot_dp_rgate u_rrl_30 (.clk(clk), .d(rst_rl_29), .run(rn_rst_rl_29), .q(rst_n_t4));  // gated tap tap 4 depth 4 @ (198.7, 881.3)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_root_n), .q(rst_rl_31));  // raw wire tap None depth 1 @ (393.1, 851.0)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(run_root), .q(rn_rst_rl_31));  // run wire tap None depth 1 @ (393.1, 851.0)
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_rl_32));  // raw wire tap None depth 2 @ (280.8, 617.8)
    wire rn_rst_rl_32;
    ot_dp_rrelay u_srl_32 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_32));  // run wire tap None depth 2 @ (280.8, 617.8)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));  // raw wire tap None depth 3 @ (211.7, 341.3)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_32), .q(rn_rst_rl_33));  // run wire tap None depth 3 @ (211.7, 341.3)
    wire rr_t6;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rr_t6));  // raw tap tap 6 depth 4 @ (8.2, 181.4)
    wire rn_rr_t6;
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(rn_rst_rl_33), .q(rn_rr_t6));  // run tap tap 6 depth 4 @ (8.2, 181.4)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_root_n), .q(rst_rl_35));  // raw wire tap None depth 1 @ (390.3, 851.0)
    wire rn_rst_rl_35;
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(run_root), .q(rn_rst_rl_35));  // run wire tap None depth 1 @ (390.3, 851.0)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));  // raw wire tap None depth 2 @ (384.3, 479.3)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_35), .q(rn_rst_rl_36));  // run wire tap None depth 2 @ (384.3, 479.3)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 9 depth 3 @ (300.8, 203.0)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 9 depth 3 @ (300.8, 203.0)
    ot_dp_rgate u_rrl_38 (.clk(clk), .d(rst_rl_37), .run(rn_rst_rl_37), .q(rst_n_t9));  // gated tap tap 9 depth 4 @ (300.8, 203.0)
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_36), .q(rst_rl_39));  // raw wire tap None depth 3 @ (384.3, 289.3)
    wire rn_rst_rl_39;
    ot_dp_rrelay u_srl_39 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_39));  // run wire tap None depth 3 @ (384.3, 289.3)
    ot_dp_rgate u_rrl_40 (.clk(clk), .d(rst_rl_39), .run(rn_rst_rl_39), .q(rst_n_t7));  // gated tap tap 7 depth 4 @ (102.1, 203.0)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_root_n), .q(rst_rl_41));  // raw pad tap None depth 1 @ (108.0, 1070.3)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(run_root), .q(rn_rst_rl_41));  // run pad tap None depth 1 @ (108.0, 1070.3)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // raw wire tap None depth 2 @ (108.0, 1070.3)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_41), .q(rn_rst_rl_42));  // run wire tap None depth 2 @ (108.0, 1070.3)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw wire tap None depth 3 @ (99.3, 764.3)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run wire tap None depth 3 @ (99.3, 764.3)
    ot_dp_rgate u_rrl_44 (.clk(clk), .d(rst_rl_43), .run(rn_rst_rl_43), .q(rst_n_t8));  // gated tap tap 8 depth 4 @ (89.1, 522.7)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_root_n), .q(rst_rl_45));  // raw pad tap None depth 1 @ (384.3, 1049.3)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(run_root), .q(rn_rst_rl_45));  // run pad tap None depth 1 @ (384.3, 1049.3)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // raw wire tap None depth 2 @ (384.3, 1049.3)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_46));  // run wire tap None depth 2 @ (384.3, 1049.3)
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));  // raw wire tap None depth 3 @ (341.3, 750.6)
    wire rn_rst_rl_47;
    ot_dp_rrelay u_srl_47 (.clk(clk), .d(rn_rst_rl_46), .q(rn_rst_rl_47));  // run wire tap None depth 3 @ (341.3, 750.6)
    ot_dp_rgate u_rrl_48 (.clk(clk), .d(rst_rl_47), .run(rn_rst_rl_47), .q(rst_n_t10));  // gated tap tap 10 depth 4 @ (227.4, 522.7)
    assign rst_o_0 = rr_t6;  // registered reset out (wavefront) at (8.2, 181.4)
    assign start_o_0 = rn_rr_t6;  // registered START out beside rst_o_0
