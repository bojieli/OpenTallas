`timescale 1ns/1ps
// MU-S81-2/HOSTEP (2026-10-19): bench of the HOST-PLANE multi-user endpoint ot_s81sl_lep_mu_h (s_7N of a non-duplicated
// die: MU_EN 1, AB_EN 0, HOST_EN 1; kit s81sl_lepmuh) against the single-user host endpoint ot_s81sl_lep (the reference),
// both on the same link model (2 x dsfd_coll_lane_w LCR 1 + 2 x ot_pdie_ucie, lane 1 skewed) to a behavioural host-side
// frame codec (as tb_s81sl_lep_host).  Dies: M = lep_mu_h + dsdv_mu_land (NB beats, SRAM), R = lep.
// Traffic, both directions at once, identical stimulus on M and R except the MU tags:
//   H -> die  untagged ring beats, HOST frames, KS frames, and three tagged XB messages of NB beats interleaved with them:
//             user 0 cut-through (the latency user), user 2 landed, user 3 cut-through.  M's peer sends the tagged beats,
//             R's peer the same beats with the tag field 0 (the single-user beat).  Checks: R delivers every ring beat /
//             HOST / KS payload bit-exact in order; M delivers every cut-through beat on ri at the SAME cycle as R with the
//             SAME bits (tag stripped) and mu_rt = {1, user, pos} (0 untagged), every landed beat on ml_wv / ml_wd at the
//             cycle R delivers it on ri (full beat, tag kept); M's f_host / f_ks / f_lf equal R's on EVERY cycle.  Then a
//             replay command for user 2 (die seq_host slot): its NB beats leave M's ri, stripped, with their tag on mu_rt.
//   die -> H  XB ring beats on ro + seq_host t_host / t_kd events, identical on M and R; M opens two TX tag windows
//             (mu_c): user 0 cut (land 0) and user 5 land, with t_host / t_kd events firing inside the windows.  Both
//             peers must receive the same frames at the same cycles; M's in-window ring beats carry the stamped tag, all
//             other frames (incl. THOST / TKD inside a window) are bit-identical to R's.
//   no fault on M / R / landing in the main phase; then F1: a non-XB ring beat inside a window -> M fault.
// Mutants: +define+OT_S81SL_LEP_MUT_HSTAMP (host-plane frames stamped inside a TX window), OT_S81SL_LEP_MUT_TAGDROP,
//          OT_S81SL_LEP_MUT_LANDCUT, OT_S81SL_LEP_MUT_KSOFF: each must FAIL.
// Verdict: "PASS lep_muh ..." or "FAIL lep_muh ...".
module tb_lmh_link (
    input  wire clk, input wire rst_n,
    input  wire lo0_v, output wire lo0_r, input wire [552:0] lo0_d,
    input  wire lo1_v, output wire lo1_r, input wire [552:0] lo1_d,
    output wire li0_v, input wire li0_r, output wire [552:0] li0_d,
    output wire li1_v, input wire li1_r, output wire [552:0] li1_d,
    input  wire [1:0] rxv, output wire [2:0] l0_f, output wire [2:0] l1_f, output wire [1:0] l0_st, output wire [1:0] l1_st,
    input  wire h0v, output wire h0r, input wire [552:0] h0d,
    input  wire h1v, output wire h1r, input wire [552:0] h1d,
    output wire hi0v, output wire [552:0] hi0d, output wire hi1v, output wire [552:0] hi1d
);
    wire [511:0] atx0, atx1, htx0, htx1, arx0, arx1, hrx0, hrx1; wire [1:0] hst0, hst1; wire [2:0] hf0, hf1;
    wire [512:0] pa0, pa1, ph0, ph1; wire ta0, ta1, th0, th1;
    dsfd_coll_lane_w #(.LCR(1)) a_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({l0_st[0], l0_st[1], arx0, rxv[0]}), .tx(atx0), .tf(),
        .lo_v(lo0_v), .lo_r(lo0_r), .lo_d(lo0_d), .li_v(li0_v), .li_r(li0_r), .li_d(li0_d), .flt(l0_f));
    dsfd_coll_lane_w #(.LCR(1)) a_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({l1_st[0], l1_st[1], arx1, rxv[1]}), .tx(atx1), .tf(),
        .lo_v(lo1_v), .lo_r(lo1_r), .lo_d(lo1_d), .li_v(li1_v), .li_r(li1_r), .li_d(li1_d), .flt(l1_f));
    dsfd_coll_lane_e h_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({hst0[0], hst0[1], hrx0, rst_n}), .tx(htx0), .tf(),
        .lo_v(h0v), .lo_r(h0r), .lo_d(h0d), .li_v(hi0v), .li_r(1'b1), .li_d(hi0d), .flt(hf0));
    dsfd_coll_lane_e h_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({hst1[0], hst1[1], hrx1, rst_n}), .tx(htx1), .tf(),
        .lo_v(h1v), .lo_r(h1r), .lo_d(h1d), .li_v(hi1v), .li_r(1'b1), .li_d(hi1d), .flt(hf1));
    ot_pdie_ucie #(.PMA_LAT(2)) ua0 (.clk(clk), .rst(rst_n), .tx(atx0), .rx(arx0), .st(l0_st), .pma_tx(pa0), .pma_tck(ta0), .pma_rx(ph0), .pma_rck(th0));
    ot_pdie_ucie #(.PMA_LAT(2)) uh0 (.clk(clk), .rst(rst_n), .tx(htx0), .rx(hrx0), .st(hst0), .pma_tx(ph0), .pma_tck(th0), .pma_rx(pa0), .pma_rck(ta0));
    ot_pdie_ucie #(.PMA_LAT(6)) ua1 (.clk(clk), .rst(rst_n), .tx(atx1), .rx(arx1), .st(l1_st), .pma_tx(pa1), .pma_tck(ta1), .pma_rx(ph1), .pma_rck(th1));
    ot_pdie_ucie #(.PMA_LAT(6)) uh1 (.clk(clk), .rst(rst_n), .tx(htx1), .rx(hrx1), .st(hst1), .pma_tx(ph1), .pma_tck(th1), .pma_rx(pa1), .pma_rck(ta1));
endmodule

module tb_s81sl_lep_muh #(parameter integer NB = 80, parameter integer RXSRAM = 0, parameter integer SEED = 1, parameter integer WAIT = 8000,
                          parameter integer HIER = 0, parameter integer INPIPE = 0);   // LEPCAP: M with IN_PIPE 1 vs R fed through one TB face register
    localparam integer TG = 1045;
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    // ------------------------------------------------------------------ dies
    reg [1103:0] d_ro = 0; reg [76:0] t_host = 0; reg [53:0] t_kd = 0; reg [33:0] m_mc = 0; reg [10:0] m_rc = 0;
    reg [1103:0] m_ro_x = 0;                                          // F1 only: an extra beat on M alone
    wire [1103:0] m_ri, r_ri; wire [31:0] m_rt; wire m_f, r_f, m_lf;
    wire [514:0] m_fh, r_fh; wire [3:0] m_flf, r_flf; wire [52:0] m_fks, r_fks;
    wire m_mwv, m_mrv; wire [1103:0] m_mwd, m_mrd;
    wire [1:0] mlv, mlr, miv, mir, mrxv, rlv, rlr, riv_, rir, rrxv; wire [2*553-1:0] mld, mid, rld, rid_;
    wire [2:0] mf0, mf1, rf0, rf1; wire [1:0] mst0, mst1, rst0, rst1;
    ot_s81sl_lep_mu_h #(.RX_SRAM(RXSRAM), .SRAM(1), .NB(NB), .IN_PIPE(INPIPE), .HIER_LANES(HIER)) lm (.clk(clk), .rst_n(rst_n), .ro(d_ro | m_ro_x), .ri(m_ri),
        .lo0_v(mlv[0]), .lo0_r(mlr[0]), .lo0_d(mld[0 +: 553]), .lo1_v(mlv[1]), .lo1_r(mlr[1]), .lo1_d(mld[553 +: 553]),
        .li0_v(miv[0]), .li0_r(mir[0]), .li0_d(mid[0 +: 553]), .li1_v(miv[1]), .li1_r(mir[1]), .li1_d(mid[553 +: 553]),
        .rxv(mrxv), .sl_f(1'b0), .l0_f(mf0), .l1_f(mf1), .l0_st(mst0), .l1_st(mst1),
        .t_host(t_host), .t_kd(t_kd), .f_host(m_fh), .f_lf(m_flf), .f_ks(m_fks),
        .mu_c(m_mc), .mu_rt(m_rt), .ml_wv(m_mwv), .ml_wd(m_mwd), .ml_rv(m_mrv), .ml_rd(m_mrd), .ml_f(m_lf), .fault(m_f));
    dsdv_mu_land #(.NB(NB), .NS(1), .SRAM(1)) mland (.clk(clk), .rst_n(rst_n), .wv(m_mwv), .wd(m_mwd), .rc(m_rc),
        .rv(m_mrv), .rd(m_mrd), .fault(m_lf));
    // LEPCAP: with INPIPE 1 the reference sees ro / t_host / t_kd one edge late (= M's internal face stage), so every
    // same-cycle check below compares M with the +1-edge single-user schedule.
    reg [1103:0] r_ro_p = 0; reg [76:0] r_th_p = 0; reg [53:0] r_tk_p = 0;
    always @(posedge clk) begin r_ro_p <= d_ro; r_th_p <= t_host; r_tk_p <= t_kd; end
    wire [1103:0] r_ro = (INPIPE != 0) ? r_ro_p : d_ro; wire [76:0] r_th = (INPIPE != 0) ? r_th_p : t_host;
    wire [53:0] r_tk = (INPIPE != 0) ? r_tk_p : t_kd;
    ot_s81sl_lep lr (.clk(clk), .rst_n(rst_n), .ro(r_ro), .ri(r_ri),
        .lo0_v(rlv[0]), .lo0_r(rlr[0]), .lo0_d(rld[0 +: 553]), .lo1_v(rlv[1]), .lo1_r(rlr[1]), .lo1_d(rld[553 +: 553]),
        .li0_v(riv_[0]), .li0_r(rir[0]), .li0_d(rid_[0 +: 553]), .li1_v(riv_[1]), .li1_r(rir[1]), .li1_d(rid_[553 +: 553]),
        .rxv(rrxv), .sl_f(1'b0), .l0_f(rf0), .l1_f(rf1), .l0_st(rst0), .l1_st(rst1),
        .t_host(r_th), .t_kd(r_tk), .f_host(r_fh), .f_lf(r_flf), .f_ks(r_fks), .fault(r_f));
    // host-side peers (HM of M, HR of R)
    reg hm0v = 0, hm1v = 0, hr0v = 0, hr1v = 0; reg [552:0] hm0d = 0, hm1d = 0, hr0d = 0, hr1d = 0;
    wire hm0r, hm1r, hr0r, hr1r, hmi0v, hmi1v, hri0v, hri1v; wire [552:0] hmi0d, hmi1d, hri0d, hri1d;
    tb_lmh_link km (.clk(clk), .rst_n(rst_n), .lo0_v(mlv[0]), .lo0_r(mlr[0]), .lo0_d(mld[0 +: 553]),
        .lo1_v(mlv[1]), .lo1_r(mlr[1]), .lo1_d(mld[553 +: 553]), .li0_v(miv[0]), .li0_r(mir[0]), .li0_d(mid[0 +: 553]),
        .li1_v(miv[1]), .li1_r(mir[1]), .li1_d(mid[553 +: 553]), .rxv(mrxv), .l0_f(mf0), .l1_f(mf1), .l0_st(mst0), .l1_st(mst1),
        .h0v(hm0v), .h0r(hm0r), .h0d(hm0d), .h1v(hm1v), .h1r(hm1r), .h1d(hm1d),
        .hi0v(hmi0v), .hi0d(hmi0d), .hi1v(hmi1v), .hi1d(hmi1d));
    tb_lmh_link kr (.clk(clk), .rst_n(rst_n), .lo0_v(rlv[0]), .lo0_r(rlr[0]), .lo0_d(rld[0 +: 553]),
        .lo1_v(rlv[1]), .lo1_r(rlr[1]), .lo1_d(rld[553 +: 553]), .li0_v(riv_[0]), .li0_r(rir[0]), .li0_d(rid_[0 +: 553]),
        .li1_v(riv_[1]), .li1_r(rir[1]), .li1_d(rid_[553 +: 553]), .rxv(rrxv), .l0_f(rf0), .l1_f(rf1), .l0_st(rst0), .l1_st(rst1),
        .h0v(hr0v), .h0r(hr0r), .h0d(hr0d), .h1v(hr1v), .h1r(hr1r), .h1d(hr1d),
        .hi0v(hri0v), .hi0d(hri0d), .hi1v(hri1v), .hi1d(hri1d));

    function automatic [1103:0] rnd(input integer dummy);
        integer i; reg [1103:0] b;
        begin for (i = 0; i < 34; i = i + 1) b[i * 32 +: 32] = $urandom; b[1103:1088] = $urandom; rnd = b; end
    endfunction
    function automatic [1103:0] xb(input integer dummy);              // an XB ring beat (spare bits 0, as ot_s81sl_vq)
        integer i; reg [1103:0] b;
        begin
            b = 0; for (i = 0; i < 32; i = i + 1) b[21 + 32 * i +: 32] = $urandom;
            b[20:13] = $urandom; b[12:9] = $urandom; b[8:4] = 5'd1 + ($urandom % 8); b[3:1] = 3'd2; b[0] = 1'b1; xb = b;
        end
    endfunction
    function automatic [1103:0] hfrm(input [2:0] ty, input [513:0] pay);
        begin hfrm = 1104'd0; hfrm[3:1] = ty; hfrm[4 +: 514] = pay; end
    endfunction
    function automatic [1103:0] tframe(input [2:0] ty, input [76:0] w);
        begin tframe = 1104'd0; tframe[3:1] = ty; tframe[4 +: 77] = w; end
    endfunction

    // ------------------------------------------------------------------ H -> die lists
    localparam integer QN = 2048;
    reg [1103:0] hsm [0:QN-1]; reg [1103:0] hsr [0:QN-1]; integer hn = 0;          // frames the peers send
    reg [1103:0] gs [0:QN-1]; reg [1103:0] gt [0:QN-1]; reg [31:0] grt [0:QN-1]; reg gl [0:QN-1]; integer gn = 0;
    reg [513:0] eh [0:511]; integer ehn = 0, ehk = 0; reg [52:0] ek [0:511]; integer ekn = 0, ekk = 0;
    integer pm0 = 0, pm1 = 0, pr0 = 0, pr1 = 0;
    always @(negedge clk) begin
        hm0v <= pm0 < hn; hm0d <= {pm0[0], hsm[pm0][551:0]}; hm1v <= pm1 < hn; hm1d <= {pm1[0], hsm[pm1][1103:552]};
        hr0v <= pr0 < hn; hr0d <= {pr0[0], hsr[pr0][551:0]}; hr1v <= pr1 < hn; hr1d <= {pr1[0], hsr[pr1][1103:552]};
    end
    // deliveries
    reg [1103:0] rrd [0:QN-1]; integer rrc [0:QN-1]; integer nrr = 0;               // R ri
    reg [1103:0] mrd [0:QN-1]; reg [31:0] mrt [0:QN-1]; integer mrc [0:QN-1]; integer nmr = 0;   // M ri
    reg [1103:0] mld_ [0:QN-1]; integer mlc [0:QN-1]; integer nml = 0;             // M landed
    integer bad = 0, hid = 0, cmp_on = 0;
    // ------------------------------------------------------------------ die -> H lists
    reg [1103:0] eam [0:QN-1]; reg [1103:0] ear [0:QN-1]; integer ean = 0;
    reg [1103:0] eth [0:1023]; integer ethn = 0; reg [1103:0] etk [0:1023]; integer etkn = 0;
    reg [552:0] qm0 [0:4095]; reg [552:0] qm1 [0:4095]; reg [552:0] qr0 [0:4095]; reg [552:0] qr1 [0:4095];
    integer nqm0 = 0, nqm1 = 0, nqr0 = 0, nqr1 = 0, km_ = 0, kr_ = 0;
    integer fmc [0:4095]; integer frc [0:4095];
    integer m_eak = 0, m_ethk = 0, m_etkk = 0, r_eak = 0, r_ethk = 0, r_etkk = 0, xbad = 0, ncyc = 0;
    reg [1103:0] fx;
    task automatic chk_frame(input [1103:0] f, input integer isr);
        begin
            if (f[0]) begin
                if (isr) begin if (r_eak >= ean || f !== ear[r_eak]) begin xbad = xbad + 1; if (xbad < 8) $display("MISMATCH R->H ring %0d", r_eak); end r_eak = r_eak + 1; end
                else begin if (m_eak >= ean || f !== eam[m_eak]) begin xbad = xbad + 1; if (xbad < 8) $display("MISMATCH M->H ring %0d got tag %h exp %h", m_eak, f[TG +: 33], eam[m_eak][TG +: 33]); end m_eak = m_eak + 1; end
            end else if (f[3:1] == 3'd3) begin
                if (isr) begin if (r_ethk >= ethn || f !== eth[r_ethk]) begin xbad = xbad + 1; if (xbad < 8) $display("MISMATCH R->H THOST %0d", r_ethk); end r_ethk = r_ethk + 1; end
                else begin if (m_ethk >= ethn || f !== eth[m_ethk]) begin xbad = xbad + 1; if (xbad < 8) $display("MISMATCH M->H THOST %0d (tag field %h)", m_ethk, f[TG +: 33]); end m_ethk = m_ethk + 1; end
            end else if (f[3:1] == 3'd4) begin
                if (isr) begin if (r_etkk >= etkn || f !== etk[r_etkk]) begin xbad = xbad + 1; if (xbad < 8) $display("MISMATCH R->H TKD %0d", r_etkk); end r_etkk = r_etkk + 1; end
                else begin if (m_etkk >= etkn || f !== etk[m_etkk]) begin xbad = xbad + 1; if (xbad < 8) $display("MISMATCH M->H TKD %0d (tag field %h)", m_etkk, f[TG +: 33]); end m_etkk = m_etkk + 1; end
            end else begin xbad = xbad + 1; $display("MISMATCH %s->H unknown frame type %0d", isr ? "R" : "M", f[3:1]); end
        end
    endtask
    always @(posedge clk) begin
        if (hm0v && hm0r) pm0 = pm0 + 1; if (hm1v && hm1r) pm1 = pm1 + 1;
        if (hr0v && hr0r) pr0 = pr0 + 1; if (hr1v && hr1r) pr1 = pr1 + 1;
        if (r_ri[0]) begin rrd[nrr] = r_ri; rrc[nrr] = cyc; nrr = nrr + 1; end
        if (m_ri[0]) begin mrd[nmr] = m_ri; mrt[nmr] = m_rt; mrc[nmr] = cyc; nmr = nmr + 1; end
        else if (m_rt != 32'd0) begin bad = bad + 1; $display("MISMATCH M mu_rt %h without a beat cyc %0d", m_rt, cyc); end
        if (m_mwv) begin mld_[nml] = m_mwd; mlc[nml] = cyc; nml = nml + 1; end
        if (r_fh[0]) begin
            if (ehk >= ehn || r_fh[514:1] !== eh[ehk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH R f_host %0d", ehk); end
            ehk = ehk + 1;
        end
        if (r_fks[52]) begin
            if (ekk >= ekn || r_fks !== ek[ekk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH R f_ks %0d", ekk); end
            ekk = ekk + 1;
        end
        if (cmp_on && (m_fh !== r_fh || m_fks !== r_fks || m_flf !== r_flf)) begin
            hid = hid + 1; if (hid < 8) $display("MISMATCH host plane M vs R cyc %0d: f_host v %b/%b f_ks %h/%h f_lf %b/%b", cyc,
                m_fh[0], r_fh[0], m_fks, r_fks, m_flf, r_flf);
        end
        // peers receive
        if (hmi0v) begin qm0[nqm0] = hmi0d; nqm0 = nqm0 + 1; end
        if (hmi1v) begin qm1[nqm1] = hmi1d; nqm1 = nqm1 + 1; end
        if (hri0v) begin qr0[nqr0] = hri0d; nqr0 = nqr0 + 1; end
        if (hri1v) begin qr1[nqr1] = hri1d; nqr1 = nqr1 + 1; end
        while (km_ < nqm0 && km_ < nqm1) begin
            fx = {qm1[km_][551:0], qm0[km_][551:0]};
            if (qm0[km_][552] !== qm1[km_][552]) begin xbad = xbad + 1; $display("MISMATCH M->H parity %0d", km_); end
            if (ncyc == 0) chk_frame(fx, 0); fmc[km_] = cyc; km_ = km_ + 1;
        end
        while (kr_ < nqr0 && kr_ < nqr1) begin
            fx = {qr1[kr_][551:0], qr0[kr_][551:0]};
            if (qr0[kr_][552] !== qr1[kr_][552]) begin xbad = xbad + 1; $display("MISMATCH R->H parity %0d", kr_); end
            chk_frame(fx, 1); frc[kr_] = cyc; kr_ = kr_ + 1;
        end
    end

    // ------------------------------------------------------------------ stimulus
    reg [1103:0] b, bs; reg [513:0] hp; reg [52:0] kw; reg [63:0] td; reg [11:0] stat; reg [32:0] tg;
    integer k, j, u, gap_h, wq, wleft, wuser, wland, nwin, ii, jj, ok, idc, rp_i, f_main, f1, rdone;
    integer mu_u [0:3]; integer mu_l [0:3];
    task automatic add_ring_untagged;
        begin b = rnd(0); b[0] = 1'b1; b[TG +: 33] = 33'd0;
            hsm[hn] = b; hsr[hn] = b; hn = hn + 1; gs[gn] = b; gt[gn] = b; grt[gn] = 0; gl[gn] = 0; gn = gn + 1; end
    endtask
    task automatic add_host_or_ks;
        begin
            if ($urandom % 2) begin hp = rnd(0); hsm[hn] = hfrm(3'd1, hp); hsr[hn] = hsm[hn]; hn = hn + 1; eh[ehn] = hp; ehn = ehn + 1; end
            else begin kw = rnd(0); kw[52] = 1'b1; hsm[hn] = hfrm(3'd2, {461'd0, kw}); hsr[hn] = hsm[hn]; hn = hn + 1; ek[ekn] = kw; ekn = ekn + 1; end
        end
    endtask
    task automatic add_msg(input integer uu, input integer land);
        integer kk;
        begin
            kk = 0;
            while (kk < NB) begin
                case ($urandom % 8)
                    0: add_host_or_ks;
                    1: add_ring_untagged;
                    default: begin
                        b = xb(0); bs = b; b[TG +: 33] = {21'(300 + uu), 10'(uu), 1'(land), 1'b1};
                        hsm[hn] = b; hsr[hn] = bs; hn = hn + 1;
                        gs[gn] = bs; gt[gn] = b; grt[gn] = {1'b1, 10'(uu), 21'(300 + uu)}; gl[gn] = land[0]; gn = gn + 1;
                        kk = kk + 1;
                    end
                endcase
            end
        end
    endtask
    initial begin
        void'($urandom(SEED));
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);
        cmp_on = 1;
        // H -> die frame lists (sent at lane rate from now on)
        for (k = 0; k < 60; k = k + 1) if ($urandom % 3 == 0) add_host_or_ks; else add_ring_untagged;
        add_msg(0, 0);
        for (k = 0; k < 20; k = k + 1) if ($urandom % 3 == 0) add_host_or_ks; else add_ring_untagged;
        add_msg(2, 1);
        for (k = 0; k < 20; k = k + 1) if ($urandom % 3 == 0) add_host_or_ks; else add_ring_untagged;
        add_msg(3, 0);
        for (k = 0; k < 40; k = k + 1) if ($urandom % 3 == 0) add_host_or_ks; else add_ring_untagged;
        // die -> H: XB ring beats at 0.4, t_host / t_kd events; TX windows on M: user 0 cut, user 5 land
        stat = 12'h801; gap_h = 0;
        @(negedge clk); t_host = {stat, 1'b0, 64'd0};
        @(posedge clk); @(posedge clk); @(posedge clk);
        eth[ethn] = tframe(3'd3, {stat, 1'b0, 64'd0}); ethn = ethn + 1;
        mu_u[0] = 0; mu_l[0] = 0; mu_u[1] = 5; mu_l[1] = 1;
        wq = -1; wleft = 0; nwin = 0;
        for (k = 0; k < 1400; k = k + 1) begin
            @(negedge clk);
            d_ro = 0; m_mc = 0; t_host[64] = 1'b0; t_kd = 54'd0; gap_h = gap_h + 1;
            if (nwin < 2 && wleft == 0 && wq < 0 && (k == 150 || k == 700)) begin
                wuser = mu_u[nwin]; wland = mu_l[nwin];
                m_mc = {21'(400 + wuser), 10'(wuser), 1'(wland), 1'b0, 1'b1}; wq = 4; nwin = nwin + 1;
            end else if (wq > 0) wq = wq - 1;
            else begin
                if (wq == 0) begin wq = -1; wleft = NB; end
                if (($urandom % 100) < 40) begin
                    b = xb(0); d_ro = b; ear[ean] = b; eam[ean] = b;
                    if (wleft > 0) begin eam[ean][TG +: 33] = {21'(400 + wuser), 10'(wuser), 1'(wland), 1'b1}; wleft = wleft - 1; end
                    ean = ean + 1;
                end
            end
            if (k % 97 == 50 && gap_h > 16) begin
                stat = $urandom; t_host[76:65] = stat; gap_h = 0;
                eth[ethn] = tframe(3'd3, {stat, 1'b0, t_host[63:0]}); ethn = ethn + 1;
            end else if (gap_h > 16 && ($urandom % 8) == 0) begin
                td = {$urandom, $urandom}; t_host = {stat, 1'b1, td}; gap_h = 0;
                eth[ethn] = tframe(3'd3, {stat, 1'b1, td}); ethn = ethn + 1;
            end
            if (k % 23 == 7) begin
                t_kd = {1'b1, 21'($urandom), 32'd0};
                etk[etkn] = tframe(3'd4, {23'd0, t_kd}); etkn = etkn + 1;
            end
        end
        @(negedge clk); d_ro = 0; t_host[64] = 1'b0; t_kd = 0;
        repeat (3000) @(posedge clk);
        // replay of the landed user 2 (die seq_host slot) on M
        rdone = nmr;
        @(negedge clk); m_rc = {10'd2, 1'b1}; @(negedge clk); m_rc = 0;
        repeat (400) @(posedge clk);
        f_main = {m_f, r_f, m_lf};
        // ---- offline H -> die checks
        ok = 1; ii = 0; jj = 0; idc = 0;
        if (nrr != gn) begin ok = 0; $display("R ri count %0d exp %0d", nrr, gn); end
        for (k = 0; k < gn && k < nrr; k = k + 1) begin
            if (rrd[k] !== gs[k]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH R ri %0d", k); end
            if (gl[k]) begin
                if (jj >= nml || mld_[jj] !== gt[k] || mlc[jj] != rrc[k]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH M landed %0d (ring %0d) cyc %0d vs R %0d", jj, k, mlc[jj], rrc[k]); end
                jj = jj + 1;
            end else begin
                if (ii >= rdone || mrd[ii] !== gs[k] || mrt[ii] !== grt[k] || mrc[ii] != rrc[k]) begin
                    bad = bad + 1; if (bad < 8) $display("MISMATCH M ri %0d (ring %0d) rt %h exp %h cyc %0d vs R %0d", ii, k, mrt[ii], grt[k], mrc[ii], rrc[k]);
                end else idc = idc + 1;
                ii = ii + 1;
            end
        end
        if (ii != rdone || jj != nml || nml != NB) begin ok = 0; $display("M cut %0d/%0d landed %0d (exp %0d)", ii, rdone, jj, nml); end
        rp_i = rdone;                                                 // replay: user 2's landed beats, in order
        for (k = 0; k < gn; k = k + 1) if (gl[k]) begin
            if (rp_i >= nmr || mrd[rp_i] !== gs[k] || mrt[rp_i] !== grt[k]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH M replay %0d", rp_i - rdone); end
            rp_i = rp_i + 1;
        end
        if (rp_i != nmr || nmr - rdone != NB) begin ok = 0; $display("M replay %0d beats exp %0d", nmr - rdone, NB); end
        // ---- die -> H: both peers saw the same frame count at the same cycles
        if (km_ != kr_) begin ok = 0; $display("peer frames M %0d R %0d", km_, kr_); end
        for (k = 0; k < km_ && k < kr_; k = k + 1) if (fmc[k] != frc[k]) begin xbad = xbad + 1; if (xbad < 8) $display("MISMATCH die->H frame %0d cycle M %0d R %0d", k, fmc[k], frc[k]); end
        if (m_eak != ean || r_eak != ean || m_ethk != ethn || r_ethk != ethn || m_etkk != etkn || r_etkk != etkn) ok = 0;
        if (ehk != ehn || ekk != ekn) ok = 0;
        $display("LEPMUH_STATS H->die ring %0d (M cut %0d same-cycle %0d, landed %0d, replayed %0d) host %0d/%0d ks %0d/%0d | die->H ring %0d/%0d/%0d thost %0d/%0d/%0d tkd %0d/%0d/%0d frames M %0d R %0d | mismatch rx %0d tx %0d hostplane %0d | faults %b",
            gn, ii, idc, jj, nmr - rdone, ehk, ehn, ekk, ekn, m_eak, r_eak, ean, m_ethk, r_ethk, ethn, m_etkk, r_etkk, etkn, km_, kr_,
            bad, xbad, hid, f_main[2:0]);
        // ---- F1: a non-XB ring beat inside a TX window on M -> fault
        ncyc = 1;
        @(negedge clk); m_mc = {21'd9, 10'd1, 1'b0, 1'b0, 1'b1}; @(negedge clk); m_mc = 0;
        repeat (3) @(negedge clk);
        b = rnd(0); b[0] = 1'b1; b[3:1] = 3'd5; m_ro_x = b; @(negedge clk); m_ro_x = 0;
        repeat (20) @(negedge clk);
        f1 = m_f;
        if (ok && bad == 0 && xbad == 0 && hid == 0 && f_main[2:0] == 0 && f1)
            $display("PASS lep_muh: host-plane MU endpoint == single-user lep: %0d H->die ring beats (%0d cut-through same cycle+bits with mu_rt, %0d landed + replayed), %0d HOST + %0d KS identical every cycle; die->H %0d frames same cycles (%0d ring incl. %0d stamped, %0d THOST, %0d TKD); F1 faulted",
                gn, ii, NB, ehn, ekn, km_, ean, 2 * NB, ethn, etkn);
        else
            $display("FAIL lep_muh: ok %0d rx %0d tx %0d hostplane %0d faults %b F1 %0d", ok, bad, xbad, hid, f_main[2:0], f1);
        $finish;
    end
    initial begin #(0.8333 * (WAIT + 30000)); $display("FAIL lep_muh: TIMEOUT"); $finish; end
endmodule
