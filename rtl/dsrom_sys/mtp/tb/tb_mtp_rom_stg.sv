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
module tb_mtp_rom_stg;
    parameter integer READPIPE = 0, FULLSTALL = 0, SEED = 1, NJOB = 60, NUSR = 3, VMSLOW = 0, VMNAT = 0, LAG = 0, T_CORE = 80, MAXC = 400000;
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
    wire [6:0] vqi;
    wire vm_we, vm_re; wire [VWA-1:0] vm_waddr, vm_raddr; wire [FLIT-1:0] vm_wdata, vm_rq;
    wire pr_re; wire [USER_W-1:0] pr_user; wire [NW-1:0] pr_pos; wire [3:0] pr_blk;
    wire core_busy, tok_valid, proto_fault, wf_issue, wf_reject, wf_squash;
    wire [USER_W-1:0] tok_user, users_done; wire [NW-1:0] tok_pos, tok_id;
`ifdef OT_VMX_TOKPIPE
    ot_rom_pkg_ctrl_wfc_tokpipe #(
`else
    ot_rom_pkg_ctrl_wfc #(
`endif.WAVE(1), .WIN(6), .FLIT(FLIT), .NW(NW), .AW(30), .VWA(VWA), .USER_W(USER_W), .MAXU(866),
        .KVW(32768), .SEND_HIDDEN(1), .HID_DEST(1), .FWD_TOKEN(1), .SOURCE(0), .XWORDS(TXW), .RXWORDS(RXW),
        .UPOS_LWR(1), .CONTROL_PIPE(1), .PRECOMP(1), .IN_DEC(1), .TXQ_SLICE(1), .RDY_LT(1), .FANOUT_COPY(1),
        .MARGIN(1), .LINK_REG(1), .LINK_SEL(1), .VM_REG(1), .VM_RETURN_EXTRA(READPIPE), .TXQ(READPIPE?8:4), .SLEW_COPY(1)) u_wfc (
        .clk(fclk), .rst_n(rst_n), .cfg_users(10'd0), .cfg_prompt_len(21'd0), .cfg_gen_len(21'd0),
        .in_valid(w_in_valid), .in_ready(w_in_ready), .in_data(w_in_data), .in_last(w_in_last),
        .out_valid(w_out_valid), .out_ready(w_out_ready), .out_data(w_out_data), .out_last(w_out_last),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos), .core_user(core_user),
        .core_done(core_done_w), .core_next_token(cnt_tok), .core_next_val(cnt_val), .kv_base(kv_base),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq), .vm_rv(vqi[6]), .vm_ridx(vqi[5:0]),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(21'd0), .pr_blk(pr_blk), .pr_qk(1'b0),
        .core_busy(core_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id),
        .users_done(users_done), .proto_fault(proto_fault), .wf_issue(wf_issue), .wf_reject(wf_reject),
        .wf_squash(wf_squash));
    reg li_v = 0; reg [FLIT:0] li_d = 0; wire li_r;
    wire lo_v; wire [FLIT:0] lo_d; reg lo_r = 0;
    wire [FLIT:0] dw; wire vc_ret, lnk_ft;
    dsfd_wfc_lnk u_lnk (.ck(fclk), .rst(rst_n), .f_liv(li_v), .f_lid(li_d), .t_lir(li_r),
        .t_wiv(w_in_valid), .t_wid({w_in_last, w_in_data}), .f_wig(w_in_ready),
        .f_wov(w_out_valid), .f_wod({w_out_last, w_out_data}), .t_wog(w_out_ready),
        .t_lov(lo_v), .t_lod(lo_d), .f_lor(lo_r), .t_dw(dw), .f_vc(vc_ret), .t_ft(lnk_ft));
    wire swv; wire [VWA+FLIT-1:0] swd; reg swr = 0, swa = 0;
    wire srv; wire [VWA-1:0] srd; reg srr = 0; reg [FLIT:0] srq = 0;
    wire [USER_W+2*NW:0] ks; reg [NW+32:0] kd = 0; wire vmx_ft;
    dsfd_wfc_vmx #(.XWORDS(TXW), .LAG(LAG), .READPIPE(READPIPE)) u_vmx (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_vw({vm_we, vm_waddr, vm_wdata}), .f_vr({vm_re, vm_raddr}), .t_vq(vm_rq), .t_vqi(vqi),
        .f_cs({core_start, core_user, core_token, core_pos}), .t_cd({core_done_w, cnt_tok, cnt_val}), .t_vc(vc_ret),
        .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(srq),
        .t_ks(ks), .f_kd(kd), .t_ft(vmx_ft));

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
        lo_r <= FULLSTALL ? (cyc % 160 >= 96) : rnd[2:0] != 0;
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
    integer peak_queue=0, peak_debt=0, stalls=0;
    always @(posedge fclk) if(rst_n) begin
        if(u_wfc.txq_n>peak_queue) peak_queue=u_wfc.txq_n;
        if((u_wfc.rd_inflight+u_wfc.rd_pre+u_wfc.rd_extra[0]+u_wfc.rd_extra[1])>peak_debt)
            peak_debt=u_wfc.rd_inflight+u_wfc.rd_pre+u_wfc.rd_extra[0]+u_wfc.rd_extra[1];
        if(lo_v&&!lo_r) stalls=stalls+1;
        if(lo_v&&lo_r&&m_k>=0 && lo_d[FLIT] !== (m_k==TXW-1)) begin
            $display("MTP_STG FAIL: last flag word=%0d",m_k); $finish;
        end
    end
    integer i;
    initial begin
        for (i = 0; i < 8; i = i + 1) nxt[i] = 0;
        repeat (8) @(posedge fclk);
        rst_n = 1;
        while (outs < NJOB && cyc < MAXC) @(posedge fclk);
        if (outs < NJOB) begin $display("MTP_STG FAIL: timeout, %0d of %0d out", outs, NJOB); $finish; end
        repeat (100) @(posedge fclk);
        if(READPIPE && FULLSTALL && (peak_queue<8 || peak_debt<4 || stalls==0)) begin
            $display("MTP_STG FAIL: insufficient finite queue coverage q=%0d debt=%0d stalls=%0d",peak_queue,peak_debt,stalls); $finish;
        end
        $display("MTP_STG_QUEUE peak=%0d debt=%0d stalls=%0d readpipe=%0d",peak_queue,peak_debt,stalls,READPIPE);
        $display("MTP_STG PASS jobs=%0d starts=%0d out=%0d cycles=%0d vmslow=%0d core_user_mismatch_at_start=%0d", jobs_in, starts, outs, cyc, VMSLOW, user_mis);
        $display("MTP_STG_CYC start_mean=%0.2f start_max=%0d done_mean=%0.2f done_max=%0d link_in_mean=%0.2f link_in_max=%0d txw=%0d (fast cycles; done = k_done -> WFC core_done incl. the %0d-word prefetch)",
                 1.0 * sum_s / n_s, max_s, 1.0 * sum_d / n_d, max_d, 1.0 * sum_li / wi_n, max_li, TXW, TXW);
        $finish;
    end
endmodule
