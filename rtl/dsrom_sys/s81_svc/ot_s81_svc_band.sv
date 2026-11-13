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
// MUT (bench only, 0 in every kit): 2 = merge tags not captured (one edge early).
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
        if (NF != fpos(GW, XOFF, DPT) || TD != 32 || H != 8) begin : g_bad
            initial $error("ot_s81_svc_band: NF must be the fused bit count; needs TD 32, H 8");
        end
    endgenerate

    // ---- input capture (the band's relay stage): valids reset, the rest data
    reg [19:2]      c_d;
    reg [1:0]       c_v;
    reg [NL-1:0]    c_pad;
    reg [NL*NF-1:0] c_fw;
    reg [GW-1:0]    c_q;
    reg             c_qp;
    reg             l_v, i_v;
    reg             l_mode, l_w2v;
    reg [BW-1:0]    l_bank, i_bank;
    reg [7:0]       l_grp;
    reg [PWORDS*TD*16-1:0] l_w;
    reg             g_pv, g_fin;
    reg [MLEV-1:0]  g_blk;
    always @(posedge clk) begin
        c_d <= ctl_i[19:2]; c_pad <= wpad_i; c_fw <= fw_i; c_q <= q_i; c_qp <= qpad_i;
        l_mode <= ld_mode_i; l_w2v <= ld_w2v_i; l_bank <= ld_bank_i; l_grp <= ld_grp_i; l_w <= ld_w_i;
        i_bank <= ibank_i;
        g_pv <= t_pv_i; g_fin <= t_fin_i; g_blk <= t_blk_i;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_v <= 2'b00; l_v <= 1'b0; i_v <= 1'b0; end
        else begin c_v <= ctl_i[1:0]; l_v <= ld_v_i; i_v <= iv_i; end
    end

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
        .clk(clk), .rst_n(rst_n),
        .w_en_i(c_v[1]), .w_half_i(c_d[2]), .w_cnt_i(c_d[10:3]), .w_pad_i(c_pad), .w_g(w_g),
        .r_half_i(c_d[11]), .r_c_i(c_d[19:12]), .sel_i(c_v[0]), .qk_ib(qk_x),
        .col(col), .eib(eib));

    // ---- tile (the 8 attention hard cores)
    wire            t_ov;
    wire [H*32-1:0] t_y;
    wire [H-1:0]    t_f;
    ot_hdc_v41x_attn_tile_s #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(FML), .F12(F12)) u_t (
        .clk(clk), .rst_n(rst_n), .ld_v(l_v), .ld_mode(l_mode), .ld_bank(l_bank),
        .ld_grp(l_grp), .ld_w(l_w), .ld_w2v(l_w2v), .iv(i_v), .ibank(i_bank),
        .ib(eib), .ov(t_ov), .oy(t_y), .oflt(t_f));

    // ---- p.v block merge (same module and alignment as the flat engine's g_m[k].g_real.g_x.u_m)
    wire            x_pv  = (MUT == 2) ? t_pv_i  : g_pv;
    wire            x_fin = (MUT == 2) ? t_fin_i : g_fin;
    wire [MLEV-1:0] x_blk = (MUT == 2) ? t_blk_i : g_blk;
    wire            mo_v;
    wire [H*32-1:0] mo_y;
    wire [H-1:0]    mo_f;
`ifdef OT_SVC_MERGE_H4
    ot_s81_svc_merge_h8_split #(.DPT(DPT), .MLEV(MLEV), .FPL(FX), .F12(F12)) u_m (
        .clk(clk), .rst_n(rst_n), .iv(t_ov && x_pv), .ifin(x_fin), .iblk(x_blk),
        .iy(t_y), .if_(t_f), .ov(mo_v), .oy(mo_y), .of_(mo_f));
`else
    ot_hdc_v41x_attn_merge_x #(.H(H), .DPT(DPT), .MLEV(MLEV), .FPL(FX), .F12(F12)) u_m (
        .clk(clk), .rst_n(rst_n), .iv(t_ov && x_pv), .ifin(x_fin), .iblk(x_blk),
        .iy(t_y), .if_(t_f), .ov(mo_v), .oy(mo_y), .of_(mo_f));
`endif

    // ---- output registers
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov <= 1'b0; m_ov <= 1'b0; end
        else begin ov <= t_ov; m_ov <= mo_v; end
    end
    always @(posedge clk) begin
        oy <= t_y; oflt <= t_f; m_y <= mo_y; m_f <= mo_f;
    end
endmodule
