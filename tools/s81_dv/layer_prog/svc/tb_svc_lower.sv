`timescale 1ns/1ps
// LB2-S81/CC-svc (10-18): the svc attention-job bench of the layer compiler.  The 16 REAL regional service slices
// dsdv_svc_rs (p4j entries 5 / 11; protect-lib builds, the same slices tb_dsdv_svc_rs runs), driven ONLY by what
// tools/s81_dv/layer_prog/lower_svc.py emits for the layer, at the compiler's cycles:
//   meta.hex  [0] q words, [1] T, [2] / [3] j cycle at the W / E entry, [4] / [5] job word lo / hi, [6] HBM sectors,
//             [7] expected first P.V word cycle, [8] / [12] expected jd done cycle at the E / W entry, [9] GO cycle,
//             [10] PV frame cycle, [11] ST
//   qcyc.hex / qwd.hex  every q word and the cycle it is driven on BOTH entries' q pins (die: {fault 0, live 0, d, v})
//   hkey.hex / hdat.hex the HBM window image (127 rows before the position) in the slices' own PCs
//   sc.hex    expected q.k scores [T] x 16 heads (golden dots of the fixture q / rows; scaled = fixture attn.scores)
//   pv.hex    expected P.V [512 dims] x 16 heads (= fixture attn.pv, bit-exact)
//   meta [13] PMODE (TOK-S81-GAPS/SVCP 10-19: P produced ON-DIE -- GO PIO != 0, no host PV frame), [14] NPW = words of
//             the PV frame;  pexp.hex = that frame (header + ceil(T / 2) words, word w = rows 2w, 2w + 1 x 16 heads
//             BF16 = bf16(fixture attn.exp)).  PMODE checks: every root P beat (after the T / 4 score beats) bit-exact
//             (head lanes {P, 16'h0}, flags 0, row tag), the PV frame on BOTH entries' dn stream (child face) exactly
//             once, back to back, every word bit-exact; plus all the checks above (P.V of the on-die P bit-exact).
// Cycle convention (tb_dsdv_svc_rs): the tb drives a value at cycle c (non-blocking), the pin holds it from the next
// edge.  HBM is the elastic off-die boundary: per-PC request queue, <= 8 outstanding (DQ credits), latency lat + rand.
// Checks (PASS = all): every complete root score beat (all T rows: window-only job, every row held) bit-exact and in
// order; every slice's SE operand rows (16 rows of its head = tile) bit-exact; the SM head writes one row per SE row;
// the quarter-ST P.V: 160 words at the half-PVH entry pins, back to back, FIRST WORD AT THE COMPILED CYCLE, every value
// bit-exact; one jd done per entry AT THE COMPILED CYCLE, no jd fault, no slice fault, HBM credits <= 8; the PV frame
// after the last fold score.
`ifndef RS_OBS
`define RS_OBS
`endif
`define RS_ENT_MOD dsdv_svc_rs_entry_pl
`define RS_SL_MOD dsdv_svc_rs_pl
module tb_svc_lower;
    parameter integer DIE = 0;
    parameter integer ST = 0;
    parameter integer MAXCYC = 20000;
`include "dsdv_svc_rs_roles.svh"
    localparam integer H = 16, D = 512, NHBM = 8192, QMAX = 4096;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst = 0;
    reg [31:0] meta [0:31];
    reg [31:0] qcyc [0:QMAX-1];
    reg [511:0] qwd [0:QMAX-1];
    reg [63:0] hkey [0:NHBM-1];
    reg [255:0] hdat [0:NHBM-1];
    reg [H*33-1:0] scm [0:639];
    reg [H*33-1:0] pvm [0:D-1];
    reg [255:0] hbm [longint];
    reg [1023:0] dir;
    integer seed = 1, lat = 40;
    integer NQ, T, JW, JE, NH, EXP_PV0, EXP_DONE, EXP_DONE_W, GO_C, PV_C, i, PMODE, NPW;
    reg [511:0] pexp [0:511];
    reg [32:0] JWORD;
    function automatic integer tile_of(input integer sd); reg [21:0] r; r = rs_role(4'(sd)); tile_of = r[3:0]; endfunction
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("lat=%d", lat)) ;
        $readmemh({dir, "/meta.hex"}, meta);
        NQ = meta[0]; T = meta[1]; JW = meta[2]; JE = meta[3]; JWORD = {meta[5][0], meta[4]}; NH = meta[6];
        EXP_PV0 = meta[7]; EXP_DONE = meta[8]; GO_C = meta[9]; PV_C = meta[10]; EXP_DONE_W = meta[12];
        PMODE = meta[13]; NPW = meta[14];
        if (PMODE != 0) $readmemh({dir, "/pexp.hex"}, pexp, 0, NPW - 1);
        if (meta[11] != ST) begin $display("image ST %0d != bench ST %0d", meta[11], ST); $finish; end
        $readmemh({dir, "/qcyc.hex"}, qcyc, 0, NQ - 1);
        $readmemh({dir, "/qwd.hex"}, qwd, 0, NQ - 1);
        $readmemh({dir, "/hkey.hex"}, hkey, 0, NH - 1);
        $readmemh({dir, "/hdat.hex"}, hdat, 0, NH - 1);
        $readmemh({dir, "/sc.hex"}, scm, 0, T - 1);
        $readmemh({dir, "/pv.hex"}, pvm);
        for (i = 0; i < NH; i = i + 1) hbm[hkey[i]] = hdat[i];
        void'($urandom(seed));
        $display("SVCLOW_IMG dir=%0s nq=%0d T=%0d jW=%0d jE=%0d go=%0d pv_frame=%0d exp_pv0=%0d exp_done=%0d hbm=%0d seed=%0d",
                 dir, NQ, T, JW, JE, GO_C, PV_C, EXP_PV0, EXP_DONE, NH, seed);
    end

    // ---------------- 16 slices (tb_dsdv_svc_rs wiring, abutted faces) ----------------
    localparam integer W = 2132, SW = 1076, DW = 805, UW = 16;
    wire [3:0] gi_v [0:15], go_v [0:15], si_v [0:15], so_v [0:15];
    wire [4*W-1:0] gi_d [0:15], go_d [0:15]; wire [4*SW-1:0] si_d [0:15], so_d [0:15];
    wire [4*DW-1:0] dn_i [0:15], dn_o [0:15]; wire [4*UW-1:0] up_i [0:15], up_o [0:15];
    wire [2*341-1:0] rq [0:15]; reg [1:0] rk [0:15], wd [0:15], rv [0:15];
    reg [2*256-1:0] r_data [0:15]; reg [2*17-1:0] r_tag [0:15]; reg [2*4-1:0] r_beat [0:15];
    wire [15:0] pv_v, w_v; wire [512:0] pv_d [0:15]; wire [13:0] w_a [0:15]; wire [15:0] w_m [0:15];
    wire [511:0] w_d [0:15]; wire [11:0] w_st [0:15];
    reg [32:0] jcmd [0:1]; reg q_v = 0; reg [511:0] q_d = 0;
    wire [1:0] jdx [0:1]; wire [8:0] hcx [0:1]; wire [1:0] rfx; wire [1:0] stx [0:1];
    wire [4*514-1:0] ri [0:15], ro [0:15];
    reg [1:0] hsv [0:15];
    initial begin jcmd[0] = 0; jcmd[1] = 0; for (int k = 0; k < 16; k++) hsv[k] = 2'b01; end
    wire [2678:0] obs [0:15];
    function automatic integer nb(input integer sd, input integer fc);
        integer r, c;
        r = sd % 2; c = sd / 2;
        case (fc)
            0: nb = (r == 0) ? 2*c + 1 : -1;
            1: nb = (c < 7) ? 2*(c+1) + r : -1;
            2: nb = (r == 1) ? 2*c : -1;
            default: nb = (c > 0) ? 2*(c-1) + r : -1;
        endcase
    endfunction
    genvar gs, gf;
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_s
        for (gf = 0; gf < 4; gf = gf + 1) begin : g_f
            localparam integer NBS = nb(gs, gf), OF = (gf + 2) % 4;
            if (NBS >= 0) begin : g_c
                assign gi_v[gs][gf] = go_v[NBS][OF]; assign gi_d[gs][W*gf +: W] = go_d[NBS][W*OF +: W];
                assign si_v[gs][gf] = so_v[NBS][OF]; assign si_d[gs][SW*gf +: SW] = so_d[NBS][SW*OF +: SW];
                assign dn_i[gs][DW*gf +: DW] = dn_o[NBS][DW*OF +: DW]; assign up_i[gs][UW*gf +: UW] = up_o[NBS][UW*OF +: UW];
                assign ri[gs][514*gf +: 514] = ro[NBS][514*OF +: 514];
            end else begin : g_e
                assign gi_v[gs][gf] = 1'b0; assign gi_d[gs][W*gf +: W] = '0;
                assign si_v[gs][gf] = 1'b0; assign si_d[gs][SW*gf +: SW] = '0;
                assign dn_i[gs][DW*gf +: DW] = '0; assign up_i[gs][UW*gf +: UW] = '0;
                assign ri[gs][514*gf +: 514] = '0;
            end
        end
        if (gs == RS_ENTRY_W || gs == RS_ENTRY_E) begin : g_r
            localparam integer HX = (gs == RS_ENTRY_E) ? 1 : 0;
            // die.v: .q({2'd0, w_q_*_l1_lnd[236:0], w_q_*_l0_lnd[275:0]}), hw idle (no host sector writes in this job)
            `RS_ENT_MOD u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .j(jcmd[HX]), .jd(jdx[HX]), .q({2'b00, q_d, q_v}), .hw(292'd0), .hc(hcx[HX]), .fault(rfx[HX]), .st_rg(stx[HX]),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]), .ri(ri[gs]), .ro(ro[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(hsv[gs]), .pv_v(pv_v[gs]), .pv_d(pv_d[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]), .obs(obs[gs]));
        end else begin : g_n
            `RS_SL_MOD u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]), .ri(ri[gs]), .ro(ro[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(hsv[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]), .obs(obs[gs]));
            assign pv_v[gs] = 1'b0; assign pv_d[gs] = '0;
        end
    end endgenerate
    wire [15:0] sflt; wire [31:0] afc [0:15];
    wire [15:0] se_v; wire [511:0] se_d [0:15]; wire [15:0] rt_vv; wire [2131:0] rt_dd [0:15];
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_p
        assign sflt[gs] = obs[gs][0]; assign afc[gs] = obs[gs][32:1];
        assign se_d[gs] = obs[gs][544:33]; assign se_v[gs] = obs[gs][545];
        assign rt_dd[gs] = obs[gs][2677:546]; assign rt_vv[gs] = obs[gs][2678];
    end endgenerate

    // ---------------- HBM: 32 PCs (tb_dsdv_svc_rs model) ----------------
    localparam integer PQ = 64;
    integer pq_t [0:31][0:PQ-1]; reg [340:0] pq_w [0:31][0:PQ-1]; integer pq_h [0:31], pq_n [0:31], pq_b [0:31];
    integer cred_err = 0, cyc = 0, hbm_wr = 0, hbm_rd = 0;
    initial for (i = 0; i < 32; i = i + 1) begin pq_h[i] = 0; pq_n[i] = 0; pq_b[i] = 0; end
    always @(posedge ck) begin
        reg [340:0] w341; reg [255:0] old; longint key; integer pc, sd, pp, jj;
        for (sd = 0; sd < 16; sd = sd + 1) begin rk[sd] <= 0; wd[sd] <= 0; rv[sd] <= 0; end
        for (pc = 0; pc < 32; pc = pc + 1) begin
            sd = pc / 2; pp = pc % 2;
            if (rq[sd][341*pp]) begin
                pq_t[pc][(pq_h[pc] + pq_n[pc]) % PQ] = cyc + lat + ($urandom % 16);
                pq_w[pc][(pq_h[pc] + pq_n[pc]) % PQ] = rq[sd][341*pp +: 341];
                pq_n[pc] = pq_n[pc] + 1;
                if (pq_n[pc] > 8) cred_err = cred_err + 1;
            end
            if (pq_n[pc] > 0 && pq_t[pc][pq_h[pc]] <= cyc) begin
                w341 = pq_w[pc][pq_h[pc]];
                key = (longint'(pc) << 32) | longint'(w341[31:2] + (w341[1] ? 0 : pq_b[pc]));
                if (w341[1]) begin
                    old = hbm.exists(key) ? hbm[key] : 256'd0;
                    for (jj = 0; jj < 32; jj = jj + 1) if (w341[53 + jj]) old[8*jj +: 8] = w341[85 + 8*jj +: 8];
                    hbm[key] = old; wd[sd][pp] <= 1'b1; rk[sd][pp] <= 1'b1; hbm_wr = hbm_wr + 1;
                    pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1;
                end else begin
                    rv[sd][pp] <= 1'b1; r_tag[sd][17*pp +: 17] <= w341[52:36]; r_beat[sd][4*pp +: 4] <= 4'(pq_b[pc]);
                    r_data[sd][256*pp +: 256] <= hbm.exists(key) ? hbm[key] : 256'd0;
                    if (pq_b[pc] + 1 == w341[35:32]) begin
                        pq_b[pc] = 0; pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1; rk[sd][pp] <= 1'b1; hbm_rd = hbm_rd + 1;
                    end else pq_b[pc] = pq_b[pc] + 1;
                end
            end
        end
    end

    // ---------------- run + checks ----------------
    integer qi = 0, late_q = 0, rt_beats = 0, sc_err = 0, sc_chk = 0, ord_err = 0;
    integer se_rows [0:15], se_err = 0, se_chk = 0, wrows [0:15];
    integer pv_err = 0, pv_chk = 0, pv_first = -1, pv_last = -1, pv_gap = 0, pv_other = 0, pv_n = 0;
    reg [7:0] pvc [0:15]; reg [63:0] pvf [0:15];
    integer first_rt = -1, last_rt = -1, done_c [0:1], n_done [0:1];
    integer p_first = -1, p_last = -1, p_beats = 0, p_err = 0, p_chk = 0, pf_err = 0, we_first [0:15], we_last [0:15];
    integer pf_i [0:1], pf_n [0:1], pf_c [0:1], pf_lc [0:1];
    initial for (i = 0; i < 16; i = i + 1) begin we_first[i] = -1; we_last[i] = -1; end
    initial for (i = 0; i < 2; i = i + 1) begin pf_i[i] = 0; pf_n[i] = 0; pf_c[i] = -1; pf_lc[i] = -1; end
    initial for (i = 0; i < 16; i = i + 1) begin se_rows[i] = 0; wrows[i] = 0; end
    initial begin done_c[0] = -1; done_c[1] = -1; n_done[0] = 0; n_done[1] = 0; end
    localparam integer PVH = (ST >= 2) ? 0 : 1;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst <= 1;
        jcmd[0] <= (cyc == JW) ? JWORD : 33'd0;
        jcmd[1] <= (cyc == JE) ? JWORD : 33'd0;
        for (int k = 0; k < 2; k++) if (jdx[k][0]) begin n_done[k] = n_done[k] + 1; done_c[k] = cyc; end
        // q stream: word qi exactly at its compiled cycle (never earlier, never later)
        q_v <= 0;
        if (qi < NQ && cyc == qcyc[qi]) begin q_v <= 1; q_d <= qwd[qi]; qi = qi + 1; end
        else if (qi < NQ && cyc > qcyc[qi]) late_q = late_q + 1;
        if (rt_vv[RS_FOLD] && PMODE != 0 && rt_beats >= (T + 3) / 4) begin
            // on-die P beat k = rt beat (T + 3) / 4 + k: rows 4k .. 4k + 3, head lane h = {bf16 P, 16'h0}
            reg [2131:0] b; integer r0, rr, h; reg [15:0] e16;
            b = rt_dd[RS_FOLD];
            r0 = b[2131:2116];
            if (p_first < 0) p_first = cyc; p_last = cyc;
            if (r0 != 4 * p_beats || b[63:0] != 64'd0) p_err = p_err + 1;
            for (rr = 0; rr < 4; rr = rr + 1) for (h = 0; h < H; h = h + 1) begin
                e16 = (r0 + rr < T) ? pexp[1 + (r0 + rr) / 2][16 * (((r0 + rr) % 2) * 16 + h) +: 16] : 16'd0;
                p_chk = p_chk + 1;
                if (b[64 + (rr*16 + h)*32 +: 32] !== {e16, 16'h0000}) begin
                    p_err = p_err + 1;
                    if (p_err < 8) $display("P MISMATCH root beat row %0d head %0d got %08x exp %04x0000", r0 + rr, h,
                        b[64 + (rr*16 + h)*32 +: 32], e16);
                end
            end
            p_beats = p_beats + 1;
        end else if (rt_vv[RS_FOLD]) begin
            reg [2131:0] b; integer r0, rr, h;
            b = rt_dd[RS_FOLD];
            r0 = b[2131:2116];
            if (first_rt < 0) first_rt = cyc; last_rt = cyc;
            if (r0 != 4 * rt_beats) ord_err = ord_err + 1;
            for (rr = 0; rr < 4; rr = rr + 1) if (r0 + rr < T) begin
                if (!b[2115 - 3 + rr]) sc_err = sc_err + 1;              // every row of a window-only job is held
                for (h = 0; h < H; h = h + 1) begin
                    sc_chk = sc_chk + 1;
                    if (b[64 + (rr*16 + h)*32 +: 32] !== scm[r0 + rr][h*33 +: 32] || b[rr*16 + h] !== scm[r0 + rr][h*33 + 32]) begin
                        sc_err = sc_err + 1;
                        if (sc_err < 8) $display("SC MISMATCH row %0d head %0d got %08x f%0d exp %08x f%0d", r0 + rr, h,
                            b[64 + (rr*16 + h)*32 +: 32], b[rr*16 + h], scm[r0 + rr][h*33 +: 32], scm[r0 + rr][h*33 + 32]);
                    end
                end
            end
            rt_beats = rt_beats + 1;
        end
        for (int s = 0; s < 16; s++) begin
            if (se_v[s]) begin
                integer rr, t; t = tile_of(s);
                for (rr = 0; rr < 16; rr = rr + 1) if (16 * se_rows[s] + rr < T) begin
                    se_chk = se_chk + 1;
                    if (se_d[s][32*rr +: 32] !== scm[16 * se_rows[s] + rr][t*33 +: 32]) begin
                        se_err = se_err + 1;
                        if (se_err < 8) $display("SE MISMATCH slice %0d row %0d got %08x exp %08x", s, 16 * se_rows[s] + rr,
                            se_d[s][32*rr +: 32], scm[16 * se_rows[s] + rr][t*33 +: 32]);
                    end
                end
                se_rows[s] = se_rows[s] + 1;
            end
            if (w_v[s]) wrows[s] = wrows[s] + 1;
            if (pv_v[s]) begin
                integer wi, t, dm, h;
                if (s != ((PVH == 1) ? RS_ENTRY_E : RS_ENTRY_W)) pv_other = pv_other + 1;
                else begin
                    t = 4 * ST + pv_n / 40; wi = pv_n % 5;
                    if (pv_first < 0) pv_first = cyc; else if (cyc != pv_last + 1) pv_gap = pv_gap + 1;
                    pv_last = cyc;
                    if (pv_n >= 160) pv_err = pv_err + 1;
                    else if (wi == 0) begin
                        if (!pv_d[s][512]) pv_err = pv_err + 1;
                        pvc[s] = pv_d[s][71:64]; pvf[s] = pv_d[s][63:0];
                    end else begin
                        if (pv_d[s][512]) pv_err = pv_err + 1;
                        dm = 32 * t + 8 * (wi - 1) + pvc[s];
                        for (h = 0; h < H; h = h + 1) begin
                            pv_chk = pv_chk + 1;
                            if (pv_d[s][32*h +: 32] !== pvm[dm][h*33 +: 32] || pvf[s][16 * (wi - 1) + h] !== pvm[dm][h*33 + 32]) begin
                                pv_err = pv_err + 1;
                                if (pv_err < 8) $display("PV MISMATCH entry %0d tile %0d dim %0d head %0d got %08x f%0d exp %08x f%0d", s, t, dm, h,
                                    pv_d[s][32*h +: 32], pvf[s][16 * (wi - 1) + h], pvm[dm][h*33 +: 32], pvm[dm][h*33 + 32]);
                            end
                        end
                    end
                    pv_n = pv_n + 1;
                end
            end
        end
        // PMODE: the PV frame on each entry's dn stream (11 -> 09 W face, 05 -> 07 E face) and the SM e-row cycles
        for (int s = 0; s < 16; s++) if (w_v[s]) begin if (we_first[s] < 0) we_first[s] = cyc; we_last[s] = cyc; end
        for (int k = 0; k < 2; k++) begin
            integer es, ef; reg [DW-1:0] dw;
            es = (k == 0) ? RS_ENTRY_W : RS_ENTRY_E; ef = (k == 0) ? 1 : 3;
            dw = dn_o[es][DW*ef +: DW];
            if (PMODE != 0 && dw[0]) begin
                if (pf_i[k] == 0 && dw[512:1] == pexp[0]) begin pf_i[k] = 1; pf_n[k] = pf_n[k] + 1; pf_c[k] = cyc; end
                else if (pf_i[k] > 0) begin
                    if (dw[512:1] !== pexp[pf_i[k]]) begin
                        pf_err = pf_err + 1;
                        if (pf_err < 8) $display("PF MISMATCH entry %0d word %0d", es, pf_i[k]);
                    end
                    if (cyc != pf_lc[k] + 1) pf_err = pf_err + 1;            // back to back
                    pf_i[k] = (pf_i[k] + 1 == NPW) ? 0 : pf_i[k] + 1;
                end
                pf_lc[k] = cyc;
            end else if (PMODE != 0 && pf_i[k] > 0) begin pf_err = pf_err + 1; pf_i[k] = 0; end   // a gap inside the frame
        end
        if ((n_done[0] > 0 && n_done[1] > 0 && cyc > done_c[0] + 300 && cyc > done_c[1] + 300) || cyc >= MAXCYC) begin
            integer bad_se, bad_w, sched_bad, pv_early; reg [15:0] fl; reg [31:0] fc0;
            bad_se = 0; bad_w = 0; fl = 0; fc0 = 0;
            for (int s = 0; s < 16; s++) begin
                if (se_rows[s] != (T + 15) / 16) bad_se = bad_se + 1;
                if (wrows[s] != se_rows[s]) bad_w = bad_w + 1;
                fl[s] = sflt[s]; if (sflt[s] && fc0 == 0) fc0 = afc[s];
            end
            pv_early = (PMODE == 0 && last_rt >= PV_C) ? 1 : 0;
            sched_bad = (pv_first != EXP_PV0) + (pv_last != EXP_PV0 + 159) + (done_c[0] != EXP_DONE_W) + (done_c[1] != EXP_DONE) +
                        (late_q != 0) + (qi != NQ) + pv_early;
            $display("SVCLOW_SCHED go=%0d pv_frame=%0d first_score=%0d last_score=%0d pv_first=%0d exp_pv_first=%0d pv_last=%0d done_W=%0d exp_done_W=%0d done_E=%0d exp_done_E=%0d n_done=%0d/%0d q_sent=%0d/%0d late_q=%0d pv_early=%0d hbm_wr=%0d hbm_rd=%0d sched_bad=%0d",
                GO_C, PV_C, first_rt, last_rt, pv_first, EXP_PV0, pv_last, done_c[0], EXP_DONE_W, done_c[1], EXP_DONE, n_done[0], n_done[1],
                qi, NQ, late_q, pv_early, hbm_wr, hbm_rd, sched_bad);
            begin
                integer wl_min, wl_max, wf_min; wl_min = 1 << 30; wl_max = -1; wf_min = 1 << 30;
                for (int s = 0; s < 16; s++) begin
                    if (we_last[s] < wl_min) wl_min = we_last[s]; if (we_last[s] > wl_max) wl_max = we_last[s];
                    if (we_first[s] >= 0 && we_first[s] < wf_min) wf_min = we_first[s];
                end
                $display("SVCLOW_P pmode=%0d go=%0d p_nominal=%0d erow_first=%0d erow_last_min=%0d erow_last_max=%0d p_beat_first=%0d p_beat_last=%0d pf_W=%0d pf_E=%0d pf_n=%0d/%0d p_beats=%0d p_checked=%0d p_errors=%0d pf_errors=%0d npw=%0d",
                    PMODE, GO_C, PV_C, wf_min, wl_min, wl_max, p_first, p_last, pf_c[0], pf_c[1], pf_n[0], pf_n[1], p_beats, p_chk, p_err, pf_err, NPW);
            end
            $display("SVCLOW die=%0d st=%0d T=%0d root_beats=%0d sc_checked=%0d sc_errors=%0d order_errors=%0d se_checked=%0d se_errors=%0d se_bad_slices=%0d sm_rows_bad=%0d pv_checked=%0d pv_errors=%0d pv_words=%0d pv_gaps=%0d pv_other_entry=%0d jd_fault=%0d root_fault=%0d slice_faults=%04x first_fault_code=%08x cred_err=%0d sched_bad=%0d cycles=%0d verdict=%s",
                DIE, ST, T, rt_beats, sc_chk, sc_err, ord_err, se_chk, se_err, bad_se, bad_w, pv_chk, pv_err, pv_n, pv_gap, pv_other,
                jdx[0][1] | jdx[1][1], rfx != 0, fl, fc0, cred_err, sched_bad, cyc,
                (sc_err == 0 && ord_err == 0 && rt_beats == (T + 3) / 4 && sc_chk == T * H && se_err == 0 && se_chk == 16 * T &&
                 bad_se == 0 && bad_w == 0 && pv_err == 0 && pv_chk == 4 * 8 * 4 * 16 && pv_n == 160 && pv_gap == 0 &&
                 pv_other == 0 && n_done[0] == 1 && n_done[1] == 1 && !jdx[0][1] && !jdx[1][1] && rfx == 0 && fl == 0 &&
                 cred_err == 0 && sched_bad == 0 && cyc < MAXCYC &&
                 (PMODE == 0 || (p_err == 0 && pf_err == 0 && p_beats == (T + 3) / 4 && p_chk == 64 * ((T + 3) / 4) &&
                                 pf_n[0] == 1 && pf_n[1] == 1 && pf_i[0] == 0 && pf_i[1] == 0))) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
