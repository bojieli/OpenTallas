// Opt-in native bootstrap vehicle: qualified B33 sender cadence and independent mission START.
// Requires a matching HOST ABI and current bound/image cohort; not a whole-token qualification.
`timescale 1ns/1fs
// TOKj-KV 10-23: KV DIE-SLICE VEHICLE on the BOUND KV die top (qwen_kvsys_bound_top, tools/die_plan/bind.py output).
// The DUT is the whole bound top byte-for-byte (all 160 partitions, every landed lane / pad / R8 delay as bound).  Only
// the off-die boundaries are bench models (owner 10-14):
//   HBM PHY slices  qkd_hbm3e_phy_pc4      -> KV-P7 bench model (qkd_hbm3e_phy_pc4_bench.sv, RL 23, preload)
//   host SerDes     ot_qfd_serdes_112g_x6_phy x2 -> kvs_link_phy_models.sv; the far end = the HOST BOARD PORT, built from the
//                   real host link adapter + CDC RTL (qkd_host_board_port_fixture: qfd_link_adp512_split + qkd_host_phy_cdc5)
//   UCIe d2d PHY    ot_qkvd_ucie_x64_phy   -> kvs_link_phy_models.sv; far end = the compute-die driver (phase TOKEN)
// Clocks: the top clock inputs at the as-built PLL periods (core 1.2 GHz, phy 0.959; b23h binds: the HBM PHY slices,
// HOST and ingest run on the die clock clk_core); the host board 1.0 GHz; pad_refclk 100 MHz.  The die's own analog PLL model (hub_C u_pll) produces pll_locked.
// Phase BOOT (+PHASE=boot): replay the boot bundle (+FRAMES=<hex, one 528-b class-8 frame per line>) through the host
// board port with its credits (the die's host path is real RTL end to end); watch the host root's boot_image_* and the
// kvs_ctl dispatcher; PASS = every image of +EXPECT=<file: "target digest" per line, bundle order> reported ready with the
// expected target/digest/epoch, no boot fault, kvs_ctl setup_ready.  Mutant +MUT_FRAME=<n> flips data bit 19 of frame n
// (one program word) -> the image digest must mismatch -> FAIL required.
module tb_kvslice;
    // ------------------------------------------------------------------ clocks / reset
    reg ck_core = 0, ck_host = 0, ck_phy = 0, ck_ref = 0;
    always #0.416500 ck_core = ~ck_core;
    always #0.500    ck_host = ~ck_host;     // the host BOARD's own clock (off-die host port fixture)
    always #0.521500 ck_phy  = ~ck_phy;
    always #5.0      ck_ref  = ~ck_ref;
    reg por_n = 0, rst_n = 0;
    // Optional physical mission START after native bootstrap setup; reset and START are independent inputs.
    reg mission_start = 0;
    integer start_after_setup = 0, mission_start_delay = 130, mission_start_cycle = -1;
    reg [2:0] die_id = 3'd1;
    // ------------------------------------------------------------------ link far ends (read by the PHY models)
    wire         h2d_v;
    wire [1042:0] h2d_flit;
    wire         c2k_v;
    wire [582:0] c2k_flit;
    // TOK-KVE 10-26: the bound top's pad set (b23h strict bind): one die clock clk_core (+ the SerDes PHY clock clk_clk_phy;
    // the HBM PHY slices and the HOST run on clk_core), pad_por_n = the reset root (asynchronous assert), start = the START
    // broadcast pad (decision 13c: every region releases on the later of its wavefront reset and START), and the UCIe
    // line-side bumps (sys_c_link_* out = KV TX at the bump, sys_c_far_* in = the compute die's TX, c2k_*).
    wire         kv_link_v;
    wire [582:0] kv_link_flit;
    qwen_kvsys_bound_top dut (
        .pad_por_n(por_n), .start(start_after_setup ? mission_start : rst_n), .clk_clk_phy(ck_phy), .clk_core(ck_core),
        .pad_die_id(die_id), .pad_refclk(ck_ref),
        .sys_c_link_v(kv_link_v), .sys_c_link_flit(kv_link_flit), .sys_c_far_v(c2k_v), .sys_c_far_flit(c2k_flit));
    // ------------------------------------------------------------------ compute-die far end on the UCIe link (+FAR=1)
    // KV-TOK 10-24 token phase: kvs_compute_end.sv (the compute die's real d2d master + calendar sequencer + record codec
    // + KVN transport on the pair image of the KV boot image; see that file).  +FAR=0 (default): the link is silent.
    // +EP_RAW=1 (DIAGNOSTIC): the compute pin follows the d2d_kv fwd_epoch / fwd_link_rst_n OUTPUT (before the 5 bound relay
    // stages to the bump pad u_fwb_*) -- isolates the epoch-anchor skew question (KV dcal EP_SKEW 3 vs pad + package).
    reg far_en = 0, far_m1 = 0, far_epraw = 0; reg [4:0] far_epb = 0; reg [12:0] far_pos = 13'd255;
    kvs_compute_end u_far (.ck(ck_core), .rst_n(rst_n), .en(far_en), .epb(far_epb), .epoch(dut.sys_c.i_host_token_epoch_q),
        .pos(far_pos), .kv_tx_v(kv_link_v), .kv_tx_flit(kv_link_flit),
        .kv_fwd_ep_pad(far_epraw ? dut.sys_c.w_d2d_kv_fwd_epoch[0] : dut.sys_c.d5_d2d_kv_fwd_epoch[0]),
        .kv_fwd_lrst_pad(far_epraw ? dut.sys_c.w_d2d_kv_fwd_link_rst_n[0] : dut.sys_c.d5_d2d_kv_fwd_link_rst_n[0]),
        .mut_cmd_late(far_m1), .c2k_v(c2k_v), .c2k_flit(c2k_flit));
    // die host TX (two halves) -> host board port RX.  Each half is the as-built ot_qfd_serdes_112g_x6_phy_c45 (real FDI
    // CDC u_fdi_cdc, core -> clk_clk_phy) around the PHY u_phy (= the bench model): the line side is the PHY's tx word.
    wire d2h_v;
    wire [1042:0] d2h_flit;
    ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_board_half_join (
        .clk(ck_phy), .rst_n(por_n),
        .a_v(dut.sys_SW.u_core.u_phy.tx_v), .a_d(dut.sys_SW.u_core.u_phy.tx_flit),
        .b_v(dut.sys_SE.u_core.u_phy.tx_v), .b_d(dut.sys_SE.u_core.u_phy.tx_flit),
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
    localparam integer BOOT_REPLAY_SLACK = 16, HOST_LINK_LAT = 160;  // host board send -> die loader: measured 122 core cycles (B33 first BEGIN sent cyc 531, at loader 653) + margin
    integer hold_core = 0, img_pw = 0, img_dw = 0; reg auth_pending = 0;
    // TOK-QK 10-26 run6: static host frame issue interval.  The host->loader path delivers one 528-b frame per 2.29 ns
    // (run5 LDOBS: 1024 frames BEGIN->SEAL 2346 ns, 471 frames 1081 ns), slower than the credit loop of the board IBUF,
    // so a long image builds a queue behind the credit point and its AUTH reaches the loader late (run5 t6: +266 core
    // cycles), shortening the AUTH->next-BEGIN gap below the pw+dw+16 replay.  Issuing at most one frame every
    // HOST_FRAME_GAP host cycles (3 ns >= 2.29 ns) keeps the path queue-free, so the declared HOST_LINK_LAT holds.
    localparam integer HOST_FRAME_GAP = 3;
    // KV-BOOT-SETUP 10-26 host boot ordering: the die accepts boot images only after the HOST sequencer released die reset
    // (die_rst_n: cold-boot HBM check of all 128 slices passed). The board issues its FIRST frame DIE_READY_CORE core cycles
    // after link up: a DECLARED static bound (measured link up 531 -> die_rst_n 1093 = 562 cycles, CHECKED, boot fix B
    // vehicle); no die status feedback. Fail-closed: any boot_pr word while die_rst_n is 0 is an error (lost words).
    localparam integer DIE_READY_CORE = 1024;
    integer next_issue_host = 0;
    integer nfr = 0, mut_frame = -1, cyc_host = 0, sent = 0, credits = 4, rx_words = 0;
    integer n_ready = 0, n_exp = 0, errors = 0, ready_cyc [0:31], cyc_core = 0, t_setup = -1, t_bfault = -1, t_last = 0;
    reg [3:0] exp_t [0:31]; reg [63:0] exp_d [0:31];
    string fpath, epath, phase;
    integer maxcyc = 200000, setup_wait = 20000, epoch_exp = -1;
    always @(posedge ck_core) cyc_core <= cyc_core + 1;
    always @(negedge ck_core) if (start_after_setup && t_setup >= 0 && !mission_start &&
                                cyc_core >= t_setup + mission_start_delay) begin
        mission_start = 1; mission_start_cycle = cyc_core;
        $display("KVSLICE_START cycle %0d setup_cycle %0d delay %0d", mission_start_cycle, t_setup, mission_start_delay);
    end
    // DIE-KV-49-FN 10-30 first token's HOST command (stimulus only).  This die is a TP8 peer (pad_die_id 1, STRAPPED
    // host root): its host token command is the package controller's CTRL START frame, not a HOST BAR write (a class-0
    // frame at a strapped peer is a fault).  Format = qkd_host_ctrl_token_service_packet_collected_mu peer token frame:
    // class 1; opcode 22 / version 2; src die 0; target 1<<die; sequence 0 (first frame from die 0); hc[38:0] =
    // {start 1, gen2, token18, pos18} at 86:48 (pos[17:16] = user, pos[15:13] = 0); token epoch at 245:230 with
    // [231:230] = user, epoch valid 246; service epoch 262:247.  Without it the die's native token endpoint never holds a
    // request, so its CONTEXT producer is empty when D2D_FIRST_TOKEN's calendar slot fires (d2d fault 0x80, DIE-KV-48-FN).
    // Sent once, after the die's ready STATUS (KV-FN-3, below) and after every boot frame, through the same credited
    // board port.  Default on in the token phase (+START_AFTER_SETUP +FAR=1); +HOST_TOKEN_OFF = control.
    // +HOST_TOKEN_TOK (1) +HOST_TOKEN_POS (CTX-1) +HOST_TOKEN_GEN (1) +HOST_TOKEN_EPOCH (4) +HOST_TOKEN_SEPOCH (0).
    // KV-FN-3 10-31 START only after the die reports ready (replaces the fixed +64 delay, which raced the die: the peer
    // token service is fail-closed, a START whose peer_service_fresh is false -- local_service_ready = guard ready &&
    // program_ready, and program_ready needs the program commit -- sets a sticky fault and never latches token_epoch).
    // Protocol form: the peer advertises its readiness to the package controller in its CTRL STATUS frame (opcode 0x21,
    // version 2, src = role, ready bit 153, service epoch 169:154; sent on every ready/epoch change).  The board decodes
    // every die->host word and queues START once a STATUS with ready 1 and service epoch == +HOST_TOKEN_SEPOCH arrived,
    // + HOST_TOKEN_READY_MARGIN (32) core cycles, and not before HOST_TOKEN_DELAY (default 0 here) after mission START.
    // +HOST_TOKEN_NOWAIT = the old fixed-delay form (control; default delay 64 then).
    integer host_tok_delay = -1, host_tok_frame = -1, host_tok_tok = 1, host_tok_pos = -1, host_tok_gen = 1,
            host_tok_epoch = 4, host_tok_sepoch = 0, host_tok_margin = 32, die_ready_cyc = -1, n_d2h = 0;
    reg host_tok_on = 0, host_tok_sent_seen = 0, host_tok_wait = 1;
    always @(posedge ck_host) if (hc_rx_v) begin
        if (n_d2h < 200)
            $display("D2H cyc %0d n %0d class %0d op %02h ver %0d src %0d seq %0d ready %0d sepoch %04h", cyc_core, n_d2h,
                     hc_rx_d[527:524], hc_rx_d[7:0], hc_rx_d[15:8], hc_rx_d[18:16], hc_rx_d[47:32], hc_rx_d[153], hc_rx_d[169:154]);
        n_d2h = n_d2h + 1;
        if (hc_rx_d[7:0] == 8'h21 && hc_rx_d[15:8] == 8'd2) begin
            if (hc_rx_d[153] && hc_rx_d[169:154] == 16'(host_tok_sepoch)) begin
                if (die_ready_cyc < 0) begin die_ready_cyc = cyc_core; $display("DIE_SVC_READY cyc %0d", cyc_core); end
            end else die_ready_cyc = -1;
        end
    end
    always @(negedge ck_host) begin
        if (host_tok_on && host_tok_frame < 0 && mission_start_cycle >= 0 && cyc_core >= mission_start_cycle + host_tok_delay &&
            (!host_tok_wait || (die_ready_cyc >= 0 && cyc_core >= die_ready_cyc + host_tok_margin)) &&
            sent == nfr && nfr < 16384) begin : host_tok
            reg [527:0] f; reg [38:0] hc;
            hc = {1'b1, 2'(host_tok_gen), 18'(host_tok_tok), 18'(host_tok_pos)};
            f = '0; f[7:0] = 8'h22; f[15:8] = 8'd2; f[18:16] = 3'd0; f[31:24] = 8'd1 << die_id; f[47:32] = 16'd0;
            f[86:48] = hc; f[245:230] = 16'(host_tok_epoch); f[246] = 1'b1; f[262:247] = 16'(host_tok_sepoch);
            f[527:524] = 4'd1;
            frames[nfr] = f; host_tok_frame = nfr; nfr = nfr + 1;
            $display("HOSTTOK_QUEUED cyc %0d frame %0d mission_start %0d die_ready %0d hc %010h epoch %04h", cyc_core, host_tok_frame,
                     mission_start_cycle, die_ready_cyc, hc, 16'(host_tok_epoch));
        end
        if (host_tok_frame >= 0 && !host_tok_sent_seen && sent > host_tok_frame) begin
            host_tok_sent_seen = 1; $display("HOSTTOK_SENT cyc %0d", cyc_core);
        end
    end
    always @(posedge ck_host) begin
        cyc_host <= cyc_host + 1;
        hc_rx_cr <= hc_rx_v;                       // host consumes every die->host word at once (returns its credit)
        if (hc_rx_v) rx_words <= rx_words + 1;
    end
    // credit-based host sender (IBUF 4 of the host CDC write face)
    always @(posedge ck_host) if (host_up) begin
        automatic integer c = credits + (hc_tx_cr ? 1 : 0);
        hc_tx_v <= 1'b0;
        if (sent < nfr && c > 0 && !auth_pending && cyc_core >= hold_core && cyc_host >= next_issue_host) begin
            next_issue_host = cyc_host + HOST_FRAME_GAP;
            hc_tx_v <= 1'b1; hc_tx_d <= frames[sent] ^ ((sent == mut_frame) ? (528'd1 << 19) : 528'd0);
            sent <= sent + 1; c = c - 1;
            // KV-TOK 10-26 host boot ordering contract (external boot ABI, qkd_host_program_loader_target): after an
            // image's AUTH the die replays its pw program + dw descriptor writes on fixed consecutive loader (core) cycles
            // and refuses a BEGIN during the replay (sticky fault).  The host therefore issues the next image only after
            // the fixed replay time of the image it just authorised (pw + dw + REPLAY_W/READY edges + transport slack):
            // a static gap from the image's own BEGIN fields, counted from the AUTH's acceptance at the die's host ingress
            // (all IBUF credits of the board port returned = every sent frame, AUTH included, consumed), so a queue in
            // the link cannot shorten it; no die ready/status feedback is used.
            if (frames[sent][7:0] == 8'd1) begin img_pw = frames[sent][34:24]; img_dw = frames[sent][38:35]; end
            if (frames[sent][7:0] == 8'd4) hold_core = cyc_core + HOST_LINK_LAT + img_pw + img_dw + BOOT_REPLAY_SLACK;
        end
        if (auth_pending && c == 4) begin   // never the AUTH send edge itself (c <= 3 there)
            auth_pending = 0;
        end
        credits <= c;
    end
    reg [3:0] host_adapter_fault_q = 0;
    wire [3:0] host_adapter_fault_now = {u_host.u_adapter.g_slice[0].u_slice.u_body.f_die_ovr,
       u_host.u_adapter.g_slice[0].u_slice.u_body.f_link_ovr,
       u_host.u_adapter.g_slice[0].u_slice.u_body.f_seq,
       u_host.u_adapter.g_slice[0].u_slice.u_body.f_cred};
    always @(posedge ck_phy) begin
      host_adapter_fault_q <= host_adapter_fault_now;
      if (host_adapter_fault_now != host_adapter_fault_q)
        $display("HOST_ADAPTER_FAULT cyc %0d die_ovr/link_ovr/seq/cred %b rxseq %0d gotseq %0d rxv %b", cyc_core,
          host_adapter_fault_now, u_host.u_adapter.g_slice[0].u_slice.u_body.rx_seq,
          d2h_q[3][7:0], d2h_vq[3]);
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
    reg [4:0] bo_q = 0; reg [142:0] bpr_q = 0; integer bpr_n = 0, n_pre_rst = 0;
    always @(posedge ck_core) begin
        bo_q <= bo_sig; bpr_q <= dut.x_hub_Wi_o_host_boot_pr_hub_C[142:0];
        if (dut.x_hub_Wi_o_host_boot_pr_hub_C[142:0] != bpr_q) bpr_n <= bpr_n + 1;
        if (dut.x_hub_Wi_o_host_boot_pr_hub_C[74] && !bo_sig[1]) begin
            if (n_pre_rst == 0) $display("KVSLICE_FAIL boot_pr word before die reset release cyc %0d", cyc_core);
            n_pre_rst = n_pre_rst + 1; errors = errors + 1;
        end
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
    // The force list is GENERATED by build.sh from the bound top (every "reset spine" net x_hub_Wi_rs_host_die_rst_n_<n>_pc_<Q>_<k>),
    // so it follows the bind's net numbering; the plusarg is off by default (nominal and mutant runs never force).
    initial if ($test$plusargs("DIAG_KVPC_RST_HBM")) begin
`include "kvpc_rst_diag.svh"
    end
    // partition input record (+REC_hub_Wi=<file>, partrec/gen_partrec.py; build.sh regenerates it from the bound top)
`include "partrec_hub_Wi.svh"
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
        start_after_setup = $test$plusargs("START_AFTER_SETUP");
        void'($value$plusargs("MISSION_START_DELAY=%d", mission_start_delay));
        if (mission_start_delay < 1) $fatal(1, "MISSION_START_DELAY must be positive");
        begin : farcfg integer x;
            if ($value$plusargs("FAR=%d", x)) far_en = (x != 0);
            if ($value$plusargs("EPB=%d", x)) far_epb = 5'(x);
            if ($value$plusargs("CTX=%d", x)) far_pos = 13'(x - 1);
            if ($test$plusargs("MUT_CMD_LATE")) far_m1 = 1;
            if ($value$plusargs("EP_RAW=%d", x)) far_epraw = (x != 0);
        end
        host_tok_on = start_after_setup && far_en && !$test$plusargs("HOST_TOKEN_OFF");
        host_tok_wait = !$test$plusargs("HOST_TOKEN_NOWAIT");
        void'($value$plusargs("HOST_TOKEN_DELAY=%d", host_tok_delay));
        if (host_tok_delay < 0) host_tok_delay = host_tok_wait ? 0 : 64;
        void'($value$plusargs("HOST_TOKEN_READY_MARGIN=%d", host_tok_margin));
        void'($value$plusargs("HOST_TOKEN_TOK=%d", host_tok_tok));
        void'($value$plusargs("HOST_TOKEN_GEN=%d", host_tok_gen));
        void'($value$plusargs("HOST_TOKEN_EPOCH=%d", host_tok_epoch));
        void'($value$plusargs("HOST_TOKEN_SEPOCH=%d", host_tok_sepoch));
        if (!$value$plusargs("HOST_TOKEN_POS=%d", host_tok_pos)) host_tok_pos = int'(far_pos);
        if (host_tok_on && (host_tok_epoch % 4 != (host_tok_pos >> 16) % 4 || ((host_tok_pos >> 13) & 7) != 0 || host_tok_tok >= 151936))
            $fatal(1, "HOST_TOKEN fields violate the peer token frame rules (epoch[1:0] = pos[17:16], pos[15:13] = 0, token < 151936)");
        $display("HOSTTOK_WAIT ready_wait %0d margin %0d (die CTRL STATUS 0x21 ready=1)", host_tok_wait, host_tok_margin);
        $display("HOSTTOK_CFG on %0d delay %0d tok %0d pos %0d gen %0d epoch %0d sepoch %0d", host_tok_on, host_tok_delay,
                 host_tok_tok, host_tok_pos, host_tok_gen, host_tok_epoch, host_tok_sepoch);
        fd = $fopen(fpath, "r"); if (fd == 0) $fatal(1, "FRAMES %s", fpath);
        while (!$feof(fd) && $fscanf(fd, "%h\n", frames[nfr]) == 1) nfr = nfr + 1;
        $fclose(fd);
        if ($value$plusargs("EXPECT=%s", epath)) begin
            fd = $fopen(epath, "r");
            while ($fscanf(fd, "%d %h\n", t, d) == 2) begin exp_t[n_exp] = 4'(t); exp_d[n_exp] = d; n_exp = n_exp + 1; end
            $fclose(fd);
        end
        $display("KVSLICE_CFG phase %s frames %0d expect %0d mut_frame %0d top %m", phase, nfr, n_exp, mut_frame);
        repeat (20) @(posedge ck_ref); por_n = 1;
        repeat (4) @(posedge ck_ref); rst_n = 1;
        // board link up only once the die's link end can receive: its HOST is out of reset (host_rst_n at the hub) and
        // both SerDes halves report tx_up, + 64 host cycles for the 30-cycle lanes.  Before this the board adapter's
        // idle flits are lost and its FDI sequence is ahead of the die's (die adapter f_seq on the first flit).
        while (!(bo_sig[3] && dut.sys_SW.u_core.tx_up && dut.sys_SE.u_core.tx_up) && cyc_core < maxcyc)
            @(posedge ck_core);
        if (!(bo_sig[3] && dut.sys_SW.u_core.tx_up && dut.sys_SE.u_core.tx_up))
            $fatal(1, "KVSLICE_BOOT FAIL link wait exceeded MAXCYC");
        repeat (64) @(posedge ck_host); hold_core = cyc_core + DIE_READY_CORE; host_up = 1;
        $display("KVSLICE host board link up at core cycle %0d", cyc_core);
        while (cyc_core < maxcyc && !(n_ready >= n_exp && n_exp > 0 && (t_setup >= 0 || cyc_core > t_last + setup_wait)) && t_bfault < 0)
            @(posedge ck_core);
        repeat (2000) @(posedge ck_core);
        $display("KVSLICE_BOOT %s frames_sent %0d/%0d images_ready %0d/%0d errors %0d boot_fault %0d setup_ready %0d (cyc %0d) cf_fault %0d pll_locked %0d host_faults %b dcal_fault %b die_to_host_words %0d last_ready_cyc %0d cyc %0d",
            (errors == 0 && n_ready == n_exp && n_exp > 0 && t_bfault < 0 && t_setup >= 0 && !cf_fault && !dut.sys_c.w_dcal_fault[0]) ? "PASS" : "FAIL",
            sent, nfr, n_ready, n_exp, errors, (t_bfault >= 0), (t_setup >= 0), t_setup, cf_fault, locked, host_faults, dut.sys_c.w_dcal_fault[0], rx_words,
            t_last, cyc_core);
        if (!(errors == 0 && n_ready == n_exp && n_exp > 0 && t_bfault < 0 && t_setup >= 0 && !cf_fault && !dut.sys_c.w_dcal_fault[0]))
            $fatal(1, "KVSLICE_BOOT verdict FAIL: native bench exits nonzero");
        if (post > 0) begin
            repeat (post) @(posedge ck_core);
            $display("KVSLICE_POST cyc %0d events %0d fdi_tx_words %0d", cyc_core, po_n, ftx_n);
            if (far_en) u_far.report();
        end
        $display("KVSLICE_FINALCAL dcal_fault %b cyc %0d", dut.sys_c.w_dcal_fault[0], cyc_core);
        if (dut.sys_c.w_dcal_fault[0]) $fatal(1, "KVSLICE_FINALCAL FAIL: calendar fault after POST");
        $finish;
    end
endmodule
