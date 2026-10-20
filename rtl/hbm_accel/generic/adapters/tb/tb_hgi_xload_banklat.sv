`timescale 1ns/1ps
// HBM-BANKLAT-XL 10-19: x-load control ctlx (via ot_hgi_sm_xload_static_xql NP 2, the d4g quadrant x-load) on the d4g
// FACES banks (pin flop on every input: read answer n+7 at the bank ports) behind UNEQUAL die lanes, with the per-bank
// RD_LAT vector (ot_hgi_sm_xload_cl2_ctl RD_LAT header).
//   ref : xql #(RD_LAT 6) on the reference bank model (ot_vms_bank_static n+6, zero die stages) -- today's function.
//   dut : xql #(RD_LAT V) on 8 lanes: rq lane LQ_b registers (+ die pad PAD_b), faces bank 7 registers, rr lane LR_b.
// Lock, every edge after reset: dut x_done / xw_en / xw_last == ref's exactly DLT = RLM - 6 edges earlier, and on every
// beat xw_addr / xw_grp / 2048-b xw_data equal; dut rq lane b == ref rq lane b exactly D_b + DLT - (RLM - 6) = D_b
// edges later (D_b = RLM - V_b, the ctl's per-bank issue stagger); configured / fault equal, no lane fault.
// Both units receive the same F20 commands (one host ingress, both tgt 100), 20 random rounds (fmt 0 / 1 / 2).
// -DCFG n (PASS cases): 0 GEN2c NE lanes, V = NE round trips; 1 GEN2c NW lanes, V = NW round trips; 2 BUDGET vector
//   on NE lanes + die rq pads; 3 BUDGET vector on NW lanes + die rq pads; 4 scalar 6 on the reference model (DLT 0).
// -DBMUT n (must FAIL, on CFG 0 lanes): 1 dut RD_LAT 6 (old value); 2 dut scalar RD_LAT 41 (= max, no stagger: lanes
//   unequal); 3 dut ctl MUT 7 (RTL: stagger ignored); 4 vector element 3 off by one (24 for 25).
`ifndef CFG
`define CFG 0
`endif
`ifndef BMUT
`define BMUT 0
`endif
module tb_bl_vm #(
    parameter [63:0] LQ = 64'd0,      // rq lane registers per bank (packed 8 b per bank, element b at [8b +: 8])
    parameter [63:0] LR = 64'd0,      // rr lane registers per bank
    parameter integer BK = 6          // bank registers (6 = ot_vms_bank_static, 7 = faces pin flop + 6)
) (
    input  wire               clk,
    input  wire [8*17-1:0]    rq,
    output wire [8*257-1:0]   rr,
    output wire integer       lanefault
);
    reg [31:0] mem [0:32767];
    function automatic [31:0] val(input integer k, input integer h, input integer row, input integer w);
        reg [31:0] r;
        begin
            r = 32'h9E3779B9 * (k * 131 + h * 17 + 1) ^ (row * 32'h85EBCA6B) ^ (w * 32'hC2B2AE35);
            r = r ^ (r >> 15); r = r * 32'h2C1B3C6D; r = r ^ (r >> 12);
            r[30:23] = 8'd100 + 8'(r[7:0] % 50);
            if (r[13:8] == 6'd0) r = 32'h0;
            val = r;
        end
    endfunction
    initial begin
        for (integer k = 0; k < 4; k = k + 1) for (integer h = 0; h < 2; h = h + 1)
            for (integer row = 0; row < 4096; row = row + 1) for (integer w = 0; w < 8; w = w + 1)
                mem[(row * 8 + (k + 4 * h)) * 8 + w] = val(k, h, row, w);
    end
    reg [7:0] lfv = 8'd0;
    assign lanefault = (lfv != 8'd0) ? 1 : 0;
    function automatic [256:0] look(input [16:0] q);
        reg [14:0] s;
        begin
            look = '0; s = q[14:0];
            if (q[16]) begin
                look[256] = 1'b1;
                for (integer w = 0; w < 8; w = w + 1) look[32*w +: 32] = mem[{s[11:0], 3'(w)}];
            end
        end
    endfunction
    genvar gb;
    generate for (gb = 0; gb < 8; gb = gb + 1) begin : g_b
        localparam integer NQ = (LQ >> (8 * gb)) & 64'hFF, NRR = (LR >> (8 * gb)) & 64'hFF;
        // rq lane: NQ registers
        wire [16:0] at;
        if (NQ == 0) begin : g_q0
            assign at = rq[gb*17 +: 17];
        end else begin : g_q
            reg [16:0] ql [1:NQ];
            always @(posedge clk) begin ql[1] <= rq[gb*17 +: 17]; for (integer d = 2; d <= NQ; d = d + 1) ql[d] <= ql[d-1]; end
            assign at = ql[NQ];
        end
        // bank: lookup at its port, BK registers to its rr port
        reg [256:0] bp [1:BK];
        always @(posedge clk) begin
            if (at[16] && (at[2:0] != 3'(gb) || at[15])) lfv[gb] <= 1'b1;
            bp[1] <= look(at);
            for (integer d = 2; d <= BK; d = d + 1) bp[d] <= bp[d-1];
        end
        // rr lane: NRR registers
        if (NRR == 0) begin : g_r0
            assign rr[gb*257 +: 257] = bp[BK];
        end else begin : g_r
            reg [256:0] rl [1:NRR];
            always @(posedge clk) begin rl[1] <= bp[BK]; for (integer d = 2; d <= NRR; d = d + 1) rl[d] <= rl[d-1]; end
            assign rr[gb*257 +: 257] = rl[NRR];
        end
    end endgenerate
endmodule

module tb_xload_banklat;
    localparam integer T = 2, CFG = `CFG, BM = `BMUT;
    function automatic [63:0] pk(input integer a0, a1, a2, a3, a4, a5, a6, a7);
        pk = {8'(a7), 8'(a6), 8'(a5), 8'(a4), 8'(a3), 8'(a2), 8'(a1), 8'(a0)};
    endfunction
    function automatic integer el(input [63:0] v, input integer b);
        reg [63:0] x; begin x = v >> (8 * b); el = x[7:0]; end
    endfunction
    // GEN2c contract_pre lanes (results/arch/hbm_banklat_1019/gen2c_contract_pre_bank_latency.json), banks 0..7
    localparam [63:0] NE_LQ = pk(2, 3, 8, 9, 10, 11, 16, 17),  NE_LR = pk(1, 3, 8, 9, 9, 11, 16, 17);
    localparam [63:0] NW_LQ = pk(13, 14, 7, 8, 21, 22, 15, 16), NW_LR = pk(13, 14, 6, 7, 21, 22, 14, 15);
    localparam [63:0] NE_RT = pk(10, 13, 23, 25, 26, 29, 39, 41), NW_RT = pk(33, 35, 20, 22, 49, 51, 36, 38);
    // BUDGET (one hardened view for all quadrants): element-wise max over the 4 quadrants + 4 edges GEN2d headroom
    localparam [63:0] BUD = pk(37, 39, 27, 29, 53, 55, 43, 45);
    function automatic [63:0] padq(input [63:0] lq, input [63:0] rt, input [63:0] bud);
        padq = 0;
        for (integer b = 0; b < 8; b = b + 1) padq = padq | (64'(el(lq, b) + el(bud, b) - el(rt, b)) << (8 * b));
    endfunction
    localparam [63:0] LQ = (CFG == 1 || CFG == 3) ? ((CFG == 3) ? padq(NW_LQ, NW_RT, BUD) : NW_LQ) :
                           (CFG == 2) ? padq(NE_LQ, NE_RT, BUD) : (CFG == 4) ? 64'd0 : NE_LQ;
    localparam [63:0] LR = (CFG == 1 || CFG == 3) ? NW_LR : (CFG == 4) ? 64'd0 : NE_LR;
    localparam integer BK = (CFG == 4) ? 6 : 7;
    localparam [63:0] V0 = (CFG == 1) ? NW_RT : (CFG == 2 || CFG == 3) ? BUD : (CFG == 4) ? 64'd6 : NE_RT;
    localparam [63:0] V = (BM == 1) ? 64'd6 : (BM == 2) ? 64'd41 : (BM == 4) ? ((V0 & ~(64'hFF << 24)) | (64'd24 << 24)) : V0;
    function automatic integer vmax(input [63:0] v);
        vmax = 0;
        if (v >> 8 == 0) vmax = v[7:0];
        else for (integer b = 0; b < 8; b = b + 1) if (el(v, b) > vmax) vmax = el(v, b);
    endfunction
    localparam integer RLM0 = vmax(V0), DLT = RLM0 - 6;     // expected shift (the correct vector's RLM)
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; integer seed = 7, errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 7;
        $display("SEED=%0d CFG=%0d BMUT=%0d V=%h RLM=%0d DLT=%0d LQ=%h LR=%h BK=%0d", seed, CFG, BM, V, vmax(V), DLT, LQ, LR, BK);
    end
    // ---- host ingress (AXI-lite F20..F30), target 100
    reg awv = 0, wv = 0; reg [11:0] awa = 0; reg [31:0] wd = 0;
    wire awr, wr, bv; wire [1:0] bresp;
    wire cfg_v, desc_v, launch_v, ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    wire act_any;
    ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1 << 100)) ing (
        .clk(clk), .rst_n(rst_n), .s_awvalid(awv), .s_awready(awr), .s_awaddr(awa), .s_wvalid(wv), .s_wready(wr),
        .s_wdata(wd), .s_wstrb(4'hf), .s_bvalid(bv), .s_bready(1'b1), .s_bresp(bresp), .s_arvalid(1'b0), .s_arready(),
        .s_araddr(12'd0), .s_rvalid(), .s_rready(1'b1), .s_rdata(), .block_ready(1'b1), .program_active(act_any),
        .program_fault(1'b0), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .fault(ing_fault));
    wire [8*17-1:0] rq_r, rq_d; wire [8*257-1:0] rr_r, rr_d;
    integer lf_r, lf_d;
    wire [1:0] cf, ft, ac;
    wire [1:0] d_r, e_r, l_r, d_d, e_d, l_d; wire [13:0] a_r, g_r, a_d, g_d; wire [2*2048-1:0] x_r, x_d;
`define BL_PORTS(RQ, RR, CF, FT, AC, D, E, L, A, G, X) \
        .clk(clk), .clk_cal(clk), .clk_qlo(clk), .clk_qhi(clk), .clk_bf({8{clk}}), .clk_bd({2{clk}}), .clk_eg({2{clk}}), \
        .rst_n(rst_n), .tgt(8'd100), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), \
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), \
        .configured(CF), .fault(FT), .active(AC), .x_done(D), .xw_en(E), .xw_last(L), .xw_addr(A), .xw_grp(G), \
        .xw_data(X), .rq(RQ), .rr(RR)
    ot_hgi_sm_xload_static_xql #(.RD_LAT(64'd6), .MUT(0), .NP(2), .T(T), .XQL_MUT(0)) u_ref (
        `BL_PORTS(rq_r, rr_r, cf[0], ft[0], ac[0], d_r, e_r, l_r, a_r, g_r, x_r));
    ot_hgi_sm_xload_static_xql #(.RD_LAT(V), .MUT((BM == 3) ? 7 : 0), .NP(2), .T(T), .XQL_MUT(0)) u_dut (
        `BL_PORTS(rq_d, rr_d, cf[1], ft[1], ac[1], d_d, e_d, l_d, a_d, g_d, x_d));
    assign act_any = |ac;
    tb_bl_vm #(.LQ(64'd0), .LR(64'd0), .BK(6)) vm_r (.clk(clk), .rq(rq_r), .rr(rr_r), .lanefault(lf_r));
    tb_bl_vm #(.LQ(LQ), .LR(LR), .BK(BK)) vm_d (.clk(clk), .rq(rq_d), .rr(rr_d), .lanefault(lf_d));
    // ---- reference history (DLT + 64 edges)
    localparam integer H = DLT + 64;
    reg [1:0] hd [0:H], he [0:H], hl [0:H]; reg [13:0] ha [0:H], hg [0:H]; reg [2*2048-1:0] hx [0:H];
    reg [8*17-1:0] hq [0:H];
    always @(posedge clk) begin
        hd[0] <= d_r; he[0] <= e_r; hl[0] <= l_r; ha[0] <= a_r; hg[0] <= g_r; hx[0] <= x_r; hq[0] <= rq_r;
        for (integer i = 1; i <= H; i = i + 1) begin
            hd[i] <= hd[i-1]; he[i] <= he[i-1]; hl[i] <= hl[i-1]; ha[i] <= ha[i-1]; hg[i] <= hg[i-1]; hx[i] <= hx[i-1]; hq[i] <= hq[i-1];
        end
    end
    // dut at edge n vs ref at edge n - DLT: index DLT - 1 of the history holds ref's value DLT edges ago (DLT 0: live)
    integer ndiff = 0, nqdiff = 0, ncmp = 0, nbeat = 0, ndone_r = 0, ndone_d = 0, nrq = 0;
    always @(posedge clk) if (rst_n && cyc > H + 20) begin : cmp
        reg bad; reg [1:0] rd, re, rl; reg [13:0] ra, rg; reg [2*2048-1:0] rx; integer db;
        reg [16:0] rqb;
        if (DLT == 0) begin rd = d_r; re = e_r; rl = l_r; ra = a_r; rg = g_r; rx = x_r; end
        else begin rd = hd[DLT-1]; re = he[DLT-1]; rl = hl[DLT-1]; ra = ha[DLT-1]; rg = hg[DLT-1]; rx = hx[DLT-1]; end
        bad = 1'b0;
        for (integer p = 0; p < 2; p = p + 1) begin
            if (d_d[p] !== rd[p] || e_d[p] !== re[p] || l_d[p] !== rl[p]) bad = 1'b1;
            if (re[p] && (a_d[p*7 +: 7] !== ra[p*7 +: 7] || g_d[p*7 +: 7] !== rg[p*7 +: 7] || x_d[p*2048 +: 2048] !== rx[p*2048 +: 2048])) bad = 1'b1;
            if (e_d[p]) nbeat = nbeat + 1;
        end
        if (cf[1] !== cf[0] || ft[1] !== ft[0]) bad = 1'b1;
        // rq lane b of the dut == ref lane b D_b edges earlier (the correct vector's stagger)
        for (integer b = 0; b < 8; b = b + 1) begin
            db = RLM0 - ((V0 >> 8 == 0) ? V0[7:0] : el(V0, b));
            rqb = (db == 0) ? rq_r[b*17 +: 17] : hq[db-1][b*17 +: 17];
            if (rq_d[b*17 +: 17] !== rqb) nqdiff = nqdiff + 1;
            if (rq_d[b*17 + 16]) nrq = nrq + 1;
        end
        if (rd[0]) ndone_r = ndone_r + 1;
        if (d_d[0]) ndone_d = ndone_d + 1;
        ncmp = ncmp + 1;
        if (bad) begin
            if (ndiff < 5) $display("ERR dut differs from ref (shift %0d) at cycle %0d: en %b/%b done %b/%b fault %b/%b", DLT, cyc, e_d, re, d_d, rd, ft[1], ft[0]);
            ndiff = ndiff + 1;
        end
    end
    // ---- host writes (as tb_hgi_xload_xql_quad_lock)
    task automatic axw(input [11:0] a, input [31:0] d);
        reg ad, dd;
        begin
            ad = 0; dd = 0; @(negedge clk); awv = 1; awa = a; wv = 1; wd = d;
            while (!(ad && dd)) begin
                begin : HS reg ha2, hw; ha2 = awv && awr; hw = wv && wr;
                @(posedge clk); #0.01; if (ha2) begin ad = 1; awv = 0; end if (hw) begin dd = 1; wv = 0; end end
                @(negedge clk);
            end
            begin : BW integer w; w = 0;
                while (!bv) begin @(posedge clk); w = w + 1;
                    if (w > 2000) begin $display("XLOAD_BANKLAT FAIL: AXI write %h no bvalid", a); $fflush; $finish; end end
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
    task automatic mk_cmd(input integer c, output [107:0] pl);
        reg [20:0] n; reg [3:0] p; reg [39:0] base; reg [31:0] st; reg [6:0] xb; reg [1:0] fmt;
        begin
            p = 1 + ($unsigned($random(seed)) % 8); n = 1 + ($unsigned($random(seed)) % 1500);
            base = 8 * ($unsigned($random(seed)) % 20); st = 8 * (((n + 7) / 8) + ($unsigned($random(seed)) % 3));
            xb = $unsigned($random(seed)) % 128;
            fmt = (c < 8) ? 2'd0 : (c % 2 == 0) ? 2'd1 : 2'd2;
            if (fmt != 0) begin n = 32 * (1 + ($unsigned($random(seed)) % 180)); st = 8 * (((n + 7) / 8) + ($unsigned($random(seed)) % 3)); end
            if (c == 0) begin p = 2; n = 9000; st = 8 * 1130; end
            pl = {xb, fmt, 2'd1, st, p, n, base};
        end
    endtask
    integer c, t, r0, d0; reg [107:0] pl;
    initial begin
        repeat (3) @(posedge clk); rst_n = 1; repeat (H + 24) @(posedge clk);
        for (c = 0; c < 16; c = c + 1) begin
            mk_cmd(c, pl);
            f20_install(8'd100, pl, 32'(3 * (c % 7)));
            repeat (10) @(posedge clk);
            if (cf !== 2'b11 || |ft || ing_fault) begin $display("ERR F20 install: configured %b fault %b ingress %b", cf, ft, ing_fault); errors = errors + 1; end
            r0 = ndone_r; d0 = ndone_d;
            axw(12'hf30, 32'd1);
            t = 0; while ((ndone_r == r0 || ndone_d == d0 || act_any) && t < 400000) begin @(posedge clk); t = t + 1; end
            repeat (DLT + 8) @(posedge clk);
            if (t >= 400000) begin $display("ERR round %0d did not finish (done ref %0d dut %0d active %b)", c, ndone_r - r0, ndone_d - d0, ac); errors = errors + 1; end
            $display("round %0d {fmt %0d P %0d K %0d}: %0d edges", c, pl[100:99], pl[64:61], pl[60:40], t);
            $fflush;
        end
        $display("XLOAD_BANKLAT dut vs ref (+%0d edges): %0d cycles compared, %0d dut beats, %0d differ; rq lanes off-stagger %0d (dut rq %0d); done ref %0d dut %0d; fault ref %b dut %b; lanefault ref %0d dut %0d",
                 DLT, ncmp, nbeat, ndiff, nqdiff, nrq, ndone_r, ndone_d, ft[0], ft[1], lf_r, lf_d);
        if (ndiff || nqdiff || lf_r || lf_d || nbeat == 0 || ndone_d != 16 || ndone_r != 16 || |ft) errors = errors + 1;
        if (errors == 0) $display("XLOAD_BANKLAT PASS CFG=%0d", CFG); else $display("XLOAD_BANKLAT FAIL CFG=%0d BMUT=%0d errors=%0d", CFG, BM, errors);
        $finish;
    end
endmodule
