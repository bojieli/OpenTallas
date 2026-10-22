`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81 SU SwiGLU function, rate-matched and split (el1011-s81su-sw, 2026-10-12; PHYSICAL SPEC SW v3).
// Replaces the NSW = SW_W / 128 SW lane tiles of ot_s81_su_tile (128 lanes x ~21k flops each = ~2.7M flops on one root)
// by a TAP at the down-spine stop, NSE = SW_W / LPE position-independent LANE ENGINES (one SwiGLU lane pipeline each,
// time-shared over LPE lanes) and NSQ act-quant engines = the QB master ot_s81_su_qbe (unchanged), each <= 15k sinks.
// Rate match: a SW beat is RPB = 2 RSW rows (RSW = SW_W / 16 g rows, then the RSW u rows of the same lanes); the down
//   spine brings S_RD rows a cycle, so a beat takes >= RPB / S_RD = LPE cycles and NSE = SW_W / LPE lanes a cycle keep
//   the spine rate (full: 128 engines x 8 lanes; reduced S_RD 2: 16 x 4).
// Passes: L = 2 NSQ rows (= NSQ quant blocks); pass P of a half is rows [P L, P L + L) of that half (NPS = RSW / L).
//   The tap releases a pass in one cycle (S_RD == L: a spine cycle IS a pass; S_RD < L: assembled as ot_s81_su_qbt).
//   Lane engine (P, r, c) owns lanes 16 (P L + r) + LPE c .. + LPE - 1: it holds its g chunk from the g pass and starts at
//   its u pass (g, u, the beat's route weight w = descriptor word 5 + beat, lim = descriptor word 3, tag {beat, P}).
// Values: every lane is ot_dsrom_su_swiglu_lane's chain (PRE min / clip, exp_f12, qadd, fdiv_f12, qmul, qmul) on the
//   same operands in the same order; its delay lines are SRAM wait lines (cycle-exact).  The BF16 rounding (the old
//   quantiser-input front) is in the engine: only the high 16 b travel ({hi, 16'h0} at the quant engine).  Blocks are
//   independent, so ot_s81_su_qbe (QB_NB = SW_W / 32: the same 49-row beat layout) writes exactly the old rows.
// Chains: the NPS engines of one (r, c) form a registered chain P = NPS-1 -> 0 -> quant engine r / 2 (half r % 2); pass P
//   reaches the chain head P cycles after its own completion, and passes complete in order, so no two values meet.
// ---------------------------------------------------------------------------------------------------------------------

// SRAM wait line (ot_sram_dline on the 128 x 256 macro): q(t) = d(t - D), D in [3, 128], W <= 256 a macro
module ot_s81_su_dl128 #(
    parameter integer W = 108,
    parameter integer D = 80
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer NM = (W + 255) / 256;
`ifndef SYNTHESIS
    initial if (D < 3 || D > 128) $fatal(1, "ot_s81_su_dl128: D must be in [3, 128]");
`endif
    reg [6:0] wp, rp;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 7'd0; rp <= 7'd0 - (D - 2); end
        else begin wp <= wp + 7'd1; rp <= rp + 7'd1; end
    wire [NM*256-1:0] wd = {{(NM*256-W){1'b0}}, d};
    wire [NM*256-1:0] rq;
    reg  [NM*256-1:0] cq;                                  // capture flops at the macro outputs
    always @(posedge clk) cq <= rq;
    assign q = cq[W-1:0];
    genvar m;
    generate for (m = 0; m < NM; m = m + 1) begin : g_m
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(1'b1), .r_addr_in(rp), .rd_out(rq[256*m +: 256]),
            .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(wd[256*m +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
endmodule

// one SwiGLU lane (ot_dsrom_su_swiglu_lane, ROUTED 1, IREG 0, ESUM 0) with its g / u / w delay lines in SRAM and a tag
// carried to the result; fault = the units' raw flags (the engine keeps them sticky)
module ot_s81_su_swl #(
    parameter integer LM = 5, LA = 4, TW = 12
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [31:0]   g, u, w, lim,
    input  wire [TW-1:0] t,
    output wire [31:0]   a,
    output wire [TW-1:0] ta,
    output wire          vo,
    output wire          fault
);
    localparam integer D_EXP = 7 * LM + 6 * LA + 12 + 5;
    localparam integer D_DIV = 21;
    localparam integer KS = 1;
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    // PRE: g' = min(g, lim), u' = clip(u, -lim, lim)
    wire [31:0] k_lim = okey(lim);
    wire [31:0] c_lo = {1'b1, lim[30:0]};
    wire le_g, c_ge_lo, c_le_hi, c_lohi;
    ot_hdc_kge #(.W(32), .K(KS)) u_leg (.a(k_lim), .b(okey(g)), .ge(le_g));
    ot_hdc_kge #(.W(32), .K(KS)) u_cgl (.a(okey(u)), .b(okey(c_lo)), .ge(c_ge_lo));
    ot_hdc_kge #(.W(32), .K(KS)) u_clh (.a(k_lim), .b(okey(u)), .ge(c_le_hi));
    ot_hdc_kge #(.W(32), .K(KS)) u_clo (.a(k_lim), .b(okey(c_lo)), .ge(c_lohi));
    reg [31:0] p_g, p_u, p_w; reg [TW-1:0] p_t;
    reg        p_v;
    always @(posedge clk or negedge rst_n) if (!rst_n) p_v <= 1'b0; else p_v <= v;
    always @(posedge clk) begin
        p_g <= le_g ? g : lim;
        p_u <= c_ge_lo ? (c_le_hi ? u : lim) : (c_lohi ? c_lo : lim);
        p_w <= w; p_t <= t;
    end
    // wait lines: {t, w, u, g} D_EXP + LA -> g (the divider's dividend); {t, w, u} D_DIV more -> u; w LM more
    wire [31:0] g_d, u_d, w_d, uA, wA, wB; wire [TW-1:0] tA, tB;
    ot_s81_su_dl128 #(.W(96 + TW), .D(D_EXP + LA)) u_la (.clk(clk), .rst_n(rst_n), .d({p_t, p_w, p_u, p_g}),
                                                        .q({tA, wA, uA, g_d}));
    ot_s81_su_dl128 #(.W(64 + TW), .D(D_DIV)) u_lb (.clk(clk), .rst_n(rst_n), .d({tA, wA, uA}), .q({tB, wB, u_d}));
    ot_hdc_delay #(.W(32), .D(LM)) u_wd (.clk(clk), .rst_n(rst_n), .d(wB), .q(w_d));
    ot_hdc_delay #(.W(TW), .D(2 * LM)) u_td (.clk(clk), .rst_n(rst_n), .d(tB), .q(ta));
    // s = g' / (exp(-g') + 1)
    wire [31:0] y_exp, den, y_div;
    wire f_e, f_den, f_div, f_m1, f_m2;
    wire [D_EXP:0] ve;
    ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk), .rst_n(rst_n), .v(p_v), .vd(ve));
    ot_dsrom_exp_f12 #(.LM(LM), .LA(LA), .ASUM(0)) u_exp (.clk(clk), .rst_n(rst_n), .v(p_v), .x({~p_g[31], p_g[30:0]}),
                                                     .y(y_exp), .vo(), .fault(f_e));
    ot_hdc_qadd_lat #(.KEEP(KS), .LAT(LA)) u_den (clk, rst_n, ve[D_EXP], y_exp, 32'h3F800000, den, f_den);
    wire [LA:0] vdn;
    ot_hdc_vline #(.D(LA)) u_vdn (.clk(clk), .rst_n(rst_n), .v(ve[D_EXP]), .vd(vdn));
    wire v_div;
    ot_dsrom_fdiv_f12 u_div (.clk(clk), .rst_n(rst_n), .v(vdn[LA]), .a(g_d), .b(den), .y(y_div), .vo(v_div),
                            .fault(f_div));
    // t = s * u', a = t * w
    wire [31:0] tt;
    ot_hdc_qmul_lat #(LM) u_m1 (clk, rst_n, v_div, y_div, u_d, tt, f_m1);
    wire [LM:0] vm1, vm2;
    ot_hdc_vline #(.D(LM)) u_vm1 (.clk(clk), .rst_n(rst_n), .v(v_div), .vd(vm1));
    ot_hdc_qmul_lat #(LM) u_m2 (clk, rst_n, vm1[LM], tt, w_d, a, f_m2);
    ot_hdc_vline #(.D(LM)) u_vm2 (.clk(clk), .rst_n(rst_n), .v(vm1[LM]), .vd(vm2));
    assign vo = vm2[LM];
    assign fault = f_e | f_den | f_div | f_m1 | f_m2;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// LANE ENGINE: LPE lanes on one lane pipeline (one element a cycle).  Pins: its g / u chunk (32 LPE b) with the pass's
// one-hot g / u valid, the pass's {w, lim, tag}; the chain in (from pass P + 1) and out (to pass P - 1 / the quant
// engine).  No configuration: the parent wires the chunk and the pass valids.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_swe #(
    parameter integer LPE = 8, LM = 5, LA = 4
) (
    input  wire              clk,
    input  wire              rst_in,
    input  wire              i_gv, i_uv,
    input  wire [32*LPE-1:0] i_d,
    input  wire [11:0]       i_t,
    input  wire [31:0]       i_w, i_lim,
    input  wire              c_iv,
    input  wire [16*LPE-1:0] c_id,
    input  wire [11:0]       c_it,
    input  wire              c_if,
    output reg               c_ov,
    output reg  [16*LPE-1:0] c_od,
    output reg  [11:0]       c_ot,
    output reg               c_of
);
    localparam integer LB = (LPE > 1) ? $clog2(LPE) : 1;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg gv_q, uv_q; reg [32*LPE-1:0] d_q; reg [11:0] t_q; reg [31:0] w_q, l_q;
    always @(posedge clk) begin d_q <= i_d; t_q <= i_t; w_q <= i_w; l_q <= i_lim; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin gv_q <= 1'b0; uv_q <= 1'b0; end
                                           else begin gv_q <= i_gv; uv_q <= i_uv; end
    // g chunk held from its pass; at the u pass both chunks load the serialiser (shift registers: element 0 first)
    reg [32*LPE-1:0] gh, sg, su; reg [31:0] sw, sl; reg [11:0] st;
    reg act; reg [LB-1:0] cnt; reg ovr;
    always @(posedge clk) begin
        if (gv_q) gh <= d_q;
        if (uv_q) begin sg <= gh; su <= d_q; sw <= w_q; sl <= l_q; st <= t_q; end
        else begin sg <= sg >> 32; su <= su >> 32; end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin act <= 1'b0; cnt <= 0; ovr <= 1'b0; end
        else begin
            if (uv_q) begin act <= 1'b1; cnt <= 0; end
            else if (act) begin cnt <= cnt + 1'b1; if (cnt == LPE - 1) act <= 1'b0; end
            if (uv_q && act && cnt != LPE - 1) ovr <= 1'b1;            // a u pass before the group left: overrun
        end
    end
    wire [31:0] a; wire [11:0] ta; wire vo, lf;
    ot_s81_su_swl #(.LM(LM), .LA(LA), .TW(12)) u_l (.clk(clk), .rst_n(rst_n), .v(act), .g(sg[31:0]), .u(su[31:0]),
        .w(sw), .lim(sl), .t(st), .a(a), .ta(ta), .vo(vo), .fault(lf));
    // BF16 round-to-nearest-even (the old quantiser-input front): the high half only
    wire [31:0] ab;
    ot_dsrom_su_bf16rnd u_r (.x(a), .y(ab));
    // deserialiser: element j -> bits 16 j; the group completes on its LPE-th result
    reg [LB-1:0] dc; reg [16*LPE-1:0] ds;
    wire last = vo && dc == LPE - 1;
    wire [16*LPE-1:0] own;
    genvar j;
    generate for (j = 0; j < LPE; j = j + 1) begin : g_o
        if (j == LPE - 1) begin : g_l
            assign own[16 * j +: 16] = ab[31:16];
        end else begin : g_e
            assign own[16 * j +: 16] = ds[16 * j +: 16];
        end
    end endgenerate
    always @(posedge clk) begin : dsr
        integer k;
        for (k = 0; k < LPE; k = k + 1) if (vo && dc == k) ds[16 * k +: 16] <= ab[31:16];
        c_od <= last ? own : c_id;
        c_ot <= last ? ta : c_it;
    end
    reg fs;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin dc <= 0; fs <= 1'b0; c_ov <= 1'b0; c_of <= 1'b0; end
        else begin
            if (vo) dc <= (dc == LPE - 1) ? {LB{1'b0}} : dc + 1'b1;
            fs <= fs | lf | ovr | (last && c_iv);                      // unit faults, overrun, a chain collision
            c_ov <= last | c_iv;
            c_of <= fs | c_if;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// TAP: the down-spine stop of the SW function.  Releases one pass (L rows) a cycle at most to the lane engines: the
// position bus e_d (row r of the pass at 512 r), the pass's one-hot g / u valid, tag {beat, P}, the beat's route weight,
// lim and the job's obase (to the quant engines).  Lane faults (chain heads) come back on i_f.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_swt #(
    parameter integer SW_W = 1024, S_RD = 16,
    parameter integer NSQ = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer NCH = 32
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire                   dn_fp4_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    input  wire [NCH-1:0]         i_f,
    output reg  [2*NSQ*512-1:0]   e_d,
    output reg  [((SW_W/32)/NSQ)-1:0] e_gv, e_uv,
    output reg  [11:0]            e_t,
    output reg  [31:0]            e_w, e_lim,
    output reg  [13:0]            e_ob,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer L = 2 * NSQ, RSW = SW_W / 16, RPB = 2 * RSW, NPS = RSW / L;
    localparam integer LL = $clog2(L), LR = $clog2(RPB);
    localparam integer NWB = 11;                                  // route weights in the descriptor (words 5..15)
    localparam [3:0] K_SW = 3;
`ifndef SYNTHESIS
    initial begin
        if ((1 << LL) != L || (1 << LR) != RPB) $fatal(1, "ot_s81_su_swt: L and RPB powers of two");
        if (S_RD > L || RSW % L || NPS > 4) $fatal(1, "ot_s81_su_swt: S_RD <= L, RSW a multiple of L, <= 4 passes");
    end
`endif
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // lane faults (relayed chain heads): sticky
    reg [NCH-1:0] f_q; reg fs;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin f_q <= 0; fs <= 1'b0; end
                                           else begin f_q <= i_f; fs <= fs | (|f_q); end
    // descriptor words: obase (bits 13:0), lim (word 3), route weights (words 5..15); datapath: no reset
    reg [32*NWB-1:0] wv;
    function automatic [31:0] wsel(input [9:0] b);
        integer k;
        begin
            wsel = 32'd0;
            for (k = 0; k < NWB; k = k + 1) if (b == k) wsel = wv[32 * k +: 32];
        end
    endfunction
    genvar gp;
    generate if (S_RD == L) begin : g_al
        // RATE-ALIGNED (full): descriptor alone in slot 0 of its cycle, then operand cycles S_RD-full from slot 0
        // (ot_s81_su_hctl, as the QB tap): a spine cycle IS a pass; the data takes one register.
        reg mine, rnz; reg [7:0] jid; reg [15:0] rcnt, rinc;
        reg dq_m, dq_desc; reg [S_RD-1:0] dq_v;
        reg [9:0] bq; reg bqv;
        wire v0   = dn_v_i[0] && !dn_st_i;
        wire desc = mine && v0 && !rnz;
        wire opc  = mine && v0 && rnz;
        wire [15:0] ix0 = rcnt - 16'd1;
        wire [9:0]  bt  = ix0 >> LR;                                // the beat (a 10-bit select of ix0 runs past bit 15)
        wire        isu = ix0[LR - 1];
        wire [15:0] pp  = (ix0 >> LL) % NPS;
        always @(posedge clk) begin : dreg
            integer k;
            e_d <= dn_d_i;
            e_t <= {bt, pp[1:0]};
            if (desc) begin e_ob <= dn_d_i[13:0]; e_lim <= dn_d_i[96 +: 32]; wv <= dn_d_i[160 +: 32 * NWB]; end
            e_w <= wsel(bt);
        end
        always @(posedge clk or negedge rst_n) begin : creg
            integer k;
            if (!rst_n) begin
                mine <= 1'b0; rnz <= 1'b0; jid <= 8'd0; rcnt <= 16'd0; rinc <= 16'd0; e_gv <= 0; e_uv <= 0;
                dq_m <= 1'b0; dq_desc <= 1'b0; dq_v <= 0;
                o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0;
            end else begin
                if (dn_st_i) begin mine <= (dn_kind_i == K_SW); jid <= dn_jid_i; rcnt <= 16'd0; rnz <= 1'b0; end
                else if (desc) begin rcnt <= 16'd1; rinc <= 16'd1 + S_RD; rnz <= 1'b1; end
                else if (opc) begin rcnt <= rinc; rinc <= rinc + S_RD; end
                for (k = 0; k < NPS; k = k + 1) begin
                    e_gv[k] <= opc && !isu && pp == k;
                    e_uv[k] <= opc && isu && pp == k;
                end
                dq_m <= mine && !dn_st_i; dq_desc <= desc; dq_v <= dn_v_i;
                o_fu <= fs; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= jid;
                o_fo <= o_fo | (dq_m && (|dq_v) && (dq_desc ? (|dq_v[S_RD-1:1]) : !(&dq_v)));
            end
        end
    end else begin : g_asm
        // ASSEMBLING (S_RD < L, reduced only): a pass spans L / S_RD spine cycles; rotation + hold as ot_s81_su_qbt
        reg dq_st; reg [3:0] dq_kind; reg [7:0] dq_jid; reg [S_RD-1:0] dq_v; reg [S_RD*512-1:0] dq_d;
        always @(posedge clk) begin dq_kind <= dn_kind_i; dq_jid <= dn_jid_i; dq_d <= dn_d_i; end
        always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; end
                                               else begin dq_st <= dn_st_i; dq_v <= dn_v_i; end
        reg mine; reg [7:0] jid; reg [15:0] rcnt;
        always @(posedge clk or negedge rst_n) begin : jb
            integer i; reg [15:0] c;
            if (!rst_n) begin mine <= 1'b0; jid <= 8'd0; rcnt <= 16'd0; end
            else if (dq_st) begin mine <= (dq_kind == K_SW); jid <= dq_jid; rcnt <= 16'd0; end
            else begin
                c = rcnt;
                for (i = 0; i < S_RD; i = i + 1) if (dq_v[i]) c = c + 16'd1;
                rcnt <= c;
            end
        end
        wire prm = mine && dq_v[0] && rcnt == 16'd0;
        always @(posedge clk) if (prm) begin e_ob <= dq_d[13:0]; e_lim <= dq_d[96 +: 32]; wv <= dq_d[160 +: 32 * NWB]; end
        // per slot: operand-row valid and tag {beat, u, pass}
        localparam integer TB = 13, RB = 512 + TB + 1;
        reg [L-1:0] sv; reg [L*512-1:0] sd; reg [L*TB-1:0] stg;
        always @(*) begin : sl
            integer s; reg [15:0] ix, pp; reg [9:0] bx;
            sv = 0; sd = 0; stg = 0;
            for (s = 0; s < S_RD; s = s + 1) begin
                ix = rcnt + s - 16'd1;
                sv[s] = mine && dq_v[s] && (rcnt != 16'd0 || s != 0);
                sd[512 * s +: 512] = dq_d[512 * s +: 512];
                pp = (ix >> LL) % NPS;
                bx = ix >> LR;
                stg[TB * s +: TB] = {bx, ix[LR - 1], pp[1:0]};
            end
        end
        wire [LL-1:0] off = rcnt[LL-1:0] - 1'b1;
        reg [L*RB-1:0] rv [0:LL];
        always @(*) begin : rot
            integer s, k;
            for (s = 0; s < L; s = s + 1) rv[0][RB * s +: RB] = {sv[s], stg[TB * s +: TB], sd[512 * s +: 512]};
            for (k = 0; k < LL; k = k + 1)
                for (s = 0; s < L; s = s + 1)
                    rv[k + 1][RB * s +: RB] = off[k] ? rv[k][RB * ((s - (1 << k) + L) % L) +: RB] : rv[k][RB * s +: RB];
        end
        wire [L-1:0] iv, same;
        wire [TB-1:0] tl = rv[LL][RB * (L - 1) + 512 +: TB];
        wire          done = iv[L - 1];
        for (gp = 0; gp < L; gp = gp + 1) begin : g_as
            assign iv[gp] = rv[LL][RB * gp + 512 + TB];
            assign same[gp] = iv[gp] && rv[LL][RB * gp + 512 +: TB] == tl;
        end
        reg [L-1:0] hv; reg [L*512-1:0] hd;
        always @(posedge clk) begin : oreg
            integer j;
            for (j = 0; j < L; j = j + 1) begin
                e_d[512 * j +: 512] <= same[j] ? rv[LL][RB * j +: 512] : hd[512 * j +: 512];
                if (iv[j] && !(done && same[j])) hd[512 * j +: 512] <= rv[LL][RB * j +: 512];
            end
            e_t <= {tl[12:3], tl[1:0]};
            e_w <= wsel(tl[12:3]);
        end
        always @(posedge clk or negedge rst_n) begin : vreg
            integer j;
            if (!rst_n) begin e_gv <= 0; e_uv <= 0; hv <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; end
            else begin
                for (j = 0; j < L; j = j + 1) begin
                    if (iv[j] && !(done && same[j])) hv[j] <= 1'b1;
                    else if (done) hv[j] <= 1'b0;
                end
                for (j = 0; j < NPS; j = j + 1) begin
                    e_gv[j] <= done && !tl[2] && tl[1:0] == j;
                    e_uv[j] <= done && tl[2] && tl[1:0] == j;
                end
                o_fu <= fs; o_fo <= o_fo | (done && !(&(same | hv))); o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0;
                o_rjid <= jid;
            end
        end
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// TAP, SPLIT (el1013-s81su-qual, structural change after swt v1 FLOORPLAN_MARGIN / v2 EARLY_FAIL_DRC): the rate-aligned
// tap (S_RD == 2 NSQ, the full configuration) as TWO half-taps, each a kvt-shaped column with its own clock root:
//   ot_s81_su_swtl  the low S_RD / 2 slots (slot 0 = the descriptor row) + the whole control (job, pass counters, tag,
//                   route weight, lim, obase, status, the lane-fault relay);
//   ot_s81_su_swth  the high S_RD / 2 slots: a pure two-register data stage.
// REGISTER AT THE PIN (owner 10-13): every input pin feeds exactly one flop (q_*) and nothing else, every output is a
// flop.  The data takes two registers (pin flop, output flop), so the pair is ONE CYCLE DEEPER than ot_s81_su_swt's
// g_al branch and otherwise identical cycle for cycle (bench tb_s81_su_swt_split: lockstep against ot_s81_su_swt).
// ot_s81_su_swt stays as the assembling tap of the reduced shapes (S_RD < L) and as the lockstep reference.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_swtl #(
    parameter integer SW_W = 1024, S_RD = 16,
    parameter integer NSQ = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer NCH = 32,
    parameter integer MUT = 0                      // bench negative control: 1 = the pass tag one pass early
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire                   dn_fp4_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*256-1:0]    dn_d_i,         // slots 0 .. S_RD / 2 - 1
    input  wire [NCH-1:0]         i_f,
    output reg  [S_RD*256-1:0]    e_d,            // pass rows 0 .. NSQ - 1
    output reg  [((SW_W/32)/NSQ)-1:0] e_gv, e_uv,
    output reg  [11:0]            e_t,
    output reg  [31:0]            e_w, e_lim,
    output reg  [13:0]            e_ob,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer L = 2 * NSQ, RSW = SW_W / 16, RPB = 2 * RSW, NPS = RSW / L;
    localparam integer LL = $clog2(L), LR = $clog2(RPB);
    localparam integer NWB = 11;                                  // route weights in the descriptor (words 5..15)
    localparam [3:0] K_SW = 3;
`ifndef SYNTHESIS
    initial begin
        if ((1 << LL) != L || (1 << LR) != RPB) $fatal(1, "ot_s81_su_swtl: L and RPB powers of two");
        if (S_RD != L || RSW % L || NPS > 4) $fatal(1, "ot_s81_su_swtl: S_RD == L (rate-aligned), RSW a multiple of L, <= 4 passes");
    end
`endif
    // reset relay: rr1 releases the pin flops, rr2 (one cycle later) the tap state, so the tap is ot_s81_su_swt delayed
    // by exactly one cycle from the first cycle out of reset
    reg rr0, rr1, rr2;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; rr2 <= 1'b0; end
                                            else begin rr0 <= 1'b1; rr1 <= rr0; rr2 <= rr1; end
    wire rst_p = rr1, rst_n = rr2;
    // pin flops
    reg q_st; reg [3:0] q_kind; reg [7:0] q_jid; reg [S_RD-1:0] q_v; reg [S_RD*256-1:0] q_d;
    always @(posedge clk) begin q_kind <= dn_kind_i; q_jid <= dn_jid_i; q_d <= dn_d_i; end
    always @(posedge clk or negedge rst_p) if (!rst_p) begin q_st <= 1'b0; q_v <= 0; end
                                           else begin q_st <= dn_st_i; q_v <= dn_v_i; end
    // lane faults (relayed chain heads): sticky
    reg [NCH-1:0] f_q; reg fs;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin f_q <= 0; fs <= 1'b0; end
                                           else begin f_q <= i_f; fs <= fs | (|f_q); end
    // descriptor words: obase (bits 13:0), lim (word 3), route weights (words 5..15); datapath: no reset
    reg [32*NWB-1:0] wv;
    function automatic [31:0] wsel(input [9:0] b);
        integer k;
        begin
            wsel = 32'd0;
            for (k = 0; k < NWB; k = k + 1) if (b == k) wsel = wv[32 * k +: 32];
        end
    endfunction
    reg mine, rnz; reg [7:0] jid; reg [15:0] rcnt, rinc;
    reg dq_m, dq_desc; reg [S_RD-1:0] dq_v;
    wire v0   = q_v[0] && !q_st;
    wire desc = mine && v0 && !rnz;
    wire opc  = mine && v0 && rnz;
    wire [15:0] ix0 = rcnt - 16'd1;
    wire [9:0]  bt  = ix0 >> LR;                                // the beat
    wire        isu = ix0[LR - 1];
    wire [15:0] pp  = (ix0 >> LL) % NPS;
    wire [1:0]  ppm = (MUT == 1) ? pp[1:0] + 2'd1 : pp[1:0];
    always @(posedge clk) begin : dreg
        e_d <= q_d;
        e_t <= {bt, ppm};
        if (desc) begin e_ob <= q_d[13:0]; e_lim <= q_d[96 +: 32]; wv <= q_d[160 +: 32 * NWB]; end
        e_w <= wsel(bt);
    end
    always @(posedge clk or negedge rst_n) begin : creg
        integer k;
        if (!rst_n) begin
            mine <= 1'b0; rnz <= 1'b0; jid <= 8'd0; rcnt <= 16'd0; rinc <= 16'd0; e_gv <= 0; e_uv <= 0;
            dq_m <= 1'b0; dq_desc <= 1'b0; dq_v <= 0;
            o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0;
        end else begin
            if (q_st) begin mine <= (q_kind == K_SW); jid <= q_jid; rcnt <= 16'd0; rnz <= 1'b0; end
            else if (desc) begin rcnt <= 16'd1; rinc <= 16'd1 + S_RD; rnz <= 1'b1; end
            else if (opc) begin rcnt <= rinc; rinc <= rinc + S_RD; end
            for (k = 0; k < NPS; k = k + 1) begin
                e_gv[k] <= opc && !isu && pp == k;
                e_uv[k] <= opc && isu && pp == k;
            end
            dq_m <= mine && !q_st; dq_desc <= desc; dq_v <= q_v;
            o_fu <= fs; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= jid;
            o_fo <= o_fo | (dq_m && (|dq_v) && (dq_desc ? (|dq_v[S_RD-1:1]) : !(&dq_v)));
        end
    end
endmodule

module ot_s81_su_swth #(
    parameter integer S_RD = 16,
    parameter integer MUT = 0                      // bench negative control: 1 = one register only
) (
    input  wire                   clk,
    input  wire [S_RD*256-1:0]    dn_d_i,         // slots S_RD / 2 .. S_RD - 1
    output reg  [S_RD*256-1:0]    e_d             // pass rows NSQ .. 2 NSQ - 1
);
    reg [S_RD*256-1:0] q_d;                        // pin flop; datapath: no reset
    always @(posedge clk) begin q_d <= dn_d_i; e_d <= (MUT == 1) ? dn_d_i : q_d; end
endmodule
