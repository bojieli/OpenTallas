`timescale 1ns/1ps
// H-ELEM-A 2026-10-15: static SM x-load (ot_hgi_sm_xload_static, fixed-slot VM read group, no credits) vs the
// production credited x-load (ot_hgi_sm_xload, BF16 packet path over the real ot_hgi_vm_unit): random commands
// (P 1..8, K 1..1,500, random base / stride / slot base), every x-store write identical (address, beat, data) and the
// static load's beats on the cycles its command fixes.  The static load's VM read group is the declared boundary: a
// fixed-latency model of the 8 static banks (sector S on lane S[2:0], response exactly RD_LAT edges later); it checks
// every request's lane/bank and is the stimulus only (the bank RTL has its own exact benches).
// -DMUT1 / -DMUT2 (static load mutants) must FAIL.
module tb_xload_static_lock;
    localparam integer RD_LAT = 6;
`ifdef MUT1
    localparam integer MS = 1;
`elsif MUT2
    localparam integer MS = 2;
`elsif MUT3
    localparam integer MS = 3;
`elsif MUT4
    localparam integer MS = 4;
`else
    localparam integer MS = 0;
`endif
`ifdef XLOAD_LOCAL_MASK_REGS
    localparam integer LM=1;
`else
    localparam integer LM=0;
`endif
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; integer seed = 3, errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 3; $display("SEED=%0d", seed); end
    reg xa_v = 0, xs_v = 0; reg [39:0] x_base = 0; reg [20:0] x_n = 0; reg [3:0] x_p = 0; reg [31:0] x_stride = 0; reg [6:0] x_xb = 0; reg [1:0] x_fmt = 0;
    wire rdy_a, done_a, f_a, en_a; wire [6:0] ad_a, gr_a; wire [2047:0] d_a;
    wire busy_b, done_b, f_b, en_b, last_b; wire [6:0] ad_b, gr_b; wire [2047:0] d_b;
    wire [4*338-1:0] qa; wire [4*274-1:0] ra; wire [273:0] tra; reg [337:0] tq = 0;
    ot_hgi_sm_xload #(.BD(1)) ua (.clk(clk), .rst_n(rst_n), .x_xb(x_xb), .x_v(xa_v), .x_rdy(rdy_a), .x_base(x_base), .x_n(x_n), .x_p(x_p),
        .x_stride(x_stride), .x_space(2'd1), .x_fmt(x_fmt), .xw_ready(1'b1), .xw_last(), .x_done(done_a), .x_fault(f_a),
        .xw_en(en_a), .xw_addr(ad_a), .xw_grp(gr_a), .xw_data(d_a), .vmq(qa), .vmr(ra),
        .rg_req(), .rg_gnt(1'b0), .wrq(), .wrq_cr(32'd0), .wrr({32*257{1'b0}}));
    ot_hgi_vm_unit #(.NC(5)) va (.clk(clk), .rst_n(rst_n), .cq({tq, qa}), .cr({tra, ra}), .status());
    wire [8*17-1:0] rq; reg [8*257-1:0] rr;
`ifdef XLOAD_CL2
    // H-SM 2026-10-15: the hardened-leaf cluster successor (ot_hgi_sm_xload_static_cl2) is the unit under the lock;
    // the flat clock-leaf cl runs beside it on the same stimulus and every output must match on every cycle.
    ot_hgi_sm_xload_static_cl2 #(.RD_LAT(RD_LAT), .MUT(MS)) ub (.clk(clk), .clk_bf(clk), .clk_qlo(clk), .clk_qhi(clk), .clk_bd(clk),
        .rst_n(rst_n), .x_v(xs_v), .x_base(x_base), .x_n(x_n),
`elsif XLOAD_CLOCK_LEAVES
    // five related phase-0 roots of the clock-leaf successor, all from the die clock (local mask capture built in)
    ot_hgi_sm_xload_static_cl #(.RD_LAT(RD_LAT), .MUT(MS)) ub (.clk(clk), .clk_bf(clk), .clk_qlo(clk), .clk_qhi(clk), .clk_bd(clk),
        .rst_n(rst_n), .x_v(xs_v), .x_base(x_base), .x_n(x_n),
`else
    ot_hgi_sm_xload_static #(.RD_LAT(RD_LAT), .MUT(MS), .LOCAL_MASK_REGS(LM)) ub (.clk(clk), .rst_n(rst_n), .x_v(xs_v), .x_base(x_base), .x_n(x_n),
`endif
        .x_p(x_p), .x_stride(x_stride), .x_space(2'd1), .x_fmt(x_fmt), .x_xb(x_xb), .x_busy(busy_b), .x_done(done_b),
        .x_fault(f_b), .xw_en(en_b), .xw_last(last_b), .xw_addr(ad_b), .xw_grp(gr_b), .xw_data(d_b), .rq(rq), .rr(rr));
`ifdef XLOAD_CL2
    wire busy_r, done_r, f_r, en_r, last_r; wire [6:0] ad_r, gr_r; wire [2047:0] d_r; wire [8*17-1:0] rq_r;
    ot_hgi_sm_xload_static_cl #(.RD_LAT(RD_LAT), .MUT(0)) ur (.clk(clk), .clk_bf(clk), .clk_qlo(clk), .clk_qhi(clk), .clk_bd(clk),
        .rst_n(rst_n), .x_v(xs_v), .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(2'd1), .x_fmt(x_fmt),
        .x_xb(x_xb), .x_busy(busy_r), .x_done(done_r), .x_fault(f_r), .xw_en(en_r), .xw_last(last_r), .xw_addr(ad_r),
        .xw_grp(gr_r), .xw_data(d_r), .rq(rq_r), .rr(rr));
    // owner rule 19:50 (every leaf pin registered): cl2 adds exactly XW_ADD = 2 edges to every xw beat and x_done
    // (raw rr pin capture + egress pin capture); rq is unchanged.
    localparam integer XW_ADD = 2;
    reg done_d [0:XW_ADD-1]; reg en_d [0:XW_ADD-1]; reg last_d [0:XW_ADD-1];
    reg [6:0] ad_d [0:XW_ADD-1]; reg [6:0] gr_d [0:XW_ADD-1]; reg [2047:0] dd_d [0:XW_ADD-1];
    always @(posedge clk) begin
        done_d[0] <= done_r; en_d[0] <= en_r; last_d[0] <= last_r; ad_d[0] <= ad_r; gr_d[0] <= gr_r; dd_d[0] <= d_r;
        for (integer i = 1; i < XW_ADD; i = i + 1) begin
            done_d[i] <= done_d[i-1]; en_d[i] <= en_d[i-1]; last_d[i] <= last_d[i-1]; ad_d[i] <= ad_d[i-1]; gr_d[i] <= gr_d[i-1]; dd_d[i] <= dd_d[i-1];
        end
    end
    integer cl2_diff = 0, cl2_cmp = 0;
    always @(posedge clk) if (rst_n && cyc > 20) begin : cl2cmp
        reg bad; bad = 1'b0;
        if (done_b !== done_d[XW_ADD-1] || en_b !== en_d[XW_ADD-1] || last_b !== last_d[XW_ADD-1]) bad = 1'b1;
        if (en_b && (ad_b !== ad_d[XW_ADD-1] || gr_b !== gr_d[XW_ADD-1] || d_b !== dd_d[XW_ADD-1])) bad = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) begin
            if (rq[b*17 + 16] !== rq_r[b*17 + 16]) bad = 1'b1;
            if (rq_r[b*17 + 16] && rq[b*17 +: 16] !== rq_r[b*17 +: 16]) bad = 1'b1;
        end
        cl2_cmp = cl2_cmp + 1;
        if (bad) begin
            if (cl2_diff < 5) $display("ERR cl2 differs from cl (+%0d) at cycle %0d (en %b/%b done %b/%b)", XW_ADD, cyc, en_b, en_d[XW_ADD-1], done_b, done_d[XW_ADD-1]);
            cl2_diff = cl2_diff + 1;
        end
    end
`endif
    // ---- static VM read group model (declared boundary): word memory mirrored from the VM unit writes
    reg [31:0] mem [0:32767];
    integer z; initial for (z = 0; z < 32768; z = z + 1) mem[z] = 0;
    reg [8*257-1:0] pipe [0:RD_LAT-1];
    integer lanefault = 0;
    always @(posedge clk) begin : vmmodel
        reg [8*257-1:0] nw; integer b, w; reg [14:0] s;
        nw = '0;
        for (b = 0; b < 8; b = b + 1) if (rq[b*17 + 16]) begin
            s = rq[b*17 +: 15];
            if (s[2:0] != b[2:0] || rq[b*17 + 15]) lanefault = lanefault + 1;
            nw[b*257 + 256] = 1'b1;
            for (w = 0; w < 8; w = w + 1) nw[b*257 + 32*w +: 32] = mem[{s, 3'(w)}];
        end
        // request visible on rq at edge n -> response on rr at n + RD_LAT
        pipe[0] <= nw;
        for (b = 1; b < RD_LAT; b = b + 1) pipe[b] <= pipe[b-1];
    end
    always @* rr = pipe[RD_LAT-1];
    // ---- x-store write maps
    reg [2047:0] ma [0:16383]; reg [2047:0] mb [0:16383]; reg [16383:0] wa, wb;
    integer first_b, last_bc, nbeats_b;
    integer be_cyc [0:4095]; reg [6:0] be_ad [0:4095]; reg [6:0] be_gr [0:4095];
    // block-dot streaming emission model (= tools/hbm_sm_xload_static_timing.py): pair (k, b) decided at
    // E = max(k WB + n(b), E_prev + 2) after the tpair origin; beat (k, b, a) on the xw pins at command + CBD + E + a
`ifdef XLOAD_CL2
    localparam integer CBD = 27 + 2;          // cl2: + 2 fixed edges (pin-registered landing and egress)
`else
    localparam integer CBD = 27;
`endif
    function automatic integer nall(input integer lav, input integer bb);
        integer p2, j2; nall = 0;
        for (p2 = 0; p2 < 8; p2 = p2 + 1) for (j2 = 0; j2 < lav; j2 = j2 + 1)
            if (p2 * 3152 + 266 * j2 < 2048 * (bb + 1)) nall = nall + 1;
    endfunction
    integer mk, mb2, ma2, me, mprev, mn, mwb, mla, mgtp, mi, bd_bad;
    always @(posedge clk) begin
        if (en_a) begin ma[{ad_a, gr_a}] <= d_a; wa[{ad_a, gr_a}] <= 1'b1; end
        if (en_b) begin mb[{ad_b, gr_b}] <= d_b; wb[{ad_b, gr_b}] <= 1'b1;
                        if (nbeats_b < 4096) begin be_cyc[nbeats_b] = cyc; be_ad[nbeats_b] = ad_b; be_gr[nbeats_b] = gr_b; end
                        nbeats_b = nbeats_b + 1;
                        if (first_b < 0) first_b = cyc; last_bc = cyc; end
    end
    task automatic vm_w(input [31:0] word, input [31:0] data);
        begin
            mem[word[14:0]] = data;
            @(negedge clk); tq = {1'b1, 1'b1, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0; repeat (6) @(negedge clk);
        end
    endtask
    integer c, i, k, nda, ndb, t, t0, nb_e, gn_e, exp_first, exp_beats; reg [31:0] rd;
    always @(posedge clk) begin if (done_a) nda = nda + 1; if (done_b) ndb = ndb + 1; end
    initial begin
        repeat (3) @(posedge clk); rst_n = 1; repeat (6) @(posedge clk);
        for (i = 0; i < 20000; i = i + 1) begin rd = $random(seed); rd[30:23] = 8'd100 + ($unsigned($random(seed)) % 50); if (($unsigned($random(seed)) % 97) == 0) rd = 32'h0; vm_w(i, rd); end
        for (c = 0; c < 24; c = c + 1) begin
            wa = 0; wb = 0; nda = 0; ndb = 0; first_b = -1; nbeats_b = 0;
            x_p = 1 + ($unsigned($random(seed)) % 8); x_n = 1 + ($unsigned($random(seed)) % 1500);
            if (c == 0) begin x_p = 2; x_n = 9000; end            // > 16 groups: x-store word wrap
            x_base = 8 * ($unsigned($random(seed)) % 20); x_stride = 8 * (((x_n + 7) / 8) + ($unsigned($random(seed)) % 3));
            if (c == 0) x_stride = 8 * 1130;
            x_xb = $unsigned($random(seed)) % 128;
            x_fmt = (c < 12) ? 2'd0 : (c % 2 == 0) ? 2'd1 : 2'd2;
            if (x_fmt != 0) begin x_n = 32 * (1 + ($unsigned($random(seed)) % 180)); if (c == 12) begin x_p = 1; x_n = 18432; end
                x_stride = 8 * (((x_n + 7) / 8) + ($unsigned($random(seed)) % 3)); if (c == 12) x_stride = 8 * 2310; end
            @(negedge clk); xa_v = 1; xs_v = 1; t0 = cyc; @(negedge clk); xa_v = 0; xs_v = 0;
            t = 0; while ((nda == 0 || ndb == 0) && t < 400000) begin @(posedge clk); t = t + 1; end
            repeat (4) @(posedge clk);
            // the static load's schedule is a function of the command alone
            nb_e = (x_p * 3152 + 2047) / 2048; gn_e = (x_fmt == 0) ? (x_n - 1) / 512 + 1 : (x_fmt == 1) ? (x_n - 1) / 1024 + 1 : (x_n - 1) / 2048 + 1; exp_beats = gn_e * 8 * nb_e;
            exp_first = 8 * x_p + RD_LAT + 3 + 1 + 1 + 1 + 1 + 7;  // cmd, start, I0, em_off, em_on, E0 -> pins
            if (nbeats_b != exp_beats || (x_fmt == 0 && last_bc - first_b + 1 != exp_beats)) begin
                $display("ERR cmd %0d static beats %0d span %0d expected %0d contiguous", c, nbeats_b, last_bc - first_b + 1, exp_beats);
                errors = errors + 1; end
            if (c == 0) $display("static first beat at command + %0d edges (model %0d)", first_b - t0, exp_first);
            if (x_fmt != 0) begin
                mla = (x_fmt == 2) ? 8 : 4; mwb = ((x_p * mla > 2 * nb_e) ? x_p * mla : 2 * nb_e) + 4; mgtp = gn_e * 4;
                mprev = -1000000; mi = 0; bd_bad = 0;
                for (mk = 0; mk < mgtp; mk = mk + 1) for (mb2 = 0; mb2 < nb_e; mb2 = mb2 + 1) begin
                    mn = nall(mla, mb2); if (mn > x_p * mla) mn = x_p * mla;
                    me = mk * mwb + mn; if (me < mprev + 2) me = mprev + 2; mprev = me;
                    for (ma2 = 0; ma2 < 2; ma2 = ma2 + 1) begin
                        if (mi >= nbeats_b || be_cyc[mi] != t0 + CBD + me + ma2 || be_gr[mi] != 7'(mb2) ||
                            be_ad[mi] != 7'(((mk % 64) * 2 + ma2) + x_xb)) begin
                            if (bd_bad < 3) $display("ERR cmd %0d BD beat %0d (k %0d b %0d a %0d) at %0d grp %0d addr %0d, model edge %0d", c, mi, mk, mb2, ma2,
                                                     (mi < nbeats_b) ? be_cyc[mi] - t0 : -1, be_gr[mi], be_ad[mi], CBD + me + ma2);
                            bd_bad = bd_bad + 1; end
                        mi = mi + 1;
                    end
                end
                if (bd_bad) errors = errors + 1;
                $display("cmd %0d BD streaming: %0d beats on the model edges (%0d off), last beat at command + %0d", c, mi, bd_bad, last_bc - t0);
            end
            for (k = 0; k < 16384; k = k + 1) if (wa[k] || wb[k]) if (wa[k] !== wb[k] || ma[k] !== mb[k]) begin
                if (errors < 5) $display("ERR cmd %0d P %0d K %0d write %0d differs (%b %b)", c, x_p, x_n, k, wa[k], wb[k]);
                errors = errors + 1; end
            $display("cmd %0d fmt %0d P %0d K %0d xb %0d done %0d/%0d beats %0d span %0d", c, x_fmt, x_p, x_n, x_xb, nda, ndb, nbeats_b, last_bc - first_b + 1);
        end
`ifdef XLOAD_CL2
        $display("cl2 vs cl (+%0d edges): %0d cycles compared, %0d differ; fault %b/%b", XW_ADD, cl2_cmp, cl2_diff, f_b, f_r);
        if (cl2_diff || f_r) errors = errors + 1;
`endif
        if (f_b || lanefault) begin $display("static fault %b lanefault %0d", f_b, lanefault); errors = errors + 1; end
        if (errors == 0) $display("XLOAD_STATIC_LOCK PASS"); else $display("XLOAD_STATIC_LOCK FAIL %0d", errors);
        $finish;
    end
endmodule
