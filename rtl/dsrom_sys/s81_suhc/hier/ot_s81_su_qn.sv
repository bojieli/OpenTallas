`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81 SU q RMSNorm -> FP8, split into small hardened masters (el1011-s81su-qn, 2026-10-12; PHYSICAL SPEC QN v3).
// Replaces the two QN lane tiles of ot_s81_su_tile (TK 0: 450,764 flops on one root each) by
//   TAP    ot_s81_su_qnt x 2   (data halves: half h carries bits [256 h, 256 h + 256) of every spine row; the control is
//                               identical in both): pin flops, row numbering, a registered rotation of the operand rows
//                               into positions (operand row index mod RPB), each with its vector index; job fields.
//   NORM   ot_s81_su_qne x NE  (NE = N / 8; 8 lanes = one golden chunk each, position-independent, hardened once):
//                               x and the 4 gain sets in one SRAM bank, ONE multiplier a lane (time-shared: the squares
//                               while the operands stream in, then x * r / w * p in blocks of LM vectors), the chunk's
//                               sequential sum -> a registered partial; y = bf16(w * (x * r)) registered out.
//   REDUCE ot_s81_su_qnr x 1   : the NE chunk sums -> the golden's pairwise tree (aligned: engine n = chunk n), the
//                               vector levels, ss / D, + eps, rsqrt -> rstd, broadcast over equal-depth relays.
//   QUANT  ot_s81_su_qnq x NQ  (NQ = N / 32): the QB v3 engine pattern (ot_dsrom_actquant_f12, XSRAM wait line, one
//                               32-element block from 4 norm engines), pair exchange, one write slot each: an even
//                               engine the codes row {q_b+1, q_b}, an odd engine the masked exps word {e_b, e_b-1}.
// Values: every step is the golden's (ot_dsrom_su_norm / ot_s81_su_norm_lg): lane-local multiplies, the chunk chain
// (8 lanes summed sequentially), the chunk tree pairwise in order, the vector levels, the same divc / eps / rsqrt; only
// latency changes.  VM rows as before: vector v of the job writes rows obase + v (N / 64 + 1) + [0, N / 64) (codes) and
// + N / 64 (exps, one masked word a block pair).  No pass assembly anywhere: every engine takes its own position when
// it arrives; the reduce matches the NE partials of a vector by the vector's parity (2 entries an engine), and the scale
// phase starts at the rstd, which reaches every engine in the same cycle, so the y of a block leave in one cycle.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qnt #(
    parameter integer N = 256, S_RD = 16, NFI = 33, MUT = 0, CB = 32
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*256-1:0]    dn_d_i,         // this half of every slot
    input  wire [NFI-1:0]         i_f,            // the norm engines' / reduce's sticky faults (relayed)
    output reg  [N/16-1:0]        e_v,            // position j: operand row j of a vector (this half)
    output reg  [N/16*256-1:0]    e_d,
    output reg  [N/16*8-1:0]      e_t,            // its vector index
    output reg                    e_gq,           // the job is a gain load (K_GQ)
    output reg  [1:0]             e_gr, e_gw,     // gain set read (QN) / written (GQ)
    output reg                    e_go,           // a QN job's parameter row is in (a pulse)
    output reg  [13:0]            e_ob,           // the QN job's obase (half 0)
    output reg  [31:0]            e_eps,          // the QN job's eps (half 0)
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer L = N / 16, LL = $clog2(L);
    localparam [3:0] K_QN = 0, K_GQ = 6;
`ifndef SYNTHESIS
    initial if ((1 << LL) != L || L < 2 || S_RD > L || CB < 1 || CB > 256 || 256 % CB != 0) $fatal(1, "ot_s81_su_qnt: N / 16 a power of two >= max(2, S_RD)");
`endif
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg dq_st; reg [3:0] dq_kind; reg [1:0] dq_gsel; reg [7:0] dq_jid; reg [S_RD-1:0] dq_v; reg [S_RD*256-1:0] dq_d;
    reg [NFI-1:0] fq;
    always @(posedge clk) begin dq_kind <= dn_kind_i; dq_gsel <= dn_gsel_i; dq_jid <= dn_jid_i; dq_d <= dn_d_i; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; fq <= 0; end
                                           else begin dq_st <= dn_st_i; dq_v <= dn_v_i; fq <= i_f; end
    // job context and row numbering (the first row of a QN / GQ job is its parameter row, the rest operand rows).
    // rcnt (rows before this cycle's group) = st_r ? 0 : ra + pc_r, from REGISTERED terms only: pc_r = the previous
    // group's slot count (popcount of the dq_v pin flops, its own stage), st_r its start, ra = the previous rcnt.
    // Induction: rcnt(t+1) = st(t) ? 0 : rcnt(t) + pc(t), the former recurrence; reset 0 = the former reset.  So the
    // popcount is never in series with the add (was dq_v -> rc_j 725 ps / 19 lv) and no input pin feeds logic.
    localparam integer PCW = $clog2(S_RD + 1);
    reg mine, gq; reg [1:0] gsel; reg [7:0] jid; reg [15:0] ra; reg [PCW-1:0] pc_r; reg st_r;
    reg [PCW-1:0] pc;
    always @(*) begin : pcnt
        integer i;
        pc = 0;
        for (i = 0; i < S_RD; i = i + 1) pc = pc + dq_v[i];
    end
    wire [15:0] rcnt = st_r ? 16'd0 : ra + pc_r;
    // the rotation offset off = (rcnt - 1) mod L, REGISTERED, one copy a position (265-bit 2:1 mux a level each) in a
    // kept module (SYNTH_KEEP_MODULES): synthesis cannot merge the copies into one 12k-load net (opt_merge folded the
    // former plain rc_j copies).  Next off = (st ? 0 : rcnt + pc) - 1 on LL bits only (popcount mod L + a 4-bit add);
    // the mux selects stay register outputs (an add in front of them cost the e_d outputs 340 ps after placement).
    localparam integer KW = LL;
    wire [LL-1:0] off_n = (dq_st ? {LL{1'b0}} : rcnt[LL-1:0] + pc[LL-1:0]) - 1'b1;
    wire [KW*L-1:0] kq;
    genvar gj;
    generate for (gj = 0; gj < L; gj = gj + 1) begin : g_off
        ot_s81_su_qn_keep_ff #(.W(KW)) u_k (.clk(clk), .rst_n(rst_n), .d(off_n),
                                            .q(kq[KW * gj +: KW]));
    end endgenerate
    // Opt-in physical control banks: bit-interleaved face plans spread a position's 256 data bits over the full
    // strip. CB32/16 keeps one offset copy beside each data bank (select fanout32/16), while the original copy drives
    // only the nine metadata bits. Same offset, clock edge, mux levels and registers; CB256 preserves the original.
    localparam integer DB = 256 / ((CB > 0) ? CB : 256);
    wire [KW*L*DB-1:0] kqd;
    genvar gp, gb;
    generate if (CB < 256) begin : g_data_ctrl
        for (gp = 0; gp < L; gp = gp + 1) begin : g_pos
            for (gb = 0; gb < DB; gb = gb + 1) begin : g_bank
                ot_s81_su_qn_keep_ff #(.W(KW)) u_k (.clk(clk), .rst_n(rst_n),
                    .d(off_n ^ ((MUT == 6) ? {{(KW-1){1'b0}},1'b1} : {KW{1'b0}})),
                    .q(kqd[KW*(gp*DB+gb) +: KW]));
            end
        end
    end else begin : g_original_ctrl
        assign kqd = kq;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin mine <= 1'b0; gq <= 1'b0; gsel <= 2'd0; jid <= 8'd0; ra <= 16'd0; pc_r <= 0; st_r <= 1'b0; end
        else begin
            if (dq_st) begin mine <= (dq_kind == K_QN || dq_kind == K_GQ); gq <= (dq_kind == K_GQ); gsel <= dq_gsel;
                             jid <= dq_jid; end
            ra <= rcnt; pc_r <= pc; st_r <= dq_st;
        end
    end
    wire prm = mine && dq_v[0] && rcnt == 16'd0;
    // per slot: operand-row valid, vector index; rotate left by off = (rcnt - 1) mod L into positions
    localparam integer RB = 256 + 8 + 1;
    reg [L*RB-1:0] rv [0:LL];
    always @(*) begin : rot
        integer s, k, b;
        reg [15:0] ix;
        rv[0] = 0;
        for (s = 0; s < S_RD; s = s + 1) begin
            ix = rcnt + s - 16'd1;
            rv[0][RB * s +: RB] = {mine && dq_v[s] && (rcnt != 16'd0 || s != 0), ix[LL +: 8], dq_d[256 * s +: 256]};
        end
        for (k = 0; k < LL; k = k + 1)
            for (s = 0; s < L; s = s + 1) begin : pos
                reg [LL-1:0] off;
                off = kq[KW * s +: KW];
                rv[k + 1][RB * s +: RB] = off[k] ? rv[k][RB * ((s - (1 << k) + L) % L) +: RB] : rv[k][RB * s +: RB];
                if (CB < 256)
                    for (b = 0; b < DB; b = b + 1)
                        rv[k + 1][RB*s+CB*b +: CB] = kqd[KW*(s*DB+b)+k]
                            ? rv[k][RB*((s-(1<<k)+L)%L)+CB*b +: CB]
                            : rv[k][RB*s+CB*b +: CB];
            end
    end
    always @(posedge clk) begin : oreg
        integer j;
        for (j = 0; j < L; j = j + 1) begin
            e_d[256 * j +: 256] <= rv[LL][RB * j +: 256];
            e_t[8 * j +: 8] <= rv[LL][RB * j + 256 +: 8];
        end
        if (prm && !gq) begin e_ob <= dq_d[13:0]; e_eps <= dq_d[96 +: 32]; end
        e_gq <= gq; e_gr <= (MUT == 4) ? 2'd0 : gsel; e_gw <= gsel;
    end
    always @(posedge clk or negedge rst_n) begin : vreg
        integer j;
        if (!rst_n) begin e_v <= 0; e_go <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; end
        else begin
            for (j = 0; j < L; j = j + 1) e_v[j] <= rv[LL][RB * j + 264];
            e_go <= prm && !gq; o_rdy <= prm && !gq; o_rjid <= jid;
            o_fu <= o_fu | (|fq); o_fo <= 1'b0; o_alive <= 1'b1; o_den <= 1'b1;
        end
    end
endmodule

// a register that synthesis must keep (SYNTH_KEEP_MODULES + keep): per-position copies of a broadcast control value.
// Reset value all ones = the off of rcnt 0 (bit-identical to the former rc_j <= 0 copies).
// keep_hierarchy (S81-QNTKEEP 10-18, ROOT-KEEP f3c8ca0d1): instances are #(.W(..)), so yosys renames them $paramod\...
// and SYNTH_KEEP_MODULES alone matches nothing; the attribute is copied to every $paramod derivative.
(* keep_hierarchy *)
module ot_s81_su_qn_keep_ff #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d,
                                                           output wire [W-1:0] q);
    (* keep = "true" *) reg [W-1:0] q_k;
    always @(posedge clk or negedge rst_n) if (!rst_n) q_k <= {W{1'b1}}; else q_k <= d;
    assign q = q_k;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// NORM ENGINE: 8 lanes (one golden chunk).  SRAM word a = g NV + v: [255:0] x of vector v (written at the job's read
// set g), [511:256] gain vector v of set g.  One multiplier a lane: the square (input phase), then, from the rstd,
// blocks of LM vectors: LM x reads -> x * r, then LM gain reads -> w * p (p = the multiplier's own output that cycle).
// The phases never overlap (a job's scale phase ends before the next job's operands: the controller runs one job at a
// time and its done counts the job's writes).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qne #(
    parameter integer NV = 5, LM = 5, LA = 4
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire          i_v,
    input  wire [255:0]  i_x,
    input  wire [7:0]    i_t,
    input  wire          i_gq,
    input  wire [1:0]    i_gr, i_gw,
    input  wire          r_v,
    input  wire [31:0]   r_d,
    output reg           p_v,
    output reg  [7:0]    p_i,
    output reg  [31:0]   p_d,
    output reg           y_v,
    output reg  [7:0]    y_i,
    output reg  [255:0]  y,
    output reg           o_f
);
    localparam integer DEP = 4 * NV;
    localparam integer AW = (DEP > 64) ? $clog2(DEP) : 6;
    localparam integer DS = LM + 7 * LA;                   // square + chain
`ifndef SYNTHESIS
    initial if (NV < 1 || NV > 255 || LM < 2) $fatal(1, "ot_s81_su_qne: 1 <= NV <= 255, LM >= 2");
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
    reg v_q, gq_q, rv_q; reg [255:0] x_q; reg [7:0] t_q; reg [1:0] gr_q, gw_q; reg [31:0] rd_q;
    always @(posedge clk) begin x_q <= i_x; t_q <= i_t; gq_q <= i_gq; gr_q <= i_gr; gw_q <= i_gw; rd_q <= r_d; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin v_q <= 1'b0; rv_q <= 1'b0; end
                                           else begin v_q <= i_v; rv_q <= r_v; end
    // scale sequencer: blocks of LM slots, x phase (ph 0) then gain phase (ph 1)
    reg run, ph; reg [7:0] bx; reg [7:0] j; reg [31:0] rh;
    wire [8:0] idx = {1'b0, bx} + {1'b0, j};
    wire       iss = run && idx < NV;
    always @(posedge clk) if (rv_q) rh <= rd_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin run <= 1'b0; ph <= 1'b0; bx <= 8'd0; j <= 8'd0; end
        else if (rv_q) begin run <= 1'b1; ph <= 1'b0; bx <= 8'd0; j <= 8'd0; end
        else if (run) begin
            if (j == LM - 1) begin
                j <= 8'd0;
                if (!ph) ph <= 1'b1;
                else begin ph <= 1'b0; bx <= bx + LM; if ({1'b0, bx} + LM >= NV) run <= 1'b0; end
            end else j <= j + 8'd1;
        end
    end
    // the SRAM bank: writes from the pins, reads from the sequencer; a read is captured two cycles later
    wire [AW-1:0] wa = (gq_q ? gw_q : gr_q) * NV + t_q;
    wire [AW-1:0] ra = gr_q * NV + idx[7:0];
    wire [511:0]  mq;
    ot_sram_bank #(.DEPTH(DEP), .AW(AW)) u_m (.clk(clk), .we(v_q), .wa(wa), .wd({x_q, x_q}),
        .wm(gq_q ? {{256{1'b1}}, 256'd0} : {256'd0, {256{1'b1}}}), .re(iss), .ra(ra), .q(mq));
    reg [511:0] cq;
    always @(posedge clk) cq <= mq;                        // capture at the macro output
    reg m1v, m2v, m1p, m2p; reg [7:0] m1i, m2i;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin m1v <= 1'b0; m2v <= 1'b0; end
                                           else begin m1v <= iss; m2v <= m1v; end
    always @(posedge clk) begin m1p <= ph; m2p <= m1p; m1i <= idx[7:0]; m2i <= m1i; end
    // the multiplier issue: square | x * r | w * p
    wire sqv = v_q && !gq_q;
    wire xrv = m2v && !m2p;
    wire wpv = m2v && m2p;
    wire mv = sqv || xrv || wpv;
    wire [255:0] ym;
    wire [7:0] lf;
    genvar l, k;
    generate for (l = 0; l < 8; l = l + 1) begin : g_lane
        wire [31:0] a = sqv ? x_q[32 * l +: 32] : wpv ? cq[256 + 32 * l +: 32] : cq[32 * l +: 32];
        wire [31:0] b = sqv ? x_q[32 * l +: 32] : wpv ? ym[32 * l +: 32] : rh;
        ot_hdc_qmul_lat #(LM) u_m (clk, rst_n, mv, a, b, ym[32 * l +: 32], lf[l]);
    end endgenerate
    // what leaves the multiplier: kind and vector index, LM cycles after the issue
    wire [LM:0] ksq, kxr, kwp;
    ot_hdc_vline #(.D(LM)) u_ks (.clk(clk), .rst_n(rst_n), .v(sqv), .vd(ksq));
    ot_hdc_vline #(.D(LM)) u_kx (.clk(clk), .rst_n(rst_n), .v(xrv), .vd(kxr));
    ot_hdc_vline #(.D(LM)) u_kw (.clk(clk), .rst_n(rst_n), .v(wpv), .vd(kwp));
    wire [7:0] ki;
    ot_hdc_delay #(.W(8), .D(LM)) u_ki (.clk(clk), .rst_n(rst_n), .d(m2i), .q(ki));
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n) begin
        if (sqv && m2v) $fatal(1, "ot_s81_su_qne: square and scale phases overlap");
        if (wpv && !(kxr[LM] && ki == m2i)) $fatal(1, "ot_s81_su_qne: w * p issued without its x * r");
    end
`endif
    // y = bf16(w * (x * r)), registered out
    always @(posedge clk) if (kwp[LM]) begin : yo
        integer q;
        for (q = 0; q < 8; q = q + 1) y[32 * q +: 32] <= bf16(ym[32 * q +: 32]);
        y_i <= ki;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) y_v <= 1'b0; else y_v <= kwp[LM];
    // the chunk: 8 squares summed sequentially (as ot_s81_su_norm_lg g_chunk)
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rst_n), .v(sqv), .vd(vs));
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rst_n), .d(t_q), .q(si));
    wire [31:0] acc [0:7];
    wire [7:0] cf;
    assign acc[0] = ym[31:0];
    assign cf[0] = 1'b0;
    generate for (k = 1; k < 8; k = k + 1) begin : g_j
        wire [31:0] sd;
        if (k == 1) begin : g_nd
            assign sd = ym[32 +: 32];
        end else begin : g_d
            ot_hdc_delay #(.W(32), .D(LA * (k - 1))) u_sd (.clk(clk), .rst_n(rst_n), .d(ym[32 * k +: 32]), .q(sd));
        end
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, vs[LM + LA * (k - 1)], acc[k - 1], sd, acc[k], cf[k]);
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) p_v <= 1'b0; else p_v <= vs[DS];
    always @(posedge clk) begin p_i <= si; p_d <= acc[7]; end
    always @(posedge clk or negedge rst_n) if (!rst_n) o_f <= 1'b0; else o_f <= o_f | (|lf) | (|cf);
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// REDUCE: NE chunk sums a vector -> pairwise tree (golden order) -> vector levels -> ss / D -> + eps -> rsqrt.
// A partial is held by its vector's parity (an engine's vector v + 2 cannot arrive before every engine's vector v).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qnr #(
    parameter integer NE = 32, NV = 5, D = 1280, LM = 5, LA = 4
) (
    input  wire            clk,
    input  wire            rst_in,
    input  wire            i_go,
    input  wire [31:0]     i_eps,
    input  wire [NE-1:0]   p_v,
    input  wire [NE-1:0]   p_p,           // the partial's vector parity
    input  wire [NE*32-1:0] p_d,
    input  wire [NE-1:0]   p_f,           // upstream (half-tree) faults, sticky into o_f
    output reg             r_v,
    output reg  [31:0]     r_d,
    output reg             o_f
);
    localparam integer LT  = $clog2(NE);
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
`ifndef SYNTHESIS
    initial if ((1 << LT) != NE || NE < 2) $fatal(1, "ot_s81_su_qnr: NE a power of two >= 2");
`endif
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg go; reg [31:0] eps; reg [NE-1:0] pv; reg [NE-1:0] pp; reg [NE*32-1:0] pd; reg [NE-1:0] pf;
    always @(posedge clk) begin eps <= i_eps; pd <= p_d; pp <= p_p; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin go <= 1'b0; pv <= 0; pf <= 0; end else begin go <= i_go; pv <= p_v; pf <= p_f; end
    // two entries an engine (by vector parity)
    reg [NE*32-1:0] e0, e1;
    reg [NE-1:0] h0, h1;
    reg ptr; reg [7:0] vi;
    wire fire = (ptr ? (&h1) : (&h0)) && !go;
    always @(posedge clk) begin : ent
        integer e;
        for (e = 0; e < NE; e = e + 1) if (pv[e]) begin
            if (pp[e]) e1[32 * e +: 32] <= pd[32 * e +: 32]; else e0[32 * e +: 32] <= pd[32 * e +: 32];
        end
    end
    always @(posedge clk or negedge rst_n) begin : hb
        integer e;
        if (!rst_n) begin h0 <= 0; h1 <= 0; ptr <= 1'b0; vi <= 8'd0; end
        else if (go) begin h0 <= 0; h1 <= 0; ptr <= 1'b0; vi <= 8'd0; end
        else begin
            if (fire) begin if (ptr) h1 <= 0; else h0 <= 0; ptr <= !ptr; vi <= vi + 8'd1; end
            for (e = 0; e < NE; e = e + 1) if (pv[e]) begin if (pp[e]) h1[e] <= 1'b1; else h0[e] <= 1'b1; end
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && !go) begin : ovc
        integer e;
        for (e = 0; e < NE; e = e + 1)
            if (pv[e] && (pp[e] ? h1[e] : h0[e]) && !(fire && pp[e] == ptr))
                $fatal(1, "ot_s81_su_qnr: engine %0d partial overruns its entry", e);
    end
`endif
    // the chunk tree
    wire [NE*32-1:0] lv = ptr ? e1 : e0;
    wire [31:0] tv [0:LT][0:NE-1];
    wire [LT:0] tf;
    wire [LA*LT:0] fv;
    ot_hdc_vline #(.D(LA * LT)) u_fv (.clk(clk), .rst_n(rst_n), .v(fire), .vd(fv));
    wire [7:0] vsi;
    ot_hdc_delay #(.W(8), .D(LA * LT)) u_vi (.clk(clk), .rst_n(rst_n), .d(vi), .q(vsi));
    genvar c, k, n;
    generate
        for (c = 0; c < NE; c = c + 1) begin : g_t0
            assign tv[0][c] = lv[32 * c +: 32];
        end
        assign tf[0] = 1'b0;
        for (k = 1; k <= LT; k = k + 1) begin : g_tl
            wire [(NE >> k)-1:0] f;
            for (c = 0; c < (NE >> k); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, fv[LA * (k - 1)], tv[k - 1][2 * c], tv[k - 1][2 * c + 1],
                                               tv[k][c], f[c]);
            end
            for (c = (NE >> k); c < NE; c = c + 1) begin : g_tz
                assign tv[k][c] = 32'd0;
            end
            assign tf[k] = |f;
        end
    endgenerate
    wire        vsum_v = fv[LA * LT];
    wire [31:0] vsum = tv[LT][0];
    // vector levels (as ot_s81_su_norm_lg)
    wire [31:0] nv [1:2*NVP-1];
    wire        nd [1:2*NVP-1];
    wire        np [1:2*NVP-1];
    wire [NVP:0] nf;
    assign nf[0] = 1'b0;
    assign nf[NVP] = 1'b0;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            reg [31:0] val;
            reg        vld;
            wire       hit = vsum_v && vsi == n - NVP;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) vld <= 1'b0;
                else if (go) vld <= 1'b0;
                else if (hit) vld <= 1'b1;
            always @(posedge clk) if (hit) val <= vsum;
            assign np[n] = hit;
            assign nd[n] = vld || hit;
            assign nv[n] = vld ? val : vsum;
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_vn
            localparam integer H = $clog2(NVP) - ($clog2(n + 1) - 1);
            if ((((2 * n + 1) << (H - 1)) - NVP) < NV) begin : g_add
                reg st, vld;
                reg [31:0] val;
                wire [LAV:0] av;
                wire [31:0] s;
                wire fire_n = nd[2 * n] && nd[2 * n + 1] && !st && !go;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rst_n), .v(fire_n), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rst_n, fire_n, nv[2 * n], nv[2 * n + 1], s, nf[n]);
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin st <= 1'b0; vld <= 1'b0; end
                    else if (go) begin st <= 1'b0; vld <= 1'b0; end
                    else begin
                        if (fire_n) st <= 1'b1;
                        if (av[LAV]) vld <= 1'b1;
                    end
                end
                always @(posedge clk) if (av[LAV]) val <= s;
                assign np[n] = av[LAV];
                assign nd[n] = vld || av[LAV];
                assign nv[n] = vld ? val : s;
            end else begin : g_pass
                assign nv[n] = nv[2 * n];
                assign nd[n] = nd[2 * n];
                assign np[n] = np[2 * n];
                assign nf[n] = 1'b0;
            end
        end
    endgenerate
    // ss -> register -> / D -> + eps -> rsqrt -> registered out
    reg ssv; reg [31:0] ssd;
    always @(posedge clk or negedge rst_n) if (!rst_n) ssv <= 1'b0; else ssv <= np[1] && !go;
    always @(posedge clk) ssd <= nv[1];
    wire [31:0] mq, me, rr;
    wire        mq_v, me_v, rr_v, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rst_n), .v(ssv), .x(ssd), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps, me, f_eps);
    assign me_v = ve[LA];
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    always @(posedge clk or negedge rst_n) if (!rst_n) r_v <= 1'b0; else r_v <= rr_v;
    always @(posedge clk) r_d <= rr;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) o_f <= 1'b0;
        else o_f <= o_f | (|tf) | (|nf) | f_div | f_eps | f_rsq | (|pf);
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// HALF TREE: NE engines' chunk partials of a vector -> pairwise tree (golden order) -> one registered sum + vector parity.
// Two halves (engines 0..NE-1, NE..2NE-1) feed the reduce (NE 2), whose single level is the golden tree's top add.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qnh #(
    parameter integer NE = 16, LA = 4
) (
    input  wire            clk,
    input  wire            rst_in,
    input  wire            i_go,
    input  wire [NE-1:0]   p_v,
    input  wire [NE-1:0]   p_p,           // the partial's vector parity
    input  wire [NE*32-1:0] p_d,
    output reg             s_v,
    output reg             s_p,           // the sum's vector parity (the reduce holds it by parity)
    output reg  [31:0]     s_d,
    output reg             o_f
);
    localparam integer LT = $clog2(NE);
`ifndef SYNTHESIS
    initial if ((1 << LT) != NE || NE < 2) $fatal(1, "ot_s81_su_qnh: NE a power of two >= 2");
`endif
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg go; reg [NE-1:0] pv; reg [NE-1:0] pp; reg [NE*32-1:0] pd;
    always @(posedge clk) begin pd <= p_d; pp <= p_p; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin go <= 1'b0; pv <= 0; end else begin go <= i_go; pv <= p_v; end
    // two entries an engine (by vector parity)
    reg [NE*32-1:0] e0, e1;
    reg [NE-1:0] h0, h1;
    reg ptr; reg [7:0] vi;
    wire fire = (ptr ? (&h1) : (&h0)) && !go;
    always @(posedge clk) begin : ent
        integer e;
        for (e = 0; e < NE; e = e + 1) if (pv[e]) begin
            if (pp[e]) e1[32 * e +: 32] <= pd[32 * e +: 32]; else e0[32 * e +: 32] <= pd[32 * e +: 32];
        end
    end
    always @(posedge clk or negedge rst_n) begin : hb
        integer e;
        if (!rst_n) begin h0 <= 0; h1 <= 0; ptr <= 1'b0; vi <= 8'd0; end
        else if (go) begin h0 <= 0; h1 <= 0; ptr <= 1'b0; vi <= 8'd0; end
        else begin
            if (fire) begin if (ptr) h1 <= 0; else h0 <= 0; ptr <= !ptr; vi <= vi + 8'd1; end
            for (e = 0; e < NE; e = e + 1) if (pv[e]) begin if (pp[e]) h1[e] <= 1'b1; else h0[e] <= 1'b1; end
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && !go) begin : ovc
        integer e;
        for (e = 0; e < NE; e = e + 1)
            if (pv[e] && (pp[e] ? h1[e] : h0[e]) && !(fire && pp[e] == ptr))
                $fatal(1, "ot_s81_su_qnh: engine %0d partial overruns its entry", e);
    end
`endif
    // the chunk tree
    wire [NE*32-1:0] lv = ptr ? e1 : e0;
    wire [31:0] tv [0:LT][0:NE-1];
    wire [LT:0] tf;
    wire [LA*LT:0] fv;
    ot_hdc_vline #(.D(LA * LT)) u_fv (.clk(clk), .rst_n(rst_n), .v(fire), .vd(fv));
    wire [7:0] vsi;
    ot_hdc_delay #(.W(8), .D(LA * LT)) u_vi (.clk(clk), .rst_n(rst_n), .d(vi), .q(vsi));
    genvar c, k, n;
    generate
        for (c = 0; c < NE; c = c + 1) begin : g_t0
            assign tv[0][c] = lv[32 * c +: 32];
        end
        assign tf[0] = 1'b0;
        for (k = 1; k <= LT; k = k + 1) begin : g_tl
            wire [(NE >> k)-1:0] f;
            for (c = 0; c < (NE >> k); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, fv[LA * (k - 1)], tv[k - 1][2 * c], tv[k - 1][2 * c + 1],
                                               tv[k][c], f[c]);
            end
            for (c = (NE >> k); c < NE; c = c + 1) begin : g_tz
                assign tv[k][c] = 32'd0;
            end
            assign tf[k] = |f;
        end
    endgenerate
    wire        vsum_v = fv[LA * LT];
    wire [31:0] vsum = tv[LT][0];
    always @(posedge clk or negedge rst_n) if (!rst_n) s_v <= 1'b0; else s_v <= vsum_v && !go;
    always @(posedge clk) begin s_d <= vsum; s_p <= vsi[0]; end
    always @(posedge clk or negedge rst_n) if (!rst_n) o_f <= 1'b0; else o_f <= o_f | (|tf);
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// QUANT ENGINE: one FP8 act-quant block (32 lanes = norm engines 4 b .. 4 b + 3), the QB v3 engine pattern
// (ot_s81_su_qbe) with the QN addressing and one write slot: an even engine (cfg_b[0] 0) writes the codes row
// {q_b+1, q_b} at obase + v (N / 64 + 1) + b / 2, an odd engine the exps word {e_b, e_b-1} (mask bit b / 2) of the
// row obase + v (N / 64 + 1) + N / 64, both two cycles after the block's output (the pair's halves cross on registered
// pins).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qnq #(
    parameter integer N = 256, MLAT = 5
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire [3:0]    cfg_b,
    input  wire          i_v,
    input  wire [7:0]    i_t,
    input  wire [1023:0] i_y,
    input  wire [13:0]   i_ob,
    input  wire          nx_i_v,
    input  wire [255:0]  nx_i_q,
    input  wire [9:0]    nx_i_e,
    output reg           nx_o_v,
    output reg  [255:0]  nx_o_q,
    output reg  [9:0]    nx_o_e,
    output reg           o_v,
    output reg  [13:0]   o_a,
    output reg  [15:0]   o_m,
    output reg  [511:0]  o_d,
    output reg           o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]    o_rjid
);
    localparam integer LAT = 13 + MLAT;                    // ot_dsrom_actquant_f12: v -> vo
    localparam integer RQ = N / 64 + 1;                    // VM rows a vector
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q, nv_q; reg [1023:0] y_q; reg [7:0] t_q; reg [13:0] ob_q; reg [255:0] nq_q; reg [9:0] ne_q; reg [3:0] cb_q;
    always @(posedge clk) begin y_q <= i_y; t_q <= i_t; ob_q <= i_ob; nq_q <= nx_i_q; ne_q <= nx_i_e; cb_q <= cfg_b; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin v_q <= 1'b0; nv_q <= 1'b0; end
                                           else begin v_q <= i_v; nv_q <= nx_i_v; end
    wire vo, fault; wire [255:0] q; wire signed [9:0] e; wire [511:0] yq;
    ot_dsrom_actquant_f12 #(.MLAT(MLAT), .XSRAM(1)) u_aq (.clk(clk), .rst_n(rst_n), .v(v_q), .fp4(1'b0), .x(y_q),
                                                         .vo(vo), .q(q), .e(e), .y(yq), .fault(fault));
    wire [21:0] tg;
    ot_hdc_delay #(.W(22), .D(LAT - 2)) u_tg (.clk(clk), .rst_n(rst_n), .d({ob_q, t_q}), .q(tg));
    reg [13:0] a_b, aq, ae; reg [3:0] aw;
    always @(posedge clk) begin
        a_b <= tg[21:8] + tg[7:0] * RQ;
        aq <= a_b + (cb_q >> 1);
        ae <= a_b + N / 64;
        aw <= cb_q >> 1;
    end
`ifndef SYNTHESIS
    wire [LAT:0] vchk;
    ot_hdc_vline #(.D(LAT)) u_vc (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vchk));
    always @(posedge clk) if (rst_n && vo !== vchk[LAT]) $fatal(1, "ot_s81_su_qnq: block latency is not %0d", LAT);
`endif
    reg d1v, d2v; reg [255:0] d1q, d2q; reg [9:0] d1e, d2e; reg [13:0] d1a, d2a, d1x, d2x; reg [3:0] d1w, d2w;
    always @(posedge clk) begin
        nx_o_q <= q; nx_o_e <= e;
        d1q <= q; d1e <= e; d1a <= aq; d1x <= ae; d1w <= aw;
        d2q <= d1q; d2e <= d1e; d2a <= d1a; d2x <= d1x; d2w <= d1w;
    end
    always @(posedge clk) begin
        if (!cb_q[0]) begin
            o_a <= d2a; o_m <= 16'hFFFF; o_d <= {nq_q, d2q};
        end else begin
            o_a <= d2x; o_m <= 16'd1 << d2w; o_d <= {16{6'd0, d2e, 6'd0, ne_q}};
        end
    end
    reg fs;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            nx_o_v <= 0; d1v <= 0; d2v <= 0; o_v <= 0; fs <= 0;
            o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0;
        end else begin
            nx_o_v <= vo; d1v <= vo; d2v <= d1v; o_v <= d2v; fs <= fs | fault;
            o_fu <= fs; o_fo <= o_fo | (d2v && !nv_q); o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= 8'd0;
        end
    end
endmodule
