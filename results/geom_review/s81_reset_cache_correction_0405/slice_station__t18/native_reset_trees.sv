// ot_dp_rrelay: one synchronous reset relay flop (OWNER RESET RULE 10-24, tools/die_plan/reset_tree.py).  No reset
// of its own: the synchronised reset is carried like data, so assertion is synchronous too (the clock runs at boot).
// keep_hierarchy + keep: the per-tap relays have identical inputs and would otherwise be merged (Yosys opt_merge), and a
// relay whose tap has no sinks is kept.  The flop drives q DIRECTLY (output reg, like ot_dp_ep): an internal kept alias
// (keep reg r; assign q = r) made ORFS insbuf hang a dangling BUFx2 q->r on every relay output, so a registered
// rst_o_<k> / start_o_<k> pin register had a load besides its port (face_guard 'shared', S81 stations 10-25).
(* keep_hierarchy, keep *)
module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule

module old_tree(input wire clk,input wire arst_n,output wire[42:0] observations,output wire rst_o_0);
    // OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree, depth 7 to all 43 taps, hops <= 405 um; release 8 clocks after the entry pin
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (die reset tree)
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    wire rst_n_t8;
    wire rst_n_t9;
    wire rst_n_t10;
    wire rst_n_t11;
    wire rst_n_t12;
    wire rst_n_t13;
    wire rst_n_t14;
    wire rst_n_t15;
    wire rst_n_t16;
    wire rst_n_t17;
    wire rst_n_t18;
    wire rst_n_t19;
    wire rst_n_t20;
    wire rst_n_t21;
    wire rst_n_t22;
    wire rst_n_t23;
    wire rst_n_t24;
    wire rst_n_t25;
    wire rst_n_t26;
    wire rst_n_t27;
    wire rst_n_t28;
    wire rst_n_t29;
    wire rst_n_t30;
    wire rst_n_t31;
    wire rst_n_t32;
    wire rst_n_t33;
    wire rst_n_t34;
    wire rst_n_t35;
    wire rst_n_t36;
    wire rst_n_t37;
    wire rst_n_t38;
    wire rst_n_t39;
    wire rst_n_t40;
    wire rst_n_t41;
    wire rst_n_t42;
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // pad tap 34 depth 1 @ (1425.6, 1209.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // pad tap 34 depth 2 @ (1425.6, 1209.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // pad tap 34 depth 3 @ (1425.6, 1209.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // pad tap 34 depth 4 @ (1425.6, 1209.6)
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));  // pad tap 34 depth 5 @ (1425.6, 1209.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));  // pad tap 34 depth 6 @ (1425.6, 1209.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t34));  // tap tap 34 depth 7 @ (1425.6, 1209.6)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_root_n), .q(rst_rl_7));  // tap tap 35 depth 1 @ (1425.6, 871.1)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // pad tap 35 depth 2 @ (1425.6, 871.1)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // pad tap 35 depth 3 @ (1425.6, 871.1)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // pad tap 35 depth 4 @ (1425.6, 871.1)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // pad tap 35 depth 5 @ (1425.6, 871.1)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // pad tap 35 depth 6 @ (1425.6, 871.1)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_n_t35));  // pad tap 35 depth 7 @ (1425.6, 871.1)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_7), .q(rst_rl_14));  // tap tap 30 depth 2 @ (1425.6, 514.8)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // pad tap 30 depth 3 @ (1425.6, 514.8)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // pad tap 30 depth 4 @ (1425.6, 514.8)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // pad tap 30 depth 5 @ (1425.6, 514.8)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // pad tap 30 depth 6 @ (1425.6, 514.8)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t30));  // pad tap 30 depth 7 @ (1425.6, 514.8)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_14), .q(rst_rl_20));  // tap tap 14 depth 3 @ (1425.6, 185.2)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));  // pad tap 14 depth 4 @ (1425.6, 185.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // pad tap 14 depth 5 @ (1425.6, 185.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // pad tap 14 depth 6 @ (1425.6, 185.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t14));  // pad tap 14 depth 7 @ (1425.6, 185.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_20), .q(rst_rl_25));  // tap tap 12 depth 4 @ (1101.9, 174.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // pad tap 12 depth 5 @ (1101.9, 174.0)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // pad tap 12 depth 6 @ (1101.9, 174.0)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_n_t12));  // pad tap 12 depth 7 @ (1101.9, 174.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_25), .q(rst_rl_29));  // pad tap 13 depth 5 @ (769.0, 183.5)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));  // tap tap 13 depth 6 @ (769.0, 183.5)
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_n_t13));  // pad tap 13 depth 7 @ (769.0, 183.5)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_30), .q(rst_n_t11));  // tap tap 11 depth 7 @ (457.6, 164.9)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_25), .q(rst_rl_33));  // wire tap None depth 5 @ (745.3, 174.0)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // tap tap 3 depth 6 @ (545.4, 17.3)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t3));  // pad tap 3 depth 7 @ (545.4, 17.3)
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_34), .q(rst_o_0));  // registered reset out rst_o_0 (wavefront, dedicated relay): tap tap 41 depth 7 @ (180.4, 8.6)
    ot_dp_rrelay u_rrl_36_t (.clk(clk), .d(rst_rl_34), .q(rst_n_t41));  // tap-net copy of u_rrl_36 for in-type loads: depth 7 @ (180.4, 8.6)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_25), .q(rst_rl_37));  // pad tap None depth 5 @ (738.8, 174.0)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // wire tap None depth 6 @ (738.8, 174.0)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_o_1));  // registered reset out rst_o_1 (wavefront, dedicated relay): tap tap 42 depth 7 @ (541.1, 8.6)
    ot_dp_rrelay u_rrl_39_t (.clk(clk), .d(rst_rl_38), .q(rst_n_t42));  // tap-net copy of u_rrl_39 for in-type loads: depth 7 @ (541.1, 8.6)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_14), .q(rst_rl_40));  // pad tap 17 depth 3 @ (1425.6, 297.3)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // pad tap 17 depth 4 @ (1425.6, 297.3)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // tap tap 17 depth 5 @ (1425.6, 297.3)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // pad tap 17 depth 6 @ (1425.6, 297.3)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t17));  // pad tap 17 depth 7 @ (1425.6, 297.3)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_42), .q(rst_rl_45));  // tap tap 19 depth 6 @ (1129.8, 298.1)
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_n_t19));  // pad tap 19 depth 7 @ (1129.8, 298.1)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_45), .q(rst_n_t18));  // tap tap 18 depth 7 @ (817.6, 298.1)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_14), .q(rst_rl_48));  // pad tap 23 depth 3 @ (1425.6, 423.5)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));  // pad tap 23 depth 4 @ (1425.6, 423.5)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));  // pad tap 23 depth 5 @ (1425.6, 423.5)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // tap tap 23 depth 6 @ (1425.6, 423.5)
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_n_t23));  // pad tap 23 depth 7 @ (1425.6, 423.5)
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_51), .q(rst_n_t8));  // tap tap 8 depth 7 @ (1425.6, 53.4)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_14), .q(rst_rl_54));  // tap tap 29 depth 3 @ (1082.2, 514.8)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));  // pad tap 29 depth 4 @ (1082.2, 514.8)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // pad tap 29 depth 5 @ (1082.2, 514.8)
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));  // pad tap 29 depth 6 @ (1082.2, 514.8)
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_n_t29));  // pad tap 29 depth 7 @ (1082.2, 514.8)
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_54), .q(rst_rl_59));  // tap tap 0 depth 4 @ (721.4, 514.8)
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_rl_60));  // pad tap 0 depth 5 @ (721.4, 514.8)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));  // pad tap 0 depth 6 @ (721.4, 514.8)
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_n_t0));  // pad tap 0 depth 7 @ (721.4, 514.8)
    wire rst_rl_63;
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_59), .q(rst_rl_63));  // tap tap 28 depth 5 @ (360.7, 514.8)
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_63), .q(rst_rl_64));  // pad tap 28 depth 6 @ (360.7, 514.8)
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_n_t28));  // pad tap 28 depth 7 @ (360.7, 514.8)
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_63), .q(rst_rl_66));  // tap tap 15 depth 6 @ (403.6, 199.5)
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_n_t15));  // pad tap 15 depth 7 @ (403.6, 199.5)
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_66), .q(rst_n_t2));  // tap tap 2 depth 7 @ (207.3, 17.3)
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_63), .q(rst_rl_69));  // wire tap None depth 6 @ (147.9, 372.5)
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_n_t1));  // tap tap 1 depth 7 @ (147.9, 17.3)
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_59), .q(rst_rl_71));  // pad tap None depth 5 @ (349.0, 514.8)
    wire rst_rl_72;
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_rl_72));  // wire tap None depth 6 @ (349.0, 514.8)
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_rl_72), .q(rst_n_t16));  // tap tap 16 depth 7 @ (196.7, 294.8)
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_54), .q(rst_rl_74));  // pad tap 26 depth 4 @ (1081.7, 424.3)
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_rl_75));  // pad tap 26 depth 5 @ (1081.7, 424.3)
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_rl_76));  // pad tap 26 depth 6 @ (1081.7, 424.3)
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_n_t26));  // tap tap 26 depth 7 @ (1081.7, 424.3)
    wire rst_rl_78;
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_7), .q(rst_rl_78));  // pad tap None depth 2 @ (1425.6, 493.0)
    wire rst_rl_79;
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_rl_78), .q(rst_rl_79));  // pad tap None depth 3 @ (1425.6, 493.0)
    wire rst_rl_80;
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_79), .q(rst_rl_80));  // pad tap None depth 4 @ (1425.6, 493.0)
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_rl_80), .q(rst_rl_81));  // pad tap None depth 5 @ (1425.6, 493.0)
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));  // wire tap None depth 6 @ (1425.6, 493.0)
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_n_t10));  // tap tap 10 depth 7 @ (1425.6, 115.0)
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_root_n), .q(rst_rl_84));  // tap tap 36 depth 1 @ (1089.3, 1209.6)
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_rl_85));  // pad tap 36 depth 2 @ (1089.3, 1209.6)
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));  // pad tap 36 depth 3 @ (1089.3, 1209.6)
    wire rst_rl_87;
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_rl_87));  // pad tap 36 depth 4 @ (1089.3, 1209.6)
    wire rst_rl_88;
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_87), .q(rst_rl_88));  // pad tap 36 depth 5 @ (1089.3, 1209.6)
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_rl_88), .q(rst_rl_89));  // pad tap 36 depth 6 @ (1089.3, 1209.6)
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_n_t36));  // pad tap 36 depth 7 @ (1089.3, 1209.6)
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_84), .q(rst_rl_91));  // tap tap 37 depth 2 @ (743.9, 1209.6)
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_rl_92));  // pad tap 37 depth 3 @ (743.9, 1209.6)
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));  // pad tap 37 depth 4 @ (743.9, 1209.6)
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));  // pad tap 37 depth 5 @ (743.9, 1209.6)
    wire rst_rl_95;
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_rl_95));  // pad tap 37 depth 6 @ (743.9, 1209.6)
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_95), .q(rst_n_t37));  // pad tap 37 depth 7 @ (743.9, 1209.6)
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_91), .q(rst_rl_97));  // tap tap 38 depth 3 @ (398.5, 1209.6)
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));  // pad tap 38 depth 4 @ (398.5, 1209.6)
    wire rst_rl_99;
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_rl_99));  // pad tap 38 depth 5 @ (398.5, 1209.6)
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_99), .q(rst_rl_100));  // pad tap 38 depth 6 @ (398.5, 1209.6)
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_n_t38));  // pad tap 38 depth 7 @ (398.5, 1209.6)
    wire rst_rl_102;
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_97), .q(rst_rl_102));  // tap tap 33 depth 4 @ (61.7, 1209.6)
    wire rst_rl_103;
    ot_dp_rrelay u_rrl_103 (.clk(clk), .d(rst_rl_102), .q(rst_rl_103));  // pad tap 33 depth 5 @ (61.7, 1209.6)
    wire rst_rl_104;
    ot_dp_rrelay u_rrl_104 (.clk(clk), .d(rst_rl_103), .q(rst_rl_104));  // pad tap 33 depth 6 @ (61.7, 1209.6)
    ot_dp_rrelay u_rrl_105 (.clk(clk), .d(rst_rl_104), .q(rst_n_t33));  // pad tap 33 depth 7 @ (61.7, 1209.6)
    wire rst_rl_106;
    ot_dp_rrelay u_rrl_106 (.clk(clk), .d(rst_rl_102), .q(rst_rl_106));  // tap tap 32 depth 5 @ (61.7, 920.2)
    wire rst_rl_107;
    ot_dp_rrelay u_rrl_107 (.clk(clk), .d(rst_rl_106), .q(rst_rl_107));  // pad tap 32 depth 6 @ (61.7, 920.2)
    ot_dp_rrelay u_rrl_108 (.clk(clk), .d(rst_rl_107), .q(rst_n_t32));  // pad tap 32 depth 7 @ (61.7, 920.2)
    wire rst_rl_109;
    ot_dp_rrelay u_rrl_109 (.clk(clk), .d(rst_rl_106), .q(rst_rl_109));  // tap tap 31 depth 6 @ (61.7, 613.4)
    ot_dp_rrelay u_rrl_110 (.clk(clk), .d(rst_rl_109), .q(rst_n_t31));  // pad tap 31 depth 7 @ (61.7, 613.4)
    ot_dp_rrelay u_rrl_111 (.clk(clk), .d(rst_rl_109), .q(rst_n_t21));  // tap tap 21 depth 7 @ (33.2, 306.7)
    wire rst_rl_112;
    ot_dp_rrelay u_rrl_112 (.clk(clk), .d(rst_root_n), .q(rst_rl_112));  // wire tap None depth 1 @ (1081.7, 1191.6)
    wire rst_rl_113;
    ot_dp_rrelay u_rrl_113 (.clk(clk), .d(rst_rl_112), .q(rst_rl_113));  // tap tap 40 depth 2 @ (1081.7, 812.0)
    wire rst_rl_114;
    ot_dp_rrelay u_rrl_114 (.clk(clk), .d(rst_rl_113), .q(rst_rl_114));  // pad tap 40 depth 3 @ (1081.7, 812.0)
    wire rst_rl_115;
    ot_dp_rrelay u_rrl_115 (.clk(clk), .d(rst_rl_114), .q(rst_rl_115));  // pad tap 40 depth 4 @ (1081.7, 812.0)
    wire rst_rl_116;
    ot_dp_rrelay u_rrl_116 (.clk(clk), .d(rst_rl_115), .q(rst_rl_116));  // pad tap 40 depth 5 @ (1081.7, 812.0)
    wire rst_rl_117;
    ot_dp_rrelay u_rrl_117 (.clk(clk), .d(rst_rl_116), .q(rst_rl_117));  // pad tap 40 depth 6 @ (1081.7, 812.0)
    ot_dp_rrelay u_rrl_118 (.clk(clk), .d(rst_rl_117), .q(rst_n_t40));  // pad tap 40 depth 7 @ (1081.7, 812.0)
    wire rst_rl_119;
    ot_dp_rrelay u_rrl_119 (.clk(clk), .d(rst_rl_113), .q(rst_rl_119));  // tap tap 39 depth 3 @ (721.4, 801.1)
    wire rst_rl_120;
    ot_dp_rrelay u_rrl_120 (.clk(clk), .d(rst_rl_119), .q(rst_rl_120));  // pad tap 39 depth 4 @ (721.4, 801.1)
    wire rst_rl_121;
    ot_dp_rrelay u_rrl_121 (.clk(clk), .d(rst_rl_120), .q(rst_rl_121));  // pad tap 39 depth 5 @ (721.4, 801.1)
    wire rst_rl_122;
    ot_dp_rrelay u_rrl_122 (.clk(clk), .d(rst_rl_121), .q(rst_rl_122));  // pad tap 39 depth 6 @ (721.4, 801.1)
    ot_dp_rrelay u_rrl_123 (.clk(clk), .d(rst_rl_122), .q(rst_n_t39));  // pad tap 39 depth 7 @ (721.4, 801.1)
    wire rst_rl_124;
    ot_dp_rrelay u_rrl_124 (.clk(clk), .d(rst_rl_119), .q(rst_rl_124));  // tap tap 25 depth 4 @ (721.4, 424.3)
    wire rst_rl_125;
    ot_dp_rrelay u_rrl_125 (.clk(clk), .d(rst_rl_124), .q(rst_rl_125));  // pad tap 25 depth 5 @ (721.4, 424.3)
    wire rst_rl_126;
    ot_dp_rrelay u_rrl_126 (.clk(clk), .d(rst_rl_125), .q(rst_rl_126));  // pad tap 25 depth 6 @ (721.4, 424.3)
    ot_dp_rrelay u_rrl_127 (.clk(clk), .d(rst_rl_126), .q(rst_n_t25));  // pad tap 25 depth 7 @ (721.4, 424.3)
    wire rst_rl_128;
    ot_dp_rrelay u_rrl_128 (.clk(clk), .d(rst_rl_124), .q(rst_rl_128));  // pad tap 4 depth 5 @ (721.4, 52.7)
    wire rst_rl_129;
    ot_dp_rrelay u_rrl_129 (.clk(clk), .d(rst_rl_128), .q(rst_rl_129));  // pad tap 4 depth 6 @ (721.4, 52.7)
    ot_dp_rrelay u_rrl_130 (.clk(clk), .d(rst_rl_129), .q(rst_n_t4));  // tap tap 4 depth 7 @ (721.4, 52.7)
    wire rst_rl_131;
    ot_dp_rrelay u_rrl_131 (.clk(clk), .d(rst_rl_124), .q(rst_rl_131));  // pad tap 9 depth 5 @ (721.4, 113.2)
    wire rst_rl_132;
    ot_dp_rrelay u_rrl_132 (.clk(clk), .d(rst_rl_131), .q(rst_rl_132));  // pad tap 9 depth 6 @ (721.4, 113.2)
    ot_dp_rrelay u_rrl_133 (.clk(clk), .d(rst_rl_132), .q(rst_n_t9));  // tap tap 9 depth 7 @ (721.4, 113.2)
    wire rst_rl_134;
    ot_dp_rrelay u_rrl_134 (.clk(clk), .d(rst_rl_124), .q(rst_rl_134));  // pad tap 20 depth 5 @ (505.5, 298.1)
    wire rst_rl_135;
    ot_dp_rrelay u_rrl_135 (.clk(clk), .d(rst_rl_134), .q(rst_rl_135));  // pad tap 20 depth 6 @ (505.5, 298.1)
    ot_dp_rrelay u_rrl_136 (.clk(clk), .d(rst_rl_135), .q(rst_n_t20));  // tap tap 20 depth 7 @ (505.5, 298.1)
    wire rst_rl_137;
    ot_dp_rrelay u_rrl_137 (.clk(clk), .d(rst_rl_124), .q(rst_rl_137));  // tap tap 24 depth 5 @ (361.0, 423.9)
    wire rst_rl_138;
    ot_dp_rrelay u_rrl_138 (.clk(clk), .d(rst_rl_137), .q(rst_rl_138));  // pad tap 24 depth 6 @ (361.0, 423.9)
    ot_dp_rrelay u_rrl_139 (.clk(clk), .d(rst_rl_138), .q(rst_n_t24));  // pad tap 24 depth 7 @ (361.0, 423.9)
    wire rst_rl_140;
    ot_dp_rrelay u_rrl_140 (.clk(clk), .d(rst_rl_137), .q(rst_rl_140));  // tap tap 7 depth 6 @ (360.7, 53.1)
    ot_dp_rrelay u_rrl_141 (.clk(clk), .d(rst_rl_140), .q(rst_n_t7));  // pad tap 7 depth 7 @ (360.7, 53.1)
    ot_dp_rrelay u_rrl_142 (.clk(clk), .d(rst_rl_140), .q(rst_n_t6));  // tap tap 6 depth 7 @ (17.3, 52.7)
    wire rst_rl_143;
    ot_dp_rrelay u_rrl_143 (.clk(clk), .d(rst_rl_137), .q(rst_rl_143));  // pad tap 27 depth 6 @ (17.3, 424.7)
    ot_dp_rrelay u_rrl_144 (.clk(clk), .d(rst_rl_143), .q(rst_n_t27));  // tap tap 27 depth 7 @ (17.3, 424.7)
    wire rst_rl_145;
    ot_dp_rrelay u_rrl_145 (.clk(clk), .d(rst_rl_124), .q(rst_rl_145));  // pad tap None depth 5 @ (346.6, 424.3)
    wire rst_rl_146;
    ot_dp_rrelay u_rrl_146 (.clk(clk), .d(rst_rl_145), .q(rst_rl_146));  // wire tap None depth 6 @ (346.6, 424.3)
    ot_dp_rrelay u_rrl_147 (.clk(clk), .d(rst_rl_146), .q(rst_n_t22));  // tap tap 22 depth 7 @ (89.4, 306.7)
    wire rst_rl_148;
    ot_dp_rrelay u_rrl_148 (.clk(clk), .d(rst_rl_113), .q(rst_rl_148));  // pad tap None depth 3 @ (1081.7, 432.3)
    wire rst_rl_149;
    ot_dp_rrelay u_rrl_149 (.clk(clk), .d(rst_rl_148), .q(rst_rl_149));  // pad tap None depth 4 @ (1081.7, 432.3)
    wire rst_rl_150;
    ot_dp_rrelay u_rrl_150 (.clk(clk), .d(rst_rl_149), .q(rst_rl_150));  // pad tap None depth 5 @ (1081.7, 432.3)
    wire rst_rl_151;
    ot_dp_rrelay u_rrl_151 (.clk(clk), .d(rst_rl_150), .q(rst_rl_151));  // wire tap None depth 6 @ (1081.7, 432.3)
    ot_dp_rrelay u_rrl_152 (.clk(clk), .d(rst_rl_151), .q(rst_n_t5));  // tap tap 5 depth 7 @ (1081.7, 52.7)
assign observations[0]=rst_n_t0;
assign observations[1]=rst_n_t1;
assign observations[2]=rst_n_t2;
assign observations[3]=rst_n_t3;
assign observations[4]=rst_n_t4;
assign observations[5]=rst_n_t5;
assign observations[6]=rst_n_t6;
assign observations[7]=rst_n_t7;
assign observations[8]=rst_n_t8;
assign observations[9]=rst_n_t9;
assign observations[10]=rst_n_t10;
assign observations[11]=rst_n_t11;
assign observations[12]=rst_n_t12;
assign observations[13]=rst_n_t13;
assign observations[14]=rst_n_t14;
assign observations[15]=rst_n_t15;
assign observations[16]=rst_n_t16;
assign observations[17]=rst_n_t17;
assign observations[18]=rst_n_t18;
assign observations[19]=rst_n_t19;
assign observations[20]=rst_n_t20;
assign observations[21]=rst_n_t21;
assign observations[22]=rst_n_t22;
assign observations[23]=rst_n_t23;
assign observations[24]=rst_n_t24;
assign observations[25]=rst_n_t25;
assign observations[26]=rst_n_t26;
assign observations[27]=rst_n_t27;
assign observations[28]=rst_n_t28;
assign observations[29]=rst_n_t29;
assign observations[30]=rst_n_t30;
assign observations[31]=rst_n_t31;
assign observations[32]=rst_n_t32;
assign observations[33]=rst_n_t33;
assign observations[34]=rst_n_t34;
assign observations[35]=rst_n_t35;
assign observations[36]=rst_n_t36;
assign observations[37]=rst_n_t37;
assign observations[38]=rst_n_t38;
assign observations[39]=rst_n_t39;
assign observations[40]=rst_n_t40;
assign observations[41]=rst_n_t41;
assign observations[42]=rst_n_t42;
endmodule
module new_tree(input wire clk,input wire arst_n,output wire[42:0] observations,output wire rst_o_0);
    // OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree, depth 7 to all 43 taps, hops <= 405 um; release 8 clocks after the entry pin
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (die reset tree)
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    wire rst_n_t8;
    wire rst_n_t9;
    wire rst_n_t10;
    wire rst_n_t11;
    wire rst_n_t12;
    wire rst_n_t13;
    wire rst_n_t14;
    wire rst_n_t15;
    wire rst_n_t16;
    wire rst_n_t17;
    wire rst_n_t18;
    wire rst_n_t19;
    wire rst_n_t20;
    wire rst_n_t21;
    wire rst_n_t22;
    wire rst_n_t23;
    wire rst_n_t24;
    wire rst_n_t25;
    wire rst_n_t26;
    wire rst_n_t27;
    wire rst_n_t28;
    wire rst_n_t29;
    wire rst_n_t30;
    wire rst_n_t31;
    wire rst_n_t32;
    wire rst_n_t33;
    wire rst_n_t34;
    wire rst_n_t35;
    wire rst_n_t36;
    wire rst_n_t37;
    wire rst_n_t38;
    wire rst_n_t39;
    wire rst_n_t40;
    wire rst_n_t41;
    wire rst_n_t42;
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // pad tap 34 depth 1 @ (1425.6, 1209.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // pad tap 34 depth 2 @ (1425.6, 1209.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // pad tap 34 depth 3 @ (1425.6, 1209.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // pad tap 34 depth 4 @ (1425.6, 1209.6)
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));  // pad tap 34 depth 5 @ (1425.6, 1209.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));  // pad tap 34 depth 6 @ (1425.6, 1209.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t34));  // tap tap 34 depth 7 @ (1425.6, 1209.6)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_root_n), .q(rst_rl_7));  // tap tap 35 depth 1 @ (1425.6, 871.1)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // pad tap 35 depth 2 @ (1425.6, 871.1)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // pad tap 35 depth 3 @ (1425.6, 871.1)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // pad tap 35 depth 4 @ (1425.6, 871.1)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // pad tap 35 depth 5 @ (1425.6, 871.1)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // pad tap 35 depth 6 @ (1425.6, 871.1)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_n_t35));  // pad tap 35 depth 7 @ (1425.6, 871.1)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_7), .q(rst_rl_14));  // tap tap 30 depth 2 @ (1425.6, 514.8)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // pad tap 30 depth 3 @ (1425.6, 514.8)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // pad tap 30 depth 4 @ (1425.6, 514.8)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // pad tap 30 depth 5 @ (1425.6, 514.8)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // pad tap 30 depth 6 @ (1425.6, 514.8)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t30));  // pad tap 30 depth 7 @ (1425.6, 514.8)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_14), .q(rst_rl_20));  // tap tap 14 depth 3 @ (1425.6, 185.2)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));  // pad tap 14 depth 4 @ (1425.6, 185.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // pad tap 14 depth 5 @ (1425.6, 185.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // pad tap 14 depth 6 @ (1425.6, 185.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t14));  // pad tap 14 depth 7 @ (1425.6, 185.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_20), .q(rst_rl_25));  // tap tap 12 depth 4 @ (1101.9, 174.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // pad tap 12 depth 5 @ (1101.9, 174.0)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // pad tap 12 depth 6 @ (1101.9, 174.0)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_n_t12));  // pad tap 12 depth 7 @ (1101.9, 174.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_25), .q(rst_rl_29));  // pad tap 13 depth 5 @ (769.0, 183.5)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));  // tap tap 13 depth 6 @ (769.0, 183.5)
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_n_t13));  // pad tap 13 depth 7 @ (769.0, 183.5)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_30), .q(rst_n_t11));  // tap tap 11 depth 7 @ (457.6, 164.9)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_25), .q(rst_rl_33));  // wire tap None depth 5 @ (745.3, 174.0)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // tap tap 3 depth 6 @ (545.4, 17.3)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t3));  // pad tap 3 depth 7 @ (545.4, 17.3)
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_34), .q(rst_o_0));  // registered reset out rst_o_0 (wavefront, dedicated relay): tap tap 41 depth 7 @ (180.4, 8.6)
    ot_dp_rrelay u_rrl_36_t (.clk(clk), .d(rst_rl_34), .q(rst_n_t41));  // tap-net copy of u_rrl_36 for in-type loads: depth 7 @ (180.4, 8.6)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_25), .q(rst_rl_37));  // pad tap None depth 5 @ (738.8, 174.0)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // wire tap None depth 6 @ (738.8, 174.0)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_o_1));  // registered reset out rst_o_1 (wavefront, dedicated relay): tap tap 42 depth 7 @ (541.1, 8.6)
    ot_dp_rrelay u_rrl_39_t (.clk(clk), .d(rst_rl_38), .q(rst_n_t42));  // tap-net copy of u_rrl_39 for in-type loads: depth 7 @ (541.1, 8.6)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_14), .q(rst_rl_40));  // pad tap 17 depth 3 @ (1425.6, 297.3)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // pad tap 17 depth 4 @ (1425.6, 297.3)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // tap tap 17 depth 5 @ (1425.6, 297.3)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // pad tap 17 depth 6 @ (1425.6, 297.3)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t17));  // pad tap 17 depth 7 @ (1425.6, 297.3)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_42), .q(rst_rl_45));  // tap tap 19 depth 6 @ (1129.8, 298.1)
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_n_t19));  // pad tap 19 depth 7 @ (1129.8, 298.1)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_45), .q(rst_n_t18));  // tap tap 18 depth 7 @ (817.6, 298.1)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_14), .q(rst_rl_48));  // pad tap 23 depth 3 @ (1425.6, 423.5)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));  // pad tap 23 depth 4 @ (1425.6, 423.5)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));  // pad tap 23 depth 5 @ (1425.6, 423.5)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // tap tap 23 depth 6 @ (1425.6, 423.5)
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_n_t23));  // pad tap 23 depth 7 @ (1425.6, 423.5)
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_51), .q(rst_n_t8));  // tap tap 8 depth 7 @ (1425.6, 53.4)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_14), .q(rst_rl_54));  // tap tap 29 depth 3 @ (1082.2, 514.8)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));  // pad tap 29 depth 4 @ (1082.2, 514.8)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // pad tap 29 depth 5 @ (1082.2, 514.8)
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));  // pad tap 29 depth 6 @ (1082.2, 514.8)
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_n_t29));  // pad tap 29 depth 7 @ (1082.2, 514.8)
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_54), .q(rst_rl_59));  // tap tap 0 depth 4 @ (721.4, 514.8)
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_rl_60));  // pad tap 0 depth 5 @ (721.4, 514.8)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));  // pad tap 0 depth 6 @ (721.4, 514.8)
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_n_t0));  // pad tap 0 depth 7 @ (721.4, 514.8)
    wire rst_rl_63;
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_59), .q(rst_rl_63));  // tap tap 28 depth 5 @ (360.7, 514.8)
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_63), .q(rst_rl_64));  // pad tap 28 depth 6 @ (360.7, 514.8)
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_n_t28));  // pad tap 28 depth 7 @ (360.7, 514.8)
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_63), .q(rst_rl_66));  // tap tap 15 depth 6 @ (403.6, 199.5)
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_n_t15));  // pad tap 15 depth 7 @ (403.6, 199.5)
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_66), .q(rst_n_t2));  // tap tap 2 depth 7 @ (207.3, 17.3)
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_63), .q(rst_rl_69));  // wire tap None depth 6 @ (147.9, 372.5)
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_n_t1));  // tap tap 1 depth 7 @ (147.9, 17.3)
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_59), .q(rst_rl_71));  // pad tap None depth 5 @ (348.9, 514.8)
    wire rst_rl_72;
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_rl_72));  // wire tap None depth 6 @ (348.9, 514.8)
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_rl_72), .q(rst_n_t16));  // tap tap 16 depth 7 @ (197.1, 294.1)
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_54), .q(rst_rl_74));  // pad tap 26 depth 4 @ (1081.7, 424.3)
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_rl_75));  // pad tap 26 depth 5 @ (1081.7, 424.3)
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_rl_76));  // pad tap 26 depth 6 @ (1081.7, 424.3)
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_n_t26));  // tap tap 26 depth 7 @ (1081.7, 424.3)
    wire rst_rl_78;
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_7), .q(rst_rl_78));  // pad tap None depth 2 @ (1425.6, 493.0)
    wire rst_rl_79;
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_rl_78), .q(rst_rl_79));  // pad tap None depth 3 @ (1425.6, 493.0)
    wire rst_rl_80;
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_79), .q(rst_rl_80));  // pad tap None depth 4 @ (1425.6, 493.0)
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_rl_80), .q(rst_rl_81));  // pad tap None depth 5 @ (1425.6, 493.0)
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));  // wire tap None depth 6 @ (1425.6, 493.0)
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_n_t10));  // tap tap 10 depth 7 @ (1425.6, 115.0)
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_root_n), .q(rst_rl_84));  // tap tap 36 depth 1 @ (1089.3, 1209.6)
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_rl_85));  // pad tap 36 depth 2 @ (1089.3, 1209.6)
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));  // pad tap 36 depth 3 @ (1089.3, 1209.6)
    wire rst_rl_87;
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_rl_87));  // pad tap 36 depth 4 @ (1089.3, 1209.6)
    wire rst_rl_88;
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_87), .q(rst_rl_88));  // pad tap 36 depth 5 @ (1089.3, 1209.6)
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_rl_88), .q(rst_rl_89));  // pad tap 36 depth 6 @ (1089.3, 1209.6)
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_n_t36));  // pad tap 36 depth 7 @ (1089.3, 1209.6)
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_84), .q(rst_rl_91));  // tap tap 37 depth 2 @ (743.9, 1209.6)
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_rl_92));  // pad tap 37 depth 3 @ (743.9, 1209.6)
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));  // pad tap 37 depth 4 @ (743.9, 1209.6)
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));  // pad tap 37 depth 5 @ (743.9, 1209.6)
    wire rst_rl_95;
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_rl_95));  // pad tap 37 depth 6 @ (743.9, 1209.6)
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_95), .q(rst_n_t37));  // pad tap 37 depth 7 @ (743.9, 1209.6)
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_91), .q(rst_rl_97));  // tap tap 38 depth 3 @ (398.5, 1209.6)
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));  // pad tap 38 depth 4 @ (398.5, 1209.6)
    wire rst_rl_99;
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_rl_99));  // pad tap 38 depth 5 @ (398.5, 1209.6)
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_99), .q(rst_rl_100));  // pad tap 38 depth 6 @ (398.5, 1209.6)
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_n_t38));  // pad tap 38 depth 7 @ (398.5, 1209.6)
    wire rst_rl_102;
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_97), .q(rst_rl_102));  // tap tap 33 depth 4 @ (61.7, 1209.6)
    wire rst_rl_103;
    ot_dp_rrelay u_rrl_103 (.clk(clk), .d(rst_rl_102), .q(rst_rl_103));  // pad tap 33 depth 5 @ (61.7, 1209.6)
    wire rst_rl_104;
    ot_dp_rrelay u_rrl_104 (.clk(clk), .d(rst_rl_103), .q(rst_rl_104));  // pad tap 33 depth 6 @ (61.7, 1209.6)
    ot_dp_rrelay u_rrl_105 (.clk(clk), .d(rst_rl_104), .q(rst_n_t33));  // pad tap 33 depth 7 @ (61.7, 1209.6)
    wire rst_rl_106;
    ot_dp_rrelay u_rrl_106 (.clk(clk), .d(rst_rl_102), .q(rst_rl_106));  // tap tap 32 depth 5 @ (61.7, 920.2)
    wire rst_rl_107;
    ot_dp_rrelay u_rrl_107 (.clk(clk), .d(rst_rl_106), .q(rst_rl_107));  // pad tap 32 depth 6 @ (61.7, 920.2)
    ot_dp_rrelay u_rrl_108 (.clk(clk), .d(rst_rl_107), .q(rst_n_t32));  // pad tap 32 depth 7 @ (61.7, 920.2)
    wire rst_rl_109;
    ot_dp_rrelay u_rrl_109 (.clk(clk), .d(rst_rl_106), .q(rst_rl_109));  // tap tap 31 depth 6 @ (61.7, 613.4)
    ot_dp_rrelay u_rrl_110 (.clk(clk), .d(rst_rl_109), .q(rst_n_t31));  // pad tap 31 depth 7 @ (61.7, 613.4)
    ot_dp_rrelay u_rrl_111 (.clk(clk), .d(rst_rl_109), .q(rst_n_t21));  // tap tap 21 depth 7 @ (33.2, 306.7)
    wire rst_rl_112;
    ot_dp_rrelay u_rrl_112 (.clk(clk), .d(rst_root_n), .q(rst_rl_112));  // wire tap None depth 1 @ (1081.7, 1191.6)
    wire rst_rl_113;
    ot_dp_rrelay u_rrl_113 (.clk(clk), .d(rst_rl_112), .q(rst_rl_113));  // tap tap 40 depth 2 @ (1081.7, 812.0)
    wire rst_rl_114;
    ot_dp_rrelay u_rrl_114 (.clk(clk), .d(rst_rl_113), .q(rst_rl_114));  // pad tap 40 depth 3 @ (1081.7, 812.0)
    wire rst_rl_115;
    ot_dp_rrelay u_rrl_115 (.clk(clk), .d(rst_rl_114), .q(rst_rl_115));  // pad tap 40 depth 4 @ (1081.7, 812.0)
    wire rst_rl_116;
    ot_dp_rrelay u_rrl_116 (.clk(clk), .d(rst_rl_115), .q(rst_rl_116));  // pad tap 40 depth 5 @ (1081.7, 812.0)
    wire rst_rl_117;
    ot_dp_rrelay u_rrl_117 (.clk(clk), .d(rst_rl_116), .q(rst_rl_117));  // pad tap 40 depth 6 @ (1081.7, 812.0)
    ot_dp_rrelay u_rrl_118 (.clk(clk), .d(rst_rl_117), .q(rst_n_t40));  // pad tap 40 depth 7 @ (1081.7, 812.0)
    wire rst_rl_119;
    ot_dp_rrelay u_rrl_119 (.clk(clk), .d(rst_rl_113), .q(rst_rl_119));  // tap tap 39 depth 3 @ (721.4, 801.1)
    wire rst_rl_120;
    ot_dp_rrelay u_rrl_120 (.clk(clk), .d(rst_rl_119), .q(rst_rl_120));  // pad tap 39 depth 4 @ (721.4, 801.1)
    wire rst_rl_121;
    ot_dp_rrelay u_rrl_121 (.clk(clk), .d(rst_rl_120), .q(rst_rl_121));  // pad tap 39 depth 5 @ (721.4, 801.1)
    wire rst_rl_122;
    ot_dp_rrelay u_rrl_122 (.clk(clk), .d(rst_rl_121), .q(rst_rl_122));  // pad tap 39 depth 6 @ (721.4, 801.1)
    ot_dp_rrelay u_rrl_123 (.clk(clk), .d(rst_rl_122), .q(rst_n_t39));  // pad tap 39 depth 7 @ (721.4, 801.1)
    wire rst_rl_124;
    ot_dp_rrelay u_rrl_124 (.clk(clk), .d(rst_rl_119), .q(rst_rl_124));  // tap tap 25 depth 4 @ (721.4, 424.3)
    wire rst_rl_125;
    ot_dp_rrelay u_rrl_125 (.clk(clk), .d(rst_rl_124), .q(rst_rl_125));  // pad tap 25 depth 5 @ (721.4, 424.3)
    wire rst_rl_126;
    ot_dp_rrelay u_rrl_126 (.clk(clk), .d(rst_rl_125), .q(rst_rl_126));  // pad tap 25 depth 6 @ (721.4, 424.3)
    ot_dp_rrelay u_rrl_127 (.clk(clk), .d(rst_rl_126), .q(rst_n_t25));  // pad tap 25 depth 7 @ (721.4, 424.3)
    wire rst_rl_128;
    ot_dp_rrelay u_rrl_128 (.clk(clk), .d(rst_rl_124), .q(rst_rl_128));  // pad tap 4 depth 5 @ (721.4, 52.7)
    wire rst_rl_129;
    ot_dp_rrelay u_rrl_129 (.clk(clk), .d(rst_rl_128), .q(rst_rl_129));  // pad tap 4 depth 6 @ (721.4, 52.7)
    ot_dp_rrelay u_rrl_130 (.clk(clk), .d(rst_rl_129), .q(rst_n_t4));  // tap tap 4 depth 7 @ (721.4, 52.7)
    wire rst_rl_131;
    ot_dp_rrelay u_rrl_131 (.clk(clk), .d(rst_rl_124), .q(rst_rl_131));  // pad tap 9 depth 5 @ (721.4, 113.2)
    wire rst_rl_132;
    ot_dp_rrelay u_rrl_132 (.clk(clk), .d(rst_rl_131), .q(rst_rl_132));  // pad tap 9 depth 6 @ (721.4, 113.2)
    ot_dp_rrelay u_rrl_133 (.clk(clk), .d(rst_rl_132), .q(rst_n_t9));  // tap tap 9 depth 7 @ (721.4, 113.2)
    wire rst_rl_134;
    ot_dp_rrelay u_rrl_134 (.clk(clk), .d(rst_rl_124), .q(rst_rl_134));  // pad tap 20 depth 5 @ (505.5, 298.1)
    wire rst_rl_135;
    ot_dp_rrelay u_rrl_135 (.clk(clk), .d(rst_rl_134), .q(rst_rl_135));  // pad tap 20 depth 6 @ (505.5, 298.1)
    ot_dp_rrelay u_rrl_136 (.clk(clk), .d(rst_rl_135), .q(rst_n_t20));  // tap tap 20 depth 7 @ (505.5, 298.1)
    wire rst_rl_137;
    ot_dp_rrelay u_rrl_137 (.clk(clk), .d(rst_rl_124), .q(rst_rl_137));  // tap tap 24 depth 5 @ (361.0, 423.9)
    wire rst_rl_138;
    ot_dp_rrelay u_rrl_138 (.clk(clk), .d(rst_rl_137), .q(rst_rl_138));  // pad tap 24 depth 6 @ (361.0, 423.9)
    ot_dp_rrelay u_rrl_139 (.clk(clk), .d(rst_rl_138), .q(rst_n_t24));  // pad tap 24 depth 7 @ (361.0, 423.9)
    wire rst_rl_140;
    ot_dp_rrelay u_rrl_140 (.clk(clk), .d(rst_rl_137), .q(rst_rl_140));  // tap tap 7 depth 6 @ (360.7, 53.1)
    ot_dp_rrelay u_rrl_141 (.clk(clk), .d(rst_rl_140), .q(rst_n_t7));  // pad tap 7 depth 7 @ (360.7, 53.1)
    ot_dp_rrelay u_rrl_142 (.clk(clk), .d(rst_rl_140), .q(rst_n_t6));  // tap tap 6 depth 7 @ (17.3, 52.7)
    wire rst_rl_143;
    ot_dp_rrelay u_rrl_143 (.clk(clk), .d(rst_rl_137), .q(rst_rl_143));  // pad tap 27 depth 6 @ (17.3, 424.7)
    ot_dp_rrelay u_rrl_144 (.clk(clk), .d(rst_rl_143), .q(rst_n_t27));  // tap tap 27 depth 7 @ (17.3, 424.7)
    wire rst_rl_145;
    ot_dp_rrelay u_rrl_145 (.clk(clk), .d(rst_rl_124), .q(rst_rl_145));  // pad tap None depth 5 @ (346.6, 424.3)
    wire rst_rl_146;
    ot_dp_rrelay u_rrl_146 (.clk(clk), .d(rst_rl_145), .q(rst_rl_146));  // wire tap None depth 6 @ (346.6, 424.3)
    ot_dp_rrelay u_rrl_147 (.clk(clk), .d(rst_rl_146), .q(rst_n_t22));  // tap tap 22 depth 7 @ (89.4, 306.7)
    wire rst_rl_148;
    ot_dp_rrelay u_rrl_148 (.clk(clk), .d(rst_rl_113), .q(rst_rl_148));  // pad tap None depth 3 @ (1081.7, 432.3)
    wire rst_rl_149;
    ot_dp_rrelay u_rrl_149 (.clk(clk), .d(rst_rl_148), .q(rst_rl_149));  // pad tap None depth 4 @ (1081.7, 432.3)
    wire rst_rl_150;
    ot_dp_rrelay u_rrl_150 (.clk(clk), .d(rst_rl_149), .q(rst_rl_150));  // pad tap None depth 5 @ (1081.7, 432.3)
    wire rst_rl_151;
    ot_dp_rrelay u_rrl_151 (.clk(clk), .d(rst_rl_150), .q(rst_rl_151));  // wire tap None depth 6 @ (1081.7, 432.3)
    ot_dp_rrelay u_rrl_152 (.clk(clk), .d(rst_rl_151), .q(rst_n_t5));  // tap tap 5 depth 7 @ (1081.7, 52.7)
assign observations[0]=rst_n_t0;
assign observations[1]=rst_n_t1;
assign observations[2]=rst_n_t2;
assign observations[3]=rst_n_t3;
assign observations[4]=rst_n_t4;
assign observations[5]=rst_n_t5;
assign observations[6]=rst_n_t6;
assign observations[7]=rst_n_t7;
assign observations[8]=rst_n_t8;
assign observations[9]=rst_n_t9;
assign observations[10]=rst_n_t10;
assign observations[11]=rst_n_t11;
assign observations[12]=rst_n_t12;
assign observations[13]=rst_n_t13;
assign observations[14]=rst_n_t14;
assign observations[15]=rst_n_t15;
assign observations[16]=rst_n_t16;
assign observations[17]=rst_n_t17;
assign observations[18]=rst_n_t18;
assign observations[19]=rst_n_t19;
assign observations[20]=rst_n_t20;
assign observations[21]=rst_n_t21;
assign observations[22]=rst_n_t22;
assign observations[23]=rst_n_t23;
assign observations[24]=rst_n_t24;
assign observations[25]=rst_n_t25;
assign observations[26]=rst_n_t26;
assign observations[27]=rst_n_t27;
assign observations[28]=rst_n_t28;
assign observations[29]=rst_n_t29;
assign observations[30]=rst_n_t30;
assign observations[31]=rst_n_t31;
assign observations[32]=rst_n_t32;
assign observations[33]=rst_n_t33;
assign observations[34]=rst_n_t34;
assign observations[35]=rst_n_t35;
assign observations[36]=rst_n_t36;
assign observations[37]=rst_n_t37;
assign observations[38]=rst_n_t38;
assign observations[39]=rst_n_t39;
assign observations[40]=rst_n_t40;
assign observations[41]=rst_n_t41;
assign observations[42]=rst_n_t42;
endmodule
module mutant_tree(input wire clk,input wire arst_n,output wire[42:0] observations,output wire rst_o_0);
    // OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree, depth 7 to all 43 taps, hops <= 405 um; release 8 clocks after the entry pin
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (die reset tree)
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    wire rst_n_t8;
    wire rst_n_t9;
    wire rst_n_t10;
    wire rst_n_t11;
    wire rst_n_t12;
    wire rst_n_t13;
    wire rst_n_t14;
    wire rst_n_t15;
    wire rst_n_t16;
    wire rst_n_t17;
    wire rst_n_t18;
    wire rst_n_t19;
    wire rst_n_t20;
    wire rst_n_t21;
    wire rst_n_t22;
    wire rst_n_t23;
    wire rst_n_t24;
    wire rst_n_t25;
    wire rst_n_t26;
    wire rst_n_t27;
    wire rst_n_t28;
    wire rst_n_t29;
    wire rst_n_t30;
    wire rst_n_t31;
    wire rst_n_t32;
    wire rst_n_t33;
    wire rst_n_t34;
    wire rst_n_t35;
    wire rst_n_t36;
    wire rst_n_t37;
    wire rst_n_t38;
    wire rst_n_t39;
    wire rst_n_t40;
    wire rst_n_t41;
    wire rst_n_t42;
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // pad tap 34 depth 1 @ (1425.6, 1209.6)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // pad tap 34 depth 2 @ (1425.6, 1209.6)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // pad tap 34 depth 3 @ (1425.6, 1209.6)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // pad tap 34 depth 4 @ (1425.6, 1209.6)
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));  // pad tap 34 depth 5 @ (1425.6, 1209.6)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));  // pad tap 34 depth 6 @ (1425.6, 1209.6)
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t34));  // tap tap 34 depth 7 @ (1425.6, 1209.6)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_root_n), .q(rst_rl_7));  // tap tap 35 depth 1 @ (1425.6, 871.1)
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));  // pad tap 35 depth 2 @ (1425.6, 871.1)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));  // pad tap 35 depth 3 @ (1425.6, 871.1)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // pad tap 35 depth 4 @ (1425.6, 871.1)
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));  // pad tap 35 depth 5 @ (1425.6, 871.1)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));  // pad tap 35 depth 6 @ (1425.6, 871.1)
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_n_t35));  // pad tap 35 depth 7 @ (1425.6, 871.1)
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_7), .q(rst_rl_14));  // tap tap 30 depth 2 @ (1425.6, 514.8)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));  // pad tap 30 depth 3 @ (1425.6, 514.8)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // pad tap 30 depth 4 @ (1425.6, 514.8)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // pad tap 30 depth 5 @ (1425.6, 514.8)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // pad tap 30 depth 6 @ (1425.6, 514.8)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t30));  // pad tap 30 depth 7 @ (1425.6, 514.8)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_14), .q(rst_rl_20));  // tap tap 14 depth 3 @ (1425.6, 185.2)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));  // pad tap 14 depth 4 @ (1425.6, 185.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // pad tap 14 depth 5 @ (1425.6, 185.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // pad tap 14 depth 6 @ (1425.6, 185.2)
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_n_t14));  // pad tap 14 depth 7 @ (1425.6, 185.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_20), .q(rst_rl_25));  // tap tap 12 depth 4 @ (1101.9, 174.0)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));  // pad tap 12 depth 5 @ (1101.9, 174.0)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // pad tap 12 depth 6 @ (1101.9, 174.0)
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_n_t12));  // pad tap 12 depth 7 @ (1101.9, 174.0)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_25), .q(rst_rl_29));  // pad tap 13 depth 5 @ (769.0, 183.5)
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));  // tap tap 13 depth 6 @ (769.0, 183.5)
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_n_t13));  // pad tap 13 depth 7 @ (769.0, 183.5)
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_30), .q(rst_n_t11));  // tap tap 11 depth 7 @ (457.6, 164.9)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_25), .q(rst_rl_33));  // wire tap None depth 5 @ (745.3, 174.0)
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));  // tap tap 3 depth 6 @ (545.4, 17.3)
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_n_t3));  // pad tap 3 depth 7 @ (545.4, 17.3)
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_34), .q(rst_o_0));  // registered reset out rst_o_0 (wavefront, dedicated relay): tap tap 41 depth 7 @ (180.4, 8.6)
    ot_dp_rrelay u_rrl_36_t (.clk(clk), .d(rst_rl_34), .q(rst_n_t41));  // tap-net copy of u_rrl_36 for in-type loads: depth 7 @ (180.4, 8.6)
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_25), .q(rst_rl_37));  // pad tap None depth 5 @ (738.8, 174.0)
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));  // wire tap None depth 6 @ (738.8, 174.0)
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_o_1));  // registered reset out rst_o_1 (wavefront, dedicated relay): tap tap 42 depth 7 @ (541.1, 8.6)
    ot_dp_rrelay u_rrl_39_t (.clk(clk), .d(rst_rl_38), .q(rst_n_t42));  // tap-net copy of u_rrl_39 for in-type loads: depth 7 @ (541.1, 8.6)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_14), .q(rst_rl_40));  // pad tap 17 depth 3 @ (1425.6, 297.3)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // pad tap 17 depth 4 @ (1425.6, 297.3)
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));  // tap tap 17 depth 5 @ (1425.6, 297.3)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));  // pad tap 17 depth 6 @ (1425.6, 297.3)
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t17));  // pad tap 17 depth 7 @ (1425.6, 297.3)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_42), .q(rst_rl_45));  // tap tap 19 depth 6 @ (1129.8, 298.1)
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_n_t19));  // pad tap 19 depth 7 @ (1129.8, 298.1)
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_45), .q(rst_n_t18));  // tap tap 18 depth 7 @ (817.6, 298.1)
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_14), .q(rst_rl_48));  // pad tap 23 depth 3 @ (1425.6, 423.5)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));  // pad tap 23 depth 4 @ (1425.6, 423.5)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));  // pad tap 23 depth 5 @ (1425.6, 423.5)
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));  // tap tap 23 depth 6 @ (1425.6, 423.5)
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_n_t23));  // pad tap 23 depth 7 @ (1425.6, 423.5)
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_51), .q(rst_n_t8));  // tap tap 8 depth 7 @ (1425.6, 53.4)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_14), .q(rst_rl_54));  // tap tap 29 depth 3 @ (1082.2, 514.8)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));  // pad tap 29 depth 4 @ (1082.2, 514.8)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // pad tap 29 depth 5 @ (1082.2, 514.8)
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));  // pad tap 29 depth 6 @ (1082.2, 514.8)
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_n_t29));  // pad tap 29 depth 7 @ (1082.2, 514.8)
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_54), .q(rst_rl_59));  // tap tap 0 depth 4 @ (721.4, 514.8)
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_rl_60));  // pad tap 0 depth 5 @ (721.4, 514.8)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));  // pad tap 0 depth 6 @ (721.4, 514.8)
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_n_t0));  // pad tap 0 depth 7 @ (721.4, 514.8)
    wire rst_rl_63;
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_59), .q(rst_rl_63));  // tap tap 28 depth 5 @ (360.7, 514.8)
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_63), .q(rst_rl_64));  // pad tap 28 depth 6 @ (360.7, 514.8)
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_n_t28));  // pad tap 28 depth 7 @ (360.7, 514.8)
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_63), .q(rst_rl_66));  // tap tap 15 depth 6 @ (403.6, 199.5)
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_n_t15));  // pad tap 15 depth 7 @ (403.6, 199.5)
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_66), .q(rst_n_t2));  // tap tap 2 depth 7 @ (207.3, 17.3)
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_63), .q(rst_rl_69));  // wire tap None depth 6 @ (147.9, 372.5)
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_n_t1));  // tap tap 1 depth 7 @ (147.9, 17.3)
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_59), .q(rst_rl_71));  // pad tap None depth 5 @ (348.9, 514.8)
    wire rst_rl_72;
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_rl_72));  // wire tap None depth 6 @ (348.9, 514.8)
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_rl_71), .q(rst_n_t16));  // tap tap 16 depth 7 @ (197.1, 294.1)
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_54), .q(rst_rl_74));  // pad tap 26 depth 4 @ (1081.7, 424.3)
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_rl_75));  // pad tap 26 depth 5 @ (1081.7, 424.3)
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_rl_76));  // pad tap 26 depth 6 @ (1081.7, 424.3)
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_n_t26));  // tap tap 26 depth 7 @ (1081.7, 424.3)
    wire rst_rl_78;
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_7), .q(rst_rl_78));  // pad tap None depth 2 @ (1425.6, 493.0)
    wire rst_rl_79;
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_rl_78), .q(rst_rl_79));  // pad tap None depth 3 @ (1425.6, 493.0)
    wire rst_rl_80;
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_79), .q(rst_rl_80));  // pad tap None depth 4 @ (1425.6, 493.0)
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_rl_80), .q(rst_rl_81));  // pad tap None depth 5 @ (1425.6, 493.0)
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));  // wire tap None depth 6 @ (1425.6, 493.0)
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_n_t10));  // tap tap 10 depth 7 @ (1425.6, 115.0)
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_root_n), .q(rst_rl_84));  // tap tap 36 depth 1 @ (1089.3, 1209.6)
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_rl_85));  // pad tap 36 depth 2 @ (1089.3, 1209.6)
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));  // pad tap 36 depth 3 @ (1089.3, 1209.6)
    wire rst_rl_87;
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_rl_87));  // pad tap 36 depth 4 @ (1089.3, 1209.6)
    wire rst_rl_88;
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_87), .q(rst_rl_88));  // pad tap 36 depth 5 @ (1089.3, 1209.6)
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_rl_88), .q(rst_rl_89));  // pad tap 36 depth 6 @ (1089.3, 1209.6)
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_n_t36));  // pad tap 36 depth 7 @ (1089.3, 1209.6)
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_84), .q(rst_rl_91));  // tap tap 37 depth 2 @ (743.9, 1209.6)
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_rl_92));  // pad tap 37 depth 3 @ (743.9, 1209.6)
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));  // pad tap 37 depth 4 @ (743.9, 1209.6)
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));  // pad tap 37 depth 5 @ (743.9, 1209.6)
    wire rst_rl_95;
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_rl_95));  // pad tap 37 depth 6 @ (743.9, 1209.6)
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_95), .q(rst_n_t37));  // pad tap 37 depth 7 @ (743.9, 1209.6)
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_91), .q(rst_rl_97));  // tap tap 38 depth 3 @ (398.5, 1209.6)
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));  // pad tap 38 depth 4 @ (398.5, 1209.6)
    wire rst_rl_99;
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_rl_99));  // pad tap 38 depth 5 @ (398.5, 1209.6)
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_99), .q(rst_rl_100));  // pad tap 38 depth 6 @ (398.5, 1209.6)
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_n_t38));  // pad tap 38 depth 7 @ (398.5, 1209.6)
    wire rst_rl_102;
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_97), .q(rst_rl_102));  // tap tap 33 depth 4 @ (61.7, 1209.6)
    wire rst_rl_103;
    ot_dp_rrelay u_rrl_103 (.clk(clk), .d(rst_rl_102), .q(rst_rl_103));  // pad tap 33 depth 5 @ (61.7, 1209.6)
    wire rst_rl_104;
    ot_dp_rrelay u_rrl_104 (.clk(clk), .d(rst_rl_103), .q(rst_rl_104));  // pad tap 33 depth 6 @ (61.7, 1209.6)
    ot_dp_rrelay u_rrl_105 (.clk(clk), .d(rst_rl_104), .q(rst_n_t33));  // pad tap 33 depth 7 @ (61.7, 1209.6)
    wire rst_rl_106;
    ot_dp_rrelay u_rrl_106 (.clk(clk), .d(rst_rl_102), .q(rst_rl_106));  // tap tap 32 depth 5 @ (61.7, 920.2)
    wire rst_rl_107;
    ot_dp_rrelay u_rrl_107 (.clk(clk), .d(rst_rl_106), .q(rst_rl_107));  // pad tap 32 depth 6 @ (61.7, 920.2)
    ot_dp_rrelay u_rrl_108 (.clk(clk), .d(rst_rl_107), .q(rst_n_t32));  // pad tap 32 depth 7 @ (61.7, 920.2)
    wire rst_rl_109;
    ot_dp_rrelay u_rrl_109 (.clk(clk), .d(rst_rl_106), .q(rst_rl_109));  // tap tap 31 depth 6 @ (61.7, 613.4)
    ot_dp_rrelay u_rrl_110 (.clk(clk), .d(rst_rl_109), .q(rst_n_t31));  // pad tap 31 depth 7 @ (61.7, 613.4)
    ot_dp_rrelay u_rrl_111 (.clk(clk), .d(rst_rl_109), .q(rst_n_t21));  // tap tap 21 depth 7 @ (33.2, 306.7)
    wire rst_rl_112;
    ot_dp_rrelay u_rrl_112 (.clk(clk), .d(rst_root_n), .q(rst_rl_112));  // wire tap None depth 1 @ (1081.7, 1191.6)
    wire rst_rl_113;
    ot_dp_rrelay u_rrl_113 (.clk(clk), .d(rst_rl_112), .q(rst_rl_113));  // tap tap 40 depth 2 @ (1081.7, 812.0)
    wire rst_rl_114;
    ot_dp_rrelay u_rrl_114 (.clk(clk), .d(rst_rl_113), .q(rst_rl_114));  // pad tap 40 depth 3 @ (1081.7, 812.0)
    wire rst_rl_115;
    ot_dp_rrelay u_rrl_115 (.clk(clk), .d(rst_rl_114), .q(rst_rl_115));  // pad tap 40 depth 4 @ (1081.7, 812.0)
    wire rst_rl_116;
    ot_dp_rrelay u_rrl_116 (.clk(clk), .d(rst_rl_115), .q(rst_rl_116));  // pad tap 40 depth 5 @ (1081.7, 812.0)
    wire rst_rl_117;
    ot_dp_rrelay u_rrl_117 (.clk(clk), .d(rst_rl_116), .q(rst_rl_117));  // pad tap 40 depth 6 @ (1081.7, 812.0)
    ot_dp_rrelay u_rrl_118 (.clk(clk), .d(rst_rl_117), .q(rst_n_t40));  // pad tap 40 depth 7 @ (1081.7, 812.0)
    wire rst_rl_119;
    ot_dp_rrelay u_rrl_119 (.clk(clk), .d(rst_rl_113), .q(rst_rl_119));  // tap tap 39 depth 3 @ (721.4, 801.1)
    wire rst_rl_120;
    ot_dp_rrelay u_rrl_120 (.clk(clk), .d(rst_rl_119), .q(rst_rl_120));  // pad tap 39 depth 4 @ (721.4, 801.1)
    wire rst_rl_121;
    ot_dp_rrelay u_rrl_121 (.clk(clk), .d(rst_rl_120), .q(rst_rl_121));  // pad tap 39 depth 5 @ (721.4, 801.1)
    wire rst_rl_122;
    ot_dp_rrelay u_rrl_122 (.clk(clk), .d(rst_rl_121), .q(rst_rl_122));  // pad tap 39 depth 6 @ (721.4, 801.1)
    ot_dp_rrelay u_rrl_123 (.clk(clk), .d(rst_rl_122), .q(rst_n_t39));  // pad tap 39 depth 7 @ (721.4, 801.1)
    wire rst_rl_124;
    ot_dp_rrelay u_rrl_124 (.clk(clk), .d(rst_rl_119), .q(rst_rl_124));  // tap tap 25 depth 4 @ (721.4, 424.3)
    wire rst_rl_125;
    ot_dp_rrelay u_rrl_125 (.clk(clk), .d(rst_rl_124), .q(rst_rl_125));  // pad tap 25 depth 5 @ (721.4, 424.3)
    wire rst_rl_126;
    ot_dp_rrelay u_rrl_126 (.clk(clk), .d(rst_rl_125), .q(rst_rl_126));  // pad tap 25 depth 6 @ (721.4, 424.3)
    ot_dp_rrelay u_rrl_127 (.clk(clk), .d(rst_rl_126), .q(rst_n_t25));  // pad tap 25 depth 7 @ (721.4, 424.3)
    wire rst_rl_128;
    ot_dp_rrelay u_rrl_128 (.clk(clk), .d(rst_rl_124), .q(rst_rl_128));  // pad tap 4 depth 5 @ (721.4, 52.7)
    wire rst_rl_129;
    ot_dp_rrelay u_rrl_129 (.clk(clk), .d(rst_rl_128), .q(rst_rl_129));  // pad tap 4 depth 6 @ (721.4, 52.7)
    ot_dp_rrelay u_rrl_130 (.clk(clk), .d(rst_rl_129), .q(rst_n_t4));  // tap tap 4 depth 7 @ (721.4, 52.7)
    wire rst_rl_131;
    ot_dp_rrelay u_rrl_131 (.clk(clk), .d(rst_rl_124), .q(rst_rl_131));  // pad tap 9 depth 5 @ (721.4, 113.2)
    wire rst_rl_132;
    ot_dp_rrelay u_rrl_132 (.clk(clk), .d(rst_rl_131), .q(rst_rl_132));  // pad tap 9 depth 6 @ (721.4, 113.2)
    ot_dp_rrelay u_rrl_133 (.clk(clk), .d(rst_rl_132), .q(rst_n_t9));  // tap tap 9 depth 7 @ (721.4, 113.2)
    wire rst_rl_134;
    ot_dp_rrelay u_rrl_134 (.clk(clk), .d(rst_rl_124), .q(rst_rl_134));  // pad tap 20 depth 5 @ (505.5, 298.1)
    wire rst_rl_135;
    ot_dp_rrelay u_rrl_135 (.clk(clk), .d(rst_rl_134), .q(rst_rl_135));  // pad tap 20 depth 6 @ (505.5, 298.1)
    ot_dp_rrelay u_rrl_136 (.clk(clk), .d(rst_rl_135), .q(rst_n_t20));  // tap tap 20 depth 7 @ (505.5, 298.1)
    wire rst_rl_137;
    ot_dp_rrelay u_rrl_137 (.clk(clk), .d(rst_rl_124), .q(rst_rl_137));  // tap tap 24 depth 5 @ (361.0, 423.9)
    wire rst_rl_138;
    ot_dp_rrelay u_rrl_138 (.clk(clk), .d(rst_rl_137), .q(rst_rl_138));  // pad tap 24 depth 6 @ (361.0, 423.9)
    ot_dp_rrelay u_rrl_139 (.clk(clk), .d(rst_rl_138), .q(rst_n_t24));  // pad tap 24 depth 7 @ (361.0, 423.9)
    wire rst_rl_140;
    ot_dp_rrelay u_rrl_140 (.clk(clk), .d(rst_rl_137), .q(rst_rl_140));  // tap tap 7 depth 6 @ (360.7, 53.1)
    ot_dp_rrelay u_rrl_141 (.clk(clk), .d(rst_rl_140), .q(rst_n_t7));  // pad tap 7 depth 7 @ (360.7, 53.1)
    ot_dp_rrelay u_rrl_142 (.clk(clk), .d(rst_rl_140), .q(rst_n_t6));  // tap tap 6 depth 7 @ (17.3, 52.7)
    wire rst_rl_143;
    ot_dp_rrelay u_rrl_143 (.clk(clk), .d(rst_rl_137), .q(rst_rl_143));  // pad tap 27 depth 6 @ (17.3, 424.7)
    ot_dp_rrelay u_rrl_144 (.clk(clk), .d(rst_rl_143), .q(rst_n_t27));  // tap tap 27 depth 7 @ (17.3, 424.7)
    wire rst_rl_145;
    ot_dp_rrelay u_rrl_145 (.clk(clk), .d(rst_rl_124), .q(rst_rl_145));  // pad tap None depth 5 @ (346.6, 424.3)
    wire rst_rl_146;
    ot_dp_rrelay u_rrl_146 (.clk(clk), .d(rst_rl_145), .q(rst_rl_146));  // wire tap None depth 6 @ (346.6, 424.3)
    ot_dp_rrelay u_rrl_147 (.clk(clk), .d(rst_rl_146), .q(rst_n_t22));  // tap tap 22 depth 7 @ (89.4, 306.7)
    wire rst_rl_148;
    ot_dp_rrelay u_rrl_148 (.clk(clk), .d(rst_rl_113), .q(rst_rl_148));  // pad tap None depth 3 @ (1081.7, 432.3)
    wire rst_rl_149;
    ot_dp_rrelay u_rrl_149 (.clk(clk), .d(rst_rl_148), .q(rst_rl_149));  // pad tap None depth 4 @ (1081.7, 432.3)
    wire rst_rl_150;
    ot_dp_rrelay u_rrl_150 (.clk(clk), .d(rst_rl_149), .q(rst_rl_150));  // pad tap None depth 5 @ (1081.7, 432.3)
    wire rst_rl_151;
    ot_dp_rrelay u_rrl_151 (.clk(clk), .d(rst_rl_150), .q(rst_rl_151));  // wire tap None depth 6 @ (1081.7, 432.3)
    ot_dp_rrelay u_rrl_152 (.clk(clk), .d(rst_rl_151), .q(rst_n_t5));  // tap tap 5 depth 7 @ (1081.7, 52.7)
assign observations[0]=rst_n_t0;
assign observations[1]=rst_n_t1;
assign observations[2]=rst_n_t2;
assign observations[3]=rst_n_t3;
assign observations[4]=rst_n_t4;
assign observations[5]=rst_n_t5;
assign observations[6]=rst_n_t6;
assign observations[7]=rst_n_t7;
assign observations[8]=rst_n_t8;
assign observations[9]=rst_n_t9;
assign observations[10]=rst_n_t10;
assign observations[11]=rst_n_t11;
assign observations[12]=rst_n_t12;
assign observations[13]=rst_n_t13;
assign observations[14]=rst_n_t14;
assign observations[15]=rst_n_t15;
assign observations[16]=rst_n_t16;
assign observations[17]=rst_n_t17;
assign observations[18]=rst_n_t18;
assign observations[19]=rst_n_t19;
assign observations[20]=rst_n_t20;
assign observations[21]=rst_n_t21;
assign observations[22]=rst_n_t22;
assign observations[23]=rst_n_t23;
assign observations[24]=rst_n_t24;
assign observations[25]=rst_n_t25;
assign observations[26]=rst_n_t26;
assign observations[27]=rst_n_t27;
assign observations[28]=rst_n_t28;
assign observations[29]=rst_n_t29;
assign observations[30]=rst_n_t30;
assign observations[31]=rst_n_t31;
assign observations[32]=rst_n_t32;
assign observations[33]=rst_n_t33;
assign observations[34]=rst_n_t34;
assign observations[35]=rst_n_t35;
assign observations[36]=rst_n_t36;
assign observations[37]=rst_n_t37;
assign observations[38]=rst_n_t38;
assign observations[39]=rst_n_t39;
assign observations[40]=rst_n_t40;
assign observations[41]=rst_n_t41;
assign observations[42]=rst_n_t42;
endmodule
