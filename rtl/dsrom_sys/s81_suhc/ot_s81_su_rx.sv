`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_rx / ot_s81_su_rxe (s81-functional-token 2026-10-14, die item F1): the three SU job kinds the S81 stage
// programs issue to the SU (eng su, port 1) that no S81 die unit computed:
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
// ot_s81_su_rxe is the row engine shared by the flat core (through the walker ot_s81_su_rx) and the hierarchical slab's
// tile ot_s81_su_rxt: one operand row in (i_v / i_k / i_x, RB its bias row i_b, QR the row's index j within the head's 4
// rope rows), its result row out (o_v / o_d) in issue order.  RA with RAL < 16 lanes takes 16 / RAL cycles a row:
// i_rdy is low while a row is being issued.  cos / sin: the position's 32-entry RoPE table (QR).
// fault: a lane's range check (spsqrt) or an adder's / multiplier's error; sticky until reset.
// MUT (negative controls of the SU gate): 1 RA returns softplus (sp) instead of sqrt(softplus); 2 RB drops the bias
// (scores pass); 3 QR uses the INVERSE rotation (the SO tail's sign).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_rxe #(
    parameter integer RAL = 16,             // RA lanes (16, 8 or 4)
    parameter integer LM  = 5,
    parameter integer LA  = 4,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              i_v,
    input  wire [1:0]        i_k,            // 0 RA, 1 RB, 2 QR
    input  wire [511:0]      i_x,
    input  wire [511:0]      i_b,
    input  wire [1:0]        i_j,
    output wire              i_rdy,
    input  wire [32*32-1:0]  cos_t,
    input  wire [32*32-1:0]  sin_t,
    output reg               o_v,
    output reg  [511:0]      o_d,
    output reg               fault
);
    localparam integer SUB = 16 / RAL;      // RA issue cycles a row
    localparam integer LMR = LM + 1, LAR = (LA >= 5) ? LA : LA + 1;
    localparam integer DQ  = LMR + LAR + 1; // QR: multiply, add, BF16 output register
    localparam integer DB  = LAR + 1;       // RB: add, output register
`ifndef SYNTHESIS
    initial if (SUB * RAL != 16 || SUB > 4) $fatal(1, "ot_s81_su_rxe: RAL must be 16, 8 or 4");
`endif
    function automatic [31:0] bf16(input [31:0] x);         // RNE to BF16 (tools/hdc_golden.to_bf16)
        reg [32:0] s;
        begin
            s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {s[31:16], 16'd0};
        end
    endfunction
    genvar l;
    integer g;

    // ------------------------------------------------------------------ RA: sqrt(softplus), RAL lanes, SUB issues a row
    reg  [511:0] ax;                         // the row being issued (SUB > 1)
    reg  [1:0]   si;
    reg          abusy;
    wire         a_new = i_v && i_k == 2'd0;
    wire         iss_a = a_new || abusy;
    wire [1:0]   sub = a_new ? 2'd0 : si;
    wire [511:0] arow = a_new ? i_x : ax;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin abusy <= 0; si <= 0; end
        else if (a_new && SUB > 1) begin abusy <= 1; si <= 1; end
        else if (abusy) begin
            if (si == SUB - 1) begin abusy <= 0; si <= 0; end else si <= si + 1;
        end
    end
    always @(posedge clk) if (a_new) ax <= i_x;
    assign i_rdy = !abusy && !(a_new && SUB > 1);
    wire [RAL*32-1:0] ra_r, ra_sp;
    wire [RAL-1:0]    ra_vo, ra_f;
    generate
        for (l = 0; l < RAL; l = l + 1) begin : g_ra
            ot_hdc_v41x_softplus_s #(.PCUT(1)) u (.clk(clk), .rst_n(rst_n), .v(iss_a), .x(arow[32 * (RAL * sub + l) +: 32]),
                .sp(ra_sp[32 * l +: 32]), .r(ra_r[32 * l +: 32]), .vo(ra_vo[l]), .fault(ra_f[l]));
        end
    endgenerate
    // the lanes return in issue order: count the output sub-beats (no reliance on the lane depth)
    reg [1:0]   ra_so;
    reg [511:0] ra_row;
    reg         ra_ov;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ra_ov <= 0; ra_so <= 0; end
        else begin
            ra_ov <= 0;
            if (ra_vo[0]) begin
                if (ra_so == SUB - 1) begin ra_ov <= 1; ra_so <= 0; end else ra_so <= ra_so + 1;
            end
        end
    end
    always @(posedge clk)
        if (ra_vo[0])
            for (g = 0; g < RAL; g = g + 1)
                ra_row[32 * (RAL * ra_so + g) +: 32] <= (MUT == 1) ? ra_sp[32 * g +: 32] : ra_r[32 * g +: 32];

    // ------------------------------------------------------------------ RB: scores + bias, 16 lanes
    wire iss_b = i_v && i_k == 2'd1;
    wire [511:0] rb_y; wire [15:0] rb_f;
    generate
        for (l = 0; l < 16; l = l + 1) begin : g_rb
            ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, iss_b, i_x[32 * l +: 32], (MUT == 2) ? 32'd0 : i_b[32 * l +: 32],
                                            rb_y[32 * l +: 32], rb_f[l]);     // fault gated by the adder's valid out
        end
    endgenerate
    wire [DB:0] vb;
    ot_hdc_vline #(.D(DB)) u_vb (.clk(clk), .rst_n(rst_n), .v(iss_b), .vd(vb));
    reg [511:0] rb_o;
    always @(posedge clk) rb_o <= rb_y;

    // ------------------------------------------------------------------ QR: forward RoPE of one row (8 pairs), 16 lanes
    wire iss_q = i_v && i_k == 2'd2;
    wire [511:0] qr_y; wire [15:0] qr_f;
    wire [DQ:0] vq;
    ot_hdc_vline #(.D(DQ)) u_vq (.clk(clk), .rst_n(rst_n), .v(iss_q), .vd(vq));
    generate
        for (l = 0; l < 16; l = l + 1) begin : g_qr
            localparam integer ODD = l % 2;
            wire [4:0]  kk = {i_j, 3'd0} + (l / 2);
            wire [31:0] cc = cos_t[32 * kk +: 32], sn = sin_t[32 * kk +: 32];
            wire [31:0] mine = i_x[32 * l +: 32], pair = i_x[32 * (ODD ? l - 1 : l + 1) +: 32];
            // forward: a' = a*c + (-(b*s)), b' = b*c + a*s; MUT 3: the inverse (a*c + b*s, b*c - a*s)
            wire [31:0] sg = ((ODD != 0) ^ (MUT == 3)) ? sn : {~sn[31], sn[30:0]};
            wire [31:0] pp, qq, rs;
            wire f0, f1, f2;
            ot_hdc_qmul_lat #(LMR) u_p (clk, rst_n, iss_q, mine, cc, pp, f0);
            ot_hdc_qmul_lat #(LMR) u_q (clk, rst_n, iss_q, pair, sg, qq, f1);
            ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, vq[LMR], pp, qq, rs, f2);
            assign qr_y[32 * l +: 32] = rs;
            assign qr_f[l] = f0 | f1 | f2;   // each unit's fault is gated by its own valid out
        end
    endgenerate
    reg [511:0] qr_o;
    always @(posedge clk) for (g = 0; g < 16; g = g + 1) qr_o[32 * g +: 32] <= bf16(qr_y[32 * g +: 32]);

    // ------------------------------------------------------------------ result row (one job kind runs at a time)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_v <= 0; fault <= 0; end
        else begin
            o_v <= ra_ov | vb[DB] | vq[DQ];
            if (|(ra_vo & ra_f) || |rb_f || |qr_f) fault <= 1;
        end
    end
    always @(posedge clk) o_d <= ra_ov ? ra_row : vb[DB] ? rb_o : qr_o;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_rx: the flat core's form.  The core hands ONE operand beat holding every operand row of the job (bt, NR
// rows, stable while the walker runs) and a start pulse; the walker feeds the engine a row a cycle (RA: when the engine
// is ready), RB pairing score row r with bias row NR/2 + r; QR row r is rope row r % 4 of head r / 4.  Result rows come
// back in row order with their index o_i.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_rx #(
    parameter integer BR  = 64,             // beat rows the core can hold (its BMAX)
    parameter integer RAL = 16,
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
    output wire              o_v,
    output reg  [15:0]       o_i,
    output wire [511:0]      o_d,
    output wire              fault
);
    reg         run;
    reg  [1:0]  k;
    reg  [15:0] n, ri;
    wire        rdy;
    wire        iss = run && rdy;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin run <= 0; k <= 0; n <= 0; ri <= 0; end
        else if (start) begin run <= 1; k <= knd; n <= (knd == 2'd1) ? nr >> 1 : nr; ri <= 0; end
        else if (iss) begin
            ri <= ri + 1;
            if (ri + 1 == n) run <= 0;
        end
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) o_i <= 0; else if (start) o_i <= 0; else if (o_v) o_i <= o_i + 1;
    ot_s81_su_rxe #(.RAL(RAL), .LM(LM), .LA(LA), .MUT(MUT)) u_e (
        .clk(clk), .rst_n(rst_n), .i_v(iss), .i_k(k), .i_x(bt[512 * ri +: 512]), .i_b(bt[512 * (ri + n) +: 512]),
        .i_j(ri[1:0]), .i_rdy(rdy), .cos_t(cos_t), .sin_t(sin_t), .o_v(o_v), .o_d(o_d), .fault(fault));
endmodule
