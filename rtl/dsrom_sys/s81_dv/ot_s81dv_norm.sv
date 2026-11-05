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
    // FORM-NF 11-04 (DIE-S81-56, OWNER conservative form, as ot_s81dv_eng_finish form 4; xfin dissolved, this block is its own
    // hard core): f_v lands raw in its face flop; go clear after the flop (iv = old go_t ? 0 : f_v register).  One kept select
    // flop per leaf, id one stage later (+1 cycle): a leaf only has its AND-OR.  Flit bases are sid * K by construction (xfin
    // sbase), so leaf IX is only ever slot IX % K (3:1 leaf mux instead of 15:1).
    reg [P-1:0] iv_r; reg go_q; reg [P*8-1:0] ib; reg [P*K*32-1:0] id; reg [31:0] eps_c;
    always @(posedge clk or negedge rstn) if (!rstn) begin iv_r <= {P{1'b0}}; go_q <= 1'b0; end
                                         else begin iv_r <= f_v; go_q <= go_t; end
    wire [P-1:0] iv = iv_r & {P{~go_q}};
    always @(posedge clk) begin ib <= f_base; id <= f_d; eps_c <= eps; end
    wire [P*NV-1:0] sel_q;
    reg  [P*K*32-1:0] id_q;
`ifdef OT_S81DV_MUT_NFQ     // bench mutant: leaf data not delayed with its select
    always @* id_q = id;
`else
    always @(posedge clk) id_q <= id;
`endif
    genvar sp, sb;
    generate for (sp = 0; sp < P; sp = sp + 1) begin : g_sp
        for (sb = 0; sb < NV; sb = sb + 1) begin : g_sb
            (* keep = "true" *) reg q;
            always @(posedge clk or negedge rsr[(sp + sb) % NRS])
                if (!rsr[(sp + sb) % NRS]) q <= 1'b0;
                else q <= iv[sp] && !go_t && ib[sp * 8 +: 8] == (sb / K) * K;
            assign sel_q[sp * NV + sb] = q;
        end
    end endgenerate
    // ---------------------------------------------------------------- node values: leaves (beats) and add nodes
    wire [31:0] V  [1:2*NVP-1];
    wire        VD [1:2*NVP-1];
    wire [NVP-1:0] dup;
    wire        wr_v, wr_v1;            // adder result write-back; _1 = the tag one stage before the result
    wire [7:0]  wr_n, wr_n1;
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
                        if (k == IXM % K) begin : g_m
                            assign m[p * K + k] = sel_q[p * NV + IXM];
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id_q[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (hit) vld <= 1'b1;
                always @(posedge clk) if (hit) val <= mv[P * K];
                assign dup[IX] = hit && (vld || ((m & (m - 1)) != 0));
                // leaf value masked by its reset valid (read only when vld = 1): no free initial value in LEC, as eng_finish
                assign V[n] = val & {32{vld}}; assign VD[n] = vld;
            end else begin : g_pad
                assign dup[IX] = 1'b0;
                assign V[n] = 32'd0; assign VD[n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg [31:0] val; reg vld;
                // FORM-NF: registered one-hot write enable pre-decoded one stage early; we_r == (wr_v && wr_n == n), cycle-exact
                reg we_r;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) we_r <= 1'b0; else we_r <= wr_v1 && wr_n1 == n;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (we_r) vld <= 1'b1;
                always @(posedge clk) if (we_r) val <= wr_d;
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
    // FORM-NF: lowest non-empty group by a log-depth OR prefix, same one-hot, 0 cycles (as eng_finish LEC-EGN-1)
    localparam integer LG8 = (NG8 > 1) ? $clog2(NG8) : 1;
    wire [NG8-1:0] gpo [0:LG8];
    assign gpo[0] = ga1;
    genvar gl, gi;
    generate for (gl = 0; gl < LG8; gl = gl + 1) begin : g_gpo
        for (gi = 0; gi < NG8; gi = gi + 1) begin : g_b
            if (gi >= (1 << gl)) begin : g_o
                assign gpo[gl + 1][gi] = gpo[gl][gi] | gpo[gl][gi - (1 << gl)];
            end else begin : g_p
                assign gpo[gl + 1][gi] = gpo[gl][gi];
            end
        end
    end endgenerate
    wire [NG8-1:0] gs = ga1 & ~{gpo[LG8][NG8-2:0], 1'b0};
    wire [NVP-1:0] win;
    generate
        for (n = 0; n < NVP; n = n + 1) begin : g_win
            assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n] && !go_t;
        end
    endgenerate
    // FORM-NF: the operand mux takes a registered win (+1 cycle) and a stage per 32 candidates (+1 cycle), then a 4:1 OR into
    // a_q / b_q / t_q.  f_q moves with them, so the result tag line stays aligned.  The children V are stable those cycles:
    // written once per go, cleared only on go_t, which already blocks win.  The issue loop keeps the unregistered win.
    reg [NVP-1:0] win_op_q;
    always @(posedge clk or negedge rstn) if (!rstn) win_op_q <= {NVP{1'b0}}; else win_op_q <= win;
    localparam integer OGS = 32;
    localparam integer NOG = NVP / OGS;
    wire [31:0] tma [0:NVP-1], tmb [0:NVP-1];
    wire [7:0]  tmt [0:NVP-1];
    generate for (n = 0; n < NVP; n = n + 1) begin : g_mux
        if (n >= 1 && isadd(n)) begin : g_m
            assign tma[n] = {32{win_op_q[n]}} & V[2 * n];
            assign tmb[n] = {32{win_op_q[n]}} & V[2 * n + 1];
            assign tmt[n] = {8{win_op_q[n]}} & n[7:0];
        end else begin : g_z
            assign tma[n] = 32'd0; assign tmb[n] = 32'd0; assign tmt[n] = 8'd0;
        end
    end endgenerate
    wire [31:0] ga_q [0:NOG], gb_q [0:NOG];
    wire [7:0]  gt_q [0:NOG];
    assign ga_q[0] = 32'd0; assign gb_q[0] = 32'd0; assign gt_q[0] = 8'd0;
    genvar og, oi;
    generate for (og = 0; og < NOG; og = og + 1) begin : g_og
        wire [31:0] ca_ [0:OGS], cb_ [0:OGS];
        wire [7:0]  ct_ [0:OGS];
        assign ca_[0] = 32'd0; assign cb_[0] = 32'd0; assign ct_[0] = 8'd0;
        for (oi = 0; oi < OGS; oi = oi + 1) begin : g_oi
            assign ca_[oi + 1] = ca_[oi] | tma[og * OGS + oi];
            assign cb_[oi + 1] = cb_[oi] | tmb[og * OGS + oi];
            assign ct_[oi + 1] = ct_[oi] | tmt[og * OGS + oi];
        end
        reg [31:0] ra, rb; reg [7:0] rt;
        always @(posedge clk) begin ra <= ca_[OGS]; rb <= cb_[OGS]; rt <= ct_[OGS]; end
        assign ga_q[og + 1] = ga_q[og] | ra;
        assign gb_q[og + 1] = gb_q[og] | rb;
        assign gt_q[og + 1] = gt_q[og] | rt;
    end endgenerate
    reg  fire_g;
    always @(posedge clk or negedge rstn) if (!rstn) fire_g <= 1'b0; else fire_g <= |win_op_q;
    reg  f_q; reg [31:0] a_q, b_q; reg [7:0] t_q;      // operand stage (registered: issue mux -> adder)
`ifdef OT_S81DV_MUT_NFOPG   // bench mutant: valid not moved with the operand stage
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= |win_op_q;
`else
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire_g;
`endif
    always @(posedge clk) begin a_q <= ga_q[NOG]; b_q <= gb_q[NOG]; t_q <= gt_q[NOG]; end
    wire [LAV:0] av;
    wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(f_q), .vd(av));
    ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, f_q, a_q, b_q, wr_d, f_add);
    // tag line split LAV-1 + 1 (same LAV flops)
    ot_hdc_delay #(.W(8), .D(LAV - 1)) u_t (.clk(clk), .rst_n(rstn), .d(t_q), .q(wr_n1));
    ot_hdc_delay #(.W(8), .D(1)) u_t1 (.clk(clk), .rst_n(rstn), .d(wr_n1), .q(wr_n));
    assign wr_v1 = av[LAV - 1];
    assign wr_v = av[LAV];
    // FORM-NF: dup OR gets a stage (fault +1 cycle, sticky until go; cleared by go_t so a dup in the go_t cycle stays ignored)
    reg dup_t;
    always @(posedge clk or negedge rstn) if (!rstn) dup_t <= 1'b0; else dup_t <= !go_t && |dup;
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
    // FORM-NF: uniform out face as eng_finish: face flop -> negative-edge flop -> port (same T/2 hold window, 0 cycles).
    // fault = its own face flop loading the next state of the kept sticky flt (no output pin flop reads itself).
    reg r_v_q; reg [31:0] r_q; (* keep = "true" *) reg flt; reg flt_o;
    wire flt_set = f_add || f_div || f_eps || f_rsq || dup_t;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin r_v_q <= 1'b0; flt <= 1'b0; flt_o <= 1'b0; end
        else begin
            r_v_q <= rr_v;
            flt_o <= go_t ? 1'b0 : (flt | flt_set);
            if (go_t) flt <= 1'b0;
            else if (flt_set) flt <= 1'b1;
        end
    always @(posedge clk) r_q <= rr;
    reg r_v_n, flt_n; reg [31:0] r_n;
    always @(negedge clk) begin r_v_n <= r_v_q; r_n <= r_q; flt_n <= flt_o; end
    assign r_v = r_v_n; assign r = r_n; assign fault = flt_n;
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
    // S81-CORES-KITS-9 10-31 (hard child face rule, raw face_guard): f_v lands RAW in its face flop iv_r; the go clear
    // is applied after the flop with go_t delayed by the same edge (iv = iv_r & ~go_q == old go_t ? 0 : f_v register,
    // cycle-exact, both reset 0 under rstn).
    reg [P-1:0] iv_r; reg go_q; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rstn) if (!rstn) begin iv_r <= {P{1'b0}}; go_q <= 1'b0; end
                                         else begin iv_r <= f_v; go_q <= go_t; end
    wire [P-1:0] iv = iv_r & {P{~go_q}};
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end
    // DIE-S81-52 11-04 (xfin form 3, form 2 routed TT -254 on 2789 g_leaf val/D: ib/it/iv compare in every leaf -> enable +
    // data mux in one cycle): +1 cycle at the input.  One registered one-hot select per port x tree x base group (K
    // leaves each) and id one stage later, so a leaf only has its AND-OR.  iv is blocked by go_t here so a flit that the
    // old form lost to the go_t clear priority is still lost.  OT_S81DV_EF_NOLEAFQ = form 2.
    // DIE-S81-54/ECO 11-04 (form 4, form 3 routed TT -66.73 on 153 ep: one group select drove 5 leaves x 32 enable + AND-OR
    // through 4 fanout buffers).  One kept select flop per leaf, same D as its group, 0 cycles.
    // OT_S81DV_EF_GROUPSEL = form 3.
`ifndef OT_S81DV_EF_NOLEAFQ
`ifdef OT_S81DV_EF_GROUPSEL
    localparam integer NBG = (NV + K - 1) / K;
    localparam integer SGK = K;
    localparam integer SGD = 1;
`else
    localparam integer NBG = NV;
    localparam integer SGK = 1;
    localparam integer SGD = K;
`endif
    wire [P*T*NBG-1:0] sel_q;
    reg  [P*K*32-1:0] id_q;
`ifdef OT_S81DV_MUT_LEAFQ   // bench mutant: leaf data not delayed with its select
    always @* id_q = id;
`else
    always @(posedge clk) id_q <= id;
`endif
    genvar sp, st, sb;
    generate for (sp = 0; sp < P; sp = sp + 1) begin : g_sp
        for (st = 0; st < T; st = st + 1) begin : g_st
            for (sb = 0; sb < NBG; sb = sb + 1) begin : g_sb
                (* keep = "true" *) reg q;
                always @(posedge clk or negedge rsr[(sp + sb) % NRS])
                    if (!rsr[(sp + sb) % NRS]) q <= 1'b0;
                    else q <= iv[sp] && !go_t && it[sp * 2 +: 2] == st && ib[sp * 8 +: 8] == (sb / SGD) * K;
                assign sel_q[(sp * T + st) * NBG + sb] = q;
            end
        end
    end endgenerate
`endif
    wire        wr_v, wr_v1;
    wire [CW-1:0] wr_n, wr_n1;
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
`ifdef OT_S81DV_EF_NOLEAFQ
                            assign m[p * K + k] = iv[p] && it[p * 2 +: 2] == t && (ib[p * 8 +: 8] == IX - k);
`else
                            assign m[p * K + k] = sel_q[(p * T + t) * NBG + IX / SGK];
`endif
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
`ifdef OT_S81DV_EF_NOLEAFQ
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
`else
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id_q[(p * K + k) * 32 +: 32]);
`endif
                    end
                end
                wire hit = |m;
                reg [31:0] val; reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0; else if (hit) vld <= 1'b1;
                always @(posedge clk) if (hit) val <= mv[P * K];
                assign dup[t * NVP + IX] = hit && (vld || ((m & (m - 1)) != 0));
                // LEC-EGN-1 11-03: the leaf value is masked by its (reset) valid bit.  val has no reset and is read only
                // when vld = 1 (rdy needs both children valid), so V is unchanged wherever it is observed; the mask makes
                // V a defined 0 before the first load, so the LEC need not pair free initial values of val (kit
                // ot_s81dv_eng_finish_rf1_r64 was UNPROVEN on a_q / b_q through V[137..] vs g_leaf[138].g_live.val).
                assign V[t][n] = val & {32{vld}}; assign VD[t][n] = vld;
            end else begin : g_pad
                assign dup[t * NVP + IX] = 1'b0;
                assign V[t][n] = 32'd0; assign VD[t][n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg [31:0] val; reg vld;
                // RF-B 11-03 (S81-RF1 RE-FORM, xfin): the node write enable is a registered one-hot bit pre-decoded one
                // stage early from the tag line (was: the 9-bit wr_n compare fanned out to all 237 nodes x 32 enables in
                // one cycle, routed -105 ps).  we_r == (wr_v && wr_n == C) every cycle: cycle-exact, no port change.
`ifdef OT_S81DV_EF_NOPREDEC
                wire we_n = wr_v && wr_n == t * NVP + n;
`else
                reg we_r;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) we_r <= 1'b0; else we_r <= wr_v1 && wr_n1 == t * NVP + n;
                wire we_n = we_r;
`endif
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t) vld <= 1'b0;
                    else if (we_n) vld <= 1'b1;
                always @(posedge clk) if (we_n) val <= wr_d;
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
    // LEC-EGN-1 11-03 (OWNER conservative form, xfin S81-046): lowest non-empty group by a log-depth OR prefix
    // (Kogge-Stone, $clog2(NG8) levels) instead of the ga1 - 1 borrow chain (96-bit, ~545 ps of the placed -165 ps
    // g_r -> a_q path).  gs = ga1 & ~(OR of all lower groups): the same one-hot lowest set bit, 0 cycles.
    localparam integer LG8 = (NG8 > 1) ? $clog2(NG8) : 1;
    wire [NG8-1:0] gpo [0:LG8];
    assign gpo[0] = ga1;
    genvar gl, gi;
    generate for (gl = 0; gl < LG8; gl = gl + 1) begin : g_gpo
        for (gi = 0; gi < NG8; gi = gi + 1) begin : g_b
            if (gi >= (1 << gl)) begin : g_o
                assign gpo[gl + 1][gi] = gpo[gl][gi] | gpo[gl][gi - (1 << gl)];
            end else begin : g_p
                assign gpo[gl + 1][gi] = gpo[gl][gi];
            end
        end
    end endgenerate
`ifdef OT_S81DV_EF_GSCHAIN
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});
`else
    wire [NG8-1:0] gs = ga1 & ~{gpo[LG8][NG8-2:0], 1'b0};
`endif
    generate for (n = 0; n < NC; n = n + 1) begin : g_win
        assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n] && !go_t;
    end endgenerate
    // LEC-EGN-1 11-03 (OWNER conservative form): the operand mux takes a REGISTERED copy of win (win_op_q), so the
    // feed-forward select -> 768:1 AND-OR -> a_q / b_q / t_q branch gets its own stage.  The issue loop (win -> iss ->
    // rdy) keeps the unregistered win (its 2-cycle timing is unchanged).  Cost: +1 cycle from issue to the adder
    // operands (f_q / a_q / b_q / t_q move together, so the result tag line stays aligned).  The children V of a
    // winner are stable that extra cycle: each node / leaf value is written once per tile and cleared only on go_t,
    // which already blocks win.
`ifdef OT_S81DV_EF_NOWINQ
    wire [NC-1:0] win_op_q = win;
`else
    reg  [NC-1:0] win_op_q;
    always @(posedge clk or negedge rstn) if (!rstn) win_op_q <= {NC{1'b0}}; else win_op_q <= win;
`endif
`ifdef OT_S81DV_EF_NOOPG
    wire fire = |win_op_q;
    wire [31:0] oa [0:NC], ob [0:NC];
    wire [CW-1:0] ot [0:NC];
    assign oa[0] = 32'd0; assign ob[0] = 32'd0; assign ot[0] = {CW{1'b0}};
    generate for (t = 0; t < T; t = t + 1) begin : g_mt
        for (n = 0; n < NVP; n = n + 1) begin : g_mux
            localparam integer C = t * NVP + n;
            if (n >= 1 && isadd(n)) begin : g_m
                assign oa[C + 1] = oa[C] | ({32{win_op_q[C]}} & V[t][ca(n)]);
                assign ob[C + 1] = ob[C] | ({32{win_op_q[C]}} & V[t][cb(n)]);
                assign ot[C + 1] = ot[C] | ({CW{win_op_q[C]}} & C[CW-1:0]);
            end else begin : g_z
                assign oa[C + 1] = oa[C]; assign ob[C + 1] = ob[C]; assign ot[C + 1] = ot[C];
            end
        end
    end endgenerate
    reg  f_q; reg [31:0] a_q, b_q; reg [CW-1:0] t_q;
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) begin a_q <= oa[NC]; b_q <= ob[NC]; t_q <= ot[NC]; end
`else
    // DIE-S81-52 11-04 (xfin form 3, form 2 routed TT -257 win_op_q -> OR tree -> a_q): the operand AND-OR gets a stage
    // per 32 candidates, then a 12:1 OR into a_q / b_q / t_q.  +1 cycle per issue on top of win_op_q; f_q moves with them,
    // so the result tag line stays aligned.  Children V stay stable the extra cycle, as for win_op_q.
    localparam integer OGS = 32;
    localparam integer NOG = NC / OGS;
    wire [31:0] tma [0:NC-1], tmb [0:NC-1];
    wire [CW-1:0] tmt [0:NC-1];
    generate for (t = 0; t < T; t = t + 1) begin : g_mt
        for (n = 0; n < NVP; n = n + 1) begin : g_mux
            localparam integer C = t * NVP + n;
            if (n >= 1 && isadd(n)) begin : g_m
                assign tma[C] = {32{win_op_q[C]}} & V[t][ca(n)];
                assign tmb[C] = {32{win_op_q[C]}} & V[t][cb(n)];
                assign tmt[C] = {CW{win_op_q[C]}} & C[CW-1:0];
            end else begin : g_z
                assign tma[C] = 32'd0; assign tmb[C] = 32'd0; assign tmt[C] = {CW{1'b0}};
            end
        end
    end endgenerate
    wire [31:0] ga_q [0:NOG], gb_q [0:NOG];
    wire [CW-1:0] gt_q [0:NOG];
    assign ga_q[0] = 32'd0; assign gb_q[0] = 32'd0; assign gt_q[0] = {CW{1'b0}};
    genvar og, oi;
    generate for (og = 0; og < NOG; og = og + 1) begin : g_og
        wire [31:0] ca_ [0:OGS], cb_ [0:OGS];
        wire [CW-1:0] ct_ [0:OGS];
        assign ca_[0] = 32'd0; assign cb_[0] = 32'd0; assign ct_[0] = {CW{1'b0}};
        for (oi = 0; oi < OGS; oi = oi + 1) begin : g_oi
            assign ca_[oi + 1] = ca_[oi] | tma[og * OGS + oi];
            assign cb_[oi + 1] = cb_[oi] | tmb[og * OGS + oi];
            assign ct_[oi + 1] = ct_[oi] | tmt[og * OGS + oi];
        end
        reg [31:0] ra, rb; reg [CW-1:0] rt;
        always @(posedge clk) begin ra <= ca_[OGS]; rb <= cb_[OGS]; rt <= ct_[OGS]; end
        assign ga_q[og + 1] = ga_q[og] | ra;
        assign gb_q[og + 1] = gb_q[og] | rb;
        assign gt_q[og + 1] = gt_q[og] | rt;
    end endgenerate
    reg  fire_g;
    always @(posedge clk or negedge rstn) if (!rstn) fire_g <= 1'b0; else fire_g <= |win_op_q;
    reg  f_q; reg [31:0] a_q, b_q; reg [CW-1:0] t_q;
`ifdef OT_S81DV_MUT_OPG     // bench mutant: valid not moved with the operand stage
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= |win_op_q;
`else
    always @(posedge clk or negedge rstn) if (!rstn) f_q <= 1'b0; else f_q <= fire_g;
`endif
    always @(posedge clk) begin a_q <= ga_q[NOG]; b_q <= gb_q[NOG]; t_q <= gt_q[NOG]; end
`endif
    wire [LAV:0] av; wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rstn), .v(f_q), .vd(av));
    ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rstn, f_q, a_q, b_q, wr_d, f_add);
    // tag line split LAV-1 + 1 (same LAV flops): wr_n1 / wr_v1 = the tag one stage before the adder result
    ot_hdc_delay #(.W(CW), .D(LAV - 1)) u_t (.clk(clk), .rst_n(rstn), .d(t_q), .q(wr_n1));
    ot_hdc_delay #(.W(CW), .D(1)) u_t1 (.clk(clk), .rst_n(rstn), .d(wr_n1), .q(wr_n));
    assign wr_v1 = av[LAV - 1];
    assign wr_v = av[LAV];
    // DIE-S81-52 11-04 (xfin form 3, flt -90 through the 240-bit dup OR): one stage per tree; fault +1 cycle, sticky until
    // go, cleared by go_t as flt so a dup in the go_t cycle stays ignored.  OT_S81DV_EF_NOLEAFQ = form 2.
`ifdef OT_S81DV_EF_NOLEAFQ
    wire dup_any = |dup;
`else
    reg [T-1:0] dup_t;
    integer dti;
    always @(posedge clk or negedge rstn)
        if (!rstn) dup_t <= {T{1'b0}};
        else for (dti = 0; dti < T; dti = dti + 1) dup_t[dti] <= !go_t && |dup[dti * NVP +: NVP];
    wire dup_any = |dup_t;
`endif
    // roots: node 1 of each tree
    reg [T-1:0] dn; (* keep = "true" *) reg flt;
    reg r_v_q; reg [31:0] r_hh_q, r_kk_q, r_dd_q;   // RF-B: the face flops (ports = their lockup latches)
    always @(posedge clk or negedge rstn)
        if (!rstn) begin dn <= {T{1'b0}}; r_v_q <= 1'b0; flt <= 1'b0; end
        else begin
            r_v_q <= 1'b0;
            if (go_t) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_n == 1 * 1)           dn[0] <= 1'b1;
                if (wr_v && wr_n == NVP + 1)         dn[1] <= 1'b1;
                if (wr_v && wr_n == 2 * NVP + 1)     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_n == 2 * NVP + 1, wr_v && wr_n == NVP + 1, wr_v && wr_n == 1})
                    == {T{1'b1}}) r_v_q <= 1'b1;
                if (f_add || dup_any) flt <= 1'b1;
            end
        end
    // S81-CORES-KITS-9 10-31 (hard child face rule: no output pin flop reads itself): the root values are held in
    // internal registers *_s; the r_* pin flops load the root value on the r_v edge and ZERO otherwise, so r_* equal
    // the old held r_* whenever r_v = 1 (the only cycle ot_s81dv_xfin reads them: ehh/ekk/edd and e_* load under cr_v).
    // fault = its own pin flop loading the next state of the kept sticky flt (same value every cycle, as xfin's fault).
    wire w_hh = wr_v && wr_n == 1, w_kk = wr_v && wr_n == NVP + 1, w_dd = wr_v && wr_n == 2 * NVP + 1;
    wire fin = !go_t && dn != {T{1'b1}} && (dn | {w_dd, w_kk, w_hh}) == {T{1'b1}};   // = the r_v set condition
    reg [31:0] hh_s, kk_s, dd_s;
    always @(posedge clk) begin
        if (w_hh) hh_s <= wr_d;
        if (w_kk) kk_s <= wr_d;
        if (w_dd) dd_s <= wr_d;
        r_hh_q <= fin ? (w_hh ? wr_d : hh_s) : 32'd0;
        r_kk_q <= fin ? (w_kk ? wr_d : kk_s) : 32'd0;
        r_dd_q <= fin ? (w_dd ? wr_d : dd_s) : 32'd0;
    end
    reg flt_o;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt_o <= 1'b0; else flt_o <= go_t ? 1'b0 : (flt | f_add | dup_any);
    // RF-B 11-03 (S81-RF1 RE-FORM, DIE-S81-51/CLK crossing table row 1): every output face = face flop -> negative-level
    // lockup latch -> port, no logic between (core-owned hold-safe face: the port moves at the falling edge, half a
    // period after the flop; a transparent-low latch between rising-edge flops is a wire in the cycle model).
    // DIE-S81-51/NFF 11-03 (uniform out-face form ruling): default = negative-EDGE flop (DFFLQN) per output bit, same
    // T/2 hold window as the latch, 0 cycles; +define+OT_S81DV_EF_OLATCH keeps the transparent-low latch form.
`ifdef OT_S81DV_EF_NOLATCH
    always @* begin r_v = r_v_q; r_hh = r_hh_q; r_kk = r_kk_q; r_dd = r_dd_q; end
    assign fault = flt_o;
`elsif OT_S81DV_EF_OLATCH
    reg flt_l;
    always @* if (!clk) begin r_v = r_v_q; r_hh = r_hh_q; r_kk = r_kk_q; r_dd = r_dd_q; flt_l = flt_o; end
    assign fault = flt_l;
`else
    reg flt_l;
    always @(negedge clk) begin r_v <= r_v_q; r_hh <= r_hh_q; r_kk <= r_kk_q; r_dd <= r_dd_q; flt_l <= flt_o; end
    assign fault = flt_l;
`endif
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
    // ENG slot-fill inject (RTL-BUILD-S81 10-18): eng = 1 replaces the registered inj_* by a same-cycle inject ej_*
    // that the owner raises only when ej_free (no forward leaves this stop this cycle, either side).  Forwards are
    // never delayed, so per-source order and every path latency stay fixed; the inject slot is a deterministic
    // function of the static arrival times (no ready, no credit).  eng = 0: the stop is unchanged.
    input  wire            eng,
    input  wire            ej_v,
    input  wire [7:0]      ej_b,
    input  wire [K*32-1:0] ej_d,
    output wire            ej_free,
    output reg             fault
);
    // input flops
    reg iv0, iv1, iv2; reg [3:0] ih1, ih2; reg [7:0] ib0, ib1, ib2; reg [K*32-1:0] id0, id1, id2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv0 <= 1'b0; iv1 <= 1'b0; iv2 <= 1'b0; end
        else begin iv0 <= eng ? ej_v : inj_v; iv1 <= wi_v; iv2 <= ei_v; end
    always @(posedge clk) begin
        ib0 <= eng ? ej_b : inj_base; id0 <= eng ? ej_d : inj_d;
        ih1 <= wi_h; ib1 <= wi_b; id1 <= wi_d; ih2 <= ei_h; ib2 <= ei_b; id2 <= ei_d;
    end
    wire fe = iv1 && ih1 > 4'd1;        // forward east
    wire fw = iv2 && ih2 > 4'd1;        // forward west
    assign ej_free = !(fe || fw);
    wire       jv = eng ? ej_v : iv0;   // the flit injected on the outputs this cycle
    wire [7:0] jb = eng ? ej_b : ib0;
    wire [K*32-1:0] jd = eng ? ej_d : id0;
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
    parameter integer LA  = 6,
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant pins): the S81 hardened master (defaults) takes s_i[6:0] -- its
    // producer xrt's x_si[7] is constant 0 (max index 59) and was dropped; s_i[7] is 0 inside.  ot_s81dv_norm (and DV
    // benches whose s_i may carry 8 bits) pass SIW = 8.
    parameter integer SIW = 7
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               go,
    input  wire               mode,         // sampled with go: 0 NORM (rstd on rb), 1 ENG (Engram csum totals on e_*)
    input  wire [3:0]         sid,          // slice id STRAP (captured; one hardened master serves all 16 slices)
    input  wire [31:0]        eps,
    input  wire               s_v,          // group beat partials (NORM: s_i = leaf; ENG: s_i = v * NVL + leaf)
    input  wire [SIW-1:0]     s_i,
    input  wire [31:0]        s,
    input  wire               wi_v, input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [NVL*32-1:0] wi_d,
    input  wire               ei_v, input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [NVL*32-1:0] ei_d,
    output reg                eo_v, output reg  [3:0] eo_h, output reg  [7:0] eo_b, output reg  [NVL*32-1:0] eo_d,
    output reg                wo_v, output reg  [3:0] wo_h, output reg  [7:0] wo_b, output reg  [NVL*32-1:0] wo_d,
    output reg                rb_v,         // rstd to the group scale (NORM)
    output reg  [31:0]        rb_d,
    output reg                e_v,          // ENG: one copy's three csum totals (one copy a cycle, lowest copy first)
    output reg  [1:0]         e_c,
    output reg  [31:0]        e_hh, e_kk, e_dd,
    output reg                fault         // RTLC 10-24: pin flop = the kept sticky flt next state (0 edges)
);
    // RF-B 11-03 (S81-RF1 RE-FORM, DIE-S81-51/CLK crossing table row 1): the face flops of every output; each port =
    // face flop -> negative-level lockup latch -> port, no logic between (core-owned hold-safe face).
    wire eo_v_q, wo_v_q; wire [3:0] eo_h_q, wo_h_q; wire [7:0] eo_b_q, wo_b_q; wire [NVL*32-1:0] eo_d_q, wo_d_q;
    reg rb_v_q, e_v_q, fault_q; reg [31:0] rb_d_q, e_hh_q, e_kk_q, e_dd_q; reg [1:0] e_c_q;
    // DIE-S81-51/NFF 11-03: default = negative-EDGE flop per output bit (same T/2 window, 0 cycles);
    // +define+OT_S81DV_XF_OLATCH keeps the transparent-low latch form.
`ifdef OT_S81DV_XF_NOLATCH
    always @* begin
        eo_v = eo_v_q; eo_h = eo_h_q; eo_b = eo_b_q; eo_d = eo_d_q; wo_v = wo_v_q; wo_h = wo_h_q; wo_b = wo_b_q; wo_d = wo_d_q;
        rb_v = rb_v_q; rb_d = rb_d_q; e_v = e_v_q; e_c = e_c_q; e_hh = e_hh_q; e_kk = e_kk_q; e_dd = e_dd_q; fault = fault_q;
    end
`elsif OT_S81DV_XF_OLATCH
    always @* if (!clk) begin
        eo_v = eo_v_q; eo_h = eo_h_q; eo_b = eo_b_q; eo_d = eo_d_q; wo_v = wo_v_q; wo_h = wo_h_q; wo_b = wo_b_q; wo_d = wo_d_q;
        rb_v = rb_v_q; rb_d = rb_d_q; e_v = e_v_q; e_c = e_c_q; e_hh = e_hh_q; e_kk = e_kk_q; e_dd = e_dd_q; fault = fault_q;
    end
`else
    always @(negedge clk) begin
        eo_v <= eo_v_q; eo_h <= eo_h_q; eo_b <= eo_b_q; eo_d <= eo_d_q; wo_v <= wo_v_q; wo_h <= wo_h_q; wo_b <= wo_b_q; wo_d <= wo_d_q;
        rb_v <= rb_v_q; rb_d <= rb_d_q; e_v <= e_v_q; e_c <= e_c_q; e_hh <= e_hh_q; e_kk <= e_kk_q; e_dd <= e_dd_q; fault <= fault_q;
    end
`endif
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
    reg go_c; reg mode_c; reg [31:0] eps_c; reg sv_c; reg [7:0] si_c; reg [31:0] s_c;
    wire [7:0] s_i8 = s_i;                         // zero-extended (SIW = 7: s_i[7] = 0)
    always @(posedge clk) begin go_c <= go; mode_c <= mode; eps_c <= eps; si_c <= s_i8; s_c <= s; end
    always @(posedge clk or negedge rstn) if (!rstn) sv_c <= 1'b0; else sv_c <= s_v;
    reg md;                                        // mode of the current go
    always @(posedge clk or negedge rstn) if (!rstn) md <= 1'b0; else if (go_c) md <= mode_c;
    // ---------------------------------------------------------------- NORM collector (closed x5 logic, gated by !md)
    reg [NVL*32-1:0] col; reg inj_v;
    always @(posedge clk or negedge rstn) if (!rstn) inj_v <= 1'b0; else inj_v <= sv_c && !md && si_c == NVL - 1;
    always @(posedge clk) if (sv_c && !md) col[si_c * 32 +: 32] <= s_c;
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
    always @(posedge clk or negedge rstn) if (!rstn) ev_q <= 1'b0; else ev_q <= sv_c && md;
    always @(posedge clk) begin ebad_q <= e1_bad; evec_q <= e1_vec; el_q <= e1_l; ed_q <= s_c; end
    reg [NVL*32-1:0] ecol [0:NE-1];
    reg [NVL-1:0] emsk [0:NE-1];
    reg [NE-1:0] pend; reg eflt;
    wire [NE-1:0] psel = pend & ~(pend - {{(NE-1){1'b0}}, 1'b1});   // lowest pending vector
    wire ej_free; wire ej_v = md && (|pend) && ej_free;
    reg [3:0] vsel; reg [NVL*32-1:0] vdat;
    integer b2;
    always @(*) begin
        vsel = 4'd0; vdat = {NVL*32{1'b0}};
        for (b2 = 0; b2 < NE; b2 = b2 + 1) if (psel[b2]) begin vsel = b2; vdat = ecol[b2]; end
    end
`ifdef OT_S81DV_MUT_ETAG
    wire [3:0] vtag = (sid_c == 4'd3 && vsel == 4'd1) ? 4'd5 : (sid_c == 4'd3 && vsel == 4'd5) ? 4'd1 : vsel;
`else
    wire [3:0] vtag = vsel;
`endif
    integer c2;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin pend <= {NE{1'b0}}; eflt <= 1'b0; for (c2 = 0; c2 < NE; c2 = c2 + 1) emsk[c2] <= {NVL{1'b0}}; end
        else if (go_c) begin pend <= {NE{1'b0}}; eflt <= 1'b0; for (c2 = 0; c2 < NE; c2 = c2 + 1) emsk[c2] <= {NVL{1'b0}}; end
        else begin
            if (ej_v) pend <= (pend & ~psel) | ((ev_q && !ebad_q && (emsk[evec_q] | (1 << el_q)) == {NVL{1'b1}}
                                                && emsk[evec_q] != {NVL{1'b1}}) ? (1 << evec_q) : {NE{1'b0}});
            else if (ev_q && !ebad_q && (emsk[evec_q] | (1 << el_q)) == {NVL{1'b1}} && emsk[evec_q] != {NVL{1'b1}})
                pend <= pend | (1 << evec_q);
            if (ev_q && !ebad_q) emsk[evec_q] <= emsk[evec_q] | (1 << el_q);
            if (ev_q && (ebad_q || emsk[evec_q][el_q])) eflt <= 1'b1;
        end
    always @(posedge clk) if (ev_q && !ebad_q) ecol[evec_q][el_q * 32 +: 32] <= ed_q;
    // ---------------------------------------------------------------- exchange ring stop
    wire [2:0] dl_v; wire [3*8-1:0] dl_b; wire [3*NVL*32-1:0] dl_d; wire xf, rf;
    ot_s81dv_xstop #(.K(NVL), .HE(HE), .HW(HW)) u_x (.clk(clk), .rst_n(rstn), .inj_v(inj_v), .inj_base(sbase),
        .inj_d(col), .wi_v(wi_v), .wi_h(wi_h), .wi_b(wi_b), .wi_d(wi_d), .ei_v(ei_v), .ei_h(ei_h), .ei_b(ei_b), .ei_d(ei_d),
        .eo_v(eo_v_q), .eo_h(eo_h_q), .eo_b(eo_b_q), .eo_d(eo_d_q), .wo_v(wo_v_q), .wo_h(wo_h_q), .wo_b(wo_b_q), .wo_d(wo_d_q),
        .dl_v(dl_v), .dl_b(dl_b), .dl_d(dl_d),
        .eng(md), .ej_v(ej_v), .ej_b({vtag, sid_c}), .ej_d(vdat), .ej_free(ej_free), .fault(xf));
    // ---------------------------------------------------------------- NORM finish (closed x5; ENG flits gated off)
    wire fr_v; wire [31:0] fr;
    ot_s81dv_norm_finish #(.NV(NS * NVL), .K(NVL), .P(3), .D(64 * NVL * NS), .LM(LM), .LA(LA)) u_f (.clk(clk),
        .rst_n(rstn), .go(go_c), .f_v(dl_v & {3{!md}}), .f_base(dl_b), .f_d(dl_d), .eps(eps_c), .r_v(fr_v), .r(fr), .fault(rf));
    always @(posedge clk or negedge rstn) if (!rstn) rb_v_q <= 1'b0; else rb_v_q <= fr_v;
    always @(posedge clk) rb_d_q <= fr;
    // ---------------------------------------------------------------- ENG finish: one per copy
    wire [2:0] tbad; wire [3*2-1:0] ft; wire [3*8-1:0] fb; wire [3:0] cr_v, cf; wire [31:0] chh [0:3], ckk [0:3], cdd [0:3];
    genvar pp, cc;
    generate
        for (pp = 0; pp < 3; pp = pp + 1) begin : g_dec
            wire [3:0] tv = dl_b[pp * 8 + 4 +: 4], ts = dl_b[pp * 8 +: 4];
            assign tbad[pp] = md && dl_v[pp] && tv >= NE;
            assign ft[pp * 2 +: 2] = tv[3:2];
            assign fb[pp * 8 +: 8] = ts * NVL;
        end
        for (cc = 0; cc < 4; cc = cc + 1) begin : g_cp
            wire [2:0] fv;
            for (pp = 0; pp < 3; pp = pp + 1) begin : g_v
                assign fv[pp] = md && dl_v[pp] && dl_b[pp * 8 + 4 +: 2] == cc && dl_b[pp * 8 + 6 +: 2] != 2'd3;
            end
            ot_s81dv_eng_finish #(.NV(NS * NVL), .K(NVL), .P(3), .LA(LA)) u_e (.clk(clk), .rst_n(rstn), .go(go_c),
                .f_v(fv), .f_t(ft), .f_base(fb), .f_d(dl_d), .r_v(cr_v[cc]), .r_hh(chh[cc]), .r_kk(ckk[cc]), .r_dd(cdd[cc]),
                .fault(cf[cc]));
        end
    endgenerate
    // per-copy results: pending until emitted, lowest copy first, one a cycle
    reg [3:0] epd; reg [31:0] ehh [0:3], ekk [0:3], edd [0:3];
    wire [3:0] eall = epd | cr_v;
    wire [3:0] eoh = eall & ~(eall - 4'd1);
    integer d2;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin epd <= 4'd0; e_v_q <= 1'b0; end
        else if (go_c) begin epd <= 4'd0; e_v_q <= 1'b0; end
        else begin epd <= eall & ~eoh; e_v_q <= |eall; end
    always @(posedge clk) begin
        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (cr_v[d2]) begin ehh[d2] <= chh[d2]; ekk[d2] <= ckk[d2]; edd[d2] <= cdd[d2]; end
        // S81-KITS-RTLC 10-24 (raw face_guard: no output pin flop reads itself): the ENG result registers are ZERO when no
        // copy is emitted (were: hold), so e_* change only where e_v = 0 (the collection reads them under e_v).
        e_c_q <= 2'd0; e_hh_q <= 32'd0; e_kk_q <= 32'd0; e_dd_q <= 32'd0;
`ifdef OT_RTLC_MUT_XFIN   // RTLC bench mutant: e_kk carries e_hh
        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (eoh[d2]) begin
            e_c_q <= d2; e_hh_q <= cr_v[d2] ? chh[d2] : ehh[d2]; e_kk_q <= cr_v[d2] ? chh[d2] : ehh[d2];
            e_dd_q <= cr_v[d2] ? cdd[d2] : edd[d2];
        end
`else
        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (eoh[d2]) begin
            e_c_q <= d2; e_hh_q <= cr_v[d2] ? chh[d2] : ehh[d2]; e_kk_q <= cr_v[d2] ? ckk[d2] : ekk[d2];
            e_dd_q <= cr_v[d2] ? cdd[d2] : edd[d2];
        end
`endif
    end
    (* keep = "true" *) reg flt;                        // sticky state (kept); the fault pin flop loads its next value
    wire flt_set = xf || rf || eflt || (|tbad) || (|cf);
    always @(posedge clk or negedge rstn)
        if (!rstn) begin flt <= 1'b0; fault_q <= 1'b0; end
        else if (go_c) begin flt <= 1'b0; fault_q <= 1'b0; end
        else begin flt <= flt | flt_set; fault_q <= flt | flt_set; end
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
    ot_s81dv_xfin #(.NS(NS), .NVL(NVL), .LM(LM), .LA(LA), .SIW(8)) u_xf (.clk(clk), .rst_n(rstn), .go(go), .mode(1'b0), .sid(SID[3:0]), .eps(eps),
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
