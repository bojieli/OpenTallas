// Extracted actual retained provider ancestor cone. SOURCE_ONLY.
// Clock inputs require selected actual source/polarity binding; no dummy aliases.
module ot_die_start_stages_native_cone (
    input wire rst_raw_n,
    input wire t_st_b0__clk,
    input wire t_st_r3_1__clk,
    input wire t_st_b3__clk,
    input wire t_st_r4_1__clk,
    input wire t_st_b4__clk,
    input wire t_st_r19_1__clk,
    input wire t_st_b19__clk,
    input wire t_st_r20_1__clk,
    input wire t_st_b20__clk,
    input wire t_st_r53_1__clk,
    input wire t_st_b53__clk,
    input wire t_st_r54_1__clk,
    input wire t_st_b54__clk,
    input wire t_st_r87_1__clk,
    input wire t_st_b87__clk,
    input wire t_st_r88_1__clk,
    input wire t_st_b88__clk,
    input wire t_st_r147_1__clk,
    input wire t_st_b147__clk,
    input wire t_st_r148_1__clk,
    input wire t_st_b148__clk,
    input wire t_st_r209_1__clk,
    input wire t_st_b209__clk,
    input wire t_st_r210_1__clk,
    input wire t_st_b210__clk,
    input wire t_st_r299_1__clk,
    input wire t_st_b299__clk,
    input wire t_st_r300_1__clk,
    input wire t_st_b300__clk,
    input wire t_st_r380_1__clk,
    input wire t_st_b380__clk,
    input wire t_st_r381_1__clk,
    input wire t_st_b381__clk,
    input wire t_st_r477_1__clk,
    input wire t_st_b477__clk,
    input wire t_st_r478_1__clk,
    input wire t_st_b478__clk,
    input wire t_st_r563_1__clk,
    input wire t_st_b563__clk,
    input wire t_st_r564_1__clk,
    input wire t_st_b564__clk,
    input wire t_st_r661_1__clk,
    input wire t_st_b661__clk,
    input wire t_st_r662_1__clk,
    input wire t_st_b662__clk,
    input wire t_st_b741__clk,
    input wire t_st_r745_1__clk,
    input wire t_st_b747__clk,
    input wire t_st_r742_1__clk,
    input wire t_st_b745__clk,
    input wire t_st_r748_1__clk,
    input wire t_st_b742__clk,
    input wire t_st_r746_1__clk,
    input wire t_st_b748__clk,
    input wire t_st_b743__clk,
    input wire t_st_b746__clk,
    input wire t_st_b749__clk,
    input wire t_st_r744_1__clk,
    input wire t_st_r750_1__clk,
    input wire t_st_b744__clk,
    input wire t_st_b6499__clk,
    input wire t_st_b750__clk,
    input wire t_st_r841_0__clk,
    input wire t_st_r841_1__clk,
    input wire t_st_r844_2__clk,
    input wire t_st_b6375__clk,
    input wire t_st_b17286__clk,
    input wire t_st_b842__clk,
    input wire t_st_b845__clk,
    input wire t_st_r6377_0__clk,
    input wire t_st_b846__clk,
    input wire t_st_r6747_1__clk,
    input wire t_st_b17296__clk,
    input wire t_st_r6748_0__clk,
    input wire t_st_b6778__clk,
    input wire t_st_r6779_0__clk,
    output wire pst_sl_W5_ctl,
    output wire pst_sl_W5_stm,
    output wire pst_sl_W5_su_c,
    output wire pst_sl_W5_su_l0,
    output wire pst_sl_W5_su_l1
);
    wire st_b0_start;
    wire st_r3_1_start;
    wire st_b3_start;
    wire st_r4_1_start;
    wire st_b4_start;
    wire st_r19_1_start;
    wire st_b19_start;
    wire st_r20_1_start;
    wire st_b20_start;
    wire st_r53_1_start;
    wire st_b53_start;
    wire st_r54_1_start;
    wire st_b54_start;
    wire st_r87_1_start;
    wire st_b87_start;
    wire st_r88_1_start;
    wire st_b88_start;
    wire st_r147_1_start;
    wire st_b147_start;
    wire st_r148_1_start;
    wire st_b148_start;
    wire st_r209_1_start;
    wire st_b209_start;
    wire st_r210_1_start;
    wire st_b210_start;
    wire st_r299_1_start;
    wire st_b299_start;
    wire st_r300_1_start;
    wire st_b300_start;
    wire st_r380_1_start;
    wire st_b380_start;
    wire st_r381_1_start;
    wire st_b381_start;
    wire st_r477_1_start;
    wire st_b477_start;
    wire st_r478_1_start;
    wire st_b478_start;
    wire st_r563_1_start;
    wire st_b563_start;
    wire st_r564_1_start;
    wire st_b564_start;
    wire st_r661_1_start;
    wire st_b661_start;
    wire st_r662_1_start;
    wire st_b662_start;
    wire st_b741_start;
    wire st_r745_1_start;
    wire st_b747_start;
    wire st_r742_1_start;
    wire st_b745_start;
    wire st_r748_1_start;
    wire st_b742_start;
    wire st_r746_1_start;
    wire st_b748_start;
    wire st_b743_start;
    wire st_b746_start;
    wire st_b749_start;
    wire st_r744_1_start;
    wire st_r750_1_start;
    wire st_b744_start;
    wire st_b6499_start;
    wire st_b750_start;
    wire st_r841_0_start;
    wire st_r841_1_start;
    wire st_r844_2_start;
    wire st_b6375_start;
    wire st_b17286_start;
    wire st_b842_start;
    wire st_b845_start;
    wire st_r6377_0_start;
    wire st_b846_start;
    wire st_r6747_1_start;
    wire st_b17296_start;
    wire st_r6748_0_start;
    wire st_b6778_start;
    wire st_r6779_0_start;
    wire st_b0_rraw = rst_raw_n;
    ot_dp_landing_root #(.SETTLE(64)) u_st_b0 (.clk(t_st_b0__clk), .rst_raw_n(rst_raw_n), .start(st_b0_start));
    wire st_r3_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r3_1 (.clk(t_st_r3_1__clk), .d(st_b0_rraw), .q(st_r3_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r3_1 (.clk(t_st_r3_1__clk), .rst_raw_n(st_r3_1_rraw), .p_start(st_b0_start), .start(st_r3_1_start));
    wire st_b3_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b3 (.clk(t_st_b3__clk), .d(st_r3_1_rraw), .q(st_b3_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b3 (.clk(t_st_b3__clk), .rst_raw_n(st_b3_rraw), .p_start(st_r3_1_start), .start(st_b3_start));
    wire st_r4_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r4_1 (.clk(t_st_r4_1__clk), .d(st_b3_rraw), .q(st_r4_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r4_1 (.clk(t_st_r4_1__clk), .rst_raw_n(st_r4_1_rraw), .p_start(st_b3_start), .start(st_r4_1_start));
    wire st_b4_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b4 (.clk(t_st_b4__clk), .d(st_r4_1_rraw), .q(st_b4_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b4 (.clk(t_st_b4__clk), .rst_raw_n(st_b4_rraw), .p_start(st_r4_1_start), .start(st_b4_start));
    wire st_r19_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r19_1 (.clk(t_st_r19_1__clk), .d(st_b4_rraw), .q(st_r19_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r19_1 (.clk(t_st_r19_1__clk), .rst_raw_n(st_r19_1_rraw), .p_start(st_b4_start), .start(st_r19_1_start));
    wire st_b19_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b19 (.clk(t_st_b19__clk), .d(st_r19_1_rraw), .q(st_b19_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b19 (.clk(t_st_b19__clk), .rst_raw_n(st_b19_rraw), .p_start(st_r19_1_start), .start(st_b19_start));
    wire st_r20_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r20_1 (.clk(t_st_r20_1__clk), .d(st_b19_rraw), .q(st_r20_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r20_1 (.clk(t_st_r20_1__clk), .rst_raw_n(st_r20_1_rraw), .p_start(st_b19_start), .start(st_r20_1_start));
    wire st_b20_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b20 (.clk(t_st_b20__clk), .d(st_r20_1_rraw), .q(st_b20_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b20 (.clk(t_st_b20__clk), .rst_raw_n(st_b20_rraw), .p_start(st_r20_1_start), .start(st_b20_start));
    wire st_r53_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r53_1 (.clk(t_st_r53_1__clk), .d(st_b20_rraw), .q(st_r53_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r53_1 (.clk(t_st_r53_1__clk), .rst_raw_n(st_r53_1_rraw), .p_start(st_b20_start), .start(st_r53_1_start));
    wire st_b53_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b53 (.clk(t_st_b53__clk), .d(st_r53_1_rraw), .q(st_b53_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b53 (.clk(t_st_b53__clk), .rst_raw_n(st_b53_rraw), .p_start(st_r53_1_start), .start(st_b53_start));
    wire st_r54_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r54_1 (.clk(t_st_r54_1__clk), .d(st_b53_rraw), .q(st_r54_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r54_1 (.clk(t_st_r54_1__clk), .rst_raw_n(st_r54_1_rraw), .p_start(st_b53_start), .start(st_r54_1_start));
    wire st_b54_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b54 (.clk(t_st_b54__clk), .d(st_r54_1_rraw), .q(st_b54_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b54 (.clk(t_st_b54__clk), .rst_raw_n(st_b54_rraw), .p_start(st_r54_1_start), .start(st_b54_start));
    wire st_r87_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r87_1 (.clk(t_st_r87_1__clk), .d(st_b54_rraw), .q(st_r87_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r87_1 (.clk(t_st_r87_1__clk), .rst_raw_n(st_r87_1_rraw), .p_start(st_b54_start), .start(st_r87_1_start));
    wire st_b87_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b87 (.clk(t_st_b87__clk), .d(st_r87_1_rraw), .q(st_b87_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b87 (.clk(t_st_b87__clk), .rst_raw_n(st_b87_rraw), .p_start(st_r87_1_start), .start(st_b87_start));
    wire st_r88_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r88_1 (.clk(t_st_r88_1__clk), .d(st_b87_rraw), .q(st_r88_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r88_1 (.clk(t_st_r88_1__clk), .rst_raw_n(st_r88_1_rraw), .p_start(st_b87_start), .start(st_r88_1_start));
    wire st_b88_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b88 (.clk(t_st_b88__clk), .d(st_r88_1_rraw), .q(st_b88_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b88 (.clk(t_st_b88__clk), .rst_raw_n(st_b88_rraw), .p_start(st_r88_1_start), .start(st_b88_start));
    wire st_r147_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r147_1 (.clk(t_st_r147_1__clk), .d(st_b88_rraw), .q(st_r147_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r147_1 (.clk(t_st_r147_1__clk), .rst_raw_n(st_r147_1_rraw), .p_start(st_b88_start), .start(st_r147_1_start));
    wire st_b147_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b147 (.clk(t_st_b147__clk), .d(st_r147_1_rraw), .q(st_b147_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b147 (.clk(t_st_b147__clk), .rst_raw_n(st_b147_rraw), .p_start(st_r147_1_start), .start(st_b147_start));
    wire st_r148_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r148_1 (.clk(t_st_r148_1__clk), .d(st_b147_rraw), .q(st_r148_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r148_1 (.clk(t_st_r148_1__clk), .rst_raw_n(st_r148_1_rraw), .p_start(st_b147_start), .start(st_r148_1_start));
    wire st_b148_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b148 (.clk(t_st_b148__clk), .d(st_r148_1_rraw), .q(st_b148_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b148 (.clk(t_st_b148__clk), .rst_raw_n(st_b148_rraw), .p_start(st_r148_1_start), .start(st_b148_start));
    wire st_r209_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r209_1 (.clk(t_st_r209_1__clk), .d(st_b148_rraw), .q(st_r209_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r209_1 (.clk(t_st_r209_1__clk), .rst_raw_n(st_r209_1_rraw), .p_start(st_b148_start), .start(st_r209_1_start));
    wire st_b209_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b209 (.clk(t_st_b209__clk), .d(st_r209_1_rraw), .q(st_b209_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b209 (.clk(t_st_b209__clk), .rst_raw_n(st_b209_rraw), .p_start(st_r209_1_start), .start(st_b209_start));
    wire st_r210_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r210_1 (.clk(t_st_r210_1__clk), .d(st_b209_rraw), .q(st_r210_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r210_1 (.clk(t_st_r210_1__clk), .rst_raw_n(st_r210_1_rraw), .p_start(st_b209_start), .start(st_r210_1_start));
    wire st_b210_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b210 (.clk(t_st_b210__clk), .d(st_r210_1_rraw), .q(st_b210_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b210 (.clk(t_st_b210__clk), .rst_raw_n(st_b210_rraw), .p_start(st_r210_1_start), .start(st_b210_start));
    wire st_r299_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r299_1 (.clk(t_st_r299_1__clk), .d(st_b210_rraw), .q(st_r299_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r299_1 (.clk(t_st_r299_1__clk), .rst_raw_n(st_r299_1_rraw), .p_start(st_b210_start), .start(st_r299_1_start));
    wire st_b299_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b299 (.clk(t_st_b299__clk), .d(st_r299_1_rraw), .q(st_b299_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b299 (.clk(t_st_b299__clk), .rst_raw_n(st_b299_rraw), .p_start(st_r299_1_start), .start(st_b299_start));
    wire st_r300_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r300_1 (.clk(t_st_r300_1__clk), .d(st_b299_rraw), .q(st_r300_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r300_1 (.clk(t_st_r300_1__clk), .rst_raw_n(st_r300_1_rraw), .p_start(st_b299_start), .start(st_r300_1_start));
    wire st_b300_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b300 (.clk(t_st_b300__clk), .d(st_r300_1_rraw), .q(st_b300_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b300 (.clk(t_st_b300__clk), .rst_raw_n(st_b300_rraw), .p_start(st_r300_1_start), .start(st_b300_start));
    wire st_r380_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r380_1 (.clk(t_st_r380_1__clk), .d(st_b300_rraw), .q(st_r380_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r380_1 (.clk(t_st_r380_1__clk), .rst_raw_n(st_r380_1_rraw), .p_start(st_b300_start), .start(st_r380_1_start));
    wire st_b380_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b380 (.clk(t_st_b380__clk), .d(st_r380_1_rraw), .q(st_b380_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b380 (.clk(t_st_b380__clk), .rst_raw_n(st_b380_rraw), .p_start(st_r380_1_start), .start(st_b380_start));
    wire st_r381_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r381_1 (.clk(t_st_r381_1__clk), .d(st_b380_rraw), .q(st_r381_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r381_1 (.clk(t_st_r381_1__clk), .rst_raw_n(st_r381_1_rraw), .p_start(st_b380_start), .start(st_r381_1_start));
    wire st_b381_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b381 (.clk(t_st_b381__clk), .d(st_r381_1_rraw), .q(st_b381_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b381 (.clk(t_st_b381__clk), .rst_raw_n(st_b381_rraw), .p_start(st_r381_1_start), .start(st_b381_start));
    wire st_r477_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r477_1 (.clk(t_st_r477_1__clk), .d(st_b381_rraw), .q(st_r477_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r477_1 (.clk(t_st_r477_1__clk), .rst_raw_n(st_r477_1_rraw), .p_start(st_b381_start), .start(st_r477_1_start));
    wire st_b477_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b477 (.clk(t_st_b477__clk), .d(st_r477_1_rraw), .q(st_b477_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b477 (.clk(t_st_b477__clk), .rst_raw_n(st_b477_rraw), .p_start(st_r477_1_start), .start(st_b477_start));
    wire st_r478_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r478_1 (.clk(t_st_r478_1__clk), .d(st_b477_rraw), .q(st_r478_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r478_1 (.clk(t_st_r478_1__clk), .rst_raw_n(st_r478_1_rraw), .p_start(st_b477_start), .start(st_r478_1_start));
    wire st_b478_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b478 (.clk(t_st_b478__clk), .d(st_r478_1_rraw), .q(st_b478_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b478 (.clk(t_st_b478__clk), .rst_raw_n(st_b478_rraw), .p_start(st_r478_1_start), .start(st_b478_start));
    wire st_r563_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r563_1 (.clk(t_st_r563_1__clk), .d(st_b478_rraw), .q(st_r563_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r563_1 (.clk(t_st_r563_1__clk), .rst_raw_n(st_r563_1_rraw), .p_start(st_b478_start), .start(st_r563_1_start));
    wire st_b563_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b563 (.clk(t_st_b563__clk), .d(st_r563_1_rraw), .q(st_b563_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b563 (.clk(t_st_b563__clk), .rst_raw_n(st_b563_rraw), .p_start(st_r563_1_start), .start(st_b563_start));
    wire st_r564_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r564_1 (.clk(t_st_r564_1__clk), .d(st_b563_rraw), .q(st_r564_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r564_1 (.clk(t_st_r564_1__clk), .rst_raw_n(st_r564_1_rraw), .p_start(st_b563_start), .start(st_r564_1_start));
    wire st_b564_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b564 (.clk(t_st_b564__clk), .d(st_r564_1_rraw), .q(st_b564_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b564 (.clk(t_st_b564__clk), .rst_raw_n(st_b564_rraw), .p_start(st_r564_1_start), .start(st_b564_start));
    wire st_r661_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r661_1 (.clk(t_st_r661_1__clk), .d(st_b564_rraw), .q(st_r661_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r661_1 (.clk(t_st_r661_1__clk), .rst_raw_n(st_r661_1_rraw), .p_start(st_b564_start), .start(st_r661_1_start));
    wire st_b661_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b661 (.clk(t_st_b661__clk), .d(st_r661_1_rraw), .q(st_b661_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b661 (.clk(t_st_b661__clk), .rst_raw_n(st_b661_rraw), .p_start(st_r661_1_start), .start(st_b661_start));
    wire st_r662_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r662_1 (.clk(t_st_r662_1__clk), .d(st_b661_rraw), .q(st_r662_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r662_1 (.clk(t_st_r662_1__clk), .rst_raw_n(st_r662_1_rraw), .p_start(st_b661_start), .start(st_r662_1_start));
    wire st_b662_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b662 (.clk(t_st_b662__clk), .d(st_r662_1_rraw), .q(st_b662_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b662 (.clk(t_st_b662__clk), .rst_raw_n(st_b662_rraw), .p_start(st_r662_1_start), .start(st_b662_start));
    wire st_b741_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b741 (.clk(t_st_b741__clk), .d(st_b662_rraw), .q(st_b741_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b741 (.clk(t_st_b741__clk), .rst_raw_n(st_b741_rraw), .p_start(st_b662_start), .start(st_b741_start));
    wire st_r745_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r745_1 (.clk(t_st_r745_1__clk), .d(st_b662_rraw), .q(st_r745_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r745_1 (.clk(t_st_r745_1__clk), .rst_raw_n(st_r745_1_rraw), .p_start(st_b662_start), .start(st_r745_1_start));
    wire st_b747_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b747 (.clk(t_st_b747__clk), .d(st_b662_rraw), .q(st_b747_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b747 (.clk(t_st_b747__clk), .rst_raw_n(st_b747_rraw), .p_start(st_b662_start), .start(st_b747_start));
    wire st_r742_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r742_1 (.clk(t_st_r742_1__clk), .d(st_b741_rraw), .q(st_r742_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r742_1 (.clk(t_st_r742_1__clk), .rst_raw_n(st_r742_1_rraw), .p_start(st_b741_start), .start(st_r742_1_start));
    wire st_b745_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b745 (.clk(t_st_b745__clk), .d(st_r745_1_rraw), .q(st_b745_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b745 (.clk(t_st_b745__clk), .rst_raw_n(st_b745_rraw), .p_start(st_r745_1_start), .start(st_b745_start));
    wire st_r748_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r748_1 (.clk(t_st_r748_1__clk), .d(st_b747_rraw), .q(st_r748_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r748_1 (.clk(t_st_r748_1__clk), .rst_raw_n(st_r748_1_rraw), .p_start(st_b747_start), .start(st_r748_1_start));
    wire st_b742_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b742 (.clk(t_st_b742__clk), .d(st_r742_1_rraw), .q(st_b742_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b742 (.clk(t_st_b742__clk), .rst_raw_n(st_b742_rraw), .p_start(st_r742_1_start), .start(st_b742_start));
    wire st_r746_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r746_1 (.clk(t_st_r746_1__clk), .d(st_b745_rraw), .q(st_r746_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r746_1 (.clk(t_st_r746_1__clk), .rst_raw_n(st_r746_1_rraw), .p_start(st_b745_start), .start(st_r746_1_start));
    wire st_b748_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b748 (.clk(t_st_b748__clk), .d(st_r748_1_rraw), .q(st_b748_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b748 (.clk(t_st_b748__clk), .rst_raw_n(st_b748_rraw), .p_start(st_r748_1_start), .start(st_b748_start));
    wire st_b743_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b743 (.clk(t_st_b743__clk), .d(st_b742_rraw), .q(st_b743_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b743 (.clk(t_st_b743__clk), .rst_raw_n(st_b743_rraw), .p_start(st_b742_start), .start(st_b743_start));
    wire st_b746_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b746 (.clk(t_st_b746__clk), .d(st_r746_1_rraw), .q(st_b746_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b746 (.clk(t_st_b746__clk), .rst_raw_n(st_b746_rraw), .p_start(st_r746_1_start), .start(st_b746_start));
    wire st_b749_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b749 (.clk(t_st_b749__clk), .d(st_b748_rraw), .q(st_b749_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b749 (.clk(t_st_b749__clk), .rst_raw_n(st_b749_rraw), .p_start(st_b748_start), .start(st_b749_start));
    wire st_r744_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r744_1 (.clk(t_st_r744_1__clk), .d(st_b743_rraw), .q(st_r744_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r744_1 (.clk(t_st_r744_1__clk), .rst_raw_n(st_r744_1_rraw), .p_start(st_b743_start), .start(st_r744_1_start));
    wire st_r750_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r750_1 (.clk(t_st_r750_1__clk), .d(st_b749_rraw), .q(st_r750_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r750_1 (.clk(t_st_r750_1__clk), .rst_raw_n(st_r750_1_rraw), .p_start(st_b749_start), .start(st_r750_1_start));
    wire st_b744_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b744 (.clk(t_st_b744__clk), .d(st_r744_1_rraw), .q(st_b744_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b744 (.clk(t_st_b744__clk), .rst_raw_n(st_b744_rraw), .p_start(st_r744_1_start), .start(st_b744_start));
    wire st_b6499_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b6499 (.clk(t_st_b6499__clk), .d(st_b746_rraw), .q(st_b6499_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b6499 (.clk(t_st_b6499__clk), .rst_raw_n(st_b6499_rraw), .p_start(st_b746_start), .start(st_b6499_start));
    wire st_b750_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b750 (.clk(t_st_b750__clk), .d(st_r750_1_rraw), .q(st_b750_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b750 (.clk(t_st_b750__clk), .rst_raw_n(st_b750_rraw), .p_start(st_r750_1_start), .start(st_b750_start));
    wire st_r841_0_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r841_0 (.clk(t_st_r841_0__clk), .d(st_b750_rraw), .q(st_r841_0_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r841_0 (.clk(t_st_r841_0__clk), .rst_raw_n(st_r841_0_rraw), .p_start(st_b750_start), .start(st_r841_0_start));
    wire st_r841_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r841_1 (.clk(t_st_r841_1__clk), .d(st_r841_0_rraw), .q(st_r841_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r841_1 (.clk(t_st_r841_1__clk), .rst_raw_n(st_r841_1_rraw), .p_start(st_r841_0_start), .start(st_r841_1_start));
    wire st_r844_2_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r844_2 (.clk(t_st_r844_2__clk), .d(st_b750_rraw), .q(st_r844_2_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r844_2 (.clk(t_st_r844_2__clk), .rst_raw_n(st_r844_2_rraw), .p_start(st_b750_start), .start(st_r844_2_start));
    wire st_b6375_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b6375 (.clk(t_st_b6375__clk), .d(st_b744_rraw), .q(st_b6375_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b6375 (.clk(t_st_b6375__clk), .rst_raw_n(st_b6375_rraw), .p_start(st_b744_start), .start(st_b6375_start));
    wire st_b17286_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b17286 (.clk(t_st_b17286__clk), .d(st_b750_rraw), .q(st_b17286_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b17286 (.clk(t_st_b17286__clk), .rst_raw_n(st_b17286_rraw), .p_start(st_b750_start), .start(st_b17286_start));
    wire st_b842_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b842 (.clk(t_st_b842__clk), .d(st_r841_1_rraw), .q(st_b842_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b842 (.clk(t_st_b842__clk), .rst_raw_n(st_b842_rraw), .p_start(st_r841_1_start), .start(st_b842_start));
    wire st_b845_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b845 (.clk(t_st_b845__clk), .d(st_r844_2_rraw), .q(st_b845_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b845 (.clk(t_st_b845__clk), .rst_raw_n(st_b845_rraw), .p_start(st_r844_2_start), .start(st_b845_start));
    wire st_r6377_0_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r6377_0 (.clk(t_st_r6377_0__clk), .d(st_b6375_rraw), .q(st_r6377_0_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r6377_0 (.clk(t_st_r6377_0__clk), .rst_raw_n(st_r6377_0_rraw), .p_start(st_b6375_start), .start(st_r6377_0_start));
    wire st_b846_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b846 (.clk(t_st_b846__clk), .d(st_b845_rraw), .q(st_b846_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b846 (.clk(t_st_b846__clk), .rst_raw_n(st_b846_rraw), .p_start(st_b845_start), .start(st_b846_start));
    wire st_r6747_1_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r6747_1 (.clk(t_st_r6747_1__clk), .d(st_b842_rraw), .q(st_r6747_1_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r6747_1 (.clk(t_st_r6747_1__clk), .rst_raw_n(st_r6747_1_rraw), .p_start(st_b842_start), .start(st_r6747_1_start));
    wire st_b17296_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_b17296 (.clk(t_st_b17296__clk), .d(st_b17286_rraw), .q(st_b17296_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_b17296 (.clk(t_st_b17296__clk), .rst_raw_n(st_b17296_rraw), .p_start(st_b17286_start), .start(st_b17296_start));
    wire st_r6748_0_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r6748_0 (.clk(t_st_r6748_0__clk), .d(st_r6747_1_rraw), .q(st_r6748_0_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r6748_0 (.clk(t_st_r6748_0__clk), .rst_raw_n(st_r6748_0_rraw), .p_start(st_r6747_1_start), .start(st_r6748_0_start));
    wire st_b6778_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(0)) u_rst_b6778 (.clk(t_st_b6778__clk), .d(st_b846_rraw), .q(st_b6778_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(0)) u_st_b6778 (.clk(t_st_b6778__clk), .rst_raw_n(st_b6778_rraw), .p_start(st_b846_start), .start(st_b6778_start));
    wire st_r6779_0_rraw;
    ot_die_start_reset_relay #(.EDGE_FALL(1)) u_rst_r6779_0 (.clk(t_st_r6779_0__clk), .d(st_b6778_rraw), .q(st_r6779_0_rraw));
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_st_r6779_0 (.clk(t_st_r6779_0__clk), .rst_raw_n(st_r6779_0_rraw), .p_start(st_b6778_start), .start(st_r6779_0_start));
    assign pst_sl_W5_ctl = st_r6377_0_start;
    assign pst_sl_W5_stm = st_b6499_start;
    assign pst_sl_W5_su_c = st_b17296_start;
    assign pst_sl_W5_su_l0 = st_r6748_0_start;
    assign pst_sl_W5_su_l1 = st_r6779_0_start;
endmodule
(* keep_hierarchy *) module ot_die_start_reset_relay #(parameter bit EDGE_FALL=0) (
    input wire clk, input wire d, output wire q);
    (* keep = "true" *) reg r0, r1;
    wire x;
    if (EDGE_FALL) begin: g_fall
        (* keep = "true" *) reg rf;
        always @(negedge clk) rf <= d;
        assign x=rf;
    end else begin: g_rise assign x=d; end
    always @(posedge clk) begin r0<=x; r1<=r0; end
    assign q=r1;
endmodule
