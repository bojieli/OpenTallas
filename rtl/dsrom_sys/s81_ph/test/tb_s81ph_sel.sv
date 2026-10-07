`timescale 1ns/1ps
// CLAUDE S81-PH: exact bench of the S81 selector slab dsfd_bk_selector against the UNCHANGED reference
// ot_hdc_v41x_sel (native ports, behavioural line memory as ot_hdc_v41x_xu_adapt).  Both get the same segments
// (same beats, same bubble pattern, the slab through its die lane words: header + score beats + rebase, index
// reconstructed in the slab); the reference re-streams after each rep_req pulse, the slab after each REP word.
// Checked per segment: every out beat (quarter, lane valids, indices, -inf flags, last) in order, the selected count,
// the overflow / replay count, no fault; at most one vd word every PACE cycles.  Directed fail-closed cases: k
// mismatch, orphan beat, qslot collision -> FAULT word with the right bit.  Mutants: +define+OT_S81PH_MUT1/2/3.
module tb_s81ph_sel #(parameter integer SEARCH_PIPE = 0, parameter integer CMP_RETIME = 0);
    localparam integer Q = 4, W = 16, IW = 20, K = 512, AW = 8, EW = 37, PACE = 2;
    reg clk = 0, rst_n = 0;
    always #0.4166 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ---------------- reference
    reg  [Q-1:0] r_iv, r_il; reg [Q*W-1:0] r_ilv; reg [Q*W*16-1:0] r_ival; reg [Q*W*IW-1:0] r_iidx; reg [9:0] r_k;
    wire [Q-1:0] r_ir, r_ov, r_ol; wire [Q*W-1:0] r_olv, r_oninf; wire [Q*W*16-1:0] r_oval; wire [Q*W*IW-1:0] r_oidx;
    wire [Q-1:0] r_mwe, r_mre; wire [Q*AW-1:0] r_mwa, r_mra; wire [Q*W*EW-1:0] r_mwd; reg [Q*W*EW-1:0] r_mrd;
    wire r_rep, r_ovf, r_busy;
    ot_hdc_v41x_sel #(.Q(Q), .W(W), .IW(IW), .K(K), .AW(AW)) u_ref (.clk(clk), .rst_n(rst_n), .in_valid(r_iv),
        .in_ready(r_ir), .in_last(r_il), .in_lv(r_ilv), .in_val(r_ival), .in_idx(r_iidx), .in_k(r_k),
        .out_valid(r_ov), .out_ready({Q{1'b1}}), .out_last(r_ol), .out_lv(r_olv), .out_val(r_oval), .out_idx(r_oidx),
        .out_ninf(r_oninf), .mem_we(r_mwe), .mem_waddr(r_mwa), .mem_wdata(r_mwd), .mem_re(r_mre), .mem_raddr(r_mra),
        .mem_rdata(r_mrd), .rep_req(r_rep), .ovf(r_ovf), .busy(r_busy), .stats());
    reg [W*EW-1:0] lm [0:Q*(1<<AW)-1];
    integer mq;
    always @(posedge clk) for (mq = 0; mq < Q; mq = mq + 1) begin
        if (r_mwe[mq]) lm[mq*(1<<AW) + r_mwa[AW*mq +: AW]] <= r_mwd[W*EW*mq +: W*EW];
        if (r_mre[mq]) r_mrd[W*EW*mq +: W*EW] <= lm[mq*(1<<AW) + r_mra[AW*mq +: AW]];
    end

    // ---------------- DUT
    reg  [514:0] d_in [0:Q-1];      // index = input lane (0 SW, 1 SE, 2 NW, 3 NE)
    wire [513:0] vd; wire vf;
    dsfd_bk_selector #(.CMP_RETIME(CMP_RETIME), .SEARCH_PIPE(SEARCH_PIPE)) u_dut (.ck(clk), .iNE(d_in[3]), .iNW(d_in[2]), .iSE(d_in[1]), .iSW(d_in[0]), .rst(rst_n),
        .vd(vd), .vf(vf));

    // ---------------- segment description
    // per quarter slot q: beats (lv, vals, idx base, last) + rebase markers
    typedef struct { bit reb; bit [19:0] pos; bit [15:0] lv; bit [255:0] val; bit last; } item_t;
    item_t it [0:Q-1][$];
    int perm [0:Q-1];               // input lane s feeds quarter slot perm[s]
    int seg_k; int seg_tag; int hdr_base [0:Q-1];
    int bub_pct; int ref_holds = 0;

    function automatic bit [15:0] rbf(int fam, int pos);
        bit [15:0] x;
        case (fam)
            1: begin int r = $urandom % 5; x = (r == 0) ? 16'h3F80 : (r == 1) ? 16'h4000 : (r == 2) ? 16'hBF80 : (r == 3) ? 16'h0000 : 16'h8000; end
            2: x = ($urandom % 10 < 7) ? 16'hFF80 : 16'($urandom);
            3: x = 16'h3F80 + 16'(pos >> 4);             // ascending: every key survives -> overflow
            4: x = {1'b0, 7'h3C + 7'($urandom % 6), 8'($urandom)};
            5: x = 16'h4040;                             // all equal: tie quota across quarters, overflow
            default: x = 16'($urandom);
        endcase
        if (x[14:7] == 8'hFF && x[6:0] != 0) x[6:0] = 0;   // no NaN (outside the contract)
        return x;
    endfunction

    task automatic make_seg(int fam, int nmax, int k, bit allow_reb, bit allow_empty);
        int pos; int p [0:Q-1];
        for (int q = 0; q < Q; q++) it[q].delete();
        // random permutation lane -> slot
        for (int s = 0; s < Q; s++) p[s] = s;
        for (int s = Q - 1; s > 0; s--) begin int j = $urandom % (s + 1); int t = p[s]; p[s] = p[j]; p[j] = t; end
        for (int s = 0; s < Q; s++) perm[s] = p[s];
        seg_k = k; seg_tag = $urandom % 256;
        pos = $urandom % 64;
        for (int q = 0; q < Q; q++) begin
            int nb = (fam >= 3 && fam != 4) ? nmax / 16 : (allow_empty && $urandom % 6 == 0) ? 0 : 1 + ($urandom % ((nmax + 15) / 16));
            hdr_base[q] = pos;
            if (nb == 0) begin
                item_t e; e.reb = 0; e.pos = pos; e.lv = 0; e.val = 0; e.last = 1; it[q].push_back(e);
            end else for (int b = 0; b < nb; b++) begin
                item_t e;
                if (allow_reb && b > 0 && $urandom % 20 == 0) begin
                    item_t r; pos = pos + 1 + ($urandom % 300); r.reb = 1; r.pos = pos; r.lv = 0; r.val = 0; r.last = 0;
                    it[q].push_back(r);
                end
                e.reb = 0; e.pos = pos; e.last = (b == nb - 1);
                e.lv = ($urandom % 12 == 0) ? 16'h0 : ($urandom % 3 == 0) ? 16'($urandom) : 16'hFFFF;
                for (int l = 0; l < 16; l++) e.val[16*l +: 16] = rbf(fam, pos + l);
                it[q].push_back(e);
                pos = pos + 16;
            end
            pos = pos + ($urandom % 40);
        end
    endtask

    // ---------------- drivers
    // bubble pattern shared by both drivers of a pass (same seed)
    task automatic drive_ref();
        int ix [0:Q-1]; bit busy;
        for (int q = 0; q < Q; q++) ix[q] = 0;
        r_k = 10'(seg_k);
        busy = 1;
        while (busy) begin
            @(negedge clk);
            r_iv = 0; r_il = 0; r_ilv = 0; r_ival = 0; r_iidx = 0;
            busy = 0;
            for (int q = 0; q < Q; q++) begin
                while (ix[q] < it[q].size() && it[q][ix[q]].reb) ix[q]++;
                if (ix[q] < it[q].size()) begin
                    busy = 1;
                    if ($urandom % 100 >= bub_pct) begin
                        item_t e = it[q][ix[q]];
                        r_iv[q] = 1; r_il[q] = e.last; r_ilv[W*q +: W] = e.lv; r_ival[256*q +: 256] = e.val;
                        for (int l = 0; l < 16; l++) r_iidx[320*q + 20*l +: 20] = 20'(e.pos + l);
                    end
                end
            end
            #0.2;   // in_ready is a registered function: sample it before the accepting edge
            for (int q = 0; q < Q; q++) if (r_iv[q]) begin
                if (!r_ir[q]) ref_holds++;      // the reference waits (valid/ready); the slab may not
                else ix[q]++;
            end
            @(posedge clk);
        end
        @(negedge clk); r_iv = 0;
    endtask

    task automatic drive_dut(bit bad_k, bit orphan, bit coll);
        int ix [0:Q-1]; bit hs [0:Q-1]; bit busy;
        for (int s = 0; s < Q; s++) begin ix[s] = 0; hs[s] = 0; end
        busy = 1;
        while (busy) begin
            @(negedge clk);
            busy = 0;
            for (int s = 0; s < Q; s++) begin
                int q = perm[s];
                d_in[s] = {1'b0, 1'b1, 512'd0, 1'b0};
                if (!hs[s] || ix[q] < it[q].size()) begin
                    busy = 1;
                    if ($urandom % 100 >= bub_pct) begin
                        bit [511:0] d = 0;
                        if (!hs[s] && !(orphan && s == 0)) begin
                            d[511:508] = 1; d[507:500] = 8'(seg_tag); d[19:0] = 20'(hdr_base[q]);
                            d[29:20] = 10'(bad_k && s == 1 ? seg_k ^ 1 : seg_k);
                            d[31:30] = 2'(coll && s == 1 ? perm[0] : q);
                            hs[s] = 1;
                        end else begin
                            item_t e = it[q][ix[q]];
                            hs[s] = 1;
                            if (e.reb) begin d[511:508] = 6; d[19:0] = e.pos; end
                            else begin d[511:508] = 2; d[255:0] = e.val; d[271:256] = e.lv; d[272] = e.last; end
                            d[507:500] = 8'(seg_tag);
                            ix[q]++;
                        end
                        d_in[s] = {1'b0, 1'b1, d, 1'b1};
                    end
                end
            end
            @(posedge clk);
        end
        @(negedge clk);
        for (int s = 0; s < Q; s++) d_in[s] = {1'b0, 1'b1, 512'd0, 1'b0};
    endtask

    // ---------------- collectors
    typedef struct { bit [15:0] lv; bit [319:0] idx; bit [15:0] ninf; bit last; int q; } ob_t;
    ob_t rq_ [$];                 // reference beats, concatenated in quarter order at segment end
    ob_t rqq [0:Q-1][$];
    int r_reps, r_lastq, r_lastcyc;
    always @(posedge clk) if (rst_n) begin
        for (int q = 0; q < Q; q++) if (r_ov[q]) begin
            ob_t o; o.lv = r_olv[W*q +: W]; o.idx = r_oidx[320*q +: 320]; o.ninf = r_oninf[W*q +: W]; o.last = r_ol[q]; o.q = q;
            rqq[q].push_back(o);
            if (r_ol[q]) begin r_lastq++; r_lastcyc = cyc; end
        end
        if (r_rep) r_reps++;
    end
    bit [511:0] dw [$]; int dcyc [$]; int last_vd = -100; int pace_err = 0;
    always @(posedge clk) if (vd[1]) begin
        if (cyc - last_vd < PACE) pace_err++;
        last_vd = cyc;
        dw.push_back(vd[513:2]); dcyc.push_back(cyc);
    end

    int errors = 0, segs = 0, reps_total = 0, lat_max = 0, lat_sum = 0, beats_total = 0;
    task automatic run_seg(string name);
        int d_reps = 0, rr = 0; bit d_done = 0; int t0;
        int dix = 0; bit [511:0] done_w;
        d_reps = 0; rr = 0; d_done = 0; dix = 0; done_w = 0;
        for (int q = 0; q < Q; q++) rqq[q].delete();
        r_reps = 0; r_lastq = 0; dw.delete(); dcyc.delete();
        bub_pct = $urandom % 3 == 0 ? 0 : $urandom % 25;
        t0 = cyc;
        fork drive_ref(); drive_dut(0, 0, 0); join
        // replays
        fork
            begin   // reference
                while (r_lastq < Q) begin
                    @(posedge clk);
                    if (r_reps > rr) begin rr++; drive_ref(); end
                end
            end
            begin   // DUT
                while (!d_done) begin
                    @(posedge clk);
                    while (dix < dw.size()) begin
                        bit [511:0] w = dw[dix]; dix++;
                        if (w[511:508] == 7) begin d_reps++; drive_dut(0, 0, 0); end
                        else if (w[511:508] == 4) begin d_done = 1; done_w = w; end
                        else if (w[511:508] == 5) begin $display("FAIL %s: FAULT word %h", name, w[15:11]); errors++; d_done = 1; end
                    end
                end
            end
        join
        // compare
        begin
            int n = 0; int cnt = 0; int k = 0;
            ob_t rl [$];
            rl.delete(); n = 0; cnt = 0; k = 0;   // block variables are not re-initialised per call
            for (int q = 0; q < Q; q++) foreach (rqq[q][j]) rl.push_back(rqq[q][j]);
            foreach (dw[j]) if (dw[j][511:508] == 3) begin
                bit [511:0] w = dw[j];
                if (k >= rl.size()) begin errors++; $display("FAIL %s: extra IDX word", name); break; end
                if (w[335:320] != rl[k].lv || w[353:352] != rl[k].q[1:0] || w[354] != rl[k].last ||
                    w[351:336] != rl[k].ninf) begin errors++; $display("FAIL %s beat %0d: lv %h/%h q %0d/%0d last %0d/%0d", name, k, w[335:320], rl[k].lv, w[353:352], rl[k].q, w[354], rl[k].last); end
                for (int l = 0; l < 16; l++) if (rl[k].lv[l]) begin
                    cnt++;
                    if (w[20*l +: 20] != rl[k].idx[20*l +: 20]) begin errors++; if (errors < 10) $display("FAIL %s beat %0d lane %0d idx %0d ref %0d", name, k, l, w[20*l +: 20], rl[k].idx[20*l +: 20]); end
                end
                k++;
            end
            if (k != rl.size()) begin errors++; $display("FAIL %s: %0d IDX words, ref %0d beats (per q %0d %0d %0d %0d, lastq %0d)", name, k, rl.size(), rqq[0].size(), rqq[1].size(), rqq[2].size(), rqq[3].size(), r_lastq);
                for (int q = 0; q < Q; q++) foreach (rqq[q][j]) if (j < 3 || rqq[q][j].last) $display("   ref q%0d b%0d lv %h idx0 %0d last %0d", q, j, rqq[q][j].lv, rqq[q][j].idx[19:0], rqq[q][j].last);
                foreach (dw[j]) if (dw[j][511:508] == 3) $display("   dut q%0d lv %h idx0 %0d last %0d", dw[j][353:352], dw[j][335:320], dw[j][19:0], dw[j][354]); end
            if (done_w[9:0] != 10'(cnt)) begin errors++; $display("FAIL %s: DONE count %0d ref %0d", name, done_w[9:0], cnt); end
            if (done_w[15:11] != 0) begin errors++; $display("FAIL %s: DONE fault %h", name, done_w[15:11]); end
            if (d_reps != r_reps || done_w[10] != (r_reps > 0)) begin errors++; $display("FAIL %s: replays %0d ref %0d ovf %0d", name, d_reps, r_reps, done_w[10]); end
            beats_total += rl.size();
            if (dcyc.size() > 0) begin int lat = dcyc[dcyc.size()-1] - r_lastcyc; if (lat > lat_max) lat_max = lat; lat_sum += lat;
                $display("seg %0d %s k %0d sel %0d beats %0d reps %0d tail_slab_minus_ref %0d cyc %0d", segs, name, seg_k, cnt, rl.size(), r_reps, lat, cyc); $fflush; end
            reps_total += r_reps;
        end
        segs++;
        repeat (20) @(posedge clk);
    endtask

    task automatic wait_ready();
        bit ok = 0;
        dw.delete();
        while (!ok) begin @(posedge clk); foreach (dw[j]) if (dw[j][511:508] == 4) ok = 1; end
        repeat (2) @(posedge clk);
    endtask

    task automatic fault_case(string name, int bit_, bit bad_k, bit orphan, bit coll);
        bit seen = 0; int t;
        dw.delete();
        make_seg(0, 200, 64, 0, 0);
        bub_pct = 0;
        drive_dut(bad_k, orphan, coll);
        for (t = 0; t < 400 && !seen; t++) begin
            @(posedge clk);
            foreach (dw[j]) if (dw[j][511:508] == 5 && dw[j][bit_]) seen = 1;
        end
        $display("fault case %s: FAULT bit %0d %s", name, bit_, seen ? "seen" : "MISSING");
        if (!seen) errors++;
        rst_n = 0; repeat (5) @(posedge clk); rst_n = 1; wait_ready();
        // the reference saw nothing; nothing to reset there
    endtask

    initial begin
        for (int s = 0; s < Q; s++) d_in[s] = {1'b0, 1'b1, 512'd0, 1'b0};
        r_iv = 0; r_il = 0; r_ilv = 0; r_ival = 0; r_iidx = 0; r_k = 0;
        void'($urandom(20261006));
        repeat (8) @(posedge clk); rst_n = 1; wait_ready();
        if ($test$plusargs("dbg")) begin
            make_seg(0, 200, 16, 1, 0);
            for (int q = 0; q < Q; q++) foreach (it[q][j]) $display("slot %0d item %0d reb %0d pos %0d lv %h last %0d", q, j, it[q][j].reb, it[q][j].pos, it[q][j].lv, it[q][j].last);
            run_seg("dbg");
            for (int q = 0; q < Q; q++) foreach (rqq[q][j]) $display("ref q%0d lv %h idx0 %0d idx1 %0d last %0d", q, rqq[q][j].lv, rqq[q][j].idx[19:0], rqq[q][j].idx[39:20], rqq[q][j].last);
            foreach (dw[j]) $display("dut type %0d q %0d lv %h idx0 %0d idx1 %0d last %0d", dw[j][511:508], dw[j][353:352], dw[j][335:320], dw[j][19:0], dw[j][39:20], dw[j][354]);
            $finish;
        end
        if (!$test$plusargs("rand_only")) begin
        // directed
        make_seg(0, 3000, 512, 1, 1); run_seg("uniform_k512");
        make_seg(1, 2000, 300, 0, 0); run_seg("ties");
        make_seg(2, 2000, 512, 1, 0); run_seg("neginf");
        make_seg(0, 40, 512, 0, 1);   run_seg("k_gt_n");
        make_seg(0, 1, 7, 0, 1);      run_seg("tiny");
        make_seg(4, 12000, 512, 1, 0); run_seg("normal_12k");
        make_seg(3, 50000, 512, 0, 0); run_seg("ascending_overflow");
        make_seg(5, 20000, 300, 1, 0); run_seg("all_equal_overflow");
        end
        // random
        for (int r = 0; r < 24; r++) begin
            make_seg($urandom % 5 == 3 ? 0 : $urandom % 5, 1 + $urandom % 6000, 1 + $urandom % 512, $urandom % 2, $urandom % 2);
            run_seg($sformatf("rand%0d", r));
        end
        // fail-closed
        fault_case("k_mismatch", 13, 1, 0, 0);
        fault_case("orphan_beat", 11, 0, 1, 0);
        fault_case("qslot_collision", 12, 0, 0, 1);
        if (pace_err) begin errors++; $display("FAIL pace: %0d vd words closer than %0d cycles", pace_err, PACE); end
        $display("RESULT %s segments %0d out_beats %0d replays %0d errors %0d tail_minus_ref max %0d mean %0d ref_holds %0d",
                 errors == 0 ? "PASS" : "FAIL", segs, beats_total, reps_total, errors, lat_max, lat_sum / segs, ref_holds);
        $finish;
    end
    initial begin #3000000; $display("FAIL timeout cyc %0d dw %0d", cyc, dw.size()); foreach (dw[j]) $display("  w %0d type %0d", j, dw[j][511:508]); $finish; end
    always @(posedge clk) if (cyc % 20000 == 0) begin $display("cyc %0d", cyc); $fflush; end
endmodule
