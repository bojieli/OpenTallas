module hbm_arch_q_spb0 (
    input  wire clk,
    input  wire arst_n,
    input  wire [0:0] io_lk_S0_pma_rck,    
    input  wire [543:0] io_lk_S0_pma_rx,    
    input  wire [632:0] L720_i,    
    output wire [11:0] L117_o,    
    output wire [2:0] L138_o,    
    output wire [308:0] L722_o,    
    output wire [307:0] L723_o    
);
    wire [631:0] L720_i_q;
    wire L720_i_eq;
    wire [0:0] w_u_ep_S0_fault;
    wire [10:0] w_u_ep_S0_fault_cause;
    wire [0:0] w_u_ep_S0_phy_up;
    wire [1:0] w_u_ep_S0_rx_block_ready;
    wire [611:0] w_u_ep_S0_rx_pin_flit;
    wire [0:0] w_u_ep_S0_rx_pin_v;
    wire [511:0] w_u_ep_S0_sd_tx;
    wire [0:0] w_u_lk_S0_pma_tck;
    wire [543:0] w_u_lk_S0_pma_tx;
    wire [511:0] w_u_lk_S0_rx;
    wire [1:0] w_u_lk_S0_st;
     
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
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_n_t17));   
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_0), .q(rst_rl_6));   
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));   
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));   
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_n_t12));   
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_8), .q(rst_rl_11));   
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_n_t7));   
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_11), .q(rst_n_t2));   
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_0), .q(rst_rl_14));   
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));   
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));   
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));   
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_n_t16));   
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_0), .q(rst_rl_19));   
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));   
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));   
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));   
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_n_t18));   
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_19), .q(rst_rl_24));   
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));   
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));   
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t13));   
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_24), .q(rst_rl_28));   
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));   
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t8));   
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_28), .q(rst_rl_31));   
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t3));   
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_28), .q(rst_rl_33));   
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_n_t9));   
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_33), .q(rst_n_t4));   
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_19), .q(rst_rl_36));   
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));   
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));   
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t19));   
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_38), .q(rst_n_t14));   
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_0), .q(rst_rl_41));   
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));   
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));   
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));   
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_n_t15));   
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_root_n), .q(rst_rl_46));   
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));   
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));   
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));   
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));   
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_n_t11));   
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_root_n), .q(rst_rl_52));   
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));   
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));   
    wire rst_rl_55;
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_rl_55));   
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_55), .q(rst_rl_56));   
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_n_t6));   
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_56), .q(rst_n_t1));   
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_root_n), .q(rst_rl_59));   
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_rl_60));   
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));   
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));   
    wire rst_rl_63;
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_rl_63));   
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_63), .q(rst_n_t20));   
    wire rst_rl_65;
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_61), .q(rst_rl_65));   
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_65), .q(rst_rl_66));   
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_n_t10));   
    wire rst_rl_68;
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_65), .q(rst_rl_68));   
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_68), .q(rst_n_t5));   
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_68), .q(rst_n_t0));   
    wire rst_n = rst_n_t7;
    ot_dp_st #(.W(632)) u_bin_L720_i (.clk(clk), .rst_n(rst_n), .d(L720_i[631:0]), .ea(L720_i[632]), .q(L720_i_q), .eq(L720_i_eq));
    ot_dp_st #(.W(11)) u_bout_L117_o (.clk(clk), .rst_n(rst_n), .d(w_u_ep_S0_fault_cause[10:0]), .ea(rst_n), .q(L117_o[10:0]), .eq(L117_o[11]));
    ot_dp_st #(.W(2)) u_bout_L138_o (.clk(clk), .rst_n(rst_n), .d(w_u_ep_S0_rx_block_ready[1:0]), .ea(rst_n), .q(L138_o[1:0]), .eq(L138_o[2]));
    ot_dp_st #(.W(308)) u_bout_L722_o (.clk(clk), .rst_n(rst_n), .d({w_u_ep_S0_rx_pin_flit[305:0], w_u_ep_S0_phy_up[0], w_u_ep_S0_fault[0]}), .ea(rst_n), .q(L722_o[307:0]), .eq(L722_o[308]));
    ot_dp_st #(.W(307)) u_bout_L723_o (.clk(clk), .rst_n(rst_n), .d({w_u_ep_S0_rx_pin_v[0], w_u_ep_S0_rx_pin_flit[611:306]}), .ea(rst_n), .q(L723_o[306:0]), .eq(L723_o[307]));
     
    hfd_ep_static u_u_ep_S0 (
        .clk(clk),
        .fault(w_u_ep_S0_fault),
        .fault_cause(w_u_ep_S0_fault_cause),
        .phy_up(w_u_ep_S0_phy_up),
        .rst_n(rst_n_t20),
        .rx_arm_bank(L720_i_q[1]),
        .rx_arm_v(L720_i_q[0]),
        .rx_block_ready(w_u_ep_S0_rx_block_ready),
        .rx_block_words(L720_i_q[8:2]),
        .rx_pin_flit(w_u_ep_S0_rx_pin_flit),
        .rx_pin_v(w_u_ep_S0_rx_pin_v),
        .rx_release_bank(L720_i_q[10]),
        .rx_release_v(L720_i_q[9]),
        .rx_slot_bank(L720_i_q[12]),
        .rx_slot_index(L720_i_q[18:13]),
        .rx_slot_v(L720_i_q[11]),
        .sd_rx(w_u_lk_S0_rx[511:0]),
        .sd_st(w_u_lk_S0_st[1:0]),
        .sd_tx(w_u_ep_S0_sd_tx),
        .tx_frame(L720_i_q[630:19]),
        .tx_v(L720_i_q[631])
    );
     
    ot_pdie_serdes u_u_lk_S0 (
        .clk(clk),
        .pma_rck(io_lk_S0_pma_rck[0]),
        .pma_rx(io_lk_S0_pma_rx[543:0]),
        .pma_tck(w_u_lk_S0_pma_tck),
        .pma_tx(w_u_lk_S0_pma_tx),
        .rst(rst_n),
        .rx(w_u_lk_S0_rx),
        .st(w_u_lk_S0_st),
        .tx(w_u_ep_S0_sd_tx[511:0])
    );
endmodule
