// Isolated S81 successor; historical V4.1x sources remain byte-identical.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Shared pieces of the V4.1x streaming-filter SELECT (ot_s81ph_native_sel.sv):
//   ot_s81ph_native_sel_hist  256-bin histogram of one 8-bit digit per lane, W lanes a
//                         beat, saturating bins, registered 16-group sums and the
//                         registered 16 bins of one group (the two-step radix-16 walk)
//   ot_s81ph_native_sel_pack  compaction of the selected lanes of each beat and packing
//                         into full W-lane lines (partial line on a flush)
//   ot_s81ph_native_sel_su    the two-step (radix-16) threshold search over Q slices'
//                         histograms: the highest bucket b with count(>= b) >= q
//   combinational helpers (popcount, prefix counts, compaction and rotate stages).
// ---------------------------------------------------------------------------

// popcount of N bits
module ot_s81ph_native_sel_popc #(
    parameter integer N  = 16,
    parameter integer OW = 5
) (
    input  wire [N-1:0]  x,
    output wire [OW-1:0] y
);
    localparam integer NP = (N > 1) ? (1 << $clog2(N)) : 2;
    /* verilator lint_off UNOPTFLAT */
    wire [2*NP*OW-1:0] t;
    /* verilator lint_on UNOPTFLAT */
    genvar n;
    generate
        for (n = 0; n < NP; n = n + 1) begin : g_leaf
            if (n < N) begin : g_x
                assign t[OW*(NP+n) +: OW] = {{(OW-1){1'b0}}, x[n]};
            end else begin : g_0
                assign t[OW*(NP+n) +: OW] = {OW{1'b0}};
            end
        end
        for (n = 1; n < NP; n = n + 1) begin : g_node
            assign t[OW*n +: OW] = t[OW*(2*n) +: OW] + t[OW*(2*n+1) +: OW];
        end
    endgenerate
    assign t[OW-1:0] = {OW{1'b0}};
    assign y = t[OW +: OW];
endmodule

// inclusive prefix counts (Kogge-Stone): y[OW*l +: OW] = popcount(x[l:0])
module ot_s81ph_native_sel_prefix #(
    parameter integer N  = 16,
    parameter integer OW = 5
) (
    input  wire [N-1:0]    x,
    output wire [N*OW-1:0] y
);
    localparam integer LV = (N > 1) ? $clog2(N) : 1;
    /* verilator lint_off UNOPTFLAT */
    wire [(LV+1)*N*OW-1:0] s;
    /* verilator lint_on UNOPTFLAT */
    genvar d, l;
    generate
        for (l = 0; l < N; l = l + 1) begin : g_in
            assign s[OW*l +: OW] = {{(OW-1){1'b0}}, x[l]};
        end
        for (d = 0; d < LV; d = d + 1) begin : g_lv
            for (l = 0; l < N; l = l + 1) begin : g_l
                if (l >= (1 << d)) begin : g_add
                    assign s[N*OW*(d+1) + OW*l +: OW] = s[N*OW*d + OW*l +: OW] + s[N*OW*d + OW*(l - (1 << d)) +: OW];
                end else begin : g_pass
                    assign s[N*OW*(d+1) + OW*l +: OW] = s[N*OW*d + OW*l +: OW];
                end
            end
        end
    endgenerate
    assign y = s[N*OW*LV +: N*OW];
endmodule

// compaction stage S: lane j takes lane j + 2^S when that lane is valid (bit CE-1) and its shift
// count has bit S set (bit ZB), else keeps its own lane when that is valid and does not move
module ot_s81ph_native_sel_cstage #(
    parameter integer W  = 16,
    parameter integer CE = 40,
    parameter integer ZB = 37,
    parameter integer S  = 0
) (
    input  wire [W*CE-1:0] a,
    output wire [W*CE-1:0] y
);
    genvar j;
    generate
        for (j = 0; j < W; j = j + 1) begin : g_lane
            wire [CE-1:0] me = a[CE*j +: CE];
            wire [CE-1:0] up;
            if (j + (1 << S) < W) begin : g_up
                assign up = a[CE*(j + (1 << S)) +: CE];
            end else begin : g_none
                assign up = {CE{1'b0}};
            end
            wire take = up[CE-1] && up[ZB];
            wire keep = me[CE-1] && !me[ZB];
            assign y[CE*j +: CE] = take ? up : keep ? me : {CE{1'b0}};
        end
    endgenerate
endmodule

// rotate stage over N lanes: every lane moves 2^S up when `sh` is set
module ot_s81ph_native_sel_rstage #(
    parameter integer N  = 32,
    parameter integer RE = 38,
    parameter integer S  = 0
) (
    input  wire [N*RE-1:0] a,
    input  wire            sh,
    output wire [N*RE-1:0] y
);
    genvar j;
    generate
        for (j = 0; j < N; j = j + 1) begin : g_lane
            if (j >= (1 << S)) begin : g_mv
                assign y[RE*j +: RE] = sh ? a[RE*(j - (1 << S)) +: RE] : a[RE*j +: RE];
            end else begin : g_lo
                assign y[RE*j +: RE] = sh ? {RE{1'b0}} : a[RE*j +: RE];
            end
        end
    endgenerate
endmodule

// ---------------------------------------------------------------------------
// 256-bin histogram.  A beat (i_v) carries W lanes; lane l counts in bin i_dg[l] when i_en[l].
// Pipeline: predecode (two 16-way one-hots) -> per-bin popcount -> saturating bin add ->
// 4-bin sums -> 16-bin group sums.  `clr` zeroes the bins and kills the beats in flight.
// Bins saturate at 2^CB - 1 (the unit only compares counts against quotas <= K < 2^(CB-1)).
//   gsum  registered group sums, group g = bins 16g .. 16g+15 (valid 2 edges after the bins)
//   gbin  registered bins of group `gsel` (one edge after the bins / gsel)
//   busy  a beat is between the input and the bins
// ---------------------------------------------------------------------------
module ot_s81ph_native_sel_hist #(
    parameter integer W  = 16,
    parameter integer CB = 11
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 clr,
    input  wire                 i_v,
    input  wire [W-1:0]         i_en,
    input  wire [W*8-1:0]       i_dg,
    input  wire [3:0]           gsel,
    output reg  [16*(CB+4)-1:0] gsum,
    output reg  [16*CB-1:0]     gbin,
    output wire                 busy
);
    localparam integer LW = (W > 1) ? $clog2(W) : 1;
    localparam integer HW = LW + 1;                 // per-beat count width
    localparam [CB-1:0] SAT = {CB{1'b1}};

    reg          v1, v2;
    reg [W*16-1:0] h1_hi, h1_lo;
    genvar gl, gb;
    wire [W*16-1:0] h1_hi_d, h1_lo_d;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_pre
            wire [7:0] d = i_dg[8*gl +: 8];
            assign h1_hi_d[16*gl +: 16] = i_en[gl] ? (16'h0001 << d[7:4]) : 16'h0000;
            assign h1_lo_d[16*gl +: 16] = 16'h0001 << d[3:0];
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v1 <= 1'b0; v2 <= 1'b0; end
        else begin v1 <= i_v && !clr; v2 <= v1 && !clr; end
    end
    always @(posedge clk) begin h1_hi <= h1_hi_d; h1_lo <= h1_lo_d; end

    reg  [256*HW-1:0] h2;
    wire [256*HW-1:0] h2_d;
    generate
        for (gb = 0; gb < 256; gb = gb + 1) begin : g_cnt
            wire [W-1:0] x;
            for (gl = 0; gl < W; gl = gl + 1) begin : g_x
                assign x[gl] = h1_hi[16*gl + (gb >> 4)] && h1_lo[16*gl + (gb & 15)];
            end
            ot_s81ph_native_sel_popc #(.N(W), .OW(HW)) u_pc (.x(x), .y(h2_d[HW*gb +: HW]));
        end
    endgenerate
    always @(posedge clk) h2 <= h2_d;

    reg  [256*CB-1:0] hbin;
    wire [256*CB-1:0] hbin_d;
    generate
        for (gb = 0; gb < 256; gb = gb + 1) begin : g_add
            wire [CB:0] s = {1'b0, hbin[CB*gb +: CB]} + {{(CB+1-HW){1'b0}}, h2[HW*gb +: HW]};
            assign hbin_d[CB*gb +: CB] = s[CB] ? SAT : s[CB-1:0];
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) hbin <= {256*CB{1'b0}};
        else if (clr) hbin <= {256*CB{1'b0}};
        else if (v2) hbin <= hbin_d;
    end

    // group sums: 4-bin sums, then 16-bin sums
    reg [64*(CB+2)-1:0] gs1;
    integer j;
    always @(posedge clk) begin
        for (j = 0; j < 64; j = j + 1)
            gs1[(CB+2)*j +: CB+2] <= {2'b00, hbin[CB*(4*j) +: CB]} + {2'b00, hbin[CB*(4*j+1) +: CB]}
                                    + {2'b00, hbin[CB*(4*j+2) +: CB]} + {2'b00, hbin[CB*(4*j+3) +: CB]};
        for (j = 0; j < 16; j = j + 1)
            gsum[(CB+4)*j +: CB+4] <= {2'b00, gs1[(CB+2)*(4*j) +: CB+2]} + {2'b00, gs1[(CB+2)*(4*j+1) +: CB+2]}
                                     + {2'b00, gs1[(CB+2)*(4*j+2) +: CB+2]} + {2'b00, gs1[(CB+2)*(4*j+3) +: CB+2]};
        gbin <= hbin[16*CB*gsel +: 16*CB];
    end
    assign busy = v1 || v2;
endmodule

// ---------------------------------------------------------------------------
// Compaction + packing.  Every beat (i_v) enters with its selected lanes (i_sel) and payloads;
// the selected payloads leave in order, packed into full W-lane lines (o_v, o_lv all ones); a
// flush beat (i_fl) closes the stream: whatever is left leaves as a partial line (o_lv = its
// lanes), possibly one edge after a full line, and o_fl marks the edge on which the flush is
// complete (with or without a line).  One beat per edge; after a flush beat the next beat must
// not arrive before o_fl.  o_bv pulses once per beat, PL = 2 + 2 ceil(log2(W)/2) edges after it.
// ---------------------------------------------------------------------------
module ot_s81ph_native_sel_pack #(
    parameter integer W  = 16,
    parameter integer PW = 37
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            i_v,
    input  wire            i_fl,
    input  wire [W-1:0]    i_sel,
    input  wire [W*PW-1:0] i_p,
    output reg             o_v,
    output reg  [W-1:0]    o_lv,
    output reg  [W*PW-1:0] o_line,
    output reg             o_bv,
    output reg             o_fl
);
    localparam integer LW  = (W > 1) ? $clog2(W) : 1;
    localparam integer CE  = 1 + LW + PW;           // {v, z, payload}
    localparam integer RE  = 1 + PW;                // {v, payload}
    localparam integer NCR = (LW + 1) / 2;

    // stage 1: shift counts
    wire [W*(LW+1)-1:0] inc;
    ot_s81ph_native_sel_prefix #(.N(W), .OW(LW + 1)) u_pre (.x(i_sel), .y(inc));
    wire [W*CE-1:0] e_d;
    genvar gl, gr;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_z
            localparam integer LANEI = gl;
            localparam [LW:0]  LANE = LANEI[LW:0];
            wire [LW:0] below;
            if (gl == 0) begin : g_first
                assign below = {(LW+1){1'b0}};
            end else begin : g_rest
                assign below = inc[(LW+1)*(gl-1) +: LW+1];
            end
            wire [LW:0] zz = LANE - below;
            assign e_d[CE*gl +: CE] = i_sel[gl] ? {1'b1, zz[LW-1:0], i_p[PW*gl +: PW]} : {CE{1'b0}};
        end
    endgenerate
    reg          s1_v, s1_fl;
    reg [LW:0]   s1_cnt;
    reg [W*CE-1:0] s1_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_fl <= 1'b0; end
        else begin s1_v <= i_v; s1_fl <= i_v && i_fl; end
    end
    always @(posedge clk) begin s1_e <= e_d; s1_cnt <= inc[(LW+1)*(W-1) +: LW+1]; end

    // compaction: NCR registered groups of two stages
    wire [NCR*W*CE-1:0]   crf;
    wire [NCR*(LW+1)-1:0] crc;
    reg  [NCR-1:0]        cr_v, cr_fl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cr_v <= 0; cr_fl <= 0; end
        else begin
            cr_v  <= (NCR > 1) ? {cr_v[(NCR > 1 ? NCR-2 : 0):0], s1_v} : s1_v;
            cr_fl <= (NCR > 1) ? {cr_fl[(NCR > 1 ? NCR-2 : 0):0], s1_fl} : s1_fl;
        end
    end
    generate
        for (gr = 0; gr < NCR; gr = gr + 1) begin : g_cst
            wire [W*CE-1:0] a0 = (gr == 0) ? s1_e : crf[W*CE*(gr == 0 ? 0 : gr - 1) +: W*CE];
            wire [W*CE-1:0] a1, a2;
            ot_s81ph_native_sel_cstage #(.W(W), .CE(CE), .ZB(PW + 2 * gr), .S(2 * gr)) u_c0 (.a(a0), .y(a1));
            if (2 * gr + 1 < LW) begin : g_c1
                ot_s81ph_native_sel_cstage #(.W(W), .CE(CE), .ZB(PW + 2 * gr + 1), .S(2 * gr + 1)) u_c1 (.a(a1), .y(a2));
            end else begin : g_c1n
                assign a2 = a1;
            end
            reg [W*CE-1:0] q;
            reg [LW:0]     qc;
            always @(posedge clk) begin
                q  <= a2;
                qc <= (gr == 0) ? s1_cnt : crc[(LW+1)*(gr == 0 ? 0 : gr - 1) +: LW+1];
            end
            assign crf[W*CE*gr +: W*CE] = q;
            assign crc[(LW+1)*gr +: LW+1] = qc;
        end
    endgenerate

    // rotate by the running fill into 2W lanes
    wire [W*CE-1:0] cp = crf[W*CE*(NCR-1) +: W*CE];
    wire            cp_v = cr_v[NCR-1], cp_fl = cr_fl[NCR-1];
    wire [LW:0]     cp_cnt = crc[(LW+1)*(NCR-1) +: LW+1];
    reg  [LW-1:0]   frun;
    reg  [NCR-1:0]  ro_v, ro_fl;
    wire [NCR*2*W*RE-1:0] rof;
    wire [NCR*LW-1:0]     rff;
    wire [NCR*(LW+1)-1:0] rcf;
    wire [2*W*RE-1:0] rin;
    generate
        for (gl = 0; gl < 2 * W; gl = gl + 1) begin : g_rin
            if (gl < W) begin : g_l
                assign rin[RE*gl +: RE] = {cp[CE*gl + CE - 1], cp[CE*gl +: PW]};
            end else begin : g_h
                assign rin[RE*gl +: RE] = {RE{1'b0}};
            end
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ro_v <= 0; ro_fl <= 0; frun <= 0; end
        else begin
            ro_v  <= (NCR > 1) ? {ro_v[(NCR > 1 ? NCR-2 : 0):0], cp_v} : cp_v;
            ro_fl <= (NCR > 1) ? {ro_fl[(NCR > 1 ? NCR-2 : 0):0], cp_fl} : cp_fl;
            if (cp_v) frun <= cp_fl ? {LW{1'b0}} : frun + cp_cnt[LW-1:0];
        end
    end
    generate
        for (gr = 0; gr < NCR; gr = gr + 1) begin : g_rst
            wire [2*W*RE-1:0] a0 = (gr == 0) ? rin : rof[2*W*RE*(gr == 0 ? 0 : gr - 1) +: 2*W*RE];
            wire [LW-1:0]     f  = (gr == 0) ? frun : rff[LW*(gr == 0 ? 0 : gr - 1) +: LW];
            wire [2*W*RE-1:0] a1, a2;
            ot_s81ph_native_sel_rstage #(.N(2 * W), .RE(RE), .S(2 * gr)) u_r0 (.a(a0), .sh(f[2 * gr]), .y(a1));
            if (2 * gr + 1 < LW) begin : g_r1
                ot_s81ph_native_sel_rstage #(.N(2 * W), .RE(RE), .S(2 * gr + 1)) u_r1 (.a(a1), .sh(f[2 * gr + 1]), .y(a2));
            end else begin : g_r1n
                assign a2 = a1;
            end
            reg [2*W*RE-1:0] q;
            reg [LW-1:0]     qf;
            reg [LW:0]       qc;
            always @(posedge clk) begin
                q  <= a2;
                qf <= f;
                qc <= (gr == 0) ? cp_cnt : rcf[(LW+1)*(gr == 0 ? 0 : gr - 1) +: LW+1];
            end
            assign rof[2*W*RE*gr +: 2*W*RE] = q;
            assign rff[LW*gr +: LW] = qf;
            assign rcf[(LW+1)*gr +: LW+1] = qc;
        end
    endgenerate

    // accumulate
    wire [2*W*RE-1:0] rq = rof[2*W*RE*(NCR-1) +: 2*W*RE];
    wire              rq_v = ro_v[NCR-1], rq_fl = ro_fl[NCR-1];
    wire [LW:0]       rq_tot = {1'b0, rff[LW*(NCR-1) +: LW]} + rcf[(LW+1)*(NCR-1) +: LW+1];
    reg  [W*RE-1:0]   acc;
    reg               oflush;
    wire [2*W*RE-1:0] win;
    generate
        for (gl = 0; gl < 2 * W; gl = gl + 1) begin : g_win
            if (gl < W) begin : g_l
                assign win[RE*gl +: RE] = acc[RE*gl + RE - 1] ? acc[RE*gl +: RE] : rq[RE*gl +: RE];
            end else begin : g_h
                assign win[RE*gl +: RE] = rq[RE*gl +: RE];
            end
        end
    endgenerate
    reg [W*RE-1:0] oline_d;
    reg            ov_d;
    integer l;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc <= 0; oflush <= 1'b0; o_v <= 1'b0; o_bv <= 1'b0; o_fl <= 1'b0;
        end else begin
            o_v <= 1'b0; o_fl <= 1'b0; o_bv <= rq_v;
            if (oflush) begin
                o_v <= 1'b1; o_fl <= 1'b1; acc <= 0; oflush <= 1'b0;
            end else if (rq_v) begin
                if (rq_tot[LW]) begin
                    o_v <= 1'b1;
                    acc <= win[2*W*RE-1:W*RE];
                    if (rq_fl) begin
                        if (rq_tot[LW-1:0] != 0) oflush <= 1'b1;
                        else begin o_fl <= 1'b1; acc <= 0; end
                    end
                end else if (rq_fl) begin
                    o_v <= (rq_tot != 0); o_fl <= 1'b1; acc <= 0;
                end else acc <= win[W*RE-1:0];
            end
        end
    end
    always @(*) oline_d = oflush ? acc : win[W*RE-1:0];
    always @(posedge clk) begin
        for (l = 0; l < W; l = l + 1) begin
            o_lv[l] <= oline_d[RE*l + RE - 1];
            o_line[PW*l +: PW] <= oline_d[RE*l +: PW];
        end
    end
endmodule

// ---------------------------------------------------------------------------
// Two-step radix-16 threshold search over Q slices' histograms (fully pipelined; a new
// search every edge).  Result: the highest bucket b (8 bits) such that count(>= b) >= q, with
// above = count(> b) and ok = 1; when no bucket qualifies, b = 0, above = count(> 0), ok = 0
// (so "b = 0 and quota m = q - above" is ot_hdc_tselect's walk result in both cases).
// Step A reads the slices' registered group sums (gs); its group G leaves on g_out (a register)
// and the slices return the registered hbin of G (bs) three edges later; step B searches them.
// Latency: a result is registered 14 edges after the gs it was computed from.  Counts sampled
// at different edges are consistent as long as they only grow (then ok still implies
// count_now(>= b) >= q); with static counts the result is exact.
// eq: per-slice bin b count taken from the current bs one edge after res_b (exact once the
// counts are static).
// ---------------------------------------------------------------------------
module ot_s81ph_native_sel_su #(
    parameter integer Q  = 4,
    parameter integer CB = 11,
    parameter integer QW = 11,                      // quota width
    parameter integer XR = 0                        // CLAUDE S81-PH tiles: extra edges in the slice round trip (default 0)
) (
    input  wire                  clk,
    input  wire [Q*16*(CB+4)-1:0] gs,
    input  wire [Q*16*CB-1:0]    bs,
    input  wire [QW-1:0]         q,
    output reg  [3:0]            g_out,
    output reg  [7:0]            res_b,
    output reg  [CB+9:0]         res_above,
    output reg                   res_ok,
    output reg  [Q*CB-1:0]       res_eq
);
    localparam integer GW = CB + 4;
    localparam integer SW = GW + 2;                 // sum of <= 4 slices
    localparam integer XW = CB + 10;                // suffix sums (16 x SW)
    integer i, s;

    // -- step A: slice sums -> suffix sums -> highest group ----------------------------------
    reg [Q*16*GW-1:0] gs_r;
    reg [16*SW-1:0]   sa_r;
    reg [16*XW-1:0]   s2_r, s3_r;
    reg [QW-1:0]      q0, q1, q2, q3;
    reg [16*SW-1:0]   sa_d;
    reg [16*XW-1:0]   s2_d, t_d, s3_d;
    always @(*) begin
        for (i = 0; i < 16; i = i + 1) begin
            sa_d[SW*i +: SW] = {SW{1'b0}};
            for (s = 0; s < Q; s = s + 1)
                sa_d[SW*i +: SW] = sa_d[SW*i +: SW] + {{(SW-GW){1'b0}}, gs_r[GW*(16*s + i) +: GW]};
        end
        for (i = 0; i < 16; i = i + 1) begin
            s2_d[XW*i +: XW] = {{(XW-SW){1'b0}}, sa_r[SW*i +: SW]};
            for (s = 1; s < 4; s = s + 1)
                if (i + s < 16) s2_d[XW*i +: XW] = s2_d[XW*i +: XW] + {{(XW-SW){1'b0}}, sa_r[SW*((i + s) % 16) +: SW]};
        end
        for (i = 0; i < 16; i = i + 1)
            t_d[XW*i +: XW] = s2_r[XW*i +: XW] + ((i + 4 < 16) ? s2_r[XW*((i + 4) % 16) +: XW] : {XW{1'b0}});
        for (i = 0; i < 16; i = i + 1)
            s3_d[XW*i +: XW] = t_d[XW*i +: XW] + ((i + 8 < 16) ? t_d[XW*((i + 8) % 16) +: XW] : {XW{1'b0}});
    end
    always @(posedge clk) begin
        gs_r <= gs;   q0 <= q;
        sa_r <= sa_d; q1 <= q0;
        s2_r <= s2_d; q2 <= q1;
        s3_r <= s3_d; q3 <= q2;
    end
    // compares registered, then the priority encode and the suffix mux
    reg [15:0]      gea;
    reg [16*XW-1:0] s4_r;
    reg [QW-1:0]    q4;
    always @(posedge clk) begin
        for (i = 0; i < 16; i = i + 1) gea[i] <= (s3_r[XW*i +: XW] >= {{(XW-QW){1'b0}}, q3});
        s4_r <= s3_r; q4 <= q3;
    end
    reg [3:0]    ga;
    reg [XW-1:0] acca;
    always @(*) begin
        ga = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (gea[i]) ga = i[3:0];
        acca = (ga == 4'd15) ? {XW{1'b0}} : s4_r[XW*(ga + 4'd1) +: XW];
    end
    reg [XW-1:0] acc_a;
    reg [QW-1:0] qa;
    always @(posedge clk) begin g_out <= ga; acc_a <= acca; qa <= q4; end

    // -- 3-edge round trip through the slices, then step B over the hbin of G ----------------
    reg [XW-1:0] acc_d1, acc_d2, acc_d3, acc_b1, acc_b2, acc_b3;
    reg [QW-1:0] q_d1, q_d2, q_d3, q_b1, q_b2, q_b3;
    reg [3:0]    g_d1, g_d2, g_d3, g_b1, g_b2, g_b3;
    // the step-A results wait XR more edges when the slices sit XR edges further away (hardened tiles)
    wire [XW-1:0] acc_e; wire [QW-1:0] q_e; wire [3:0] g_e;
    generate if (XR == 0) begin : g_x0
        assign acc_e = acc_d3; assign q_e = q_d3; assign g_e = g_d3;
    end else begin : g_x
        reg [XW+QW+4-1:0] xd [1:XR];
        integer xi;
        always @(posedge clk) begin
            xd[1] <= {acc_d3, q_d3, g_d3};
            for (xi = 2; xi <= XR; xi = xi + 1) xd[xi] <= xd[xi-1];
        end
        assign {acc_e, q_e, g_e} = xd[XR];
    end endgenerate
    reg [Q*16*CB-1:0] bs_r;
    reg [16*SW-1:0]   sb_r;
    reg [16*XW-1:0]   u2_r, u3_r;
    reg [16*SW-1:0]   sb_d;
    reg [16*XW-1:0]   u2_d, v_d, u3_d;
    always @(*) begin
        for (i = 0; i < 16; i = i + 1) begin
            sb_d[SW*i +: SW] = {SW{1'b0}};
            for (s = 0; s < Q; s = s + 1)
                sb_d[SW*i +: SW] = sb_d[SW*i +: SW] + {{(SW-CB){1'b0}}, bs_r[CB*(16*s + i) +: CB]};
        end
        for (i = 0; i < 16; i = i + 1) begin
            u2_d[XW*i +: XW] = {{(XW-SW){1'b0}}, sb_r[SW*i +: SW]};
            for (s = 1; s < 4; s = s + 1)
                if (i + s < 16) u2_d[XW*i +: XW] = u2_d[XW*i +: XW] + {{(XW-SW){1'b0}}, sb_r[SW*((i + s) % 16) +: SW]};
        end
        for (i = 0; i < 16; i = i + 1)
            v_d[XW*i +: XW] = u2_r[XW*i +: XW] + ((i + 4 < 16) ? u2_r[XW*((i + 4) % 16) +: XW] : {XW{1'b0}});
        for (i = 0; i < 16; i = i + 1)
            u3_d[XW*i +: XW] = acc_b2 + v_d[XW*i +: XW] + ((i + 8 < 16) ? v_d[XW*((i + 8) % 16) +: XW] : {XW{1'b0}});
    end
    always @(posedge clk) begin
        acc_d1 <= acc_a;  acc_d2 <= acc_d1; acc_d3 <= acc_d2;
        q_d1   <= qa;     q_d2   <= q_d1;   q_d3   <= q_d2;
        g_d1   <= g_out;  g_d2   <= g_d1;   g_d3   <= g_d2;
        bs_r   <= bs;
        sb_r   <= sb_d;   acc_b1 <= acc_e;  q_b1 <= q_e;  g_b1 <= g_e;
        u2_r   <= u2_d;   acc_b2 <= acc_b1; q_b2 <= q_b1; g_b2 <= g_b1;
        u3_r   <= u3_d;   acc_b3 <= acc_b2; q_b3 <= q_b2; g_b3 <= g_b2;
    end
    reg [15:0]      geb;
    reg [16*XW-1:0] u4_r;
    reg [XW-1:0]    acc_b4;
    reg [3:0]       g_b4;
    always @(posedge clk) begin
        for (i = 0; i < 16; i = i + 1) geb[i] <= (u3_r[XW*i +: XW] >= {{(XW-QW){1'b0}}, q_b3});
        u4_r <= u3_r; acc_b4 <= acc_b3; g_b4 <= g_b3;
    end
    reg [3:0]    bb;
    reg          okb;
    reg [XW-1:0] aboveb;
    always @(*) begin
        bb = 4'd0; okb = 1'b0;
        for (i = 0; i < 16; i = i + 1)
            if (geb[i]) begin bb = i[3:0]; okb = 1'b1; end
        aboveb = (bb == 4'd15) ? acc_b4 : u4_r[XW*(bb + 4'd1) +: XW];
    end
    always @(posedge clk) begin
        res_b <= {g_b4, bb}; res_ok <= okb; res_above <= aboveb;
        for (s = 0; s < Q; s = s + 1)                // one edge after res_b (static counts only)
            res_eq[CB*s +: CB] <= bs_r[CB*(16*s + res_b[3:0]) +: CB];
    end
endmodule
