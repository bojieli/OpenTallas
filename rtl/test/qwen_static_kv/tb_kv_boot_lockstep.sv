`timescale 1ns/1ps
// RTL-BUILD-KV/BOOT 2026-10-18: RUNTIME UNCHANGED.  Lock-step of the boot-capable static PC chain against the current
// one, full shape (4 stacks x 32 PCs), with the boot face idle:
//   ref: qkd_kv_es_fan_root2 -> 4 x qkd_kv_es_fan_stack -> 4 x 32 qkd_kv_pc_chain_station -> 128 x qkd_static_kv_pc_es_merge
//   dut: qkd_kv_es_fan_root2_b -> 4 x qkd_kv_es_fan_stack_b -> 4 x 32 qkd_kv_pc_chain_station_b -> 128 x qkd_static_kv_pc_es_merge_b
// Stimulus (random, seeded): native writer face events at the production cadence (two-lane edges >= 2 apart, random
// lanes / dest stack / pc / data / identity, expected descriptors), token-run starts, player calendar boot words for
// every PC, controller er words (random valid / data / flags) at every merge, emb_boot_ready = 1 (run phase).
// Every edge: root h[782:0] == h, h[783] == 0; every station's dout[778:0], wes, es_context, es_expected_*, emb_*,
// capture / transfer slots and fault equal; land_es == 0; every merge's es, beat_*, corrected, outstanding, fault equal;
// her / hcv / hcw == 0.  Then (lock-step off) the boot face: (a) a boot word on the same edge as a writer expected event
// must latch the root fault and never reach a station; (b) clean boot words for random {stack, pc} reach exactly that
// station's land_es, once, as {1, 1, address, data, 1}, chain bit 779 set only on boot edges.
// MUT (OT_BOOT_MUT): 7 = the dut stack strap of stack 1 off by one (lock-step FAIL); 1 = root2_b boot word overrides a
// writer edge with no fault; 6 = station_b boot tap compares pc[3:0] only.
`ifndef OT_BOOT_MUT
`define OT_BOOT_MUT 0
`endif
`ifndef OT_BOOT_SEED
`define OT_BOOT_SEED 1
`endif
module tb_kv_boot_lockstep;
    localparam integer MUT = `OT_BOOT_MUT;
    localparam integer RMUT = (MUT == 1) ? 1 : 0, SMUT = (MUT == 6) ? 6 : 0;
    reg cmp = 1; reg [292:0] bwr = 0; wire [127:0] bv_all;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    integer cyc = 0, errors = 0, seed = `OT_BOOT_SEED, i, nwr = 0, nst = 0, ncf = 0, nbeat = 0;
    always @(posedge ck) cyc <= cyc + 1;
    reg [1151:0] es = 0; reg [19:0] dpc = 0, epc = 0; reg [1:0] dst = 0, gen = 0, est = 0, egen = 0;
    reg [58:0] id = 0, eid = 0; reg [28:0] ea = 0; reg [3:0] ev = 0;
    reg ss = 0; reg [17:0] tok = 0; reg [15:0] ep = 0; reg cw = 0; reg [7:0] ca = 0; reg [63:0] cd = 0;
    wire [782:0] h_r; wire [783:0] h_d; wire rf_r, rf_d;
    qkd_kv_es_fan_root2 u_rr (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dpc), .dest_stack(dst), .identity(id), .generation(gen),
        .expected_valid(ev), .expected_pc(epc), .expected_stack(est), .expected_identity(eid), .expected_generation(egen),
        .expected_address(ea), .emb_start(ss), .emb_token(tok), .emb_epoch(ep), .cfg_we(cw), .cfg_addr(ca), .cfg_data(cd),
        .h(h_r), .fault(rf_r));
    qkd_kv_es_fan_root2_b #(.MUT(RMUT)) u_rd (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dpc), .dest_stack(dst), .identity(id), .generation(gen),
        .expected_valid(ev), .expected_pc(epc), .expected_stack(est), .expected_identity(eid), .expected_generation(egen),
        .expected_address(ea), .emb_start(ss), .emb_token(tok), .emb_epoch(ep), .cfg_we(cw), .cfg_addr(ca), .cfg_data(cd),
        .bw(bwr), .h(h_d), .fault(rf_d));
    always @(negedge ck) if (rst_n && cmp) begin
        if (h_d[782:0] !== h_r || h_d[783] !== 1'b0 || rf_d !== rf_r) begin
            errors = errors + 1; if (errors < 10) $display("FAIL root h / fault differ at %0d", cyc); end
    end
    genvar s, p;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        wire [778:0] cr [0:32]; wire [779:0] cd_ [0:32];
        qkd_kv_es_fan_stack u_sr (.ck(ck), .rst_n(rst_n), .stack(2'(s)), .h(h_r), .d(cr[32]));
        qkd_kv_es_fan_stack_b u_sd (.ck(ck), .rst_n(rst_n), .stack((MUT == 7 && s == 1) ? 2'd2 : 2'(s)), .h(h_d), .d(cd_[32]));
        for (p = 0; p < 32; p = p + 1) begin : g_p
            wire [287:0] wes_r, wes_d, les, es_r, es_d; wire [317:0] cx_r, cx_d; wire xv_r, xv_d; wire [60:0] xi_r, xi_d;
            wire [28:0] xa_r, xa_d; wire [4:0] xp_r, xp_d; wire [1:0] xs_r, xs_d;
            wire iv_r, iv_d, ih_r, ih_d, ic_r, ic_d, rs_r, rs_d, cs_r, cs_d, ts_r, ts_d, sf_r, sf_d;
            wire [17:0] it_r, it_d; wire [5:0] iw_r, iw_d; wire [15:0] ie_r, ie_d;
            qkd_kv_pc_chain_station u_r (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)), .di(cr[p + 1]), .dout(cr[p]),
                .wes(wes_r), .es_context(cx_r), .es_expected_valid(xv_r), .es_expected_identity(xi_r),
                .es_expected_address(xa_r), .es_expected_pc(xp_r), .es_expected_stack(xs_r), .emb_issue_v(iv_r),
                .emb_token(it_r), .emb_word_index(iw_r), .emb_half(ih_r), .emb_scale(ic_r), .emb_epoch(ie_r),
                .emb_return_slot(rs_r), .capture_slot(cs_r), .transfer_slot(ts_r), .fault(sf_r));
            qkd_kv_pc_chain_station_b #(.MUT(SMUT)) u_d (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)), .di(cd_[p + 1]), .dout(cd_[p]),
                .land_es(les), .land_er(261'd0),
                .wes(wes_d), .es_context(cx_d), .es_expected_valid(xv_d), .es_expected_identity(xi_d),
                .es_expected_address(xa_d), .es_expected_pc(xp_d), .es_expected_stack(xs_d), .emb_issue_v(iv_d),
                .emb_token(it_d), .emb_word_index(iw_d), .emb_half(ih_d), .emb_scale(ic_d), .emb_epoch(ie_d),
                .emb_return_slot(rs_d), .capture_slot(cs_d), .transfer_slot(ts_d), .fault(sf_d));
            // controller er: random words, the same to both merges
            reg [260:0] er = 0;
            always @(posedge ck) begin
                er[0] <= cyc > 20 && ($urandom % 23) == 0; er[256:1] <= {8{$urandom}}; er[257] <= ($urandom % 7) == 0;
                er[258] <= cyc > 20 && ($urandom % 97) == 0; er[259] <= ($urandom % 3) == 0; er[260] <= cyc > 20 && ($urandom % 401) == 0;
            end
            wire bv_r, bv_d, bh_r, bh_d, bs_r, bs_d, co_r, co_d, eo_r, eo_d, mf_r, mf_d, hcv, hcw;
            wire [255:0] bd_r, bd_d; wire [17:0] bt_r, bt_d; wire [5:0] bw_r, bw_d; wire [15:0] be_r, be_d; wire [260:0] her;
            qkd_static_kv_pc_es_merge u_mr (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)), .wes(wes_r),
                .emb_boot_ready(1'b1), .emb_issue_v(iv_r), .emb_token(it_r), .emb_word_index(iw_r), .emb_half(ih_r),
                .emb_scale(ic_r), .emb_epoch(ie_r), .emb_return_slot(rs_r), .es(es_r), .er(er), .beat_v(bv_r),
                .beat_data(bd_r), .beat_token(bt_r), .beat_word(bw_r), .beat_half(bh_r), .beat_scale(bs_r),
                .beat_epoch(be_r), .corrected(co_r), .emb_outstanding(eo_r), .fault(mf_r));
            qkd_static_kv_pc_es_merge_b u_md (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)), .wes(wes_d),
                .emb_boot_ready(1'b1), .emb_issue_v(iv_d), .emb_token(it_d), .emb_word_index(iw_d), .emb_half(ih_d),
                .emb_scale(ic_d), .emb_epoch(ie_d), .emb_return_slot(rs_d), .hes(288'd0), .her(her),
                .completion_v(er[0]), .completion_we(er[257]), .hcv(hcv), .hcw(hcw), .es(es_d), .er(er), .beat_v(bv_d),
                .beat_data(bd_d), .beat_token(bt_d), .beat_word(bw_d), .beat_half(bh_d), .beat_scale(bs_d),
                .beat_epoch(be_d), .corrected(co_d), .emb_outstanding(eo_d), .fault(mf_d));
            integer nboot = 0;
            assign bv_all[32*s + p] = les[0];
            always @(negedge ck) if (rst_n && !cmp && les[0]) begin
                nboot = nboot + 1;
                if (s != bst || p != bpc || les[287:1] !== {1'b1, 1'b1, bad, bdat}) begin
                    errors = errors + 1; if (errors < 20) $display("FAIL boot word at %0d/%0d (sent %0d/%0d)", s, p, bst, bpc); end
            end
            always @(negedge ck) if (rst_n && cmp && cyc > 8) begin
                if (cd_[p][778:0] !== cr[p] || cd_[p][779] !== 1'b0 || wes_d !== wes_r || cx_d !== cx_r || xv_d !== xv_r ||
                    xi_d !== xi_r || xa_d !== xa_r || xp_d !== xp_r || xs_d !== xs_r || iv_d !== iv_r || it_d !== it_r ||
                    iw_d !== iw_r || ih_d !== ih_r || ic_d !== ic_r || ie_d !== ie_r || rs_d !== rs_r || cs_d !== cs_r ||
                    ts_d !== ts_r || sf_d !== sf_r || les !== 288'd0) begin
                    errors = errors + 1; if (errors < 10) $display("FAIL station %0d/%0d differs at %0d", s, p, cyc); end
                if (es_d !== es_r || bv_d !== bv_r || bd_d !== bd_r || bt_d !== bt_r || bw_d !== bw_r || bh_d !== bh_r ||
                    bs_d !== bs_r || be_d !== be_r || co_d !== co_r || eo_d !== eo_r || mf_d !== mf_r || her[0] || her[259] || her[260] ||
                    hcv !== 1'b0 || hcw !== 1'b0) begin
                    errors = errors + 1; if (errors < 10) $display("FAIL merge %0d/%0d differs at %0d", s, p, cyc); end
                if (wes_r[0]) nwr = nwr + 1;
                if (iv_r) nst = nst + 1;
                if (bv_r) nbeat = nbeat + 1;
            end
        end
    end endgenerate
    // ---- stimulus ----
    integer gapw = 0, k, pc_, st_, rg, nb, nbt = 0, bst = 0, bpc = 0; reg [28:0] bad = 0; reg [255:0] bdat = 0;
    initial begin
        i = $urandom(seed);
        repeat (4) @(negedge ck); rst_n = 1; repeat (12) @(negedge ck);
        // player calendars for every PC (issue / return / capture / transfer / scale), random small offsets
        for (st_ = 0; st_ < 4; st_ = st_ + 1) for (pc_ = 0; pc_ < 32; pc_ = pc_ + 1) for (rg = 0; rg < 8; rg = rg + 1) begin
            cw = 1; ca = {5'(pc_), 3'(rg)}; cd = 0; cd[17:16] = 2'(st_);
            cd[15:0] = (rg == 2 || rg == 3 || rg == 6 || rg == 7) ? 16'hffff : 16'(4 + rg * 9 + ($urandom % 5));
            @(negedge ck); ncf = ncf + 1;
        end
        cw = 0;
        for (k = 0; k < 6000; k = k + 1) begin
            // writer event at most every other edge
            ev = 0; es = 0;
            if (gapw == 0 && ($urandom % 3) == 0) begin
                for (i = 0; i < 4; i = i + 1) begin
                    es[288*i +: 288] = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                    es[288*i] = ($urandom % 4) != 0;
                    es[288*i + 286] = 1'b1; es[288*i + 287] = 1'b1;
                end
                dpc = {$urandom}; dst = $urandom; id = {$urandom, $urandom}; gen = $urandom;
                ev = $urandom; epc = {$urandom}; est = $urandom; eid = {$urandom, $urandom}; egen = $urandom; ea = $urandom;
                gapw = 2;
            end else if (gapw != 0) gapw = gapw - 1;
            ss = ($urandom % 211) == 0; tok = $urandom; ep = $urandom;
            @(negedge ck);
        end
        ev = 0; es = 0; ss = 0;
        repeat (300) @(negedge ck);
        // ---- boot face (lock-step off: the dut now differs by design) ----
        cmp = 0;
        // (a) collision: a boot word on a writer expected-event edge
        bst = 1; bpc = 9; bad = 29'h1234567; bdat = {8{32'hdeadbeef}};
        bwr = {bdat, bad, 5'(bpc), 2'(bst), 1'b1}; ev = 4'b0001; epc = 20'd3; est = 2'd2;
        @(negedge ck); bwr = 0; ev = 0;
        repeat (60) @(negedge ck);
        if (!rf_d) begin errors = errors + 1; $display("FAIL boot / writer collision did not fault the root"); end
        if (tb_kv_boot_lockstep.g_s[1].g_p[9].nboot != 0) begin errors = errors + 1; $display("FAIL collided boot word was delivered"); end
        // (b) clean boot words
        for (k = 0; k < 64; k = k + 1) begin
            bst = $urandom % 4; bpc = $urandom % 32; bad = $urandom; bdat = {8{$urandom}};
            bwr = {bdat, bad, 5'(bpc), 2'(bst), 1'b1}; @(negedge ck); bwr = 0;
            nb = 0;
            repeat (50) begin @(negedge ck); for (i = 0; i < 128; i = i + 1) nb = nb + bv_all[i]; end
            if (nb != 1) begin errors = errors + 1; if (errors < 20) $display("FAIL boot word %0d/%0d delivered %0d times", bst, bpc, nb); end
            nbt = nbt + nb;
        end
        if (nwr < 1000 || nst < 50) begin errors = errors + 1; $display("FAIL weak stimulus writes %0d issues %0d", nwr, nst); end
        if (errors) $display("FAIL MUT %0d errors %0d (writer words %0d, embedding issues %0d, beats %0d)", MUT, errors, nwr, nst, nbeat);
        else $display("PASS KV_BOOT_LOCKSTEP 4x32 PCs: root h, every station and es merge equal the current chain (writer words %0d, embedding issues %0d, beats %0d, %0d calendar words, boot faces idle); boot / writer collision faults the root and is not delivered; %0d / 64 clean boot words each reach exactly their station's land_es", nwr, nst, nbeat, ncf, nbt);
        $finish;
    end
endmodule
