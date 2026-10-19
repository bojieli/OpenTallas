`timescale 1ns/1ps
`default_nettype none
// LH-P3UNITS/UNIONTILE 10-19: PER-QUADRANT factored union dispatch behind the ACTUAL IDX.UNION engine on the ACTUAL SW
// VM slice (fork of tb_hnx_union_factored.sv).  The head ot_hnx_union_tap taps the real IDX packet-write bus beside
// idx_sel and broadcasts its stream word over fixed-latency links (LQ = L0..L3 edges incl. the tile pin register; the
// farthest = 23 relay hops (9.06 mm @ 405 um) + 4 landing = 27 + pin = 28) to FOUR ot_hnx_union_qtile copies
// (dispatcher + metadata macro + 7-macro kernel store).  EVERY copy must emit every (loop, slot, c, kref) launch on the
// SAME exact golden edge as the central dispatcher golden (launch.txt, i.e. no link latency on the critical path), and
// its kernel store must stream the golden descriptor words (boot image word(a)) KLAT edges after each launch.  IDX
// fault records must produce no launch and exactly one abort per copy.  PMUT = qdisp mutant (1..4), PMUT 5 = kernel-store
// address mutant (KMUT 1).
module tb_hnx_union_quad;
    parameter integer PMUT=0;
    parameter integer MUT = 0;
    parameter integer L0 = 28, L1 = 20, L2 = 12, L3 = 6;     // stream latency per quadrant (relays + landing + pin reg)
    localparam integer KLAT = 6;
    localparam integer NE = 131072, NL = 4096, NPRE = 4096, NCHK = 1024, NREC = 64;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    // slice calendar / ports
    reg [675:0] cq_all = 0; wire [547:0] cr_all;
    reg [5:0] client_seq = 0; reg [2:0] response_enable = 0; reg [5:0] response_seq = 0;
    reg [7:0] bank_enable = 0; reg [15:0] bank_client = 0;
    reg [7:0] rslot_v = 0, wslot_v = 0; reg [23:0] rslot = 0, wslot = 0;
    reg [679:0] rq_bench = 0; wire [679:0] rq; wire [10279:0] rr;
    reg [2247:0] dq = 0; wire [7:0] wq_done, dq_done, kq_done;
    wire [2223:0] cw_out, ccw_out; wire [143:0] bank_status; wire [2:0] hub_status, ring_fault; wire [1:0] mirror_busy;
    wire [18:0] vmstat;
    // engine
    reg go = 0; reg [3:0] k = 0, kk = 0; reg [4:0] nr = 0; reg [9:0] ex = 0; reg a_mirror = 0;
    reg [17:0] a_base = 0, a_str = 0, o_base = 0, d_base = 0, r_base = 0;
    wire [135:0] vm_rq; wire [337:0] cq; wire [1:0] cq_seq; wire busy, done, fault;
    wire union_v; wire [9:0] union_count;
    reg [15:0] s_off = 0;
    reg bw_v = 0; reg [13:0] bw_addr = 0; reg [255:0] bw_data [0:3];
    integer ncfg = 0, nl = 0;
    reg [47:0] lexp [0:NL-1];
    integer lexe [0:NL-1];
    wire [49:0] s_head;
    ot_hnx_union_tap head(.clk(clk), .rst_n(rst_n), .go(go), .n_rows(nr), .k(k), .d_base(d_base), .r_base(r_base),
        .s_off(s_off), .cq(cq), .union_v(union_v), .union_count(union_count), .union_fault(fault), .s_out(s_head));
    wire [49:0] s_q [0:3];
    ot_hnx_union_bcast #(.W(50), .N(L0 - 1)) lk0(.clk(clk), .d(s_head), .q(s_q[0]));
    ot_hnx_union_bcast #(.W(50), .N(L1 - 1)) lk1(.clk(clk), .d(s_head), .q(s_q[1]));
    ot_hnx_union_bcast #(.W(50), .N(L2 - 1)) lk2(.clk(clk), .d(s_head), .q(s_q[2]));
    ot_hnx_union_bcast #(.W(50), .N(L3 - 1)) lk3(.clk(clk), .d(s_head), .q(s_q[3]));
    wire [3:0] q_hold;
    wire [3:0] q_busy, q_fault, q_abort, q_done, q_lv, q_kv, q_kf, q_kh;
    wire [1:0] q_loop [0:3]; wire [6:0] q_slot [0:3]; wire [4:0] q_c [0:3]; wire [11:0] q_kref [0:3];
    wire [255:0] q_kw [0:3];
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
        ot_hnx_union_qtile #(.MUT(PMUT == 5 ? 0 : PMUT), .KMUT(PMUT == 5 ? 1 : 0)) t(.clk(clk), .rst_n(rst_n),
            .s_in(s_q[gq]), .bw_v(bw_v), .bw_addr(bw_addr), .bw_data(bw_data[gq]), .busy(q_busy[gq]),
            .fault(q_fault[gq]), .abort(q_abort[gq]), .done(q_done[gq]), .launch_v(q_lv[gq]),
            .launch_loop(q_loop[gq]), .launch_slot(q_slot[gq]), .launch_c(q_c[gq]), .launch_kref(q_kref[gq]),
            .kw_v(q_kv[gq]), .kw_first(q_kf[gq]), .kw_half(q_kh[gq]), .kw_data(q_kw[gq]));
        assign q_hold[gq] = t.u_qd.dst == 3'd6;          // dispatcher holding for late metadata (informative)
    end endgenerate
    // golden boot image word of the kernel store
    function automatic [255:0] kword(input integer a);
        integer l; reg [31:0] x;
        begin
            for (l = 0; l < 8; l = l + 1) begin
                x = 32'(a) * 32'h9E3779B1 ^ (32'(l) * 32'h01000193) ^ 32'h5A5A0000;
                kword[l*32 +: 32] = x;
            end
        end
    endfunction
    // per-quadrant checkers: launch edge/variant exact vs the central golden; kernel words exact; aborts
    integer li [0:3], aborts [0:3], ks_a [0:3], ks_n [0:3], ks_e [0:3], ks_h [0:3], kp_a [0:3], kp_n [0:3], kp_e [0:3], kp_h [0:3], ka, ke, kh, holds [0:3], ks_words [0:3];
    integer qq, la, e0 = -1, lead_min = 1 << 30, ext [0:3], ext_max [0:3], ext_recs [0:3], lq [0:3];
    initial begin
        lq[0] = L0; lq[1] = L1; lq[2] = L2; lq[3] = L3;
        for (qq = 0; qq < 4; qq = qq + 1) begin
            li[qq] = 0; aborts[qq] = 0; ks_n[qq] = 0; kp_n[qq] = 0; holds[qq] = 0; ks_words[qq] = 0; ext[qq] = 0; ext_max[qq] = 0;
            ext_recs[qq] = 0;
        end
    end
    // static start hold (spec, from the HEAD stream, independent of the copies): a copy starts at
    // max(S, tap0 + LQ + 3) with S = union-done edge + 1 and tap0 = head word edge of the record's first valid expert
    // (pin reg -> E1 -> E2 -> start).  Every launch of the record moves by ext = max(0, tap0 + LQ + 3 - S).
    always @(negedge clk) if (rst_n && base != 0) begin
        if (s_head[0]) e0 = -1;
        if (s_head[22] && s_head[36] && !s_head[37] && e0 < 0) e0 = ecnt - base;
        if (union_v) begin
            if (ecnt - base + 1 - e0 < lead_min) lead_min = ecnt - base + 1 - e0;
            for (qq = 0; qq < 4; qq = qq + 1) begin
                ext[qq] = e0 + lq[qq] + 3 - (ecnt - base + 1); if (ext[qq] < 0) ext[qq] = 0;
                if (ext[qq] > ext_max[qq]) ext_max[qq] = ext[qq];
                if (ext[qq] > 0) ext_recs[qq] = ext_recs[qq] + 1;
            end
            $display("UNION_QUAD_REC done_edge %0d n_rows %0d U %0d lead %0d start_hold q0..3 %0d %0d %0d %0d", ecnt - base, nr,
                     union_count, ecnt - base + 1 - e0, ext[0], ext[1], ext[2], ext[3]);
        end
    end
    always @(negedge clk) if (rst_n && base != 0) for (qq = 0; qq < 4; qq = qq + 1) begin
        if (q_fault[qq]) $fatal(1, "UNION_QUAD q%0d dispatcher/kstore fault at %0d", qq, ecnt - base);
        if (q_abort[qq]) aborts[qq] = aborts[qq] + 1;
        // kernel-store word stream (two trackers: the previous launch's words may still be in flight)
        ka = -1;
        if (ks_n[qq] != 0 && ecnt - base >= ks_e[qq] && ecnt - base < ks_e[qq] + ks_n[qq]) begin ka = ks_a[qq]; ke = ks_e[qq]; kh = ks_h[qq]; end
        else if (kp_n[qq] != 0 && ecnt - base >= kp_e[qq] && ecnt - base < kp_e[qq] + kp_n[qq]) begin ka = kp_a[qq]; ke = kp_e[qq]; kh = kp_h[qq]; end
        if (ka >= 0) begin
            if (!q_kv[qq] || q_kw[qq] !== kword(ka + ecnt - base - ke) || q_kf[qq] !== (ecnt - base == ke) ||
                q_kh[qq] !== (ecnt - base == ke && kh != 0))
                $fatal(1, "UNION_QUAD_KSTORE_WORD q%0d edge %0d word %0d of addr %0d: v %b first %b half %b data %h expected %h",
                       qq, ecnt - base, ecnt - base - ke, ka, q_kv[qq], q_kf[qq], q_kh[qq], q_kw[qq][63:0],
                       kword(ka + ecnt - base - ke) & 256'hffffffffffffffff);
            ks_words[qq] = ks_words[qq] + 1;
        end else if (q_kv[qq]) $fatal(1, "UNION_QUAD_KSTORE_WORD q%0d spurious word at %0d", qq, ecnt - base);
        if (q_lv[qq]) begin
            if (li[qq] >= nl) $fatal(1, "UNION_QUAD q%0d spurious launch at %0d", qq, ecnt - base);
            if (q_kref[qq] !== lexp[li[qq]][11:0] || q_c[qq] !== lexp[li[qq]][16:12] || q_slot[qq] !== lexp[li[qq]][23:17] ||
                q_loop[qq] !== lexp[li[qq]][25:24])
                $fatal(1, "UNION_FACTORED_WRONG_VARIANT q%0d launch %0d edge %0d loop %0d slot %0d c %0d kref %h expected loop %0d slot %0d c %0d kref %h",
                       qq, li[qq], ecnt - base, q_loop[qq], q_slot[qq], q_c[qq], q_kref[qq], lexp[li[qq]][25:24],
                       lexp[li[qq]][23:17], lexp[li[qq]][16:12], lexp[li[qq]][11:0]);
            if (ecnt - base != lexe[li[qq]] + ext[qq])
                $fatal(1, "UNION_FACTORED_WRONG_START q%0d launch %0d edge %0d expected %0d (loop %0d slot %0d)", qq, li[qq],
                       ecnt - base, lexe[li[qq]] + ext[qq], q_loop[qq], q_slot[qq]);
            if (q_loop[qq] != 2'd3) begin
                if (ks_n[qq] != 0 && ks_e[qq] + ks_n[qq] > ecnt - base + KLAT)
                    $fatal(1, "UNION_QUAD q%0d kernel stream overlap at %0d", qq, ecnt - base);
                kp_a[qq] = ks_a[qq]; kp_n[qq] = ks_n[qq]; kp_e[qq] = ks_e[qq]; kp_h[qq] = ks_h[qq];
                la = 11 * q_kref[qq];
                if (q_loop[qq] == 2'd1) begin ks_a[qq] = la; ks_n[qq] = 11; ks_h[qq] = 0; end
                else begin ks_a[qq] = 4400 + la / 2; ks_n[qq] = 6; ks_h[qq] = la % 2; end
                ks_e[qq] = ecnt - base + KLAT;
            end
            li[qq] = li[qq] + 1;
        end else if (li[qq] < nl && ecnt - base > lexe[li[qq]] + ext[qq])
            $fatal(1, "UNION_FACTORED_MISSING q%0d launch %0d expected edge %0d", qq, li[qq], lexe[li[qq]] + ext[qq]);
        if (q_hold[qq]) holds[qq] = holds[qq] + 1;
    end
    ot_hnx_idx_union_static #(.MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .sid(2'd0), .go(go), .k(k), .n_rows(nr),
        .experts(ex), .pitch_k(kk), .a_mirror(a_mirror), .a_base(a_base), .a_str(a_str), .o_base(o_base), .d_base(d_base),
        .r_base(r_base), .vm_rq(vm_rq), .vm_rr(rr[4*2056 +: 2056]), .cq(cq), .cq_seq(cq_seq), .cr(cr_all[1*274 +: 274]),
        .busy(busy), .done(done), .fault(fault), .union_v(union_v), .union_count(union_count));
    assign rq = {vm_rq, rq_bench[4*136-1:0]};   // IDX is the top read group (4 of 0..4)
    always @* begin cq_all = 0; cq_all[1*338 +: 338] = cq; client_seq = 0; client_seq[2 +: 2] = cq_seq; end
    hfd_hgi_vms_static_SW slice(.clk_bank({8{clk}}), .clk_hub(clk), .clk_ring({2{clk}}), .clk_replay(clk), .rst_n(rst_n),
        .cq(cq_all), .cr(cr_all), .client_seq(client_seq), .response_enable(response_enable), .response_seq(response_seq),
        .bank_enable(bank_enable), .bank_client(bank_client), .hub_ring_enable(2'd0), .hub_ring_client(4'd0),
        .rslot_v(rslot_v), .wslot_v(wslot_v), .rslot(rslot), .wslot(wslot), .rq(rq), .rr(rr),
        .wq(4496'd0), .wq_done(wq_done), .dq(dq), .kq(2248'd0), .dq_done(dq_done), .kq_done(kq_done),
        .cw_in(2224'd0), .ccw_in(2224'd0), .cw_out(cw_out), .ccw_out(ccw_out), .ring_tx_enable(2'd0),
        .ring_tx_source(6'd0), .replay_enable(1'b0), .replay_source(1'b0), .bank_status(bank_status),
        .hub_status(hub_status), .mirror_busy(mirror_busy), .vmstat(vmstat), .ring_fault(ring_fault));
    // images
    reg [26:0] cal [0:NE-1];
    reg [271:0] pre [0:NPRE-1];
    reg [271:0] chk [0:NCHK-1];
    integer nrec, last, npre, nchk, fd, rc, wq, wa;
    integer rG [0:NREC-1], rEnd [0:NREC-1], rF [0:NREC-1];
    integer ecnt = 0, base = 0, errors = 0, dones = 0, faults = 0, checked = 0;
    always @(posedge clk) ecnt <= ecnt + 1;
    // done / fault must rise exactly on the compiler edge
    integer exp_done [0:NE-1], exp_fault [0:NE-1];
    always @(negedge clk) if (rst_n && base != 0) begin
        if (ecnt - base >= 0 && ecnt - base < NE) begin
            if (done !== (exp_done[ecnt - base] != 0) || fault !== (exp_fault[ecnt - base] != 0)) begin
                errors = errors + 1;
                if (errors < 10) $display("END MISMATCH ecnt %0d done %b fault %b expected %0d/%0d", ecnt - base, done, fault,
                    exp_done[ecnt - base], exp_fault[ecnt - base]);
            end
            if (done) dones = dones + 1;
            if (fault) faults = faults + 1;
        end
        if (bank_status !== 144'd0 || hub_status !== 3'd0 || ring_fault !== 3'd0) begin
            errors = errors + 1;
            if (errors < 10) $display("SLICE STATUS ecnt %0d bank %h hub %b", ecnt - base, bank_status, hub_status);
        end
    end
    // measured done/fault edge of every record (relative to the schedule origin)
    always @(negedge clk) if (rst_n && base != 0 && (done || fault)) $display("END_EDGE %0d %s", ecnt - base, done ? "done" : "fault");
    integer i, e, b, rec_i;
    reg [255:0] d;
    reg [31:0] x [0:12];
    initial begin
        for (i = 0; i < NE; i = i + 1) begin exp_done[i] = 0; exp_fault[i] = 0; cal[i] = 0; end
        fd = $fopen("rec.txt", "r");
        rc = $fscanf(fd, "%d %d\n", nrec, last);
        for (i = 0; i < nrec; i = i + 1) begin
            rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h\n", x[0], x[1], x[2], x[3], x[4], x[5], x[6],
                         x[7], x[8], x[9], x[10], x[11], x[12]);
            rG[i] = x[0]; rEnd[i] = x[1]; rF[i] = x[2];
            if (x[2]) exp_fault[x[1]] = 1; else exp_done[x[1]] = 1;
        end
        $fclose(fd);
        fd = $fopen("counts.txt", "r"); rc = $fscanf(fd, "%d %d %d", npre, nchk, nl); $fclose(fd);
        if (nl > NL) $fatal(1, "bench launch capacity");
        fd = $fopen("launch.txt", "r");
        for (i = 0; i < nl; i = i + 1) begin
            rc = $fscanf(fd, "%h %h %h %h %h\n", x[0], x[1], x[2], x[3], x[4]);
            lexp[i] = {22'(x[0]), 2'(x[1]), 7'(x[2]), 5'(x[3]), 12'(x[4])}; lexe[i] = x[0];
        end
        $fclose(fd);
        $readmemh("cal.mem", cal); $readmemh("pre.mem", pre); $readmemh("chk.mem", chk);
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        // boot: dispatcher configuration (idle only; LQ per copy) + kernel-store image, one boot word per edge
        fd = $fopen("cfg.txt", "r"); rc = $fscanf(fd, "%d\n", ncfg);
        for (i = 0; i < ncfg; i = i + 1) begin
            rc = $fscanf(fd, "%h %h\n", x[0], x[1]);
            @(negedge clk); bw_v = 1; bw_addr = 14'(x[0]);
            for (b = 0; b < 4; b = b + 1) bw_data[b] = 256'(x[1]);
        end
        $fclose(fd);
        @(negedge clk); bw_v = 1; bw_addr = 14'd37;
        bw_data[0] = 256'(L0); bw_data[1] = 256'(L1); bw_data[2] = 256'(L2); bw_data[3] = 256'(L3);
        for (wa = 0; wa < 7168; wa = wa + 1) begin
            @(negedge clk); bw_v = 1; bw_addr = 14'h2000 | 14'(wa);
            for (b = 0; b < 4; b = b + 1) bw_data[b] = kword(wa);
        end
        @(negedge clk); bw_v = 0; repeat (8) @(negedge clk);
        // preload through the actual DMA port (wslot WG+4 = 5), one sector per bank per ecnt
        i = 0;
        while (i < npre) begin
            dq = 0; wslot_v = 0; wslot = 0;
            for (b = 0; b < 8; b = b + 1) if (i < npre && pre[i][258:256] == 3'(b) && !wslot_v[b]) begin
                wslot_v[b] = 1; wslot[b*3 +: 3] = 3'd6;
                dq[b*281 +: 281] = {1'b1, pre[i][271:256], pre[i][255:0], 8'hff};
                i = i + 1;
            end
            if (wslot_v == 0) begin $display("preload order"); $fatal(1, "bench"); end
            @(negedge clk);
        end
        dq = 0; wslot_v = 0; wslot = 0; repeat (12) @(negedge clk);
        // compiler calendar replay: entries for sample ecnt e are presented after ecnt e-1
        base = ecnt + 1;                 // schedule ecnt e == the posedge after which ecnt == base+e
        for (e = 0; e <= last; e = e + 1) begin
            rslot_v = 0; rslot = 0; bank_enable = 0; bank_client = 0; wslot_v = 0; wslot = 0;
            response_enable = 0; response_seq = 0; go = 0;
            for (b = 0; b < 8; b = b + 1) begin
                if (cal[e][b]) begin rslot_v[b] = 1; rslot[b*3 +: 3] = 3'd4; end
                if (cal[e][8+b]) begin bank_enable[b] = 1; bank_client[b*2 +: 2] = 2'd1; end
                if (cal[e][16+b]) begin wslot_v[b] = 1; wslot[b*3 +: 3] = 3'd4; end
            end
            if (cal[e][26]) begin response_enable[1] = 1; response_seq[2 +: 2] = cal[e][25:24]; end
            for (rec_i = 0; rec_i < nrec; rec_i = rec_i + 1) if (rG[rec_i] == e) begin
                    fd = $fopen("rec.txt", "r"); rc = $fscanf(fd, "%d %d\n", i, i);
                for (i = 0; i <= rec_i; i = i + 1)
                    rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h\n", x[0], x[1], x[2], x[3], x[4],
                                 x[5], x[6], x[7], x[8], x[9], x[10], x[11], x[12]);
                $fclose(fd);
                go = 1; k = x[3]; nr = x[4]; ex = x[5]; kk = x[6]; a_mirror = x[7]; a_base = x[8]; a_str = x[9];
                o_base = x[10]; d_base = x[11]; r_base = x[12];
                s_off = x[2] ? 16'hffff : 16'(x[1] - x[0]);
            end
            @(negedge clk);              // after this negedge, posedge base+e samples the values set above
        end
        go = 0; rslot_v = 0; bank_enable = 0; wslot_v = 0; response_enable = 0;
        repeat (16) @(negedge clk);
        // read back every output sector through read group 1 (actual bank path, fixed n+6 response)
        for (i = 0; i < nchk; i = i + 1) begin
            rq_bench = 0; rslot_v = 0; rslot = 0;
            b = chk[i][258:256];
            rq_bench[(1*8+b)*17 +: 17] = {1'b1, chk[i][271:256]};
            rslot_v[b] = 1; rslot[b*3 +: 3] = 3'd1;
            @(negedge clk); rq_bench = 0; rslot_v = 0; rslot = 0;
            repeat (6) @(negedge clk);
            if (rr[(1*8+b)*257 +: 257] !== {1'b1, chk[i][255:0]}) begin
                errors = errors + 1;
                if (errors < 20) $display("VM MISMATCH sector %h got %h expected %h", chk[i][271:256], rr[(1*8+b)*257 +: 256],
                    chk[i][255:0]);
            end
            checked = checked + 1;
        end
        $display("IDX_UNION MUT%0d records%0d dones%0d faults%0d sectors_checked%0d errors%0d schedule_edges%0d", MUT, nrec,
                 dones, faults, checked, errors, last);
        if (errors != 0 || checked != nchk || dones + faults != nrec) $fatal(1, "IDX_UNION FAIL: union record on actual SW slice mismatch");
        for (qq = 0; qq < 4; qq = qq + 1) begin
            if (li[qq] != nl) $fatal(1, "UNION_FACTORED_MISSING q%0d launches %0d of %0d", qq, li[qq], nl);
            if (aborts[qq] != faults) $fatal(1, "UNION_QUAD q%0d aborts %0d expected %0d", qq, aborts[qq], faults);
            $display("UNION_QUAD q%0d LQ %0d launches %0d kernel_words %0d aborts %0d metadata_hold_edges %0d start_hold_records %0d max %0d",
                     qq, lq[qq], li[qq], ks_words[qq], aborts[qq], holds[qq], ext_recs[qq], ext_max[qq]);
        end
        $display("UNION_QUAD lead_min_tap0_to_S %0d", lead_min);
        $display("UNION_QUAD PASS real_IDX_UNION_to_per_quadrant_dispatch+kstore PMUT%0d KLAT%0d", PMUT, KLAT);
        $finish;
    end
endmodule
`default_nettype wire
