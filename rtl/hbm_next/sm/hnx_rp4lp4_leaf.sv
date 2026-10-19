// HBM-NEXT-SM4: the P-lane leaf of hnx_rp4lp4 (lane fan-out, x-slot lane select, slot-major publish); see hnx_rp4lp4.sv
`timescale 1ns/1ps

// ---------------------------------------------------------------------------------------------------------------------
// per-lane registered fan-out of the row bundle and the x-write beat, lane-select decode (one leaf)
// MUT (bench negative controls only, default 0): 1 = lane P-1 takes lane 0's x target bit (lane alias);
//                                                2 = lane-select beats ignored (every lane takes every x beat).
module hnx_rp4lp4_lanefan #(parameter integer P = 4, parameter integer MUT = 0) (
    input  wire clk, input wire rst_n,
    input  wire [817:0] rl1, input wire [2068:0] bk1,
    output wire [P*818-1:0] rl_p, output wire [P*2069-1:0] bk_p, output wire [P-1:0] act
);
    wire sel = bk1[2068] && (bk1[2060:2048] == 13'd0);
    reg [P-1:0] tgt_q, act_q;
    always @(posedge clk)
        if (!rst_n) begin tgt_q <= {{(P-1){1'b0}}, 1'b1}; act_q <= {{(P-1){1'b0}}, 1'b1}; end
        else if (sel && MUT != 2) begin tgt_q <= bk1[P-1:0]; act_q <= bk1[8 +: P]; end
    assign act = act_q;
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        localparam integer TB = (MUT == 1 && p == P - 1 && P > 1) ? 0 : p;
        wire take = (MUT == 2) ? 1'b1 : tgt_q[TB];
        (* keep *) reg [817:0] rq;
        (* keep *) reg bv;
        (* keep *) reg [2067:0] bd;
        always @(posedge clk) rq <= rl1;
        always @(posedge clk)
            if (!rst_n) bv <= 1'b0;
            else bv <= bk1[2068] && !sel && take;
        always @(posedge clk) bd <= bk1[2067:0];
        assign rl_p[p*818 +: 818] = rq;
        assign bk_p[p*2069 +: 2069] = {bv, bd};
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// slot-major publish: lane p delayed p*LSKEW, merged onto one gather word {gv, gf, gy[31:0], gt[15:0]}, registered.
// MUT 3 (bench only): lane 2 uses lane 1's slot (collides).
// RING (P3-SM 10-19): 1 = ring-buffer lane delays (production, safe-design item 5), 0 = the SM4 shift registers.
module hnx_rp4lp4_pub #(parameter integer P = 4, parameter integer LSKEW = 8, parameter integer MUT = 0, parameter integer RING = 1) (
    input  wire clk, input wire rst_n,
    input  wire [P*50-1:0] g_p, input wire [P-1:0] act,
    output wire [49:0] g
);
    wire [P-1:0] v, f;
    wire [P*48-1:0] d;
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        localparam integer DL = ((MUT == 3 && p == 2) ? 1 : p) * LSKEW;
        wire vi = g_p[p*50 + 49] && act[p];
        wire fi = g_p[p*50 + 48] && act[p];
        if (DL == 0) begin : g_d0
            assign v[p] = vi; assign f[p] = fi; assign d[p*48 +: 48] = g_p[p*50 +: 48];
        end else if (RING == 0) begin : g_dl
            // plain flop shift registers (flat vectors, no array: never a yosys memory)
            reg [DL-1:0] sv, sf;
            reg [DL*48-1:0] sd;
            always @(posedge clk)
                if (!rst_n) begin sv <= {DL{1'b0}}; sf <= {DL{1'b0}}; end
                else begin sv <= (sv << 1) | {{(DL-1){1'b0}}, vi}; sf <= (sf << 1) | {{(DL-1){1'b0}}, fi}; end
            always @(posedge clk) sd <= (sd << 48) | {{((DL-1)*48){1'b0}}, g_p[p*50 +: 48]};
            assign v[p] = sv[DL-1]; assign f[p] = sf[DL-1]; assign d[p*48 +: 48] = sd[(DL-1)*48 +: 48];
        end else begin : g_rb
            // RING BUFFER (P3-SM 10-19, safe-design item 5: a delay line >= 3 deep is a ring, not a flop->flop chain):
            // DL entries, one write pointer; each cycle the entry written DL cycles ago is read, then overwritten.
            // Delay exactly DL, every entry written once per DL cycles (no shifting, no hold chain).  <= 2 kb per lane
            // (P = 3: 16 x 50 b) -> flops, read through a registered-pointer DL:1 mux (log2 DL levels).
            localparam integer AW = (DL <= 2) ? 1 : $clog2(DL);
            reg [AW-1:0] wp;
            reg [DL-1:0] rv, rf;
            reg [DL*48-1:0] rd;
            integer e, e2;
            always @(posedge clk)
                if (!rst_n) begin wp <= {AW{1'b0}}; rv <= {DL{1'b0}}; rf <= {DL{1'b0}}; end
                else begin
                    wp <= (wp == DL - 1) ? {AW{1'b0}} : wp + 1'b1;
                    for (e = 0; e < DL; e = e + 1) if (wp == e) begin rv[e] <= vi; rf[e] <= fi; end
                end
            always @(posedge clk)
                for (e2 = 0; e2 < DL; e2 = e2 + 1) if (wp == e2) rd[e2*48 +: 48] <= g_p[p*50 +: 48];
            assign v[p] = rv[wp]; assign f[p] = rf[wp]; assign d[p*48 +: 48] = rd[wp*48 +: 48];
        end
    end endgenerate
    // merge: AND-OR of the valid lanes; two valid lanes in one cycle = schedule collision -> fault
    reg [47:0] m;
    reg multi;
    integer j, n;
    always @* begin
        m = 48'd0; n = 0;
        for (j = 0; j < P; j = j + 1) begin
            m = m | ({48{v[j]}} & d[j*48 +: 48]);
            n = n + (v[j] ? 1 : 0);
        end
        multi = (n > 1);
    end
    reg gv_q, gf_q;
    reg [47:0] gd_q;
    always @(posedge clk)
        if (!rst_n) begin gv_q <= 1'b0; gf_q <= 1'b0; end
        else begin gv_q <= |v; gf_q <= (|f) | multi; end
    always @(posedge clk) gd_q <= m;
    assign g = {gv_q, gf_q, gd_q};
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// one P-lane leaf (soft child of the flat parent; holds 5 x P hard children): g = {gv, gf, gy, gt} as ot_rp4l_leaf
module hnx_rp4lp4_lf #(parameter integer P = 4, parameter integer LSKEW = 8, parameter integer MUT = 0) (
    input  wire clk, input wire rst_n, input wire [25:0] st, input wire [817:0] rl1,
    input  wire [2068:0] bk1, output wire [49:0] g
);
    wire [P*818-1:0] rl_p;
    wire [P*2069-1:0] bk_p;
    wire [P-1:0] act;
    wire [P*50-1:0] g_p;
    hnx_rp4lp4_lanefan #(.P(P), .MUT(MUT)) u_fan (.clk(clk), .rst_n(rst_n), .rl1(rl1), .bk1(bk1), .rl_p(rl_p), .bk_p(bk_p),
        .act(act));
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        wire gv, gf; wire [31:0] gy; wire [15:0] gt;
        wire [2068:0] bk = bk_p[p*2069 +: 2069];
        hnx_rp4_leafh u_lh (.clk(clk), .clk_xb(clk), .clk_xf(clk), .clk_hard({5{clk}}), .rst_n(rst_n),
            .xs_a1(st[8:0]), .xs_g1(st[13:9]), .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rl_p[p*818 +: 818]), .bk1(bk),
            .ohl1(bk[2060:2048]), .gv(gv), .gf(gf), .gy(gy), .gt(gt));
        assign g_p[p*50 +: 50] = {gv, gf, gy, gt};
    end endgenerate
    hnx_rp4lp4_pub #(.P(P), .LSKEW(LSKEW), .MUT(MUT)) u_pub (.clk(clk), .rst_n(rst_n), .g_p(g_p), .act(act), .g(g));
endmodule


// ---------------------------------------------------------------------------------------------------------------------
// LEVER (a) (PROG 10-19): the P-lane leaf on the SHARED P-lane x store hnx_xs4.  One registered lane front (+1, one copy:
// the x store is one child), one hnx_xs4 (shared landing / rotation / weight operand, P SRAM sets), and per lane the
// d4g leafh's own XREL operand stations (xb_* / xf_*: one register on every operand bit between the x store and the
// lane's columns = the per-lane registered fan-out of the shared weight word) -> block-dot column + BF16 column (CLOSED
// views) -> G1 -> slot-major publish.  Per lane exactly the d4g leafh datapath; cycle timing = hnx_rp4lp4_lf.
// MUT: 1 = x-store lane alias (hnx_xs4 MUT 1), 2 = lane-select ignored, 3 = publish slot error, 4 = W-face BF16 weight
// copy sign bits inverted (hnx_xs4 MUT 4: proves the W-face lanes read the W copy).
module hnx_rp4lp4_lfx #(parameter integer P = 4, parameter integer LSKEW = 8, parameter integer MUT = 0,
                        parameter integer TAGW = 16, parameter integer LBS = 2, parameter integer LSB = 16) (
    input  wire clk, input wire rst_n, input wire [25:0] st, input wire [817:0] rl1,
    input  wire [2068:0] bk1, output wire [49:0] g
);
    // lane front: lane-select decode, ONE registered copy of the row bundle / x beat (+1, as hnx_rp4lp4_lanefan)
    wire sel = bk1[2068] && (bk1[2060:2048] == 13'd0);
    reg [P-1:0] tgt_q, act_q;
    always @(posedge clk)
        if (!rst_n) begin tgt_q <= {{(P-1){1'b0}}, 1'b1}; act_q <= {{(P-1){1'b0}}, 1'b1}; end
        else if (sel && MUT != 2) begin tgt_q <= bk1[P-1:0]; act_q <= bk1[8 +: P]; end
    (* keep *) reg [817:0] rq;
    (* keep *) reg bv;
    (* keep *) reg [2067:0] bd;
    (* keep *) reg [P-1:0] wl;
    always @(posedge clk) rq <= rl1;
    always @(posedge clk)
        if (!rst_n) bv <= 1'b0;
        else bv <= bk1[2068] && !sel && ((MUT == 2) ? 1'b1 : (|tgt_q));
    always @(posedge clk) begin bd <= bk1[2067:0]; wl <= (MUT == 2) ? {P{1'b1}} : tgt_q; end
    // reset copies (as the d4g leafh rq: one kept register per consumer)
    (* keep *) reg [1+4*P-1:0] rr;
    always @(posedge clk) rr <= {(1+4*P){rst_n}};
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    // x store faces (10-19 face split): N = block-dot operands, W = BF16 lanes 0..PW-1, E = BF16 lanes PW..P-1
    localparam integer PW = (P + 1) / 2, PEW = (P - PW) > 0 ? (P - PW) : 1;
    wire iv_fw, ifirst_w, ilast_w;
    wire [TAGW-1:0] itag_w;
    wire [LBS*266-1:0] iwb;
    wire [P*LBS*266-1:0] ixb;
    wire [LSB*16-1:0] iwf_e, iwf_w;
    wire [PEW*LSB*16-1:0] ixf_e;
    wire [PW*LSB*16-1:0] ixf_w;
    // The store is a HARD child: at P = 3 (owner 10-19 production, P3+(a)) it is hnx_xs3 (P = 3 by default) instantiated
    // WITHOUT a parameter override in the kit (MUT = 0), so synthesis keeps the master name hnx_xs3 (no $paramod rename);
    // other P (P = 4 evidence, P = 1 / 2 benches) use hnx_xs4 #(.P(P)).  Instance path: u_lfN.g_xs3.u_xs / u_lfN.g_xs.u_xs.
    localparam integer XMUT = (MUT == 1 || MUT == 4) ? MUT : 0;
`define HNX_LFX_XS_PORTS (.clk(clk), .rst_a(rr[0]), .xs_a1(st[8:0]), .xs_g1(st[13:9]), \
        .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rq), .bk1({bv, bd}), .ohl1(bd[2060:2048]), .wl(wl), \
        .o_iv_b(iv_b), .o_iv_f(iv_f), .o_ifirst(ifirst), .o_ilast(ilast), .o_ifp4(ifp4), .o_itag(itag), .o_iwb(iwb), .o_ixb(ixb), \
        .o_iwf_e(iwf_e), .o_ixf_e(ixf_e), .o_iwf_w(iwf_w), .o_ixf_w(ixf_w), \
        .o_ifirst_e(ifirst_e), .o_ilast_e(ilast_e), .o_itag_e(itag_e), \
        .o_iv_fw(iv_fw), .o_ifirst_w(ifirst_w), .o_ilast_w(ilast_w), .o_itag_w(itag_w))
`ifdef SYNTHESIS
    // hard-build path (kit define SYNTHESIS = spec hard_define): hard children with NO parameter overrides
    generate if (P == 3) begin : g_xs3
        hnx_xs3 u_xs `HNX_LFX_XS_PORTS;
    end else begin : g_xs
        hnx_xs4 u_xs `HNX_LFX_XS_PORTS;
    end endgenerate
`else
    // simulation: bench mutants and P = 1 / 2 / 4 through the parameterised stores
    generate if (P == 3 && XMUT == 0) begin : g_xs3
        hnx_xs3 u_xs `HNX_LFX_XS_PORTS;
    end else if (P == 3) begin : g_xs3m
        hnx_xs3 #(.MUT(XMUT)) u_xs `HNX_LFX_XS_PORTS;
    end else begin : g_xs
        hnx_xs4 #(.P(P), .MUT(XMUT)) u_xs `HNX_LFX_XS_PORTS;
    end endgenerate
`endif
`undef HNX_LFX_XS_PORTS
    wire [P*50-1:0] g_p;
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        wire r_bdc = rr[1 + 4*p], r_tcc = rr[2 + 4*p], r_g = rr[3 + 4*p], r_x = rr[4 + 4*p];
        // XREL stations of lane p (the d4g leafh's xb_* / xf_*, per lane)
        reg xb_v, xf_v, xb_first, xb_last, xb_fp4, xf_first, xf_last;
        reg [TAGW-1:0] xb_tag, xf_tag;
        reg [LBS*266-1:0] xb_w, xb_x;
        reg [LSB*16-1:0] xf_w, xf_x;
        always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xb_v <= 0; else xb_v <= iv_b;
        // BF16 operands from the x store face of this lane's side (W lanes < PW, E lanes >= PW)
        wire sv_f = (p < PW) ? iv_fw : iv_f, sfirst = (p < PW) ? ifirst_w : ifirst_e, slast = (p < PW) ? ilast_w : ilast_e;
        wire [TAGW-1:0] stag = (p < PW) ? itag_w : itag_e;
        wire [LSB*16-1:0] swf = (p < PW) ? iwf_w : iwf_e;
        wire [LSB*16-1:0] sxf = (p < PW) ? ixf_w[((p < PW) ? p : 0)*LSB*16 +: LSB*16] : ixf_e[((p < PW) ? 0 : p - PW)*LSB*16 +: LSB*16];
        always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xf_v <= 0; else xf_v <= sv_f;
        always @(posedge clk) begin
            xb_first <= ifirst; xb_last <= ilast; xb_fp4 <= ifp4; xb_tag <= itag;
            xb_w <= iwb; xb_x <= ixb[p*LBS*266 +: LBS*266];
            xf_first <= sfirst; xf_last <= slast; xf_tag <= stag;
            xf_w <= swf; xf_x <= sxf;
        end
        wire bov, bfault, fov, ffault;
        wire [31:0] by, fy;
        wire [TAGW-1:0] btag, ftag;
        ot_hbm_accel_smh_bdc u_bdc (.clk(clk), .rst_a(r_bdc), .i_v(xb_v), .i_first(xb_first), .i_last(xb_last), .i_fp4(xb_fp4),
            .i_tag(xb_tag), .i_w(xb_w), .i_x(xb_x), .ov(bov), .y(by), .otag(btag), .fault(bfault));
        hnx_rp4_tcc u_tcc (.clk_hard({3{clk}}), .rst_a(r_tcc), .i_v(xf_v), .i_first(xf_first), .i_last(xf_last), .i_tag(xf_tag),
            .i_w(xf_w), .i_x(xf_x), .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        reg gv_q, gf_q;
        reg [31:0] gy_q;
        reg [TAGW-1:0] gt_q;
        always @(`OT_RP4_AR(clk, r_g))
            if (!r_g) begin gv_q <= 1'b0; gf_q <= 1'b0; end
            else begin gv_q <= bov | fov; gf_q <= bfault | ffault | (bov & fov); end
        always @(posedge clk) begin gy_q <= bov ? by : fy; gt_q <= bov ? btag : ftag; end
        wire gv = gv_q, gf = gf_q; wire [31:0] gy = gy_q; wire [15:0] gt = gt_q;
        assign g_p[p*50 +: 50] = {gv, gf, gy, gt};
    end endgenerate
    hnx_rp4lp4_pub #(.P(P), .LSKEW(LSKEW), .MUT(MUT)) u_pub (.clk(clk), .rst_n(rst_n), .g_p(g_p), .act(act_q), .g(g));
endmodule
