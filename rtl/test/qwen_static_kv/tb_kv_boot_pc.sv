`timescale 1ns/1ps
// RTL-BUILD-KV/BOOT 2026-10-18 (results/arch/qwen_kv_boot_path_1018/note.md): the static KV die's boot paths into HBM,
// end to end on one stack's 32 PCs with the REAL per-PC HOST slices.
//   host hb -> qkd_embgw_boot_s -> qkd_kv_es_fan_root2_b -> 4 x qkd_kv_es_fan_stack_b -> 4 x 32 qkd_kv_pc_chain_station_b
//   stack SM, every PC: station_b land_es -> qkd_host_pc_slice_die (unchanged, lpc = pc) -> ctrl_es ->
//                       qkd_static_kv_pc_es_merge_b -> bench controller model (es288 / er261 face: in-order static
//                       queue, credit er[259] CRL edges after the word, completion WD edges after, read data LC edges
//                       after; memory = what was written) -> er / completion -> merge_b -> slice
//   host fi chain -> the 32 slices' ingest stations (HOST KV writes), co / ao / status chains back to the bench host.
//   other stacks: station_b land_es observed + a slice landing-credit model.
// Phases: P1 cold boot (bgi chain): every slice's scratch check passes through merge_b (soo all set, sfo 0);
//   P2 HOST KV writes (fi) to 8 PCs; P3 embedding image: 6 full token rows (128 code sectors each, all stacks) + their
//   scale sectors, ascending E, through hb; wait (as the HOST dispatcher) for every SM word's slice ack on the status
//   chain; BOOT_END with the true {count, checksum} -> est ready after HOLD; P4 run phase: the players read every token
//   (code half at every SM PC, scale at its home) through merge_b's embedding endpoint: beat data == the sector the
//   boot wrote (the boot map emb_loc and the read map qkd_embedding_static_map agree, end to end); memory == every
//   KV / embedding write, exactly; P5 re-load token 0 with new data while ready (REOPEN), BOOT_END, run reads see the
//   new data; P6 a HOST word in the run phase faults that PC's merge only; P7 BOOT_END with a wrong checksum -> est
//   fault, not ready.  Everywhere else: no slice / station / merge / root / gateway fault.
// MUT (OT_BOOT_MUT): 11 gateway pc ^ 1, 12 gateway count-only check, 13 gateway no REOPEN, 14 merge er not steered,
// 15 merge no run-phase slice-word fault, 16 merge completions not steered, 17 station boot tap pc[3:0]: must FAIL.
`ifndef OT_BOOT_MUT
`define OT_BOOT_MUT 0
`endif
module tb_kv_boot_pc;
    import ot_qfd_emb_pkg::*;
    localparam integer MUT = `OT_BOOT_MUT, SM = 2, LC = 24, WD = 12, CRL = 2, ROW0 = 24427, HOLD = 64;
    localparam integer GMUT = (MUT >= 11 && MUT <= 13) ? MUT - 10 : 0;
    localparam integer MMUT = (MUT >= 14 && MUT <= 16) ? MUT - 10 : 0;
    localparam integer SMUT = (MUT == 17) ? 6 : 0;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    integer cyc = 0, errors = 0;
    always @(posedge ck) cyc <= cyc + 1;
    function automatic [255:0] dat(input [24:0] e, input integer g);
        integer j; reg [31:0] h;
        begin
            for (j = 0; j < 8; j = j + 1) begin
                h = (32'(e) * 32'h9e3779b1) ^ (32'(g + 3) * 32'h85ebca77) ^ (32'(j) * 32'hc2b2ae3d);
                dat[32*j +: 32] = h ^ (h >> 13) ^ (h << 7);
            end
        end
    endfunction
    // ---- gateway + root ----
    reg [282:0] hb = 0; wire hb_cr; wire [12:0] est; wire [292:0] bw;
    qkd_embgw_boot_s #(.HOLD(HOLD), .MUT(GMUT)) u_gw (.ck(ck), .rst_n(rst_n), .hb(hb), .hb_cr(hb_cr), .est(est), .bw(bw));
    reg ss = 0; reg [17:0] tok = 0; reg [15:0] epo = 0; reg cw = 0; reg [7:0] ca = 0; reg [63:0] cd = 0;
    wire [783:0] h; wire root_fault;
    qkd_kv_es_fan_root2_b u_root (.ck(ck), .rst_n(rst_n), .es(1152'd0), .dest_pc(20'd0), .dest_stack(2'd0), .identity(59'd0),
        .generation(2'd0), .expected_valid(4'd0), .expected_pc(20'd0), .expected_stack(2'd0), .expected_identity(59'd0),
        .expected_generation(2'd0), .expected_address(29'd0), .emb_start(ss), .emb_token(tok), .emb_epoch(epo),
        .cfg_we(cw), .cfg_addr(ca), .cfg_data(cd), .bw(bw), .h(h), .fault(root_fault));
    // ---- the bench host: fi chain head + reverse chains ----
    reg [290:0] fi0 = 0; reg bgi0 = 0;
    wire [290:0] f [0:32]; wire [31:0] c [0:32], a [0:32], sk [0:32], sd [0:32], so [0:32], sf [0:32];
    wire fl [0:32]; wire bg [0:32];
    assign f[0] = fi0; assign bg[0] = bgi0;
    assign c[32] = 0; assign a[32] = 0; assign sk[32] = 0; assign sd[32] = 0; assign so[32] = 0; assign sf[32] = 0;
    assign fl[32] = 1'b0;
    wire [127:0] stf, mrf; wire [31:0] mbv;
    genvar s, p;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        wire [779:0] ch [0:32];
        qkd_kv_es_fan_stack_b u_fs (.ck(ck), .rst_n(rst_n), .stack(2'(s)), .h(h), .d(ch[32]));
        for (p = 0; p < 32; p = p + 1) begin : g_p
            wire [287:0] wes, les; wire [260:0] ler; wire [317:0] ctx; wire xv; wire [60:0] eid; wire [28:0] ead;
            wire [4:0] xpc; wire [1:0] xst; wire iv, ih, isc, rs; wire [17:0] it; wire [5:0] iw; wire [15:0] ie;
            qkd_kv_pc_chain_station_b #(.MUT(SMUT)) u_st (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)),
                .di(ch[p + 1]), .dout(ch[p]), .land_es(les), .land_er(ler), .wes(wes), .es_context(ctx),
                .es_expected_valid(xv), .es_expected_identity(eid), .es_expected_address(ead), .es_expected_pc(xpc),
                .es_expected_stack(xst), .emb_issue_v(iv), .emb_token(it), .emb_word_index(iw), .emb_half(ih),
                .emb_scale(isc), .emb_epoch(ie), .emb_return_slot(rs), .capture_slot(), .transfer_slot(),
                .fault(stf[32*s + p]));
            if (s == SM) begin : g_full
                wire [287:0] hes, es; wire [260:0] her; wire hcv, hcw;
                qkd_host_pc_slice_die u_sl (.ck_station(ck), .ck_static(ck), .ck_boot(ck), .ck_boot_test(ck),
                    .host_rst_n(rst_n), .hbm_rst_n(rst_n), .lpc(5'(p)), .bgi(bg[p]), .bgo(bg[p + 1]),
                    .fi(f[p]), .fo(f[p + 1]), .ci(c[p + 1]), .co(c[p]), .ai(a[p + 1]), .ao(a[p]),
                    .fault_i(fl[p + 1]), .fault_o(fl[p]), .land_es(les), .land_er(ler), .ctrl_es(hes), .ctrl_er(her),
                    .ctrl_completion_v(hcv), .ctrl_completion_we(hcw),
                    .ski(sk[p + 1]), .sdi(sd[p + 1]), .soi(so[p + 1]), .sfi(sf[p + 1]),
                    .sko(sk[p]), .sdo(sd[p]), .soo(so[p]), .sfo(sf[p]));
                // ---- controller model ----
                reg [CRL-1:0] crl = 0; reg [1:0] cpl [0:WD-1]; reg [256:0] rdl [0:LC-1];
                integer k;
                wire [28:0] ad = es[285:257];
                always @(posedge ck) begin
                    crl <= {crl[CRL-2:0], es[0]};
                    cpl[0] <= {es[286], es[0]}; for (k = 1; k < WD; k = k + 1) cpl[k] <= cpl[k - 1];
                    rdl[0] <= {es[0] && !es[286], mrd(p, ad)};
                    for (k = 1; k < LC; k = k + 1) rdl[k] <= rdl[k - 1];
                    if (es[0] && es[286]) mw(p, ad, es[256:1]);
                end
                wire [260:0] er = {1'b0, crl[CRL-1], 2'b00, rdl[LC-1][255:0], rdl[LC-1][256]};
                wire bv, bh, bs; wire [255:0] bd; wire [17:0] bt; wire [5:0] bwi; wire [15:0] be;
                qkd_static_kv_pc_es_merge_b #(.MUT(MMUT)) u_m (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)),
                    .wes(wes), .emb_boot_ready(est[0]), .emb_issue_v(iv), .emb_token(it), .emb_word_index(iw),
                    .emb_half(ih), .emb_scale(isc), .emb_epoch(ie), .emb_return_slot(rs), .hes(hes), .her(her),
                    .completion_v(cpl[WD-1][0]), .completion_we(cpl[WD-1][1]), .hcv(hcv), .hcw(hcw), .es(es), .er(er),
                    .beat_v(bv), .beat_data(bd), .beat_token(bt), .beat_word(bwi), .beat_half(bh), .beat_scale(bs),
                    .beat_epoch(be), .corrected(), .emb_outstanding(), .fault(mrf[32*s + p]));
                assign mbv[p] = bv;
                // beat check: the code half {SM, p} of the token, or its scale sector at the home PC
                always @(negedge ck) if (rst_n && bv) begin
                    if (!bs) begin
                        if (bd !== want(25'(bt) * 25'd128 + 25'({2'(s), 5'(p)}))) begin
                            errors = errors + 1; if (errors < 20) $display("FAIL beat data PC %0d token %0d", p, bt); end
                    end else if (bd !== want(25'(E_SCALE) + 25'(bt >> 4)) || bt[8:4] != p || bt[10:9] != s) begin
                        errors = errors + 1; if (errors < 20) $display("FAIL scale beat PC %0d token %0d", p, bt); end
                    if (bt != tok || be != epo) begin errors = errors + 1; $display("FAIL beat identity PC %0d", p); end
                    nbeat = nbeat + 1;
                end
            end else begin : g_obs
                // slice landing-credit model (no slice on this stack) + scoreboard of the delivered boot words
                reg [3:0] cdl = 0;
                always @(posedge ck) cdl <= {cdl[2:0], les[0]};
                assign ler = {1'b0, cdl[3], 259'd0};
                always @(negedge ck) if (rst_n && les[0]) land_obs(s, p, les);
                assign mrf[32*s + p] = 1'b0;
            end
        end
    end endgenerate
    // ---- the image (the bench's record of what each sector holds) ----
    reg [255:0] img [logic [24:0]];
    reg [255:0] mm [logic [33:0]];                // the controller models' memory: {pc, address} -> data
    integer mwn [0:31];
    task automatic mw(input integer pc, input [28:0] ad, input [255:0] d);
        begin mm[{5'(pc), ad}] = d; mwn[pc] = mwn[pc] + 1; end
    endtask
    function automatic [255:0] mrd(input integer pc, input [28:0] ad);
        mrd = mm.exists({5'(pc), ad}) ? mm[{5'(pc), ad}] : 256'h0;
    endfunction
    function automatic bit dut_mem_has(input integer pc, input [28:0] ad, input [255:0] d);
        dut_mem_has = mm.exists({5'(pc), ad}) && mm[{5'(pc), ad}] === d;
    endfunction
    reg [255:0] kvx [logic [33:0]];               // {pc, address} -> data of the HOST KV writes
    integer nbeat = 0, nobs = 0, nexp_obs = 0;
    function automatic [255:0] want(input [24:0] e);
        want = img.exists(e) ? img[e] : 256'hx;
    endfunction
    task automatic land_obs(input integer st, input integer pc, input [287:0] w);
        reg [24:0] e; reg found; reg [25:0] l;
        begin
            nobs = nobs + 1;
            // find the sector by its independent read-side address (qkd_embedding_static_map ABI)
            found = 0;
            foreach (img[k]) begin
                l = emb_loc(k);
                if (!found && img[k] === w[256:1] && l[24:23] == st && l[22:18] == pc &&
                    w[285:257] == {l[17:13], l[12:8], 19'(ROW0) + 19'(l[7:0])}) found = 1;
            end
            if (!found || w[287:286] != 2'b11) begin
                errors = errors + 1; if (errors < 20) $display("FAIL boot word at %0d/%0d not a sector of the image", st, pc); end
        end
    endtask
    // ---- host model ----
    integer i, j, t, e_, ncnt = 0, nacks, want_acks, hcred, ti; reg [31:0] csum = 0, cnt = 0;
    reg [24:0] el [0:1023]; integer ne;
    reg [17:0] toks [0:5];
    integer ack_cnt [0:31], ao_cnt [0:31], co_cnt [0:31], kvn [0:31];
    integer jj;
    always @(negedge ck) if (rst_n) for (jj = 0; jj < 32; jj = jj + 1) begin
        if (sk[0][jj]) ack_cnt[jj] = ack_cnt[jj] + 1;
        if (a[0][jj]) ao_cnt[jj] = ao_cnt[jj] + 1;
        if (c[0][jj]) co_cnt[jj] = co_cnt[jj] + 1;
    end
    // hb sender with the gateway's BD = 4 credits
    always @(posedge ck) if (hb_cr) hcred = hcred + 1;
    task automatic send_hb(input end_, input [24:0] e, input [255:0] d);
        begin
            while (hcred == 0) @(negedge ck);
            hcred = hcred - 1;
            hb = {d, e, end_, 1'b1}; @(negedge ck); hb = 0;
        end
    endtask
    task automatic sector(input [24:0] e, input integer g);
        reg [255:0] d;
        begin
            d = dat(e, g); img[e] = d; send_hb(1'b0, e, d);
            cnt = cnt + 1; csum = csum + crc_sector(e, d);
            if (e < E_SCALE ? (e[6:5] != SM) : (25'(e - E_SCALE) >> 5) % 4 != SM) nexp_obs = nexp_obs + 1;
        end
    endtask
    function automatic integer sm_words();     // image words homed on stack SM
        integer n; reg [25:0] l;
        begin n = 0; foreach (img[k]) begin l = emb_loc(k); if (l[24:23] == SM) n = n + 1; end sm_words = n; end
    endfunction
    task automatic wait_acks(input integer n);
        integer w, tot;
        begin
            w = 0;
            forever begin
                tot = 0; for (j = 0; j < 32; j = j + 1) tot = tot + ack_cnt[j];
                if (tot >= n || w > 200000) break;
                @(negedge ck); w = w + 1;
            end
            if (tot != n) begin errors = errors + 1; $display("FAIL slice acks %0d (want %0d)", tot, n); end
        end
    endtask
    task automatic cfg(input integer pc, input integer rg, input integer v);
        begin cw = 1; ca = {5'(pc), 3'(rg)}; cd = 0; cd[17:16] = 2'(SM); cd[15:0] = 16'(v); @(negedge ck); cw = 0; end
    endtask
    task automatic run_reads();
        integer n0;
        begin
            for (t = 0; t < 6; t = t + 1) begin
                tok = toks[t]; epo = 16'(16'h4321 + t * 13 + cyc); n0 = nbeat;
                ss = 1; @(negedge ck); ss = 0;
                repeat (220) @(negedge ck);
                if (nbeat - n0 != 32 + ((toks[t][10:9] == SM) ? 1 : 0)) begin
                    errors = errors + 1; $display("FAIL token %0d beats %0d", toks[t], nbeat - n0); end
            end
        end
    endtask
    task automatic wait_ready(input v);
        integer w; begin w = 0; while (est[0] != v && w < 5000) begin @(negedge ck); w = w + 1; end
            if (est[0] != v) begin errors = errors + 1; $display("FAIL est ready never %0d (est %h)", v, est); end end
    endtask
    integer sawlow, nw0;
    initial begin
        hcred = 4;
        for (j = 0; j < 32; j = j + 1) begin ack_cnt[j] = 0; ao_cnt[j] = 0; co_cnt[j] = 0; kvn[j] = 0; mwn[j] = 0; end
        // tokens: scale homes on stack SM and elsewhere; the last token id
        toks[0] = 18'd2037; toks[1] = 18'(2048 * 5 + (SM << 9) + (7 << 4) + 3); toks[2] = 18'd151935;
        toks[3] = 18'd77777; toks[4] = 18'(2048 * 37 + (SM << 9) + (31 << 4)); toks[5] = 18'd123;
        repeat (4) @(negedge ck); rst_n = 1; repeat (8) @(negedge ck);
        // ---- P1 cold boot ----
        bgi0 = 1; @(negedge ck); bgi0 = 0;
        i = 0; while (so[0] != 32'hffffffff && i < 4000) begin @(negedge ck); i = i + 1; end
        if (so[0] != 32'hffffffff || sf[0] != 0 || sd[0] != 32'hffffffff) begin
            errors = errors + 1; $display("FAIL cold boot: ok %h done %h fault %h", so[0], sd[0], sf[0]); end
        // ---- P2 HOST KV writes: 3 a PC on 8 PCs (rows 64..99, never the scratch sector) ----
        for (j = 0; j < 8; j = j + 1) for (i = 0; i < 3; i = i + 1) begin : kv
            reg [4:0] bk, cl; reg [18:0] rw; reg [255:0] d; reg [4:0] lp;
            lp = 5'(j * 4 + 1); bk = $urandom; cl = $urandom; rw = 19'(64 + ($urandom % 36)); d = {8{$urandom}};
            kvx[{lp, bk, cl, rw}] = d; kvn[lp] = kvn[lp] + 1;
            fi0 = {d, rw, cl, bk, lp, 1'b1}; @(negedge ck); fi0 = 0; repeat (6) @(negedge ck);
        end
        // ---- P3 the embedding image, ascending E ----
        ne = 0;
        for (t = 0; t < 6; t = t + 1) for (i = 0; i < 128; i = i + 1) begin el[ne] = 25'(toks[t]) * 25'd128 + 25'(i); ne = ne + 1; end
        for (t = 0; t < 6; t = t + 1) begin el[ne] = 25'(E_SCALE) + 25'(toks[t] >> 4); ne = ne + 1; end
        for (i = 0; i < ne; i = i + 1) for (j = i + 1; j < ne; j = j + 1) if (el[j] < el[i]) begin e_ = el[i]; el[i] = el[j]; el[j] = 25'(e_); end
        sawlow = 1;
        for (i = 0; i < ne; i = i + 1) if (i == 0 || el[i] != el[i - 1]) begin
            if (est[0]) sawlow = 0;
            sector(el[i], 0);
        end
        want_acks = sm_words() + 24;
        wait_acks(want_acks);
        send_hb(1'b1, 25'd0, {192'd0, csum, cnt});
        repeat (HOLD / 2) @(negedge ck);
        if (est[0]) begin errors = errors + 1; $display("FAIL est ready inside HOLD"); end
        wait_ready(1);
        if (!sawlow) begin errors = errors + 1; $display("FAIL est ready during the load"); end
        // ---- P4 run phase reads ----
        for (i = 0; i < 32; i = i + 1) begin
            cfg(i, 0, 8); cfg(i, 1, 8 + LC + 8); cfg(i, 2, 16'hffff); cfg(i, 3, 16'hffff);
            cfg(i, 4, 8 + LC + 12); cfg(i, 5, 8 + LC + 12 + LC + 8); cfg(i, 6, 16'hffff); cfg(i, 7, 16'hffff);
        end
        repeat (40) @(negedge ck);
        run_reads();
        // memory == every write: KV words + image sectors homed on SM (+ the scratch sector), nothing else
        for (j = 0; j < 32; j = j + 1) begin : memchk
            integer nk, ni; reg [25:0] l; nk = 0; ni = 0;
            foreach (kvx[k]) if (k[33:29] == j) begin
                nk = nk + 1;
                if (!dut_mem_has(j, k[28:0], kvx[k])) begin errors = errors + 1; if (errors < 20) $display("FAIL KV write PC %0d", j); end
            end
            foreach (img[k]) begin l = emb_loc(k); if (l[24:23] == SM && l[22:18] == j) begin
                ni = ni + 1;
                if (!dut_mem_has(j, {l[17:13], l[12:8], 19'(ROW0) + 19'(l[7:0])}, img[k])) begin
                    errors = errors + 1; if (errors < 20) $display("FAIL image sector %0d at PC %0d", k, j); end
            end end
            if (mwn[j] != nk + ni + 2) begin errors = errors + 1; $display("FAIL PC %0d writes %0d (want %0d)", j, mwn[j], nk + ni + 2); end
            if (ao_cnt[j] != kvn[j] || co_cnt[j] != kvn[j]) begin
                errors = errors + 1; $display("FAIL PC %0d host acks %0d credits %0d (sent %0d)", j, ao_cnt[j], co_cnt[j], kvn[j]); end
        end
        if (nobs != nexp_obs) begin errors = errors + 1; $display("FAIL other-stack boot words %0d (want %0d)", nobs, nexp_obs); end
        // ---- P5 re-load token 0 with new data while ready ----
        nw0 = 0; for (j = 0; j < 32; j = j + 1) nw0 = nw0 + ack_cnt[j];
        for (i = 0; i < 128; i = i + 1) sector(25'(toks[0]) * 25'd128 + 25'(i), 1);
        if (est[0]) begin errors = errors + 1; $display("FAIL est ready during the re-load"); end
        wait_acks(nw0 + 32);
        send_hb(1'b1, 25'd0, {192'd0, csum, cnt});
        wait_ready(1);
        run_reads();
        // ---- P6 a HOST word in the run phase: PC 3's merge faults, no other ----
        if (|mrf) begin errors = errors + 1; $display("FAIL merge faults before P6 %h", mrf); end
        fi0 = {256'h5a5a, 19'd70, 5'd1, 5'd1, 5'd3, 1'b1}; @(negedge ck); fi0 = 0; repeat (60) @(negedge ck);
        if (mrf != (128'd1 << (32 * SM + 3))) begin errors = errors + 1; $display("FAIL run-phase host word: merge faults %h", mrf); end
        // ---- P7 BOOT_END with a wrong checksum ----
        send_hb(1'b1, 25'd0, {192'd0, csum + 32'd1, cnt});
        repeat (HOLD + 20) @(negedge ck);
        if (est[0] || !est[1] || !est[7]) begin errors = errors + 1; $display("FAIL wrong checksum accepted: est %h", est); end
        if (root_fault || |stf || fl[0] || sf[0] != 0) begin
            errors = errors + 1; $display("FAIL faults root %0d station %h slice chain %0d slice boot %h", root_fault, stf, fl[0], sf[0]); end
        if (errors) $display("FAIL MUT %0d errors %0d (beats %0d)", MUT, errors, nbeat);
        else $display("PASS KV_BOOT_PC cold boot 32/32 via merge_b; %0d HOST KV writes; image %0d sectors (%0d on stack %0d via the real slices, %0d boot words elsewhere incl. the re-load), est ready after HOLD; %0d run-phase beats == boot data; re-load + REOPEN; run-phase host word and wrong checksum fault", 24, cnt - 128, sm_words(), SM, nobs, nbeat);
        $finish;
    end
endmodule
