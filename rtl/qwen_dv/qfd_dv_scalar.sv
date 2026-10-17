`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_scalar -- the Q-DV slice's scalar-tree face and (when configured as root) the global-sum root.
//
// Scalar word (96 b):  [95] v, [94:92] kind (1 PSUM = a block partial sum, 2 RB = a broadcast scalar), [91:88] src
// slice, [87:64] idx (PSUM: block index 0..31; RB: the receivers' VM element address), [63:32] 0, [31:0] value.
// Port behaviour (static schedule; a pass word and an own word on the same edge is a sticky fault, never a stall):
//   in PSUM : root -> absorbed into its block slot; other slices -> passed on (registered, one edge)
//   in RB   : src == this slice -> absorbed (the ring has delivered it to every slice); else written into the local
//             VM at idx (w1) and passed on
//   own PSUM (the reducer's block sum, red window 11): root -> its block slot; else -> sent
//   own RB   (an SU write to window 11; the local VM write is done by the slice top) -> sent with src = this slice
// ROOT (step 2: pipelined): after `nb` block sums of the armed op are in (any order: filed by idx), a 5-level
// pipelined pairwise tree of ot_hdc_qadd (16 + 8 + 4 + 2 + 1, the SU's adder, LA 3) adds the 32 slots
// ((s0 + s1) + (s2 + s3)) + ... -- slots past nb hold +0, and x + (+0) = x exactly for every non-negative-zero x
// the adders produce (zero results are canonical +0), so the 32-slot tree equals the golden tree padded to
// p2ceil(nb) (R-ARITH: each block sum is an aligned 16-chunk subtree of the csum8 tree).  15 edges trigger -> total.
//   fuse 0: the total is written into the local VM at ss (w1); the SU then runs the rsqrt op.
//   fuse 1: the root itself forms r = rsqrt_q(qadd(qmul(total, 2^-k), eps)) -- the SU's op order and primitives
//           (MA_AIMM imm1 = 1/n = 2^-k, AD_IMM imm2 = eps, SFU_RSQRT) -- writes r into the local VM at rx and sends it
//           as an RB word: no SU op on the critical path.
// ARGMAX (LM head): kind 3 AMAX = a slice's running (max, lowest index) candidate {idx, value}; non-roots send theirs
// / pass others; the root merges am_nb candidates (larger value; equal values -> lower index; key order as the
// ot_qwen_me_spport_w12 argmax) and sends kind 4 TOK {idx, value} round the ring (absorbed at the root).
// MUT 1 (bench negative control): the root folds the block sums sequentially (((s0 + s1) + s2) + ...) (must FAIL).
// MUT 6 (bench negative control): level 1 pairs slot i with slot i + 16 instead of 2i with 2i + 1 (must FAIL).
// MUT 7 (bench negative control): argmax ties go to the HIGHER index (must FAIL).
// =====================================================================================================================
module qfd_dv_scalar #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [3:0]    sid,          // slice id (strap, pin-registered by the top)
    input  wire          cfg_v,
    input  wire          cfg_root,
    input  wire [5:0]    cfg_nb,       // 1 .. 32
    input  wire [23:0]   cfg_ss,
    input  wire          cfg_fuse,
    input  wire [23:0]   cfg_rx,
    input  wire [31:0]   cfg_eps,
    input  wire [4:0]    cfg_k,        // 1/n = 2^-k
    input  wire [5:0]    cfg_amnb,     // argmax candidates the root merges
    input  wire [95:0]   sc_i,         // pin-registered by the top
    output reg  [95:0]   sc_o,
    input  wire          ps_v,         // own block sum
    input  wire [23:0]   ps_idx,
    input  wire [31:0]   ps_val,
    input  wire          rb_v,         // own broadcast scalar
    input  wire [23:0]   rb_idx,
    input  wire [31:0]   rb_val,
    input  wire          am_v,         // own argmax candidate
    input  wire [23:0]   am_idx,
    input  wire [31:0]   am_val,
    output reg           w1_we,
    output reg  [23:0]   w1_addr,
    output reg  [31:0]   w1_data,
    output reg           tok_v,        // the merged token (root), also sent as a TOK word
    output reg  [23:0]   tok_idx,
    output reg           busy,
    output reg           fault
);
    localparam [2:0] K_PSUM = 3'd1, K_RB = 3'd2, K_AMAX = 3'd3, K_TOK = 3'd4;
    reg        root, fuse; reg [5:0] nb, amnb; reg [23:0] ss, rx; reg [31:0] eps; reg [4:0] kk;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin root <= 1'b0; nb <= 6'd0; ss <= 24'd0; fuse <= 1'b0; rx <= 24'd0; eps <= 32'd0; kk <= 5'd0;
                          amnb <= 6'd0; end
        else if (cfg_v) begin root <= cfg_root; nb <= cfg_nb; ss <= cfg_ss; fuse <= cfg_fuse; rx <= cfg_rx;
                              eps <= cfg_eps; kk <= cfg_k; amnb <= cfg_amnb; end
    wire        iv = sc_i[95];
    wire [2:0]  ik = sc_i[94:92];
    wire [3:0]  is = sc_i[91:88];
    wire        in_ps = iv && ik == K_PSUM;
    wire        in_rb = iv && ik == K_RB;
    wire        in_am = iv && ik == K_AMAX;
    wire        in_tk = iv && ik == K_TOK;
    wire        pass = (in_ps && !root) || (in_rb && is != sid) || (in_am && !root) || (in_tk && is != sid);
    wire        own_ps_out = ps_v && !root;
    wire        own_am_out = am_v && !root;
    // fused r and the merged token leave from the root as own words
    wire        rr_v;  wire [31:0] rr_y;
    reg         tk_send;
    reg  [56:0] am_best;           // {valid, idx 24, value 32}
    // -------------------------------------------------------------- the out port
    always @(posedge ck or negedge rst_n)
        if (!rst_n) sc_o <= 96'd0;
        else if (pass) sc_o <= sc_i;
        else if (own_ps_out) sc_o <= {1'b1, K_PSUM, sid, ps_idx, 32'd0, ps_val};
        else if (rb_v) sc_o <= {1'b1, K_RB, sid, rb_idx, 32'd0, rb_val};
        else if (rr_v) sc_o <= {1'b1, K_RB, sid, rx, 32'd0, rr_y};
        else if (own_am_out) sc_o <= {1'b1, K_AMAX, sid, am_idx, 32'd0, am_val};
        else if (tk_send) sc_o <= {1'b1, K_TOK, sid, am_best[55:32], 32'd0, am_best[31:0]};
        else sc_o <= 96'd0;
    // -------------------------------------------------------------- root slots
    reg [31:0] s [0:31];
    reg [5:0]  cnt;
    reg        trig;
    wire       in_root = in_ps && root;
    wire       own_root = ps_v && root;
    integer k;
    wire [5:0] cnt_n = cnt + (in_root ? 6'd1 : 6'd0) + (own_root ? 6'd1 : 6'd0);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin cnt <= 6'd0; trig <= 1'b0; end
        else begin
            trig <= 1'b0;
            if (cfg_v) begin
                cnt <= 6'd0;
                for (k = 0; k < 32; k = k + 1) s[k] <= 32'd0;
            end else begin
                if (in_root) s[sc_i[68:64]] <= sc_i[31:0];
                if (own_root) s[ps_idx[4:0]] <= ps_val;
                if ((in_root || own_root) && cnt_n == nb && nb != 6'd0) begin trig <= 1'b1; cnt <= 6'd0; end
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
    // -------------------------------------------------------------- argmax merge (root)
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic better(input [56:0] a, input [56:0] b);   // a strictly preferred over b
        better = a[56] && (!b[56] || okey(a[31:0]) > okey(b[31:0]) ||
                 (okey(a[31:0]) == okey(b[31:0]) && ((MUT == 7) ? a[55:32] > b[55:32] : a[55:32] < b[55:32])));
    endfunction
    wire        in_amr = in_am && root, own_amr = am_v && root;
    wire [56:0] ca = {1'b1, sc_i[87:64], sc_i[31:0]}, cb = {1'b1, am_idx, am_val};
    wire [56:0] m1 = (in_amr && better(ca, am_best)) ? ca : am_best;
    wire [56:0] m2 = (own_amr && better(cb, m1)) ? cb : m1;
    reg  [5:0]  amc;
    wire [5:0]  amc_n = amc + (in_amr ? 6'd1 : 6'd0) + (own_amr ? 6'd1 : 6'd0);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin am_best <= 57'd0; amc <= 6'd0; tk_send <= 1'b0; tok_v <= 1'b0; tok_idx <= 24'd0; end
        else begin
            tk_send <= 1'b0; tok_v <= 1'b0;
            if (cfg_v) begin am_best <= 57'd0; amc <= 6'd0; end
            else if (in_amr || own_amr) begin
                am_best <= m2;
                if (amc_n == amnb && amnb != 6'd0) begin amc <= 6'd0; tk_send <= 1'b1; tok_v <= 1'b1; tok_idx <= m2[55:32]; end
                else amc <= amc_n;
            end
        end
    // -------------------------------------------------------------- VM writes: RB tap, root total, fused r
    wire tap_rb = in_rb && is != sid;
    wire tot_w = tot_v && !fuse;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) w1_we <= 1'b0;
        else w1_we <= tap_rb || tot_w || rr_v;
    always @(posedge ck) begin
        w1_addr <= tap_rb ? sc_i[87:64] : rr_v ? rx : ss;
        w1_data <= tap_rb ? sc_i[31:0] : rr_v ? rr_y : total;
    end
    reg [6:0] bc;                                   // root busy: trigger .. r out
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin bc <= 7'd0; busy <= 1'b0; end
        else begin
            bc <= trig ? 7'd127 : (bc != 0 && (tot_w || rr_v)) ? 7'd0 : bc;
            busy <= trig || (bc != 0);
        end
    // -------------------------------------------------------------- faults
    wire own_any = own_ps_out || rb_v || rr_v || own_am_out || tk_send;
    wire bad = (pass && own_any) ||
               ((own_ps_out ? 1 : 0) + (rb_v ? 1 : 0) + (rr_v ? 1 : 0) + (own_am_out ? 1 : 0) + (tk_send ? 1 : 0) > 1) ||
               (tap_rb && (tot_w || rr_v)) || (tot_w && rr_v) ||
               (iv && (ik == 3'd0 || ik > K_TOK)) || ((in_root || own_root) && trig) ||
               (tot_v && |tf) || (vd1[3] && f1) || (vd2[3] && f2) || (rr_v && f3) ||
               (in_root && (sc_i[87:69] != 0 || sc_i[68:64] >= {1'b0, nb[4:0]} && nb != 6'd32)) ||
               (own_root && (ps_idx[23:5] != 0 || ps_idx[4:0] >= {1'b0, nb[4:0]} && nb != 6'd32));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | bad;
endmodule
