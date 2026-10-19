// LAYERBENCH-QWEN G-K1: the KV die PROGRAMME LOAD = the full authenticated HOST boot through the KV GEN netlist, on the
// boot vehicle qwk_slice_boot (tools/qwen_layerbench/slice_cut.py: qkd_kvs_ctl + 4 qkd_kvs_hroot + 32 qkd_kvs_grp/_grp_h
// (the 160 qkd_static_kv_boot_cdc sinks: 4 PC controller CDCs + 1 front CDC per group) + 128 qkd_kvs_pc/_pc_h (the
// controller-calendar consumers) + every die relay / reset region between them, verbatim from the die netlist).
// The HOST root is the slice-edge neighbour: the bench instantiates the REAL HOST image loader of the die's HOST root
// (qkd_host_program_loader_target, the qkd_host_root_admission u_program leaf) and drives the slice edge exactly as the
// root does: boot_pr = raw_pr, boot_image_target = replay_target, boot_image_ready = replay_done && !fault && !begin_image,
// boot_image_fault / epoch / digest = the loader's.  Per image: BEGIN (target, epoch 0x0b0b, PW/DW counts), the words on
// consecutive edges, SEAL, AUTH (the trusted digest = digests.memh, equal to the compiler's boot_bundle.json), then the
// loader replays the words on fixed consecutive edges (no ready / credit) and raises program_ready.
// Order (qkd_static_kv_boot_dispatch DIECFG=1 LINKCFG=1 ESCFG=1 DIECAP=1): target 10 (die cfg) after the first, unaligned
// POR + functional release; then the functional resets (die + HBM; NOT the POR pad, the die cfg keeps its words) are
// re-asserted and released; then targets 1..9, 11, 12, 13, then the ISA target 0.
// Images: +KVIMG=<dir> (tools/qwen_layerbench/kv_boot_images.py).  +KVB_T10FIX = the ALTERNATE HOST loader copy
// qkd_host_program_loader_target_alt (run_kv_boot.sh KVB_ALT): 77 = DIAGNOSTIC target_words(10) = 77 on a pre-F-K1 loader
// (76 = 32 + 43 + 1; the dispatcher's DIECAP=1 image is 32 + 43 + 2); 76 = the OLD pre-F-K1 loader as a MUTANT of the
// fixed as-built loader (QW-KVATTN 10-18, KV-HROOT 81633db23).  +KVB_ALT_DESC=<s> names it in the log.
// Mutants (+KVB_MUT=n, checker sensitivity, run on the DIAGNOSTIC loader): 1 = one target-7 controller word corrupted at
// the slice edge (bit 0 of word 100, after the loader's digest); 2 = wrong target order (target 2 before target 1);
// 3 = one layer-programme word (target 1 word 1, kgo of stage 1) corrupted at the slice edge.
// Checks: loader / dispatcher fault 0; every image's words reach the dispatcher pins bit-exact and in order; every image
// installed (installed 9'h1ff, link cfg, es 12 / 13, ISA seen); all 160 CDC sinks applied, each sink's word stream = one
// PC controller image (targets 6..9, 32 words) or one group's front image (target 5, 6 words), as a permutation of the
// compiled images; local_configured 3'b111; die cfg sealed with the image's ECTL cfg and capability; setup_ready rises
// (cycle printed, compared across the two random initial states by run_kv_boot.sh); u_lprg holds target 1 bit-exact
// (36 x 9 roots, LP_DIGEST, epoch).  Every event cycle is printed as KVB_EVT.
    localparam integer KVB_N = 1032;
    reg [63:0] kvb_img [0:14*KVB_N-1];
    reg [63:0] kvb_tmp [0:KVB_N-1];
    reg [63:0] kvb_dig [0:13];
    integer kvb_wc [0:13];
    string kvb_dir, kvb_alt;
    integer kvb_mut = 0, kvb_fix = 0, kvb_i, kvb_t, kvb_a;
    // ---- the HOST root's image loader (real RTL) and its DIAGNOSTIC copy ----
    reg h_begin = 0, h_wv = 0, h_desc = 0, h_seal = 0, h_auth = 0;
    reg [3:0] h_t = 0; reg [10:0] h_pw = 0; reg [3:0] h_dw = 0; reg [9:0] h_addr = 0; reg [63:0] h_data = 0, h_ad = 0;
    wire [142:0] h_pr0, h_pr1; wire [3:0] h_rt0, h_rt1; wire h_rdy0, h_rdy1, h_f0, h_f1, h_afv0, h_afv1;
    wire [63:0] h_dg0, h_dg1, h_af0, h_af1; wire [15:0] h_ep0, h_ep1;
    qkd_host_program_loader_target u_host (.ck(ck), .rst_n(por_n), .begin_image(h_begin), .image_epoch(16'h0b0b),
        .image_target(h_t), .auth_target(h_t), .replay_target(h_rt0), .pw_count(h_pw), .dw_count(h_dw), .word_v(h_wv),
        .word_desc(h_desc), .word_addr(h_addr), .word_data(h_data), .seal(h_seal), .auth_v(h_auth), .auth_epoch(16'h0b0b),
        .auth_digest(h_ad), .execution_active(1'b0), .pr(h_pr0), .program_ready(h_rdy0), .fault(h_f0), .digest(h_dg0),
        .program_epoch(h_ep0), .authorized_footer_valid(h_afv0), .authorized_footer(h_af0));
    qkd_host_program_loader_target_alt u_host_t10fix (.ck(ck), .rst_n(por_n), .begin_image(h_begin), .image_epoch(16'h0b0b),
        .image_target(h_t), .auth_target(h_t), .replay_target(h_rt1), .pw_count(h_pw), .dw_count(h_dw), .word_v(h_wv),
        .word_desc(h_desc), .word_addr(h_addr), .word_data(h_data), .seal(h_seal), .auth_v(h_auth), .auth_epoch(16'h0b0b),
        .auth_digest(h_ad), .execution_active(1'b0), .pr(h_pr1), .program_ready(h_rdy1), .fault(h_f1), .digest(h_dg1),
        .program_epoch(h_ep1), .authorized_footer_valid(h_afv1), .authorized_footer(h_af1));
    wire [142:0] h_pr = kvb_fix ? h_pr1 : h_pr0; wire [3:0] h_rt = kvb_fix ? h_rt1 : h_rt0;
    wire h_rdy = kvb_fix ? h_rdy1 : h_rdy0, h_f = kvb_fix ? h_f1 : h_f0;
    wire [63:0] h_dg = kvb_fix ? h_dg1 : h_dg0; wire [15:0] h_ep = kvb_fix ? h_ep1 : h_ep0;
    // the HOST root's boot outputs (qkd_host_root_admission assigns) at the slice edge; mutants 1 / 3 corrupt one word here
    reg [142:0] h_prm;
    always @* begin
        h_prm = h_pr;
        if (kvb_mut == 1 && h_pr[74] && h_rt == 4'd7 && h_pr[73:64] == 10'd100) h_prm[0] = ~h_pr[0];
        if (kvb_mut == 3 && h_pr[74] && h_rt == 4'd1 && h_pr[73:64] == 10'd1) h_prm[0] = ~h_pr[0];
        drv_i_n_ks_host_boot_pr = h_prm; drv_i_n_ks_host_boot_image_target = h_rt;
        drv_i_n_ks_host_boot_image_ready = h_rdy && !h_f && !h_begin; drv_i_n_ks_host_boot_image_fault = h_f;
        drv_i_n_ks_host_boot_image_epoch = h_ep; drv_i_n_ks_host_boot_image_digest = h_dg;
    end
    // POR pad: released with the first (unaligned) release, never re-asserted (the functional re-reset leaves it high)
    reg por_hold = 0; always @* por_n = rst_n | por_hold; always @(posedge rst_n) por_hold <= 1;
    // ---- images ----
    initial begin
        kvb_wc[0] = 1032; kvb_wc[1] = 327; kvb_wc[2] = 181; kvb_wc[3] = 4; kvb_wc[4] = 192; kvb_wc[5] = 192;
        for (kvb_t = 6; kvb_t <= 9; kvb_t = kvb_t + 1) kvb_wc[kvb_t] = 1024;
        kvb_wc[10] = 77; kvb_wc[11] = 66; kvb_wc[12] = 1024; kvb_wc[13] = 8;
        if (!$value$plusargs("KVIMG=%s", kvb_dir)) kvb_dir = "img";
        if (!$value$plusargs("KVB_MUT=%d", kvb_mut)) kvb_mut = 0;
        kvb_fix = $test$plusargs("KVB_T10FIX") ? 1 : 0;
        if (!$value$plusargs("KVB_ALT_DESC=%s", kvb_alt)) kvb_alt = "DIAGNOSTIC t10w77 copy";
        $readmemh({kvb_dir, "/digests.memh"}, kvb_dig);
        for (kvb_t = 0; kvb_t <= 13; kvb_t = kvb_t + 1) begin
            for (kvb_a = 0; kvb_a < KVB_N; kvb_a = kvb_a + 1) kvb_tmp[kvb_a] = 64'hdeadbeefdeadbeef;
            $readmemh($sformatf("%s/target%0d.hex", kvb_dir, kvb_t), kvb_tmp);
            if (kvb_tmp[kvb_wc[kvb_t] - 1] === 64'hdeadbeefdeadbeef || (kvb_wc[kvb_t] < KVB_N && kvb_tmp[kvb_wc[kvb_t]] !== 64'hdeadbeefdeadbeef))
                smoke_err("image file word count differs from the dispatcher ABI");
            for (kvb_a = 0; kvb_a < KVB_N; kvb_a = kvb_a + 1) kvb_img[kvb_t * KVB_N + kvb_a] = kvb_tmp[kvb_a];
        end
        $display("KVB_INFO images %0s mut %0d host_loader %0s", kvb_dir, kvb_mut,
                 kvb_fix ? kvb_alt : "AS-BUILT qkd_host_program_loader_target");
    end
    // ---- dispatcher pins: every word bit-exact, in order, per target ----
    integer kvb_seen [0:13]; integer kvb_bad = 0, kvb_pin_first = -1, kvb_host_first = -1, kvb_ff = 0, kvb_ff_said = 0;
    integer kvb_ready_cyc [0:13]; reg kvb_rdy_q = 0; integer kvb_setup_cyc = -1, kvb_t0_begin = -1, kvb_rel2 = -1;
    initial for (kvb_t = 0; kvb_t <= 13; kvb_t = kvb_t + 1) begin kvb_seen[kvb_t] = 0; kvb_ready_cyc[kvb_t] = -1; end
    wire [142:0] kvb_ppr = dut.kvs_ctl.u_boot.boot_pr; wire [3:0] kvb_pt = dut.kvs_ctl.u_boot.boot_image_target;
    always @(posedge ck) if (rst_n) begin
        if (h_pr[74] && kvb_host_first < 0) kvb_host_first = cyc;
        if (kvb_ppr[74]) begin
            if (kvb_pin_first < 0) kvb_pin_first = cyc;
            if (kvb_ppr[73:64] != kvb_seen[kvb_pt][9:0] || kvb_ppr[63:0] !== kvb_img[kvb_pt * KVB_N + kvb_ppr[73:64]]) begin
                if (kvb_bad < 4) $display("KVB_ERR @%0d word at the dispatcher pins: target %0d addr %0d (expected %0d) data %h (image %h)",
                    cyc, kvb_pt, kvb_ppr[73:64], kvb_seen[kvb_pt], kvb_ppr[63:0], kvb_img[kvb_pt * KVB_N + kvb_ppr[73:64]]);
                kvb_bad = kvb_bad + 1;
            end
            kvb_seen[kvb_pt] = kvb_seen[kvb_pt] + 1;
        end
        if (kvb_ppr[142]) begin
            if (kvb_ppr[141:139] != 3'(kvb_seen[0] - 1024) || kvb_ppr[138:75] !== kvb_img[1024 + kvb_ppr[141:139]]) kvb_bad = kvb_bad + 1;
            kvb_seen[0] = kvb_seen[0] + 1;
        end
        kvb_rdy_q <= dut.kvs_ctl.u_boot.boot_image_ready;
        if (dut.kvs_ctl.u_boot.boot_image_ready && !kvb_rdy_q) begin
            kvb_ready_cyc[kvb_pt] = cyc; $display("KVB_EVT @%0d image_ready target %0d at the dispatcher pins", cyc, kvb_pt);
        end
        if (dut.kvs_ctl.u_boot.setup_ready === 1'b1 && kvb_setup_cyc < 0) begin
            kvb_setup_cyc = cyc; $display("KVB_EVT @%0d setup_ready", cyc);
        end
        if (dut.kvs_ctl.u_boot.fault === 1'b1 && !kvb_ff_said) begin
            kvb_ff_said = 1; $display("KVB_EVT @%0d dispatcher fault code %b (expected_target %0d next_word %0d target %0d)", cyc,
                dut.kvs_ctl.u_boot.fault_code, dut.kvs_ctl.u_boot.expected_target, dut.kvs_ctl.u_boot.next_word, kvb_pt);
        end
        if (h_f === 1'b1 && !kvb_ff) begin kvb_ff = 1; $display("KVB_EVT @%0d HOST loader fault (target %0d)", cyc, h_t); end
    end
    // ---- the 160 boot CDC sinks (HBM domain): word stream hash, count, applied cycle ----
    reg [63:0] kvb_h [0:159]; integer kvb_n [0:159], kvb_app [0:159], kvb_cf [0:159];
    initial for (kvb_i = 0; kvb_i < 160; kvb_i = kvb_i + 1) begin kvb_h[kvb_i] = 0; kvb_n[kvb_i] = 0; kvb_app[kvb_i] = -1; kvb_cf[kvb_i] = 0; end
`define KVB_CDC(I, P) \
    always @(posedge hck) if (trace_on) begin \
        if (P.sink_we) begin kvb_h[I] = {kvb_h[I][56:0], kvb_h[I][63:57]} ^ P.sink_data ^ 64'(P.sink_addr); kvb_n[I] = kvb_n[I] + 1; end \
        if (P.applied_hbm === 1'b1 && kvb_app[I] < 0) kvb_app[I] = cyc; \
        if ((P.fault_hbm === 1'b1 || P.fault_core === 1'b1) && !kvb_cf[I]) begin kvb_cf[I] = 1; smoke_err("boot CDC fault"); \
            $display("KVB_ERR @%0d boot CDC %0d fault core %b hbm %b", cyc, I, P.fault_core, P.fault_hbm); end \
    end
    `KVB_CDC(0, dut.slg_WS_0.u_bcdc0)
    `KVB_CDC(1, dut.slg_WS_0.u_bcdc1)
    `KVB_CDC(2, dut.slg_WS_0.u_bcdc2)
    `KVB_CDC(3, dut.slg_WS_0.u_bcdc3)
    `KVB_CDC(4, dut.slg_WS_0.u_bcdcf)
    `KVB_CDC(5, dut.slg_WS_1.u_bcdc0)
    `KVB_CDC(6, dut.slg_WS_1.u_bcdc1)
    `KVB_CDC(7, dut.slg_WS_1.u_bcdc2)
    `KVB_CDC(8, dut.slg_WS_1.u_bcdc3)
    `KVB_CDC(9, dut.slg_WS_1.u_bcdcf)
    `KVB_CDC(10, dut.slg_WS_2.u_bcdc0)
    `KVB_CDC(11, dut.slg_WS_2.u_bcdc1)
    `KVB_CDC(12, dut.slg_WS_2.u_bcdc2)
    `KVB_CDC(13, dut.slg_WS_2.u_bcdc3)
    `KVB_CDC(14, dut.slg_WS_2.u_bcdcf)
    `KVB_CDC(15, dut.slg_WS_3.u_bcdc0)
    `KVB_CDC(16, dut.slg_WS_3.u_bcdc1)
    `KVB_CDC(17, dut.slg_WS_3.u_bcdc2)
    `KVB_CDC(18, dut.slg_WS_3.u_bcdc3)
    `KVB_CDC(19, dut.slg_WS_3.u_bcdcf)
    `KVB_CDC(20, dut.slg_WS_4.u_bcdc0)
    `KVB_CDC(21, dut.slg_WS_4.u_bcdc1)
    `KVB_CDC(22, dut.slg_WS_4.u_bcdc2)
    `KVB_CDC(23, dut.slg_WS_4.u_bcdc3)
    `KVB_CDC(24, dut.slg_WS_4.u_bcdcf)
    `KVB_CDC(25, dut.slg_WS_5.u_bcdc0)
    `KVB_CDC(26, dut.slg_WS_5.u_bcdc1)
    `KVB_CDC(27, dut.slg_WS_5.u_bcdc2)
    `KVB_CDC(28, dut.slg_WS_5.u_bcdc3)
    `KVB_CDC(29, dut.slg_WS_5.u_bcdcf)
    `KVB_CDC(30, dut.slg_WS_6.u_bcdc0)
    `KVB_CDC(31, dut.slg_WS_6.u_bcdc1)
    `KVB_CDC(32, dut.slg_WS_6.u_bcdc2)
    `KVB_CDC(33, dut.slg_WS_6.u_bcdc3)
    `KVB_CDC(34, dut.slg_WS_6.u_bcdcf)
    `KVB_CDC(35, dut.slg_WS_7.u_bcdc0)
    `KVB_CDC(36, dut.slg_WS_7.u_bcdc1)
    `KVB_CDC(37, dut.slg_WS_7.u_bcdc2)
    `KVB_CDC(38, dut.slg_WS_7.u_bcdc3)
    `KVB_CDC(39, dut.slg_WS_7.u_bcdcf)
    `KVB_CDC(40, dut.slg_WN_0.u_bcdc0)
    `KVB_CDC(41, dut.slg_WN_0.u_bcdc1)
    `KVB_CDC(42, dut.slg_WN_0.u_bcdc2)
    `KVB_CDC(43, dut.slg_WN_0.u_bcdc3)
    `KVB_CDC(44, dut.slg_WN_0.u_bcdcf)
    `KVB_CDC(45, dut.slg_WN_1.u_bcdc0)
    `KVB_CDC(46, dut.slg_WN_1.u_bcdc1)
    `KVB_CDC(47, dut.slg_WN_1.u_bcdc2)
    `KVB_CDC(48, dut.slg_WN_1.u_bcdc3)
    `KVB_CDC(49, dut.slg_WN_1.u_bcdcf)
    `KVB_CDC(50, dut.slg_WN_2.u_bcdc0)
    `KVB_CDC(51, dut.slg_WN_2.u_bcdc1)
    `KVB_CDC(52, dut.slg_WN_2.u_bcdc2)
    `KVB_CDC(53, dut.slg_WN_2.u_bcdc3)
    `KVB_CDC(54, dut.slg_WN_2.u_bcdcf)
    `KVB_CDC(55, dut.slg_WN_3.u_bcdc0)
    `KVB_CDC(56, dut.slg_WN_3.u_bcdc1)
    `KVB_CDC(57, dut.slg_WN_3.u_bcdc2)
    `KVB_CDC(58, dut.slg_WN_3.u_bcdc3)
    `KVB_CDC(59, dut.slg_WN_3.u_bcdcf)
    `KVB_CDC(60, dut.slg_WN_4.u_bcdc0)
    `KVB_CDC(61, dut.slg_WN_4.u_bcdc1)
    `KVB_CDC(62, dut.slg_WN_4.u_bcdc2)
    `KVB_CDC(63, dut.slg_WN_4.u_bcdc3)
    `KVB_CDC(64, dut.slg_WN_4.u_bcdcf)
    `KVB_CDC(65, dut.slg_WN_5.u_bcdc0)
    `KVB_CDC(66, dut.slg_WN_5.u_bcdc1)
    `KVB_CDC(67, dut.slg_WN_5.u_bcdc2)
    `KVB_CDC(68, dut.slg_WN_5.u_bcdc3)
    `KVB_CDC(69, dut.slg_WN_5.u_bcdcf)
    `KVB_CDC(70, dut.slg_WN_6.u_bcdc0)
    `KVB_CDC(71, dut.slg_WN_6.u_bcdc1)
    `KVB_CDC(72, dut.slg_WN_6.u_bcdc2)
    `KVB_CDC(73, dut.slg_WN_6.u_bcdc3)
    `KVB_CDC(74, dut.slg_WN_6.u_bcdcf)
    `KVB_CDC(75, dut.slg_WN_7.u_bcdc0)
    `KVB_CDC(76, dut.slg_WN_7.u_bcdc1)
    `KVB_CDC(77, dut.slg_WN_7.u_bcdc2)
    `KVB_CDC(78, dut.slg_WN_7.u_bcdc3)
    `KVB_CDC(79, dut.slg_WN_7.u_bcdcf)
    `KVB_CDC(80, dut.slg_ES_0.u_bcdc0)
    `KVB_CDC(81, dut.slg_ES_0.u_bcdc1)
    `KVB_CDC(82, dut.slg_ES_0.u_bcdc2)
    `KVB_CDC(83, dut.slg_ES_0.u_bcdc3)
    `KVB_CDC(84, dut.slg_ES_0.u_bcdcf)
    `KVB_CDC(85, dut.slg_ES_1.u_bcdc0)
    `KVB_CDC(86, dut.slg_ES_1.u_bcdc1)
    `KVB_CDC(87, dut.slg_ES_1.u_bcdc2)
    `KVB_CDC(88, dut.slg_ES_1.u_bcdc3)
    `KVB_CDC(89, dut.slg_ES_1.u_bcdcf)
    `KVB_CDC(90, dut.slg_ES_2.u_bcdc0)
    `KVB_CDC(91, dut.slg_ES_2.u_bcdc1)
    `KVB_CDC(92, dut.slg_ES_2.u_bcdc2)
    `KVB_CDC(93, dut.slg_ES_2.u_bcdc3)
    `KVB_CDC(94, dut.slg_ES_2.u_bcdcf)
    `KVB_CDC(95, dut.slg_ES_3.u_bcdc0)
    `KVB_CDC(96, dut.slg_ES_3.u_bcdc1)
    `KVB_CDC(97, dut.slg_ES_3.u_bcdc2)
    `KVB_CDC(98, dut.slg_ES_3.u_bcdc3)
    `KVB_CDC(99, dut.slg_ES_3.u_bcdcf)
    `KVB_CDC(100, dut.slg_ES_4.u_bcdc0)
    `KVB_CDC(101, dut.slg_ES_4.u_bcdc1)
    `KVB_CDC(102, dut.slg_ES_4.u_bcdc2)
    `KVB_CDC(103, dut.slg_ES_4.u_bcdc3)
    `KVB_CDC(104, dut.slg_ES_4.u_bcdcf)
    `KVB_CDC(105, dut.slg_ES_5.u_bcdc0)
    `KVB_CDC(106, dut.slg_ES_5.u_bcdc1)
    `KVB_CDC(107, dut.slg_ES_5.u_bcdc2)
    `KVB_CDC(108, dut.slg_ES_5.u_bcdc3)
    `KVB_CDC(109, dut.slg_ES_5.u_bcdcf)
    `KVB_CDC(110, dut.slg_ES_6.u_bcdc0)
    `KVB_CDC(111, dut.slg_ES_6.u_bcdc1)
    `KVB_CDC(112, dut.slg_ES_6.u_bcdc2)
    `KVB_CDC(113, dut.slg_ES_6.u_bcdc3)
    `KVB_CDC(114, dut.slg_ES_6.u_bcdcf)
    `KVB_CDC(115, dut.slg_ES_7.u_bcdc0)
    `KVB_CDC(116, dut.slg_ES_7.u_bcdc1)
    `KVB_CDC(117, dut.slg_ES_7.u_bcdc2)
    `KVB_CDC(118, dut.slg_ES_7.u_bcdc3)
    `KVB_CDC(119, dut.slg_ES_7.u_bcdcf)
    `KVB_CDC(120, dut.slg_EN_0.u_bcdc0)
    `KVB_CDC(121, dut.slg_EN_0.u_bcdc1)
    `KVB_CDC(122, dut.slg_EN_0.u_bcdc2)
    `KVB_CDC(123, dut.slg_EN_0.u_bcdc3)
    `KVB_CDC(124, dut.slg_EN_0.u_bcdcf)
    `KVB_CDC(125, dut.slg_EN_1.u_bcdc0)
    `KVB_CDC(126, dut.slg_EN_1.u_bcdc1)
    `KVB_CDC(127, dut.slg_EN_1.u_bcdc2)
    `KVB_CDC(128, dut.slg_EN_1.u_bcdc3)
    `KVB_CDC(129, dut.slg_EN_1.u_bcdcf)
    `KVB_CDC(130, dut.slg_EN_2.u_bcdc0)
    `KVB_CDC(131, dut.slg_EN_2.u_bcdc1)
    `KVB_CDC(132, dut.slg_EN_2.u_bcdc2)
    `KVB_CDC(133, dut.slg_EN_2.u_bcdc3)
    `KVB_CDC(134, dut.slg_EN_2.u_bcdcf)
    `KVB_CDC(135, dut.slg_EN_3.u_bcdc0)
    `KVB_CDC(136, dut.slg_EN_3.u_bcdc1)
    `KVB_CDC(137, dut.slg_EN_3.u_bcdc2)
    `KVB_CDC(138, dut.slg_EN_3.u_bcdc3)
    `KVB_CDC(139, dut.slg_EN_3.u_bcdcf)
    `KVB_CDC(140, dut.slg_EN_4.u_bcdc0)
    `KVB_CDC(141, dut.slg_EN_4.u_bcdc1)
    `KVB_CDC(142, dut.slg_EN_4.u_bcdc2)
    `KVB_CDC(143, dut.slg_EN_4.u_bcdc3)
    `KVB_CDC(144, dut.slg_EN_4.u_bcdcf)
    `KVB_CDC(145, dut.slg_EN_5.u_bcdc0)
    `KVB_CDC(146, dut.slg_EN_5.u_bcdc1)
    `KVB_CDC(147, dut.slg_EN_5.u_bcdc2)
    `KVB_CDC(148, dut.slg_EN_5.u_bcdc3)
    `KVB_CDC(149, dut.slg_EN_5.u_bcdcf)
    `KVB_CDC(150, dut.slg_EN_6.u_bcdc0)
    `KVB_CDC(151, dut.slg_EN_6.u_bcdc1)
    `KVB_CDC(152, dut.slg_EN_6.u_bcdc2)
    `KVB_CDC(153, dut.slg_EN_6.u_bcdc3)
    `KVB_CDC(154, dut.slg_EN_6.u_bcdcf)
    `KVB_CDC(155, dut.slg_EN_7.u_bcdc0)
    `KVB_CDC(156, dut.slg_EN_7.u_bcdc1)
    `KVB_CDC(157, dut.slg_EN_7.u_bcdc2)
    `KVB_CDC(158, dut.slg_EN_7.u_bcdc3)
    `KVB_CDC(159, dut.slg_EN_7.u_bcdcf)
    function automatic [63:0] kvb_hash(input integer t, input integer base, input integer n);
        reg [63:0] h; integer k; begin h = 0;
            for (k = 0; k < n; k = k + 1) h = {h[56:0], h[63:57]} ^ kvb_img[t * KVB_N + base + k] ^ 64'(k);
            kvb_hash = h; end
    endfunction
    task automatic kvb_load(input integer t); begin kvb_begin(t); kvb_body(t); end endtask
    task automatic kvb_begin(input integer t); integer n; begin
        n = (t == 0) ? 1024 : kvb_wc[t];
        @(negedge ck); h_begin = 1; h_t = t[3:0]; h_pw = n[10:0]; h_dw = (t == 0) ? 4'd8 : 4'd0;
        $display("KVB_EVT @%0d HOST begin target %0d (%0d + %0d words)", cyc, t, n, (t == 0) ? 8 : 0);
        if (t == 0) kvb_t0_begin = cyc;
        @(negedge ck); h_begin = 0;
    end endtask
    task automatic kvb_body(input integer t); integer a, n, w; begin
        n = (t == 0) ? 1024 : kvb_wc[t];
        for (a = 0; a < n; a = a + 1) begin h_wv = 1; h_desc = 0; h_addr = a[9:0]; h_data = kvb_img[t * KVB_N + a]; @(negedge ck); end
        if (t == 0) for (a = 0; a < 8; a = a + 1) begin h_wv = 1; h_desc = 1; h_addr = a[9:0]; h_data = kvb_img[1024 + a]; @(negedge ck); end
        h_wv = 0; h_seal = 1; @(negedge ck); h_seal = 0; h_auth = 1; h_ad = kvb_dig[t]; @(negedge ck); h_auth = 0;
        for (w = 0; w < 3000 && !(h_rdy && !h_f); w = w + 1) @(negedge ck);
        if (h_f) smoke_err("HOST loader fault (image refused)");
        else $display("KVB_EVT @%0d HOST program_ready target %0d digest %h (trusted %h)", cyc, t, h_dg, kvb_dig[t]);
        repeat (8) @(negedge ck);
    end endtask
    task automatic kvb_check_lprg(); integer g, bad; begin bad = 0;
        for (g = 0; g < 36; g = g + 1) begin
            if (dut.kvs_ctl.u_lprg.t_ctrl[g]   !== kvb_img[1 * KVB_N + 9 * g + 0][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_k[g]      !== kvb_img[1 * KVB_N + 9 * g + 1][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_v[g]      !== kvb_img[1 * KVB_N + 9 * g + 2][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_issue[g]  !== kvb_img[1 * KVB_N + 9 * g + 3][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_run[g]    !== kvb_img[1 * KVB_N + 9 * g + 4][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_writer[g] !== kvb_img[1 * KVB_N + 9 * g + 5][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_link[g]   !== kvb_img[1 * KVB_N + 9 * g + 6][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_quiet[g]  !== kvb_img[1 * KVB_N + 9 * g + 7][31:0]) bad = bad + 1;
            if (dut.kvs_ctl.u_lprg.t_end[g]    !== kvb_img[1 * KVB_N + 9 * g + 8][31:0]) bad = bad + 1;
        end
        if (dut.kvs_ctl.u_lprg.bound_digest !== kvb_img[1 * KVB_N + 324]) bad = bad + 1;
        if ({48'd0, dut.kvs_ctl.u_lprg.bound_epoch} !== kvb_img[1 * KVB_N + 325]) bad = bad + 1;
        $display("KVB_INFO u_lprg layer image: %0d of 326 roots/binds differ from target 1; configured %b fault %b code %b",
                 bad, dut.kvs_ctl.u_lprg.configured, dut.kvs_ctl.u_lprg.fault, dut.kvs_ctl.u_lprg.fault_code);
        if (bad || dut.kvs_ctl.u_lprg.configured !== 1'b1) smoke_err("u_lprg does not hold the compiled layer image bit-exact");
    end endtask
    task automatic kvb_check_sinks(); integer i, p, nm, bad_n, nap; reg [63:0] e_c [0:127]; reg [63:0] e_f [0:31];
        reg [127:0] used_c; reg [31:0] used_f; integer amin, amax; begin
        for (p = 0; p < 128; p = p + 1) e_c[p] = kvb_hash(6 + p / 32, (p % 32) * 32, 32);
        for (p = 0; p < 32; p = p + 1) e_f[p] = kvb_hash(5, 6 * p, 6);
        used_c = 0; used_f = 0; nm = 0; bad_n = 0; nap = 0; amin = -1; amax = -1;
        for (i = 0; i < 160; i = i + 1) begin
            if (kvb_app[i] >= 0) begin nap = nap + 1; if (amin < 0 || kvb_app[i] < amin) amin = kvb_app[i]; if (kvb_app[i] > amax) amax = kvb_app[i]; end
            if (i % 5 == 4) begin
                if (kvb_n[i] != 6) bad_n = bad_n + 1;
                for (p = 0; p < 32; p = p + 1) if (!used_f[p] && e_f[p] == kvb_h[i]) begin used_f[p] = 1; p = 99; end
                if (p != 100) nm = nm + 1;
            end else begin
                if (kvb_n[i] != 32) bad_n = bad_n + 1;
                for (p = 0; p < 128; p = p + 1) if (!used_c[p] && e_c[p] == kvb_h[i]) begin used_c[p] = 1; p = 999; end
                if (p != 1000) nm = nm + 1;
            end
        end
        $display("KVB_INFO boot CDC sinks: applied %0d/160 (edges %0d..%0d), word-count errors %0d, streams not matching a compiled image %0d; dispatcher sink_applied %h",
                 nap, amin, amax, bad_n, nm, dut.kvs_ctl.u_boot.sink_applied);
        if (nap != 160 || dut.kvs_ctl.u_boot.sink_applied !== {160{1'b1}}) smoke_err("not all 160 boot CDC sinks applied");
        if (bad_n || nm) smoke_err("KVB CDC sink streams differ from the compiled controller / front images");
    end endtask
    task automatic slice_programme(); integer k, w, ok; begin
        // pass 1 (after the first, unaligned POR + functional release): the die cfg image
        kvb_load(10);
        $display("KVB_INFO die cfg after target 10: sealed %b fault %b capability %b dispatcher diecfg_done %b fault %b",
                 dut.kvs_ctl.u_dcfg.sealed, dut.kvs_ctl.u_dcfg.fault, dut.kvs_ctl.u_dcfg.fused_program_capability,
                 dut.kvs_ctl.u_boot.diecfg_done, dut.kvs_ctl.u_boot.fault);
        // functional re-reset (die + HBM trees; the POR pad stays released).  Default HOST order: BEGIN the first pass-2
        // image (this drops the loader's program_ready, so boot_image_ready is low) BEFORE the functional reset, its words
        // / seal / auth / replay after the release.  +KVB_ORDER_A = the literal order (re-reset, then BEGIN target 1):
        // the HOST's boot_image_ready of target 10 is still high at the dispatcher's release (finding F-K2).
        k = (kvb_mut == 2) ? 2 : 1;
        if (!$test$plusargs("KVB_ORDER_A")) kvb_begin(k);
        @(negedge ck); rst_n = 0; $display("KVB_EVT @%0d functional resets asserted", cyc);
        repeat (`RST_EDGES) @(negedge ck); rst_n = 1; kvb_rel2 = cyc; $display("KVB_EVT @%0d functional resets released", cyc);
        repeat (`RST_EDGES) @(negedge ck);
        if ($test$plusargs("KVB_ORDER_A")) kvb_begin(k);
        kvb_body(k);
        kvb_load(3 - k);
        for (k = 3; k <= 9; k = k + 1) kvb_load(k);
        kvb_load(11); kvb_load(12); kvb_load(13); kvb_load(0);
        for (w = 0; w < 4000 && kvb_setup_cyc < 0; w = w + 1) @(negedge ck);
        repeat (64) @(negedge ck);
        // ---- checks ----
        ok = 1;
        for (k = 0; k <= 13; k = k + 1) if (kvb_seen[k] != kvb_wc[k]) begin ok = 0;
            $display("KVB_ERR target %0d: %0d words at the dispatcher pins, image %0d", k, kvb_seen[k], kvb_wc[k]); end
        $display("KVB_INFO dispatcher pins: %0d words, %0d bad; first word host %0d -> pins %0d (die relay edges %0d)",
                 kvb_seen[0] + kvb_seen[1] + kvb_seen[2] + kvb_seen[3] + kvb_seen[4] + kvb_seen[5] + kvb_seen[6] + kvb_seen[7] + kvb_seen[8]
                 + kvb_seen[9] + kvb_seen[10] + kvb_seen[11] + kvb_seen[12] + kvb_seen[13], kvb_bad, kvb_host_first, kvb_pin_first,
                 kvb_pin_first - kvb_host_first);
        if (!ok || kvb_bad) smoke_err("boot words at the dispatcher pins differ from the images");
        $display("KVB_INFO dispatcher: fault %b code %b installed %b linkcfg %b es12 %b es13 %b isa_seen %b local_configured %b epoch %h isa_digest %h",
                 dut.kvs_ctl.u_boot.fault, dut.kvs_ctl.u_boot.fault_code, dut.kvs_ctl.u_boot.installed, dut.kvs_ctl.u_boot.linkcfg_done,
                 dut.kvs_ctl.u_boot.es12_done, dut.kvs_ctl.u_boot.es13_done, dut.kvs_ctl.u_boot.isa_seen, dut.kvs_ctl.u_boot.local_configured,
                 dut.kvs_ctl.u_boot.installed_epoch, dut.kvs_ctl.u_boot.installed_isa_digest);
        if (dut.kvs_ctl.u_boot.fault !== 1'b0) smoke_err("dispatcher fault");
        if (dut.kvs_ctl.u_boot.installed !== 9'h1ff || dut.kvs_ctl.u_boot.linkcfg_done !== 1'b1 || dut.kvs_ctl.u_boot.es12_done !== 1'b1
            || dut.kvs_ctl.u_boot.es13_done !== 1'b1 || dut.kvs_ctl.u_boot.isa_seen !== 1'b1) smoke_err("not every image installed");
        if (dut.kvs_ctl.u_boot.installed_isa_digest !== kvb_dig[0]) smoke_err("installed ISA digest differs");
        if (dut.kvs_ctl.u_boot.local_configured !== 3'b111) smoke_err("local_configured not 3'b111 (own, wprg, lprg)");
        ok = 1;
        for (k = 0; k < 32; k = k + 1) if (dut.kvs_ctl.u_dcfg.ectl_a_cfg[5 * k +: 5] !== kvb_img[10 * KVB_N + k][4:0]) ok = 0;
        $display("KVB_INFO die cfg: sealed %b fault %b capability %b ectl_a_cfg %s", dut.kvs_ctl.u_dcfg.sealed, dut.kvs_ctl.u_dcfg.fault,
                 dut.kvs_ctl.u_dcfg.fused_program_capability, ok ? "= image" : "DIFFERS");
        if (dut.kvs_ctl.u_dcfg.sealed !== 1'b1 || dut.kvs_ctl.u_dcfg.fault !== 1'b0 || !ok
            || dut.kvs_ctl.u_dcfg.fused_program_capability !== kvb_img[10 * KVB_N + 75][0]) smoke_err("die cfg not sealed with the target-10 image");
        kvb_check_sinks();
        kvb_check_lprg();
        if (kvb_setup_cyc < 0) smoke_err("setup_ready did not rise");
        $display("KVB_CYCLES t10_ready %0d release2 %0d t1_ready %0d t9_ready %0d t13_ready %0d t0_begin %0d t0_ready %0d setup_ready %0d (t0_begin + %0d, release2 + %0d)",
                 kvb_ready_cyc[10], kvb_rel2, kvb_ready_cyc[1], kvb_ready_cyc[9], kvb_ready_cyc[13], kvb_t0_begin, kvb_ready_cyc[0],
                 kvb_setup_cyc, kvb_setup_cyc - kvb_t0_begin, kvb_setup_cyc - kvb_rel2);
    end endtask
    // Simulation assertions inside the die RTL (e.g. ot_async_fifo Gray-pointer checks) fire on the random pre-reset
    // state before the die's own reset tree (relays + qkd_rst_region) has delivered the reset; run_kv_boot.sh runs with
    // +verilator+error+limit and FAILS a run on any %Error at or after this mark (reset delivered everywhere).
    initial begin wait (trace_on === 1'b1); $display("KVB_TRACE_ON t=%0t", $time); end
