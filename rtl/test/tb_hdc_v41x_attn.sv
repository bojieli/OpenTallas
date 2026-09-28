`timescale 1ns/1ps
// Performance + bit-exactness bench of ot_hdc_v41x_attn against tools/hdc_golden_v41.py (chunk8), driven by
// tools/rtl_hdc_v41x_attn_campaign.py.  Jobs (one layer's attention each) run back to back:
//   job_v -> q (H words) -> KV rows (NL per beat, from row 0; after q when KV_AFTER_Q) -> scores out, compared
//   -> P_DELAY cycles after the job's last score (the stream unit's softmax barrier) the probabilities
//   stream in (one word per cycle) -> pv out, compared.
// BUB > 0 inserts random bubbles on every input stream and random credit-return delays (flow-control test).
// Files (+dir=<path>): jobs.hex {pv_off, sc_off, p_off, kv_off, T} x 32 bits, q.hex, kv.hex, p.hex, sc.hex, pv.hex.
// Prints per job  V41XJOB ...  and a summary  V41XATTN ...
module tb_hdc_v41x_attn (input wire clk);
    parameter integer H = 16;
    parameter integer D = 512;
    parameter integer TD = 64;
    parameter integer NL = 4;
    parameter integer TROWS = 640;
    parameter integer SRAM_MACRO = 0;
    parameter integer NJOBMAX = 2;
    parameter integer NKV = 1280;
    parameter integer NP = 320;
    parameter integer NSC = 1280;
    parameter integer NPV = 1024;
    parameter integer KV_AFTER_Q = 1;
    parameter integer P_DELAY = 0;
    parameter integer BUB = 0;             // percent
    parameter integer MAXCYC = 200000;
    localparam integer S = D / TD;
    localparam integer NT = NL * S;
    localparam integer DPT = D / NT;
    localparam integer G = D / 32;
    localparam integer ROWW = G * 265;
    localparam integer R = TD / H;

    reg [159:0]      jobs [0:NJOBMAX-1];
    reg [D*16-1:0]   qm   [0:NJOBMAX*H-1];
    integer NJOB = NJOBMAX;
    reg [ROWW-1:0]   kvm  [0:NKV-1];
    reg [TD*16-1:0]  pm   [0:NP-1];
    reg [H*33-1:0]   scm  [0:NSC-1];
    reg [H*33-1:0]   pvm  [0:NPV-1];
    reg [1023:0] dir;
    integer seed = 1;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("njob=%d", NJOB)) ;
        $readmemh({dir, "/jobs.hex"}, jobs);
        $readmemh({dir, "/q.hex"}, qm);
        $readmemh({dir, "/kv.hex"}, kvm);
        $readmemh({dir, "/p.hex"}, pm);
        $readmemh({dir, "/sc.hex"}, scm);
        $readmemh({dir, "/pv.hex"}, pvm);
    end
    function automatic integer jT(input integer j);   jT = jobs[j][15:0];      endfunction
    function automatic integer jKV(input integer j);  jKV = jobs[j][63:32];    endfunction
    function automatic integer jP(input integer j);   jP = jobs[j][95:64];     endfunction
    function automatic integer jSC(input integer j);  jSC = jobs[j][127:96];   endfunction
    function automatic integer jPV(input integer j);  jPV = jobs[j][159:128];  endfunction

    reg rst_n = 1'b0;
    integer cyc = 0;

    // ---- DUT ----
    reg job_v = 0; reg [15:0] job_t = 0; wire job_ready;
    reg q_v = 0; reg [D*16-1:0] q_w = 0; wire q_ready;
    reg kv_v = 0; reg [NL-1:0] kv_m = 0; reg [NL*ROWW-1:0] kv_w = 0; wire kv_ready;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    reg sc_cr = 0;
    reg p_v = 0; reg [TD*16-1:0] p_w = 0; wire p_ready;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
    reg pv_cr = 0;
    wire qk_iss, pv_iss;
    ot_hdc_v41x_attn #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(TROWS),
                        .SRAM_MACRO(SRAM_MACRO != 0)) dut (
        .clk(clk), .rst_n(rst_n), .job_v(job_v), .job_t(job_t), .job_ready(job_ready),
        .q_v(q_v), .q_w(q_w), .q_ready(q_ready), .kv_v(kv_v), .kv_m(kv_m), .kv_w(kv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(sc_cr),
        .p_v(p_v), .p_w(p_w), .p_ready(p_ready), .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f),
        .pv_cr(pv_cr), .qk_iss(qk_iss), .pv_iss(pv_iss));

    // ---- driver state ----
    integer dj = 0;             // job being driven
    integer st = 0;             // 0 wait job_ready, 1 q, 2 kv, 3 wait scores, 4 p, 5 done-driving
    integer qn = 0, kvr = 0, pn = 0, pwait = 0;
    integer enter [0:65535];    // entry cycle of each row of the job being driven (by row)
    integer sc_last_cyc [0:63];
    integer p_last_cyc [0:63];
    integer pv_last_cyc [0:63];
    integer qk_first [0:63], qk_last [0:63], pv_first [0:63], pv_last [0:63];
    integer qk_beats [0:63], pv_beats [0:63];
    // ---- checker state ----
    integer sj = 0, srows = 0;  // score job / rows received
    integer vj = 0, vdims = 0;  // pv job / dims received
    integer sc_chk = 0, sc_err = 0, pv_chk = 0, pv_err = 0, nflt = 0;
    integer lat_sc_max = 0, lat_sc_min = 1 << 30, lat_pv_max = 0;
    integer ij_qk = 0, ij_pv = 0;   // job of the issue counters
    integer qk_rows_iss = 0, pv_beats_iss = 0;
    integer sc_pend = 0, pv_pend = 0, sc_hold = 0, pv_hold = 0;
    integer i, l, h, k, tt, ok;

    function automatic bit bub();
        bub = (BUB > 0) && (($urandom % 100) < BUB);
    endfunction

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        // ---------------- drive ----------------
        job_v <= 1'b0;
        if (q_v && q_ready) begin qn = qn + 1; q_v <= 1'b0; end
        if (kv_v && kv_ready) begin
            for (l = 0; l < NL; l = l + 1) if (kv_m[l]) enter[kvr + l] = cyc;
            kvr = kvr + NL; kv_v <= 1'b0;
        end
        if (p_v && p_ready) begin pn = pn + 1; p_v <= 1'b0; p_last_cyc[dj] = cyc; end
        if (rst_n && dj < NJOB) begin
            case (st)
                0: if (job_ready && !job_v) begin
                       job_v <= 1'b1; job_t <= jT(dj); qn = 0; kvr = 0; pn = 0; st = 1;
                       qk_first[dj] = -1; pv_first[dj] = -1; qk_beats[dj] = 0; pv_beats[dj] = 0;
                   end
                default: ;
            endcase
            if (st >= 1 && st <= 4) begin
                // q words
                if (qn < H && !(q_v && !q_ready) && !bub()) begin
                    q_v <= 1'b1; q_w <= qm[dj * H + qn];
                end
                if (qn >= H) q_v <= 1'b0;
                // kv rows
                if ((KV_AFTER_Q == 0 || qn >= H) && kvr < jT(dj) && !bub()) begin
                    kv_v <= 1'b1;
                    for (l = 0; l < NL; l = l + 1) begin
                        kv_m[l] <= (kvr + l) < jT(dj);
                        kv_w[l*ROWW +: ROWW] <= ((kvr + l) < jT(dj)) ? kvm[jKV(dj) + kvr + l] : {ROWW{1'b0}};
                    end
                end
                // probabilities after the job's last score + P_DELAY
                if (sj > dj && pwait < P_DELAY) pwait = pwait + 1;
                if (sj > dj && pwait >= P_DELAY && pn < (jT(dj) + R - 1) / R && !bub()) begin
                    p_v <= 1'b1; p_w <= pm[jP(dj) + pn];
                end
                if (pn >= (jT(dj) + R - 1) / R && qn >= H && kvr >= jT(dj)) begin
                    dj = dj + 1; st = 0; pwait = 0;
                end
            end
        end
        // ---------------- issue counters ----------------
        if (qk_iss) begin
            if (qk_first[ij_qk] < 0) qk_first[ij_qk] = cyc;
            qk_last[ij_qk] = cyc; qk_beats[ij_qk] = qk_beats[ij_qk] + 1;
            qk_rows_iss = qk_rows_iss + NL;
            if (qk_rows_iss >= jT(ij_qk)) begin ij_qk = ij_qk + 1; qk_rows_iss = 0; end
        end
        if (pv_iss) begin
            if (pv_first[ij_pv] < 0) pv_first[ij_pv] = cyc;
            pv_last[ij_pv] = cyc; pv_beats[ij_pv] = pv_beats[ij_pv] + 1;
            pv_beats_iss = pv_beats_iss + 1;
            if (pv_beats_iss >= ((jT(ij_pv) + TD - 1) / TD) * DPT) begin ij_pv = ij_pv + 1; pv_beats_iss = 0; end
        end
        // ---------------- check scores ----------------
        sc_cr <= 1'b0;
        if (sc_v) begin
            sc_pend = sc_pend + 1;
            for (l = 0; l < NL; l = l + 1) if (sc_m[l]) begin
                tt = sc_row + l;
                for (h = 0; h < H; h = h + 1) begin
                    sc_chk = sc_chk + 1;
                    if (scm[jSC(sj) + tt][h*33 + 32]) begin
                        nflt = nflt + 1;
                        if (!sc_f[l*H + h]) begin
                            sc_err = sc_err + 1;
                            if (sc_err < 8) $display("SC MISS-FAULT job %0d row %0d head %0d", sj, tt, h);
                        end
                    end else if (sc_f[l*H + h] || sc_y[(l*H + h)*32 +: 32] !== scm[jSC(sj) + tt][h*33 +: 32]) begin
                        sc_err = sc_err + 1;
                        if (sc_err < 8) $display("SC MISMATCH job %0d row %0d head %0d got %08x f%0d exp %08x", sj, tt, h,
                                                 sc_y[(l*H + h)*32 +: 32], sc_f[l*H + h], scm[jSC(sj) + tt][h*33 +: 32]);
                    end
                end
                if (cyc - enter[tt] > lat_sc_max && sj == dj) lat_sc_max = cyc - enter[tt];
                if (cyc - enter[tt] < lat_sc_min && sj == dj) lat_sc_min = cyc - enter[tt];
                srows = srows + 1;
            end
            if (srows >= jT(sj)) begin sc_last_cyc[sj] = cyc; sj = sj + 1; srows = 0; end
        end
        if (sc_pend > 0) begin
            if (sc_hold > 0) sc_hold = sc_hold - 1;
            else begin sc_cr <= 1'b1; sc_pend = sc_pend - 1; if (BUB > 0) sc_hold = $urandom % 4; end
        end
        // ---------------- check pv ----------------
        pv_cr <= 1'b0;
        if (pv_v) begin
            pv_pend = pv_pend + 1;
            for (k = 0; k < NT; k = k + 1) begin
                tt = k * DPT + pv_c;
                for (h = 0; h < H; h = h + 1) begin
                    pv_chk = pv_chk + 1;
                    if (pvm[jPV(vj) + tt][h*33 + 32]) begin
                        nflt = nflt + 1;
                        if (!pv_f[k*H + h]) begin
                            pv_err = pv_err + 1;
                            if (pv_err < 8) $display("PV MISS-FAULT job %0d dim %0d head %0d", vj, tt, h);
                        end
                    end else if (pv_f[k*H + h] || pv_y[(k*H + h)*32 +: 32] !== pvm[jPV(vj) + tt][h*33 +: 32]) begin
                        pv_err = pv_err + 1;
                        if (pv_err < 8) $display("PV MISMATCH job %0d dim %0d head %0d got %08x f%0d exp %08x", vj, tt, h,
                                                 pv_y[(k*H + h)*32 +: 32], pv_f[k*H + h], pvm[jPV(vj) + tt][h*33 +: 32]);
                    end
                end
            end
            vdims = vdims + NT;
            if (vdims >= D) begin
                pv_last_cyc[vj] = cyc;
                if (cyc - p_last_cyc[vj] > lat_pv_max) lat_pv_max = cyc - p_last_cyc[vj];
                $display("V41XJOB job=%0d T=%0d qk_first=%0d qk_last=%0d qk_beats=%0d pv_first=%0d pv_last=%0d pv_beats=%0d last_score=%0d last_p=%0d last_pv=%0d",
                         vj, jT(vj), qk_first[vj], qk_last[vj], qk_beats[vj], pv_first[vj], pv_last[vj], pv_beats[vj],
                         sc_last_cyc[vj], p_last_cyc[vj], cyc);
                vj = vj + 1; vdims = 0;
            end
        end
        if (pv_pend > 0) begin
            if (pv_hold > 0) pv_hold = pv_hold - 1;
            else begin pv_cr <= 1'b1; pv_pend = pv_pend - 1; if (BUB > 0) pv_hold = $urandom % 4; end
        end
        if (vj >= NJOB || cyc >= MAXCYC) begin
            $display("V41XATTN jobs=%0d sc_checked=%0d sc_errors=%0d pv_checked=%0d pv_errors=%0d faults=%0d lat_score_max=%0d lat_score_min=%0d lat_pv_max=%0d cycles=%0d timeout=%0d",
                     vj, sc_chk, sc_err, pv_chk, pv_err, nflt, lat_sc_max, lat_sc_min, lat_pv_max, cyc, cyc >= MAXCYC);
            $finish;
        end
    end
endmodule
