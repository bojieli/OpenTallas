`timescale 1ns/1ps
// Q-LINK 2026-10-15 component bench: compute-die end + KV/system-die end of the static D2D link through a behavioural
// UCIe PHY pair (the only modelled part). Real RTL: both static ends (calendars, slot SRAM/CRC links), the typed
// native attention record codecs on both dies, the kind-15 status codec, the recovery controllers and the HOST
// link-service collector. Stimuli (Q / RESULT data, compute status levels, HOST reset / clear) are declared external
// inputs at this component boundary. Calendars are the compiler images of tools/qwen_split/d2d_link_calendar.py,
// loaded through the cfg port before boot.
//
// Checks: every frame arrives and is decoded at its compiled cycle (exact cycle, payload bit-exact), no fault in normal
// epochs; recovery scenario: one corrupted PHY bit -> KV CRC abort -> compute missing-frame abort -> drain -> HOST link
// reset -> retrain -> forwarded epoch -> exact replay of the layer; witnesses and typed faults checked.
// MUT: 1 compute write slot +1, 2 KV RX demux swap, 3 producer fires 1 cycle late, 4 calendar compiled with a wrong TXL
//      (run script), 5 kind-15 status levels forced stale (fresh gating mutant in the bench reference) -> must FAIL.
module tb_qwen_d2d_static;
    parameter integer MUT = 0, TXL = 6, PHY = 5, P = 100, NLAY = 6, BAD_LAYER = 4;
    parameter CALDIR = "cal";
    localparam integer FW = 548, PW = 583;
    reg ck = 0; always #0.4167 ck = ~ck;
    reg por_n = 0, rst_n = 0;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;

    // ---------------- calendars (compiler images) ----------------
    reg [31:0] img_ct [0:127], img_cr [0:127], img_kt [0:127], img_kr [0:127];
    reg cfg_c_tx = 0, cfg_c_rx = 0, cfg_k_tx = 0, cfg_k_rx = 0; reg [6:0] cfg_a = 0; reg [31:0] cfg_dc = 0, cfg_dk = 0;

    // ---------------- PHY pair (behavioural) ----------------
    wire c_ptx_v, k_ptx_v, c_prx_v, k_prx_v, c_up, k_up; wire [PW-1:0] c_ptx, k_ptx, c_prx, k_prx;
    wire c_lv, k_lv; wire [PW-1:0] c_lf, k_lf;
    reg corrupt = 0;
    integer bad_armed = 0;   // set by the sequence for the exceptional layer only
    wire c_phy_rst_n, k_phy_rst_n;
    ot_qkvd_ucie_x64_phy_model #(.LAT(PHY), .FW(PW)) u_cphy (.clk(ck), .rst_n(c_phy_rst_n), .tx_up(c_up),
        .tx_v(c_ptx_v), .tx_flit(c_ptx), .rx_v(c_prx_v), .rx_flit(c_prx), .link_v(c_lv), .link_flit(c_lf),
        .far_v(k_lv), .far_flit(k_lf));
    ot_qkvd_ucie_x64_phy_model #(.LAT(PHY), .FW(PW)) u_kphy (.clk(ck), .rst_n(k_phy_rst_n), .tx_up(k_up),
        .tx_v(k_ptx_v), .tx_flit(k_ptx), .rx_v(k_prx_v), .rx_flit(k_prx), .link_v(k_lv), .link_flit(k_lf),
        .far_v(c_lv), .far_flit(c_lf ^ (corrupt ? {{(PW-77){1'b0}}, 1'b1, 76'd0} : {PW{1'b0}})));

    // ---------------- recovery + epoch (KV = master, compute = follower) ----------------
    reg host_reset_req = 0, host_clear = 0, host_boot = 0;
    wire k_eb, c_eb; wire [7:0] k_ep, c_ep; wire k_abort, c_abort, k_endf, c_endf; wire [7:0] k_fc, c_fc;
    wire fwd_ep, fwd_lrst_n, k_lu, c_lu, k_dr, k_seen, k_rt, k_rec, c_rec; wire [7:0] k_tf, c_tf;
    wire [31:0] k_rcyc, c_rcyc;
    reg [2:0] bump_ep = 0, bump_lr = 3'b111;          // package bumps beside the forwarded clock: fixed 3 cycles
    always @(posedge ck) begin bump_ep <= {bump_ep, fwd_ep}; bump_lr <= {bump_lr, fwd_lrst_n}; end
    wire c_lrst_n;
    ot_qwen_d2d_recovery #(.MASTER(1), .BUMP(3)) u_krec (.ck(ck), .por_n(por_n), .rst_n(rst_n),
        .abort(k_abort | k_endf), .fault_cause(k_fc), .end_fault(k_endf), .p_tx_up(k_up), .p_tx_v(k_ptx_v),
        .p_rx_v(k_prx_v), .reset_req(host_reset_req), .recovery_clear(host_clear), .boot_begin(host_boot),
        .fwd_epoch_i(1'b0), .fwd_epoch_o(fwd_ep), .fwd_link_rst_n(fwd_lrst_n), .phy_rst_n(k_phy_rst_n),
        .epoch_begin(k_eb), .epoch(k_ep), .link_up(k_lu), .links_drained(k_dr), .link_reset_seen(k_seen),
        .retrained(k_rt), .transport_fault(k_tf), .recovering(k_rec), .recovery_cycles(k_rcyc));
    wire c_phy_own;
    ot_qwen_d2d_recovery #(.MASTER(0), .BUMP(3)) u_crec (.ck(ck), .por_n(por_n), .rst_n(rst_n),
        .abort(c_abort | c_endf), .fault_cause(c_fc), .end_fault(c_endf), .p_tx_up(c_up), .p_tx_v(c_ptx_v),
        .p_rx_v(c_prx_v), .reset_req(1'b0), .recovery_clear(1'b0), .boot_begin(1'b0),
        .fwd_epoch_i(bump_ep[2]), .fwd_epoch_o(), .fwd_link_rst_n(), .phy_rst_n(c_phy_own),
        .epoch_begin(c_eb), .epoch(c_ep), .link_up(c_lu), .links_drained(), .link_reset_seen(),
        .retrained(), .transport_fault(c_tf), .recovering(c_rec), .recovery_cycles(c_rcyc));
    assign c_phy_rst_n = c_phy_own & bump_lr[2];

    // ---------------- layer starts (compiled: fixed offset after each epoch_begin) ----------------
    integer lay = -1, lstart = 0, ep_cyc = 0;
    reg cstart = 0;
    always @(posedge ck) if (k_eb) ep_cyc <= cyc;
    // ---------------- link ends ----------------
    wire [3:0] c_txs, k_txs; wire [3:0] c_tk, k_tk; wire [4:0] c_tb, k_tb;
    wire [3:0] c_rxe, c_rxs, k_rxe, k_rxs; wire [3:0] c_rk, k_rk; wire [4:0] c_rb, k_rb; wire [FW-1:0] c_rxp, k_rxp;
    wire [3:0] c_tv, k_tv; wire [4*FW-1:0] c_tp, k_tp;
    ot_qwen_d2d_static_end #(.NT(4), .NR(4), .TXD({8'd1, 8'd1, 8'd1, 8'd1}), .MUT(MUT == 1 ? 1 : 0)) u_cend (
        .ck({5{ck}}), .rst_n(rst_n), .cfg_tx_we(cfg_c_tx), .cfg_rx_we(cfg_c_rx), .cfg_addr(cfg_a), .cfg_data(cfg_dc),
        .epoch_begin(c_eb), .epoch(c_ep), .cal_start(cstart),
        .tx_slot(c_txs), .tx_kind(c_tk), .tx_beat(c_tb), .tx_valid(c_tv), .tx_payload(c_tp),
        .rx_event(c_rxe), .rx_slot(c_rxs), .rx_kind(c_rk), .rx_beat(c_rb), .rx_payload(c_rxp),
        .p_tx_up(c_up), .p_tx_v(c_ptx_v), .p_tx_flit(c_ptx), .p_rx_v(c_prx_v), .p_rx_flit(c_prx),
        .epoch_abort(c_abort), .fault_cause(c_fc), .end_fault(c_endf), .cal_running());
    ot_qwen_d2d_static_end #(.NT(4), .NR(4), .TXD({8'd1, 8'd1, 8'd1, 8'd1}), .MUT(MUT == 2 ? 2 : 0)) u_kend (
        .ck({5{ck}}), .rst_n(rst_n), .cfg_tx_we(cfg_k_tx), .cfg_rx_we(cfg_k_rx), .cfg_addr(cfg_a), .cfg_data(cfg_dk),
        .epoch_begin(k_eb), .epoch(k_ep), .cal_start(cstart),
        .tx_slot(k_txs), .tx_kind(k_tk), .tx_beat(k_tb), .tx_valid(k_tv), .tx_payload(k_tp),
        .rx_event(k_rxe), .rx_slot(k_rxs), .rx_kind(k_rk), .rx_beat(k_rb), .rx_payload(k_rxp),
        .p_tx_up(k_up), .p_tx_v(k_ptx_v), .p_tx_flit(k_ptx), .p_rx_v(k_prx_v), .p_rx_flit(k_prx),
        .epoch_abort(k_abort), .fault_cause(k_fc), .end_fault(k_endf), .cal_running());

    // ---------------- producers (stimulus schedule = the compiled send cycles of the bench layer profile) ----------
    function automatic [511:0] word(input integer l, input integer k, input integer b);
        integer i; begin for (i = 0; i < 16; i = i + 1) word[i*32 +: 32] = 32'h9e3779b9 * (l * 997 + k * 131 + b * 17 + i + 1); end
    endfunction
    integer rel; always @* rel = cyc - lstart;
    wire [15:0] op_epoch = 16'h0400 + lay[15:0];
    wire [5:0]  op_layer = 6'(lay % 36);
    wire shift = (MUT == 3);
    wire [31:0] crel = rel - (shift ? 1 : 0);
    wire c_q_ev = lay >= 0 && (crel == 2 || (crel >= 3 && crel < 35));
    wire [3:0] c_q_kind = crel == 2 ? 4'd1 : 4'd2;
    wire [4:0] c_q_beat = crel == 2 ? 5'd0 : 5'(crel - 3);
    wire [511:0] c_q_data = crel == 2 ? {493'd0, 5'd0, 13'(lay * 7 + 5), 1'b1} : word(lay, 2, crel - 3);
    wire k_r_ev = lay >= 0 && (rel >= 50 && rel < 82 || rel == 83);
    wire [3:0] k_r_kind = rel == 83 ? 4'd4 : 4'd3;
    wire [4:0] k_r_beat = rel == 83 ? 5'd0 : 5'(rel - 50);
    wire [511:0] k_r_data = rel == 83 ? {507'd0, 5'b01001} : word(lay, 3, rel - 50);
    wire ca_rv, ka_rv, ca_f, ka_f; wire [3:0] ca_rk, ka_rk, ca_fc, ka_fc; wire [15:0] ca_re, ka_re; wire [5:0] ca_rl, ka_rl;
    wire [4:0] ca_rb, ka_rb; wire [511:0] ca_rd, ka_rd;
    qkd_native_attention_record #(.KV_SIDE(0)) u_ca (.ck(ck), .rst_n(rst_n & ~c_eb),
        .tx_event(c_q_ev), .tx_expected(c_txs[0]), .tx_kind(c_q_kind), .tx_expected_kind(c_tk),
        .tx_epoch(op_epoch), .tx_expected_epoch(op_epoch), .tx_layer(op_layer), .tx_expected_layer(op_layer),
        .tx_beat(c_q_beat), .tx_expected_beat(c_tb), .tx_data(c_q_data), .tx_valid(c_tv[0]), .tx_payload(c_tp[0 +: FW]),
        .rx_event(c_rxe[0]), .rx_expected(c_rxs[0]), .rx_payload(c_rxp), .rx_expected_kind(c_rk),
        .rx_expected_epoch(op_epoch), .rx_expected_layer(op_layer), .rx_expected_beat(c_rb),
        .rx_valid(ca_rv), .rx_kind(ca_rk), .rx_epoch(ca_re), .rx_layer(ca_rl), .rx_beat(ca_rb), .rx_data(ca_rd),
        .fault(ca_f), .fault_cause(ca_fc));
    qkd_native_attention_record #(.KV_SIDE(1)) u_ka (.ck(ck), .rst_n(rst_n & ~k_eb),
        .tx_event(k_r_ev), .tx_expected(k_txs[0]), .tx_kind(k_r_kind), .tx_expected_kind(k_tk),
        .tx_epoch(op_epoch), .tx_expected_epoch(op_epoch), .tx_layer(op_layer), .tx_expected_layer(op_layer),
        .tx_beat(k_r_beat), .tx_expected_beat(k_tb), .tx_data(k_r_data), .tx_valid(k_tv[0]), .tx_payload(k_tp[0 +: FW]),
        .rx_event(k_rxe[0]), .rx_expected(k_rxs[0]), .rx_payload(k_rxp), .rx_expected_kind(k_rk),
        .rx_expected_epoch(op_epoch), .rx_expected_layer(op_layer), .rx_expected_beat(k_rb),
        .rx_valid(ka_rv), .rx_kind(ka_rk), .rx_epoch(ka_re), .rx_layer(ka_rl), .rx_beat(ka_rb), .rx_data(ka_rd),
        .fault(ka_f), .fault_cause(ka_fc));
    // kind-15 status: compute levels/result (stimulus), compute encoder (port 2) -> KV decoder (port 2)
    wire st_res = lay >= 0 && rel == 20;
    wire cs_f, ks_f, s_vm, s_co, s_cb, s_cf, s_ea, s_ar, s_fr, s_rv, s_rd, s_rf; wire [3:0] s_rc; wire [58:0] s_rt;
    wire [1:0] s_rg; wire [17:0] s_rtok; wire [31:0] s_rval, s_rcyc;
    assign c_tv[1] = 1'b0; assign c_tp[FW +: FW] = 0; assign c_tv[3] = 1'b0; assign c_tp[3*FW +: FW] = 0;
    assign k_tv[3:1] = 3'b0; assign k_tp[4*FW-1:FW] = 0;
    ot_qwen_d2d_status_tx u_cst (.ck(ck), .rst_n(rst_n & ~c_eb), .epoch16(op_epoch),
        .vm_drained(lay[0]), .collective_drained(~lay[0]), .collective_busy(lay[1]), .crom_fault(1'b0),
        .execution_active(1'b1), .admit_ready(lay[0] ^ lay[1]),
        .result_v(st_res), .result_done(1'b1), .result_fault(1'b0), .result_cause(4'd0), .result_tag(59'(lay * 4093 + 11)),
        .result_gen(2'(lay)), .result_token(18'(lay * 1001)), .result_value(32'(lay * 77)), .result_cycles(32'(lay * 1052)),
        .tx_slot(c_txs[2]), .tx_kind(c_tk), .tx_valid(c_tv[2]), .tx_payload(c_tp[2*FW +: FW]), .fault(cs_f));
    ot_qwen_d2d_status_rx u_kst (.ck(ck), .rst_n(rst_n), .epoch16(op_epoch), .rx_event(k_rxe[2]), .rx_slot(k_rxs[2]),
        .rx_payload(k_rxp), .vm_drained(s_vm), .collective_drained(s_co), .collective_busy(s_cb), .crom_fault(s_cf),
        .execution_active(s_ea), .admit_ready(s_ar), .status_fresh(s_fr), .result_v(s_rv), .result_done(s_rd),
        .result_fault(s_rf), .result_cause(s_rc), .result_tag(s_rt), .result_gen(s_rg), .result_token(s_rtok),
        .result_value(s_rval), .result_cycles(s_rcyc), .epoch_begin(k_eb), .fault(ks_f));
    // HOST link services (KV die)
    wire [1:0] h_lu; wire [7:0] h_tf; wire h_ld, h_ls, h_rt; wire [3:0] h_ad;
    wire h_kvd, h_vmd, h_cod, h_hd, h_cb, h_kf, h_ar, h_cf, h_ea, h_wv, h_rxv; wire [1:0] h_sk; wire [547:0] h_rx;
    qkd_host_link_services #(.NL(2)) u_hls (.ck(ck), .rst_n(rst_n),
        .d2d_link_up(k_lu), .serdes_up(1'b1), .d2d_transport_fault(k_tf), .d2d_links_drained(k_dr),
        .d2d_link_reset_seen(k_seen), .d2d_retrained(k_rt),
        .rec_tx_slot(k_txs[1]), .rec_tx_kind(k_tk), .rec_tx_beat(k_tb), .rec_rx_event(k_rxe[1]), .rec_rx_slot(k_rxs[1]),
        .rx_payload(k_rxp), .c_vm_drained(s_vm), .c_collective_drained(s_co), .c_collective_busy(s_cb),
        .c_crom_fault(s_cf), .c_execution_active(s_ea), .c_admit_ready(s_ar), .c_status_fresh(MUT == 5 ? 1'b1 : s_fr),
        .kv_drained_local(1'b1), .kv_flush_local(1'b0), .host_drained_local(1'b1), .kv_active_local(1'b0),
        .link_up(h_lu), .transport_fault(h_tf), .native_links_drained(h_ld), .native_link_reset_seen(h_ls),
        .native_retrained(h_rt), .abort_drained(h_ad), .native_kv_drained(h_kvd), .native_vm_drained(h_vmd),
        .native_collective_drained(h_cod), .native_host_drained(h_hd), .native_collective_busy(h_cb),
        .native_kv_flush(h_kf), .native_admit_ready(h_ar), .crom_fault(h_cf), .execution_active(h_ea),
        .record_send_kind(h_sk), .record_witness_slot(h_wv), .record_rx_v(h_rxv), .record_rx(h_rx));

    always @(negedge ck) corrupt <= bad_armed && lay >= 0 && rel == 3 + 7 + TXL;
    // ---------------- exact-cycle checks ----------------
    integer errs = 0, frames_ck = 0, frames_kc = 0, statuses = 0, results = 0, normal_aborts = 0;
    integer aborted_layer = -1;
    reg first_after_eb = 0;
    always @(posedge ck) if (lay >= 0 && rst_n) begin
        // compute codec output at arrival + 3 (end rx at +2, codec register +1): RESULT beats + STATUS
        if (ca_rv) begin
            if (!((rel - 3 - TXL - PHY >= 50 && rel - 3 - TXL - PHY < 82) || rel - 3 - TXL - PHY == 83)) begin
                errs = errs + 1; $display("ERR compute rx at unplanned rel %0d", rel); end
            else if (ca_rd !== (rel - 3 - TXL - PHY == 83 ? {507'd0, 5'b01001} : word(lay, 3, rel - 3 - TXL - PHY - 50))) begin
                errs = errs + 1; $display("ERR compute rx data rel %0d", rel); end
            else if (aborted_layer != lay) frames_kc = frames_kc + 1;
        end
        if (ka_rv) begin
            if (!(rel - 3 - TXL - PHY >= 2 && rel - 3 - TXL - PHY < 35)) begin errs = errs + 1; $display("ERR kv rx unplanned rel %0d", rel); end
            else if (ka_rd !== (rel - 3 - TXL - PHY == 2 ? {493'd0, 5'd0, 13'(lay * 7 + 5), 1'b1} : word(lay, 2, rel - 3 - TXL - PHY - 3))) begin
                errs = errs + 1; $display("ERR kv rx data rel %0d", rel); end
            else if (aborted_layer != lay) frames_ck = frames_ck + 1;
        end
        if (s_rv) begin
            if (rel != 40 + TXL + PHY + 3 || s_rtok !== 18'(lay * 1001) || s_rval !== 32'(lay * 77) ||
                s_rcyc !== 32'(lay * 1052) || s_rt !== 59'(lay * 4093 + 11) || s_rg !== 2'(lay) || !s_rd) begin
                errs = errs + 1; $display("ERR status result rel %0d tok %0d", rel, s_rtok); end
            else if (aborted_layer != lay) results = results + 1;
        end
        if (rel == P - 2 && aborted_layer != lay) begin
            if (h_vmd !== lay[0] || h_cod !== ~lay[0] || h_cb !== lay[1] || h_ar !== (lay[0] ^ lay[1]) || !h_ea ||
                h_ad !== {1'b1, ~lay[0], lay[0], 1'b1} || h_lu !== 2'b11 || h_tf !== 0) begin
                errs = errs + 1; $display("ERR host services lay %0d vm%b co%b cb%b ar%b ad%b lu%b", lay, h_vmd, h_cod, h_cb, h_ar, h_ad, h_lu); end
            else statuses = statuses + 1;
        end
        // right after an epoch begin, the collector must not report stale compute drains as drained
        if (rel == 5 && first_after_eb && (h_vmd || h_cod || h_ar)) begin errs = errs + 1; $display("ERR stale status reported drained lay %0d", lay); end
        if (aborted_layer != lay && (ca_f || ka_f || cs_f || ks_f || c_abort || k_abort || c_endf || k_endf)) begin
            normal_aborts = normal_aborts + 1;
            if (normal_aborts < 4) $display("ERR fault in normal epoch lay %0d rel %0d ca%0d ka%0d cs%0d ks%0d cab%0d/%h kab%0d/%h endf %0d%0d",
                lay, rel, ca_f, ka_f, cs_f, ks_f, c_abort, c_fc, k_abort, k_fc, c_endf, k_endf);
        end
    end

    // ---------------- sequence ----------------
    integer l, i, t0, rec_kv = 0, rec_c = 0, tbad = -1;
    task tick(input integer n); repeat (n) @(negedge ck); endtask
    task run_layer(input integer L);
        begin
            $display("layer %0d start cyc %0d epoch %0d/%0d", L, cyc + 1, c_ep, k_ep);
            lay = L; lstart = cyc + 1; cstart = 1; first_after_eb = (L == 0) || (aborted_layer == 99 && L == BAD_LAYER); tick(1); cstart = 0; tick(P - 1);
        end
    endtask
    initial begin
        $readmemh({CALDIR, "/cal_C_tx.memh"}, img_ct); $readmemh({CALDIR, "/cal_C_rx.memh"}, img_cr);
        $readmemh({CALDIR, "/cal_K_tx.memh"}, img_kt); $readmemh({CALDIR, "/cal_K_rx.memh"}, img_kr);
        tick(3); por_n = 1; tick(3); rst_n = 1; tick(2);
        // init mode: calendar images through the cfg port (both dies' control-image loaders)
        for (i = 0; i < 128; i = i + 1) begin
            cfg_a = i; cfg_dc = img_ct[i]; cfg_dk = img_kt[i]; cfg_c_tx = 1; cfg_k_tx = 1; tick(1);
            cfg_c_tx = 0; cfg_k_tx = 0; cfg_dc = img_cr[i]; cfg_dk = img_kr[i]; cfg_c_rx = 1; cfg_k_rx = 1; tick(1);
            cfg_c_rx = 0; cfg_k_rx = 0;
        end
        wait (k_up && c_up); tick(2);
        host_boot = 1; tick(1); host_boot = 0; wait (k_eb); tick(10);
        if (!(c_ep == k_ep && c_ep == 1)) begin errs = errs + 1; $display("ERR boot epochs %0d %0d", c_ep, k_ep); end
        for (l = 0; l < NLAY; l = l + 1) begin
            if (l == BAD_LAYER && aborted_layer < 0) begin
                // exceptional episode: one corrupted bit on C->S Q beat 7 of this layer
                aborted_layer = l; bad_armed = 1;
                run_layer(l);
                if (!(k_abort && c_abort && k_tf[0] && c_tf[2])) begin errs = errs + 1;
                    $display("ERR expected KV crc abort + compute missing abort: k%0d/%h c%0d/%h", k_abort, k_tf, c_abort, c_tf); end
                bad_armed = 0; t0 = cyc;
                $display("abort at cyc %0d", cyc);
                wait (h_ld); $display("drained %0d", cyc); host_reset_req = 1; wait (h_ls); host_reset_req = 0;
                $display("reset seen %0d", cyc); wait (h_rt); $display("retrained %0d", cyc); tick(2);
                if (h_lu[0]) begin errs = errs + 1; $display("ERR link_up during recovery"); end
                host_clear = 1; tick(1); host_clear = 0; wait (k_eb); tick(10);
                rec_kv = k_rcyc; rec_c = c_rcyc;
                if (!(c_ep == k_ep && k_ep == 2) || h_tf !== 0 || !h_lu[0]) begin errs = errs + 1;
                    $display("ERR after recovery epochs %0d %0d tf %h lu %b", c_ep, k_ep, h_tf, h_lu); end
                $display("RECOVERY abort->epoch_begin KV %0d cycles, compute %0d cycles; HOST-visible %0d cycles", rec_kv, rec_c, cyc - t0);
                l = l - 1;   // HOST replays the aborted layer
                aborted_layer = 99;
            end else run_layer(l);
        end
        lay = -1; tick(20);
        $display("frames C->S %0d S->C %0d results %0d host-checks %0d normal-epoch faults %0d errors %0d",
            frames_ck, frames_kc, results, statuses, normal_aborts, errs);
        if (errs == 0 && normal_aborts == 0 && frames_ck == 33 * NLAY && frames_kc == 33 * NLAY && results == NLAY)
            $display("D2D_STATIC_PASS");
        else $display("D2D_STATIC_FAIL");
        $finish;
    end
    initial begin #20000; $display("D2D_STATIC_FAIL timeout"); $finish; end
endmodule
