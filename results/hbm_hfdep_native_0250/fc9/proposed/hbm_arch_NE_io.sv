module hbm_arch_NE_io (
    input  wire clk,
    input  wire arst_n,
    input  wire [0:0] io_lk_N2_pma_rck,    
    input  wire [543:0] io_lk_N2_pma_rx,    
    input  wire [21:0] L101_i,    
    input  wire [2:0] L106_i,    
    input  wire [612:0] L51_i,    
    output wire [5:0] L125_o,    
    output wire [5:0] L126_o,    
    output wire [7:0] L48_o,    
    output wire [612:0] L52_o    
);
    wire [20:0] L101_i_q;
    wire L101_i_eq;
    wire [1:0] L106_i_q;
    wire L106_i_eq;
    wire [611:0] L51_i_q;
    wire L51_i_eq;
    wire [0:0] w_u_ep_N2_fault;
    wire [8:0] w_u_ep_N2_fault_cause;
    wire [0:0] w_u_ep_N2_phy_up;
    wire [1:0] w_u_ep_N2_rx_block_ready;
    wire [611:0] w_u_ep_N2_rx_pin_flit;
    wire [0:0] w_u_ep_N2_rx_pin_v;
    wire [511:0] w_u_ep_N2_sd_tx;
    wire [0:0] w_u_lk_N2_pma_tck;
    wire [543:0] w_u_lk_N2_pma_tx;
    wire [511:0] w_u_lk_N2_rx;
    wire [1:0] w_u_lk_N2_st;
     
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));   
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
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));   
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));   
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));   
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));   
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));   
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));   
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));   
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));   
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_n_t21));   
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_0), .q(rst_rl_10));   
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));   
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));   
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));   
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));   
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));   
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));   
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));   
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_n_t20));   
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_0), .q(rst_rl_19));   
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));   
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));   
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));   
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));   
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));   
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));   
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));   
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t18));   
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_0), .q(rst_rl_28));   
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));   
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));   
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));   
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_rl_32));   
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));   
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));   
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_rl_35));   
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_n_t16));   
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_0), .q(rst_rl_37));   
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));   
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_rl_39));   
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));   
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));   
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));   
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));   
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));   
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_n_t14));   
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_40), .q(rst_rl_46));   
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));   
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));   
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));   
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_n_t22));   
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_0), .q(rst_rl_51));   
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));   
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));   
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));   
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));   
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));   
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));   
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_rl_58));   
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_n_t12));   
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_root_n), .q(rst_rl_60));   
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));   
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));   
    wire rst_rl_63;
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_rl_63));   
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_63), .q(rst_rl_64));   
    wire rst_rl_65;
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_rl_65));   
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_65), .q(rst_rl_66));   
    wire rst_rl_67;
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_rl_67));   
    wire rst_rl_68;
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_67), .q(rst_rl_68));   
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_68), .q(rst_n_t19));   
    wire rst_rl_70;
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_64), .q(rst_rl_70));   
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_70), .q(rst_rl_71));   
    wire rst_rl_72;
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_rl_72));   
    wire rst_rl_73;
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_rl_72), .q(rst_rl_73));   
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_73), .q(rst_n_t10));   
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_root_n), .q(rst_rl_75));   
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_rl_76));   
    wire rst_rl_77;
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_rl_77));   
    wire rst_rl_78;
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_77), .q(rst_rl_78));   
    wire rst_rl_79;
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_rl_78), .q(rst_rl_79));   
    wire rst_rl_80;
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_79), .q(rst_rl_80));   
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_rl_80), .q(rst_rl_81));   
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));   
    wire rst_rl_83;
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_rl_83));   
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_rl_83), .q(rst_n_t17));   
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_78), .q(rst_rl_85));   
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));   
    wire rst_rl_87;
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_rl_87));   
    wire rst_rl_88;
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_87), .q(rst_rl_88));   
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_rl_88), .q(rst_rl_89));   
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_n_t8));   
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_78), .q(rst_rl_91));   
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_rl_92));   
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));   
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));   
    wire rst_rl_95;
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_rl_95));   
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_95), .q(rst_n_t5));   
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_78), .q(rst_rl_97));   
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));   
    wire rst_rl_99;
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_rl_99));   
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_99), .q(rst_rl_100));   
    wire rst_rl_101;
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_rl_101));   
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_101), .q(rst_n_t1));   
    wire rst_rl_103;
    ot_dp_rrelay u_rrl_103 (.clk(clk), .d(rst_root_n), .q(rst_rl_103));   
    wire rst_rl_104;
    ot_dp_rrelay u_rrl_104 (.clk(clk), .d(rst_rl_103), .q(rst_rl_104));   
    wire rst_rl_105;
    ot_dp_rrelay u_rrl_105 (.clk(clk), .d(rst_rl_104), .q(rst_rl_105));   
    wire rst_rl_106;
    ot_dp_rrelay u_rrl_106 (.clk(clk), .d(rst_rl_105), .q(rst_rl_106));   
    wire rst_rl_107;
    ot_dp_rrelay u_rrl_107 (.clk(clk), .d(rst_rl_106), .q(rst_rl_107));   
    wire rst_rl_108;
    ot_dp_rrelay u_rrl_108 (.clk(clk), .d(rst_rl_107), .q(rst_rl_108));   
    wire rst_rl_109;
    ot_dp_rrelay u_rrl_109 (.clk(clk), .d(rst_rl_108), .q(rst_rl_109));   
    wire rst_rl_110;
    ot_dp_rrelay u_rrl_110 (.clk(clk), .d(rst_rl_109), .q(rst_rl_110));   
    wire rst_rl_111;
    ot_dp_rrelay u_rrl_111 (.clk(clk), .d(rst_rl_110), .q(rst_rl_111));   
    ot_dp_rrelay u_rrl_112 (.clk(clk), .d(rst_rl_111), .q(rst_n_t15));   
    wire rst_rl_113;
    ot_dp_rrelay u_rrl_113 (.clk(clk), .d(rst_rl_106), .q(rst_rl_113));   
    wire rst_rl_114;
    ot_dp_rrelay u_rrl_114 (.clk(clk), .d(rst_rl_113), .q(rst_rl_114));   
    wire rst_rl_115;
    ot_dp_rrelay u_rrl_115 (.clk(clk), .d(rst_rl_114), .q(rst_rl_115));   
    wire rst_rl_116;
    ot_dp_rrelay u_rrl_116 (.clk(clk), .d(rst_rl_115), .q(rst_rl_116));   
    wire rst_rl_117;
    ot_dp_rrelay u_rrl_117 (.clk(clk), .d(rst_rl_116), .q(rst_rl_117));   
    ot_dp_rrelay u_rrl_118 (.clk(clk), .d(rst_rl_117), .q(rst_n_t6));   
    wire rst_rl_119;
    ot_dp_rrelay u_rrl_119 (.clk(clk), .d(rst_rl_106), .q(rst_rl_119));   
    wire rst_rl_120;
    ot_dp_rrelay u_rrl_120 (.clk(clk), .d(rst_rl_119), .q(rst_rl_120));   
    wire rst_rl_121;
    ot_dp_rrelay u_rrl_121 (.clk(clk), .d(rst_rl_120), .q(rst_rl_121));   
    wire rst_rl_122;
    ot_dp_rrelay u_rrl_122 (.clk(clk), .d(rst_rl_121), .q(rst_rl_122));   
    wire rst_rl_123;
    ot_dp_rrelay u_rrl_123 (.clk(clk), .d(rst_rl_122), .q(rst_rl_123));   
    ot_dp_rrelay u_rrl_124 (.clk(clk), .d(rst_rl_123), .q(rst_n_t4));   
    wire rst_rl_125;
    ot_dp_rrelay u_rrl_125 (.clk(clk), .d(rst_root_n), .q(rst_rl_125));   
    wire rst_rl_126;
    ot_dp_rrelay u_rrl_126 (.clk(clk), .d(rst_rl_125), .q(rst_rl_126));   
    wire rst_rl_127;
    ot_dp_rrelay u_rrl_127 (.clk(clk), .d(rst_rl_126), .q(rst_rl_127));   
    wire rst_rl_128;
    ot_dp_rrelay u_rrl_128 (.clk(clk), .d(rst_rl_127), .q(rst_rl_128));   
    wire rst_rl_129;
    ot_dp_rrelay u_rrl_129 (.clk(clk), .d(rst_rl_128), .q(rst_rl_129));   
    wire rst_rl_130;
    ot_dp_rrelay u_rrl_130 (.clk(clk), .d(rst_rl_129), .q(rst_rl_130));   
    wire rst_rl_131;
    ot_dp_rrelay u_rrl_131 (.clk(clk), .d(rst_rl_130), .q(rst_rl_131));   
    wire rst_rl_132;
    ot_dp_rrelay u_rrl_132 (.clk(clk), .d(rst_rl_131), .q(rst_rl_132));   
    wire rst_rl_133;
    ot_dp_rrelay u_rrl_133 (.clk(clk), .d(rst_rl_132), .q(rst_rl_133));   
    ot_dp_rrelay u_rrl_134 (.clk(clk), .d(rst_rl_133), .q(rst_n_t13));   
    wire rst_rl_135;
    ot_dp_rrelay u_rrl_135 (.clk(clk), .d(rst_rl_129), .q(rst_rl_135));   
    wire rst_rl_136;
    ot_dp_rrelay u_rrl_136 (.clk(clk), .d(rst_rl_135), .q(rst_rl_136));   
    wire rst_rl_137;
    ot_dp_rrelay u_rrl_137 (.clk(clk), .d(rst_rl_136), .q(rst_rl_137));   
    wire rst_rl_138;
    ot_dp_rrelay u_rrl_138 (.clk(clk), .d(rst_rl_137), .q(rst_rl_138));   
    ot_dp_rrelay u_rrl_139 (.clk(clk), .d(rst_rl_138), .q(rst_n_t2));   
    wire rst_rl_140;
    ot_dp_rrelay u_rrl_140 (.clk(clk), .d(rst_root_n), .q(rst_rl_140));   
    wire rst_rl_141;
    ot_dp_rrelay u_rrl_141 (.clk(clk), .d(rst_rl_140), .q(rst_rl_141));   
    wire rst_rl_142;
    ot_dp_rrelay u_rrl_142 (.clk(clk), .d(rst_rl_141), .q(rst_rl_142));   
    wire rst_rl_143;
    ot_dp_rrelay u_rrl_143 (.clk(clk), .d(rst_rl_142), .q(rst_rl_143));   
    wire rst_rl_144;
    ot_dp_rrelay u_rrl_144 (.clk(clk), .d(rst_rl_143), .q(rst_rl_144));   
    wire rst_rl_145;
    ot_dp_rrelay u_rrl_145 (.clk(clk), .d(rst_rl_144), .q(rst_rl_145));   
    wire rst_rl_146;
    ot_dp_rrelay u_rrl_146 (.clk(clk), .d(rst_rl_145), .q(rst_rl_146));   
    wire rst_rl_147;
    ot_dp_rrelay u_rrl_147 (.clk(clk), .d(rst_rl_146), .q(rst_rl_147));   
    wire rst_rl_148;
    ot_dp_rrelay u_rrl_148 (.clk(clk), .d(rst_rl_147), .q(rst_rl_148));   
    ot_dp_rrelay u_rrl_149 (.clk(clk), .d(rst_rl_148), .q(rst_n_t11));   
    wire rst_rl_150;
    ot_dp_rrelay u_rrl_150 (.clk(clk), .d(rst_rl_145), .q(rst_rl_150));   
    wire rst_rl_151;
    ot_dp_rrelay u_rrl_151 (.clk(clk), .d(rst_rl_150), .q(rst_rl_151));   
    wire rst_rl_152;
    ot_dp_rrelay u_rrl_152 (.clk(clk), .d(rst_rl_151), .q(rst_rl_152));   
    ot_dp_rrelay u_rrl_153 (.clk(clk), .d(rst_rl_152), .q(rst_n_t0));   
    wire rst_rl_154;
    ot_dp_rrelay u_rrl_154 (.clk(clk), .d(rst_root_n), .q(rst_rl_154));   
    wire rst_rl_155;
    ot_dp_rrelay u_rrl_155 (.clk(clk), .d(rst_rl_154), .q(rst_rl_155));   
    wire rst_rl_156;
    ot_dp_rrelay u_rrl_156 (.clk(clk), .d(rst_rl_155), .q(rst_rl_156));   
    wire rst_rl_157;
    ot_dp_rrelay u_rrl_157 (.clk(clk), .d(rst_rl_156), .q(rst_rl_157));   
    wire rst_rl_158;
    ot_dp_rrelay u_rrl_158 (.clk(clk), .d(rst_rl_157), .q(rst_rl_158));   
    wire rst_rl_159;
    ot_dp_rrelay u_rrl_159 (.clk(clk), .d(rst_rl_158), .q(rst_rl_159));   
    wire rst_rl_160;
    ot_dp_rrelay u_rrl_160 (.clk(clk), .d(rst_rl_159), .q(rst_rl_160));   
    wire rst_rl_161;
    ot_dp_rrelay u_rrl_161 (.clk(clk), .d(rst_rl_160), .q(rst_rl_161));   
    wire rst_rl_162;
    ot_dp_rrelay u_rrl_162 (.clk(clk), .d(rst_rl_161), .q(rst_rl_162));   
    ot_dp_rrelay u_rrl_163 (.clk(clk), .d(rst_rl_162), .q(rst_n_t9));   
    wire rst_rl_164;
    ot_dp_rrelay u_rrl_164 (.clk(clk), .d(rst_root_n), .q(rst_rl_164));   
    wire rst_rl_165;
    ot_dp_rrelay u_rrl_165 (.clk(clk), .d(rst_rl_164), .q(rst_rl_165));   
    wire rst_rl_166;
    ot_dp_rrelay u_rrl_166 (.clk(clk), .d(rst_rl_165), .q(rst_rl_166));   
    wire rst_rl_167;
    ot_dp_rrelay u_rrl_167 (.clk(clk), .d(rst_rl_166), .q(rst_rl_167));   
    wire rst_rl_168;
    ot_dp_rrelay u_rrl_168 (.clk(clk), .d(rst_rl_167), .q(rst_rl_168));   
    wire rst_rl_169;
    ot_dp_rrelay u_rrl_169 (.clk(clk), .d(rst_rl_168), .q(rst_rl_169));   
    wire rst_rl_170;
    ot_dp_rrelay u_rrl_170 (.clk(clk), .d(rst_rl_169), .q(rst_rl_170));   
    wire rst_rl_171;
    ot_dp_rrelay u_rrl_171 (.clk(clk), .d(rst_rl_170), .q(rst_rl_171));   
    wire rst_rl_172;
    ot_dp_rrelay u_rrl_172 (.clk(clk), .d(rst_rl_171), .q(rst_rl_172));   
    ot_dp_rrelay u_rrl_173 (.clk(clk), .d(rst_rl_172), .q(rst_n_t7));   
    wire rst_rl_174;
    ot_dp_rrelay u_rrl_174 (.clk(clk), .d(rst_root_n), .q(rst_rl_174));   
    wire rst_rl_175;
    ot_dp_rrelay u_rrl_175 (.clk(clk), .d(rst_rl_174), .q(rst_rl_175));   
    wire rst_rl_176;
    ot_dp_rrelay u_rrl_176 (.clk(clk), .d(rst_rl_175), .q(rst_rl_176));   
    wire rst_rl_177;
    ot_dp_rrelay u_rrl_177 (.clk(clk), .d(rst_rl_176), .q(rst_rl_177));   
    wire rst_rl_178;
    ot_dp_rrelay u_rrl_178 (.clk(clk), .d(rst_rl_177), .q(rst_rl_178));   
    wire rst_rl_179;
    ot_dp_rrelay u_rrl_179 (.clk(clk), .d(rst_rl_178), .q(rst_rl_179));   
    wire rst_rl_180;
    ot_dp_rrelay u_rrl_180 (.clk(clk), .d(rst_rl_179), .q(rst_rl_180));   
    wire rst_rl_181;
    ot_dp_rrelay u_rrl_181 (.clk(clk), .d(rst_rl_180), .q(rst_rl_181));   
    wire rst_rl_182;
    ot_dp_rrelay u_rrl_182 (.clk(clk), .d(rst_rl_181), .q(rst_rl_182));   
    ot_dp_rrelay u_rrl_183 (.clk(clk), .d(rst_rl_182), .q(rst_n_t3));   
    wire rst_n = rst_n_t10;
    ot_dp_st #(.W(21)) u_bin_L101_i (.clk(clk), .rst_n(rst_n), .d(L101_i[20:0]), .ea(L101_i[21]), .q(L101_i_q), .eq(L101_i_eq));
    ot_dp_st #(.W(2)) u_bin_L106_i (.clk(clk), .rst_n(rst_n), .d(L106_i[1:0]), .ea(L106_i[2]), .q(L106_i_q), .eq(L106_i_eq));
    ot_dp_st #(.W(612)) u_bin_L51_i (.clk(clk), .rst_n(rst_n), .d(L51_i[611:0]), .ea(L51_i[612]), .q(L51_i_q), .eq(L51_i_eq));
    ot_dp_st #(.W(5)) u_bout_L125_o (.clk(clk), .rst_n(rst_n), .d(w_u_ep_N2_fault_cause[4:0]), .ea(rst_n), .q(L125_o[4:0]), .eq(L125_o[5]));
    ot_dp_st #(.W(5)) u_bout_L126_o (.clk(clk), .rst_n(rst_n), .d({w_u_ep_N2_rx_pin_flit[2:0], w_u_ep_N2_phy_up[0], w_u_ep_N2_fault[0]}), .ea(rst_n), .q(L126_o[4:0]), .eq(L126_o[5]));
    ot_dp_st #(.W(7)) u_bout_L48_o (.clk(clk), .rst_n(rst_n), .d({L51_i_q[611], w_u_ep_N2_rx_block_ready[1:0], w_u_ep_N2_fault_cause[8:5]}), .ea(rst_n), .q(L48_o[6:0]), .eq(L48_o[7]));
    ot_dp_st #(.W(612)) u_bout_L52_o (.clk(clk), .rst_n(rst_n), .d({L106_i_q[1:0], w_u_ep_N2_rx_pin_v[0], w_u_ep_N2_rx_pin_flit[611:3]}), .ea(rst_n), .q(L52_o[611:0]), .eq(L52_o[612]));
     
    hfd_ep_static_fc9 u_u_ep_N2 (
        .clk(clk),
        .fault(w_u_ep_N2_fault),
        .fault_cause(w_u_ep_N2_fault_cause),
        .phy_up(w_u_ep_N2_phy_up),
        .rst_n(rst_n_t22),
        .rx_arm_bank(L101_i_q[1]),
        .rx_arm_v(L101_i_q[0]),
        .rx_block_ready(w_u_ep_N2_rx_block_ready),
        .rx_block_words(L101_i_q[8:2]),
        .rx_pin_flit(w_u_ep_N2_rx_pin_flit),
        .rx_pin_v(w_u_ep_N2_rx_pin_v),
        .rx_release_bank(L101_i_q[10]),
        .rx_release_v(L101_i_q[9]),
        .rx_slot_bank(L101_i_q[12]),
        .rx_slot_index(L101_i_q[18:13]),
        .rx_slot_v(L101_i_q[11]),
        .sd_rx(w_u_lk_N2_rx[511:0]),
        .sd_st(w_u_lk_N2_st[1:0]),
        .sd_tx(w_u_ep_N2_sd_tx),
        .tx_frame({L51_i_q[609:0], L101_i_q[20:19]}),
        .tx_v(L51_i_q[610])
    );
     
    ot_pdie_serdes u_u_lk_N2 (
        .clk(clk),
        .pma_rck(io_lk_N2_pma_rck[0]),
        .pma_rx(io_lk_N2_pma_rx[543:0]),
        .pma_tck(w_u_lk_N2_pma_tck),
        .pma_tx(w_u_lk_N2_pma_tx),
        .rst(rst_n),
        .rx(w_u_lk_N2_rx),
        .st(w_u_lk_N2_st),
        .tx(w_u_ep_N2_sd_tx[511:0])
    );
endmodule
