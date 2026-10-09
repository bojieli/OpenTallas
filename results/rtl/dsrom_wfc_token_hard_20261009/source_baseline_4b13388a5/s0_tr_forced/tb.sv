`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_mtp_rom_s0: DS-ROM MTP control plane on the minimum vehicle (stream mtp-rom, 2026-10-08).
//
// DUT (all real RTL):
//   the closed SOURCE WFC ot_rom_pkg_ctrl_wfc (the r22 src_u55 parameters: WAVE 1, MAXU 866, REC_SRAM, MARGIN,
//   LINK_REG, VM_REG, ...), with its three S0 integration shims dsfd_wfc_lnk (link + DRAFT divert + VM credits),
//   dsfd_wfc_tok_r3 (cfg / prompt / draft store), dsfd_wfc_vmx (1.2 / 0.9 GHz VM + core transport), and the
//   head-die sequencer dsfd_mtp_seq.
// Models (the mechanisms that are not under test, each a delay with exact content checks):
//   S0 core (0.9 GHz): k_start -> after T_CORE writes the outbound words f(user, pos, token, w) into the VM;
//   VM (0.9 GHz): random write-ready / ACK delay, random read-ready / response delay;
//   stage pipeline + head lm_head: consumes the S0 HIDDEN message (checks every payload word: the VM / staging
//   transport end to end), returns the RESULT {user, pos, argmax} after L cycles, in issue order;
//   token-return link: R cycles; draft dies: rows ready T_DRAFT after the seed; draft head: T_HEAD a step.
// Targets / drafts:
//   MODE 0 (golden trace): the reduced V4.1 golden's own speculative decode (hdc_golden_v41.generate_spec,
//     results/rtl/dshbm_dspark_rtl_20261003/traces/*.cfg.json, converted by tools/dsrom_mtp_rom_bench.py):
//     a position's target is the golden pass's target for the issued context (fatal if the context is not one
//     the golden ran), the drafts are the golden pass's drafts (fatal if the seed's anchor / bonus differ).
//   MODE 1 (hash model): target = H(user, every issued token up to the position), the greedy continuation
//     computed by the bench, drafts right with probability RHO% (else wrong), several users interleaved.
// PASS needs: every emitted token (WFC tok_valid, positions >= plen-1) = greedy; every closed step's
// (closing position, accepted count) = the golden pass (MODE 0) / the bench's own prefix accept (MODE 1);
// speculative passes = expected count (drafts really used: no silent autoregressive fallback); no fault in any
// block; WFC proto_fault 0.
// ---------------------------------------------------------------------------
module tb_mtp_rom_s0_tokpipe;
    parameter integer MODE    = 0;
    parameter integer NUSR    = 2;          // users (MODE 0: each runs the same trace)
    parameter integer SEQ_MAXU = 8;         // users >= this pass the sequencer (autoregressive)
    parameter integer NGEN_H  = 40;         // MODE 1: tokens per user
    parameter integer PLEN_H  = 5;          // MODE 1: prompt length
    parameter integer RHO     = 70;         // MODE 1: draft accuracy %
    parameter integer SEED    = 1;
    parameter integer L       = 2600;       // pipeline + head latency (fast cycles) > (G+1) x S0 interval
    parameter integer R       = 40;         // token-return link
    parameter integer T_CORE  = 60;         // S0 core (slow cycles)
    parameter integer T_DRAFT = 700;
    parameter integer T_HEAD  = 30;
    parameter integer MAXC    = 3000000;
    localparam integer FLIT = 512, NW = 21, USER_W = 10, VWA = 15, XW = 41, G = 5, V = 129280;
    localparam integer HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32, HDR_POS = 40, HDR_IDX = 61, HDR_VAL = 82,
                       HDR_TOK = 114, HDR_ADDR = 135, HDR_USER_HI = 151;
    localparam integer PMAXB = 64, NPMAX = 64, MAXP = 512;

    reg fclk = 0, sclk = 0;
    always #1.5 fclk = ~fclk;                  // 1.2 GHz : 0.9 GHz = 3 : 4 (one PLL)
    always #2.0 sclk = ~sclk;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge fclk) cyc <= cyc + 1;

    // ------------------------------------------------------------------ trace / model state
    reg [31:0] trc [0:65535];
    integer plen, ngen, npass, steps;
    integer prompt [0:PMAXB-1];
    integer gtok [0:MAXP-1];                   // greedy tokens emitted (index = pos - (plen-1))
    integer pa_q [0:NPMAX-1], pa_a [0:NPMAX-1], pa_g [0:NPMAX-1];
    integer pa_d [0:NPMAX*5-1], pa_t [0:NPMAX*6-1];
    integer i, j, u, k;
    // per-user context / hash model
    reg [31:0] ph [0:NUSR*MAXP-1];             // prefix hash of the issued context
    integer tok_at [0:NUSR*MAXP-1];
    integer tru [0:NUSR*MAXP-1];               // MODE 1 greedy truth
    integer exp_pass_n;                        // expected speculative passes (all users)
    function automatic [31:0] mix(input [31:0] h, input [31:0] x);
        reg [31:0] t; begin t = (h ^ (x * 32'h9E3779B1)) + 32'h7F4A7C15; t = t ^ (t >> 15); t = t * 32'h2C1B3C6D;
        mix = t ^ (t >> 12); end
    endfunction
    function automatic integer htok(input integer uu, input [31:0] h);
        htok = mix(h, uu + 77) % V;
    endfunction

    // ------------------------------------------------------------------ DUT wiring
    // WFC
    wire w_in_valid, w_in_ready, w_in_last, w_out_valid, w_out_ready, w_out_last;
    wire [FLIT-1:0] w_in_data, w_out_data;
    wire core_start, core_done_w; wire [NW-1:0] core_token, core_pos, cnt_tok; wire [31:0] cnt_val;
    wire [USER_W-1:0] core_user; wire [29:0] kv_base;
    wire vm_we, vm_re; wire [VWA-1:0] vm_waddr, vm_raddr; wire [FLIT-1:0] vm_wdata, vm_rq;
    wire pr_re; wire [USER_W-1:0] pr_user; wire [NW-1:0] pr_pos, pr_q; wire [3:0] pr_blk; wire pr_qk;
    wire core_busy, tok_valid, proto_fault, wf_issue, wf_reject, wf_squash;
    wire [USER_W-1:0] tok_user, users_done; wire [NW-1:0] tok_pos, tok_id;
    wire [9:0] cfg_users; wire [NW-1:0] cfg_plen, cfg_glen;
    ot_dsrom_wfc_tokpipe_src #(.WAVE(1), .WIN(6), .FLIT(FLIT), .NW(NW), .AW(30), .VWA(VWA), .USER_W(USER_W), .MAXU(866),
        .KVW(32768), .SEND_HIDDEN(1), .HID_DEST(1), .FWD_TOKEN(1), .SOURCE(1), .XWORDS(41), .RXWORDS(41), .REC_SRAM(1),
        .UPOS_LWR(1), .CONTROL_PIPE(1), .CFG_Q(1), .PRECOMP(1), .IN_DEC(1), .TXQ_SLICE(1), .RDY_LT(1), .FANOUT_COPY(1),
        .MARGIN(1), .LINK_REG(1), .LINK_SEL(1), .VM_REG(1), .RD_PIPE(1), .SLEW_COPY(1)) u_wfc (
        .clk(fclk), .rst_n(rst_n), .cfg_users(cfg_users), .cfg_prompt_len(cfg_plen), .cfg_gen_len(cfg_glen),
        .in_valid(w_in_valid), .in_ready(w_in_ready), .in_data(w_in_data), .in_last(w_in_last),
        .out_valid(w_out_valid), .out_ready(w_out_ready), .out_data(w_out_data), .out_last(w_out_last),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos), .core_user(core_user),
        .core_done(core_done_w), .core_next_token(cnt_tok), .core_next_val(cnt_val), .kv_base(kv_base),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q), .pr_blk(pr_blk), .pr_qk(pr_qk),
        .core_busy(core_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id),
        .users_done(users_done), .proto_fault(proto_fault), .wf_issue(wf_issue), .wf_reject(wf_reject),
        .wf_squash(wf_squash));
    // link shim
    reg li_v = 0; reg [FLIT:0] li_d = 0; wire li_r;
    wire lo_v; wire [FLIT:0] lo_d; reg lo_r = 0;
    wire [FLIT:0] dw; wire vc_ret; wire lnk_ft;
    dsfd_wfc_lnk u_lnk (.ck(fclk), .rst(rst_n), .f_liv(li_v), .f_lid(li_d), .t_lir(li_r),
        .t_wiv(w_in_valid), .t_wid({w_in_last, w_in_data}), .f_wig(w_in_ready),
        .f_wov(w_out_valid), .f_wod({w_out_last, w_out_data}), .t_wog(w_out_ready),
        .t_lov(lo_v), .t_lod(lo_d), .f_lor(lo_r), .t_dw(dw), .f_vc(vc_ret), .t_ft(lnk_ft));
    // token store
    reg [2+USER_W+2*NW:0] cfgw = 0;
    wire tok_ft;
    dsfd_wfc_tok_r3 u_tok (.ck(fclk), .rst(rst_n), .f_c(cfgw), .t_cfg({cfg_users, cfg_plen, cfg_glen}), .f_dw(dw),
        .f_pr({pr_re, pr_user, pr_pos, pr_blk}), .t_pr({pr_qk, pr_q}), .t_ft(tok_ft));
    // VM / core transport
    wire swv; wire [VWA+FLIT-1:0] swd; reg swr = 0, swa = 0;
    wire srv; wire [VWA-1:0] srd; reg srr = 0; reg [FLIT:0] srq = 0;
    wire [USER_W+2*NW:0] ks; reg [NW+32:0] kd = 0; wire vmx_ft;
    dsfd_wfc_vmx #(.XWORDS(XW)) u_vmx (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_vw({vm_we, vm_waddr, vm_wdata}), .f_vr({vm_re, vm_raddr}), .t_vq(vm_rq),
        .f_cs({core_start, core_user, core_token, core_pos}), .t_cd({core_done_w, cnt_tok, cnt_val}), .t_vc(vc_ret),
        .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(srq),
        .t_ks(ks), .f_kd(kd), .t_ft(vmx_ft));
    // sequencer (head die)
    localparam integer SW = USER_W + 3 * NW + 4, DW = USER_W + 3 + NW;
    wire s_rv, s_rg, s_tv, s_tg, s_sv, s_sg, s_wv, s_wg, s_hv, s_hg, s_qv, s_qg;
    wire [FLIT-1:0] s_rd, s_td; wire [SW-1:0] s_sd; wire [USER_W-1:0] s_wd; wire [DW-1:0] s_hd, s_qd;
    wire [2*NW+USER_W+4:0] s_acc;
    dsfd_mtp_seq #(.MAXU(SEQ_MAXU)) u_seq (.ck(fclk), .rst(rst_n), .f_cfg({cfg_glen, cfg_plen}),
        .f_rv(s_rv), .f_rd(s_rd), .t_rg(s_rg), .t_tv(s_tv), .t_td(s_td), .f_tg(s_tg),
        .t_sv(s_sv), .t_sd(s_sd), .f_sg(s_sg), .f_wv(s_wv), .f_wd(s_wd), .t_wg(s_wg),
        .t_hv(s_hv), .t_hd(s_hd), .f_hg(s_hg), .f_qv(s_qv), .f_qd(s_qd), .t_qg(s_qg), .t_acc(s_acc));
    // bench-side grant adapters (the same pair the blocks use)
    reg br_v = 0; reg [FLIT-1:0] br_d = 0; wire br_r;                 // RESULT -> seq
    ot_rom_pkg_ctrl_wfc_ltx #(.W(FLIT)) a_r (.clk(fclk), .rst_n(rst_n), .c_valid(br_v), .c_ready(br_r), .c_data(br_d),
        .l_valid(s_rv), .l_ready(s_rg), .l_data(s_rd));
    wire bt_v; wire [FLIT-1:0] bt_d; reg bt_r = 0;                      // seq -> token-return link
    ot_rom_pkg_ctrl_wfc_lrx #(.W(FLIT)) a_t (.clk(fclk), .rst_n(rst_n), .l_valid(s_tv), .l_ready(s_tg), .l_data(s_td),
        .c_valid(bt_v), .c_ready(bt_r), .c_data(bt_d));
    wire bs_v; wire [SW-1:0] bs_d;                                      // seeds
    ot_rom_pkg_ctrl_wfc_lrx #(.W(SW)) a_s (.clk(fclk), .rst_n(rst_n), .l_valid(s_sv), .l_ready(s_sg), .l_data(s_sd),
        .c_valid(bs_v), .c_ready(1'b1), .c_data(bs_d));
    reg bw_v = 0; reg [USER_W-1:0] bw_d = 0; wire bw_r;                 // rows ready
    ot_rom_pkg_ctrl_wfc_ltx #(.W(USER_W)) a_w (.clk(fclk), .rst_n(rst_n), .c_valid(bw_v), .c_ready(bw_r), .c_data(bw_d),
        .l_valid(s_wv), .l_ready(s_wg), .l_data(s_wd));
    wire bh_v; wire [DW-1:0] bh_d;                                      // draft-head steps
    ot_rom_pkg_ctrl_wfc_lrx #(.W(DW)) a_h (.clk(fclk), .rst_n(rst_n), .l_valid(s_hv), .l_ready(s_hg), .l_data(s_hd),
        .c_valid(bh_v), .c_ready(1'b1), .c_data(bh_d));
    reg bq_v = 0; reg [DW-1:0] bq_d = 0; wire bq_r;                     // draft-head results
    ot_rom_pkg_ctrl_wfc_ltx #(.W(DW)) a_q (.clk(fclk), .rst_n(rst_n), .c_valid(bq_v), .c_ready(bq_r), .c_data(bq_d),
        .l_valid(s_qv), .l_ready(s_qg), .l_data(s_qd));

    // ------------------------------------------------------------------ slow side: VM + S0 core
    reg [FLIT-1:0] vmem [0:63];
    function automatic [FLIT-1:0] word(input integer uu, input integer pp, input integer tt, input integer ww);
        integer b; reg [31:0] h; begin
            h = mix(mix(mix(uu, pp), tt), ww);
            for (b = 0; b < FLIT / 32; b = b + 1) begin word[b*32 +: 32] = h; h = mix(h, b); end
        end
    endfunction
    integer sr_q [0:15]; integer sr_qt [0:15]; integer srn = 0, srw = 0, srr_i = 0;
    integer wq_w = 0, wq_r = 0; integer wq_a [0:15], wq_t [0:15]; reg [FLIT-1:0] wq_d [0:15];
    integer scyc = 0, core_t = -1, core_u, core_p, core_k; integer core_starts = 0;
    integer rnd;
    always @(posedge sclk) begin
        scyc <= scyc + 1;
        swa <= 1'b0; srq[FLIT] <= 1'b0; kd[NW+32] <= 1'b0;
        rnd = mix(SEED + scyc, 32'h51ed2701);
        // VM write: accept, ACK (and visible) 1..4 cycles later, one at a time
        // VM write: accepted on swv && swr, visible + ACKed in order 1..4 cycles later
        swr <= rnd[3:0] != 0 && (wq_w - wq_r) < 8;
        if (swv && swr) begin
            wq_a[wq_w % 16] = swd[FLIT +: VWA]; wq_d[wq_w % 16] = swd[FLIT-1:0];
            wq_t[wq_w % 16] = scyc + 1 + rnd[5:4]; wq_w = wq_w + 1;
            if (swd[FLIT +: VWA] >= 64) begin $display("FAIL: VM write address"); $finish; end
        end
        if (wq_r < wq_w && scyc >= wq_t[wq_r % 16]) begin
            vmem[wq_a[wq_r % 16]] = wq_d[wq_r % 16]; swa <= 1'b1; wq_r = wq_r + 1;
        end
        // VM read: random ready, in-order responses 2..5 cycles later
        srr <= rnd[7:6] != 0 && srn < 8;
        if (srv && srr) begin
            sr_q[srw % 16] = srd; sr_qt[srw % 16] = scyc + 2 + rnd[9:8]; srw = srw + 1; srn = srn + 1;
        end
        if (srn > 0 && scyc >= sr_qt[srr_i % 16]) begin
            if (sr_q[srr_i % 16] >= 64) begin $display("MTP_S0 FAIL: VM read address"); $finish; end
            srq <= {1'b1, vmem[sr_q[srr_i % 16]]}; srr_i = srr_i + 1; srn = srn - 1;
        end
        // S0 core: k_start -> T_CORE slow cycles -> outbound words written -> done pulse
        if (ks[USER_W+2*NW]) begin
            if (core_t >= 0) begin $display("MTP_S0 FAIL: start while the core is busy"); $finish; end
            core_u = ks[2*NW +: USER_W]; core_k = ks[NW +: NW]; core_p = ks[NW-1:0]; core_t = scyc + T_CORE;
            core_starts = core_starts + 1;
        end else if (core_t >= 0 && scyc >= core_t) begin
            // (the S0 core needs token and position only: in SOURCE mode the closed WFC's core_user at the start pulse is
            //  the previous job's, CONTROL_PIPE keeps the reference's pre-edge sample)
            for (k = 0; k < XW; k = k + 1) vmem[k] = word(0, core_p, core_k, k);
            kd <= {1'b1, NW'(core_k ^ 21'h155), 32'h3f800000 ^ core_p};
            core_t = -1;
        end
    end

    // ------------------------------------------------------------------ pipeline model (HIDDEN -> RESULT after L)
    integer pq_u [0:255], pq_p [0:255], pq_t [0:255], pq_g [0:255], pq_w = 0, pq_r = 0;
    integer m_k = -1, m_u, m_p, m_tk; integer hid_msgs = 0;
    // MODE 0 target for (user, pos) given the issued context
    function automatic integer tgt0(input integer uu, input integer pp);
        integer s, ok, x, best; begin
            best = -1;
            if (pp < plen - 1) best = 0;                     // a prompt position: not verified
            else if (pp == plen - 1) best = gtok[0];
            else begin
                for (s = 0; s < npass; s = s + 1) begin
                    if (pp >= pa_q[s] + 1 && pp <= pa_q[s] + 1 + pa_g[s]) begin
                        ok = 1;
                        for (x = pa_q[s] + 1; x <= pp; x = x + 1)
                            if (tok_at[uu * MAXP + x] != ((x == pa_q[s] + 1) ? gtok[pa_q[s] + 1 - plen] : pa_d[s * 5 + x - pa_q[s] - 2]))
                                ok = 0;
                        if (ok) best = pa_t[s * 6 + pp - pa_q[s] - 1];
                    end
                end
            end
            tgt0 = best;
        end
    endfunction
    integer tg;
    always @(posedge fclk) if (rst_n) begin
        rnd = mix(SEED * 7 + cyc, 32'h51ed2701);
        lo_r <= rnd[2:0] != 0;
        if (lo_v && lo_r) begin
            if (m_k < 0) begin
                if (lo_d[HDR_TYPE +: 4] != 4'd1 || lo_d[HDR_LEN +: 8] != XW || lo_d[FLIT]) begin
                    $display("MTP_S0 FAIL: S0 sent a non-HIDDEN header %h", lo_d[63:0]); $finish; end
                m_u = lo_d[HDR_USER +: 8] | (lo_d[HDR_USER_HI +: 2] << 8); m_p = lo_d[HDR_POS +: NW];
                m_tk = lo_d[HDR_TOK +: NW]; m_k = 0;
            end else begin
                if (lo_d[FLIT-1:0] !== word(0, m_p, m_tk, m_k)) begin
                    $display("MTP_S0 FAIL: HIDDEN payload word %0d of (u%0d, p%0d, t%0d) (VM / staging transport) got %h exp %h at %0d", m_k, m_u, m_p, m_tk, lo_d[63:0], word(0, m_p, m_tk, m_k) & 64'hffffffffffffffff, cyc);
                    $finish;
                end
                m_k = m_k + 1;
                if (m_k == XW) begin
                    if (!lo_d[FLIT]) begin $display("MTP_S0 FAIL: HIDDEN last"); $finish; end
                    // the issued context: position m_p of user m_u carries token m_tk
                    tok_at[m_u * MAXP + m_p] = m_tk;
                    ph[m_u * MAXP + m_p] = mix((m_p == 0) ? 32'd5 : ph[m_u * MAXP + m_p - 1], m_tk);
                    if (MODE == 0) tg = tgt0(m_u, m_p); else tg = htok(m_u, ph[m_u * MAXP + m_p]);
                    if (tg < 0) begin
                        $display("MTP_S0 FAIL: u%0d pos %0d issued with a context the golden never ran", m_u, m_p); $finish;
                    end
                    pq_u[pq_w % 256] = m_u; pq_p[pq_w % 256] = m_p; pq_g[pq_w % 256] = tg; pq_t[pq_w % 256] = cyc + L;
                    pq_w = pq_w + 1; m_k = -1; hid_msgs = hid_msgs + 1;
                end
            end
        end
        // RESULT out of the head, in issue order
        if (br_v && br_r) br_v <= 1'b0;
        if ((!br_v || br_r) && pq_r < pq_w && cyc >= pq_t[pq_r % 256]) begin
            br_v <= 1'b1;
            br_d <= 0;
            br_d[15:0] <= 16'h3a00;                                          // DEST 0 (S0), SRC 0x3a (head)
            br_d[HDR_TYPE +: 4] <= 4'd2;
            br_d[HDR_USER +: 8] <= pq_u[pq_r % 256]; br_d[HDR_USER_HI +: 2] <= pq_u[pq_r % 256] >> 8;
            br_d[HDR_POS +: NW] <= pq_p[pq_r % 256]; br_d[HDR_IDX +: NW] <= pq_g[pq_r % 256];
            br_d[HDR_VAL +: 32] <= 32'h40000000 + pq_g[pq_r % 256];
            pq_r = pq_r + 1;
        end
    end

    // ------------------------------------------------------------------ token-return link (R cycles), draft models
    reg [FLIT:0] tl_d [0:63]; integer tl_t [0:63]; integer tl_w = 0, tl_r = 0;
    integer dr_u [0:63], dr_t [0:63], dr_w = 0, dr_r = 0;                  // rows-ready events
    integer dq_u [0:63], dq_j [0:63], dq_k [0:63], dq_t [0:63], dq_w = 0, dq_r = 0;
    integer sd_y [0:15], sd_c [0:15], sd_s [0:15], sd_g [0:15];             // per user: seed (bonus, anchor, pass)
    integer drafts [0:16*5-1];
    integer seeds = 0, dh_steps = 0, drafts_flits = 0;
    integer su, sc, sy, sn, se, s;
    always @(posedge fclk) if (rst_n) begin
        rnd = mix(SEED * 13 + cyc, 32'h51ed2701);
        bt_r <= rnd[1:0] != 0 && (tl_w - tl_r) < 60;
        if (bt_v && bt_r) begin
            tl_d[tl_w % 64] = {1'b1, bt_d}; tl_t[tl_w % 64] = cyc + R; tl_w = tl_w + 1;
            if (bt_d[HDR_TYPE +: 4] == 4'd4) drafts_flits = drafts_flits + 1;
        end
        if (li_v && li_r) li_v <= 1'b0;
        if ((!li_v || li_r) && tl_r < tl_w && cyc >= tl_t[tl_r % 64]) begin
            li_v <= 1'b1; li_d <= tl_d[tl_r % 64]; tl_r = tl_r + 1;
        end
        // seeds -> the drafter (MODE 0: the golden pass with this anchor; MODE 1: truth with RHO)
        if (bs_v) begin
            su = bs_d[SW-1 -: USER_W]; sc = bs_d[3*NW+3 -: NW]; sn = bs_d[2*NW+3 -: NW]; sy = bs_d[NW+3 -: NW];
            seeds = seeds + 1;
            sd_y[su] = sy; sd_c[su] = sc;
            if (MODE == 0) begin
                sd_s[su] = -1;
                for (s = 0; s < npass; s = s + 1) if (pa_q[s] == sc) sd_s[su] = s;
                if (sd_s[su] < 0 || gtok[sc + 1 - plen] != sy) begin
                    $display("MTP_S0 FAIL: seed u%0d anchor %0d bonus %0d is not a golden pass", su, sc, sy); $finish;
                end
                for (k = 0; k < 5; k = k + 1) drafts[su * 5 + k] = pa_d[sd_s[su] * 5 + k];
            end else begin
                for (k = 0; k < 5; k = k + 1) begin
                    rnd = mix(SEED * 31 + cyc * 5 + k, 32'h51ed2701);
                    drafts[su * 5 + k] = ((rnd % 100 + 100) % 100 < RHO && sc + 2 + k < MAXP) ? tru[su * MAXP + sc + 2 + k]
                                         : (tru[su * MAXP + ((sc + 2 + k < MAXP) ? sc + 2 + k : 0)] + 1 + k) % V;
                end
            end
            if (sn != sc + 1 - sd_g[su]) begin
                $display("MTP_S0 FAIL: seed rows %0d (anchor %0d, last %0d)", sn, sc, sd_g[su]); $finish; end
            sd_g[su] = sc + 1;
            dr_u[dr_w % 64] = su; dr_t[dr_w % 64] = cyc + T_DRAFT; dr_w = dr_w + 1;
        end
        if (bw_v && bw_r) bw_v <= 1'b0;
        if ((!bw_v || bw_r) && dr_r < dr_w && cyc >= dr_t[dr_r % 64]) begin
            bw_v <= 1'b1; bw_d <= dr_u[dr_r % 64]; dr_r = dr_r + 1;
        end
        // draft-head steps: check the previous token, return d_j after T_HEAD
        if (bh_v) begin
            su = bh_d[DW-1 -: USER_W]; k = bh_d[NW +: 3]; sy = bh_d[NW-1:0];
            dh_steps = dh_steps + 1;
            if (k < 1 || k > 5 || sy != ((k == 1) ? sd_y[su] : drafts[su * 5 + k - 2])) begin
                $display("MTP_S0 FAIL: draft-head step u%0d j%0d prev %0d", su, k, sy); $finish; end
            dq_u[dq_w % 64] = su; dq_j[dq_w % 64] = k; dq_k[dq_w % 64] = drafts[su * 5 + k - 1];
            dq_t[dq_w % 64] = cyc + T_HEAD; dq_w = dq_w + 1;
        end
        if (bq_v && bq_r) bq_v <= 1'b0;
        if ((!bq_v || bq_r) && dq_r < dq_w && cyc >= dq_t[dq_r % 64]) begin
            bq_v <= 1'b1; bq_d <= {dq_u[dq_r % 64][USER_W-1:0], dq_j[dq_r % 64][2:0], dq_k[dq_r % 64][NW-1:0]};
            dq_r = dq_r + 1;
        end
    end

    // ------------------------------------------------------------------ checks: emitted tokens, steps
    integer emitted [0:15]; integer last_pos [0:15];
    integer acc_n [0:15]; integer last_close [0:15]; integer acc_tot = 0, acc_sum = 0, rej = 0, sq = 0, iss = 0;
    integer bq [0:15], bg [0:15];          // MODE 1 expected block (b, g) per user
    integer exa, ga, sa, xw;
    always @(posedge fclk) if (rst_n) begin
        if (wf_issue) iss = iss + 1;
        if (wf_reject) rej = rej + 1;
        if (wf_squash) sq = sq + 1;
        if (tok_valid && tok_pos >= plen - 1) begin
            u = tok_user;
            if (tok_pos != last_pos[u] + 1) begin
                $display("MTP_S0 FAIL: u%0d committed pos %0d after %0d", u, tok_pos, last_pos[u]); $finish; end
            last_pos[u] = tok_pos;
            if (tok_id != ((MODE == 0) ? gtok[tok_pos - plen + 1] : tru[u * MAXP + tok_pos + 1])) begin
                $display("MTP_S0 FAIL: u%0d pos %0d token %0d != greedy %0d", u, tok_pos, tok_id,
                         (MODE == 0) ? gtok[tok_pos - plen + 1] : tru[u * MAXP + tok_pos + 1]);
                $finish;
            end
            emitted[u] = emitted[u] + 1;
        end
        if (s_acc[2*NW+3+USER_W]) begin                                   // a step closed in the sequencer
            u = s_acc[2*NW+3 +: USER_W]; exa = s_acc[2*NW +: 3]; xw = s_acc[NW +: NW];
            acc_tot = acc_tot + 1; acc_sum = acc_sum + exa;
            if (MODE == 0) begin
                // the n-th closing of a user = golden pass n-1's (anchor + 1 + a), pass -1 = the prefill end
                k = acc_n[u];
                if (k == 0) begin
                    if (xw != plen - 1 || exa != 0) begin $display("MTP_S0 FAIL: prefill close u%0d at %0d a %0d", u, xw, exa); $finish; end
                end else begin
                    ga = (steps - 1 - (pa_q[k-1] + 1)) < 5 ? steps - 1 - (pa_q[k-1] + 1) : 5;
                    sa = (pa_a[k-1] < ga) ? pa_a[k-1] : ga;
                    if (xw != pa_q[k-1] + 1 + sa || exa != sa) begin
                        $display("MTP_S0 FAIL: u%0d step %0d closed at %0d a %0d, golden anchor %0d a %0d (g %0d)", u, k - 1,
                                 xw, exa, pa_q[k-1], pa_a[k-1], ga);
                        $finish;
                    end
                end
            end else begin
                // MODE 1: the prefix accept against the truth for the block the sequencer ran
                exa = 0;
                if (acc_n[u] > 0) while (exa < bg[u] && drafts[u * 5 + exa] == tru[u * MAXP + bq[u] + 1 + exa]) exa = exa + 1;
                if (s_acc[2*NW +: 3] != exa || xw != ((acc_n[u] == 0) ? plen - 1 : bq[u] + exa)) begin
                    $display("MTP_S0 FAIL: u%0d closed at %0d a %0d, expected %0d a %0d", u, xw, s_acc[2*NW +: 3],
                             bq[u] + exa, exa); $finish; end
                bq[u] = xw + 1; bg[u] = (xw + 1 >= steps) ? 0 : (steps - 1 - (xw + 1) < 5) ? steps - 1 - (xw + 1) : 5;
            end
            acc_n[u] = acc_n[u] + 1;
            last_close[u] = cyc;
        end
        // step watchdog: a speculative step closes within L + T_DRAFT + 6 x NUSR S0 intervals (< 3 L + T_DRAFT + 1500 NUSR); an autoregressive fallback
        // (drafts not used) takes (g + 1) L
        for (u = 0; u < NUSR && u < SEQ_MAXU; u = u + 1)
            if (emitted[u] < ngen && acc_n[u] > 0 && cyc - last_close[u] > 3 * L + T_DRAFT + 1500 * NUSR) begin
                $display("MTP_S0 FAIL: u%0d step stalled %0d cycles (autoregressive fallback or hang)", u, cyc - last_close[u]);
                $finish;
            end
        if (proto_fault || lnk_ft || tok_ft || vmx_ft || s_acc[2*NW+USER_W+4]) begin
            $display("MTP_S0 FAIL: fault wfc %0d lnk %0d tok %0d vmx %0d seq %0d", proto_fault, lnk_ft, tok_ft, vmx_ft,
                     s_acc[2*NW+USER_W+4]);
            $finish;
        end
    end

    // ------------------------------------------------------------------ cycle measurements (sequencer)
    integer t_rin [0:NUSR*MAXP-1]; integer t_qin [0:15], t_win [0:15];
    integer n_sdm = 0, x_sdm = 0, n_dh = 0, s_dh = 0, n_rw = 0, s_rw = 0, n_rl = 0, s_rl = 0, n_fw = 0, s_fw = 0, min_fw = 99999;
    integer mu, mp, last_rin_u;
    always @(posedge fclk) if (rst_n) begin
        if (br_v && br_r) t_rin[br_d[HDR_USER +: 8] * MAXP + br_d[HDR_POS +: NW]] = cyc;
        if (bw_v && bw_r) t_win[bw_d] = cyc;
        if (bq_v && bq_r) t_qin[bq_d[DW-1 -: USER_W]] = cyc;
        if (bs_v) begin n_sdm = n_sdm + 1; x_sdm = x_sdm + cyc - t_rin[bs_d[SW-1 -: USER_W] * MAXP + bs_d[3*NW+3 -: NW]]; end
        if (bh_v) begin
            mu = bh_d[DW-1 -: USER_W];
            if (bh_d[NW +: 3] == 1) begin n_rw = n_rw + 1; s_rw = s_rw + cyc - t_win[mu]; end
            else begin n_dh = n_dh + 1; s_dh = s_dh + cyc - t_qin[mu]; end
        end
        if (bt_v && bt_r) begin
            mu = bt_d[HDR_USER +: 8]; mp = bt_d[HDR_POS +: NW];
            if (bt_d[HDR_TYPE +: 4] == 4'd4) begin n_rl = n_rl + 1; s_rl = s_rl + cyc - t_qin[mu]; end
            else if (cyc - t_rin[mu * MAXP + mp] < min_fw) min_fw = cyc - t_rin[mu * MAXP + mp];
        end
    end

    // ------------------------------------------------------------------ setup + finish
    task cfgw_put(input [1:0] sel, input integer uu, input integer pp, input integer vv);
        begin
            @(negedge fclk); cfgw = {1'b1, sel, USER_W'(uu), NW'(pp), NW'(vv)};
            @(negedge fclk); cfgw = 0;
        end
    endtask
    integer done_all, nspec, ar_users;
    initial begin
        if (MODE == 0) begin
            $readmemh("trace.hex", trc);
            plen = trc[0]; ngen = trc[1]; npass = trc[2]; k = 3;
            for (i = 0; i < plen; i = i + 1) begin prompt[i] = trc[k]; k = k + 1; end
            for (i = 0; i < ngen; i = i + 1) begin gtok[i] = trc[k]; k = k + 1; end
            for (i = 0; i < npass; i = i + 1) begin
                pa_q[i] = trc[k]; pa_a[i] = trc[k+1]; pa_g[i] = trc[k+2];
                for (j = 0; j < 5; j = j + 1) pa_d[i*5+j] = trc[k+3+j];
                for (j = 0; j < 6; j = j + 1) pa_t[i*6+j] = trc[k+8+j];
                k = k + 14;
            end
        end else begin
            plen = PLEN_H; ngen = NGEN_H; npass = 0;
            for (u = 0; u < NUSR; u = u + 1) begin
                for (i = 0; i < plen; i = i + 1) begin
                    rnd = mix(SEED * 101 + u * 17 + i, 32'h51ed2701); tru[u * MAXP + i] = (rnd % V + V) % V;
                    ph[u * MAXP + i] = mix(i == 0 ? 32'd5 : ph[u * MAXP + i - 1], tru[u * MAXP + i]);
                end
                for (i = plen - 1; i < plen + ngen && i + 1 < MAXP; i = i + 1) begin
                    tru[u * MAXP + i + 1] = htok(u, ph[u * MAXP + i]);
                    ph[u * MAXP + i + 1] = mix(ph[u * MAXP + i], tru[u * MAXP + i + 1]);
                end
            end
        end
        steps = plen + ngen - 1;
        for (u = 0; u < 16; u = u + 1) begin emitted[u] = 0; last_pos[u] = plen - 2; acc_n[u] = 0; sd_g[u] = 0; bq[u] = 0; bg[u] = 0; end
        // static configuration before reset release
        cfgw_put(2'd0, 0, 0, NUSR); cfgw_put(2'd1, 0, 0, plen); cfgw_put(2'd2, 0, 0, ngen);
        for (u = 0; u < NUSR; u = u + 1) for (i = 0; i < plen; i = i + 1)
            cfgw_put(2'd3, u, i, (MODE == 0) ? prompt[i] : tru[u * MAXP + i]);
        repeat (8) @(posedge fclk);
        rst_n = 1;
        done_all = 0;
        while (!done_all && cyc < MAXC) begin
            @(posedge fclk);
            done_all = 1;
            for (u = 0; u < NUSR; u = u + 1) if (emitted[u] < ngen) done_all = 0;
        end
        repeat (200) @(posedge fclk);
        if (!done_all) begin $display("MTP_S0 FAIL: timeout at %0d cycles (emitted u0 %0d)", cyc, emitted[0]); $finish; end
        // speculative passes: every MTP user closes 1 (prefill) + golden passes (MODE 0) steps
        nspec = 0; ar_users = 0;
        for (u = 0; u < NUSR; u = u + 1) begin
            if (u < SEQ_MAXU) begin
                nspec = nspec + acc_n[u];
                if (MODE == 0 && acc_n[u] != npass + 1) begin
                    $display("MTP_S0 FAIL: u%0d closed %0d steps, golden %0d passes + prefill", u, acc_n[u], npass); $finish; end
            end else begin
                ar_users = ar_users + 1;
                if (acc_n[u] != 0) begin $display("MTP_S0 FAIL: pass-through user closed steps"); $finish; end
            end
        end
        $display("MTP_S0 PASS mode=%0d users=%0d (ar %0d) plen=%0d ngen=%0d steps_closed=%0d accepted=%0d seeds=%0d dh=%0d draft_flits=%0d issues=%0d rejects=%0d squashed=%0d hidden=%0d s0_starts=%0d cycles=%0d",
                 MODE, NUSR, ar_users, plen, ngen, nspec, acc_sum, seeds, dh_steps, drafts_flits, iss, rej, sq, hid_msgs,
                 core_starts, cyc);
        $display("MTP_S0_CYC seq_forward_min=%0d seed_after_close=%0.2f rows_to_dh1=%0.2f dh_result_to_next=%0.2f last_dh_to_draft_flit=%0.2f (fast cycles, bench adapters included: +2 in, +1 out)",
                 min_fw, 1.0 * x_sdm / (n_sdm > 0 ? n_sdm : 1), 1.0 * s_rw / (n_rw > 0 ? n_rw : 1), 1.0 * s_dh / (n_dh > 0 ? n_dh : 1),
                 1.0 * s_rl / (n_rl > 0 ? n_rl : 1));
        $finish;
    end
endmodule
