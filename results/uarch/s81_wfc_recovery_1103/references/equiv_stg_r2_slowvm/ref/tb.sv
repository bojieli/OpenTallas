`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_mtp_rom_stg: the closed STAGE WFC (r11 stg_u50 parameters: SOURCE 0, WAVE 1, RXWORDS 41, XWORDS 46, MARGIN,
// LINK_REG, VM_REG, ...) with its integration shims dsfd_wfc_lnk (bindings "in_* out_*") and dsfd_wfc_vmx (bindings
// "vm_*" across 1.2 / 0.9 GHz and "core_*") -- stream mtp-rom, 2026-10-08.
// Upstream: NUSR users' HIDDEN messages (header + 41 payload words word(p, t, w), t = H(u, p)), users interleaved at random,
// each user's positions in order, random link stalls.  Stage core (0.9 GHz): at k_start it reads the 41 received
// words from the VM and checks them (the writes crossed and were ACKed before the start), after T_CORE it writes
// 46 outbound words word2(u, p, t, w) and pulses done.  VM: random write-ready / ACK delay (VMSLOW: mostly stalled),
// random read delay; VMNAT: the native VM backend (always ready, write ACK 4 edges, read valid 5 edges).  Downstream: every outbound HIDDEN (header user / pos / token, 46 words) is checked word for word.
// PASS: NJOB jobs in, NJOB messages out, all content exact, no fault (WFC proto_fault, lnk, vmx).
// ---------------------------------------------------------------------------
module tb_mtp_rom_stg_tokpipe;
    parameter integer SEED = 1, NJOB = 60, NUSR = 3, VMSLOW = 0, VMNAT = 0, LAG = 0, T_CORE = 80, MAXC = 400000;
    localparam integer FLIT = 512, NW = 21, USER_W = 10, VWA = 15, RXW = 41, TXW = 46;
    localparam integer HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32, HDR_POS = 40, HDR_IDX = 61, HDR_VAL = 82,
                       HDR_TOK = 114, HDR_USER_HI = 151;
    reg fclk = 0, sclk = 0;
    always #1.5 fclk = ~fclk;
    always #2.0 sclk = ~sclk;
    reg rst_n = 0;
    integer cyc = 0, scyc = 0;
    always @(posedge fclk) cyc <= cyc + 1;
    function automatic [31:0] mix(input [31:0] h, input [31:0] x);
        reg [31:0] t; begin t = (h ^ (x * 32'h9E3779B1)) + 32'h7F4A7C15; t = t ^ (t >> 15); t = t * 32'h2C1B3C6D;
        mix = t ^ (t >> 12); end
    endfunction
    function automatic [FLIT-1:0] word(input integer s, input integer uu, input integer pp, input integer tt,
                                       input integer ww);
        integer b; reg [31:0] h; begin
            h = mix(mix(mix(mix(s, uu), pp), tt), ww);
            for (b = 0; b < FLIT / 32; b = b + 1) begin word[b*32 +: 32] = h; h = mix(h, b); end
        end
    endfunction

    wire w_in_valid, w_in_ready, w_in_last, w_out_valid, w_out_ready, w_out_last;
    wire [FLIT-1:0] w_in_data, w_out_data;
    wire core_start, core_done_w; wire [NW-1:0] core_token, core_pos, cnt_tok; wire [31:0] cnt_val;
    wire [USER_W-1:0] core_user; wire [29:0] kv_base;
    wire vm_we, vm_re; wire [VWA-1:0] vm_waddr, vm_raddr; wire [FLIT-1:0] vm_wdata, vm_rq;
    wire pr_re; wire [USER_W-1:0] pr_user; wire [NW-1:0] pr_pos; wire [3:0] pr_blk;
    wire core_busy, tok_valid, proto_fault, wf_issue, wf_reject, wf_squash;
    wire [USER_W-1:0] tok_user, users_done; wire [NW-1:0] tok_pos, tok_id;
    reg li_v = 0; reg [FLIT:0] li_d = 0; wire li_r;
    wire lo_v; wire [FLIT:0] lo_d; reg lo_r = 0;
    wire [FLIT:0] dw; wire vc_ret, lnk_ft;
    wire swv; wire [VWA+FLIT-1:0] swd; reg swr = 0, swa = 0;
    wire srv; wire [VWA-1:0] srd; reg srr = 0; reg [FLIT:0] srq = 0;
    wire [USER_W+2*NW:0] ks; reg [NW+32:0] kd = 0; wire vmx_ft;
    // POSTED (main decision 10-10): the kit's VM channels behind VF / VR hub stations into the VM-side endpoint
    // dsfd_vm_wfc_ep (one in-order op pipe to a VM port); START reaches the core from the endpoint (KS stations);
    // the VM port model applies ops at the pins in order and returns reads RL cycles later; errors are a sticky level.
    localparam integer VF = 13, VR = 13, KS = 1, RL = 6;
    wire k_swv, k_swg, k_srv, k_srg, r_swv, r_swg, r_srv, r_srg, k_err, e_err; wire [VWA+FLIT-1:0] k_swd, r_swd;
    wire [2*VWA:0] k_srd, r_srd; wire [2*FLIT+1:0] k_srq, e_srq; wire [USER_W+2*NW:0] e_ks, k_ks_unused;
    wire e_mv, e_mwe; wire [VWA-1:0] e_mrow; wire [FLIT-1:0] e_md; reg e_mov = 0; reg [FLIT-1:0] e_mod = 0;
    mtp_test_relay #(.W(VWA+FLIT+1), .HOPS(VF)) y_swf (.clk(sclk), .rst_n(rst_n), .in_data({k_swv, k_swd}), .out_data({r_swv, r_swd}));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_swr (.clk(sclk), .rst_n(rst_n), .in_data(r_swg), .out_data(k_swg));
    mtp_test_relay #(.W(2*VWA+2), .HOPS(VF)) y_srf (.clk(sclk), .rst_n(rst_n), .in_data({k_srv, k_srd}), .out_data({r_srv, r_srd}));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_srr (.clk(sclk), .rst_n(rst_n), .in_data(r_srg), .out_data(k_srg));
    mtp_test_relay #(.W(1), .HOPS(VR)) y_err (.clk(sclk), .rst_n(rst_n), .in_data(e_err), .out_data(k_err));
    mtp_test_relay #(.W(2*FLIT+2), .HOPS(VR)) y_srq (.clk(sclk), .rst_n(rst_n), .in_data(e_srq), .out_data(k_srq));
    mtp_test_relay #(.W(USER_W+2*NW+1), .HOPS(KS)) y_ks (.clk(sclk), .rst_n(rst_n), .in_data(e_ks), .out_data(ks));
    dsfd_vm_wfc_ep #(.VF(VF), .VR(VR), .RL(RL), .RD2(1)) u_ep (.ck(sclk), .rst(rst_n), .f_swv(r_swv), .f_swd(r_swd), .t_swg(r_swg),
        .f_srv(r_srv), .f_srd(r_srd), .t_srg(r_srg), .t_srq(e_srq), .t_err(e_err), .t_ks(e_ks),
        .m_v(e_mv), .m_we(e_mwe), .m_row(e_mrow), .m_d(e_md), .m_ov(e_mov), .m_od(e_mod), .m_fault(1'b0), .m1_v(e_m1v), .m1_row(e_m1row), .m1_ov(e_m1ov), .m1_od(e_m1od));
    reg [RL-1:0] e_rv = 0; reg [VWA-1:0] e_rr [0:RL-1]; integer e_i;
    wire e_m1v; wire [VWA-1:0] e_m1row; reg e_m1ov = 0; reg [FLIT-1:0] e_m1od = 0;
    reg [RL-1:0] e_rv1 = 0; reg [VWA-1:0] e_rr1 [0:RL-1];
    always @(posedge sclk) begin             // VM port: ops take effect at the pins in issue order; fixed-latency reads
        if (e_mv === 1'b1 && e_mwe === 1'b1) begin
            if (e_mrow >= 64) begin $display("FAIL: VM write address"); $finish; end
            vmem[e_mrow] = e_md;
        end
        e_rv <= rst_n ? {e_rv[RL-2:0], e_mv === 1'b1 && e_mwe === 1'b0} : '0; e_rr[0] <= e_mrow;
        for (e_i = 1; e_i < RL; e_i = e_i + 1) e_rr[e_i] <= e_rr[e_i-1];
        e_mov <= rst_n && e_rv[RL-1]; e_mod <= vmem[e_rr[RL-1]];
        e_rv1 <= rst_n ? {e_rv1[RL-2:0], e_m1v === 1'b1} : '0; e_rr1[0] <= e_m1row;
        for (e_i = 1; e_i < RL; e_i = e_i + 1) e_rr1[e_i] <= e_rr1[e_i-1];
        e_m1ov <= rst_n && e_rv1[RL-1]; e_m1od <= vmem[e_rr1[RL-1]];
    end
    assign swv = 1'b0; assign srv = 1'b0; assign swd = '0; assign srd = '0;   // the TB's own VM model stays idle
    wire [3:0] k_ft;
    dsfd_wfc_stg_cl u_kit (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(li_v), .f_lid(li_d), .t_lir(li_r), .t_lov(lo_v), .t_lod(lo_d), .f_lor(lo_r),
        .t_swv(k_swv), .t_swd(k_swd), .f_swr(k_swg), .f_swa(k_err), .t_srv(k_srv), .t_srd(k_srd), .f_srr(k_srg), .f_srq(k_srq),
        .t_ks(k_ks_unused), .f_kd(kd), .t_ft(k_ft), .t_hep(k_hep));
    assign proto_fault = k_ft[3]; assign lnk_ft = k_ft[2]; assign vmx_ft = k_ft[0];
    assign tok_valid = u_kit.u_wfc.tok_valid; assign tok_user = u_kit.u_wfc.tok_user; assign tok_pos = u_kit.u_wfc.tok_pos;
    assign tok_id = u_kit.u_wfc.tok_id;
    // HEP (DSpark hrow versioning): every stage start's issue epoch; a re-issued (user, pos) must carry a strictly higher
    // epoch than its previous issue (its old row can never be served), a user's epoch never decreases, and in total the
    // epochs advance exactly once per WFC rejection (checked before PASS)
    wire [USER_W+NW+4:0] k_hep;
    integer h_ep [0:1023]; integer h_pe [0:1023][0:255]; integer h_inc = 0, h_i, h_j;
    initial for (h_i = 0; h_i < 1024; h_i = h_i + 1) begin h_ep[h_i] = 0; for (h_j = 0; h_j < 256; h_j = h_j + 1) h_pe[h_i][h_j] = -1; end
    always @(posedge sclk) if (k_hep[USER_W+NW+4]) begin : hepchk
        integer hu, hp, he;
        hu = k_hep[NW+4 +: USER_W]; hp = k_hep[4 +: NW]; he = k_hep[3:0];
        if (he < h_ep[hu] && !(h_ep[hu] == 15 && he == 0)) begin $display("MTP_STG FAIL: hep epoch of u%0d decreased %0d -> %0d", hu, h_ep[hu], he); $finish; end
        if (he != h_ep[hu]) h_inc = h_inc + ((he - h_ep[hu] + 16) % 16);
        if (h_pe[hu][hp % 256] >= 0 && h_pe[hu][hp % 256] == he) begin $display("MTP_STG FAIL: hep u%0d pos %0d re-issued under the same epoch %0d (stale row)", hu, hp, he); $finish; end
        h_pe[hu][hp % 256] = he; h_ep[hu] = he;
    end
    assign w_in_valid = u_kit.w_in_valid;
    assign w_in_ready = u_kit.w_in_ready;
    assign w_in_last = u_kit.w_in_last;
    assign w_out_valid = u_kit.w_out_valid;
    assign w_out_ready = u_kit.w_out_ready;
    assign w_out_last = u_kit.w_out_last;
    assign w_in_data = u_kit.w_in_data;
    assign w_out_data = u_kit.w_out_data;
    assign core_start = u_kit.core_start;
    assign core_done_w = u_kit.u_wfc.core_done;
    assign core_token = u_kit.core_token;
    assign core_pos = u_kit.core_pos;
    assign cnt_tok = u_kit.u_wfc.core_next_token;
    assign cnt_val = u_kit.u_wfc.core_next_val;
    assign core_user = u_kit.core_user;
    assign kv_base = u_kit.u_wfc.kv_base;
    assign vm_we = u_kit.vm_we;
    assign vm_re = u_kit.vm_re;
    assign vm_waddr = u_kit.vm_waddr;
    assign vm_raddr = u_kit.vm_raddr;
    assign vm_wdata = u_kit.vm_wdata;
    assign vm_rq = u_kit.vm_rq;
    assign pr_re = u_kit.u_wfc.pr_re;
    assign pr_user = u_kit.u_wfc.pr_user;
    assign pr_pos = u_kit.u_wfc.pr_pos;
    assign pr_blk = u_kit.u_wfc.pr_blk;
    assign core_busy = u_kit.u_wfc.core_busy;
    assign wf_issue = u_kit.u_wfc.wf_issue;
    assign wf_reject = u_kit.u_wfc.wf_reject;
    assign wf_squash = u_kit.u_wfc.wf_squash;
    assign users_done = u_kit.u_wfc.users_done;
    assign dw = u_kit.u_lnk.t_dw;
    assign vc_ret = u_kit.vc_ret;

    // ---------------------------------------------------------------- upstream generator
    integer nxt [0:7]; integer jobs_in = 0, k_in = -1, gu, gp, gt, rnd;
    integer job_u [0:1023], job_p [0:1023], job_t [0:1023];
    always @(posedge fclk) if (rst_n) begin
        rnd = mix(SEED * 3, cyc);
        if (li_v && li_r) li_v <= 1'b0;
        if ((!li_v || li_r) && rnd[3:0] != 0) begin
            if (k_in < 0 && jobs_in < NJOB && rnd[7:4] < 6) begin
                gu = (rnd >> 8) % NUSR; if (gu < 0) gu = -gu;
                gp = nxt[gu]; gt = mix(gu, gp) % 129280; nxt[gu] = nxt[gu] + 1;
                job_u[jobs_in] = gu; job_p[jobs_in] = gp; job_t[jobs_in] = gt;
                li_v <= 1'b1; li_d <= 0;
                li_d[7:0] <= 8'd1; li_d[15:8] <= 8'd0; li_d[HDR_TYPE +: 4] <= 4'd1; li_d[HDR_LEN +: 8] <= RXW;
                li_d[HDR_USER +: 8] <= gu; li_d[HDR_POS +: NW] <= gp; li_d[HDR_IDX +: NW] <= gt ^ 7;
                li_d[HDR_VAL +: 32] <= 32'h3f000000 + gp; li_d[HDR_TOK +: NW] <= gt;
                k_in = 0;
            end else if (k_in >= 0) begin
                li_v <= 1'b1; li_d <= {k_in == RXW - 1, word(1, 0, job_p[jobs_in], job_t[jobs_in], k_in)};
                k_in = k_in + 1;
                if (k_in == RXW) begin k_in = -1; jobs_in = jobs_in + 1; end
            end
        end
    end
    // ---------------------------------------------------------------- slow side: VM + stage core
    reg [FLIT-1:0] vmem [0:63];
    integer sr_q [0:15], sr_qt [0:15], srn = 0, srw = 0, srr_i = 0;
    integer wq_w = 0, wq_r = 0; integer wq_a [0:15], wq_t [0:15]; reg [FLIT-1:0] wq_d [0:15];
    integer core_t = -1, cu, cp, ct, k, starts = 0, ji = 0, user_mis = 0;
    always @(posedge sclk) begin
        scyc <= scyc + 1;
        swa <= 1'b0; srq[FLIT] <= 1'b0; kd[NW+32] <= 1'b0;
        rnd = mix(SEED * 5, scyc);
        // VM write: accepted on swv && swr, visible + ACKed in order 1..4(+6 VMSLOW) cycles later
        swr <= (VMNAT ? 1'b1 : VMSLOW ? rnd[3:0] == 0 : rnd[3:0] != 0) && (wq_w - wq_r) < 8;
        if (swv && swr) begin
            wq_a[wq_w % 16] = swd[FLIT +: VWA]; wq_d[wq_w % 16] = swd[FLIT-1:0];
            wq_t[wq_w % 16] = VMNAT ? scyc + 4 : scyc + 1 + rnd[5:4] + (VMSLOW ? 6 : 0); wq_w = wq_w + 1;
            if (swd[FLIT +: VWA] >= 64) begin $display("FAIL: VM write address"); $finish; end
        end
        if (wq_r < wq_w && scyc >= wq_t[wq_r % 16]) begin
            vmem[wq_a[wq_r % 16]] = wq_d[wq_r % 16]; swa <= 1'b1; wq_r = wq_r + 1;
        end
        srr <= (VMNAT ? 1'b1 : rnd[7:6] != 0) && srn < 8;
        if (srv && srr) begin sr_q[srw % 16] = srd; sr_qt[srw % 16] = VMNAT ? scyc + 5 : scyc + 2 + rnd[9:8]; srw = srw + 1; srn = srn + 1; end
        if (srn > 0 && scyc >= sr_qt[srr_i % 16]) begin
            srq <= {1'b1, vmem[sr_q[srr_i % 16]]}; srr_i = srr_i + 1; srn = srn - 1;
        end
        if (ks[USER_W+2*NW]) begin
            if (core_t >= 0) begin $display("MTP_STG FAIL: start while busy"); $finish; end
            cu = ks[2*NW +: USER_W]; ct = ks[NW +: NW]; cp = ks[NW-1:0]; starts = starts + 1;
            // the job's identity: the token / position the WFC started; the received words must be in the VM now
            for (k = 0; k < RXW; k = k + 1)
                if (vmem[k] !== word(1, 0, cp, ct, k)) begin
                    $display("MTP_STG FAIL: RX word %0d of (p%0d, t%0d) not in the VM at start (write / start order)", k, cp, ct);
                    $finish;
                end
            core_t = scyc + T_CORE;
            // the WFC's core_user at the start pulse (observation: stage mode should carry the job's user)
            for (k = 0; k < jobs_in; k = k + 1) if (job_p[k] == cp && job_t[k] == ct && job_u[k] != cu) user_mis = user_mis + 1;
        end else if (core_t >= 0 && scyc >= core_t) begin
            for (k = 0; k < TXW; k = k + 1) vmem[k] = word(2, 0, cp, ct, k);
            kd <= {1'b1, NW'(ct ^ 21'h33), 32'h40400000 ^ cp};
            core_t = -1;
        end
    end
    // ---------------------------------------------------------------- downstream checker
    integer m_k = -1, m_u, m_p, m_t, outs = 0;
    always @(posedge fclk) if (rst_n) begin
        rnd = mix(SEED * 9, cyc);
        lo_r <= rnd[2:0] != 0;
        if (lo_v && lo_r) begin
            if (m_k < 0) begin
                if (lo_d[HDR_TYPE +: 4] != 4'd1 || lo_d[HDR_LEN +: 8] != TXW) begin
                    $display("MTP_STG FAIL: outbound header %h", lo_d[63:0]); $finish; end
                m_u = lo_d[HDR_USER +: 8]; m_p = lo_d[HDR_POS +: NW]; m_t = lo_d[HDR_TOK +: NW]; m_k = 0;
                if (m_t != mix(m_u, m_p) % 129280) begin $display("MTP_STG FAIL: outbound token / user / pos"); $finish; end
            end else begin
                if (lo_d[FLIT-1:0] !== word(2, 0, m_p, m_t, m_k)) begin
                    $display("MTP_STG FAIL: outbound word %0d of (u%0d p%0d) (staging / prefetch)", m_k, m_u, m_p); $finish; end
                m_k = m_k + 1;
                if (m_k == TXW) begin m_k = -1; outs = outs + 1; end
            end
        end
        if (proto_fault || lnk_ft || vmx_ft) begin
            $display("MTP_STG FAIL: fault wfc %0d lnk %0d vmx %0d", proto_fault, lnk_ft, vmx_ft); $finish; end
    end
    // ---------------------------------------------------------------- cycle measurements (fast cycles)
    integer t_ws = -1, t_ks = -1, t_kd = -1, n_s = 0, n_d = 0, sum_s = 0, sum_d = 0, max_s = 0, max_d = 0;
    integer t_li [0:4095], li_n = 0, wi_n = 0, sum_li = 0, max_li = 0;
    reg ks_seen = 0, kd_seen = 0, done_q = 0;
    always @(posedge fclk) if (rst_n) begin
        if (core_start) t_ws = cyc;
        if (ks[USER_W+2*NW] && !ks_seen && t_ws >= 0) begin sum_s = sum_s + (cyc - t_ws); if (cyc - t_ws > max_s) max_s = cyc - t_ws; n_s = n_s + 1; t_ws = -1; end
        ks_seen = ks[USER_W+2*NW];
        if (kd[NW+32] && !kd_seen) t_kd = cyc;
        kd_seen = kd[NW+32];
        if (core_done_w && !done_q && t_kd >= 0) begin sum_d = sum_d + (cyc - t_kd); if (cyc - t_kd > max_d) max_d = cyc - t_kd; n_d = n_d + 1; t_kd = -1; end
        done_q = core_done_w;
        // link shim, inbound: die-link accept -> the WFC's in_valid (the grant-protocol launch)
        if (li_v && li_r) begin t_li[li_n % 4096] = cyc; li_n = li_n + 1; end
        if (w_in_valid) begin sum_li = sum_li + (cyc - t_li[wi_n % 4096]); if (cyc - t_li[wi_n % 4096] > max_li) max_li = cyc - t_li[wi_n % 4096]; wi_n = wi_n + 1; end
    end
    integer i;
    initial begin
        for (i = 0; i < 8; i = i + 1) nxt[i] = 0;
        repeat (8) @(posedge fclk);
        rst_n = 1;
        while (outs < NJOB && cyc < MAXC) @(posedge fclk);
        if (outs < NJOB) begin $display("MTP_STG FAIL: timeout, %0d of %0d out", outs, NJOB); $finish; end
        repeat (100) @(posedge fclk);
        if(user_mis!=0) begin $display("MTP_STG FAIL: previous-job user published %0d times",user_mis);$finish;end
        $display("MTP_STG PASS jobs=%0d starts=%0d out=%0d cycles=%0d vmslow=%0d core_user_mismatch_at_start=%0d", jobs_in, starts, outs, cyc, VMSLOW, user_mis);
        $display("MTP_STG_CYC start_mean=%0.2f start_max=%0d done_mean=%0.2f done_max=%0d link_in_mean=%0.2f link_in_max=%0d txw=%0d (fast cycles; done = k_done -> WFC core_done incl. the %0d-word prefetch)",
                 1.0 * sum_s / n_s, max_s, 1.0 * sum_d / n_d, max_d, 1.0 * sum_li / wi_n, max_li, TXW, TXW);
        $finish;
    end
    integer rd_fo, rd_i;
    initial rd_fo = $fopen("ref_out.hex", "w");
    always @(posedge fclk) if (rst_n && lo_v && lo_r) $fwrite(rd_fo, "%h\n", lo_d);
    final begin
        $fclose(rd_fo); rd_fo = $fopen("jobs.txt", "w");
        for (rd_i = 0; rd_i < jobs_in; rd_i = rd_i + 1) $fwrite(rd_fo, "%h %h %h\n", job_u[rd_i], job_p[rd_i], job_t[rd_i]);
        $fclose(rd_fo);
    end
endmodule
