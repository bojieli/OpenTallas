`timescale 1ns/1ps
// el1013-hbm-hc: tb_hgi_hc_eng for the B2 engine ot_hgi_hc_eng_b2: FOUR local VM slices (ot_hgi_vm_unit RP 8 / W2 8 each;
// bench lane 8 q + b = bank b of slice q), vectors hc_eng_bench.py --b2 (the same golden, operands partitioned by quarter).
// -DRLQV / -DCDV: centre <-> quarter relay flops and chunk-slot credits.  Original header:
// hgi-1010/b-hc (2026-10-10): standalone bench of ot_hgi_hc_eng on the REAL wide VM lanes (ot_hgi_vm_unit RP 32 / W2 32,
// LQ credits).  Vectors tools/hgi_adapters/hc_eng_bench.py (DS d 5,120 HC_POST / HC_PRE_NORM, hdc_golden_v41 chunk8):
// the bench preloads VM through the write lanes, runs one job a case (cycles = job accept -> done), reads every output
// sector (and the guard sectors around it) back through the read lanes.  Prints HGI_HC_ENG PASS / FAIL.
// +GDLY=n: g_rdy rises n cycles after the job (the gain mover's landing; default 0 = gain already in VM).
module tb_hgi_hc_eng_b2;
    `include "hc_sizes.svh"
`ifndef LQV
 `define LQV 32
`endif
`ifndef HMUT
 `define HMUT 0
`endif
`ifndef RLQV
 `define RLQV 6
`endif
`ifndef CDV
 `define CDV 16
`endif
    localparam integer LQ = `LQV;
    reg clk = 0; always #1 clk = ~clk;
    reg [279:0] casem [0:NCASE-1]; reg [275:0] initm [0:NINIT-1]; reg [275:0] expm [0:NEXP-1];
    reg [8*256-1:0] dir;
    integer gdly = 0;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("GDLY=%d", gdly)) gdly = 0;
        $readmemh({dir, "/hc_case.mem"}, casem); $readmemh({dir, "/hc_init.mem"}, initm); $readmemh({dir, "/hc_exp.mem"}, expm);
    end
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0;
    // engine
    reg job_v = 0; reg [148:0] jw = 0; reg g_rdy = 0; wire job_rdy, e_done, e_fault, e_idle;
    wire [32*16-1:0] e_rq; wire [32*280-1:0] e_wq; wire e_rg, e_wg;
    // VM lanes
    wire [31:0] rq_cr, w2_cr, w2_done; wire [32*257-1:0] rr;
    reg own = 0;                                     // 1: the engine drives the lanes; 0: the bench
    reg [32*16-1:0] t_rq = 0; reg [32*280-1:0] t_wq = 0;
    wire [32*16-1:0] rq = own ? e_rq : t_rq; wire [32*280-1:0] w2q = own ? e_wq : t_wq;
    ot_hgi_hc_eng_b2 #(.D(HD), .LQ(LQ), .RLQ(`RLQV), .CD(`CDV), .MUT(`HMUT)) u_e (.clk(clk), .rst_n(rst_n), .job_v(job_v),
        .job_rdy(job_rdy), .job(jw),
        .g_rdy(g_rdy), .done(e_done), .fault(e_fault), .idle(e_idle), .wrq(e_rq), .wrq_cr(own ? rq_cr : 32'd0),
        .wrr(own ? rr : '0), .wwq(e_wq), .wwq_cr(own ? w2_cr : 32'd0), .wwq_done(own ? w2_done : 32'd0),
        .rg_req(e_rg), .rg_gnt(1'b1), .wg_req(e_wg), .wg_gnt(1'b1));
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_vm
        ot_hgi_vm_unit #(.NC(1), .WP(1), .RP(8), .W2(8), .LQ(LQ)) u_vm (.clk(clk), .rst_n(rst_n), .cq(338'd0), .cr(),
            .status(), .wq(280'd0), .wq_done(), .rq(rq[gq*128 +: 128]), .rq_cr(rq_cr[gq*8 +: 8]), .rr(rr[gq*2056 +: 2056]),
            .w2q(w2q[gq*2240 +: 2240]), .w2q_cr(w2_cr[gq*8 +: 8]), .w2q_done(w2_done[gq*8 +: 8]));
    end endgenerate

    // ---- bench lane traffic: per-lane sector queues, LQ credits
    reg [270:0] wq_l [0:31][$]; reg [270:0] rq_l [0:31][$];     // writes {sec, data}; reads {sec, expected}
    integer wcr [0:31], rcr [0:31], wpd [0:31], wout = 0, errors = 0, checked = 0;
    reg [270:0] rexp [0:31][$];
    task automatic lanes_run();                      // drain every queue (writes first, then reads), wait for the landings
        integer b, busy, tw;
        begin
            for (b = 0; b < 32; b = b + 1) begin wcr[b] = LQ; rcr[b] = LQ; wpd[b] = 0; end
            busy = 1; tw = 0;
            while (busy && tw < 200000) begin
                @(negedge clk);
                t_rq = 0; t_wq = 0; busy = 0;
                for (b = 0; b < 32; b = b + 1) begin
                    if (w2_cr[b]) wcr[b] = wcr[b] + 1;
                    if (rq_cr[b]) rcr[b] = rcr[b] + 1;
                    if (w2_done[b]) wpd[b] = wpd[b] - 1;     // a preload write landed (dones trail the credits)
                    if (rr[b*257 + 256]) begin : rsp
                        reg [270:0] e; e = rexp[b].pop_front();
                        if (rr[b*257 +: 256] !== e[255:0]) begin
                            if (errors < 12) $display("ERR sector %0d lane %0d: got %h expected %h", e[270:256], b,
                                                      rr[b*257 +: 256], e[255:0]);
                            errors = errors + 1;
                        end
                        checked = checked + 1;
                    end
                    if (wq_l[b].size() > 0 && wcr[b] > 0) begin : wr
                        reg [270:0] x; x = wq_l[b].pop_front();
                        t_wq[b*280 +: 280] = {1'b1, x[270:256], x[255:0], 8'hFF}; wcr[b] = wcr[b] - 1; wpd[b] = wpd[b] + 1;
                    end else if (wq_l[b].size() == 0 && rq_l[b].size() > 0 && rcr[b] > 0 && wcr[b] == LQ) begin : rd
                        reg [270:0] x; x = rq_l[b].pop_front();
                        t_rq[b*16 +: 16] = {1'b1, x[270:256]}; rcr[b] = rcr[b] - 1; rexp[b].push_back(x);
                    end
                    if (wq_l[b].size() > 0 || rq_l[b].size() > 0 || rexp[b].size() > 0 || wcr[b] != LQ || rcr[b] != LQ || wpd[b] != 0) busy = 1;
                end
                tw = tw + 1;
            end
            @(negedge clk); t_rq = 0; t_wq = 0;
            if (busy) begin $display("ERR bench lane traffic hung"); errors = errors + 1; end
        end
    endtask

    integer c, j, t, i0, ni, e0, ne, t0, tot = 0;
    // the engine retires only after its last write is in the macro: count the VM write dones while it owns the lanes
    integer wdn = 0;
    always @(posedge clk) if (own) for (integer b = 0; b < 32; b = b + 1) if (w2_done[b]) wdn = wdn + 1;
    integer cyc_case [0:15];
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            i0 = casem[c][127:96]; ni = casem[c][95:64]; e0 = casem[c][63:32]; ne = casem[c][31:0];
            own = 0; rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < ni; j = j + 1) wq_l[8 * initm[i0 + j][273:272] + initm[i0 + j][258:256]].push_back({initm[i0 + j][270:256], initm[i0 + j][255:0]});
            lanes_run();
            @(negedge clk); own = 1; wdn = 0; jw = casem[c][276:128]; job_v = 1; t0 = cyc;
            t = 0; while (!job_rdy && t < 1000) begin @(negedge clk); t = t + 1; end
            @(negedge clk); job_v = 0;
            fork
                begin repeat (gdly) @(posedge clk); #0.1 g_rdy = 1; end
            join_none
`ifndef WDOG
 `define WDOG 200000
`endif
            t = 0; while (!e_done && !e_fault && t < `WDOG) begin @(posedge clk); t = t + 1; end
            if (!e_done && !e_fault)
                $display("HANG st %0d ndone %0d nexp %0d fin %0d scl %0d nsc %0d", u_e.u_ctl.st, u_e.u_ctl.ndone, u_e.u_ctl.nexp,
                         u_e.u_ctl.fin_all, u_e.u_ctl.scl, u_e.u_ctl.nsc);
            cyc_case[c] = cyc - t0;
            begin : landed
                integer want; want = (jw[148:147] == 2'd1) ? HD / 2 : HD / 8;     // output sectors (HC_POST 4 x D / 8)
                if (e_done && wdn != want) begin
                    $display("ERR case %0d: retired with %0d of %0d output writes landed", c, wdn, want); errors = errors + 1;
                end
            end
            if (!e_done) begin $display("ERR case %0d: %s after %0d cycles", c, e_fault ? "FAULT" : "HANG", cyc - t0); errors = errors + 1; end
            $display("case %0d: %s d %0d %s%0d cycles", c, jw[148:147] == 2'd1 ? "HC_POST" : "HC_PRE_NORM", HD,
                     (jw[148:147] == 2'd0 && jw[36]) ? "packed gain " : "", cyc - t0); $fflush;
            repeat (2) @(negedge clk); own = 0; g_rdy = 0;
            for (j = 0; j < ne; j = j + 1) rq_l[8 * expm[e0 + j][273:272] + expm[e0 + j][258:256]].push_back({expm[e0 + j][270:256], expm[e0 + j][255:0]});
            lanes_run();
            tot = tot + 1;
        end
        $display("summary: %0d HC B2 engine cases, %0d sectors checked, %0d sector errors, stale chunks %0d", tot, checked, errors, u_e.u_ctl.c_stale);
        if (errors == 0 && tot == NCASE) $display("HGI_HC_ENG_B2 PASS"); else $display("HGI_HC_ENG_B2 FAIL errors=%0d", errors);
        $finish;
    end
endmodule
