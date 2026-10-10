// hfd_cmdproc: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 command processor (hgi-takeover 2026-10-09): ot_hgi_cp_die = hbm-forks ot_hgi_cp (config path + v1.0 sequencer) + loader link stations + VM read client + per-unit dispatch credits. One block (no N / S split). Units without a record adapter yet (ux_*) and the legacy SM launch tree (c*), SU (t_su_*), barrier, router and legacy coll config buses are not driven by the HGI CP: they show as ties until hgi-adapters lands the unit adapters. Bench rtl/hbm_accel/generic/tb/tb_hgi_cp_die_seq.sv: all sequencer vectors through the die binding exact. Single-CP die with the ARGMAX unit (hgi-takeover decision (3), mtp-lead item (1)): am_rec 691 = {die_id, n_O, n_A, O, A, header, valid} / am_ret 3 to hfd_hgi_am (MTP slot), unit 7 credit.
module hfd_cmdproc (
    inout wire [826:0] cNE,
    inout wire [826:0] cNW,
    inout wire [826:0] cSE,
    inout wire [826:0] cSW,
    input wire [0:0] ck,
    input wire [63:0] f_barrier,
    input wire [32:0] f_coll,
    input wire [2:0] f_hgi_argmax,
    input wire [2:0] f_hgi_coll,
    input wire [2:0] f_hgi_idx,
    input wire [418:0] f_hgi_loader,
    input wire [2:0] f_hgi_quant,
    input wire [273:0] f_hgi_vmr,
    input wire [18:0] f_hgi_vmstat,
    input wire [516:0] f_mtp,
    input wire [0:0] rst,
    output wire [63:0] t_barrier,
    output wire [24:0] t_coll,
    output wire [690:0] t_hgi_argmax,
    output wire [39:0] t_hgi_cfg_coll,
    output wire [967:0] t_hgi_coll,
    output wire [1818:0] t_hgi_idx,
    output wire [221:0] t_hgi_loader,
    output wire [682:0] t_hgi_quant,
    output wire [337:0] t_hgi_vmq,
    output wire [196:0] t_mtp,
    output wire [63:0] t_su_NE,
    output wire [63:0] t_su_NW,
    output wire [63:0] t_su_SE,
    output wire [63:0] t_su_SW
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [826:0] i0_cNE; always @(posedge clk) i0_cNE <= cNE;
    reg [826:0] i1_cNE; always @(posedge clk) i1_cNE <= i0_cNE;
    reg [826:0] i2_cNE; always @(posedge clk) i2_cNE <= i1_cNE;
    reg [826:0] i3_cNE; always @(posedge clk) i3_cNE <= i2_cNE;
    reg [826:0] i_cNE; always @(posedge clk) i_cNE <= i3_cNE;
    reg [826:0] i0_cNW; always @(posedge clk) i0_cNW <= cNW;
    reg [826:0] i1_cNW; always @(posedge clk) i1_cNW <= i0_cNW;
    reg [826:0] i2_cNW; always @(posedge clk) i2_cNW <= i1_cNW;
    reg [826:0] i3_cNW; always @(posedge clk) i3_cNW <= i2_cNW;
    reg [826:0] i_cNW; always @(posedge clk) i_cNW <= i3_cNW;
    reg [826:0] i0_cSE; always @(posedge clk) i0_cSE <= cSE;
    reg [826:0] i1_cSE; always @(posedge clk) i1_cSE <= i0_cSE;
    reg [826:0] i2_cSE; always @(posedge clk) i2_cSE <= i1_cSE;
    reg [826:0] i3_cSE; always @(posedge clk) i3_cSE <= i2_cSE;
    reg [826:0] i_cSE; always @(posedge clk) i_cSE <= i3_cSE;
    reg [826:0] i0_cSW; always @(posedge clk) i0_cSW <= cSW;
    reg [826:0] i1_cSW; always @(posedge clk) i1_cSW <= i0_cSW;
    reg [826:0] i2_cSW; always @(posedge clk) i2_cSW <= i1_cSW;
    reg [826:0] i3_cSW; always @(posedge clk) i3_cSW <= i2_cSW;
    reg [826:0] i_cSW; always @(posedge clk) i_cSW <= i3_cSW;
    reg [63:0] i0_f_barrier; always @(posedge clk) i0_f_barrier <= f_barrier;
    reg [63:0] i1_f_barrier; always @(posedge clk) i1_f_barrier <= i0_f_barrier;
    reg [63:0] i2_f_barrier; always @(posedge clk) i2_f_barrier <= i1_f_barrier;
    reg [63:0] i3_f_barrier; always @(posedge clk) i3_f_barrier <= i2_f_barrier;
    reg [63:0] i_f_barrier; always @(posedge clk) i_f_barrier <= i3_f_barrier;
    reg [32:0] i0_f_coll; always @(posedge clk) i0_f_coll <= f_coll;
    reg [32:0] i1_f_coll; always @(posedge clk) i1_f_coll <= i0_f_coll;
    reg [32:0] i2_f_coll; always @(posedge clk) i2_f_coll <= i1_f_coll;
    reg [32:0] i3_f_coll; always @(posedge clk) i3_f_coll <= i2_f_coll;
    reg [32:0] i_f_coll; always @(posedge clk) i_f_coll <= i3_f_coll;
    reg [2:0] i0_f_hgi_argmax; always @(posedge clk) i0_f_hgi_argmax <= f_hgi_argmax;
    reg [2:0] i1_f_hgi_argmax; always @(posedge clk) i1_f_hgi_argmax <= i0_f_hgi_argmax;
    reg [2:0] i2_f_hgi_argmax; always @(posedge clk) i2_f_hgi_argmax <= i1_f_hgi_argmax;
    reg [2:0] i3_f_hgi_argmax; always @(posedge clk) i3_f_hgi_argmax <= i2_f_hgi_argmax;
    reg [2:0] i_f_hgi_argmax; always @(posedge clk) i_f_hgi_argmax <= i3_f_hgi_argmax;
    reg [2:0] i0_f_hgi_coll; always @(posedge clk) i0_f_hgi_coll <= f_hgi_coll;
    reg [2:0] i1_f_hgi_coll; always @(posedge clk) i1_f_hgi_coll <= i0_f_hgi_coll;
    reg [2:0] i2_f_hgi_coll; always @(posedge clk) i2_f_hgi_coll <= i1_f_hgi_coll;
    reg [2:0] i3_f_hgi_coll; always @(posedge clk) i3_f_hgi_coll <= i2_f_hgi_coll;
    reg [2:0] i_f_hgi_coll; always @(posedge clk) i_f_hgi_coll <= i3_f_hgi_coll;
    reg [2:0] i0_f_hgi_idx; always @(posedge clk) i0_f_hgi_idx <= f_hgi_idx;
    reg [2:0] i1_f_hgi_idx; always @(posedge clk) i1_f_hgi_idx <= i0_f_hgi_idx;
    reg [2:0] i2_f_hgi_idx; always @(posedge clk) i2_f_hgi_idx <= i1_f_hgi_idx;
    reg [2:0] i3_f_hgi_idx; always @(posedge clk) i3_f_hgi_idx <= i2_f_hgi_idx;
    reg [2:0] i_f_hgi_idx; always @(posedge clk) i_f_hgi_idx <= i3_f_hgi_idx;
    reg [418:0] i0_f_hgi_loader; always @(posedge clk) i0_f_hgi_loader <= f_hgi_loader;
    reg [418:0] i1_f_hgi_loader; always @(posedge clk) i1_f_hgi_loader <= i0_f_hgi_loader;
    reg [418:0] i2_f_hgi_loader; always @(posedge clk) i2_f_hgi_loader <= i1_f_hgi_loader;
    reg [418:0] i3_f_hgi_loader; always @(posedge clk) i3_f_hgi_loader <= i2_f_hgi_loader;
    reg [418:0] i_f_hgi_loader; always @(posedge clk) i_f_hgi_loader <= i3_f_hgi_loader;
    reg [2:0] i0_f_hgi_quant; always @(posedge clk) i0_f_hgi_quant <= f_hgi_quant;
    reg [2:0] i1_f_hgi_quant; always @(posedge clk) i1_f_hgi_quant <= i0_f_hgi_quant;
    reg [2:0] i2_f_hgi_quant; always @(posedge clk) i2_f_hgi_quant <= i1_f_hgi_quant;
    reg [2:0] i3_f_hgi_quant; always @(posedge clk) i3_f_hgi_quant <= i2_f_hgi_quant;
    reg [2:0] i_f_hgi_quant; always @(posedge clk) i_f_hgi_quant <= i3_f_hgi_quant;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i1_f_hgi_vmr; always @(posedge clk) i1_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [273:0] i2_f_hgi_vmr; always @(posedge clk) i2_f_hgi_vmr <= i1_f_hgi_vmr;
    reg [273:0] i3_f_hgi_vmr; always @(posedge clk) i3_f_hgi_vmr <= i2_f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i3_f_hgi_vmr;
    reg [18:0] i0_f_hgi_vmstat; always @(posedge clk) i0_f_hgi_vmstat <= f_hgi_vmstat;
    reg [18:0] i1_f_hgi_vmstat; always @(posedge clk) i1_f_hgi_vmstat <= i0_f_hgi_vmstat;
    reg [18:0] i2_f_hgi_vmstat; always @(posedge clk) i2_f_hgi_vmstat <= i1_f_hgi_vmstat;
    reg [18:0] i3_f_hgi_vmstat; always @(posedge clk) i3_f_hgi_vmstat <= i2_f_hgi_vmstat;
    reg [18:0] i_f_hgi_vmstat; always @(posedge clk) i_f_hgi_vmstat <= i3_f_hgi_vmstat;
    reg [516:0] i0_f_mtp; always @(posedge clk) i0_f_mtp <= f_mtp;
    reg [516:0] i1_f_mtp; always @(posedge clk) i1_f_mtp <= i0_f_mtp;
    reg [516:0] i2_f_mtp; always @(posedge clk) i2_f_mtp <= i1_f_mtp;
    reg [516:0] i3_f_mtp; always @(posedge clk) i3_f_mtp <= i2_f_mtp;
    reg [516:0] i_f_mtp; always @(posedge clk) i_f_mtp <= i3_f_mtp;
    wire [0:0] w_cpd_clk;
    wire [0:0] w_cpd_rst_n;
    wire [418:0] w_cpd_lcp;
    wire [221:0] w_cpd_cpl;
    wire [337:0] w_cpd_vmq;
    wire [273:0] w_cpd_vmr;
    wire [18:0] w_cpd_vmstat;
    wire [967:0] w_cpd_coll_rec;
    wire [2:0] w_cpd_coll_ret;
    wire [682:0] w_cpd_quant_rec;
    wire [2:0] w_cpd_quant_ret;
    wire [1818:0] w_cpd_idx_rec;
    wire [2:0] w_cpd_idx_ret;
    wire [690:0] w_cpd_am_rec;
    wire [2:0] w_cpd_am_ret;
    wire [39:0] w_cpd_cfg_bus;
    wire [15:0] w_cpd_ux_v;
    wire [15:0] w_cpd_ux_rdy;
    wire [15:0] w_cpd_ux_done;
    wire [15:0] w_cpd_ux_fault;
    wire [0:0] w_cpd_wr_quiet;
    // configuration chain: 49 RTL input bits the die interface does not carry, shifted from die input cNE[42]
    reg [48:0] cfg; always @(posedge clk) cfg <= {cfg[47:0], i_cNE[42]};
    assign w_cpd_clk = {1{clk}};
    assign w_cpd_rst_n = {1{rst_n}};
    assign w_cpd_lcp = {i_f_hgi_loader[418:0]};
    assign w_cpd_vmr = {i_f_hgi_vmr[273:0]};
    assign w_cpd_vmstat = {i_f_hgi_vmstat[18:0]};
    assign w_cpd_coll_ret = {i_f_hgi_coll[2:0]};
    assign w_cpd_quant_ret = {i_f_hgi_quant[2:0]};
    assign w_cpd_idx_ret = {i_f_hgi_idx[2:0]};
    assign w_cpd_am_ret = {i_f_hgi_argmax[2:0]};
    assign w_cpd_ux_rdy = cfg[15:0];
    assign w_cpd_ux_done = cfg[31:16];
    assign w_cpd_ux_fault = cfg[47:32];
    assign w_cpd_wr_quiet = cfg[48:48];
    ot_hgi_cp_die #(.USE_MACRO(1)) u_cpd (.clk(w_cpd_clk), .rst_n(w_cpd_rst_n), .lcp(w_cpd_lcp), .cpl(w_cpd_cpl), .vmq(w_cpd_vmq), .vmr(w_cpd_vmr), .vmstat(w_cpd_vmstat), .coll_rec(w_cpd_coll_rec), .coll_ret(w_cpd_coll_ret), .quant_rec(w_cpd_quant_rec), .quant_ret(w_cpd_quant_ret), .idx_rec(w_cpd_idx_rec), .idx_ret(w_cpd_idx_ret), .am_rec(w_cpd_am_rec), .am_ret(w_cpd_am_ret), .cfg_bus(w_cpd_cfg_bus), .ux_v(w_cpd_ux_v), .ux_rdy(w_cpd_ux_rdy), .ux_done(w_cpd_ux_done), .ux_fault(w_cpd_ux_fault), .wr_quiet(w_cpd_wr_quiet));
    for (genvar k = 0; k < 16; k = k + 1) begin : g_sink_w_cpd_ux_v
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpd_ux_v[k]), .q());
    end
    wire fclk_0; ot_fwd_clk_inv u_fclk_0 (.a(clk), .y(fclk_0));
    wire fclk_1; ot_fwd_clk_inv u_fclk_1 (.a(clk), .y(fclk_1));
    wire fclk_2; ot_fwd_clk_inv u_fclk_2 (.a(clk), .y(fclk_2));
    wire fclk_3; ot_fwd_clk_inv u_fclk_3 (.a(clk), .y(fclk_3));
    wire fclk_4; ot_fwd_clk_inv u_fclk_4 (.a(clk), .y(fclk_4));
    wire fclk_5; ot_fwd_clk_inv u_fclk_5 (.a(clk), .y(fclk_5));
    wire fclk_6; ot_fwd_clk_inv u_fclk_6 (.a(clk), .y(fclk_6));
    wire fclk_7; ot_fwd_clk_inv u_fclk_7 (.a(clk), .y(fclk_7));
    wire [826:0] od_cNE = {827'd0};
    wire [826:0] o_cNE;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cNE
        ot_hfd_oreg5 u (.clk(clk), .d(od_cNE[k]), .q(o_cNE[k]));
    end
    assign cNE[41:0] = o_cNE[41:0];
    assign cNE[101:45] = o_cNE[101:45];
    assign cNE[144:103] = o_cNE[144:103];
    assign cNE[204:148] = o_cNE[204:148];
    assign cNE[247:206] = o_cNE[247:206];
    assign cNE[307:251] = o_cNE[307:251];
    assign cNE[350:309] = o_cNE[350:309];
    assign cNE[410:354] = o_cNE[410:354];
    assign cNE[453:412] = o_cNE[453:412];
    assign cNE[513:457] = o_cNE[513:457];
    assign cNE[556:515] = o_cNE[556:515];
    assign cNE[616:560] = o_cNE[616:560];
    assign cNE[659:618] = o_cNE[659:618];
    assign cNE[719:663] = o_cNE[719:663];
    assign cNE[762:721] = o_cNE[762:721];
    assign cNE[822:766] = o_cNE[822:766];
    assign cNE[824] = fclk_0;
    assign cNE[825] = fclk_1;
    wire [826:0] od_cNW = {827'd0};
    wire [826:0] o_cNW;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cNW
        ot_hfd_oreg5 u (.clk(clk), .d(od_cNW[k]), .q(o_cNW[k]));
    end
    assign cNW[41:0] = o_cNW[41:0];
    assign cNW[101:45] = o_cNW[101:45];
    assign cNW[144:103] = o_cNW[144:103];
    assign cNW[204:148] = o_cNW[204:148];
    assign cNW[247:206] = o_cNW[247:206];
    assign cNW[307:251] = o_cNW[307:251];
    assign cNW[350:309] = o_cNW[350:309];
    assign cNW[410:354] = o_cNW[410:354];
    assign cNW[453:412] = o_cNW[453:412];
    assign cNW[513:457] = o_cNW[513:457];
    assign cNW[556:515] = o_cNW[556:515];
    assign cNW[616:560] = o_cNW[616:560];
    assign cNW[659:618] = o_cNW[659:618];
    assign cNW[719:663] = o_cNW[719:663];
    assign cNW[762:721] = o_cNW[762:721];
    assign cNW[822:766] = o_cNW[822:766];
    assign cNW[824] = fclk_2;
    assign cNW[825] = fclk_3;
    wire [826:0] od_cSE = {827'd0};
    wire [826:0] o_cSE;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cSE
        ot_hfd_oreg5 u (.clk(clk), .d(od_cSE[k]), .q(o_cSE[k]));
    end
    assign cSE[41:0] = o_cSE[41:0];
    assign cSE[101:45] = o_cSE[101:45];
    assign cSE[144:103] = o_cSE[144:103];
    assign cSE[204:148] = o_cSE[204:148];
    assign cSE[247:206] = o_cSE[247:206];
    assign cSE[307:251] = o_cSE[307:251];
    assign cSE[350:309] = o_cSE[350:309];
    assign cSE[410:354] = o_cSE[410:354];
    assign cSE[453:412] = o_cSE[453:412];
    assign cSE[513:457] = o_cSE[513:457];
    assign cSE[556:515] = o_cSE[556:515];
    assign cSE[616:560] = o_cSE[616:560];
    assign cSE[659:618] = o_cSE[659:618];
    assign cSE[719:663] = o_cSE[719:663];
    assign cSE[762:721] = o_cSE[762:721];
    assign cSE[822:766] = o_cSE[822:766];
    assign cSE[824] = fclk_4;
    assign cSE[825] = fclk_5;
    wire [826:0] od_cSW = {827'd0};
    wire [826:0] o_cSW;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cSW
        ot_hfd_oreg5 u (.clk(clk), .d(od_cSW[k]), .q(o_cSW[k]));
    end
    assign cSW[41:0] = o_cSW[41:0];
    assign cSW[101:45] = o_cSW[101:45];
    assign cSW[144:103] = o_cSW[144:103];
    assign cSW[204:148] = o_cSW[204:148];
    assign cSW[247:206] = o_cSW[247:206];
    assign cSW[307:251] = o_cSW[307:251];
    assign cSW[350:309] = o_cSW[350:309];
    assign cSW[410:354] = o_cSW[410:354];
    assign cSW[453:412] = o_cSW[453:412];
    assign cSW[513:457] = o_cSW[513:457];
    assign cSW[556:515] = o_cSW[556:515];
    assign cSW[616:560] = o_cSW[616:560];
    assign cSW[659:618] = o_cSW[659:618];
    assign cSW[719:663] = o_cSW[719:663];
    assign cSW[762:721] = o_cSW[762:721];
    assign cSW[822:766] = o_cSW[822:766];
    assign cSW[824] = fclk_6;
    assign cSW[825] = fclk_7;
    wire [63:0] od_t_barrier = {64'd0};
    wire [63:0] o_t_barrier;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_barrier
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_barrier[k]), .q(o_t_barrier[k]));
    end
    assign t_barrier[63:0] = o_t_barrier[63:0];
    wire [24:0] od_t_coll = {25'd0};
    wire [24:0] o_t_coll;
    for (genvar k = 0; k < 25; k = k + 1) begin : g_o_t_coll
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_coll[k]), .q(o_t_coll[k]));
    end
    assign t_coll[24:0] = o_t_coll[24:0];
    wire [690:0] od_t_hgi_argmax = {w_cpd_am_rec[690:0]};
    wire [690:0] o_t_hgi_argmax;
    for (genvar k = 0; k < 691; k = k + 1) begin : g_o_t_hgi_argmax
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_argmax[k]), .q(o_t_hgi_argmax[k]));
    end
    assign t_hgi_argmax[690:0] = o_t_hgi_argmax[690:0];
    wire [39:0] od_t_hgi_cfg_coll = {w_cpd_cfg_bus[39:0]};
    wire [39:0] o_t_hgi_cfg_coll;
    for (genvar k = 0; k < 40; k = k + 1) begin : g_o_t_hgi_cfg_coll
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_cfg_coll[k]), .q(o_t_hgi_cfg_coll[k]));
    end
    assign t_hgi_cfg_coll[39:0] = o_t_hgi_cfg_coll[39:0];
    wire [967:0] od_t_hgi_coll = {w_cpd_coll_rec[967:0]};
    wire [967:0] o_t_hgi_coll;
    for (genvar k = 0; k < 968; k = k + 1) begin : g_o_t_hgi_coll
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_coll[k]), .q(o_t_hgi_coll[k]));
    end
    assign t_hgi_coll[967:0] = o_t_hgi_coll[967:0];
    wire [1818:0] od_t_hgi_idx = {w_cpd_idx_rec[1818:0]};
    wire [1818:0] o_t_hgi_idx;
    for (genvar k = 0; k < 1819; k = k + 1) begin : g_o_t_hgi_idx
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_idx[k]), .q(o_t_hgi_idx[k]));
    end
    assign t_hgi_idx[1818:0] = o_t_hgi_idx[1818:0];
    wire [221:0] od_t_hgi_loader = {w_cpd_cpl[221:0]};
    wire [221:0] o_t_hgi_loader;
    for (genvar k = 0; k < 222; k = k + 1) begin : g_o_t_hgi_loader
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_loader[k]), .q(o_t_hgi_loader[k]));
    end
    assign t_hgi_loader[221:0] = o_t_hgi_loader[221:0];
    wire [682:0] od_t_hgi_quant = {w_cpd_quant_rec[682:0]};
    wire [682:0] o_t_hgi_quant;
    for (genvar k = 0; k < 683; k = k + 1) begin : g_o_t_hgi_quant
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_quant[k]), .q(o_t_hgi_quant[k]));
    end
    assign t_hgi_quant[682:0] = o_t_hgi_quant[682:0];
    wire [337:0] od_t_hgi_vmq = {w_cpd_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmq[k]), .q(o_t_hgi_vmq[k]));
    end
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
    wire [196:0] od_t_mtp = {197'd0};
    wire [196:0] o_t_mtp;
    for (genvar k = 0; k < 197; k = k + 1) begin : g_o_t_mtp
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_mtp[k]), .q(o_t_mtp[k]));
    end
    assign t_mtp[196:0] = o_t_mtp[196:0];
    wire [63:0] od_t_su_NE = {64'd0};
    wire [63:0] o_t_su_NE;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_NE
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_NE[k]), .q(o_t_su_NE[k]));
    end
    assign t_su_NE[63:0] = o_t_su_NE[63:0];
    wire [63:0] od_t_su_NW = {64'd0};
    wire [63:0] o_t_su_NW;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_NW
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_NW[k]), .q(o_t_su_NW[k]));
    end
    assign t_su_NW[63:0] = o_t_su_NW[63:0];
    wire [63:0] od_t_su_SE = {64'd0};
    wire [63:0] o_t_su_SE;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_SE
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_SE[k]), .q(o_t_su_SE[k]));
    end
    assign t_su_SE[63:0] = o_t_su_SE[63:0];
    wire [63:0] od_t_su_SW = {64'd0};
    wire [63:0] o_t_su_SW;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_SW
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_SW[k]), .q(o_t_su_SW[k]));
    end
    assign t_su_SW[63:0] = o_t_su_SW[63:0];
endmodule
