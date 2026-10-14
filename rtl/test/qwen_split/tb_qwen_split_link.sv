`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B TP8 two-die split (owner 2026-10-14 06:45 PT): MEASUREMENT BENCH of the die link on the NATIVE protocol
// (HEADS 1, Q_FP32 1: per layer 4 KVN + 32 FP32 Q words forward, 32 FP32 RES words back).  One whole decode step
// (38 stages: E, L0..L35, H) through the REAL RTL of every block on the crossing path:
//   SPLIT = 1  compute die: ROM-sequencer / SU / VM models -> C_ST relay stages (data forward, credit back) ->
//              ot_qfd_split_romlink (ot_qkvd_rom_end + level-face codec) -> UCIe x64 macro model pair (PHY_LAT)
//              KV/system die: ot_qkvd_kv_end (KVE_SPL: 1 = the thin cluster over its closed hard tiles) ->
//              ot_qkvd_split_kvlink (bridge) -> K_ST relay stages -> ot_qkvd_kv_seq_merged (HEADS 1, Q_FP32 1,
//              unchanged closed sequencer RTL, stage stepper inside) -> QX stages -> attention model -> RX stages back
//   SPLIT = 0  the merged-die reference: the same models -> ROM_ST on-die relay stages -> the same sequencer
// Attention model (timing stand-in, NOT the arithmetic): on the aq start it takes the 32 Q beats, ENG cycles after the
// last beat it emits 32 RES beats (no ready, as the hub); RES[b] = Q[b] ^ H(layer, b), so a lost, swapped or stale Q
// word is visible at the VM.  The landings model returns each quadrant's posted-row credit after 3 / 5 / 7 / 9 cycles
// and checks the row bits.  The ROM-sequencer model answers each stage: E after E_CYC, a layer stage = PRE cycles, then
// 4 KVN + 32 Q words on x3 + the score / weighted-sum descriptors on kvd, wait for the 32 RES at the VM face, POST
// cycles, s_done; H after H_CYC with {ntok, nval}.  Host (on the KV/system die): one d_start, waits d_done.
// Reported: STEP cycles (d_start -> d_done) and per layer ATT cycles (first x3 word -> last RES at the VM face).
// MUT: 1 = one flit dropped in the PHY (C->S; with LLR it is replayed: must PASS) | 2 = Q beats 0/1 swapped (seq MUT 2) |
//      3 = kvlink KVN tag bit 2 dropped (V rows posted as K) | 4 = LLR CRC never checked (with ERRP: must FAIL) |
//      5 = LLR nak ignored (with ERRP: must FAIL)
// ---------------------------------------------------------------------------------------------------------------------
module tb_qwen_split_link;
    parameter integer SPLIT   = 1;
    parameter integer C_ST    = 8;
    parameter integer K_ST    = 16;
    parameter integer ROM_ST  = 24;
    parameter integer PHY_LAT = 5;
    parameter integer QX      = 0;
    parameter integer RX      = 0;
    parameter integer ENG     = 200;
    parameter integer PRE     = 40;
    parameter integer POST    = 40;
    parameter integer E_CYC   = 50;
    parameter integer H_CYC   = 80;
    parameter integer KVE_SPL = 0;
    parameter integer MUT     = 0;
    parameter integer LLR     = 1;      // 1 = link-level retry + CRC (ot_qkvd_d2d_llr) at both ends
    parameter integer ERRP    = 0;      // > 0: flip one PHY bit every ERRP cycles in each direction (needs LLR)
    localparam integer W = 528, FW = 548, HD = 128;
    localparam integer NQ = 32, NK = 4, NR = 32, NL = 36;   // the stepper runs 38 stages: E, L0..L35, H

    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    reg [31:0] cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ================= compute-die side faces (models drive / observe these) =================
    reg          su_x3_v = 0;  reg [10:0] su_x3_tag = 0;  reg [511:0] su_x3_d = 0;  wire su_x3_cr;
    reg  [43:0]  su_kvd = 0;
    reg  [55:0]  rs_sd = 0;
    wire [186:0] rs_ds;  wire [74:0] rs_pw;
    wire         vm_ar_v; wire [518:0] vm_ar_d; reg vm_ar_cr = 0;
    // ================= sequencer faces (KV/system die) =================
    wire         q_x3_v;  wire [10:0] q_x3_tag; wire [511:0] q_x3_d; wire q_x3_cr;
    wire [55:0]  q_sd;    wire [43:0] q_kvd;
    wire         q_ar_v;  wire [518:0] q_ar_d; wire q_ar_cr;
    wire [186:0] q_ds;    wire [74:0] q_pw;
    wire [3:0]   faults_link;

    generate if (SPLIT) begin : g_split
        // ---- compute die relays (C_ST stages each way) ----
        wire c_x3_v, c_x3_cr, c_ar_v, c_ar_cr;  wire [522:0] c_x3; wire [518:0] c_ar; wire [55:0] c_sd; wire [43:0] c_kvd;
        wire [261:0] c_sc;
        ot_hdc_delay #(.W(1),   .D(C_ST), .RESET(1)) u_c1 (.clk(clk), .rst_n(rst_n), .d(su_x3_v), .q(c_x3_v));
        ot_hdc_delay #(.W(523), .D(C_ST))            u_c2 (.clk(clk), .rst_n(rst_n), .d({su_x3_tag, su_x3_d}), .q(c_x3));
        ot_hdc_delay #(.W(1),   .D(C_ST), .RESET(1)) u_c3 (.clk(clk), .rst_n(rst_n), .d(c_x3_cr), .q(su_x3_cr));
        ot_hdc_delay #(.W(56+44), .D(C_ST), .RESET(1)) u_c4 (.clk(clk), .rst_n(rst_n), .d({rs_sd, su_kvd}), .q({c_sd, c_kvd}));
        ot_hdc_delay #(.W(1),   .D(C_ST), .RESET(1)) u_c5 (.clk(clk), .rst_n(rst_n), .d(c_ar_v), .q(vm_ar_v));
        ot_hdc_delay #(.W(519), .D(C_ST))            u_c6 (.clk(clk), .rst_n(rst_n), .d(c_ar), .q(vm_ar_d));
        ot_hdc_delay #(.W(1),   .D(C_ST), .RESET(1)) u_c7 (.clk(clk), .rst_n(rst_n), .d(vm_ar_cr), .q(c_ar_cr));
        ot_hdc_delay #(.W(262), .D(C_ST), .RESET(1)) u_c8 (.clk(clk), .rst_n(rst_n), .d(c_sc), .q({rs_pw, rs_ds}));
        // ---- compute die link end ----
        wire c_up, c_txv, c_rxv, c_lv, k_up, k_txv, k_rxv, k_lv;
        wire [FW-1:0] c_txf, c_rxf, k_txf, k_rxf;
        wire [1:0] llr_f;
        wire [7:0] c_fc; wire [4:0] k_fc;
        wire [186:0] c_ds; wire [74:0] c_pw;
        assign c_sc = {c_pw, c_ds};
        ot_qfd_split_romlink #(.XS(2 * C_ST + 48), .OCR_AR(2 * C_ST + 40), .RB_RES(32)) u_rl (
            .clk(clk), .rst_n(rst_n), .x3_v(c_x3_v), .x3_d(c_x3[511:0]), .x3_tag(c_x3[522:512]), .x3_cr(c_x3_cr),
            .ar_v(c_ar_v), .ar_d(c_ar), .ar_cr(c_ar_cr), .ea_v(1'b0), .ea_kind(1'b0), .ea_addr(24'd0), .ea_cr(),
            .eq_v(), .eq_d(), .sd(c_sd), .kvd(c_kvd), .ds(c_ds), .pw(c_pw),
            .tx_up(c_up), .tx_v(c_txv), .tx_flit(c_txf), .rx_v(c_rxv), .rx_flit(c_rxf), .fault(faults_link[0]), .fault_cause(c_fc));
        // ---- package: the two macros (+ the link-level retry layer at each end when LLR) ----
        localparam integer PW = LLR ? FW + 35 : FW;
        wire drop = (MUT == 1) && c_lv && (cyc == 32'd3000);
        wire c_pup, c_ptv, c_prv, k_pup, k_ptv, k_prv;
        wire [PW-1:0] c_ptf, c_prf, k_ptf, k_prf, c_plf, k_plf;
        wire [PW-1:0] c_flip = (ERRP > 0 && cyc % ERRP == 0) ? (PW'(1) << (cyc % PW)) : {PW{1'b0}};
        wire [PW-1:0] k_flip = (ERRP > 0 && (cyc + 37) % ERRP == 0) ? (PW'(1) << ((cyc * 3) % PW)) : {PW{1'b0}};
        ot_qkvd_ucie_x64_phy_model #(.LAT(PHY_LAT), .FW(PW)) u_pc (.clk(clk), .rst_n(rst_n), .tx_up(c_pup), .tx_v(c_ptv), .tx_flit(c_ptf),
            .rx_v(c_prv), .rx_flit(c_prf), .link_v(c_lv), .link_flit(c_plf), .far_v(k_lv), .far_flit(k_plf ^ k_flip));
        ot_qkvd_ucie_x64_phy_model #(.LAT(PHY_LAT), .FW(PW)) u_pk (.clk(clk), .rst_n(rst_n), .tx_up(k_pup), .tx_v(k_ptv), .tx_flit(k_ptf),
            .rx_v(k_prv), .rx_flit(k_prf), .link_v(k_lv), .link_flit(k_plf), .far_v(c_lv && !drop), .far_flit(c_plf ^ c_flip));
        if (LLR) begin : g_llr
            wire [2:0] fc0, fc1;
            ot_qkvd_d2d_llr #(.FW(FW), .MUT(MUT == 4 ? 1 : (MUT == 5 ? 2 : 0))) u_lc (.clk(clk), .rst_n(rst_n),
                .a_tx_up(c_up), .a_tx_v(c_txv), .a_tx_flit(c_txf), .a_rx_v(c_rxv), .a_rx_flit(c_rxf),
                .p_tx_up(c_pup), .p_tx_v(c_ptv), .p_tx_flit(c_ptf), .p_rx_v(c_prv), .p_rx_flit(c_prf), .fault(llr_f[0]), .fault_cause(fc0));
            ot_qkvd_d2d_llr #(.FW(FW), .MUT(MUT == 4 ? 1 : (MUT == 5 ? 2 : 0))) u_lk (.clk(clk), .rst_n(rst_n),
                .a_tx_up(k_up), .a_tx_v(k_txv), .a_tx_flit(k_txf), .a_rx_v(k_rxv), .a_rx_flit(k_rxf),
                .p_tx_up(k_pup), .p_tx_v(k_ptv), .p_tx_flit(k_ptf), .p_rx_v(k_prv), .p_rx_flit(k_prf), .fault(llr_f[1]), .fault_cause(fc1));
        end else begin : g_nollr
            assign c_up = c_pup; assign c_ptv = c_txv; assign c_ptf = c_txf; assign c_rxv = c_prv; assign c_rxf = c_prf;
            assign k_up = k_pup; assign k_ptv = k_txv; assign k_ptf = k_txf; assign k_rxv = k_prv; assign k_rxf = k_prf;
            assign llr_f = 2'b00;
        end
        // ---- KV/system die link end + bridge ----
        wire [3:0] kr_v, kr_cr; wire [4*W-1:0] kr_d; wire [2:0] kt_v, kt_cr; wire [3*W-1:0] kt_d;
        ot_qkvd_kv_end #(.QD(8), .UCX(64), .FCR_RES(32), .SPL(KVE_SPL)) u_ke (.clk(clk), .rst_n(rst_n),
            .t_v(kt_v), .t_d(kt_d), .t_cr(kt_cr), .r_v(kr_v), .r_d(kr_d), .r_cr(kr_cr),
            .tx_up(k_up), .tx_v(k_txv), .tx_flit(k_txf), .rx_v(k_rxv), .rx_flit(k_rxf), .fault(faults_link[1]), .fault_cause(k_fc));
        wire b_x3_v, b_x3_cr, b_ar_v, b_ar_cr; wire [10:0] b_x3_tag; wire [511:0] b_x3_d; wire [55:0] b_sd; wire [43:0] b_kvd;
        wire [518:0] b_ar_d; wire [186:0] b_ds; wire [74:0] b_pw;
        ot_qkvd_split_kvlink #(.QB(8), .KB(8), .XS(40), .MUT(MUT == 3 ? 1 : 0)) u_kl (.clk(clk), .rst_n(rst_n),
            .r_v(kr_v), .r_d(kr_d), .r_cr(kr_cr), .t_v(kt_v), .t_d(kt_d), .t_cr(kt_cr),
            .x3_v(b_x3_v), .x3_tag(b_x3_tag), .x3_d(b_x3_d), .x3_cr(b_x3_cr), .sd(b_sd), .kvd(b_kvd),
            .ar_v(b_ar_v), .ar_d(b_ar_d), .ar_cr(b_ar_cr), .ds(b_ds), .pw(b_pw),
            .ea_v(), .ea_kind(), .ea_addr(), .ea_cr(1'b0), .eq_v(1'b0), .eq_d(512'd0), .d2d_fault(faults_link[1]), .d2d_cause(k_fc),
            .fault(faults_link[2]));
        // ---- KV/system die relays bridge <-> sequencer (K_ST stages each way) ----
        ot_hdc_delay #(.W(1),   .D(K_ST), .RESET(1)) u_k1 (.clk(clk), .rst_n(rst_n), .d(b_x3_v), .q(q_x3_v));
        ot_hdc_delay #(.W(523), .D(K_ST))            u_k2 (.clk(clk), .rst_n(rst_n), .d({b_x3_tag, b_x3_d}), .q({q_x3_tag, q_x3_d}));
        ot_hdc_delay #(.W(1),   .D(K_ST), .RESET(1)) u_k3 (.clk(clk), .rst_n(rst_n), .d(q_x3_cr), .q(b_x3_cr));
        ot_hdc_delay #(.W(100), .D(K_ST), .RESET(1)) u_k4 (.clk(clk), .rst_n(rst_n), .d({b_sd, b_kvd}), .q({q_sd, q_kvd}));
        ot_hdc_delay #(.W(1),   .D(K_ST), .RESET(1)) u_k5 (.clk(clk), .rst_n(rst_n), .d(q_ar_v), .q(b_ar_v));
        ot_hdc_delay #(.W(519), .D(K_ST))            u_k6 (.clk(clk), .rst_n(rst_n), .d(q_ar_d), .q(b_ar_d));
        ot_hdc_delay #(.W(1),   .D(K_ST), .RESET(1)) u_k7 (.clk(clk), .rst_n(rst_n), .d(b_ar_cr), .q(q_ar_cr));
        ot_hdc_delay #(.W(262), .D(K_ST), .RESET(1)) u_k8 (.clk(clk), .rst_n(rst_n), .d({q_pw, q_ds}), .q({b_pw, b_ds}));
        assign faults_link[3] = |llr_f;
    end else begin : g_merged
        ot_hdc_delay #(.W(1),   .D(ROM_ST), .RESET(1)) u_r1 (.clk(clk), .rst_n(rst_n), .d(su_x3_v), .q(q_x3_v));
        ot_hdc_delay #(.W(523), .D(ROM_ST))            u_r2 (.clk(clk), .rst_n(rst_n), .d({su_x3_tag, su_x3_d}), .q({q_x3_tag, q_x3_d}));
        ot_hdc_delay #(.W(1),   .D(ROM_ST), .RESET(1)) u_r3 (.clk(clk), .rst_n(rst_n), .d(q_x3_cr), .q(su_x3_cr));
        ot_hdc_delay #(.W(100), .D(ROM_ST), .RESET(1)) u_r4 (.clk(clk), .rst_n(rst_n), .d({rs_sd, su_kvd}), .q({q_sd, q_kvd}));
        ot_hdc_delay #(.W(1),   .D(ROM_ST), .RESET(1)) u_r5 (.clk(clk), .rst_n(rst_n), .d(q_ar_v), .q(vm_ar_v));
        ot_hdc_delay #(.W(519), .D(ROM_ST))            u_r6 (.clk(clk), .rst_n(rst_n), .d(q_ar_d), .q(vm_ar_d));
        ot_hdc_delay #(.W(1),   .D(ROM_ST), .RESET(1)) u_r7 (.clk(clk), .rst_n(rst_n), .d(vm_ar_cr), .q(q_ar_cr));
        ot_hdc_delay #(.W(262), .D(ROM_ST), .RESET(1)) u_r8 (.clk(clk), .rst_n(rst_n), .d({q_pw, q_ds}), .q({rs_pw, rs_ds}));
        assign faults_link = 4'd0;
    end endgenerate

    // ================= the sequencer (KV/system die), unchanged RTL =================
    wire [4*540-1:0] aq;  wire [4*(HD*8+23)-1:0] kvn;  reg [3:0] kvn_cr = 0;  wire [4*33-1:0] kc;
    reg  a_ov = 0, a_og = 0; reg [5:0] a_ob = 0; reg [511:0] a_od = 0;
    wire a_ov_r, a_og_r; wire [5:0] a_ob_r; wire [511:0] a_od_r;
    wire hs, seq_f; wire [8:0] seq_fc;
    reg  [181:0] hc = 0; wire [92:0] tk;
    ot_hdc_delay #(.W(1), .D(RX), .RESET(1)) u_rxv (.clk(clk), .rst_n(rst_n), .d(a_ov), .q(a_ov_r));
    ot_hdc_delay #(.W(519), .D(RX)) u_rxd (.clk(clk), .rst_n(rst_n), .d({a_og, a_ob, a_od}), .q({a_og_r, a_ob_r, a_od_r}));
    ot_qkvd_kv_seq_merged #(.HD(HD), .HEADS(1), .Q_FP32(1), .OCR_AR(64), .MUT(MUT == 2 ? 2 : 0)) u_seq (
        .clk(clk), .rst_n(rst_n), .x3_v(q_x3_v), .x3_tag(q_x3_tag), .x3_d(q_x3_d), .x3_cr(q_x3_cr),
        .sd(q_sd), .kvd(q_kvd), .ar_v(q_ar_v), .ar_d(q_ar_d), .ar_cr(q_ar_cr), .ds(q_ds), .pw(q_pw),
        .aq(aq), .kvn(kvn), .kvn_cr(kvn_cr), .kc(kc), .af(4'd0), .mf(4'd0), .hs(hs),
        .a_out_valid(a_ov_r), .a_out_g(a_og_r), .a_out_beat(a_ob_r), .a_out_data(a_od_r), .a_hub_fault(1'b0),
        .hc(hc), .tk(tk), .fault(seq_f), .fault_cause(seq_fc));
    wire [539:0] aq0;
    ot_hdc_delay #(.W(540), .D(QX), .RESET(1)) u_qx (.clk(clk), .rst_n(rst_n), .d(aq[0 +: 540]), .q(aq0));

    // ================= checks / models =================
    integer errors = 0;
    function automatic [511:0] qword(input integer l, input integer b);
        integer j; begin for (j = 0; j < 16; j = j + 1) qword[32*j +: 32] = 32'h3f80_0000 ^ (l * 7919 + b * 131 + j * 17); end
    endfunction
    function automatic [511:0] kword(input integer l, input integer t);
        integer j; begin for (j = 0; j < 64; j = j + 1) kword[8*j +: 8] = 8'(l * 29 + t * 53 + j * 3); end
    endfunction
    function automatic [511:0] hres(input integer l, input integer b);
        integer j; begin for (j = 0; j < 16; j = j + 1) hres[32*j +: 32] = 32'hA5A5_0000 + l * 4096 + b * 64 + j; end
    endfunction

    // ---- attention model (at aq copy 0 after QX) ----
    reg [511:0] aqw [0:31];
    integer a_layer = -1, a_nq = 0, a_cnt = -1, a_out = -1, qcop_bad = 0;
    always @(posedge clk) if (rst_n) begin
        a_ov <= 1'b0;
        if (aq0[539]) begin a_layer = aq0[524:519]; a_nq = 0; end
        if (aq0[518]) begin aqw[aq0[517:512]] = aq0[511:0]; a_nq = a_nq + 1; if (a_nq == NQ) a_cnt = ENG; end
        if (a_cnt > 0) a_cnt = a_cnt - 1;
        else if (a_cnt == 0) begin a_cnt = -1; a_out = 0; end
        if (a_out >= 0) begin
            a_ov <= 1'b1; a_og <= 1'b0; a_ob <= 6'(a_out); a_od <= aqw[a_out] ^ hres(a_layer, a_out);
            a_out = (a_out == NR - 1) ? -1 : a_out + 1;
        end
    end
    // ---- landing model: per-quadrant row credit after 3/5/7/9 cycles; row bits checked on copy 0 ----
    integer nrow_l = 0;
    reg [9:0] crp [0:3];
    initial begin crp[0] = 0; crp[1] = 0; crp[2] = 0; crp[3] = 0; end
    integer qd;
    always @(posedge clk) if (rst_n) begin
        for (qd = 0; qd < 4; qd = qd + 1) begin
            crp[qd] <= {crp[qd][8:0], kvn[(HD*8+23)*qd + HD*8+22]};
            kvn_cr[qd] <= crp[qd][2 + 2*qd];
        end
        if (kvn[HD*8+22]) begin : rowchk
            integer vg, tg0;
            vg = kvn[HD*8+21 -: 2];
            tg0 = (vg == 0) ? 0 : 4;
            if (vg != (nrow_l % 2) * 2 || kvn[HD*8-1:0] !== {kword(kvn[HD*8+5 -: 6], tg0 + 1), kword(kvn[HD*8+5 -: 6], tg0)}) begin
                errors = errors + 1; $display("ROW mismatch layer %0d vg %0d", kvn[HD*8+5 -: 6], vg);
            end
            nrow_l = nrow_l + 1;
        end
        for (qd = 1; qd < 4; qd = qd + 1) if (aq[540*qd +: 540] !== aq[0 +: 540]) qcop_bad = qcop_bad + 1;
    end

    // ---- VM model: RES credits back after 2 cycles, words checked ----
    integer vm_n = 0, vm_layer = 0;
    reg [1:0] vcr = 0;
    always @(posedge clk) if (rst_n) begin
        vcr <= {vcr[0], vm_ar_v};
        vm_ar_cr <= vcr[1];
        if (vm_ar_v) begin
            if (vm_ar_d[517:512] != 6'(vm_n) || vm_ar_d[518] != 1'b0 || vm_ar_d[511:0] !== (qword(vm_layer, vm_n) ^ hres(vm_layer, vm_n))) begin
                errors = errors + 1; $display("RES mismatch layer %0d beat %0d", vm_layer, vm_n);
            end
            vm_n = vm_n + 1;
        end
    end

    // ---- ROM sequencer + SU model (compute die faces) ----
    integer stage = -1, xcr = 40, rs_busy = 0, step_start = 0, step_end = 0;
    integer att_start [0:63];
    integer att_end [0:63];
    integer att_sum = 0, att_min = 1 << 30, att_max = 0;
    always @(posedge clk) if (rst_n && su_x3_cr) xcr = xcr + 1;
    task tick; begin @(posedge clk); #0.05; end endtask
    task send_x3(input [10:0] tag, input [511:0] d);
        begin
            while (xcr == 0) tick();
            su_x3_v = 1; su_x3_tag = tag; su_x3_d = d; xcr = xcr - 1; tick(); su_x3_v = 0;
        end
    endtask
    integer i, l, t;
    initial begin
        // credits on the x3 face: the merged-die SU starts with the sequencer's 40; the split SU with the ROM end's XS
        if (SPLIT) xcr = 2 * C_ST + 48;
        repeat (8) tick(); rst_n = 1; repeat (40) tick();
        // host: one decode step {token 5, pos 1000, gen 1}
        hc = 0; hc[17:0] = 18'd1000; hc[35:18] = 18'd5; hc[37:36] = 2'd1; hc[38] = 1'b1; step_start = cyc; tick(); hc[38] = 1'b0;
        forever begin
            // wait for h_start
            while (!rs_ds[42]) tick();
            stage = rs_ds[41:36];
            rs_sd[50] = 1'b0;                 // s_done falls
            if (stage == 0) begin repeat (E_CYC) tick(); end
            else if (stage <= NL) begin
                l = stage - 1;
                repeat (PRE) tick();
                att_start[l] = cyc;
                for (t = 0; t < 2; t = t + 1) for (i = 0; i < 2; i = i + 1)
                    send_x3({3'b010, 5'd0, 3'(4 * t + i)}, kword(l, 4 * t + i));
                for (i = 0; i < NQ; i = i + 1) send_x3({3'b001, 2'd0, 6'(i)}, qword(l, i));
                su_kvd = {1'b1, 1'b1, 18'd1000, 12'd0, 6'(l), 6'd0}; tick();
                su_kvd = {1'b1, 1'b0, 18'd1000, 12'd0, 6'(l), 6'd0}; tick(); su_kvd = 0;
                while (vm_n < NR) tick();
                att_end[l] = cyc; vm_n = 0; vm_layer = vm_layer + 1;
                if (l < 2 || l == NL - 1) $display("LAYER %0d att=%0d at cycle %0d", l, att_end[l] - att_start[l], cyc);
                att_sum = att_sum + (att_end[l] - att_start[l]);
                if (att_end[l] - att_start[l] < att_min) att_min = att_end[l] - att_start[l];
                if (att_end[l] - att_start[l] > att_max) att_max = att_end[l] - att_start[l];
                repeat (POST) tick();
            end else begin
                repeat (H_CYC) tick();
                rs_sd[49:32] = 18'd77; rs_sd[31:0] = 32'h4141_4141;
            end
            rs_sd[50] = 1'b1;
            if (stage == NL + 1) begin
                while (!tk[92]) tick();
                step_end = cyc;
                if (tk[81:64] != 18'd77 || tk[63:32] != 32'h4141_4141) begin errors = errors + 1; $display("TOKEN mismatch %0d", tk[81:64]); end
                repeat (40) tick();
                if (seq_f || |faults_link) begin errors = errors + 1; $display("FAULT seq %b cause %h link %b", seq_f, seq_fc, faults_link); end
                if (qcop_bad) begin errors = errors + 1; $display("QUADRANT copies differ %0d", qcop_bad); end
                if (nrow_l != 2 * NL) begin errors = errors + 1; $display("ROWS %0d", nrow_l); end
                if (errors == 0)
                    $display("SPLIT_LINK_PASS split=%0d c_st=%0d k_st=%0d rom_st=%0d phy=%0d spl=%0d eng=%0d step=%0d att_mean=%0d att_min=%0d att_max=%0d",
                             SPLIT, C_ST, K_ST, ROM_ST, PHY_LAT, KVE_SPL, ENG, step_end - step_start, att_sum / NL, att_min, att_max);
                else $display("SPLIT_LINK_FAIL errors=%0d split=%0d mut=%0d", errors, SPLIT, MUT);
                $finish;
            end
            tick();
        end
    end
    // debug trace (DBG=1): first words through the faces
    parameter integer DBG = 0;
    always @(posedge clk) if (DBG && rst_n && cyc < 3000) begin
        if (su_x3_v) $display("%0d SU x3 tag %h", cyc, su_x3_tag);
        if (q_x3_v) $display("%0d SEQ x3 tag %h", cyc, q_x3_tag);
        if (q_kvd[43]) $display("%0d SEQ kvd %h", cyc, q_kvd);
        if (aq[539]) $display("%0d SEQ aq start", cyc);
        if (q_ar_v) $display("%0d SEQ ar beat %0d", cyc, q_ar_d[517:512]);
        if (vm_ar_v) $display("%0d VM ar beat %0d", cyc, vm_ar_d[517:512]);
        if (q_ds[42]) $display("%0d SEQ h_start stage %0d", cyc, q_ds[41:36]);
        if (rs_ds[42]) $display("%0d ROM h_start stage %0d", cyc, rs_ds[41:36]);
    end
    // watchdog
    initial begin
        #(1000000 * 0.8334);
        $display("SPLIT_LINK_FAIL timeout stage=%0d vm_n=%0d seq_f=%b cause=%h link=%b split=%0d mut=%0d", stage, vm_n, seq_f, seq_fc, faults_link, SPLIT, MUT);
        $finish;
    end
endmodule
