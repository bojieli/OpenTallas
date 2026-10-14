`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81 SU kv RMSNorm -> RoPE -> FP8 QDQ, split into small hardened masters (el1011-s81su-kv, 2026-10-12; PHYSICAL SPEC
// KV v3, the QN v3 method).  Replaces the two KV lane tiles of ot_s81_su_tile (TK 1: 942k flops on one root each) by
//   TAP    ot_s81_su_kvt x 4   (data QUARTERS: quarter u carries bits [128 u, 128 u + 128) of every spine row; the control
//                               is identical in all four): pin flops, row numbering (5 parameter rows a KV job, 1 a GK
//                               job), a registered rotation of the operand rows into positions (operand row mod N / 16),
//                               the cos / sin parameter rows (rows 1-4: this quarter's 128 b = RoPE engines u and u + 4),
//                               quarter 0: obase / eps / go / ready / the faults.
//   NORM   ot_s81_su_kve x N/8 (8 lanes = one golden chunk; RP 1 on the last RD / 8 engines: the RoPE tail): x and the 4
//                               gain sets in flops (NV 1: no SRAM macro), ONE multiplier a lane (time-shared: the square,
//                               x * r, w * p, and for RP 1 the two RoPE products), the chunk's 8 squares summed by ONE
//                               sequential adder (the golden chain order, the same 7 LA latency) -> a registered partial;
//                               y = bf16(w * (x * r)) (RP 1: bf16(y cos -+ y_pair sin)) registered out.
//   HALF   ot_s81_su_qnh x 4   (the QN master, unchanged): 16 chunk partials -> the golden's aligned subtree.
//   REDUCE ot_s81_su_qnr x 1   (NE 4, NV 1, D 512): the top two tree levels, / D, + eps, rsqrt -> rstd (broadcast over
//                               equal-depth relays to every engine: lockstep).
//   QUANT  ot_s81_su_kvq x N/32: one FP8 act-quant block (32 lanes = engines 4 b .. 4 b + 3; ot_dsrom_actquant_f12
//                               XSRAM, the qbe pattern), one write slot: every engine its y row at its output; an even
//                               engine also the codes row {q_b+1, q_b} (pair exchange); engine b % 8 == 7 also the masked
//                               exps row of its 8 blocks (their e gathered over registered pins).
// Values: every step is the golden's (ot_s81_su_norm_lg TK 1): lane-local multiplies, the chunk chain (8 lanes summed
// sequentially), the chunk tree pairwise in order, the same divc / eps / rsqrt, RoPE products and add in the same
// operand order, the same act-quant; only latency changes.  VM rows as before: codes rows obase + [0, N / 64), the
// exps row obase + N / 64 (one masked write a group of 8 blocks: N / 256 writes), y rows obase + N / 64 + 1 + b.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_kvt #(
    parameter integer N = 512, S_RD = 16, NFI = 65, MUT = 0,
    parameter integer NB = 64                       // offset-copy banks over the 128 data bits (bit-local floorplan)
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*128-1:0]    dn_d_i,         // this quarter of every slot
    input  wire [NFI-1:0]         i_f,            // the norm engines' / reduce's sticky faults (relayed; quarter 0)
    output reg  [N/16-1:0]        e_v,            // position j: operand row j (this quarter)
    output reg  [N/16*128-1:0]    e_d,
    output reg                    e_gk,           // the job is a gain load (K_GK)
    output reg  [1:0]             e_gr, e_gw,     // gain set read (KV) / written (GK)
    output reg                    e_go,           // a KV job's parameter rows are in (a pulse)
    output reg  [13:0]            e_ob,           // the KV job's obase (quarter 0)
    output reg  [31:0]            e_eps,          // the KV job's eps (quarter 0)
    output reg  [511:0]           e_cs,           // {sin hi, sin lo, cos hi, cos lo}: this quarter of param rows 4..1
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer L = N / 16, LL = $clog2(L);
    localparam [3:0] K_KV = 1, K_GK = 7;
    localparam integer NPK = 5;                    // parameter rows of a KV job (descriptor, cos lo / hi, sin lo / hi)
`ifndef SYNTHESIS
    initial if ((1 << LL) != L || L < 2 || S_RD > L || NB < 1 || NB > 128) $fatal(1, "ot_s81_su_kvt: N / 16 a power of two >= max(2, S_RD)");
`endif
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg dq_st; reg [3:0] dq_kind; reg [1:0] dq_gsel; reg [7:0] dq_jid; reg [S_RD-1:0] dq_v; reg [S_RD*128-1:0] dq_d;
    reg [NFI-1:0] fq;
    always @(posedge clk) begin dq_kind <= dn_kind_i; dq_gsel <= dn_gsel_i; dq_jid <= dn_jid_i; dq_d <= dn_d_i; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; fq <= 0; end
                                           else begin dq_st <= dn_st_i; dq_v <= dn_v_i; fq <= i_f; end
    // row numbering, all from registers: rl = rows of the job before this cycle's group (mod L), sr = the same count
    // saturated at 8 (>= every parameter count), np = the job's parameter rows (KV 5, GK 1); slot s carries row
    // rows-before + s: a parameter row while that is < np, else operand row (rows-before + s - np), position mod L.
    localparam integer PCW = $clog2(S_RD + 1);
    reg mine, gk; reg [1:0] gsel; reg [7:0] jid; reg [LL-1:0] rl; reg [3:0] sr; reg [2:0] np;
    reg [PCW-1:0] pc;
    always @(*) begin : pcnt
        integer i;
        pc = 0;
        for (i = 0; i < S_RD; i = i + 1) pc = pc + dq_v[i];
    end
    wire [2:0]    np_n = dq_st ? ((dq_kind == K_GK) ? 3'd1 : NPK[2:0]) : np;
    wire [LL-1:0] rl_n = dq_st ? {LL{1'b0}} : rl + pc;     // mod L
    wire [4+PCW:0] sr_s = {{(PCW+1){1'b0}}, sr} + {5'd0, pc};
    wire [3:0]    sr_n = dq_st ? 4'd0 : (sr_s >= 8) ? 4'd8 : sr_s[3:0];
    // the rotation offset off = (rows before - np) mod L, REGISTERED, one kept copy a BIT BANK (el1013 s81su-kvsw: the
    // tap is floorplanned bit-local -- bit b of all S_RD slots and all L positions shares one 3.3 um band of the pin
    // faces, so the 16 -> L rotation of a bit never leaves its band; the copy that selects it sits in the band too:
    // copy c drives bits [128 c / NB, 128 (c + 1) / NB) of every position, copy NB the valid bit.  The former copy a
    // POSITION drove 129 selects spread over the whole 400 um face.  Every copy holds the same value: no value change.)
    wire [LL-1:0] off_n = rl_n - {{(LL > 3 ? LL - 3 : 0){1'b0}}, np_n};
    wire [LL*(NB+1)-1:0] kq;
    genvar gj;
    generate for (gj = 0; gj <= NB; gj = gj + 1) begin : g_off
        ot_s81_su_qn_keep_ff #(.W(LL)) u_k (.clk(clk), .rst_n(rst_n), .d(off_n), .q(kq[LL * gj +: LL]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin mine <= 1'b0; gk <= 1'b0; gsel <= 2'd0; jid <= 8'd0; rl <= 0; sr <= 4'd0; np <= 3'd1; end
        else begin
            if (dq_st) begin mine <= (dq_kind == K_KV || dq_kind == K_GK); gk <= (dq_kind == K_GK); gsel <= dq_gsel;
                             jid <= dq_jid; end
            rl <= rl_n; sr <= sr_n; np <= np_n;
        end
    end
    // per slot: operand-row valid; parameter row j (KV jobs) captured by a decoded compare
    reg [S_RD-1:0] opv;
    reg [S_RD-1:0] pj [0:NPK-1];
    always @(*) begin : slots
        integer s, j;
        reg [4:0] gi;
        for (s = 0; s < S_RD; s = s + 1) begin
            gi = {1'b0, sr} + s;
            opv[s] = mine && dq_v[s] && (gi >= {2'd0, np});
            for (j = 0; j < NPK; j = j + 1) pj[j][s] = mine && !gk && dq_v[s] && (gi == j);
        end
    end
    wire prm_last = |pj[NPK - 1];
    localparam integer RB = 128 + 1;
    reg [L*RB-1:0] rv [0:LL];
    always @(*) begin : rot
        integer s, k, b;
        rv[0] = 0;
        for (s = 0; s < S_RD; s = s + 1) rv[0][RB * s +: RB] = {opv[s], dq_d[128 * s +: 128]};
        for (k = 0; k < LL; k = k + 1)
            for (s = 0; s < L; s = s + 1)
                for (b = 0; b < RB; b = b + 1) begin : pos
                    reg [LL-1:0] off;
                    off = kq[LL * ((b == 128) ? NB : (b * NB) / 128) +: LL];
                    rv[k + 1][RB * s + b] = off[k] ? rv[k][RB * ((s - (1 << k) + L) % L) + b] : rv[k][RB * s + b];
                end
    end
    always @(posedge clk) begin : oreg
        integer j, s;
        for (j = 0; j < L; j = j + 1) e_d[128 * j +: 128] <= rv[LL][RB * j +: 128];
        for (s = 0; s < S_RD; s = s + 1) begin
            if (pj[0][s]) begin e_ob <= dq_d[128 * s +: 14]; e_eps <= dq_d[128 * s + 96 +: 32]; end
            for (j = 1; j < NPK; j = j + 1) if (pj[j][s]) e_cs[128 * (j - 1) +: 128] <= dq_d[128 * s +: 128];
        end
        e_gk <= gk; e_gr <= (MUT == 4) ? 2'd0 : gsel; e_gw <= gsel;
    end
    always @(posedge clk or negedge rst_n) begin : vreg
        integer j;
        if (!rst_n) begin e_v <= 0; e_go <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; end
        else begin
            for (j = 0; j < L; j = j + 1) e_v[j] <= rv[LL][RB * j + 128];
            e_go <= prm_last; o_rdy <= prm_last; o_rjid <= jid;
            o_fu <= o_fu | (|fq); o_fo <= 1'b0; o_alive <= 1'b1; o_den <= 1'b1;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// NORM ENGINE (NV 1): 8 lanes (one golden chunk).  x (the KV job's operand row) and the 4 gain sets in flops.  One
// multiplier a lane: the square (operand arrival), x * r (the rstd's arrival + 1), w * p (LM later, p = the multiplier's
// own output that cycle); RP 1 (the RoPE tail): then y * cos and y_pair * (-+ sin) on the same multiplier, one add a lane.
// A KV job is one vector and the controller runs one job at a time, so the phases never overlap.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_kve #(
    parameter integer RP = 0, LM = 5, LA = 4
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire          i_v,
    input  wire [255:0]  i_x,
    input  wire          i_gk,
    input  wire [1:0]    i_gr, i_gw,
    input  wire [127:0]  i_cos,           // RP 1: cos of this engine's 4 lane pairs (static over the job)
    input  wire [127:0]  i_sin,
    input  wire          r_v,
    input  wire [31:0]   r_d,
    output reg           p_v,
    output reg  [31:0]   p_d,
    output reg           y_v,
    output reg  [255:0]  y,
    output reg           o_f
);
    localparam integer LAR = (LA >= 5) ? LA : LA + 1;      // the RoPE add (as ot_s81_su_norm_lg)
`ifndef SYNTHESIS
    initial if (LM < 2 || LA < 2) $fatal(1, "ot_s81_su_kve: LM, LA >= 2");
`endif
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin
            s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {s[31:16], 16'd0};
        end
    endfunction
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg v_q, gk_q, rv_q; reg [255:0] x_q; reg [1:0] gr_q, gw_q; reg [31:0] rd_q;
    always @(posedge clk) begin x_q <= i_x; gk_q <= i_gk; gr_q <= i_gr; gw_q <= i_gw; rd_q <= r_d; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin v_q <= 1'b0; rv_q <= 1'b0; end
                                           else begin v_q <= i_v; rv_q <= r_v; end
    // the store: x and the 4 gain sets (no reset)
    reg [255:0] xs; reg [255:0] gn [0:3]; reg [31:0] rh;
    always @(posedge clk) begin : st
        integer g;
        if (v_q && !gk_q) xs <= x_q;
        for (g = 0; g < 4; g = g + 1) if (v_q && gk_q && gw_q == g) gn[g] <= x_q;
        if (rv_q) rh <= rd_q;
    end
    reg [255:0] gs;
    always @(*) begin : gsel
        integer g;
        gs = 256'd0;
        for (g = 0; g < 4; g = g + 1) if (gr_q == g) gs = gs | gn[g];
    end
    // cos / sin pin flops (RP 1; static over the job)
    wire [127:0] i_cs_cos, i_cs_sin;
    generate if (RP != 0) begin : g_csp
        reg [127:0] cq, sq;
        always @(posedge clk) begin cq <= i_cos; sq <= i_sin; end
        assign i_cs_cos = cq; assign i_cs_sin = sq;
    end else begin : g_csz
        assign i_cs_cos = 128'd0; assign i_cs_sin = 128'd0;
    end endgenerate
    // the multiplier issue: square | x * r | w * p | (RP) y * cos | y_pair * -+sin
    localparam integer DR = 2 + LM + LAR;
    wire [LM+1:0] sc;
    ot_hdc_vline #(.D(LM + 1)) u_sc (.clk(clk), .rst_n(rst_n), .v(rv_q), .vd(sc));
    wire sqv = v_q && !gk_q;
    wire xrv = sc[1];
    wire wpv = sc[LM + 1];
    wire [LM:0] kwp;
    wire [DR:0] kr;
    wire r1v = (RP != 0) && kr[1];
    wire r2v = (RP != 0) && kr[2];
    wire mv = sqv || xrv || wpv || r1v || r2v;
    wire [255:0] ym;
    wire [7:0] lf;
    reg  [255:0] yr;                                       // RP: bf16(w * p), the RoPE operand
    genvar l;
    generate for (l = 0; l < 8; l = l + 1) begin : g_lane
        wire [31:0] cc = i_cs_cos[32 * (l / 2) +: 32];
        wire [31:0] sn = i_cs_sin[32 * (l / 2) +: 32];
        wire [31:0] sb = (l % 2) ? sn : {~sn[31], sn[30:0]};
        wire [31:0] a = sqv ? x_q[32 * l +: 32] : wpv ? gs[32 * l +: 32] : r1v ? yr[32 * l +: 32] :
                        r2v ? yr[32 * (l ^ 1) +: 32] : xs[32 * l +: 32];
        wire [31:0] b = sqv ? x_q[32 * l +: 32] : wpv ? ym[32 * l +: 32] : r1v ? cc : r2v ? sb : rh;
        ot_hdc_qmul_lat #(LM) u_m (clk, rst_n, mv, a, b, ym[32 * l +: 32], lf[l]);
    end endgenerate
    ot_hdc_vline #(.D(LM)) u_kw (.clk(clk), .rst_n(rst_n), .v(wpv), .vd(kwp));
    ot_hdc_vline #(.D(DR)) u_kr (.clk(clk), .rst_n(rst_n), .v(kwp[LM]), .vd(kr));
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && sqv && (xrv || wpv || r1v || r2v)) $fatal(1, "ot_s81_su_kve: square and scale phases overlap");
`endif
    // y: RP 0 = bf16(w * p); RP 1 = bf16(qadd(y cos, y_pair (-+ sin))) of y = bf16(w * p)
    wire ff;
    generate if (RP == 0) begin : g_y
        always @(posedge clk) if (kwp[LM]) begin : yo
            integer q;
            for (q = 0; q < 8; q = q + 1) y[32 * q +: 32] <= bf16(ym[32 * q +: 32]);
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) y_v <= 1'b0; else y_v <= kwp[LM];
        assign ff = 1'b0;
    end else begin : g_rope
        reg [255:0] pp;
        wire [255:0] rs;
        wire [7:0] af;
        always @(posedge clk) begin : yrb
            integer q;
            if (kwp[LM]) for (q = 0; q < 8; q = q + 1) yr[32 * q +: 32] <= bf16(ym[32 * q +: 32]);
            if (kr[1 + LM]) pp <= ym;
        end
        genvar q;
        for (q = 0; q < 8; q = q + 1) begin : g_ra
            ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, kr[2 + LM], pp[32 * q +: 32], ym[32 * q +: 32], rs[32 * q +: 32], af[q]);
        end
        always @(posedge clk) if (kr[DR]) begin : yo
            integer k;
            for (k = 0; k < 8; k = k + 1) y[32 * k +: 32] <= bf16(rs[32 * k +: 32]);
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) y_v <= 1'b0; else y_v <= kr[DR];
        assign ff = |af;
    end endgenerate
    // the chunk: 8 squares summed sequentially (the golden chain: acc = ((s0 + s1) + s2) + ... + s7) on one adder,
    // add k issued LA (k - 1) cycles after the squares (the latency of the former 7-adder chain)
    localparam integer DS = LM + 7 * LA;
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rst_n), .v(sqv), .vd(vs));
    reg [31:0] sh [2:7];
    always @(posedge clk) begin : shb
        integer k;
        if (vs[LM]) for (k = 2; k < 8; k = k + 1) sh[k] <= ym[32 * k +: 32];
    end
    reg av; reg [31:0] aa, ab;
    wire [31:0] acc;
    wire cf;
    always @(*) begin : aop
        integer k;
        av = vs[LM]; aa = ym[31:0]; ab = ym[63:32];
        for (k = 2; k < 8; k = k + 1) if (vs[LM + LA * (k - 1)]) begin av = 1'b1; aa = acc; ab = sh[k]; end
    end
    ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, av, aa, ab, acc, cf);
    always @(posedge clk or negedge rst_n) if (!rst_n) p_v <= 1'b0; else p_v <= vs[DS];
    always @(posedge clk) p_d <= acc;
    always @(posedge clk or negedge rst_n) if (!rst_n) o_f <= 1'b0; else o_f <= o_f | (|lf) | cf | ff;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// QUANT ENGINE: one FP8 act-quant block b = cfg_b (32 lanes = norm engines 4 b .. 4 b + 3), one write slot.  The y row
// (obase + N / 64 + 1 + b) at the block's output; an even engine the codes row {q_b+1, q_b} at obase + b / 2 two cycles
// later (the odd neighbour's q over registered pins); engine b % 8 == 7 the exps row obase + N / 64 of blocks
// b - 7 .. b (mask: their 4 words), once all 8 e's have arrived (gathered over registered pins, any order).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_kvq #(
    parameter integer N = 512, MLAT = 5
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire [3:0]    cfg_b,
    input  wire          i_v,
    input  wire [1023:0] i_y,
    input  wire [13:0]   i_ob,
    input  wire          nx_i_v,
    input  wire [255:0]  nx_i_q,
    output reg           nx_o_v,
    output reg  [255:0]  nx_o_q,
    output reg           e_o_v,
    output reg  [9:0]    e_o_e,
    input  wire [7:0]    g_i_v,           // b % 8 == 7: the e of blocks b - 7 .. b (others tie 0)
    input  wire [79:0]   g_i_e,
    output reg           o_v,
    output reg  [13:0]   o_a,
    output reg  [15:0]   o_m,
    output reg  [511:0]  o_d,
    output reg           o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]    o_rjid
);
    localparam integer LAT = 13 + MLAT;                    // ot_dsrom_actquant_f12: v -> vo
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q, nv_q; reg [1023:0] y_q; reg [13:0] ob_q; reg [255:0] nq_q; reg [3:0] cb_q; reg [7:0] gv_q; reg [79:0] ge_q;
    always @(posedge clk) begin y_q <= i_y; ob_q <= i_ob; nq_q <= nx_i_q; cb_q <= cfg_b; ge_q <= g_i_e; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin v_q <= 1'b0; nv_q <= 1'b0; gv_q <= 8'd0; end
                                           else begin v_q <= i_v; nv_q <= nx_i_v; gv_q <= g_i_v; end
    wire vo, fault; wire [255:0] q; wire signed [9:0] e; wire [511:0] yq;
    ot_dsrom_actquant_f12 #(.MLAT(MLAT), .XSRAM(1)) u_aq (.clk(clk), .rst_n(rst_n), .v(v_q), .fp4(1'b0), .x(y_q),
                                                         .vo(vo), .q(q), .e(e), .y(yq), .fault(fault));
`ifndef SYNTHESIS
    wire [LAT:0] vchk;
    ot_hdc_vline #(.D(LAT)) u_vc (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vchk));
    always @(posedge clk) if (rst_n && vo !== vchk[LAT]) $fatal(1, "ot_s81_su_kvq: block latency is not %0d", LAT);
`endif
    // the gather (b % 8 == 7): hold each e until all 8 are in
    reg [7:0] gh; reg [79:0] gd; reg ex_p; reg [127:0] ex_d;
    wire last = (cb_q[2:0] == 3'd7);
    always @(posedge clk) begin : gdb
        integer j;
        for (j = 0; j < 8; j = j + 1) if (gv_q[j]) gd[10 * j +: 10] <= ge_q[10 * j +: 10];
        if (last && &gh) for (j = 0; j < 8; j = j + 1) ex_d[16 * j +: 16] <= {6'd0, gd[10 * j +: 10]};
    end
    reg d1v, d2v; reg [255:0] d1q, d2q;
    always @(posedge clk) begin
        nx_o_q <= q; e_o_e <= e;
        d1q <= q; d2q <= d1q;
    end
    // the slot: y row at vo; codes row (even) at d2; the exps row (last) when pending and the slot is free
    wire ex_w = ex_p && !vo;
    always @(posedge clk) begin
        if (vo) begin
            o_a <= ob_q + N / 64 + 1 + cb_q; o_m <= 16'hFFFF; o_d <= yq;
        end else if (d2v && !cb_q[0]) begin
            o_a <= ob_q + cb_q[3:1]; o_m <= 16'hFFFF; o_d <= {nq_q, d2q};
        end else begin
            o_a <= ob_q + N / 64; o_m <= 16'h000F << (4 * cb_q[3]); o_d <= {4{ex_d}};
        end
    end
    reg fs;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            nx_o_v <= 0; e_o_v <= 0; d1v <= 0; d2v <= 0; o_v <= 0; fs <= 0; gh <= 0; ex_p <= 0;
            o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0;
        end else begin
            nx_o_v <= vo; e_o_v <= vo; d1v <= vo; d2v <= d1v; fs <= fs | fault;
            o_v <= vo || (d2v && !cb_q[0]) || ex_w;
            if (last && &gh) begin gh <= 8'd0; ex_p <= 1'b1; end
            else begin gh <= gh | gv_q; if (ex_w) ex_p <= 1'b0; end
            o_fu <= fs; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= 8'd0;
            o_fo <= o_fo | (d2v && !cb_q[0] && !nv_q) | (d2v && !cb_q[0] && vo) | (|(gh & gv_q));
        end
    end
endmodule
