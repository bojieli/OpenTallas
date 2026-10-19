`timescale 1ns/1ps
`default_nettype none
// VEH-FMT-COLL2/HC (10-19): replay-format pre-check of hc_images.py on the REAL SW-slice HC RTL (sw2 bundle masters):
// hleaf_SW ot_hbm_host_cfg_leaf_sw, calendar_SW hfd_hgi_vm_calendar_f20 (tgt 96), hc_SW ot_hbm_hc_qhub_static DRLY 2
// (tgt 108) and hc_SW0..3 ot_hgi_sfu_lg_pair_tap_leaf_term (READ_RETURN 18 / WRITE_RETURN 15, calendar_SW
// lg_local_read/write [17:16]..[23:22]) wired as in slice.v.  Below the hc taps (sfu_SW<k> far path -> su_SW<k> ->
// VM bank) a VM model answers on near_rr NRD edges / near_w_done NWD edges after it samples near_rq / near_wq (the
// latencies the tap's fixed return calendar demands; a wrong value faults the tap).  hc_eng (root, outside the slice)
// is replayed on result_v / result / result_position; qd_* / qi_* / s_i / wf_* idle as in an HC_MIX_POST replay.
// Slice TB edge semantics (gen_slice_tb.py): D at cyc c -> value right after edge c; C at cyc c -> value AT edge c.
// Event file: "<cyc> <kind 1 D|2 C|3 M> <port> <sector-or-mask hex> <value hex>".  Prints HCRPL PASS / FAIL.
module tb_hc_replay;
    localparam integer NE = 8192;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    integer cnt = -1, NRD = 14, NWD = 11;
    reg cfg_v = 0, desc_v = 0, launch_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    reg [11:0] desc_base = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0;
    reg [3:0] res_v = 0; reg [11:0] res_pos = 0; reg [3071:0] res = 0;
    wire a_cv, a_dv, a_lv, b_cv, b_dv, b_lv; wire [7:0] a_ct, b_ct; wire [11:0] a_ca, b_ca, a_db, b_db; wire [255:0] a_cd, b_cd;
    wire [12:0] a_dl, b_dl; wire [15:0] a_dlp, b_dlp; wire [17:0] s_ready, s_active; wire [28:0] s_fault;
    wire hc_conf, hc_pa, hc_pd, hcq_fault, eng_fault, cal_conf, cal_tf, cal_f, cal_v, cal_act, cal_dn;
    wire [23:0] lg_r, lg_w; wire [135:0] lg_rq; wire [2247:0] lg_wq; wire [2055:0] lg_rr; wire [7:0] lg_wd;
    wire gm_v; wire [4:0] gm_row; wire [2:0] gm_pos; wire [31:0] gm_data; wire [3:0] tap_f;
    ot_hbm_host_cfg_leaf_sw hleaf(.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .a_cfg_v(a_cv), .a_cfg_target(a_ct), .a_cfg_addr(a_ca), .a_cfg_data(a_cd), .a_desc_v(a_dv),
        .a_desc_base(a_db), .a_desc_limit(a_dl), .a_desc_loops(a_dlp), .a_launch_v(a_lv), .b_cfg_v(b_cv),
        .b_cfg_target(b_ct), .b_cfg_addr(b_ca), .b_cfg_data(b_cd), .b_desc_v(b_dv), .b_desc_base(b_db),
        .b_desc_limit(b_dl), .b_desc_loops(b_dlp), .b_launch_v(b_lv),
        .t_ready({7'd0, hc_conf, 2'd0, cal_conf, 7'd0}), .t_active(18'd0),
        .t_fault({14'd0, hcq_fault, 2'd0, cal_f, cal_tf, 10'd0}), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
    hfd_hgi_vm_calendar_f20 calendar(.clk(clk), .clk_cap(clk), .clk_mem(clk), .clk_tgt(clk), .rst_n(rst_n), .tgt(8'd96),
        .cfg_v(a_cv), .cfg_target(a_ct), .cfg_addr(a_ca), .cfg_data(a_cd), .desc_v(a_dv), .desc_base(a_db),
        .desc_limit(a_dl), .desc_loops(a_dlp), .launch_v(a_lv), .tgt_configured(cal_conf), .tgt_fault(cal_tf),
        .calendar_v(cal_v), .active(cal_act), .done(cal_dn), .fault(cal_f), .ordinal(), .client_seq(),
        .response_enable(), .response_seq(), .bank_enable(), .bank_client(), .hub_ring_enable(), .hub_ring_client(),
        .rslot_v(), .wslot_v(), .rslot(), .wslot(), .ring_tx_enable(), .ring_tx_source(), .replay_enable(),
        .replay_source(), .lg_local_read(lg_r), .lg_local_write(lg_w));
    ot_hbm_hc_qhub_static #(.DRLY(2)) hub(.clk(clk), .rst_n(rst_n), .tgt(8'd108), .cfg_v(a_cv), .cfg_target(a_ct),
        .cfg_addr(a_ca), .cfg_data(a_cd), .desc_v(a_dv), .desc_base(a_db), .desc_limit(a_dl), .desc_loops(a_dlp),
        .launch_v(a_lv), .configured(hc_conf), .lg_rq(lg_rq), .lg_wq(lg_wq), .lg_rr(lg_rr), .lg_w_done(lg_wd),
        .residual_done(), .gathered_mix_v(gm_v), .gathered_mix_row(gm_row), .gathered_mix_pos(gm_pos),
        .gathered_mix_data(gm_data), .gather_done(), .result_v(res_v[0]), .result_position(res_pos[2:0]),
        .result(res[767:0]), .program_active(hc_pa), .program_done(hc_pd), .hcq_fault(hcq_fault),
        .d_v(1'b0), .d_ss(1'b0), .d_nv(7'd0), .d_wa(10'd0), .d_xa(10'd0), .i_v(1'b0), .i_kind(1'b0), .i_slot(2'd0),
        .i_lo(5'd0), .i_w(5'd0), .i_cnt(12'd0), .i_word(10'd0), .ps_v(), .ps(), .ps_f(), .eng_fault(eng_fault),
        .rstb_w(), .rstb_e(), .rstb_n(), .rstb_s(), .bd_v(), .bd_ss(), .bd_nv(), .bd_wa(), .bd_xa(), .s_i(2049'd0),
        .wf_w(1'b0), .wf_e(1'b0), .wf_n(3'd0), .wf_s(3'd0), .wc_w(), .wc_n(), .wc_e(), .wc_s(), .xb_v(), .xb_beat(),
        .xb_v_n(), .xb_v_e(), .xb_v_s(), .xb_beat_n(), .xb_beat_e(), .xb_beat_s(), .xb_d0(), .xb_d1(), .xb_d2(),
        .xb_d3(), .xb_d4(), .xb_d5(), .xb_d6(), .xb_d7());
    wire [33:0] n_rq [0:3]; wire [561:0] n_wq [0:3]; reg [513:0] n_rr [0:3]; reg [1:0] n_wd [0:3];
    for (genvar k = 0; k < 4; k = k + 1) begin : g_tap
        ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(18), .WRITE_RETURN(15)) tap(.clk(clk), .rst_n(rst_n),
            .c_rq(lg_rq[34*k +: 34]), .c_wq(lg_wq[562*k +: 562]), .c_rr(lg_rr[514*k +: 514]), .c_w_done(lg_wd[2*k +: 2]),
            .local_read(lg_r[16 + 2*k +: 2]), .local_write(lg_w[16 + 2*k +: 2]), .near_rq(n_rq[k]), .near_wq(n_wq[k]),
            .near_rr(n_rr[k]), .near_w_done(n_wd[k]), .fault(tap_f[k]));
    end
    // ---- VM model below the hc taps (sector {s[15], s[12:0]}; bank = s[2:0])
    reg [255:0] mem [0:16383];
    reg [256:0] rp [0:7][0:31]; reg wp [0:7][0:31];
    integer vm_errors = 0, reads = 0, writes = 0;
    always @(posedge clk) begin
        for (integer b = 0; b < 8; b = b + 1) begin
            reg [16:0] r; reg [280:0] w; reg [13:0] a;
            r = n_rq[b/2][(b%2)*17 +: 17]; w = n_wq[b/2][(b%2)*281 +: 281];
            for (integer d = 31; d > 0; d = d - 1) begin rp[b][d] <= rp[b][d-1]; wp[b][d] <= wp[b][d-1]; end
            rp[b][0] <= 0; wp[b][0] <= 0;
            n_rr[b/2][(b%2)*257 +: 257] <= rp[b][NRD-1];
            n_wd[b/2][b%2] <= wp[b][NWD-1];
            if (rst_n && r[16]) begin
                a = {r[15], r[12:0]};
                if (r[2:0] != 3'(b) || (!r[15] && r[14:13] != 2'd0)) begin vm_errors++; $display("HCRPL VM b%0d bad read %h", b, r[15:0]); end
                reads++; rp[b][0] <= {1'b1, mem[a]};
            end
            if (rst_n && w[280]) begin
                a = {w[279], w[276:264]};
                if (w[266:264] != 3'(b) || (!w[279] && w[278:277] != 2'd0) || w[7:0] != 8'hff) begin vm_errors++; $display("HCRPL VM b%0d bad write %h", b, w[279:264]); end
                writes++; mem[a] <= w[263:8]; wp[b][0] <= 1'b1;
            end
        end
    end
    // ---- events
    integer e_cyc [0:NE-1]; integer e_kind [0:NE-1]; integer e_port [0:NE-1]; reg [15:0] e_sec [0:NE-1]; reg [3071:0] e_val [0:NE-1];
    integer ne = 0, ptr = 0, checks = 0, fails = 0, drives = 0, ifault = 0;
    function automatic [3071:0] sample(input integer p);
        case (p)
            20: sample = 3072'(gm_v); 21: sample = 3072'(gm_row); 22: sample = 3072'(gm_pos); 23: sample = 3072'(gm_data);
            24: sample = 3072'(eng_fault); 25: sample = 3072'(s_fault); 26: sample = 3072'(s_ready);
            default: sample = '0;
        endcase
    endfunction
    always @(posedge clk) if (rst_n) begin
        cnt = cnt + 1;
        if ((hcq_fault | eng_fault | (|tap_f) | cal_f | cal_tf) && ifault == 0) begin
            ifault = cnt; $display("HCRPL internal fault at cyc %0d hcq=%0d eng=%0d tap=%b cal=%0d/%0d q=%0d cal_tgt=%0d", cnt,
                hcq_fault, eng_fault, tap_f, cal_f, cal_tf, hub.u_q.fault, calendar.u_target.fault);
        end
        while (ptr < ne && e_cyc[ptr] <= cnt) begin
            if (e_cyc[ptr] < cnt) begin fails++; $display("HCRPL late event %0d", ptr); end
            else if (e_kind[ptr] == 1) begin
                drives++;
                case (e_port[ptr])
                    0: cfg_v <= e_val[ptr][0]; 1: cfg_target <= e_val[ptr][7:0]; 2: cfg_addr <= e_val[ptr][11:0];
                    3: cfg_data <= e_val[ptr][255:0]; 4: desc_v <= e_val[ptr][0]; 5: desc_base <= e_val[ptr][11:0];
                    6: desc_limit <= e_val[ptr][12:0]; 7: desc_loops <= e_val[ptr][15:0]; 8: launch_v <= e_val[ptr][0];
                    10: res_v <= e_val[ptr][3:0]; 11: res_pos <= e_val[ptr][11:0]; 12: res <= e_val[ptr];
                    default: ;
                endcase
            end else if (e_kind[ptr] == 2) begin
                reg [3071:0] got, m;
                m = (e_port[ptr] == 25 || e_port[ptr] == 26) ? 3072'(e_sec[ptr]) : ~3072'd0;
                got = e_port[ptr] == 30 ? 3072'(mem[{e_sec[ptr][15], e_sec[ptr][12:0]}]) : sample(e_port[ptr]);
                checks++;
                if ((got & m) !== (e_val[ptr] & m)) begin
                    fails++;
                    if (fails < 25) $display("HCRPL MISMATCH cyc=%0d port=%0d sec=%h got=%h exp=%h", cnt, e_port[ptr], e_sec[ptr], got[255:0], e_val[ptr][255:0]);
                end
            end
            ptr++;
        end
    end
    // timing trace (first occurrences) for the manifest
    integer t_word0 = -1, t_lgrq = -1, t_gm = -1, t_lgwq = -1, t_res = -1;
    always @(posedge clk) if (rst_n) begin
        if (t_word0 < 0 && hub.u_q.c != 0) t_word0 = cnt + 1;
        if (t_lgrq < 0 && |lg_rq) t_lgrq = cnt + 1;
        if (t_gm < 0 && gm_v) t_gm = cnt + 1;
        if (t_lgwq < 0 && |lg_wq) t_lgwq = cnt + 1;
        if (t_res < 0 && res_v[0]) t_res = cnt + 1;
    end
    initial begin
        integer fd, c, k, p; reg [15:0] s; reg [3071:0] v; string ev;
        if (!$value$plusargs("EV=%s", ev)) ev = "events.txt";
        if ($value$plusargs("NRD=%d", NRD)) ; if ($value$plusargs("NWD=%d", NWD)) ;
        for (integer a = 0; a < 16384; a = a + 1) mem[a] = 256'd0;
        for (integer b = 0; b < 8; b = b + 1) for (integer d = 0; d < 32; d = d + 1) begin rp[b][d] = 0; wp[b][d] = 0; end
        for (integer b = 0; b < 4; b = b + 1) begin n_rr[b] = 0; n_wd[b] = 0; end
        fd = $fopen(ev, "r");
        if (fd == 0) begin $display("HCRPL FAIL no event file %s", ev); $finish; end
        while ($fscanf(fd, "%d %d %d %h %h\n", c, k, p, s, v) == 5) begin
            if (k == 3) mem[{s[15], s[12:0]}] = v[255:0];
            else begin e_cyc[ne] = c; e_kind[ne] = k; e_port[ne] = p; e_sec[ne] = s; e_val[ne] = v; ne++; end
        end
        $fclose(fd);
        repeat (5) @(negedge clk); rst_n = 1;
        while (ptr < ne) @(negedge clk);
        repeat (4) @(negedge clk);
        $display("HCRPL TRACE word0_after_edge=%0d lg_rq_after=%0d gm_v_after=%0d lg_wq_after=%0d result_v_after=%0d NRD=%0d NWD=%0d",
                 t_word0 - 1, t_lgrq - 1, t_gm - 1, t_lgwq - 1, t_res - 1, NRD, NWD);
        if (fails == 0 && vm_errors == 0 && checks > 0 && ifault == 0)
            $display("HCRPL PASS events=%0d drives=%0d checks=%0d vm_reads=%0d vm_writes=%0d last_cyc=%0d", ne, drives, checks, reads, writes, cnt);
        else $display("HCRPL FAIL fails=%0d vm_errors=%0d internal_fault_cyc=%0d checks=%0d reads=%0d writes=%0d", fails, vm_errors, ifault, checks, reads, writes);
        $finish;
    end
endmodule
`default_nettype wire
