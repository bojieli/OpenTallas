`timescale 1ns/1ps
// DRIVE-S81-ATTN1 (10-20): lockstep bench of the S81 attention engine with ONE physical tile (ot_hdc_v41x_attn_s NTP 1:
// 4 virtual tiles time-multiplexed) against the as-built engine (NTP 0 = 4 tiles), both at the production dsdv_svc_att
// parameters (H16 D32 TD32 NL4 TROWS640 PWORDS2 ILV1 REPL2 NSTAGE2 FPL4 FML6 TILE_S1 NARROW1 MFAN1 TRX1 F12 FX5,
// SC_CRED 0, PV_CRED 0; TEXT 0 so the tiles are inside).
//
// MODE +static=0 (default, LOCK): the same job sequence (NJOB jobs, T from the seed incl. 640 / 46 / 1 / 33 tails, random
//   q / KV / p words) is offered to both engines through their own elastic drivers (random bubbles +bub=<pct>); every
//   score beat (row, mask, 16 heads x 4 rows FP32, flags) and every P.V beat (c, 4 tiles x 16 heads FP32, flags) of the
//   DUT must equal the reference's, in order, and the counts must match: ATTN1LOCK ... mismatches=0.
// MODE +static=1 (PROBE, the compiled program of dsdv_svc_att, one job): job at rc 0, q heads 1..16, row beats 1..ceil(T/4)
//   (any refusal counted), p steps (2 words) offered at the FIXED cycles P0 + PACE k with no look at p_ready (PACE 1 for
//   the reference, +pace=<n> for the DUT); prints per engine refused steps, the last score beat and the last P.V beat
//   (rc), and checks the DUT's beats bit-exact vs the reference's (both run the same data).
// Parameters: NMUT (DUT negative control, ot_hdc_v41x_attn_s NMUT), NTP (DUT physical tiles, 1 or 2).
module tb_attn1_nt1;
    integer guardstress=0; integer gi[0:1]; integer glast[0:1];
    parameter integer NMUT = 0;
    parameter integer NTP = 1;
    localparam integer H = 16, D = 32, TD = 32, NL = 4, NT = 4, R = TD / H;
    localparam integer QW = D * 16, KW = NL * 265, PW = 2 * TD * 16;
    localparam integer SCW = 16 + NL + NL*H*32 + NL*H, PVW = 8 + NT*H*32 + NT*H;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer seed = 1, njob = 12, bub = 20, st = 0, tst = 640, p0r = 0, p0d = 0, pace = 4, maxcyc = 400000;
    integer cyc = 0;

    // ---------------- stimulus store (shared by both engines) ----------------
    localparam integer MJ = 64, MQ = MJ * 16, MK = MJ * 160, MP = MJ * 160;
    reg [15:0] jt [0:MJ-1];
    reg [QW-1:0] qs [0:MQ-1];
    reg [KW-1:0] ks [0:MK-1];
    reg [NL-1:0] km [0:MK-1];
    reg [PW-1:0] ps [0:MP-1];
    integer nq = 0, nk = 0, np = 0;
    function automatic [31:0] rnd32(input integer dummy); rnd32 = $urandom; endfunction
    task automatic gen();
        integer j, t, i, b, w;
        for (j = 0; j < njob; j = j + 1) begin
            case (j % 6)
                0: t = 640; 1: t = 46; 2: t = 1 + ($urandom % 640); 3: t = 33; 4: t = 1 + ($urandom % 96); default: t = 1;
            endcase
            if (st != 0) t = tst;
            if (guardstress != 0) t = 4;
            jt[j] = 16'(t);
            for (i = 0; i < 16; i = i + 1) begin
                for (w = 0; w < QW / 32; w = w + 1) qs[nq][32*w +: 32] = guardstress ? ((j==0)?32'h3c003c00:32'h40004000) : rnd32(0);
                nq = nq + 1;
            end
            for (b = 0; b < (t + 3) / 4; b = b + 1) begin
                for (w = 0; w < (KW + 31) / 32; w = w + 1) ks[nk][32*w +: 32] = rnd32(0);
                if (guardstress != 0) begin
                    ks[nk]='0;
                    for(integer lane=0;lane<4;lane++)begin
                        ks[nk][265*lane+:256]={32{8'h38}};
                        ks[nk][265*lane+256+:8]=8'd127;
                    end
                end
                // group words: format bit 264 random per lane, scale random
                km[nk] = (4 * (b + 1) <= t) ? 4'hf : 4'((1 << (t - 4 * b)) - 1);
                nk = nk + 1;
            end
            for (b = 0; b < (((t + R - 1) / R) + 1) / 2; b = b + 1) begin
                for (w = 0; w < PW / 32; w = w + 1) ps[np][32*w +: 32] = rnd32(0);
                // p words are FP16 probabilities: keep them finite-ish (exponent < 31) so the sums carry values, not
                // only NaN; a few raw words stay unconstrained (flags path)
                if ($urandom % 8 != 0)
                    for (w = 0; w < PW / 16; w = w + 1) ps[np][16*w + 14] = 1'b0;
                np = np + 1;
            end
        end
    endtask

    // ---------------- two engines ----------------
    wire [1:0] j_rdy, q_rdy, k_rdy, p_rdy;
    reg  [1:0] j_v = 0, q_v = 0, k_v = 0, p_v = 0;
    reg  [15:0] j_t [0:1];
    reg  [QW-1:0] q_w [0:1];
    reg  [KW-1:0] k_w [0:1];
    reg  [NL-1:0] k_m [0:1];
    reg  [PW-1:0] p_w [0:1];
    wire [1:0] sc_v, pv_v;
    wire [SCW-1:0] sc_d [0:1];
    wire [PVW-1:0] pv_d [0:1];
    genvar e;
    generate for (e = 0; e < 2; e = e + 1) begin : g_e
        wire [15:0] sr; wire [NL-1:0] sm; wire [NL*H*32-1:0] sy; wire [NL*H-1:0] sf;
        wire [7:0] pc; wire [NT*H*32-1:0] py; wire [NT*H-1:0] pf;
        ot_hdc_v41x_attn_s #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(640), .SRAM_MACRO(0), .PWORDS(2),
                             .ILV(1), .REPL(2), .NSTAGE(2), .FPL(4), .FML(6), .NBANKP(0), .TILE_S(1),
                             .NARROW(1), .MFAN(1), .TRX(1), .F12(1), .FPLX(5),
                             .SC_CRED(0), .PV_CRED(0), .TEXT(0), .TLX(0), .TXD(0),
                             .NTP((e == 0) ? 0 : NTP), .NMUT((e == 0) ? 0 : NMUT)) u_eng (
            .clk(clk), .rst_n(rst_n), .job_v(j_v[e]), .job_t(j_t[e]), .job_ready(j_rdy[e]),
            .q_v(q_v[e]), .q_w(q_w[e]), .q_ready(q_rdy[e]),
            .kv_v(k_v[e]), .kv_m(k_m[e]), .kv_w(k_w[e]), .kv_ready(k_rdy[e]),
            .sc_v(sc_v[e]), .sc_row(sr), .sc_m(sm), .sc_y(sy), .sc_f(sf), .sc_cr(1'b0),
            .p_v(p_v[e]), .p_w(p_w[e]), .p_ready(p_rdy[e]),
            .pv_v(pv_v[e]), .pv_c(pc), .pv_y(py), .pv_f(pf), .pv_cr(1'b0),
            .qk_iss(), .pv_iss(), .tx_i(), .tx_o('0));
        assign sc_d[e] = {sr, sm, sy, sf};
        assign pv_d[e] = {pc, py, pf};
    end endgenerate

    // ---------------- elastic drivers (LOCK) / compiled program (PROBE) ----------------
    integer ji [0:1], qi [0:1], ki [0:1], pi_ [0:1];
    integer refused [0:1], prog_bad [0:1], last_sc [0:1], last_pv [0:1], first_pv [0:1], nsc [0:1], npv [0:1];
    integer ps_k [0:1];
    integer rc, x;
    initial for (x = 0; x < 2; x = x + 1) begin
        ji[x] = 0; qi[x] = 0; ki[x] = 0; pi_[x] = 0; refused[x] = 0; prog_bad[x] = 0; last_sc[x] = -1; last_pv[x] = -1;
        gi[x]=-1;glast[x]=-1;first_pv[x] = -1; nsc[x] = 0; npv[x] = 0; ps_k[x] = 0;
    end
    // scoreboards: reference beats in order
    localparam integer SBN = 65536;
    reg [SCW-1:0] sc_ref [0:SBN-1];
    reg [PVW-1:0] pv_ref [0:SBN-1];
    integer mism = 0, sc_mis = 0, pv_mis = 0;
    integer expected_sc = 0, expected_pv = 0, incomplete = 0;

    initial begin
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("njob=%d", njob)) ;
        if ($value$plusargs("bub=%d", bub)) ;
        if ($value$plusargs("static=%d", st)) ;
        if ($value$plusargs("t=%d", tst)) ;
        if ($value$plusargs("p0r=%d", p0r)) ;
        if ($value$plusargs("p0d=%d", p0d)) ;
        if ($value$plusargs("pace=%d", pace)) ;
        if ($value$plusargs("maxcyc=%d", maxcyc)) ;
        if ($value$plusargs("guardstress=%d",guardstress)) ;
        if(guardstress != 0)begin njob=2;bub=0;end
        if (st != 0) njob = 1;
        x = $urandom(seed);
        gen();
        for(integer job=0;job<njob;job++) expected_sc+=(jt[job]+NL-1)/NL;
        expected_pv=(D/(NL*(D/TD)))*njob;
        $display("ATTN1 cfg seed=%0d njob=%0d bub=%0d static=%0d t=%0d nq=%0d nk=%0d np=%0d NTP=%0d NMUT=%0d",
                 seed, njob, bub, st, tst, nq, nk, np, NTP, NMUT);
    end

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        rc = cyc - 10;
        if(guardstress && rst_n)begin
          if(gi[0]<0 && g_e[0].u_eng.qk_go && g_e[0].u_eng.qk_row+NL>=g_e[0].u_eng.T)gi[0]=rc;
          if(gi[1]<0 && g_e[1].u_eng.qk_go && g_e[1].u_eng.qk_row+NL>=g_e[1].u_eng.T)gi[1]=rc;
        end
        if(rst_n && rc>=-1)begin
        for (x = 0; x < 2; x = x + 1) begin
            // Trace first last-QK issue and the exact first stationary-Q load of the next job.
            if(q_v[x] && q_rdy[x] && qi[x]==16)
                $display("GUARD_TURN e=%0d qload_rc=%0d first_last_issue=%0d delta=%0d",x,rc,gi[x],rc-gi[x]);
            // handshakes of the cycle that ends now
            if (j_v[x] && j_rdy[x]) ji[x] = ji[x] + 1;
            if (q_v[x] && q_rdy[x]) qi[x] = qi[x] + 1;
            if (k_v[x] && k_rdy[x]) ki[x] = ki[x] + 1;
            if (p_v[x] && p_rdy[x]) pi_[x] = pi_[x] + 1;
            if (st != 0) begin
                if ((j_v[x] && !j_rdy[x]) || (q_v[x] && !q_rdy[x]) || (k_v[x] && !k_rdy[x])) prog_bad[x] = prog_bad[x] + 1;
                if (p_v[x] && !p_rdy[x]) refused[x] = refused[x] + 1;
                if (p_v[x]) ps_k[x] = ps_k[x] + 1;
            end
            // next offers
            if (st == 0) begin
                j_v[x] <= (ji[x] < njob) && ($urandom % 100 >= bub);
                j_t[x] <= jt[ji[x] < MJ ? ji[x] : 0];
                q_v[x] <= (qi[x] < nq) && ($urandom % 100 >= bub) &&
                    (!(guardstress && qi[x]==16) || (gi[x]>=0 && rc+1>=gi[x]+guardstress));
                q_w[x] <= qs[qi[x] < MQ ? qi[x] : 0];
                k_v[x] <= (ki[x] < nk) && ($urandom % 100 >= bub);
                k_w[x] <= ks[ki[x] < MK ? ki[x] : 0]; k_m[x] <= km[ki[x] < MK ? ki[x] : 0];
                p_v[x] <= (pi_[x] < np) && ($urandom % 100 >= bub);
                p_w[x] <= ps[pi_[x] < MP ? pi_[x] : 0];
            end else begin
                j_v[x] <= (rc + 1 == 0); j_t[x] <= jt[0];
                q_v[x] <= (rc + 1 >= 1 && rc + 1 <= 16); q_w[x] <= qs[(rc + 1 >= 1 && rc + 1 <= 16) ? rc : 0];
                k_v[x] <= (rc + 1 >= 1 && rc + 1 <= nk); k_w[x] <= ks[(rc + 1 >= 1 && rc + 1 <= nk) ? rc : 0];
                k_m[x] <= km[(rc + 1 >= 1 && rc + 1 <= nk) ? rc : 0];
                // compiled p feed: step k at rc P0 + PACE k
                if (ps_k[x] < np && rc + 1 >= ((x == 0) ? p0r : p0d) &&
                    ((rc + 1 - ((x == 0) ? p0r : p0d)) % ((x == 0) ? 1 : pace)) == 0) begin
                    p_v[x] <= 1'b1; p_w[x] <= ps[ps_k[x]];
                end else p_v[x] <= 1'b0;
            end
            // outputs
            if (sc_v[x]) begin
                if (x == 0) sc_ref[nsc[0] % SBN] = sc_d[0];
                nsc[x] = nsc[x] + 1; last_sc[x] = rc;
            end
            if (pv_v[x]) begin
                if (x == 0) pv_ref[npv[0] % SBN] = pv_d[0];
                npv[x] = npv[x] + 1; last_pv[x] = rc; if (first_pv[x] < 0) first_pv[x] = rc;
            end
        end
        end
        // DUT beats vs reference beats (reference is never behind: it is the 4-tile engine; checked)
        if (sc_v[1]) begin
            if (nsc[1] > nsc[0]) begin mism = mism + 1; if (mism <= 8) $display("MISMATCH sc beat %0d before the reference", nsc[1] - 1); end
            else if (sc_d[1] !== sc_ref[(nsc[1] - 1) % SBN]) begin
                mism = mism + 1; sc_mis = sc_mis + 1;
                if (mism <= 8) $display("MISMATCH sc beat %0d row %0d/%0d rc %0d", nsc[1] - 1, sc_d[1][SCW-1 -: 16],
                                        sc_ref[(nsc[1] - 1) % SBN][SCW-1 -: 16], rc);
            end
        end
        if (pv_v[1]) begin
            if (npv[1] > npv[0]) begin mism = mism + 1; if (mism <= 8) $display("MISMATCH pv beat %0d before the reference", npv[1] - 1); end
            else if (pv_d[1] !== pv_ref[(npv[1] - 1) % SBN]) begin
                mism = mism + 1; pv_mis = pv_mis + 1;
                if (mism <= 8) $display("MISMATCH pv beat %0d c %0d/%0d rc %0d", npv[1] - 1, pv_d[1][PVW-1 -: 8],
                                        pv_ref[(npv[1] - 1) % SBN][PVW-1 -: 8], rc);
            end
        end
        if (rc == maxcyc || (rc > 2000 && last_pv[1] >= 0 && last_pv[0] >= 0 && rc > last_pv[1] + 3000 && rc > last_sc[1] + 3000
                             && (st != 0 || (pi_[0] >= np && pi_[1] >= np)))) begin
            incomplete = (nsc[0] != expected_sc || nsc[1] != expected_sc || npv[0] != expected_pv || npv[1] != expected_pv);
            for (integer engine = 0; engine < 2; engine = engine + 1) begin
                if (ji[engine] != njob || qi[engine] != nq || ki[engine] != nk || pi_[engine] != np) incomplete = 1;
                if (st != 0 && (prog_bad[engine] != 0 || refused[engine] != 0)) incomplete = 1;
            end
            $display("ATTN1_COMPLETE expected_sc=%0d expected_pv=%0d incomplete=%0d inputs0=%0d/%0d/%0d/%0d inputs1=%0d/%0d/%0d/%0d", expected_sc, expected_pv, incomplete,
                     ji[0], qi[0], ki[0], pi_[0], ji[1], qi[1], ki[1], pi_[1]);
            if (st != 0)
                $display("ATTN1PROBE T=%0d p0r=%0d p0d=%0d pace=%0d ref: refused=%0d prog_bad=%0d last_sc=%0d first_pv=%0d last_pv=%0d | dut: refused=%0d prog_bad=%0d last_sc=%0d first_pv=%0d last_pv=%0d | d_sc=%0d d_pv=%0d",
                         tst, p0r, p0d, pace, refused[0], prog_bad[0], last_sc[0], first_pv[0], last_pv[0],
                         refused[1], prog_bad[1], last_sc[1], first_pv[1], last_pv[1],
                         last_sc[1] - last_sc[0], last_pv[1] - last_pv[0]);
            $display("ATTN1LOCK cycles=%0d sc=%0d/%0d pv=%0d/%0d mismatches=%0d sc_mis=%0d pv_mis=%0d %s",
                     rc, nsc[1], nsc[0], npv[1], npv[0],
                     mism + incomplete,
                     sc_mis, pv_mis,
                     (mism == 0 && incomplete == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
