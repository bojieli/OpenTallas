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
    // SEQUENCED golden-order finish (gate 10-16: the replicated parallel tree was 58.7k flops on one root).  The tree is
    // ot_dsrom_su_norm's vector-level tree exactly (heap over NVP leaves; a node adds its two children when its right
    // subtree holds a real beat, else it passes its left child), evaluated by ONE pipelined adder with dataflow issue
    // (highest-index ready node first).  Same additions, same operands, same order of association -> bit-identical;
    // arrival times are compiler static, so the issue schedule is fixed (no flow control).
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer tz(input integer x);
        integer t;
        begin
            t = 0;
            while (t < 31 && ((x >> t) & 1) == 0) t = t + 1;
            tz = t;
        end
    endfunction
    function automatic integer isadd(input integer n);  // the verbatim g_add condition
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction
    localparam integer DK = tz(D);
    localparam integer DF = D >> DK;
    localparam integer NRS = 8;         // reset relay copies (one per 16-node region; gate 10-16: 766 loads on one flop)
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    (* keep = "true", dont_touch = "true" *) reg [NRS-1:0] rsr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= {NRS{1'b0}}; else rsr <= {NRS{rs[0]}};
    reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    reg [P-1:0] iv; reg [P*8-1:0] ib; reg [P*K*32-1:0] id; reg [31:0] eps_c;
    always @(posedge clk or negedge rstn) if (!rstn) iv <= {P{1'b0}}; else iv <= go_t ? {P{1'b0}} : f_v;
    always @(posedge clk) begin ib <= f_base; id <= f_d; eps_c <= eps; end
    // ---------------------------------------------------------------- node values: leaves (beats) and add nodes
    wire [31:0] V  [1:2*NVP-1];
    wire        VD [1:2*NVP-1];
    wire [NVP-1:0] dup;
    wire        wr_v;                   // adder result write-back
    wire [7:0]  wr_n;
    wire [31:0] wr_d;
    genvar n, p, k;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            if (IX < NV) begin : g_live
                wire [P*K-1:0] m;
                wire [31:0] mv [0:P*K];
                assign mv[0] = 32'd0;
                for (p = 0; p < P; p = p + 1) begin : g_p
                    for (k = 0; k < K; k = k + 1) begin : g_k
`ifdef OT_S81DV_MUT_LEAF
                        // NEGATIVE CONTROL: leaf 1 is fed beat 2's partial (a wrong-operand exchange / tag error).
                        // (A 0/1 swap only commutes one add, and a 1/2 association swap rounded identically on the DS1M
                        // row: order exactness is evidenced by the golden match, operand identity by this control.)
                        localparam integer IXM = (IX == 1) ? 2 : IX;
`else
                        localparam integer IXM = IX;
`endif
                        if (IXM - k >= 0) begin : g_m
                            assign m[p * K + k] = iv[p] && (ib[p * 8 +: 8] == IXM - k);
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (hit) vld <= 1'b1;
                always @(posedge clk) if (hit) val <= mv[P * K];
                assign dup[IX] = hit && (vld || ((m & (m - 1)) != 0));
                assign V[n] = val; assign VD[n] = vld;
            end else begin : g_pad
                assign dup[IX] = 1'b0;
                assign V[n] = 32'd0; assign VD[n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (wr_v && wr_n == n) vld <= 1'b1;
                always @(posedge clk) if (wr_v && wr_n == n) val <= wr_d;
                assign V[n] = val; assign VD[n] = vld;
            end else begin : g_pass
                assign V[n] = V[2 * n]; assign VD[n] = VD[2 * n];
            end
        end
    endgenerate
    // ---------------------------------------------------------------- dataflow issue + the one adder
    // Ready add nodes (both children valid, not issued) are selected lowest heap index first in two registered
    // levels (16 groups of 8: in-group one-hot, then the lowest non-empty group), re-masked by `iss` at the second
    // level so a node never issues twice (a stale pick is a bubble).  Any fixed priority is exact: every node still adds
    // its own two golden children exactly once; arrival times are compiler static, so the issue schedule is static.
    localparam integer NG8 = NVP / 8;
    wire [NVP-1:0] rdy, iss_v;
    wire [NVP-1:0] oh1;                 // stage 1: in-group one-hot (lowest ready node of each group)
    wire [NG8-1:0] ga1;                 // stage 1: group has a ready node
    genvar q;
    generate
        for (n = 0; n < NVP; n = n + 1) begin : g_rdy
            if (n >= 1 && isadd(n)) begin : g_a
                reg iss;
                always @(posedge clk or negedge rsr[(n + 3) % NRS])
                    if (!rsr[(n + 3) % NRS]) iss <= 1'b0; else if (go_t) iss <= 1'b0; else if (win[n]) iss <= 1'b1;
                assign iss_v[n] = iss;
                assign rdy[n] = VD[2 * n] && VD[2 * n + 1] && !iss && !go_t;
            end else begin : g_n
                assign iss_v[n] = 1'b1; assign rdy[n] = 1'b0;
            end
        end
        for (q = 0; q < NG8; q = q + 1) begin : g_grp
            wire [7:0] r8 = rdy[q * 8 +: 8];
            wire [7:0] o8 = r8 & ~(r8 - 8'd1);          // lowest set bit (8-bit)
            reg [7:0] o_r; reg g_r;
            always @(posedge clk or negedge rsr[q % NRS])
                if (!rsr[q % NRS]) begin o_r <= 8'd0; g_r <= 1'b0; end
                else begin o_r <= o8; g_r <= |r8; end
            assign oh1[q * 8 +: 8] = o_r; assign ga1[q] = g_r;
        end
    endgenerate
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});   // lowest non-empty group (16-bit)
    wire [NVP-1:0] win;
    generate
        for (n = 0; n < NVP; n = n + 1) begin : g_win
            assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n] && !go_t;
        end
    endgenerate
    wire fire = |win;
    wire [31:0] oa [0:NVP], ob [0:NVP];
    wire [7:0]  ot [0:NVP];
    assign oa[0] = 32'd0; assign ob[0] = 32'd0; assign ot[0] = 8'd0;
    generate
        for (n = 1; n <= NVP; n = n + 1) begin : g_mux
            if (n < NVP && isadd(n)) begin : g_m
                assign oa[n] = oa[n - 1] | ({32{win[n]}} & V[2 * n]);
                assign ob[n] = ob[n - 1] | ({32{win[n]}} & V[2 * n + 1]);
                assign ot[n] = ot[n - 1] | ({8{win[n]}} & n[7:0]);
            end else begin : g_z
                assign oa[n] = oa[n - 1]; assign ob[n] = ob[n - 1]; assign ot[n] = ot[n - 1];
            end
        end
    endgenerate
    reg  f_q; reg [31:0] a_q, b_q; reg [7:0] t_q;      // operand stage (registered: issue mux -> adder)
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) begin a_q <= oa[NVP]; b_q <= ob[NVP]; t_q <= ot[NVP]; end
    wire [LAV:0] av;
    wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(f_q), .vd(av));
    ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, f_q, a_q, b_q, wr_d, f_add);
    ot_hdc_delay #(.W(8), .D(LAV)) u_t (.clk(clk), .rst_n(rstn), .d(t_q), .q(wr_n));
    assign wr_v = av[LAV];
    // ---------------------------------------------------------------- tail: / D, + eps, rsqrt (ot_dsrom_su_norm)
    reg ssr_v; reg [31:0] ssr;
    always @(posedge clk or negedge rstn) if (!rstn) ssr_v <= 1'b0; else ssr_v <= wr_v && wr_n == 8'd1 && !go_t;
    always @(posedge clk) ssr <= wr_d;
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
            else if (f_add || f_div || f_eps || f_rsq || (|dup)) flt <= 1'b1;
        end
    always @(posedge clk) r_o <= rr;
    assign r_v = r_v_o; assign r = r_o; assign fault = flt;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81dv_eng_finish (RTL-BUILD-S81 10-18): the Engram finish of ONE copy -- T = 3 golden trees (hh, kk, dd) over the
// NV beat partials, evaluated by ONE pipelined adder shared by the 3 trees (interleaved by dataflow issue).  Each tree is
// ot_s81dv_norm_finish's vector-level heap verbatim (same isadd condition, same leaves, same pairs, same order of
// association), so every root equals hdc_golden_v41 csum over D: no / D, eps or rsqrt here (the scalar finish
// ot_s81sl_eg takes the three csum totals).  Leaves are matched by (tree, flit base); a leaf hit twice is a fault.
// MUT (bench negative control, +define+OT_S81DV_MUT_EASSOC): nodes 4 / 5 of every tree add (8 + 10) / (9 + 11)
// instead of (8 + 9) / (10 + 11) -- the same operands, the golden association broken.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81dv_eng_finish #(
    parameter integer NV = 80,
    parameter integer K  = 5,
    parameter integer P  = 3,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [P-1:0]      f_v,
    input  wire [P*2-1:0]    f_t,         // tree (0 hh, 1 kk, 2 dd)
    input  wire [P*8-1:0]    f_base,      // global index of the flit's first partial
    input  wire [P*K*32-1:0] f_d,
    output reg               r_v,         // one pulse when all three roots are final
    output reg  [31:0]       r_hh, r_kk, r_dd,
    output wire              fault
);
    localparam integer T   = 3;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer NC  = T * NVP;   // issue candidates (tree-major)
    localparam integer CW  = $clog2(NC);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer isadd(input integer n);
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction
    function automatic integer ca(input integer n);     // left operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            ca = (n == 4) ? 8 : (n == 5) ? 9 : 2 * n;
`else
            ca = 2 * n;
`endif
        end
    endfunction
    function automatic integer cb(input integer n);     // right operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            cb = (n == 4) ? 10 : (n == 5) ? 11 : 2 * n + 1;
`else
            cb = 2 * n + 1;
`endif
        end
    endfunction
    localparam integer NRS = 8;
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    (* keep = "true", dont_touch = "true" *) reg [NRS-1:0] rsr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= {NRS{1'b0}}; else rsr <= {NRS{rs[0]}};
    reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    reg [P-1:0] iv; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rstn) if (!rstn) iv <= {P{1'b0}}; else iv <= go_t ? {P{1'b0}} : f_v;
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end
    wire        wr_v;
    wire [CW-1:0] wr_n;
    wire [31:0] wr_d;
    wire [NC-1:0] rdy, iss_v, win;
    wire [T*NVP-1:0] dup;
    wire [31:0] V  [0:T-1][1:2*NVP-1];
    wire        VD [0:T-1][1:2*NVP-1];
    genvar t, n, p, k;
    generate for (t = 0; t < T; t = t + 1) begin : g_t
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            if (IX < NV) begin : g_live
                wire [P*K-1:0] m;
                wire [31:0] mv [0:P*K];
                assign mv[0] = 32'd0;
                for (p = 0; p < P; p = p + 1) begin : g_p
                    for (k = 0; k < K; k = k + 1) begin : g_k
                        // ENG flit bases are sid * K by construction (xfin fb), so leaf IX is only ever slot IX % K:
                        // the other slots are not wired (3:1 leaf mux instead of 15:1)
                        if (k == IX % K) begin : g_m
                            assign m[p * K + k] = iv[p] && it[p * 2 +: 2] == t && (ib[p * 8 +: 8] == IX - k);
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (hit) vld <= 1'b1;
                always @(posedge clk) if (hit) val <= mv[P * K];
                assign dup[t * NVP + IX] = hit && (vld || ((m & (m - 1)) != 0));
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pad
                assign dup[t * NVP + IX] = 1'b0;
                assign V[t][n] = 32'd0; assign VD[t][n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0;
                    else if (wr_v && wr_n == t * NVP + n) vld <= 1'b1;
                always @(posedge clk) if (wr_v && wr_n == t * NVP + n) val <= wr_d;
                assign V[t][n] = val; assign VD[t][n] = vld;
            end else begin : g_pass
                assign V[t][n] = V[t][2 * n]; assign VD[t][n] = VD[t][2 * n];
            end
        end
        for (n = 0; n < NVP; n = n + 1) begin : g_rdy
            if (n >= 1 && isadd(n)) begin : g_a
                reg iss;
                always @(posedge clk or negedge rsr[(n + 3) % NRS])
                    if (!rsr[(n + 3) % NRS]) iss <= 1'b0; else if (go_t) iss <= 1'b0; else if (win[t * NVP + n]) iss <= 1'b1;
                assign iss_v[t * NVP + n] = iss;
                assign rdy[t * NVP + n] = VD[t][ca(n)] && VD[t][cb(n)] && !iss && !go_t;
            end else begin : g_n
                assign iss_v[t * NVP + n] = 1'b1; assign rdy[t * NVP + n] = 1'b0;
            end
        end
    end endgenerate
    // two-level registered priority issue (as ot_s81dv_norm_finish): 8-node groups, then the lowest non-empty group
    localparam integer NG8 = NC / 8;
    wire [NC-1:0] oh1; wire [NG8-1:0] ga1;
    genvar q;
    generate for (q = 0; q < NG8; q = q + 1) begin : g_grp
        wire [7:0] r8 = rdy[q * 8 +: 8];
        wire [7:0] o8 = r8 & ~(r8 - 8'd1);
        reg [7:0] o_r; reg g_r;
        always @(posedge clk or negedge rsr[q % NRS])
            if (!rsr[q % NRS]) begin o_r <= 8'd0; g_r <= 1'b0; end
            else begin o_r <= o8; g_r <= |r8; end
        assign oh1[q * 8 +: 8] = o_r; assign ga1[q] = g_r;
    end endgenerate
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});
    generate for (n = 0; n < NC; n = n + 1) begin : g_win
        assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n] && !go_t;
    end endgenerate
    wire fire = |win;
    wire [31:0] oa [0:NC], ob [0:NC];
    wire [CW-1:0] ot [0:NC];
    assign oa[0] = 32'd0; assign ob[0] = 32'd0; assign ot[0] = {CW{1'b0}};
    generate for (t = 0; t < T; t = t + 1) begin : g_mt
        for (n = 0; n < NVP; n = n + 1) begin : g_mux
            localparam integer C = t * NVP + n;
            if (n >= 1 && isadd(n)) begin : g_m
                assign oa[C + 1] = oa[C] | ({32{win[C]}} & V[t][ca(n)]);
                assign ob[C + 1] = ob[C] | ({32{win[C]}} & V[t][cb(n)]);
                assign ot[C + 1] = ot[C] | ({CW{win[C]}} & C[CW-1:0]);
            end else begin : g_z
                assign oa[C + 1] = oa[C]; assign ob[C + 1] = ob[C]; assign ot[C + 1] = ot[C];
            end
        end
    end endgenerate
    reg  f_q; reg [31:0] a_q, b_q; reg [CW-1:0] t_q;
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) begin a_q <= oa[NC]; b_q <= ob[NC]; t_q <= ot[NC]; end
    wire [LAV:0] av; wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(f_q), .vd(av));
    ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, f_q, a_q, b_q, wr_d, f_add);
    ot_hdc_delay #(.W(CW), .D(LAV)) u_t (.clk(clk), .rst_n(rstn), .d(t_q), .q(wr_n));
    assign wr_v = av[LAV];
    // roots: node 1 of each tree
    reg [T-1:0] dn; reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin dn <= {T{1'b0}}; r_v <= 1'b0; flt <= 1'b0; end
        else begin
            r_v <= 1'b0;
            if (go_t) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_n == 1 * 1)           dn[0] <= 1'b1;
                if (wr_v && wr_n == NVP + 1)         dn[1] <= 1'b1;
                if (wr_v && wr_n == 2 * NVP + 1)     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_n == 2 * NVP + 1, wr_v && wr_n == NVP + 1, wr_v && wr_n == 1})
                    == {T{1'b1}}) r_v <= 1'b1;
                if (f_add || (|dup)) flt <= 1'b1;
            end
        end
    always @(posedge clk) begin
        if (wr_v && wr_n == 1)           r_hh <= wr_d;
        if (wr_v && wr_n == NVP + 1)     r_kk <= wr_d;
        if (wr_v && wr_n == 2 * NVP + 1) r_dd <= wr_d;
    end
    assign fault = flt;
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
    parameter integer HW = 7,
    // N32 = 1 (ELEM-XFV/XFIN 10-21, SRAM xfin): KEPT same-edge copies so no net drives > 32 loads -- forward
    // decisions per 32-bit chunk, eng (= md) per mux group, and one dl_v / dl_b copy per finish (NF); 0 edges.
    parameter integer N32 = 0,
    parameter integer NF  = 5,
    parameter integer NENG = 1
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
    // ENG slot-fill inject (RTL-BUILD-S81 10-18): eng = 1 replaces the registered inj_* by a same-cycle inject ej_*
    // that the owner raises only when ej_free (no forward leaves this stop this cycle, either side).  Forwards are
    // never delayed, so per-source order and every path latency stay fixed; the inject slot is a deterministic
    // function of the static arrival times (no ready, no credit).  eng = 0: the stop is unchanged.
    input  wire [NENG-1:0] eng,
    output wire [NF*3-1:0] dlv_f,                 // per-finish copies of dl_v / dl_b (N32; else plain copies)
    output wire [NF*24-1:0] dlb_f,
    input  wire            ej_v,
    input  wire [7:0]      ej_b,
    input  wire [K*32-1:0] ej_d,
    output wire            ej_free,
    output reg             fault
);
    localparam integer NCH = (K * 32 + 31) / 32;
    generate if (N32 == 0) begin : g_orig
    // input flops
    reg iv0, iv1, iv2; reg [3:0] ih1, ih2; reg [7:0] ib0, ib1, ib2; reg [K*32-1:0] id0, id1, id2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv0 <= 1'b0; iv1 <= 1'b0; iv2 <= 1'b0; end
        else begin iv0 <= eng[0] ? ej_v : inj_v; iv1 <= wi_v; iv2 <= ei_v; end
    always @(posedge clk) begin
        ib0 <= eng[0] ? ej_b : inj_base; id0 <= eng[0] ? ej_d : inj_d;
        ih1 <= wi_h; ib1 <= wi_b; id1 <= wi_d; ih2 <= ei_h; ib2 <= ei_b; id2 <= ei_d;
    end
    wire fe = iv1 && ih1 > 4'd1;        // forward east
    wire fw = iv2 && ih2 > 4'd1;        // forward west
    assign ej_free = !(fe || fw);
    wire       jv = eng[0] ? ej_v : iv0;   // the flit injected on the outputs this cycle
    wire [7:0] jb = eng[0] ? ej_b : ib0;
    wire [K*32-1:0] jd = eng[0] ? ej_d : id0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin eo_v <= 1'b0; wo_v <= 1'b0; fault <= 1'b0; end
        else begin
            eo_v <= fe || (jv && HE > 0);
            wo_v <= fw || (jv && HW > 0);
            if (jv && (fe || fw)) fault <= 1'b1;
        end
    always @(posedge clk) begin
        if (fe) begin eo_h <= ih1 - 4'd1; eo_b <= ib1; eo_d <= id1; end
        else begin eo_h <= HE[3:0]; eo_b <= jb; eo_d <= jd; end
        if (fw) begin wo_h <= ih2 - 4'd1; wo_b <= ib2; wo_d <= id2; end
        else begin wo_h <= HW[3:0]; wo_b <= jb; wo_d <= jd; end
    end
    assign dl_v = {iv2, iv1, iv0};
    assign dl_b = {ib2, ib1, ib0};
    assign dl_d = {id2, id1, id0};
        assign dlv_f = {NF{iv2, iv1, iv0}};
        assign dlb_f = {NF{ib2, ib1, ib0}};
    end else begin : g_n32
        // N32: rst_n is RAW here (the xfin top passes the pin reset); local 2-edge leaves = the former rstn edge
        wire [2:0] xr;
        ot_s81dv_finish_reset2 #(.LEAVES(3)) u_xrst (.clk(clk), .rst_n(rst_n), .q(xr));
        // eng copies: [c] jd chunk c, [NCH+c] id0 chunk c, [2NCH] iv0/ib0, [2NCH+1] dl copies 0..1, [2NCH+2] 2..NF-1,
        // [2NCH+3] jv/jb
        reg iv0, iv1, iv2; reg [3:0] ih1, ih2; reg [7:0] ib0, ib1, ib2; reg [K*32-1:0] id0, id1, id2;
        (* keep *) reg [NCH:0] iv1c, iv2c; (* keep *) reg [4*(NCH+1)-1:0] ih1c, ih2c;
        (* keep *) reg [NF*3-1:0] dlv_c; (* keep *) reg [NF*24-1:0] dlb_c;
        always @(posedge clk or negedge xr[0])
            if (!xr[0]) begin iv0 <= 1'b0; iv1 <= 1'b0; iv2 <= 1'b0; iv1c <= {(NCH+1){1'b0}}; iv2c <= {(NCH+1){1'b0}}; end
            else begin
                iv0 <= eng[2*NCH] ? ej_v : inj_v; iv1 <= wi_v; iv2 <= ei_v;
                iv1c <= {(NCH+1){wi_v}}; iv2c <= {(NCH+1){ei_v}};
            end
        integer c;
        always @(posedge clk or negedge xr[1])
            if (!xr[1]) dlv_c <= {(NF*3){1'b0}};
            else for (c = 0; c < NF; c = c + 1)
                dlv_c[c*3 +: 3] <= {ei_v, wi_v, eng[c < 2 ? 2*NCH+1 : 2*NCH+2] ? ej_v : inj_v};
        always @(posedge clk) begin
            ib0 <= eng[2*NCH] ? ej_b : inj_base;
            for (c = 0; c < NCH; c = c + 1) id0[c*32 +: 32] <= eng[NCH+c] ? ej_d[c*32 +: 32] : inj_d[c*32 +: 32];
            ih1 <= wi_h; ib1 <= wi_b; id1 <= wi_d; ih2 <= ei_h; ib2 <= ei_b; id2 <= ei_d;
            ih1c <= {(NCH+1){wi_h}}; ih2c <= {(NCH+1){ei_h}};
            for (c = 0; c < NF; c = c + 1)
                dlb_c[c*24 +: 24] <= {ei_b, wi_b, eng[c < 2 ? 2*NCH+1 : 2*NCH+2] ? ej_b : inj_base};
        end
        wire [NCH:0] fec, fwc;
        genvar g;
        for (g = 0; g <= NCH; g = g + 1) begin : g_f
            assign fec[g] = iv1c[g] && ih1c[g*4 +: 4] > 4'd1;
            assign fwc[g] = iv2c[g] && ih2c[g*4 +: 4] > 4'd1;
        end
        assign ej_free = !(fec[NCH] || fwc[NCH]);
        wire       jv = eng[2*NCH+3] ? ej_v : iv0;
        wire [7:0] jb = eng[2*NCH+3] ? ej_b : ib0;
        wire [K*32-1:0] jd;
        for (g = 0; g < NCH; g = g + 1) begin : g_jd
            assign jd[g*32 +: 32] = eng[g] ? ej_d[g*32 +: 32] : id0[g*32 +: 32];
        end
        always @(posedge clk or negedge xr[2])
            if (!xr[2]) begin eo_v <= 1'b0; wo_v <= 1'b0; fault <= 1'b0; end
            else begin
                eo_v <= fec[NCH] || (jv && HE > 0);
                wo_v <= fwc[NCH] || (jv && HW > 0);
                if (jv && (fec[NCH] || fwc[NCH])) fault <= 1'b1;
            end
        always @(posedge clk) begin
            if (fec[NCH]) begin eo_h <= ih1 - 4'd1; eo_b <= ib1; end else begin eo_h <= HE[3:0]; eo_b <= jb; end
            if (fwc[NCH]) begin wo_h <= ih2 - 4'd1; wo_b <= ib2; end else begin wo_h <= HW[3:0]; wo_b <= jb; end
            for (c = 0; c < NCH; c = c + 1) begin
                eo_d[c*32 +: 32] <= fec[c] ? id1[c*32 +: 32] : jd[c*32 +: 32];
                wo_d[c*32 +: 32] <= fwc[c] ? id2[c*32 +: 32] : jd[c*32 +: 32];
            end
        end
        assign dl_v = {iv2, iv1, iv0};
        assign dl_b = {ib2, ib1, ib0};
        assign dl_d = {id2, id1, id0};
        assign dlv_f = dlv_c;
        assign dlb_f = dlb_c;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81dv_xfin: the slice's NEW norm logic as one leaf tile -- the partial collector (NVL beat partials -> one flit),
// the exchange ring stop and the replicated finish.  Every input pin lands in a flop (robust first cell; no hold
// padding at the pins: hold belongs to the die-level budget at the relay stations).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81dv_xfin #(
    parameter integer NS  = 16,
    parameter integer NVL = 5,
    parameter integer LM  = 5,
    parameter integer LA  = 6
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               go,
    input  wire               mode,         // sampled with go: 0 NORM (rstd on rb), 1 ENG (Engram csum totals on e_*)
    input  wire [3:0]         sid,          // slice id STRAP (captured; one hardened master serves all 16 slices)
    input  wire [31:0]        eps,
    input  wire               s_v,          // group beat partials (NORM: s_i = leaf; ENG: s_i = v * NVL + leaf)
    input  wire [7:0]         s_i,
    input  wire [31:0]        s,
    input  wire               wi_v, input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [NVL*32-1:0] wi_d,
    input  wire               ei_v, input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [NVL*32-1:0] ei_d,
    output wire               eo_v, output wire [3:0] eo_h, output wire [7:0] eo_b, output wire [NVL*32-1:0] eo_d,
    output wire               wo_v, output wire [3:0] wo_h, output wire [7:0] wo_b, output wire [NVL*32-1:0] wo_d,
    output reg                rb_v,         // rstd to the group scale (NORM)
    output reg  [31:0]        rb_d,
    output reg                e_v,          // ENG: one copy's three csum totals (one copy a cycle, lowest copy first)
    output reg  [1:0]         e_c,
    output reg  [31:0]        e_hh, e_kk, e_dd,
    output wire               fault
);
    // ENG mode (RTL-BUILD-S81 10-18, the in-slice Engram mix; S81U-MIX verdict build_plan "xfin ENG mode"):
    //   12 vectors a go, v = kind * 4 + copy (kind 0 hh, 1 kk, 2 dd), each NVL beat partials (s_i = v * NVL + leaf, any
    //   order).  A complete vector is one flit on the SAME exchange ring (format unchanged: {hops 4, b 8, NVL x 32});
    //   in ENG b = {v[3:0], sid[3:0]} (12 x 16 tags fit the 8-bit field), so receivers identify vector and source
    //   explicitly (arrival order free).  Flits fill free ring slots (ot_s81dv_xstop ej_*: forwards first, never
    //   delayed), lowest pending vector first -- a deterministic function of the static partial arrival times.
    //   Finish: 4 x ot_s81dv_eng_finish (one adder per copy, the hh / kk / dd trees interleaved), the golden heap of
    //   ot_s81dv_norm_finish; totals out on e_* (no / D, eps, rsqrt: ot_s81sl_eg).  Faults (sticky until go): a partial
    //   for v >= 12 or a repeated (v, leaf), a flit tag v >= 12, a duplicate leaf, a ring collision.
    //   NORM (mode 0): every NORM path below is the closed x5 RTL; the ENG logic is idle and gated off.
    // MUT (bench negative control): +define+OT_S81DV_MUT_ETAG -- slice 3 swaps the tags of vectors 1 and 5.
    localparam integer HE = NS / 2, HW = NS - 1 - NS / 2;
    localparam integer NE = 12;
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    // N32 (SRAM build): bounded 2-edge reset leaves (prefix + leaf from the pin = the release edge of rs[1]):
    // [0] scalar control, [1] mdc, [2] ew_q, [3..8] collector vectors (2 each), [9] epf, [10..14] finishes,
    // [15] xstop raw handled inside; default build: every leaf = rstn
    wire [23:0] rt;
`ifdef OT_S81DV_XFIN_SRAM
    ot_s81dv_finish_reset2 #(.LEAVES(24)) u_top_reset (.clk(clk), .rst_n(rst_n), .q(rt));
    wire rst_xs = rst_n;                           // xstop N32 builds its own 2-edge leaves
`else
    assign rt = {24{rstn}};
    wire rst_xs = rstn;
`endif
    reg go_c; reg mode_c; reg [31:0] eps_c; reg sv_c; reg [7:0] si_c; reg [31:0] s_c;
    always @(posedge clk) begin go_c <= go; mode_c <= mode; eps_c <= eps; si_c <= s_i; s_c <= s; end
    always @(posedge clk or negedge rt[0]) if (!rt[0]) sv_c <= 1'b0; else sv_c <= s_v;
    // finish go: one KEPT same-edge copy of go_c per finish instance under the SRAM build (NATIVE32, ELEM-XFV/XFIN
    // 10-21: each SRAM finish fans its go into <=32 go_t copies; go_c itself drove 82 loads); default build = go_c
    wire [4:0] go_f;
`ifdef OT_S81DV_XFIN_SRAM
    (* keep *) reg [4:0] go_fr;
    always @(posedge clk) go_fr <= {5{go}};
    assign go_f = go_fr;
`else
    assign go_f = {5{go_c}};
`endif
    reg md;                                        // mode of the current go
    always @(posedge clk or negedge rt[0]) if (!rt[0]) md <= 1'b0; else if (go_c) md <= mode_c;
    // N32 (SRAM build): KEPT same-edge copies of md (xstop eng muxes 14 + finish gating 3) and of go_c (collector
    // clears); NMD/NGC = 1 in the default build (one copy = the original register).
`ifdef OT_S81DV_XFIN_SRAM
    localparam integer N32 = 1, NENG = 14, NMD = NENG + 3, NGC = 10;
`else
    localparam integer N32 = 0, NENG = 1, NMD = NENG + 3, NGC = 10;
`endif
    (* keep *) reg [NMD-1:0] mdc; (* keep *) reg [NGC-1:0] gcc;
    always @(posedge clk) gcc <= {NGC{go}};
    always @(posedge clk or negedge rt[1]) if (!rt[1]) mdc <= {NMD{1'b0}}; else if (gcc[0]) mdc <= {NMD{mode_c}};
    // ---------------------------------------------------------------- NORM collector (closed x5 logic, gated by !md)
    reg [NVL*32-1:0] col; reg inj_v;
    always @(posedge clk or negedge rt[0]) if (!rt[0]) inj_v <= 1'b0; else inj_v <= sv_c && !mdc[NENG+2] && si_c == NVL - 1;
    always @(posedge clk) if (sv_c && !mdc[NENG+2]) col[si_c * 32 +: 32] <= s_c;
    // slice id strap: captured once per cycle like every pin (static value); base = sid * NVL
    reg [3:0] sid_c;
    always @(posedge clk) sid_c <= sid;
`ifdef OT_S81DV_MUT_BASE
    // NEGATIVE CONTROL: slice 3 tags its flit as slice 4's (exchange delivers partials to the wrong tree leaves)
    wire [3:0] sid_e = (sid_c == 4'd3) ? 4'd4 : sid_c;
`else
    wire [3:0] sid_e = sid_c;
`endif
    reg [7:0] sbase;
    always @(posedge clk) sbase <= sid_e * NVL;
    // ---------------------------------------------------------------- ENG collector: 12 vectors x NVL partials
    reg e1_v; reg [3:0] e1_vec; reg [2:0] e1_l; reg [31:0] e1_d; reg e1_bad;
    integer a;
    always @(*) begin : dec5                       // v = si_c / NVL, leaf = si_c % NVL (si_c < 256)
        e1_bad = 1'b1; e1_vec = 4'd0; e1_l = 3'd0;
        for (a = 0; a < NE; a = a + 1)
            if (si_c >= a * NVL && si_c < (a + 1) * NVL) begin e1_bad = 1'b0; e1_vec = a; e1_l = si_c - a * NVL; end
    end
    reg ev_q, ebad_q; reg [3:0] evec_q; reg [2:0] el_q; reg [31:0] ed_q;
    always @(posedge clk or negedge rt[0]) if (!rt[0]) ev_q <= 1'b0; else ev_q <= sv_c && mdc[NENG];
    always @(posedge clk) begin ebad_q <= e1_bad; evec_q <= e1_vec; el_q <= e1_l; ed_q <= s_c; end
    // same-edge one-hot forms of the same decode (N32): ew_q[v] = ev && !bad && vec == v, el_oh = 1 << leaf
    reg [NE-1:0] ew_q; reg [NVL-1:0] el_oh; (* keep *) reg [31:0] ed_q2;
    always @(posedge clk or negedge rt[2]) if (!rt[2]) ew_q <= {NE{1'b0}};
        else ew_q <= (sv_c && mdc[NENG] && !e1_bad) ? ({{(NE-1){1'b0}}, 1'b1} << e1_vec) : {NE{1'b0}};
    always @(posedge clk) begin el_oh <= {{(NVL-1){1'b0}}, 1'b1} << e1_l; ed_q2 <= s_c; end
    reg [NVL*32-1:0] ecol [0:NE-1];
    reg [NVL-1:0] emsk [0:NE-1];
    reg [NE-1:0] pend; reg eflt;
    // pend + one KEPT same-update copy per 32-bit vdat chunk (N32: psel drove 12 x 160 mux loads)
    (* keep *) reg [NVL*NE-1:0] pendc;
    wire [NE-1:0] psel = pend & ~(pend - {{(NE-1){1'b0}}, 1'b1});   // lowest pending vector
    wire ej_free; wire pany = |pend;
    // ej_v and per-chunk copies of it (pendc chunk updates), each <= 12 loads
    wire [NVL:0] ejc;
    genvar ejg;
    for (ejg = 0; ejg <= NVL; ejg = ejg + 1) begin : g_ejc
        // chunk copies read their own kept pend copy (|pendc == |pend), so they are distinct nets
        if (ejg < NVL) begin : g_c
            assign ejc[ejg] = mdc[NENG+1] && (|pendc[ejg*NE +: NE]) && ej_free;
        end else begin : g_p
            assign ejc[ejg] = mdc[NENG+1] && pany && ej_free;
        end
    end
    wire ej_v = ejc[NVL];
    reg [3:0] vsel; reg [NVL*32-1:0] vdat;
    integer b2, b3;
    always @(*) begin
        vsel = 4'd0; vdat = {NVL*32{1'b0}};
        for (b2 = 0; b2 < NE; b2 = b2 + 1) if (psel[b2]) vsel = b2;
        for (b3 = 0; b3 < NVL; b3 = b3 + 1)
            for (b2 = 0; b2 < NE; b2 = b2 + 1)
                if ((pendc[b3*NE +: NE] & ~(pendc[b3*NE +: NE] - {{(NE-1){1'b0}}, 1'b1})) == ({{(NE-1){1'b0}}, 1'b1} << b2))
                    vdat[b3*32 +: 32] = ecol[b2][b3*32 +: 32];
    end
`ifdef OT_S81DV_MUT_ETAG
    wire [3:0] vtag = (sid_c == 4'd3 && vsel == 4'd1) ? 4'd5 : (sid_c == 4'd3 && vsel == 4'd5) ? 4'd1 : vsel;
`else
    wire [3:0] vtag = vsel;
`endif
    // one-hot form of the original update (same edges, same values): vector v completes when ew_q[v] fills the
    // last missing leaf; emsk[v] |= el_oh on ew_q[v]; a fault on a bad tag or a repeated leaf.
    integer c2, c3;
    reg [NE-1:0] pset; reg rep;
    always @(*) begin
        rep = 1'b0;
        for (c2 = 0; c2 < NE; c2 = c2 + 1) begin
            pset[c2] = ew_q[c2] && ((emsk[c2] | el_oh) == {NVL{1'b1}}) && emsk[c2] != {NVL{1'b1}};
            if (ew_q[c2] && (|(emsk[c2] & el_oh))) rep = 1'b1;
        end
    end
    // per vector v: pend[v], its NVL chunk copies and emsk[v] on leaf rt[3 + v/2] and go-clear copy gcc[4 + v/2]
    genvar vv;
    for (vv = 0; vv < NE; vv = vv + 1) begin : g_cv
        integer cc3;
        always @(posedge clk or negedge rt[3 + vv / 2])
            if (!rt[3 + vv / 2]) begin
                pend[vv] <= 1'b0; emsk[vv] <= {NVL{1'b0}};
                for (cc3 = 0; cc3 < NVL; cc3 = cc3 + 1) pendc[cc3*NE + vv] <= 1'b0;
            end else if (gcc[4 + vv / 2]) begin
                pend[vv] <= 1'b0; emsk[vv] <= {NVL{1'b0}};
                for (cc3 = 0; cc3 < NVL; cc3 = cc3 + 1) pendc[cc3*NE + vv] <= 1'b0;
            end else begin
                pend[vv] <= (ejc[NVL] ? (pend[vv] & ~psel[vv]) : pend[vv]) | pset[vv];
                for (cc3 = 0; cc3 < NVL; cc3 = cc3 + 1)
                    pendc[cc3*NE + vv] <= (ejc[cc3] ? (pendc[cc3*NE + vv] & ~psel[vv]) : pendc[cc3*NE + vv]) | pset[vv];
                if (ew_q[vv]) emsk[vv] <= emsk[vv] | el_oh;
            end
    end
    always @(posedge clk or negedge rt[0])
        if (!rt[0]) eflt <= 1'b0; else if (gcc[1]) eflt <= 1'b0; else if ((ev_q && ebad_q) || rep) eflt <= 1'b1;
    integer c4, c5;
    always @(posedge clk)
        for (c4 = 0; c4 < NE; c4 = c4 + 1)
            for (c5 = 0; c5 < NVL; c5 = c5 + 1)
                if (ew_q[c4] && el_oh[c5]) ecol[c4][c5 * 32 +: 32] <= (c4 < NE / 2) ? ed_q : ed_q2;
    // ---------------------------------------------------------------- exchange ring stop
    wire [2:0] dl_v; wire [3*8-1:0] dl_b; wire [3*NVL*32-1:0] dl_d; wire xf, rf;
    wire [5*3-1:0] dlv_f; wire [5*24-1:0] dlb_f;    // per-finish copies (copy 4 = NORM finish)
    ot_s81dv_xstop #(.K(NVL), .HE(HE), .HW(HW), .N32(N32), .NF(5), .NENG(NENG)) u_x (.clk(clk), .rst_n(rst_xs), .inj_v(inj_v), .inj_base(sbase),
        .inj_d(col), .wi_v(wi_v), .wi_h(wi_h), .wi_b(wi_b), .wi_d(wi_d), .ei_v(ei_v), .ei_h(ei_h), .ei_b(ei_b), .ei_d(ei_d),
        .eo_v(eo_v), .eo_h(eo_h), .eo_b(eo_b), .eo_d(eo_d), .wo_v(wo_v), .wo_h(wo_h), .wo_b(wo_b), .wo_d(wo_d),
        .dl_v(dl_v), .dl_b(dl_b), .dl_d(dl_d),
        .eng(mdc[NENG-1:0]), .dlv_f(dlv_f), .dlb_f(dlb_f), .ej_v(ej_v), .ej_b({vtag, sid_c}), .ej_d(vdat), .ej_free(ej_free), .fault(xf));
    // ---------------------------------------------------------------- NORM finish (closed x5; ENG flits gated off)
    wire fr_v; wire [31:0] fr;
`ifdef OT_S81DV_XFIN_SRAM
    ot_s81dv_norm_finish_sram #(.NV(NS * NVL)
`else
    ot_s81dv_norm_finish #(.NV(NS * NVL)
`endif
      , .K(NVL), .P(3), .D(64 * NVL * NS), .LM(LM), .LA(LA)) u_f (.clk(clk),
        .rst_n(rt[14]), .go(go_f[4]), .f_v(dlv_f[4*3 +: 3] & {3{!mdc[NENG+2]}}), .f_base(dlb_f[4*24 +: 24]), .f_d(dl_d), .eps(eps_c), .r_v(fr_v), .r(fr), .fault(rf));
    always @(posedge clk or negedge rt[0]) if (!rt[0]) rb_v <= 1'b0; else rb_v <= fr_v;
    always @(posedge clk) rb_d <= fr;
    // ---------------------------------------------------------------- ENG finish: one per copy
    wire [2:0] tbad; wire [3:0] cr_v, cf; wire [4*10-1:0] crk; wire [31:0] chh [0:3], ckk [0:3], cdd [0:3];
    genvar pp, cc;
    generate
        for (pp = 0; pp < 3; pp = pp + 1) begin : g_dec
            wire [3:0] tv = dlb_f[4 * 24 + pp * 8 + 4 +: 4];
            assign tbad[pp] = mdc[NENG+1] && dlv_f[4 * 3 + pp] && tv >= NE;
        end
        for (cc = 0; cc < 4; cc = cc + 1) begin : g_cp
            wire [2:0] fv; wire [3*2-1:0] ft; wire [3*8-1:0] fb;   // decoded from this finish's own dl copy
            for (pp = 0; pp < 3; pp = pp + 1) begin : g_v
                wire [3:0] tv = dlb_f[cc * 24 + pp * 8 + 4 +: 4], ts = dlb_f[cc * 24 + pp * 8 +: 4];
                assign fv[pp] = mdc[NENG + (cc & 1)] && dlv_f[cc * 3 + pp] && tv[1:0] == cc && tv[3:2] != 2'd3;
                assign ft[pp * 2 +: 2] = tv[3:2];
                assign fb[pp * 8 +: 8] = ts * NVL;
            end
`ifdef OT_S81DV_XFIN_SRAM
            ot_s81dv_eng_finish_sram #(.NV(NS * NVL)
`else
            ot_s81dv_eng_finish #(.NV(NS * NVL)
`endif
      , .K(NVL), .P(3), .LA(LA)) u_e (.clk(clk), .rst_n(rt[10 + cc]), .go(go_f[cc]),
                .f_v(fv), .f_t(ft), .f_base(fb), .f_d(dl_d), .r_v(cr_v[cc]), .r_hh(chh[cc]), .r_kk(ckk[cc]), .r_dd(cdd[cc]),
`ifdef OT_S81DV_XFIN_SRAM
                .r_vk(crk[cc * 10 +: 10]),
`endif
                .fault(cf[cc]));
        end
    endgenerate
    // per-copy results: pending until emitted, lowest copy first, one a cycle
    reg [3:0] epd; reg [31:0] ehh [0:3], ekk [0:3], edd [0:3];
    integer d2;
`ifdef OT_S81DV_XFIN_SRAM
    // N32: the pending set is kept 4x (control + one per result field), each with its own r_v copy, so every
    // select (capture enable, source select, lowest-pending one-hot) drives <= 32 loads; same values as below
    (* keep *) reg [3:0] epf [0:3];
    wire [3:0] eallf [0:3], eohf [0:3];
    genvar ef;
    for (ef = 0; ef < 4; ef = ef + 1) begin : g_ef
        assign eallf[ef] = epf[ef] | {crk[30 + 6 + ef], crk[20 + 6 + ef], crk[10 + 6 + ef], crk[0 + 6 + ef]};
        assign eohf[ef] = eallf[ef] & ~(eallf[ef] - 4'd1);
    end
    wire [3:0] eall = eallf[0], eoh = eohf[0];
    always @(posedge clk or negedge rt[9])
        if (!rt[9]) begin epd <= 4'd0; e_v <= 1'b0; for (d2 = 0; d2 < 4; d2 = d2 + 1) epf[d2] <= 4'd0; end
        else if (gcc[2]) begin epd <= 4'd0; e_v <= 1'b0; for (d2 = 0; d2 < 4; d2 = d2 + 1) epf[d2] <= 4'd0; end
        else begin
            epd <= eall & ~eoh; e_v <= |eall;
            for (d2 = 0; d2 < 4; d2 = d2 + 1) epf[d2] <= eallf[d2] & ~eohf[d2];
        end
    always @(posedge clk) begin
        for (d2 = 0; d2 < 4; d2 = d2 + 1) begin
            if (crk[d2 * 10 + 0]) ehh[d2] <= chh[d2];
            if (crk[d2 * 10 + 1]) ekk[d2] <= ckk[d2];
            if (crk[d2 * 10 + 2]) edd[d2] <= cdd[d2];
        end
        for (d2 = 0; d2 < 4; d2 = d2 + 1) begin
            if (eohf[0][d2]) e_c <= d2;
            if (eohf[1][d2]) e_hh <= crk[d2 * 10 + 3] ? chh[d2] : ehh[d2];
            if (eohf[2][d2]) e_kk <= crk[d2 * 10 + 4] ? ckk[d2] : ekk[d2];
            if (eohf[3][d2]) e_dd <= crk[d2 * 10 + 5] ? cdd[d2] : edd[d2];
        end
    end
`else
    wire [3:0] eall = epd | cr_v;
    wire [3:0] eoh = eall & ~(eall - 4'd1);
    always @(posedge clk or negedge rt[9])
        if (!rt[9]) begin epd <= 4'd0; e_v <= 1'b0; end
        else if (gcc[2]) begin epd <= 4'd0; e_v <= 1'b0; end
        else begin epd <= eall & ~eoh; e_v <= |eall; end
    always @(posedge clk) begin
        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (cr_v[d2]) begin ehh[d2] <= chh[d2]; ekk[d2] <= ckk[d2]; edd[d2] <= cdd[d2]; end
        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (eoh[d2]) begin
            e_c <= d2; e_hh <= cr_v[d2] ? chh[d2] : ehh[d2]; e_kk <= cr_v[d2] ? ckk[d2] : ekk[d2];
            e_dd <= cr_v[d2] ? cdd[d2] : edd[d2];
        end
    end
`endif
    reg flt;
    always @(posedge clk or negedge rt[0])
        if (!rt[0]) flt <= 1'b0; else if (gcc[3]) flt <= 1'b0; else if (xf || rf || eflt || (|tbad) || (|cf)) flt <= 1'b1;
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
    ot_s81dv_xfin #(.NS(NS), .NVL(NVL), .LM(LM), .LA(LA)) u_xf (.clk(clk), .rst_n(rstn), .go(go), .mode(1'b0), .sid(SID[3:0]), .eps(eps),
        .s_v(s_v), .s_i(s_i), .s(s), .wi_v(wi_v), .wi_h(wi_h), .wi_b(wi_b), .wi_d(wi_d), .ei_v(ei_v), .ei_h(ei_h),
        .ei_b(ei_b), .ei_d(ei_d), .eo_v(eo_v), .eo_h(eo_h), .eo_b(eo_b), .eo_d(eo_d), .wo_v(wo_v), .wo_h(wo_h),
        .wo_b(wo_b), .wo_d(wo_d), .rb_v(rb_v), .rb_d(rb_d), .e_v(), .e_c(), .e_hh(), .e_kk(), .e_dd(), .fault(xff));
    assign r_v = rb_v; assign r = rb_d;
    reg go_c, flt;
    always @(posedge clk) go_c <= go;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt <= 1'b0; else if (go_c) flt <= 1'b0; else if (gf || xff) flt <= 1'b1;
    assign fault = flt;
endmodule
