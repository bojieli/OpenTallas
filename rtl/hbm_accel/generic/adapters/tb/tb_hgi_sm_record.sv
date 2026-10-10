`timescale 1ns/1ps
// hgi-adapters (2026-10-09): bench of ot_hgi_sm_record.  Vectors: tools/hgi_adapters/sm_bench.py (+DIR=).
//  RUN cases: records -> adapter H -> 32 stub SM elements (start / d_valid handshakes with random ready, busy for
//    d_lines + random cycles, then arrive toggles), stub x-load and publication services (random latency).  Every SM's
//    command word at start == the reference (SM layout rule), inactive SMs are never started, the x / publication
//    commands == the reference, the SMs start only after x_done, and each record retires once, in order, only after
//    every active SM arrived and the publication completed; released (release_in == arrive) after the retire.
//  NEGATIVE cases: rec_fault, nothing issued, halted.
//  LOCKSTEP: adapter L (hgi_en 0) with random legacy per-SM buses: sm_cmd == lg_cmd and lg_ret == sm_ret every cycle.
// Prints HGI_SM PASS / HGI_SM FAIL.
module tb_hgi_sm_record;
`ifdef MUT_ROWS
    localparam integer MR = 1;
`else
    localparam integer MR = 0;
`endif
`ifdef MUT_EARLY
    localparam integer ME = 1;
`else
    localparam integer ME = 0;
`endif
    `include "sm_sizes.svh"
    localparam integer NSM = 32, CW = 106;
    reg clk = 0;
    always #1 clk = ~clk;
    reg [937:0]    recm [0:NREC-1];
    reg [REFB-1:0] refm [0:NREC-1];
    reg [95:0]     casem [0:NCASE-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/sm_rec.mem"}, recm); $readmemh({dir, "/sm_ref.mem"}, refm); $readmemh({dir, "/sm_case.mem"}, casem);
    end
    integer errors = 0, cyc = 0, seed = 1;
    always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0;
    reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted;
    wire x_v, pub_v; reg x_rdy = 0, pub_rdy = 0, x_done = 0, pub_done = 0;
    wire [39:0] x_base, pub_base; wire [20:0] x_n; wire [3:0] x_p, pub_p; wire [31:0] x_stride, pub_stride;
    wire [1:0] x_space, x_fmt, pub_space; wire [19:0] pub_m; wire [12:0] pub_q;
    wire [NSM*CW-1:0] sm_cmd; reg [NSM*4-1:0] sm_ret = 0;
    ot_hgi_sm_record #(.MUT_ROWS(MR), .MUT_EARLY(ME)) u_h (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1),
        .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]),
        .rec_o(cur[895:640]), .rec_n_a(cur[916:896]), .rec_n_b(cur[937:917]), .rec_done(done), .rec_fault(fault),
        .halted(halted), .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride),
        .x_space(x_space), .x_fmt(x_fmt), .x_done(x_done), .x_fault(1'b0), .pub_v(pub_v), .pub_rdy(pub_rdy),
        .pub_base(pub_base), .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q),
        .pub_p(pub_p), .pub_done(pub_done), .pub_fault(1'b0), .lg_cmd({NSM*CW{1'b0}}), .lg_ret(), .sm_cmd(sm_cmd),
        .sm_ret(sm_ret));
    // ---- legacy-mode identity
    reg [NSM*CW-1:0] lgc; reg [NSM*4-1:0] lgr; wire [NSM*CW-1:0] l_cmd; wire [NSM*4-1:0] l_ret; integer q, lock_n = 0;
    wire l_rdy, l_done, l_fault;
    ot_hgi_sm_record #(.MUT_ROWS(MR), .MUT_EARLY(ME)) u_l (.clk(clk), .rst_n(rst_n), .hgi_en(1'b0),
        .rec_v(1'b1), .rec_rdy(l_rdy), .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]),
        .rec_o(cur[895:640]), .rec_n_a(cur[916:896]), .rec_n_b(cur[937:917]), .rec_done(l_done), .rec_fault(l_fault),
        .halted(), .x_v(), .x_rdy(1'b1), .x_base(), .x_n(), .x_p(), .x_stride(), .x_space(), .x_fmt(), .x_done(1'b1),
        .x_fault(1'b0), .pub_v(), .pub_rdy(1'b1), .pub_base(), .pub_stride(), .pub_space(), .pub_m(), .pub_q(),
        .pub_p(), .pub_done(1'b1), .pub_fault(1'b0), .lg_cmd(lgc), .lg_ret(l_ret), .sm_cmd(l_cmd), .sm_ret(lgr));
    always @(posedge clk) begin
        for (q = 0; q < NSM*CW; q = q + 32) lgc[q +: 32] <= $random(seed);
        lgr <= $random(seed);
        if (rst_n) begin
            lock_n = lock_n + 1;
            if (l_cmd !== lgc || l_ret !== lgr || l_rdy || l_done || l_fault) begin
                if (errors < 20) $display("ERR legacy identity at %0d", cyc);
                errors = errors + 1;
            end
        end
    end
    // ---- stub SMs
    integer s, k = 0, base = 0, issued = 0, x_seen = 0, pub_seen = 0;
    integer busy [0:NSM-1];
    reg [NSM-1:0] started, arrived_now, st_ok;
    reg x_got, xdone_q, pub_got, pdone_q;
    integer xlat, plat;
    reg [REFB-1:0] rw;
    always @(posedge clk) begin
        rw = refm[base + k];
        // x load / publication services
        x_rdy <= ($random(seed) & 1); pub_rdy <= ($random(seed) & 1); x_done <= 0; pub_done <= 0;
        if (rst_n && x_v && x_rdy) begin
            x_got = 1; xlat = 3 + ($random(seed) & 31); x_seen = x_seen + 1;
            if (rw[REFB-1 -: 4] == 4'd0 && {x_base, x_n, x_p, x_stride, x_space} !== rw[REFB-5 -: 99]) begin
                $display("ERR x command mismatch at record %0d", base + k); errors = errors + 1; end
        end else if (x_got) begin
            if (xlat == 0) begin x_done <= 1; x_got = 0; xdone_q = 1; end else xlat = xlat - 1;
        end
        if (rst_n && pub_v && pub_rdy) begin
            pub_got = 1; plat = 0; pub_seen = pub_seen + 1;
            if (rw[REFB-1 -: 4] == 4'd0 && {pub_base, pub_stride, pub_space, pub_m, pub_q, pub_p} !== rw[REFB-104 -: 111]) begin
                $display("ERR publication command mismatch at record %0d", base + k); errors = errors + 1; end
        end
        for (s = 0; s < NSM; s = s + 1) begin
            sm_ret[s*4 + 0] <= (busy[s] == 0) && ($random(seed) & 1);  // start_ready
            sm_ret[s*4 + 1] <= ($random(seed) & 1);                    // d_ready
            if (rst_n && sm_cmd[s*CW] && sm_ret[s*4 + 0]) begin
                if (!xdone_q) begin $display("ERR SM %0d started before x_done", s); errors = errors + 1; end
                if (started[s]) begin $display("ERR SM %0d started twice", s); errors = errors + 1; end
                started[s] = 1; issued = issued + 1;
                busy[s] = 4 + sm_cmd[s*CW + 81 +: 24] % 97 + ($random(seed) & 15);
                if (sm_cmd[s*CW + 1 +: 13] !== rw[s*69 + 56 +: 13] || sm_cmd[s*CW + 49 +: 32] !== rw[s*69 + 24 +: 32] ||
                    sm_cmd[s*CW + 81 +: 24] !== rw[s*69 +: 24] || sm_cmd[s*CW + 14 +: 16] !== 16'd8 ||
                    sm_cmd[s*CW + 30 +: 8] !== rw[NSM*69 + 2 +: 8] || sm_cmd[s*CW + 39 +: 2] !== rw[NSM*69 +: 2] ||
                    sm_cmd[s*CW + 38] !== 1'b1 || sm_cmd[s*CW + 41 +: 7] !== 7'd0 || rw[s*69 + 56 +: 13] == 0) begin
                    $display("ERR SM %0d command mismatch at record %0d (rows %0d / %0d)", s, base + k,
                             sm_cmd[s*CW + 1 +: 13], rw[s*69 + 56 +: 13]);
                    errors = errors + 1;
                end
            end
            if (busy[s] > 0) begin
                busy[s] = busy[s] - 1;
                if (busy[s] == 0) sm_ret[s*4 + 2] <= ~sm_ret[s*4 + 2];
            end
            if (!rst_n) begin sm_ret[s*4 + 2] <= 1'b0; busy[s] = 0; end      // the SMs reset with the adapter
        end
        // publication done once every started SM finished
        if (pub_got && xdone_q && (|started)) begin
            plat = 1;
            for (s = 0; s < NSM; s = s + 1) if (busy[s] != 0 || (rw[s*69 + 56 +: 13] != 0 && !started[s])) plat = 0;
            if (plat) begin pub_done <= 1; pub_got = 0; pdone_q = 1; end
        end
        if (rst_n && done) begin
            for (s = 0; s < NSM; s = s + 1) if ((rw[s*69 + 56 +: 13] != 0) != started[s] || busy[s] != 0) begin
                $display("ERR record %0d retired: SM %0d started %0d busy %0d", base + k, s, started[s], busy[s]);
                errors = errors + 1;
            end
            if (!pdone_q) begin $display("ERR record %0d retired before its publication", base + k); errors = errors + 1; end
            k = k + 1; started = 0; xdone_q = 0; pdone_q = 0;
        end
    end
    integer fault_n = 0;
    always @(posedge clk) if (rst_n && fault) fault_n = fault_n + 1;
    integer c, j, kind, r0, nr, t, runs = 0, negs = 0;
    initial begin
        for (s = 0; s < NSM; s = s + 1) busy[s] = 0;
        started = 0; x_got = 0; pub_got = 0; xdone_q = 0; pdone_q = 0;
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][95:64]; r0 = casem[c][63:32]; nr = casem[c][31:0];
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; @(posedge clk);
            base = r0; k = 0; issued = 0; x_seen = 0; pub_seen = 0; fault_n = 0; started = 0;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 200000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && fault_n == 0 && t < 200000) begin @(posedge clk); t = t + 1; end
            repeat (40) @(posedge clk);
            if (kind == 0) begin
                if (k != nr || fault_n != 0 || halted) begin
                    $display("ERR run case %0d: retired %0d / %0d, faults %0d", c, k, nr, fault_n); errors = errors + 1; end
                for (s = 0; s < NSM; s = s + 1) if (sm_cmd[s*CW + 105] !== sm_ret[s*4 + 2]) begin
                    $display("ERR case %0d: SM %0d not released after the last retire", c, s); errors = errors + 1; end
                runs = runs + nr;
            end else begin
                if (fault_n != 1 || k != 0 || issued != 0 || !halted) begin   // (a base-remainder refusal comes after the x load issued)
                    $display("ERR negative case %0d: faults %0d retired %0d issued %0d x %0d", c, fault_n, k, issued, x_seen);
                    errors = errors + 1;
                end else negs = negs + 1;
            end
        end
        $display("summary: %0d records run on 32 stub SMs, %0d negatives refused, %0d legacy identity cycles", runs, negs, lock_n);
        if (errors == 0) $display("HGI_SM PASS"); else $display("HGI_SM FAIL errors=%0d", errors);
        $finish;
    end
endmodule
