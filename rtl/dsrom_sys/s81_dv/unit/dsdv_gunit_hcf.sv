`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-1 (2026-10-17): dsdv_gunit_hcf -- the HC coefficient leaf groups of the S81-DV G-unit (L0 HP unpack + root
// store, L4 coefficient finish, L5 Sinkhorn tail).
//
// Function (tools/hdc_golden_v41.Model.hc_mixes, R-ARITH chunk8, every rounding the golden's), per hc_mixes job:
//     ss     = csum(mul(flat, flat))                  acc 24          flat = the 4-copy BF16 residual, K = 4 D = 20,480
//     proj_o = csum(mul(fn[o], flat))                 acc 0 .. 23     csum: chunks of 8 sequential from +0, the 2,560
//     r      = rsqrt(add(div(ss, K), eps))                            chunk sums by a pairwise tree padded to 4,096
//     mix_o  = mul(proj_o, r)
//     pre / post / comb + Sinkhorn(ITERS 20)          ot_hbm_hc_tail_unit_static (the codex exact tail, unchanged;
//                                                     ot_hdc_sinkhorn + its 42-kb seed ROM on the derived /SDIV clock)
// The 24 coefficients (pre 0..3, post 0..3, comb row-major) go back to every slice as six CTL row writes.
//
// HP BEAT (kind 7, PROPOSED here; S81-DV p4i must adopt it in the slice send path, ot_s81sl_xr send config kind 7):
// slice g (owner of elements [320 g, 320 g + 320) of each copy) holds, per accumulation and copy k, the 40 chunk sums
// [640 k + 40 g, + 40) of the golden tree; it sends the roots of the MAXIMAL ALIGNED subtrees of that range, in leaf
// order -- sizes (chunks) by g mod 4: 0 {32, 8}, 1 {8, 16, 16}, 2 {16, 16, 8}, 3 {8, 32} -- as two V beats per
// (accumulation, slice): the slice send format with
//     [40 +: 5] acc (0..23 fn row, 24 sum of squares), [45 +: 4] g, [49] h (copies 2h, 2h+1), [51:50] 0
//     [52 + 32 j +: 32]  j = 0..2 copy 2h's roots, j = 3..5 copy 2h+1's roots (unused words 0), j = 6 unused
// Static contract (assertions, never flow control): an accumulation's 32 beats form a WINDOW (any order, either rung
// direction, two in one cycle allowed); windows do not overlap; successive window completions are >= 20 edges apart;
// a job's 25 windows come in any accumulation order; a job's first beat comes after the previous job's mix phase.
//
// Finish datapath (the golden tree above the slice roots, exactly; every add one ot_dsrom_qadd, the same operands in
// the same association):
//   A  group (k, m) = slices 4m .. 4m+3 of copy k -> the 5 level-5 nodes (32 chunks) 20 k + 5 m + 0..4:
//        N0 = A32   N1 = (A8 + B8) + B16a   N2 = B16b + C16a   N3 = C16b + (C8 + D8)   N4 = D32
//      one group a cycle, 16 cycles an accumulation, 5 adders; nodes into an 80-word level-5 store
//   Q  quads of level-5 nodes -> level-7 nodes (128 chunks) 0..19, one a cycle, 3 adders
//   T  streaming levels 8..12 (one adder each): an odd node adds its stored left sibling, the last node when even adds
//      +0 (its right sibling is padding: the golden's own add(x, 0)), so 20 level-7 nodes -> the root
//   ss -> ot_dsrom_divc (/ 20,480) -> + eps -> ot_dsrom_rsqrt -> r;  mix phase: 24 multiplies, then the tail launch
// Configuration (cw, shared with the router; registered): table rows of set s = cw_a[8] (cw_a[9] = 0): 56 + 3 w + i =
// bases 8 i .. 8 i + 7 of which w (0 attn, 1 ffn); 62 = {norm eps [255:224], route_scale (router), ffn scales 2..0
// [191:96], attn scales 2..0 [95:0]}.  HC JOB (cw_a[9:8] = 2'b10, cw_a[0] = 1): cw_d {which [41], set [40], row
// [30:21], lmask [20:16], smask [15:0]}, armed before the job's first HP beat.
// fault (sticky): any contract breach above, a duplicate (g, h) or accumulation, reserved bits, an unarmed job, an
// adder / multiplier / divider / rsqrt / tail fault.  Every input lands in a flop; every output leaves a flop.
// MUT (bench only): 5 = group association N1 = A8 + (B8 + B16a); 6 = roots 1 / 2 of g = 1 mod 4 swapped (B16a <-> B16b);
// 7 = the r chain skips + eps.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_hcf #(
    parameter integer V    = 276,
    parameter integer LA   = 4,
    parameter integer LM   = 5,
    parameter integer NSET = 2,
    parameter integer SDIV = 8,                         // Sinkhorn clock divider (0.833 ns x 8 = 6.67 ns >= 6.58 routed)
    parameter integer MUT  = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire          ha_v, input wire [V-1:0] ha_b,     // HP beats tapped northbound / southbound
    input  wire          hb_v, input wire [V-1:0] hb_b,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d,
    output reg           ct_v,
    output reg  [V-1:0]  ct_b,
    output reg           fault
);
    localparam integer SB = (NSET > 1) ? $clog2(NSET) : 1;
    localparam integer NACC = 25;
    integer i, j;
    // ---------------------------------------------------------------- input flops
    reg av, bv, wv; reg [V-1:0] ab, bb; reg [9:0] wa; reg [255:0] wd; reg [3:0] sid_c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin av <= 1'b0; bv <= 1'b0; wv <= 1'b0; end
        else begin av <= ha_v; bv <= hb_v; wv <= cw_v; end
    always @(posedge clk) begin ab <= ha_b; bb <= hb_b; wa <= cw_a; wd <= cw_d; sid_c <= sid; end
    wire [SB-1:0] wset = (NSET > 1) ? wa[8 +: SB] : {SB{1'b0}};
    // ---------------------------------------------------------------- tables: bases, scales, eps
    reg [31:0] base_t [0:NSET*48-1];                    // [set][which][24]
    reg [95:0] scl_t  [0:NSET*2-1];
    reg [31:0] eps_t  [0:NSET-1];
    always @(posedge clk) if (wv && !wa[9]) begin
        if (wa[5:0] >= 6'd56 && wa[5:0] < 6'd62)
            for (j = 0; j < 8; j = j + 1) base_t[48 * wset + 8 * (wa[5:0] - 6'd56) + j] <= wd[32 * j +: 32];
        if (wa[5:0] == 6'd62) begin
            scl_t[2 * wset] <= wd[95:0]; scl_t[2 * wset + 1] <= wd[191:96]; eps_t[wset] <= wd[255:224];
        end
    end
    // ---------------------------------------------------------------- jobs: armed -> active (first beat) -> tail
    wire job_w = wv && wa[9:8] == 2'b10 && wa[0];
    reg pj_v; reg [SB-1:0] pj_set; reg pj_w; reg [9:0] pj_row; reg [4:0] pj_lm; reg [15:0] pj_sm;
    reg aj_v; reg [SB-1:0] aj_set; reg aj_w; reg [9:0] aj_row; reg [4:0] aj_lm; reg [15:0] aj_sm;
    reg [SB-1:0] tj_set; reg tj_w; reg [9:0] tj_row; reg [4:0] tj_lm; reg [15:0] tj_sm;
    // ---------------------------------------------------------------- L0: HP unpack + root store (2 window buffers)
    // buffer b, slice g, half h, word j (0..5)
    reg [31:0] rs [0:2*16*2*6-1];
    wire [4:0] aacc = ab[44:40], bacc = bb[44:40];
    wire [3:0] ag = ab[48:45], bg = bb[48:45];
    wire ah = ab[49], bh = bb[49];
    reg wb;                                             // buffer of the open window
    reg win_o; reg [4:0] win_acc; reg [31:0] win_seen; reg [5:0] win_n;
    reg [5:0] gap;                                      // edges since the last window completion (saturating)
    reg [24:0] wdone;                                   // windows completed in the active job
    reg mixed;                                          // previous job's mix phase is over (a new job may start)
    wire [4:0] cacc = av ? aacc : bacc;                 // the accumulation the arriving beat(s) belong to
    wire [5:0] nn = win_n + av + bv;
    wire w_fin = (av || bv) && nn == 6'd32;
    always @(posedge clk) begin
        if (av) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 12 * ag + 6 * ah + j] <= ab[52 + 32 * j +: 32];
        if (bv) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 12 * bg + 6 * bh + j] <= bb[52 + 32 * j +: 32];
    end
    // window bookkeeping, job hand-over, contract checks
    reg go_a; reg [4:0] go_acc; reg go_b;              // processing start (edge after the window completes)
    reg mix_go;
    wire u_fault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            wb <= 1'b0; win_o <= 1'b0; win_seen <= 32'd0; win_n <= 6'd0; gap <= 6'd63; wdone <= 25'd0;
            pj_v <= 1'b0; aj_v <= 1'b0; go_a <= 1'b0; mixed <= 1'b1; fault <= 1'b0;
        end else begin
            go_a <= 1'b0;
            gap <= (gap == 6'd63) ? gap : gap + 6'd1;
            if (job_w) begin
                if (pj_v) fault <= 1'b1;
                pj_v <= 1'b1; pj_set <= wd[40 +: SB]; pj_w <= wd[41]; pj_row <= wd[30:21]; pj_lm <= wd[20:16]; pj_sm <= wd[15:0];
            end
            if (av && (ab[51:50] != 2'd0 || aacc > 5'd24)) fault <= 1'b1;
            if (bv && (bb[51:50] != 2'd0 || bacc > 5'd24)) fault <= 1'b1;
            if (av && bv && (aacc != bacc || (ag == bg && ah == bh))) fault <= 1'b1;
            if (av && win_seen[{ag, ah}]) fault <= 1'b1;
            if (bv && win_seen[{bg, bh}]) fault <= 1'b1;
            if ((av || bv) && win_o && cacc != win_acc) fault <= 1'b1;            // overlapping windows
            if (av || bv) begin
                if (!win_o) begin
                    win_acc <= cacc;
                    if (wdone == 25'd0 && !aj_v) begin                             // the job's first beat
                        if (!pj_v || !mixed) fault <= 1'b1;
                        aj_v <= 1'b1; aj_set <= pj_set; aj_w <= pj_w; aj_row <= pj_row; aj_lm <= pj_lm; aj_sm <= pj_sm;
                        pj_v <= job_w;
                    end
                    if (wdone[cacc]) fault <= 1'b1;                                // accumulation twice in a job
                end
                win_o <= !w_fin;
                win_n <= w_fin ? 6'd0 : nn;
                win_seen <= w_fin ? 32'd0 : win_seen | (av ? 32'd1 << {ag, ah} : 32'd0) | (bv ? 32'd1 << {bg, bh} : 32'd0);
                if (w_fin) begin
                    if (gap < 6'd19) fault <= 1'b1;                               // completions >= 20 edges apart
                    gap <= 6'd0; go_a <= 1'b1; go_acc <= cacc; go_b <= wb; wb <= !wb;
                    wdone <= wdone | (25'd1 << cacc);
                end
            end
            if (mix_go) begin aj_v <= 1'b0; wdone <= 25'd0; end
            if (u_fault) fault <= 1'b1;
        end
    // ---------------------------------------------------------------- A: group pipeline (16 groups an accumulation)
    reg a_on; reg [3:0] a_i; reg [4:0] a_acc; reg a_b;
    reg o_v; reg [3:0] o_i; reg [4:0] o_acc;
    reg [31:0] A32, A8, B8, B16a, B16b, C16a, C16b, C8, D8, D32;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_on <= 1'b0; a_i <= 4'd0; o_v <= 1'b0; end
        else begin
            if (go_a) begin a_on <= 1'b1; a_i <= 4'd0; a_acc <= go_acc; a_b <= go_b; end
            else if (a_on) begin a_i <= a_i + 4'd1; if (a_i == 4'd15) a_on <= 1'b0; end
            o_v <= a_on; o_i <= a_i; o_acc <= a_acc;
        end
    // group i = 4 k + m: slices 4m + t, half k >> 1, words (k & 1) * 3 + 0..2
    wire [1:0] gk = a_i[3:2], gm = a_i[1:0];
    wire [8:0] rb0 = 9'd192 * a_b + 9'd12 * {gm, 2'd0} + 9'd6 * gk[1] + 9'd3 * gk[0];
    always @(posedge clk) begin
        A32 <= rs[rb0 + 0];      A8 <= rs[rb0 + 1];
        B8  <= rs[rb0 + 12 + 0]; B16a <= rs[rb0 + 12 + ((MUT == 6) ? 2 : 1)]; B16b <= rs[rb0 + 12 + ((MUT == 6) ? 1 : 2)];
        C16a <= rs[rb0 + 24 + 0]; C16b <= rs[rb0 + 24 + 1]; C8 <= rs[rb0 + 24 + 2];
        D8  <= rs[rb0 + 36 + 0]; D32 <= rs[rb0 + 36 + 1];
    end
    // level 1: p1 = A8 + B8 (MUT 5: B8 + B16a), N2 = B16b + C16a, p2 = C8 + D8
    wire [31:0] p1, n2, p2, n1, n3; wire f1, f2, f3, f4, f5;
    ot_dsrom_qadd #(.LAT(LA)) u_a1 (clk, rst_n, o_v, (MUT == 5) ? B8 : A8, (MUT == 5) ? B16a : B8, p1, f1);
    ot_dsrom_qadd #(.LAT(LA)) u_a2 (clk, rst_n, o_v, B16b, C16a, n2, f2);
    ot_dsrom_qadd #(.LAT(LA)) u_a3 (clk, rst_n, o_v, C8, D8, p2, f3);
    wire [31:0] d_a32, d_b16a, d_c16b, d_d32, d_a8; wire [8:0] d_t1; wire [LA:0] v1;
    ot_hdc_delay #(.W(160), .D(LA)) u_d1 (.clk(clk), .rst_n(rst_n), .d({A32, B16a, C16b, D32, A8}),
                                          .q({d_a32, d_b16a, d_c16b, d_d32, d_a8}));
    ot_hdc_delay #(.W(9), .D(LA)) u_t1 (.clk(clk), .rst_n(rst_n), .d({o_i, o_acc}), .q(d_t1));
    ot_hdc_vline #(.D(LA)) u_v1 (.clk(clk), .rst_n(rst_n), .v(o_v), .vd(v1));
    // level 2: N1 = p1 + B16a (MUT 5: A8 + p1), N3 = C16b + p2
    ot_dsrom_qadd #(.LAT(LA)) u_a4 (clk, rst_n, v1[LA], (MUT == 5) ? d_a8 : p1, (MUT == 5) ? p1 : d_b16a, n1, f4);
    ot_dsrom_qadd #(.LAT(LA)) u_a5 (clk, rst_n, v1[LA], d_c16b, p2, n3, f5);
    wire [31:0] e_a32, e_n2, e_d32; wire [8:0] e_t; wire [LA:0] v2;
    ot_hdc_delay #(.W(96), .D(LA)) u_d2 (.clk(clk), .rst_n(rst_n), .d({d_a32, n2, d_d32}), .q({e_a32, e_n2, e_d32}));
    ot_hdc_delay #(.W(9), .D(LA)) u_t2 (.clk(clk), .rst_n(rst_n), .d(d_t1), .q(e_t));
    ot_hdc_vline #(.D(LA)) u_v2 (.clk(clk), .rst_n(rst_n), .v(v1[LA]), .vd(v2));
    // level-5 store (80 words; one accumulation at a time: Q reads a node before the next accumulation rewrites it)
    reg [31:0] l5 [0:79];
    wire [3:0] e_i = e_t[8:5];
    always @(posedge clk) if (v2[LA]) begin
        l5[5 * e_i + 0] <= e_a32; l5[5 * e_i + 1] <= n1; l5[5 * e_i + 2] <= e_n2; l5[5 * e_i + 3] <= n3;
        l5[5 * e_i + 4] <= e_d32;
    end
    // ---------------------------------------------------------------- Q: quads -> level-7 nodes, one a cycle
    localparam integer DQ = 2 + 2 * LA;                 // go_a -> first quad read (after group 0 is written)
    wire [DQ:0] qs;
    ot_hdc_vline #(.D(DQ)) u_qs (.clk(clk), .rst_n(rst_n), .v(go_a), .vd(qs));
    wire [4:0] q_acc0;
    ot_hdc_delay #(.W(5), .D(DQ)) u_qacc (.clk(clk), .rst_n(rst_n), .d(go_acc), .q(q_acc0));
    reg q_on; reg [4:0] q_i; reg [4:0] q_acc;
    reg qr_v; reg [4:0] qr_i; reg [4:0] qr_acc; reg [31:0] q0, q1, q2, q3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_on <= 1'b0; q_i <= 5'd0; qr_v <= 1'b0; end
        else begin
            if (qs[DQ]) begin q_on <= 1'b1; q_i <= 5'd0; q_acc <= q_acc0; end
            else if (q_on) begin q_i <= q_i + 5'd1; if (q_i == 5'd19) q_on <= 1'b0; end
            qr_v <= q_on; qr_i <= q_i; qr_acc <= q_acc;
        end
    always @(posedge clk) begin q0 <= l5[4 * q_i]; q1 <= l5[4 * q_i + 1]; q2 <= l5[4 * q_i + 2]; q3 <= l5[4 * q_i + 3]; end
    wire [31:0] l6a, l6b, l7; wire f6, f7, f8; wire [LA:0] vq1, vq2; wire [9:0] tq1, tq2;
    ot_dsrom_qadd #(.LAT(LA)) u_a6 (clk, rst_n, qr_v, q0, q1, l6a, f6);
    ot_dsrom_qadd #(.LAT(LA)) u_a7 (clk, rst_n, qr_v, q2, q3, l6b, f7);
    ot_hdc_vline #(.D(LA)) u_vq1 (.clk(clk), .rst_n(rst_n), .v(qr_v), .vd(vq1));
    ot_hdc_delay #(.W(10), .D(LA)) u_tq1 (.clk(clk), .rst_n(rst_n), .d({qr_i, qr_acc}), .q(tq1));
    ot_dsrom_qadd #(.LAT(LA)) u_a8 (clk, rst_n, vq1[LA], l6a, l6b, l7, f8);
    ot_hdc_vline #(.D(LA)) u_vq2 (.clk(clk), .rst_n(rst_n), .v(vq1[LA]), .vd(vq2));
    ot_hdc_delay #(.W(10), .D(LA)) u_tq2 (.clk(clk), .rst_n(rst_n), .d(tq1), .q(tq2));
    // ---------------------------------------------------------------- T: streaming levels 8 .. 12
    wire [5:0] t_vv; wire [32*6-1:0] t_d; wire [5*6-1:0] t_i; wire [5:0] t_l; wire [5*6-1:0] t_a; wire [4:0] t_f;
    assign t_vv[0] = vq2[LA]; assign t_d[31:0] = l7; assign t_i[4:0] = tq2[9:5]; assign t_l[0] = tq2[9:5] == 5'd19;
    assign t_a[4:0] = tq2[4:0];
    genvar lv;
    generate for (lv = 0; lv < 5; lv = lv + 1) begin : g_lv
        wire        iv = t_vv[lv];
        wire [31:0] id = t_d[32 * lv +: 32];
        wire [4:0]  ii = t_i[5 * lv +: 5], ia = t_a[5 * lv +: 5];
        wire        il = t_l[lv];
        reg  [31:0] pend;
        always @(posedge clk) if (iv && !ii[0]) pend <= id;
        wire go = iv && (ii[0] || il);
        wire [31:0] y; wire f; wire [LA:0] vv; wire [10:0] tt;
        ot_dsrom_qadd #(.LAT(LA)) u_t (clk, rst_n, go, ii[0] ? pend : id, ii[0] ? id : 32'd0, y, f);
        ot_hdc_vline #(.D(LA)) u_tv (.clk(clk), .rst_n(rst_n), .v(go), .vd(vv));
        ot_hdc_delay #(.W(11), .D(LA)) u_tt (.clk(clk), .rst_n(rst_n), .d({il, ii >> 1, ia}), .q(tt));
        assign t_vv[lv + 1] = vv[LA];
        assign t_d[32 * (lv + 1) +: 32] = y; assign t_i[5 * (lv + 1) +: 5] = tt[9:5]; assign t_a[5 * (lv + 1) +: 5] = tt[4:0];
        assign t_l[lv + 1] = tt[10];
        assign t_f[lv] = f;
    end endgenerate
    wire root_v = t_vv[5]; wire [31:0] root = t_d[32 * 5 +: 32]; wire [4:0] root_acc = t_a[5 * 5 +: 5];
    // ---------------------------------------------------------------- roots -> proj / ss -> r
    reg [31:0] proj [0:23];
    reg [24:0] rdone; reg ss_v; reg [31:0] ss; reg [31:0] eps_c;
    always @(posedge clk) if (root_v && root_acc < 5'd24) proj[root_acc] <= root;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ss_v <= 1'b0;
        else ss_v <= root_v && root_acc == 5'd24;
    always @(posedge clk) begin if (root_v) ss <= root; eps_c <= (MUT == 7) ? 32'd0 : eps_t[aj_set]; end
    wire [31:0] mq, me, rr; wire mq_v, me_v, rr_v, f_div, f_eps, f_rsq; wire [LA:0] ve;
    ot_dsrom_divc #(.F(5), .K(12)) u_div (.clk(clk), .rst_n(rst_n), .v(ss_v), .x(ss), .y(mq), .vo(mq_v), .fault(f_div));
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps_c, me, f_eps);
    assign me_v = ve[LA];
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    reg r_ok; reg [31:0] r;
    // ---------------------------------------------------------------- mix phase: 24 multiplies, then the tail launch
    reg m_on; reg [4:0] m_i; reg mm_v; reg [4:0] mm_i; reg [31:0] mm_a;
    wire [31:0] my; wire f_mul; wire [LM:0] vm; wire [4:0] mi;
    reg [767:0] mixes; reg launch;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rdone <= 25'd0; r_ok <= 1'b0; m_on <= 1'b0; mm_v <= 1'b0; mix_go <= 1'b0; launch <= 1'b0; end
        else begin
            mix_go <= 1'b0; launch <= 1'b0;
            if (root_v) begin
                rdone <= rdone | (25'd1 << root_acc);
            end
            if (rr_v) begin r_ok <= 1'b1; r <= rr; end
            if (!m_on && rdone == {NACC{1'b1}} && r_ok) begin
                m_on <= 1'b1; m_i <= 5'd0; mix_go <= 1'b1; rdone <= 25'd0; r_ok <= 1'b0;
                tj_set <= aj_set; tj_w <= aj_w; tj_row <= aj_row; tj_lm <= aj_lm; tj_sm <= aj_sm;
            end
            if (m_on) begin m_i <= m_i + 5'd1; if (m_i == 5'd23) m_on <= 1'b0; end
            mm_v <= m_on; mm_i <= m_i;
            if (vm[LM] && mi == 5'd23) launch <= 1'b1;
        end
    always @(posedge clk) mm_a <= proj[m_i];
    ot_hdc_qmul_lat #(.LAT(LM)) u_mul (clk, rst_n, mm_v, mm_a, r, my, f_mul);
    ot_hdc_vline #(.D(LM)) u_vm (.clk(clk), .rst_n(rst_n), .v(mm_v), .vd(vm));
    ot_hdc_delay #(.W(5), .D(LM)) u_mi (.clk(clk), .rst_n(rst_n), .d(mm_i), .q(mi));
    always @(posedge clk) if (vm[LM]) mixes[32 * mi +: 32] <= my;
    always @(posedge clk or negedge rst_n) if (!rst_n) mixed <= 1'b1; else mixed <= mix_go ? 1'b0 : launch ? 1'b1 : mixed;
    // ---------------------------------------------------------------- L5: the exact tail (sigmoid, exp, Sinkhorn)
    reg [767:0] bases; reg [95:0] scales;
    always @(posedge clk) begin
        for (j = 0; j < 24; j = j + 1) bases[32 * j +: 32] <= base_t[48 * tj_set + 24 * tj_w + j];
        scales <= scl_t[2 * tj_set + tj_w];
    end
    wire tl_v, tl_f; wire [767:0] coef;
    ot_hbm_hc_tail_unit_static #(.SDIV(SDIV), .CAP(41 * SDIV + 2)) u_tail (.clk(clk), .rst_n(rst_n), .launch(launch),
        .mixes(mixes), .bases(bases), .scales(scales), .result_v(tl_v), .result(coef), .fault(tl_f));
    // ---------------------------------------------------------------- coefficient CTL rows (target 5), output flops
    function automatic [V-1:0] ctl(input [9:0] a, input [127:0] d, input [15:0] sm, input [4:0] lm, input [3:0] s);
        reg [185:0] p;
        begin
            p = 186'd0; p[15:0] = sm; p[20:16] = 5'd5; p[25:21] = lm;
            p[26 +: 10] = a; p[36 +: 4] = 4'hf; p[40 +: 128] = d;
            ctl = {V{1'b0}}; ctl[0] = 1'b1; ctl[12:9] = s; ctl[21 +: 186] = p;
        end
    endfunction
    reg c_on; reg [2:0] c_i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin c_on <= 1'b0; c_i <= 3'd0; ct_v <= 1'b0; end
        else begin
            if (tl_v) begin c_on <= 1'b1; c_i <= 3'd0; end
            else if (c_on) begin c_i <= c_i + 3'd1; if (c_i == 3'd5) c_on <= 1'b0; end
            ct_v <= c_on;
        end
    always @(posedge clk) ct_b <= ctl(tj_row + {7'd0, c_i}, coef[128 * c_i +: 128], tj_sm, tj_lm, sid_c);
    // ---------------------------------------------------------------- unit faults (sticky in `fault`)
    assign u_fault = f1 | f2 | f3 | f4 | f5 | f6 | f7 | f8 | (|t_f) | f_div | f_eps | f_rsq | f_mul | tl_f
                 | (root_v && rdone[root_acc]) | (mix_go && !aj_v) | (go_a && a_on && a_i != 4'd15)
                 | (qs[DQ] && q_on && q_i != 5'd19) | (tl_v && c_on);
endmodule
