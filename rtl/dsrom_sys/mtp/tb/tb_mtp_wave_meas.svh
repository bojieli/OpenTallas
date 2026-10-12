    // tb_mtp_wave measurement probes + report (included in tb_mtp_wave).  Every charge is measured at the same start / end
    // events as its price formula (results/arch/mtp_step_20261009/ds_rom_step.json); times are fast cycles (1.2 GHz).
    // ---- dedicated MTP lane adapters: TX = die-side pin valid -> lane flit launch, RX = lane landing -> consumer link valid
    integer lt_in [0:1023], lt_lo [0:1023], lt_li [0:1023]; integer lt_ni = 0, lt_nlo = 0, lt_nli = 0, lt_nrt = 0;
    integer ls_in [0:255], ls_lo [0:255], ls_li [0:255]; integer ls_ni = 0, ls_nlo = 0, ls_nli = 0, ls_nrs = 0;
    integer lt_tx = 0, lt_rx = 0, ls_tx = 0, ls_rx = 0;
    always @(posedge fclk) if (rst_n) begin
        if (s_tv) begin lt_in[lt_ni % 1024] = cyc; lt_ni = lt_ni + 1; end
        if (hT_lov && hT_lod[551:549] == 3'd1) begin lt_tx = lt_tx + (cyc - lt_in[lt_nlo % 1024]); lt_nlo = lt_nlo + 1; end
        if (sT_liv && sT_lid[551:549] == 3'd1) begin lt_li[lt_nli % 1024] = cyc; lt_nli = lt_nli + 1; end
        if (sT_rtv) begin lt_rx = lt_rx + (cyc - lt_li[lt_nrt % 1024]); lt_nrt = lt_nrt + 1; end
        if (s_sv) begin ls_in[ls_ni % 256] = cyc; ls_ni = ls_ni + 1; end
        if (hS_lov && hS_lod[551:549] == 3'd2) begin ls_tx = ls_tx + (cyc - ls_in[ls_nlo % 256]); ls_nlo = ls_nlo + 1; end
        if (pS_liv && pS_lid[551:549] == 3'd2) begin ls_li[ls_nli % 256] = cyc; ls_nli = ls_nli + 1; end
        if (pS_rsv) begin ls_rx = ls_rx + (cyc - ls_li[ls_nrs % 256]); ls_nrs = ls_nrs + 1; end
    end
    // ---- P2 lane adapters: start (primary TX, die A RX) and the last result row (die A TX 2nd beat, primary RX)
    integer ps_acc = -1, ps_tx = 0, ps_rx = 0, ps_n = 0, ps_li = -1, pr_x = -1, pr_tx = 0, pr_rx = 0, pr_n = 0, pr_li = -1;
    integer a_rowacc = 0, a_seg1 = 0, p_seg1 = 0, p_rowsn = 0;
    always @(posedge fclk) if (rst_n) begin
        if (ps_v && ps_r) ps_acc = cyc;
        if (pP_lov && pP_lod[551:549] == 3'd6 && ps_acc >= 0) begin ps_tx = ps_tx + (cyc - ps_acc); ps_acc = -1; end
        if (aP_liv && aP_lid[551:549] == 3'd6) ps_li = cyc;
        if (a_sv && a_sr && ps_li >= 0) begin ps_rx = ps_rx + (cyc - ps_li); ps_n = ps_n + 1; ps_li = -1; end
        if (a_ov && a_or) begin a_rowacc = a_rowacc + 1; if (a_rowacc % 80 == 0) pr_x = cyc; end
        if (aP_lov && aP_lod[551:549] == 3'd7 && aP_lod[548]) begin
            a_seg1 = a_seg1 + 1; if (a_seg1 % 80 == 0 && pr_x >= 0) begin pr_tx = pr_tx + (cyc - pr_x); pr_x = -1; end
        end
        if (pP_liv && pP_lid[551:549] == 3'd7 && pP_lid[548]) begin p_seg1 = p_seg1 + 1; if (p_seg1 % 80 == 0) pr_li = cyc; end
        if (pr_rv) begin p_rowsn = p_rowsn + 1; if (p_rowsn % 80 == 0 && pr_li >= 0) begin pr_rx = pr_rx + (cyc - pr_li); pr_n = pr_n + 1; pr_li = -1; end end
    end
    // ---- in-loop P2 transaction (primary start accept -> last row at the primary), for the record
    integer p2l_t0 = -1, p2l_sum = 0, p2l_n = 0;
    always @(posedge fclk) if (rst_n) begin
        if (ps_v && ps_r) p2l_t0 = cyc;
        if (pr_rv && p_rowsn % 80 == 79 && p2l_t0 >= 0) begin p2l_sum = p2l_sum + (cyc - p2l_t0); p2l_n = p2l_n + 1; p2l_t0 = -1; end
    end
    // ---- seed launch: descriptor at the pin -> first x beat, x done at the pin -> next row's first beat / program start
    integer sl_d = -1, sl_x1 = 0, sl_gd = -1, sl_sum [0:63], sl_rows [0:63], sl_nd = 0, sl_d2x = 0, sl_d2p = 0, sl_gap = 0, sl_ng = 0;
    always @(posedge fclk) if (rst_n) begin
        if (sl_mrs[0] && sl_d < 0) begin sl_d = cyc; sl_x1 = 1; sl_sum[sl_nd % 64] = 0; sl_rows[sl_nd % 64] = 0; end
        if (t_x[0] && sl_x1 && sl_d >= 0) begin sl_sum[sl_nd % 64] = sl_sum[sl_nd % 64] + (cyc - sl_d); if (sl_nd > 0) sl_d2x = sl_d2x + (cyc - sl_d); sl_x1 = 0; end
        if (t_x[0] && sl_gd >= 0) begin sl_sum[sl_nd % 64] = sl_sum[sl_nd % 64] + (cyc - sl_gd); if (sl_nd > 0) begin sl_gap = sl_gap + (cyc - sl_gd); sl_ng = sl_ng + 1; end sl_gd = -1; end
        if (f_x[1]) begin sl_gd = cyc; sl_rows[sl_nd % 64] = sl_rows[sl_nd % 64] + 1; end
        if (t_ps[0] && sl_gd >= 0) begin
            sl_sum[sl_nd % 64] = sl_sum[sl_nd % 64] + (cyc - sl_gd); if (sl_nd > 0) sl_d2p = sl_d2p + (cyc - sl_gd);
            sl_gd = -1; sl_d = -1; sl_nd = sl_nd + 1;
        end
    end
    // ---- hrow transport: header launched at the stage-die pin -> last flit through the part receiver + store write (+1)
    integer hrw_t [1:3][0:4095]; integer hrw_n [1:3]; integer hrw_m [1:3]; integer hrw_sum = 0, hrw_cnt = 0, hp_i;
    initial for (hp_i = 1; hp_i <= 3; hp_i = hp_i + 1) begin hrw_n[hp_i] = 0; hrw_m[hp_i] = 0; end
    always @(posedge fclk) if (rst_n) begin
        for (hp_i = 1; hp_i <= 3; hp_i = hp_i + 1) begin
            if (h_lv[hp_i] && h_ld[hp_i][513]) begin hrw_t[hp_i][hrw_n[hp_i] % 4096] = cyc; hrw_n[hp_i] = hrw_n[hp_i] + 1; end
            if (u_hr.pv[hp_i-1] && u_hr.pr[hp_i-1] && !u_hr.pd[514*(hp_i-1) + 513] && u_hr.pd[514*(hp_i-1) + 512]) begin
                hrw_sum = hrw_sum + (cyc + 1 - hrw_t[hp_i][hrw_m[hp_i] % 4096] - PF); hrw_cnt = hrw_cnt + 1; hrw_m[hp_i] = hrw_m[hp_i] + 1;
            end
        end
    end
    // ---- draft-head step receiver: seq pin data at the VM end (f_hv) -> core-side valid, vs the OUTPUT_PIPE 0 reference
    integer ep_t = -1, ep_sum = 0, ep_n = 0, rf_sum = 0, rf_n = 0;
    always @(posedge fclk) if (rst_n) begin
        if (s_hv) ep_t = cyc;
        if (rf_hv && ep_t >= 0) begin rf_sum = rf_sum + (cyc - ep_t); rf_n = rf_n + 1; end
        if (bh_v && ep_t >= 0) begin ep_sum = ep_sum + (cyc - ep_t); ep_n = ep_n + 1; end
    end
    // ---- history rings: read acceptance -> last streamed token (per ring)
    integer hq0 [0:63], hq1 [0:63], h0w = 0, h0r = 0, h1w = 0, h1r = 0, h0k = 0, h1k = 0, h0s = 0, h1s = 0, h0n = 0, h1n = 0;
    integer h0t [0:63], h1t [0:63], h0e, h1e;
    always @(posedge fclk) if (rst_n) begin
        if (u_h0.rd_v && h0_rdy) begin hq0[h0w % 64] = hr_pos; h0t[h0w % 64] = cyc; h0w = h0w + 1; end
        if (u_h1.rd_v && h1_rdy) begin hq1[h1w % 64] = hr_pos; h1t[h1w % 64] = cyc; h1w = h1w + 1; end
        if (h0_v) begin
            h0e = hq0[h0r % 64] - h0k;
            if (!h0_pad && h0_tok !== 17'((h0e <= h_pass_q) ? tru[h0e] : h_tok[h0e])) begin $display("WAVE FAIL: hist_ring read %0d k %0d got %0d exp %0d (q %0d) at %0d", hq0[h0r % 64], h0k, h0_tok, (h0e <= h_pass_q) ? tru[h0e] : h_tok[h0e], h_pass_q, cyc); errs = errs + 1; end
            if (h0_pad != (h0e < 0)) begin $display("WAVE FAIL: hist_ring pad"); errs = errs + 1; end
            if (h0_last) begin h0s = h0s + (cyc - h0t[h0r % 64]); h0n = h0n + 1; h0r = h0r + 1; h0k = 0; end else h0k = h0k + 1;
        end
        if (h1_v) begin
            h1e = hq1[h1r % 64] - h1k;
            if (!h1_pad && h1_tok !== 17'((h1e <= h_pass_q) ? tru[h1e] : h_tok[h1e])) begin $display("WAVE FAIL: hist_ring_p read %0d k %0d", hq1[h1r % 64], h1k); errs = errs + 1; end
            if (h1_pad != (h1e < 0)) begin $display("WAVE FAIL: hist_ring_p pad"); errs = errs + 1; end
            if (h1_last) begin h1s = h1s + (cyc - h1t[h1r % 64]); h1n = h1n + 1; h1r = h1r + 1; h1k = 0; end else h1k = h1k + 1;
        end
    end

    // ---- report: one WAVE_CHARGE line per charge (price = ds_rom_step.json, measured = this bench, same events)
    function automatic real avg(input integer s, input integer n); avg = n > 0 ? 1.0 * s / n : -1.0; endfunction
    task report;
        integer j, d, nh, sh, sh2, ni, si, bf, ideal, sp, pp, n2;
        real hop, itv, x;
        begin
            bf = (T_BUSY * 4 + 1) / 3;
            ideal = 2 * S_L + 47 + 1;   // header + the TXW 46 outbound words a stage sends (the composed model's serialised hop)
            // wfc_kit.ar_pass: stage done (core op done at dsfd_stage_seq) -> next stage's core op command, minus the ideal hop
            nh = 0; sh = 0;
            for (j = 0; j < s4.n_job; j = j + 1) begin
                if (s2.jpos[j] != s1.jpos[j] || s3.jpos[j] != s1.jpos[j] || s4.jpos[j] != s1.jpos[j] ||
                    s2.jtok[j] != s1.jtok[j] || s4.jtok[j] != s1.jtok[j]) begin
                    $display("WAVE FAIL: stage job %0d differs across dies", j); errs = errs + 1;
                end
                sh = sh + (s2.js_t[j] - s1.jd_t[j]) + (s3.js_t[j] - s2.jd_t[j]) + (s4.js_t[j] - s3.jd_t[j]); nh = nh + 3;
            end
            hop = avg(sh, nh) - ideal;
            $display("WAVE_EVENT hop_done_to_start_mean=%0.2f ideal=%0d (header + 46 words + 2 x %0d stations + stub 1) hops=%0d jobs=%0d",
                     avg(sh, nh), ideal, S_L, nh, s4.n_job);
            $display("WAVE_CHARGE id=wfc_kit.ar_pass price=160.53 measured=%0.2f n=%0d unit=cycles_per_stage_hop", hop, nh);
            // wfc_kit.intervals: same-pass consecutive positions at the last stage: start-to-start - busy - composed handoff 46
            ni = 0; si = 0;
            for (j = 1; j < s4.n_job; j = j + 1)
                if (s4.js_t[j] - s4.js_t[j-1] < 2 * bf && s4.jpos[j] == s4.jpos[j-1] + 1) begin si = si + (s4.js_t[j] - s4.js_t[j-1]); ni = ni + 1; end
            itv = avg(si, ni) - bf - 46;
            $display("WAVE_EVENT interval_start_to_start_mean=%0.2f busy_fast=%0d intervals=%0d", avg(si, ni), bf, ni);
            $display("WAVE_CHARGE id=wfc_kit.intervals price=310.62 measured=%0.2f n=%0d unit=cycles_per_wavefront_interval", itv, ni);
            // sequencer
            $display("WAVE_EVENT rows_to_dh1=%0.2f (n %0d) dh_result_to_next=%0.2f (n %0d) seed_after_close=%0.2f (n %0d) last_dh_to_draft_flit=%0.2f (n %0d)",
                     avg(s_rw, n_rw), n_rw, avg(s_dh, n_dh), n_dh, avg(s_sac, n_sac), n_sac, avg(s_ldf, n_ldf), n_ldf);
            $display("WAVE_CHARGE id=mtp_seq.draft_chain price=48.0 measured=%0.2f n=%0d unit=cycles_per_step",
                     avg(s_rw, n_rw) + 5.0 * avg(s_dh, n_dh), n_rw);
            $display("WAVE_EVENT seed_release_all_steps=%0.2f last_dh_to_draft_flit_clean=%0.2f (clean steps %0d of %0d)",
                     avg(s_sac, n_sac) + avg(s_ldf, n_ldf), avg(s_ldc, n_ldc), n_ldc, n_ldf);
            $display("WAVE_CHARGE id=mtp_seq.seed_release price=22.4 measured=%0.2f n=%0d unit=cycles_per_step (steps with no squashed verify result in flight, the price's condition)",
                     avg(s_sac, n_sac) + avg(s_ldc, n_ldc), n_ldc);
            $display("WAVE_CHARGE id=wfc_tok.edges price=3.0 measured=%0.2f n=%0d unit=edges_per_step (HARD read pr_re -> registered response, less the 1-edge legacy read)",
                     avg(s0.pr_sum, s0.pr_n) - 1.0, s0.pr_n);
            $display("WAVE_CHARGE id=mtp_commit price=1.0 measured=%0.2f n=%0d unit=cycles_per_step", avg(cm_lat_sum, cm_lat_n), cm_lat_n);
            // P2
            sp = 0; pp = 0;
            for (j = 0; j < 3; j = j + 1) begin sp = sp + (u_tw1.tx_cyc[j] - u_tw0.tx_cyc[j]); pp = pp + u_tw0.tx_cyc[j]; end
            $display("WAVE_EVENT p2_twin_direct0=%0d direct1=%0d direct2=%0d lnk0=%0d lnk1=%0d lnk2=%0d in_loop_tx_mean=%0.2f (n %0d)", u_tw0.tx_cyc[0], u_tw0.tx_cyc[1],
                     u_tw0.tx_cyc[2], u_tw1.tx_cyc[0], u_tw1.tx_cyc[1], u_tw1.tx_cyc[2], avg(p2l_sum, p2l_n), p2l_n);
            $display("WAVE_CHARGE id=p2.link_ends price=51.0 measured=%0d n=3 unit=cycles_per_3_transactions", sp);
            $display("WAVE_CHARGE id=p2.core_transaction price=5467.0 measured=%0.2f n=3 unit=cycles_per_transaction (ot_mtp_p2_prefix_path driven directly; p2.selected_path per-rank-prefix basis)",
                     pp / 3.0);
            $display("WAVE_EVENT mtp_lane_token_tx=%0.2f token_rx=%0.2f (n %0d / %0d) seed_tx=%0.2f seed_rx=%0.2f (n %0d / %0d)",
                     avg(lt_tx, lt_nlo), avg(lt_rx, lt_nrt), lt_nlo, lt_nrt, avg(ls_tx, ls_nlo), avg(ls_rx, ls_nrs), ls_nlo, ls_nrs);
            $display("WAVE_CHARGE id=mtp_lane.adapters price=16.0 measured=%0.2f n=%0d unit=cycles_per_step (token return + seed traversals)",
                     avg(lt_tx, lt_nlo) + avg(lt_rx, lt_nrt) + avg(ls_tx, ls_nlo) + avg(ls_rx, ls_nrs), ls_nrs);
            $display("WAVE_EVENT p2_lane_start_tx=%0.2f start_rx=%0.2f (n %0d) last_row_tx=%0.2f last_row_rx=%0.2f (n %0d)",
                     avg(ps_tx, ps_n), avg(ps_rx, ps_n), ps_n, avg(pr_tx, pr_n), avg(pr_rx, pr_n), pr_n);
            $display("WAVE_CHARGE id=p2.lane_adapters price=51.0 measured=%0.2f n=%0d unit=cycles_per_3_transactions",
                     3.0 * (avg(ps_tx, ps_n) + avg(ps_rx, ps_n) + avg(pr_tx, pr_n) + avg(pr_rx, pr_n)), pr_n);
            // draft head
            $display("WAVE_EVENT markov_first_result=%0.2f (n %0d) ep_step=%0.2f ref_ep_step=%0.2f (n %0d)",
                     avg(mk_lat_sum, mk_lat_n), mk_lat_n, avg(ep_sum, ep_n), avg(rf_sum, rf_n), ep_n);
            $display("WAVE_CHARGE id=markov.floor price=562.5 measured=%0.2f n=%0d unit=cycles_per_step (5 x (first result - 65.5))",
                     5.0 * (avg(mk_lat_sum, mk_lat_n) - 65.5), mk_lat_n);
            $display("WAVE_CHARGE id=draft_head.pipe_regs.vm_mtp_ep price=5.0 measured=%0.2f n=%0d unit=cycles_per_step (5 x OUTPUT_PIPE; the HBRELAY half is not in this bench)",
                     5.0 * (avg(ep_sum, ep_n) - avg(rf_sum, rf_n)), ep_n);
            // seed launch: per descriptor after the prefill, measured vs 34 + 3 + (rows - 1) x 35
            sh = 0; sh2 = 0; n2 = 0;
            for (j = 1; j < sl_nd; j = j + 1) begin sh = sh + sl_sum[j]; sh2 = sh2 + 34 + 3 + (sl_rows[j] - 1) * 35; n2 = n2 + 1; end
            $display("WAVE_EVENT seedl_desc_to_x=%0.2f done_to_ps=%0.2f row_gap=%0.2f (gaps %0d) descriptors=%0d rows_mean=%0.3f",
                     avg(sl_d2x, sl_nd - 1), avg(sl_d2p, sl_nd - 1), avg(sl_gap, sl_ng), sl_ng, n2, avg(sh2 - 37 * n2, 35 * n2) + 1.0);
            $display("WAVE_CHARGE id=seedl.launch price=%0.2f measured=%0.2f n=%0d unit=cycles_per_step (price at this bench's rows: 34 + 3 + (rows - 1) x 35)",
                     avg(sh2, n2), avg(sh, n2), n2);
            $display("WAVE_CHARGE id=hrow.transport price=165.0 measured=%0.2f n=%0d unit=cycles_per_row_part", avg(hrw_sum, hrw_cnt), hrw_cnt);
            $display("WAVE_EVENT hist_ring_read_to_last=%0.2f (n %0d) hist_ring_p_read_to_last=%0.2f (n %0d)", avg(h0s, h0n), h0n, avg(h1s, h1n), h1n);
        end
    endtask
