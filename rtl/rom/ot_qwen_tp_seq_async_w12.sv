`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Asynchronous-collective variant of ot_qwen_tp_seq_w12 (which stays
// byte-identical): the tensor-group sequencer of one die, with an opt-in
// CUT-THROUGH all-reduce (dataflow level 5, collective fusion).
//
// ASYNC_COLL = 0 (default): identical behaviour to ot_qwen_tp_seq_w12; the ME
// observation ports are ignored.
//
// ASYNC_COLL = 1: an all-reduce descriptor with bit [20] (CUT) set is sent
// WHILE the core still runs the segment, instead of after its END.  The
// sequencer observes the matrix engine's result writes (the die's vw_me_*
// ports) and keeps one bit per vector-memory word of the all-reduce region
// [vw, vw + nw); word k is sent, in word order, as soon as the engine has
// written all 16 of its lanes in one result write in this segment (the
// engine's masks are full except past the op's output count), or once the
// core reports END, whose barrier means every write has landed (so a word
// written in partial masks waits for END: slower, never early).  Receives are
// accepted from the first one and written back in word order exactly as
// before; the segment advances when the core is done AND the last word is
// received.  The per-word rank-order fold ((p0+p1)+p2)+p3 in
// ot_rom_oneshot_allreduce, the word order, the record tags and the `last`
// protocol checks are unchanged: only the send time moves.
//
// Program contract for CUT (checked by tools/qwen_rom_async_coll.py, which is
// the only producer of the bit): in the segment, the last operation before END
// is the one ME op that writes the whole region, no other ME op of the segment
// writes into it, nothing after it reads or writes it, and END carries a
// barrier.  A descriptor without CUT runs the legacy path, so a binary with
// ASYNC_COLL = 1 runs every existing image unchanged.
// ---------------------------------------------------------------------------
module ot_qwen_tp_seq_async_w12 #(
    parameter integer ENABLE_AR256 = 0,
    parameter integer ASYNC_COLL = 0,      // 1: decode descriptor bit [20] as a cut-through all-reduce
    // 1: pipelined scoreboard set (see below): tap register (the ME->sequencer hop), then offset /
    // range / predecode, then AND-OR into lw.  A result write is visible to the send check 2 cycles
    // later than with 0 (never earlier, so never an early send).  0: the original single-cycle set.
    // 2 / 3: the read loop has no wide lookup (see "registered read" below): the send check reads a
    // REGISTERED ready bit, precomputed a cycle early from lw[rd_k] (hold) and lw[rd_k + 1] (advance),
    // so a mark is visible 3 cycles after the write (never earlier).  The set narrows the tap to
    // {valid & full & addr < 512, addr[8:0]} and range-checks by two short compares against
    // registered limits; 2 registers the offset as two 16-way one-hots (as 1), 3 registers the
    // 8-bit offset and decodes it in the AND-OR stage (fewer flops).
    // 4: the mark visibility of 2 (cycle-identical to 2) with no segment-end compare and no wide
    // select or subtract on any loop: `more` (= rd_k < nw) and `rx_end` (= rx_k == rx_total - 1) are
    // registers precomputed from both outcomes (hold / advance); the ready bit is the registered pair
    // {lw[ra], lw[ra + 1]} selected by the registered previous rd_go; and lw is indexed by the word's
    // ABSOLUTE address mod 256 (a region is at most 256 consecutive words, so the index is unique in
    // it), so the set decodes addr[7:0] directly (no addr - vw) and the read index is ra = vw + rd_k,
    // the vector-memory read address, kept as a register.
    parameter integer SB_PIPE = 0,
    parameter integer NP   = 1,            // ME result-port groups observed (G >> SMIN)
    parameter integer MAW  = 24,           // ME result word-address width
    parameter integer N    = 4,
    parameter integer NW   = 16,
    parameter integer PAW  = 12,
    parameter integer VWA  = 8,
    parameter integer DAW  = 6,
    parameter integer FW   = 512,
    parameter integer TAGW = 32,
    // Qwen full-vocabulary descriptors extend row0 with reserved bits
    // [19:18]; the existing 64-bit descriptor shape is unchanged.
    parameter integer QWEN_FULLSHAPE = 0,
    parameter integer RB   = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    // package controller side (the core's handshake)
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    output reg               done,
    output reg  [NW-1:0]     next_token,
    output reg  [31:0]       next_val,
    output reg               fault,
    output wire              coll_busy,
    // decode core
    output wire              core_start,
    output wire [NW-1:0]     core_token,
    output wire [NW-1:0]     core_pos,
    input  wire              core_done,
    input  wire [NW-1:0]     core_next_token,
    input  wire [31:0]       core_next_val,
    input  wire              core_fault,
    output reg  [PAW-1:0]    prog_base,
    // segment descriptors (synchronous read)
    output reg               desc_re,
    output reg  [DAW-1:0]    desc_addr,
    input  wire [63:0]       desc_q,
    // vector memory word port (synchronous read)
    output reg               vm_re,
    output reg  [VWA-1:0]    vm_raddr,
    input  wire [FW-1:0]     vm_rq,
    output reg               vm_we,
    output reg  [VWA-1:0]    vm_waddr,
    output reg  [FW-1:0]     vm_wdata,
    // one-shot collective unit (ot_rom_oneshot_allreduce die port)
    output wire              c_valid,
    input  wire              c_ready,
    output wire [FW-1:0]     c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [TAGW-1:0]   c_tag,
    input  wire              r_valid,
    input  wire [FW-1:0]     r_data,
    input  wire              r_last,
    input  wire [RB-1:0]     r_rank,
    input  wire              r_err,
    // matrix-engine result writes of the die (observation only; ASYNC_COLL = 1)
    input  wire [NP-1:0]     me_we,
    input  wire [NP*MAW-1:0] me_addr,
    input  wire [NP*16-1:0]  me_mask
);
    localparam [1:0] K_END = 2'd0, K_AR = 2'd1, K_ARGMAX = 2'd2;
    localparam [2:0] S_IDLE = 0, S_DESC = 1, S_DLAT = 2, S_RUN = 3, S_CWAIT = 4, S_COLL = 5;
    localparam integer CUT_BIT = 20;
    localparam integer LN = FW / 32;          // lanes per vector-memory word
    reg [2:0]     st;
    reg [NW-1:0]  tok_r, pos_r;
    reg [DAW-1:0] seg;
    reg [1:0]     kind;
    reg [VWA-1:0] vw;
    reg [8:0]     nw;
    reg [NW-1:0]  row0;
    reg           cut;                      // this segment's all-reduce is cut-through
    reg           core_fin, rx_fin;         // cut-through: the core's END seen / the last word received

    assign core_start = (st == S_RUN);
    assign core_token = tok_r;
    assign core_pos   = pos_r;
    assign c_tag      = {tok_r, pos_r[7:0], {(8 - DAW){1'b0}}, seg};
    // the collective is live in S_COLL, and for a cut-through segment already while the core runs
    wire   coll_on    = (st == S_COLL) || (cut && st == S_CWAIT);
    assign coll_busy  = coll_on;

    // argmax order: larger logit wins (ties are impossible across ranks' rows
    // except by value, and then the earlier rank -- the lower row -- stays)
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction

    // -- cut-through scoreboard: region words the engine has written whole this segment -------------
    // one bit per word, set by a full-mask result write: a decoder per port and a port-OR per word
    reg  [255:0]  lw;
    wire [7:0]    rd_w = rd_k[7:0];
    reg           rdy;                      // SB_PIPE >= 2: registered lw[rd_k] (one cycle old)
    reg           rdy_h, rdy_a, go_r;       // SB_PIPE = 4: lw[ra], lw[ra + 1] and rd_go, one cycle old
    reg  [7:0]    ra, rab;                  // SB_PIPE = 4: vw + rd_k and vw + rd_k + 1 (mod 256)
    wire          rdy_s = (SB_PIPE >= 4) ? (go_r ? rdy_a : rdy_h) : rdy;
    wire          word_ok = !cut || core_fin || ((SB_PIPE >= 2) ? rdy_s : lw[rd_w]);

    // -- transmit: vector-memory words (all-reduce) or the argmax record ------------------
    localparam integer QD = 4;
    reg [FW-1:0] q_d [0:QD-1];
    reg [1:0]    q_w, q_r;
    reg [2:0]    q_n;
    reg [8:0]    rd_k, tx_k, rx_k;
    reg [7:0]    rd_kb;                     // rd_k + 1 (mod 256): the advance select of the registered read
    reg          rd_v;
    assign c_valid = coll_on && (q_n != 0);
    assign c_data  = q_d[q_r];
    assign c_mode  = (kind == K_ARGMAX);
    assign c_last  = (tx_k == ((kind == K_ARGMAX) ? 9'd0 : nw - 1'b1));
    wire   c_fire  = c_valid && c_ready;
    reg    more;                            // SB_PIPE = 4: registered rd_k < nw (the segment-end check)
    wire   rd_more = (SB_PIPE >= 4) ? more : (rd_k < nw);
    wire   rd_go   = coll_on && kind == K_AR && rd_more && (q_n + rd_v) < QD && word_ok;

    reg [NW-1:0] best_i;
    reg [31:0]   best_v;
    wire [31:0]  g_val = r_data[31:0];
    wire [NW-1:0] g_idx = r_data[32 +: NW];
    wire [8:0]   rx_total = (kind == K_ARGMAX) ? N : nw;
    reg          rx_end;                    // SB_PIPE = 4: registered rx_k == rx_total - 1
    wire         rx_is_end = (SB_PIPE >= 4) ? rx_end : (rx_k == rx_total - 1'b1);
    wire         rx_last = r_valid && rx_is_end;

    always @(*) begin
        vm_re = rd_go;
        vm_raddr = vw + rd_k;
    end

    generate if (SB_PIPE == 0) begin : g_sb0
    // per port: the region word offset it writes whole this cycle (one-hot over 256 words)
    wire [255:0] hit_p [0:NP-1];
    wire [255:0] hit;
    genvar gp;
        for (gp = 0; gp < NP; gp = gp + 1) begin : g_port
            wire [MAW-1:0] a   = me_addr[gp*MAW +: MAW];
            wire [MAW-1:0] off = a - {{(MAW - VWA){1'b0}}, vw};
            wire           in  = me_we[gp] && (&me_mask[gp*16 +: LN]) && a >= {{(MAW - VWA){1'b0}}, vw}
                                 && off < {{(MAW - 9){1'b0}}, nw};
            assign hit_p[gp] = in ? (256'd1 << off[7:0]) : 256'd0;
        end
    integer pi;
    reg [255:0] hit_or;
    always @(*) begin
        hit_or = 256'd0;
        for (pi = 0; pi < NP; pi = pi + 1) hit_or = hit_or | hit_p[pi];
    end
    assign hit = hit_or;
    always @(posedge clk) begin
        if (ASYNC_COLL != 0) begin
            if (st == S_DLAT) lw <= 256'd0;
            else if (cut && (st == S_RUN || st == S_CWAIT)) lw <= lw | hit;
        end
    end
    end else if (SB_PIPE == 1) begin : g_sb1
    // Pipelined scoreboard set (SB_PIPE = 1).  Every stage only DELAYS a mark, so a word is still
    // sent only after the engine wrote it whole in this segment:
    //   t0  tap register: we & full-mask, word address (the register on the ME -> sequencer hop)
    //   t1  per port: offset = addr - vw and range check, registered as two 16-way one-hots
    //       (offset[3:0], offset[7:4]) -- the subtract never meets the decode or the OR tree
    //   t2  hit[w] = OR over ports of lo[w%16] & hi[w/16]; lw <= lw | hit
    // Segment isolation: t1/t2 only capture while this segment's core runs (S_RUN/S_CWAIT; vw is
    // stable there) and lw only updates then.  The previous segment's writes all land before its
    // core_done, which leaves S_CWAIT, so none of them can reach lw after the S_DLAT clear.
    wire run_seg = cut && (st == S_RUN || st == S_CWAIT);
    reg  [NP-1:0]     s0_v;
    reg  [NP*MAW-1:0] s0_a;
    reg  [NP-1:0]     s1_v;
    reg  [NP*16-1:0]  s1_lo, s1_hi;
    genvar gp;
    for (gp = 0; gp < NP; gp = gp + 1) begin : g_port
        wire [MAW-1:0] a   = s0_a[gp*MAW +: MAW];
        wire [MAW-1:0] off = a - {{(MAW - VWA){1'b0}}, vw};
        wire           in  = s0_v[gp] && a >= {{(MAW - VWA){1'b0}}, vw} && off < {{(MAW - 9){1'b0}}, nw};
        always @(posedge clk) begin
            s0_v[gp] <= me_we[gp] && (&me_mask[gp*16 +: LN]);
            s0_a[gp*MAW +: MAW] <= me_addr[gp*MAW +: MAW];
            s1_v[gp] <= in && run_seg;
            s1_lo[gp*16 +: 16] <= 16'd1 << off[3:0];
            s1_hi[gp*16 +: 16] <= 16'd1 << off[7:4];
        end
    end
    reg [255:0] hit_or;
    integer pi, wi;
    always @(*) begin
        hit_or = 256'd0;
        for (wi = 0; wi < 256; wi = wi + 1)
            for (pi = 0; pi < NP; pi = pi + 1)
                hit_or[wi] = hit_or[wi] | (s1_v[pi] & s1_lo[pi*16 + (wi % 16)] & s1_hi[pi*16 + (wi / 16)]);
    end
    always @(posedge clk) begin
        if (ASYNC_COLL != 0) begin
            if (st == S_DLAT) lw <= 256'd0;
            else if (run_seg) lw <= lw | hit_or;
        end
    end
    end else begin : g_sb2
    // SB_PIPE = 2 / 3.  Every stage only DELAYS a mark (as 1):
    //   t0  tap register: v = we & full mask & addr < 512 (a region word is < vw + nw <= 511), a9 = addr[8:0]
    //   t1  per port: in = v & vw <= a9 < vlim (vlim = vw + nw, a register), offset = a9 - vw (8 bits);
    //       2: registered as two 16-way one-hots; 3: registered as the 8-bit offset
    //   t2  hit[w] = OR over ports of (offset == w); lw <= lw | hit
    // t1 captures only in S_CWAIT: vlim is loaded at the S_RUN edge, and nothing of this segment can
    // reach the tap in S_RUN (the core samples core_start on that edge; the previous segment's writes
    // all land before its core_done).
    wire run_seg = cut && (st == S_RUN || st == S_CWAIT);
    reg  [9:0]        vlim;
    always @(posedge clk) vlim <= {2'b00, vw} + {1'b0, nw};
    reg  [NP-1:0]     s0_v;
    reg  [NP*9-1:0]   s0_a;
    reg  [NP-1:0]     s1_v;
    reg  [NP*16-1:0]  s1_lo, s1_hi;
    reg  [NP*8-1:0]   s1_o;
    genvar gp;
    for (gp = 0; gp < NP; gp = gp + 1) begin : g_port
        wire [MAW-1:0] ma  = me_addr[gp*MAW +: MAW];
        wire [8:0]     a   = s0_a[gp*9 +: 9];
        wire [7:0]     off = a[7:0] - vw;
        wire           in  = s0_v[gp] && a >= {1'b0, vw} && {1'b0, a} < vlim;
        always @(posedge clk) begin
            s0_v[gp] <= me_we[gp] && (&me_mask[gp*16 +: LN]) && (ma >> 9) == 0;
            s0_a[gp*9 +: 9] <= ma[8:0];
            s1_v[gp] <= in && cut && st == S_CWAIT;
            if (SB_PIPE >= 4) begin                     // absolute index: no subtract
                s1_lo[gp*16 +: 16] <= 16'd1 << a[3:0];
                s1_hi[gp*16 +: 16] <= 16'd1 << a[7:4];
            end else if (SB_PIPE == 2) begin
                s1_lo[gp*16 +: 16] <= 16'd1 << off[3:0];
                s1_hi[gp*16 +: 16] <= 16'd1 << off[7:4];
            end else s1_o[gp*8 +: 8] <= off;
        end
    end
    reg [255:0] hit_or;
    integer pi, wi;
    always @(*) begin
        hit_or = 256'd0;
        for (wi = 0; wi < 256; wi = wi + 1)
            for (pi = 0; pi < NP; pi = pi + 1)
                if (SB_PIPE != 3)
                    hit_or[wi] = hit_or[wi] | (s1_v[pi] & s1_lo[pi*16 + (wi % 16)] & s1_hi[pi*16 + (wi / 16)]);
                else
                    hit_or[wi] = hit_or[wi] | (s1_v[pi] && s1_o[pi*8 +: 8] == wi[7:0]);
    end
    always @(posedge clk) begin
        if (ASYNC_COLL != 0) begin
            if (st == S_DLAT) lw <= 256'd0;
            else if (run_seg) lw <= lw | hit_or;
        end
    end
    end endgenerate

    // -- registered read (SB_PIPE >= 2): the issue/read loop rd_k -> word_ok -> rd_go -> rd_k has no
    // wide lookup.  rdy is lw[rd_k] of the previous cycle: the 256:1 selects lw[rd_k] and lw[rd_kb]
    // are register-to-register paths (rd_k, rd_kb -> mux -> rdy), and rd_go only picks one of the two.
    // lw only grows inside a segment and is cleared in S_DLAT, where rdy is cleared too, so rdy = 1
    // implies lw[rd_k] = 1 (asserted below): a word is never sent before the engine wrote it whole.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rdy <= 1'b0;
        else if (st == S_DLAT) rdy <= 1'b0;
        else rdy <= rd_go ? lw[rd_kb] : lw[rd_w];
    end
    // SB_PIPE = 4: both outcomes are registered without rd_go (rdy_h = lw[ra], rdy_a = lw[ra + 1])
    // and the previous rd_go picks one, so rdy_s(t+1) = rd_go(t) ? lw(t)[ra(t) + 1] : lw(t)[ra(t)]:
    // the rdy of SB_PIPE = 2 with lw re-indexed (cleared alike in S_DLAT), so the same send cycles.
    // ra follows rd_k: +1 on rd_go, vw at the two clears (the S_DLAT one loads vw from desc_q).
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rdy_h <= 1'b0; rdy_a <= 1'b0; go_r <= 1'b0; end
        else if (st == S_DLAT) begin rdy_h <= 1'b0; rdy_a <= 1'b0; go_r <= 1'b0; end
        else begin rdy_h <= lw[ra]; rdy_a <= lw[rab]; go_r <= rd_go; end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ra <= 8'd0; rab <= 8'd1; end
        else if (st == S_DLAT && !desc_re) begin ra <= desc_q[2 +: 8]; rab <= desc_q[2 +: 8] + 8'd1; end
        else if (st == S_CWAIT && core_done && !cut) begin ra <= vw; rab <= vw + 8'd1; end
        else if (coll_on && rd_go) begin ra <= rab; rab <= rab + 8'd1; end
    end
    // SB_PIPE = 4: rx_end = (rx_k == rx_total - 1), precomputed likewise: rx_k changes only by an
    // accepted receive in coll_on (+1) and the two clears; kind and nw change only in S_DLAT.
    wire [8:0] n9 = N;
    wire [8:0] rx_tot_ld = (desc_q[1:0] == K_ARGMAX) ? n9 : nw_ld;
    wire [8:0] rx_k1  = rx_k + 9'd1;
    wire [8:0] rx_tm1 = rx_total - 9'd1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rx_end <= 1'b0;
        else if (st == S_DLAT && !desc_re) rx_end <= rx_tot_ld == 9'd1;
        else if (st == S_CWAIT && core_done && !cut) rx_end <= rx_total == 9'd1;
        else if (coll_on && r_valid) rx_end <= rx_k1 == rx_tm1;
        else rx_end <= rx_k == rx_tm1;
    end
    // SB_PIPE = 4: more = (rd_k < nw), precomputed from both outcomes of this cycle.  rd_k changes only
    // by rd_go (+1) and by the two clears (S_DLAT, which also loads nw, and the non-cut S_CWAIT END);
    // nw changes only in S_DLAT.  Asserted below against the direct compare.
    wire [8:0] nw_ld = (ENABLE_AR256 != 0 && desc_q[1:0] == K_AR && desc_q[10 +: 8] == 8'd0) ? 9'd256 : {1'b0, desc_q[10 +: 8]};
    wire       m_hold = rd_k < nw;
    wire       m_adv  = {1'b0, rd_k} + 10'd1 < {1'b0, nw};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) more <= 1'b0;
        else if (st == S_DLAT && !desc_re) more <= nw_ld != 9'd0;
        else if (st == S_CWAIT && core_done && !cut) more <= nw != 9'd0;
        else more <= rd_go ? m_adv : m_hold;
    end
`ifndef SYNTHESIS
    always @(posedge clk) begin
        if (rst_n && ASYNC_COLL != 0 && SB_PIPE >= 4 && (more != (rd_k < nw) || rx_end != (rx_k == rx_total - 1'b1)
                || ra != vw + rd_k[7:0] || rab != vw + rd_k[7:0] + 8'd1)) begin
            $display("ot_qwen_tp_seq_async_w12: %m: precomputed issue state diverged (more=%0d rd_k=%0d nw=%0d rx_end=%0d rx_k=%0d ra=%0d vw=%0d)",
                     more, rd_k, nw, rx_end, rx_k, ra, vw);
            $fatal(1);
        end
        if (rst_n && ASYNC_COLL != 0 && SB_PIPE >= 4 && rd_go && cut && !core_fin && !lw[ra]) begin
            $display("ot_qwen_tp_seq_async_w12: %m: early send of word %0d", rd_k);
            $fatal(1);
        end
    end
`endif
`ifndef SYNTHESIS
    always @(posedge clk) begin
        if (rst_n && ASYNC_COLL != 0 && (SB_PIPE == 2 || SB_PIPE == 3) && rd_go && cut && !core_fin && !lw[rd_w]) begin
            $display("ot_qwen_tp_seq_async_w12: %m: early send of word %0d", rd_k);
            $fatal(1);
        end
    end
`endif
`ifdef OT_SB_TRACE
    // ME-write order trace of cut-through segments (measurement only)
    integer tr_cyc = 0, tr_p;
    always @(posedge clk) begin
        tr_cyc <= tr_cyc + 1;
        if (cut && (st == S_RUN || st == S_CWAIT)) begin
            for (tr_p = 0; tr_p < NP; tr_p = tr_p + 1)
                if (me_we[tr_p] && (&me_mask[tr_p*16 +: LN]) && me_addr[tr_p*MAW +: MAW] >= {{(MAW - VWA){1'b0}}, vw}
                    && me_addr[tr_p*MAW +: MAW] - {{(MAW - VWA){1'b0}}, vw} < {{(MAW - 9){1'b0}}, nw})
                    $display("SBT %m c=%0d seg=%0d p=%0d w=%0d", tr_cyc, seg, tr_p, me_addr[tr_p*MAW +: MAW] - vw);
            if (rd_go) $display("SBR %m c=%0d seg=%0d k=%0d", tr_cyc, seg, rd_k);
        end
        if (cut && st == S_CWAIT && core_done) $display("SBD %m c=%0d seg=%0d", tr_cyc, seg);
    end
`endif

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; next_token <= 0; next_val <= 0;
            tok_r <= 0; pos_r <= 0; seg <= 0; kind <= K_END; vw <= 0; nw <= 0; row0 <= 0;
            prog_base <= 0; desc_re <= 1'b0; desc_addr <= 0;
            vm_we <= 1'b0; vm_waddr <= 0; vm_wdata <= 0;
            q_w <= 0; q_r <= 0; q_n <= 0; rd_k <= 0; rd_kb <= 8'd1; tx_k <= 0; rx_k <= 0; rd_v <= 1'b0;
            best_i <= 0; best_v <= 0; cut <= 1'b0; core_fin <= 1'b0; rx_fin <= 1'b0;
        end else begin
            desc_re <= 1'b0;
            vm_we <= 1'b0;
            rd_v <= rd_go;
            // queue (vector-memory words read one cycle earlier; pop on send) and receive: in S_COLL,
            // and for a cut-through segment from the core's start
            if (coll_on) begin
                if (rd_go) begin rd_k <= rd_k + 1'b1; rd_kb <= rd_kb + 1'b1; end
                if (rd_v) begin q_d[q_w] <= vm_rq; q_w <= q_w + 1'b1; end
                if (c_fire) begin q_r <= q_r + 1'b1; tx_k <= tx_k + 1'b1; end
                q_n <= q_n + (rd_v ? 1'b1 : 1'b0) - (c_fire ? 1'b1 : 1'b0);
                if (r_valid) begin
                    if (r_err) fault <= 1'b1;
                    rx_k <= rx_k + 1'b1;
                    if (r_last != rx_is_end) fault <= 1'b1;
                    if (kind == K_AR) begin
                        vm_we <= 1'b1; vm_waddr <= vw + rx_k; vm_wdata <= r_data;
                    end else begin
                        if (r_rank != rx_k[RB-1:0]) fault <= 1'b1;
                        if (rx_k == 0 || okey(g_val) > okey(best_v)) begin
                            best_v <= g_val; best_i <= g_idx;
                        end
                    end
                end
            end
            case (st)
                S_IDLE: if (start) begin
                    tok_r <= token; pos_r <= pos; seg <= 0; done <= 1'b0;
                    desc_re <= 1'b1; desc_addr <= 0; st <= S_DLAT;
                end
                S_DESC: begin desc_re <= 1'b1; desc_addr <= seg; st <= S_DLAT; end
                S_DLAT: if (!desc_re) begin
                    kind <= desc_q[1:0]; vw <= desc_q[2 +: 8];
                    nw <= (ENABLE_AR256 != 0 && desc_q[1:0] == K_AR && desc_q[10 +: 8] == 8'd0) ? 9'd256 : {1'b0, desc_q[10 +: 8]};
                    prog_base <= desc_q[32 +: PAW];
                    row0 <= (QWEN_FULLSHAPE != 0) ?
                            ({desc_q[19:18], desc_q[63:48]}) : desc_q[48 +: NW];
                    cut <= (ASYNC_COLL != 0) && desc_q[1:0] == K_AR && desc_q[CUT_BIT];
                    core_fin <= 1'b0; rx_fin <= 1'b0;
                    rd_k <= 0; rd_kb <= 8'd1; tx_k <= 0; rx_k <= 0;
                    st <= S_RUN;
                end
                S_RUN: st <= S_CWAIT;              // the core samples core_start on this edge
                S_CWAIT: begin
                    if (cut && rx_last) rx_fin <= 1'b1;        // only after every word was sent: see word_ok
                    if (core_done) begin
                        if (core_fault) fault <= 1'b1;
                        if (cut) begin
                            // the transfer is already running: keep its counters
                            core_fin <= 1'b1;
                            if (rx_fin || rx_last) begin
                                cut <= 1'b0; seg <= seg + 1'b1; st <= S_DESC;
                            end else st <= S_COLL;
                        end else begin
                            rd_k <= 0; rd_kb <= 8'd1; tx_k <= 0; rx_k <= 0;
                            if (kind == K_END) begin
                                done <= 1'b1; next_token <= core_next_token + row0; next_val <= core_next_val;
                                st <= S_IDLE;
                            end else begin
                                if (kind == K_ARGMAX) begin
                                    // the die's own {logit, row} is the one record it gathers
                                    q_d[q_w] <= {{(FW - 32 - NW){1'b0}}, core_next_token + row0, core_next_val};
                                    q_w <= q_w + 1'b1;
                                    q_n <= q_n + 1'b1;
                                end
                                st <= S_COLL;
                            end
                        end
                    end
                end
                S_COLL: begin
                    if (rx_last) begin
                        if (kind == K_AR) begin
                            cut <= 1'b0; seg <= seg + 1'b1; st <= S_DESC;
                        end else begin
                            done <= 1'b1; st <= S_IDLE;
                            if (okey(g_val) > okey(best_v)) begin
                                next_token <= g_idx; next_val <= g_val;
                            end else begin
                                next_token <= best_i; next_val <= best_v;
                            end
                        end
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
