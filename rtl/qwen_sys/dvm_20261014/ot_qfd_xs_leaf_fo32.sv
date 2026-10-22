// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xs_leaf_fo32 (SQC-CB16b 2026-10-22): native-census (<= 32 dynamic loads per driver) successor of the CLOSED
// w130 x-slice leaf = ot_qfd_xs_leaf #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1), .BANK_PIPE(0)).
// SAME ports, SAME cycle behaviour (0 added edges; tb_qfd_xs_leaf_fo32 checks every output on every edge against the
// reference leaf), SAME storage. Only the fanout structure changes:
//   * write controls: every write/clear control pin is captured RAW (no logic before the pin register) into one kept
//     copy per region of GRP slot positions (w_v, w_ep, c_v, c_ep, w_off and each tile's {en, d, wo}); a copy only
//     feeds the write enables of its own region (<= 2 tiles x 2 epochs x GRP entries);
//   * read selects: the 128:1 x 17-b tree of each tile is built from kept-hierarchy 16-bit 2:1 slices
//     (ot_qfd_xs_mx16, ABC cannot move a select across slices); each slice has its own registered select replica
//     (was one replica per 256 mux bits, re-associated by ABC up to 569 loads), loaded from NG independent
//     next-select cones per tile, each built from its own kept copies of the request / held-request / element state;
//   * storage entries are two kept halves (ot_qfd_xs_ent9/ent8) each forming its own write enable; line assembly in
//     two halves from kept sequencer copies; answer select from NQ = 6 copies;
//   * the answer-side tile select (done[1]) is computed from NQ kept copies of tile 1's sequencer state.
// The x-slice timing contract (lanes/SQC-CB16.md, qfd_xs_leaf_w130m5 successor) is unchanged: a read request at
// the pins at edge R answers at the same edge as the reference; a write is readable one edge after it lands.
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xs_leaf_fo32 #(
    parameter integer GRP  = 8,     // slot positions per write-control copy region (64 / GRP regions)
    parameter integer NG   = 3,     // independent next-select cones per tile
    parameter integer NQ   = 6,     // copies of tile 1's sequencer state for the answer select
    parameter integer MUT  = 0      // 2: tile 1's reads return tile 0's data (swapped tile) -- must FAIL
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          w_v,
    input  wire          w_ep,
    input  wire [5:0]    w_off,
    input  wire [63:0]   w_m,
    input  wire [1023:0] w_d,
    input  wire [71:0]   w_ctl,
    input  wire          c_v,
    input  wire          c_ep,
    output wire          wo_v,
    output wire          wo_ep,
    output wire [5:0]    wo_off,
    output wire [63:0]   wo_m,
    output wire [1023:0] wo_d,
    output wire [71:0]   wo_ctl,
    output wire          co_v,
    output wire          co_ep,
    input  wire          r_v,
    input  wire          r_t,
    input  wire          r_ep,
    input  wire [27:0]   r_p,
    output reg           q_v,
    output reg  [63:0]   q,
    output reg           q_bad
);
    localparam integer CTW = 9;
    localparam integer NCH = 4;
    localparam integer NRG = 64 / GRP;          // write-control regions
    localparam integer SELW = 16;               // mux bits per select replica = one kept 16-b slice

    // ---- write chain pin registers (unchanged: they are the FILL_PIPE input stage) ----
    reg          wv, cv, wep, cep;
    reg [5:0]    woff;
    reg [63:0]   wm;
    reg [1023:0] wd;
    reg [NCH*2*CTW-1:0] wctl;
    always @(posedge clk) wd <= w_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wv <= 1'b0; cv <= 1'b0; end
        else begin wv <= w_v; cv <= c_v; end
    always @(posedge clk) begin wep <= w_ep; woff <= w_off; wm <= w_m; wctl <= w_ctl; cep <= c_ep; end
    (* keep *) reg [63:0] wma, wmb;                     // raw kept mask copies: one per entry half (4 entries each)
    always @(posedge clk) begin wma <= w_m; wmb <= w_m; end
    // FILL_PIPE = 1 output stage
    reg pv, pcv, pep, pcep;
    reg [5:0] poff;
    reg [63:0] pm;
    reg [1023:0] pd;
    reg [NCH*2*CTW-1:0] pctl;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pv <= 0; pcv <= 0; end
        else begin pv <= wv; pcv <= cv; end
    always @(posedge clk) begin
        pep <= wep; pcep <= cep; poff <= woff; pm <= wm; pd <= wd;
        pctl <= {{(2*CTW){1'b0}}, wctl[NCH*2*CTW-1:2*CTW]};
    end
    assign wo_v = pv; assign wo_ep = pep; assign wo_off = poff; assign wo_m = pm; assign wo_d = pd; assign wo_ctl = pctl;
    assign co_v = pcv; assign co_ep = pcep;

    // ---- read pin registers (READ_PIN_PIPE = 1: exactly one raw capture) ----
    reg rp_v, rp_t, rp_ep;
    reg [27:0] rp_p;
    always @(posedge clk or negedge rst_n) if (!rst_n) rp_v <= 1'b0; else rp_v <= r_v;
    always @(posedge clk) begin rp_t <= r_t; rp_ep <= r_ep; rp_p <= r_p; end

    // ---- storage + write enables, per region of GRP positions ----
    wire [2176*2-1:0] mem_all;
    genvar gr, gt, gk, ge;
    generate for (gr = 0; gr < NRG; gr = gr + 1) begin : g_r
        // raw kept copies of the write/clear controls for this region (same edge as the reference pin registers).
        // No reset: during reset the chain's w_v/c_v come from reset pin registers upstream (0), and the copies only
        // gate local storage, which needs no reset (an epoch is always claimed before it is filled or read).
        (* keep *) reg        kv, kep, kcv, kcep;
        (* keep *) reg [5:0]  koff;
        (* keep *) reg [2*CTW-1:0] kctl;      // {tile 1, tile 0} x {en, d[1:0], wo[5:0]}
        always @(posedge clk) begin
            kv <= w_v; kep <= w_ep; kcv <= c_v; kcep <= c_ep; koff <= w_off; kctl <= w_ctl[2*CTW-1:0];
        end
        for (gt = 0; gt < 2; gt = gt + 1) begin : g_t
            wire        en = kctl[CTW*gt + 8];
            wire [1:0]  dd = kctl[CTW*gt + 6 +: 2];
            wire [5:0]  wo = kctl[CTW*gt +: 6];
            for (gk = 0; gk < GRP; gk = gk + 1) begin : g_p
                localparam integer EP = gr*GRP + gk;
                wire tf = (EP >= koff);
                wire tw = (EP >= wo);
                wire cond = (dd == 2'b00) ? (tf == tw) : (dd == 2'b01) ? (tf && !tw) :
                            (dd == 2'b10) ? (!tf && tw) : 1'b0;
                for (ge = 0; ge < 2; ge = ge + 1) begin : g_e
                    wire pw  = kv && (kep == ge) && en && cond;   // into both entry halves (2 loads)
                    wire clr = kcv && (kcep == ge);
                    wire we_lo = pw && wma[EP];                     // distinct mask copies -> distinct enable nets
                    wire we_hi = pw && wmb[EP];
                    ot_qfd_xs_ent9 u_lo (.clk(clk), .we(we_lo), .clr(clr), .d(wd[16*EP +: 8]),
                                         .q({mem_all[2176*gt + 17*(64*ge + EP) + 16], mem_all[2176*gt + 17*(64*ge + EP) +: 8]}));
                    ot_qfd_xs_ent8 u_hi (.clk(clk), .we(we_hi), .d(wd[16*EP + 8 +: 8]),
                                         .q(mem_all[2176*gt + 17*(64*ge + EP) + 8 +: 8]));
                end
            end
        end
    end endgenerate

    // ---- per tile: sequencer, NG next-select cones, select replicas, read tree, line assembly ----
    function automatic integer nrep16(input integer lv);   // slices (= select replicas) of level lv
        nrep16 = ((17 << (6 - lv)) + SELW - 1) / SELW;
    endfunction
    function automatic integer soff16(input integer lv);
        integer l;
        begin soff16 = 0; for (l = 0; l < lv; l = l + 1) soff16 = soff16 + nrep16(l); end
    endfunction
    localparam integer RSW = soff16(7);

    wire [16:0] tr [0:1];
    wire [1:0]  done;
    wire [47:0] asm_d [0:1];
    wire [2:0]  asm_v [0:1];
    wire [2:0]  asm_e [0:1];
    wire [1:0]  l_en;
    wire [1:0]  coll;
    genvar gn, lv, c, hb;
    generate for (gt = 0; gt < 2; gt = gt + 1) begin : g_t
        // primary sequencer (reference behaviour); the primary held request keeps only the four element enables
        wire       req = rp_v && (rp_t == gt);
        reg  [1:0] el;
        reg        sv;
        reg  [3:0] hen;                                   // hp[27], hp[20], hp[13], hp[6] of the reference
        always @(posedge clk) if (req) hen <= {rp_p[27], rp_p[20], rp_p[13], rp_p[6]};
        wire       sv_n = req ? 1'b1 : (sv && el == 2'd3) ? 1'b0 : sv;
        wire [1:0] el_n = req ? 2'd0 : sv ? el + 1'b1 : el;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin sv <= 1'b0; el <= 2'd0; end
            else begin sv <= sv_n; el <= el_n; end
        assign coll[gt] = req && sv && (el != 2'd3);
        assign done[gt] = sv && (el == 2'd3);
        // NG independent next-select cones. Each has its own raw request captures (A: held-request load enable,
        // B: next-select mux) and a kept copy of the element counter (same D as the primary, so equal every edge
        // after the first reset edge; no reset load).
        wire [6:0] nsel [0:NG-1];
        for (gn = 0; gn < NG; gn = gn + 1) begin : g_n
            (* keep *) reg       cvb, ctb, cep_;
            (* keep *) reg [5:0] cp0;                       // element 0 position from the pins
            (* keep *) reg [1:0] cel;
            (* keep *) reg       chep;
            (* keep *) reg [23:0] chp;                      // positions of elements 0 .. 3
            always @(posedge clk) begin
                cvb <= r_v; ctb <= r_t; cep_ <= r_ep; cp0 <= r_p[5:0]; cel <= el_n;
            end
            wire creqb = cvb && (ctb == gt);
            for (hb = 0; hb < 2; hb = hb + 1) begin : g_ha
                // own raw request capture per half (elements 2hb, 2hb+1; one shared 25-bit load enable measured 50 pins;
                // four per-element captures put 41 loads on the r_v / r_t input pins at NG=4)
                (* keep *) reg cva, cta;
                always @(posedge clk) begin cva <= r_v; cta <= r_t; end
                wire creqa = cva && (cta == gt);
                always @(posedge clk) if (creqa) chp[12*hb +: 12] <= {rp_p[14*hb+7 +: 6], rp_p[14*hb +: 6]};
                if (hb == 0) begin : g_ep
                    always @(posedge clk) if (creqa) chep <= cep_;
                end
            end
            wire [1:0] nel = creqb ? 2'd0 : cel + 1'b1;
            assign nsel[gn] = creqb ? {cep_, cp0} : {chep, chp[6*nel +: 6]};
        end
        // select replicas: replica c of level lv takes cone (c * NG) / NR
        wire [RSW-1:0] sr;
        for (lv = 0; lv < 7; lv = lv + 1) begin : g_lv
            localparam integer NR = nrep16(lv);
            localparam integer OF = soff16(lv);
            for (c = 0; c < NR; c = c + 1) begin : g_c
                (* keep *) reg f;
                always @(posedge clk) f <= nsel[(c * NG) / NR][lv];
                assign sr[OF + c] = f;
            end
        end
        localparam integer SRC = (MUT == 2 && gt == 1) ? 0 : gt;
        ot_qfd_xs_mux_rep16 #(.LN(7), .SW(RSW)) u_m (.d(mem_all[2176*SRC +: 2176]), .s(sr), .q(tr[gt]));
        // assembly of elements 0 .. 2: two halves, each enabled from its own kept copy of the sequencer state
        // (one shared position enable measured 36 pins: 16 bits x 2 pins + valid/enable)
        reg [23:0] adl, adh;                             // low / high bytes of elements 0 .. 2 (separate registers)
        reg [2:0]  av, ae;
        (* keep *) reg [3:0] hl, hh;                     // per-half copies of hen (one shared hen[el] measured 54 pins)
        always @(posedge clk) if (req) begin hl <= {rp_p[27], rp_p[20], rp_p[13], rp_p[6]}; hh <= {rp_p[27], rp_p[20], rp_p[13], rp_p[6]}; end
        (* keep *) reg       asv0, asv1;
        (* keep *) reg [1:0] ael0, ael1;
        always @(posedge clk) begin asv0 <= sv_n; asv1 <= sv_n; ael0 <= el_n; ael1 <= el_n; end
        always @(posedge clk)
            if (asv0 && ael0 != 2'd3) begin
                adl[8*ael0 +: 8] <= hl[ael0] ? tr[gt][7:0] : 8'd0;
                av[ael0] <= hl[ael0] && tr[gt][16];
                ae[ael0] <= hl[ael0];
            end
        always @(posedge clk)
            if (asv1 && ael1 != 2'd3) adh[8*ael1 +: 8] <= hh[ael1] ? tr[gt][15:8] : 8'd0;
        wire [47:0] ad = {adh[23:16], adl[23:16], adh[15:8], adl[15:8], adh[7:0], adl[7:0]};
        assign asm_d[gt] = ad; assign asm_v[gt] = av; assign asm_e[gt] = ae;
        assign l_en[gt] = hen[3];
    end endgenerate

    // ---- answer: the tile select (reference: done[1]) from NQ kept copies of tile 1's sequencer state ----
    wire [NQ-1:0] ftc;
    genvar gq;
    generate for (gq = 0; gq < NQ; gq = gq + 1) begin : g_q
        (* keep *) reg [1:0] qel;
        (* keep *) reg       qsv;
        always @(posedge clk) begin qsv <= g_t[1].sv_n; qel <= g_t[1].el_n; end
        assign ftc[gq] = qsv && (qel == 2'd3);
    end endgenerate
    wire       fin  = done[0] | done[1];
    wire       ft   = done[1];
    wire [15:0] l3;
    wire [47:0] ad_sel;
    genvar gb;
    generate for (gb = 0; gb < 64; gb = gb + 1) begin : g_ans
        wire s = ftc[(gb * NQ) / 64];
        if (gb < 48) begin : g_d
            assign ad_sel[gb] = s ? asm_d[1][gb] : asm_d[0][gb];
        end else begin : g_l
            assign l3[gb-48] = (s ? l_en[1] : l_en[0]) ? (s ? tr[1][gb-48] : tr[0][gb-48]) : 1'b0;
        end
    end endgenerate
    wire       bad3 = l_en[ft] && !tr[ft][16];
    wire       badx = |(asm_e[ft] & ~asm_v[ft]);
    reg        coll_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_v <= 1'b0; q_bad <= 1'b0; coll_q <= 1'b0; end
        else begin
            coll_q <= |coll;
            q_v <= fin;
            q_bad <= fin && (bad3 || badx || (done[0] && done[1]) || coll_q);
        end
    always @(posedge clk) q <= {l3, ad_sel};
endmodule

// 2^LN : 1 x 17-b tree of kept 16-b slices: level lv's NODES x 17 output bits are cut into 16-b slices in order,
// slice j has select s[OFF + j] (<= 16 mux bits per select replica whatever ABC does inside the slice)
module ot_qfd_xs_mux_rep16 #(parameter integer LN = 7, parameter integer SW = 138) (
    input  wire [(17 << LN)-1:0] d,
    input  wire [SW-1:0]         s,
    output wire [16:0]           q
);
    function automatic integer nrep16(input integer lv);
        nrep16 = ((17 << (LN - 1 - lv)) + 15) / 16;
    endfunction
    function automatic integer soff16(input integer lv);
        integer l;
        begin soff16 = 0; for (l = 0; l < lv; l = l + 1) soff16 = soff16 + nrep16(l); end
    endfunction
    genvar lv, k, b, j;
    generate for (lv = 0; lv <= LN; lv = lv + 1) begin : g_l
        wire [(17 << (LN - lv))-1:0] n;
        if (lv == 0) begin : g_in
            assign n = d;
        end else begin : g_mx
            localparam integer NB  = 17 << (LN - lv);      // output bits of this level
            localparam integer NS  = (NB + 15) / 16;
            localparam integer OFF = soff16(lv - 1);
            wire [16*NS-1:0] a, bb, o;
            for (k = 0; k < (NB / 17); k = k + 1) begin : g_k
                for (b = 0; b < 17; b = b + 1) begin : g_b
                    assign a[17*k + b]  = g_l[lv-1].n[17*(2*k) + b];
                    assign bb[17*k + b] = g_l[lv-1].n[17*(2*k+1) + b];
                end
            end
            if (16*NS > NB) begin : g_pad
                assign a[16*NS-1:NB] = {(16*NS-NB){1'b0}};
                assign bb[16*NS-1:NB] = {(16*NS-NB){1'b0}};
            end
            for (j = 0; j < NS; j = j + 1) begin : g_s
                ot_qfd_xs_mx16 u_s (.a(a[16*j +: 16]), .b(bb[16*j +: 16]), .s(s[OFF + j]), .q(o[16*j +: 16]));
            end
            assign n = o[NB-1:0];
        end
    end endgenerate
    assign q = g_l[LN].n;
endmodule

// one {valid, BF16} storage entry = two kept halves, each with its OWN write-enable input net (formed in the parent
// from distinct mask copies), so an enable drives 8 bits (2 pins each) + valid <= 17 pins (one shared enable measured
// 33; an enable formed inside the half was decomposed by ABC into its mask bit: wm 73)
(* keep_hierarchy = "yes" *) module ot_qfd_xs_ent9 (
    input  wire       clk,
    input  wire       we,
    input  wire       clr,
    input  wire [7:0] d,
    output wire [8:0] q          // {valid, data[7:0]}
);
    reg [7:0] r;
    reg       v;
    always @(posedge clk) if (we) r <= d;
    always @(posedge clk)
        if (clr) v <= 1'b0;
        else if (we) v <= 1'b1;
    assign q = {v, r};
endmodule

(* keep_hierarchy = "yes" *) module ot_qfd_xs_ent8 (
    input  wire       clk,
    input  wire       we,
    input  wire [7:0] d,
    output wire [7:0] q
);
    reg [7:0] r;
    always @(posedge clk) if (we) r <= d;
    assign q = r;
endmodule

// one select, sixteen 2:1 bits; kept through ABC (route.synth_keep_modules) so a select never leaves its slice
(* keep_hierarchy = "yes" *) module ot_qfd_xs_mx16 (
    input  wire [15:0] a,
    input  wire [15:0] b,
    input  wire        s,
    output wire [15:0] q
);
    assign q = s ? b : a;
endmodule
