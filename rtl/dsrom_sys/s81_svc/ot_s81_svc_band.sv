`timescale 1ns/1ps
// S81 svc BAND (HARD-S81-SVC-1 11-13, COORD ruling "svc option A", R-CAP-3 point 2): one engine lane band of
// ot_s81_svc_attn_s as ONE module, so the die plan can make it its own partition (asbuilt part prefix
// u_eng.g_tr[k].g_xb.u_band).  It holds tile k's transposer (ot_hdc_v41x_attn_tr_x), its head-group tile
// (ot_hdc_v41x_attn_tile_s, the 8 attn hard cores) and its p.v block merge.
// Registered boundary, both ways:
//   in : EVERY input is captured by a register here (one more relay stage after the engine's SRX stages), so the
//        band runs exactly one edge after the SRX-stage bundle with unchanged internal timing;
//   out: the tile outputs (ov / oy / oflt) and the merge outputs (m_ov / m_y / m_f) leave through a register.
// The engine delays its output tags by 2 more (BANDX): scores +2, P.V +2 against the same p feed, i.e. the SRX
// signature with n = SRX + 2 (svc_srx_lockstep.py --band).  The merge tags (pv / fin / blk) are sent one edge before
// the tile's own output and captured here, so the merge sees the same alignment as in the flat engine.
// Ports carry only bits that are used: fw = the fill-row bits this tile's dims read (srx_fused), packed.
// v2 (COORD 11-13 after the first band place + GRT: reset / merge-valid / load paths were the worst):
//   CAPD  input capture depth (1 = v1; 2 = a second relay stage, so the first sits at the pins and the second at the
//         transposer / tile load stage): the band runs CAPD edges after the SRX-stage bundle;
//   MREG  1 = the merge inputs (valid, fin, blk, tile values and flags) are registered before the merge cores, so
//         core 0's valid no longer runs combinationally to both merge providers: P.V +1 more;
//   reset: rst_n is registered once at the band root and once more per consumer group (band registers + transposer,
//         tile, merge): a 2-stage registered reset tree instead of a port broadcast (rst_n is held >= 64 clk).
// Latency: scores +(CAPD + 1), P.V +(CAPD + 1 + MREG) on top of SRX.
// MUT (bench only, 0 in every kit): 2 = merge tags one capture stage early.
module ot_s81_svc_band #(
    parameter integer H = 8,
    parameter integer TD = 32,
    parameter integer DPT = 8,
    parameter integer NL = 4,
    parameter integer NBANK = 5,
    parameter integer BW = 3,
    parameter integer PWORDS = 2,
    parameter integer FPL = 4,
    parameter integer FML = 6,
    parameter integer F12 = 1,
    parameter integer MLEV = 5,
    parameter integer FX = 5,
    parameter integer XOFF = 0,
    parameter integer NF = 1,          // fused fill bits per lane (the engine computes it; checked below)
    parameter integer CAPD = 1,
    parameter integer MREG = 0,
    parameter integer TILEX = 0,       // edges the tile's outputs leave later than as built (OT_S81C_TILE_STAGE: 1)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // transposer bundle (engine relay stage SRX): {r_c[7:0], r_half, w_cnt[7:0], w_half, w_en, sel}
    input  wire [19:0]       ctl_i,
    input  wire [NL-1:0]     wpad_i,
    input  wire [NL*NF-1:0]  fw_i,
    input  wire [264:0]      q_i,       // this tile's raw q.k row word
    input  wire              qpad_i,
    // tile load / issue line (engine stage SRX)
    input  wire              ld_v_i,
    input  wire              ld_mode_i,
    input  wire              ld_w2v_i,
    input  wire [BW-1:0]     ld_bank_i,
    input  wire [7:0]        ld_grp_i,
    input  wire [PWORDS*TD*16-1:0] ld_w_i,
    input  wire              iv_i,
    input  wire [BW-1:0]     ibank_i,
    // merge tags, one edge before the tile's output
    input  wire              t_pv_i,
    input  wire              t_fin_i,
    input  wire [MLEV-1:0]   t_blk_i,
    // registered outputs
    output reg               ov,
    output reg  [H*32-1:0]   oy,
    output reg  [H-1:0]      oflt,
    output reg               m_ov,
    output reg  [H*32-1:0]   m_y,
    output reg  [H-1:0]      m_f
);
    localparam integer GW = 265;
    function automatic bit fused(input integer b, input integer xo, input integer n);   // = the engine's srx_fused
        integer x;
        begin
            fused = (b >= 256);
            for (x = xo; x < xo + n; x = x + 1)
                if ((b >= 8*x && b < 8*x + 8) || (b >= 4*x && b < 4*x + 4) || (b >= 128 + 8*(x/16) && b < 136 + 8*(x/16)))
                    fused = 1'b1;
        end
    endfunction
    function automatic integer fpos(input integer b, input integer xo, input integer n);   // fused bits below b
        integer i;
        begin
            fpos = 0;
            for (i = 0; i < b; i = i + 1)
                if (fused(i, xo, n)) fpos = fpos + 1;
        end
    endfunction
    function automatic [17:0] elem(input [GW-1:0] gw, input integer x, input pad);          // = the engine's elem
        begin
            if (gw[264]) elem = {pad, 1'b1, 4'd0, gw[4*x +: 4], gw[128 + 8*(x/16) +: 8]};
            else         elem = {pad, 1'b0, gw[8*x +: 8], gw[263:256]};
        end
    endfunction
    generate
        if (NF != fpos(GW, XOFF, DPT) || TD != 32 || H != 8 || CAPD < 1 || CAPD > 4) begin : g_bad
            initial $error("ot_s81_svc_band: NF must be the fused bit count; needs TD 32, H 8, CAPD 1..4");
        end
    endgenerate

    // ---- registered reset tree: band root, then one copy per consumer group
    (* keep = "true" *) reg       r_root;
    (* keep = "true" *) reg [2:0] r_leaf;          // [0] band registers + transposer, [1] tile, [2] merge
    always @(posedge clk) begin r_root <= rst_n; r_leaf <= {3{r_root}}; end
    wire rb = r_leaf[0];

    // ---- input capture: CAPD relay stages; valids reset, the rest data
    localparam integer DW = 18 + NL + NL*NF + GW + 1 + 2 + BW + 8 + PWORDS*TD*16 + BW + 2 + MLEV;
    wire [DW-1:0] d_in = {ctl_i[19:2], wpad_i, fw_i, q_i, qpad_i, ld_mode_i, ld_w2v_i, ld_bank_i, ld_grp_i, ld_w_i,
                          ibank_i, t_pv_i, t_fin_i, t_blk_i};
    wire [3:0]    v_in = {ctl_i[1:0], ld_v_i, iv_i};
    reg [DW-1:0] d_q [0:CAPD-1];
    reg [3:0]    v_q [0:CAPD-1];
    integer ci;
    always @(posedge clk)
        for (ci = 0; ci < CAPD; ci = ci + 1) d_q[ci] <= (ci == 0) ? d_in : d_q[ci - 1];
    always @(posedge clk or negedge rb) begin
        if (!rb) for (ci = 0; ci < CAPD; ci = ci + 1) v_q[ci] <= 4'd0;
        else     for (ci = 0; ci < CAPD; ci = ci + 1) v_q[ci] <= (ci == 0) ? v_in : v_q[ci - 1];
    end
    wire [19:2]     c_d;
    wire [1:0]      c_v;
    wire [NL-1:0]   c_pad;
    wire [NL*NF-1:0] c_fw;
    wire [GW-1:0]   c_q;
    wire            c_qp;
    wire            l_v, i_v;
    wire            l_mode, l_w2v;
    wire [BW-1:0]   l_bank, i_bank;
    wire [7:0]      l_grp;
    wire [PWORDS*TD*16-1:0] l_w;
    wire            g_pv, g_fin;
    wire [MLEV-1:0] g_blk;
    wire            g0_pv, g0_fin;
    wire [MLEV-1:0] g0_blk;
    assign {c_d, c_pad, c_fw, c_q, c_qp, l_mode, l_w2v, l_bank, l_grp, l_w, i_bank, g0_pv, g0_fin, g0_blk} = d_q[CAPD-1];
    // TILEX: the merge tags wait as many edges as the tile's own extra stages
    generate if (TILEX > 0) begin : g_tx
        reg [MLEV+1:0] tq [0:TILEX-1];
        integer ti;
        always @(posedge clk) for (ti = 0; ti < TILEX; ti = ti + 1) tq[ti] <= (ti == 0) ? {g0_pv, g0_fin, g0_blk} : tq[ti - 1];
        assign {g_pv, g_fin, g_blk} = tq[TILEX-1];
    end else begin : g_tx0
        assign {g_pv, g_fin, g_blk} = {g0_pv, g0_fin, g0_blk};
    end endgenerate
    assign {c_v, l_v, i_v} = v_q[CAPD-1];
    // the merge tags one capture stage early (MUT 2 only)
    wire [DW-1:0] d_e = (CAPD == 1) ? d_in : d_q[(CAPD > 1) ? CAPD - 2 : 0];
    wire            e_pv  = d_e[MLEV + 1];
    wire            e_fin = d_e[MLEV];
    wire [MLEV-1:0] e_blk = d_e[MLEV-1:0];

    // ---- transposer operands
    wire [NL*GW-1:0] w_g;
    wire [TD*18-1:0] qk_x;
    genvar gl, gs;
    generate
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_g
            for (gs = 0; gs < GW; gs = gs + 1) begin : g_b
                if (fused(gs, XOFF, DPT)) begin : g_u
                    assign w_g[gl*GW + gs] = c_fw[gl*NF + fpos(gs, XOFF, DPT)];
                end else begin : g_z
                    assign w_g[gl*GW + gs] = 1'b0;
                end
            end
        end
        for (gs = 0; gs < TD; gs = gs + 1) begin : g_e
            assign qk_x[gs*18 +: 18] = elem(c_q, gs % 32, c_qp);
        end
    endgenerate
    wire [TD*18-1:0] col;                 // unused (REPL != 0 engines take eib)
    wire [TD*18-1:0] eib;
    ot_hdc_v41x_attn_tr_x #(.TD(TD), .DPT(DPT), .NL(NL), .XOFF(XOFF)) u_tr (
        .clk(clk), .rst_n(rb),
        .w_en_i(c_v[1]), .w_half_i(c_d[2]), .w_cnt_i(c_d[10:3]), .w_pad_i(c_pad), .w_g(w_g),
        .r_half_i(c_d[11]), .r_c_i(c_d[19:12]), .sel_i(c_v[0]), .qk_ib(qk_x),
        .col(col), .eib(eib));

    // ---- tile (the 8 attention hard cores)
    wire            t_ov;
    wire [H*32-1:0] t_y;
    wire [H-1:0]    t_f;
    ot_hdc_v41x_attn_tile_s #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(FML), .F12(F12)) u_t (
        .clk(clk), .rst_n(r_leaf[1]), .ld_v(l_v), .ld_mode(l_mode), .ld_bank(l_bank),
        .ld_grp(l_grp), .ld_w(l_w), .ld_w2v(l_w2v), .iv(i_v), .ibank(i_bank),
        .ib(eib), .ov(t_ov), .oy(t_y), .oflt(t_f));

    // ---- p.v block merge (same module and alignment as the flat engine's g_m[k].g_real.g_x.u_m)
    wire            x_pv  = (MUT == 2) ? e_pv  : g_pv;
    wire            x_fin = (MUT == 2) ? e_fin : g_fin;
    wire [MLEV-1:0] x_blk = (MUT == 2) ? e_blk : g_blk;
    // MREG: the merge inputs registered here (core 0's valid stops at this register)
    reg             mr_v;
    reg             mr_fin;
    reg [MLEV-1:0]  mr_blk;
    reg [H*32-1:0]  mr_y;
    reg [H-1:0]     mr_f;
    always @(posedge clk) begin mr_fin <= x_fin; mr_blk <= x_blk; mr_y <= t_y; mr_f <= t_f; end
    always @(posedge clk or negedge r_leaf[2]) begin
        if (!r_leaf[2]) mr_v <= 1'b0;
        else mr_v <= t_ov && x_pv;
    end
    wire            mi_v   = (MREG != 0) ? mr_v   : (t_ov && x_pv);
    wire            mi_fin = (MREG != 0) ? mr_fin : x_fin;
    wire [MLEV-1:0] mi_blk = (MREG != 0) ? mr_blk : x_blk;
    wire [H*32-1:0] mi_y   = (MREG != 0) ? mr_y   : t_y;
    wire [H-1:0]    mi_f   = (MREG != 0) ? mr_f   : t_f;
    wire            mo_v;
    wire [H*32-1:0] mo_y;
    wire [H-1:0]    mo_f;
`ifdef OT_SVC_MERGE_H4
    ot_s81_svc_merge_h8_split #(.DPT(DPT), .MLEV(MLEV), .FPL(FX), .F12(F12)) u_m (
        .clk(clk), .rst_n(r_leaf[2]), .iv(mi_v), .ifin(mi_fin), .iblk(mi_blk),
        .iy(mi_y), .if_(mi_f), .ov(mo_v), .oy(mo_y), .of_(mo_f));
`else
    ot_hdc_v41x_attn_merge_x #(.H(H), .DPT(DPT), .MLEV(MLEV), .FPL(FX), .F12(F12)) u_m (
        .clk(clk), .rst_n(r_leaf[2]), .iv(mi_v), .ifin(mi_fin), .iblk(mi_blk),
        .iy(mi_y), .if_(mi_f), .ov(mo_v), .oy(mo_y), .of_(mo_f));
`endif

    // ---- output registers
    always @(posedge clk or negedge rb) begin
        if (!rb) begin ov <= 1'b0; m_ov <= 1'b0; end
        else begin ov <= t_ov; m_ov <= mo_v; end
    end
    always @(posedge clk) begin
        oy <= t_y; oflt <= t_f; m_y <= mo_y; m_f <= mo_f;
    end
endmodule
