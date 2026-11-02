    // OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree, depth 6 to all 44 taps, hops <= 405 um; release 7 clocks after the entry pin
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
    wire rst_n_t43;
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // pad tap 11 depth 1 @ (1262.5, 766.8)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // pad tap 11 depth 2 @ (1262.5, 766.8)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // tap tap 11 depth 3 @ (1262.5, 766.8)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // pad tap 11 depth 4 @ (1262.5, 766.8)
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));  // pad tap 11 depth 5 @ (1262.5, 766.8)
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_n_t11));  // pad tap 11 depth 6 @ (1262.5, 766.8)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_2), .q(rst_rl_6));  // tap tap 10 depth 4 @ (901.8, 766.8)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // pad tap 10 depth 5 @ (901.8, 766.8)
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_n_t10));  // pad tap 10 depth 6 @ (901.8, 766.8)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_6), .q(rst_rl_9));  // tap tap 9 depth 5 @ (541.1, 766.8)
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_n_t9));  // pad tap 9 depth 6 @ (541.1, 766.8)
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_9), .q(rst_n_t8));  // tap tap 8 depth 6 @ (180.4, 766.8)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_2), .q(rst_rl_12));  // wire tap None depth 4 @ (972.0, 781.9)
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));  // pad tap 31 depth 5 @ (673.9, 853.5)
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_n_t31));  // tap tap 31 depth 6 @ (673.9, 853.5)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_12), .q(rst_rl_15));  // wire tap None depth 5 @ (678.2, 853.5)
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_n_t13));  // tap tap 13 depth 6 @ (564.8, 1073.5)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_2), .q(rst_rl_17));  // wire tap None depth 4 @ (920.2, 781.9)
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));  // wire tap None depth 5 @ (548.6, 781.9)
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t33));  // tap tap 33 depth 6 @ (275.1, 881.3)
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_18), .q(rst_n_t42));  // tap tap 42 depth 6 @ (275.1, 885.6)
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_root_n), .q(rst_rl_21));  // pad tap 18 depth 1 @ (1425.6, 920.2)
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));  // tap tap 18 depth 2 @ (1425.6, 920.2)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));  // pad tap 18 depth 3 @ (1425.6, 920.2)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // pad tap 18 depth 4 @ (1425.6, 920.2)
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));  // pad tap 18 depth 5 @ (1425.6, 920.2)
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_n_t18));  // pad tap 18 depth 6 @ (1425.6, 920.2)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_22), .q(rst_rl_27));  // pad tap 15 depth 3 @ (1262.5, 1073.5)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // pad tap 15 depth 4 @ (1262.5, 1073.5)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // pad tap 15 depth 5 @ (1262.5, 1073.5)
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t15));  // tap tap 15 depth 6 @ (1262.5, 1073.5)
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_22), .q(rst_rl_31));  // tap tap 28 depth 3 @ (1126.4, 980.6)
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_rl_32));  // pad tap 28 depth 4 @ (1126.4, 980.6)
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));  // pad tap 28 depth 5 @ (1126.4, 980.6)
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_n_t28));  // pad tap 28 depth 6 @ (1126.4, 980.6)
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_31), .q(rst_rl_35));  // wire tap None depth 4 @ (885.5, 1115.6)
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));  // wire tap None depth 5 @ (513.9, 1115.6)
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_n_t12));  // tap tap 12 depth 6 @ (180.4, 1121.0)
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_36), .q(rst_n_t37));  // tap tap 37 depth 6 @ (162.2, 1122.0)
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_22), .q(rst_rl_39));  // pad tap None depth 3 @ (1213.9, 1058.4)
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));  // pad tap None depth 4 @ (1213.9, 1058.4)
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));  // wire tap None depth 5 @ (1213.9, 1058.4)
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_n_t14));  // tap tap 14 depth 6 @ (901.8, 1121.0)
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_root_n), .q(rst_rl_43));  // pad tap 19 depth 1 @ (1425.6, 574.3)
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));  // pad tap 19 depth 2 @ (1425.6, 574.3)
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_rl_45));  // tap tap 19 depth 3 @ (1425.6, 574.3)
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));  // pad tap 19 depth 4 @ (1425.6, 574.3)
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));  // pad tap 19 depth 5 @ (1425.6, 574.3)
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_n_t19));  // pad tap 19 depth 6 @ (1425.6, 574.3)
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_45), .q(rst_rl_49));  // wire tap None depth 4 @ (1144.3, 479.3)
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));  // pad tap 6 depth 5 @ (901.8, 457.9)
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_n_t6));  // tap tap 6 depth 6 @ (901.8, 457.9)
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_49), .q(rst_rl_52));  // wire tap None depth 5 @ (1049.3, 194.3)
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_n_t36));  // tap tap 36 depth 6 @ (864.5, 17.3)
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_root_n), .q(rst_rl_54));  // pad tap 35 depth 1 @ (1425.6, 744.2)
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));  // pad tap 35 depth 2 @ (1425.6, 744.2)
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));  // pad tap 35 depth 3 @ (1425.6, 744.2)
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));  // pad tap 35 depth 4 @ (1425.6, 744.2)
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_rl_58));  // pad tap 35 depth 5 @ (1425.6, 744.2)
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_n_t35));  // tap tap 35 depth 6 @ (1425.6, 744.2)
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_root_n), .q(rst_rl_60));  // wire tap None depth 1 @ (1429.3, 574.3)
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));  // pad tap 27 depth 2 @ (1386.7, 304.6)
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));  // pad tap 27 depth 3 @ (1386.7, 304.6)
    wire rst_rl_63;
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_rl_63));  // pad tap 27 depth 4 @ (1386.7, 304.6)
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_63), .q(rst_rl_64));  // pad tap 27 depth 5 @ (1386.7, 304.6)
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_n_t27));  // tap tap 27 depth 6 @ (1386.7, 304.6)
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_60), .q(rst_rl_66));  // wire tap None depth 2 @ (1386.7, 298.1)
    wire rst_rl_67;
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_rl_67));  // wire tap None depth 3 @ (1162.1, 289.4)
    wire rst_rl_68;
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_67), .q(rst_rl_68));  // pad tap 2 depth 4 @ (901.8, 177.1)
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_68), .q(rst_rl_69));  // pad tap 2 depth 5 @ (901.8, 177.1)
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_n_t2));  // tap tap 2 depth 6 @ (901.8, 177.1)
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_67), .q(rst_rl_71));  // wire tap None depth 4 @ (885.5, 211.7)
    wire rst_rl_72;
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_rl_72));  // wire tap None depth 5 @ (513.9, 211.7)
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_rl_72), .q(rst_n_t0));  // tap tap 0 depth 6 @ (180.4, 177.1)
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_root_n), .q(rst_rl_74));  // pad tap None depth 1 @ (1334.3, 764.3)
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_rl_75));  // wire tap None depth 2 @ (1334.3, 764.3)
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_rl_76));  // wire tap None depth 3 @ (971.9, 756.0)
    wire rst_rl_77;
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_rl_77));  // wire tap None depth 4 @ (686.9, 738.6)
    wire rst_rl_78;
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_77), .q(rst_rl_78));  // wire tap None depth 5 @ (595.3, 453.6)
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_rl_78), .q(rst_n_t1));  // tap tap 1 depth 6 @ (541.1, 153.4)
    wire rst_rl_80;
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_75), .q(rst_rl_80));  // pad tap None depth 3 @ (1317.6, 453.6)
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_rl_80), .q(rst_rl_81));  // pad tap None depth 4 @ (1317.6, 453.6)
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));  // wire tap None depth 5 @ (1317.6, 453.6)
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_n_t3));  // tap tap 3 depth 6 @ (1262.5, 153.4)
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_root_n), .q(rst_rl_84));  // pad tap None depth 1 @ (1239.3, 764.3)
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_rl_85));  // wire tap None depth 2 @ (1239.3, 764.3)
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));  // pad tap 29 depth 3 @ (1157.8, 548.6)
    wire rst_rl_87;
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_rl_87));  // pad tap 29 depth 4 @ (1157.8, 548.6)
    wire rst_rl_88;
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_87), .q(rst_rl_88));  // pad tap 29 depth 5 @ (1157.8, 548.6)
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_rl_88), .q(rst_n_t29));  // tap tap 29 depth 6 @ (1157.8, 548.6)
    wire rst_rl_90;
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_85), .q(rst_rl_90));  // wire tap None depth 3 @ (1162.1, 548.6)
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_90), .q(rst_rl_91));  // wire tap None depth 4 @ (859.7, 505.4)
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_rl_92));  // pad tap 5 depth 5 @ (541.1, 460.1)
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_n_t5));  // tap tap 5 depth 6 @ (541.1, 460.1)
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_91), .q(rst_rl_94));  // wire tap None depth 5 @ (548.6, 453.6)
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_n_t4));  // tap tap 4 depth 6 @ (180.4, 449.3)
    wire rst_rl_96;
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_85), .q(rst_rl_96));  // wire tap None depth 3 @ (859.3, 764.3)
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_96), .q(rst_rl_97));  // tap tap 26 depth 4 @ (669.3, 574.3)
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));  // pad tap 26 depth 5 @ (669.3, 574.3)
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_n_t26));  // pad tap 26 depth 6 @ (669.3, 574.3)
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_97), .q(rst_rl_100));  // wire tap None depth 5 @ (558.4, 306.7)
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_n_t40));  // tap tap 40 depth 6 @ (275.1, 211.7)
    wire rst_rl_102;
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_root_n), .q(rst_rl_102));  // pad tap None depth 1 @ (1334.3, 669.3)
    wire rst_rl_103;
    ot_dp_rrelay u_rrl_103 (.clk(clk), .d(rst_rl_102), .q(rst_rl_103));  // pad tap None depth 2 @ (1334.3, 669.3)
    wire rst_rl_104;
    ot_dp_rrelay u_rrl_104 (.clk(clk), .d(rst_rl_103), .q(rst_rl_104));  // wire tap None depth 3 @ (1334.3, 669.3)
    wire rst_rl_105;
    ot_dp_rrelay u_rrl_105 (.clk(clk), .d(rst_rl_104), .q(rst_rl_105));  // pad tap 7 depth 4 @ (1262.5, 414.7)
    wire rst_rl_106;
    ot_dp_rrelay u_rrl_106 (.clk(clk), .d(rst_rl_105), .q(rst_rl_106));  // pad tap 7 depth 5 @ (1262.5, 414.7)
    ot_dp_rrelay u_rrl_107 (.clk(clk), .d(rst_rl_106), .q(rst_n_t7));  // tap tap 7 depth 6 @ (1262.5, 414.7)
    wire rst_rl_108;
    ot_dp_rrelay u_rrl_108 (.clk(clk), .d(rst_rl_104), .q(rst_rl_108));  // wire tap None depth 4 @ (1300.3, 375.8)
    wire rst_rl_109;
    ot_dp_rrelay u_rrl_109 (.clk(clk), .d(rst_rl_108), .q(rst_rl_109));  // pad tap 24 depth 5 @ (1126.4, 306.7)
    ot_dp_rrelay u_rrl_110 (.clk(clk), .d(rst_rl_109), .q(rst_n_t24));  // tap tap 24 depth 6 @ (1126.4, 306.7)
    wire rst_rl_111;
    ot_dp_rrelay u_rrl_111 (.clk(clk), .d(rst_rl_108), .q(rst_rl_111));  // wire tap None depth 5 @ (1120.0, 306.7)
    ot_dp_rrelay u_rrl_112 (.clk(clk), .d(rst_rl_111), .q(rst_n_t41));  // tap tap 41 depth 6 @ (836.7, 211.7)
    wire rst_rl_113;
    ot_dp_rrelay u_rrl_113 (.clk(clk), .d(rst_root_n), .q(rst_rl_113));  // wire tap None depth 1 @ (1118.9, 799.2)
    wire rst_rl_114;
    ot_dp_rrelay u_rrl_114 (.clk(clk), .d(rst_rl_113), .q(rst_rl_114));  // wire tap None depth 2 @ (833.8, 842.4)
    wire rst_rl_115;
    ot_dp_rrelay u_rrl_115 (.clk(clk), .d(rst_rl_114), .q(rst_rl_115));  // wire tap None depth 3 @ (488.2, 853.5)
    wire rst_rl_116;
    ot_dp_rrelay u_rrl_116 (.clk(clk), .d(rst_rl_115), .q(rst_rl_116));  // wire tap None depth 4 @ (146.0, 853.5)
    wire rst_rl_117;
    ot_dp_rrelay u_rrl_117 (.clk(clk), .d(rst_rl_116), .q(rst_rl_117));  // tap tap 16 depth 5 @ (17.3, 943.4)
    ot_dp_rrelay u_rrl_118 (.clk(clk), .d(rst_rl_117), .q(rst_n_t16));  // pad tap 16 depth 6 @ (17.3, 943.4)
    ot_dp_rrelay u_rrl_119 (.clk(clk), .d(rst_rl_117), .q(rst_n_t21));  // tap tap 21 depth 6 @ (17.3, 1209.6)
    wire rst_rl_120;
    ot_dp_rrelay u_rrl_120 (.clk(clk), .d(rst_root_n), .q(rst_rl_120));  // wire tap None depth 1 @ (1145.7, 756.0)
    wire rst_rl_121;
    ot_dp_rrelay u_rrl_121 (.clk(clk), .d(rst_rl_120), .q(rst_rl_121));  // wire tap None depth 2 @ (1144.3, 384.3)
    wire rst_rl_122;
    ot_dp_rrelay u_rrl_122 (.clk(clk), .d(rst_rl_121), .q(rst_rl_122));  // wire tap None depth 3 @ (954.3, 194.3)
    wire rst_rl_123;
    ot_dp_rrelay u_rrl_123 (.clk(clk), .d(rst_rl_122), .q(rst_rl_123));  // wire tap None depth 4 @ (574.3, 194.3)
    wire rst_rl_124;
    ot_dp_rrelay u_rrl_124 (.clk(clk), .d(rst_rl_123), .q(rst_rl_124));  // wire tap None depth 5 @ (220.3, 171.0)
    ot_dp_rrelay u_rrl_125 (.clk(clk), .d(rst_rl_124), .q(rst_n_t17));  // tap tap 17 depth 6 @ (17.3, 17.3)
    wire rst_rl_126;
    ot_dp_rrelay u_rrl_126 (.clk(clk), .d(rst_root_n), .q(rst_rl_126));  // pad tap None depth 1 @ (1429.3, 859.3)
    wire rst_rl_127;
    ot_dp_rrelay u_rrl_127 (.clk(clk), .d(rst_rl_126), .q(rst_rl_127));  // pad tap None depth 2 @ (1429.3, 859.3)
    wire rst_rl_128;
    ot_dp_rrelay u_rrl_128 (.clk(clk), .d(rst_rl_127), .q(rst_rl_128));  // pad tap None depth 3 @ (1429.3, 859.3)
    wire rst_rl_129;
    ot_dp_rrelay u_rrl_129 (.clk(clk), .d(rst_rl_128), .q(rst_rl_129));  // pad tap None depth 4 @ (1429.3, 859.3)
    wire rst_rl_130;
    ot_dp_rrelay u_rrl_130 (.clk(clk), .d(rst_rl_129), .q(rst_rl_130));  // wire tap None depth 5 @ (1429.3, 859.3)
    ot_dp_rrelay u_rrl_131 (.clk(clk), .d(rst_rl_130), .q(rst_n_t20));  // tap tap 20 depth 6 @ (1425.6, 1209.6)
    wire rst_rl_132;
    ot_dp_rrelay u_rrl_132 (.clk(clk), .d(rst_root_n), .q(rst_rl_132));  // wire tap None depth 1 @ (1239.3, 669.3)
    wire rst_rl_133;
    ot_dp_rrelay u_rrl_133 (.clk(clk), .d(rst_rl_132), .q(rst_rl_133));  // wire tap None depth 2 @ (1162.1, 375.8)
    wire rst_rl_134;
    ot_dp_rrelay u_rrl_134 (.clk(clk), .d(rst_rl_133), .q(rst_rl_134));  // wire tap None depth 3 @ (1018.7, 171.0)
    wire rst_rl_135;
    ot_dp_rrelay u_rrl_135 (.clk(clk), .d(rst_rl_134), .q(rst_rl_135));  // wire tap None depth 4 @ (678.2, 171.0)
    wire rst_rl_136;
    ot_dp_rrelay u_rrl_136 (.clk(clk), .d(rst_rl_135), .q(rst_rl_136));  // wire tap None depth 5 @ (470.9, 99.4)
    ot_dp_rrelay u_rrl_137 (.clk(clk), .d(rst_rl_136), .q(rst_n_t22));  // tap tap 22 depth 6 @ (288.0, 17.3)
    wire rst_rl_138;
    ot_dp_rrelay u_rrl_138 (.clk(clk), .d(rst_root_n), .q(rst_rl_138));  // pad tap None depth 1 @ (1334.3, 859.3)
    wire rst_rl_139;
    ot_dp_rrelay u_rrl_139 (.clk(clk), .d(rst_rl_138), .q(rst_rl_139));  // wire tap None depth 2 @ (1334.3, 859.3)
    wire rst_rl_140;
    ot_dp_rrelay u_rrl_140 (.clk(clk), .d(rst_rl_139), .q(rst_rl_140));  // wire tap None depth 3 @ (954.3, 859.3)
    wire rst_rl_141;
    ot_dp_rrelay u_rrl_141 (.clk(clk), .d(rst_rl_140), .q(rst_rl_141));  // wire tap None depth 4 @ (574.3, 859.3)
    wire rst_rl_142;
    ot_dp_rrelay u_rrl_142 (.clk(clk), .d(rst_rl_141), .q(rst_rl_142));  // wire tap None depth 5 @ (479.3, 1144.3)
    ot_dp_rrelay u_rrl_143 (.clk(clk), .d(rst_rl_142), .q(rst_n_t23));  // tap tap 23 depth 6 @ (340.0, 1209.6)
    wire rst_rl_144;
    ot_dp_rrelay u_rrl_144 (.clk(clk), .d(rst_root_n), .q(rst_rl_144));  // pad tap None depth 1 @ (1434.2, 462.2)
    wire rst_rl_145;
    ot_dp_rrelay u_rrl_145 (.clk(clk), .d(rst_rl_144), .q(rst_rl_145));  // pad tap None depth 2 @ (1434.2, 462.2)
    wire rst_rl_146;
    ot_dp_rrelay u_rrl_146 (.clk(clk), .d(rst_rl_145), .q(rst_rl_146));  // pad tap None depth 3 @ (1434.2, 462.2)
    wire rst_rl_147;
    ot_dp_rrelay u_rrl_147 (.clk(clk), .d(rst_rl_146), .q(rst_rl_147));  // wire tap None depth 4 @ (1434.2, 462.2)
    wire rst_rl_148;
    ot_dp_rrelay u_rrl_148 (.clk(clk), .d(rst_rl_147), .q(rst_rl_148));  // pad tap 30 depth 5 @ (1425.6, 97.7)
    ot_dp_rrelay u_rrl_149 (.clk(clk), .d(rst_rl_148), .q(rst_n_t30));  // tap tap 30 depth 6 @ (1425.6, 97.7)
    wire rst_rl_150;
    ot_dp_rrelay u_rrl_150 (.clk(clk), .d(rst_rl_147), .q(rst_rl_150));  // wire tap None depth 5 @ (1334.9, 211.7)
    ot_dp_rrelay u_rrl_151 (.clk(clk), .d(rst_rl_150), .q(rst_n_t25));  // tap tap 25 depth 6 @ (1154.1, 17.3)
    wire rst_rl_152;
    ot_dp_rrelay u_rrl_152 (.clk(clk), .d(rst_root_n), .q(rst_rl_152));  // pad tap None depth 1 @ (1144.3, 764.3)
    wire rst_rl_153;
    ot_dp_rrelay u_rrl_153 (.clk(clk), .d(rst_rl_152), .q(rst_rl_153));  // wire tap None depth 2 @ (1144.3, 764.3)
    wire rst_rl_154;
    ot_dp_rrelay u_rrl_154 (.clk(clk), .d(rst_rl_153), .q(rst_rl_154));  // wire tap None depth 3 @ (781.9, 756.0)
    wire rst_rl_155;
    ot_dp_rrelay u_rrl_155 (.clk(clk), .d(rst_rl_154), .q(rst_rl_155));  // wire tap None depth 4 @ (639.4, 548.6)
    wire rst_rl_156;
    ot_dp_rrelay u_rrl_156 (.clk(clk), .d(rst_rl_155), .q(rst_rl_156));  // pad tap 32 depth 5 @ (318.8, 531.7)
    ot_dp_rrelay u_rrl_157 (.clk(clk), .d(rst_rl_156), .q(rst_n_t32));  // tap tap 32 depth 6 @ (318.8, 531.7)
    wire rst_rl_158;
    ot_dp_rrelay u_rrl_158 (.clk(clk), .d(rst_rl_155), .q(rst_rl_158));  // wire tap None depth 5 @ (318.8, 525.2)
    ot_dp_rrelay u_rrl_159 (.clk(clk), .d(rst_rl_158), .q(rst_o_0));  // registered reset out rst_o_0 (wavefront, dedicated relay): tap tap 39 depth 6 @ (8.2, 460.6)
    ot_dp_rrelay u_rrl_159_t (.clk(clk), .d(rst_rl_158), .q(rst_n_t39));  // tap-net copy of u_rrl_159 for in-type loads: depth 6 @ (8.2, 460.6)
    wire rst_rl_160;
    ot_dp_rrelay u_rrl_160 (.clk(clk), .d(rst_root_n), .q(rst_rl_160));  // pad tap None depth 1 @ (1429.3, 764.3)
    wire rst_rl_161;
    ot_dp_rrelay u_rrl_161 (.clk(clk), .d(rst_rl_160), .q(rst_rl_161));  // wire tap None depth 2 @ (1429.3, 764.3)
    wire rst_rl_162;
    ot_dp_rrelay u_rrl_162 (.clk(clk), .d(rst_rl_161), .q(rst_rl_162));  // wire tap None depth 3 @ (1049.3, 764.3)
    wire rst_rl_163;
    ot_dp_rrelay u_rrl_163 (.clk(clk), .d(rst_rl_162), .q(rst_rl_163));  // wire tap None depth 4 @ (686.9, 756.0)
    wire rst_rl_164;
    ot_dp_rrelay u_rrl_164 (.clk(clk), .d(rst_rl_163), .q(rst_rl_164));  // wire tap None depth 5 @ (323.9, 756.0)
    ot_dp_rrelay u_rrl_165 (.clk(clk), .d(rst_rl_164), .q(rst_n_t34));  // tap tap 34 depth 6 @ (17.3, 739.8)
    wire rst_rl_166;
    ot_dp_rrelay u_rrl_166 (.clk(clk), .d(rst_root_n), .q(rst_rl_166));  // pad tap None depth 1 @ (1300.3, 972.0)
    wire rst_rl_167;
    ot_dp_rrelay u_rrl_167 (.clk(clk), .d(rst_rl_166), .q(rst_rl_167));  // pad tap None depth 2 @ (1300.3, 972.0)
    wire rst_rl_168;
    ot_dp_rrelay u_rrl_168 (.clk(clk), .d(rst_rl_167), .q(rst_rl_168));  // pad tap None depth 3 @ (1300.3, 972.0)
    wire rst_rl_169;
    ot_dp_rrelay u_rrl_169 (.clk(clk), .d(rst_rl_168), .q(rst_rl_169));  // wire tap None depth 4 @ (1300.3, 972.0)
    wire rst_rl_170;
    ot_dp_rrelay u_rrl_170 (.clk(clk), .d(rst_rl_169), .q(rst_rl_170));  // wire tap None depth 5 @ (1075.5, 1115.6)
    ot_dp_rrelay u_rrl_171 (.clk(clk), .d(rst_rl_170), .q(rst_n_t38));  // tap tap 38 depth 6 @ (735.1, 1121.9)
    wire rst_rl_172;
    ot_dp_rrelay u_rrl_172 (.clk(clk), .d(rst_root_n), .q(rst_rl_172));  // pad tap None depth 1 @ (1209.6, 885.6)
    wire rst_rl_173;
    ot_dp_rrelay u_rrl_173 (.clk(clk), .d(rst_rl_172), .q(rst_rl_173));  // pad tap None depth 2 @ (1209.6, 885.6)
    wire rst_rl_174;
    ot_dp_rrelay u_rrl_174 (.clk(clk), .d(rst_rl_173), .q(rst_rl_174));  // pad tap None depth 3 @ (1209.6, 885.6)
    wire rst_rl_175;
    ot_dp_rrelay u_rrl_175 (.clk(clk), .d(rst_rl_174), .q(rst_rl_175));  // pad tap None depth 4 @ (1209.6, 885.6)
    wire rst_rl_176;
    ot_dp_rrelay u_rrl_176 (.clk(clk), .d(rst_rl_175), .q(rst_rl_176));  // wire tap None depth 5 @ (1209.6, 885.6)
    ot_dp_rrelay u_rrl_177 (.clk(clk), .d(rst_rl_176), .q(rst_n_t43));  // tap tap 43 depth 6 @ (836.7, 885.6)
