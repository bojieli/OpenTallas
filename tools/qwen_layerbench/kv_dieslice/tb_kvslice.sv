`timescale 1ns/1ps
// TOKj-KV 10-23: KV DIE-SLICE VEHICLE on the BOUND KV die top (qwen_kvsys_bound_top, tools/die_plan/bind.py output).
// The DUT is the whole bound top byte-for-byte (all 160 partitions, every landed lane / pad / R8 delay as bound).  Only
// the off-die boundaries are bench models (owner 10-14):
//   HBM PHY slices  qkd_hbm3e_phy_pc4      -> KV-P7 bench model (qkd_hbm3e_phy_pc4_bench.sv, RL 23, preload)
//   host SerDes     ot_qfd_serdes_112g_x6_phy x2 -> kvs_link_phy_models.sv; the far end = the HOST BOARD PORT, built from the
//                   real host link adapter + CDC RTL (qkd_host_board_port_fixture: qfd_link_adp512_split + qkd_host_phy_cdc5)
//   UCIe d2d PHY    ot_qkvd_ucie_x64_phy   -> kvs_link_phy_models.sv; far end = the compute-die driver (phase TOKEN)
// Clocks: the top clock inputs at the as-built PLL periods (qkd_hbm3e PLL analog model: core 1.2 GHz, hbm 0.977, host
// 1.0, ingest 0.6, phy 0.959); pad_refclk 100 MHz.  The die's own analog PLL model (hub_C u_pll) produces pll_locked.
// Phase BOOT (+PHASE=boot): replay the boot bundle (+FRAMES=<hex, one 528-b class-8 frame per line>) through the host
// board port with its credits (the die's host path is real RTL end to end); watch the host root's boot_image_* and the
// kvs_ctl dispatcher; PASS = every image of +EXPECT=<file: "target digest" per line, bundle order> reported ready with the
// expected target/digest/epoch, no boot fault, kvs_ctl setup_ready.  Mutant +MUT_FRAME=<n> flips data bit 19 of frame n
// (one program word) -> the image digest must mismatch -> FAIL required.
module tb_kvslice;
    // ------------------------------------------------------------------ clocks / reset
    reg ck_core = 0, ck_hbm = 0, ck_host = 0, ck_ing = 0, ck_phy = 0, ck_ref = 0;
    always #0.416667 ck_core = ~ck_core;
    always #0.512    ck_hbm  = ~ck_hbm;
    always #0.500    ck_host = ~ck_host;
    always #0.833334 ck_ing  = ~ck_ing;
    always #0.521500 ck_phy  = ~ck_phy;
    always #5.0      ck_ref  = ~ck_ref;
    reg por_n = 0, rst_n = 0;
    reg [2:0] die_id = 3'd1;
    // ------------------------------------------------------------------ link far ends (read by the PHY models)
    wire         h2d_v;
    wire [1042:0] h2d_flit;
    wire         c2k_v;
    wire [582:0] c2k_flit;
`ifdef KV_NATIVE_TOP
    // PATH-KV-TOK 10-25: native f5 bound top (codex-kv-bind-0719 run4 successor): ports rst_n, start, clk_core, clk_clk_phy,
    // pad_*; the HOST/HBM/ingest logic clocks are clk_core (native 833 common clock).  start = the die START pin (decision
    // 13c broadcast): +START_AT=<core cycles after rst_n release> (default 0 = START with reset release).  DIAGNOSTIC until
    // CLOCK-RESET start_role bootstrap|mission lands (today every consumer tap waits for START, so a late START stalls boot).
    reg start_pin = 0; integer start_at = 0;
    initial if (!$value$plusargs("START_AT=%d", start_at)) start_at = 0;
    always @(posedge ck_core) if (rst_n) begin
        if (start_at <= 0) start_pin <= 1'b1; else start_at <= start_at - 1;
    end
    qwen_kvsys_bound_top dut (
        .rst_n(rst_n), .start(start_pin), .clk_clk_phy(ck_phy), .clk_core(ck_core),
        .pad_die_id(die_id), .pad_por_n(por_n), .pad_refclk(ck_ref));
`else
    qwen_kvsys_bound_top dut (
        .rst_n(rst_n), .clk_clk_fwd(ck_core),
`ifndef KV_DFI_CORE   // TOK-QK/D dfi-core (owner decision 14): the HBM PHY DFI clock is clk_core -> the top has no HBM clock input
        .clk_clk_hbm_EN(ck_hbm), .clk_clk_hbm_ES(ck_hbm), .clk_clk_hbm_WN(ck_hbm), .clk_clk_hbm_WS(ck_hbm),
`endif
        .clk_clk_host(ck_host), .clk_clk_ingest(ck_ing), .clk_clk_phy(ck_phy), .clk_core(ck_core),
        .pad_die_id(die_id), .pad_por_n(por_n), .pad_refclk(ck_ref));
`endif
    // ------------------------------------------------------------------ compute-die far end on the UCIe link (+FAR=1)
    // KV-TOK 10-24 token phase: kvs_compute_end.sv (the compute die's real d2d master + calendar sequencer + record codec
    // + KVN transport on the pair image of the KV boot image; see that file).  +FAR=0 (default): the link is silent.
    // +EP_RAW=1 (DIAGNOSTIC): the compute pin follows the d2d_kv fwd_epoch / fwd_link_rst_n OUTPUT (before the 5 bound relay
    // stages to the bump pad u_fwb_*) -- isolates the epoch-anchor skew question (KV dcal EP_SKEW 3 vs pad + package).
    reg far_en = 0, far_m1 = 0, far_epraw = 0; reg [4:0] far_epb = 0; reg [12:0] far_pos = 13'd255;
    kvs_compute_end u_far (.ck(ck_core), .rst_n(rst_n), .en(far_en), .epb(far_epb), .epoch(dut.sys_c.i_host_token_epoch_q),
        .pos(far_pos), .kv_tx_v(dut.sys_c.w_d2d_kv_fdi_tx_v[0]), .kv_tx_flit(dut.sys_c.w_d2d_kv_fdi_tx_flit[582:0]),
        .kv_fwd_ep_pad(far_epraw ? dut.sys_c.w_d2d_kv_fwd_epoch[0] : dut.sys_c.d5_d2d_kv_fwd_epoch[0]),
        .kv_fwd_lrst_pad(far_epraw ? dut.sys_c.w_d2d_kv_fwd_link_rst_n[0] : dut.sys_c.d5_d2d_kv_fwd_link_rst_n[0]),
        .mut_cmd_late(far_m1), .c2k_v(c2k_v), .c2k_flit(c2k_flit));
    // die host TX (two halves) -> host board port RX
    // TOK-QK/C 10-24: the two x6 halves are separate in-order streams on clk_phy (each behind its own CDC FIFO); the board
    // PHY deskews them by order (ot_fdi_join2 on clk_phy) -- never a same-cycle AND of the halves.
    wire d2h_v; wire [1042:0] d2h_flit;
    ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_board_deskew (.clk(ck_phy), .rst_n(por_n),
        .a_v(dut.sys_SW.u_core.tx_v), .a_d(dut.sys_SW.u_core.tx_flit), .b_v(dut.sys_SE.u_core.tx_v), .b_d(dut.sys_SE.u_core.tx_flit),
        .o_v(d2h_v), .o_d(d2h_flit));
    reg  [1042:0] d2h_q [0:3]; reg d2h_vq [0:3];
    always @(posedge ck_phy) begin
        d2h_q[0] <= d2h_flit; d2h_vq[0] <= d2h_v;
        for (int i = 1; i < 4; i++) begin d2h_q[i] <= d2h_q[i-1]; d2h_vq[i] <= d2h_vq[i-1]; end
    end
    reg host_up = 0;
    reg  hc_tx_v = 0; reg [527:0] hc_tx_d = '0; wire hc_tx_cr;
    wire hc_rx_v; wire [527:0] hc_rx_d; reg hc_rx_cr = 0;
    wire [5:0] host_faults;
    qkd_host_board_port_fixture u_host (
        .ck_phy({8{ck_phy}}), .ck_pad(ck_phy), .ck_rx_core(ck_host), .ck_tx_core(ck_host), .rst_n(por_n), .phy_up(host_up),
        .phy_rx_v(d2h_vq[3]), .phy_rx_flit(d2h_q[3]), .phy_tx_v(h2d_v), .phy_tx_flit(h2d_flit),
        .core_tx_v(hc_tx_v), .core_tx_d(hc_tx_d), .core_tx_cr(hc_tx_cr),
        .core_rx_v(hc_rx_v), .core_rx_d(hc_rx_d), .core_rx_cr(hc_rx_cr), .faults(host_faults));
    // ------------------------------------------------------------------ observation taps (ports of RTL instances only)
    // (top-level lane wires of the bound top, so the partitions can be hierarchical Verilator blocks; each crossing word
    //  = data + epoch bit, one ot_dp_st stage after the source leaf -> the observed edge is +1 vs the leaf port)
    wire       b_ready  = dut.x_hub_Wi_o_host_boot_image_ready_hub_C[0];
    wire       b_fault  = dut.x_hub_Wi_o_host_boot_image_fault_hub_C[0];
    wire [3:0] b_target = dut.x_hub_Wi_o_host_boot_image_target_hub_C[3:0];
    wire [15:0] b_epoch = dut.x_hub_Wi_o_host_boot_image_epoch_hub_C[15:0];
    wire [63:0] b_dig   = dut.x_hub_Wi_o_host_boot_image_digest_hub_C[63:0];
    wire       setup    = dut.x_hub_C_o_kvs_ctl_boot_setup_ready_hub_Wi[0];
    wire       cf_fault = dut.x_hub_C_o_kvs_ctl_cf_root_fault_hub_Wi[0];
    wire       locked   = dut.x_hub_C_o_pll_locked_hub_Wi[0];
    // ------------------------------------------------------------------ stimulus
    reg [527:0] frames [0:16383];
    integer nfr = 0, mut_frame = -1, cyc_host = 0, sent = 0, credits = 4, rx_words = 0;
    integer n_ready = 0, n_exp = 0, errors = 0, ready_cyc [0:31], cyc_core = 0, t_setup = -1, t_bfault = -1, t_last = 0;
    reg [3:0] exp_t [0:31]; reg [63:0] exp_d [0:31];
    string fpath, epath, phase;
    integer maxcyc = 200000, setup_wait = 20000, epoch_exp = -1;
    always @(posedge ck_core) cyc_core <= cyc_core + 1;
    always @(posedge ck_host) begin
        cyc_host <= cyc_host + 1;
        hc_rx_cr <= hc_rx_v;                       // host consumes every die->host word at once (returns its credit)
        if (hc_rx_v) rx_words <= rx_words + 1;
    end
    // credit-based host sender (IBUF 4 of the host CDC write face)
    // TOK-QK/E 10-25: boot replay window.  The die's program loader (qkd_host_program_loader_target) replays an
    // authorised image on fixed consecutive ck_program_loader (= core) edges: REPLAY_P pw + REPLAY_W 1 + REPLAY_D dw +
    // READY 1, and a BEGIN that lands before READY is a protocol fault (sticky boot_image_fault; the unit bench
    // rtl/test/qwen_static_kv/tb_host_program_target.sv waits n+d+20 for the same reason).  The host -> die path is
    // credit flow controlled end to end (latency not cycle-fixed: the die adapter's 512-word link receive buffer drains at
    // the die's rate), so a gap counted from the AUTH send is shortened by the queue in front of it (measured: a 288-host-
    // cycle gap arrived as 251 core cycles, BEGIN at REPLAY_P index ~250).  The host program service therefore, after each
    // class-8 AUTH frame: (1) waits until its own link has drained -- the host CDC holds no word (all IBUF credits back),
    // the board adapter's die-face buffer is empty and it holds every link credit (tx_cred = RXD: the die adapter's receive
    // buffer is empty; host-side state only); (2) stays idle for the replay window of the image it just authorised (pw/dw
    // from that image's BEGIN), core -> host cycles, plus +BOOT_SLACK core cycles (default 32: the die skid / HOST CDC /
    // program_rx words behind the receive buffer, the READY edge, the ready lane to hub_C).
    // +BOOT_GAP=0 = the old back-to-back stream (negative control: the second BEGIN lands during REPLAY_P -> boot fault).
    `define KVS_HOST_ADP u_host.u_adapter.g_slice[0].u_slice.u_body
    localparam integer HOST_RXD = 512;     // qfd_link_adp128: ot_qfd_link_adapter RXD
    integer boot_gap_en = 1, boot_slack = 32, hold = 0, n_gaps = 0; reg drain_wait = 0; reg [10:0] img_pw = 0; reg [3:0] img_dw = 0;
    initial begin void'($value$plusargs("BOOT_GAP=%d", boot_gap_en)); void'($value$plusargs("BOOT_SLACK=%d", boot_slack)); end
    wire host_link_drained = (`KVS_HOST_ADP.ib_n == 0) && (int'(`KVS_HOST_ADP.tx_cred) == HOST_RXD) && !`KVS_HOST_ADP.ci_v;
    always @(posedge ck_host) if (host_up) begin
        automatic integer c = credits + (hc_tx_cr ? 1 : 0);
        hc_tx_v <= 1'b0;
        if (drain_wait) begin
            if (credits == 4 && !hc_tx_v && host_link_drained) begin
                drain_wait <= 1'b0;
                // core cycles (T 0.833334 ns) -> host cycles (T 1.0 ns), rounded up: ceil(n * 5 / 6)
                hold <= ((int'(img_pw) + int'(img_dw) + 2 + boot_slack) * 5 + 5) / 6;
            end
        end else if (hold > 0) hold <= hold - 1;
        else if (sent < nfr && c > 0) begin
            hc_tx_v <= 1'b1; hc_tx_d <= frames[sent] ^ ((sent == mut_frame) ? (528'd1 << 19) : 528'd0);
            sent <= sent + 1; c = c - 1;
            if (frames[sent][527:524] == 4'd8 && frames[sent][7:0] == 8'd1) begin img_pw <= frames[sent][34:24]; img_dw <= frames[sent][38:35]; end
            if (boot_gap_en != 0 && frames[sent][527:524] == 4'd8 && frames[sent][7:0] == 8'd4 && sent + 1 < nfr) begin
                drain_wait <= 1'b1; n_gaps <= n_gaps + 1;
            end
        end
        credits <= c;
    end
    reg b_ready_q = 0;
    always @(posedge ck_core) begin
        b_ready_q <= b_ready;
        if (b_ready && !b_ready_q) begin
            $display("BOOT_IMAGE cyc %0d target %0d epoch %0d digest %016h fault %0d", cyc_core, b_target, b_epoch, b_dig, b_fault);
            if (n_ready < n_exp && (b_target != exp_t[n_ready] || b_dig != exp_d[n_ready] || (epoch_exp >= 0 && b_epoch != 16'(epoch_exp)))) begin
                errors = errors + 1;
                $display("BOOT_MISMATCH image %0d want target %0d digest %016h", n_ready, exp_t[n_ready], exp_d[n_ready]);
            end
            if (n_ready < 32) ready_cyc[n_ready] = cyc_core;
            n_ready = n_ready + 1; t_last = cyc_core;
        end
        if (b_fault && t_bfault < 0) begin t_bfault = cyc_core; $display("BOOT_FAULT cyc %0d target %0d", cyc_core, b_target); end
        if (setup && t_setup < 0) begin t_setup = cyc_core; $display("SETUP_READY cyc %0d", cyc_core); end
    end
    // ------------------------------------------------------------------ post-boot observation (+POST=<core cycles>)
    // KV-TOK 10-24: after the boot verdict, keep running and print every change of the die's own token-start chain in
    // sys_c (non-hier partition: host boot_go / link reset / program begin -> d2d_kv fwd epoch -> dcal admission ->
    // AUTO token start; d2d abort / fault / transport fault).  Diagnostic only; no verdict.
    wire [11:0] po_sig = {dut.sys_c.i_host_boot_go_q[0], dut.sys_c.i_host_link_rst_n_q[0], dut.sys_c.i_host_program_begin_v_q[0],
                          dut.sys_c.w_d2d_kv_fwd_epoch[0], dut.sys_c.w_d2d_kv_fwd_link_rst_n[0], dut.sys_c.w_dcal_cal_ready[0],
                          dut.sys_c.w_dcal_adm_done[0], dut.sys_c.w_dcal_tok_start[0], dut.sys_c.w_dcal_running[0],
                          dut.sys_c.w_d2d_kv_epoch_abort[0], dut.sys_c.w_d2d_kv_fault[0], dut.sys_c.w_dcal_fault[0]};
    reg [11:0] po_q = 0; integer po_n = 0, ftx_n = 0;
    always @(posedge ck_core) begin
        po_q <= po_sig; if (dut.sys_c.w_d2d_kv_fdi_tx_v[0]) ftx_n <= ftx_n + 1;
        if (po_sig != po_q && po_n < 400) begin
            po_n <= po_n + 1;
            $display("POSTOBS cyc %0d boot_go %b link_rst_n %b prog_begin %b fwd_epoch %b fwd_lrst_n %b cal_ready %b adm_done %b tok_start %b running %b epoch_abort %b d2d_fault %b dcal_fault %b tf %h link_up %b token_epoch %h fdi_tx %0d",
                cyc_core, po_sig[11], po_sig[10], po_sig[9], po_sig[8], po_sig[7], po_sig[6], po_sig[5], po_sig[4], po_sig[3],
                po_sig[2], po_sig[1], po_sig[0], dut.sys_c.w_d2d_kv_transport_fault, dut.sys_c.w_d2d_kv_link_up,
                dut.sys_c.i_host_token_epoch_q, ftx_n);
        end
    end
    integer post = 0;
    // boot-path observation (hub_Wi HOST outputs at the top lanes): reset / boot_go levels to hub_C, boot_pr words
    wire [4:0] bo_sig = {dut.x_hub_Wi_o_host_boot_go_d1_hgi_WN_7[0], dut.x_hub_Wi_o_host_host_rst_n_d1_hub_Wo[0], dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0],
                         dut.x_hub_Wi_o_host_die_rst_n_hub_C[0], dut.x_hub_Wi_o_host_boot_go_hub_C[0]};
    reg [4:0] bo_q = 0; reg [142:0] bpr_q = 0; integer bpr_n = 0;
    always @(posedge ck_core) begin
        bo_q <= bo_sig; bpr_q <= dut.x_hub_Wi_o_host_boot_pr_hub_C[142:0];
        if (dut.x_hub_Wi_o_host_boot_pr_hub_C[142:0] != bpr_q) bpr_n <= bpr_n + 1;
        if (bo_sig != bo_q) $display("BOOTOBS cyc %0d boot_go_d1_hgi_WN_7 %b host_rst_n %b hbm_rst_n %b die_rst_n %b boot_go %b", cyc_core,
                                     bo_sig[4], bo_sig[3], bo_sig[2], bo_sig[1], bo_sig[0]);
    end
    // HBM boot_go fan-out and per-stack slice boot status (sdo/soo/sfo = done/ok/fault bit per slice, 32 per stack)
    wire [10:0] bg_sig = {dut.x_hub_Wi_o_host_boot_go_d2_hub_Wo[0], dut.x_hub_Ei_ft47_o_hub_Eo[0],
        dut.x_hroot_WS_ft1_o_pc_WS_7[0], dut.x_hroot_WN_ft1_o_pc_WN_7[0], dut.x_hroot_ES_ft1_o_pc_ES_7[0], dut.x_hroot_EN_ft1_o_pc_EN_7[0],
        dut.x_pc_WS_1_o_hsl_Q_N_bgo_pc_WS_0[0], dut.x_pc_WN_1_o_hsl_Q_N_bgo_pc_WN_0[0], dut.x_pc_ES_1_o_hsl_Q_N_bgo_pc_ES_0[0],
        dut.x_pc_EN_1_o_hsl_Q_N_bgo_pc_EN_0[0], 1'b0};
    reg [10:0] bg_q = 0;
`define SST(S) {8'($countones(dut.x_pc_``S``_7_o_hsl_Q_N_sdo_hroot_``S``[31:0])), 8'($countones(dut.x_pc_``S``_7_o_hsl_Q_N_soo_hroot_``S``[31:0])), 8'($countones(dut.x_pc_``S``_7_o_hsl_Q_N_sfo_hroot_``S``[31:0]))}
    wire [95:0] sst = {`SST(WS), `SST(WN), `SST(ES), `SST(EN)};
    reg [95:0] sst_q = 0;
    always @(posedge ck_core) begin
        bg_q <= bg_sig; sst_q <= sst;
        if (bg_sig != bg_q) $display("BGOBS cyc %0d d2_hub_Wo %b hub_Eo_in %b hroot_ft1 WS %b WN %b ES %b EN %b chain_end WS %b WN %b ES %b EN %b",
                                     cyc_core, bg_sig[10], bg_sig[9], bg_sig[8], bg_sig[7], bg_sig[6], bg_sig[5], bg_sig[4], bg_sig[3], bg_sig[2], bg_sig[1]);
        if (sst != sst_q) $display("SLICEBOOT cyc %0d done/ok/fault WS %0d/%0d/%0d WN %0d/%0d/%0d ES %0d/%0d/%0d EN %0d/%0d/%0d", cyc_core,
            sst[95:88], sst[87:80], sst[79:72], sst[71:64], sst[63:56], sst[55:48], sst[47:40], sst[39:32], sst[31:24], sst[23:16], sst[15:8], sst[7:0]);
    end
    // DIAGNOSTIC ONLY (+DIAG_KVPC_RST_HBM): the 32 kvpc reset spines (bound to HOST die_rst_n) follow hbm_rst_n instead.
    // The kvpc holds qkd_static_kv_pc_es_merge_b (the slice's boot-window controller face hes/her), so with die_rst_n held
    // until every slice reports boot_done the cold-boot scratch check cannot reach the controller; this tests that claim.
`ifndef KV_NATIVE_TOP   // kv43 crossing-net names (diagnostic only); the native f5 top names its spines differently
    initial if ($test$plusargs("DIAG_KVPC_RST_HBM")) begin
            $display("DIAG kvpc reset spines forced to hbm_rst_n (32 spines)");
            force dut.x_hub_Wi_rs_host_die_rst_n_65_pc_EN_0 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_69_pc_EN_1 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_70_pc_EN_2 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_71_pc_EN_3 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_72_pc_EN_4 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_73_pc_EN_5 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_89_pc_EN_6 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_93_pc_EN_7 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_66_pc_ES_0 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_74_pc_ES_1 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_75_pc_ES_2 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_76_pc_ES_3 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_77_pc_ES_4 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_78_pc_ES_5 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_90_pc_ES_6 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_94_pc_ES_7 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_67_pc_WN_0 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_79_pc_WN_1 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_80_pc_WN_2 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_81_pc_WN_3 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_82_pc_WN_4 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_83_pc_WN_5 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_91_pc_WN_6 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_95_pc_WN_7 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_68_pc_WS_0 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_84_pc_WS_1 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_85_pc_WS_2 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_86_pc_WS_3 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_87_pc_WS_4 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_88_pc_WS_5 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_92_pc_WS_6 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
            force dut.x_hub_Wi_rs_host_die_rst_n_96_pc_WS_7 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];
    end
`endif
    // partition input record (+REC_hub_Wi=<file>, partrec/gen_partrec.py) for the flat replay sub-bench
`ifndef KV_NATIVE_TOP
`include "partrec_hub_Wi.svh"
`endif
`include "kvtok2_obs.svh"
    // heartbeat (+HB=<core cycles>, default 20000): progress line + stdout flush (the log is a redirected file)
    integer hb = 20000;
    initial void'($value$plusargs("HB=%d", hb));
    always @(posedge ck_core) if (hb > 0 && cyc_core % hb == 0) begin
        $display("HB cyc %0d t %0t frames_sent %0d credits %0d images_ready %0d setup %0d boot_pr_changes %0d die_to_host %0d host_faults %b",
                 cyc_core, $time, sent, credits, n_ready, t_setup >= 0, bpr_n, rx_words, host_faults);
        $fflush;
    end
    initial begin
        integer fd, t; reg [63:0] d;
        if (!$value$plusargs("PHASE=%s", phase)) phase = "boot";
        if (!$value$plusargs("FRAMES=%s", fpath)) $fatal(1, "+FRAMES required");
        if (!$value$plusargs("MUT_FRAME=%d", mut_frame)) mut_frame = -1;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 200000;
        if (!$value$plusargs("SETUP_WAIT=%d", setup_wait)) setup_wait = 20000;
        if (!$value$plusargs("EPOCH=%d", epoch_exp)) epoch_exp = -1;
        if (!$value$plusargs("POST=%d", post)) post = 0;
        begin : farcfg integer x;
            if ($value$plusargs("FAR=%d", x)) far_en = (x != 0);
            if ($value$plusargs("EPB=%d", x)) far_epb = 5'(x);
            if ($value$plusargs("CTX=%d", x)) far_pos = 13'(x - 1);
            if ($test$plusargs("MUT_CMD_LATE")) far_m1 = 1;
            if ($value$plusargs("EP_RAW=%d", x)) far_epraw = (x != 0);
        end
        fd = $fopen(fpath, "r"); if (fd == 0) $fatal(1, "FRAMES %s", fpath);
        while (!$feof(fd) && $fscanf(fd, "%h\n", frames[nfr]) == 1) nfr = nfr + 1;
        $fclose(fd);
        if ($value$plusargs("EXPECT=%s", epath)) begin
            fd = $fopen(epath, "r");
            while ($fscanf(fd, "%d %h\n", t, d) == 2) begin exp_t[n_exp] = 4'(t); exp_d[n_exp] = d; n_exp = n_exp + 1; end
            $fclose(fd);
        end
        $display("KVSLICE_CFG phase %s frames %0d expect %0d mut_frame %0d boot_gap %0d boot_slack %0d top %m", phase, nfr, n_exp, mut_frame, boot_gap_en, boot_slack);
        repeat (20) @(posedge ck_ref); por_n = 1;
        repeat (4) @(posedge ck_ref); rst_n = 1;
        // board link up only once the die's link end can receive: its HOST is out of reset (host_rst_n at the hub) and
        // both SerDes halves report tx_up, + 64 host cycles for the 30-cycle lanes.  Before this the board adapter's
        // idle flits are lost and its FDI sequence is ahead of the die's (die adapter f_seq on the first flit).
        wait (bo_sig[3] && dut.sys_SW.u_core.tx_up && dut.sys_SE.u_core.tx_up);
        repeat (64) @(posedge ck_host); host_up = 1;
        $display("KVSLICE host board link up at core cycle %0d", cyc_core);
        while (cyc_core < maxcyc && !(n_ready >= n_exp && n_exp > 0 && (t_setup >= 0 || cyc_core > t_last + setup_wait)) && t_bfault < 0)
            @(posedge ck_core);
        repeat (2000) @(posedge ck_core);
        $display("KVSLICE_BOOT %s frames_sent %0d/%0d images_ready %0d/%0d errors %0d boot_fault %0d setup_ready %0d (cyc %0d) cf_fault %0d pll_locked %0d host_faults %b die_to_host_words %0d last_ready_cyc %0d cyc %0d",
            (errors == 0 && n_ready == n_exp && n_exp > 0 && t_bfault < 0 && t_setup >= 0 && !cf_fault) ? "PASS" : "FAIL",
            sent, nfr, n_ready, n_exp, errors, (t_bfault >= 0), (t_setup >= 0), t_setup, cf_fault, locked, host_faults, rx_words,
            t_last, cyc_core);
        if (post > 0) begin
            repeat (post) @(posedge ck_core);
            $display("KVSLICE_POST cyc %0d events %0d fdi_tx_words %0d", cyc_core, po_n, ftx_n);
            if (far_en) u_far.report();
        end
        $finish;
    end
endmodule
