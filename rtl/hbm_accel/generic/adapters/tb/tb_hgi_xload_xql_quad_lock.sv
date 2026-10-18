`timescale 1ns/1ps
// RTL-BUILD-HBM / RBH-XQL 2026-10-18 (d4g plan (b) item 9): x-load per QUADRANT (R1: a quadrant service serves only
// its own 4 SMs and reads only its own 8 VM banks).
//   reference (today, GEN0 / d4f): the stack-level xl_<S>_ctl = ot_hgi_sm_xload_static_xql NP 4 (ctlx + 2 aq13 + 4 SM-pair
//     clusters; pairs 2/3 feed sm_<S>4..7 = the E quadrant), one per image below (ref_W on the W-quadrant image,
//     ref_E on the E-quadrant image), F20 targets 100 / 101.
//   unit (d4g): one quadrant x-load per quadrant = the SAME masters (ctlx unchanged, aq13 x2, pair clusters) with NP 2:
//     quad_W (SW: tgt 100, banks vmb_SW0..7, pairs 0/1 = sm_SW0..3) and quad_E (SE: tgt 101, banks vmb_SE0..7,
//     pairs 0/1 = sm_SW4..7).
// Lock: every edge, quad_W rq == ref_W rq, quad_E rq == ref_E rq; quad_W pair p stream == ref_W pair p, quad_E pair p
// stream == ref_E pair 2 + p (xw_en/last/x_done every edge, addr/grp/data on every beat); configured/fault/active equal.
// VM images (declared boundary, fixed-latency static read group r2 = sector S on lane S[2:0], response RD_LAT edges
// later; one model per unit, each checks its own lanes): each quadrant's 8 banks are filled by its own 4 SMs with the
// RTL1 writer map (HBM-B-RTL1 vm_quadrant_map.json: SM k half 0 -> bank 4 LB + k, half 1 -> bank (4 LB + k + 4) % 8,
// LB 0 for SW, 1 for SE); the bench checks the map covers each bank exactly once and that the two quadrants' data
// differ, so a cross-quadrant read is visible.
// Commands: per round one F20 command per target (different K / P / base / stride / xb / at), one global launch.
// Mutants (-DQMUT=n, must FAIL): 1 quad_E pair 1 write dropped (xql XQL_MUT 1, RTL); 2 quad_E ctl rotation select + 1
// (ctl MUT 1, RTL); 3 quad_E issuer fires one edge late (ctlw MUT 6, RTL); 4 quad_E bound to the SW banks (die binding,
// cross-quadrant read); 5 quad_E tgt strap 100 (die binding: SE runs the SW command).
// -DCTL_OLD_REF (ELEM-GAPS/HBMN1 10-18): ref_w / ref_e use the CLOSED q1-7af6f4406 ctlx function (xql CTL_OLD 1), so
// the lock also proves today's native ctlx (l_d_o pin copy, pin reset relay) against the closed control.
`ifdef CTL_OLD_REF
`define CTL_OLD_ 1
`else
`define CTL_OLD_ 0
`endif
`ifndef QMUT
`define QMUT 0
`endif
module tb_xql_vm_img #(
    parameter integer RD_LAT = 6,
    parameter integer LB     = 0     // quadrant bank base of the RTL1 writer map (0 SW, 1 SE)
) (
    input  wire               clk,
    input  wire [8*17-1:0]    rq,
    output wire [8*257-1:0]   rr,
    output integer            lanefault
);
    reg [31:0] mem [0:32767];
    // SM writers (RTL1 map): sector s = {row, bank}; SM k half h owns bank (4 LB + k + 4 h) % 8 of every row
    function automatic [31:0] val(input integer k, input integer h, input integer row, input integer w);
        reg [31:0] r;
        begin
            r = 32'h9E3779B9 * (LB * 8191 + k * 131 + h * 17 + 1) ^ (row * 32'h85EBCA6B) ^ (w * 32'hC2B2AE35);
            r = r ^ (r >> 15); r = r * 32'h2C1B3C6D; r = r ^ (r >> 12);
            r[30:23] = 8'd100 + 8'(r[7:0] % 50);           // finite, quantiser-friendly exponents
            if (r[13:8] == 6'd0) r = 32'h0;                  // some zero words
            val = r;
        end
    endfunction
    integer cov [0:7];
    initial begin
        for (integer b = 0; b < 8; b = b + 1) cov[b] = 0;
        for (integer k = 0; k < 4; k = k + 1) for (integer h = 0; h < 2; h = h + 1) begin
            integer bk; bk = (4 * LB + k + 4 * h) % 8; cov[bk] = cov[bk] + 1;
            for (integer row = 0; row < 4096; row = row + 1) for (integer w = 0; w < 8; w = w + 1)
                mem[(row * 8 + bk) * 8 + w] = val(k, h, row, w);
        end
        for (integer b = 0; b < 8; b = b + 1) if (cov[b] != 1) begin
            $display("ERR writer map LB %0d: bank %0d written by %0d (SM, half) pairs", LB, b, cov[b]); lanefault = lanefault + 1; end
    end
    reg [8*257-1:0] pipe [0:RD_LAT-1];
    initial lanefault = 0;
    always @(posedge clk) begin : vm
        reg [8*257-1:0] nw; reg [14:0] s;
        nw = '0;
        for (integer b = 0; b < 8; b = b + 1) if (rq[b*17 + 16]) begin
            s = rq[b*17 +: 15];
            if (s[2:0] != 3'(b) || rq[b*17 + 15]) lanefault = lanefault + 1;
            nw[b*257 + 256] = 1'b1;
            for (integer w = 0; w < 8; w = w + 1) nw[b*257 + 32*w +: 32] = mem[{s[11:0], 3'(w)}];
        end
        pipe[0] <= nw;
        for (integer d = 1; d < RD_LAT; d = d + 1) pipe[d] <= pipe[d-1];
    end
    assign rr = pipe[RD_LAT-1];
endmodule

module tb_xload_xql_quad_lock;
    localparam integer RD_LAT = 6, T = 2, LEAD = 8, QM = `QMUT;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; integer seed = 5, errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 5; $display("SEED=%0d QMUT=%0d", seed, QM); end
    // ---- host ingress (AXI-lite F20..F30), targets 100 (SW x-load) and 101 (SE x-load)
    reg awv = 0, wv = 0; reg [11:0] awa = 0; reg [31:0] wd = 0;
    wire awr, wr, bv; wire [1:0] bresp;
    wire cfg_v, desc_v, launch_v, ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    wire act_any;
    ot_hbm_host_static_ingress #(.TARGET_MASK((256'd1 << 100) | (256'd1 << 101))) ing (
        .clk(clk), .rst_n(rst_n), .s_awvalid(awv), .s_awready(awr), .s_awaddr(awa), .s_wvalid(wv), .s_wready(wr),
        .s_wdata(wd), .s_wstrb(4'hf), .s_bvalid(bv), .s_bready(1'b1), .s_bresp(bresp), .s_arvalid(1'b0), .s_arready(),
        .s_araddr(12'd0), .s_rvalid(), .s_rready(1'b1), .s_rdata(), .block_ready(1'b1), .program_active(act_any),
        .program_fault(1'b0), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .fault(ing_fault));
    // ---- four units: ref_W / ref_E (today, NP 4) and quad_W / quad_E (d4g, NP 2)
    wire [8*17-1:0] rq_rw, rq_re, rq_qw, rq_qe; wire [8*257-1:0] rr_rw, rr_re, rr_qw, rr_qe;
    integer lf_rw, lf_re, lf_qw, lf_qe;
    wire [3:0] cf, ft, ac;
    wire [3:0] d_rw, e_rw, l_rw, d_re, e_re, l_re; wire [1:0] d_qw, e_qw, l_qw, d_qe, e_qe, l_qe;
    wire [27:0] a_rw, g_rw, a_re, g_re; wire [13:0] a_qw, g_qw, a_qe, g_qe;
    wire [4*2048-1:0] x_rw, x_re; wire [2*2048-1:0] x_qw, x_qe;
`define XQL_PORTS(NP_, TGT_, RQ, RR, CF, FT, AC, D, E, L, A, G, X) \
        .clk(clk), .clk_cal(clk), .clk_qlo(clk), .clk_qhi(clk), .clk_bf({NP_*4{clk}}), .clk_bd({NP_{clk}}), .clk_eg({NP_{clk}}), \
        .rst_n(rst_n), .tgt(TGT_), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), \
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), \
        .configured(CF), .fault(FT), .active(AC), .x_done(D), .xw_en(E), .xw_last(L), .xw_addr(A), .xw_grp(G), \
        .xw_data(X), .rq(RQ), .rr(RR)
    ot_hgi_sm_xload_static_xql #(.RD_LAT(RD_LAT), .MUT(0), .NP(4), .T(T), .XQL_MUT(0), .CTL_OLD(`CTL_OLD_)) ref_w (
        `XQL_PORTS(4, 8'd100, rq_rw, rr_rw, cf[0], ft[0], ac[0], d_rw, e_rw, l_rw, a_rw, g_rw, x_rw));
    ot_hgi_sm_xload_static_xql #(.RD_LAT(RD_LAT), .MUT(0), .NP(4), .T(T), .XQL_MUT(0), .CTL_OLD(`CTL_OLD_)) ref_e (
        `XQL_PORTS(4, 8'd101, rq_re, rr_re, cf[1], ft[1], ac[1], d_re, e_re, l_re, a_re, g_re, x_re));
    ot_hgi_sm_xload_static_xql #(.RD_LAT(RD_LAT), .MUT(0), .NP(2), .T(T), .XQL_MUT(0)) quad_w (
        `XQL_PORTS(2, 8'd100, rq_qw, rr_qw, cf[2], ft[2], ac[2], d_qw, e_qw, l_qw, a_qw, g_qw, x_qw));
    ot_hgi_sm_xload_static_xql #(.RD_LAT(RD_LAT), .MUT((QM == 2) ? 1 : (QM == 3) ? 6 : 0), .NP(2), .T(T),
                                 .XQL_MUT((QM == 1) ? 1 : 0)) quad_e (
        `XQL_PORTS(2, ((QM == 5) ? 8'd100 : 8'd101), rq_qe, rr_qe, cf[3], ft[3], ac[3], d_qe, e_qe, l_qe, a_qe, g_qe, x_qe));
    assign act_any = |ac;
    tb_xql_vm_img #(.RD_LAT(RD_LAT), .LB(0)) vm_rw (.clk(clk), .rq(rq_rw), .rr(rr_rw), .lanefault(lf_rw));
    tb_xql_vm_img #(.RD_LAT(RD_LAT), .LB(1)) vm_re (.clk(clk), .rq(rq_re), .rr(rr_re), .lanefault(lf_re));
    tb_xql_vm_img #(.RD_LAT(RD_LAT), .LB(0)) vm_qw (.clk(clk), .rq(rq_qw), .rr(rr_qw), .lanefault(lf_qw));
    tb_xql_vm_img #(.RD_LAT(RD_LAT), .LB((QM == 4) ? 0 : 1)) vm_qe (.clk(clk), .rq(rq_qe), .rr(rr_qe), .lanefault(lf_qe));
    // ---- lockstep compare
    integer ndiff = 0, ncmp = 0, nbeat_w = 0, nbeat_e = 0, nwe_diff = 0;
    integer ndone_w = 0, ndone_e = 0;
    always @(posedge clk) if (rst_n && cyc > 20) begin : cmp
        reg bad; integer rp;
        bad = 1'b0;
        if (rq_qw !== rq_rw || rq_qe !== rq_re) bad = 1'b1;
        if (cf[2] !== cf[0] || ft[2] !== ft[0] || ac[2] !== ac[0]) bad = 1'b1;
        if (cf[3] !== cf[1] || ft[3] !== ft[1] || ac[3] !== ac[1]) bad = 1'b1;
        for (integer p = 0; p < 2; p = p + 1) begin
            if (d_qw[p] !== d_rw[p] || e_qw[p] !== e_rw[p] || l_qw[p] !== l_rw[p]) bad = 1'b1;
            if (e_rw[p] && (a_qw[p*7 +: 7] !== a_rw[p*7 +: 7] || g_qw[p*7 +: 7] !== g_rw[p*7 +: 7] ||
                            x_qw[p*2048 +: 2048] !== x_rw[p*2048 +: 2048])) bad = 1'b1;
            rp = 2 + p;
            if (d_qe[p] !== d_re[rp] || e_qe[p] !== e_re[rp] || l_qe[p] !== l_re[rp]) bad = 1'b1;
            if (e_re[rp] && (a_qe[p*7 +: 7] !== a_re[rp*7 +: 7] || g_qe[p*7 +: 7] !== g_re[rp*7 +: 7] ||
                             x_qe[p*2048 +: 2048] !== x_re[rp*2048 +: 2048])) bad = 1'b1;
            if (e_qw[p]) nbeat_w = nbeat_w + 1;
            if (e_qe[p]) nbeat_e = nbeat_e + 1;
        end
        // the two quadrants' reference beats on the same edge differ somewhere (distinct images / commands)
        if (e_rw[0] && e_re[2] && x_rw[2047:0] !== x_re[2*2048 +: 2048]) nwe_diff = nwe_diff + 1;
        if (d_rw[0]) ndone_w = ndone_w + 1;
        if (d_re[2]) ndone_e = ndone_e + 1;
        ncmp = ncmp + 1;
        if (bad) begin
            if (ndiff < 5) $display("ERR quadrant x-load differs from today's xql at cycle %0d (W en %b/%b, E en %b/%b)",
                                    cyc, e_qw, e_rw[1:0], e_qe, e_re[3:2]);
            ndiff = ndiff + 1;
        end
    end
    // ---- host writes
    task automatic axw(input [11:0] a, input [31:0] d);
        reg ad, dd;
        begin
            ad = 0; dd = 0; @(negedge clk); awv = 1; awa = a; wv = 1; wd = d;
            while (!(ad && dd)) begin
                begin : HS reg ha, hw; ha = awv && awr; hw = wv && wr;
                @(posedge clk); #0.01; if (ha) begin ad = 1; awv = 0; end if (hw) begin dd = 1; wv = 0; end end
                @(negedge clk);
            end
            begin : BW integer w; w = 0;
                while (!bv) begin @(posedge clk); w = w + 1;
                    if (w > 2000) begin $display("XQL_QUAD_LOCK FAIL: AXI write %h no bvalid", a); $fflush; $finish; end end
            end
            if (bresp != 0) begin $display("ERR bresp %0d at %h data %h", bresp, a, d); errors = errors + 1; end
            @(posedge clk);
        end
    endtask
    task automatic f20_install(input [7:0] tg, input [107:0] pl, input [31:0] at);
        reg [255:0] row;
        begin
            row = {116'd0, pl, at};
            axw(12'hf20, {12'd0, 12'h800, tg});
            for (integer p = 0; p < 8; p = p + 1) axw(12'hf24, row[p*32 +: 32]);
            axw(12'hf20, {12'd0, 12'd0, tg}); axw(12'hf28, {7'd0, 13'd1, 12'd0}); axw(12'hf2c, 32'd1);
        end
    endtask
    // ---- random command (as tb_hgi_xload_static_lock)
    task automatic mk_cmd(input integer c, output [107:0] pl);
        reg [20:0] n; reg [3:0] p; reg [39:0] base; reg [31:0] st; reg [6:0] xb; reg [1:0] fmt;
        begin
            p = 1 + ($unsigned($random(seed)) % 8); n = 1 + ($unsigned($random(seed)) % 1500);
            base = 8 * ($unsigned($random(seed)) % 20); st = 8 * (((n + 7) / 8) + ($unsigned($random(seed)) % 3));
            xb = $unsigned($random(seed)) % 128;
            fmt = (c < 10) ? 2'd0 : (c % 2 == 0) ? 2'd1 : 2'd2;
            if (fmt != 0) begin n = 32 * (1 + ($unsigned($random(seed)) % 180)); st = 8 * (((n + 7) / 8) + ($unsigned($random(seed)) % 3)); end
            if (c == 0) begin p = 2; n = 9000; st = 8 * 1130; end   // > 16 groups: x-store word wrap
            pl = {xb, fmt, 2'd1, st, p, n, base};
        end
    endtask
    integer c, t, w0, e0; reg [107:0] plw, ple;
    initial begin
        repeat (3) @(posedge clk); rst_n = 1; repeat (12) @(posedge clk);
        for (c = 0; c < 20; c = c + 1) begin
            mk_cmd(c, plw); mk_cmd(c, ple);
            f20_install(8'd100, plw, 32'(3 * (c % 7)));
            f20_install(8'd101, ple, 32'(5 * (c % 5)));
            repeat (10) @(posedge clk);
            if (cf !== 4'hf || |ft || ing_fault) begin $display("ERR F20 install: configured %b fault %b ingress %b", cf, ft, ing_fault); errors = errors + 1; end
            w0 = ndone_w; e0 = ndone_e;
            axw(12'hf30, 32'd1);
            t = 0; while ((ndone_w == w0 || ndone_e == e0 || act_any) && t < 400000) begin @(posedge clk); t = t + 1; end
            repeat (8) @(posedge clk);
            if (t >= 400000) begin $display("ERR round %0d did not finish (done W %0d E %0d active %b)", c, ndone_w - w0, ndone_e - e0, ac); errors = errors + 1; end
            $display("round %0d W {fmt %0d P %0d K %0d} E {fmt %0d P %0d K %0d}: %0d edges", c, plw[100:99], plw[64:61], plw[60:40],
                     ple[100:99], ple[64:61], ple[60:40], t);
            $fflush;
        end
        $display("quadrant vs today's xql (pairs W0,1 = ref 0,1; E0,1 = ref 2,3): %0d cycles compared, %0d W beats, %0d E beats, %0d differ; W/E distinct beats %0d",
                 ncmp, nbeat_w, nbeat_e, ndiff, nwe_diff);
        if (ndiff || nbeat_w == 0 || nbeat_e == 0 || nwe_diff == 0) errors = errors + 1;
        if (|ft || ing_fault || lf_rw || lf_re || lf_qw || lf_qe) begin
            $display("ERR fault %b ingress %b lanefault %0d/%0d/%0d/%0d", ft, ing_fault, lf_rw, lf_re, lf_qw, lf_qe); errors = errors + 1; end
        if (errors == 0) $display("XQL_QUAD_LOCK PASS"); else $display("XQL_QUAD_LOCK FAIL %0d", errors);
        $finish;
    end
endmodule
