`timescale 1ns/1ps
// Q-LINK 2026-10-15 DIE-NAME bench (qfd_d2d_static + qkd_d2d_static, as bound in the die netlists). Derived from
// tb_qwen_d2d_static; adds the KVN path (real qfd_kvn_static_transport -> kind 5 -> KV writer face). Component bench: compute-die end + KV/system-die end of the static D2D link through a behavioural
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
module tb_qwen_d2d_dies;
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

    reg host_reset_req = 0, host_clear = 0, host_boot = 0;
    wire fwd_ep, fwd_lrst_n; reg [2:0] bump_ep = 0, bump_lr = 3'b111;
    always @(posedge ck) begin bump_ep <= {bump_ep, fwd_ep}; bump_lr <= {bump_lr, fwd_lrst_n}; end
    integer lay = -1, lstart = 0;
    reg cstart = 0;
    wire c_txs0, c_rxe0, c_rxs0, k_txs0, k_rxe0, k_rxs0; wire [3:0] c_tk, k_tk, c_rk, k_rk; wire [4:0] c_tb, k_tb, c_rb, k_rb;
    wire [FW-1:0] c_rxp, k_rxp; wire c_tv0, k_tv0; wire [FW-1:0] c_tp0, k_tp0;
    wire c_abort, k_abort, c_f, k_f; wire [7:0] c_tf, h_tf; wire [31:0] k_rcyc;
    wire [1:0] h_lu; wire h_ld, h_ls, h_rt; wire [3:0] h_ad;
    wire h_kvd, h_vmd, h_cod, h_hd, h_cb, h_kf, h_ar, h_cf, h_ea, h_wv, h_rxv; wire [1:0] h_sk; wire [547:0] h_rx;
    wire s_rv, s_rd, s_rf; wire [3:0] s_rc; wire [58:0] s_rt; wire [1:0] s_rg; wire [17:0] s_rtok; wire [31:0] s_rval, s_rcyc;
    wire kv_x3_slot; wire [523:0] x3; wire [58:0] x3_id; wire [1:0] x3_gen; wire kvt_f;
    wire kw_v, kw_slot; wire [10:0] kw_tag; wire [511:0] kw_data; wire [58:0] kw_id; wire [1:0] kw_gen, kw_idx;
    wire [15:0] op_epoch = 16'h0400 + lay[15:0];
    wire [5:0]  op_layer = 6'(lay % 36);
    wire [58:0] op_tag = {op_epoch, op_layer + 6'd1, 18'd4242, 13'd77, 6'd0};
    wire st_res;
    wire c_eb = u_c.eb, k_eb = u_k.eb; wire [7:0] c_ep = u_c.ep, k_ep = u_k.ep;
    qfd_d2d_static #(.MUT(MUT == 1 ? 1 : 0)) u_c (.ck({5{ck}}), .por_n(por_n), .rst_n(rst_n),
        .cfg_tx_we(cfg_c_tx), .cfg_rx_we(cfg_c_rx), .cfg_addr(cfg_a), .cfg_data(cfg_dc), .cal_start(cstart),
        .fwd_epoch(bump_ep[2]), .fwd_link_rst_n(bump_lr[2]),
        .native_tx_slot(c_txs0), .native_tx_slot_kind(c_tk), .native_tx_slot_beat(c_tb), .native_tx_v(c_tv0),
        .native_tx_payload(c_tp0), .native_rx_v(c_rxe0), .native_rx_payload(c_rxp), .native_rx_slot(c_rxs0),
        .native_rx_slot_kind(c_rk), .native_rx_slot_beat(c_rb),
        .prog_witness_slot(), .prog_auth_slot(), .prog_context_slot(), .prog_tx_observed_v(1'b0), .prog_tx_record(548'd0),
        .prog_rx_v(), .prog_rx_record(),
        .kv_x3_slot(kv_x3_slot), .x3(x3), .x3_identity(x3_id), .x3_generation(x3_gen),
        .status_epoch16(op_epoch), .vm_drained(lay[0]), .collective_drained(~lay[0]), .collective_busy(lay[1]),
        .crom_fault(1'b0), .execution_active(1'b1), .admit_ready(lay[0] ^ lay[1]),
        .result_v(st_res), .result_done(1'b1), .result_fault(1'b0), .result_cause(4'd0), .result_tag(59'(lay * 4093 + 11)),
        .result_gen(2'(lay)), .result_token(18'(lay * 1001)), .result_value(32'(lay * 77)), .result_cycles(32'(lay * 1052)),
        .fdi_tx_up(c_up), .fdi_tx_v(c_ptx_v), .fdi_tx_flit(c_ptx), .fdi_rx_v(c_prx_v), .fdi_rx_flit(c_prx),
        .phy_rst_n(c_phy_rst_n), .epoch_abort(c_abort), .transport_fault(c_tf), .fault(c_f));
    qkd_d2d_static #(.MUT(MUT == 2 ? 2 : 0)) u_k (.ck({5{ck}}), .por_n(por_n), .rst_n(rst_n),
        .cfg_tx_we(cfg_k_tx), .cfg_rx_we(cfg_k_rx), .cfg_addr(cfg_a), .cfg_data(cfg_dk), .cal_start(cstart),
        .host_link_reset_req(host_reset_req), .host_recovery_clear(host_clear), .host_boot_begin(host_boot),
        .fwd_epoch(fwd_ep), .fwd_link_rst_n(fwd_lrst_n),
        .att_tx_slot(k_txs0), .att_tx_kind(k_tk), .att_tx_beat(k_tb), .att_tx_v(k_tv0), .att_tx_payload(k_tp0),
        .att_rx_v(k_rxe0), .att_rx_slot(k_rxs0), .att_rx_kind(k_rk), .att_rx_beat(k_rb), .rx_payload(k_rxp),
        .record_tx_observed_v(1'b0), .record_tx(548'd0), .record_send_kind(h_sk), .record_witness_slot(h_wv),
        .record_rx_v(h_rxv), .record_rx(h_rx),
        .kvn_compiled_identity(op_tag), .kvn_compiled_generation(2'(lay)),
        .kvn_word_valid(kw_v), .kvn_word_tag(kw_tag), .kvn_word_data(kw_data), .kvn_word_identity(kw_id),
        .kvn_word_generation(kw_gen), .kvn_word_slot(kw_slot), .kvn_word_index(kw_idx),
        .status_epoch16(op_epoch), .serdes_up(1'b1), .kv_drained_local(1'b1), .kv_flush_local(1'b0),
        .host_drained_local(1'b1), .kv_active_local(1'b0),
        .link_up(h_lu), .transport_fault(h_tf), .native_links_drained(h_ld), .native_link_reset_seen(h_ls),
        .native_retrained(h_rt), .abort_drained(h_ad), .native_kv_drained(h_kvd), .native_vm_drained(h_vmd),
        .native_collective_drained(h_cod), .native_host_drained(h_hd), .native_collective_busy(h_cb),
        .native_kv_flush(h_kf), .native_admit_ready(h_ar), .crom_fault(h_cf), .execution_active(h_ea),
        .engine_result_v(s_rv), .engine_result_done(s_rd), .engine_result_fault(s_rf), .engine_result_cause(s_rc),
        .engine_result_tag(s_rt), .engine_result_gen(s_rg), .engine_result_token(s_rtok),
        .engine_result_value(s_rval), .engine_result_cycles(s_rcyc),
        .fdi_tx_up(k_up), .fdi_tx_v(k_ptx_v), .fdi_tx_flit(k_ptx), .fdi_rx_v(k_prx_v), .fdi_rx_flit(k_prx),
        .phy_rst_n(k_phy_rst_n), .epoch_abort(k_abort), .recovery_cycles(k_rcyc), .fault(k_f));
    // real KVN producer: the compute die's fixed-slot KVN transport (2 seats), words pushed 1 cycle before their slot
    wire kvn_push = lay >= 0 && rel >= 41 && rel < 45;
    qfd_kvn_static_transport u_kvt (.ck(ck), .rst_n(rst_n & ~c_eb), .word_v(kvn_push), .word_tag({3'd2, 8'(rel - 41)}),
        .word_data(word(lay, 5, rel - 41)), .word_identity(op_tag), .word_generation(2'(lay)), .slot_v(kv_x3_slot),
        .x3(x3), .x3_identity(x3_id), .x3_generation(x3_gen), .fault(kvt_f));
    integer kvn_ok = 0;
    // ---------------- producers (stimulus schedule = the compiled send cycles of the bench layer profile) ----------
    function automatic [511:0] word(input integer l, input integer k, input integer b);
        integer i; begin for (i = 0; i < 16; i = i + 1) word[i*32 +: 32] = 32'h9e3779b9 * (l * 997 + k * 131 + b * 17 + i + 1); end
    endfunction
    integer rel; always @* rel = cyc - lstart;
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
        .tx_event(c_q_ev), .tx_expected(c_txs0), .tx_kind(c_q_kind), .tx_expected_kind(c_tk),
        .tx_epoch(op_epoch), .tx_expected_epoch(op_epoch), .tx_layer(op_layer), .tx_expected_layer(op_layer),
        .tx_beat(c_q_beat), .tx_expected_beat(c_tb), .tx_data(c_q_data), .tx_valid(c_tv0), .tx_payload(c_tp0),
        .rx_event(c_rxe0), .rx_expected(c_rxs0), .rx_payload(c_rxp), .rx_expected_kind(c_rk),
        .rx_expected_epoch(op_epoch), .rx_expected_layer(op_layer), .rx_expected_beat(c_rb),
        .rx_valid(ca_rv), .rx_kind(ca_rk), .rx_epoch(ca_re), .rx_layer(ca_rl), .rx_beat(ca_rb), .rx_data(ca_rd),
        .fault(ca_f), .fault_cause(ca_fc));
    qkd_native_attention_record #(.KV_SIDE(1)) u_ka (.ck(ck), .rst_n(rst_n & ~k_eb),
        .tx_event(k_r_ev), .tx_expected(k_txs0), .tx_kind(k_r_kind), .tx_expected_kind(k_tk),
        .tx_epoch(op_epoch), .tx_expected_epoch(op_epoch), .tx_layer(op_layer), .tx_expected_layer(op_layer),
        .tx_beat(k_r_beat), .tx_expected_beat(k_tb), .tx_data(k_r_data), .tx_valid(k_tv0), .tx_payload(k_tp0),
        .rx_event(k_rxe0), .rx_expected(k_rxs0), .rx_payload(k_rxp), .rx_expected_kind(k_rk),
        .rx_expected_epoch(op_epoch), .rx_expected_layer(op_layer), .rx_expected_beat(k_rb),
        .rx_valid(ka_rv), .rx_kind(ka_rk), .rx_epoch(ka_re), .rx_layer(ka_rl), .rx_beat(ka_rb), .rx_data(ka_rd),
        .fault(ka_f), .fault_cause(ka_fc));
    assign st_res = lay >= 0 && rel == 20;
    wire c_endf = c_f, k_endf = k_f, cs_f = 1'b0, ks_f = 1'b0;
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
        if (kw_v) begin
            if (rel != 42 + (kw_idx) + 2 - 1 + TXL + PHY + 3 || kw_tag !== {3'd2, 8'(kw_idx)} || kw_data !== word(lay, 5, kw_idx) ||
                kw_id !== op_tag || kw_gen !== 2'(lay) || !kw_slot) begin
                errs = errs + 1; $display("ERR kvn word rel %0d idx %0d", rel, kw_idx); end
            else if (aborted_layer != lay) kvn_ok = kvn_ok + 1;
        end
        if (rel == P - 2 && aborted_layer != lay) begin
            if (h_vmd !== lay[0] || h_cod !== ~lay[0] || h_cb !== lay[1] || h_ar !== (lay[0] ^ lay[1]) || !h_ea ||
                h_ad !== {1'b1, ~lay[0], lay[0], 1'b1} || h_lu !== 2'b11 || h_tf !== 0) begin
                errs = errs + 1; $display("ERR host services lay %0d vm%b co%b cb%b ar%b ad%b lu%b", lay, h_vmd, h_cod, h_cb, h_ar, h_ad, h_lu); end
            else statuses = statuses + 1;
        end
        // right after an epoch begin, the collector must not report stale compute drains as drained
        if (rel == 5 && first_after_eb && (h_vmd || h_cod || h_ar)) begin errs = errs + 1; $display("ERR stale status reported drained lay %0d", lay); end
        if (aborted_layer != lay && (ca_f || ka_f || c_abort || k_abort || c_f || k_f || kvt_f)) begin
            normal_aborts = normal_aborts + 1;
            if (normal_aborts < 4) $display("ERR fault in normal epoch lay %0d rel %0d ca%0d ka%0d cs%0d ks%0d cab%0d/%h kab%0d/%h endf %0d%0d",
                lay, rel, ca_f, ka_f, kvt_f, 1'b0, c_abort, c_tf, k_abort, h_tf, c_f, k_f);
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
                if (!(k_abort && c_abort && h_tf[0] && c_tf[2])) begin errs = errs + 1;
                    $display("ERR expected KV crc abort + compute missing abort: k%0d/%h c%0d/%h", k_abort, h_tf, c_abort, c_tf); end
                bad_armed = 0; t0 = cyc;
                $display("abort at cyc %0d", cyc);
                wait (h_ld); $display("drained %0d", cyc); host_reset_req = 1; wait (h_ls); host_reset_req = 0;
                $display("reset seen %0d", cyc); wait (h_rt); $display("retrained %0d", cyc); tick(2);
                if (h_lu[0]) begin errs = errs + 1; $display("ERR link_up during recovery"); end
                host_clear = 1; tick(1); host_clear = 0; wait (k_eb); tick(10);
                rec_kv = k_rcyc; rec_c = 0;
                if (!(c_ep == k_ep && k_ep == 2) || h_tf !== 0 || !h_lu[0]) begin errs = errs + 1;
                    $display("ERR after recovery epochs %0d %0d tf %h lu %b", c_ep, k_ep, h_tf, h_lu); end
                $display("RECOVERY abort->epoch_begin KV %0d cycles, compute %0d cycles; HOST-visible %0d cycles", rec_kv, rec_c, cyc - t0);
                l = l - 1;   // HOST replays the aborted layer
                aborted_layer = 99;
            end else run_layer(l);
        end
        lay = -1; tick(20);
        $display("frames C->S %0d S->C %0d kvn %0d results %0d host-checks %0d normal-epoch faults %0d errors %0d",
            frames_ck, frames_kc, kvn_ok, results, statuses, normal_aborts, errs);
        if (errs == 0 && normal_aborts == 0 && frames_ck == 33 * NLAY && frames_kc == 33 * NLAY && kvn_ok == 4 * NLAY && results == NLAY)
            $display("D2D_DIES_PASS");
        else $display("D2D_DIES_FAIL");
        $finish;
    end
    initial begin #20000; $display("D2D_DIES_FAIL timeout"); $finish; end
endmodule
