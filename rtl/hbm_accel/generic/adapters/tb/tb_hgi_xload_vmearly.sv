`timescale 1ns/1ps
// HBM-VMEARLY-XL 10-19: ISSUE_AHEAD (compiler early issue) of the d4g x-load on the CURRENT hardware.
// Claim: ot_hgi_sm_xload_cl2_ctlx already accepts record i+1's command while the SM still consumes record i's x (x_busy
// covers only the x-load's OWN record: command -> x_done), and the consumer double buffer already exists (the command's
// x_xb slot base is added to every xw beat address; the SM reads x at its op_xb slot base out of its XD = 128 x store).
// So ISSUE_AHEAD = 1 is compiler-side: the x-load of record i is fired at
//     s_i = max(x-load free (s_{i-1} + B_{i-1}), RAW (producer write retired + 1), window start_{i-1} (N = 1),
//               slot free: first xw beat of i after the end of every record whose slot region overlaps i's)
// with x_xb = a static ring over the 128 x-store addresses (record footprint fp = 8 gn BF / 8 gnb BD).  ISSUE_AHEAD = 0
// (today, as priced) fires it when the SM ends record i-1 into one slot (xb 0).
// Bench: three xql (NP 2, T 2) units behind one host ingress (F20 calendars, one launch):
//   u_n0 tgt 100 RD_LAT = budget vector [37,39,27,29,53,55,43,45] on the GEN2c NE lanes + die rq pads + faces bank n+7,
//        ISSUE_AHEAD 0 schedule;  u_n1 tgt 101 same hardware, ISSUE_AHEAD 1 schedule;
//   u_r6 tgt 102 RD_LAT 6 on the reference bank n+6 with zero lanes, ISSUE_AHEAD 0 (= before the bank-latency budgets).
// Phase 1 calibrates every record alone (ctl start -> first beat F, -> x_done X, -> x_busy low B; launch -> start FO).
// Phase 2 runs the DS layer-5 x-load record list (29 records, lead model layer5_records_n1.tsv order and RAW classes;
// p = 1 AR shapes) back to back on all three units from static calendars.  SM model per unit (pair 0): one record at a
// time, start_i = max(end_{i-1} + 1, x_done_i + 1), busy MV edges on its slot; a RAW record's x region is rewritten in that
// unit's VM PW edges after the SM end of the previous record (the producer retire).  Checks: no fault, every x_done and
// SM start exactly at the compiler's prediction, no xw write into the slot of a record that is loaded and not ended,
// every record's slot content at its SM start bit-identical across the three units (ref = u_n0, today's function),
// ISSUE_AHEAD 1 overlaps (an x-load fired before the previous record's SM end) and exposes fewer edges.
// Exposed edges of record i = SM start_i - (SM end_{i-1} + 1) (record 0: from the launch).
// -DBMUT n (must FAIL): 1 slot index ignored (u_n1 commands carry xb 0; the SM reads its ring slot: live slot overwritten);
//   2 read issued before the producer's write retired (u_n1 drops a RAW record's own producer term: stale x);
//   3 ISSUE_AHEAD ignored (u_n1 predicted at N = 1 but fired at the N = 0 times: exposure / timing check).
`ifndef BMUT
`define BMUT 0
`endif
`ifndef MVD
`define MVD 800
`endif
module tb_ve_vm #(
    parameter [63:0] LQ = 64'd0,
    parameter [63:0] LR = 64'd0,
    parameter integer BK = 6
) (
    input  wire               clk,
    input  wire [8*17-1:0]    rq,
    output wire [8*257-1:0]   rr,
    output wire integer       lanefault,
    input  wire               pw_v,      // producer write retire: region [pw_base, pw_base + pw_n) := wval(word, pw_key)
    input  wire [14:0]        pw_base,
    input  wire [15:0]        pw_n,
    input  wire [7:0]         pw_key
);
    reg [31:0] mem [0:32767];
    function automatic [31:0] fin(input [31:0] r0);
        reg [31:0] r;
        begin
            r = r0 ^ (r0 >> 15); r = r * 32'h2C1B3C6D; r = r ^ (r >> 12);
            r[30:23] = 8'd100 + 8'(r[7:0] % 50);
            if (r[13:8] == 6'd0) r = 32'h0;
            fin = r;
        end
    endfunction
    initial for (integer a = 0; a < 32768; a = a + 1) mem[a] = fin(32'h9E3779B9 * (a + 1) ^ 32'h85EBCA6B);
    always @(posedge clk) if (pw_v)
        for (integer a = 0; a < 32768; a = a + 1)
            if (a >= pw_base && a < pw_base + pw_n) mem[a] <= fin((32'hC2B2AE35 * (a + 7)) ^ (32'h27D4EB2F * (pw_key + 1)));
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
        wire [16:0] at;
        if (NQ == 0) begin : g_q0
            assign at = rq[gb*17 +: 17];
        end else begin : g_q
            reg [16:0] ql [1:NQ];
            always @(posedge clk) begin ql[1] <= rq[gb*17 +: 17]; for (integer d = 2; d <= NQ; d = d + 1) ql[d] <= ql[d-1]; end
            assign at = ql[NQ];
        end
        reg [256:0] bp [1:BK];
        always @(posedge clk) begin
            if (at[16] && (at[2:0] != 3'(gb) || at[15])) lfv[gb] <= 1'b1;
            bp[1] <= look(at);
            for (integer d = 2; d <= BK; d = d + 1) bp[d] <= bp[d-1];
        end
        if (NRR == 0) begin : g_r0
            assign rr[gb*257 +: 257] = bp[BK];
        end else begin : g_r
            reg [256:0] rl [1:NRR];
            always @(posedge clk) begin rl[1] <= bp[BK]; for (integer d = 2; d <= NRR; d = d + 1) rl[d] <= rl[d-1]; end
            assign rr[gb*257 +: 257] = rl[NRR];
        end
    end endgenerate
endmodule

module tb_xload_vmearly;
    localparam integer BM = `BMUT, R = 29, NU = 3, MVD = `MVD, PW = 24, AT0 = 4, XD = 128, NG = 2, FPM = 64, T = 2;
    function automatic [63:0] pk(input integer a0, a1, a2, a3, a4, a5, a6, a7);
        pk = {8'(a7), 8'(a6), 8'(a5), 8'(a4), 8'(a3), 8'(a2), 8'(a1), 8'(a0)};
    endfunction
    function automatic integer el(input [63:0] v, input integer b);
        reg [63:0] x; begin x = v >> (8 * b); el = x[7:0]; end
    endfunction
    localparam [63:0] NE_LQ = pk(2, 3, 8, 9, 10, 11, 16, 17),  NE_LR = pk(1, 3, 8, 9, 9, 11, 16, 17);
    localparam [63:0] NE_RT = pk(10, 13, 23, 25, 26, 29, 39, 41);
    localparam [63:0] BUD = pk(37, 39, 27, 29, 53, 55, 43, 45);
    function automatic [63:0] padq(input [63:0] lq, input [63:0] rt, input [63:0] bud);
        padq = 0;
        for (integer b = 0; b < 8; b = b + 1) padq = padq | (64'(el(lq, b) + el(bud, b) - el(rt, b)) << (8 * b));
    endfunction
    localparam [63:0] LQB = padq(NE_LQ, NE_RT, BUD);
    function automatic integer mx(input integer a, input integer b); mx = (a > b) ? a : b; endfunction
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; integer errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    // ---- record list (DS layer 5, lead model order): n, fmt, RAW (x = the previous record's output), x region
    integer rn [0:R-1], rf [0:R-1], rraw [0:R-1], rreg [0:R-1], fp [0:R-1];
    string rnm [0:R-1];
    integer gbase [0:13], glen [0:13];
    task automatic rec(input integer i, input string nm, input integer n, input integer f, input integer raw, input integer g);
        begin
            rnm[i] = nm; rn[i] = n; rf[i] = f; rraw[i] = raw; rreg[i] = g;
            fp[i] = (f == 0) ? 8 * (((n - 1) >> 9) + 1) : (f == 2) ? 8 * (((n - 1) >> 11) + 1) : 8 * (((n - 1) >> 10) + 1);
        end
    endtask
    initial begin
        // x regions in VM words: h1 (attention input), q latent, q, P, o, o2, h2 (router / expert input), 7 expert mids
        gbase[0] = 0;    glen[0] = 5120; gbase[1] = 5120; glen[1] = 1024; gbase[2] = 6144; glen[2] = 512;
        gbase[3] = 6656; glen[3] = 512;  gbase[4] = 7168; glen[4] = 512;  gbase[5] = 7680; glen[5] = 1024;
        gbase[6] = 8704; glen[6] = 5120;
        for (integer k = 0; k < 7; k = k + 1) begin gbase[7 + k] = 13824 + 2048 * k; glen[7 + k] = 2048; end
        rec(0, "wq_a", 5120, 1, 1, 0);           rec(1, "wkv", 5120, 1, 0, 0);
        rec(2, "wq_b", 1024, 1, 1, 1);           rec(3, "att.qk(q)", 512, 0, 1, 2);
        rec(4, "att.pv(P)", 512, 0, 1, 3);       rec(5, "wo_a", 512, 1, 1, 4);
        rec(6, "wo_b", 1024, 1, 1, 5);           rec(7, "router", 5120, 1, 1, 6);
        rec(8, "e0.w1", 5120, 2, 0, 6);  rec(9, "e6.w1", 5120, 2, 0, 6);  rec(10, "e6.w3", 5120, 2, 0, 6);
        rec(11, "e0.w3", 5120, 2, 0, 6); rec(12, "e1.w1", 5120, 2, 0, 6); rec(13, "e1.w3", 5120, 2, 0, 6);
        rec(14, "e2.w1", 5120, 2, 0, 6); rec(15, "e2.w3", 5120, 2, 0, 6); rec(16, "e3.w1", 5120, 2, 0, 6);
        rec(17, "e3.w3", 5120, 2, 0, 6); rec(18, "e4.w1", 5120, 2, 0, 6); rec(19, "e4.w3", 5120, 2, 0, 6);
        rec(20, "e5.w1", 5120, 2, 0, 6); rec(21, "e5.w3", 5120, 2, 0, 6);
        rec(22, "e1.w2", 2048, 2, 1, 8); rec(23, "e4.w2", 2048, 2, 0, 11); rec(24, "e3.w2", 2048, 2, 0, 10);
        rec(25, "e0.w2", 2048, 2, 0, 7); rec(26, "e5.w2", 2048, 2, 0, 12); rec(27, "e2.w2", 2048, 2, 0, 9);
        rec(28, "e6.w2", 2048, 2, 1, 13);
    end
    function automatic [107:0] mkpl(input integer i, input integer xb);
        reg [39:0] base; reg [31:0] st;
        begin
            base = 40'(gbase[rreg[i]]); st = 32'(8 * ((rn[i] + 7) / 8));
            mkpl = {7'(xb), 2'(rf[i]), 2'd1, st, 4'd1, 21'(rn[i]), base};
        end
    endfunction
    // ---- host ingress, targets 100..102
    reg awv = 0, wv = 0; reg [11:0] awa = 0; reg [31:0] wd = 0;
    wire awr, wr, bv; wire [1:0] bresp;
    wire cfg_v, desc_v, launch_v, ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    wire act_any;
    ot_hbm_host_static_ingress #(.TARGET_MASK((256'd1 << 100) | (256'd1 << 101) | (256'd1 << 102))) ing (
        .clk(clk), .rst_n(rst_n), .s_awvalid(awv), .s_awready(awr), .s_awaddr(awa), .s_wvalid(wv), .s_wready(wr),
        .s_wdata(wd), .s_wstrb(4'hf), .s_bvalid(bv), .s_bready(1'b1), .s_bresp(bresp), .s_arvalid(1'b0), .s_arready(),
        .s_araddr(12'd0), .s_rvalid(), .s_rready(1'b1), .s_rdata(), .block_ready(1'b1), .program_active(act_any),
        .program_fault(1'b0), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .fault(ing_fault));
    wire [8*17-1:0] rq [0:NU-1]; wire [8*257-1:0] rr [0:NU-1];
    integer lf [0:NU-1];
    wire [NU-1:0] cf, ft, ac;
    wire [1:0] xd [0:NU-1], xe [0:NU-1], xl [0:NU-1]; wire [13:0] xa [0:NU-1], xg [0:NU-1]; wire [2*2048-1:0] xx [0:NU-1];
`define VE_PORTS(U, TG) \
        .clk(clk), .clk_cal(clk), .clk_qlo(clk), .clk_qhi(clk), .clk_bf({8{clk}}), .clk_bd({2{clk}}), .clk_eg({2{clk}}), \
        .rst_n(rst_n), .tgt(8'd``TG), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), \
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), \
        .configured(cf[U]), .fault(ft[U]), .active(ac[U]), .x_done(xd[U]), .xw_en(xe[U]), .xw_last(xl[U]), .xw_addr(xa[U]), \
        .xw_grp(xg[U]), .xw_data(xx[U]), .rq(rq[U]), .rr(rr[U])
    ot_hgi_sm_xload_static_xql #(.RD_LAT(BUD), .MUT(0), .NP(2), .T(T), .XQL_MUT(0)) u_n0 (`VE_PORTS(0, 100));
    ot_hgi_sm_xload_static_xql #(.RD_LAT(BUD), .MUT(0), .NP(2), .T(T), .XQL_MUT(0)) u_n1 (`VE_PORTS(1, 101));
    ot_hgi_sm_xload_static_xql #(.RD_LAT(64'd6), .MUT(0), .NP(2), .T(T), .XQL_MUT(0)) u_r6 (`VE_PORTS(2, 102));
    assign act_any = |ac;
    wire [NU-1:0] pst = {u_r6.g_ctl.u_ctl.u_w.u_ctl.start, u_n1.g_ctl.u_ctl.u_w.u_ctl.start, u_n0.g_ctl.u_ctl.u_w.u_ctl.start};
    wire [NU-1:0] pbz = {u_r6.g_ctl.u_ctl.u_w.u_ctl.x_busy, u_n1.g_ctl.u_ctl.u_w.u_ctl.x_busy, u_n0.g_ctl.u_ctl.u_w.u_ctl.x_busy};
    reg [NU-1:0] pw_v = 0; reg [14:0] pw_base [0:NU-1]; reg [15:0] pw_n [0:NU-1]; reg [7:0] pw_key [0:NU-1];
    tb_ve_vm #(.LQ(LQB), .LR(NE_LR), .BK(7)) vm0 (.clk(clk), .rq(rq[0]), .rr(rr[0]), .lanefault(lf[0]),
        .pw_v(pw_v[0]), .pw_base(pw_base[0]), .pw_n(pw_n[0]), .pw_key(pw_key[0]));
    tb_ve_vm #(.LQ(LQB), .LR(NE_LR), .BK(7)) vm1 (.clk(clk), .rq(rq[1]), .rr(rr[1]), .lanefault(lf[1]),
        .pw_v(pw_v[1]), .pw_base(pw_base[1]), .pw_n(pw_n[1]), .pw_key(pw_key[1]));
    tb_ve_vm #(.LQ(64'd0), .LR(64'd0), .BK(6)) vm6 (.clk(clk), .rq(rq[2]), .rr(rr[2]), .lanefault(lf[2]),
        .pw_v(pw_v[2]), .pw_base(pw_base[2]), .pw_n(pw_n[2]), .pw_key(pw_key[2]));
    // ---- launch reference + phase-1 calibration capture
    integer Lc = 0; integer ph = 0;
    always @(posedge clk) if (launch_v) Lc <= cyc;
    integer c_st [0:NU-1], c_fb [0:NU-1], c_xd [0:NU-1], c_bf [0:NU-1];
    integer FO [0:NU-1], F [0:NU-1][0:R-1], X [0:NU-1][0:R-1], B [0:NU-1][0:R-1];
    always @(posedge clk) if (ph == 1) for (integer u = 0; u < NU; u = u + 1) begin
        if (pst[u] && c_st[u] < 0) c_st[u] <= cyc;
        if (xe[u][0] && c_st[u] >= 0 && c_fb[u] < 0) c_fb[u] <= cyc;
        if (xd[u][0] && c_xd[u] < 0) c_xd[u] <= cyc;
        if (c_st[u] >= 0 && cyc > c_st[u] && !pbz[u] && c_bf[u] < 0) c_bf[u] <= cyc;
    end
    // ---- compiler plan (launch-relative cycles)
    integer ps [0:NU-1][0:R-1], pat [0:NU-1][0:R-1], pxd [0:NU-1][0:R-1], pstt [0:NU-1][0:R-1], pend [0:NU-1][0:R-1];
    integer pxb [0:NU-1][0:R-1], ipl_at [0:NU-1][0:R-1], ipl_xb [0:NU-1][0:R-1];
    function automatic integer ovl(input integer xa0, input integer fa, input integer xb0, input integer fb);
        integer hit; hit = 0;
        for (integer r = 0; r < fb; r = r + 1) if (((xb0 + r - xa0 + 2 * XD) % XD) < fa) hit = 1;
        ovl = hit;
    endfunction
    task automatic plan(input integer u, input integer mode, input integer use_raw);
        integer lo, xbp, pj;
        begin
            xbp = 0;
            for (integer i = 0; i < R; i = i + 1) begin
                if (mode == 1) begin pxb[u][i] = xbp; xbp = (xbp + fp[i]) % XD; end else pxb[u][i] = 0;
                lo = FO[u] + AT0;
                if (i > 0) lo = mx(lo, ps[u][i-1] + B[u][i-1]);
                for (integer j = 0; j <= i; j = j + 1) if (rraw[j] && rreg[j] == rreg[i] && (use_raw || j != i)) begin
                    pj = (j == 0) ? PW : pend[u][j-1] + PW;
                    lo = mx(lo, pj + 1);
                end
                if (mode == 0) begin
                    if (i > 0) lo = mx(lo, pend[u][i-1] + 1);
                end else begin
                    if (i > 0) lo = mx(lo, pstt[u][i-1]);
                    for (integer j = 0; j < i; j = j + 1)
                        if (ovl(pxb[u][j], fp[j], pxb[u][i], fp[i])) lo = mx(lo, pend[u][j] + 1 - F[u][i]);
                end
                ps[u][i] = lo; pat[u][i] = lo - FO[u];
                pxd[u][i] = lo + X[u][i];
                pstt[u][i] = mx((i > 0) ? pend[u][i-1] + 1 : 0, pxd[u][i] + 1);
                pend[u][i] = pstt[u][i] + MVD - 1;
            end
        end
    endtask
    // ---- phase-2 SM model (pair 0 of every unit) + producers
    reg [2047:0] xs [0:NU-1][0:XD-1][0:NG-1];
    reg [2047:0] snap [0:NU-1][0:R*FPM*NG-1];
    integer cur [0:NU-1], kn [0:NU-1], m_xd [0:NU-1][0:R-1], m_st [0:NU-1][0:R-1], m_en [0:NU-1][0:R-1];
    integer m_fire [0:NU-1][0:R-1], nfire [0:NU-1];
    integer novw [0:NU-1], nbeat [0:NU-1];
    integer L2 = 0;
    always @(posedge clk) if (ph == 2) begin : smm
        integer tau, a, g, k, pj;
        if (launch_v) L2 = cyc;
        tau = cyc - L2;
        pw_v <= '0;
        for (integer u = 0; u < NU; u = u + 1) begin
            if (pst[u]) begin if (nfire[u] < R) m_fire[u][nfire[u]] = tau; nfire[u] = nfire[u] + 1; end
            if (xe[u][0]) begin
                a = xa[u][6:0]; g = xg[u][6:0]; nbeat[u] = nbeat[u] + 1;
                for (integer j = 0; j < R; j = j + 1)
                    if (j < cur[u] && (m_en[u][j] < 0 || tau <= m_en[u][j]) && ovl(pxb[u][j], fp[j], a, 1)) begin
                        if (novw[u] < 4) $display("ERR unit %0d: xw write addr %0d (record %0d) into the live slot of record %0d at tau %0d", u, a, cur[u], j, tau);
                        novw[u] = novw[u] + 1;
                    end
                if (g < NG) xs[u][a][g] = xx[u][2047:0];
            end
            if (xd[u][0]) begin if (cur[u] < R) m_xd[u][cur[u]] = tau; cur[u] = cur[u] + 1; end
            k = kn[u];
            if (k < R && m_xd[u][k] >= 0 && tau >= m_xd[u][k] + 1 && tau >= ((k > 0) ? m_en[u][k-1] + 1 : 0)) begin
                m_st[u][k] = tau; m_en[u][k] = tau + MVD - 1; kn[u] = k + 1;
                for (integer r = 0; r < fp[k]; r = r + 1) for (integer gg = 0; gg < NG; gg = gg + 1)
                    snap[u][(k * FPM + r) * NG + gg] = xs[u][(pxb[u][k] + r) % XD][gg];
            end
            // producers: RAW record i's x region retires PW edges after the SM end of record i-1 (record 0: tau = PW)
            for (integer i = 0; i < R; i = i + 1) if (rraw[i]) begin
                pj = (i == 0) ? PW : ((m_en[u][i-1] >= 0) ? m_en[u][i-1] + PW : -1);
                if (tau == pj) begin pw_v[u] <= 1'b1; pw_base[u] <= 15'(gbase[rreg[i]]); pw_n[u] <= 16'(glen[rreg[i]]); pw_key[u] <= 8'(i); end
            end
        end
    end
    // ---- host writes (as tb_hgi_xload_banklat)
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
                    if (w > 2000) begin $display("XLOAD_VMEARLY FAIL: AXI write %h no bvalid", a); $fflush; $finish; end end
            end
            if (bresp != 0) begin $display("ERR bresp %0d at %h data %h", bresp, a, d); errors = errors + 1; end
            @(posedge clk);
        end
    endtask
    task automatic row_install(input [7:0] tg, input integer row, input [107:0] pl, input [31:0] at);
        reg [255:0] w;
        begin
            w = {116'd0, pl, at};
            axw(12'hf20, {12'd0, 12'(12'h800 + row), tg});
            for (integer p = 0; p < 8; p = p + 1) axw(12'hf24, w[p*32 +: 32]);
        end
    endtask
    task automatic arm(input [7:0] tg, input integer nrow);
        begin axw(12'hf20, {12'd0, 12'd0, tg}); axw(12'hf28, {7'd0, 13'(nrow), 12'd0}); axw(12'hf2c, 32'd1); end
    endtask
    integer t, sum [0:NU-1], sbl0, sbl1, nov, nmis, ntm, e0, e1, e6;
    initial begin
        for (integer u = 0; u < NU; u = u + 1) begin
            cur[u] = 0; kn[u] = 0; novw[u] = 0; nbeat[u] = 0; nfire[u] = 0; pw_base[u] = 0; pw_n[u] = 0; pw_key[u] = 0;
            for (integer i = 0; i < R; i = i + 1) begin m_xd[u][i] = -1; m_st[u][i] = -1; m_en[u][i] = -1; m_fire[u][i] = -1; end
        end
        $display("XLOAD_VMEARLY BMUT=%0d MVD=%0d PW=%0d RD_LAT budget %h (RLM 55) lanes NE + pads %h / ref RD_LAT 6", BM, MVD, PW, BUD, LQB);
        repeat (3) @(posedge clk); rst_n = 1; repeat (40) @(posedge clk);
        // ===== phase 1: calibrate every record alone on every unit
        ph = 1;
        for (integer i = 0; i < R; i = i + 1) begin
            for (integer u = 0; u < NU; u = u + 1) begin c_st[u] = -1; c_fb[u] = -1; c_xd[u] = -1; c_bf[u] = -1; end
            for (integer u = 0; u < NU; u = u + 1) begin row_install(8'(100 + u), 0, mkpl(i, 0), 32'(AT0)); arm(8'(100 + u), 1); end
            repeat (6) @(posedge clk);
            if (cf !== 3'b111 || |ft || ing_fault) begin $display("ERR calibrate %0d install: configured %b fault %b", i, cf, ft); errors = errors + 1; end
            axw(12'hf30, 32'd1);
            t = 0; while ((c_xd[0] < 0 || c_xd[1] < 0 || c_xd[2] < 0 || act_any || c_bf[0] < 0 || c_bf[1] < 0 || c_bf[2] < 0) && t < 100000) begin @(posedge clk); t = t + 1; end
            repeat (8) @(posedge clk);
            if (t >= 100000) begin $display("ERR calibrate %0d timeout", i); errors = errors + 1; end
            for (integer u = 0; u < NU; u = u + 1) begin
                F[u][i] = c_fb[u] - c_st[u]; X[u][i] = c_xd[u] - c_st[u]; B[u][i] = c_bf[u] - c_st[u];
                if (i == 0) FO[u] = c_st[u] - Lc - AT0;
                else if (c_st[u] - Lc - AT0 != FO[u]) begin $display("ERR unit %0d launch->start offset varies", u); errors = errors + 1; end
            end
            $display("CAL %2d %-10s fmt %0d n %5d fp %2d | RL55 F %3d X %3d B %3d | RL6 F %3d X %3d B %3d", i, rnm[i], rf[i], rn[i], fp[i],
                     F[0][i], X[0][i], B[0][i], F[2][i], X[2][i], B[2][i]);
            if (F[0][i] != F[1][i] || X[0][i] != X[1][i] || B[0][i] != B[1][i]) begin $display("ERR u_n0 / u_n1 calibrations differ"); errors = errors + 1; end
        end
        $display("CAL launch->start FO %0d / %0d / %0d", FO[0], FO[1], FO[2]);
        // ===== compiler: N0 for u_n0 / u_r6, N1 for u_n1 (mutants: see header)
        plan(0, 0, 1); plan(2, 0, 1);
        if (BM == 3) begin
            plan(1, 0, 1);
            for (integer i = 0; i < R; i = i + 1) begin ipl_at[1][i] = pat[1][i]; ipl_xb[1][i] = pxb[1][i]; end
            plan(1, 1, 1);
            for (integer i = 0; i < R; i = i + 1) ipl_xb[1][i] = pxb[1][i];
        end else begin
            plan(1, 1, (BM == 2) ? 0 : 1);
            for (integer i = 0; i < R; i = i + 1) begin ipl_at[1][i] = pat[1][i]; ipl_xb[1][i] = (BM == 1) ? 0 : pxb[1][i]; end
        end
        for (integer i = 0; i < R; i = i + 1) begin
            ipl_at[0][i] = pat[0][i]; ipl_xb[0][i] = pxb[0][i]; ipl_at[2][i] = pat[2][i]; ipl_xb[2][i] = pxb[2][i];
        end
        // ===== phase 2: the layer, one launch
        for (integer u = 0; u < NU; u = u + 1) begin
            for (integer i = 0; i < R; i = i + 1) row_install(8'(100 + u), i, mkpl(i, ipl_xb[u][i]), 32'(ipl_at[u][i]));
            arm(8'(100 + u), R);
        end
        repeat (6) @(posedge clk);
        if (cf !== 3'b111 || |ft || ing_fault) begin $display("ERR layer install: configured %b fault %b", cf, ft); errors = errors + 1; end
        @(negedge clk); ph = 2;
        axw(12'hf30, 32'd1);
        t = 0; while ((kn[0] < R || kn[1] < R || kn[2] < R) && t < 400000) begin @(posedge clk); t = t + 1; end
        repeat (MVD + 40) @(posedge clk);
        if (t >= 400000) begin $display("ERR layer did not finish: SM records %0d / %0d / %0d, x_done %0d / %0d / %0d, fault %b",
                                        kn[0], kn[1], kn[2], cur[0], cur[1], cur[2], ft); errors = errors + 1; end
        // ===== checks + report
        nov = 0; nmis = 0; ntm = 0;
        for (integer u = 0; u < NU; u = u + 1) begin
            sum[u] = 0; nov = nov + novw[u];
            if (cur[u] != R) begin $display("ERR unit %0d x_done %0d of %0d", u, cur[u], R); errors = errors + 1; end
            for (integer i = 0; i < R; i = i + 1) begin
                if (m_xd[u][i] != pxd[u][i] || m_st[u][i] != pstt[u][i]) begin
                    if (ntm < 6) $display("ERR unit %0d record %0d: x_done %0d / SM start %0d, predicted %0d / %0d", u, i, m_xd[u][i], m_st[u][i], pxd[u][i], pstt[u][i]);
                    ntm = ntm + 1;
                end
                sum[u] = sum[u] + m_st[u][i] - ((i > 0) ? m_en[u][i-1] + 1 : 0);
            end
        end
        for (integer u = 1; u < NU; u = u + 1) for (integer i = 0; i < R; i = i + 1)
            for (integer r = 0; r < fp[i]; r = r + 1) for (integer gg = 0; gg < NG; gg = gg + 1)
                if (snap[u][(i * FPM + r) * NG + gg] !== snap[0][(i * FPM + r) * NG + gg]) begin
                    if (nmis < 6) $display("ERR unit %0d record %0d (%s) slot word %0d beat %0d differs from u_n0 at its SM start", u, i, rnm[i], r, gg);
                    nmis = nmis + 1;
                end
        sbl0 = 0; sbl1 = 0;
        $display("LAYER rec  name       fmt     n  xb1 | exposed RL6/N0  RL55/N0  RL55/N1 | N1 fire-before-prev-end");
        for (integer i = 0; i < R; i = i + 1) begin
            e0 = m_st[0][i] - ((i > 0) ? m_en[0][i-1] + 1 : 0);
            e1 = m_st[1][i] - ((i > 0) ? m_en[1][i-1] + 1 : 0);
            e6 = m_st[2][i] - ((i > 0) ? m_en[2][i-1] + 1 : 0);
            sbl0 = sbl0 + e0 - e6; sbl1 = sbl1 + mx(0, e1 - e6);
            $display("LAYER %3d  %-10s %0d  %5d  %3d | %6d   %6d   %6d | %0s%0s", i, rnm[i], rf[i], rn[i], pxb[1][i], e6, e0, e1,
                     (i > 0 && m_fire[1][i] >= 0 && m_fire[1][i] < m_en[1][i-1]) ? "yes" : "no", rraw[i] ? " (RAW)" : "");
        end
        $display("XLOAD_VMEARLY_LAYER exposed x-leg edges (29 records): RL6 N0 %0d | RL55 N0 %0d | RL55 N1 %0d; bank-latency part (vs RL6): before %0d after %0d; layer span N0 %0d N1 %0d",
                 sum[2], sum[0], sum[1], sbl0, sbl1, m_en[0][R-1], m_en[1][R-1]);
        $display("XLOAD_VMEARLY checks: timing-off-plan %0d, live-slot writes %0d (u %0d/%0d/%0d), slot words differing %0d, beats %0d/%0d/%0d, fault %b, lanefault %0d/%0d/%0d",
                 ntm, nov, novw[0], novw[1], novw[2], nmis, nbeat[0], nbeat[1], nbeat[2], ft, lf[0], lf[1], lf[2]);
        if (ntm || nov || nmis || |ft || ing_fault || lf[0] || lf[1] || lf[2] || nbeat[0] == 0 || !(sum[1] < sum[0])) errors = errors + 1;
        if (errors == 0) $display("XLOAD_VMEARLY PASS"); else $display("XLOAD_VMEARLY FAIL BMUT=%0d errors=%0d", BM, errors);
        $finish;
    end
endmodule
