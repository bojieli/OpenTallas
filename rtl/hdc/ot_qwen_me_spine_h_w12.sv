`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_me_spine_h_w12: the W12 ME spine (ot_qwen_me_spine_w12, rtl/hdc/ot_qwen_me_array_w12.sv) built from
// hardened elements, for 1.2 GHz @ SS sign-off.  Same parameters and ports; a successor, the original is untouched.
//
// The flat spine (the engine top ot_qwen_w12_matvec_part PART 2 plus its wire stages) is ~10 M cells at G = 6,144:
// 1,504 tree adders, 1,536 post-scale multipliers, 2.4 M held-word flops and the 2,048-port x network; Yosys did
// not finish it in 24 h (results/rtl/qwen_rom_w12_runtime/terminal_review_20261001/spine_s833b).  Here it is
//   ot_qwen_me_spctl_w12    x 1        issue loop, x read addresses, element tags and their delay lines, the split
//                                      tree's per-level selects, the scale requests, argmax top levels, per-slot
//                                      maxima, progress, idle, fault
//   ot_qwen_me_sptree_w12   x W (16)   ONE LANE of split-tree levels TCUT+1 .. LG-1 (lanes never mix in the tree)
//   ot_qwen_me_spport_w12   x NPG/PQ   PQ (4) result-port groups: tree level LG (a pure hold at G = 6,144), the
//                                      INT8 post-scale, the two result registers, the argmax leaves and its first
//                                      log2(PQ*W) levels
// and the wire stages (instruction broadcast BD, x network, tree words TWS, result write ORD) between them.
//
// Every element port is a register on both sides (the input lands in a flop, the output leaves one), so each
// element closes alone.  Signals the elements need from the control are tapped ONE CYCLE EARLY from the same
// delay lines and registered inside the element (zero added cycles): the tree's per-level select and valid,
// the result tags, the post-scale valid.  Two zero-cycle look-aheads replace in-loop arithmetic:
//   x_addr   the per-port offset c*xcs (c = port mod S) is latched at the go as a carry-save pair from
//            i_split/i_xcs (the edge that latches split_r/xcs_r), so the loop cycle is a 3:2 row + a kept add;
//   scale    the scale ROM request leaves one cycle earlier (an earlier tap of the same tag line) and the
//            port element captures scale_q in a register before its multiplier (the ROM's SS clk->q no longer
//            shares a cycle with the multiplier's first stage).
// Port-visible differences from ot_qwen_me_spine_w12 (everything else is cycle-identical):
//   scale_re / scale_gre / scale_addr  one cycle EARLIER (same sequence; the scale ROM is a synchronous ROM);
//   fault                              a post-scale fault is seen one cycle later (registered in its element).
// Requires (checked at elaboration): PRUNE (SMIN > 0), GT >> LG == 0 (level LG holds only), (GT >> SMIN) % PQ == 0,
// BD - XVM - IREG >= 1, TWS >= 1.
// ---------------------------------------------------------------------------

module ot_qwen_me_spine_h_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer BD = 0,
    parameter integer XVM = 0,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer MEM_EXTRA = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer ACC_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer PQ = 4,              // result-port groups per port element
    // post-scale multiplier latency: 5 = ot_hdc_fmul (cycle-identical to ot_qwen_me_spine_w12; -450 ps at 0.833 ns SS),
    // 6 = ot_hdc_fp32_mul_lat #(6) (bit-identical, closes at SS): results, argmax and maxima one cycle later
    parameter integer SCALE_LAT = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_tiles, i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase, i_ts, i_ks, i_js,
    input  wire [AW-1:0]     i_xbase, i_xks, i_xjs, i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase, i_ots, i_ojs,
    input  wire              i_mmode, i_oen, i_amax, i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output wire              scale_re,
    output wire [(GT >> SMIN)-1:0]     scale_gre,
    output wire [(GT >> SMIN)*AW-1:0]  scale_addr,
    input  wire [(GT >> SMIN)*W*16-1:0] scale_q,
    output wire [(1<<SMAX)-1:0]    x_re,
    output wire [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    output wire              kv_re,
    output wire              tgo,
    output wire [3*NW+13*AW+13-1:0] tb,
    output wire [(1<<SMAX)*32-1:0] xl_d,
    input  wire [(GT >> TCUT)*W*32-1:0] t_lvl,
    input  wire              fab_fault,
    output wire              ov,
    output wire [(GT >> SMIN)-1:0]     o_we,
    output wire [(GT >> SMIN)*AW-1:0]  o_addr,
    output wire [(GT >> SMIN)*W-1:0]   o_mask,
    output wire [(GT >> SMIN)*W*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output wire [15:0]       progress,
    output wire              fault
);
    localparam integer NT  = GT / TG;
    localparam integer LT  = $clog2(TG);
    localparam integer LG  = $clog2(GT);
    localparam integer NXC = 1 << SMAX;
    localparam integer XD  = BD + (TCUT - LT) * NWS + TWS + MEM_EXTRA;
    localparam integer NPT = GT >> TCUT;
    localparam integer GI  = NPT;
    localparam integer NPG = GT >> SMIN;
    localparam integer NPE = NPG / PQ;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer IREG = (BD > XVM && BD > 0) ? 1 : 0;
    localparam integer XNS = BD - XVM - IREG;             // x network stages (the first is the control's select stage)
    localparam integer CW = 1 + 32 + NW;
    localparam integer FW = 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1);
    generate if (SMIN == 0 || (GT >> LG) != 0 || (NPG % PQ) != 0 || XNS < 1 || TWS < 1) begin : g_bad
        ot_qwen_me_spine_h_w12_unsupported_parameters u_trap ();
    end endgenerate

    // -- control element ---------------------------------------------------------------------------------------
    wire [LG:0] t_sel_e, t_tv_e;
    wire [W-1:0] tr_fault;
    wire p_v_e2;
    wire [FW-1:0] p_f_e2;
    wire [NPE*CW-1:0] p_am;
    wire [NPE-1:0] p_fault;
    wire [NXC*32-1:0] xl0;
    ot_qwen_me_spctl_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .GT(GT),
        .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .XD(XD), .XVM(XVM), .ORD(ORD), .SCALE_LOCAL(SCALE_LOCAL),
        .PQ(PQ), .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP),
        .MUL_LAT(MUL_LAT), .SCALE_LAT(SCALE_LAT)) u_ctl (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .kv_re(kv_re),
        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr),
        .x_re(x_re), .x_addr(x_addr), .x_q(x_q), .xl0(xl0),
        .t_sel_e(t_sel_e), .t_tv_e(t_tv_e), .tr_fault(tr_fault),
        .p_v_e2(p_v_e2), .p_f_e2(p_f_e2), .p_am(p_am), .p_fault(p_fault), .fab_fault(fab_fault),
        .ov(ov), .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(fault));

    // -- wire stages: instruction broadcast, x network ----------------------------------------------------------
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    ot_hdc_delay #(.W(IBW), .D(BD - IREG)) u_ib (.clk(clk), .rst_n(rst_n), .d(ib), .q(tb));
    ot_hdc_delay #(.W(1), .D(BD - IREG), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go && ready), .q(tgo));
    ot_hdc_delay #(.W(NXC*32), .D(XNS - 1)) u_xnet (.clk(clk), .rst_n(rst_n), .d(xl0), .q(xl_d));

    // -- tree elements: one per lane (the last TWS wire stage is the element's input register) ------------------
    wire [NPT*W*32-1:0] t_in;
    ot_hdc_delay #(.W(NPT*W*32), .D(TWS - 1)) u_tws (.clk(clk), .rst_n(rst_n), .d(t_lvl), .q(t_in));
    wire [NPG*W*32-1:0] lvt;           // level LG-1, position-major (position, lane) as the engine's words
    genvar l, p, q;
    generate
        for (l = 0; l < W; l = l + 1) begin : g_tree
            wire [GI*32-1:0] tl;
            wire [NPG*32-1:0] yl;
            for (p = 0; p < GI; p = p + 1) begin : g_in
                assign tl[p*32 +: 32] = t_in[(p*W + l)*32 +: 32];
            end
            ot_qwen_me_sptree_w12 #(.GT(GT), .SMIN(SMIN), .TCUT(TCUT), .TREE_LAT(TREE_LAT), .TINREG(1)) u_tr (
                .clk(clk), .rst_n(rst_n), .t_in(tl), .sel_e(t_sel_e), .tv_e(t_tv_e), .y(yl), .fault(tr_fault[l]));
            for (p = 0; p < NPG; p = p + 1) begin : g_out
                assign lvt[(p*W + l)*32 +: 32] = yl[p*32 +: 32];
            end
        end
    endgenerate

    // -- port elements, then the ORD result-write wire stages --------------------------------------------------
    wire [NPG-1:0]      we2;
    wire [NPG*AW-1:0]   addr2;
    wire [NPG*W-1:0]    mask2;
    wire [NPG*W*32-1:0] data2;
    generate
        for (q = 0; q < NPE; q = q + 1) begin : g_port
            ot_qwen_me_spport_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .SMIN(SMIN), .PQ(PQ),
                .TREE_LAT(TREE_LAT), .SCALE_LAT(SCALE_LAT)) u_pt (
                .clk(clk), .rst_n(rst_n), .pt_id(q[15:0]),
                .lv_in(lvt[q*PQ*W*32 +: PQ*W*32]), .a_v_e2(p_v_e2), .a_f_e2(p_f_e2),
                .scale_q(scale_q[q*PQ*W*16 +: PQ*W*16]),
                .o_we(we2[q*PQ +: PQ]), .o_addr(addr2[q*PQ*AW +: PQ*AW]), .o_mask(mask2[q*PQ*W +: PQ*W]),
                .o_data(data2[q*PQ*W*32 +: PQ*W*32]), .am(p_am[q*CW +: CW]), .fault(p_fault[q]));
        end
        if (ORD > 0) begin : g_ord
            ot_hdc_delay #(.W(NPG), .D(ORD), .RESET(1)) u_owe (.clk(clk), .rst_n(rst_n), .d(we2), .q(o_we));
            ot_hdc_delay #(.W(NPG*AW + NPG*W + NPG*W*32), .D(ORD)) u_od (.clk(clk), .rst_n(rst_n),
                .d({addr2, mask2, data2}), .q({o_addr, o_mask, o_data}));
        end else begin : g_no_ord
            assign o_we = we2; assign o_addr = addr2; assign o_mask = mask2; assign o_data = data2;
        end
    endgenerate
endmodule

// The spine control element: ot_qwen_w12_matvec_part PART 2 without the tree words, the post-scale, the result
// registers and the argmax leaves (those are ot_qwen_me_sptree_w12 / ot_qwen_me_spport_w12), plus the spine's own
// x-network select stage, range fault and fabric-fault register.
module ot_qwen_me_spctl_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer XD = 0,
    parameter integer XVM = 0,
    parameter integer ORD = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer PQ = 4,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer SCALE_LAT = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_amax,
    input  wire              i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    output reg               kv_re,
    // scale requests (ONE CYCLE EARLIER than ot_qwen_me_spine_w12's)
    output reg               scale_re,
    output reg  [(GT >> SMIN)-1:0]    scale_gre,
    output reg  [(GT >> SMIN)*AW-1:0] scale_addr,
    // x reads and the x network's first (select) stage
    output reg  [(1<<SMAX)-1:0]    x_re,
    output reg  [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    output reg  [(1<<SMAX)*32-1:0] xl0,
    // the x read as a descriptor (qwen-rtl-finish 2026-10-07, die master qfd_sp_tree_top): x_re[c] = x_dv for every
    // enabled port, x_addr[c] = x_dc + (c mod 2^x_dsp) * x_dcs (mod 2^AW), the x network select stage's split = x_dsp
    // (op_split, before its 2 + XVM delay).  Equivalent to x_re / x_addr; a caller uses one or the other.
    output reg               x_dv,
    output reg  [AW-1:0]     x_dc,
    output reg  [AW-1:0]     x_dcs,
    output wire [3:0]        x_dsp,
    // tree elements: per level (index = level) the hold/sum select and the adder valid, one cycle early
    output wire [$clog2(GT):0] t_sel_e,
    output wire [$clog2(GT):0] t_tv_e,
    input  wire [W-1:0]        tr_fault,       // the tree elements' registered faults
    // port elements: the element tag fields and valid two cycles early; their argmax nodes and faults
    output wire              p_v_e2,
    output wire [1+1+1+1+4+AW+AW+3*(NW+1)-1:0] p_f_e2,
    input  wire [((GT >> SMIN) / PQ)*(1+32+NW)-1:0] p_am,
    input  wire [((GT >> SMIN) / PQ)-1:0]   p_fault,
    input  wire              fab_fault,
    output wire              ov,
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
    output reg               mx_we,
    output reg  [AW-1:0]     mx_addr,
    output reg  [W-1:0]      mx_mask,
    output reg  [W*32-1:0]   mx_data,
    output reg  [15:0]       progress,
    output wire              fault
);
    // the PART 2 engine top of ot_qwen_w12_matvec_part, fixed here
    localparam integer G = GT;
    localparam integer PART = 2;
    localparam integer GBASE = 0;
    localparam integer GBASE_PORT = 0;
    localparam integer INT8_WEIGHT = 1;
    localparam integer NX = 1 << SMAX;
    localparam integer MEM_EXTRA = 0;
    localparam integer GOUT = GT >> SMIN;
    wire [31:0] i_gbase = 32'd0;
    wire        active_o;
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer FB = IL - ACC_LAT; // circulation delay after the adder
    localparam integer SD = MUL_LAT + ACC_LAT;  // S3 -> the lane sums (products at +MUL_LAT, the accumulator add)
    localparam integer TA = TREE_LAT;     // split-tree adder: ot_hdc_qadd (rtl/hdc/ot_hdc_fastfp.sv), LATENCY 3, or ot_qwen_w12_ladd
    localparam integer TL = TA + 1;       // split-tree cycles per level: the adder + 1 output register
    localparam integer OD = TL * LG;      // split tree
    localparam integer XDD = (PART == 2) ? XD : 0;
    localparam integer LV0 = (PART == 2) ? TCUT : 0;   // tree levels LV0+1..LG live here
    localparam integer PRUNE = (SMIN > 0);
    // result-port groups: the only groups a K-split tree can deliver to
    localparam integer NPG = PRUNE ? (((GT >> SMIN) < G) ? (GT >> SMIN) : G) : G;
    localparam integer NPX = (NX < G) ? NX : G;
    localparam integer LANES = (PART != 2);
    localparam integer PORTS = (PART != 1);
    //: internal widths: the lanes' (GL), the split tree's (GI: the top holds only the positions of
    //: its input level) and the result path's (GR: the result-port groups when pruned)
    localparam integer GL = LANES ? G : 1;
    localparam integer GI = (PART == 2) ? (G >> TCUT) : G;
    localparam integer GR = PRUNE ? NPG : G;
    function automatic [15:0] int8_bf16(input [7:0] code);
        reg [7:0] mag, norm;
        reg [2:0] msb;
        integer bit_index;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            msb = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) msb = bit_index[2:0];
            norm = mag << (3'd7 - msb);
            int8_bf16 = (mag == 0) ? 16'd0 :
                        {code[7], (8'd127 + {5'd0, msb}), norm[6:0]};
        end
    endfunction
    //: the global index of local group 0
    wire [31:0] gb = (GBASE_PORT != 0) ? i_gbase : GBASE;

    // -- issue loop -----------------------------------------------------------
    integer gi;
    reg              active;
    assign active_o = active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r, mmode_r, rmax_r;
    reg [AW-1:0]     mbase_r;
    reg [AW-1:0]     scale_base_r;
    reg [3:0]        split_r;
    reg [AW-1:0]     tstep_r;          // weight step per round: ts, or (G/S)*ts for KV ops
    reg [AW-1:0]     wcs_r;
    reg [NW-1:0]     ktot_r;           // KV ops: the whole K (elements past it multiply +0)
    reg [AW-1:0]     ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r;
    reg [2:0]        jsh_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, xc, xk_base, oa, ot, ot_step;
    reg [NW:0]       nb, nb_t, nb_step;    // first row of the current slot / round (port 0)
    reg [NW:0]       lb, lb_step;          // first lane-vector index of the round (mmode 1)
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);
    //: pruning: an op below the smallest split the pruned tree supports
    reg              split_fault;
    //: KV_PREP > 0: a KV-sourced op waits KV_PREP cycles after its go (ready low) for its per-group KV
    //: offsets, which leave the issue path as a pipelined multiply (see g_kv_addr)
    reg              pend;
    reg [3:0]        pcnt;

    assign ready = !active && !pend;

generate if (FAST_ISSUE == 0) begin : g_issue_legacy
    // tiles one round covers: GT/S (the whole engine's groups)
    wire [$clog2(GT):0] per_round = GT >> i_split;
    //: KV ops cut their whole K interleaved: ceil(K/S) steps
    wire [NW-1:0]    kc_in = i_wsrc ? ((i_k + ((16'd1 << i_split) - 16'd1)) >> i_split) : i_k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; k_r <= kc_in; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; tstep_r <= i_wsrc ? (i_ts * per_round) : i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= (kc_in == 1);
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase; ot_step <= i_ots * per_round;
                nb <= 0; nb_t <= 0; nb_step <= per_round * (W * IL);
                lb <= 0; lb_step <= per_round * W;
            end
        end else begin
            // this cycle's element: (r, k, j) at `cur`
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa + ojs_r; nb <= nb + W; xc <= xc + xjs_r;
                //: the weight word advances once per 2^jsh slots
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur + js_r;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k + 1'b1; k_last <= (k + 2 == k_r);
                    base_k <= base_k + ks_r; cur <= base_k + ks_r;
                    xk <= xk + xks_r; xc <= xk + xks_r;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t + 1'b1; t_last <= (t + 2 == tiles_r);
                        base_t <= base_t + tstep_r; base_k <= base_t + tstep_r; cur <= base_t + tstep_r;
                        ot <= ot + ot_step; oa <= ot + ot_step;
                        nb_t <= nb_t + nb_step; nb <= nb_t + nb_step; lb <= lb + lb_step;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
end else begin : g_issue_fast
    //: FAST_ISSUE (1.2 GHz @ SS): the same schedule, cycle for cycle (plus KV_PREP on KV ops).
    //: (1) The per-op products (the round steps ts*(GT/S), ots*(GT/S), (GT/S)*W*IL, (GT/S)*W and the KV
    //:     K-step count ceil(K/S)) are first needed at the first K or round boundary, IL >= 3 cycles after
    //:     the go: they are two register stages computed from the latched fields, not an input-to-register
    //:     multiply; ts*(GT/S) is shifted adds of ts (GT's set bits), not a multiplier.
    //: (2) Every loop add is ot_qwen_w12_kadd: a Kogge-Stone prefix adder whose levels are kept netlist
    //:     boundaries (ABC re-maps a flattened `+` as a MAJ ripple: 22 cells, -656 ps at SS on `cur`).
    localparam integer PRW = $clog2(GT) + 1;
    //: x * (GT >> s), exactly, as the sum of x shifted to each set bit b >= s of the constant GT (two terms at
    //: 6,144): no multiplier
    function automatic [AW+PRW-1:0] mul_gt_shr(input [AW-1:0] x, input [3:0] sh);
        integer b;
        reg [AW+PRW-1:0] acc;
        begin
            acc = 0;
            for (b = 0; b < PRW; b = b + 1)
                if (((GT >> b) & 1) != 0 && b >= sh) acc = acc + ({{PRW{1'b0}}, x} << (b - sh));
            mul_gt_shr = acc;
        end
    endfunction
    reg [PRW-1:0]    pr_a;                 // GT >> split
    reg [AW+PRW-1:0] tsg_a, otsg_a;        // ts*(GT>>S), ots*(GT>>S)
    reg [NW-1:0]     kc_a;
    localparam [NW:0]   WNB = W;
    localparam [NW-1:0] ONE = 1, TWO = 2;
    //: three stages (the first use is IL >= 3 cycles after the go): the shifted terms, their kept sum, the result
    localparam integer NB_GT = PRW;
    reg [AW+PRW-1:0] tsh [0:NB_GT-1];
    reg [AW+PRW-1:0] osh [0:NB_GT-1];
    reg [NW:0]       kpad_a;
    always @(posedge clk) begin : p_terms
        integer b;
        for (b = 0; b < NB_GT; b = b + 1) begin
            tsh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ts_r} << (b - split_r)) : {(AW+PRW){1'b0}};
            osh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ots_r} << (b - split_r)) : {(AW+PRW){1'b0}};
        end
        pr_a <= GT >> split_r;
        kpad_a <= {1'b0, ktot_r} + ((1 << split_r) - 1);
    end
    wire [AW+PRW-1:0] tsum, osum;
    wire [NB_GT*(AW+PRW)-1:0] tsh_flat, osh_flat;
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_ts (.rows(tsh_flat), .s(tsum));
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_os (.rows(osh_flat), .s(osum));
    genvar tb;
    for (tb = 0; tb < NB_GT; tb = tb + 1) begin : g_fl
        assign tsh_flat[tb*(AW+PRW) +: AW+PRW] = tsh[tb];
        assign osh_flat[tb*(AW+PRW) +: AW+PRW] = osh[tb];
    end
    always @(posedge clk) begin
        tsg_a <= tsum; otsg_a <= osum;
        kc_a <= wsrc_r ? kpad_a[NW-1:0] >> split_r : ktot_r;       // ceil(K/S) (K + S - 1 < 2^NW)
        tstep_r <= !wsrc_r ? ts_r : tsg_a[AW-1:0];
        ot_step <= otsg_a[AW-1:0];
        nb_step <= pr_a * (W * IL);
        lb_step <= pr_a * W;
        k_r <= kc_a;
    end
    //: loop adds
    wire [AW-1:0] cur_js, oa_j, xc_j, bk_k, xk_k, bt_t, ot_t;
    wire [NW:0]   nb_j, nbt_t, lb_t;
    wire [NW-1:0] k_1, k_2, t_1, t_2;
    ot_qwen_w12_kadd #(.W(AW)) u_a0 (.a(cur), .b(js_r), .s(cur_js));
    ot_qwen_w12_kadd #(.W(AW)) u_a1 (.a(oa), .b(ojs_r), .s(oa_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a2 (.a(xc), .b(xjs_r), .s(xc_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a3 (.a(base_k), .b(ks_r), .s(bk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a4 (.a(xk), .b(xks_r), .s(xk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a5 (.a(base_t), .b(tstep_r), .s(bt_t));
    ot_qwen_w12_kadd #(.W(AW)) u_a6 (.a(ot), .b(ot_step), .s(ot_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a7 (.a(nb), .b(WNB), .s(nb_j));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a8 (.a(nb_t), .b(nb_step), .s(nbt_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a9 (.a(lb), .b(lb_step), .s(lb_t));
    ot_qwen_w12_kadd #(.W(NW)) u_a10 (.a(k), .b(ONE), .s(k_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a11 (.a(k), .b(TWO), .s(k_2));
    ot_qwen_w12_kadd #(.W(NW)) u_a12 (.a(t), .b(ONE), .s(t_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a13 (.a(t), .b(TWO), .s(t_2));
    //: the go's own first-boundary flags, without the K-step divide: ceil(K/S) == 1 <=> K <= S
    wire kc_is_1 = i_wsrc ? ({{(32-NW){1'b0}}, i_k} <= (32'd1 << i_split)) : (i_k == 1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (pend) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (pcnt == 0) begin pend <= 1'b0; active <= 1'b1; end
            else pcnt <= pcnt - 1'b1;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                if (KV_PREP > 0 && i_wsrc) begin pend <= 1'b1; pcnt <= KV_PREP - 1; end
                else active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= kc_is_1;
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase;
                nb <= 0; nb_t <= 0;
                lb <= 0;
            end
        end else begin
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa_j; nb <= nb_j; xc <= xc_j;
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur_js;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k_1; k_last <= (k_2 == k_r);
                    base_k <= bk_k; cur <= bk_k;
                    xk <= xk_k; xc <= xk_k;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t_1; t_last <= (t_2 == tiles_r);
                        base_t <= bt_t; base_k <= bt_t; cur <= bt_t;
                        ot <= ot_t; oa <= ot_t;
                        nb_t <= nbt_t; nb <= nbt_t; lb <= lb_t;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
end endgenerate

    // -- x reads -------------------------------------------------------------------------------------------
    //: accepted go: the edge that latches split_r / xcs_r (pend is never set on the FAST_ISSUE = 0 loop)
    wire go_acc = go && !active && !pend;
    //: x_re: the per-port enable (port < GT/S tiles of chunks) is a function of the op's split only -> latched at the go
    reg [NPX-1:0] xre_en;
    always @(posedge clk)
        if (go_acc)
            for (gi = 0; gi < NPX; gi = gi + 1)
                xre_en[gi] <= (((gb + gi) >> i_split) < (GT >> i_split));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) x_re <= 0;
        else if (!active) x_re <= 0;
        else
            for (gi = 0; gi < NX; gi = gi + 1)
                x_re[gi] <= (gi < NPX) && xre_en[gi];
    end
    //: descriptor form of the same read (registered on the same edges as x_re / x_addr)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) x_dv <= 1'b0;
        else x_dv <= active;
    end
    always @(posedge clk) begin
        x_dc <= xc;
        if (go_acc) x_dcs <= i_xcs;
    end
    //: x_addr = xc + c * xcs (c = port mod S): c * xcs is constant through the op, latched at the go as the
    //: carry-save pair of its shifted rows (one row per set bit b of the port number, kept when b < split)
    function automatic integer pc_below(input integer v, input integer b);
        integer i;
        begin pc_below = 0; for (i = 0; i < b; i = i + 1) pc_below = pc_below + ((v >> i) & 1); end
    endfunction
    genvar xg, xb;
    generate
        for (xg = 0; xg < NX; xg = xg + 1) begin : g_xa
            localparam integer NB = pc_below(xg, 16);
            if (xg >= NPX) begin : g_none
                always @(posedge clk) x_addr[xg*AW +: AW] <= {AW{1'b0}};
            end else if (NB == 0) begin : g_zero
                always @(posedge clk) x_addr[xg*AW +: AW] <= xc;
            end else begin : g_off
                wire [NB*AW-1:0] rows;
                for (xb = 0; xb < 16; xb = xb + 1) begin : g_r
                    if ((xg >> xb) & 1) begin : g_set
                        assign rows[pc_below(xg, xb)*AW +: AW] = (xb < i_split) ? (i_xcs << xb) : {AW{1'b0}};
                    end
                end
                wire [AW-1:0] r_s, r_c;
                ot_qwen_w12_csa_tree #(.W(AW), .N(NB)) u_cs (.rows(rows), .s(r_s), .c(r_c));
                reg  [AW-1:0] o_s, o_c;
                always @(posedge clk) if (go_acc) begin o_s <= r_s; o_c <= r_c; end
                wire [AW-1:0] a_s = xc ^ o_s ^ o_c;
                wire [AW-1:0] a_c = ((xc & o_s) | (xc & o_c) | (o_s & o_c)) << 1;
                wire [AW-1:0] a_y;
                ot_qwen_w12_kadd #(.W(AW)) u_ka (.a(a_s), .b(a_c), .s(a_y));
                always @(posedge clk) x_addr[xg*AW +: AW] <= a_y;
            end
        end
    endgenerate

    // -- element tags (as ot_qwen_w12_matvec_part; no lanes here) -----------------------------------------
    reg          e_v, e_first, e_last, e_oen, e_amax, e_wsrc, e_round, e_mmode;
    reg [3:0]    e_split;
    reg          e_rmax, e_opend;
    reg [2:0]    e_j;
    reg [AW-1:0] e_mbase;
    reg [AW-1:0] e_oa, e_ots;
    reg [NW:0]   e_nb, e_lb, e_rem;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0;
        else e_v <= active;
    end
    reg [NW-1:0] e_t, s1_t, s1b_t, s2_t, s3_t;
    wire [NW-1:0] m_t;
    ot_hdc_delay #(.W(NW), .D(MEM_EXTRA)) u_mtt (.clk(clk), .rst_n(rst_n), .d(e_t), .q(m_t));
    always @(posedge clk) begin e_t <= t; s1_t <= m_t; s1b_t <= s1_t; s2_t <= s1b_t; s3_t <= s2_t; end
    always @(posedge clk) begin
        e_first <= (k == 0); e_last <= k_last;
        e_oen <= oen_r; e_amax <= amax_r; e_wsrc <= wsrc_r; e_round <= round_r; e_mmode <= mmode_r;
        e_split <= split_r; e_oa <= oa; e_ots <= ots_r; e_nb <= nb; e_lb <= lb;
        e_rem <= {1'b0, nout_r};
        e_rmax <= rmax_r; e_j <= j; e_mbase <= mbase_r;
        e_opend <= t_last && k_last && j_last;
    end
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1) + 1 + 3 + 1 + AW + AW;
    wire [TW-1:0] e_tag = {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_rem,
                           e_rmax, e_j, e_opend, e_mbase, scale_base_r};
    reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;
    wire [TW-1:0] m_tag;
    wire          m_first, m_wsrc, m_round;
    wire [MEM_EXTRA+2:0] m_vl;
    ot_hdc_vline #(.D(MEM_EXTRA + 2)) u_mv (.clk(clk), .rst_n(rst_n), .v(e_v), .vd(m_vl));
    wire          m_v = m_vl[MEM_EXTRA];
    ot_hdc_delay #(.W(TW + 3), .D(MEM_EXTRA)) u_mt (.clk(clk), .rst_n(rst_n),
        .d({e_tag, e_first, e_wsrc, e_round}), .q({m_tag, m_first, m_wsrc, m_round}));
    reg          s1_v, s1b_v, s2_v, s3_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s1b_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= m_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end
    end
    always @(posedge clk) begin
        s1_tag <= m_tag; s1b_tag <= s1_tag; s2_tag <= s1b_tag; s3_tag <= s2_tag;
    end
    //: a_tag = s3_tag + (SD + OD + XDD); the port elements take it TWO cycles early (a_tag_e2) and register it twice
    localparam integer AD = SD + OD + XDD;
    wire [TW-1:0] a_tag_e2;
    reg  [TW-1:0] a_tag_e1, a_tag;
    ot_qwen_me_rdelay_w12 #(.W(TW), .D(AD - 2)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag_e2));
    always @(posedge clk) begin a_tag_e1 <= a_tag_e2; a_tag <= a_tag_e1; end
    wire [AD:0] vline;
    ot_hdc_vline #(.D(AD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    assign p_v_e2 = vline[AD - 2];
    wire          pf_last, pf_oen, pf_amax, pf_wsrc, pf_mmode, pf_rmax, pf_opend;
    wire [3:0]    pf_split;
    wire [AW-1:0] pf_oa, pf_ots, pf_mbase, pf_sbase;
    wire [NW:0]   pf_nb, pf_lb, pf_nout;
    wire [2:0]    pf_j;
    assign {pf_last, pf_oen, pf_amax, pf_wsrc, pf_mmode, pf_split, pf_oa, pf_ots, pf_nb, pf_lb, pf_nout,
            pf_rmax, pf_j, pf_opend, pf_mbase, pf_sbase} = a_tag_e2;
    assign p_f_e2 = {pf_last, pf_oen, pf_wsrc, pf_mmode, pf_split, pf_oa, pf_ots, pf_nb, pf_lb, pf_nout};

    // -- split tree control: level lv's input split (split_at), its select and adder valid ----------------
    //: split_at[lv] at level lv+1's input; sat_e[lv] the same value one cycle earlier
    wire [LG*4+3:0] split_at, sat_e;
    wire [3:0] t_split, t_split_e;
    localparam integer D0 = SD + TL * LV0 + XDD;
    ot_qwen_me_rdelay_w12 #(.W(4), .D(D0 - 1)) u_ts (.clk(clk), .rst_n(rst_n), .d(s3_tag[TW-6 -: 4]), .q(t_split_e));
    reg [3:0] t_split_r;
    always @(posedge clk) t_split_r <= t_split_e;
    assign t_split = t_split_r;
    assign split_at[4*LV0+3 -: 4] = t_split;
    assign sat_e[4*LV0+3 -: 4] = t_split_e;
    genvar lv;
    generate
        for (lv = 0; lv <= LG; lv = lv + 1) begin : g_lctl
            if (lv <= LV0) begin : g_none
                assign t_sel_e[lv] = 1'b0;
                assign t_tv_e[lv] = 1'b0;
            end else begin : g_lvl
                //: sp_sel = split_at[lv-1] + TA (the select when the level's sums emerge); sp_e one cycle earlier
                wire [3:0] sp_e;
                reg  [3:0] sp_sel, sp_out;
                ot_hdc_delay #(.W(4), .D(TA - 1)) u_sd (.clk(clk), .rst_n(rst_n), .d(split_at[4*lv-1 -: 4]), .q(sp_e));
                always @(posedge clk) begin sp_sel <= sp_e; sp_out <= sp_sel; end
                assign split_at[4*lv+3 -: 4] = sp_out;
                assign sat_e[4*lv+3 -: 4] = sp_sel;
                assign t_sel_e[lv] = (sp_e >= lv);
                assign t_tv_e[lv] = vline[SD + TL*(lv-1) + XDD - 1] && (sat_e[4*lv-1 -: 4] >= lv);
            end
        end
    endgenerate

    // -- post-scale: the scale requests, ONE CYCLE EARLIER than the monolithic engine's ---------------------
    //: pre = s3 + (SD - 2 + OD + XDD) in ot_qwen_w12_matvec_part; here s3 + (SD - 3 + OD + XDD); the port element
    //: registers scale_q once before its multiplier, so the multiplier sees the same word on the same edge
    localparam integer PD = SD - 3 + OD + XDD;
    wire [TW-1:0] pre_tag;
    wire [PD:0]   pre_vline;
    ot_qwen_me_rdelay_w12 #(.W(TW), .D(PD)) u_pretag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(pre_tag));
    ot_hdc_vline #(.D(PD)) u_prev (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(pre_vline));
    wire [NW-1:0] pre_t;
    generate if (SCALE_LOCAL != 0) begin : g_pret
        ot_qwen_me_rdelay_w12 #(.W(NW), .D(PD)) u_pret (.clk(clk), .rst_n(rst_n), .d(s3_t), .q(pre_t));
    end else begin : g_nopret
        assign pre_t = {NW{1'b0}};
    end endgenerate
    wire pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode, pre_rmax, pre_opend;
    wire [3:0] pre_split;
    wire [AW-1:0] pre_oa, pre_ots, pre_mbase, pre_sbase;
    wire [NW:0] pre_nb, pre_lb, pre_nout;
    wire [2:0] pre_j;
    assign {pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode, pre_split, pre_oa, pre_ots, pre_nb, pre_lb, pre_nout,
            pre_rmax, pre_j, pre_opend, pre_mbase, pre_sbase} = pre_tag;
    wire [GOUT-1:0] pre_scale_active;
    genvar pg;
    generate
        for (pg = 0; pg < NPG; pg = pg + 1) begin : g_scale_request_mask
            assign pre_scale_active[pg] = pre_vline[PD] && pre_last && !pre_wsrc &&
                ((gb + pg) < (GT >> pre_split)) &&
                (pre_mmode ? (pre_lb + (gb + pg)*W < pre_nout) :
                             (pre_nb + (gb + pg)*(W*IL) < pre_nout));
        end
    endgenerate
    integer sg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin scale_re <= 1'b0; scale_gre <= 0; end
        else begin scale_re <= |pre_scale_active; scale_gre <= pre_scale_active; end
    end
    always @(posedge clk) begin
        for (sg = 0; sg < NPG; sg = sg + 1)
            scale_addr[sg*AW +: AW] <= !pre_scale_active[sg] ? pre_sbase :
                (SCALE_LOCAL != 0) ? pre_sbase + pre_t * IL + pre_j :
                                     pre_sbase + (pre_nb >> LW) + (gb + sg) * IL;
    end

    // -- result tag (a_tag + SCALE_LAT, the post-scale multiply) and the result valid ---------------------------------
    wire [TW-1:0] result_tag;
    wire [SCALE_LAT:0] vd;
    ot_qwen_me_rdelay_w12 #(.W(TW), .D(SCALE_LAT)) u_rtag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(result_tag));
    ot_hdc_vline #(.D(SCALE_LAT)) u_rv (.clk(clk), .rst_n(rst_n), .v(vline[AD]), .vd(vd));
    wire [SCALE_LAT:0] post_pending = vd;
    wire          r_v = vd[SCALE_LAT];
    wire          r_last, r_oen, r_amax, r_wsrc, r_mmode;
    wire [3:0]    r_split;
    wire [AW-1:0] r_oa, r_ots;
    wire [NW:0]   r_nb, r_lb, r_nout;
    wire          r_rmax, r_opend;
    wire [2:0]    r_j;
    wire [AW-1:0] r_mbase, r_sbase;
    assign {r_last, r_oen, r_amax, r_wsrc, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout,
            r_rmax, r_j, r_opend, r_mbase, r_sbase} = result_tag;

    // -- fault: the tree elements register their adders' faults (as fault_q[G] here); the port elements
    //: register their multipliers' faults (seen one cycle later than the monolithic engine's)
    reg  fq_t;
    reg  [3:0] range_q;
    reg  range_fault;
    reg  fault_in;
    reg  fault_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fq_t <= 1'b0; fault_r <= 1'b0; fault_in <= 1'b0; range_fault <= 1'b0; end
        else begin
            fault_in <= fab_fault;
            fq_t <= fault_in;
            fault_r <= fq_t | (|tr_fault) | (|p_fault) | split_fault;
            if (go && ready && (i_split > SMAX)) range_fault <= 1'b1;
        end
    end
    assign fault = fault_r | range_fault;

    // -- results: the valid line (the data are the port elements') ---------------------------------------------
    reg ov1, ov2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov1 <= 1'b0; ov2 <= 1'b0; end
        else begin ov1 <= r_v && r_last; ov2 <= ov1; end
    end
    wire [ORD+2:0] ov_line;
    ot_hdc_vline #(.D(ORD + 2)) u_ovl (.clk(clk), .rst_n(rst_n), .v(ov2), .vd(ov_line));
    generate if (ORD > 0) begin : g_ord
        assign ov = ov_line[ORD];
    end else begin : g_no_ord
        assign ov = ov2;
    end endgenerate

    // -- argmax: levels LPT+1 .. LV over the port elements' level-LPT nodes ---------------------------------
    localparam integer NL = NPG * W;
    localparam integer LV = $clog2(NL);
    localparam integer AN = 1 << LV;
    localparam integer LPT = $clog2(PQ * W);
    localparam integer NPT = NPG / PQ;
    localparam integer CW = 1 + 32 + NW;
    wire [CW*AN-1:0] alv [LPT:LV];
    reg  [LV:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LV-1:0], r_v && r_last && (r_amax || r_rmax)};
    end
    wire [1+3+1+AW-1:0] ttag;
    ot_qwen_me_rdelay_w12 #(.W(1 + 3 + 1 + AW), .D(LV + 1)) u_ttag (.clk(clk), .rst_n(rst_n),
        .d({r_rmax, r_j, r_opend && r_last, r_mbase}), .q(ttag));
    wire          t_rmax, t_opend;
    wire [2:0]    t_j;
    wire [AW-1:0] t_mbase;
    assign {t_rmax, t_j, t_opend, t_mbase} = ttag;
    genvar e, al;
    generate
        assign alv[LPT][CW*NPT-1:0] = p_am;
        if ((AN >> LPT) > NPT) begin : g_ppad
            assign alv[LPT][CW*AN-1:CW*NPT] = 0;
        end else if (AN > (AN >> LPT)) begin : g_ppad2
            assign alv[LPT][CW*AN-1:CW*(AN >> LPT)] = 0;
        end
        for (al = LPT + 1; al <= LV; al = al + 1) begin : g_alvl
            for (e = 0; e < (AN >> al); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[al-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[al-1][CW*(2*e+1) +: CW];
                //: key0 > key1, or equal keys and row0 < row1  <=>  {key0, ~row0} > {key1, ~row1}: one kept
                //: prefix carry (A > B <=> carry out of A + ~B), not Yosys's rippled > / == / <
                wire          gt, gt_c;
                wire [32+NW-1:0] gt_s;
                ot_qwen_w12_ksa #(.W(32 + NW)) u_gt (.a({x0[CW-2 -: 32], ~x0[NW-1:0]}), .b(~{x1[CW-2 -: 32], ~x1[NW-1:0]}),
                    .cin(1'b0), .s(gt_s), .cout(gt_c));
                assign gt = gt_c;
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || gt);
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[al][CW*e +: CW] = c;
            end
            assign alv[al][CW*AN-1 : CW*(AN >> al)] = 0;
        end
    endgenerate
    wire [CW-1:0] top = alv[LV][CW-1:0];
    wire          top_v = top[CW-1];
    wire [31:0]   top_key = top[CW-2 -: 32];
    wire [31:0]   top_val = top_key[31] ? {1'b0, top_key[30:0]} : ~top_key;
    wire [NW-1:0] top_idx = top[NW-1:0];
    reg [31:0] best_key;
    //: top > best (key, then the lower index): the same kept carry as the tree nodes
    wire best_gt;
    wire [32+NW-1:0] best_s;
    ot_qwen_w12_ksa #(.W(32 + NW)) u_bgt (.a({top_key, ~top_idx}), .b(~{best_key, ~am_idx}), .cin(1'b0), .s(best_s),
        .cout(best_gt));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            am_any <= 1'b0; am_idx <= 0; am_val <= 0; best_key <= 0;
        end else begin
            if (go && ready && i_amax) am_any <= 1'b0;
            else if (tv[LV] && !t_rmax && top_v && (!am_any || best_gt)) begin
                am_any <= 1'b1; best_key <= top_key; am_idx <= top_idx; am_val <= top_val;
            end
        end
    end
    reg [31:0] rk [0:IL-1];
    reg [IL-1:0] rseen;
    integer rj;
    wire [31:0] rk_j = rk[t_j];
    wire        rk_ge, rk_c;
    wire [31:0] rk_s;
    //: rk_j >= top_key (carry out of rk_j + ~top_key + 1), kept prefix
    ot_qwen_w12_ksa #(.W(32)) u_rge (.a(rk_j), .b(~top_key), .cin(1'b1), .s(rk_s), .cout(rk_c));
    assign rk_ge = rk_c;
    wire [31:0] nk = (!top_v || (rseen[t_j] && rk_ge)) ? rk_j : top_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rseen <= 0; mx_we <= 1'b0; end
        else begin
            mx_we <= 1'b0;
            if (tv[LV] && t_rmax) begin
                if (t_opend) begin
                    mx_we <= 1'b1;
                    rseen <= 0;
                end else if (top_v) begin
                    rk[t_j] <= nk;
                    rseen[t_j] <= 1'b1;
                end
            end
        end
    end
    always @(posedge clk) begin
        if (tv[LV] && t_rmax && t_opend) begin
            mx_addr <= t_mbase >> LW;
            mx_mask <= {W{1'b0}};
            mx_data <= {(W*32){1'b0}};
            for (rj = 0; rj < IL; rj = rj + 1) begin
                mx_mask[(t_mbase[LW-1:0] + rj) % W] <= 1'b1;
                mx_data[32*((t_mbase[LW-1:0] + rj) % W) +: 32] <=
                    (rj == t_j) ? (nk[31] ? {1'b0, nk[30:0]} : ~nk) : (rk[rj][31] ? {1'b0, rk[rj][30:0]} : ~rk[rj]);
            end
        end
    end

    // -- progress, idle (as ot_qwen_w12_matvec_part) ----------------------------------------------------------
    reg [15:0] n_last_issued, n_ov, ov_mark;
    wire [15:0] ov_done = n_ov - ov_mark;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_last_issued <= 0; n_ov <= 0; ov_mark <= 0; progress <= 0;
        end else begin
            n_last_issued <= n_last_issued + ((active && k_last) ? 16'd1 : 16'd0);
            n_ov <= n_ov + (ov ? 16'd1 : 16'd0);
            if (go && ready) begin
                ov_mark <= n_last_issued; progress <= 0;
            end else begin
                progress <= ov_done[15] ? 16'd0 : ov_done;
            end
        end
    end
    localparam [ORD+2:0] OMASK = (1 << (ORD + 1)) - 2;
    wire ord_busy = |(ov_line & OMASK);
    wire idle_c = !active && !pend && !e_v && !(|m_vl) && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|post_pending) && !(|tv) && !ov1
                  && !ov2 && !ord_busy && !mx_we;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end

    // -- x network select stage: the split of the element whose x arrives now (ot_qwen_me_spine_w12) -------
    localparam integer NXL = NX / TG;
    reg  [3:0] op_split;
    always @(posedge clk) if (go && ready) op_split <= i_split;
    assign x_dsp = op_split;
    wire [3:0] x_split;
    ot_hdc_delay #(.W(4), .D(2 + XVM)) u_xs (.clk(clk), .rst_n(rst_n), .d(op_split), .q(x_split));
    genvar r, i;
    generate
        for (r = 0; r < NXL; r = r + 1) begin : g_line
            wire [SMAX:0] quads = (1 << x_split) / TG;
            wire [SMAX:0] src = r & (quads - 1);
            for (i = 0; i < TG; i = i + 1) begin : g_e
                always @(posedge clk) xl0[(r*TG + i)*32 +: 32] <= x_q[(src*TG + i)*32 +: 32];
            end
        end
    endgenerate
endmodule

// One lane of the spine's split-tree levels TCUT+1 .. LG-1 (ot_qwen_w12_matvec_part g_lvl, PART 2): position p of
// level lv adds positions 2p, 2p+1 of level lv-1 (p < GT >> lv), or holds position p for TA cycles (p < NPG) when
// the op's split is below lv.  Lanes never mix in the tree, so the spine's tree top is W copies of this element.
// Inputs land in flops: the level-TCUT words (the last of the TWS wire stages, TINREG), the per-level select
// and adder valid (taken one cycle early from the control element).  Output: level LG-1, positions 0..NPG-1.
module ot_qwen_me_sptree_w12 #(
    parameter integer GT = 80,
    parameter integer SMIN = 3,
    parameter integer TCUT = 3,
    parameter integer TREE_LAT = 3,
    parameter integer TINREG = 1,
    parameter integer FREG = 0          // 1: each level's adder-fault OR registered before the fault OR (+1 fault latency)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [(GT >> TCUT)*32-1:0] t_in,       // this lane of tree level TCUT
    input  wire [$clog2(GT):0] sel_e,             // per level: (split >= level) when its sums emerge, one cycle early
    input  wire [$clog2(GT):0] tv_e,              // per level: the adders' valid, one cycle early
    output wire [(GT >> SMIN)*32-1:0] y,          // this lane of tree level LG-1, the result-port positions
    output reg         fault
);
    localparam integer LG = $clog2(GT);
    localparam integer LV0 = TCUT;
    localparam integer GI = GT >> TCUT;
    localparam integer NPG = GT >> SMIN;
    localparam integer TA = TREE_LAT;
    localparam integer PRUNE = (SMIN > 0);
    reg  [LG:0] sel_r, tv_r;
    always @(posedge clk) sel_r <= sel_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) tv_r <= 0; else tv_r <= tv_e;
    //: level lv's words at lvf[lv*GI*32 +: GI*32] (a flat vector: Yosys 0.68 asserts on a wire array here)
    wire [LG*GI*32-1:0] lvf;
    wire [LG:0] tfault;
    generate if (TINREG != 0) begin : g_tin
        reg [GI*32-1:0] tin_q;
        always @(posedge clk) tin_q <= t_in;
        assign lvf[LV0*GI*32 +: GI*32] = tin_q;
    end else begin : g_tin_w
        assign lvf[LV0*GI*32 +: GI*32] = t_in;
    end endgenerate
    assign tfault[LV0:0] = 0;
    assign tfault[LG] = 1'b0;
    genvar lv, p;
    generate
        for (lv = LV0 + 1; lv <= LG - 1; lv = lv + 1) begin : g_lvl
            localparam integer ALWAYS = PRUNE && (SMIN >= lv);
            localparam integer HOLD_TO = NPG;
            localparam integer R0 = (GT >> lv);
            localparam integer R1 = ALWAYS ? R0 : ((HOLD_TO > R0) ? HOLD_TO : R0);
            localparam integer RW = (R1 > 0) ? R1 : 1;
            localparam integer PAIRS = R0;
            reg  [RW*32-1:0] lq;
            wire [GI*32-1:0] held;
            wire [(PAIRS > 0 ? PAIRS : 1)-1:0] pf;
            if (PAIRS == 0) begin : g_nopf
                assign pf = 1'b0;
            end
            if (!ALWAYS && HOLD_TO > 0) begin : g_hold
                ot_qwen_me_rdelay_w12 #(.W(HOLD_TO*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_n),
                    .d(lvf[(lv-1)*GI*32 +: HOLD_TO*32]), .q(held[HOLD_TO*32-1:0]));
                if (HOLD_TO < GI) begin : g_hz
                    assign held[GI*32-1:HOLD_TO*32] = 0;
                end
            end else begin : g_nohold
                assign held = {GI*32{1'b0}};
            end
            for (p = 0; p < PAIRS; p = p + 1) begin : g_add
                wire [31:0] s_out;
                ot_qwen_w12_tadd #(.LAT(TREE_LAT)) u_add (clk, rst_n, tv_r[lv],
                                   lvf[(lv-1)*GI*32 + 32*(2*p) +: 32], lvf[(lv-1)*GI*32 + 32*(2*p+1) +: 32], s_out, pf[p]);
                if (ALWAYS) begin : g_a
                    always @(posedge clk) lq[32*p +: 32] <= s_out;
                end else begin : g_s
                    always @(posedge clk) lq[32*p +: 32] <= sel_r[lv] ? s_out : held[32*p +: 32];
                end
            end
            if (R1 > R0) begin : g_rest
                always @(posedge clk) lq[R1*32-1 : R0*32] <= held[R1*32-1 : R0*32];
            end
            if (R1 == 0) begin : g_lz
                assign lvf[lv*GI*32 +: GI*32] = {GI*32{1'b0}};
            end else if (R1 < GI) begin : g_lp
                assign lvf[lv*GI*32 +: GI*32] = {{((GI - R1) * 32){1'b0}}, lq};
            end else begin : g_lf
                assign lvf[lv*GI*32 +: GI*32] = lq;
            end
            assign tfault[lv] = |pf;
        end
    endgenerate
    assign y = lvf[(LG-1)*GI*32 +: NPG*32];
    wire [LG:0] tf_u;
    generate if (FREG != 0) begin : g_freg
        reg [LG:0] tf_q;
        always @(posedge clk or negedge rst_n) if (!rst_n) tf_q <= 0; else tf_q <= tfault;
        assign tf_u = tf_q;
    end else begin : g_fw
        assign tf_u = tfault;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else fault <= |tf_u;
    end
endmodule

// PQ result-port groups of the spine (ot_qwen_w12_matvec_part PART 2 g_post_scale / results / argmax leaves) for
// global groups q = pt_id*PQ .. +PQ-1 (pt_id: a strap, so every port element is one netlist): tree level LG (at
// GT >> LG == 0 a pure TA-cycle hold of level LG-1, then the level register), the INT8 post-scale (scale_q captured
// in a register first, its request having left one cycle early), the two result registers, the argmax leaves and
// the first log2(PQ*W) argmax levels.  The element tags arrive TWO cycles early: stage E registers them and forms
// the per-group quantities (group in range, nout - row base, row base, (q0+g)*ots) with kept adders; stage A (the
// monolithic engine's a_tag cycle) registers those, so the lane mask is a 4-bit compare, and the result tag
// (a + SCALE_LAT) carries the finished mask, rows and addresses: zero added cycles.
module ot_qwen_me_spport_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer GT = 80,
    parameter integer SMIN = 3,
    parameter integer PQ = 4,
    parameter integer TREE_LAT = 3,
    parameter integer SCALE_LAT = 5       // 5: ot_hdc_fmul (the monolithic engine's); 6: ot_hdc_fp32_mul_lat #(6)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       pt_id,
    input  wire [PQ*W*32-1:0] lv_in,          // tree level LG-1 at positions pt_id*PQ.., word-major (position, lane)
    input  wire              a_v_e2,
    input  wire [1+1+1+1+4+AW+AW+3*(NW+1)-1:0] a_f_e2,
    input  wire [PQ*W*16-1:0] scale_q,
    output reg  [PQ-1:0]     o_we,
    output reg  [PQ*AW-1:0]  o_addr,
    output reg  [PQ*W-1:0]   o_mask,
    output reg  [PQ*W*32-1:0] o_data,
    output wire [1+32+NW-1:0] am,
    output reg               fault
);
    localparam integer TA = TREE_LAT;
    localparam integer NL = PQ * W;
    localparam integer LPT = $clog2(NL);
    localparam integer CW = 1 + 32 + NW;
    localparam integer FW = 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1);
    localparam integer BW = 32;
    // -- tree level LG: hold TA, then the level register ---------------------------------------------------
    wire [NL*32-1:0] held;
    reg  [NL*32-1:0] raw_res;
    ot_qwen_me_rdelay_w12 #(.W(NL*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_n), .d(lv_in), .q(held));
    always @(posedge clk) raw_res <= held;
    // -- stage E: the tags (a - 1) ------------------------------------------------------------------------------
    reg          e_v;
    reg [FW-1:0] e_f;
    always @(posedge clk or negedge rst_n) if (!rst_n) e_v <= 1'b0; else e_v <= a_v_e2;
    always @(posedge clk) e_f <= a_f_e2;
    wire          e_last, e_oen, e_wsrc, e_mmode;
    wire [3:0]    e_split;
    wire [AW-1:0] e_oa, e_ots;
    wire [NW:0]   e_nb, e_lb, e_nout;
    assign {e_last, e_oen, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_nout} = e_f;
    wire [31:0] q0 = {16'd0, pt_id} * PQ;
    wire [$clog2(GT):0] e_ports = GT >> e_split;
    localparam integer QB = 16;
    wire [PQ-1:0]     e_gok, e_pos, e_big;
    wire [PQ*4-1:0]   e_dlo;
    wire [PQ*BW-1:0]  e_rowb;
    wire [PQ*AW-1:0]  e_qots;
    genvar b, g, e;
    generate for (g = 0; g < PQ; g = g + 1) begin : g_e
        wire [31:0] qg = q0 + g;
        assign e_gok[g] = (qg < e_ports);
        //: row base nb + qg*W*IL, lane-vector base lb + qg*W; the lane mask is base + lane < nout
        wire [BW-1:0] rowb, lvb, base, nd;
        ot_qwen_w12_kadd #(.W(BW)) u_rb (.a({{(BW-NW-1){1'b0}}, e_nb}), .b(qg * (W * IL)), .s(rowb));
        ot_qwen_w12_kadd #(.W(BW)) u_lb (.a({{(BW-NW-1){1'b0}}, e_lb}), .b(qg * W), .s(lvb));
        assign base = e_mmode ? lvb : rowb;
        //: nout - base (base <= nout - 1 iff the borrow is clear and the difference is non-zero)
        wire nd_c;
        ot_qwen_w12_ksa #(.W(BW)) u_nd (.a({{(BW-NW-1){1'b0}}, e_nout}), .b(~base), .cin(1'b1), .s(nd), .cout(nd_c));
        assign e_pos[g] = nd_c && (nd != 0);
        assign e_big[g] = (nd[BW-1:4] != 0);
        assign e_dlo[g*4 +: 4] = nd[3:0];
        assign e_rowb[g*BW +: BW] = rowb;
        //: (q0 + g) * ots
        wire [QB*AW-1:0] qrows;
        wire [AW-1:0] qs, qc;
        for (b = 0; b < QB; b = b + 1) begin : g_qr
            assign qrows[b*AW +: AW] = qg[b] ? (e_ots << b) : {AW{1'b0}};
        end
        ot_qwen_w12_csa_tree #(.W(AW), .N(QB)) u_qcs (.rows(qrows), .s(qs), .c(qc));
        ot_qwen_w12_kadd #(.W(AW)) u_qka (.a(qs), .b(qc), .s(e_qots[g*AW +: AW]));
    end endgenerate
    // -- stage A (the monolithic a_tag cycle) --------------------------------------------------------------------
    reg              raw_v, raw_last, raw_oen, raw_wsrc;
    reg  [AW-1:0]    raw_oa;
    reg  [PQ-1:0]    a_gok, a_pos, a_big;
    reg  [PQ*4-1:0]  a_dlo;
    reg  [PQ*BW-1:0] a_rowb;
    reg  [PQ*AW-1:0] a_qots;
    always @(posedge clk or negedge rst_n) if (!rst_n) raw_v <= 1'b0; else raw_v <= e_v;
    always @(posedge clk) begin
        raw_last <= e_last; raw_oen <= e_oen; raw_wsrc <= e_wsrc; raw_oa <= e_oa;
        a_gok <= e_gok; a_pos <= e_pos; a_big <= e_big; a_dlo <= e_dlo; a_rowb <= e_rowb; a_qots <= e_qots;
    end
    //: lane l of group g is active (an output row): (q0+g < GT >> split) && base + l < nout
    wire [NL-1:0]    act;
    wire [NL*NW-1:0] rows;
    generate for (e = 0; e < NL; e = e + 1) begin : g_act
        localparam integer EQ = e / W, EL = e % W;
        assign act[e] = a_gok[EQ] && a_pos[EQ] && (a_big[EQ] || (a_dlo[EQ*4 +: 4] > EL));
        wire [NW-1:0] r;
        ot_qwen_w12_kadd #(.W(NW)) u_row (.a(a_rowb[EQ*BW +: NW]), .b(EL[NW-1:0]), .s(r));
        assign rows[e*NW +: NW] = r;
    end endgenerate
    // -- post-scale ----------------------------------------------------------------------------------------------
    reg  [NL*16-1:0] sq;
    always @(posedge clk) sq <= scale_q;
    wire [NL*32-1:0] res;
    wire [NL-1:0]    sf;
    generate for (e = 0; e < NL; e = e + 1) begin : g_scale
        if (SCALE_LAT == 5) begin : g_fmul
            ot_hdc_fmul u_mul (.clk(clk), .rst_n(rst_n), .v(raw_v && raw_last && act[e]),
                .a(raw_res[32*e +: 32]), .b({raw_wsrc ? 16'h3F80 : sq[16*e +: 16], 16'd0}),
                .y(res[32*e +: 32]), .fault(sf[e]));
        end else begin : g_lat
            //: bit-identical to ot_hdc_fmul (ot_hdc_fp32_mul_fast cut at SCALE_LAT stages; rtl/test/tb_hdc_fastfp_equiv.sv,
            //: rtl/test/tb_w11_fp32_mul_lat.cpp); routed alone at 0.833 ns SS +11.4 ps at LAT 6
            wire [1:0] err;
            wire vo;
            ot_hdc_fp32_mul_lat #(.LAT(SCALE_LAT)) u_mul (.clk(clk), .rst_n(rst_n), .valid_in(raw_v && raw_last && act[e]),
                .a(raw_res[32*e +: 32]), .b({raw_wsrc ? 16'h3F80 : sq[16*e +: 16], 16'd0}),
                .y(res[32*e +: 32]), .err(err), .valid_out(vo));
            assign sf[e] = vo && (err != 2'd0);
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= |sf;
    // -- result tag: a + SCALE_LAT, carrying the finished mask, rows and addresses -------------------------------
    localparam integer RW = 1 + 1 + PQ + AW + PQ*AW + NL + NL*NW;
    wire [PQ*AW-1:0] a_oaq;
    generate for (g = 0; g < PQ; g = g + 1) begin : g_oa
        ot_qwen_w12_kadd #(.W(AW)) u_a (.a(raw_oa), .b(a_qots[g*AW +: AW]), .s(a_oaq[g*AW +: AW]));
    end endgenerate
    wire [RW-1:0] rt;
    wire [SCALE_LAT:0] rv;
    ot_qwen_me_rdelay_w12 #(.W(RW), .D(SCALE_LAT)) u_rt (.clk(clk), .rst_n(rst_n),
        .d({raw_last, raw_oen, a_gok, raw_oa, a_oaq, act, rows}), .q(rt));
    ot_hdc_vline #(.D(SCALE_LAT)) u_rv (.clk(clk), .rst_n(rst_n), .v(raw_v), .vd(rv));
    wire          r_v = rv[SCALE_LAT];
    wire          r_last, r_oen;
    wire [PQ-1:0] r_gok;
    wire [AW-1:0] r_oa;
    wire [PQ*AW-1:0] r_oaq;
    wire [NL-1:0] r_mask;
    wire [NL*NW-1:0] r_rows;
    assign {r_last, r_oen, r_gok, r_oa, r_oaq, r_mask, r_rows} = rt;
    // -- the two result registers --------------------------------------------------------------------------------
    reg  [PQ-1:0]     o_we1;
    reg  [PQ*AW-1:0]  o_addr1;
    reg  [PQ*W-1:0]   o_mask1;
    reg  [PQ*W*32-1:0] o_data1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we1 <= 0; o_we <= 0; end
        else begin
            o_we1 <= {PQ{r_v && r_last && r_oen}} & r_gok;
            o_we <= o_we1;
        end
    end
    always @(posedge clk) begin
        o_addr1 <= r_oaq; o_mask1 <= r_mask; o_data1 <= res;
        o_mask <= o_mask1; o_data <= o_data1; o_addr <= o_addr1;
    end
    // -- argmax leaves and levels 1 .. LPT ------------------------------------------------------------------------
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    wire [(LPT+1)*CW*NL-1:0] alv;          // level al at [al*CW*NL +: CW*NL] (flat: Yosys 0.68 wire-array assert)
    genvar al;
    generate
        for (e = 0; e < NL; e = e + 1) begin : g_leaf
            reg [CW-1:0] c;
            always @(posedge clk) c <= {r_mask[e], okey(res[32*e +: 32]), r_rows[e*NW +: NW]};
            assign alv[CW*e +: CW] = c;
        end
        for (al = 1; al <= LPT; al = al + 1) begin : g_alvl
            for (e = 0; e < (NL >> al); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[(al-1)*CW*NL + CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[(al-1)*CW*NL + CW*(2*e+1) +: CW];
                //: key0 > key1, or equal keys and row0 < row1  <=>  {key0, ~row0} > {key1, ~row1}: one kept
                //: prefix carry (A > B <=> carry out of A + ~B), not Yosys's rippled > / == / <
                wire          gt, gt_c;
                wire [32+NW-1:0] gt_s;
                ot_qwen_w12_ksa #(.W(32 + NW)) u_gt (.a({x0[CW-2 -: 32], ~x0[NW-1:0]}), .b(~{x1[CW-2 -: 32], ~x1[NW-1:0]}),
                    .cin(1'b0), .s(gt_s), .cout(gt_c));
                assign gt = gt_c;
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || gt);
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[al*CW*NL + CW*e +: CW] = c;
            end
            assign alv[al*CW*NL + CW*NL-1 : al*CW*NL + CW*(NL >> al)] = 0;
        end
    endgenerate
    assign am = alv[LPT*CW*NL +: CW];
endmodule

// ot_qwen_me_rdelay_w12: q = d delayed D cycles, as ot_hdc_delay, built as a ring of D entries (one-hot write/read
// pointer, a copy per SL-bit slice) instead of a D-deep shift register: every entry is written once and read D
// cycles later through a one-hot select, so no flop drives a flop directly (no hold buffer per bit at FF) and a
// word toggles one entry per cycle instead of D.  D <= 1: ot_hdc_delay.
module ot_qwen_me_rdelay_w12 #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer SL = 64
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (D <= 1) begin : g_short
        ot_hdc_delay #(.W(W), .D(D)) u_d (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
    end else begin : g_ring
        localparam integer NS = (W + SL - 1) / SL;
        genvar s, i;
        for (s = 0; s < NS; s = s + 1) begin : g_s
            localparam integer LO = s * SL;
            localparam integer SW = ((W - LO) < SL) ? (W - LO) : SL;
            reg [D-1:0] ptr;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) ptr <= {{(D-1){1'b0}}, 1'b1};
                else ptr <= {ptr[D-2:0], ptr[D-1]};
            reg  [D*SW-1:0] mem;            // flat (entry-major): Yosys 0.68 asserts on wire arrays under chparam
            wire [(D+1)*SW-1:0] sel;
            assign sel[SW-1:0] = {SW{1'b0}};
            for (i = 0; i < D; i = i + 1) begin : g_e
                always @(posedge clk) if (ptr[i]) mem[i*SW +: SW] <= d[LO +: SW];
                assign sel[(i+1)*SW +: SW] = sel[i*SW +: SW] | (mem[i*SW +: SW] & {SW{ptr[i]}});
            end
            assign q[LO +: SW] = sel[D*SW +: SW];
        end
    end endgenerate
endmodule
