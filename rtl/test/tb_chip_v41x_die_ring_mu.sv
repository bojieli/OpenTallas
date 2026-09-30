`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11: the ring key layout in the adopted V4.1 die top at FULL ring capacity, two
// users interleaved.  Derived from tb_chip_v41x_die_ring.sv (one step, one user,
// C = 1,024 rings); that bench and its record are unchanged.
//
// The die is built with IDX_RING = 1, IDX_RING_RSB = RSB, IDX_RING_RTAIL = RTAIL
// (C = RSB x 1,024 + RTAIL slots a region a stack: 65,568 at RSB 64, RTAIL 32; a
// region is UBLK = 1,090 blocks) and IDX_RING_MU = 1: the die keys the index-key
// user base from the step's 10-bit user id (host_user): user u's key slice starts
// at sector u x IKH_SLICE, and its key region r (r the core's VM key region) at
// block u x IKH_SLICE / 128 + r x UBLK -- at full shape (one indexed layer a die,
// IKH_SLICE = 1,090 x 128) the region is user x 1,090 blocks.
//
// NSTEPS decode steps (plusargs +DIRi +USERi +TOKENi +POSi +EXPECTi +NPRIMEi +PFIRSTi,
// i < 4) run back to back in host mode with no reset between them.  Before step i
// the bench loads that step's golden state into the ONE vector memory and the ONE
// host-mode KV slice (a context switch the die does not implement in host mode),
// and its Engram primes.  The index keys are NOT reloaded: a user's ring is placed
// from the image at its first step only; at every later step of that user the bench
// first compares the user's ring as it stands in HBM (written by the die's ring
// path in the user's earlier steps, left alone by the other user's steps) against
// the ring placement of this step's golden key image (key_carry mismatches), then
// the step runs and is checked bit for bit (every logit, the whole vector memory,
// the whole KV cache against the ISA model of that step; token against golden).
// ---------------------------------------------------------------------------
module tb_chip_v41x_die_ring_mu #(
    parameter integer RSB = 64, RTAIL = 32,
    parameter integer KEY_USERS = 3,
    parameter integer IKH_SLICE = 4 * 1090 * 128,   // sectors a user slice: four VM key regions of UBLK blocks
    parameter integer K_MEM = 1 << 21
) (input wire clk);
    localparam integer RING = 1;
    localparam integer W = 16, VOCAB = 4040, KV_WORDS = 32768, VM_ELEMS = 65536;
    localparam integer IKH_WORDS = 1 << 18, HMEM = 1 << 20, QROM_WORDS = 1 << 16;
    localparam integer BL = 16, QLB = 272, PW = 512 + 3 + 32;
    localparam integer C = RSB * 1024 + RTAIL;
    localparam integer UBLK = RSB * 17 + ((RTAIL != 0) ? 1 + (RTAIL + 63) / 64 : 0);
    localparam integer KV_SBASE = KEY_USERS * IKH_SLICE;   // the die's map

    reg rst_n = 1'b0, start = 1'b0;
    reg [15:0] token, pos, expect_tok;
    reg [9:0] user;
    reg prime_v = 1'b0, prime_first = 1'b0;
    reg [11:0] prime_cid = 0;
    reg [23:0] cfg [0:15];
    reg [15:0] qlead, qrate;
    wire done;
    wire [15:0] next_token;
    wire [31:0] next_val, cycles;
    wire [7:0] fault;
    wire [4:0] unit_busy; wire [2:0] issue_unit;
    wire [31:0] qs_fetched, qs_consumed, kb_records, kb_writes, kb_highwater, kb_stalls, hbm_w_reads, rtr_drops;
    wire [3:0] qs_why;
    wire [63:0] hbm_refreshes;
    wire [31:0] kv_ops, kv_words, kv_sw, kv_ref, kv_wqh, kv_hold, kv_grants; wire [4:0] kv_code;

    ot_chip_v41x_die #(.RANK(0), .IDX_RING(1), .IDX_RING_RSB(RSB), .IDX_RING_RTAIL(RTAIL), .IDX_RING_MU(1),
                       .KEY_USERS(KEY_USERS), .IKH_SLICE(IKH_SLICE), .K_MEM(K_MEM)) dut (
        .clk(clk), .rst_n(rst_n),
        .host_mode(1'b1), .host_start(start), .host_token(token), .host_pos(pos), .host_user(user), .host_entry(14'd0),
        .host_prime_v(prime_v), .host_prime_first(prime_first), .host_prime_cid(prime_cid),
        .core_done(done), .core_next_token(next_token), .core_next_val(next_val), .core_cycles(cycles),
        .core_acc_n(),
        .cfg_ik_base(cfg[0]), .cfg_me_xs(cfg[1][3:0]), .cfg_q_base(24'd0), .cfg_q_lbase(12'd0),
        .cfg_q_lead(qlead), .cfg_q_rate(qrate),
        .cfg_users(8'd1), .cfg_prompt_len(16'd0), .cfg_gen_len(16'd0),
        .pr_re(), .pr_user(), .pr_pos(), .pr_q(16'd0),
        .tok_valid(), .tok_user(), .tok_pos(), .tok_id(), .users_done(),
        .rcfg_we(1'b0), .rcfg_dest(8'd0), .rcfg_mask(3'd0),
        .coll_go(1'b0), .coll_mode(1'b0), .coll_tag(32'd0), .coll_src(12'd0), .coll_n(12'd0), .coll_dst(12'd0),
        .coll_busy(),
        .ucie_tx_valid(), .ucie_tx_ready(1'b1), .ucie_tx_data(), .ucie_tx_last(),
        .ucie_rx_valid(1'b0), .ucie_rx_ready(), .ucie_rx_data(512'd0), .ucie_rx_last(1'b0),
        .ucie_ctx_valid(), .ucie_ctx_ready(1'b1), .ucie_ctx_rec(), .ucie_ccr_in(2'b00),
        .ucie_crx_valid(1'b0), .ucie_crx_rec({PW{1'b0}}), .ucie_ccr_out(),
        .ucie_rl_tx_valid(), .ucie_rl_tx_rec(), .ucie_rl_rx_valid(4'd0), .ucie_rl_rx_rec({4*PW{1'b0}}),
        .bl_tx_valid(), .bl_tx_ready(1'b1), .bl_tx_data(), .bl_tx_last(),
        .bl_rx_valid(1'b0), .bl_rx_ready(), .bl_rx_data(512'd0), .bl_rx_last(1'b0),
        .bl_ctx_valid(), .bl_ctx_ready(2'b11), .bl_ctx_rec(), .bl_ccr_in(4'd0),
        .bl_crx_valid(2'b00), .bl_crx_rec({2*PW{1'b0}}), .bl_ccr_out(),
        .fault(fault), .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qs_fetched(qs_fetched), .qs_consumed(qs_consumed), .qs_why(qs_why),
        .kb_records(kb_records), .kb_writes(kb_writes), .kb_highwater(kb_highwater), .kb_stalls(kb_stalls),
        .hbm_refreshes(hbm_refreshes), .hbm_w_reads(hbm_w_reads), .rtr_drops(rtr_drops),
        .kv_ops(kv_ops), .kv_words(kv_words), .kv_sectors_written(kv_sw), .kv_refetches(kv_ref),
        .kv_wq_high(kv_wqh), .kv_hold_cycles(kv_hold), .kv_hbm_grants(kv_grants), .kv_fault_code(kv_code));

    // -- steps -------------------------------------------------------------------------------
    reg [8*512-1:0] sdir [0:3];
    integer suser [0:3], stok [0:3], spos [0:3], sexp [0:3], snp [0:3], spf [0:3];
    integer nsteps = 1, step = 0;
    reg [1:0] seen = 2'b00;       // users (step-user index 0/1 by first appearance) whose ring is placed
    integer seen_user [0:1];
    // -- images ------------------------------------------------------------------------------
    reg [BL*QLB-1:0] qrom [0:QROM_WORDS-1];       // independent delivered-word oracle only
    reg [31:0] e_vm [0:VM_ELEMS-1];
    reg [31:0] e_kv [0:KV_WORDS*W-1];
    reg [31:0] e_lg [0:VOCAB-1];
    reg [31:0] lg   [0:VOCAB-1];
    reg [31:0] kvimg [0:KV_WORDS*W-1];
    reg [255:0] ikimg [0:IKH_WORDS-1];
    reg [15:0] prime [0:7];
    reg [8*512-1:0] dir;
    integer i, cyc = 0, n_prime = 0, pfirst = 0, prime_i = 0, bad_lg, bad_vm, bad_kv;
    reg trace = 1'b0;
    initial begin
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if (!$value$plusargs("NSTEPS=%d", nsteps)) nsteps = 1;
        if (!$value$plusargs("DIR0=%s", sdir[0])) sdir[0] = ".";
        if (!$value$plusargs("DIR1=%s", sdir[1])) sdir[1] = ".";
        if (!$value$plusargs("DIR2=%s", sdir[2])) sdir[2] = ".";
        if (!$value$plusargs("DIR3=%s", sdir[3])) sdir[3] = ".";
        if (!$value$plusargs("USER0=%d", suser[0])) suser[0] = 0;
        if (!$value$plusargs("USER1=%d", suser[1])) suser[1] = 0;
        if (!$value$plusargs("USER2=%d", suser[2])) suser[2] = 0;
        if (!$value$plusargs("USER3=%d", suser[3])) suser[3] = 0;
        if (!$value$plusargs("TOKEN0=%d", stok[0])) stok[0] = 0;
        if (!$value$plusargs("TOKEN1=%d", stok[1])) stok[1] = 0;
        if (!$value$plusargs("TOKEN2=%d", stok[2])) stok[2] = 0;
        if (!$value$plusargs("TOKEN3=%d", stok[3])) stok[3] = 0;
        if (!$value$plusargs("POS0=%d", spos[0])) spos[0] = 0;
        if (!$value$plusargs("POS1=%d", spos[1])) spos[1] = 0;
        if (!$value$plusargs("POS2=%d", spos[2])) spos[2] = 0;
        if (!$value$plusargs("POS3=%d", spos[3])) spos[3] = 0;
        if (!$value$plusargs("EXPECT0=%d", sexp[0])) sexp[0] = 0;
        if (!$value$plusargs("EXPECT1=%d", sexp[1])) sexp[1] = 0;
        if (!$value$plusargs("EXPECT2=%d", sexp[2])) sexp[2] = 0;
        if (!$value$plusargs("EXPECT3=%d", sexp[3])) sexp[3] = 0;
        if (!$value$plusargs("NPRIME0=%d", snp[0])) snp[0] = 0;
        if (!$value$plusargs("NPRIME1=%d", snp[1])) snp[1] = 0;
        if (!$value$plusargs("NPRIME2=%d", snp[2])) snp[2] = 0;
        if (!$value$plusargs("NPRIME3=%d", snp[3])) snp[3] = 0;
        if (!$value$plusargs("PFIRST0=%d", spf[0])) spf[0] = 0;
        if (!$value$plusargs("PFIRST1=%d", spf[1])) spf[1] = 0;
        if (!$value$plusargs("PFIRST2=%d", spf[2])) spf[2] = 0;
        if (!$value$plusargs("PFIRST3=%d", spf[3])) spf[3] = 0;
        if (!$value$plusargs("QLEAD=%d", qlead)) qlead = 512;
        if (!$value$plusargs("QRATE=%d", qrate)) qrate = 0;
        if (nsteps < 1 || nsteps > 4) $fatal(1, "NSTEPS 1..4");
        dir = sdir[0];
        // tile ROM banks (the via mask; one model: every step's images carry the same ROMs, checked by the tool)
        $readmemh({dir, "/prog.hex"}, dut.u_tile.prog);
        $readmemh({dir, "/wrom.hex"}, dut.u_tile.wrom);
        $readmemh({dir, "/hrom.hex"}, dut.u_tile.hrom);
        $readmemh({dir, "/hbank.hex"}, dut.u_tile.hbank);
        $readmemh({dir, "/mbank.hex"}, dut.u_tile.mbank);
        $readmemh({dir, "/erom.hex"}, dut.u_tile.erom);
        $readmemh({dir, "/crom.hex"}, dut.u_tile.crom);
        $readmemh({dir, "/qlist.hex"}, dut.u_tile.qlist);
        $readmemh({dir, "/cfg.hex"}, cfg);
        $readmemh({dir, "/qrom.hex"}, qrom);
        for (i = 0; i < HMEM; i = i + 1) dut.g_hbm[0].u_hbm.g_w.u_w.mem[i] = 256'd0;
        $readmemh({dir, "/hbm_q.hex"}, dut.g_hbm[0].u_hbm.g_w.u_w.mem);
    end

    // -- per-step loading (bench-side context switch) ---------------------------------------------
    integer ring_regions = 0, ring_keys = 0, ring_maxn = 0, carry_bad = 0, carry_checked = 0;
    reg [511:0] kvw;
    integer kq;
    function automatic [255:0] kget(input integer s, input integer a);
        case (s)
            0: kget = dut.g_hbm[0].u_hbm.u_k.mem[a];
            1: kget = dut.g_hbm[1].u_hbm.u_k.mem[a];
            2: kget = dut.g_hbm[2].u_hbm.u_k.mem[a];
            default: kget = dut.g_hbm[3].u_hbm.u_k.mem[a];
        endcase
    endfunction
    task automatic kset(input integer s, input integer a, input [255:0] d);
        case (s)
            0: dut.g_hbm[0].u_hbm.u_k.mem[a] = d;
            1: dut.g_hbm[1].u_hbm.u_k.mem[a] = d;
            2: dut.g_hbm[2].u_hbm.u_k.mem[a] = d;
            default: dut.g_hbm[3].u_hbm.u_k.mem[a] = d;
        endcase
    endtask
    // place (check = 0) or compare (check = 1) user u's rings against this step's golden key image
    task automatic ring_image(input integer u, input integer check);
        integer r, t, cnt, qs, q, cs, ss, rcs, rss, sl, ub;
        reg [255:0] z;
        begin
            for (r = 0; (r + 1) * 2176 <= IKH_WORDS && (r + 1) * UBLK * 128 <= IKH_SLICE; r = r + 1) begin
                cnt = 0;
                for (t = 0; t < 1024; t = t + 1) begin
                    cs = (17 * r + 1 + t / 64) * 128 + 2 * (t % 64); ss = 17 * r * 128 + t / 8;
                    if (ikimg[cs] != 0 || ikimg[cs + 1] != 0 || ikimg[ss][32 * (t % 8) +: 32] != 0) cnt = t + 1;
                end
                if (cnt != 0 && !check) begin
                    ring_regions = ring_regions + 1; ring_keys = ring_keys + cnt;
                    if (cnt > ring_maxn) ring_maxn = cnt;
                end
                qs = (cnt / 32) * 8;
                ub = u * (IKH_SLICE / 128) + r * UBLK;
                for (t = 0; t < cnt; t = t + 1) begin
                    q = (t < qs) ? 0 : (t < 2 * qs) ? 1 : (t < 3 * qs) ? 2 : 3;
                    cs = (17 * r + 1 + t / 64) * 128 + 2 * (t % 64); ss = 17 * r * 128 + t / 8;
                    sl = t % C;
                    rcs = (ub + 17 * (sl / 1024) + 1 + (sl % 1024) / 64) * 128 + 2 * (sl % 64);
                    rss = (ub + 17 * (sl / 1024)) * 128 + (sl % 1024) / 8;
                    if (check) begin
                        carry_checked = carry_checked + 1;
                        z = kget(q, rss);
                        if (kget(q, rcs) !== ikimg[cs] || kget(q, rcs + 1) !== ikimg[cs + 1] ||
                            z[32 * (sl % 8) +: 32] !== ikimg[ss][32 * (t % 8) +: 32]) begin
                            if (carry_bad < 5) $display("KEYCARRY user=%0d region=%0d row=%0d stack=%0d mismatch", u, r, t, q);
                            carry_bad = carry_bad + 1;
                        end
                    end else begin
                        kset(q, rcs, ikimg[cs]); kset(q, rcs + 1, ikimg[cs + 1]);
                        z = kget(q, rss); z[32 * (sl % 8) +: 32] = ikimg[ss][32 * (t % 8) +: 32]; kset(q, rss, z);
                    end
                end
            end
        end
    endtask
    task automatic load_step(input integer s);
        integer ui;
        begin
            dir = sdir[s];
            token = 16'(stok[s]); pos = 16'(spos[s]); expect_tok = 16'(sexp[s]); user = 10'(suser[s]);
            n_prime = snp[s]; pfirst = spf[s]; prime_i = 0;
            for (i = 0; i < VM_ELEMS; i = i + 1) dut.u_tile.vm[i] = 32'd0;
            $readmemh({dir, "/vm_init.hex"}, dut.u_tile.vm);
            $readmemh({dir, "/kv.hex"}, kvimg);
            $readmemh({dir, "/prime.hex"}, prime);
            $readmemh({dir, "/expect_vm.hex"}, e_vm);
            $readmemh({dir, "/expect_kv.hex"}, e_kv);
            $readmemh({dir, "/expect_logits.hex"}, e_lg);
            for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
            for (i = 0; i < IKH_WORDS; i = i + 1) ikimg[i] = 256'd0;
            $readmemh({dir, "/ikhbm.hex"}, ikimg);
            // the golden-prefilled KV into the host-mode KV slice: word U on stack U mod 4,
            // sectors KV_SBASE + 2 (U >> 2) + {0, 1}
            for (i = 0; i < KV_WORDS; i = i + 1) begin
                for (kq = 0; kq < W; kq = kq + 1) kvw[32*kq +: 32] = kvimg[i * W + kq];
                kset(i % 4, KV_SBASE + 2*(i/4), kvw[255:0]);
                kset(i % 4, KV_SBASE + 2*(i/4) + 1, kvw[511:256]);
            end
            ui = (seen[0] && seen_user[0] == suser[s]) ? 0 : (seen[1] && seen_user[1] == suser[s]) ? 1 : -1;
            if (ui < 0) begin
                if (!seen[0]) begin seen[0] = 1'b1; seen_user[0] = suser[s]; end
                else begin seen[1] = 1'b1; seen_user[1] = suser[s]; end
                ring_image(suser[s], 0);
                $display("STEP%0d user=%0d keys placed from the image (first step of this user)", s, suser[s]);
            end else begin
                ring_image(suser[s], 1);
                $display("STEP%0d user=%0d key_carry checked=%0d mismatches=%0d", s, suser[s], carry_checked, carry_bad);
            end
        end
    endtask
    wire [47:0] ring_migs = dut.u_tile.g_kb_ring.u_kb.dbg_migrations;
    wire [47:0] ring_copied = dut.u_tile.g_kb_ring.u_kb.dbg_copied_sectors;
    function automatic [511:0] hbm_kv(input integer u);
        hbm_kv = {kget(u % 4, KV_SBASE + 2*(u/4) + 1), kget(u % 4, KV_SBASE + 2*(u/4))};
    endfunction
    // the attention gate: cycles an attention-class ME op was ready to issue but held for kv_ok, and
    // attention issues (each only with kv_ok high: the prefetch faults on any read of an incomplete slot)
    integer att_hold = 0, att_issue = 0;
    always @(posedge clk)
        if (dut.u_tile.u_core.st == 4'd6 && !dut.u_tile.u_core.d_skip && dut.u_tile.u_core.d_unit == 3'd1 &&
            dut.u_tile.u_core.me_cls == 2'd1 && dut.u_tile.u_core.waited && dut.u_tile.u_core.unit_ready &&
            dut.u_tile.u_core.q_gate) begin
            if (!dut.u_tile.u_core.kv_gate) att_hold <= att_hold + 1;
            else att_issue <= att_issue + 1;
        end

    // -- observation: logits (the one unwritten matrix-vector op), QE delivered words ---------------
    integer q, l;
    always @(posedge clk)
        if (dut.u_tile.me_ov && dut.u_tile.vw_me_we == 0)
            for (q = 0; q < 4; q = q + 1)
                for (l = 0; l < W; l = l + 1)
                    if (dut.u_tile.me_omask[q*W + l] && ({dut.u_tile.me_oaddr[q*24 +: 12], 4'b0} + l) < VOCAB)
                        lg[{dut.u_tile.me_oaddr[q*24 +: 12], 4'b0} + l] <= dut.u_tile.me_odata[32*(q*W + l) +: 32];
    reg qchk_v; reg [23:0] qchk_a;
    integer q_bad = 0, q_words = 0, q_ops = 0;
    always @(posedge clk) begin
        qchk_v <= dut.u_tile.qrom_re; qchk_a <= dut.u_tile.qrom_addr;
        if (qchk_v) begin
            q_words <= q_words + 1;
            if (dut.u_tile.qrom_q !== qrom[qchk_a[15:0]]) begin
                if (q_bad < 3) $display("QBAD addr=%0d got=%h expected=%h", qchk_a, dut.u_tile.qrom_q, qrom[qchk_a[15:0]]);
                q_bad = q_bad + 1;
            end
        end
        if (dut.u_tile.qd_v) q_ops <= q_ops + 1;
    end

    // the core's attention KV handshake reaches the die (descriptors announced)
    integer kvd_n = 0;
    always @(posedge clk) if (dut.kvd_v) kvd_n <= kvd_n + 1;
    integer busy_me = 0, busy_su = 0, busy_qe = 0, busy_xu = 0, busy_he = 0, all_idle = 0;
    always @(posedge clk) if (dut.u_tile.u_core.st != 0) begin
        if (unit_busy[0]) busy_me <= busy_me + 1;
        if (unit_busy[1]) busy_su <= busy_su + 1;
        if (unit_busy[2]) busy_qe <= busy_qe + 1;
        if (unit_busy[3]) busy_xu <= busy_xu + 1;
        if (unit_busy[4]) busy_he <= busy_he + 1;
        if (unit_busy == 0) all_idle <= all_idle + 1;
    end

    task print_counters;
        begin
            $display("XCNT unit=he ops=%0d elems=%0d", dut.u_tile.u_core.g_he_x.u_he.dbg_ops,
                     dut.u_tile.u_core.g_he_x.u_he.dbg_elems);
            $display("XCNT unit=me ops=%0d elems=%0d", dut.u_tile.u_core.g_me_x.u_mw.dbg_ops,
                     dut.u_tile.u_core.g_me_x.u_mw.dbg_elems);
            $display("XCNT unit=att ops=%0d elems=%0d", dut.u_tile.u_core.g_att_x.u_att.dbg_ops,
                     dut.u_tile.u_core.g_att_x.u_att.dbg_elems);
            $display("XCNT unit=su ops=%0d elems=%0d", dut.u_tile.u_core.g_su_x.u_su.dbg_ops,
                     dut.u_tile.u_core.g_su_x.u_su.dbg_elems);
            $display("XCNT unit=sel ops=%0d elems=%0d reps=%0d", dut.u_tile.u_core.g_xu_x.u_xu.dbg_sel_ops,
                     dut.u_tile.u_core.g_xu_x.u_xu.dbg_sel_elems, dut.u_tile.u_core.g_xu_x.u_xu.dbg_sel_reps);
            $display("XCNT unit=eg ops=%0d elems=%0d", dut.u_tile.u_core.g_xu_x.u_xu.dbg_eg_ops,
                     dut.u_tile.u_core.g_xu_x.u_xu.dbg_eg_elems);
            $display("XCNT unit=idx ops=%0d elems=%0d", dut.u_tile.u_core.g_idx_x.g_pool.u_idx.dbg_ops,
                     dut.u_tile.u_core.g_idx_x.g_pool.u_idx.dbg_elems);
            $display("XCNT unit=idx_hbm ops=%0d elems=%0d", dut.u_tile.u_core.g_idx_x.g_pool.u_idx.dbg_keys_streamed,
                     dut.u_tile.u_core.g_idx_x.g_pool.u_idx.dbg_hbm_beats);
            $display("XCNT unit=idx_fused ops=%0d elems=%0d", dut.u_tile.u_core.g_idx_x.g_pool.u_idx.dbg_keys_scored,
                     dut.u_tile.u_core.g_idx_x.g_pool.u_idx.dbg_headsums_fused);
            $display("XCNT unit=idx_kwr ops=%0d elems=%0d", dut.u_tile.u_core.g_idx_x.g_pool.u_kwr.dbg_keys,
                     dut.u_tile.u_core.g_idx_x.g_pool.u_kwr.dbg_keys);
            if (RING != 0)
                $display("IDXRING regions=%0d preloaded_keys=%0d max_region_keys=%0d migrations=%0d copied_sectors=%0d",
                         ring_regions, ring_keys, ring_maxn, ring_migs, ring_copied);
            $display("IDXHBMWR records=%0d writes=%0d highwater=%0d read_stalls=%0d writer_stalls=%0d refreshes=%0d refpb=3",
                     kb_records, kb_writes, kb_highwater, dut.u_tile.kb_read_stalls, dut.u_tile.kb_writer_stalls,
                     hbm_refreshes);
        end
    endtask

    reg [31:0] kv_e;
    integer drain = 0, t0 = 0, all_ok = 1;
    reg loaded = 1'b0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        prime_v <= 1'b0;
        start <= 1'b0;
        if (!loaded) begin load_step(step); loaded = 1'b1; t0 = cyc; end
        if (cyc >= t0 + 8 && prime_i < n_prime) begin
            prime_v <= 1'b1; prime_cid <= prime[prime_i][11:0]; prime_first <= (prime_i == 0) && pfirst;
            prime_i <= prime_i + 1;
        end
        if (cyc == t0 + 30) start <= 1'b1;
        if (trace && issue_unit != 0)
            $display("ISSUE cyc=%0d pc=%0d unit=%0d", cycles, dut.u_tile.u_core.pc, issue_unit);
        if (cyc > t0 + 64 && done && drain == 0) drain <= 1;
        if (drain != 0 && drain < 4000) drain <= drain + 1;      // the KV write queue drains to HBM
        if (drain == 4000) begin
            print_counters();
            bad_lg = 0; bad_vm = 0; bad_kv = 0;
            for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_lg[i]) begin
                if (bad_lg < 5) $display("logit %0d rtl %h expect %h", i, lg[i], e_lg[i]);
                bad_lg = bad_lg + 1;
            end
            for (i = 0; i < VM_ELEMS; i = i + 1) if (dut.u_tile.vm[i] !== e_vm[i]) begin
                if (bad_vm < 10) $display("vm %0d rtl %h expect %h", i, dut.u_tile.vm[i], e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            for (i = 0; i < KV_WORDS * W; i = i + 1) begin
                if (i % W == 0) kvw = hbm_kv(i / W);
                kv_e = kvw[32*(i % W) +: 32];
                if (kv_e !== e_kv[i]) begin
                    if (bad_kv < 10) $display("kv %0d rtl %h expect %h", i, kv_e, e_kv[i]);
                    bad_kv = bad_kv + 1;
                end
            end
            $display("HDC41 step=%0d user=%0d token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d key_carry_mismatch=%0d",
                     step, user, token, pos, next_token, expect_tok, cycles, fault[0], bad_lg, bad_vm, bad_kv, carry_bad);
            $display("UTIL me_busy=%0d su_busy=%0d qe_busy=%0d xu_busy=%0d he_busy=%0d all_idle=%0d", busy_me,
                     busy_su, busy_qe, busy_xu, busy_he, all_idle);
            $display("QSTREAM q_ops=%0d q_words=%0d q_bad=%0d qs_fault=%0d qs_why=%0d fetched=%0d consumed=%0d hbm_reads=%0d",
                     q_ops, q_words, q_bad, fault[1], qs_why, qs_fetched, qs_consumed, hbm_w_reads);
            $display("DIE fault=%b rtr_drops=%0d kv_descriptors=%0d", fault, rtr_drops, kvd_n);
            $display("KVHBM ops=%0d words=%0d sectors_written=%0d refetches=%0d wq_high=%0d hold_cycles=%0d grants=%0d code=%b att_issue=%0d att_held_cycles=%0d",
                     kv_ops, kv_words, kv_sw, kv_ref, kv_wqh, kv_hold, kv_grants, kv_code, att_issue, att_hold);
            if (!(next_token == expect_tok && fault == 8'd0 && bad_lg == 0 && bad_vm == 0 && bad_kv == 0 && q_bad == 0 &&
                  carry_bad == 0)) all_ok = 0;
            $display("STEP%0d %s", step, (next_token == expect_tok && fault == 8'd0 && bad_lg == 0 && bad_vm == 0 &&
                                         bad_kv == 0 && q_bad == 0 && carry_bad == 0) ? "PASS" : "FAIL");
            drain <= 0;
            if (step + 1 == nsteps) begin
                if (all_ok != 0) $display("PASS"); else $display("FAIL");
                $finish;
            end
            step <= step + 1; loaded = 1'b0;
        end
        if (cyc > 80000000) begin
            $display("TIMEOUT pc=%0d st=%0d", dut.u_tile.u_core.pc, dut.u_tile.u_core.st);
            $finish;
        end
    end
endmodule
