`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l0 -- G-unit leaf L0 (3rd of 6, above the stop L2): HP root store, window
// bookkeeping, the HC job hand-over and the level-5 group operand stream to L4.
//
// HP BEAT (kind 7; S81-DV p4i adopts it in the slice send path): slice g holds, per accumulation and copy k, the 40
// chunk sums [640 k + 40 g, + 40) of the golden tree and sends the roots of the MAXIMAL ALIGNED subtrees of that range in
// leaf order -- sizes (chunks) by g mod 4: 0 {32, 8}, 1 {8, 16, 16}, 2 {16, 16, 8}, 3 {8, 32} -- as two V beats per
// (accumulation, slice):  [40 +: 5] acc (0..23 fn row, 24 sum of squares), [45 +: 4] g, [49] h (copies 2h, 2h+1),
// [51:50] 0, [52 + 32 j +: 32] j = 0..2 copy 2h's roots, 3..5 copy 2h+1's roots.
// Static contract (assertions, never flow control): an accumulation's 32 beats form a WINDOW (any order, either rung
// direction, two in one cycle allowed); windows do not overlap; successive window completions are >= 20 edges apart;
// a job's 25 windows come in any accumulation order; a job's first beat comes after the previous job's mix phase (L4's
// mix_go / launch, relayed back here).
// HC JOB (cw relayed by L2; cw_a[9:8] = 2'b10, cw_a[0] = 1): {which [41], set [40], row [30:21], lmask [20:16],
// smask [15:0]}, armed before the job's first HP beat; the active job's fields leave to L4 (static during the job).
// Group stream to L4 (one group a cycle, 16 an accumulation, the edge after the window completes + 1):
// grp i = 4 k + m = slices 4m .. 4m+3 of copy k: {A32, A8, B8, B16a, B16b, C16a, C16b, C8, D8, D32} (10 words).
// Feedthroughs: the rung (L2 <-> L4), cw (to L4 / L5), sid, the HC CTL rows (L4 -> L2), each 2 edges.
// fault (sticky): any contract breach, a duplicate (g, h) or accumulation, reserved bits, an unarmed job, L4's fault.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 6 = roots 1 / 2 of g = 1 mod 4 swapped.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l0 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // S face (L2)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    input  wire          hp_av, input wire [275:0] hp_a, input wire hp_bv, input wire [275:0] hp_b,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output wire          hct_v, output wire [275:0] hct_b, output reg fault,
    // N face (L4)
    output wire [275:0]  rn_o,  input wire [275:0] rn_i,
    output reg           g_v, output reg [3:0] g_i, output reg [4:0] g_acc, output reg [319:0] g_d,
    output reg           j_v, output reg j_set, output reg j_w, output reg [9:0] j_row, output reg [4:0] j_lm,
    output reg  [15:0]   j_sm,
    output wire          cwo_v, output wire [9:0] cwo_a, output wire [255:0] cwo_d, output wire [3:0] sid_o,
    input  wire          hct4_v, input wire [275:0] hct4_b, input wire mix_go, input wire launch, input wire f4
);
    localparam integer V = 276;
    integer j;
    // ---------------------------------------------------------------- feedthroughs
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rst_n), .d(rs_i), .q(rn_o));
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rst_n), .d(rn_i), .q(rs_o));
    dsdv_gunit_pass #(.W(277)) u_ct (.clk(clk), .rst_n(rst_n), .d({hct4_b, hct4_v}), .q({hct_b, hct_v}));
    dsdv_gunit_pass #(.W(271)) u_cw (.clk(clk), .rst_n(rst_n), .d({cw_d, cw_a, cw_v}), .q({cwo_d, cwo_a, cwo_v}));
    dsdv_gunit_pass #(.W(4)) u_sid (.clk(clk), .rst_n(rst_n), .d(sid_i), .q(sid_o));
    // ---------------------------------------------------------------- input flops
    reg av, bv, wv, mg, ln, f4_q; reg [V-1:0] ab, bb; reg [9:0] wa; reg [255:0] wd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin av <= 1'b0; bv <= 1'b0; wv <= 1'b0; mg <= 1'b0; ln <= 1'b0; f4_q <= 1'b0; end
        else begin av <= hp_av; bv <= hp_bv; wv <= cw_v; mg <= mix_go; ln <= launch; f4_q <= f4; end
    always @(posedge clk) begin ab <= hp_a; bb <= hp_b; wa <= cw_a; wd <= cw_d; end
    // ---------------------------------------------------------------- jobs: armed -> active (first beat)
    wire job_w = wv && wa[9:8] == 2'b10 && wa[0];
    reg pj_v; reg pj_set; reg pj_w; reg [9:0] pj_row; reg [4:0] pj_lm; reg [15:0] pj_sm;
    // ---------------------------------------------------------------- root store (2 window buffers)
    reg [31:0] rs [0:2*16*2*6-1];                       // buffer b, slice g, half h, word j (0..5)
    wire [4:0] aacc = ab[44:40], bacc = bb[44:40];
    wire [3:0] ag = ab[48:45], bg = bb[48:45];
    wire ah = ab[49], bh = bb[49];
    reg wb; reg win_o; reg [4:0] win_acc; reg [31:0] win_seen; reg [5:0] win_n; reg [5:0] gap; reg [24:0] wdone;
    reg mixed;
    wire [4:0] cacc = av ? aacc : bacc;
    wire [5:0] nn = win_n + av + bv;
    wire w_fin = (av || bv) && nn == 6'd32;
    always @(posedge clk) begin
        if (av) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 12 * ag + 6 * ah + j] <= ab[52 + 32 * j +: 32];
        if (bv) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 12 * bg + 6 * bh + j] <= bb[52 + 32 * j +: 32];
    end
    reg go_a; reg [4:0] go_acc; reg go_b;
    reg a_on; reg [3:0] a_i; reg [4:0] a_acc; reg a_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            wb <= 1'b0; win_o <= 1'b0; win_seen <= 32'd0; win_n <= 6'd0; gap <= 6'd63; wdone <= 25'd0;
            pj_v <= 1'b0; j_v <= 1'b0; go_a <= 1'b0; mixed <= 1'b1; fault <= 1'b0;
        end else begin
            go_a <= 1'b0;
            gap <= (gap == 6'd63) ? gap : gap + 6'd1;
            if (job_w) begin
                if (pj_v) fault <= 1'b1;
                pj_v <= 1'b1; pj_set <= wd[40]; pj_w <= wd[41]; pj_row <= wd[30:21]; pj_lm <= wd[20:16]; pj_sm <= wd[15:0];
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
                    if (wdone == 25'd0 && !j_v) begin                              // the job's first beat
                        if (!pj_v || !mixed) fault <= 1'b1;
                        j_v <= 1'b1; j_set <= pj_set; j_w <= pj_w; j_row <= pj_row; j_lm <= pj_lm; j_sm <= pj_sm;
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
            if (mg) begin
                if (!j_v) fault <= 1'b1;
                j_v <= 1'b0; wdone <= 25'd0;
            end
            if (go_a && a_on && a_i != 4'd15) fault <= 1'b1;
            if (f4_q) fault <= 1'b1;
        end
    always @(posedge clk or negedge rst_n) if (!rst_n) mixed <= 1'b1; else mixed <= mg ? 1'b0 : ln ? 1'b1 : mixed;
    // ---------------------------------------------------------------- group stream (16 groups an accumulation)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_on <= 1'b0; a_i <= 4'd0; g_v <= 1'b0; end
        else begin
            if (go_a) begin a_on <= 1'b1; a_i <= 4'd0; a_acc <= go_acc; a_b <= go_b; end
            else if (a_on) begin a_i <= a_i + 4'd1; if (a_i == 4'd15) a_on <= 1'b0; end
            g_v <= a_on;
        end
    // group i = 4 k + m: slices 4m + t, half k >> 1, words (k & 1) * 3 + 0..2
    wire [1:0] gk = a_i[3:2], gm = a_i[1:0];
    wire [8:0] rb0 = 9'd192 * a_b + 9'd12 * {gm, 2'd0} + 9'd6 * gk[1] + 9'd3 * gk[0];
    always @(posedge clk) begin
        g_i <= a_i; g_acc <= a_acc;
        g_d <= {rs[rb0 + 36 + 1], rs[rb0 + 36 + 0], rs[rb0 + 24 + 2], rs[rb0 + 24 + 1], rs[rb0 + 24 + 0],
                rs[rb0 + 12 + ((MUT == 6) ? 1 : 2)], rs[rb0 + 12 + ((MUT == 6) ? 2 : 1)], rs[rb0 + 12 + 0],
                rs[rb0 + 1], rs[rb0 + 0]};
        //       D32 [319:288]  D8            C8             C16b           C16a
        //       B16b           B16a          B8             A8             A32 [31:0]
    end
endmodule
