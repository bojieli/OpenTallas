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
    parameter integer NENG = 1,
    // N8 = 1 (STW-S81-COLLA-XFIN 10-21, with N32): forward / eng selects per byte lane instead of per 32-bit chunk
    // (census R33: a chunk select drove 32 mux bits = 62-65 loads); eng then needs 2 * K * 4 + 4 copies
    parameter integer N8 = 0
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
    localparam integer NC8 = N8 ? K * 4 : NCH, SW = (K * 32) / NC8;   // select slices and their width
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
        // N8 (STW-S81-COLLA-XFIN 10-21): every payload select is BYTE-granular (census R33: the per-32-bit-chunk
        // forward decisions fec/fwc and eng selects drove 62-65 loads).  NBY = K*4 byte lanes.
        //   forward copies [y] byte y of eo_d/wo_d, [NBY] eo_v/wo_v/fault/ej_free, [NBY+1] eo_h/eo_b (wo_h/wo_b)
        //   eng copies: [y] jd byte y, [NBY+y] id0 byte y, [2NBY] iv0/ib0, [2NBY+1] dl copies 0..1,
        //   [2NBY+2] dl copies 2..NF-1, [2NBY+3] jv/jb   (NENG = 2*NBY+4)
        // Every copy is a function-identical same-edge register of the original; no edge moves.
        localparam integer NBY = NCH * 4;
`ifdef OT_S81DV_XFIN_N12
        // N12 (STW-S81c-COLLA-SLICE): iv1c / iv2c get their own reset leaves (N11 census: xr[0] leaf 45 loads)
        wire [4:0] xr;
        ot_s81dv_finish_reset2 #(.LEAVES(5)) u_xrst (.clk(clk), .rst_n(rst_n), .q(xr));
`else
        wire [2:0] xr;
        ot_s81dv_finish_reset2 #(.LEAVES(3)) u_xrst (.clk(clk), .rst_n(rst_n), .q(xr));
`endif
        reg iv0, iv1, iv2; reg [3:0] ih1, ih2; reg [7:0] ib0, ib1, ib2; reg [K*32-1:0] id0, id1, id2;
        (* keep *) reg [NBY+1:0] iv1c, iv2c; (* keep *) reg [4*(NBY+2)-1:0] ih1c, ih2c;
        (* keep *) reg [NF*3-1:0] dlv_c; (* keep *) reg [NF*24-1:0] dlb_c;
`ifdef OT_S81DV_XFIN_N12
        always @(posedge clk or negedge xr[3]) if (!xr[3]) iv1c <= {(NBY+2){1'b0}}; else iv1c <= {(NBY+2){wi_v}};
        always @(posedge clk or negedge xr[4]) if (!xr[4]) iv2c <= {(NBY+2){1'b0}}; else iv2c <= {(NBY+2){ei_v}};
        always @(posedge clk or negedge xr[0])
            if (!xr[0]) begin iv0 <= 1'b0; iv1 <= 1'b0; iv2 <= 1'b0; end
            else begin iv0 <= eng[2*NBY] ? ej_v : inj_v; iv1 <= wi_v; iv2 <= ei_v; end
`else
        always @(posedge clk or negedge xr[0])
            if (!xr[0]) begin iv0 <= 1'b0; iv1 <= 1'b0; iv2 <= 1'b0; iv1c <= {(NBY+2){1'b0}}; iv2c <= {(NBY+2){1'b0}}; end
            else begin
                iv0 <= eng[2*NBY] ? ej_v : inj_v; iv1 <= wi_v; iv2 <= ei_v;
                iv1c <= {(NBY+2){wi_v}}; iv2c <= {(NBY+2){ei_v}};
            end
`endif
        integer c;
        always @(posedge clk or negedge xr[1])
            if (!xr[1]) dlv_c <= {(NF*3){1'b0}};
            else for (c = 0; c < NF; c = c + 1)
                dlv_c[c*3 +: 3] <= {ei_v, wi_v, eng[c < 2 ? 2*NBY+1 : 2*NBY+2] ? ej_v : inj_v};
        always @(posedge clk) begin
            ib0 <= eng[2*NBY] ? ej_b : inj_base;
            for (c = 0; c < NBY; c = c + 1) id0[c*8 +: 8] <= eng[NBY+c] ? ej_d[c*8 +: 8] : inj_d[c*8 +: 8];
            ih1 <= wi_h; ib1 <= wi_b; id1 <= wi_d; ih2 <= ei_h; ib2 <= ei_b; id2 <= ei_d;
            ih1c <= {(NBY+2){wi_h}}; ih2c <= {(NBY+2){ei_h}};
            for (c = 0; c < NF; c = c + 1)
                dlb_c[c*24 +: 24] <= {ei_b, wi_b, eng[c < 2 ? 2*NBY+1 : 2*NBY+2] ? ej_b : inj_base};
        end
        wire [NBY+1:0] fec, fwc;
        genvar g;
        for (g = 0; g < NBY + 2; g = g + 1) begin : g_f
            assign fec[g] = iv1c[g] && ih1c[g*4 +: 4] > 4'd1;
            assign fwc[g] = iv2c[g] && ih2c[g*4 +: 4] > 4'd1;
        end
        assign ej_free = !(fec[NBY] || fwc[NBY]);
        wire       jv = eng[2*NBY+3] ? ej_v : iv0;
        wire [7:0] jb = eng[2*NBY+3] ? ej_b : ib0;
        wire [K*32-1:0] jd;
        for (g = 0; g < NBY; g = g + 1) begin : g_jd
            assign jd[g*8 +: 8] = eng[g] ? ej_d[g*8 +: 8] : id0[g*8 +: 8];
        end
        always @(posedge clk or negedge xr[2])
            if (!xr[2]) begin eo_v <= 1'b0; wo_v <= 1'b0; fault <= 1'b0; end
            else begin
                eo_v <= fec[NBY] || (jv && HE > 0);
                wo_v <= fwc[NBY] || (jv && HW > 0);
                if (jv && (fec[NBY] || fwc[NBY])) fault <= 1'b1;
            end
        always @(posedge clk) begin
            if (fec[NBY+1]) begin eo_h <= ih1 - 4'd1; eo_b <= ib1; end else begin eo_h <= HE[3:0]; eo_b <= jb; end
            if (fwc[NBY+1]) begin wo_h <= ih2 - 4'd1; wo_b <= ib2; end else begin wo_h <= HW[3:0]; wo_b <= jb; end
            for (c = 0; c < NBY; c = c + 1) begin
                eo_d[c*8 +: 8] <= fec[c] ? id1[c*8 +: 8] : jd[c*8 +: 8];
                wo_d[c*8 +: 8] <= fwc[c] ? id2[c*8 +: 8] : jd[c*8 +: 8];
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
    wire [31:0] rt;
`ifdef OT_S81DV_XFIN_SRAM
    ot_s81dv_finish_reset2 #(.LEAVES(32)) u_top_reset (.clk(clk), .rst_n(rst_n), .q(rt));
    wire rst_xs = rst_n;                           // xstop N32 builds its own 2-edge leaves
`else
    assign rt = {32{rstn}};
    wire rst_xs = rstn;
`endif
    reg go_c; reg mode_c; reg [31:0] eps_c; reg sv_c; reg [7:0] si_c; reg [31:0] s_c;
    always @(posedge clk) begin go_c <= go; mode_c <= mode; eps_c <= eps; si_c <= s_i; s_c <= s; end
    always @(posedge clk or negedge rt[0]) if (!rt[0]) sv_c <= 1'b0; else sv_c <= s_v;
    // finish go: one KEPT same-edge copy of go_c per finish instance under the SRAM build (NATIVE32, ELEM-XFV/XFIN
    // 10-21: each SRAM finish fans its go into <=32 go_t copies; go_c itself drove 82 loads); default build = go_c
    // N8 (STW-S81-COLLA-XFIN 10-21): [10 + cc] = second go_mem copy of ENG finish cc (its per-tree mem_go owners)
    wire [13:0] go_f;
`ifdef OT_S81DV_XFIN_SRAM
    (* keep *) reg [13:0] go_fr;
    always @(posedge clk) go_fr <= {14{go}};
    assign go_f = go_fr;
`else
    assign go_f = {14{go_c}};
`endif
    reg md;                                        // mode of the current go
    always @(posedge clk or negedge rt[0]) if (!rt[0]) md <= 1'b0; else if (go_c) md <= mode_c;
    // N32 (SRAM build): KEPT same-edge copies of md (xstop eng muxes 14 + finish gating 3) and of go_c (collector
    // clears); NMD/NGC = 1 in the default build (one copy = the original register).
    // N8 (SRAM build, STW-S81-COLLA-XFIN 10-21): every word select / write enable reads a byte-lane copy (<= 8 bits x 2
    // mux loads).  NB8 byte lanes of the flit; xstop eng copies [y] jd byte y, [NB8+y] id0 byte y, [2NB8..2NB8+3] as
    // before; top copies [NENG] ev / ew / fv even, [NENG+1] tbad / fv odd, [NENG+2] inj_v / norm f_v, [NENG+3+y] col
    // byte lane y, [NENG+7] pend-copy inject flags.  mdc halves: enable gcc[0] / gcc[1], mode copy mode_cc[0] / [1],
    // reset leaf rt[1] / rt[15].  gcc (SRAM): [0] mdc half 0 + eflt, [1] mdc half 1 + flt, [2 + v] vector v clears,
    // [14] / [15] ENG result-pending clears (+ epd).  No edge moves: every copy is the original register's twin.
`ifdef OT_S81DV_XFIN_SRAM
    localparam integer N32 = 1, NB8 = NVL * 4, NENG = 2 * NB8 + 4, NMD = NENG + 8, NGC = 16, NMH = NMD / 2;
    localparam integer GEF = 0, GEP = 15, GFL = 1, NPC = NVL * 4, MEJ = NENG + 7;
`else
    localparam integer N32 = 0, NB8 = NVL * 4, NENG = 1, NMD = NENG + 3, NGC = 10, NMH = NMD;
    localparam integer GEF = 1, GEP = 2, GFL = 3, NPC = NVL, MEJ = NENG + 1;
`endif
    (* keep *) reg [NMD-1:0] mdc; (* keep *) reg [NGC-1:0] gcc;
    always @(posedge clk) gcc <= {NGC{go}};
`ifdef OT_S81DV_XFIN_SRAM
    (* keep *) reg [1:0] mode_cc;
    always @(posedge clk) mode_cc <= {2{mode}};
    always @(posedge clk or negedge rt[1]) if (!rt[1]) mdc[NMH-1:0] <= {NMH{1'b0}}; else if (gcc[0]) mdc[NMH-1:0] <= {NMH{mode_cc[0]}};
    always @(posedge clk or negedge rt[15])
        if (!rt[15]) mdc[NMD-1:NMH] <= {(NMD-NMH){1'b0}}; else if (gcc[1]) mdc[NMD-1:NMH] <= {(NMD-NMH){mode_cc[1]}};
`else
    always @(posedge clk or negedge rt[1]) if (!rt[1]) mdc <= {NMD{1'b0}}; else if (gcc[0]) mdc <= {NMD{mode_c}};
`endif
    // ---------------------------------------------------------------- NORM collector (closed x5 logic, gated by !md)
    reg [NVL*32-1:0] col; reg inj_v;
    always @(posedge clk or negedge rt[0]) if (!rt[0]) inj_v <= 1'b0; else inj_v <= sv_c && !mdc[NENG+2] && si_c == NVL - 1;
`ifdef OT_S81DV_XFIN_SRAM
    // N8: byte-lane capture owners (copies of sv_c / si_c, own md copy per lane); the same write, 8 bits per enable
    (* keep *) reg [3:0] sv_cb;
`ifdef OT_S81DV_XFIN_N15
    // N15 (STW-S81c-COLLA 10-22, N14 census si_cb[1/2/4] 36-40 loads): six lane-index copies, one per (byte-lane pair,
    // third of the NVL target lanes), in distinct-ID keep_hierarchy cells (plain kept same-D regs were merged: 33-38
    // loads) and replacing si_cb (s_i itself feeds 24 ecb owners + si_c: 31 loads).  Same D (s_i), same edge.
    wire [47:0] si_cbh;
    for (genvar ch = 0; ch < 6; ch = ch + 1) begin : g_sih
        ot_s81dv_sicp #(.ID(ch)) u_c (.clk(clk), .d(s_i), .q(si_cbh[ch*8 +: 8]));
    end
`else
    (* keep *) reg [31:0] si_cb;
    always @(posedge clk) si_cb <= {4{s_i}};
`endif
    always @(posedge clk or negedge rt[16]) if (!rt[16]) sv_cb <= 4'd0; else sv_cb <= {4{s_v}};
    integer cy, cz;
    always @(posedge clk)
        for (cy = 0; cy < NVL; cy = cy + 1)
            for (cz = 0; cz < 4; cz = cz + 1)
`ifdef OT_S81DV_XFIN_N15
                if (sv_cb[cz] && !mdc[NENG+3+cz] && si_cbh[((cz/2)*3 + (cy*3)/NVL)*8 +: 8] == cy) col[cy*32 + 8*cz +: 8] <= s_c[8*cz +: 8];
`else
                if (sv_cb[cz] && !mdc[NENG+3+cz] && si_cb[cz*8 +: 8] == cy) col[cy*32 + 8*cz +: 8] <= s_c[8*cz +: 8];
`endif
`else
    always @(posedge clk) if (sv_c && !mdc[NENG+2]) col[si_c * 32 +: 32] <= s_c;
`endif
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
`ifdef OT_S81DV_XFIN_N12
    // N12: el_oh is two kept same-edge copies, vectors 0..NE/2-1 read el_oh, NE/2.. read el_oh2 (N11 census 36 loads)
    reg [NE-1:0] ew_q; (* keep *) reg [NVL-1:0] el_oh; (* keep *) reg [NVL-1:0] el_oh2;
    always @(posedge clk) el_oh2 <= {{(NVL-1){1'b0}}, 1'b1} << e1_l;
`define OT_XFIN_ELOH(v) (((v) < NE / 2) ? el_oh : el_oh2)
`else
    reg [NE-1:0] ew_q; reg [NVL-1:0] el_oh;
`define OT_XFIN_ELOH(v) el_oh
`endif
    always @(posedge clk or negedge rt[2]) if (!rt[2]) ew_q <= {NE{1'b0}};
        else ew_q <= (sv_c && mdc[NENG] && !e1_bad) ? ({{(NE-1){1'b0}}, 1'b1} << e1_vec) : {NE{1'b0}};
    always @(posedge clk) el_oh <= {{(NVL-1){1'b0}}, 1'b1} << e1_l;
`ifdef OT_S81DV_XFIN_SRAM
`ifndef OT_S81DV_XFIN_ECOL_BYTEOWN
    // N8: byte-lane copies of the capture decode: ew_qb[h] (bytes 2h, 2h+1), el_ohb[y] (byte y), edq[k] (vectors 2k,
    // 2k+1) -- each ecol byte enable drives 8 bits (census R33: 60 word enables of 65 loads, ed_q2 60, el_oh 38)
    (* keep *) reg [2*NE-1:0] ew_qb; (* keep *) reg [4*NVL-1:0] el_ohb; (* keep *) reg [6*32-1:0] edq;
    always @(posedge clk or negedge rt[16]) if (!rt[16]) ew_qb <= {(2*NE){1'b0}};
        else ew_qb <= {2{(sv_c && mdc[NENG] && !e1_bad) ? ({{(NE-1){1'b0}}, 1'b1} << e1_vec) : {NE{1'b0}}}};
    always @(posedge clk) begin el_ohb <= {4{{{(NVL-1){1'b0}}, 1'b1} << e1_l}}; edq <= {6{s_c}}; end
`endif
`else
    (* keep *) reg [31:0] ed_q2;
    always @(posedge clk) ed_q2 <= s_c;
`endif
    reg [NVL*32-1:0] ecol [0:NE-1];
    reg [NVL-1:0] emsk [0:NE-1];
    reg [NE-1:0] pend; reg eflt;
    // pend + one KEPT same-update copy per vdat slice of PW bits (N32: per 32-bit chunk, psel drove 12 x 160 mux
    // loads; N8 SRAM: per byte, NPC = 4 NVL copies -- a 32-bit chunk copy drove 67 loads)
    localparam integer PW = 32 * NVL / NPC;
    (* keep *) reg [NPC*NE-1:0] pendc;
    wire [NE-1:0] psel = pend & ~(pend - {{(NE-1){1'b0}}, 1'b1});   // lowest pending vector
    wire ej_free; wire pany = |pend;
    // ej_v and per-chunk copies of it (pendc chunk updates), each <= 12 loads
    wire [NPC:0] ejc;
    genvar ejg;
    for (ejg = 0; ejg <= NPC; ejg = ejg + 1) begin : g_ejc
        // chunk copies read their own kept pend copy (|pendc == |pend), so they are distinct nets
        if (ejg < NPC) begin : g_c
            assign ejc[ejg] = mdc[MEJ] && (|pendc[ejg*NE +: NE]) && ej_free;
        end else begin : g_p
            assign ejc[ejg] = mdc[NENG+1] && pany && ej_free;
        end
    end
    wire ej_v = ejc[NPC];
    reg [3:0] vsel; reg [NVL*32-1:0] vdat;
    integer b2, b3;
    always @(*) begin
        vsel = 4'd0; vdat = {NVL*32{1'b0}};
        for (b2 = 0; b2 < NE; b2 = b2 + 1) if (psel[b2]) vsel = b2;
        for (b3 = 0; b3 < NPC; b3 = b3 + 1)
            for (b2 = 0; b2 < NE; b2 = b2 + 1)
                if ((pendc[b3*NE +: NE] & ~(pendc[b3*NE +: NE] - {{(NE-1){1'b0}}, 1'b1})) == ({{(NE-1){1'b0}}, 1'b1} << b2))
                    vdat[b3*PW +: PW] = ecol[b2][b3*PW +: PW];
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
            pset[c2] = ew_q[c2] && ((emsk[c2] | `OT_XFIN_ELOH(c2)) == {NVL{1'b1}}) && emsk[c2] != {NVL{1'b1}};
            if (ew_q[c2] && (|(emsk[c2] & `OT_XFIN_ELOH(c2)))) rep = 1'b1;
        end
    end
    // per vector v: pend[v], its NPC copies and emsk[v] on leaf rt[RV] and go-clear copy gcc[GV] (N8: one leaf and
    // one go copy per vector, 26 flops each; default build: rt[3 + v/2], gcc[4 + v/2])
    genvar vv;
    for (vv = 0; vv < NE; vv = vv + 1) begin : g_cv
        localparam integer RV = N32 ? ((vv < 6) ? 3 + vv : 11 + vv) : 3 + vv / 2;
        localparam integer GV = N32 ? 2 + vv : 4 + vv / 2;
        integer cc3;
        always @(posedge clk or negedge rt[RV])
            if (!rt[RV]) begin
                pend[vv] <= 1'b0; emsk[vv] <= {NVL{1'b0}};
                for (cc3 = 0; cc3 < NPC; cc3 = cc3 + 1) pendc[cc3*NE + vv] <= 1'b0;
            end else if (gcc[GV]) begin
                pend[vv] <= 1'b0; emsk[vv] <= {NVL{1'b0}};
                for (cc3 = 0; cc3 < NPC; cc3 = cc3 + 1) pendc[cc3*NE + vv] <= 1'b0;
            end else begin
                pend[vv] <= (ejc[NPC] ? (pend[vv] & ~psel[vv]) : pend[vv]) | pset[vv];
                for (cc3 = 0; cc3 < NPC; cc3 = cc3 + 1)
                    pendc[cc3*NE + vv] <= (ejc[cc3] ? (pendc[cc3*NE + vv] & ~psel[vv]) : pendc[cc3*NE + vv]) | pset[vv];
                if (ew_q[vv]) emsk[vv] <= emsk[vv] | `OT_XFIN_ELOH(vv);
            end
    end
    always @(posedge clk or negedge rt[0])
        if (!rt[0]) eflt <= 1'b0; else if (gcc[GEF]) eflt <= 1'b0; else if ((ev_q && ebad_q) || rep) eflt <= 1'b1;
    integer c4, c5, c6;
`ifdef OT_S81DV_XFIN_SRAM
`ifdef OT_S81DV_XFIN_ECOL_BYTEOWN
    // Source-bound N9: a group owns two vectors and one byte, giving at most ten
    // byte consumers per data bit. Its first captures are the old s_c/si_c/sv_c
    // edge, and its output captures are the old edq/ew_qb/el_ohb edge.
    localparam integer ECB_GROUPS = ((NE+1)/2)*4;
    wire [ECB_GROUPS-1:0] ecb_reset;
    ot_s81dv_finish_reset2 #(.LEAVES(ECB_GROUPS)) u_ecb_reset (.clk(clk),.rst_n(rst_n),.q(ecb_reset));
    for(genvar eg=0;eg<ECB_GROUPS;eg=eg+1)begin:g_ecb
        localparam integer V0=2*(eg/4), BY=eg%4;
        wire [2*NVL-1:0] we;
        wire [7:0] payload;
        ot_s81dv_ecol_byteowner #(.NVL(NVL),.V0(V0)) u_owner (
            .clk(clk),.rst_n(ecb_reset[eg]),.s_v(s_v),.s_i(s_i),.s_byte(s[8*BY+:8]),
            .mode_owned(mdc[eg]),.we(we),.payload(payload));
        for(genvar vv0=0;vv0<2;vv0=vv0+1)begin:g_v
            for(genvar sl0=0;sl0<NVL;sl0=sl0+1)begin:g_s
                always @(posedge clk) if(we[vv0*NVL+sl0])
                    ecol[V0+vv0][sl0*32+BY*8+:8] <= payload;
            end
        end
    end
`else
    always @(posedge clk)
        for (c4 = 0; c4 < NE; c4 = c4 + 1)
            for (c5 = 0; c5 < NVL; c5 = c5 + 1)
                for (c6 = 0; c6 < 4; c6 = c6 + 1)
                    if (ew_qb[(c6/2)*NE + c4] && el_ohb[c6*NVL + c5]) ecol[c4][c5*32 + 8*c6 +: 8] <= edq[(c4/2)*32 + 8*c6 +: 8];
`endif
`else
    always @(posedge clk)
        for (c4 = 0; c4 < NE; c4 = c4 + 1)
            for (c5 = 0; c5 < NVL; c5 = c5 + 1)
                if (ew_q[c4] && el_oh[c5]) ecol[c4][c5 * 32 +: 32] <= (c4 < NE / 2) ? ed_q : ed_q2;
`endif
    // ---------------------------------------------------------------- exchange ring stop
    wire [2:0] dl_v; wire [3*8-1:0] dl_b; wire [3*NVL*32-1:0] dl_d; wire xf, rf;
    wire [5*3-1:0] dlv_f; wire [5*24-1:0] dlb_f;    // per-finish copies (copy 4 = NORM finish)
    ot_s81dv_xstop #(.K(NVL), .HE(HE), .HW(HW), .N32(N32), .NF(5), .NENG(NENG), .N8(N32)) u_x (.clk(clk), .rst_n(rst_xs), .inj_v(inj_v), .inj_base(sbase),
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
        .rst_n(rt[14]),
`ifdef OT_S81DV_XFIN_SRAM
        .go(go_f[8]), .go_mem(go_f[9]),
`else
        .go(go_f[4]),
`endif
        .f_v(dlv_f[4*3 +: 3] & {3{!mdc[NENG+2]}}), .f_base(dlb_f[4*24 +: 24]), .f_d(dl_d), .eps(eps_c), .r_v(fr_v), .r(fr), .fault(rf));
    always @(posedge clk or negedge rt[0]) if (!rt[0]) rb_v <= 1'b0; else rb_v <= fr_v;
    always @(posedge clk) rb_d <= fr;
    // ---------------------------------------------------------------- ENG finish: one per copy
    wire [2:0] tbad; wire [3:0] cr_v, cf; wire [4*25-1:0] crk; wire [31:0] chh [0:3], ckk [0:3], cdd [0:3];
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
      , .K(NVL), .P(3), .LA(LA)) u_e (.clk(clk), .rst_n(rt[10 + cc]),
`ifdef OT_S81DV_XFIN_SRAM
                .go(go_f[cc*2]), .go_mem(go_f[cc*2+1]), .go_mem2(go_f[10+cc]),
`else
                .go(go_f[cc]),
`endif
                .f_v(fv), .f_t(ft), .f_base(fb), .f_d(dl_d), .r_v(cr_v[cc]), .r_hh(chh[cc]), .r_kk(ckk[cc]), .r_dd(cdd[cc]),
`ifdef OT_S81DV_XFIN_SRAM
                .r_vk(crk[cc * 25 +: 25]),
`endif
                .fault(cf[cc]));
        end
    endgenerate
    // per-copy results: pending until emitted, lowest copy first, one a cycle
    reg [3:0] epd; reg [31:0] ehh [0:3], ekk [0:3], edd [0:3];
    integer d2;
`ifdef OT_S81DV_XFIN_SRAM
    // Byte-owned capture and selection: every finish pulse owns only eight
    // payload bits. Pending copies use the same release and update edges.
    (* keep *) reg [3:0] epf [0:12];   // N8: clears from gcc[14] (ef 0..6) / gcc[15] (ef 7..12, + epd)
    wire [3:0] eallf [0:12], eohf [0:12];
    genvar ef, eb;
    for (ef = 0; ef < 13; ef = ef + 1) begin : g_ef
        assign eallf[ef] = epf[ef] | {crk[75 + 12 + ef], crk[50 + 12 + ef], crk[25 + 12 + ef], crk[12 + ef]};
        assign eohf[ef] = eallf[ef] & ~(eallf[ef] - 4'd1);
        always @(posedge clk or negedge rt[24 + ef/2])
            if (!rt[24 + ef/2]) epf[ef] <= 4'd0;
            else if (gcc[ef < 7 ? 14 : 15]) epf[ef] <= 4'd0;
            else epf[ef] <= eallf[ef] & ~eohf[ef];
    end
    wire [3:0] eall = eallf[0], eoh = eohf[0];
    always @(posedge clk or negedge rt[9])
        if (!rt[9]) begin epd <= 4'd0; e_v <= 1'b0; end
        else if (gcc[GEP]) begin epd <= 4'd0; e_v <= 1'b0; end
        else begin epd <= eall & ~eoh; e_v <= |eall; end
    always @(posedge clk)
        for (d2 = 0; d2 < 4; d2 = d2 + 1)
            if (eohf[0][d2]) e_c <= d2;
    for (eb = 0; eb < 4; eb = eb + 1) begin : g_emit_byte
        integer dc;
        always @(posedge clk) begin
            for (dc = 0; dc < 4; dc = dc + 1) begin
                if (crk[dc*25+eb]) ehh[dc][eb*8+:8] <= chh[dc][eb*8+:8];
                if (crk[dc*25+4+eb]) ekk[dc][eb*8+:8] <= ckk[dc][eb*8+:8];
                if (crk[dc*25+8+eb]) edd[dc][eb*8+:8] <= cdd[dc][eb*8+:8];
                if (eohf[1+eb][dc]) e_hh[eb*8+:8] <= crk[dc*25+eb] ? chh[dc][eb*8+:8] : ehh[dc][eb*8+:8];
                if (eohf[5+eb][dc]) e_kk[eb*8+:8] <= crk[dc*25+4+eb] ? ckk[dc][eb*8+:8] : ekk[dc][eb*8+:8];
                if (eohf[9+eb][dc]) e_dd[eb*8+:8] <= crk[dc*25+8+eb] ? cdd[dc][eb*8+:8] : edd[dc][eb*8+:8];
            end
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
        if (!rt[0]) flt <= 1'b0; else if (gcc[GFL]) flt <= 1'b0; else if (xf || rf || eflt || (|tbad) || (|cf)) flt <= 1'b1;
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

// N9 collector capsule: hierarchy prevents equal-valued owners being merged
// across physical byte groups. All payload edges match the original collector.
(* keep_hierarchy=1 *)
module ot_s81dv_ecol_byteowner #(parameter integer NVL=5,V0=0)(
 input wire clk,rst_n,s_v,input wire[7:0]s_i,input wire[7:0]s_byte,
 input wire mode_owned,output reg[2*NVL-1:0]we,output reg[7:0]payload);
 reg valid_c;reg[7:0]index_c,data_c;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)valid_c<=0;else valid_c<=s_v;
 always @(posedge clk)begin index_c<=s_i;data_c<=s_byte;payload<=data_c;end
 for(genvar v=0;v<2;v=v+1)begin:g_v
  for(genvar l=0;l<NVL;l=l+1)begin:g_l
   always @(posedge clk or negedge rst_n)
    if(!rst_n)we[v*NVL+l]<=0;
    else we[v*NVL+l]<=valid_c && mode_owned && index_c==8'((V0+v)*NVL+l);
  end
 end
endmodule

`ifdef OT_S81DV_XFIN_N15
// distinct-ID same-D strap/index copy behind a module boundary (synthesis may not merge it)
(* keep_hierarchy="yes" *)
module ot_s81dv_sicp #(parameter integer ID=0)(input wire clk, input wire [7:0] d, output wire [7:0] q);
 (* keep *) reg [7:0] r; always @(posedge clk) r<=d; assign q=r;
endmodule
`endif
