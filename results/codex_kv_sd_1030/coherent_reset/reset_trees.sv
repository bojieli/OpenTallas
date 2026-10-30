module old0(input wire clk,input wire arst_n,input wire start_i,output wire [18:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 18 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
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
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t0 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw tap tap 0 depth 3 @ (1110.0, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run tap tap 0 depth 3 @ (1110.0, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 0 depth 4 @ (1110.0, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 0 depth 4 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t0));  // boot pad tap 0 depth 5 @ (1110.0, 21.6)
    wire start_t0;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t0));  // gated pad tap 0 depth 5 @ (1110.0, 21.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_2), .q(rst_rl_5));  // raw tap tap 1 depth 4 @ (1490.0, 21.6)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_5));  // run tap tap 1 depth 4 @ (1490.0, 21.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t1));  // boot pad tap 1 depth 5 @ (1490.0, 21.6)
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_5), .q(rst_n_t12));  // boot tap tap 12 depth 5 @ (1850.0, 30.2)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_root_n), .q(rst_rl_8));  // raw pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_8;
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(run_root), .q(rn_rst_rl_8));  // run pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // raw pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_8), .q(rn_rst_rl_9));  // run pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // raw pad tap 6 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_10), .q(rn_rst_rl_11));  // run pad tap 6 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1150.0, 30.2)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_root_n), .q(rst_rl_13));  // raw pad tap 7 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_13;
    ot_dp_rrelay u_srl_13 (.clk(clk), .d(run_root), .q(rn_rst_rl_13));  // run pad tap 7 depth 1 @ (1300.0, 30.2)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // raw tap tap 7 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_13), .q(rn_rst_rl_14));  // run tap tap 7 depth 2 @ (1300.0, 30.2)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // raw pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_15));  // run pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 7 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 7 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t7));  // boot pad tap 7 depth 5 @ (1300.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_14), .q(rst_rl_18));  // raw pad tap 9 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_18));  // run pad tap 9 depth 3 @ (1550.0, 30.2)
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));  // raw pad tap 9 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_19;
    ot_dp_rrelay u_srl_19 (.clk(clk), .d(rn_rst_rl_18), .q(rn_rst_rl_19));  // run pad tap 9 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_n_t9));  // boot tap tap 9 depth 5 @ (1550.0, 30.2)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_14), .q(rst_rl_21));  // raw tap tap 10 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_21;
    ot_dp_rrelay u_srl_21 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_21));  // run tap tap 10 depth 3 @ (1650.0, 30.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // raw pad tap 10 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_22));  // run pad tap 10 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1650.0, 30.2)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_21), .q(rst_rl_24));  // raw pad tap 4 depth 4 @ (1892.2, 160.0)
    wire rn_rst_rl_24;
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_24));  // run pad tap 4 depth 4 @ (1892.2, 160.0)
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1892.2, 160.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_21), .q(rst_rl_26));  // raw tap tap 13 depth 4 @ (1892.2, 120.0)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(rn_rst_rl_21), .q(rn_rst_rl_26));  // run tap tap 13 depth 4 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_26), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1892.2, 400.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_root_n), .q(rst_rl_29));  // raw tap tap 8 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(run_root), .q(rn_rst_rl_29));  // run tap tap 8 depth 1 @ (1450.0, 30.2)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));  // raw pad tap 8 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_30;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_29), .q(rn_rst_rl_30));  // run pad tap 8 depth 2 @ (1450.0, 30.2)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));  // raw pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_31));  // run pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_rl_32));  // raw pad tap 8 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_32;
    ot_dp_rrelay u_srl_32 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_32));  // run pad tap 8 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_n_t8));  // boot pad tap 8 depth 5 @ (1450.0, 30.2)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_29), .q(rst_rl_34));  // raw pad tap 2 depth 2 @ (1690.0, 21.6)
    wire rn_rst_rl_34;
    ot_dp_rrelay u_srl_34 (.clk(clk), .d(rn_rst_rl_29), .q(rn_rst_rl_34));  // run pad tap 2 depth 2 @ (1690.0, 21.6)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_rl_35));  // raw pad tap 2 depth 3 @ (1690.0, 21.6)
    wire rn_rst_rl_35;
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(rn_rst_rl_34), .q(rn_rst_rl_35));  // run pad tap 2 depth 3 @ (1690.0, 21.6)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));  // raw pad tap 2 depth 4 @ (1690.0, 21.6)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_35), .q(rn_rst_rl_36));  // run pad tap 2 depth 4 @ (1690.0, 21.6)
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_n_t2));  // boot tap tap 2 depth 5 @ (1690.0, 21.6)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_29), .q(rst_rl_38));  // raw tap tap 11 depth 2 @ (1750.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_29), .q(rn_rst_rl_38));  // run tap tap 11 depth 2 @ (1750.0, 30.2)
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_rl_39));  // raw pad tap 11 depth 3 @ (1750.0, 30.2)
    wire rn_rst_rl_39;
    ot_dp_rrelay u_srl_39 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_39));  // run pad tap 11 depth 3 @ (1750.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));  // raw pad tap 11 depth 4 @ (1750.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_39), .q(rn_rst_rl_40));  // run pad tap 11 depth 4 @ (1750.0, 30.2)
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1750.0, 30.2)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_38), .q(rst_rl_42));  // raw tap tap 14 depth 3 @ (1892.2, 250.0)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_42));  // run tap tap 14 depth 3 @ (1892.2, 250.0)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw pad tap 14 depth 4 @ (1892.2, 250.0)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run pad tap 14 depth 4 @ (1892.2, 250.0)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t14));  // boot pad tap 14 depth 5 @ (1892.2, 250.0)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_42), .q(rst_rl_45));  // raw tap tap 16 depth 4 @ (1892.2, 560.0)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_45));  // run tap tap 16 depth 4 @ (1892.2, 560.0)
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_n_t16));  // boot pad tap 16 depth 5 @ (1892.2, 560.0)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_45), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1892.2, 820.0)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_38), .q(rst_rl_48));  // raw pad tap None depth 3 @ (1892.2, 264.0)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_48));  // run pad tap None depth 3 @ (1892.2, 264.0)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));  // raw wire tap None depth 4 @ (1892.2, 264.0)
    wire rn_rst_rl_49;
    ot_dp_rrelay u_srl_49 (.clk(clk), .d(rn_rst_rl_48), .q(rn_rst_rl_49));  // run wire tap None depth 4 @ (1892.2, 264.0)
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1892.2, 640.0)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_root_n), .q(rst_rl_51));  // raw pad tap None depth 1 @ (1488.4, 8.6)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(run_root), .q(rn_rst_rl_51));  // run pad tap None depth 1 @ (1488.4, 8.6)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));  // raw pad tap None depth 2 @ (1488.4, 8.6)
    wire rn_rst_rl_52;
    ot_dp_rrelay u_srl_52 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_52));  // run pad tap None depth 2 @ (1488.4, 8.6)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));  // raw pad tap None depth 3 @ (1488.4, 8.6)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_52), .q(rn_rst_rl_53));  // run pad tap None depth 3 @ (1488.4, 8.6)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));  // raw wire tap None depth 4 @ (1488.4, 8.6)
    wire rn_rst_rl_54;
    ot_dp_rrelay u_srl_54 (.clk(clk), .d(rn_rst_rl_53), .q(rn_rst_rl_54));  // run wire tap None depth 4 @ (1488.4, 8.6)
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_n_t3));  // boot tap tap 3 depth 5 @ (1855.0, 21.6)
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,start_t0};
endmodule
module new0(input wire clk,input wire arst_n,input wire start_i,output wire [18:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 18 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
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
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t0 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw tap tap 0 depth 4 @ (1110.0, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run tap tap 0 depth 4 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t0));  // boot pad tap 0 depth 5 @ (1110.0, 21.6)
    wire start_t0;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t0));  // gated pad tap 0 depth 5 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_3), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (1490.0, 21.6)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_root_n), .q(rst_rl_6));  // raw pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(run_root), .q(rn_rst_rl_6));  // run pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // raw pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_8;
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(rn_rst_rl_7), .q(rn_rst_rl_8));  // run pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // raw pad tap 6 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_8), .q(rn_rst_rl_9));  // run pad tap 6 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1150.0, 30.2)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_root_n), .q(rst_rl_11));  // raw tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(run_root), .q(rn_rst_rl_11));  // run tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));  // raw pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_13;
    ot_dp_rrelay u_srl_13 (.clk(clk), .d(rn_rst_rl_12), .q(rn_rst_rl_13));  // run pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // raw pad tap 7 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_13), .q(rn_rst_rl_14));  // run pad tap 7 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t7));  // boot pad tap 7 depth 5 @ (1300.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_11), .q(rst_rl_16));  // raw pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_16));  // run pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // raw tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_16), .q(rn_rst_rl_17));  // run tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // raw pad tap 9 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_18));  // run pad tap 9 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1550.0, 30.2)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_17), .q(rst_rl_20));  // raw tap tap 12 depth 4 @ (1892.2, 30.2)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_20));  // run tap tap 12 depth 4 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t12));  // boot pad tap 12 depth 5 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_20), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1892.2, 400.0)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_11), .q(rst_rl_23));  // raw tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_23));  // run tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // raw pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_24;
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_24));  // run pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));  // raw pad tap 10 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_24), .q(rn_rst_rl_25));  // run pad tap 10 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1650.0, 30.2)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_23), .q(rst_rl_27));  // raw pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_27));  // run pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // raw pad tap 4 depth 4 @ (1892.2, 160.0)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_27), .q(rn_rst_rl_28));  // run pad tap 4 depth 4 @ (1892.2, 160.0)
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1892.2, 160.0)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_23), .q(rst_rl_30));  // raw tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rn_rst_rl_30;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_30));  // run tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));  // raw pad tap 13 depth 4 @ (1892.2, 120.0)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_31));  // run pad tap 13 depth 4 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1892.2, 120.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_30), .q(rst_rl_33));  // raw wire tap None depth 4 @ (1892.2, 470.0)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_33));  // run wire tap None depth 4 @ (1892.2, 470.0)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1892.2, 820.0)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_root_n), .q(rst_rl_35));  // raw pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_35;
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(run_root), .q(rn_rst_rl_35));  // run pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));  // raw tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_35), .q(rn_rst_rl_36));  // run tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw pad tap 8 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run pad tap 8 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t8));  // boot pad tap 8 depth 5 @ (1450.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_36), .q(rst_rl_40));  // raw pad tap 2 depth 3 @ (1690.0, 21.6)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_40));  // run pad tap 2 depth 3 @ (1690.0, 21.6)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 2 depth 4 @ (1690.0, 21.6)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 2 depth 4 @ (1690.0, 21.6)
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_n_t2));  // boot tap tap 2 depth 5 @ (1690.0, 21.6)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_36), .q(rst_rl_43));  // raw tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_43));  // run tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));  // raw pad tap 11 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_44;
    ot_dp_rrelay u_srl_44 (.clk(clk), .d(rn_rst_rl_43), .q(rn_rst_rl_44));  // run pad tap 11 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1690.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_43), .q(rst_rl_46));  // raw wire tap None depth 4 @ (1892.2, 194.0)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_43), .q(rn_rst_rl_46));  // run wire tap None depth 4 @ (1892.2, 194.0)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1892.2, 560.0)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_36), .q(rst_rl_48));  // raw pad tap None depth 3 @ (1781.0, 30.2)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_48));  // run pad tap None depth 3 @ (1781.0, 30.2)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));  // raw wire tap None depth 4 @ (1781.0, 30.2)
    wire rn_rst_rl_49;
    ot_dp_rrelay u_srl_49 (.clk(clk), .d(rn_rst_rl_48), .q(rn_rst_rl_49));  // run wire tap None depth 4 @ (1781.0, 30.2)
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_n_t14));  // boot tap tap 14 depth 5 @ (1892.2, 250.0)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_36), .q(rst_rl_51));  // raw wire tap None depth 3 @ (1800.6, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_51));  // run wire tap None depth 3 @ (1800.6, 30.2)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));  // raw wire tap None depth 4 @ (1892.2, 289.4)
    wire rn_rst_rl_52;
    ot_dp_rrelay u_srl_52 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_52));  // run wire tap None depth 4 @ (1892.2, 289.4)
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1892.2, 640.0)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_root_n), .q(rst_rl_54));  // raw pad tap None depth 1 @ (1488.4, 8.6)
    wire rn_rst_rl_54;
    ot_dp_rrelay u_srl_54 (.clk(clk), .d(run_root), .q(rn_rst_rl_54));  // run pad tap None depth 1 @ (1488.4, 8.6)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));  // raw pad tap None depth 2 @ (1488.4, 8.6)
    wire rn_rst_rl_55;
    ot_dp_rrelay u_srl_55 (.clk(clk), .d(rn_rst_rl_54), .q(rn_rst_rl_55));  // run pad tap None depth 2 @ (1488.4, 8.6)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // raw pad tap None depth 3 @ (1488.4, 8.6)
    wire rn_rst_rl_56;
    ot_dp_rrelay u_srl_56 (.clk(clk), .d(rn_rst_rl_55), .q(rn_rst_rl_56));  // run pad tap None depth 3 @ (1488.4, 8.6)
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));  // raw wire tap None depth 4 @ (1488.4, 8.6)
    wire rn_rst_rl_57;
    ot_dp_rrelay u_srl_57 (.clk(clk), .d(rn_rst_rl_56), .q(rn_rst_rl_57));  // run wire tap None depth 4 @ (1488.4, 8.6)
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_n_t3));  // boot tap tap 3 depth 5 @ (1855.0, 21.6)
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,start_t0};
endmodule
module mut0(input wire clk,input wire arst_n,input wire start_i,output wire [18:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 18 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
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
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t0 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw tap tap 0 depth 4 @ (1110.0, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run tap tap 0 depth 4 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_root_n), .q(rst_n_t0));  // boot pad tap 0 depth 5 @ (1110.0, 21.6)
    wire start_t0;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_root_n), .run(run_root), .q(start_t0));  // gated pad tap 0 depth 5 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_3), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (1490.0, 21.6)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_root_n), .q(rst_rl_6));  // raw pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(run_root), .q(rn_rst_rl_6));  // run pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // raw pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_8;
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(rn_rst_rl_7), .q(rn_rst_rl_8));  // run pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // raw pad tap 6 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_8), .q(rn_rst_rl_9));  // run pad tap 6 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1150.0, 30.2)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_root_n), .q(rst_rl_11));  // raw tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(run_root), .q(rn_rst_rl_11));  // run tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));  // raw pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_13;
    ot_dp_rrelay u_srl_13 (.clk(clk), .d(rn_rst_rl_12), .q(rn_rst_rl_13));  // run pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // raw pad tap 7 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_13), .q(rn_rst_rl_14));  // run pad tap 7 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t7));  // boot pad tap 7 depth 5 @ (1300.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_11), .q(rst_rl_16));  // raw pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_16));  // run pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // raw tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_16), .q(rn_rst_rl_17));  // run tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // raw pad tap 9 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_18));  // run pad tap 9 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1550.0, 30.2)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_17), .q(rst_rl_20));  // raw tap tap 12 depth 4 @ (1892.2, 30.2)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_20));  // run tap tap 12 depth 4 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t12));  // boot pad tap 12 depth 5 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_20), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1892.2, 400.0)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_11), .q(rst_rl_23));  // raw tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_23));  // run tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // raw pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_24;
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_24));  // run pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));  // raw pad tap 10 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_24), .q(rn_rst_rl_25));  // run pad tap 10 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1650.0, 30.2)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_23), .q(rst_rl_27));  // raw pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_27));  // run pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // raw pad tap 4 depth 4 @ (1892.2, 160.0)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_27), .q(rn_rst_rl_28));  // run pad tap 4 depth 4 @ (1892.2, 160.0)
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1892.2, 160.0)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_23), .q(rst_rl_30));  // raw tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rn_rst_rl_30;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_30));  // run tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));  // raw pad tap 13 depth 4 @ (1892.2, 120.0)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_31));  // run pad tap 13 depth 4 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1892.2, 120.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_30), .q(rst_rl_33));  // raw wire tap None depth 4 @ (1892.2, 470.0)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_33));  // run wire tap None depth 4 @ (1892.2, 470.0)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1892.2, 820.0)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_root_n), .q(rst_rl_35));  // raw pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_35;
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(run_root), .q(rn_rst_rl_35));  // run pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));  // raw tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_35), .q(rn_rst_rl_36));  // run tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw pad tap 8 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run pad tap 8 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t8));  // boot pad tap 8 depth 5 @ (1450.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_36), .q(rst_rl_40));  // raw pad tap 2 depth 3 @ (1690.0, 21.6)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_40));  // run pad tap 2 depth 3 @ (1690.0, 21.6)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 2 depth 4 @ (1690.0, 21.6)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 2 depth 4 @ (1690.0, 21.6)
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_n_t2));  // boot tap tap 2 depth 5 @ (1690.0, 21.6)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_36), .q(rst_rl_43));  // raw tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_43));  // run tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));  // raw pad tap 11 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_44;
    ot_dp_rrelay u_srl_44 (.clk(clk), .d(rn_rst_rl_43), .q(rn_rst_rl_44));  // run pad tap 11 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1690.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_43), .q(rst_rl_46));  // raw wire tap None depth 4 @ (1892.2, 194.0)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_43), .q(rn_rst_rl_46));  // run wire tap None depth 4 @ (1892.2, 194.0)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1892.2, 560.0)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_36), .q(rst_rl_48));  // raw pad tap None depth 3 @ (1781.0, 30.2)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_48));  // run pad tap None depth 3 @ (1781.0, 30.2)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));  // raw wire tap None depth 4 @ (1781.0, 30.2)
    wire rn_rst_rl_49;
    ot_dp_rrelay u_srl_49 (.clk(clk), .d(rn_rst_rl_48), .q(rn_rst_rl_49));  // run wire tap None depth 4 @ (1781.0, 30.2)
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_n_t14));  // boot tap tap 14 depth 5 @ (1892.2, 250.0)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_36), .q(rst_rl_51));  // raw wire tap None depth 3 @ (1800.6, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_51));  // run wire tap None depth 3 @ (1800.6, 30.2)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));  // raw wire tap None depth 4 @ (1892.2, 289.4)
    wire rn_rst_rl_52;
    ot_dp_rrelay u_srl_52 (.clk(clk), .d(rn_rst_rl_51), .q(rn_rst_rl_52));  // run wire tap None depth 4 @ (1892.2, 289.4)
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1892.2, 640.0)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_root_n), .q(rst_rl_54));  // raw pad tap None depth 1 @ (1488.4, 8.6)
    wire rn_rst_rl_54;
    ot_dp_rrelay u_srl_54 (.clk(clk), .d(run_root), .q(rn_rst_rl_54));  // run pad tap None depth 1 @ (1488.4, 8.6)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));  // raw pad tap None depth 2 @ (1488.4, 8.6)
    wire rn_rst_rl_55;
    ot_dp_rrelay u_srl_55 (.clk(clk), .d(rn_rst_rl_54), .q(rn_rst_rl_55));  // run pad tap None depth 2 @ (1488.4, 8.6)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // raw pad tap None depth 3 @ (1488.4, 8.6)
    wire rn_rst_rl_56;
    ot_dp_rrelay u_srl_56 (.clk(clk), .d(rn_rst_rl_55), .q(rn_rst_rl_56));  // run pad tap None depth 3 @ (1488.4, 8.6)
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));  // raw wire tap None depth 4 @ (1488.4, 8.6)
    wire rn_rst_rl_57;
    ot_dp_rrelay u_srl_57 (.clk(clk), .d(rn_rst_rl_56), .q(rn_rst_rl_57));  // run wire tap None depth 4 @ (1488.4, 8.6)
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_n_t3));  // boot tap tap 3 depth 5 @ (1855.0, 21.6)
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,start_t0};
endmodule
module old1(input wire clk,input wire arst_n,input wire start_i,output wire [18:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 18 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
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
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t0 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw tap tap 0 depth 3 @ (1110.0, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run tap tap 0 depth 3 @ (1110.0, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 0 depth 4 @ (1110.0, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 0 depth 4 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t0));  // boot pad tap 0 depth 5 @ (1110.0, 21.6)
    wire start_t0;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t0));  // gated pad tap 0 depth 5 @ (1110.0, 21.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_2), .q(rst_rl_5));  // raw tap tap 1 depth 4 @ (1490.0, 21.6)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_5));  // run tap tap 1 depth 4 @ (1490.0, 21.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t1));  // boot pad tap 1 depth 5 @ (1490.0, 21.6)
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_5), .q(rst_n_t12));  // boot tap tap 12 depth 5 @ (1850.0, 30.2)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_root_n), .q(rst_rl_8));  // raw pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_8;
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(run_root), .q(rn_rst_rl_8));  // run pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // raw pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_8), .q(rn_rst_rl_9));  // run pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // raw pad tap 6 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(rn_rst_rl_10), .q(rn_rst_rl_11));  // run pad tap 6 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1150.0, 30.2)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_root_n), .q(rst_rl_13));  // raw pad tap 7 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_13;
    ot_dp_rrelay u_srl_13 (.clk(clk), .d(run_root), .q(rn_rst_rl_13));  // run pad tap 7 depth 1 @ (1300.0, 30.2)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // raw tap tap 7 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_13), .q(rn_rst_rl_14));  // run tap tap 7 depth 2 @ (1300.0, 30.2)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // raw pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_15));  // run pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 7 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 7 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t7));  // boot pad tap 7 depth 5 @ (1300.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_14), .q(rst_rl_18));  // raw pad tap 9 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_18));  // run pad tap 9 depth 3 @ (1550.0, 30.2)
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));  // raw tap tap 9 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_19;
    ot_dp_rrelay u_srl_19 (.clk(clk), .d(rn_rst_rl_18), .q(rn_rst_rl_19));  // run tap tap 9 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_19), .q(rst_n_t3));  // boot tap tap 3 depth 5 @ (1872.0, 21.6)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_14), .q(rst_rl_22));  // raw tap tap 10 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_14), .q(rn_rst_rl_22));  // run tap tap 10 depth 3 @ (1650.0, 30.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // raw pad tap 10 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_23));  // run pad tap 10 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1650.0, 30.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_22), .q(rst_rl_25));  // raw pad tap 4 depth 4 @ (1892.2, 160.0)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_25));  // run pad tap 4 depth 4 @ (1892.2, 160.0)
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1892.2, 160.0)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_22), .q(rst_rl_27));  // raw tap tap 13 depth 4 @ (1892.2, 120.0)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_22), .q(rn_rst_rl_27));  // run tap tap 13 depth 4 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_27), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1892.2, 400.0)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_root_n), .q(rst_rl_30));  // raw tap tap 8 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_30;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(run_root), .q(rn_rst_rl_30));  // run tap tap 8 depth 1 @ (1450.0, 30.2)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));  // raw pad tap 8 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_31;
    ot_dp_rrelay u_srl_31 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_31));  // run pad tap 8 depth 2 @ (1450.0, 30.2)
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_rl_32));  // raw pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_32;
    ot_dp_rrelay u_srl_32 (.clk(clk), .d(rn_rst_rl_31), .q(rn_rst_rl_32));  // run pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));  // raw pad tap 8 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_32), .q(rn_rst_rl_33));  // run pad tap 8 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_n_t8));  // boot pad tap 8 depth 5 @ (1450.0, 30.2)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_30), .q(rst_rl_35));  // raw pad tap 2 depth 2 @ (1730.0, 21.6)
    wire rn_rst_rl_35;
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_35));  // run pad tap 2 depth 2 @ (1730.0, 21.6)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));  // raw pad tap 2 depth 3 @ (1730.0, 21.6)
    wire rn_rst_rl_36;
    ot_dp_rrelay u_srl_36 (.clk(clk), .d(rn_rst_rl_35), .q(rn_rst_rl_36));  // run pad tap 2 depth 3 @ (1730.0, 21.6)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));  // raw pad tap 2 depth 4 @ (1730.0, 21.6)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(rn_rst_rl_36), .q(rn_rst_rl_37));  // run pad tap 2 depth 4 @ (1730.0, 21.6)
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_n_t2));  // boot tap tap 2 depth 5 @ (1730.0, 21.6)
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_30), .q(rst_rl_39));  // raw tap tap 11 depth 2 @ (1750.0, 30.2)
    wire rn_rst_rl_39;
    ot_dp_rrelay u_srl_39 (.clk(clk), .d(rn_rst_rl_30), .q(rn_rst_rl_39));  // run tap tap 11 depth 2 @ (1750.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));  // raw pad tap 11 depth 3 @ (1750.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_39), .q(rn_rst_rl_40));  // run pad tap 11 depth 3 @ (1750.0, 30.2)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // raw pad tap 11 depth 4 @ (1750.0, 30.2)
    wire rn_rst_rl_41;
    ot_dp_rrelay u_srl_41 (.clk(clk), .d(rn_rst_rl_40), .q(rn_rst_rl_41));  // run pad tap 11 depth 4 @ (1750.0, 30.2)
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1750.0, 30.2)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_39), .q(rst_rl_43));  // raw tap tap 14 depth 3 @ (1892.2, 250.0)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_39), .q(rn_rst_rl_43));  // run tap tap 14 depth 3 @ (1892.2, 250.0)
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));  // raw pad tap 14 depth 4 @ (1892.2, 250.0)
    wire rn_rst_rl_44;
    ot_dp_rrelay u_srl_44 (.clk(clk), .d(rn_rst_rl_43), .q(rn_rst_rl_44));  // run pad tap 14 depth 4 @ (1892.2, 250.0)
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_n_t14));  // boot pad tap 14 depth 5 @ (1892.2, 250.0)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_43), .q(rst_rl_46));  // raw tap tap 16 depth 4 @ (1892.2, 560.0)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_43), .q(rn_rst_rl_46));  // run tap tap 16 depth 4 @ (1892.2, 560.0)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_n_t16));  // boot pad tap 16 depth 5 @ (1892.2, 560.0)
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_46), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1892.2, 820.0)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_39), .q(rst_rl_49));  // raw pad tap None depth 3 @ (1892.2, 264.0)
    wire rn_rst_rl_49;
    ot_dp_rrelay u_srl_49 (.clk(clk), .d(rn_rst_rl_39), .q(rn_rst_rl_49));  // run pad tap None depth 3 @ (1892.2, 264.0)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));  // raw wire tap None depth 4 @ (1892.2, 264.0)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(rn_rst_rl_49), .q(rn_rst_rl_50));  // run wire tap None depth 4 @ (1892.2, 264.0)
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1892.2, 640.0)
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,start_t0};
endmodule
module new1(input wire clk,input wire arst_n,input wire start_i,output wire [18:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 18 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
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
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t0 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw tap tap 0 depth 4 @ (1110.0, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run tap tap 0 depth 4 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t0));  // boot pad tap 0 depth 5 @ (1110.0, 21.6)
    wire start_t0;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(start_t0));  // gated pad tap 0 depth 5 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_3), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (1490.0, 21.6)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_root_n), .q(rst_rl_6));  // raw pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(run_root), .q(rn_rst_rl_6));  // run pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // raw pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_8;
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(rn_rst_rl_7), .q(rn_rst_rl_8));  // run pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // raw pad tap 6 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_8), .q(rn_rst_rl_9));  // run pad tap 6 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1150.0, 30.2)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_root_n), .q(rst_rl_11));  // raw tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(run_root), .q(rn_rst_rl_11));  // run tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));  // raw pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_13;
    ot_dp_rrelay u_srl_13 (.clk(clk), .d(rn_rst_rl_12), .q(rn_rst_rl_13));  // run pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // raw pad tap 7 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_13), .q(rn_rst_rl_14));  // run pad tap 7 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t7));  // boot pad tap 7 depth 5 @ (1300.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_11), .q(rst_rl_16));  // raw pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_16));  // run pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // raw tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_16), .q(rn_rst_rl_17));  // run tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // raw pad tap 9 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_18));  // run pad tap 9 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1550.0, 30.2)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_17), .q(rst_rl_20));  // raw pad tap 3 depth 4 @ (1872.0, 21.6)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_20));  // run pad tap 3 depth 4 @ (1872.0, 21.6)
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t3));  // boot tap tap 3 depth 5 @ (1872.0, 21.6)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_17), .q(rst_rl_22));  // raw tap tap 12 depth 4 @ (1892.2, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_22));  // run tap tap 12 depth 4 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_n_t12));  // boot pad tap 12 depth 5 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_22), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1892.2, 400.0)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_11), .q(rst_rl_25));  // raw tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_25));  // run tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // raw pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_26));  // run pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // raw pad tap 10 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_26), .q(rn_rst_rl_27));  // run pad tap 10 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1650.0, 30.2)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_25), .q(rst_rl_29));  // raw pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_29));  // run pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));  // raw pad tap 4 depth 4 @ (1892.2, 160.0)
    wire rn_rst_rl_30;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_29), .q(rn_rst_rl_30));  // run pad tap 4 depth 4 @ (1892.2, 160.0)
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1892.2, 160.0)
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_25), .q(rst_rl_32));  // raw tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rn_rst_rl_32;
    ot_dp_rrelay u_srl_32 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_32));  // run tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));  // raw pad tap 13 depth 4 @ (1892.2, 120.0)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_32), .q(rn_rst_rl_33));  // run pad tap 13 depth 4 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1892.2, 120.0)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_32), .q(rst_rl_35));  // raw wire tap None depth 4 @ (1892.2, 470.0)
    wire rn_rst_rl_35;
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(rn_rst_rl_32), .q(rn_rst_rl_35));  // run wire tap None depth 4 @ (1892.2, 470.0)
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1892.2, 820.0)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_root_n), .q(rst_rl_37));  // raw pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(run_root), .q(rn_rst_rl_37));  // run pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_rl_39));  // raw pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_39;
    ot_dp_rrelay u_srl_39 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_39));  // run pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));  // raw pad tap 8 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_39), .q(rn_rst_rl_40));  // run pad tap 8 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_n_t8));  // boot pad tap 8 depth 5 @ (1450.0, 30.2)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_38), .q(rst_rl_42));  // raw pad tap 2 depth 3 @ (1730.0, 21.6)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_42));  // run pad tap 2 depth 3 @ (1730.0, 21.6)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw pad tap 2 depth 4 @ (1730.0, 21.6)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run pad tap 2 depth 4 @ (1730.0, 21.6)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t2));  // boot tap tap 2 depth 5 @ (1730.0, 21.6)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_38), .q(rst_rl_45));  // raw tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_45));  // run tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // raw pad tap 11 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_46));  // run pad tap 11 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1690.0, 30.2)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_45), .q(rst_rl_48));  // raw wire tap None depth 4 @ (1892.2, 194.0)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_48));  // run wire tap None depth 4 @ (1892.2, 194.0)
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1892.2, 560.0)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_38), .q(rst_rl_50));  // raw pad tap None depth 3 @ (1781.0, 30.2)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_50));  // run pad tap None depth 3 @ (1781.0, 30.2)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // raw wire tap None depth 4 @ (1781.0, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_50), .q(rn_rst_rl_51));  // run wire tap None depth 4 @ (1781.0, 30.2)
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_n_t14));  // boot tap tap 14 depth 5 @ (1892.2, 250.0)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_38), .q(rst_rl_53));  // raw wire tap None depth 3 @ (1800.6, 30.2)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_53));  // run wire tap None depth 3 @ (1800.6, 30.2)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));  // raw wire tap None depth 4 @ (1892.2, 289.4)
    wire rn_rst_rl_54;
    ot_dp_rrelay u_srl_54 (.clk(clk), .d(rn_rst_rl_53), .q(rn_rst_rl_54));  // run wire tap None depth 4 @ (1892.2, 289.4)
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1892.2, 640.0)
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,start_t0};
endmodule
module mut1(input wire clk,input wire arst_n,input wire start_i,output wire [18:0] o);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 18 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
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
    // START role bootstrap: consumer taps = registered RAW wavefront reset (boot before START); start_t0 = the local registered START tap (reset AND run) for the declared mission-admission input
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run pad tap 0 depth 1 @ (1110.0, 21.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (1110.0, 21.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 0 depth 3 @ (1110.0, 21.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw tap tap 0 depth 4 @ (1110.0, 21.6)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run tap tap 0 depth 4 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_root_n), .q(rst_n_t0));  // boot pad tap 0 depth 5 @ (1110.0, 21.6)
    wire start_t0;
    ot_dp_rgate u_rrl_4_g (.clk(clk), .d(rst_root_n), .run(run_root), .q(start_t0));  // gated pad tap 0 depth 5 @ (1110.0, 21.6)
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_3), .q(rst_n_t1));  // boot tap tap 1 depth 5 @ (1490.0, 21.6)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_root_n), .q(rst_rl_6));  // raw pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(run_root), .q(rn_rst_rl_6));  // run pad tap 6 depth 1 @ (1150.0, 30.2)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 6 depth 2 @ (1150.0, 30.2)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // raw pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rn_rst_rl_8;
    ot_dp_rrelay u_srl_8 (.clk(clk), .d(rn_rst_rl_7), .q(rn_rst_rl_8));  // run pad tap 6 depth 3 @ (1150.0, 30.2)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // raw pad tap 6 depth 4 @ (1150.0, 30.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_8), .q(rn_rst_rl_9));  // run pad tap 6 depth 4 @ (1150.0, 30.2)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_n_t6));  // boot tap tap 6 depth 5 @ (1150.0, 30.2)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_root_n), .q(rst_rl_11));  // raw tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rn_rst_rl_11;
    ot_dp_rrelay u_srl_11 (.clk(clk), .d(run_root), .q(rn_rst_rl_11));  // run tap tap 7 depth 1 @ (1300.0, 30.2)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // raw pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_12));  // run pad tap 7 depth 2 @ (1300.0, 30.2)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));  // raw pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rn_rst_rl_13;
    ot_dp_rrelay u_srl_13 (.clk(clk), .d(rn_rst_rl_12), .q(rn_rst_rl_13));  // run pad tap 7 depth 3 @ (1300.0, 30.2)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));  // raw pad tap 7 depth 4 @ (1300.0, 30.2)
    wire rn_rst_rl_14;
    ot_dp_rrelay u_srl_14 (.clk(clk), .d(rn_rst_rl_13), .q(rn_rst_rl_14));  // run pad tap 7 depth 4 @ (1300.0, 30.2)
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t7));  // boot pad tap 7 depth 5 @ (1300.0, 30.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_11), .q(rst_rl_16));  // raw pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_16));  // run pad tap 9 depth 2 @ (1550.0, 30.2)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // raw tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_16), .q(rn_rst_rl_17));  // run tap tap 9 depth 3 @ (1550.0, 30.2)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // raw pad tap 9 depth 4 @ (1550.0, 30.2)
    wire rn_rst_rl_18;
    ot_dp_rrelay u_srl_18 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_18));  // run pad tap 9 depth 4 @ (1550.0, 30.2)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t9));  // boot pad tap 9 depth 5 @ (1550.0, 30.2)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_17), .q(rst_rl_20));  // raw pad tap 3 depth 4 @ (1872.0, 21.6)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_20));  // run pad tap 3 depth 4 @ (1872.0, 21.6)
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t3));  // boot tap tap 3 depth 5 @ (1872.0, 21.6)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_17), .q(rst_rl_22));  // raw tap tap 12 depth 4 @ (1892.2, 30.2)
    wire rn_rst_rl_22;
    ot_dp_rrelay u_srl_22 (.clk(clk), .d(rn_rst_rl_17), .q(rn_rst_rl_22));  // run tap tap 12 depth 4 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_n_t12));  // boot pad tap 12 depth 5 @ (1892.2, 30.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_22), .q(rst_n_t15));  // boot tap tap 15 depth 5 @ (1892.2, 400.0)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_11), .q(rst_rl_25));  // raw tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rn_rst_rl_25;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_11), .q(rn_rst_rl_25));  // run tap tap 10 depth 2 @ (1650.0, 30.2)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // raw pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_26));  // run pad tap 10 depth 3 @ (1650.0, 30.2)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // raw pad tap 10 depth 4 @ (1650.0, 30.2)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_26), .q(rn_rst_rl_27));  // run pad tap 10 depth 4 @ (1650.0, 30.2)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_n_t10));  // boot pad tap 10 depth 5 @ (1650.0, 30.2)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_25), .q(rst_rl_29));  // raw pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_29));  // run pad tap 4 depth 3 @ (1892.2, 160.0)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));  // raw pad tap 4 depth 4 @ (1892.2, 160.0)
    wire rn_rst_rl_30;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_29), .q(rn_rst_rl_30));  // run pad tap 4 depth 4 @ (1892.2, 160.0)
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_n_t4));  // boot tap tap 4 depth 5 @ (1892.2, 160.0)
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_25), .q(rst_rl_32));  // raw tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rn_rst_rl_32;
    ot_dp_rrelay u_srl_32 (.clk(clk), .d(rn_rst_rl_25), .q(rn_rst_rl_32));  // run tap tap 13 depth 3 @ (1892.2, 120.0)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));  // raw pad tap 13 depth 4 @ (1892.2, 120.0)
    wire rn_rst_rl_33;
    ot_dp_rrelay u_srl_33 (.clk(clk), .d(rn_rst_rl_32), .q(rn_rst_rl_33));  // run pad tap 13 depth 4 @ (1892.2, 120.0)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_n_t13));  // boot pad tap 13 depth 5 @ (1892.2, 120.0)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_32), .q(rst_rl_35));  // raw wire tap None depth 4 @ (1892.2, 470.0)
    wire rn_rst_rl_35;
    ot_dp_rrelay u_srl_35 (.clk(clk), .d(rn_rst_rl_32), .q(rn_rst_rl_35));  // run wire tap None depth 4 @ (1892.2, 470.0)
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_n_t17));  // boot tap tap 17 depth 5 @ (1892.2, 820.0)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_root_n), .q(rst_rl_37));  // raw pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rn_rst_rl_37;
    ot_dp_rrelay u_srl_37 (.clk(clk), .d(run_root), .q(rn_rst_rl_37));  // run pad tap 8 depth 1 @ (1450.0, 30.2)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // raw tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rn_rst_rl_38;
    ot_dp_rrelay u_srl_38 (.clk(clk), .d(rn_rst_rl_37), .q(rn_rst_rl_38));  // run tap tap 8 depth 2 @ (1450.0, 30.2)
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_rl_39));  // raw pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rn_rst_rl_39;
    ot_dp_rrelay u_srl_39 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_39));  // run pad tap 8 depth 3 @ (1450.0, 30.2)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));  // raw pad tap 8 depth 4 @ (1450.0, 30.2)
    wire rn_rst_rl_40;
    ot_dp_rrelay u_srl_40 (.clk(clk), .d(rn_rst_rl_39), .q(rn_rst_rl_40));  // run pad tap 8 depth 4 @ (1450.0, 30.2)
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_n_t8));  // boot pad tap 8 depth 5 @ (1450.0, 30.2)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_38), .q(rst_rl_42));  // raw pad tap 2 depth 3 @ (1730.0, 21.6)
    wire rn_rst_rl_42;
    ot_dp_rrelay u_srl_42 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_42));  // run pad tap 2 depth 3 @ (1730.0, 21.6)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // raw pad tap 2 depth 4 @ (1730.0, 21.6)
    wire rn_rst_rl_43;
    ot_dp_rrelay u_srl_43 (.clk(clk), .d(rn_rst_rl_42), .q(rn_rst_rl_43));  // run pad tap 2 depth 4 @ (1730.0, 21.6)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t2));  // boot tap tap 2 depth 5 @ (1730.0, 21.6)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_38), .q(rst_rl_45));  // raw tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rn_rst_rl_45;
    ot_dp_rrelay u_srl_45 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_45));  // run tap tap 11 depth 3 @ (1690.0, 30.2)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // raw pad tap 11 depth 4 @ (1690.0, 30.2)
    wire rn_rst_rl_46;
    ot_dp_rrelay u_srl_46 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_46));  // run pad tap 11 depth 4 @ (1690.0, 30.2)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_n_t11));  // boot pad tap 11 depth 5 @ (1690.0, 30.2)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_45), .q(rst_rl_48));  // raw wire tap None depth 4 @ (1892.2, 194.0)
    wire rn_rst_rl_48;
    ot_dp_rrelay u_srl_48 (.clk(clk), .d(rn_rst_rl_45), .q(rn_rst_rl_48));  // run wire tap None depth 4 @ (1892.2, 194.0)
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_n_t16));  // boot tap tap 16 depth 5 @ (1892.2, 560.0)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_38), .q(rst_rl_50));  // raw pad tap None depth 3 @ (1781.0, 30.2)
    wire rn_rst_rl_50;
    ot_dp_rrelay u_srl_50 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_50));  // run pad tap None depth 3 @ (1781.0, 30.2)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // raw wire tap None depth 4 @ (1781.0, 30.2)
    wire rn_rst_rl_51;
    ot_dp_rrelay u_srl_51 (.clk(clk), .d(rn_rst_rl_50), .q(rn_rst_rl_51));  // run wire tap None depth 4 @ (1781.0, 30.2)
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_n_t14));  // boot tap tap 14 depth 5 @ (1892.2, 250.0)
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_38), .q(rst_rl_53));  // raw wire tap None depth 3 @ (1800.6, 30.2)
    wire rn_rst_rl_53;
    ot_dp_rrelay u_srl_53 (.clk(clk), .d(rn_rst_rl_38), .q(rn_rst_rl_53));  // run wire tap None depth 3 @ (1800.6, 30.2)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));  // raw wire tap None depth 4 @ (1892.2, 289.4)
    wire rn_rst_rl_54;
    ot_dp_rrelay u_srl_54 (.clk(clk), .d(rn_rst_rl_53), .q(rn_rst_rl_54));  // run wire tap None depth 4 @ (1892.2, 289.4)
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_n_t5));  // boot tap tap 5 depth 5 @ (1892.2, 640.0)
assign o={rst_n_t0,rst_n_t1,rst_n_t2,rst_n_t3,rst_n_t4,rst_n_t5,rst_n_t6,rst_n_t7,rst_n_t8,rst_n_t9,rst_n_t10,rst_n_t11,rst_n_t12,rst_n_t13,rst_n_t14,rst_n_t15,rst_n_t16,rst_n_t17,start_t0};
endmodule
