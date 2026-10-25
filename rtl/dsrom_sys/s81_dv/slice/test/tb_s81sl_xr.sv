`timescale 1ns/1ps
// S81-SLICE control-plane bench (lane S81U-XR, 2026-10-17): ONE real hardened master (ot_s81sl_xr1, or ot_s81sl_xr3 with
// HB = 1) against an independent transaction model of the slice contract (results/rtl/s81_slice_1017/SLICE_CONTRACT.md
// section 3 + the xr header), cycle exact on every output.
//
// Stimulus: a statically scheduled random program (no ready / credit anywhere): the generator plays the compiler and only
// issues what fits its reservation tables -- one ci inject slot per cycle (V CTL re-injection, SC relay, packed send), one
// sw write per leaf per cycle (RD unpack pairs, CTL row writes), one partial collection at a time, one mine CTL / RD / lo
// beat per cycle -- plus noise beats that must be ignored (other slices' CTL / RD / CL, XQ / XB / NX, non-CTL V kinds,
// SC with relay off, invalid lanes carrying random data).
// Model latencies (slot n = outputs after the n-th edge; inputs of cycle n are sampled at that edge), as generated below
//   (XR1 single-stage timing): CTL decode (c / x_go / is / cfg / row write) n+1;  V CTL re-inject and SC relay on ci n+1;
//   RD pair j n+2+j;  packed send (last lo beat) n+2;  partial j to xfin n+2+j;  rstd fan n+1.
// S81U-XR2 (10-17) adds the classify stage: check() compares ci / bo / c / sw / x_go / is / cfg one slot later (XL = 1),
//   i.e. CTL n+2, V re-inject / SC relay n+2, RD pair j n+3+j, packed send n+3; partials and rstd are unchanged.
// Checks every cycle: ci_dir, ci_b[0], c_v, sw_v, x_go, x_sv, rb_v, is_v, cfg_v, fault (= 0), bo (HB: whole word); payloads
// whenever their valid is up (ci_b / bo: the unused pack words of a short send are stale don't-care).
// Then 13 illegal programs (14 on C3: BIND mu4 10-19 adds a dir-B send config with pairs > 2), each from reset, must raise
// the sticky fault.  Band port B (C3) is 513 b = {pk[511:0], valid}: legal B configs carry at most 2 pairs.
// Prints XRB ... err=<n> and PASS / FAIL.  Mutants (RTL): +define+OT_S81SL_XR_MUT_{HOPS,ROW,PORDER,NOCOL,XHOLD} must FAIL.
// OT_XR_LAND_TB (S81-KITS-RTLB 10-24, xrt FACE_LAND = 1): the lo / p leaf inputs land in a pin register first (+1 edge),
// so the compiler issues every lo beat and partial set ONE cycle earlier (drive uses program cycle m + 1 for lo / p, the
// cycle-0 entries go out in one pre-cycle); the expected model is unchanged.  Illegal cases 4 and 12 issue their lo beat
// one cycle earlier for the same reason.
module tb_s81sl_xr #(parameter integer HB = 0, parameter integer SEED = 1, parameter integer NC = 6000);
    localparam integer W = 1104, V = 276, BW = 513, NS = NC + 16;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    // ---------------------------------------------------------------- DUT
    reg rst_n = 1'b0; reg [3:0] sid = 4'd0;
    reg dl_ev = 0, dl_wv = 0, dl_vv = 0; reg [W-1:0] dl_e = 0, dl_w = 0, bi = 0; reg [V-1:0] dl_vb = 0;
    reg [4:0] lo_v = 0, p_v = 0; reg [1279:0] lo_d = 0; reg [159:0] p_d = 0; reg x_rbv = 0; reg [31:0] x_rbd = 0;
    wire [2:0] ci_dir; wire [W-1:0] ci_b; wire [BW-1:0] bo; wire [4:0] c_v, sw_v; wire rb_v; wire [159:0] c_d; wire [49:0] sw_a;
    wire [39:0] sw_m; wire [1279:0] sw_d; wire [31:0] rb_d; wire [159:0] is_d, cfg_d; wire x_go, x_sv, is_v, cfg_v, fault;
    wire [31:0] x_eps, x_s; wire [7:0] x_si;
    // ENG ports (RTL-BUILD-S81 10-18): idle here (the ENG collector is covered by tb_s81sl_slice_eng); x_mode / x_scale are
    // checked on every x_go; g_v must stay 0.
    reg [4:0] e_v = 0; reg [9:0] e_c = 0; reg [479:0] e_d = 0; reg eg_v = 0; reg [1:0] eg_c = 0; reg [31:0] eg_d = 0;
    wire g_v; wire [1:0] g_c; wire [31:0] g_d; wire x_mode; wire [31:0] x_scale;   // XR3: g_* one copy (slice glue fan-out)
    generate if (HB != 0) begin : g3
        ot_s81sl_xr3 u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
            .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi(bi), .bo(bo), .c_v(c_v), .c_d(c_d),
            .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d),
            .rb_v(rb_v), .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v),
            .g_c(g_c), .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_scale(x_scale), .x_eps(x_eps), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv),
            .x_rbd(x_rbd), .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
    end else begin : g1
        ot_s81sl_xr1 u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
            .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .c_v(c_v), .c_d(c_d),
            .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d),
            .rb_v(rb_v), .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v),
            .g_c(g_c), .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_scale(x_scale), .x_eps(x_eps), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv),
            .x_rbd(x_rbd), .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
        assign bo = {BW{1'b0}};
    end endgenerate
    // ---------------------------------------------------------------- random (xorshift64, seeded)
    reg [63:0] rs;
    function automatic [31:0] r32();
        rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); r32 = rs[31:0];
    endfunction
    function automatic [1119:0] rw();
        integer q; for (q = 0; q < 35; q = q + 1) rw[32 * q +: 32] = r32();
    endfunction
    function automatic integer ru(input integer n); ru = r32() % n; endfunction
    // ---------------------------------------------------------------- program (inputs per cycle) and expected (per slot)
    reg i_ev [0:NS-1]; reg i_wv [0:NS-1]; reg i_vv [0:NS-1]; reg [W-1:0] i_e [0:NS-1]; reg [W-1:0] i_w [0:NS-1];
    reg [W-1:0] i_b [0:NS-1]; reg [V-1:0] i_vb [0:NS-1]; reg [4:0] i_lov [0:NS-1]; reg [1279:0] i_lod [0:NS-1];
    reg [4:0] i_pv [0:NS-1]; reg [159:0] i_pd [0:NS-1]; reg i_rbv [0:NS-1]; reg [31:0] i_rbd [0:NS-1];
    reg x_civ [0:NS-1]; reg [2:0] x_cidir [0:NS-1]; reg [W-1:0] x_cib [0:NS-1]; reg [W-1:0] x_cim [0:NS-1];
    reg [BW-1:0] x_bo [0:NS-1]; reg [BW-1:0] x_bom [0:NS-1];
    reg [4:0] x_cv [0:NS-1]; reg [159:0] x_cd [0:NS-1]; reg [4:0] x_swv [0:NS-1]; reg [49:0] x_swa [0:NS-1];
    reg [39:0] x_swm [0:NS-1]; reg [1279:0] x_swd [0:NS-1]; reg x_go_e [0:NS-1]; reg [31:0] x_eps_e [0:NS-1];
    reg x_mode_e [0:NS-1]; reg [31:0] x_scale_e [0:NS-1];
    reg x_isv [0:NS-1]; reg [159:0] x_isd [0:NS-1]; reg x_cfgv [0:NS-1]; reg [159:0] x_cfgd [0:NS-1];
    reg x_xsv [0:NS-1]; reg [7:0] x_xsi [0:NS-1]; reg [31:0] x_xs [0:NS-1]; reg x_rbv_e [0:NS-1]; reg [31:0] x_rbd_e [0:NS-1];
    reg r_ci [0:NS-1]; reg [4:0] r_sw [0:NS-1];
    // beats
    function automatic [W-1:0] ctl_beat(input [15:0] mask, input [4:0] tgt, input [4:0] lm, input [159:0] body);
        reg [1119:0] t; begin
            t = rw(); ctl_beat = t[W-1:0];
            ctl_beat[0] = 1'b1; ctl_beat[3:1] = 3'd0; ctl_beat[21 +: 16] = mask; ctl_beat[37 +: 5] = tgt;
            ctl_beat[42 +: 5] = lm; ctl_beat[47 +: 160] = body;
        end
    endfunction
    function automatic [W-1:0] rd_beat(input [2:0] kind, input [15:0] mask, input [2:0] leaf, input [9:0] row,
                                       input [1:0] np, input [1023:0] d);
        reg [1119:0] t; begin
            t = rw(); rd_beat = t[W-1:0];
            rd_beat[0] = 1'b1; rd_beat[3:1] = kind; rd_beat[21 +: 16] = mask; rd_beat[37 +: 3] = leaf; rd_beat[40 +: 10] = row;
            rd_beat[50 +: 2] = np; rd_beat[52 +: 1024] = d;
        end
    endfunction
    function automatic [15:0] mine_mask(); mine_mask = r32() | (16'd1 << sid); endfunction
    function automatic [15:0] other_mask(); other_mask = r32() & ~(16'd1 << sid); endfunction
    // ---------------------------------------------------------------- generator + model (the compiler's view)
    integer nbs = 0;
    integer n, k, j, nctl = 0, nrd = 0, nsend = 0, nvre = 0, nsc = 0, npart = 0, nrw = 0, nlo = 0;
    // send config: pending (issued at cycle cp_n, effective from cp_n + 1) and effective
    reg cp_on; integer cp_n; reg [159:0] cp_b; reg ef_on; reg [3:0] ef_dir; reg [2:0] ef_kind; reg [4:0] ef_hops;
    reg [15:0] ef_mask; reg [2:0] ef_leaf; reg [9:0] ef_row; reg [1:0] ef_np; reg ef_scv;
    integer pn; reg [1023:0] pkm; integer pfree;
    task automatic gen();
        reg [1119:0] t; reg [159:0] body; reg [4:0] tgt, lm; reg e_used, w_used, v_used, nolo, ok; integer src, np, lf;
        reg [W-1:0] bt; reg [1023:0] d; reg [255:0] w256; reg [W-1:0] mk;
        begin
            for (n = 0; n < NS; n = n + 1) begin
                t = rw(); i_e[n] = t[W-1:0]; t = rw(); i_w[n] = t[W-1:0]; t = rw(); i_vb[n] = t[V-1:0];
                i_ev[n] = 0; i_wv[n] = 0; i_vv[n] = 0; i_b[n] = 0; i_lov[n] = 0; t = rw(); i_lod[n] = {t, t[159:0]};
                i_pv[n] = 0; t = rw(); i_pd[n] = t[159:0]; i_rbv[n] = 0; i_rbd[n] = r32();
                if (HB != 0) begin t = rw(); i_b[n] = t[W-1:0]; i_b[n][0] = 1'b0; end
                x_civ[n] = 0; x_cidir[n] = 0; x_cib[n] = 0; x_cim[n] = 0; x_bo[n] = 0; x_bom[n] = {BW{1'b1}};
                x_cv[n] = 0; x_cd[n] = 0; x_swv[n] = 0; x_swa[n] = 0; x_swm[n] = 0; x_swd[n] = 0; x_go_e[n] = 0; x_mode_e[n] = 0; x_scale_e[n] = 0;
                x_eps_e[n] = 0; x_isv[n] = 0; x_isd[n] = 0; x_cfgv[n] = 0; x_cfgd[n] = 0; x_xsv[n] = 0; x_xsi[n] = 0;
                x_xs[n] = 0; x_rbv_e[n] = 0; x_rbd_e[n] = 0; r_ci[n] = 0; r_sw[n] = 0;
            end
            cp_on = 0; ef_on = 0; ef_scv = 0; pn = 0; pkm = 0; pfree = 0;
            for (n = 0; n < NC; n = n + 1) begin
                if (cp_on && cp_n == n - 1) begin
                    cp_on = 0; ef_on = 1; ef_dir = cp_b[3:0]; ef_kind = cp_b[6:4]; ef_hops = cp_b[11:7]; ef_mask = cp_b[27:12];
                    ef_leaf = cp_b[30:28]; ef_row = cp_b[40:31]; ef_np = cp_b[42:41]; ef_scv = cp_b[43];
                end
                e_used = 0; w_used = 0; v_used = 0; nolo = 0;
                // ---- one CTL for this slice
                if (ru(100) < 30) begin
                    src = ru(3); tgt = ru(6); lm = r32(); t = rw(); body = t[159:0]; ok = 1;
                    if (n < 4 || (!ef_on && !cp_on)) tgt = 5'd4;
                    if (tgt == 5'd4) begin
                        ok = (pn == 0) && !cp_on;
                        body[43] = ru(3) == 0;
                        if (HB != 0 && body[3]) body[42] = 1'b0;     // B: at most 2 pairs (513-b band word)
                    end
                    if (tgt == 5'd5) begin
                        if (lm == 0) lm = 5'd1 << ru(5);
                        for (k = 0; k < 5; k = k + 1) if (lm[k] && r_sw[n + 1][k]) ok = 0;
                    end
                    if (src == 2 && r_ci[n + 1]) src = ru(2);
                    if (ok) begin
                        bt = ctl_beat(mine_mask(), tgt, lm, body); nctl = nctl + 1;
                        if (src == 0) begin i_ev[n] = 1; i_e[n] = bt; e_used = 1; end
                        else if (src == 1) begin i_wv[n] = 1; i_w[n] = bt; w_used = 1; end
                        else begin
                            i_vv[n] = 1; i_vb[n] = bt[V-1:0]; v_used = 1; r_ci[n + 1] = 1; nvre = nvre + 1;
                            x_civ[n + 1] = 1; x_cidir[n + 1] = 3'b011; x_cim[n + 1] = {W{1'b1}};
                            x_cib[n + 1] = 0; x_cib[n + 1][V-1:0] = bt[V-1:0]; x_cib[n + 1][8:4] = 5'd0;
                        end
                        case (tgt)
                            5'd0: begin x_cv[n + 1] = lm; x_cd[n + 1] = body; end
                            5'd1: begin x_go_e[n + 1] = 1; x_eps_e[n + 1] = body[31:0]; x_mode_e[n + 1] = body[32];
                                         x_scale_e[n + 1] = body[95:64]; end
                            5'd2: begin x_isv[n + 1] = 1; x_isd[n + 1] = body; end
                            5'd3: begin x_cfgv[n + 1] = 1; x_cfgd[n + 1] = body; end
                            5'd4: begin cp_on = 1; cp_n = n; cp_b = body; nolo = 1; end
                            default: begin
                                nrw = nrw + 1;
                                for (k = 0; k < 5; k = k + 1) if (lm[k]) begin
                                    r_sw[n + 1][k] = 1; x_swv[n + 1][k] = 1; x_swa[n + 1][10 * k +: 10] = body[9:0];
                                    x_swm[n + 1][8 * k +: 8] = {4'd0, body[13:10]}; x_swd[n + 1][256 * k +: 256] = {128'd0, body[141:14]};
                                end
                            end
                        endcase
                    end
                end
                // ---- V: other slices' CTL (re-injected, not decoded) or non-CTL kinds (ignored)
                if (!v_used && ru(100) < 15) begin
                    t = rw(); body = t[159:0];
                    if (!r_ci[n + 1] && ru(2) == 0) begin
                        bt = ctl_beat(other_mask(), ru(6), r32(), body);
                        i_vv[n] = 1; i_vb[n] = bt[V-1:0]; r_ci[n + 1] = 1; nvre = nvre + 1;
                        x_civ[n + 1] = 1; x_cidir[n + 1] = 3'b011; x_cim[n + 1] = {W{1'b1}};
                        x_cib[n + 1] = 0; x_cib[n + 1][V-1:0] = bt[V-1:0]; x_cib[n + 1][8:4] = 5'd0;
                    end else begin
                        i_vv[n] = 1; i_vb[n][3:1] = 3'd1 + ru(7);
                    end
                end
                // ---- RD / CL for this slice (E, W, or B on C3) into a leaf unpacker
                if (ru(100) < 22) begin
                    src = ru(HB != 0 ? 3 : 2); lf = ru(5); np = ru(4); ok = 1;
                    if ((src == 0 && e_used) || (src == 1 && w_used)) ok = 0;
                    for (j = 0; j <= np; j = j + 1) if (r_sw[n + 2 + j][lf]) ok = 0;
                    if (ok) begin
                        t = rw(); d = {t[1023:0]};
                        bt = rd_beat(ru(2) ? 3'd4 : 3'd6, mine_mask(), lf, r32(), np, d); nrd = nrd + 1;
                        if (src == 0) begin i_ev[n] = 1; i_e[n] = bt; e_used = 1; end
                        else if (src == 1) begin i_wv[n] = 1; i_w[n] = bt; w_used = 1; end
                        else begin i_b[n] = bt; end
                        for (j = 0; j <= np; j = j + 1) begin
                            r_sw[n + 2 + j][lf] = 1; x_swv[n + 2 + j][lf] = 1;
                            x_swa[n + 2 + j][10 * lf +: 10] = bt[40 +: 10] + 2 * j; x_swm[n + 2 + j][8 * lf +: 8] = 8'hff;
                            x_swd[n + 2 + j][256 * lf +: 256] = d[256 * j +: 256];
                        end
                    end
                end
                // ---- SC (router scores): relayed to V when the relay bit is on, else ignored
                if (ru(100) < 10 && !(e_used && w_used)) begin
                    ok = !ef_scv || !r_ci[n + 1];
                    if (ok) begin
                        t = rw(); bt = t[W-1:0]; bt[0] = 1; bt[3:1] = 3'd5;
                        if (!e_used) begin i_ev[n] = 1; i_e[n] = bt; e_used = 1; end
                        else begin i_wv[n] = 1; i_w[n] = bt; w_used = 1; end
                        if (ef_scv) begin
                            r_ci[n + 1] = 1; nsc = nsc + 1; x_civ[n + 1] = 1; x_cidir[n + 1] = 3'b100; x_cim[n + 1] = {W{1'b1}};
                            x_cib[n + 1] = 0; x_cib[n + 1][V-1:0] = bt[V-1:0];
                        end
                    end
                end
                // ---- noise on free E / W lanes: other slices' CTL / RD / CL, XQ / XB / NX
                if (!e_used && ru(3) == 0) begin
                    i_ev[n] = 1; j = ru(5);
                    if (j == 0) i_e[n] = ctl_beat(other_mask(), ru(6), r32(), i_e[n][159:0]);
                    else if (j == 1) i_e[n] = rd_beat(ru(2) ? 3'd4 : 3'd6, other_mask(), ru(5), r32(), ru(4), i_e[n][1023:0]);
                    else i_e[n][3:1] = j - 1;
                end
                if (!w_used && ru(3) == 0) begin
                    i_wv[n] = 1; j = ru(5);
                    if (j == 0) i_w[n] = ctl_beat(other_mask(), ru(6), r32(), i_w[n][159:0]);
                    else if (j == 1) i_w[n] = rd_beat(ru(2) ? 3'd4 : 3'd6, other_mask(), ru(5), r32(), ru(4), i_w[n][1023:0]);
                    else i_w[n][3:1] = j - 1;
                end
                // ---- lo row pairs from the beat leaves -> packed send
                if (ef_on && !nolo && ru(100) < 35) begin
                    ok = (pn != ef_np) || !r_ci[n + 2];
                    if (ok) begin
                        lf = ru(5); i_lov[n] = 5'd1 << lf; w256 = i_lod[n][256 * lf +: 256]; pkm[256 * pn +: 256] = w256;
                        nlo = nlo + 1;
                        if (pn == ef_np) begin
                            r_ci[n + 2] = 1; nsend = nsend + 1;
                            bt = 0; bt[0] = 1; bt[3:1] = ef_kind; bt[8:4] = ef_hops; bt[12:9] = sid; bt[21 +: 16] = ef_mask;
                            bt[37 +: 3] = ef_leaf; bt[40 +: 10] = ef_row; bt[50 +: 2] = ef_np; bt[52 +: 1024] = pkm;
                            mk = {W{1'b1}};
                            for (j = 52 + 256 * (ef_np + 1); j < 52 + 1024; j = j + 1) mk[j] = 1'b0;
                            if (ef_dir[2:0] != 3'd0) begin
                                x_civ[n + 2] = 1; x_cidir[n + 2] = ef_dir[2:0]; x_cib[n + 2] = bt; x_cim[n + 2] = mk;
                            end
                            if (HB != 0 && ef_dir[3]) begin
                                x_bo[n + 2] = {pkm[511:0], 1'b1}; x_bom[n + 2] = {BW{1'b1}};
                                if (ef_np == 0) for (j = 257; j < BW; j = j + 1) x_bom[n + 2][j] = 1'b0;
                                nbs = nbs + 1;
                            end
                            pn = 0;
                        end else pn = pn + 1;
                    end
                end
                // ---- the 5 norm partials (one set, all leaves at once) -> xfin in leaf order
                if (n >= pfree && ru(100) < 6) begin
                    i_pv[n] = 5'b11111; pfree = n + 6; npart = npart + 1;
                    for (j = 0; j < 5; j = j + 1) begin
                        x_xsv[n + 2 + j] = 1; x_xsi[n + 2 + j] = j; x_xs[n + 2 + j] = i_pd[n][32 * j +: 32];
                    end
                end
                // ---- xfin rstd -> the 5 vn
                if (ru(100) < 10) begin
                    i_rbv[n] = 1; x_rbv_e[n + 1] = 1; x_rbd_e[n + 1] = i_rbd[n];
                end
            end
        end
    endtask
    // ---------------------------------------------------------------- drive / check
    integer err = 0, nerr_pr = 0;
    // XR1F-PIN (10-19): x_eps / x_scale / x_mode are config registers -- they must HOLD the last CTL target-1 value on
    // every cycle (not only on the x_go cycle): checked every slot once a first write landed (catches MUT_XHOLD).
    reg h_on = 1'b0; reg h_mode = 1'b0; reg [31:0] h_eps = 32'd0, h_scale = 32'd0;
    task automatic bad(input [8*16-1:0] what, input integer s);
        begin err = err + 1; if (nerr_pr < 12) begin nerr_pr = nerr_pr + 1; $display("MISMATCH %0s slot=%0d", what, s); end end
    endtask
    task automatic drive(input integer m);
        begin
            dl_ev = i_ev[m]; dl_e = i_e[m]; dl_wv = i_wv[m]; dl_w = i_w[m]; dl_vv = i_vv[m]; dl_vb = i_vb[m]; bi = i_b[m];
`ifdef OT_XR_LAND_TB
            if (m + 1 < NS) begin lo_v = i_lov[m + 1]; lo_d = i_lod[m + 1]; p_v = i_pv[m + 1]; p_d = i_pd[m + 1]; end
            else begin lo_v = 0; p_v = 0; end
            x_rbv = i_rbv[m]; x_rbd = i_rbd[m];
`else
            lo_v = i_lov[m]; lo_d = i_lod[m]; p_v = i_pv[m]; p_d = i_pd[m]; x_rbv = i_rbv[m]; x_rbd = i_rbd[m];
`endif
        end
    endtask
    task automatic idle();
        begin
            dl_ev = 0; dl_wv = 0; dl_vv = 0; bi = 0; lo_v = 0; p_v = 0; x_rbv = 0;
        end
    endtask
    task automatic check(input integer s);
        integer d;
        begin
            d = (s > 0) ? s - 1 : 0;      // XL = 1: the classify stage (S81U-XR2) delays every CTL / RD / lo / V / SC output
            if (ci_dir !== x_cidir[d]) bad("ci_dir", d);
            if (ci_b[0] !== x_civ[d]) bad("ci_v", d);
            if (x_civ[d] && ((ci_b ^ x_cib[d]) & x_cim[d]) != 0) bad("ci_b", d);
            if (((bo ^ x_bo[d]) & x_bom[d]) != 0) bad("bo", d);
            if (c_v !== x_cv[d]) bad("c_v", d);
            for (k = 0; k < 5; k = k + 1) if (x_cv[d][k] && c_d !== x_cd[d]) bad("c_d", d);
            if (sw_v !== x_swv[d]) bad("sw_v", d);
            for (k = 0; k < 5; k = k + 1) if (x_swv[d][k] && (sw_a[10 * k +: 10] !== x_swa[d][10 * k +: 10] ||
                sw_m[8 * k +: 8] !== x_swm[d][8 * k +: 8] || sw_d[256 * k +: 256] !== x_swd[d][256 * k +: 256])) bad("sw", d);
            if (x_go !== x_go_e[d] || (x_go_e[d] && x_eps !== x_eps_e[d])) bad("x_go", d);
            if (x_go_e[d] && (x_mode !== x_mode_e[d] || x_scale !== x_scale_e[d])) bad("x_mode", d);
            if (x_go_e[d]) begin h_on = 1'b1; h_eps = x_eps_e[d]; h_scale = x_scale_e[d]; h_mode = x_mode_e[d]; end
            if (h_on && (x_eps !== h_eps || x_scale !== h_scale || x_mode !== h_mode)) bad("x_hold", d);
            if (g_v !== 1'b0) bad("g_v", s);
            if (is_v !== x_isv[d] || (x_isv[d] && is_d !== x_isd[d])) bad("is", d);
            if (cfg_v !== x_cfgv[d] || (x_cfgv[d] && cfg_d !== x_cfgd[d])) bad("cfg", d);
            if (x_sv !== x_xsv[s] || (x_xsv[s] && (x_si !== x_xsi[s] || x_s !== x_xs[s]))) bad("x_s", s);
            if (rb_v !== x_rbv_e[s] || (x_rbv_e[s] && rb_d !== x_rbd_e[s])) bad("rb", s);
            if (fault !== 1'b0) bad("fault", s);
        end
    endtask
    task automatic do_reset();
        begin
            @(negedge clk); rst_n = 0; idle(); repeat (4) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        end
    endtask
    // illegal programs: each from reset, must leave fault = 1
    reg [W-1:0] cfgb; integer cs, nfail_ill = 0, nill;
    task automatic cfg_send(input scv);
        reg [159:0] b; begin
            b = 0; b[3:0] = 4'b0001; b[42:41] = 2'd0; b[43] = scv;
            dl_ev = 1; dl_e = ctl_beat(mine_mask(), 5'd4, 5'd0, b); @(negedge clk); idle(); @(negedge clk);
        end
    endtask
    task automatic illegal(input integer c);
        reg [1119:0] t; reg [159:0] b14; begin
            do_reset(); t = rw();
            case (c)
                1: begin dl_ev = 1; dl_e = ctl_beat(mine_mask(), 2, 0, 0); dl_wv = 1; dl_w = ctl_beat(mine_mask(), 3, 0, 0); end
                2: begin dl_ev = 1; dl_e = rd_beat(4, mine_mask(), 2, 0, 3, t[1023:0]); @(negedge clk);
                         dl_e = rd_beat(4, mine_mask(), 2, 8, 0, t[1023:0]); end
                3: begin dl_ev = 1; dl_e = rd_beat(4, mine_mask(), 1, 0, 3, t[1023:0]); @(negedge clk);
                         dl_e = ctl_beat(mine_mask(), 5, 5'b00010, 0); end
`ifdef OT_XR_LAND_TB
                4: begin b14 = 0; b14[3:0] = 4'b0001; dl_ev = 1; dl_e = ctl_beat(mine_mask(), 5'd4, 5'd0, b14); @(negedge clk);
                         idle(); lo_v = 5'b00001; @(negedge clk); idle(); @(negedge clk); dl_vv = 1; dl_vb = ctl_beat(other_mask(), 0, 0, 0); end
`else
                4: begin cfg_send(0); lo_v = 5'b00001; @(negedge clk); idle(); dl_vv = 1; dl_vb = ctl_beat(other_mask(), 0, 0, 0); end
`endif
                5: begin p_v = 5'b11111; @(negedge clk); p_v = 0; @(negedge clk); p_v = 5'b11111; end
                6: begin p_v = 5'b00111; end
                7: begin cfg_send(0); lo_v = 5'b00011; end
                8: begin dl_ev = 1; dl_e = rd_beat(4, mine_mask(), 0, 0, 0, t[1023:0]);
                         dl_wv = 1; dl_w = rd_beat(6, mine_mask(), 1, 0, 0, t[1023:0]); end
                9: begin dl_ev = 1; dl_e = rd_beat(4, mine_mask(), 6, 0, 0, t[1023:0]); end
                10: begin dl_ev = 1; dl_e = ctl_beat(mine_mask(), 7, 0, 0); end
                11: begin cfg_send(1); dl_ev = 1; dl_e = 0; dl_e[3:1] = 5; dl_wv = 1; dl_w = 0; dl_w[3:1] = 5; end
`ifdef OT_XR_LAND_TB
                12: begin b14 = 0; b14[3:0] = 4'b0001; dl_ev = 1; dl_e = ctl_beat(mine_mask(), 5'd4, 5'd0, b14); @(negedge clk);
                          idle(); lo_v = 5'b00100; @(negedge clk); idle(); dl_ev = 1; dl_e = ctl_beat(mine_mask(), 4, 0, 0); end
`else
                12: begin cfg_send(0); dl_ev = 1; dl_e = ctl_beat(mine_mask(), 4, 0, 0); lo_v = 5'b00100; end
`endif
                14: begin b14 = 0; b14[3:0] = 4'b1000; b14[42:41] = 2'd2; dl_ev = 1; dl_e = ctl_beat(mine_mask(), 5'd4, 5'd0, b14); end
                default: begin cfg_send(1); dl_ev = 1; dl_e = 0; dl_e[3:1] = 5; dl_vv = 1; dl_vb = ctl_beat(other_mask(), 0, 0, 0); end
            endcase
            @(negedge clk); idle(); repeat (8) @(negedge clk);
            $display("XRFAULT case=%0d fault=%0d", c, fault);
            if (fault !== 1'b1) nfail_ill = nfail_ill + 1;
        end
    endtask
    initial begin
        rs = 64'h9e3779b97f4a7c15 ^ SEED; for (n = 0; n < 8; n = n + 1) k = r32();
        sid = ru(16);
        gen();
        do_reset();
`ifdef OT_XR_LAND_TB
        idle(); lo_v = i_lov[0]; lo_d = i_lod[0]; p_v = i_pv[0]; p_d = i_pd[0]; @(negedge clk);   // lo / p of cycle 0, one early
`endif
        for (n = 0; n < NS; n = n + 1) begin
            drive(n); @(negedge clk); check(n);
        end
        $display("XRB hb=%0d seed=%0d sid=%0d cycles=%0d ctl=%0d rd=%0d rowwr=%0d lo=%0d sends=%0d vreinj=%0d screl=%0d parts=%0d err=%0d",
            HB, SEED, sid, NS, nctl, nrd, nrw, nlo, nsend, nvre, nsc, npart, err);
        nill = (HB != 0) ? 14 : 13;
        for (cs = 1; cs <= nill; cs = cs + 1) illegal(cs);
        $display("XRILL missed=%0d of %0d bsends=%0d", nfail_ill, nill, nbs);
        if (err == 0 && nfail_ill == 0 && nsend > 50 && nrd > 200 && nvre > 100 && nsc > 20 && npart > 20 && (HB == 0 || nbs > 10)) $display("PASS");
        else $display("FAIL");
        $finish;
    end
endmodule
