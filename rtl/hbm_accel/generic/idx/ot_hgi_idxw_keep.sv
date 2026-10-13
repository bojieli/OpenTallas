`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX wide adapter, TILED form (ot_hgi_idx_index_wt): KEEP leaf.
// Held id chunk, the exact ordinal divide and rank match as SIX registered stages, the K-result FIFO, the one-match-a-
// cycle drain, the keep bitmap and the kin launch.  SPEC results/arch/hbm_b2_idx_ixw1_1013/SPEC.md "Tiled redesign".
// The walk is free-flowing: QCORE pops a C value chunk only against a K-result credit, so no stage ever stalls and the
// stage registers load every cycle (valid bits only).  A credit returns when the drain has emptied a FIFO entry.
//   H   id chunk held (load-enable copies, one a 64-bit slice); chunk-level range bounds:
//         dn = c_base - 32 * sector_hi,  e = c_base + c_n - 32 * sector_hi   (entry p is in range iff dn <= p < e)
//   K1  fields, slot / range / id-high / value tests (parallel compares), q5 = q + 4 q
//   K2  p85 = q5 + 16 q5                      (85 q)
//   K3  s   = 2 p85 + 512 p85                 (514 * 85 q = 43,690 q)
//   K4  ord = (s + q) >> 17                   (q * 43,691 >> 17 = floor(q / 3), exact below 2^16)
//   K5  t   = 3 ord (two low bits kept), ok and ord < 1,368
//   K6  match = ok and {q - t, lo} == rank    -> written straight into the result FIFO entry (registered write enables)
// kin leaves after the last C value chunk has drained (4 beats, one every 4 cycles); kin_sent goes back to QCORE, which
// holds the last query block until then.
// MUT 11 (bench): K4 drops the + q term (must FAIL).
module ot_hgi_idxw_keep #(
    parameter integer MUT = 0,
    parameter integer KFD = 8       // result FIFO depth (power of 2) = credits held by QCORE
) (
    input  wire          clk,
    input  wire          rst_n,
    // S2 (QCORE)
    input  wire [1023:0] kc_d_i,
    input  wire          kc_ci_i, kc_cv_i, kc_last_i,
    input  wire [1:0]    kc_slot_i,
    input  wire [2:0]    kc_cnt_i,
    input  wire [12:0]   kc_shi_i,
    input  wire          kstart_i,
    input  wire          keep_en_i,
    input  wire [6:0]    rank_i,
    input  wire [17:0]   c_base_i,
    input  wire [11:0]   c_n_i,
    output reg           kcr_o,
    output reg           kin_sent_o,
    // selector
    output wire [344:0]  kin_o
);
    localparam integer KB = $clog2(KFD);
    integer l, p;
    genvar gc, ge, gp, gr;
    // ---- reset
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    wire [2:0] rnc;
    generate for (gr = 0; gr < 3; gr = gr + 1) begin : g_rn
        reg r;
        (* keep = "true" *) always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rn;
        assign rnc[gr] = r;
    end endgenerate
    // ---- pin flops
    reg ki_ci, ki_cv, kstart_q; reg ki_last; reg [1:0] ki_slot; reg [2:0] ki_cnt; reg [12:0] ki_shi; reg [1023:0] ki_d;
    reg keep_en; reg [6:0] rank; reg [17:0] c_base; reg [11:0] c_n; reg [18:0] c_end;
    always @(posedge clk or negedge rnc[0])
        if (!rnc[0]) begin ki_ci <= 1'b0; ki_cv <= 1'b0; kstart_q <= 1'b0; end
        else begin ki_ci <= kc_ci_i; ki_cv <= kc_cv_i; kstart_q <= kstart_i; end
    always @(posedge clk) begin
        ki_last <= kc_last_i; ki_slot <= kc_slot_i; ki_cnt <= kc_cnt_i; ki_shi <= kc_shi_i; ki_d <= kc_d_i;
        keep_en <= keep_en_i; rank <= rank_i; c_base <= c_base_i; c_n <= c_n_i;
        c_end <= {1'b0, c_base} + {7'd0, c_n};
    end
    // ---- H: the held id chunk (the load enable is the id-valid pin, landed in one flop a 64-bit slice)
    wire [1023:0] h0_d;
    generate for (gc = 0; gc < 16; gc = gc + 1) begin : g_h0
        reg en; reg [63:0] d;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) en <= 1'b0; else en <= kc_ci_i;
        always @(posedge clk) if (en) d <= ki_d[gc*64 +: 64];
        assign h0_d[gc*64 +: 64] = d;
    end endgenerate
    reg [1:0] h0_slot; reg [2:0] h0_cnt; reg [18:0] h0_dn; reg [19:0] h0_e;     // signed bounds
    always @(posedge clk) if (ki_ci) begin
        h0_slot <= ki_slot; h0_cnt <= ki_cnt;
        h0_dn <= {1'b0, c_base} - {1'b0, ki_shi, 5'd0};
        h0_e <= {1'b0, c_end} - {2'd0, ki_shi, 5'd0};
    end
    // ---- K1 .. K5 (free-running)
    reg k1_v, k2_v, k3_v, k4_v, k5_v;
    reg [31:0] k1_ok, k2_ok, k3_ok, k4_ok, k5_ok;
    reg [14:0] k1_q [0:31]; reg [4:0] k1_lo [0:31]; reg [17:0] k1_q5 [0:31];
    reg [14:0] k2_q [0:31]; reg [4:0] k2_lo [0:31]; reg [21:0] k2_p [0:31];
    reg [14:0] k3_q [0:31]; reg [4:0] k3_lo [0:31]; reg [31:0] k3_s [0:31];
    reg [1:0]  k4_q [0:31]; reg [4:0] k4_lo [0:31]; reg [13:0] k4_ord [0:31];
    reg [1:0]  k5_q [0:31]; reg [4:0] k5_lo [0:31]; reg [1:0] k5_t [0:31]; reg [10:0] k5_ord [0:31];
    reg [14:0] t3; reg [31:0] s4;
    always @(posedge clk) begin
        for (p = 0; p < 32; p = p + 1) begin
            k1_ok[p] <= (p / 8) >= {30'd0, h0_slot} && (p / 8) < {30'd0, h0_slot} + {29'd0, h0_cnt} &&
                        (h0_dn[18] || h0_dn[17:0] <= 18'(p)) && (!h0_e[19] && h0_e[18:0] > 19'(p)) &&
                        h0_d[p*32 + 20 +: 12] == 12'd0 && ki_d[p*32 +: 32] != 32'hFF80_0000;
            k1_q[p] <= h0_d[p*32 + 5 +: 15]; k1_lo[p] <= h0_d[p*32 +: 5];
            k1_q5[p] <= {3'd0, h0_d[p*32 + 5 +: 15]} + {1'b0, h0_d[p*32 + 5 +: 15], 2'd0};
            k2_q[p] <= k1_q[p]; k2_lo[p] <= k1_lo[p]; k2_p[p] <= {4'd0, k1_q5[p]} + {k1_q5[p], 4'd0};
            k3_q[p] <= k2_q[p]; k3_lo[p] <= k2_lo[p]; k3_s[p] <= {9'd0, k2_p[p], 1'b0} + {1'b0, k2_p[p], 9'd0};
            s4 = (MUT == 11) ? k3_s[p] : k3_s[p] + {17'd0, k3_q[p]};
            k4_q[p] <= k3_q[p][1:0]; k4_lo[p] <= k3_lo[p]; k4_ord[p] <= s4[30:17];
            t3 = {1'b0, k4_ord[p]} + {k4_ord[p], 1'b0};
            k5_q[p] <= k4_q[p]; k5_lo[p] <= k4_lo[p]; k5_t[p] <= t3[1:0]; k5_ord[p] <= k4_ord[p][10:0];
            k5_ok[p] <= k4_ok[p] && k4_ord[p] < 14'd1368;
        end
        k2_ok <= k1_ok; k3_ok <= k2_ok; k4_ok <= k3_ok;
    end
    // ---- K6 -> result FIFO entry (the write enables are registered one stage ahead, one copy a slice)
    wire [31:0] k6_m;
    generate for (gp = 0; gp < 32; gp = gp + 1) begin : g_k6
        assign k6_m[gp] = k5_ok[gp] && {2'(k5_q[gp] - k5_t[gp]), k5_lo[gp]} == rank;
    end endgenerate
    reg [KB-1:0] kwp;                       // FIFO slot of the chunk entering K5
    wire [KFD*32-1:0] fmf; wire [KFD-1:0] fzf; wire [KFD*352-1:0] fof;
    generate for (ge = 0; ge < KFD; ge = ge + 1) begin : g_fe
        for (gc = 0; gc < 7; gc = gc + 1) begin : g_c
            reg we;
            (* keep = "true" *) always @(posedge clk) we <= k4_v && kwp == KB'(ge);
            if (gc == 6) begin : g_m
                reg [31:0] m; reg z;
                always @(posedge clk) if (we) begin m <= k6_m; z <= k6_m == 32'd0; end
                assign fmf[ge*32 +: 32] = m; assign fzf[ge] = z;
            end else begin : g_o
                localparam integer P0 = (gc * 32) / 6, P1 = ((gc + 1) * 32) / 6;
                reg [(P1-P0)*11-1:0] o; integer q;
                always @(posedge clk) if (we) for (q = P0; q < P1; q = q + 1) o[(q-P0)*11 +: 11] <= k5_ord[q];
                assign fof[ge*352 + P0*11 +: (P1-P0)*11] = o;
            end
        end
    end endgenerate
    // ---- drain: one match a cycle from the head entry
    reg [KFD-1:0] hoh;                      // head, one-hot
    reg [KB:0] fn;                          // entries written, not yet loaded into the drain
    reg [31:0] mb; reg mb_z, cp_v;
    reg [31:0] hm; reg hz;
    always @* begin
        hm = 32'd0; hz = 1'b0;
        for (l = 0; l < KFD; l = l + 1) if (hoh[l]) begin hm = hm | fmf[l*32 +: 32]; hz = hz | fzf[l]; end
    end
    wire ld = mb_z && fn != '0;
    wire [351:0] osel;
    generate for (gc = 0; gc < 6; gc = gc + 1) begin : g_cp
        localparam integer P0 = (gc * 32) / 6, P1 = ((gc + 1) * 32) / 6;
        reg [KFD-1:0] cp; reg [(P1-P0)*11-1:0] v; integer e;
        (* keep = "true" *) always @(posedge clk) if (ld) cp <= hoh;
        always @* begin
            v = '0;
            for (e = 0; e < KFD; e = e + 1) if (cp[e]) v = v | fof[e*352 + P0*11 +: (P1-P0)*11];
        end
        assign osel[P0*11 +: (P1-P0)*11] = v;
    end endgenerate
    // lowest pending match as a one-hot pick (each pick line gates one 11-bit ordinal: no wide binary select)
    reg [31:0] poh; reg [10:0] pord; reg pk_v, seen;
    always @* begin
        pk_v = |mb; pord = 11'd0; seen = 1'b0;
        for (l = 0; l < 32; l = l + 1) begin
            poh[l] = mb[l] && !seen; seen = seen | mb[l];
            if (poh[l]) pord = pord | osel[l*11 +: 11];
        end
    end
    wire [31:0] mb_left = mb & ~poh;
    reg ks_v, ks2_v; reg [10:0] ks_ord;
    reg [42:0] khi; reg [31:0] klo;
    // ---- keep bitmap (bit ord), cleared at the frame start by registered clear copies, set by the two one-hot halves
    wire [1375:0] keepf;
    generate for (gc = 0; gc < 43; gc = gc + 1) begin : g_kb
        reg clr; reg [31:0] b;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) clr <= 1'b1; else clr <= kstart_i;
        always @(posedge clk) if (clr) b <= 32'd0; else if (khi[gc]) b <= b | klo;
        assign keepf[gc*32 +: 32] = b;
    end endgenerate
    // ---- kin launch
    reg run, last_seen, kin_sent, kin_v; reg [2:0] kgap; reg [1:0] kq;
    wire busy = ki_ci || ki_cv || k1_v || k2_v || k3_v || k4_v || k5_v || fn != '0 || !mb_z || cp_v || ks_v || ks2_v;
    wire kfire = run && keep_en && !kin_sent && last_seen && !busy && kgap == 3'd0;
    generate for (gc = 0; gc < 6; gc = gc + 1) begin : g_kin
        localparam integer W = (gc == 5) ? 342 - 320 : 64;
        reg [1:0] qc; reg [W-1:0] d, v; integer e;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || kstart_q) qc <= 2'd0; else if (kfire) qc <= qc + 2'd1;
        always @* begin v = '0; for (e = 0; e < 4; e = e + 1) if (qc == 2'(e)) v = v | keepf[e*342 + gc*64 +: W]; end
        always @(posedge clk) d <= v;
        assign kin_o[3 + gc*64 +: W] = d;
    end endgenerate
    reg [1:0] kin_q;
    assign kin_o[0] = kin_v; assign kin_o[2:1] = kin_q;
    always @(posedge clk) begin
        kin_q <= kq;
        if (pk_v) ks_ord <= pord;
        for (l = 0; l < 43; l = l + 1) khi[l] <= ks_v && ks_ord[10:5] == 6'(l);
        for (l = 0; l < 32; l = l + 1) klo[l] <= ks_ord[4:0] == 5'(l);
    end
    always @(posedge clk) begin
        if (!rnc[2]) begin
            k1_v <= 1'b0; k2_v <= 1'b0; k3_v <= 1'b0; k4_v <= 1'b0; k5_v <= 1'b0; kwp <= '0; hoh <= KFD'(1); fn <= '0;
            mb <= 32'd0; mb_z <= 1'b1; cp_v <= 1'b0; ks_v <= 1'b0; ks2_v <= 1'b0; kcr_o <= 1'b0; kin_sent_o <= 1'b0;
            run <= 1'b0; last_seen <= 1'b0; kin_sent <= 1'b0; kin_v <= 1'b0; kgap <= 3'd0; kq <= 2'd0;
        end else begin
            k1_v <= ki_cv; k2_v <= k1_v; k3_v <= k2_v; k4_v <= k3_v; k5_v <= k4_v;
            if (k4_v) kwp <= kwp + 1'b1;
            fn <= fn + (KB+1)'(k5_v) - (KB+1)'(ld);
            kcr_o <= mb_z && cp_v;
            if (mb_z) begin
                cp_v <= ld;
                if (ld) begin mb <= hm; mb_z <= hz; hoh <= {hoh[KFD-2:0], hoh[KFD-1]}; end
            end else begin
                mb <= mb_left; mb_z <= mb_left == 32'd0;
            end
            ks_v <= pk_v; ks2_v <= ks_v;
            if (ki_cv && ki_last) last_seen <= 1'b1;
            kin_v <= kfire;
            if (kgap != 3'd0) kgap <= kgap - 3'd1;
            if (kfire) begin kgap <= 3'd3; kq <= kq + 2'd1; if (kq == 2'd3) kin_sent <= 1'b1; end
            kin_sent_o <= kin_sent;
            if (kstart_q) begin run <= 1'b1; last_seen <= 1'b0; kin_sent <= 1'b0; kin_sent_o <= 1'b0; kgap <= 3'd0; kq <= 2'd0; end
        end
    end
endmodule
`default_nettype wire
