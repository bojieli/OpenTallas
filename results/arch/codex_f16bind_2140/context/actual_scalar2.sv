`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_scalar2 -- slice2 scalar face: the 48-b scalar chain in both directions (sc_dn: toward W5, sc_up: toward
// E5) and the root's global sum / argmax merge (arithmetic exactly as qfd_dv_scalar: the same 5-level pipelined
// pairwise ot_hdc_qadd tree over 32 block slots, the fused r = rsqrt_q(qadd(qmul(total, 2^-k), eps))).
// Word (48 b): [47] v, [46:44] kind, [43:32] tag, [31:0] value.  Kinds: 1 PSUM (tag = block index), 2 RB (a broadcast
// scalar; receivers write it at their ROOT-cfg rx), 3 AMI + 4 AMV (an argmax candidate: index beat, then value beat on
// the next edge), 5 TOK (the merged token index).
// ROOT cfg: root, rdir (where the root is: 0 down / W5 side, 1 up / E5 side).  A non-root sends its PSUM / candidate
// toward the root and passes words travelling that way; the root absorbs them (from either side) and broadcasts RB /
// TOK both ways; every slice passes broadcast words on in their direction and taps RB into its VM.  One word per
// direction per edge (static schedule; a pass and an own word on one edge in one direction is a sticky fault).
// MUT 1 / 6 / 7: as qfd_dv_scalar (sequential fold / level-1 pairing / argmax ties to the higher index).
// MU_NU > 1 (MU-ADOPT-SLICE2 10-19, MU-QWEN R4): one token per user is merged back to back, so the root's argmax merge
//   restarts after each token (am_best / amc cleared on the token edge; the TOK broadcast takes the latched tok_idx)
//   instead of only at a ROOT cfg (a ROOT cfg per user token would also clear the PSUM slots of other users' reductions
//   in flight).  MU_NU 1: today, statement for statement.  MU_MUT 1 (bench only): no restart (the pre-fix behaviour).
// MU_NU > 1 user check (MU-QW-AMIX 10-19): "one token per user at the root at a time" is CHECKED, not only scheduled.
//   The candidate's user (am_u, from qfd_dv_amax_mu = the AMAX emit's cmd[9:8]) rides in the tag of the AMI and AMV
//   beats (tag[1:0] = word[33:32]; tag is 0 on these kinds at MU_NU 1).  The root opens a merge with the first
//   candidate after a token / ROOT cfg (amc == 0) and latches its user; a candidate of another user while the merge is
//   open (or two users' candidates on one edge) is a sticky fault (the fault output -> slice sc_fault / any_fault).
//   tok_user = the merge's user; the TOK broadcast carries it in its tag[1:0], non-root slices latch it as it passes.
//   MU_MUT 2 (bench only): the mixed-merge check is dropped.
// =====================================================================================================================
module qfd_dv_scalar2 #(
    parameter integer MUT = 0,
    parameter integer MU_NU = 1,
    parameter integer MU_MUT = 0
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
    input  wire [47:0]   dn_i,          // travelling down (from the up neighbour), pin-registered by the top
    output reg  [47:0]   dn_o,
    input  wire [47:0]   up_i,          // travelling up (from the down neighbour), pin-registered by the top
    output reg  [47:0]   up_o,
    input  wire          ps_v,
    input  wire [23:0]   ps_idx,
    input  wire [31:0]   ps_val,
    input  wire          rb_v,          // own broadcast scalar (SU window-11 write; the top writes the local VM)
    input  wire [31:0]   rb_val,
    input  wire          am_v,
    input  wire [23:0]   am_idx,
    input  wire [31:0]   am_val,
    input  wire [1:0]    am_u,          // user of the own candidate (MU_NU > 1; 0 at MU_NU 1)
    output reg           w1_we,
    output reg  [23:0]   w1_addr,
    output reg  [31:0]   w1_data,
    output reg           tok_v,
    output reg  [23:0]   tok_idx,
    output reg           tok_own,       // tok_v is this root's own die-wide merge (not a passing broadcast)
    output reg  [31:0]   tok_val,       // the merged value (root, with tok_own)
    output reg  [1:0]    tok_user,      // user of tok_idx (MU_NU > 1: the merge's user / the TOK tag; 0 at MU_NU 1)
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
    // -------------------------------------------------------------- arriving words (d: travelling down, u: up)
    wire       dv = dn_i[47], uv = up_i[47];
    wire [2:0] dk = dn_i[46:44], uk = up_i[46:44];
    wire d_tw = dv && (dk == K_PSUM || dk == K_AMI || dk == K_AMV);     // toward-root kinds
    wire u_tw = uv && (uk == K_PSUM || uk == K_AMI || uk == K_AMV);
    wire d_bc = dv && (dk == K_RB || dk == K_TOK), u_bc = uv && (uk == K_RB || uk == K_TOK);
    wire d_pass = (d_tw && !root) || d_bc;
    wire u_pass = (u_tw && !root) || u_bc;
    // -------------------------------------------------------------- own words
    wire        rr_v; wire [31:0] rr_y;
    reg         tk_send;
    reg  [56:0] am_best;
    reg         am2;                                // second (value) beat of the own candidate pending
    reg  [31:0] am2_val;
    reg  [1:0]  am2_u;
    wire [11:0] am_tag = (MU_NU > 1) ? {10'd0, am_u} : 12'd0;      // MU-QW-AMIX: the candidate's user
    wire [11:0] am2_tag = (MU_NU > 1) ? {10'd0, am2_u} : 12'd0;
    wire [11:0] tk_tag = (MU_NU > 1) ? {10'd0, tok_user} : 12'd0;
    wire        own_tw = (ps_v || am_v || am2) && !root;   // toward the root
    wire [47:0] own_tw_w = ps_v ? {1'b1, K_PSUM, ps_idx[11:0], ps_val} :
                           am_v ? {1'b1, K_AMI, am_tag, 8'd0, am_idx} : {1'b1, K_AMV, am2_tag, am2_val};
    wire        own_bc = rb_v || rr_v || tk_send;
`ifdef OT_QFD_DV_SAFE_STORAGE
    wire [23:0] tk_index = tok_idx;
`else
    wire [23:0] tk_index = (MU_NU > 1) ? tok_idx : am_best[55:32];
`endif
    wire [47:0] own_bc_w = rb_v ? {1'b1, K_RB, 12'd0, rb_val} : rr_v ? {1'b1, K_RB, 12'd0, rr_y} :
                           {1'b1, K_TOK, tk_tag, 8'd0, tk_index};
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin am2 <= 1'b0; am2_val <= 32'd0; am2_u <= 2'd0; end
        else begin am2 <= am_v && !root; am2_val <= am_val; am2_u <= (MU_NU > 1) ? am_u : 2'd0; end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin dn_o <= 48'd0; up_o <= 48'd0; end
        else begin
            dn_o <= d_pass ? dn_i : (own_tw && !rdir) ? own_tw_w : own_bc ? own_bc_w : 48'd0;
            up_o <= u_pass ? up_i : (own_tw && rdir) ? own_tw_w : own_bc ? own_bc_w : 48'd0;
        end
    // -------------------------------------------------------------- root slots
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
            if (cfg_v) begin
                cnt <= 6'd0;
                for (k = 0; k < 32; k = k + 1) s[k] <= 32'd0;
            end else begin
                if (d_ps) s[dn_i[36:32]] <= dn_i[31:0];
                if (u_ps) s[up_i[36:32]] <= up_i[31:0];
                if (o_ps) s[ps_idx[4:0]] <= ps_val;
                if ((d_ps || u_ps || o_ps) && cnt_n == nb && nb != 6'd0) begin trig <= 1'b1; cnt <= 6'd0; end
                else cnt <= cnt_n;
            end
        end
    end
    // -------------------------------------------------------------- the pipelined pairwise tree (or a mutant)
    wire [31:0] total;
    wire        tot_v;
    wire [31:0] tf;                                   // adder faults
    genvar g, lv;
    generate if (MUT == 1) begin : g_fold
        // mutant: sequential left fold, 31 chained adders
        wire [31:0] acc [0:31];
        wire [31:0] av_;
        assign acc[0] = s[0];
        assign av_[0] = trig;
        for (g = 1; g < 32; g = g + 1) begin : g_c
            wire [31:0] sd;
            ot_hdc_delay #(.W(32), .D(3 * (g - 1))) u_sd (.clk(ck), .rst_n(rst_n), .d(s[g]), .q(sd));
            ot_hdc_qadd #(.L(3)) u_a (.clk(ck), .rst_n(rst_n), .v(av_[g-1]), .a(acc[g-1]), .b(sd), .y(acc[g]), .fault(tf[g]));
            wire [3:0] vd;
            ot_hdc_vline #(.D(3)) u_v (.clk(ck), .rst_n(rst_n), .v(av_[g-1]), .vd(vd));
            assign av_[g] = vd[3];
        end
        assign tf[0] = 1'b0;
        assign total = acc[31];
        assign tot_v = av_[31];
    end else begin : g_tree
        wire [32*32-1:0] lvl [0:5];
        wire [5:0] lvv;
        for (g = 0; g < 32; g = g + 1) begin : g_l0
            assign lvl[0][32*g +: 32] = s[g];
        end
        assign lvv[0] = trig;
        for (lv = 1; lv <= 5; lv = lv + 1) begin : g_lv
            for (g = 0; g < (32 >> lv); g = g + 1) begin : g_p
                localparam integer IA = (MUT == 6 && lv == 1) ? g : 2 * g;
                localparam integer IB = (MUT == 6 && lv == 1) ? g + 16 : 2 * g + 1;
                ot_hdc_qadd #(.L(3)) u_a (.clk(ck), .rst_n(rst_n), .v(lvv[lv-1]),
                    .a(lvl[lv-1][32*IA +: 32]), .b(lvl[lv-1][32*IB +: 32]), .y(lvl[lv][32*g +: 32]),
                    .fault(tf[(32 - (64 >> lv)) + g]));
            end
            if ((32 >> lv) < 32) begin : g_z
                assign lvl[lv][32*32-1 : 32*(32 >> lv)] = 0;
            end
            wire [3:0] vd;
            ot_hdc_vline #(.D(3)) u_v (.clk(ck), .rst_n(rst_n), .v(lvv[lv-1]), .vd(vd));
            assign lvv[lv] = vd[3];
        end
        assign tf[31] = 1'b0;
        assign total = lvl[5][31:0];
        assign tot_v = lvv[5];
    end endgenerate
    // -------------------------------------------------------------- fused r: (total * 2^-k + eps) -> rsqrt_q
    wire [31:0] p1, p2;
    wire        f1, f2, f3, v2, v3;
    wire [3:0]  vd1, vd2;
    wire [31:0] inv_n = {1'b0, 8'd127 - {3'd0, kk}, 23'd0};
    ot_hdc_qmul #(.L(3)) u_m (.clk(ck), .rst_n(rst_n), .v(tot_v && fuse), .a(total), .b(inv_n), .y(p1), .fault(f1));
    ot_hdc_vline #(.D(3)) u_v1 (.clk(ck), .rst_n(rst_n), .v(tot_v && fuse), .vd(vd1));
    ot_hdc_qadd #(.L(3)) u_e (.clk(ck), .rst_n(rst_n), .v(vd1[3]), .a(p1), .b(eps), .y(p2), .fault(f2));
    ot_hdc_vline #(.D(3)) u_v2 (.clk(ck), .rst_n(rst_n), .v(vd1[3]), .vd(vd2));
    ot_hdc_rsqrt_q #(.LA(3), .LM(3)) u_r (.clk(ck), .rst_n(rst_n), .v(vd2[3]), .x(p2), .y(rr_y), .vo(rr_v), .fault(f3));
    // -------------------------------------------------------------- argmax merge (root): index beat, then value beat
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic better(input [56:0] a, input [56:0] b);
        better = a[56] && (!b[56] || okey(a[31:0]) > okey(b[31:0]) ||
                 (okey(a[31:0]) == okey(b[31:0]) && ((MUT == 7) ? a[55:32] > b[55:32] : a[55:32] < b[55:32])));
    endfunction
    reg  [23:0] di, ui;                              // latched index beats per direction
    wire        d_amv = dv && dk == K_AMV && root, u_amv = uv && uk == K_AMV && root, o_am = am_v && root;
    wire [56:0] cd = {1'b1, di, dn_i[31:0]}, cu = {1'b1, ui, up_i[31:0]}, co = {1'b1, am_idx, am_val};
    reg [5:0] amc;
`ifdef OT_QFD_DV_SAFE_STORAGE
    // Stage1 reduces only this edge's arriving candidates; stage2 merges that
    // registered winner with the running best. Feedback stays one edge, so
    // back-to-back arrivals and successive MU users sustain one group/edge.
    wire [56:0] cdi = d_amv ? cd : 57'd0, cui = u_amv ? cu : 57'd0, coi = o_am ? co : 57'd0;
    wire [56:0] pair_best = better(cdi,cui) ? cdi : cui;
    wire [56:0] edge_best = better(coi,pair_best) ? coi : pair_best;
    wire [1:0] edge_user = d_amv ? dn_i[33:32] : u_amv ? up_i[33:32] : am_u;
    wire edge_mix = (d_amv && dn_i[33:32] != edge_user) ||
                    (u_amv && up_i[33:32] != edge_user) || (o_am && am_u != edge_user);
    reg [56:0] candidate;
    reg [1:0] candidate_user;
    reg [1:0] candidate_count;
    reg candidate_v,candidate_mix;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin candidate_v<=0;candidate_count<=0;candidate_mix<=0; end
        else if (cfg_v) begin candidate_v<=0;candidate_count<=0;candidate_mix<=0; end
        else begin candidate_v<=d_amv||u_amv||o_am;
            candidate_count<={1'b0,d_amv}+{1'b0,u_amv}+{1'b0,o_am};
            candidate_mix<=edge_mix; end
    always @(posedge ck) begin candidate<=edge_best;candidate_user<=edge_user;end
    wire [56:0] m3 = better(candidate,am_best) ? candidate : am_best;
    wire [5:0] amc_n = amc + {4'd0,candidate_count};
    wire a_any = candidate_v;
    wire [1:0] f_u = candidate_user;
    reg [1:0] mg_u;
    wire [1:0] cur_u = (amc == 0) ? f_u : mg_u;
    wire am_mix = (MU_NU > 1) && (MU_MUT != 2) && a_any &&
                  (candidate_mix || (f_u != cur_u));
`else
    wire [56:0] m1 = (d_amv && better(cd, am_best)) ? cd : am_best;
    wire [56:0] m2 = (u_amv && better(cu, m1)) ? cu : m1;
    wire [56:0] m3 = (o_am && better(co, m2)) ? co : m2;
    wire [5:0]  amc_n = amc + (d_amv ? 6'd1 : 6'd0) + (u_amv ? 6'd1 : 6'd0) + (o_am ? 6'd1 : 6'd0);
    // MU-QW-AMIX (MU_NU > 1): the users of the arriving candidates (AMV tag[1:0]; own = am_u) and the open merge's user
    wire [1:0]  du = dn_i[33:32], uu = up_i[33:32];
    wire        a_any = d_amv || u_amv || o_am;
    wire [1:0]  f_u = d_amv ? du : u_amv ? uu : am_u;                 // user of this edge's first arriving candidate
    reg  [1:0]  mg_u;                                                 // user of the open merge (amc != 0)
    wire [1:0]  cur_u = (amc == 6'd0) ? f_u : mg_u;
    wire        am_mix = (MU_NU > 1) && (MU_MUT != 2) && a_any &&
                         ((d_amv && du != cur_u) || (u_amv && uu != cur_u) || (o_am && am_u != cur_u));
`endif
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
                                                          if (MU_NU > 1 && MU_MUT != 1) am_best <= 57'd0; end
                else amc <= amc_n;
            end
            // a non-root slice records the broadcast token as it passes
            if (!root && dv && dk == K_TOK) begin tok_v <= 1'b1; tok_idx <= dn_i[23:0]; if (MU_NU > 1) tok_user <= dn_i[33:32]; end
            if (!root && uv && uk == K_TOK) begin tok_v <= 1'b1; tok_idx <= up_i[23:0]; if (MU_NU > 1) tok_user <= up_i[33:32]; end
        end
    // -------------------------------------------------------------- VM writes: RB tap (either way), root total, fused r
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
    // -------------------------------------------------------------- faults
    wire bad = (d_pass && ((own_tw && !rdir) || own_bc)) || (u_pass && ((own_tw && rdir) || own_bc)) ||
               (own_tw && own_bc) || (ps_v && (am_v || am2)) || (rb_v && rr_v) || (tk_send && (rb_v || rr_v)) ||
               ((dv && (dk == 3'd0 || dk > K_TOK)) || (uv && (uk == 3'd0 || uk > K_TOK))) ||
               ((dv && dk == K_RB) && (uv && uk == K_RB)) || (tap_rb && (tot_w || rr_v)) || (tot_w && rr_v) ||
               ((d_ps || u_ps || o_ps) && trig) || (tot_v && |tf) || (vd1[3] && f1) || (vd2[3] && f2) || (rr_v && f3) ||
               (d_ps && dn_i[37:32] >= nb && nb != 6'd32) || (u_ps && up_i[37:32] >= nb && nb != 6'd32) ||
               (o_ps && (ps_idx[23:5] != 0 || ps_idx[5:0] >= nb && nb != 6'd32)) ||
               am_mix;                                          // MU-QW-AMIX: one merge holds two users' candidates
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | bad;
endmodule
