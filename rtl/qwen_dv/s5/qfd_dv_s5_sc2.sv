`timescale 1ns/1ps
// =====================================================================================================================
// QW-SLICE7-LEAVES 10-20: qfd_dv_s5_sc2 -- structural successor of qfd_dv_s5_sc / scb (Q.STA.SLICE.2); originals
// untouched.  qfd_dv_scalar3 = qfd_dv_scalar2 (MU_NU > 1 production shape, MUT 0 / MU_MUT 0) with the same values,
// order and protocol; what changes:
//   * argmax merge in two stages (scb's OT_QFD_DV_SAFE_STORAGE structure) with the edge's three candidates compared
//     IN PARALLEL (three better() at once + a 2-level select; was two chained 57-b compares, scb 877 ps / sc 1030 ps).
//   * PSUM tree / fused mul / eps add / rsqrt use the bit-identical ot_hdc_fp32_add_lat #(LA) / _mul_lat #(LM), DRST 0
//     (valid bits reset only); rsqrt delay lines are the kept exact-age rings (qfd_dv_s5_dly2).
//   * the 32 root slots s[] are plain data flops (no reset term; cfg_v still clears them).
//   * every input lands in one face register and every output leaves from a face register here (kit pin wrapper OFF:
//     same in+1 / out+1 as the old kit).  Fanout <= 32 by tools/qwen_dv/bound_math_netlist.py on this source.
// PRICE vs the old kit qfd_dv_s5_sc (edges, steady state):
//   chain pass words, own PSUM / AMI / AMV / own RB words, RB taps, non-root TOK latch: +0
//   root argmax merge -> tok_* and the TOK broadcast word: +2 (edge-candidate landing stage + candidate stage)
//   root total -> w1 (fuse 0): +5 (LA - 3)                       (LA 4)
//   root fused r -> RB broadcast word + w1: +5(LA-3) + (LM-3) + (LA-3) + 3 (3(LM-3) + (LA-3))   (LA 4, LM 4: 19)
//   config (sc_cfg -> cfg registers): +1 (two face landing stages, QW-S5-SCRED 10-21)
//   boot only: reset release +4 (relay stages rc, rd, re, rf) and ring phase reset release +2.
// Schedule constraint: cfg_v (landed +1) is not issued within 3 edges of root argmax / PSUM traffic.
// OT_S5_SC2_MUT (bench witness, must FAIL): the broadcast scalar tap reads window 10.
// =====================================================================================================================

module ot_hdc_rsqrt_q2 #(parameter integer LA = 4, parameter integer LM = 4, parameter integer ID = 0) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer IT = 3 * LM + LA;
    localparam integer DEPTH = 1 + 3 * IT;
    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];
    reg [31:0] y0;
    always @(posedge clk) y0 <= 32'h5F3759DF - {1'b0, x[31:1]};
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    wire [1:0]  e [0:12];
    wire [12:0] ov;
    ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(0)) m_half (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(x), .b(32'h3F000000),
        .y(half), .err(e[12]), .valid_out(ov[12]));
    ot_hdc_delay #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                qfd_dv_s5_dly2 #(.W(32), .D(IT), .ID(ID * 8 + k)) d_h (.ck(clk), .rstn_i(rst_n), .d(hd[k]), .q(hd[k+1]));
            end
            ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(0)) m_yy (.clk(clk), .rst_n(rst_n), .valid_in(vd[1 + IT*k]),
                .a(yi[k]), .b(yi[k]), .y(yy[k]), .err(e[4*k]), .valid_out(ov[4*k]));
            ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(0)) m_hm (.clk(clk), .rst_n(rst_n), .valid_in(vd[1 + IT*k + LM]),
                .a(hd[k]), .b(yy[k]), .y(hm[k]), .err(e[4*k+1]), .valid_out(ov[4*k+1]));
            ot_hdc_fp32_add_lat #(.LAT(LA), .DRST(0)) a_s (.clk(clk), .rst_n(rst_n), .valid_in(vd[1 + IT*k + 2*LM]),
                .a(32'h3FC00000), .b({~hm[k][31], hm[k][30:0]}), .y(s[k]), .err(e[4*k+2]), .valid_out(ov[4*k+2]));
            qfd_dv_s5_dly2 #(.W(32), .D(2*LM + LA), .ID(ID * 8 + 4 + k)) d_y (.ck(clk), .rstn_i(rst_n), .d(yi[k]), .q(yd[k]));
            ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(0)) m_y (.clk(clk), .rst_n(rst_n), .valid_in(vd[1 + IT*k + 2*LM + LA]),
                .a(yd[k]), .b(s[k]), .y(yi[k+1]), .err(e[4*k+3]), .valid_out(ov[4*k+3]));
        end
        for (k = 0; k < 13; k = k + 1) begin : g_f
            assign f[k] = ov[k] && (e[k] != 2'd0);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

module qfd_dv_scalar3 #(
    parameter integer MU_NU = 4,
    parameter integer LA = 4,
    parameter integer LM = 4
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_v,
    input  wire          cfg_root,
    input  wire          cfg_rdir,
    input  wire [5:0]    cfg_nb,
    input  wire [23:0]   cfg_ss,
    input  wire          cfg_fuse,
    input  wire [23:0]   cfg_rx,
    input  wire [31:0]   cfg_eps,
    input  wire [4:0]    cfg_k,
    input  wire [5:0]    cfg_amnb,
    input  wire [47:0]   dn_i,
    output reg  [47:0]   dn_o,
    input  wire [47:0]   up_i,
    output reg  [47:0]   up_o,
    input  wire          ps_v,
    input  wire [23:0]   ps_idx,
    input  wire [31:0]   ps_val,
    input  wire          rb_v,
    input  wire [31:0]   rb_val,
    input  wire          am_v,
    input  wire [23:0]   am_idx,
    input  wire [31:0]   am_val,
    input  wire [1:0]    am_u,
    output reg           w1_we,
    output reg  [23:0]   w1_addr,
    output reg  [31:0]   w1_data,
    output reg           tok_v,
    output reg  [23:0]   tok_idx,
    output reg           tok_own,
    output reg  [31:0]   tok_val,
    output reg  [1:0]    tok_user,
    output reg           busy,
    output reg           fault
);
    localparam [2:0] K_PSUM = 3'd1, K_RB = 3'd2, K_AMI = 3'd3, K_AMV = 3'd4, K_TOK = 3'd5;
    reg        root, rdir, fuse; reg [5:0] nb, amnb; reg [23:0] ss, rx; reg [31:0] eps; reg [4:0] kk;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin root <= 1'b0; rdir <= 1'b0; nb <= 6'd0; ss <= 24'd0; fuse <= 1'b0; rx <= 24'd0;
                          eps <= 32'd0; kk <= 5'd0; amnb <= 6'd0; end
        else if (cfg_v) begin root <= cfg_root; rdir <= cfg_rdir; nb <= cfg_nb; ss <= cfg_ss; fuse <= cfg_fuse;
                              rx <= cfg_rx; eps <= cfg_eps; kk <= cfg_k; amnb <= cfg_amnb; end
    wire       dv = dn_i[47], uv = up_i[47];
    wire [2:0] dk = dn_i[46:44], uk = up_i[46:44];
    wire d_tw = dv && (dk == K_PSUM || dk == K_AMI || dk == K_AMV);
    wire u_tw = uv && (uk == K_PSUM || uk == K_AMI || uk == K_AMV);
    wire d_bc = dv && (dk == K_RB || dk == K_TOK), u_bc = uv && (uk == K_RB || uk == K_TOK);
    wire d_pass = (d_tw && !root) || d_bc;
    wire u_pass = (u_tw && !root) || u_bc;
    wire        rr_v; wire [31:0] rr_y;
    reg         tk_send;
    reg  [56:0] am_best;
    reg         am2;
    reg  [31:0] am2_val;
    reg  [1:0]  am2_u;
    wire [11:0] am_tag = (MU_NU > 1) ? {10'd0, am_u} : 12'd0;
    wire [11:0] am2_tag = (MU_NU > 1) ? {10'd0, am2_u} : 12'd0;
    wire [11:0] tk_tag = (MU_NU > 1) ? {10'd0, tok_user} : 12'd0;
    wire        own_tw = (ps_v || am_v || am2) && !root;
    wire [47:0] own_tw_w = ps_v ? {1'b1, K_PSUM, ps_idx[11:0], ps_val} :
                           am_v ? {1'b1, K_AMI, am_tag, 8'd0, am_idx} : {1'b1, K_AMV, am2_tag, am2_val};
    wire        own_bc = rb_v || rr_v || tk_send;
    wire [23:0] tk_index = tok_idx;
    wire [47:0] own_bc_w = rb_v ? {1'b1, K_RB, 12'd0, rb_val} : rr_v ? {1'b1, K_RB, 12'd0, rr_y} :
                           {1'b1, K_TOK, tk_tag, 8'd0, tk_index};
    always @(posedge ck or negedge rst_n)
        if (!rst_n) am2 <= 1'b0;
        else am2 <= am_v && !root;
    always @(posedge ck) begin am2_val <= am_val; am2_u <= (MU_NU > 1) ? am_u : 2'd0; end
    reg dn_ov, up_ov;
    always @(posedge ck) begin
        dn_o <= d_pass ? dn_i : (own_tw && !rdir) ? own_tw_w : own_bc ? own_bc_w : 48'd0;
        up_o <= u_pass ? up_i : (own_tw && rdir) ? own_tw_w : own_bc ? own_bc_w : 48'd0;
    end
    // -------------------------------------------------------------- root slots (data flops; cfg_v clears)
    reg [31:0] s [0:31];
    reg [5:0]  cnt;
    reg        trig;
    wire       d_ps = dv && dk == K_PSUM && root, u_ps = uv && uk == K_PSUM && root, o_ps = ps_v && root;
    integer k;
    wire [5:0] cnt_n = cnt + (d_ps ? 6'd1 : 6'd0) + (u_ps ? 6'd1 : 6'd0) + (o_ps ? 6'd1 : 6'd0);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin cnt <= 6'd0; trig <= 1'b0; end
        else begin
            trig <= 1'b0;
            if (cfg_v) cnt <= 6'd0;
            else if ((d_ps || u_ps || o_ps) && cnt_n == nb && nb != 6'd0) begin trig <= 1'b1; cnt <= 6'd0; end
            else cnt <= cnt_n;
        end
    end
    always @(posedge ck) begin
        if (cfg_v) begin
            for (k = 0; k < 32; k = k + 1) s[k] <= 32'd0;
        end else begin
            if (d_ps) s[dn_i[36:32]] <= dn_i[31:0];
            if (u_ps) s[up_i[36:32]] <= up_i[31:0];
            if (o_ps) s[ps_idx[4:0]] <= ps_val;
        end
    end
    // -------------------------------------------------------------- pipelined pairwise tree (LA per level)
    wire [31:0] total;
    wire        tot_v;
    wire [31:0] tf;
    genvar g, lv;
    generate begin : g_tree
        wire [32*32-1:0] lvl [0:5];
        wire [5:0] lvv;
        for (g = 0; g < 32; g = g + 1) begin : g_l0
            assign lvl[0][32*g +: 32] = s[g];
        end
        assign lvv[0] = trig;
        for (lv = 1; lv <= 5; lv = lv + 1) begin : g_lv
            for (g = 0; g < (32 >> lv); g = g + 1) begin : g_p
                wire [1:0] e; wire vo;
                ot_hdc_fp32_add_lat #(.LAT(LA), .DRST(0)) u_a (.clk(ck), .rst_n(rst_n), .valid_in(lvv[lv-1]),
                    .a(lvl[lv-1][32*(2*g) +: 32]), .b(lvl[lv-1][32*(2*g+1) +: 32]), .y(lvl[lv][32*g +: 32]),
                    .err(e), .valid_out(vo));
                assign tf[(32 - (64 >> lv)) + g] = vo && (e != 2'd0);
            end
            if ((32 >> lv) < 32) begin : g_z
                assign lvl[lv][32*32-1 : 32*(32 >> lv)] = 0;
            end
            wire [LA:0] vd;
            ot_hdc_vline #(.D(LA)) u_v (.clk(ck), .rst_n(rst_n), .v(lvv[lv-1]), .vd(vd));
            assign lvv[lv] = vd[LA];
        end
        assign tf[31] = 1'b0;
        assign total = lvl[5][31:0];
        assign tot_v = lvv[5];
    end endgenerate
    // -------------------------------------------------------------- fused r
    wire [31:0] p1, p2;
    wire        f1, f2, f3;
    wire [LM:0] vd1;
    wire [LA:0] vd2;
    wire [1:0]  e1, e2;
    wire        o1, o2;
    wire [31:0] inv_n = {1'b0, 8'd127 - {3'd0, kk}, 23'd0};
    ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(0)) u_m (.clk(ck), .rst_n(rst_n), .valid_in(tot_v && fuse), .a(total), .b(inv_n),
        .y(p1), .err(e1), .valid_out(o1));
    assign f1 = o1 && (e1 != 2'd0);
    ot_hdc_vline #(.D(LM)) u_v1 (.clk(ck), .rst_n(rst_n), .v(tot_v && fuse), .vd(vd1));
    ot_hdc_fp32_add_lat #(.LAT(LA), .DRST(0)) u_e (.clk(ck), .rst_n(rst_n), .valid_in(vd1[LM]), .a(p1), .b(eps),
        .y(p2), .err(e2), .valid_out(o2));
    assign f2 = o2 && (e2 != 2'd0);
    ot_hdc_vline #(.D(LA)) u_v2 (.clk(ck), .rst_n(rst_n), .v(vd1[LM]), .vd(vd2));
    ot_hdc_rsqrt_q2 #(.LA(LA), .LM(LM), .ID(900)) u_r (.clk(ck), .rst_n(rst_n), .v(vd2[LA]), .x(p2), .y(rr_y), .vo(rr_v), .fault(f3));
    // -------------------------------------------------------------- argmax merge (root), two stages
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic better(input [56:0] a, input [56:0] b);
        better = a[56] && (!b[56] || okey(a[31:0]) > okey(b[31:0]) ||
                 (okey(a[31:0]) == okey(b[31:0]) && a[55:32] < b[55:32]));
    endfunction
    reg  [23:0] di, ui;
    wire        d_amv = dv && dk == K_AMV && root, u_amv = uv && uk == K_AMV && root, o_am = am_v && root;
    wire [56:0] cd = {1'b1, di, dn_i[31:0]}, cu = {1'b1, ui, up_i[31:0]}, co = {1'b1, am_idx, am_val};
    reg [5:0] amc;
    // QW-S5-SCRED 10-21: the gated edge candidates land in a register stage before the three parallel compares
    // (mapped TT 643.5 ps / 22 lv was face reg -> AMV decode -> gate -> okey -> 57-b compare -> select -> candidate).
    // Every argmax-derived signal moves +1 edge together (merge -> tok / TOK broadcast +2 vs the old kit).
    wire [56:0] cdi_c = d_amv ? cd : 57'd0, cui_c = u_amv ? cu : 57'd0, coi_c = o_am ? co : 57'd0;
    reg  [56:0] cdi, cui, coi;
    reg         d_amv_r, u_amv_r, o_am_r;
    reg  [1:0]  du_r, uu_r, au_r;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin d_amv_r <= 1'b0; u_amv_r <= 1'b0; o_am_r <= 1'b0; end
        else if (cfg_v) begin d_amv_r <= 1'b0; u_amv_r <= 1'b0; o_am_r <= 1'b0; end
        else begin d_amv_r <= d_amv; u_amv_r <= u_amv; o_am_r <= o_am; end
    always @(posedge ck) begin cdi <= cdi_c; cui <= cui_c; coi <= coi_c; du_r <= dn_i[33:32]; uu_r <= up_i[33:32]; au_r <= am_u; end
    // three compares in parallel; select == scb's better(coi, better(cdi,cui) ? cdi : cui) chain exactly
    wire b_du = better(cdi, cui), b_od = better(coi, cdi), b_ou = better(coi, cui);
    wire o_win = b_du ? b_od : b_ou;
    wire [56:0] edge_best = o_win ? coi : (b_du ? cdi : cui);
    wire [1:0] edge_user = d_amv_r ? du_r : u_amv_r ? uu_r : au_r;
    wire edge_mix = (d_amv_r && du_r != edge_user) ||
                    (u_amv_r && uu_r != edge_user) || (o_am_r && au_r != edge_user);
    reg [56:0] candidate;
    reg [1:0] candidate_user;
    reg [1:0] candidate_count;
    reg candidate_v, candidate_mix;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin candidate_v <= 0; candidate_count <= 0; candidate_mix <= 0; end
        else if (cfg_v) begin candidate_v <= 0; candidate_count <= 0; candidate_mix <= 0; end
        else begin candidate_v <= d_amv_r || u_amv_r || o_am_r;
            candidate_count <= {1'b0, d_amv_r} + {1'b0, u_amv_r} + {1'b0, o_am_r};
            candidate_mix <= edge_mix; end
    always @(posedge ck) begin candidate <= edge_best; candidate_user <= edge_user; end
    wire [56:0] m3 = better(candidate, am_best) ? candidate : am_best;
    wire [5:0] amc_n = amc + {4'd0, candidate_count};
    wire a_any = candidate_v;
    wire [1:0] f_u = candidate_user;
    reg [1:0] mg_u;
    wire [1:0] cur_u = (amc == 0) ? f_u : mg_u;
    wire am_mix = (MU_NU > 1) && a_any && (candidate_mix || (f_u != cur_u));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) mg_u <= 2'd0;
        else if (MU_NU > 1 && a_any && amc == 6'd0 && !cfg_v) mg_u <= f_u;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin am_best <= 57'd0; amc <= 6'd0; tk_send <= 1'b0; tok_v <= 1'b0; tok_idx <= 24'd0;
                          di <= 24'd0; ui <= 24'd0; tok_own <= 1'b0; tok_val <= 32'd0; tok_user <= 2'd0; end
        else begin
            tk_send <= 1'b0; tok_v <= 1'b0; tok_own <= 1'b0;
            if (dv && dk == K_AMI && root) di <= dn_i[23:0];
            if (uv && uk == K_AMI && root) ui <= up_i[23:0];
            if (cfg_v) begin am_best <= 57'd0; amc <= 6'd0; end
            else if (a_any) begin
                am_best <= m3;
                if (amc_n == amnb && amnb != 6'd0) begin amc <= 6'd0; tk_send <= 1'b1; tok_v <= 1'b1; tok_idx <= m3[55:32];
                                                          tok_own <= 1'b1; tok_val <= m3[31:0];
                                                          if (MU_NU > 1) tok_user <= cur_u;
                                                          if (MU_NU > 1) am_best <= 57'd0; end
                else amc <= amc_n;
            end
            if (!root && dv && dk == K_TOK) begin tok_v <= 1'b1; tok_idx <= dn_i[23:0]; if (MU_NU > 1) tok_user <= dn_i[33:32]; end
            if (!root && uv && uk == K_TOK) begin tok_v <= 1'b1; tok_idx <= up_i[23:0]; if (MU_NU > 1) tok_user <= up_i[33:32]; end
        end
    // -------------------------------------------------------------- VM writes
    wire tap_rb = (dv && dk == K_RB) || (uv && uk == K_RB);
    wire [31:0] rb_in = (dv && dk == K_RB) ? dn_i[31:0] : up_i[31:0];
    wire tot_w = tot_v && !fuse;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) w1_we <= 1'b0;
        else w1_we <= tap_rb || tot_w || rr_v;
    always @(posedge ck) begin
        w1_addr <= (tap_rb || rr_v) ? rx : ss;
        w1_data <= tap_rb ? rb_in : rr_v ? rr_y : total;
    end
    reg [6:0] bc;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin bc <= 7'd0; busy <= 1'b0; end
        else begin
            bc <= trig ? 7'd127 : (bc != 0 && (tot_w || rr_v)) ? 7'd0 : bc;
            busy <= trig || (bc != 0);
        end
    wire bad = (d_pass && ((own_tw && !rdir) || own_bc)) || (u_pass && ((own_tw && rdir) || own_bc)) ||
               (own_tw && own_bc) || (ps_v && (am_v || am2)) || (rb_v && rr_v) || (tk_send && (rb_v || rr_v)) ||
               ((dv && (dk == 3'd0 || dk > K_TOK)) || (uv && (uk == 3'd0 || uk > K_TOK))) ||
               ((dv && dk == K_RB) && (uv && uk == K_RB)) || (tap_rb && (tot_w || rr_v)) || (tot_w && rr_v) ||
               ((d_ps || u_ps || o_ps) && trig) || (tot_v && |tf) || (vd1[LM] && f1) || (vd2[LA] && f2) || (rr_v && f3) ||
               (d_ps && dn_i[37:32] >= nb && nb != 6'd32) || (u_ps && up_i[37:32] >= nb && nb != 6'd32) ||
               (o_ps && (ps_idx[23:5] != 0 || ps_idx[5:0] >= nb && nb != 6'd32)) ||
               am_mix;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | bad;
endmodule

// ---------------------------------------------------------------------------------------------------------- sc2 leaf
module qfd_dv_s5_sc2 #(parameter integer MU_NU = 4, parameter integer LA = 4, parameter integer LM = 4) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [100:0]   sc_cfg,
    input  wire [47:0]    dn_i,
    output reg  [47:0]    dn_o,
    input  wire [47:0]    up_i,
    output reg  [47:0]    up_o,
    input  wire           red_we,
    input  wire [23:0]    red_addr,
    input  wire [31:0]    red_data,
    input  wire [7:0]     vm_we,
    input  wire [1:0]     vm_win0,
    input  wire [31:0]    vm_wdata0,
    input  wire           am_v,
    input  wire [23:0]    am_idx,
    input  wire [31:0]    am_val,
    input  wire [1:0]     am_u,
    output reg            w1_we,
    output reg  [23:0]    w1_addr,
    output reg  [31:0]    w1_data,
    output reg            tok_v,
    output reg  [23:0]    tok_idx,
    output reg            tok_own,
    output reg  [31:0]    tok_val,
    output reg  [1:0]     tok_user,
    output reg            busy,
    output reg            fault
);
    wire rst_f;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_f));
    // third reset stage (as qfd_dv_s5_red's rc): the landed reset drives ONE register, which the fanout constructor
    // replicates into <= 32-load relays (assertion async, release +1 edge, boot only)
    reg rc;
    always @(posedge ck or negedge rst_f) if (!rst_f) rc <= 1'b0; else rc <= 1'b1;
    // reset relay stages rd.. (QW-S5-SCRED 10-21): with the cfg_v landing the leaf has > 1.8k reset sinks, so one relay
    // level (rc copies <= 8 loads, rs2 copies <= 8 rc copies) still puts > 32 rs2 copies on the raw rst_n pin; the extra
    // async-chained level keeps rst_n <= ~N/512 loads.  Boot only: reset release +1.
    // (cap-8 construction measured > 16k weighted reset loads: rd, re, rf = three async-chained relay levels after rc)
    reg rd, re, rf;
    always @(posedge ck or negedge rc) if (!rc) rd <= 1'b0; else rd <= 1'b1;
    always @(posedge ck or negedge rd) if (!rd) re <= 1'b0; else re <= 1'b1;
    always @(posedge ck or negedge re) if (!re) rf <= 1'b0; else rf <= 1'b1;
    wire rst = rf;
    // face input registers: valid / strobe bits reset, data plain
    // sc_cfg lands in TWO face stages (QW-S5-SCRED 10-21): cfg_v enables the clear/load of ~1.2k root-slot and cfg bits,
    // so its landed register needs >32 kept copies; a single face register would put all of them on the raw input pin
    // (bound_math_netlist: "input bit exceeds 32 loads").  Price: config apply +1 edge (config only, static schedule).
    reg [100:0] f_cfg0;
    reg [100:0] f_cfg; reg [47:0] f_dn, f_up; reg f_rwe; reg [23:0] f_raddr; reg [31:0] f_rdata;
    reg [7:0] f_vwe; reg [1:0] f_vwin; reg [31:0] f_vwd; reg f_amv; reg [23:0] f_ami; reg [31:0] f_amval; reg [1:0] f_amu;
    always @(posedge ck or negedge rst)
        if (!rst) begin f_cfg0[100] <= 1'b0; f_cfg[100] <= 1'b0; f_dn[47] <= 1'b0; f_up[47] <= 1'b0; f_rwe <= 1'b0; f_vwe <= 8'd0; f_amv <= 1'b0; end
        else begin f_cfg0[100] <= sc_cfg[100]; f_cfg[100] <= f_cfg0[100]; f_dn[47] <= dn_i[47]; f_up[47] <= up_i[47]; f_rwe <= red_we; f_vwe <= vm_we;
                   f_amv <= am_v; end
    always @(posedge ck) begin
        f_cfg0[99:0] <= sc_cfg[99:0]; f_cfg[99:0] <= f_cfg0[99:0]; f_dn[46:0] <= dn_i[46:0]; f_up[46:0] <= up_i[46:0]; f_raddr <= red_addr;
        f_rdata <= red_data; f_vwin <= vm_win0; f_vwd <= vm_wdata0; f_ami <= am_idx; f_amval <= am_val; f_amu <= am_u;
    end
    wire red_ps = f_rwe && f_raddr[23:22] == 2'b11;
`ifdef OT_S5_SC2_MUT
    wire su_rb = (|f_vwe) && f_vwin == 2'b10;
`else
    wire su_rb = (|f_vwe) && f_vwin == 2'b11;
`endif
    wire [47:0] c_dn_o, c_up_o; wire c_w1_we, c_tok_v, c_tok_own, c_busy, c_fault;
    wire [23:0] c_w1_addr, c_tok_idx; wire [31:0] c_w1_data, c_tok_val; wire [1:0] c_tok_user;
    qfd_dv_scalar3 #(.MU_NU(MU_NU), .LA(LA), .LM(LM)) u_sc (.ck(ck), .rst_n(rst),
        .cfg_v(f_cfg[100]), .cfg_root(f_cfg[99]), .cfg_rdir(f_cfg[98]), .cfg_nb(f_cfg[97:92]), .cfg_ss(f_cfg[91:68]),
        .cfg_fuse(f_cfg[67]), .cfg_rx(f_cfg[66:43]), .cfg_eps(f_cfg[42:11]), .cfg_k(f_cfg[10:6]), .cfg_amnb(f_cfg[5:0]),
        .dn_i(f_dn), .dn_o(c_dn_o), .up_i(f_up), .up_o(c_up_o),
        .ps_v(red_ps), .ps_idx({2'b00, f_raddr[21:0]}), .ps_val(f_rdata),
        .rb_v(su_rb), .rb_val(f_vwd),
        .am_v(f_amv), .am_idx(f_ami), .am_val(f_amval), .am_u(f_amu),
        .w1_we(c_w1_we), .w1_addr(c_w1_addr), .w1_data(c_w1_data), .tok_v(c_tok_v), .tok_idx(c_tok_idx),
        .tok_own(c_tok_own), .tok_val(c_tok_val), .tok_user(c_tok_user), .busy(c_busy), .fault(c_fault));
    // face output registers
    always @(posedge ck or negedge rst)
        if (!rst) begin dn_o[47] <= 1'b0; up_o[47] <= 1'b0; w1_we <= 1'b0; tok_v <= 1'b0; tok_own <= 1'b0; busy <= 1'b0;
                        fault <= 1'b0; end
        else begin dn_o[47] <= c_dn_o[47]; up_o[47] <= c_up_o[47]; w1_we <= c_w1_we; tok_v <= c_tok_v; tok_own <= c_tok_own;
                   busy <= c_busy; fault <= c_fault; end
    always @(posedge ck) begin
        dn_o[46:0] <= c_dn_o[46:0]; up_o[46:0] <= c_up_o[46:0]; w1_addr <= c_w1_addr; w1_data <= c_w1_data;
        tok_idx <= c_tok_idx; tok_val <= c_tok_val; tok_user <= c_tok_user;
    end
endmodule
