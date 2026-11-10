`timescale 1ns/1ps
// DIE-S81-85 svc census 11-10 (COORD loopgap-153x-1109): census-safe copy of ot_s81_su_smr
// (rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv, unchanged without the define), the box body under
// -DOT_S81_SVC_CS (the box keeps its name).  Same ports, same cycles.  Only drivers above 64 load pins change:
//   - rst_n: NRN kept copies of the reset relay's second flop (each = rr1), one per load group;
//   - lt (the tap level, 3 bits into a 7-way x 33-bit select): two kept one-hot registers, loaded on cv from the
//     same pin flop (configuration contract: lt <= LTMAX, as the original's tl_v / tl_x range requires);
//   - the max tree's last valid and the den line's last stage: kept x2 (o_nmb / o_den word halves);
//   - level hold: held loads on every edge where par is low (kept par copies per half) -- held is read only by
//     comb = vi && par, and par rises only on an edge with vi && !par, which is the edge the original loads it;
//   - the adders: ot_s81_svc_qadd_lat_cs (KEEP 1, LAT LA; = ot_dsrom_su_softmax_add ADD6 0, yosys EQ vs rtl/hdc).
// Lock-step bench against the original: tools/s81_dv/svc_cs/tb_smr_cs.sv.
module ot_s81_su_smr_cs #(
    parameter integer LPH = 16, LA = 4, LTMAX = 6
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire               i_cv,
    input  wire [2:0]         i_lt,
    input  wire               i_mxv,
    input  wire [LPH*32-1:0]  i_mx,
    input  wire               i_skv,
    input  wire [31:0]        i_sk,
    input  wire               i_vv,
    input  wire               i_vl,
    input  wire [31:0]        i_vs,
    output reg                o_mv,
    output reg  [31:0]        o_nmb,
    output reg                o_dv,
    output reg  [31:0]        o_den
);
    localparam integer LH = $clog2(LPH);
    // reset copies: 0 control + max tree, 1.. 2 per time level (lines / par, adder), then 2 (den line, u_d)
    localparam integer NRN = 1 + 2 * LTMAX + 2;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    (* keep = 1 *) reg [NRN-1:0] rnk;
    always @(posedge clk or negedge rst_in) if (!rst_in) rnk <= {NRN{1'b0}}; else rnk <= {NRN{rr0}};
    wire rst_n = rnk[0];
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    reg              cv, mxv, skv, vv, vl;
    reg [2:0]        lt_p;
    reg [LPH*32-1:0] mx;
    reg [31:0]       sk, vs, sk_hold;
    always @(posedge clk) begin lt_p <= i_lt; mx <= i_mx; sk <= i_sk; vs <= i_vs; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 0; mxv <= 0; skv <= 0; vv <= 0; vl <= 0; end
        else begin cv <= i_cv; mxv <= i_mxv; skv <= i_skv; vv <= i_vv; vl <= i_vv && i_vl; end
    // lt one-hot: [0] tap + rs_x[15:0], [1] rs_x[31:16]
    (* keep = 1 *) reg [LTMAX:0] loh0, loh1;
    always @(posedge clk) if (cv) begin loh0 <= {{LTMAX{1'b0}}, 1'b1} << lt_p; loh1 <= {{LTMAX{1'b0}}, 1'b1} << lt_p; end
    always @(posedge clk) if (skv) sk_hold <= sk;
    genvar k, l;
    generate for (k = 0; k <= LH; k = k + 1) begin : g_mt
        wire [(LPH >> k)*32-1:0] x;
        wire                     v;
        if (k == 0) begin : g_0
            assign x = mx;
            assign v = mxv;
        end else begin : g_n
            reg [(LPH >> k)*32-1:0] xr;
            reg                     vr;
            for (l = 0; l < (LPH >> k); l = l + 1) begin : g_l
                wire [31:0] xa = g_mt[k-1].x[64*l +: 32], xb = g_mt[k-1].x[64*l + 32 +: 32];
                wire ge;
                ot_hdc_kge #(.W(32), .K(1)) u_ge (.a(okey(xa)), .b(okey(xb)), .ge(ge));
                always @(posedge clk) xr[32*l +: 32] <= ge ? xa : xb;
            end
            always @(posedge clk or negedge rst_n) if (!rst_n) vr <= 1'b0; else vr <= g_mt[k-1].v;
            assign x = xr;
            assign v = vr;
        end
    end endgenerate
    // the last level's valid, kept x2: [0] o_mv + o_nmb[15:0], [1] o_nmb[31:16]
    (* keep = 1 *) reg [1:0] mvk;
    always @(posedge clk or negedge rst_n) if (!rst_n) mvk <= 2'b0; else mvk <= {2{g_mt[LH-1].v}};
    always @(posedge clk or negedge rst_n) if (!rst_n) o_mv <= 1'b0; else o_mv <= mvk[0];
    always @(posedge clk) begin
        if (mvk[0]) o_nmb[15:0] <= g_mt[LH].x[15:0];
        if (mvk[1]) o_nmb[31:16] <= {~g_mt[LH].x[31], g_mt[LH].x[30:16]};
    end
    wire [(LTMAX+1)*32-1:0] tl_x;
    wire [LTMAX:0]          tl_v, tl_l;
    assign tl_x[31:0] = vs;
    assign tl_v[0] = vv;
    assign tl_l[0] = vl;
    generate for (k = 0; k < LTMAX; k = k + 1) begin : g_tl
        wire [31:0] xi = tl_x[k*32 +: 32];
        wire vi = tl_v[k], li = tl_l[k];
        wire rl = rnk[1 + 2*k];
        reg  [31:0] held;
        reg         par;
        (* keep = 1 *) reg [1:0] park;                      // par copies: held[15:0] / held[31:16] loads
        wire comb = vi && par;
        wire pass = vi && !par && li;
        wire [LA:0] ov, ol, op;
        ot_hdc_vline #(.D(LA)) u_ov (.clk(clk), .rst_n(rl), .v(comb || pass), .vd(ov));
        ot_hdc_vline #(.D(LA)) u_ol (.clk(clk), .rst_n(rl), .v((comb || pass) && li), .vd(ol));
        ot_hdc_vline #(.D(LA)) u_op (.clk(clk), .rst_n(rl), .v(pass), .vd(op));
        wire [31:0] sum, pd;
        wire fa;
        ot_s81_svc_qadd_lat_cs #(.KEEP(1), .LAT(LA)) u_a (clk, rnk[2 + 2*k], comb, held, xi, sum, fa);
        ot_hdc_delay #(.W(32), .D(LA)) u_pd (.clk(clk), .rst_n(rl), .d(xi), .q(pd));
        reg  [31:0] xo;
        reg         vo_r, lo_r;
        always @(posedge clk) xo <= op[LA] ? pd : sum;
        always @(posedge clk or negedge rl) begin
            if (!rl) begin vo_r <= 1'b0; lo_r <= 1'b0; end
            else begin vo_r <= ov[LA]; lo_r <= ol[LA]; end
        end
        assign tl_x[(k+1)*32 +: 32] = xo;
        assign tl_v[k+1] = vo_r;
        assign tl_l[k+1] = lo_r;
        always @(posedge clk or negedge rl) begin
            if (!rl) begin par <= 1'b0; park <= 2'b0; end
            else if (vi) begin par <= li ? 1'b0 : ~par; park <= {2{li ? 1'b0 : ~par}}; end
        end
        always @(posedge clk) begin
            if (!park[0]) held[15:0] <= xi[15:0];
            if (!park[1]) held[31:16] <= xi[31:16];
        end
    end endgenerate
    // tap at level lt (one-hot)
    reg  [31:0] rs_x;
    reg         rs_v;
    reg  [31:0] tx;
    reg         tap;
    integer ti;
    always @* begin
        tx = 32'd0; tap = 1'b0;
        for (ti = 0; ti <= LTMAX; ti = ti + 1) begin
            tap = tap | (loh0[ti] & tl_v[ti] & tl_l[ti]);
            tx[15:0] = tx[15:0] | ({16{loh0[ti]}} & tl_x[ti*32 +: 16]);
            tx[31:16] = tx[31:16] | ({16{loh1[ti]}} & tl_x[ti*32 + 16 +: 16]);
        end
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) rs_v <= 1'b0; else rs_v <= tap;
    always @(posedge clk) if (tap) rs_x <= tx;
    // den line: last stage kept x2 ([0] o_dv + o_den[15:0], [1] o_den[31:16])
    wire rd = rnk[1 + 2*LTMAX];
    wire [LA-1:0] dnl;
    ot_hdc_vline #(.D(LA - 1)) u_dnv (.clk(clk), .rst_n(rd), .v(rs_v), .vd(dnl));
    (* keep = 1 *) reg [1:0] dnk;
    always @(posedge clk or negedge rd) if (!rd) dnk <= 2'b0; else dnk <= {2{dnl[LA-1]}};
    wire [31:0] den_r;
    wire fd;
    ot_s81_svc_qadd_lat_cs #(.KEEP(1), .LAT(LA)) u_d (clk, rnk[2 + 2*LTMAX], rs_v, rs_x, sk_hold, den_r, fd);
    always @(posedge clk or negedge rd) if (!rd) o_dv <= 1'b0; else o_dv <= dnk[0];
    always @(posedge clk) begin
        if (dnk[0]) o_den[15:0] <= den_r[15:0];
        if (dnk[1]) o_den[31:16] <= den_r[31:16];
    end
endmodule
