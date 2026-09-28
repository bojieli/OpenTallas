`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Smoke bench of the adopted V4.1 layer die top (rtl/chip/ot_chip_v41x_die.sv):
// one reduced DeepSeek-V4.1 decode step at +POS for +TOKEN through the die --
// the core tile's ROM banks and vector memory, the die's KV staging, the QE
// weights streamed from HBM stack W_STACK's weight port, the pooled indexer's
// keys read and written through all four HBM3E stack interfaces -- from the
// golden-prefilled state, then a bit-exact check of every logit, the whole
// vector memory and the whole KV cache against the ISA-level model.
//
// The images, the plusargs and the report lines are those of the adopted
// single-token HBM gate (rtl/test/tb_hdc_core_v41x_whbm.sv, all units,
// X_IDX = 2, W_HBM = 1; tools/rtl_hdc_v41x_whbm_pooled_campaign.py), so the
// two runs are directly comparable.  The die runs in host mode (the host CSR
// port drives the core's step port); the package controller, the router, the
// collective engine and the link ports idle.  The core runs with KV_HBM = 1:
// the golden-prefilled KV starts in HBM (the die's KV region), every attention
// op's KV words are prefetched from the four stacks through the arbiters the
// pooled indexer shares, the runtime K / V writes are written through, and the
// final KV cache is read back from HBM for the check.  ROM and HBM contents are the
// via mask / DRAM contents and are loaded through the hierarchy.
// Driven by Verilator (rtl/test/chip_v41x_die_smoke_harness.cpp).
// ---------------------------------------------------------------------------
module tb_chip_v41x_die_smoke (input wire clk);
    localparam integer W = 16, VOCAB = 4040, KV_WORDS = 32768, VM_ELEMS = 65536;
    localparam integer IKH_WORDS = 1 << 18, HMEM = 1 << 20, QROM_WORDS = 1 << 16;
    localparam integer BL = 16, QLB = 272, PW = 512 + 3 + 32;

    reg rst_n = 1'b0, start = 1'b0;
    reg [15:0] token, pos, expect_tok;
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
    localparam integer KV_SBASE = 1 << 18;            // the die's map: KEY_USERS * IKH_SLICE

    ot_chip_v41x_die #(.RANK(0)) dut (
        .clk(clk), .rst_n(rst_n),
        .host_mode(1'b1), .host_start(start), .host_token(token), .host_pos(pos), .host_entry(14'd0),
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
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if (!$value$plusargs("TOKEN=%d", token)) token = 0;
        if (!$value$plusargs("POS=%d", pos)) pos = 0;
        if (!$value$plusargs("EXPECT=%d", expect_tok)) expect_tok = 0;
        if (!$value$plusargs("NPRIME=%d", n_prime)) n_prime = 0;
        if (!$value$plusargs("PFIRST=%d", pfirst)) pfirst = 0;
        if (!$value$plusargs("QLEAD=%d", qlead)) qlead = 512;
        if (!$value$plusargs("QRATE=%d", qrate)) qrate = 0;
        // tile ROM banks (the via mask)
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
        // HBM contents: the QE weight region of stack 0, the index-key images of all four stacks
        for (i = 0; i < HMEM; i = i + 1) dut.g_hbm[0].u_hbm.g_w.u_w.mem[i] = 256'd0;
        $readmemh({dir, "/hbm_q.hex"}, dut.g_hbm[0].u_hbm.g_w.u_w.mem);
        for (i = 0; i < IKH_WORDS; i = i + 1) ikimg[i] = 256'd0;
        $readmemh({dir, "/ikhbm.hex"}, ikimg);
        // golden-prefilled state: vector memory, KV staging, Engram primes
        for (i = 0; i < VM_ELEMS; i = i + 1) dut.u_tile.vm[i] = 32'd0;
        $readmemh({dir, "/vm_init.hex"}, dut.u_tile.vm);
        $readmemh({dir, "/kv.hex"}, kvimg);
        $readmemh({dir, "/prime.hex"}, prime);
        $readmemh({dir, "/expect_vm.hex"}, e_vm);
        $readmemh({dir, "/expect_kv.hex"}, e_kv);
        $readmemh({dir, "/expect_logits.hex"}, e_lg);
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end
    // the key images reach the four stacks' arrays at the first edge (as the gate loads them), and the
    // golden-prefilled KV its HBM region: word U on stack U mod 4, sectors KV_SBASE + 2 (U >> 2) + {0, 1}
    reg ik_loaded = 1'b0;
    reg [511:0] kvw;
    integer kq;
    always @(posedge clk) if (!ik_loaded) begin
        for (i = 0; i < IKH_WORDS; i = i + 1) begin
            dut.g_hbm[0].u_hbm.u_k.mem[i] = ikimg[i];
            dut.g_hbm[1].u_hbm.u_k.mem[i] = ikimg[i];
            dut.g_hbm[2].u_hbm.u_k.mem[i] = ikimg[i];
            dut.g_hbm[3].u_hbm.u_k.mem[i] = ikimg[i];
        end
        for (i = 0; i < KV_WORDS; i = i + 1) begin
            for (kq = 0; kq < W; kq = kq + 1) kvw[32*kq +: 32] = kvimg[i * W + kq];
            case (i % 4)
                0: begin dut.g_hbm[0].u_hbm.u_k.mem[KV_SBASE + 2*(i/4)] = kvw[255:0];
                         dut.g_hbm[0].u_hbm.u_k.mem[KV_SBASE + 2*(i/4) + 1] = kvw[511:256]; end
                1: begin dut.g_hbm[1].u_hbm.u_k.mem[KV_SBASE + 2*(i/4)] = kvw[255:0];
                         dut.g_hbm[1].u_hbm.u_k.mem[KV_SBASE + 2*(i/4) + 1] = kvw[511:256]; end
                2: begin dut.g_hbm[2].u_hbm.u_k.mem[KV_SBASE + 2*(i/4)] = kvw[255:0];
                         dut.g_hbm[2].u_hbm.u_k.mem[KV_SBASE + 2*(i/4) + 1] = kvw[511:256]; end
                default: begin dut.g_hbm[3].u_hbm.u_k.mem[KV_SBASE + 2*(i/4)] = kvw[255:0];
                               dut.g_hbm[3].u_hbm.u_k.mem[KV_SBASE + 2*(i/4) + 1] = kvw[511:256]; end
            endcase
        end
        ik_loaded = 1'b1;
    end
    // the KV word U as it stands in HBM
    function automatic [511:0] hbm_kv(input integer u);
        case (u % 4)
            0: hbm_kv = {dut.g_hbm[0].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1], dut.g_hbm[0].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)]};
            1: hbm_kv = {dut.g_hbm[1].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1], dut.g_hbm[1].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)]};
            2: hbm_kv = {dut.g_hbm[2].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1], dut.g_hbm[2].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)]};
            default: hbm_kv = {dut.g_hbm[3].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1], dut.g_hbm[3].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)]};
        endcase
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
            $display("IDXHBMWR records=%0d writes=%0d highwater=%0d read_stalls=%0d writer_stalls=%0d refreshes=%0d refpb=3",
                     kb_records, kb_writes, kb_highwater, dut.u_tile.kb_read_stalls, dut.u_tile.kb_writer_stalls,
                     hbm_refreshes);
        end
    endtask

    reg [31:0] kv_e;
    integer drain = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        // the die synchronises reset over two edges: release it two cycles before the gate's bench
        // (cycle 5) so the core, the streamers and the HBM models leave reset on the same edge as there
        if (cyc == 3) rst_n <= 1'b1;
        prime_v <= 1'b0;
        if (cyc >= 8 && prime_i < n_prime) begin
            prime_v <= 1'b1; prime_cid <= prime[prime_i][11:0]; prime_first <= (prime_i == 0) && pfirst;
            prime_i <= prime_i + 1;
        end
        start <= (cyc == 30);
        if (trace && issue_unit != 0)
            $display("ISSUE cyc=%0d pc=%0d unit=%0d", cycles, dut.u_tile.u_core.pc, issue_unit);
        if (cyc > 32 && done && drain == 0) drain <= 1;
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
            $display("HDC41 token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d",
                     token, pos, next_token, expect_tok, cycles, fault[0], bad_lg, bad_vm, bad_kv);
            $display("UTIL me_busy=%0d su_busy=%0d qe_busy=%0d xu_busy=%0d he_busy=%0d all_idle=%0d", busy_me,
                     busy_su, busy_qe, busy_xu, busy_he, all_idle);
            $display("QSTREAM q_ops=%0d q_words=%0d q_bad=%0d qs_fault=%0d qs_why=%0d fetched=%0d consumed=%0d hbm_reads=%0d",
                     q_ops, q_words, q_bad, fault[1], qs_why, qs_fetched, qs_consumed, hbm_w_reads);
            $display("DIE fault=%b rtr_drops=%0d kv_descriptors=%0d", fault, rtr_drops, kvd_n);
            $display("KVHBM ops=%0d words=%0d sectors_written=%0d refetches=%0d wq_high=%0d hold_cycles=%0d grants=%0d code=%b att_issue=%0d att_held_cycles=%0d",
                     kv_ops, kv_words, kv_sw, kv_ref, kv_wqh, kv_hold, kv_grants, kv_code, att_issue, att_hold);
            if (next_token == expect_tok && fault == 8'd0 && bad_lg == 0 && bad_vm == 0 && bad_kv == 0 && q_bad == 0)
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (cyc > 50000000) begin
            $display("TIMEOUT pc=%0d st=%0d", dut.u_tile.u_core.pc, dut.u_tile.u_core.st);
            $finish;
        end
    end
endmodule
