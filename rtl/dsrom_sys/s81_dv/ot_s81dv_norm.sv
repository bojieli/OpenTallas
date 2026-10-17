`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-DV (owner 0cj 2026-10-16): the distributed RMSNorm of a vector slice.
//
// Slice g owns elements [g*NVL*64, (g+1)*NVL*64) of every D-vector, i.e. the global 64-lane beats g*NVL .. g*NVL+NVL-1
// of the flat engine (ot_dsrom_su_norm N = 64: lane l of beat v = element v*64 + l).  Each beat is an aligned 8-chunk
// subtree of the golden csum (chunk8: chunks of 8 sequential from +0, then a pairwise tree padded to a power of two),
// so the slice's ot_hbm_norm_grp (G = 64, unchanged) produces exactly the flat engine's per-beat partials.  The NVL
// partials travel as ONE flit on the slice ring (ot_s81dv_xstop: fixed hop counts, registered stages, no flow control);
// every slice receives all NS flits and finishes the identical golden tree above the beats (ot_s81dv_norm_finish: the
// vector levels of ot_dsrom_su_norm verbatim, then / D, + eps, rsqrt), so every slice computes the same rstd from the
// same operands in the same order -- bit-identical to the flat engine and to hdc_golden_v41.
//
//   ot_s81dv_norm_finish : vector-level tree over NV = NS*NVL beat partials (flits on P ports, any arrival order)
//   ot_s81dv_xstop       : exchange ring stop (E- and W-bound flits; inject, deliver, forward with hop count)
//   ot_s81dv_norm_slice  : ot_hbm_norm_grp G64 + partial collector + ring stop + finish (the slice's norm datapath)
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81dv_norm_finish #(
    parameter integer NV = 80,          // global beats (NS slices x NVL)
    parameter integer K  = 5,           // beat partials per flit (NVL)
    parameter integer P  = 3,           // flit input ports (own, from W, from E)
    parameter integer D  = 5120,
    parameter integer LM = 5,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [P-1:0]      f_v,
    input  wire [P*8-1:0]    f_base,      // global index of the flit's first partial
    input  wire [P*K*32-1:0] f_d,
    input  wire [31:0]       eps,
    output wire              r_v,
    output wire [31:0]       r,
    output wire              fault
);
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer tz(input integer x);
        integer t;
        begin
            t = 0;
            while (t < 31 && ((x >> t) & 1) == 0) t = t + 1;
            tz = t;
        end
    endfunction
    localparam integer DK = tz(D);
    localparam integer DF = D >> DK;
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    // input flops (every input pin lands in a flop)
    reg [P-1:0] iv; reg [P*8-1:0] ib; reg [P*K*32-1:0] id; reg [31:0] eps_c;
    always @(posedge clk or negedge rstn) if (!rstn) iv <= {P{1'b0}}; else iv <= go_t ? {P{1'b0}} : f_v;
    always @(posedge clk) begin ib <= f_base; id <= f_d; eps_c <= eps; end

    // ---------------------------------------------------------------- vector levels (ot_dsrom_su_norm, verbatim tree)
    wire [31:0] nv [1:2*NVP-1];
    wire        nd [1:2*NVP-1];
    wire        np [1:2*NVP-1];
    wire [NVP:0] nf;
    wire [NVP-1:0] dup;                 // a leaf hit twice in one row (exchange schedule error)
    assign nf[0] = 1'b0;
    assign nf[NVP] = 1'b0;
    genvar n, p, k;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            wire [P*K-1:0] m;
            wire [31:0] mv [0:P*K];
            assign mv[0] = 32'd0;
            for (p = 0; p < P; p = p + 1) begin : g_p
                for (k = 0; k < K; k = k + 1) begin : g_k
                    if (IX - k >= 0) begin : g_m
`ifdef OT_S81DV_MUT_LEAF
                        // NEGATIVE CONTROL: leaves 0 and 1 swapped (finish tree fed out of golden order)
                        localparam integer IXM = (IX == 0) ? 1 : (IX == 1) ? 0 : IX;
                        assign m[p * K + k] = iv[p] && (ib[p * 8 +: 8] == IXM - k) && (IXM - k >= 0);
`else
                        assign m[p * K + k] = iv[p] && (ib[p * 8 +: 8] == IX - k);
`endif
                    end else begin : g_n
                        assign m[p * K + k] = 1'b0;
                    end
                    assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                end
            end
            wire hit = |m;
            reg [31:0] val;
            reg        vld;
            always @(posedge clk or negedge rstn)
                if (!rstn) vld <= 1'b0;
                else if (go_t) vld <= 1'b0;
                else if (hit) vld <= 1'b1;
            always @(posedge clk) if (hit) val <= mv[P * K];
            assign dup[IX] = hit && (vld || ((m & (m - 1)) != 0));
            if (IX < NV) begin : g_live
                assign np[n] = hit;
                assign nd[n] = vld || hit;
                assign nv[n] = vld ? val : mv[P * K];
            end else begin : g_pad
                assign np[n] = 1'b0;
                assign nd[n] = 1'b0;
                assign nv[n] = 32'd0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_vn
            localparam integer H = $clog2(NVP) - ($clog2(n + 1) - 1);
            if ((((2 * n + 1) << (H - 1)) - NVP) < NV) begin : g_add
                reg st, vld;
                reg [31:0] val;
                wire [LAV:0] av;
                wire [31:0] sm;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !st && !go_t;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(fire), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, fire, nv[2 * n], nv[2 * n + 1], sm, nf[n]);
                always @(posedge clk or negedge rstn) begin
                    if (!rstn) begin st <= 1'b0; vld <= 1'b0; end
                    else if (go_t) begin st <= 1'b0; vld <= 1'b0; end
                    else begin
                        if (fire) st <= 1'b1;
                        if (av[LAV]) vld <= 1'b1;
                    end
                end
                always @(posedge clk) if (av[LAV]) val <= sm;
                assign np[n] = av[LAV];
                assign nd[n] = vld || av[LAV];
                assign nv[n] = vld ? val : sm;
            end else begin : g_pass
                assign nv[n] = nv[2 * n];
                assign nd[n] = nd[2 * n];
                assign np[n] = np[2 * n];
                assign nf[n] = 1'b0;
            end
        end
    endgenerate
    wire        ss_v = np[1] && !go_t;
    wire [31:0] ss = nv[1];
    // ---------------------------------------------------------------- tail: / D, + eps, rsqrt (ot_dsrom_su_norm)
    reg ssr_v; reg [31:0] ssr;
    always @(posedge clk or negedge rstn) if (!rstn) ssr_v <= 1'b0; else ssr_v <= ss_v;
    always @(posedge clk) ssr <= ss;
    wire [31:0] mq, me, rr;
    wire        mq_v, me_v, rr_v, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rstn), .v(ssr_v), .x(ssr), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rstn), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rstn, mq_v, mq, eps_c, me, f_eps);
    assign me_v = ve[LA];
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rstn), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    reg r_v_o; reg [31:0] r_o; reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin r_v_o <= 1'b0; flt <= 1'b0; end
        else begin
            r_v_o <= rr_v;
            if (go_t) flt <= 1'b0;
            else if ((|nf) || f_div || f_eps || f_rsq || (|dup)) flt <= 1'b1;
        end
    always @(posedge clk) r_o <= rr;
    assign r_v = r_v_o; assign r = r_o; assign fault = flt;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Exchange ring stop.  A flit {hops, base, K x 32} injected here goes E with HE hops and W with HW hops (HE + HW =
// NS - 1, so every other stop receives it exactly once).  A flit arriving from W is delivered and, if hops > 1,
// forwarded E with hops - 1 one cycle later (and the same for E -> W).  The compiler schedules injections so that an
// injection never meets a forward on the same output in the same cycle (every stop injects on the same cycle; the
// first forward arrives one link + one stop later); a collision is a fault, never a stall: no credits, no ready.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81dv_xstop #(
    parameter integer K  = 5,
    parameter integer HE = 8,
    parameter integer HW = 7
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            inj_v,
    input  wire [7:0]      inj_base,
    input  wire [K*32-1:0] inj_d,
    input  wire            wi_v,  input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [K*32-1:0] wi_d,   // E-bound in
    input  wire            ei_v,  input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [K*32-1:0] ei_d,   // W-bound in
    output reg             eo_v,  output reg  [3:0] eo_h, output reg  [7:0] eo_b, output reg  [K*32-1:0] eo_d,
    output reg             wo_v,  output reg  [3:0] wo_h, output reg  [7:0] wo_b, output reg  [K*32-1:0] wo_d,
    output wire [2:0]      dl_v,                  // deliver: [0] own, [1] from W, [2] from E
    output wire [3*8-1:0]  dl_b,
    output wire [3*K*32-1:0] dl_d,
    output reg             fault
);
    // input flops
    reg iv0, iv1, iv2; reg [3:0] ih1, ih2; reg [7:0] ib0, ib1, ib2; reg [K*32-1:0] id0, id1, id2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv0 <= 1'b0; iv1 <= 1'b0; iv2 <= 1'b0; end
        else begin iv0 <= inj_v; iv1 <= wi_v; iv2 <= ei_v; end
    always @(posedge clk) begin
        ib0 <= inj_base; id0 <= inj_d; ih1 <= wi_h; ib1 <= wi_b; id1 <= wi_d; ih2 <= ei_h; ib2 <= ei_b; id2 <= ei_d;
    end
    wire fe = iv1 && ih1 > 4'd1;        // forward east
    wire fw = iv2 && ih2 > 4'd1;        // forward west
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin eo_v <= 1'b0; wo_v <= 1'b0; fault <= 1'b0; end
        else begin
            eo_v <= fe || (iv0 && HE > 0);
            wo_v <= fw || (iv0 && HW > 0);
            if (iv0 && (fe || fw)) fault <= 1'b1;
        end
    always @(posedge clk) begin
        if (fe) begin eo_h <= ih1 - 4'd1; eo_b <= ib1; eo_d <= id1; end
        else begin eo_h <= HE[3:0]; eo_b <= ib0; eo_d <= id0; end
        if (fw) begin wo_h <= ih2 - 4'd1; wo_b <= ib2; wo_d <= id2; end
        else begin wo_h <= HW[3:0]; wo_b <= ib0; wo_d <= id0; end
    end
    assign dl_v = {iv2, iv1, iv0};
    assign dl_b = {ib2, ib1, ib0};
    assign dl_d = {id2, id1, id0};
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81dv_xfin: the slice's NEW norm logic as one leaf tile -- the partial collector (NVL beat partials -> one flit),
// the exchange ring stop and the replicated finish.  Every input pin lands in a flop (robust first cell; no hold
// padding at the pins: hold belongs to the die-level budget at the relay stations).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81dv_xfin #(
    parameter integer SID = 0,
    parameter integer NS  = 16,
    parameter integer NVL = 5,
    parameter integer LM  = 5,
    parameter integer LA  = 6
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               go,
    input  wire [31:0]        eps,
    input  wire               s_v,          // group beat partials
    input  wire [7:0]         s_i,
    input  wire [31:0]        s,
    input  wire               wi_v, input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [NVL*32-1:0] wi_d,
    input  wire               ei_v, input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [NVL*32-1:0] ei_d,
    output wire               eo_v, output wire [3:0] eo_h, output wire [7:0] eo_b, output wire [NVL*32-1:0] eo_d,
    output wire               wo_v, output wire [3:0] wo_h, output wire [7:0] wo_b, output wire [NVL*32-1:0] wo_d,
    output reg                rb_v,         // rstd to the group scale
    output reg  [31:0]        rb_d,
    output wire               fault
);
    localparam integer HE = NS / 2, HW = NS - 1 - NS / 2;
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    reg go_c; reg [31:0] eps_c; reg sv_c; reg [7:0] si_c; reg [31:0] s_c;
    always @(posedge clk) begin go_c <= go; eps_c <= eps; si_c <= s_i; s_c <= s; end
    always @(posedge clk or negedge rstn) if (!rstn) sv_c <= 1'b0; else sv_c <= s_v;
    reg [NVL*32-1:0] col; reg inj_v;
    always @(posedge clk or negedge rstn) if (!rstn) inj_v <= 1'b0; else inj_v <= sv_c && si_c == NVL - 1;
    always @(posedge clk) if (sv_c) col[si_c * 32 +: 32] <= s_c;
`ifdef OT_S81DV_MUT_BASE
    // NEGATIVE CONTROL: slice 3 tags its flit as slice 4's (exchange delivers partials to the wrong tree leaves)
    localparam integer SBASE = (SID == 3) ? 4 * NVL : SID * NVL;
`else
    localparam integer SBASE = SID * NVL;
`endif
    wire [2:0] dl_v; wire [3*8-1:0] dl_b; wire [3*NVL*32-1:0] dl_d; wire xf, rf;
    ot_s81dv_xstop #(.K(NVL), .HE(HE), .HW(HW)) u_x (.clk(clk), .rst_n(rstn), .inj_v(inj_v), .inj_base(SBASE[7:0]),
        .inj_d(col), .wi_v(wi_v), .wi_h(wi_h), .wi_b(wi_b), .wi_d(wi_d), .ei_v(ei_v), .ei_h(ei_h), .ei_b(ei_b), .ei_d(ei_d),
        .eo_v(eo_v), .eo_h(eo_h), .eo_b(eo_b), .eo_d(eo_d), .wo_v(wo_v), .wo_h(wo_h), .wo_b(wo_b), .wo_d(wo_d),
        .dl_v(dl_v), .dl_b(dl_b), .dl_d(dl_d), .fault(xf));
    wire fr_v; wire [31:0] fr;
    ot_s81dv_norm_finish #(.NV(NS * NVL), .K(NVL), .P(3), .D(64 * NVL * NS), .LM(LM), .LA(LA)) u_f (.clk(clk),
        .rst_n(rstn), .go(go_c), .f_v(dl_v), .f_base(dl_b), .f_d(dl_d), .eps(eps_c), .r_v(fr_v), .r(fr), .fault(rf));
    always @(posedge clk or negedge rstn) if (!rstn) rb_v <= 1'b0; else rb_v <= fr_v;
    always @(posedge clk) rb_d <= fr;
    reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt <= 1'b0; else if (go_c) flt <= 1'b0; else if (xf || rf) flt <= 1'b1;
    assign fault = flt;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The slice's norm datapath: ot_hbm_norm_grp (G = 64, the slice's NVL beats, unchanged) + ot_s81dv_xfin.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81dv_norm_slice #(
    parameter integer SID = 0,
    parameter integer NS  = 16,
    parameter integer NVL = 5,
    parameter integer LM  = 5,
    parameter integer LA  = 6
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               go,
    input  wire               in_v,
    input  wire [4*64*32-1:0] in_x,
    input  wire [127:0]       pre,
    input  wire [31:0]        eps,
    input  wire               wl_v,
    input  wire [7:0]         wl_i,
    input  wire [64*32-1:0]   wl_d,
    input  wire               wi_v, input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [NVL*32-1:0] wi_d,
    input  wire               ei_v, input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [NVL*32-1:0] ei_d,
    output wire               eo_v, output wire [3:0] eo_h, output wire [7:0] eo_b, output wire [NVL*32-1:0] eo_d,
    output wire               wo_v, output wire [3:0] wo_h, output wire [7:0] wo_b, output wire [NVL*32-1:0] wo_d,
    output wire               y_v,
    output wire [7:0]         y_i,
    output wire [64*32-1:0]   y,
    output wire               r_v,
    output wire [31:0]        r,
    output wire               fault
);
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    wire s_v, gf, xff, rb_v; wire [7:0] s_i; wire [31:0] s, rb_d;
    ot_hbm_norm_grp #(.G(64), .D(64 * NVL), .N(64), .LM(LM), .LA(LA)) u_g (.clk(clk), .rst_n(rstn), .go(go), .in_v(in_v),
        .in_x(in_x), .pre(pre), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .rb_v(rb_v), .rb_d(rb_d),
        .s_v(s_v), .s_i(s_i), .s(s), .y_v(y_v), .y_i(y_i), .y(y), .gf(gf));
    ot_s81dv_xfin #(.SID(SID), .NS(NS), .NVL(NVL), .LM(LM), .LA(LA)) u_xf (.clk(clk), .rst_n(rstn), .go(go), .eps(eps),
        .s_v(s_v), .s_i(s_i), .s(s), .wi_v(wi_v), .wi_h(wi_h), .wi_b(wi_b), .wi_d(wi_d), .ei_v(ei_v), .ei_h(ei_h),
        .ei_b(ei_b), .ei_d(ei_d), .eo_v(eo_v), .eo_h(eo_h), .eo_b(eo_b), .eo_d(eo_d), .wo_v(wo_v), .wo_h(wo_h),
        .wo_b(wo_b), .wo_d(wo_d), .rb_v(rb_v), .rb_d(rb_d), .fault(xff));
    assign r_v = rb_v; assign r = rb_d;
    reg go_c, flt;
    always @(posedge clk) go_c <= go;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt <= 1'b0; else if (go_c) flt <= 1'b0; else if (gf || xff) flt <= 1'b1;
    assign fault = flt;
endmodule
