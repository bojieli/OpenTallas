`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection projection engine (HCP) of the re-specified DeepSeek-V4.1
// decode die: docs/ARCH_SPEC_V41.md section 6 item 7, gap-table row
// "hyper-connection projection" (2,048 FP32 MAC lanes).
//
// FUNCTION (tools/hdc_golden_v41.py Model.hc_mixes under R-ARITH "chunk8").
// Per position p, with flat = the BF16 4-copy residual (K = 4 x dim elements)
// and fn the [nout, K] binary32 projection:
//   ss      = csum(mul(flat, flat))                        (the norm's sum of squares)
//   r       = rsqrt(add(div(ss, nf), eps))                  (hdc_golden rsqrt: magic + 3 Newton steps)
//   mix[o]  = mul(csum(mul(fn[o, :], flat)), r)             (o = 0 .. nout-1)
// csum = chunks of 8 contiguous terms summed sequentially from +0, the chunk
// sums added by a pairwise tree padded with +0.  Every operation is one
// binary32 op of rtl/hdc/ot_hdc_fastfp.sv (3-stage add / multiply, RNE,
// gradual underflow, canonical +0) or the IEEE divider ot_hdc_fdiv.  With
// cmd_scale = 0 the engine returns the raw csum dot products (mix[o] =
// csum(...) exactly; the ss task and the scale are skipped).
//
// LANES.  8 groups x W lanes = 8W FP32 MAC lanes (W = 256: 2,048).  A lane is
// one multiplier feeding one adder whose sum re-enters exactly 3 cycles later
// (the add latency), so a lane interleaves 3 chunk accumulations ("slots") and
// retires one multiply-add per cycle.  A TASK is one aligned run of W chunks
// (8W terms) of one accumulation (position p, row o, run r): the W lanes of a
// group each own one chunk of the run.  One task issues per cycle.  Task n
// (issued in cycle n) belongs to group (n div 3) mod 8, slot n mod 3, and its
// term k (k = 0 .. 7) is multiplied in cycle n + 3k (plus a fixed offset): so
// every lane is busy every cycle, the 8 groups are always at 8 DIFFERENT terms
// k, and the chunk sums of exactly one task complete per cycle.
//
// MEMORIES (outside the engine; fixed read latency ML cycles from the
// registered address to the data at the input port, no handshake).  Both are
// banked by term k, so the 8 groups never conflict:
//   weight bank k, word wbase + o*R + r, lane l:  fn[o][8*(r*W + l) + k]      (binary32)
//   x      bank k, word xbase + p*R + r, lane l:  flat_p[8*(r*W + l) + k]     (BF16)
// with R = ceil(nchunk / W) runs, nchunk = K/8, words past the vector ignored
// (lanes l >= nchunk - r*W of the last run are masked to +0 operands).  Bank k
// in cycle c serves the task issued in cycle c - 3k; its data is rotated to
// that task's group (a one-hot AND-OR by the group field the task carries).
//
// REDUCTION, exactly the csum tree.  The W chunk sums of a task enter a
// pipelined pairwise tree of log2(W) adder levels: that is the csum subtree of
// an aligned run of W chunks.  The run sums of one accumulation (r = 0 .. R-1)
// enter the TAIL: TL levels, level l holding one pending left sibling.  At
// level l an event with bit l of r set adds the stored sibling and moves up;
// with bit l clear it is stored and stops -- unless it is the accumulation's
// last run, whose right sibling is all padding, so it moves up unchanged
// (added to +0).  Every addition is the tree's own pair, so the result is
// csum's padded tree bit for bit (padding past pow2(nchunk) only adds +0).
// Requires R <= 2^TL (fault otherwise) and K a multiple of 8.
//
// ORDER.  Positions p = 0 .. npos-1; per position the ss task run (if
// cmd_scale) then rows o = 0 .. nout-1, each its R runs.  Raw sums enter a
// DF-entry FIFO; issue reserves an entry per accumulation (credit), so the
// engine never drops a result.  The scalar unit turns ss into r (one fdiv,
// one add, one multiply, sequenced: ~90 cycles per position, while the rows
// of that position accumulate), and each raw row sum leaves through one
// multiplier as mix = raw * r (raw * 1.0 = raw when cmd_scale = 0).
//
// PROTOCOL.  cmd_valid/cmd_ready: one command at a time (cmd_ready rises again
// after the command's last result is accepted).  o_valid/o_ready: results in
// (p, o) order, o_last on the command's final result.  Every output is a flop;
// every input is registered before use.  fault (sticky per command): a
// nonfinite operand or overflow anywhere, a divide fault, or R > 2^TL.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_hcp #(
    parameter integer W    = 8,         // lanes per group (power of two >= 2); lanes = 8W (spec: W = 256)
    parameter integer TL   = 9,         // tail levels: runs per accumulation R <= 2^TL (spec: 4)
    parameter integer PMAX = 8,         // positions per command (power of two)
    parameter integer OMAX = 32,        // rows per position (power of two)
    parameter integer AW   = 16,        // bank word address width
    parameter integer CW   = 16,        // chunk-count width (nchunk = K/8)
    parameter integer ML   = 2,         // memory read latency
    parameter integer DF   = 32,        // raw-result FIFO depth (power of two)
    // el1011-hcvm-hc SYSTOLIC lanes (opt-in, default off; cycles change): SYS = 1 builds no lane groups and no bank
    // rotation.  The 8W lanes live outside in 8 bank stages (ot_hdc_v41x_hcp_stage, one per bank, chained): the task
    // descriptor leaves on sd_* (tap 0), stage k multiplies term k from its OWN bank and adds it to the partial chunk
    // sum of stage k - 1 (stage 0 adds to +0), so csum's chunk order ((0 + t0) + t1) .. + t7 is kept op for op; stage
    // 7's W chunk sums come back on sys_sum SYS_LAT cycles after tap 0 (the tree leaves at tap SYS_LAT + 1).
    parameter integer SYS  = 0,
    parameter integer SYS_LAT = 0,
    parameter integer PW   = (PMAX > 1) ? $clog2(PMAX) : 1,
    parameter integer OXW  = (OMAX > 1) ? $clog2(OMAX) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    // command
    input  wire              cmd_valid,
    output reg               cmd_ready,
    input  wire [PW:0]       cmd_npos,          // 1 .. PMAX
    input  wire [OXW:0]      cmd_nout,          // 1 .. OMAX
    input  wire [CW-1:0]     cmd_nchunk,        // K / 8, >= 1
    input  wire              cmd_scale,
    input  wire [31:0]       cmd_nf,            // binary32 of K (the mean's divisor)
    input  wire [31:0]       cmd_eps,
    input  wire [AW-1:0]     cmd_wbase,
    input  wire [AW-1:0]     cmd_xbase,
    // weight banks (binary32) and x banks (BF16), bank k at [k*...]
    output reg  [7:0]        w_re,
    output reg  [8*AW-1:0]   w_addr,
    input  wire [8*W*32-1:0] w_data,
    output reg  [7:0]        x_re,
    output reg  [8*AW-1:0]   x_addr,
    input  wire [8*W*16-1:0] x_data,
    // results
    output reg               o_valid,
    input  wire              o_ready,
    output reg  [PW-1:0]     o_pos,
    output reg  [OXW-1:0]    o_idx,
    output reg  [31:0]       o_data,
    output reg               o_last,
    output reg               fault,
    output reg               idle,
    // SYS = 1: the descriptor to stage 0, the chunk sums and lane faults back from stage 7
    output wire              sd_v,
    output wire              sd_ss,
    output wire [$clog2(W):0] sd_nv,
    output wire [AW-1:0]     sd_wa,
    output wire [AW-1:0]     sd_xa,
    input  wire [W*32-1:0]   sys_sum,
    input  wire              sys_fault
);
    localparam integer LW  = $clog2(W);
    localparam integer NVW = LW + 1;
    localparam integer DFW = $clog2(DF);
    // descriptor fields
    localparam integer F_V   = 0;
    localparam integer F_SS  = 1;
    localparam integer F_LR  = 2;                 // last run
    localparam integer F_GRP = 3;                 // 3 bits
    localparam integer F_NV  = 6;                 // NVW bits
    localparam integer F_WA  = F_NV + NVW;
    localparam integer F_XA  = F_WA + AW;
    localparam integer F_POS = F_XA + AW;
    localparam integer F_IDX = F_POS + PW;
    localparam integer F_R   = F_IDX + OXW;       // TL low bits of the run index
    localparam integer F_LO  = F_R + TL;          // last output of the command
    localparam integer DW    = F_LO + 1;
    // pipeline taps (descriptor delay-line index of the task a stage holds)
    localparam integer T_OP   = 21 + ML + 3;                 // group operands of term 7
    localparam integer T_LEAF = SYS ? SYS_LAT + 1 : 31 + ML; // tree leaves
    localparam integer T_TAIL = T_LEAF + 3 * LW;             // tree output = tail level 0 input
    localparam integer NDL    = T_TAIL + 3 * TL + 1;

    genvar gk, gg, gl, gv;
    integer i;

    // ------------------------------------------------------------------ command / issue
    reg              busy, active;
    reg [PW:0]       npos_r;
    reg [OXW:0]      nout_r;
    reg [CW-1:0]     nrun_r, nlast_r;              // runs per accumulation; lanes of the last run
    reg              scale_r;
    reg [31:0]       nf_r, eps_r;
    reg [PW-1:0]     p;
    reg [OXW-1:0]    o;
    reg              ssph;
    reg [CW-1:0]     r;
    reg [AW-1:0]     wbase_r, wcur, xpos;
    reg [4:0]        ph24;                          // free-running cycle mod 24
    reg [DFW:0]      acc_cnt;                       // accumulations reserved, not yet popped
    wire             pop_raw;
    wire [CW-1:0]    nrun_c = (cmd_nchunk + W - 1) >> LW;
    wire             first_r = (r == 0);
    wire             last_r = (r == nrun_r - 1'b1);
    wire             credit = (acc_cnt < DF);
    wire             iss = active && (!first_r || credit);
    wire             last_o = ssph ? 1'b0 : ({1'b0, o} == nout_r - 1'b1);
    wire             last_p = ({1'b0, p} == npos_r - 1'b1);
    reg  [DW-1:0]    d0;
    wire             tl_over_c = (nrun_c > (1 << TL));
    localparam [NVW-1:0] WNV = W;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; active <= 1'b0; cmd_ready <= 1'b0; ph24 <= 5'd0; acc_cnt <= 0;
        end else begin
            ph24 <= (ph24 == 5'd23) ? 5'd0 : ph24 + 5'd1;
            cmd_ready <= !busy && !(cmd_valid && cmd_ready);
            acc_cnt <= acc_cnt + (iss && first_r) - pop_raw;
            if (cmd_valid && cmd_ready) begin
                busy <= 1'b1; active <= 1'b1;
            end else if (iss && last_r && last_o && last_p) begin
                active <= 1'b0;
            end
            if (o_valid && o_ready && o_last) busy <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (cmd_valid && cmd_ready) begin
            npos_r <= cmd_npos; nout_r <= cmd_nout; scale_r <= cmd_scale;
            nrun_r <= nrun_c; nlast_r <= ((cmd_nchunk - 1'b1) & (W - 1)) + 1'b1;
            nf_r <= cmd_nf; eps_r <= cmd_eps; wbase_r <= cmd_wbase;
            p <= 0; o <= 0; r <= 0; ssph <= cmd_scale; wcur <= cmd_wbase; xpos <= cmd_xbase;
        end else if (iss) begin
            if (!last_r) r <= r + 1'b1;
            else begin
                r <= 0;
                if (ssph) ssph <= 1'b0;
                else if (!last_o) o <= o + 1'b1;
                else begin
                    o <= 0; p <= p + 1'b1; ssph <= scale_r; wcur <= wbase_r; xpos <= xpos + nrun_r;
                end
            end
            if (!ssph && !(last_r && last_o)) wcur <= wcur + 1'b1;
        end
        // the task descriptor entering the delay line (a bubble still carries its group)
        d0 <= {DW{1'b0}};
        d0[F_V] <= iss;
        d0[F_SS] <= ssph;
        d0[F_LR] <= last_r;
        d0[F_GRP +: 3] <= ph24 / 3;
        d0[F_NV +: NVW] <= last_r ? nlast_r[NVW-1:0] : WNV;
        d0[F_WA +: AW] <= wcur;
        d0[F_XA +: AW] <= xpos + r;
        d0[F_POS +: PW] <= p;
        d0[F_IDX +: OXW] <= o;
        d0[F_R +: TL] <= r[TL-1:0];
        d0[F_LO] <= !ssph && last_o && last_p;
    end
    // delay line: dl[i] = d0 delayed i cycles (dl[0] = d0); the valid bit is reset
    reg  [NDL-1:0]        dlv;                      // valid bits (reset)
    reg  [(DW-1)*NDL-1:0] dld;                      // the other fields (no reset)
    wire [DW*(NDL+1)-1:0] dl;
    assign dl[DW-1:0] = d0;
    generate for (gv = 0; gv < NDL; gv = gv + 1) begin : g_dl
        assign dl[DW*(gv+1) +: DW] = {dld[(DW-1)*gv +: DW-1], dlv[gv]};
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) dlv <= {NDL{1'b0}};
        else for (i = 0; i < NDL; i = i + 1) dlv[i] <= dl[DW*i + F_V];
    end
    always @(posedge clk)
        for (i = 0; i < NDL; i = i + 1) dld[(DW-1)*i +: DW-1] <= dl[DW*i + 1 +: DW-1];

    // ------------------------------------------------------------------ bank addresses (term k at tap 3k)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w_re <= 8'd0; x_re <= 8'd0; end
        else for (i = 0; i < 8; i = i + 1) begin
            w_re[i] <= dl[DW*(3*i) + F_V] && !dl[DW*(3*i) + F_SS];
            x_re[i] <= dl[DW*(3*i) + F_V];
        end
    end
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1) begin
            w_addr[AW*i +: AW] <= dl[DW*(3*i) + F_WA +: AW];
            x_addr[AW*i +: AW] <= dl[DW*(3*i) + F_XA +: AW];
        end

    reg [W*32-1:0] leaf;
    reg            leaf_v;
    wire           lane_fault_any;
    assign sd_v = d0[F_V]; assign sd_ss = d0[F_SS]; assign sd_nv = d0[F_NV +: NVW]; assign sd_wa = d0[F_WA +: AW];
    assign sd_xa = d0[F_XA +: AW];
    generate if (SYS == 0) begin : g_flat
    // ------------------------------------------------------------------ input registers
    reg [8*W*32-1:0] w_in;
    reg [8*W*16-1:0] x_in;
    always @(posedge clk) begin
        w_in <= w_data;
        x_in <= x_data;
    end

    // ------------------------------------------------------------------ rotation to groups, masking
    // bank k's input register holds the task at tap 3k + 2 + ML
    wire [63:0] sel;                                  // sel[8g + k]
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_sel
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_k
            //: qualified by the task's valid bit: a bubble's group field may be stale (the delay line's data
            //: bits carry no reset), and only valid tasks are guaranteed one per group
            assign sel[8*gg + gk] = dl[DW*(3*gk + 2 + ML) + F_V] && (dl[DW*(3*gk + 2 + ML) + F_GRP +: 3] == gg);
        end
    end

    reg  [7:0]        gfirst, glast;                // first: a = +0 (term 0, or no task)
    reg  [7:0]        gov;                          // the group holds a task's operands
    wire [8*W-1:0]    lane_fault;
    wire [8*W*32-1:0] gsum;
    reg  [7:0]        lastv [0:6];                  // group's last-term flag, delayed 0..6 from gw
    reg  [7:0]        fst   [0:3];                  // group's first flag, delayed 0..3
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_grp
        reg          ov, oss;
        reg [NVW-1:0] onv;
        reg [W*32-1:0] ow;
        reg [W*16-1:0] ox;
        integer k2;
        always @(*) begin
            ov = 1'b0; oss = 1'b0; onv = {NVW{1'b0}}; ow = {(W*32){1'b0}}; ox = {(W*16){1'b0}};
            for (k2 = 0; k2 < 8; k2 = k2 + 1) begin
                ov  = ov  | sel[8*gg + k2];
                oss = oss | (sel[8*gg + k2] & dl[DW*(3*k2 + 2 + ML) + F_SS]);
                onv = onv | ({NVW{sel[8*gg + k2]}} & dl[DW*(3*k2 + 2 + ML) + F_NV +: NVW]);
                ow  = ow  | ({(W*32){sel[8*gg + k2]}} & w_in[W*32*k2 +: W*32]);
                ox  = ox  | ({(W*16){sel[8*gg + k2]}} & x_in[W*16*k2 +: W*16]);
            end
        end
        for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
            wire        lv = ov && (gl < onv);
            wire [31:0] xw = {ox[16*gl +: 16], 16'h0000};
            reg  [31:0] gx, gw;                    // the lane's operands (lane-local registers)
            always @(posedge clk) begin
                gx <= lv ? xw : 32'd0;
                gw <= lv ? (oss ? xw : ow[32*gl +: 32]) : 32'd0;
            end
            // the lane: product, then the 3-slot interleaved accumulation
            wire [31:0] prod, sum;
            wire [1:0]  e0, e1;
            wire        v0, v1;
            ot_hdc_fp32_mul_fast u_mul (.clk(clk), .rst_n(rst_n), .valid_in(gov[gg]),
                                        .a(gw), .b(gx),
                                        .y(prod), .err(e0), .valid_out(v0));
            ot_hdc_fp32_add_fast u_add (.clk(clk), .rst_n(rst_n), .valid_in(v0),
                                        .a(fst[2][gg] ? 32'd0 : sum), .b(prod),
                                        .y(sum), .err(e1), .valid_out(v1));
            assign gsum[32*(W*gg + gl) +: 32] = sum;
            //: errors count only on a task's terms (the valid chains ride the units' own pipes)
            assign lane_fault[W*gg + gl] = (v0 && (|e0)) || (v1 && (|e1));
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) gov[gg] <= 1'b0; else gov[gg] <= ov;
        always @(posedge clk) begin
            gfirst[gg] <= sel[8*gg + 0] || !ov;
            glast[gg]  <= sel[8*gg + 7];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 7; i = i + 1) lastv[i] <= 8'd0;
        end else begin
            lastv[0] <= glast;
            for (i = 1; i < 7; i = i + 1) lastv[i] <= lastv[i-1];
        end
    end
    always @(posedge clk) begin
        fst[0] <= gfirst;
        for (i = 1; i < 4; i = i + 1) fst[i] <= fst[i-1];
    end
    //: fst[2] is the first flag of the term whose product the adder takes now;
    //: lastv[5] marks the group whose adder output is a finished chunk sum.
    wire [7:0] done_g = lastv[5];

    // ------------------------------------------------------------------ tree over the W chunk sums
    integer g3;
    always @(posedge clk) begin
        leaf <= {(W*32){1'b0}};
        for (g3 = 0; g3 < 8; g3 = g3 + 1)
            if (done_g[g3]) leaf <= gsum[W*32*g3 +: W*32];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= |done_g;
    end
    assign lane_fault_any = |lane_fault;
    end else begin : g_sys
    // the stage chain is outside: stage 7's chunk sums of the task at tap T_LEAF - 1 arrive on sys_sum now
    always @(posedge clk) leaf <= dl[DW*(T_LEAF-1) + F_V] ? sys_sum : {(W*32){1'b0}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= dl[DW*(T_LEAF-1) + F_V];
    assign lane_fault_any = sys_fault;
    end endgenerate
    wire [31:0] root;
    wire        tree_fault;
    wire        tree_vo;
    ot_hdc_v41x_addtree #(.N(W)) u_tree (.clk(clk), .rst_n(rst_n), .v(leaf_v), .x(leaf), .y(root), .vo(tree_vo),
                                         .fault(tree_fault));
    wire [LW*3:0] tvv;
    ot_hdc_v41x_vline #(.D(3*LW)) u_tvv (.clk(clk), .rst_n(rst_n), .v(leaf_v), .vd(tvv));

    // ------------------------------------------------------------------ tail: pairwise tree over runs
    wire [32*(TL+1)-1:0] ev_val;
    wire [TL:0]          ev_v;
    wire [TL-1:0]        tail_fault;
    assign ev_val[31:0] = root;
    assign ev_v[0] = tvv[3*LW];
    generate for (gv = 0; gv < TL; gv = gv + 1) begin : g_tail
        localparam integer TAP = T_TAIL + 3 * gv;
        wire bitl  = dl[DW*TAP + F_R + gv];
        wire lastr = dl[DW*TAP + F_LR];
        wire go    = ev_v[gv] && (bitl || lastr);
        reg [31:0] slot;
        always @(posedge clk) if (ev_v[gv] && !bitl && !lastr) slot <= ev_val[32*gv +: 32];
        wire [1:0] e;
        ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(go),
                                  .a(bitl ? slot : 32'd0), .b(ev_val[32*gv +: 32]),
                                  .y(ev_val[32*(gv+1) +: 32]), .err(e), .valid_out(ev_v[gv+1]));
        assign tail_fault[gv] = ev_v[gv+1] && (|e);
    end endgenerate
    localparam integer T_RAW = T_TAIL + 3 * TL;
    wire raw_v   = ev_v[TL] && dl[DW*T_RAW + F_LR];
    wire raw_bad = ev_v[TL] && !dl[DW*T_RAW + F_LR];      // R > 2^TL

    // ------------------------------------------------------------------ raw-result FIFO
    localparam integer RQW = 1 + 1 + PW + OXW + 32;       // {last out, ss, pos, idx, value}
    reg  [RQW-1:0] rq [0:DF-1];
    reg  [DFW:0]   rq_wp, rq_rp;
    wire           rq_ne = (rq_wp != rq_rp);
    wire [RQW-1:0] rq_h = rq[rq_rp[DFW-1:0]];
    reg  [RQW-1:0] raw_w;
    reg            raw_wv;
    always @(posedge clk) begin
        raw_w <= {dl[DW*(T_RAW) + F_LO], dl[DW*(T_RAW) + F_SS], dl[DW*(T_RAW) + F_POS +: PW],
                  dl[DW*(T_RAW) + F_IDX +: OXW], ev_val[32*TL +: 32]};
        if (raw_wv) rq[rq_wp[DFW-1:0]] <= raw_w;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rq_wp <= 0; rq_rp <= 0; raw_wv <= 1'b0; end
        else begin
            raw_wv <= raw_v;
            if (raw_wv) rq_wp <= rq_wp + 1'b1;
            if (pop_raw) rq_rp <= rq_rp + 1'b1;
        end
    end
    wire          h_lo  = rq_h[RQW-1];
    wire          h_ss  = rq_h[RQW-2];
    wire [PW-1:0] h_pos = rq_h[32 + OXW +: PW];
    wire [OXW-1:0] h_idx = rq_h[32 +: OXW];
    wire [31:0]   h_val = rq_h[31:0];

    // ------------------------------------------------------------------ scalar r unit
    reg  [31:0]     rv [0:PMAX-1];
    reg  [PMAX-1:0] r_ok;
    reg  [3:0]      st;
    reg             pend;
    reg  [1:0]      it;
    reg  [PW-1:0]   rs_pos;
    reg  [31:0]     rs_q, rs_h, rs_y, rs_a;
    localparam [3:0] S_IDLE = 4'd0, S_DIV = 4'd1, S_EPS = 4'd2, S_HALF = 4'd3, S_YY = 4'd4, S_HY = 4'd5,
                     S_SUB = 4'd6, S_MY = 4'd7;
    wire rs_take = rq_ne && h_ss && (st == S_IDLE);
    // units
    reg         dv, av, mv;
    reg  [31:0] da, db, aa, ab, ma, mb;
    wire [31:0] dy, ay, my;
    wire        dvo, avo, mvo, dfl;
    wire [1:0]  aerr, merr;
    ot_hdc_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(dv), .a(da), .b(db), .y(dy), .vo(dvo), .fault(dfl));
    ot_hdc_fp32_add_fast u_sa (.clk(clk), .rst_n(rst_n), .valid_in(av), .a(aa), .b(ab), .y(ay), .err(aerr),
                               .valid_out(avo));
    ot_hdc_fp32_mul_fast u_sm (.clk(clk), .rst_n(rst_n), .valid_in(mv), .a(ma), .b(mb), .y(my), .err(merr),
                               .valid_out(mvo));
    wire rs_fault = (dvo && dfl) || (avo && (|aerr)) || (mvo && (|merr));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pend <= 1'b0; dv <= 1'b0; av <= 1'b0; mv <= 1'b0; r_ok <= {PMAX{1'b0}};
        end else begin
            dv <= 1'b0; av <= 1'b0; mv <= 1'b0;
            if (cmd_valid && cmd_ready) r_ok <= {PMAX{1'b0}};
            case (st)
                S_IDLE: if (rs_take) begin st <= S_DIV; pend <= 1'b0; end
                S_DIV:  if (!pend) begin dv <= 1'b1; pend <= 1'b1; end
                        else if (dvo) begin pend <= 1'b0; st <= S_EPS; end
                S_EPS:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_HALF; end
                S_HALF: if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_YY; end
                S_YY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_HY; end
                S_HY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_SUB; end
                S_SUB:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_MY; end
                S_MY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin
                            pend <= 1'b0;
                            if (it == 2'd2) begin st <= S_IDLE; r_ok[rs_pos] <= 1'b1; end
                            else st <= S_YY;
                        end
                default: st <= S_IDLE;
            endcase
        end
    end
    always @(posedge clk) begin
        if (st == S_IDLE && rs_take) begin
            rs_pos <= h_pos; da <= h_val; db <= nf_r; it <= 2'd0;
        end
        if (st == S_DIV && pend && dvo) begin aa <= dy; ab <= eps_r; end
        if (st == S_EPS && pend && avo) begin
            ma <= ay; mb <= 32'h3F000000;                         // half = v * 0.5
            rs_y <= 32'h5F3759DF - {1'b0, ay[31:1]};              // y0 from v's bits
        end
        if (st == S_HALF && pend && mvo) begin rs_h <= my; ma <= rs_y; mb <= rs_y; end
        if (st == S_YY && pend && mvo) begin ma <= rs_h; mb <= my; end
        if (st == S_HY && pend && mvo) begin aa <= 32'h3FC00000; ab <= {~my[31], my[30:0]}; end
        if (st == S_SUB && pend && avo) begin ma <= rs_y; mb <= ay; end
        if (st == S_MY && pend && mvo) begin
            rs_y <= my; ma <= my; mb <= my; it <= it + 1'b1;
            if (it == 2'd2) rv[rs_pos] <= my;
        end
    end

    // ------------------------------------------------------------------ output: raw * r
    localparam integer OQ = 8;
    localparam integer OTW = 1 + PW + OXW;
    reg  [3:0]  oinf;                                 // products in flight
    reg  [3:0]  ocnt;
    wire        o_room = ({1'b0, oinf} + {1'b0, ocnt} + {4'd0, o_valid}) < OQ;
    wire        h_ok = !scale_r || r_ok[h_pos];
    wire        take_out = rq_ne && !h_ss && h_ok && o_room;
    assign pop_raw = rs_take || take_out;
    reg         ov_in;
    reg  [31:0] oa, ob;
    reg  [OTW-1:0] otag_in;
    wire [31:0] oy;
    wire [1:0]  oerr;
    wire        ovo;
    wire [OTW-1:0] otag;
    ot_hdc_fp32_mul_fast u_om (.clk(clk), .rst_n(rst_n), .valid_in(ov_in), .a(oa), .b(ob), .y(oy), .err(oerr),
                               .valid_out(ovo));
    ot_hdc_delay #(.W(OTW), .D(3)) u_otag (.clk(clk), .rst_n(rst_n), .d(otag_in), .q(otag));
    reg  [OTW+31:0] oq [0:OQ-1];
    reg  [3:0]      oq_wp, oq_rp;
    wire            oq_ne = (oq_wp != oq_rp);
    wire            o_load = oq_ne && (!o_valid || o_ready);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov_in <= 1'b0; oinf <= 4'd0; ocnt <= 4'd0; oq_wp <= 4'd0; oq_rp <= 4'd0; o_valid <= 1'b0;
        end else begin
            ov_in <= take_out;
            oinf <= oinf + {3'd0, take_out} - {3'd0, ovo};
            ocnt <= ocnt + {3'd0, ovo} - {3'd0, o_load};
            if (ovo) oq_wp <= (oq_wp == OQ - 1) ? 4'd0 : oq_wp + 4'd1;
            if (o_load) oq_rp <= (oq_rp == OQ - 1) ? 4'd0 : oq_rp + 4'd1;
            if (o_load) o_valid <= 1'b1;
            else if (o_ready) o_valid <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (take_out) begin
            oa <= h_val; ob <= scale_r ? rv[h_pos] : 32'h3F800000; otag_in <= {h_lo, h_pos, h_idx};
        end
        if (ovo) oq[oq_wp] <= {otag, oy};
        if (o_load) {o_last, o_pos, o_idx, o_data} <= oq[oq_rp];
    end

    // ------------------------------------------------------------------ fault, idle
    reg lf_r, tf_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; idle <= 1'b1; lf_r <= 1'b0; tf_r <= 1'b0; end
        else begin
            lf_r <= lane_fault_any;
            tf_r <= tree_fault || (|tail_fault) || raw_bad || rs_fault || (ovo && (|oerr));
            if (cmd_valid && cmd_ready) fault <= tl_over_c;
            else if (lf_r || tf_r) fault <= 1'b1;
            idle <= !busy;
        end
    end
endmodule

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_v41x_vline #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    generate if (D == 0) begin : g0
        assign vd = v;
    end else begin : gd
        reg [D-1:0] line;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) line <= {D{1'b0}};
            else line <= (line << 1) | {{(D-1){1'b0}}, v};
        end
        assign vd = {line, v};
    end endgenerate
endmodule

// Pairwise tree ((x0 + x1) + (x2 + x3)) + ... over N binary32 inputs (N a power
// of two), one ot_hdc_fp32_add_fast per node, 3 cycles per level, II 1.  v
// travels with the operands (vo = v delayed 3 log2 N); a node's error counts
// only on a valid pass, and fault is registered one cycle after it.
module ot_hdc_v41x_addtree #(parameter integer N = 2) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [N*32-1:0] x,
    output wire [31:0]   y,
    output wire          vo,
    output reg           fault
);
    wire [1:0] e;
    generate if (N == 1) begin : g_one
        assign y = x;
        assign vo = v;
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= 1'b0;
    end else if (N == 2) begin : g_two
        ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(x[31:0]), .b(x[63:32]), .y(y),
                                  .err(e), .valid_out(vo));
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= vo && (|e);
    end else begin : g_rec
        wire [31:0] yl, yr;
        wire        fl, fr, vl, vr;
        ot_hdc_v41x_addtree #(.N(N / 2)) u_l (.clk(clk), .rst_n(rst_n), .v(v), .x(x[0 +: N*16]), .y(yl), .vo(vl),
                                               .fault(fl));
        ot_hdc_v41x_addtree #(.N(N / 2)) u_r (.clk(clk), .rst_n(rst_n), .v(v), .x(x[N*16 +: N*16]), .y(yr), .vo(vr),
                                               .fault(fr));
        ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(vl), .a(yl), .b(yr), .y(y), .err(e),
                                  .valid_out(vo));
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= (vo && (|e)) || fl || fr;
    end endgenerate
endmodule

// el1011-hcvm-hc: one SYSTOLIC bank stage of the HCP (SYS = 1).  Stage k holds W FP32 MAC lanes beside bank k's
// weight and x memories.  The task descriptor enters through pin flops (local cycle 0 = the flat engine's tap 3k),
// addresses its own bank (registered, local 1), takes the data ML cycles later (local 1 + ML) into input registers,
// forms the masked lane operands (local 3 + ML), multiplies (3 stages) and adds the product to the partial chunk sum
// that stage k - 1 hands over (pin flop, local 6 + ML; stage 0 adds to +0 through the `first` strap): the term order of
// csum is the flat engine's ((0 + t0) + t1) .. + t7, one binary32 op each, so the chunk sums are bit-identical.  The
// descriptor leaves after 3 registers (the next stage's pin flop makes the hop 4 cycles), the partial sums leave from
// the adder's output register, the lane-fault flag from a register.  No datapath register carries a reset; the
// per-lane operand enables are replicated kept registers (one per lane, no select net over all 32 lanes).
module ot_hdc_v41x_hcp_stage #(
    parameter integer W   = 8,
    parameter integer AW  = 16,
    parameter integer ML  = 2,
    parameter integer NVW = $clog2(W) + 1,
    // pipelined IEEE units (1.2 GHz: 8-stage multiply, 7-stage add, ot_hdc_fp32_*_lat, bit for bit the fast units);
    // the stage hop is LA + 1 cycles (adder output register -> next stage's pin flop)
    parameter integer LM  = 8,
    parameter integer LA  = 7,
    // el1011-hbm-hcvm/hc round 3 (hc_tile-sys-048ca3d9e-b: rst relay -> u_add.y RESETN -310 ps, add y -> sum_out
    // pin -162 ps wire): SOR 1 registers sum_out at the seam (hop LA + 1 + SOR); LRST 1 gives every lane its own kept
    // reset flop (no rst_n net over 32 lanes' fp pipes); ADRST 0 builds the adders with data-bit reset off (valid only)
    // and the multipliers too (.DRST(ADRST), HBM-W128 2026-10-25: data FFs unreset, valid bits only)
    parameter integer SOR = 0,
    parameter integer LRST = 0,
    parameter integer ADRST = 1,
    // el1011-hbm-hcvm/hc round 4 (hc_tile-sys-faa39cbe9-b EARLY_FAIL_HOLD: ONE clock root over 56,560 sinks, avg sink wire
    // 538 um, FF insertion 415..682 ps -> hold stuck at -165 ps inside u_mul pipes; textbook REFUSE > 15k sinks/root):
    // LG 8 = the lanes live in W/8 HARD lane-group leaves (ot_hdc_v41x_hcp_lanes, own clock tree, ~13k sinks each);
    // the leaf's pin flops ARE the old input registers (w_in, x_in, sum_q, lv_r/ss_r, gov, fst_q) and its outputs are
    // the adder/seam registers + the registered group fault, so every latency is unchanged (SYS_LAT unchanged).
    parameter integer LG = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              first,
    input  wire              d_v,
    input  wire              d_ss,
    input  wire [NVW-1:0]    d_nv,
    input  wire [AW-1:0]     d_wa,
    input  wire [AW-1:0]     d_xa,
    output wire              o_v,
    output wire              o_ss,
    output wire [NVW-1:0]    o_nv,
    output wire [AW-1:0]     o_wa,
    output wire [AW-1:0]     o_xa,
    input  wire [W*32-1:0]   sum_in,
    output wire [W*32-1:0]   sum_out,
    input  wire              f_in,
    output reg               f_out,
    output reg               w_re,
    output reg  [AW-1:0]     w_addr,
    input  wire [W*32-1:0]   w_data,
    output reg               x_re,
    output reg  [AW-1:0]     x_addr,
    input  wire [W*16-1:0]   x_data
);
    localparam integer NC = (1 + ML > LA + SOR) ? 1 + ML : LA + SOR;   // descriptor delay taps kept locally
    localparam integer DW = 2 + NVW + 2 * AW;
    reg  [NC:0]      cv;                                         // valid, taps 0..NC (reset)
    reg  [DW-2:0]    cd [0:NC];                                  // other fields (no reset)
    reg              fin_q;
    wire             lf_any;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cv <= '0; w_re <= 1'b0; x_re <= 1'b0; fin_q <= 1'b0; f_out <= 1'b0; end
        else begin
            cv <= {cv[NC-1:0], d_v};
            w_re <= cv[0] && !cd[0][DW-2];
            x_re <= cv[0];
            fin_q <= f_in;
            f_out <= fin_q || lf_any;
        end
    end
    always @(posedge clk) begin
        cd[0] <= {d_ss, d_nv, d_wa, d_xa};
        for (integer j = 1; j <= NC; j = j + 1) cd[j] <= cd[j-1];
        w_addr <= cd[0][2*AW-1:AW];
        x_addr <= cd[0][AW-1:0];
    end
    assign o_v = cv[LA + SOR]; assign {o_ss, o_nv, o_wa, o_xa} = cd[LA + SOR]; // tap j = local j: out at local LA + SOR
    generate if (LG == 0) begin : g_flat
    reg fst_q, gov, lf_q;
    assign lf_any = lf_q;
    always @(posedge clk) fst_q <= first;
    // input registers (local 2 + ML) and the per-lane enables of that task (computed a cycle early, replicated)
    reg [W*32-1:0] w_in; reg [W*16-1:0] x_in;
    (* keep = "true" *) reg [W-1:0] lv_r, ss_r;
    reg ov_r;
    wire [NVW-1:0] nv_e = cd[1 + ML][DW-3 -: NVW];               // the task at local 1 + ML
    always @(posedge clk) begin
        w_in <= w_data; x_in <= x_data;
        for (integer l = 0; l < W; l = l + 1) begin
            lv_r[l] <= cv[1 + ML] && (l < nv_e);
            ss_r[l] <= cd[1 + ML][DW-2];
        end
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) ov_r <= 1'b0; else ov_r <= cv[1 + ML];
    reg [W*32-1:0] sum_q;
    always @(posedge clk) sum_q <= sum_in;
    wire [W-1:0] lfl;
    wire [W*32-1:0] y_l;
    if (SOR != 0) begin : g_sor
        reg [W*32-1:0] so_q; always @(posedge clk) so_q <= y_l; assign sum_out = so_q;
    end else begin : g_nsor
        assign sum_out = y_l;
    end
    for (genvar gl = 0; gl < W; gl = gl + 1) begin : g_lane
        wire lrn;
        if (LRST != 0) begin : g_lr
            (* keep = "true" *) reg r; always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= 1'b1;
            assign lrn = r;
        end else begin : g_nlr
            assign lrn = rst_n;
        end
        wire [31:0] xw = {x_in[16*gl +: 16], 16'h0000};
        reg  [31:0] gx, gw;
        always @(posedge clk) begin
            gx <= lv_r[gl] ? xw : 32'd0;
            gw <= lv_r[gl] ? (ss_r[gl] ? xw : w_in[32*gl +: 32]) : 32'd0;
        end
        wire [31:0] prod; wire [1:0] e0, e1; wire v0, v1;
        ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(ADRST)) u_mul (.clk(clk), .rst_n(lrn), .valid_in(gov), .a(gw), .b(gx), .y(prod),
                                    .err(e0), .valid_out(v0));
        ot_hdc_fp32_add_lat #(.LAT(LA), .DRST(ADRST)) u_add (.clk(clk), .rst_n(lrn), .valid_in(v0), .a(fst_q ? 32'd0 : sum_q[32*gl +: 32]),
                                    .b(prod), .y(y_l[32*gl +: 32]), .err(e1), .valid_out(v1));
        assign lfl[gl] = (v0 && (|e0)) || (v1 && (|e1));
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gov <= 1'b0; lf_q <= 1'b0; end else begin gov <= ov_r; lf_q <= |lfl; end
    end else begin : g_lg
        // enables one cycle earlier (task at local ML) in the shell; the leaf's pin flops hold them at local 2 + ML
        localparam integer NG = W / LG;
        (* keep = "true" *) reg [W-1:0] lvs, sss;
        reg ov_r;
        wire [NVW-1:0] nv_p = cd[ML][DW-3 -: NVW];
        always @(posedge clk) for (integer l = 0; l < W; l = l + 1) begin
            lvs[l] <= cv[ML] && (l < nv_p);
            sss[l] <= cd[ML][DW-2];
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) ov_r <= 1'b0; else ov_r <= cv[1 + ML];
        wire [NG-1:0] lfg;
        for (genvar gg = 0; gg < NG; gg = gg + 1) begin : g_grp
            // hard child: instantiated WITHOUT parameter overrides (its defaults are the hardened configuration)
            ot_hdc_v41x_hcp_lanes u_lg (.clk(clk), .rst_n(rst_n), .fst(first), .gov_i(ov_r), .lv_i(lvs[gg*LG +: LG]),
                .ss_i(sss[gg*LG +: LG]), .w_i(w_data[gg*LG*32 +: LG*32]), .x_i(x_data[gg*LG*16 +: LG*16]),
                .s_i(sum_in[gg*LG*32 +: LG*32]), .y(sum_out[gg*LG*32 +: LG*32]), .lf(lfg[gg]));
        end
        // the leaves' registered group faults stand in for lf_q (same cycle)
        assign lf_any = |lfg;
    end endgenerate
endmodule

// el1011-hbm-hcvm/hc round 4: HARD LANE-GROUP LEAF of the systolic HC bank tile (ot_hdc_v41x_hcp_stage LG = 8).  G FP32
// MAC lanes (product = w * x, partial chunk sum + product) exactly as the stage's flat g_lane, with its own clock tree.
// Every input lands in a pin flop that is the flat stage's input register (w_in, x_in, sum_q, lv_r, ss_r, gov, fst_q),
// every output is a flop (the seam register so_q when SOR, the adder output otherwise; lf = the flat lf_q), so the
// stage latency is bit-for-bit and cycle-for-cycle the flat one.  The defaults ARE the hardened configuration (the
// stage instantiates it without overrides).
module ot_hdc_v41x_hcp_lanes #(
    parameter integer G     = 8,
    parameter integer LM    = 8,
    parameter integer LA    = 7,
    parameter integer SOR   = 1,
    parameter integer LRST  = 1,
    parameter integer ADRST = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            fst,
    input  wire            gov_i,
    input  wire [G-1:0]    lv_i,
    input  wire [G-1:0]    ss_i,
    input  wire [G*32-1:0] w_i,
    input  wire [G*16-1:0] x_i,
    input  wire [G*32-1:0] s_i,
    output wire [G*32-1:0] y,
    output reg             lf
);
    reg [G*32-1:0] w_in, sum_q; reg [G*16-1:0] x_in;
    (* keep = "true" *) reg [G-1:0] lv_r, ss_r;
    reg fst_q, gov;
    always @(posedge clk) begin
        w_in <= w_i; x_in <= x_i; sum_q <= s_i; lv_r <= lv_i; ss_r <= ss_i; fst_q <= fst;
    end
    wire [G-1:0] lfl;
    wire [G*32-1:0] y_l;
    generate if (SOR != 0) begin : g_sor
        reg [G*32-1:0] so_q; always @(posedge clk) so_q <= y_l; assign y = so_q;
    end else begin : g_nsor
        assign y = y_l;
    end endgenerate
    genvar gl;
    generate for (gl = 0; gl < G; gl = gl + 1) begin : g_lane
        wire lrn;
        if (LRST != 0) begin : g_lr
            (* keep = "true" *) reg r; always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= 1'b1;
            assign lrn = r;
        end else begin : g_nlr
            assign lrn = rst_n;
        end
        wire [31:0] xw = {x_in[16*gl +: 16], 16'h0000};
        reg  [31:0] gx, gw;
        always @(posedge clk) begin
            gx <= lv_r[gl] ? xw : 32'd0;
            gw <= lv_r[gl] ? (ss_r[gl] ? xw : w_in[32*gl +: 32]) : 32'd0;
        end
        wire [31:0] prod; wire [1:0] e0, e1; wire v0, v1;
        ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(ADRST)) u_mul (.clk(clk), .rst_n(lrn), .valid_in(gov), .a(gw), .b(gx), .y(prod),
                                    .err(e0), .valid_out(v0));
        ot_hdc_fp32_add_lat #(.LAT(LA), .DRST(ADRST)) u_add (.clk(clk), .rst_n(lrn), .valid_in(v0),
                                    .a(fst_q ? 32'd0 : sum_q[32*gl +: 32]), .b(prod), .y(y_l[32*gl +: 32]), .err(e1),
                                    .valid_out(v1));
        assign lfl[gl] = (v0 && (|e0)) || (v1 && (|e1));
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gov <= 1'b0; lf <= 1'b0; end else begin gov <= gov_i; lf <= |lfl; end
endmodule

