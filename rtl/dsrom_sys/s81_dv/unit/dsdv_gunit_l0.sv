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
// fault (sticky): any contract breach, a duplicate (g, h) or accumulation, reserved bits, an unarmed job, L4's / L0r's fault.
// Every input lands in a flop; every output leaves a flop.
// S81U-GUNIT3 (10-17): the root store (12,288 flops: 15,319 sinks on one root, TT insertion 333 ps, clock-rule FAIL)
// moved to the E-side leaf dsdv_gunit_l0r (W-E registered seam).  This leaf registers each store write (wr_*: the edge
// the store used to write) and the window's go (go_*), and relays L0r's group stream to L4 (input flop -> output flop).
// Store write +2 edges, go +1, group stream +2 + 2 (relay): the stream reads a window 2 edges after its last write.
// S81U-GUNIT6 (10-17, native pin rules, NATIVE-2 lessons): rst_n drives only ot_rst_relay (4 kept region copies; release
// +3 edges, transaction-level exact); cw is captured ONCE (wv / wa / wd are both the job decode's input flops and the
// first stage of the cw feedthrough; cwo_* = their output flops, still 2 edges), so no cw pin feeds two captures; j_v
// (N output flop) has a kept internal twin ja for the job bookkeeping, so the output flop drives only its pin.  0 edges.
// S81-KITS-RTLC 10-24 (raw face_guard, 0 edges): every held output register (j_*, go_acc, go_b, sticky fault) has a kept
// internal twin (jk_*, gk_*, fault_k) that holds; the pin flop loads twin-next each edge, so no pin flop reads itself.
// cw_a / cwo_a packed {a[9:8], a[5:0]} (a[7:6] read by no gunit leaf).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l0 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // S face (L2)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins): hp_a / hp_b [243:40] (no other bit is read); hct4_b / hct_b = packed CTL rows
    input  wire          hp_av, input wire [243:40] hp_a, input wire hp_bv, input wire [243:40] hp_b,
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output wire          hct_v, output wire [169:0] hct_b, output reg fault,
    // N face (L4)
    output wire [275:0]  rn_o,  input wire [275:0] rn_i,
    output reg           g_v, output reg [3:0] g_i, output reg [4:0] g_acc, output reg [319:0] g_d,
    output reg           j_v, output reg j_set, output reg j_w, output reg [9:0] j_row, output reg [4:0] j_lm,
    output reg  [15:0]   j_sm,
    output reg           cwo_v, output reg [7:0] cwo_a, output reg [255:0] cwo_d, output wire [3:0] sid_o,
    input  wire          hct4_v, input wire [169:0] hct4_b, input wire mix_go, input wire launch, input wire f4,
    // E face (L0r: root store + group stream)
    output reg           wr_av, output reg [4:0] wr_agh, output reg [191:0] wr_ad,
    output reg           wr_bv, output reg [4:0] wr_bgh, output reg [191:0] wr_bd, output reg wr_b,
    output reg           go_a, output reg [4:0] go_acc, output reg go_b,
    input  wire          r_v, input wire [3:0] r_i, input wire [4:0] r_acc, input wire [319:0] r_d, input wire r_f
);
    localparam integer V = 276;
    integer j;
    // reset relay (S81U-GUNIT6): the rst_n port drives only ot_rst_relay; region copies 0 feedthroughs / cw, 1 input
    // flops, 2 window / job bookkeeping, 3 group stream relay.  Release is 3 edges after the port.
    wire [3:0] rq;
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- feedthroughs
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rq[0]), .d(rs_i), .q(rn_o));
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rq[0]), .d(rn_i), .q(rs_o));
    dsdv_gunit_pass #(.W(171)) u_ct (.clk(clk), .rst_n(rq[0]), .d({hct4_b, hct4_v}), .q({hct_b, hct_v}));
    dsdv_gunit_pass #(.W(4)) u_sid (.clk(clk), .rst_n(rq[0]), .d(sid_i), .q(sid_o));
    // ---------------------------------------------------------------- input flops (cw: one capture, = the feedthrough's stage 1)
    reg av, bv, wv, mg, ln, f4_q; reg [V-1:0] ab, bb; reg [9:0] wa; reg [255:0] wd;
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin av <= 1'b0; bv <= 1'b0; wv <= 1'b0; mg <= 1'b0; ln <= 1'b0; f4_q <= 1'b0; end
        else begin av <= hp_av; bv <= hp_bv; wv <= cw_v; mg <= mix_go; ln <= launch; f4_q <= f4; end
`ifdef OT_RTLC_MUT_L0   // RTLC bench mutant: hp_a unpacked one bit high
    always @(posedge clk) begin ab <= {31'd0, hp_a, 41'd0}; bb <= {32'd0, hp_b, 40'd0}; wa <= {cw_a[7:6], 2'd0, cw_a[5:0]}; wd <= cw_d; end
`else
    always @(posedge clk) begin ab <= {32'd0, hp_a, 40'd0}; bb <= {32'd0, hp_b, 40'd0}; wa <= {cw_a[7:6], 2'd0, cw_a[5:0]}; wd <= cw_d; end
`endif
    always @(posedge clk or negedge rq[0]) if (!rq[0]) cwo_v <= 1'b0; else cwo_v <= wv;   // cw feedthrough stage 2
    always @(posedge clk) begin cwo_a <= {wa[9:8], wa[5:0]}; cwo_d <= wd; end
    // ---------------------------------------------------------------- jobs: armed -> active (first beat)
    wire job_w = wv && wa[9:8] == 2'b10 && wa[0];
    reg pj_v; reg pj_set; reg pj_w; reg [9:0] pj_row; reg [4:0] pj_lm; reg [15:0] pj_sm;
    // ---------------------------------------------------------------- window bookkeeping (the store is L0r's)
    wire [4:0] aacc = ab[44:40], bacc = bb[44:40];
    wire [3:0] ag = ab[48:45], bg = bb[48:45];
    wire ah = ab[49], bh = bb[49];
    reg wb; reg win_o; reg [4:0] win_acc; reg [31:0] win_seen; reg [5:0] win_n; reg [5:0] gap; reg [24:0] wdone;
    reg mixed;
    wire [4:0] cacc = av ? aacc : bacc;
    wire [5:0] nn = win_n + av + bv;
    wire w_fin = (av || bv) && nn == 6'd32;
    always @(posedge clk) begin                         // store writes -> L0r (output flops)
        wr_agh <= {ag, ah}; wr_ad <= ab[52 +: 192]; wr_bgh <= {bg, bh}; wr_bd <= bb[52 +: 192]; wr_b <= wb;
    end
    always @(posedge clk or negedge rq[2])
        if (!rq[2]) begin wr_av <= 1'b0; wr_bv <= 1'b0; end else begin wr_av <= av; wr_bv <= bv; end
    reg rf_q;
    (* keep = "true" *) reg ja;                         // internal twin of the j_v output flop
    (* keep = "true" *) reg jk_set, jk_w; (* keep = "true" *) reg [9:0] jk_row; (* keep = "true" *) reg [4:0] jk_lm;
    (* keep = "true" *) reg [15:0] jk_sm; (* keep = "true" *) reg [4:0] gk_acc; (* keep = "true" *) reg gk_b, fault_k;
    reg fs;                                             // this edge's fault conditions (combinational, block-local)
    wire ld_j = (av || bv) && !win_o && wdone == 25'd0 && !ja;   // the job's first beat (av / bv are 0 in reset)
    wire ld_g = (av || bv) && w_fin;
    always @(posedge clk) begin                          // pin flops: twin-next, never their own Q
        {j_set, j_w, j_row, j_lm, j_sm} <= ld_j ? {pj_set, pj_w, pj_row, pj_lm, pj_sm} : {jk_set, jk_w, jk_row, jk_lm, jk_sm};
        {go_acc, go_b} <= ld_g ? {cacc, wb} : {gk_acc, gk_b};
    end
    always @(posedge clk or negedge rq[2])
        if (!rq[2]) begin
            wb <= 1'b0; win_o <= 1'b0; win_seen <= 32'd0; win_n <= 6'd0; gap <= 6'd63; wdone <= 25'd0;
            pj_v <= 1'b0; j_v <= 1'b0; ja <= 1'b0; go_a <= 1'b0; fault <= 1'b0; fault_k <= 1'b0; fs = 1'b0;
        end else begin
            fs = 1'b0;
            go_a <= 1'b0; j_v <= ja;
            gap <= (gap == 6'd63) ? gap : gap + 6'd1;
            if (job_w) begin
                if (pj_v) fs = 1'b1;
                pj_v <= 1'b1; pj_set <= wd[40]; pj_w <= wd[41]; pj_row <= wd[30:21]; pj_lm <= wd[20:16]; pj_sm <= wd[15:0];
            end
            if (av && (ab[51:50] != 2'd0 || aacc > 5'd24)) fs = 1'b1;
            if (bv && (bb[51:50] != 2'd0 || bacc > 5'd24)) fs = 1'b1;
            if (av && bv && (aacc != bacc || (ag == bg && ah == bh))) fs = 1'b1;
            if (av && win_seen[{ag, ah}]) fs = 1'b1;
            if (bv && win_seen[{bg, bh}]) fs = 1'b1;
            if ((av || bv) && win_o && cacc != win_acc) fs = 1'b1;            // overlapping windows
            if (av || bv) begin
                if (!win_o) begin
                    win_acc <= cacc;
                    if (wdone == 25'd0 && !ja) begin                               // the job's first beat
                        if (!pj_v || !mixed) fs = 1'b1;
                        j_v <= 1'b1; ja <= 1'b1; jk_set <= pj_set; jk_w <= pj_w; jk_row <= pj_row; jk_lm <= pj_lm; jk_sm <= pj_sm;
                        pj_v <= job_w;
                    end
                    if (wdone[cacc]) fs = 1'b1;                                // accumulation twice in a job
                end
                win_o <= !w_fin;
                win_n <= w_fin ? 6'd0 : nn;
                win_seen <= w_fin ? 32'd0 : win_seen | (av ? 32'd1 << {ag, ah} : 32'd0) | (bv ? 32'd1 << {bg, bh} : 32'd0);
                if (w_fin) begin
                    if (gap < 6'd19) fs = 1'b1;                               // completions >= 20 edges apart
                    gap <= 6'd0; go_a <= 1'b1; gk_acc <= cacc; gk_b <= wb; wb <= !wb;
                    wdone <= wdone | (25'd1 << cacc);
                end
            end
            if (mg) begin
                if (!ja) fs = 1'b1;
                j_v <= 1'b0; ja <= 1'b0; wdone <= 25'd0;
            end
            if (rf_q) fs = 1'b1;                                           // L0r: a go while streaming
            if (f4_q) fs = 1'b1;
            fault_k <= fault_k | fs; fault <= fault_k | fs;
        end
    always @(posedge clk or negedge rq[2]) if (!rq[2]) mixed <= 1'b1; else mixed <= mg ? 1'b0 : ln ? 1'b1 : mixed;
    // ---------------------------------------------------------------- group stream relay (L0r -> L4)
    reg rv_q; reg [3:0] ri_q; reg [4:0] racc_q; reg [319:0] rd_q;
    always @(posedge clk or negedge rq[3])
        if (!rq[3]) begin rv_q <= 1'b0; rf_q <= 1'b0; g_v <= 1'b0; end
        else begin rv_q <= r_v; rf_q <= r_f; g_v <= rv_q; end
    always @(posedge clk) begin ri_q <= r_i; racc_q <= r_acc; rd_q <= r_d; g_i <= ri_q; g_acc <= racc_q; g_d <= rd_q; end
endmodule
