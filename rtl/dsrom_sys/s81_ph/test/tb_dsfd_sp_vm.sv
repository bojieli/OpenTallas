`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_dsfd_sp_vm v2 -- exact gate, burst stress and throughput bench of the S81 VM master dsfd_sp_vm_m
// (s81-vm-1011, 2026-10-11): FE (dsfd_vm_fe), 4 x 4 CLOSED-design dsfd_vm_bgq tiles (NSTG 2, NP 24, NPR 8, real SRAM
// macro models) and BE (dsfd_vm_be).  Clocks on the 3.6 GHz VCO grid: serial ck = VCO/4, stream cks = VCO/3.
//
// Clients (all at the master's pins):
//   capture   : the dsfd_sp_capture t_vm face: 128 roots, each <= 2 elements a serial cycle at <= 4/3 a cycle (one row a
//               stream cycle), S81 profile (root r owns rows 2r, 2r+1 mod 256), address obase + row + pos * ops; phases
//               ARMed (ARMB / ARMR / ARMN through the engine adapter), then read back (P2RD / X0) and checked.
//   WFC kit   : ltx senders on the sw (writes + START doorbell) / sr (RD2 read pairs) links, VF / VR stations.
//   ctrl      : dsfd_sp_ctrl VM write / read port (stream domain), read data via vrv / vrq; engine commands cv / cd.
//   P2 lane 0 : dsfd_vm_p2_ep core side (c_l0r random grants), every flit's data and metadata checked.
//   X0 .. X2  : random reads / writes over a row pool (hazards with every client).
//   MTP       : rows-ready (c_wr random), checked against the notify slots.
// Reference: a 16,384 x 512 b array updated at the FE order register (u_fe.b_*) in (cycle, port) order; every read's
// expected row is taken there and compared at its return port.  Capture: every element must reach the order register
// exactly once with its data (no drop, no duplicate); every region read after its done must hold the phase's elements.
// PASS needs 0 mismatches, every scoreboard drained, every done, fe_flt = 0, fvec = 0, constant latency per port.
// MODE 0 gate (random), MODE 1 throughput (production-shaped concurrent streams), MODE 2 burst stress (all 128 roots
// back to back at the root rate, BROWS rows a root, BNP + 1 positions), MODE 3 misaligned phase (the DUT must flag
// the alignment fault: PASS = fault raised and nothing else wrong).
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
    parameter integer BANK_XOR = 0;
    parameter integer SEED = 1;
    parameter integer NCYC = 60000;
    parameter integer MODE = 0;
    parameter integer VF = 13, VR = 13, P2D = 40;
    parameter integer TP_ROWS = 56;          // throughput: rows per root of the capture phase
    // XCH (claude s81-grpA r3): MODE 1 adds a DEPENDENT X read of the captured region (X2, bus lane 2, XCH rows from row
    // 2048) -- the consumer of the capture slot.  XGOS 0: issued when the slot's ARMN done arrives (today's controller
    // contract); XGOS 1: issued right after the ARMN as an XGO armed on slot 0 (RTL define OT_SPVM_XGOS).  Prints XCHAIN.
    parameter integer XCH = 0;
    parameter integer XGOS = 0;
    parameter integer BROWS = 128;           // burst: rows per root
    parameter integer BNP = 0;               // burst: positions - 1
    parameter integer BSKEW = 3;             // burst: max start skew between roots (serial cycles)
    parameter integer EARLYC = 0;
    parameter integer LA = 12;              // capture lane row entries (DUT)            // negative control: read a region right after its ARMN (before done)
    parameter integer NSVC = 1;
    parameter integer LBP = 0;              // MODE 4 back-pressure: the collective offers 4 words EVERY cycle (1,024 words) so its
                                            // lanes fill past the room threshold and t_cts[0] must drop (and hold the producer)
    localparam integer QD = 4, NB = 32, NP = 28, NROW = 16384, POOL = 64, MARK = 32767, NR = 128, CP = 12;

    reg clk = 0, cks = 0;
    always #2 clk = ~clk;                    // serial, period 4 (VCO / 4)
    always #1.5 cks = ~cks;                  // stream, period 3 (VCO / 3)
    reg rst_n = 0, rss_n = 0;
    integer cyc = 0;
    // ------------------------------------------------------------ DUT
    wire t_swg, t_srg, t_err, vrv, dv, c_wv, c_l0v; wire [52:0] t_ks; wire [1025:0] t_srq; wire [511:0] vrq;
    wire [7:0] dt; wire [16*513-1:0] t_bl; wire [2:0] t_cts; wire [9:0] c_wd; wire [603:0] c_l0d; wire flt; wire [31:0] fvec;
    wire [2:0] max_occ; wire [3:0] t_rdy;
    wire p_swv, p_srv; wire [526:0] p_swd; wire [30:0] p_srd;
    reg vwe = 0, vre = 0, cv = 0, c_wr = 0, c_l0r = 0; reg [13:0] vwa = 0, vra = 0; reg [511:0] vwd = 0; reg [83:0] cd = 0;
    reg [NSVC*1027-1:0] f_svc = 0; reg [2099:0] f_coll = 0; reg [514:0] f_sel = 0, f_col = 0; reg [1025:0] f_hc = 0;
    reg [13375:0] f_cap = 0;
    dsfd_sp_vm_m #(.BANK_XOR(BANK_XOR), .MACRO(1), .VF(VF), .VR(VR), .P2D(P2D), .LA(LA), .NSVC(NSVC)) dut (
        .ck(clk), .rst(rst_n), .cks(cks), .rss(rss_n),
        .f_swv(p_swv), .f_swd(p_swd), .t_swg(t_swg), .f_srv(p_srv), .f_srd(p_srd), .t_srg(t_srg),
        .t_ks(t_ks), .t_srq(t_srq), .t_err(t_err), .f_cap(f_cap),
        .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra), .vrv(vrv), .vrq(vrq), .cv(cv), .cd(cd), .dv(dv), .dt(dt),
        .f_svc(f_svc), .f_coll(f_coll), .t_cts(t_cts), .f_sel(f_sel), .f_col(f_col), .f_hc(f_hc), .t_bl(t_bl),
        .c_wv(c_wv), .c_wd(c_wd), .c_wr(c_wr), .t_rdy(t_rdy), .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(c_l0r),
        .flt(flt), .fvec(fvec), .max_occ(max_occ));
    // ------------------------------------------------------------ WFC link senders (ltx) + relay stations
    reg s_wv = 0, s_rv = 0; reg [526:0] s_wd = 0; reg [30:0] s_rd = 0;
    wire s_wr, s_rr; wire k_swv, k_srv, g_sw, g_sr; wire [526:0] k_swd; wire [30:0] k_srd;
    ot_dsrom_mtp_ltx #(.W(527)) x_sw (.clk(clk), .rst_n(rst_n), .c_valid(s_wv), .c_ready(s_wr), .c_data(s_wd), .l_valid(k_swv), .l_ready(g_sw), .l_data(k_swd));
    ot_dsrom_mtp_ltx #(.W(31))  x_sr (.clk(clk), .rst_n(rst_n), .c_valid(s_rv), .c_ready(s_rr), .c_data(s_rd), .l_valid(k_srv), .l_ready(g_sr), .l_data(k_srd));
    tb_spvm_relay #(.W(528), .N(VF)) r1 (.clk(clk), .d({k_swv, k_swd}), .q({p_swv, p_swd}));
    tb_spvm_relay #(.W(1),   .N(VR)) r2 (.clk(clk), .d(t_swg), .q(g_sw));
    tb_spvm_relay #(.W(32),  .N(VF)) r3 (.clk(clk), .d({k_srv, k_srd}), .q({p_srv, p_srd}));
    tb_spvm_relay #(.W(1),   .N(VR)) r4 (.clk(clk), .d(t_srg), .q(g_sr));

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
    reg [511:0] ex_q [0:7][$];
    integer ex_t [0:7][$];
    integer lat [0:7]; integer nchk = 0, nbad = 0;
    integer sb_w [$], sb_r [$], sb_x [$], nw_sent_b4_db [$], ks_pay [$];
    integer n_wfc_w_seen = 0;
    // capture: expected elements of the live phases, landed set
    reg [31:0] exp_el [int];
    bit landed [int];
    integer n_el_exp = 0, n_el_land = 0;
    // ctrl: ops sent (stream side) in order {we, row}; read expectations come from the order register
    integer sb_c [$];
    integer ctrl_inflight = 0;
    integer occ_m [0:NB-1]; integer ovf_m = 0, maxocc_m = 0;
    integer bi; initial for (bi = 0; bi < NB; bi = bi + 1) occ_m[bi] = 0;

    // ------------------------------------------------------------ observe the order register
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

    integer p, e, rw, a; reg [511:0] old, nd, mk;
    integer obs_rows [$];
    integer done_seen [$];
    integer p2_words_seen = 0;
    integer cap_ops = 0, cap_first = -1, cap_last = -1, lan_ops = 0, lan_first = -1, lan_last = -1;
    reg [511:0] ex_l [0:15][$]; integer ex_lt [0:15][$]; integer lat_l [0:15];
    integer xs_row [0:4][$];                 // rows each X streamer will read, in order
    function automatic integer xidx(input integer pp);
        begin xidx = (pp == 6) ? 0 : (pp == 7) ? 1 : (pp == 2) ? 2 : (pp == 8) ? 3 : 4; end
    endfunction
    task automatic observe_b();
        obs_rows.delete();
        for (p = 0; p < NP; p = p + 1) if (b_v[p]) begin
            rw = b_row[p*14 +: 14];
            obs_rows.push_back(rw);
            if (b_we[p]) begin
                old = gm[rw]; nd = b_d[p*512 +: 512];
                for (e = 0; e < 16; e = e + 1) mk[32*e +: 32] = {32{b_m[p*16 + e]}};
`ifdef OT_SPVM_SLOC
                // capture lane (FE (a)): virtual slot e of lane g = actual word 4 (g / 4) + (e % 4) of row {key, g % 4, e / 4}
                if (p >= CP) begin
                    for (e = 0; e < 16; e = e + 1) if (b_m[p*16 + e])
                        gm[(rw / 16) * 16 + 4 * ((p - CP) % 4) + e / 4][32 * (4 * ((p - CP) / 4) + e % 4) +: 32] = nd[32*e +: 32];
                end else
`endif
                gm[rw] = (old & ~mk) | (nd & mk);
            end else if (p == 2 || p >= 6 && p <= 9) begin
                // X streamer read: expected at its bus lane (id in the data field)
                ex_l[b_d[p*512 +: 4]].push_back(gm[rw]); ex_lt[b_d[p*512 +: 4]].push_back(cyc);
                if (p == 2 && xch_first < 0) xch_first = cyc;
                if (xs_row[xidx(p)].size() == 0 || xs_row[xidx(p)][0] != rw) begin
                    $display("FAIL cyc %0d: X port %0d read row %0d not the next streamed", cyc, p, rw); nbad = nbad + 1;
                end else void'(xs_row[xidx(p)].pop_front());
            end else if (p < 10) begin
                ex_q[p].push_back(gm[rw]); ex_t[p].push_back(cyc);
            end else begin
                $display("FAIL cyc %0d: read op on capture port %0d", cyc, p); nbad = nbad + 1;
            end
            if (p >= 10) begin
                if (p >= CP) begin cap_ops = cap_ops + 1; if (cap_first < 0) cap_first = cyc; cap_last = cyc; end
                else begin lan_ops = lan_ops + 1; if (lan_first < 0) lan_first = cyc; lan_last = cyc; end
                if (p >= CP && rw % 16 != p - CP) begin $display("FAIL cyc %0d: capture lane %0d wrote row %0d", cyc, p - CP, rw); nbad = nbad + 1; end
                for (e = 0; e < 16; e = e + 1) if (b_m[p*16 + e]) begin
`ifdef OT_SPVM_SLOC
                    a = (p >= CP) ? ((rw / 16) * 16 + 4 * ((p - CP) % 4) + e / 4) * 16 + 4 * ((p - CP) / 4) + e % 4 : rw * 16 + e;
`else
                    a = rw * 16 + e;
`endif
                    if (!exp_el.exists(a)) begin $display("FAIL cyc %0d: capture element %0d not expected", cyc, a); nbad = nbad + 1; end
                    else if (landed.exists(a)) begin $display("FAIL cyc %0d: capture element %0d written twice", cyc, a); nbad = nbad + 1; end
                    else begin
                        landed[a] = 1; n_el_land = n_el_land + 1;
                        if (nd[32*e +: 32] !== exp_el[a]) begin
                            nbad = nbad + 1; if (nbad < 12) $display("MISMATCH cyc %0d capture element %0d", cyc, a);
                        end
                    end
                end
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
            if (p == 3 || p == 4) begin    // ctrl lanes: in send order (lane A before lane B in a cycle)
                if (sb_c.size() == 0 || sb_c[0] != (rw << 1 | b_we[p])) begin
                    $display("FAIL cyc %0d: ctrl op (port %0d row %0d we %0d) not the next sent (exp %0d of %0d)", cyc, p, rw, b_we[p], sb_c.size() ? sb_c[0] : -1, sb_c.size()); nbad = nbad + 1;
                end else begin void'(sb_c.pop_front()); ctrl_inflight = ctrl_inflight - 1; end
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
    task automatic chk(input integer pp, input [511:0] got, input integer fixed);
        reg [511:0] w; integer t; begin
            if (ex_q[pp].size() == 0) begin $display("FAIL cyc %0d: unexpected read data on port %0d", cyc, pp); nbad = nbad + 1; end
            else begin
                w = ex_q[pp].pop_front(); t = ex_t[pp].pop_front(); nchk = nchk + 1;
                if (fixed) begin
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
    // a region read back after its done must hold the phase's elements (catches early / stale)
    task automatic chk_region(input integer row, input [511:0 ] got);
        integer ee, aa; begin
            for (ee = 0; ee < 16; ee = ee + 1) begin
                aa = row * 16 + ee;
                if (exp_el.exists(aa) && got[32*ee +: 32] !== exp_el[aa]) begin
                    nbad = nbad + 1;
                    if (nbad < 12) $display("FAIL cyc %0d: region row %0d element %0d not the captured value (early / stale read)", cyc, row, ee);
                end
            end
        end
    endtask
    integer p2c_base [$], p2c_nw [$], p2c_ex [$], p2c_sh [$], p2c_tag [$], p2c_chk [$]; reg [73:0] p2c_id [$];
    integer p2_w = 0;
    localparam integer P2RL = 4; reg [7:0] rdh = 8'd0;     // c_l0r history (ready latency of the BE P2 port)
    integer rr_exp [$];
    integer n_rr = 0, ks_seen = 0;
    integer x0_chk [$];                     // X0 reads that are region checks: row, or -1
    // ctrl read return (stream domain): expectations in order
    task automatic check_returns();
        if (t_srq[512]) chk(0, t_srq[511:0], 1);
        if (t_srq[1025]) chk(1, t_srq[1024:513], 1);
        for (integer bl = 0; bl < 16; bl = bl + 1) if (t_bl[513*bl]) begin
            if (ex_l[bl].size() == 0) begin $display("FAIL cyc %0d: unexpected row on bus lane %0d", cyc, bl); nbad = nbad + 1; end
            else begin
                nchk = nchk + 1;
                if (lat_l[bl] < 0) lat_l[bl] = cyc - ex_lt[bl][0];
                else if (lat_l[bl] != cyc - ex_lt[bl][0]) begin $display("FAIL cyc %0d: lane %0d latency", cyc, bl); nbad = nbad + 1; end
                if (ex_l[bl][0] !== t_bl[513*bl + 1 +: 512]) begin nbad = nbad + 1; if (nbad < 12) $display("MISMATCH cyc %0d bus lane %0d", cyc, bl); end
                void'(ex_l[bl].pop_front()); void'(ex_lt[bl].pop_front());
            end
        end
        // P2 port is READY-LATENCY P2RL (BE S-FACE CONTRACT v3): every c_l0v beat is a transfer and needs c_l0r P2RL cycles earlier
        if (c_l0v && !rdh[P2RL-1]) begin $display("FAIL cyc %0d: P2 beat without ready %0d cycles earlier", cyc, P2RL); nbad = nbad + 1; end
        if (c_l0v) begin
            chk(5, c_l0d[511:0], 0);
            p2_words_seen = p2_words_seen + 1;
            if (p2c_base.size() == 0) begin $display("FAIL cyc %0d: P2 flit without a command", cyc); nbad = nbad + 1; end
            else begin
                if (c_l0d[603:530] !== p2c_id[0] || c_l0d[529:521] != p2c_ex[0] || c_l0d[520] != p2c_sh[0] ||
                     c_l0d[519] != (p2_w == p2c_nw[0]) || c_l0d[518:512] != p2_w) begin
                    $display("FAIL cyc %0d: P2 flit metadata (word %0d / %0d)", cyc, c_l0d[518:512], p2_w); nbad = nbad + 1;
                end
                if (p2c_chk[0]) chk_region(p2c_base[0] + p2_w, c_l0d[511:0]);
                if (p2_w == p2c_nw[0]) begin
                    p2_w = 0; void'(p2c_base.pop_front()); void'(p2c_nw.pop_front()); void'(p2c_ex.pop_front());
                    void'(p2c_sh.pop_front()); void'(p2c_id.pop_front()); void'(p2c_tag.pop_front()); void'(p2c_chk.pop_front());
                end else p2_w = p2_w + 1;
            end
        end
        if (t_ks[52]) begin
            ks_seen = ks_seen + 1;
            if (ks_pay.size() == 0 || ks_pay[0] != t_ks[31:0]) begin $display("FAIL cyc %0d: START payload", cyc); nbad = nbad + 1; end
            else void'(ks_pay.pop_front());
            if (nw_sent_b4_db.size() == 0 || n_wfc_w_seen < nw_sent_b4_db[0]) begin
                $display("FAIL cyc %0d: START before its writes were ordered", cyc); nbad = nbad + 1;
            end else void'(nw_sent_b4_db.pop_front());
        end
        if (c_wv && c_wr) begin
            begin : rrm
                integer f; f = -1;
                foreach (rr_exp[j]) if (f < 0 && rr_exp[j] == c_wd) f = j;
                if (f < 0) begin $display("FAIL cyc %0d: rows-ready user %0d not expected", cyc, c_wd); nbad = nbad + 1; end
                else rr_exp.delete(f);
                n_rr = n_rr + 1;
            end
        end
        rdh = {rdh[6:0], c_l0r};
    endtask
    integer n_cq = 0;
    reg [511:0] ex_q_c [$];
    always @(posedge cks) if (rss_n && vrv) begin
        if (ex_q_c.size() == 0) begin $display("FAIL: ctrl read data without a read"); nbad = nbad + 1; end
        else begin
            nchk = nchk + 1; n_cq = n_cq + 1;
            if (ex_q_c[0] !== vrq) begin nbad = nbad + 1; if (nbad < 12) $display("MISMATCH ctrl read %0d", n_cq); end
            void'(ex_q_c.pop_front());
        end
    end

    // ------------------------------------------------------------ capture source model
    // per root: queue of {addr, data}; emission <= 2 a serial cycle, <= 4/3 a cycle on average (credit in thirds)
    integer rq_a [0:NR-1][$]; reg [31:0] rq_d [0:NR-1][$];
    integer r_cr [0:NR-1], r_gap [0:NR-1], r_tail [0:NR-1];
    integer cap_pend = 0;               // elements not yet emitted
    integer cap_last_emit = -1, cap_first_emit = -1;
    integer rr, nn, kk2;
    reg [13375:0] fc;
    task automatic cap_step(input integer gaps);
        fc = '0;
        for (rr = 0; rr < NR; rr = rr + 1) begin
            r_cr[rr] = (r_cr[rr] + 4 > 6) ? 6 : r_cr[rr] + 4;
            if (r_gap[rr] > 0) r_gap[rr] = r_gap[rr] - 1;
            else begin
                nn = 0;
                if (rq_a[rr].size() == 1 && r_tail[rr] > 0) begin r_tail[rr] = r_tail[rr] - 1; nn = 2; end
                while (nn < 2 && r_cr[rr] >= 3 && rq_a[rr].size() != 0) begin
                    fc[104*rr + 52*nn] = 1'b1;
                    fc[104*rr + 52*nn + 1 +: 19] = rq_a[rr][0];
                    fc[104*rr + 52*nn + 20 +: 32] = rq_d[rr][0];
                    void'(rq_a[rr].pop_front()); void'(rq_d[rr].pop_front());
                    r_cr[rr] = r_cr[rr] - 3; nn = nn + 1; cap_pend = cap_pend - 1;
                    if (cap_first_emit < 0) cap_first_emit = cyc; cap_last_emit = cyc;
                end
                if (gaps && rnd(40 + rr) % 23 == 0) r_gap[rr] = rnd(41) % 3;
            end
        end
        f_cap <= fc;
    endtask
    // a phase: rows R a root, NPOS positions, obase / ops (elements); returns the element count
    function automatic integer cap_phase(input integer obase, input integer ops, input integer R, input integer npos,
                                         input integer skew, input integer reord, input integer salt);
        integer r_, j_, p_, addr, row, n_, tl_; reg [31:0] dd;
        begin
            n_ = 0;
            for (r_ = 0; r_ < NR; r_ = r_ + 1) begin
                r_gap[r_] = skew ? rnd(50) % (skew + 1) : 0;
                for (j_ = 0; j_ < R; j_ = j_ + 1) for (p_ = 0; p_ < npos; p_ = p_ + 1) begin
`ifdef OT_SPVM_SLOC
                    // VM FE (a) capture-slice locality (claude s81-grpA r5): root r = 8g + i of lane g (quadrant q = g / 4)
                    // writes only column slice q: row-in-block 4 (g % 4) + (i >> 1), word 4 q + 2 (i & 1) + b
                    row = 256 * (j_ >> 1) + 16 * (4 * ((r_ >> 3) % 4) + ((r_ % 8) >> 1)) + 4 * ((r_ >> 3) / 4) + 2 * ((r_ % 8) & 1) + (j_ & 1);
`else
                    row = 256 * (j_ >> 1) + 2 * r_ + (j_ & 1);
`endif
                    addr = obase + row + p_ * ops;
                    dd = mix(addr, salt);
                    rq_a[r_].push_back(addr); rq_d[r_].push_back(dd);
                    exp_el[addr] = dd; n_ = n_ + 1;
                    if (landed.exists(addr)) landed.delete(addr);
                end
                if (reord) for (j_ = 0; j_ + 1 < rq_a[r_].size(); j_ = j_ + 2) if (rnd(51) % 4 == 0) begin
                    addr = rq_a[r_][j_]; rq_a[r_][j_] = rq_a[r_][j_+1]; rq_a[r_][j_+1] = addr;
                    dd = rq_d[r_][j_]; rq_d[r_][j_] = rq_d[r_][j_+1]; rq_d[r_][j_+1] = dd;
                end
            end
            tl_ = rnd(52) % NR;                          // one rnd() call (an index side effect is evaluated twice by Verilator 5.032)
            if (MODE == 0) r_tail[tl_] = 60;      // one late last element a phase (an early done reads stale)
            cap_pend = cap_pend + n_; n_el_exp = n_el_exp + n_;
            cap_phase = n_;
        end
    endfunction

    // ------------------------------------------------------------ engine commands (stream side)
    // command word: {slot, user 10, pos 21, tok 21, arg 24, op 7}; the done tag {slot, op}
    reg [83:0] cmd_q [$];
    integer n_cmd_out = 0;           // adapter credits in use (<= 8)
    integer pend_tag [$];
    function automatic [83:0] vcmd(input [2:0] vop, input [20:0] f, input [9:0] user, input [7:0] tag);
        begin vcmd = 84'd0; vcmd[83] = tag[7]; vcmd[82:73] = user; vcmd[30:28] = vop; vcmd[27:7] = f; vcmd[6:0] = tag[6:0]; end
    endfunction
    integer tag_ctr = 1;
    function automatic integer tag_pending(input integer t);
        begin tag_pending = 0; foreach (pend_tag[j]) if (pend_tag[j] == t) tag_pending = 1; end
    endfunction
    function automatic [7:0] ntag(input integer d);
        begin
            // a tag not pending: 1 .. 250
            while (tag_pending(tag_ctr)) tag_ctr = (tag_ctr % 250) + 1;
            ntag = tag_ctr[7:0]; tag_ctr = (tag_ctr % 250) + 1;
        end
    endfunction
    // slots
    integer slot_busy [0:3]; integer slot_tag [0:3], slot_base [0:3], slot_n [0:3], slot_ntf [0:3], slot_user [0:3];
    integer slot_t_arm [0:3], slot_t_done [0:3];
    task automatic arm(input integer k, input integer base, input integer nrows, input integer nel, input integer ntf,
                       input integer user);
        reg [7:0] t;
        begin
            t = ntag(0); cmd_q.push_back(vcmd(3'd1, {k[1:0], ntf[0], 4'd0, base[13:0]}, 10'd0, t)); pend_tag.push_back(t);
            t = ntag(0); cmd_q.push_back(vcmd(3'd2, {k[1:0], 4'd0, nrows[14:0]}, 10'd0, t)); pend_tag.push_back(t);
            t = ntag(0); cmd_q.push_back(vcmd(3'd3, {k[1:0], nel[18:0]}, user[9:0], t)); pend_tag.push_back(t);
            slot_busy[k] = 1; slot_tag[k] = t; slot_base[k] = base; slot_n[k] = nrows; slot_ntf[k] = ntf; slot_user[k] = user;
            slot_t_arm[k] = cyc;
            if (ntf) rr_exp.push_back(user);
        end
    endtask
    task automatic p2rd(input integer base, input integer nw, input integer check);
        reg [7:0] t; reg [89:0] id; integer q; reg [31:0] r60, r61, r62;
        begin
            // one rnd() per statement: the evaluation order of side-effecting operands inside a concatenation is not
            // defined by IEEE 1800 (Verilator 5.032 and 5.050 differ -> different P2RD ids, the whole stimulus diverged)
            r60 = rnd(60); r61 = rnd(61); r62 = rnd(62);
            id = {r60, r61, r62};
            for (q = 0; q < 5; q = q + 1) begin t = ntag(0); cmd_q.push_back(vcmd(3'd4, {q[2:0], id[18*q +: 18]}, 10'd0, t)); pend_tag.push_back(t); end
            t = ntag(0); cmd_q.push_back(vcmd(3'd5, {base[13:0], nw[6:0] - 7'd1}, 10'd0, t)); pend_tag.push_back(t);
            p2c_base.push_back(base); p2c_nw.push_back(nw - 1); p2c_id.push_back(id[73:0]); p2c_ex.push_back(id[82:74]);
            p2c_sh.push_back(id[83]); p2c_tag.push_back(t); p2c_chk.push_back(check);
        end
    endtask
    // X streamer: map {lane, n} + go {base}; rows recorded for the order-register check
    integer x_busy [0:4], x_ln [0:4];
    task automatic xrd(input integer xp, input integer lane, input integer base, input integer n);
        reg [7:0] t; integer q;
        begin
            t = ntag(0); cmd_q.push_back(vcmd(3'd7, {xp[2:0], 1'b0, lane[3:0], n[12:0] - 13'd1}, 10'd0, t)); pend_tag.push_back(t);
            t = ntag(0); cmd_q.push_back(vcmd(3'd7, {xp[2:0], 1'b1, 3'd0, base[13:0]}, 10'd0, t)); pend_tag.push_back(t);
            for (q = 0; q < n; q = q + 1) xs_row[xp].push_back(base + q);
            x_busy[xp] = t; x_ln[xp] = lane;
        end
    endtask
    // X streamer armed on a producer slot (XGOS): go {xp, go 1, wait 1, slot, base}
    task automatic xrd_w(input integer xp, input integer lane, input integer base, input integer n, input integer slot);
        reg [7:0] t; integer q;
        begin
            t = ntag(0); cmd_q.push_back(vcmd(3'd7, {xp[2:0], 1'b0, lane[3:0], n[12:0] - 13'd1}, 10'd0, t)); pend_tag.push_back(t);
            t = ntag(0); cmd_q.push_back(vcmd(3'd7, {xp[2:0], 1'b1, 1'b1, slot[1:0], base[13:0]}, 10'd0, t)); pend_tag.push_back(t);
            for (q = 0; q < n; q = q + 1) xs_row[xp].push_back(base + q);
            x_busy[xp] = t; x_ln[xp] = lane;
        end
    endtask
    integer xch_go = -1, xch_first = -1;
    // landing producer pointer (LARM): group 0..3 svc, 4 coll, 5 sel, 6 col, 7 hc
    task automatic larm(input integer grp_, input integer base);
        reg [7:0] t; begin
            t = ntag(0); cmd_q.push_back(vcmd(3'd6, {grp_[3:0], 3'd0, base[13:0]}, 10'd0, t)); pend_tag.push_back(t);
        end
    endtask
    // landing producer sources: queues of rows (each row = 16 elements registered in exp_el)
    reg [511:0] lq_svc [$], lq_sel [$], lq_col [$], lq_hc [$], lq_coll [$];
    integer l_gap_col = 0, l_start = -1;
    function automatic [511:0] lrow(input integer row, input integer salt);
        integer ee; reg [511:0] r_; begin
            for (ee = 0; ee < 16; ee = ee + 1) begin
                r_[32*ee +: 32] = mix(row * 16 + ee, salt);
                exp_el[row * 16 + ee] = r_[32*ee +: 32];
                if (landed.exists(row * 16 + ee)) landed.delete(row * 16 + ee);
            end
            n_el_exp = n_el_exp + 16; lrow = r_;
        end
    endfunction
    integer l_pend = 0;                       // landing rows not yet sent
    task automatic lphase(input integer grp_, input integer k, input integer base, input integer nrows, input integer salt);
        integer q; begin
            larm(grp_, base);
            arm(k, base, nrows, nrows * 16, 0, 0);
            for (q = 0; q < nrows; q = q + 1) begin
                case (grp_)
                    0: lq_svc.push_back(lrow(base + q, salt));
                    4: lq_coll.push_back(lrow(base + q, salt));
                    5: lq_sel.push_back(lrow(base + q, salt));
                    6: lq_col.push_back(lrow(base + q, salt));
                    default: lq_hc.push_back(lrow(base + q, salt));
                endcase
            end
            l_pend = l_pend + nrows;
        end
    endtask
    always @(posedge cks) begin
        cv <= 1'b0;
        if (rss_n && cmd_q.size() != 0 && n_cmd_out < 8) begin
            cv <= 1'b1; cd <= cmd_q.pop_front(); n_cmd_out = n_cmd_out + 1;
        end
        if (dv) begin
            n_cmd_out = n_cmd_out - 1;
            done_seen.push_back(dt);
        end
    end
    // ------------------------------------------------------------ ctrl VM port (stream side)
    reg [13:0] cq_rows [$]; reg cq_we [$];   // ops to send
    integer c_gap = 0;
    always @(posedge cks) begin
        vwe <= 1'b0; vre <= 1'b0;
        if (rss_n && cyc > 60 && cq_rows.size() != 0) begin   // the controller starts after the VM is up
            if (c_gap > 0) c_gap = c_gap - 1;
            else begin : cs
                reg fw; fw = cq_we[0];
                if (cq_we[0]) begin vwe <= 1'b1; vwa <= cq_rows[0]; vwd <= rowdata(mix(cq_rows[0], $time)); end
                else begin vre <= 1'b1; vra <= cq_rows[0]; end
                sb_c.push_back(int'(cq_rows[0]) * 2 + int'(cq_we[0])); ctrl_inflight = ctrl_inflight + 1;
                void'(cq_rows.pop_front()); void'(cq_we.pop_front());
                // both ops in one stream cycle (write then read) sometimes
                if (fw && cq_rows.size() != 0 && !cq_we[0] && vwe_next_both()) begin
                    vre <= 1'b1; vra <= cq_rows[0]; sb_c.push_back(int'(cq_rows[0]) * 2); ctrl_inflight = ctrl_inflight + 1;
                    void'(cq_rows.pop_front()); void'(cq_we.pop_front());
                end
                c_gap = (MODE == 1) ? 0 : rnd(70) % 3;
            end
        end
    end
    reg both_ok = 0;
    function automatic bit vwe_next_both();
        begin vwe_next_both = both_ok; end
    endfunction

    // ------------------------------------------------------------ stimulus (serial domain)
    integer wj_row [$]; integer wj_pay [$]; integer rj [$];
    integer w_lastbank = 0, r_lastrow = 0, p5_lastbank = 0;
    integer reg_ptr = 1024;
    integer n_arm = 0, n_p2rd = 0, n_done = 0, n_phase = 0;
    integer xc_m1 [$], xc_m2 [$];
    integer k, j, r, g, n;
    integer x_win;                      // 1: X window, 0: ctrl window (stall-free admission in the bench)
    task automatic proj(output integer o0 [$], output integer o1 [$], output integer o2 [$]);
        integer pr, l2; begin
            o0.delete(); o1.delete(); o2.delete();
            if (dut.u_fe.e_v && !dut.u_fe.e_row[14]) o0.push_back(dut.u_fe.e_row[13:0]);
            if (dut.u_fe.e1_v) o0.push_back(dut.u_fe.e1_row[13:0]);
            if (dut.u_fe.r_iss) o0.push_back(dut.u_fe.r_base + dut.u_fe.r_w);
            foreach (xc_m2[j]) o0.push_back(xc_m2[j]);
            if (dut.u_fe.u_wfc.p_v[1] && !dut.u_fe.u_wfc.p_mk[1]) o1.push_back(dut.u_fe.u_wfc.p_row[1][13:0]);
            if (dut.u_fe.u_wfc.p_v1[1]) o1.push_back(dut.u_fe.u_wfc.p_row1[1][13:0]);
            foreach (xc_m1[j]) o1.push_back(xc_m1[j]);
            if (dut.u_fe.u_wfc.p_v[0] && !dut.u_fe.u_wfc.p_mk[0]) o2.push_back(dut.u_fe.u_wfc.p_row[0][13:0]);
            if (dut.u_fe.u_wfc.p_v1[0]) o2.push_back(dut.u_fe.u_wfc.p_row1[0][13:0]);
            if (dut.u_fe.r_act || dut.u_fe.cq_n != 0) begin
                pr = dut.u_fe.r_base + dut.u_fe.r_w;
                o1.push_back(pr + 1); o2.push_back(pr + 1); o2.push_back(pr + 2); o1.push_back(pr);
            end
            // capture: every lane may write either of its banks in each of the next cycles (conservative)
            if (cap_pend != 0 || dut.u_fe.cl_v != 0) for (l2 = 0; l2 < 16; l2 = l2 + 1) begin
                o0.push_back(l2); o1.push_back(l2); o2.push_back(l2);
                o0.push_back(l2 + 16); o1.push_back(l2 + 16); o2.push_back(l2 + 16);
            end
            // ctrl ops in flight (any cycle)
            foreach (sb_c[j]) begin o0.push_back(sb_c[j] >> 1); o1.push_back(sb_c[j] >> 1); o2.push_back(sb_c[j] >> 1); end
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
    function automatic integer lane_free(input integer ln);
        integer q; begin lane_free = 1; for (q = 0; q < 5; q = q + 1) if (x_busy[q] >= 0 && x_ln[q] == ln) lane_free = 0; end
    endfunction
    function automatic integer rr_pending(input integer u);
        begin rr_pending = 0; foreach (rr_exp[j]) if (rr_exp[j] == u) rr_pending = 1; end
    endfunction
    function automatic integer bank_row(input integer base, input integer span, input integer bank);
        begin bank_row = base + ((rnd(7) % (span / 32)) * 32) + bank; end
    endfunction

    integer tp_t0 = -1, tp_cap_t1 = -1, tp_p2_t1 = -1, tp_wfc_t1 = -1, tp_x_t1 = -1, tp_xn = 0;
    integer region_q [$];               // slots completed, region checks to issue (slot index)
    integer max_ctrl_if = 0;

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 6) begin rst_n <= 1'b1; rss_n <= 1'b1; end
        if (rst_n && cyc > 4) begin observe_b(); xfer_ctrl(); check_returns(); end
        if (rst_n && cyc > 8) begin
            cap_step(MODE == 0);
            // ---------------- landing producers (start l_start; svc / hc 2 rows a beat, coll 4 words when t_cts room)
            f_svc <= '0; f_sel <= '0; f_col <= '0; f_hc <= '0; f_coll <= '0;
            if (l_start >= 0 && cyc >= l_start) begin
                if (lq_svc.size() >= 2 && (MODE != 0 || rnd(80) % 3 == 0)) begin
                    f_svc[0] <= 1'b1; f_svc[1 +: 512] <= lq_svc.pop_front(); f_svc[513 +: 512] <= lq_svc.pop_front(); l_pend = l_pend - 2;
                end
                if (lq_sel.size() != 0 && (MODE != 0 || rnd(81) % 3 == 0)) begin f_sel[0] <= 1'b1; f_sel[512:1] <= lq_sel.pop_front(); l_pend = l_pend - 1; end
                if (lq_col.size() != 0 && cyc % 3 != 0) begin f_col[0] <= 1'b1; f_col[512:1] <= lq_col.pop_front(); l_pend = l_pend - 1; end
                if (lq_hc.size() >= 2 && (MODE != 0 || rnd(82) % 3 == 0)) begin
                    f_hc[512] <= 1'b1; f_hc[511:0] <= lq_hc.pop_front(); f_hc[1025] <= 1'b1; f_hc[1024:513] <= lq_hc.pop_front(); l_pend = l_pend - 2;
                end
                if (lq_coll.size() != 0 && t_cts[0] && (LBP != 0 || cyc % 2 == 0)) begin : cw
                    integer w; reg [3:0] mk4; mk4 = 4'd0;
                    f_coll[0] <= 1'b1; f_coll[2:1] <= 2'd1;
                    for (w = 0; w < 4; w = w + 1) if (lq_coll.size() != 0) begin
                        f_coll[52 + 512*w +: 512] <= lq_coll.pop_front(); mk4[w] = 1'b1; l_pend = l_pend - 1;
                    end
                    f_coll[9:6] <= mk4;
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
            g = rnd(2);
            c_l0r <= (MODE != 0) ? 1'b1 : (g[2:0] != 0);
            c_wr <= g[5:4] != 0;
            // ---------------- done handling
            while (done_seen.size() != 0) begin
                r = done_seen.pop_front(); n_done = n_done + 1;
                begin : dh
                    integer f; f = -1;
                    foreach (pend_tag[j]) if (f < 0 && pend_tag[j] == r) f = j;
                    if (f < 0) begin $display("FAIL cyc %0d: done tag %0d not pending", cyc, r); nbad = nbad + 1; end
                    else pend_tag.delete(f);
                end
                for (k = 0; k < 5; k = k + 1) if (x_busy[k] == r) x_busy[k] = -1;
                for (k = 0; k < 4; k = k + 1) if (slot_busy[k] == 1 && slot_tag[k] == r) begin
                    slot_busy[k] = 2; slot_t_done[k] = cyc; region_q.push_back(k);
                    // XCH baseline (today's contract): the consumer's XGO is issued when the producer's ARMN done arrives
                    if (MODE == 1 && XCH > 0 && XGOS == 0 && k == 0 && xch_go < 0) begin xrd(2, 2, 2048, XCH); xch_go = cyc; end
                    if (MODE != 3) begin : dchk
                        // done => every expected element of the slot's region has landed at the bank ports (direct
                        // contract check: an early done is caught whether or not the region read-back hits the late row)
                        integer aa, nmiss, amiss; nmiss = 0; amiss = -1;
                        for (aa = slot_base[k] * 16; aa < (slot_base[k] + slot_n[k]) * 16; aa = aa + 1)
                            if (exp_el.exists(aa) && !landed.exists(aa)) begin nmiss = nmiss + 1; if (amiss < 0) amiss = aa; end
                        if (nmiss != 0) begin
                            $display("FAIL cyc %0d: EARLY_DONE slot %0d tag %0d with %0d region elements not landed (first %0d)",
                                     cyc, k, r, nmiss, amiss); nbad = nbad + 1;
                        end
                    end
                end
            end
            // ---------------- region checks after done: P2RD (<= 128 rows) or X0 reads
            if (region_q.size() != 0 && cmd_q.size() == 0 && p2c_base.size() == 0) begin
                k = region_q.pop_front();
                n = slot_n[k] > 128 ? 128 : slot_n[k];
                p2rd(slot_base[k], n, 1); n_p2rd = n_p2rd + 1;
                slot_busy[k] = 0;
            end
            if (MODE == 0 && cyc < NCYC) begin
                x_win = ((cyc / 256) % 2 == 0) && (cyc % 256 >= 24);
                // ---------------- capture phases (ARMed), every ~600 cycles
                g = rnd(10);
                begin : ph
                    integer fk, R, np_, ops, ob, span, nel;
                    fk = -1;
                    for (k = 3; k >= 0; k = k - 1) if (slot_busy[k] == 0 && !(slot_ntf[k] && rr_pending(slot_user[k]))) fk = k;
                    if (g[9:0] < 3 && cap_pend == 0 && fk >= 0) begin
                        k = fk;
                        R = 2 + rnd(11) % 15; np_ = 1 + (g[11:10] == 0 ? rnd(12) % 3 : 0);
                        span = 256 * ((R + 1) / 2); ops = span;
                        if (reg_ptr + (span * np_) / 16 + 16 > NROW) reg_ptr = 1024;
                        ob = reg_ptr * 16; reg_ptr = reg_ptr + (span * np_) / 16 + 16;
                        nel = NR * R * np_;
                        arm(k, ob / 16, (span * np_) / 16, nel, g[12], {tag_ctr[7:0], k[1:0]});
                        n_arm = n_arm + 1; n_phase = n_phase + 1;
                        if (EARLYC) p2rd(ob / 16, 8, 0);
                        // the phase's elements start a little after the ARM (the field GO follows the ARM)
                        void'(cap_phase(ob, ops, R, np_, 6, 1, cyc));
                        for (r = 0; r < NR; r = r + 1) r_gap[r] = r_gap[r] + 40;
                    end
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
                if (g[20:16] == 0 && dut.u_fe.cq_n == 0 && cmd_q.size() == 0 && p2c_base.size() == 0 && region_q.size() == 0) begin
                    n = 1 + g[24:22];
                    r = bank_row(0, POOL, (p5_lastbank + 1) % 32);
                    p2rd(r, n, 0); n_p2rd = n_p2rd + 1;
                    p5_lastbank = (r + n - 1) % 32;
                end
                // ---------------- ctrl (ctrl window) over the pool
                if (!x_win && cyc % 256 < 200 && cq_rows.size() < 2 && sb_c.size() < 3 && rnd(30) % 4 == 0) begin
                    r = rnd(31) % POOL;
                    if (occ_m[r % 32] <= 1) begin cq_rows.push_back(r); cq_we.push_back(rnd(32) % 2); end
                end
                both_ok = rnd(33) % 3 == 0;
                // ---------------- X streams over the pool (X window): bus lane = streamer index + 4 * k
                begin : xs
                    integer xp, ln;
                    for (xp = 0; xp < 5; xp = xp + 1)
                        if (x_win && sb_c.size() == 0 && x_busy[xp] < 0 && xs_row[xp].size() == 0 && rnd(90 + xp) % 64 == 0) begin
                            n = 4 + rnd(95) % 13;
                            ln = (xp + 5 * (rnd(96) % 3)) % 16;
                            if (lane_free(ln)) xrd(xp, ln, (cyc + 7 * xp + 20) % 32, n);
                        end
                end
                // ---------------- landing phases (a free slot, no landing traffic pending)
                begin : lp
                    integer fk2, g2;
                    fk2 = -1;
                    for (k = 3; k >= 0; k = k - 1) if (slot_busy[k] == 0 && !(slot_ntf[k] && rr_pending(slot_user[k]))) fk2 = k;
                    g2 = rnd(97);
                    if (fk2 >= 0 && l_pend == 0 && g2 % 400 == 0) begin
                        n = 2 * (1 + rnd(98) % 8);
                        if (reg_ptr + n + 16 > NROW) reg_ptr = 1024;
                        lphase((g2 / 400) % 8 == 1 ? 4 : (g2 / 400) % 8 == 2 ? 5 : (g2 / 400) % 8 == 3 ? 6 : (g2 / 400) % 8 == 4 ? 7 : 0,
                               fk2, reg_ptr, n, cyc);
                        reg_ptr = ((reg_ptr + n + 16 + 15) / 16) * 16; l_start = cyc + 40;   // capture obase stays 256-aligned
                    end
                end
            end else if (MODE == 0) begin
                xc_m2 = xc_m1; xc_m1.delete();
            end else if (MODE == 1) begin
                // ---------------- THROUGHPUT (production shape, concurrent from cycle 200):
                //  capture : one ARMed phase, TP_ROWS rows a root (128 roots, 1 position) at the root rate
                //  P2      : after the done, P2RD of the region's first 128 rows at full grant rate
                //  WFC     : 46-word outbound prefetch = 23 RD2 read pairs, plus 46 inbound writes
                //  X0 / X1 : SU-style unit-stride read streams of 128 rows each
                //  ctrl    : 32 reads + 32 writes back to back
                xc_m2 = xc_m1; xc_m1.delete();
                if (cyc == 200) begin
                    tp_t0 = cyc;
                    xrd(0, 0, 9216, 128); xrd(1, 1, 9216 + 128 + 9, 128);
                    arm(0, 2048, (256 * ((TP_ROWS + 1) / 2)) / 16, NR * TP_ROWS, 1, 5);
                    void'(cap_phase(2048 * 16, 0, TP_ROWS, 1, 2, 0, 9));
                    if (XCH > 0 && XGOS != 0) begin xrd_w(2, 2, 2048, XCH, 0); xch_go = cyc; end
                    for (r = 0; r < NR; r = r + 1) r_gap[r] = r_gap[r] + 30;
                    for (r = 0; r < 46; r = r + 1) begin wj_row.push_back(8192 + r); wj_pay.push_back(0); end
                    for (r = 0; r < 23; r = r + 1) rj.push_back((8448 + 2 * r) | (1 << 16) | ((8449 + 2 * r) << 17));
                    for (r = 0; r < 32; r = r + 1) begin cq_rows.push_back(12288 + r); cq_we.push_back(1); end
                    for (r = 0; r < 32; r = r + 1) begin cq_rows.push_back(12288 + r); cq_we.push_back(0); end
                end
            end else if (MODE == 4 || MODE == 5) begin
                // ---------------- LANDING WORST BURST: MODE 4 attention window (svc 64 beats + sel 64 rows back to back,
                // collector 680 rows at 2/3 a cycle, collective 320 words under t_cts), MODE 5 HC window (hc 64 beats)
                xc_m2 = xc_m1; xc_m1.delete();
                if (cyc == 200) begin
                    tp_t0 = cyc;
                    if (MODE == 4) begin
                        lphase(0, 0, 2048, 128, 1); lphase(5, 1, 2304, 64, 2); lphase(6, 2, 4096, 680, 3); lphase(4, 3, 6144, (LBP != 0) ? 1024 : 320, 4);
                    end else lphase(7, 0, 2048, 128, 5);
                    l_start = cyc + 40;
                end
            end else if (MODE == 2 || MODE == 3) begin
                // ---------------- BURST STRESS: all 128 roots back to back at the root rate, every lane busy
                xc_m2 = xc_m1; xc_m1.delete();
                if (cyc == 200) begin
                    tp_t0 = cyc;
                    begin : bs
                        integer span, ob, ops;
                        span = 256 * ((BROWS + 1) / 2); ops = span;
                        ob = (MODE == 3) ? 2048 * 16 + 16 : 2048 * 16;       // MODE 3: obase 16 (not 256) aligned
                        arm(0, ob / 16, (span * (BNP + 1)) / 16 + 1, NR * BROWS * (BNP + 1), 0, 7);
                        void'(cap_phase(ob, ops, BROWS, BNP + 1, BSKEW, 0, 11));
                        for (r = 0; r < NR; r = r + 1) r_gap[r] = r_gap[r] + 30;
                    end
                end
            end
            if (MODE != 0 && tp_t0 > 0) begin
                if (tp_cap_t1 < 0 && slot_busy[0] != 1 && slot_busy[1] != 1 && slot_busy[2] != 1 && slot_busy[3] != 1) tp_cap_t1 = cyc;
                if (tp_p2_t1 < 0 && tp_cap_t1 > 0 && p2c_base.size() == 0 && region_q.size() == 0 && pend_tag.size() == 0) tp_p2_t1 = cyc;
                if (tp_wfc_t1 < 0 && cyc > tp_t0 + 10 && sb_r.size() == 0 && rj.size() == 0 && !s_rv && ex_q[0].size() == 0 && ex_q[1].size() == 0) tp_wfc_t1 = cyc;
                if (tp_x_t1 < 0 && (MODE != 1 || (xs_row[0].size() == 0 && xs_row[1].size() == 0 && ex_l[0].size() == 0 && ex_l[1].size() == 0 &&
                                                   xs_row[2].size() == 0 && ex_l[2].size() == 0 && (XCH == 0 || xch_go >= 0) &&
                                                   cq_rows.size() == 0 && sb_c.size() == 0 && ex_q_c.size() == 0))) tp_x_t1 = cyc;
            end
        end
        // ---------------- end
        if (cyc == NCYC + 4000 || (MODE != 0 && tp_p2_t1 > 0 && tp_wfc_t1 > 0 && tp_x_t1 > 0 && cyc > tp_p2_t1 + 60) ||
            (MODE == 3 && cyc > 3000)) begin
            for (p = 0; p < 8; p = p + 1) if (ex_q[p].size() != 0) begin $display("FAIL: %0d reads outstanding on port %0d", ex_q[p].size(), p); nbad = nbad + 1; end
            for (p = 0; p < 16; p = p + 1) if (ex_l[p].size() != 0) begin $display("FAIL: %0d rows outstanding on bus lane %0d", ex_l[p].size(), p); nbad = nbad + 1; end
            for (p = 0; p < 5; p = p + 1) if (xs_row[p].size() != 0) begin $display("FAIL: X streamer %0d did not read %0d rows", p, xs_row[p].size()); nbad = nbad + 1; end
            if (l_pend != 0) begin $display("FAIL: %0d landing rows unsent", l_pend); nbad = nbad + 1; end
            if (sb_w.size() || sb_r.size() || sb_c.size() || wj_row.size() || rj.size() || cq_rows.size() || ex_q_c.size()) begin
                $display("FAIL: scoreboards not drained (wfc w %0d r %0d, ctrl %0d / %0d)", sb_w.size(), sb_r.size(), sb_c.size(), ex_q_c.size()); nbad = nbad + 1;
            end
            if (MODE != 3) begin
                if (cap_pend != 0 || n_el_land != n_el_exp) begin $display("FAIL: capture elements landed %0d of %0d (unsent %0d)", n_el_land, n_el_exp, cap_pend); nbad = nbad + 1; end
                if (pend_tag.size() != 0) begin $display("FAIL: %0d engine dones never arrived (first tag %0d)", pend_tag.size(), pend_tag[0]); nbad = nbad + 1; end
                if (rr_exp.size() != 0) begin $display("FAIL: %0d rows-ready missing", rr_exp.size()); nbad = nbad + 1; end
                if (dut.u_fe.fe_flt != 0 || fvec != 0 || flt) begin $display("FAIL: fault fe_flt %b fvec %b", dut.u_fe.fe_flt, fvec); nbad = nbad + 1; end
            end else begin
                // misaligned phase: the alignment fault must be raised (fail closed); nothing else may be wrong
                if (dut.u_fe.fe_flt[8] !== 1'b1) begin $display("FAIL: misaligned capture phase NOT flagged (fe_flt %b)", dut.u_fe.fe_flt); nbad = nbad + 1; end
                else $display("ALIGN_FAULT raised (fe_flt %b)", dut.u_fe.fe_flt);
            end
            if (ks_pay.size() != 0) begin $display("FAIL: %0d START doorbells missing", ks_pay.size()); nbad = nbad + 1; end
            if (ovf_m != 0) begin $display("FAIL: stimulus broke the stall-free contract %0d times", ovf_m); nbad = nbad + 1; end
            $display("RESULT cyc=%0d checked=%0d mismatches_or_fails=%0d phases=%0d arm=%0d p2rd=%0d done=%0d rows_ready=%0d starts=%0d p2_words=%0d ctrl_reads=%0d el=%0d/%0d cap_ops=%0d max_occ=%0d mirror_max=%0d lat p0=%0d p1=%0d p2=%0d p4=%0d p6=%0d p7=%0d",
                     cyc, nchk, nbad, n_phase, n_arm, n_p2rd, n_done, n_rr, ks_seen, p2_words_seen, n_cq, n_el_land, n_el_exp, cap_ops,
                     max_occ, maxocc_m, lat[0], lat[1], lat[2], lat[4], lat[6], lat[7]);
            if (MODE >= 4)
                $display("LANDING mode=%0d rows=%0d land_ops=%0d span=%0d (first %0d last %0d) all_done=%0d (serial cycles from t0 %0d)",
                         MODE, n_el_exp / 16, lan_ops, lan_last - lan_first + 1, lan_first, lan_last, tp_cap_t1 - tp_t0, tp_t0);
            if (MODE == 1 || MODE == 2)
                $display("THROUGHPUT mode=%0d rows_per_root=%0d positions=%0d elements=%0d emit_cycles=%0d (first %0d last %0d) cap_ops=%0d cap_write_span=%0d landing_tail=%0d (last element at the pins -> done) arm_to_done=%0d p2_done=%0d wfc_23pairs=%0d x_ctrl=%0d (serial cycles from t0 %0d)",
                         MODE, MODE == 1 ? TP_ROWS : BROWS, MODE == 1 ? 1 : BNP + 1, n_el_exp, cap_last_emit - cap_first_emit + 1,
                         cap_first_emit, cap_last_emit, cap_ops, cap_last - cap_first + 1, slot_t_done[0] - cap_last_emit,
                         slot_t_done[0] - slot_t_arm[0], tp_p2_t1 - tp_t0, tp_wfc_t1 - tp_t0, tp_x_t1 - tp_t0, tp_t0);
            if (XCH > 0)
                $display("XCHAIN xgos=%0d rows=%0d slot_done=%0d (tb sees the ARMN done) x_go_issued=%0d first_x_row_at_bank=%0d done_to_first_row=%0d arm_to_first_row=%0d (serial cycles)",
                         XGOS, XCH, slot_t_done[0], xch_go, xch_first, xch_first - slot_t_done[0], xch_first - slot_t_arm[0]);
            if (nbad == 0 && (nchk + n_el_land > 0 || MODE == 3)) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
    // ctrl reads ride the generic per-port queues (ex_q[3] / ex_q[4]) filled by observe_b in the right order; move
    // them, in (cycle, port 3 then 4) order, to the stream-domain expectation queue
    // (called from the main clk process right after observe_b: one process owns ex_q / ex_t, so the hand-off order is
    // defined; a second always @(posedge clk) here raced observe_b on the same edge -- simulator-dependent order)
    task automatic xfer_ctrl();
        while (ex_q[3].size() != 0 || ex_q[4].size() != 0) begin
            if (ex_q[3].size() != 0 && (ex_q[4].size() == 0 || ex_t[3][0] <= ex_t[4][0])) begin
                ex_q_c.push_back(ex_q[3].pop_front()); void'(ex_t[3].pop_front());
            end else begin
                ex_q_c.push_back(ex_q[4].pop_front()); void'(ex_t[4].pop_front());
            end
        end
    endtask
    initial begin
        for (k = 0; k < 8; k = k + 1) lat[k] = -1;
        for (k = 0; k < 16; k = k + 1) lat_l[k] = -1;
        for (k = 0; k < 5; k = k + 1) x_busy[k] = -1;
        for (k = 0; k < 4; k = k + 1) slot_busy[k] = 0;
        for (k = 0; k < NR; k = k + 1) begin r_cr[k] = 0; r_gap[k] = 0; r_tail[k] = 0; end
        rs = SEED * 32'h2545f491 + 1;
    end
`ifdef OT_SPVM_FE_H
    // ------------------------------------------------------------ LOCKSTEP: hierarchy dsfd_vm_fe_h vs flat dsfd_vm_fe
    // (el1013-s81-vmfe).  Both see the same FE inputs; every FE output is compared bit-exact every serial cycle from
    // LK_IDLE cycles after reset release (the hierarchy's reset tree releases its leaves up to 2 + 1 + 2 * 10 cycles
    // after the flat module: the stimulus is idle in that window, and the flat reference gets the same window).
    // Sticky fault vectors fe_flt / m_rf (contract rule 3: inter-leaf fault wires may add cycles): the hierarchy may
    // lag the flat module by <= LK_FLAG cycles and may never lead it.  Coverage is printed; the gate refuses a
    // lockstep set that did not exercise reads, writes, landing drains and back-pressure.
    localparam integer LK_IDLE = 28, LK_FLAG = 8;
    integer lk_rel = 0, lk_n = 0, lk_bad = 0, lk_pre = 0, lk_i;
    integer lk_rd = 0, lk_wr = 0, lk_drain = 0, lk_cts_low = 0, lk_cw_stall = 0, lk_cap = 0, lk_cts_tog = 0, lk_rdy = 0, lk_dv = 0, lk_ks = 0;
    reg [NP-1:0] lk_ports = 0; reg [2:0] lk_cts_q = 0;
    reg [15:0] lk_fh [0:LK_FLAG]; reg [15:0] lk_rh [0:LK_FLAG];
    initial for (lk_i = 0; lk_i <= LK_FLAG; lk_i = lk_i + 1) begin lk_fh[lk_i] = 0; lk_rh[lk_i] = 0; end
    task automatic lk_fail(input string what);
        lk_bad = lk_bad + 1; nbad = nbad + 1;
        if (lk_bad <= 12) $display("FAIL cyc %0d: LOCKSTEP mismatch on %s", cyc, what);
    endtask
    always @(posedge clk) begin
        if (!rst_n) lk_rel <= 0; else lk_rel <= lk_rel + 1;
        lk_fh[0] <= dut.f_flt; lk_rh[0] <= dut.fmrf;
        for (lk_i = 1; lk_i <= LK_FLAG; lk_i = lk_i + 1) begin lk_fh[lk_i] <= lk_fh[lk_i-1]; lk_rh[lk_i] <= lk_rh[lk_i-1]; end
        if (rst_n && lk_rel < LK_IDLE) begin
            // the window must really be idle: no op may leave either FE before the compare starts
            if (dut.fmv != 0 || dut.hmv != 0) begin lk_pre = lk_pre + 1; $display("LOCKSTEP pre-window op at cyc %0d (rel %0d) f %x h %x", cyc, lk_rel, dut.fmv, dut.hmv); end
        end
        if (rst_n && lk_rel >= LK_IDLE) begin
            lk_n = lk_n + 1;
            if (dut.hmv !== dut.fmv) lk_fail("m_v");
            if (dut.hmwe !== dut.fmwe) lk_fail("m_we");
            if (dut.hmrow !== dut.fmrow) lk_fail("m_row");
            if (dut.hmm !== dut.fmm) lk_fail("m_mask");
            if (dut.hmd !== dut.fmd) lk_fail("m_d");
            if (dut.h_swg !== dut.f_swg) lk_fail("t_swg");
            if (dut.h_srg !== dut.f_srg) lk_fail("t_srg");
            if (dut.h_ks !== dut.f_ks) lk_fail("t_ks");
            if (dut.h_dv !== dut.f_dv) lk_fail("dv");
            if (dut.h_dt !== dut.f_dt) lk_fail("dt");
            if (dut.h_cts !== dut.f_cts) lk_fail("t_cts");
            if (dut.h_cwv !== dut.f_cwv) lk_fail("c_wv");
            if (dut.h_cwd !== dut.f_cwd) lk_fail("c_wd");
            if (dut.h_rdy !== dut.f_rdy) lk_fail("t_rdy");
            if ((dut.h_flt & ~dut.f_flt) != 0) lk_fail("fe_flt (hierarchy leads)");
            if ((lk_fh[LK_FLAG] & ~dut.h_flt) != 0) lk_fail("fe_flt (hierarchy lags > LK_FLAG)");
            if ((dut.hmrf & ~dut.fmrf) != 0) lk_fail("m_rf (hierarchy leads)");
            if ((lk_rh[LK_FLAG] & ~dut.hmrf) != 0) lk_fail("m_rf (hierarchy lags > LK_FLAG)");
            // coverage, on the flat reference's outputs (slice 0)
            for (lk_i = 0; lk_i < NP; lk_i = lk_i + 1) if (dut.fmv[lk_i]) begin
                lk_ports[lk_i] = 1'b1;
                if (dut.fmwe[lk_i]) lk_wr = lk_wr + 1; else lk_rd = lk_rd + 1;
                if (lk_i == 10 || lk_i == 11) lk_drain = lk_drain + 1;
                if (lk_i >= CP) lk_cap = lk_cap + 1;
            end
            if (dut.f_cts[1] && !dut.f_cts[0]) lk_cts_low = lk_cts_low + 1;
            if (dut.f_cts != lk_cts_q) lk_cts_tog = lk_cts_tog + 1;
            lk_cts_q <= dut.f_cts;
            if (dut.f_cwv && !c_wr) lk_cw_stall = lk_cw_stall + 1;
            if (dut.f_rdy != 0) lk_rdy = lk_rdy + 1;
            if (dut.f_dv) lk_dv = lk_dv + 1;
            if (dut.f_ks[0]) lk_ks = lk_ks + 1;
        end
    end
    final begin
        if (lk_pre != 0) $display("FAIL: LOCKSTEP idle window violated %0d cycles (an op left the FE < %0d cycles after reset)", lk_pre, LK_IDLE);
        $display("LOCKSTEP cycles=%0d mismatches=%0d pre=%0d ports=%07x rd=%0d wr=%0d drain=%0d cap=%0d cts_low=%0d cts_tog=%0d cw_stall=%0d rdy=%0d dv=%0d ks=%0d fe_flt=%04x/%04x",
                 lk_n, lk_bad, lk_pre, lk_ports, lk_rd, lk_wr, lk_drain, lk_cap, lk_cts_low, lk_cts_tog, lk_cw_stall, lk_rdy, lk_dv, lk_ks, dut.h_flt, dut.f_flt);
        if (lk_bad == 0 && lk_pre == 0 && lk_n > 0) $display("LOCKSTEP_OK"); else $display("LOCKSTEP_BAD");
    end
`endif
    reg flt_seen = 0;
    always @(posedge clk) if (!flt_seen && rst_n && (dut.u_fe.fe_flt != 0 || fvec != 0)) begin
        flt_seen <= 1; $display("FAULT first at cyc %0d: fe_flt %b fvec %b", cyc, dut.u_fe.fe_flt, fvec);
    end
endmodule
