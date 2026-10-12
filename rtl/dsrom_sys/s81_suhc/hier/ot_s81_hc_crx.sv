`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_crx (s81-suhc-hier-1011 comb v2, 2026-10-11): the return merge and VM writer of the HC combine region
// (hard tile, top row; W / E faces to the outer column roots, N face to the pin tile).  Stage 1 captures the outer
// roots' return (w_rv / w_rd / e_rv / e_rd); the centre chain's arrive padded (ot_s81_hc_ccr valids, ot_s81_hc_cpad
// rows; captured here = stage RP).  Stage 2 is the merged return (the flat comb's hroot rv / rd pin flops; it also
// feeds the S_RT act-quant tiles ot_s81_hc_caq).  The writer: h-store / y rows, the codes / exps rows from the
// act-quant outputs (captured), the exponent row being collected, the write count of HSTORE / NORM jobs.  Its
// write-slot registers ARE the w_w / e_w output flops (one stage less than the flat comb: writes leave a cycle earlier
// while the done gains cycles).  Job state comes from ot_s81_hc_cseq (start pulse + kind / base / flags, end pulse,
// fault, NORM issue complete); the write-count done goes back as a pulse (wdone), as do the return's event bits
// (POST outbound, fault codes 1 / 4).  MUT 3 / 4 as ot_s81_hc_hroot.
// ---------------------------------------------------------------------------------------------------------------------
// comb v2b (2026-10-12): the rows' 4 x 512 b data part is bit-sliced into ot_s81_hc_caq u (capture + OR + the write
// slot u data flop there); crx keeps the 108-b headers, the writer control and slots 4-7 (codes / exps) -- it was
// pin-bound at 14,197 IO pins (PPL-0024 on the 117 um outline).
module ot_s81_hc_crx #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 1, RT = 1, RW = 2, YD = 16, HALF = 0, RLY = 1, DW = 3 + RW
) (
    input  wire                 sk, srs,
    input  wire [RVW-1:0]       w_rv, e_rv,
    input  wire [P_D-1:0]       w_rd, e_rd,     // header part only (the data part is bit-sliced into ot_s81_hc_caq)
    input  wire [RVW-1:0]       c_rv,           // centre valids (ot_s81_hc_ccr, stage RP-1)
    input  wire [P_D-1:0]       c_rd,           // centre row headers (ot_s81_hc_cpad, stage RP-1)
    input  wire                 j_v,            // job state from ot_s81_hc_cseq
    input  wire [2:0]           j_kind,
    input  wire [13:0]          j_base,
    input  wire                 j_fq, j_fy, j_end, j_flt, j_civ,
    input  wire [S_RT-1:0]      a_vo, a_f,      // act-quant tiles
    input  wire [S_RT*10-1:0]   a_e,
    input  wire [S_RT*24-1:0]   a_iq,
    output wire [S_RT-1:0]      o_rv,           // to the act-quant tiles (stage-2 flops)
    output wire [P_D-1:0]       o_rd,
    output reg                  o_run,
    output reg  [2:0]           o_kind,
    output wire [4*HSL-1:0]     w_h,            // west slots 0-3 {mask, row, v}; data = caq wd (same cycle)
    output wire [4*HSL-1:0]     e_h,            // east slots 4-7 {mask, row, v}; data: 4/5 = caq cq, 6/7 = e_x
    output wire [1023:0]        e_x,            // slots 6 (exps row) / 7 data
    output reg                  x_wdone, x_pob, x_f1, x_f4
);
    // the comb's geometry (identical to ot_s81_hc_comb; defaults = the hardened NG 256 HIER=1 configuration)
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512, HSL = WSL - 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer HOP = 2 + RLY;                             // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1) * (HALF ? 2 : 1);    // the centre chain is short by NP - L1 octets
    localparam integer FP = 2 + RF + PAD;                         // forward: send + capture + RF + padding
    localparam integer RP = RT + 2 + PAD;                         // return: relay + send + capture + padding
    reg [1:0] rsr;                                                // tile-local reset relay (2 flops at the pin)
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    localparam integer N     = 4 * NG;
    localparam integer NR    = D / NG;
    localparam integer NV    = D / N;
    localparam integer HROWS = NR * NG / 8;
    localparam integer CROWS = N / 64;
    localparam integer EROWS = (N + 1023) / 1024;
    localparam integer YROWS = N / 32;
    localparam integer CR = (N / 64) > 0 ? N / 64 : 1, ER = (N + 1023) / 1024, YR = N / 32;
    localparam [2:0] K_HSTORE = 1, K_NORM = 4;
    // ---------------------------------------------------------------- captures
    reg  [RVW-1:0] wrv, erv, crv;
    reg  [P_D-1:0] wrd, erd, crd;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin wrv <= 0; erv <= 0; crv <= 0; end
        else begin wrv <= w_rv; erv <= e_rv; crv <= c_rv; end
    always @(posedge sk) begin wrd <= w_rd; erd <= e_rd; crd <= c_rd; end
    reg [RVW-1:0] rv;
    reg [P_D-1:0] rd;
    always @(posedge sk or negedge rs_n) if (!rs_n) rv <= 0; else rv <= wrv | erv | ((L1 > 0) ? crv : {RVW{1'b0}});
    always @(posedge sk) rd <= wrd | erd | ((L1 > 0) ? crd : {P_D{1'b0}});
    assign o_rv = rv[S_RT-1:0];
    assign o_rd = rd;
    reg                 jv, je, jflt, jciv, jfq, jfy;
    reg  [2:0]          jk;
    reg  [13:0]         jb;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin jv <= 1'b0; je <= 1'b0; jflt <= 1'b0; jciv <= 1'b0; end
        else begin jv <= j_v; je <= j_end; jflt <= j_flt; jciv <= j_civ; end
    always @(posedge sk) begin jk <= j_kind; jb <= j_base; jfq <= j_fq; jfy <= j_fy; end
    reg  [S_RT-1:0]     aq_vo, aq_f;
    reg  [S_RT*10-1:0]  aq_e;
    reg  [S_RT*24-1:0]  aq_iq;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin aq_vo <= 0; aq_f <= 0; end
        else begin aq_vo <= a_vo; aq_f <= a_f; end
    always @(posedge sk) begin aq_e <= a_e; aq_iq <= a_iq; end
    // ---------------------------------------------------------------- the writer
    reg  [13:0]         base;
    reg                 f_q, f_y;
    reg  [15:0]         cw, nw;
    reg  [511:0]        er;                              // the vector's exponent row being collected
    reg  [S_WR-1:0]     wq_v;
    reg  [S_WR*14-1:0]  wq_row;
    reg  [S_WR*16-1:0]  wq_mask;
    reg  [S_WR*512-1:0] wq_d;
    wire run = o_run;
    wire [2:0] kind = o_kind;
    integer s;
    always @(posedge sk or negedge rs_n) begin
        if (!rs_n) begin
            o_run <= 1'b0; o_kind <= 0; cw <= 0; nw <= 0; wq_v <= 0;
            x_wdone <= 1'b0; x_pob <= 1'b0; x_f1 <= 1'b0; x_f4 <= 1'b0;
        end else begin
            wq_v <= 0; x_wdone <= 1'b0;
            x_pob <= rv[S_RT + 1]; x_f1 <= rv[S_RT + 2] | (|aq_f); x_f4 <= rv[S_RT + 3];
            if (je) o_run <= 1'b0;
            if (jv) begin
                o_run <= 1'b1; o_kind <= jk; base <= jb; f_q <= jfq; f_y <= jfy; cw <= 0;
                nw <= (jk == K_HSTORE) ? HROWS :
                      (jk == K_NORM) ? (jfq ? NV * (CROWS + EROWS) : 0) + (jfy ? NV * YROWS : 0) : 0;
            end
            begin : wr
                reg [15:0] n_w;
                reg [511:0] ern;
                n_w = 0;
                ern = er;
                for (s = 0; s < S_RT; s = s + 1)
                    if (rv[s] && run && (rd[P_T + s] || f_y)) begin : one
                        reg [7:0] v; reg [15:0] q;
                        v = rd[P_I + 8 * s +: 8]; q = rd[P_Q + 16 * s +: 16];
                        wq_v[s] <= 1'b1; wq_mask[16 * s +: 16] <= 16'hFFFF;   // data: ot_s81_hc_caq u = s (wd)
                        wq_row[14 * s +: 14] <= rd[P_T + s] ? base + q : base + (f_q ? NV * (CR + ER) : 0) + v * YR + q;
                        n_w = n_w + 1;
                    end
                if (f_q && run && kind == K_NORM)
                    for (s = 0; s < S_RT; s = s + 2) begin : cd             // codes row: blocks 2r (slot s), 2r+1 (s+1)
                        reg [7:0] v; reg [15:0] q;
                        v = aq_iq[24 * s + 16 +: 8]; q = aq_iq[24 * s +: 16];
                        if (aq_vo[s]) begin
                            wq_v[S_RT + s / 2] <= 1'b1; wq_mask[16 * (S_RT + s / 2) +: 16] <= 16'hFFFF;
                            wq_row[14 * (S_RT + s / 2) +: 14] <= base + v * CR + q / 2;
                            // data: ot_s81_hc_caq s / s+1 cq (codes slice)
                            n_w = n_w + 1;
                        end
                    end
                if (f_q && run && kind == K_NORM)
                    for (s = 0; s < S_RT; s = s + 1)
                        if (aq_vo[s]) begin : ex
                            reg [7:0] v; reg [15:0] q;
                            v = aq_iq[24 * s + 16 +: 8]; q = aq_iq[24 * s +: 16];
                            ern[16 * (q % 32) +: 16] = {6'd0, aq_e[10 * s +: 10]};
                            if (q == YR - 1) begin
                                wq_v[S_RT + 2] <= 1'b1; wq_mask[16 * (S_RT + 2) +: 16] <= 16'hFFFF;
                                wq_row[14 * (S_RT + 2) +: 14] <= base + NV * CR + v * ER;
                                wq_d[512 * (S_RT + 2) +: 512] <= ern;
                                ern = 512'd0;
                                n_w = n_w + 1;
                            end
                        end
                er <= ern;
                if (run && (kind == K_HSTORE || kind == K_NORM) && !jflt && !(kind == K_NORM && MUT == 3)) begin
                    cw <= cw + n_w;
                    if (n_w != 0 && cw + n_w >= nw - ((MUT == 4) ? S_WR : 0) && (kind == K_HSTORE || jciv)) begin
                        o_run <= 1'b0; x_wdone <= 1'b1;
                    end
                end
            end
        end
    end
    // the write slots: the slot registers are the output flops (slots 0-3 west, 4-7 east)
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_w
        assign w_h[HSL * g +: HSL] = {wq_mask[16 * g +: 16], wq_row[14 * g +: 14], wq_v[g]};   // + caq g's wd
        assign e_h[HSL * g +: HSL] = {wq_mask[16 * (g + 4) +: 16], wq_row[14 * (g + 4) +: 14], wq_v[g + 4]};
    end endgenerate
    assign e_x = wq_d[512 * (S_RT + 2) +: 1024];
endmodule
