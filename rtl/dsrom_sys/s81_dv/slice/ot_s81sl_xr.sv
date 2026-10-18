`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): the slice control plane (centre leaf), one hardened sub-leaf.  No arithmetic; it
// turns the compiler's control traffic into the fixed-cycle commands of the slice's sub-leaves:
//
//   CTL decode  CTL beats delivered by the ring stop (tier line E-bound / W-bound, or the V rung at column 3, where the
//               G-unit injects) whose slice mask holds this slice.  Payload p = beat[21 +: 186]:
//               [15:0] slice mask, [20:16] target, [25:21] leaf mask, [185:26] body (160 b):
//                 0 vp command (body = c_d) to the masked beat leaves      1 xfin go (body[31:0] = eps)
//                 2 x streamer issuer / phase start (body = is_d)          3 capture phase config (body = cfg_d)
//                 4 send config (below)                                    5 one leaf-store row write {a 10, m 4, d 128}
//               A CTL beat from V (the G-unit) is also re-injected on the tier line both ways (hops 0 = line default)
//               so every slice of the tier gets it.  Two CTL beats in one cycle are a sticky fault.
//   RD receive  RD beats (kind 4) for this slice: payload [15:0] slice mask, [18:16] leaf, [28:19] row, [30:29] pairs - 1,
//               [31 +: 1024] up to 4 row pairs -> the leaf's row-pair write port, one pair a cycle.  A second RD to a leaf
//               whose unpacker is busy, or a collision with a CTL row write, is a sticky fault.
//   send        lo row pairs from the beat leaves (RDOUT; the compiler staggers the leaves) are packed per the send config
//               (n pairs, then one beat) and injected: line E / W / V (or B on C3) with the configured header
//               {kind, hops (0 = line default), dst mask, dst leaf, dst row}.
//   SC relay    SC beats (kind 5, router scores) delivered on the line at the relay slice (send config bit) leave on V.
//   norm        the 5 beat partials (equal-latency glue: same edge) -> xfin s port in leaf order 0..4 (xfin injects on
//               index 4); xfin's rstd -> the 5 vn rb ports.
// Every input lands in a flop; every output leaves a flop.  HB = 1 builds the C3 variant (band port B, attention).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xr #(
    parameter integer HB = 0,
    parameter integer W  = 1104,
    parameter integer V  = 276
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    // ring stop (control plane side)
    input  wire            dl_ev, input wire [W-1:0] dl_e,
    input  wire            dl_wv, input wire [W-1:0] dl_w,
    input  wire            dl_vv, input wire [V-1:0] dl_vb,
    output reg  [2:0]      ci_dir,
    output wire [W-1:0]    ci_b,
    // band port (C3 only; HB = 0 leaves it out of the netlist -- see the C1 wrapper)
    input  wire [W-1:0]    bi,
    output wire [W-1:0]    bo,
    // beat leaves
    output reg  [4:0]      c_v,
    output reg  [5*160-1:0] c_d,
    output reg  [4:0]      sw_v,
    output reg  [5*10-1:0] sw_a,
    output reg  [5*8-1:0]  sw_m,
    output reg  [5*256-1:0] sw_d,
    input  wire [4:0]      lo_v,
    input  wire [5*256-1:0] lo_d,
    input  wire [4:0]      p_v,
    input  wire [5*32-1:0] p_d,
    output reg  [4:0]      rb_v,
    output reg  [5*32-1:0] rb_d,
    // xfin
    output reg             x_go,
    output reg  [31:0]     x_eps,
    output reg             x_sv,
    output reg  [7:0]      x_si,
    output reg  [31:0]     x_s,
    input  wire            x_rbv,
    input  wire [31:0]     x_rbd,
    // x streamer, capture
    output reg             is_v,
    output reg  [159:0]    is_d,
    output reg             cfg_v,
    output reg  [159:0]    cfg_d,
    output reg             fault
);
    localparam [2:0] K_CTL = 3'd0, K_RD = 3'd4, K_SC = 3'd5, K_CL = 3'd6;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_r = rsv[1], rs_s = rsv[2], rs_o = rsv[3];
    integer k, i;
    // ---------------------------------------------------------------- input flops
    reg ev, wv, vv; reg [W-1:0] eb, wb, bb; reg [V-1:0] vb; reg [4:0] lov, pv; reg [5*256-1:0] lod; reg [5*32-1:0] pd;
    reg rbv; reg [31:0] rbd; reg [3:0] sid_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin ev <= 1'b0; wv <= 1'b0; vv <= 1'b0; lov <= 5'd0; pv <= 5'd0; rbv <= 1'b0; end
        else begin ev <= dl_ev; wv <= dl_wv; vv <= dl_vv; lov <= lo_v; pv <= p_v; rbv <= x_rbv; end
    always @(posedge clk) begin
        eb <= dl_e; wb <= dl_w; vb <= dl_vb; bb <= (HB != 0) ? bi : {W{1'b0}}; lod <= lo_d; pd <= p_d; rbd <= x_rbd;
        sid_c <= sid;
    end
    wire bv = (HB != 0) && bb[0];
    // ---------------------------------------------------------------- classify
    wire e_ctl = ev && eb[3:1] == K_CTL, w_ctl = wv && wb[3:1] == K_CTL, v_ctl = vv && vb[3:1] == K_CTL;
    wire e_rd = ev && (eb[3:1] == K_RD || eb[3:1] == K_CL), w_rd = wv && (wb[3:1] == K_RD || wb[3:1] == K_CL);
    wire b_rd = bv;
    wire e_sc = ev && eb[3:1] == K_SC, w_sc = wv && wb[3:1] == K_SC;
    wire [185:0] pe = eb[21 +: 186], pw = wb[21 +: 186], pvv = vb[21 +: 186];
    wire mine_e = pe[sid_c], mine_w = pw[sid_c], mine_v = pvv[sid_c];
    wire [2:0] nctl = (e_ctl && mine_e) + (w_ctl && mine_w) + (v_ctl && mine_v);
    reg [185:0] cp; reg cvld;
    always @(*) begin
        cvld = (e_ctl && mine_e) || (w_ctl && mine_w) || (v_ctl && mine_v);
        cp = (e_ctl && mine_e) ? pe : (w_ctl && mine_w) ? pw : pvv;
    end
    wire [4:0] tgt = cp[20:16]; wire [4:0] lmask = cp[25:21]; wire [159:0] body = cp[185:26];

    // ---------------------------------------------------------------- send config, packing, injection
    // body: [2:0] dir {V/B, W, E} ([3] band on C3), [5:3]... layout: [3:0] dir {B, V, W, E}, [6:4] kind, [11:7] hops,
    //       [27:12] dst slice mask, [30:28] dst leaf, [40:31] dst row, [42:41] pairs - 1, [43] SC relay to V
    reg [3:0] s_dir; reg [2:0] s_kind; reg [4:0] s_hops; reg [15:0] s_mask; reg [2:0] s_leaf; reg [9:0] s_row; reg [1:0] s_np;
    reg s_scv;
    reg [1023:0] pk; reg [1:0] pn; reg pk_go;
    reg [W-1:0] snd; reg snd_v; reg [3:0] snd_dir;
    reg [2:0] nlo;
    always @(*) begin nlo = 3'd0; for (k = 0; k < 5; k = k + 1) nlo = nlo + lov[k]; end
    reg [255:0] lo_sel;
    always @(*) begin lo_sel = 256'd0; for (k = 0; k < 5; k = k + 1) if (lov[k]) lo_sel = lo_sel | lod[256 * k +: 256]; end
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin s_dir <= 4'd0; pn <= 2'd0; pk_go <= 1'b0; s_scv <= 1'b0; end
        else begin
            pk_go <= 1'b0;
            if (cvld && tgt == 5'd4) begin
                s_dir <= body[3:0]; s_kind <= body[6:4]; s_hops <= body[11:7]; s_mask <= body[27:12];
                s_leaf <= body[30:28]; s_row <= body[40:31]; s_np <= body[42:41]; s_scv <= body[43]; pn <= 2'd0;
            end else if (|lov) begin
                pn <= (pn == s_np) ? 2'd0 : pn + 2'd1;
                pk_go <= pn == s_np;
            end
        end
    always @(posedge clk) if (|lov) pk[256 * pn +: 256] <= lo_sel;
    always @(*) begin
        snd = {W{1'b0}};
        snd[0] = 1'b1; snd[3:1] = s_kind; snd[8:4] = s_hops; snd[12:9] = sid_c; snd[20:13] = 8'd0;
        snd[21 +: 16] = s_mask; snd[37 +: 3] = s_leaf; snd[40 +: 10] = s_row; snd[50 +: 2] = s_np; snd[52 +: 1024] = pk;
    end
    // V-from-G-unit CTL re-injection on the tier line (both sides, hops 0 = line default), SC relay to V
    wire sc_rel = s_scv && (e_sc || w_sc);
    wire [V-1:0] sc_b = e_sc ? eb[V-1:0] : wb[V-1:0];
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin ci_dir <= 3'd0; ci_v <= 1'b0; end
        else begin
            ci_dir <= v_ctl ? 3'b011 : pk_go ? s_dir[2:0] : sc_rel ? 3'b100 : 3'b000;
            ci_v <= v_ctl || (pk_go && |s_dir[2:0]) || sc_rel;
        end
    reg ci_v; reg [W-2:0] ci_r;
    assign ci_b = {ci_r, ci_v};
    always @(posedge clk)
        ci_r <= v_ctl ? {{(W - V){1'b0}}, vb[V-1:9], 5'd0, vb[3:1]} :
                       pk_go ? snd[W-1:1] : {{(W - V){1'b0}}, sc_b[V-1:1]};
    generate if (HB != 0) begin : g_bo
        reg [W-1:0] bo_r;
        always @(posedge clk or negedge rs_s) if (!rs_s) bo_r <= {W{1'b0}}; else bo_r <= (pk_go && s_dir[3]) ? snd : {W{1'b0}};
        assign bo = bo_r;
    end else begin : g_nobo
        assign bo = {W{1'b0}};                      // C1: no band port (the C1 wrapper does not expose it)
    end endgenerate

    // ---------------------------------------------------------------- RD receive: per-leaf unpackers
    reg [W-1:0] rdb; reg rdv;
    always @(*) begin
        rdv = 1'b0; rdb = {W{1'b0}};
        if (e_rd && eb[21 + sid_c]) begin rdv = 1'b1; rdb = eb; end
        else if (w_rd && wb[21 + sid_c]) begin rdv = 1'b1; rdb = wb; end
        else if (b_rd) begin rdv = 1'b1; rdb = bb; end
    end
    wire [2:0] nrd = (e_rd && eb[21 + sid_c]) + (w_rd && wb[21 + sid_c]) + b_rd;
    wire [2:0] rl = rdb[37 +: 3]; wire [9:0] rrow = rdb[40 +: 10]; wire [1:0] rnp = rdb[50 +: 2];
    reg [4:0] ub; reg [1:0] un [0:4]; reg [1:0] ul [0:4]; reg [9:0] ur [0:4]; reg [1023:0] ud [0:4];
    reg ucol;
    always @(posedge clk or negedge rs_r)
        if (!rs_r) begin ub <= 5'd0; sw_v <= 5'd0; ucol <= 1'b0; for (k = 0; k < 5; k = k + 1) un[k] <= 2'd0; end
        else begin
            ucol <= 1'b0;
            for (k = 0; k < 5; k = k + 1) begin
                sw_v[k] <= 1'b0;
                if (ub[k]) begin
                    sw_v[k] <= 1'b1; un[k] <= un[k] + 2'd1;
                    if (un[k] == ul[k]) ub[k] <= 1'b0;
                end
                if (rdv && rl == k) begin
                    if (ub[k] && un[k] != ul[k]) ucol <= 1'b1;
                    ub[k] <= 1'b1; un[k] <= 2'd0;
                end
                if (cvld && tgt == 5'd5 && lmask[k]) begin
                    sw_v[k] <= 1'b1;
                    if (ub[k]) ucol <= 1'b1;
                end
            end
        end
    always @(posedge clk)
        for (k = 0; k < 5; k = k + 1) begin
            if (rdv && rl == k) begin ul[k] <= rnp; ur[k] <= rrow; ud[k] <= rdb[52 +: 1024]; end
            if (cvld && tgt == 5'd5 && lmask[k]) begin
                sw_a[10 * k +: 10] <= body[9:0]; sw_m[8 * k +: 8] <= {4'd0, body[13:10]};
                sw_d[256 * k +: 256] <= {128'd0, body[141:14]};
            end else begin
                sw_a[10 * k +: 10] <= ur[k] + {7'd0, un[k], 1'b0};
                sw_m[8 * k +: 8] <= 8'hff;
                sw_d[256 * k +: 256] <= ud[k][256 * un[k] +: 256];
            end
        end

    // ---------------------------------------------------------------- command fan-out, xfin, streamer, capture
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin c_v <= 5'd0; x_go <= 1'b0; is_v <= 1'b0; cfg_v <= 1'b0; end
        else begin
            c_v <= (cvld && tgt == 5'd0) ? lmask : 5'd0;
            x_go <= cvld && tgt == 5'd1;
            is_v <= cvld && tgt == 5'd2;
            cfg_v <= cvld && tgt == 5'd3;
        end
    always @(posedge clk) begin
        for (k = 0; k < 5; k = k + 1) c_d[160 * k +: 160] <= body;
        if (cvld && tgt == 5'd1) x_eps <= body[31:0];
        is_d <= body; cfg_d <= body;
    end
    // partial collector: the 5 partials arrive on one edge; xfin takes them in leaf order 0..4
    reg [31:0] pq [0:4]; reg [2:0] pi; reg prun;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin prun <= 1'b0; pi <= 3'd0; x_sv <= 1'b0; rb_v <= 5'd0; end
        else begin
            x_sv <= prun;
            if (|pv) begin prun <= 1'b1; pi <= 3'd0; end
            else if (prun) begin pi <= pi + 3'd1; if (pi == 3'd4) prun <= 1'b0; end
            rb_v <= {5{rbv}};
        end
    always @(posedge clk) begin
        for (k = 0; k < 5; k = k + 1) if (pv[k]) pq[k] <= pd[32 * k +: 32];
        x_si <= {5'd0, pi}; x_s <= pq[pi];
        rb_d <= {5{rbd}};
    end
    // ---------------------------------------------------------------- faults
    always @(posedge clk or negedge rs_o)
        if (!rs_o) fault <= 1'b0;
        else fault <= fault | (nctl > 3'd1) | (nrd > 3'd1) | ucol | (nlo > 3'd1) | ((|pv) && pv != 5'b11111) |
                      ((|pv) && prun) | (v_ctl && (pk_go || sc_rel)) | (pk_go && sc_rel);
endmodule

// C1 (14 slices): ring E/W + V.  C3 (s_1S, s_6S): + band port B (attention q / P.V).  Hardened masters, no parameters.
module ot_s81sl_xr1 (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1103:0] dl_e, input wire dl_wv, input wire [1103:0] dl_w,
    input  wire dl_vv, input wire [275:0] dl_vb, output wire [2:0] ci_dir, output wire [1103:0] ci_b,
    output wire [4:0] c_v, output wire [799:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire [4:0] rb_v, output wire [159:0] rb_d, output wire x_go, output wire [31:0] x_eps, output wire x_sv,
    output wire [7:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);
    wire [1103:0] bo_unused;
    ot_s81sl_xr #(.HB(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi({1104{1'b0}}), .bo(bo_unused), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .x_go(x_go), .x_eps(x_eps), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule

module ot_s81sl_xr3 (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1103:0] dl_e, input wire dl_wv, input wire [1103:0] dl_w,
    input  wire dl_vv, input wire [275:0] dl_vb, output wire [2:0] ci_dir, output wire [1103:0] ci_b,
    input  wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4:0] c_v, output wire [799:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire [4:0] rb_v, output wire [159:0] rb_d, output wire x_go, output wire [31:0] x_eps, output wire x_sv,
    output wire [7:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);
    ot_s81sl_xr #(.HB(1)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi(bi), .bo(bo), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .x_go(x_go), .x_eps(x_eps), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule
