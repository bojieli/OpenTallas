`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_rx (s81-functional-token 2026-10-14, die item F1): the three SU job kinds the S81 stage programs issue to the
// SU (eng su, port 1) that no S81 die unit computed:
//
//   RA (kind 8)  L*.ffn.softplus_sqrt  r = sqrt(softplus(x)) of the die's router scores     tools/hdc_golden_v41.softplus
//                                       (exp, t + 2, t / den, Horner in u^2, 2 u p, max(x,0) + l, sqrt), every rounding
//                                       the golden's: each lane is ot_hdc_v41x_softplus_s #(PCUT 1) (rtl/hdc/v41x/
//                                       ot_hdc_v41x_spshort.sv: the same bits as the serial unit, exhaustive 2^32
//                                       evidence results/rtl/w11_softplus_short.json; lever su_routeract)
//   RB (kind 9)  L*.ffn.bias           y = scores + bias (binary32 add, RNE, canonical +0: golden add) -- the selector's
//                                       biased scores; the unbiased scores stay where they are for route_w
//   QR (kind 10) L*.attn.q_rope        rope_tail(q, cs) on each q head's last 64 elements (adjacent pairs, forward):
//                                       re = a*c + (-(b*s)), im = b*c + a*s, each stored BF16 (RNE) in a binary32 word,
//                                       the arithmetic of ot_dsrom_su_norm's RD tail (golden rope_tail)
//
// The core hands the unit ONE operand beat holding every operand row of the job (bt, NR rows, stable while the unit
// runs: the core assembles no other beat for this job) and a start pulse; the unit walks the beat a row at a time and
// emits one result row (16 binary32 words) a cycle on o_v / o_i (row index) / o_d, in row order:
//   RA  NR rows of scores                      -> NR rows of r          (RAL lanes: a row takes 16 / RAL issue cycles)
//   RB  rows 0..NR/2-1 scores, NR/2.. bias     -> NR/2 rows of scores + bias
//   QR  4 rows a head (the head's rope rows)   -> NR rows, row j of a head rotated with pairs 8 (j % 4) .. 8 (j % 4) + 7
// cos / sin: the position's 32-entry RoPE table (QR; the descriptor's parameter rows, as KV / SO).
// fault: a lane's range check (spsqrt) or the rotation's adder; sticky until reset.
// MUT (negative controls of the SU gate): 1 RA returns softplus (sp) instead of sqrt(softplus); 2 RB drops the bias
// (scores pass); 3 QR uses the INVERSE rotation (the SO tail's sign).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_rx #(
    parameter integer BR  = 64,             // beat rows the core can hold (its BMAX)
    parameter integer RAL = 16,             // RA lanes (16, 8 or 4)
    parameter integer LM  = 5,
    parameter integer LA  = 4,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,          // one cycle: the beat is complete in bt
    input  wire [1:0]        knd,            // 0 RA, 1 RB, 2 QR
    input  wire [15:0]       nr,             // operand rows in the beat
    input  wire [BR*512-1:0] bt,
    input  wire [32*32-1:0]  cos_t,
    input  wire [32*32-1:0]  sin_t,
    output reg               o_v,
    output reg  [15:0]       o_i,
    output reg  [511:0]      o_d,
    output reg               fault
);
    localparam integer SUB = 16 / RAL;      // RA issue cycles a row
    localparam integer LMR = LM + 1, LAR = (LA >= 5) ? LA : LA + 1;
    localparam integer DQ  = LMR + LAR + 1; // QR: multiply, add, BF16 output register
    localparam integer DB  = LAR + 1;       // RB: add, output register
`ifndef SYNTHESIS
    initial if (SUB * RAL != 16 || SUB > 4) $fatal(1, "ot_s81_su_rx: RAL must be 16, 8 or 4");
`endif
    function automatic [31:0] bf16(input [31:0] x);         // RNE to BF16 (tools/hdc_golden.to_bf16)
        reg [32:0] s;
        begin
            s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {s[31:16], 16'd0};
        end
    endfunction

    // ------------------------------------------------------------------ the row walker
    reg         run;
    reg  [1:0]  k;
    reg  [15:0] n, ri;                      // rows to walk, next row
    reg  [1:0]  si;                         // RA sub-issue of the row
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin run <= 0; k <= 0; n <= 0; ri <= 0; si <= 0; end
        else if (start) begin run <= 1; k <= knd; n <= (knd == 2'd1) ? nr >> 1 : nr; ri <= 0; si <= 0; end
        else if (run) begin
            if (k != 2'd0 || si == SUB - 1) begin
                si <= 0; ri <= ri + 1;
                if (ri + 1 == n) run <= 0;
            end else si <= si + 1;
        end
    end
    wire [511:0] xr = bt[512 * ri +: 512];                  // the walked operand row
    wire [511:0] br = bt[512 * (ri + n) +: 512];            // RB: its bias row
    wire iss_a = run && k == 2'd0, iss_b = run && k == 2'd1, iss_q = run && k == 2'd2;

    // ------------------------------------------------------------------ RA: sqrt(softplus), RAL lanes
    wire [RAL*32-1:0] ra_x;
    genvar l;
    generate
        for (l = 0; l < RAL; l = l + 1) begin : g_ax
            assign ra_x[32 * l +: 32] = xr[32 * (RAL * si + l) +: 32];
        end
    endgenerate
    wire [RAL*32-1:0] ra_r, ra_sp;
    wire [RAL-1:0]    ra_vo, ra_f;
    generate
        for (l = 0; l < RAL; l = l + 1) begin : g_ra
            ot_hdc_v41x_softplus_s #(.PCUT(1)) u (.clk(clk), .rst_n(rst_n), .v(iss_a), .x(ra_x[32 * l +: 32]),
                .sp(ra_sp[32 * l +: 32]), .r(ra_r[32 * l +: 32]), .vo(ra_vo[l]), .fault(ra_f[l]));
        end
    endgenerate
    // the lanes return in issue order: count the output sub-beats (no reliance on the lane depth)
    reg [1:0]   ra_so;
    reg [15:0]  ra_io;
    reg [511:0] ra_row;                      // the row being re-assembled from its sub-issues
    reg         ra_ov;
    reg [15:0]  ra_oi;
    integer g;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ra_ov <= 0; ra_oi <= 0; ra_so <= 0; ra_io <= 0; end
        else begin
            ra_ov <= 0;
            if (start) begin ra_so <= 0; ra_io <= 0; end
            else if (ra_vo[0]) begin
                for (g = 0; g < RAL; g = g + 1)
                    ra_row[32 * (RAL * ra_so + g) +: 32] <= (MUT == 1) ? ra_sp[32 * g +: 32] : ra_r[32 * g +: 32];
                if (ra_so == SUB - 1) begin ra_ov <= 1; ra_oi <= ra_io; ra_so <= 0; ra_io <= ra_io + 1; end
                else ra_so <= ra_so + 1;
            end
        end
    end

    // ------------------------------------------------------------------ RB: scores + bias, 16 lanes
    wire [511:0] rb_y; wire [15:0] rb_f;
    wire [DB:0] vbl;
    ot_hdc_vline #(.D(DB)) u_vbl (.clk(clk), .rst_n(rst_n), .v(iss_b), .vd(vbl));
    generate
        for (l = 0; l < 16; l = l + 1) begin : g_rb
            wire fb;
            ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, iss_b, xr[32 * l +: 32], (MUT == 2) ? 32'd0 : br[32 * l +: 32],
                                            rb_y[32 * l +: 32], fb);
            assign rb_f[l] = fb;                // the adder's fault is gated by its own valid out
        end
    endgenerate
    wire [DB:0] vb = vbl; wire [15:0] rb_i;
    ot_hdc_delay #(.W(16), .D(DB)) u_bi (.clk(clk), .rst_n(rst_n), .d(ri), .q(rb_i));
    reg [511:0] rb_o;
    always @(posedge clk) rb_o <= rb_y;

    // ------------------------------------------------------------------ QR: forward RoPE of one row (8 pairs), 16 lanes
    wire [511:0] qr_y; wire [15:0] qr_f;
    wire [1:0]   qj = ri[1:0];                               // the row of the head's 4 rope rows
    generate
        for (l = 0; l < 16; l = l + 1) begin : g_qr
            localparam integer ODD = l % 2;
            wire [4:0]  kk = {qj, 3'd0} + (l / 2);
            wire [31:0] cc = cos_t[32 * kk +: 32], sn = sin_t[32 * kk +: 32];
            wire [31:0] mine = xr[32 * l +: 32], pair = xr[32 * (ODD ? l - 1 : l + 1) +: 32];
            // forward: a' = a*c + (-(b*s)), b' = b*c + a*s; MUT 3: the inverse (a*c + b*s, b*c - a*s)
            wire [31:0] sg = ((ODD != 0) ^ (MUT == 3)) ? sn : {~sn[31], sn[30:0]};
            wire [31:0] pp, qq;
            wire f0, f1;
            ot_hdc_qmul_lat #(LMR) u_p (clk, rst_n, iss_q, mine, cc, pp, f0);
            ot_hdc_qmul_lat #(LMR) u_q (clk, rst_n, iss_q, pair, sg, qq, f1);
            wire [DQ:0] vq_;
            ot_hdc_vline #(.D(DQ)) u_vq (.clk(clk), .rst_n(rst_n), .v(iss_q), .vd(vq_));
            wire [31:0] rs; wire f2;
            ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, vq_[LMR], pp, qq, rs, f2);
            assign qr_y[32 * l +: 32] = rs;
            assign qr_f[l] = f0 | f1 | f2;      // each unit's fault is gated by its own valid out
        end
    endgenerate
    wire [DQ:0] vqo; wire [15:0] qr_i;
    ot_hdc_vline #(.D(DQ)) u_vq (.clk(clk), .rst_n(rst_n), .v(iss_q), .vd(vqo));
    ot_hdc_delay #(.W(16), .D(DQ)) u_qi (.clk(clk), .rst_n(rst_n), .d(ri), .q(qr_i));
    reg [511:0] qr_o;
    always @(posedge clk) for (g = 0; g < 16; g = g + 1) qr_o[32 * g +: 32] <= bf16(qr_y[32 * g +: 32]);

    // ------------------------------------------------------------------ result row (one a cycle: one kind runs at a time)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_v <= 0; o_i <= 0; fault <= 0; end
        else begin
            o_v <= ra_ov | vb[DB] | vqo[DQ];
            o_i <= ra_ov ? ra_oi : vb[DB] ? rb_i : qr_i;
            if (|(ra_vo & ra_f) || |rb_f || |qr_f) fault <= 1;
        end
    end
    always @(posedge clk) o_d <= ra_ov ? ra_row : vb[DB] ? rb_o : qr_o;
endmodule
