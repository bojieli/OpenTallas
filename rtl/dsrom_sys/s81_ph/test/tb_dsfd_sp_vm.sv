`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_dsfd_sp_vm -- exact gate + throughput bench of the S81 VM master dsfd_sp_vm_m (s81-vm-1011, 2026-10-11):
// the FE (dsfd_vm_fe), 4 x 4 CLOSED dsfd_vm_bgq tiles (NSTG 2, real SRAM macro models) and the BE (dsfd_vm_be).
//
// Clients (all at the master's die pins, the link ones behind registered relay stations):
//   WFC kit   : ltx senders on the sw (writes + START doorbell) / sr (RD2 read pairs) links, VF / VR stations; t_ks and
//               t_srq checked (doorbell after every earlier write is ordered; every read pair's data).
//   capture W : ltx sender on the posted-write link (CF / CR stations): pool bursts (hazards) and ARMed region fills.
//   ctrl      : VM write / read port + engine commands ARM / P2ID / P2RD, done (dv / dt) consumed.
//   P2 lane 0 : the dsfd_vm_p2_ep core side (c_l0r random grants), every flit's data and metadata checked.
//   X0 / X1   : random reads / writes over a small row pool (cross-port hazards with every client).
//   MTP       : rows-ready (c_wr random), checked against the notify slots.
// Reference: a 16,384 x 512 b array updated at the FE order register (u_fe.b_*) in (cycle, port) order; every read's
// expected row is taken there and compared at its return port.  Per-client scoreboards check that every op the
// client sent reaches the order register exactly once and in order (catches a dropped posted write).  The
// free-running ports (ctrl, X) are gated by an exact mirror of the tiles' bank-queue arithmetic, projected over the
// two cycles between the pins and the order register (the stall-free contract the compiler's schedule keeps).
// PASS needs: 0 mismatches, every scoreboard drained, every ARM / P2RD done received, rows-ready = notify slots,
// fe_flt = 0, fvec = 0, constant read latency per port.
// MODE 1 = throughput: production-shaped streams only (see the THROUGHPUT block), measured cycles printed.
// ---------------------------------------------------------------------------------------------------------------
module tb_spvm_relay #(parameter integer W = 1, parameter integer N = 0) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (N == 0) begin : g0 assign q = d; end
    else begin : gn
        reg [W-1:0] p [0:N-1]; integer i;
        initial for (i = 0; i < N; i = i + 1) p[i] = '0;
        always @(posedge clk) begin p[0] <= d; for (i = 1; i < N; i = i + 1) p[i] <= p[i-1]; end
        assign q = p[N-1];
    end endgenerate
endmodule

module tb_dsfd_sp_vm;
    parameter integer SEED = 1;
    parameter integer NCYC = 60000;
    parameter integer MODE = 0;              // 0 gate, 1 throughput
    parameter integer CF = 8, CR = 8, VF = 13, VR = 13, P2D = 40;
    parameter integer TP_ROWS = 64;          // throughput: rows per stream
    parameter integer EARLYC = 0;            // negative control: stream a region to P2 right after its ARM (before done)
    localparam integer QD = 4, NB = 32, NP = 8, NROW = 16384, POOL = 64, MARK = 32767;

    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0;
    // ------------------------------------------------------------ DUT
    wire t_swg, t_srg, t_err, t_cwg, vrv, dv, c_wv, c_l0v; wire [52:0] t_ks; wire [1025:0] t_srq; wire [511:0] vrq;
    wire [7:0] dt; wire [1:0] x_ov; wire [1023:0] x_od; wire [9:0] c_wd; wire [603:0] c_l0d; wire flt; wire [15:0] fvec;
    wire [2:0] max_occ;
    wire p_swv, p_srv, p_cwv; wire [526:0] p_swd; wire [30:0] p_srd; wire [541:0] p_cwd;
    reg vwe = 0, vre = 0, cv = 0, c_wr = 0, c_l0r = 0; reg [13:0] vwa = 0, vra = 0; reg [511:0] vwd = 0; reg [83:0] cd = 0;
    reg [1:0] x_v = 0, x_we = 0; reg [27:0] x_row = 0; reg [31:0] x_mask = 0; reg [1023:0] x_d = 0;
    dsfd_sp_vm_m #(.MACRO(1), .CF(CF), .CR(CR), .VF(VF), .VR(VR), .P2D(P2D)) dut (
        .ck(clk), .rst(rst_n), .f_swv(p_swv), .f_swd(p_swd), .t_swg(t_swg), .f_srv(p_srv), .f_srd(p_srd), .t_srg(t_srg),
        .t_ks(t_ks), .t_srq(t_srq), .t_err(t_err), .f_cwv(p_cwv), .f_cwd(p_cwd), .t_cwg(t_cwg),
        .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra), .vrv(vrv), .vrq(vrq), .cv(cv), .cd(cd), .dv(dv), .dt(dt),
        .x_v(x_v), .x_we(x_we), .x_row(x_row), .x_mask(x_mask), .x_d(x_d), .x_ov(x_ov), .x_od(x_od),
        .c_wv(c_wv), .c_wd(c_wd), .c_wr(c_wr), .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(c_l0r),
        .flt(flt), .fvec(fvec), .max_occ(max_occ));
    // ------------------------------------------------------------ link senders (ltx) + relay stations
    reg s_wv = 0, s_rv = 0, s_cv = 0; reg [526:0] s_wd = 0; reg [30:0] s_rd = 0; reg [541:0] s_cd = 0;
    wire s_wr, s_rr, s_cr; wire k_swv, k_srv, k_cwv, g_sw, g_sr, g_cw; wire [526:0] k_swd; wire [30:0] k_srd; wire [541:0] k_cwd;
    ot_dsrom_mtp_ltx #(.W(527)) x_sw (.clk(clk), .rst_n(rst_n), .c_valid(s_wv), .c_ready(s_wr), .c_data(s_wd), .l_valid(k_swv), .l_ready(g_sw), .l_data(k_swd));
    ot_dsrom_mtp_ltx #(.W(31))  x_sr (.clk(clk), .rst_n(rst_n), .c_valid(s_rv), .c_ready(s_rr), .c_data(s_rd), .l_valid(k_srv), .l_ready(g_sr), .l_data(k_srd));
    ot_dsrom_mtp_ltx #(.W(542)) x_cw (.clk(clk), .rst_n(rst_n), .c_valid(s_cv), .c_ready(s_cr), .c_data(s_cd), .l_valid(k_cwv), .l_ready(g_cw), .l_data(k_cwd));
    tb_spvm_relay #(.W(528), .N(VF)) r1 (.clk(clk), .d({k_swv, k_swd}), .q({p_swv, p_swd}));
    tb_spvm_relay #(.W(1),   .N(VR)) r2 (.clk(clk), .d(t_swg), .q(g_sw));
    tb_spvm_relay #(.W(32),  .N(VF)) r3 (.clk(clk), .d({k_srv, k_srd}), .q({p_srv, p_srd}));
    tb_spvm_relay #(.W(1),   .N(VR)) r4 (.clk(clk), .d(t_srg), .q(g_sr));
    tb_spvm_relay #(.W(543), .N(CF)) r5 (.clk(clk), .d({k_cwv, k_cwd}), .q({p_cwv, p_cwd}));
    tb_spvm_relay #(.W(1),   .N(CR)) r6 (.clk(clk), .d(t_cwg), .q(g_cw));

    // ------------------------------------------------------------ helpers
    function automatic [31:0] mix(input [31:0] a, input [31:0] b);
        reg [31:0] h; begin h = a ^ (b * 32'h9e3779b9); h = h ^ (h >> 15); h = h * 32'h85ebca6b; h = h ^ (h >> 13); mix = h; end
    endfunction
    function automatic [511:0] rowdata(input [31:0] s);
        integer b; reg [31:0] h; begin h = s; for (b = 0; b < 16; b = b + 1) begin h = mix(h, b + 1); rowdata[32*b +: 32] = h; end end
    endfunction
    reg [31:0] rs = 0;
    function automatic [31:0] rnd(input integer dummy);
        begin rs = mix(rs, 32'h1234567 + dummy); rnd = rs; end
    endfunction

    // ------------------------------------------------------------ reference array + expectations
    reg [511:0] gm [0:NROW-1];
    integer i0; initial for (i0 = 0; i0 < NROW; i0 = i0 + 1) gm[i0] = 512'd0;
    // expected read data per return port: p0 / p1 (t_srq), p4 (vrq), p5 (P2), p6 / p7 (x_od)
    reg [511:0] ex_q [0:7][$];
    integer ex_t [0:7][$];
    integer lat [0:7]; integer nchk = 0, nbad = 0;
    // scoreboards: ops the clients sent, in order: {row, data-hash}
    integer sb_c [$];   // capture rows
    integer sb_w [$];   // WFC writes (row)
    integer sb_r [$];   // WFC read pairs: row0 | (v1 << 16) | (row1 << 17)
    integer sb_x [$];   // ctrl / X ops: {port, row, we}
    integer nw_sent_b4_db [$];   // WFC: writes sent before each doorbell
    integer ks_pay [$];
    integer n_wfc_w_seen = 0;
    // bank mirror (stall-free contract) at the order register
    integer occ_m [0:NB-1]; integer ovf_m = 0, maxocc_m = 0;
    integer bi; initial for (bi = 0; bi < NB; bi = bi + 1) occ_m[bi] = 0;

    // ------------------------------------------------------------ observe the order register (b_* set at the last edge)
    wire [NP-1:0] b_v = dut.u_fe.b_v, b_we = dut.u_fe.b_we;
    wire [NP*14-1:0] b_row = dut.u_fe.b_row; wire [NP*16-1:0] b_m = dut.u_fe.b_m; wire [NP*512-1:0] b_d = dut.u_fe.b_d;
    function automatic integer step_mirror(inout integer occ [0:NB-1], input integer rows [$]);
        integer cntb [0:NB-1]; integer b, need, ovf;
        begin
            ovf = 0;
            for (b = 0; b < NB; b = b + 1) cntb[b] = 0;
            foreach (rows[j]) cntb[rows[j] % NB] = cntb[rows[j] % NB] + 1;
            for (b = 0; b < NB; b = b + 1) begin
                need = occ[b] - (occ[b] != 0) + cntb[b];
                if (need > QD) begin ovf = 1; need = QD; end
                occ[b] = need;
            end
            step_mirror = ovf;
        end
    endfunction

    integer p, e, rw; reg [511:0] old, nd, mk;
    integer obs_rows [$];
    integer done_seen [$];
    integer p2_words_seen = 0;
    task automatic observe_b();
        obs_rows.delete();
        for (p = 0; p < NP; p = p + 1) if (b_v[p]) begin
            rw = b_row[p*14 +: 14];
            obs_rows.push_back(rw);
            if (b_we[p]) begin
                old = gm[rw]; nd = b_d[p*512 +: 512];
                for (e = 0; e < 16; e = e + 1) mk[32*e +: 32] = {32{b_m[p*16 + e]}};
                gm[rw] = (old & ~mk) | (nd & mk);
            end else begin
                ex_q[p].push_back(gm[rw]); ex_t[p].push_back(cyc);
            end
            // client scoreboards
            if (p == 2) begin
                if (sb_c.size() == 0 || sb_c[0] != rw) begin $display("FAIL cyc %0d: capture write row %0d not the next sent (%0d)", cyc, rw, sb_c.size() ? sb_c[0] : -1); nbad = nbad + 1; end
                else void'(sb_c.pop_front());
            end
            if (p == 0 && b_we[0]) begin
                n_wfc_w_seen = n_wfc_w_seen + 1;
                if (sb_w.size() == 0 || sb_w[0] != rw) begin $display("FAIL cyc %0d: WFC write row %0d not the next sent", cyc, rw); nbad = nbad + 1; end
                else void'(sb_w.pop_front());
            end
            if (p == 0 && !b_we[0]) begin
                if (sb_r.size() == 0 || (sb_r[0] & 16'hffff) != rw || ((sb_r[0] >> 16) & 1) != b_v[1] ||
                    (b_v[1] && ((sb_r[0] >> 17) & 16'h3fff) != b_row[14 +: 14])) begin
                    $display("FAIL cyc %0d: WFC read pair at %0d / %0d not the next sent", cyc, rw, b_row[14 +: 14]); nbad = nbad + 1;
                end else void'(sb_r.pop_front());
            end
            if (p == 3 || p == 4 || p == 6 || p == 7) begin
                if (sb_x.size() == 0 || sb_x[0] != (p << 20 | rw << 1 | b_we[p])) begin
                    $display("FAIL cyc %0d: port %0d op row %0d not the next pinned one", cyc, p, rw); nbad = nbad + 1;
                end else void'(sb_x.pop_front());
            end
        end
        begin : mir
            integer o;
            o = step_mirror(occ_m, obs_rows);
            if (o) begin ovf_m = ovf_m + 1; if (ovf_m < 5) $display("MIRROR OVERFLOW cyc %0d (contract broken by the stimulus)", cyc); end
            for (e = 0; e < NB; e = e + 1) if (occ_m[e] > maxocc_m) maxocc_m = occ_m[e];
        end
    endtask

    // ------------------------------------------------------------ returns
    task automatic chk(input integer pp, input [511:0] got);
        reg [511:0] w; integer t; begin
            if (ex_q[pp].size() == 0) begin $display("FAIL cyc %0d: unexpected read data on port %0d", cyc, pp); nbad = nbad + 1; end
            else begin
                w = ex_q[pp].pop_front(); t = ex_t[pp].pop_front(); nchk = nchk + 1;
                if (pp != 5) begin
                    if (lat[pp] < 0) lat[pp] = cyc - t;
                    else if (lat[pp] != cyc - t) begin $display("FAIL cyc %0d: port %0d latency %0d != %0d", cyc, pp, cyc - t, lat[pp]); nbad = nbad + 1; end
                end
                if (w !== got) begin
                    nbad = nbad + 1;
                    if (nbad < 12) $display("MISMATCH cyc %0d port %0d: got %h.. exp %h..", cyc, pp, got[63:0], w[63:0]);
                end
            end
        end
    endtask
    // P2 command bookkeeping (bench side): words expected {identity, expert, shared, base, nw}
    integer p2c_base [$], p2c_nw [$], p2c_ex [$], p2c_sh [$], p2c_tag [$]; reg [73:0] p2c_id [$];
    integer p2_w = 0;
    integer rr_exp [$];       // rows-ready users expected (multiset)
    integer n_rr = 0;
    integer ks_seen = 0;
    task automatic check_returns();
        if (t_srq[512]) chk(0, t_srq[511:0]);
        if (t_srq[1025]) chk(1, t_srq[1024:513]);
        if (vrv) chk(4, vrq);
        if (x_ov[0]) chk(6, x_od[511:0]);
        if (x_ov[1]) chk(7, x_od[1023:512]);
        if (c_l0v && c_l0r) begin
            chk(5, c_l0d[511:0]);
            p2_words_seen = p2_words_seen + 1;
            if (p2c_base.size() == 0) begin $display("FAIL cyc %0d: P2 flit without a command", cyc); nbad = nbad + 1; end
            else if (c_l0d[603:530] !== p2c_id[0] || c_l0d[529:521] != p2c_ex[0] || c_l0d[520] != p2c_sh[0] ||
                     c_l0d[519] != (p2_w == p2c_nw[0]) || c_l0d[518:512] != p2_w) begin
                $display("FAIL cyc %0d: P2 flit metadata (word %0d / %0d)", cyc, c_l0d[518:512], p2_w); nbad = nbad + 1;
            end
            if (p2c_base.size() != 0 && p2c_base[0] >= 1024) begin
                if (!fill_d.exists(p2c_base[0] + p2_w) || fill_d[p2c_base[0] + p2_w] !== c_l0d[511:0]) begin
                    nbad = nbad + 1;
                    if (nbad < 12) $display("FAIL cyc %0d: P2 word %0d of region %0d is not the captured row (early / stale read)", cyc, p2_w, p2c_base[0]);
                end
            end
            if (p2c_base.size() != 0) begin
                if (p2_w == p2c_nw[0]) begin
                    p2_w = 0; void'(p2c_base.pop_front()); void'(p2c_nw.pop_front()); void'(p2c_ex.pop_front());
                    void'(p2c_sh.pop_front()); void'(p2c_id.pop_front()); void'(p2c_tag.pop_front());
                end else p2_w = p2_w + 1;
            end
        end
        if (t_ks[52]) begin
            ks_seen = ks_seen + 1;
            if (ks_pay.size() == 0 || ks_pay[0] != t_ks[31:0]) begin $display("FAIL cyc %0d: START payload", cyc); nbad = nbad + 1; end
            else void'(ks_pay.pop_front());
            if (nw_sent_b4_db.size() == 0 || n_wfc_w_seen < nw_sent_b4_db[0]) begin
                $display("FAIL cyc %0d: START before its writes were ordered (%0d < %0d)", cyc, n_wfc_w_seen, nw_sent_b4_db.size() ? nw_sent_b4_db[0] : -1);
                nbad = nbad + 1;
            end else void'(nw_sent_b4_db.pop_front());
        end
        if (c_wv && c_wr) begin
            begin : rrm
                integer f; f = -1;
                foreach (rr_exp[j]) if (f < 0 && rr_exp[j] == c_wd) f = j;
                if (f < 0) begin $display("FAIL cyc %0d: rows-ready user %0d not expected", cyc, c_wd); nbad = nbad + 1; end
                else rr_exp.delete(f);
                for (j = 0; j < 4; j = j + 1) if (slot_busy[j] == 2 && slot_user[j] == c_wd) slot_busy[j] = 0;
                n_rr = n_rr + 1;
            end
        end
        if (dv) done_seen.push_back(dt);
    endtask

    // ------------------------------------------------------------ stimulus
    // capture jobs: rows to write (in order), and per-row gap before it
    integer cj_row [$], cj_gap [$];
    reg [511:0] fill_d [int];
    integer c_lastbank = 0;
    // WFC: pending sw ops (row, MARK = doorbell with payload) / sr pairs
    integer wj_row [$]; integer wj_pay [$];
    integer rj [$];
    integer w_lastbank = 0, r_lastrow = 0;
    // ARM / region flow
    integer slot_busy [0:3]; integer slot_tag [0:3], slot_base [0:3], slot_n [0:3], slot_ntf [0:3], slot_user [0:3];
    integer reg_ptr = 1024;
    integer tag_ctr = 1;
    integer cmd_q [$]; reg [83:0] cmd_d [$];
    integer pend_tag [$];          // tags we wait for
    integer n_arm = 0, n_p2rd = 0, n_done = 0, n_p2_out = 0;
    integer p2tags [$];
    integer p5_lastbank = 0;
    integer pool_p2_busy = 0;
    // ctrl / X pinned ops of the last 2 edges (for the projection)
    integer xc_m1 [$], xc_m2 [$];
    integer k, j, r, g, n, bb;
    reg [83:0] c;
    // ---- projection of the order-register ops of the next three edges for the gate
    task automatic proj(output integer o0 [$], output integer o1 [$], output integer o2 [$]);
        integer pr; begin
            o0.delete(); o1.delete(); o2.delete();
            // b(k): sources now
            if (dut.u_fe.e_v && !dut.u_fe.e_row[14]) o0.push_back(dut.u_fe.e_row[13:0]);
            if (dut.u_fe.e1_v) o0.push_back(dut.u_fe.e1_row[13:0]);
            if (dut.u_fe.c_v) o0.push_back(dut.u_fe.c_d[541:528]);
            if (dut.u_fe.r_iss) o0.push_back(dut.u_fe.r_base + dut.u_fe.r_w);
            foreach (xc_m2[j]) o0.push_back(xc_m2[j]);
            // b(k+1)
            if (dut.u_fe.u_wfc.p_v[1] && !dut.u_fe.u_wfc.p_mk[1]) o1.push_back(dut.u_fe.u_wfc.p_row[1][13:0]);
            if (dut.u_fe.u_wfc.p_v1[1]) o1.push_back(dut.u_fe.u_wfc.p_row1[1][13:0]);
            if (dut.u_fe.u_cw.g_rtt.u_rx.pv && dut.u_fe.u_cw.g_rtt.u_rx.live) o1.push_back(dut.u_fe.u_cw.g_rtt.u_rx.pd[541:528]);
            foreach (xc_m1[j]) o1.push_back(xc_m1[j]);
            // b(k+2)
            if (dut.u_fe.u_wfc.p_v[0] && !dut.u_fe.u_wfc.p_mk[0]) o2.push_back(dut.u_fe.u_wfc.p_row[0][13:0]);
            if (dut.u_fe.u_wfc.p_v1[0]) o2.push_back(dut.u_fe.u_wfc.p_row1[0][13:0]);
            if (p_cwv) o2.push_back(p_cwd[541:528]);
            // P2 reader: conservative (any of its next rows / the next command's base, in both later cycles)
            if (dut.u_fe.r_act || dut.u_fe.cq_n != 0) begin
                pr = dut.u_fe.r_base + dut.u_fe.r_w;
                o1.push_back(pr + 1); o2.push_back(pr + 1); o2.push_back(pr + 2); o1.push_back(pr);
                if (dut.u_fe.cq_n != 0) begin
                    o1.push_back(dut.u_fe.cq[dut.u_fe.cq_h][38:25]); o2.push_back(dut.u_fe.cq[dut.u_fe.cq_h][38:25]);
                    o2.push_back(dut.u_fe.cq[dut.u_fe.cq_h][38:25] + 1);
                end
            end
        end
    endtask
    function automatic integer fits(input integer o0 [$], input integer o1 [$], input integer o2 [$]);
        integer occ [0:NB-1]; integer b, f; begin
            for (b = 0; b < NB; b = b + 1) occ[b] = occ_m[b];
            f = step_mirror(occ, o0); if (f) return 0;
            f = step_mirror(occ, o1); if (f) return 0;
            f = step_mirror(occ, o2); fits = !f;
        end
    endfunction
    function automatic integer bank_row(input integer base, input integer span, input integer bank);
        // a row in [base, base + span) with the given bank (span a multiple of 32)
        begin bank_row = base + ((rnd(7) % (span / 32)) * 32) + bank; end
    endfunction

    // throughput bookkeeping
    integer tp_t0 = -1, tp_t1 = -1, tp_cap_t1 = -1, tp_p2_t1 = -1, tp_wfc_t1 = -1, tp_x_t1 = -1;
    integer tp_xn = 0;

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 6) rst_n <= 1'b1;
        if (rst_n && cyc > 4) begin observe_b(); check_returns(); end
        if (rst_n && cyc > 8) begin
            // ---------------- capture link sender
            if (s_cv && s_cr) s_cv <= 1'b0;
            if ((!s_cv || s_cr) && cj_row.size() != 0) begin
                if (cj_gap[0] > 0) cj_gap[0] = cj_gap[0] - 1;
                else begin
                    r = cj_row.pop_front(); void'(cj_gap.pop_front());
                    g = rnd(1);
                    s_cv <= 1'b1; s_cd <= {r[13:0], (MODE == 1 || g[3] || r >= 1024) ? 16'hffff : g[31:16], rowdata(mix(r, cyc))};
                    if (r >= 1024) fill_d[r] = rowdata(mix(r, cyc));
                    sb_c.push_back(r);
                end
            end
            // ---------------- WFC kit senders
            if (s_wv && s_wr) s_wv <= 1'b0;
            if ((!s_wv || s_wr) && wj_row.size() != 0) begin
                r = wj_row.pop_front(); g = wj_pay.pop_front();
                s_wv <= 1'b1;
                if (r == MARK) begin
                    s_wd <= {15'h7fff, 460'd0, 20'd0, g[31:0]}; ks_pay.push_back(g); nw_sent_b4_db.push_back(n_wfc_w_seen + sb_w.size());
                end else begin s_wd <= {r[14:0], rowdata(mix(r, cyc + 77))}; sb_w.push_back(r); end
            end
            if (s_rv && s_rr) s_rv <= 1'b0;
            if ((!s_rv || s_rr) && rj.size() != 0) begin
                r = rj.pop_front();
                s_rv <= 1'b1; s_rd <= {r[16], 1'b0, r[30:17], 1'b0, r[13:0]};
                sb_r.push_back(r[16] ? (r & 32'h1ffff) | ((r >> 17) << 17) : (r & 32'hffff));
            end
            // ---------------- engine commands (one a cycle)
            cv <= 1'b0;
            if (cmd_d.size() != 0 && (cmd_d[0][83:80] != 4'd3 || n_p2_out < 4)) begin
                cv <= 1'b1; cd <= cmd_d[0];
                if (cmd_d[0][83:80] == 4'd3) n_p2_out = n_p2_out + 1;
                void'(cmd_d.pop_front());
            end
            // ---------------- grants of the P2 ep / MTP ep
            g = rnd(2);
            c_l0r <= (MODE == 1) ? 1'b1 : (g[2:0] != 0);
            c_wr <= g[5:4] != 0;
            // ---------------- done handling
            while (done_seen.size() != 0) begin
                r = done_seen.pop_front(); n_done = n_done + 1;
                begin : dh
                    integer f; f = -1;
                    foreach (pend_tag[j]) if (f < 0 && pend_tag[j] == r) f = j;
                    if (f < 0) begin $display("FAIL cyc %0d: done tag %0d not pending", cyc, r); nbad = nbad + 1; end
                    else pend_tag.delete(f);
                    f = -1;
                    foreach (p2tags[j]) if (f < 0 && p2tags[j] == r) f = j;
                    if (f >= 0) begin p2tags.delete(f); n_p2_out = n_p2_out - 1; end
                end
                for (k = 0; k < 4; k = k + 1) if (slot_busy[k] == 1 && slot_tag[k] == r) begin
                    // region complete: stream it to P2; the slot is free once its rows-ready (if any) went out
                    slot_busy[k] = slot_ntf[k] ? 2 : 0;
                    c = 84'd0; c[83:80] = 4'd2; c[79:6] = {rnd(3), rnd(4), r[9:0]}; cmd_d.push_back(c);
                    p2c_id.push_back(c[79:6]);
                    c = 84'd0; c[83:80] = 4'd3; c[79:66] = slot_base[k]; c[65:59] = slot_n[k] - 1; g = rnd(5);
                    c[58:50] = g[8:0]; c[49] = g[9]; c[7:0] = tag_ctr[7:0];
                    cmd_d.push_back(c); pend_tag.push_back(tag_ctr[7:0]); p2tags.push_back(tag_ctr[7:0]); tag_ctr = (tag_ctr % 250) + 1; n_p2rd = n_p2rd + 1;
                    p2c_base.push_back(slot_base[k]); p2c_nw.push_back(slot_n[k] - 1); p2c_ex.push_back(g[8:0]); p2c_sh.push_back(g[9]);
                    p2c_tag.push_back(c[7:0]);
                end
            end
            if (MODE == 0 && cyc < NCYC) begin
                // ---------------- new ARM region (every ~170 cycles, a free slot)
                g = rnd(10);
                begin : arm
                    integer fk; fk = -1;
                    for (k = 3; k >= 0; k = k - 1) if (slot_busy[k] == 0) fk = k;
                    if (g[8:0] < 10 && cj_row.size() < 8 && fk >= 0) begin
                        k = fk;
                        n = 8 + rnd(11) % 57;  // rows
                        if (reg_ptr + 160 > NROW) reg_ptr = 1024;
                        slot_base[k] = reg_ptr + ((c_lastbank + 1) % 32); reg_ptr = reg_ptr + 160;
                        slot_n[k] = n; slot_ntf[k] = g[9]; slot_user[k] = {tag_ctr[7:0], k[1:0]}; slot_tag[k] = tag_ctr[7:0];
                        c = 84'd0; c[83:80] = 4'd1; c[79:78] = k; c[77] = g[9]; c[76:67] = slot_user[k]; c[66:53] = slot_base[k];
                        c[52:38] = n; c[37:23] = n; c[7:0] = tag_ctr[7:0];
                        cmd_d.push_back(c); pend_tag.push_back(tag_ctr[7:0]); tag_ctr = (tag_ctr % 250) + 1; n_arm = n_arm + 1;
                        if (g[9]) rr_exp.push_back(slot_user[k]);
                        slot_busy[k] = 1;
                        if (EARLYC) begin
                            c = 84'd0; c[83:80] = 4'd3; c[79:66] = slot_base[k]; c[65:59] = n - 1; c[7:0] = 8'd251;
                            cmd_d.push_back(c);
                        end
                        // the fill: a few cycles after the ARM, rows in order, random gaps, the LAST row late
                        for (r = 0; r < n; r = r + 1) begin
                            cj_row.push_back(slot_base[k] + r);
                            cj_gap.push_back(r == 0 ? 6 : r == n - 1 ? 10 + rnd(12) % 40 : (rnd(13) % 4 == 0 ? rnd(14) % 6 : 0));
                        end
                        c_lastbank = (slot_base[k] + n - 1) % 32;
                    end
                end
                // ---------------- pool capture bursts (unarmed: hazards with every reader)
                g = rnd(15);
                if (g[5:0] == 0 && cj_row.size() < 4) begin
                    n = 2 + g[10:8];
                    r = bank_row(0, POOL, (c_lastbank + 1) % 32);
                    for (j = 0; j < n; j = j + 1) begin
                        cj_row.push_back((r + j) % POOL); cj_gap.push_back(0);
                    end
                    c_lastbank = (r + n - 1) % 32;
                end
                // ---------------- WFC: writes + doorbell in the pool, read pairs
                g = rnd(16);
                if (g[6:0] == 0 && wj_row.size() < 4) begin
                    n = 1 + g[10:8];
                    r = bank_row(0, POOL, (w_lastbank + 1) % 32);
                    for (j = 0; j < n; j = j + 1) begin wj_row.push_back((r + j) % POOL); wj_pay.push_back(0); end
                    w_lastbank = (r + n - 1) % 32;
                    wj_row.push_back(MARK); wj_pay.push_back(rnd(17));
                end
                if (g[13:11] == 0 && rj.size() < 4) begin
                    r_lastrow = (r_lastrow + 2) % POOL;
                    rj.push_back(r_lastrow | (g[14] << 16) | (((r_lastrow + 1) % POOL) << 17));
                end
                // ---------------- P2 stream over pool rows (unarmed)
                if (g[20:16] == 0 && dut.u_fe.cq_n == 0 && cmd_d.size() == 0 && p2c_base.size() == 0) begin
                    n = 1 + g[24:22];
                    r = bank_row(0, POOL, (p5_lastbank + 1) % 32);
                    c = 84'd0; c[83:80] = 4'd2; c[79:6] = {rnd(18), rnd(19), 10'h3ff}; cmd_d.push_back(c); p2c_id.push_back(c[79:6]);
                    c = 84'd0; c[83:80] = 4'd3; c[79:66] = r; c[65:59] = n - 1; c[58:50] = 9'h1a5; c[49] = 1'b1; c[7:0] = tag_ctr[7:0];
                    cmd_d.push_back(c); pend_tag.push_back(tag_ctr[7:0]); p2tags.push_back(tag_ctr[7:0]); tag_ctr = (tag_ctr % 250) + 1; n_p2rd = n_p2rd + 1;
                    p2c_base.push_back(r); p2c_nw.push_back(n - 1); p2c_ex.push_back(9'h1a5); p2c_sh.push_back(1); p2c_tag.push_back(c[7:0]);
                    p5_lastbank = (r + n - 1) % 32;
                end
                // ---------------- ctrl + X random over the pool, gated by the projected bank mirror
                begin : gate
                    integer o0 [$], o1 [$], o2 [$]; integer cand_p [4], cand_r [4], cand_w [4]; integer nk;
                    reg [31:0] gx;
                    proj(o0, o1, o2);
                    vwe <= 1'b0; vre <= 1'b0; x_v <= 2'b00;
                    xc_m2 = xc_m1; xc_m1.delete();
                    for (nk = 0; nk < 4; nk = nk + 1) begin
                        gx = rnd(20 + nk);
                        if (gx[1:0] != 0) begin
                            cand_p[nk] = (nk == 0) ? 3 : (nk == 1) ? 4 : (nk == 2) ? 6 : 7;
                            cand_r[nk] = gx[13:8] % POOL;
                            cand_w[nk] = (nk == 0) ? 1 : (nk == 1) ? 0 : gx[2];
                            o2.push_back(cand_r[nk]);
                            if (!fits(o0, o1, o2)) void'(o2.pop_back());
                            else begin
                                xc_m1.push_back(cand_r[nk]);
                                sb_x.push_back(cand_p[nk] << 20 | cand_r[nk] << 1 | cand_w[nk]);
                                case (nk)
                                    0: begin vwe <= 1'b1; vwa <= cand_r[nk]; vwd <= rowdata(mix(gx, cyc)); end
                                    1: begin vre <= 1'b1; vra <= cand_r[nk]; end
                                    2: begin x_v[0] <= 1'b1; x_we[0] <= cand_w[nk]; x_row[13:0] <= cand_r[nk];
                                             x_mask[15:0] <= gx[3] ? 16'hffff : gx[31:16]; x_d[511:0] <= rowdata(mix(gx, cyc + 5)); end
                                    3: begin x_v[1] <= 1'b1; x_we[1] <= cand_w[nk]; x_row[27:14] <= cand_r[nk];
                                             x_mask[31:16] <= gx[3] ? 16'hffff : gx[31:16]; x_d[1023:512] <= rowdata(mix(gx, cyc + 9)); end
                                endcase
                            end
                        end
                    end
                end
            end else if (MODE == 0) begin
                vwe <= 1'b0; vre <= 1'b0; x_v <= 2'b00; xc_m2 = xc_m1; xc_m1.delete();
            end else if (MODE == 1) begin
                // ---------------- THROUGHPUT: production-shaped concurrent streams from cycle 200
                //  capture : TP_ROWS posted row writes back to back (one ARMed region), done measured
                //  P2      : after the done, P2RD of the region (TP_ROWS <= 128 words) at full grant rate
                //  WFC     : 46-word outbound prefetch = 23 RD2 read pairs (vmx done path), plus 46 inbound writes
                //  X0 / X1 : SU-style unit-stride read streams of TP_ROWS rows each
                vwe <= 1'b0; vre <= 1'b0; x_v <= 2'b00; xc_m2 = xc_m1; xc_m1.delete();
                if (cyc == 200) begin
                    tp_t0 = cyc;
                    c = 84'd0; c[83:80] = 4'd1; c[79:78] = 0; c[77] = 1; c[76:67] = 10'd5; c[66:53] = 14'd2048;
                    c[52:38] = TP_ROWS; c[37:23] = TP_ROWS; c[7:0] = 8'd200;
                    cmd_d.push_back(c); pend_tag.push_back(200); rr_exp.push_back(5);
                    slot_busy[0] = 1; slot_tag[0] = 200; slot_base[0] = 2048; slot_n[0] = TP_ROWS;
                    for (r = 0; r < TP_ROWS; r = r + 1) begin cj_row.push_back(2048 + r); cj_gap.push_back(r == 0 ? 4 : 0); end
                    for (r = 0; r < 46; r = r + 1) begin wj_row.push_back(4096 + r); wj_pay.push_back(0); end
                    for (r = 0; r < 23; r = r + 1) rj.push_back((6144 + 2 * r) | (1 << 16) | ((6145 + 2 * r) << 17));
                end
                if (tp_t0 > 0 && cyc >= tp_t0 + 2 && tp_xn < TP_ROWS) begin
                    // X streams: rows 8192 + i (X0) and 10240 + i + 16 (X1, another bank phase), reads
                    x_v <= 2'b11; x_we <= 2'b00; x_row <= {14'd10256 + tp_xn[13:0], 14'd8192 + tp_xn[13:0]};
                    sb_x.push_back(6 << 20 | (8192 + tp_xn) << 1); sb_x.push_back(7 << 20 | (10256 + tp_xn) << 1);
                    tp_xn = tp_xn + 1;
                end
            end
            // completion detection for throughput
            if (MODE == 1) begin
                if (tp_cap_t1 < 0 && slot_busy[0] == 0 && tp_t0 > 0) tp_cap_t1 = cyc;
                if (tp_p2_t1 < 0 && tp_cap_t1 > 0 && p2c_base.size() == 0 && pend_tag.size() == 0) tp_p2_t1 = cyc;
                if (tp_wfc_t1 < 0 && tp_t0 > 0 && cyc > tp_t0 + 10 && sb_r.size() == 0 && rj.size() == 0 && !s_rv && ex_q[0].size() == 0 && ex_q[1].size() == 0) tp_wfc_t1 = cyc;
                if (tp_x_t1 < 0 && tp_xn == TP_ROWS && ex_q[6].size() == 0 && ex_q[7].size() == 0 && sb_x.size() == 0) tp_x_t1 = cyc;
            end
        end
        // ---------------- end
        if (cyc == NCYC + 4000 || (MODE == 1 && tp_p2_t1 > 0 && tp_wfc_t1 > 0 && tp_x_t1 > 0 && cyc > tp_p2_t1 + 40)) begin
            for (p = 0; p < NP; p = p + 1) if (ex_q[p].size() != 0) begin $display("FAIL: %0d reads outstanding on port %0d", ex_q[p].size(), p); nbad = nbad + 1; end
            if (sb_c.size() || sb_w.size() || sb_r.size() || sb_x.size() || cj_row.size() || wj_row.size() || rj.size()) begin
                $display("FAIL: scoreboards not drained (capture %0d / %0d, wfc w %0d r %0d, x %0d)", sb_c.size(), cj_row.size(), sb_w.size(), sb_r.size(), sb_x.size()); nbad = nbad + 1;
            end
            if (pend_tag.size() != 0) begin $display("FAIL: %0d engine dones never arrived (first tag %0d)", pend_tag.size(), pend_tag[0]); nbad = nbad + 1; end
            if (rr_exp.size() != 0) begin $display("FAIL: %0d rows-ready missing", rr_exp.size()); nbad = nbad + 1; end
            if (ks_pay.size() != 0) begin $display("FAIL: %0d START doorbells missing", ks_pay.size()); nbad = nbad + 1; end
            if (dut.u_fe.fe_flt != 0 || fvec != 0 || flt) begin $display("FAIL: fault fe_flt %b fvec %b", dut.u_fe.fe_flt, fvec); nbad = nbad + 1; end
            if (ovf_m != 0) begin $display("FAIL: stimulus broke the stall-free contract %0d times", ovf_m); nbad = nbad + 1; end
            $display("RESULT cyc=%0d checked=%0d mismatches_or_fails=%0d arm=%0d p2rd=%0d done=%0d rows_ready=%0d starts=%0d p2_words=%0d max_occ=%0d mirror_max=%0d lat p0=%0d p1=%0d p4=%0d p6=%0d p7=%0d",
                     cyc, nchk, nbad, n_arm, n_p2rd, n_done, n_rr, ks_seen, p2_words_seen, max_occ, maxocc_m, lat[0], lat[1], lat[4], lat[6], lat[7]);
            if (MODE == 1)
                $display("THROUGHPUT rows=%0d capture_done=%0d p2_done=%0d (from capture done %0d) wfc_23pairs=%0d x_streams=%0d (cycles from t0 %0d)",
                         TP_ROWS, tp_cap_t1 - tp_t0, tp_p2_t1 - tp_t0, tp_p2_t1 - tp_cap_t1, tp_wfc_t1 - tp_t0, tp_x_t1 - tp_t0, tp_t0);
            if (nbad == 0 && nchk > 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
    initial begin
        for (k = 0; k < 8; k = k + 1) lat[k] = -1;
        for (k = 0; k < 4; k = k + 1) slot_busy[k] = 0;
        rs = SEED * 32'h2545f491 + 1;
    end
    // early-read and fault visibility (the RTL fault is checked at the end; print the first occurrence)
    reg flt_seen = 0;
    always @(posedge clk) if (!flt_seen && rst_n && (dut.u_fe.fe_flt != 0 || fvec != 0)) begin
        flt_seen <= 1; $display("FAULT first at cyc %0d: fe_flt %b fvec %b", cyc, dut.u_fe.fe_flt, fvec);
    end
endmodule
