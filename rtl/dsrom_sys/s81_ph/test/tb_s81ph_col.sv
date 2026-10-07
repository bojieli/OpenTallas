`timescale 1ns/1ps
// CLAUDE S81-PH: exact bench of the S81 collector slab dsfd_bk_collector (ot_s81ph_col.sv).
// Golden: per job an UNSPLIT result image img[0 .. T-1] of 512-b words (one attention output row each: 16 FP32
// scores of a KV row, or 16 heads of one p.v dim), generated independently of any split.  The four scan services each
// own a subset of the image's rows (split policies: row mod 4 = the engine lane split, contiguous quarters, a random
// owner per row = the CKV owner-stack layout, everything on one stack) and send them as frames
//   header {type 1/2/3, tag, op, len, payload: [19:0] base row, [27:20] stride, [29:28] stack, [45:30] frame seq}
//   + len words (rows base, base+stride, ...), plus len-0 descriptor frames, then a DONE (tag, random code).
// The lanes are valid-only with a random bubble rate (0 = every lane every cycle).  The VM model parses vd and checks:
// every word at least PACE cycles after the previous one, vd[0] (rst_n) high, every frame bit-exact and equal to the
// next frame of the stack it names (per-stack order), frames whole (no word of another frame inside), DONE only after
// all the job's frames and with the job's tag and the OR of the four codes, no FAULT; then the VM image (each word
// written at base + i*stride) equals the golden image.  The next job starts only after the DONE (the VM rule).
// Directed fail-closed cases (+mode=N): 1 overflow, 2 unknown type, 3 DONE tag mismatch, 4 link fault, 5 svc fault
// frame -> a FAULT word with the expected bit and no DONE after it.  Mutants: +define+OT_S81PH_COLMUT1/2.
module tb_s81ph_col;
    localparam integer Q = 4, PACE = 2, DEPTH = 256;
    reg clk = 0, rst_n = 0;
    always #0.4166 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    reg  [514:0] d_in [0:Q-1];      // 0 SW, 1 SE, 2 NW, 3 NE
    wire [513:0] vd; wire vf;
    dsfd_bk_collector #(.PACE(PACE)) u_dut (.ck(clk), .cNE(d_in[3]), .cNW(d_in[2]), .cSE(d_in[1]), .cSW(d_in[0]),
        .rst(rst_n), .vd(vd), .vf(vf));

    int seed, njobs, bub, mode;
    int errors = 0;
    // ---------------- job state
    bit [511:0] img [0:1023];        // golden image of the current job
    bit [511:0] vmi [0:1023];        // VM image
    bit         vmw [0:1023];
    int         T;
    int         jtag;
    bit [10:0]  jcode;
    bit [511:0] lq [0:Q-1][$];       // words still to send, per stack
    bit [511:0] ef [0:Q-1][$];       // expected frame words per stack (headers + data, in order; DONE excluded)
    int         efr [0:Q-1][$];      // frame lengths (words incl. header) per stack, in order
    int         nfr_exp, nfr_got;
    bit         job_live = 0, job_done = 0;
    int         words_out = 0, frames_out = 0, done_out = 0, jobs_ok = 0;
    int         lastw = -1000;
    int         pol;

    function automatic bit [511:0] rnd512();
        bit [511:0] x;
        for (int i = 0; i < 16; i++) x[32*i +: 32] = $urandom;
        return x;
    endfunction
    function automatic bit [511:0] hdr(int typ, int tag, int len, int base, int stride, int st, int seq);
        bit [511:0] h = '0;
        h[511:508] = typ; h[507:500] = tag; h[499:492] = $urandom; h[491:480] = len;
        h[19:0] = base; h[27:20] = stride; h[29:28] = st; h[45:30] = seq;
        h[479:46] = {14{$urandom}};      // opaque payload, carried unchanged
        return h;
    endfunction

    // build job j: golden image, split, frames
    task automatic build_job(int j, int tmax, output bit ok);
        int own [0:1023];
        int rows [0:Q-1][$];
        int seq = 0;
        ok = 1;
        for (int s = 0; s < Q; s++) rows[s].delete();     // (a simulator may keep automatic queues across calls)
        jtag = j & 8'hFF;
        if (tmax == 640) pol = $urandom % 4;
        T = (pol == 3) ? 1 + $urandom % 200 : 1 + $urandom % tmax;
        for (int r = 0; r < T; r++) begin
            img[r] = rnd512(); vmw[r] = 0;
            case (pol)
                0: own[r] = r % 4;
                1: own[r] = (r * 4) / T;
                2: own[r] = $urandom % 4;
                default: own[r] = jtag % 4;
            endcase
            rows[own[r]].push_back(r);
        end
        if (pol == 2) for (int s = 0; s < Q; s++) while (rows[s].size() > 200) begin
            // keep within the capacity contract: move the excess rows to the least loaded stack
            int m = 0; for (int t = 1; t < Q; t++) if (rows[t].size() < rows[m].size()) m = t;
            rows[m].push_back(rows[s].pop_back());
        end
        jcode = 0;
        nfr_exp = 0;
        for (int s = 0; s < Q; s++) begin
            int i = 0;
            bit [10:0] c;
            lq[s].delete(); ef[s].delete(); efr[s].delete();
            if (pol == 2) rows[s].sort();
            while (i < rows[s].size()) begin
                // a descriptor frame now and then
                if ($urandom % 6 == 0) begin
                    bit [511:0] h = hdr(1, jtag, 0, 0, 0, s, seq++);
                    lq[s].push_back(h); ef[s].push_back(h); efr[s].push_back(1); nfr_exp++;
                end
                begin
                    // a run of rows with one stride (row mod 4: stride 4; others: stride 1 runs, else single rows)
                    int base = rows[s][i], stride = 1, n = 1, lim = 16 + $urandom % 48;
                    if (i + 1 < rows[s].size()) stride = rows[s][i+1] - base;
                    if (stride > 255) stride = 1;
                    while (i + n < rows[s].size() && n < lim && rows[s][i+n] == base + n * stride) n++;
                    begin
                        bit [511:0] h = hdr(2 + $urandom % 2, jtag, n, base, stride, s, seq++);
                        lq[s].push_back(h); ef[s].push_back(h); efr[s].push_back(n + 1); nfr_exp++;
                        for (int k = 0; k < n; k++) begin lq[s].push_back(img[base + k * stride]); ef[s].push_back(img[base + k * stride]); end
                    end
                    i += n;
                end
            end
            c = $urandom;
            jcode |= c;
            begin
                bit [511:0] dn = '0;
                dn[511:508] = 4; dn[507:500] = jtag; dn[10:0] = c; dn[479:11] = {15{$urandom}};
                lq[s].push_back(dn);
            end
            if (lq[s].size() > DEPTH) ok = 0;
        end
        nfr_got = 0;
    endtask

    // ---------------- drivers
    int fault_lane = -1, fault_at = -1;
    always @(posedge clk) begin
        for (int s = 0; s < Q; s++) begin
            d_in[s] <= {1'b0, 1'b1, 512'd0, 1'b0};
            if (rst_n && job_live && lq[s].size() > 0 && ($urandom % 100) >= bub) begin
                d_in[s] <= {(mode == 4 && s == fault_lane && lq[s].size() == fault_at), 1'b1, lq[s].pop_front(), 1'b1};
            end
        end
    end

    // ---------------- VM model
    int  in_fr = 0, fr_left = 0, fr_st = -1, fr_base = 0, fr_stride = 0, fr_k = 0;
    bit  fault_seen = 0; bit [4:0] fault_bits = 0; bit done_after_fault = 0;
    always @(posedge clk) if (rst_n && cyc > 14) begin
        if (vd[0] !== 1'b1) begin errors++; if (errors < 10) $display("ERR vd rst_n low cyc %0d", cyc); end
        if (vd[1]) begin
            bit [511:0] w;
            int typ, st;
            w = vd[513:2];
            if (cyc - lastw < PACE) begin errors++; if (errors < 10) $display("ERR pace cyc %0d", cyc); end
            lastw = cyc; words_out++;
            if (in_fr) begin
                if (fault_seen) ;
                else if (ef[fr_st].size() == 0 || w !== ef[fr_st][0]) begin
                    errors++; if (errors < 10) $display("ERR data word stack %0d k %0d cyc %0d", fr_st, fr_k, cyc);
                    if (ef[fr_st].size()) void'(ef[fr_st].pop_front());
                end else begin
                    void'(ef[fr_st].pop_front());
                    vmi[fr_base + fr_k * fr_stride] = w; vmw[fr_base + fr_k * fr_stride] = 1;
                end
                fr_k++;
                if (--fr_left == 0) in_fr = 0;
            end else begin
                typ = w[511:508];
                if (typ == 5 && w[45:30] == 0 && w[15:11] != 0) begin
                    // collector FAULT word
                    fault_seen = 1; fault_bits |= w[15:11];
                    if (mode == 0) begin errors++; $display("ERR FAULT bits %b cyc %0d", w[15:11], cyc); end
                end else if (typ == 4) begin
                    if (fault_seen) done_after_fault = 1;
                    if (mode == 0) begin
                        if (w[507:500] != jtag || w[10:0] != jcode || nfr_got != nfr_exp) begin
                            errors++; $display("ERR DONE tag %0d/%0d code %h/%h frames %0d/%0d cyc %0d", w[507:500], jtag,
                                               w[10:0], jcode, nfr_got, nfr_exp, cyc);
                        end
                        for (int r = 0; r < T; r++) if (!vmw[r] || vmi[r] !== img[r]) begin
                            errors++; if (errors < 10) $display("ERR image row %0d", r);
                        end
                    end
                    done_out++; job_done = 1;
                end else begin
                    st = w[29:28];
                    nfr_got++; frames_out++;
                    if (fault_seen) ;
                    else if (ef[st].size() == 0 || w !== ef[st][0]) begin
                        errors++; if (errors < 10) $display("ERR header (stack %0d) not the stack's next frame cyc %0d", st, cyc);
                    end else void'(ef[st].pop_front());
                    fr_st = st; fr_base = w[19:0]; fr_stride = w[27:20]; fr_k = 0; fr_left = w[491:480];
                    in_fr = (fr_left != 0);
                end
            end
        end
    end

    int maxcyc;
    always @(posedge clk) if (cyc == maxcyc) begin
        $display("WATCHDOG cyc %0d job_live %0d job_done %0d lq %0d %0d %0d %0d ef %0d %0d %0d %0d words %0d", cyc, job_live, job_done,
                 lq[0].size(), lq[1].size(), lq[2].size(), lq[3].size(), ef[0].size(), ef[1].size(), ef[2].size(), ef[3].size(), words_out);
        $display("RESULT FAIL watchdog");
        $finish;
    end
    initial begin
        if (!$value$plusargs("maxcyc=%d", maxcyc)) maxcyc = 20000000;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("jobs=%d", njobs)) njobs = 40;
        if (!$value$plusargs("bub=%d", bub)) bub = -1;
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        void'($urandom(seed));
        for (int s = 0; s < Q; s++) d_in[s] = '0;
        repeat (8) @(posedge clk);
        rst_n = 1;
        repeat (20) @(posedge clk);
        if (mode == 0) begin
            for (int j = 0; j < njobs; j++) begin
                int b0, tm; bit ok;
                b0 = bub; tm = 640;
                do begin build_job(j, tm, ok); tm = tm * 3 / 4; end while (!ok);
                if (b0 < 0) bub = (j % 3 == 0) ? 0 : (j % 3 == 1) ? 30 : 80;
                job_done = 0; job_live = 1;
                begin
                    int w0; w0 = cyc;
                    while (!job_done && cyc - w0 < 200000) @(posedge clk);
                    if (!job_done) begin $display("ERR timeout job %0d cyc %0d", j, cyc); errors++; end
                end
                job_live = 0;
                for (int s = 0; s < Q; s++) if (ef[s].size() != 0) begin errors++; $display("ERR stack %0d %0d words never delivered", s, ef[s].size()); end
                $display("job %0d pol %0d T %0d bub %0d frames %0d cyc %0d", j, pol, T, bub, nfr_exp, cyc); $fflush;
                if (errors == 0) jobs_ok++;
                if (b0 < 0) bub = -1;
                if (errors > 20) break;
                repeat ($urandom % 20) @(posedge clk);
            end
            $display("RESULT %s jobs %0d/%0d words %0d frames %0d done %0d errors %0d", (errors == 0 && jobs_ok == njobs) ? "PASS" : "FAIL",
                     jobs_ok, njobs, words_out, frames_out, done_out, errors);
        end else begin
            int expbit; bit ok; bit [511:0] x;
            pol = 0;
            build_job(1, 300, ok);
            bub = 0;
            expbit = (mode == 1) ? 11 : (mode == 2) ? 12 : (mode == 3) ? 13 : (mode == 4) ? 14 : 15;
            case (mode)
                1: begin lq[0].delete(); for (int i = 0; i < 700; i++) lq[0].push_back(hdr(1, jtag, 0, 0, 0, 0, i + 1)); end
                2: begin x = hdr(7, jtag, 0, 0, 0, 1, 1); lq[1].push_front(x); end
                3: begin x = lq[2][$]; x[507:500] = jtag ^ 8'h5A; lq[2][$] = x; end
                4: begin fault_lane = 3; fault_at = lq[3].size() / 2 + 1; end
                5: begin x = hdr(5, jtag, 0, 0, 0, 1, 777); lq[1].push_front(x); end
            endcase
            job_live = 1;
            repeat (6000) @(posedge clk);
            $display("fault case mode %0d: FAULT bits %b expected bit %0d %s, DONE after FAULT %0d", mode, fault_bits, expbit,
                     fault_bits[expbit - 11] ? "seen" : "MISSING", done_after_fault);
            $display("RESULT %s fault mode %0d", (fault_seen && fault_bits[expbit - 11] && !done_after_fault) ? "PASS" : "FAIL", mode);
        end
        $finish;
    end
endmodule
