`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice BANK TILE (el1011-hbm-b2-vm, 2026-10-12).  One bank of one quadrant's VM slice; the slice is 8 of these
// (lane b <-> bank b), a hub tile (packet clients) and two ring stops.  Hardened once, placed 32x on the die: the bank
// and slice ids are strap inputs, so every instance is the same netlist.
//
// Address map (B2): global sector S = byte address >> 5.  sec16 = {m, S[14:0]}.
//   main   (m = 0): slice S[14:13], bank S[2:0], row S[12:3]           (65,536 words a slice; 262,144 on the die)
//   mirror (m = 1): S[14:13] = 0, bank S[2:0], row S[12:3] of the mirror window (65,536 words, replicated per slice)
//   rowm = {m, row 10}.  An op whose bank != bid, or (main) slice != sid, or (mirror) S[14:13] != 0, latches FAULT and
//   is executed with its write mask cleared (a read still answers, so every in-order stream drains).
// Storage per bank: three ot_sram_1r1w_1024x256 macros.  A[row] = main word bits [255:0]; C[row] = mirror [255:0];
//   B[row] = {free 144, mirror [311:256], main [311:256]}.  Each FP32 word carries its own (39,32) SECDED code (8 x 39 =
//   312 b a sector), so word-masked writes need no read-modify-write.  1R1W per bank per cycle.
// Ports (every input pin-flopped, every output a flop):
//   rq  [RG]  wide read lanes {v, sec16}; rq_cr = one credit back when the request leaves its lane queue;
//             rr {v, data 256} in request order, no back-pressure.
//   wq  [WG]  client wide write lanes {v, sec16, data 256, wmask 8}; wq_cr = credit (left the queue), wq_done = in the
//             macro.  A MIRROR write is also sent on the egress port (the ring broadcasts it to the other 3 slices); it
//             is granted only while an egress credit is held, so the client's credit protocol is unchanged.
//   dq        DMA wide write lane (never back-pressured: it always wins the write port); dq_done.
//   kq        COLL broadcast lane (the collective result tree, 2.2 kb across a die centre line): as one wq lane.
//   xq, xq2   ring write lanes {v, rowm 11, data 256, wmask 8} (a mirror write broadcast by another slice) from the CW
//             and the CCW ring stop; xq*_cr, xq*_done.
//   eg        mirror egress {v, rowm 11, data 256, wmask 8} to BOTH ring stops (CW copy -> sid+1/+2, CCW copy -> sid+3);
//             eg_cr[d] returns one of EGC credits of stop d; a mirror write is granted only with a credit of each.
//   pq        packet port from the hub {v, we, rowm 11, data 256, wmask 8, tag 8}; pq_cr = credit (PQ deep);
//             pr {v, we, tag 8, data 256}: reads and writes alike, in pq order, no back-pressure.
//   status    {fault, ue, ce 16} (sticky / saturating).
// Pipeline: pin flop -> queue -> grant (S1) -> encode, macro pins (S2) -> macro edge (M) -> capture (C, the only load of
//   the macro outputs) -> select + syndrome (D) -> correct, response flop (R).  Reads and writes take the same path to
//   the macro, so the grant order is the macro order (a packet write then read of one row is RAW-safe).
// Write port priority: DMA, then round robin over {WG lanes, kq, xq, packet, xq2}; read port: round robin over {RG, packet}.
// Reset only on control (valids, pointers, counters, credits, status); payload flops, queues and the pipeline payload
// have no reset, so rst_n loads only the control flops.
module ot_vms_bank #(
    parameter integer RG  = 2,
    parameter integer WG  = 2,
    // Wide lane credits (B2 SPEC v0.8, D-B2-12): lane g's queue depth = the credits its client holds = 4 + 2 x the relay
    // stages each way between the lane's farthest client and this tile (contract relay count; RRS / WRS, 4 b a lane).
    // 4 + 2 S covers the credit round trip, so a client S stages away keeps 1 op / lane / cycle.  Default S = 3 = the
    // local lane group's far station (slice -> SU -> SFU -> HC); the hardened tile is built at these defaults.
    parameter [RG*4-1:0] RRS = {RG{4'd3}},
    parameter [WG*4-1:0] WRS = {WG{4'd3}},
    parameter integer KQD = 2,      // coll queue depth
    parameter integer XQD = 2,      // ring write queue depth
    parameter integer PQ  = 4,      // packet queue depth = hub credits for this bank
    parameter integer EGC = 2,      // egress credits = the CW stop's lane buffer depth
    parameter integer MUT = 0       // 1: mirror writes are NOT sent on egress (broadcast lost: must FAIL);
                                    // 2: every wide lane queue one entry shorter than its credits (overrun: must FAIL)
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [2:0]         bid,
    input  wire [1:0]         sid,
    input  wire [RG*17-1:0]   rq,
    output reg  [RG-1:0]      rq_cr,
    output wire [RG*257-1:0]  rr,
    input  wire [WG*281-1:0]  wq,
    output reg  [WG-1:0]      wq_cr,
    output reg  [WG-1:0]      wq_done,
    input  wire [280:0]       dq,
    output reg                dq_done,
    input  wire [280:0]       kq,
    output reg                kq_cr,
    output reg                kq_done,
    input  wire [275:0]       xq,
    output reg                xq_cr,
    output reg                xq_done,
    input  wire [275:0]       xq2,
    output reg                xq2_cr,
    output reg                xq2_done,
    output wire [275:0]       eg,
    input  wire [1:0]         eg_cr,
    input  wire [284:0]       pq,
    output reg                pq_cr,
    output wire [265:0]       pr,
    output reg  [17:0]        status
);
    // ------------------------------------------------------------------ SECDED (39,32), same code as ot_hgi_vm_core
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1) for (b = a + 1; b < 7; b = b + 1) for (c = b + 1; c < 7; c = c + 1) begin
                if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                n = n + 1;
            end
            colv = v;
        end
    endfunction
    function automatic [32*7-1:0] cols_all(input integer dummy);
        integer i; reg [32*7-1:0] r;
        begin r = '0; for (i = 0; i < 32; i = i + 1) r[i*7 +: 7] = colv(i); cols_all = r; end
    endfunction
    localparam [32*7-1:0] COLS = cols_all(0);
    function automatic [7*32-1:0] rows_all(input integer dummy);
        integer i, j; reg [7*32-1:0] r;
        begin r = '0; for (j = 0; j < 7; j = j + 1) for (i = 0; i < 32; i = i + 1) r[j*32 + i] = COLS[i*7 + j]; rows_all = r; end
    endfunction
    localparam [7*32-1:0] ROWM = rows_all(0);
    function automatic [6:0] chk(input [31:0] d);
        integer j; reg [6:0] c;
        begin for (j = 0; j < 7; j = j + 1) c[j] = ^(d & ROWM[j*32 +: 32]); chk = c; end
    endfunction
    function automatic [311:0] enc8(input [255:0] d);
        integer k; reg [311:0] r;
        begin for (k = 0; k < 8; k = k + 1) r[k*39 +: 39] = {chk(d[k*32 +: 32]), d[k*32 +: 32]}; enc8 = r; end
    endfunction

    // ------------------------------------------------------------------ sector decode
    // returns {bad, rowm 11}
    function automatic [11:0] dsec(input [15:0] s, input [2:0] b, input [1:0] q);
        reg bad;
        begin
            bad = (s[2:0] != b) || (s[15] ? (s[14:13] != 2'd0) : (s[14:13] != q));
            dsec = {bad, s[15], s[12:3]};
        end
    endfunction

    // ------------------------------------------------------------------ pin flops (payload: no reset)
    reg [RG*17-1:0] rq_d; reg [WG*281-1:0] wq_d; reg [280:0] dq_d, kq_d; reg [275:0] xq_d, x2_d; reg [284:0] pq_d;
    reg [RG-1:0] rq_v; reg [WG-1:0] wq_v; reg dq_v, kq_v, xq_v, x2_v, pq_v; reg [1:0] eg_cr_r;
    reg [2:0] bid_r; reg [1:0] sid_r;
    reg [RG*17-1:0] rq_r; reg [WG*281-1:0] wq_r;
    always @* begin
        rq_r = rq_d; for (integer g = 0; g < RG; g = g + 1) rq_r[g*17 + 16] = rq_v[g];
        wq_r = wq_d; for (integer g = 0; g < WG; g = g + 1) wq_r[g*281 + 280] = wq_v[g];
    end
    wire [280:0] dq_r = {dq_v, dq_d[279:0]}, kq_r = {kq_v, kq_d[279:0]};
    wire [275:0] xq_r = {xq_v, xq_d[274:0]}, x2_r = {x2_v, x2_d[274:0]};
    wire [284:0] pq_r = {pq_v, pq_d[283:0]};
    always @(posedge clk) begin rq_d <= rq; wq_d <= wq; dq_d <= dq; kq_d <= kq; xq_d <= xq; x2_d <= xq2; pq_d <= pq; bid_r <= bid; sid_r <= sid; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rq_v <= '0; wq_v <= '0; dq_v <= 1'b0; kq_v <= 1'b0; xq_v <= 1'b0; x2_v <= 1'b0; pq_v <= 1'b0; eg_cr_r <= 2'b00; end
        else begin
            for (integer g = 0; g < RG; g = g + 1) rq_v[g] <= rq[g*17 + 16];
            for (integer g = 0; g < WG; g = g + 1) wq_v[g] <= wq[g*281 + 280];
            dq_v <= dq[280]; kq_v <= kq[280]; xq_v <= xq[275]; x2_v <= xq2[275]; pq_v <= pq[284]; eg_cr_r <= eg_cr;
        end
    // output registers: control valid + payload
    reg eg_v; reg [274:0] eg_d; reg [RG-1:0] rr_v; reg [RG*256-1:0] rr_d; reg pr_v; reg [264:0] pr_d;
    assign eg = {eg_v, eg_d}; assign pr = {pr_v, pr_d};
    genvar gr;
    for (gr = 0; gr < RG; gr = gr + 1) begin : g_rr
        assign rr[gr*257 +: 257] = {rr_v[gr], rr_d[gr*256 +: 256]};
    end

    // ------------------------------------------------------------------ queues
    // write-queue entry {bad, rowm 11, data 256, wmask 8} = 276 b
    localparam integer NWQ = WG + 4;              // writers in the round robin: WG lanes, kq, xq, packet (index WG+2), xq2
    // per-lane depths (credits) and the deepest one (array size); pointers wrap at the lane's own depth
    function automatic integer rlq(input integer g); rlq = 4 + 2 * RRS[g*4 +: 4] - (MUT == 2 ? 1 : 0); endfunction
    function automatic integer wlq(input integer g); wlq = 4 + 2 * WRS[g*4 +: 4] - (MUT == 2 ? 1 : 0); endfunction
    function automatic integer lqmax(input integer dummy);
        lqmax = 1;
        for (integer g = 0; g < RG; g = g + 1) if (4 + 2 * RRS[g*4 +: 4] > lqmax) lqmax = 4 + 2 * RRS[g*4 +: 4];
        for (integer g = 0; g < WG; g = g + 1) if (4 + 2 * WRS[g*4 +: 4] > lqmax) lqmax = 4 + 2 * WRS[g*4 +: 4];
    endfunction
    localparam integer LQ = lqmax(0);
    localparam integer LQB = (LQ > 1) ? $clog2(LQ) : 1, KQB = (KQD > 1) ? $clog2(KQD) : 1, XQB = (XQD > 1) ? $clog2(XQD) : 1;
    localparam integer PQB = (PQ > 1) ? $clog2(PQ) : 1;
    reg [275:0] wqm [0:WG-1][0:LQ-1]; reg [LQB-1:0] wqh [0:WG-1], wqt [0:WG-1]; reg [LQB:0] wqn [0:WG-1];
    reg [11:0]  rqm [0:RG-1][0:LQ-1]; reg [LQB-1:0] rqh [0:RG-1], rqt [0:RG-1]; reg [LQB:0] rqn [0:RG-1];
    reg [275:0] kqm [0:KQD-1]; reg [KQB-1:0] kqh, kqt; reg [KQB:0] kqn;
    reg [275:0] xqm [0:XQD-1]; reg [XQB-1:0] xqh, xqt; reg [XQB:0] xqn;
    reg [275:0] x2m [0:XQD-1]; reg [XQB-1:0] x2h, x2t; reg [XQB:0] x2n;
    reg [284:0] pqm [0:PQ-1];  reg [PQB-1:0] pqh, pqt; reg [PQB:0] pqn;   // entry = pq with bit 284 (v) := bad (0: the hub decodes)

    // heads
    reg [NWQ-1:0] w_req; reg [275:0] w_head [0:NWQ-1]; reg [WG-1:0] w_mir;
    reg [RG:0] r_req;                                  // RG lanes, packet read (index RG)
    reg [11:0] r_head [0:RG];
    reg [284:0] p_head;
    reg [3:0] egc [0:1];                               // egress credits held (CW stop, CCW stop)
    always @* begin
        for (integer g = 0; g < WG; g = g + 1) begin
            w_head[g] = wqm[g][wqh[g]];
            w_mir[g]  = w_head[g][274];
            w_req[g]  = (wqn[g] != 0) && (!w_mir[g] || (egc[0] != 4'd0 && egc[1] != 4'd0) || MUT == 1);
        end
        w_head[WG]   = kqm[kqh]; w_req[WG]   = kqn != 0;
        w_head[WG+1] = xqm[xqh]; w_req[WG+1] = xqn != 0;
        p_head = pqm[pqh];
        w_head[WG+2] = {p_head[284], p_head[282:16] /* rowm, data */, p_head[15:8] /* wmask */};
        w_req[WG+2]  = (pqn != 0) && p_head[283];
        w_head[WG+3] = x2m[x2h]; w_req[WG+3] = x2n != 0;
        for (integer g = 0; g < RG; g = g + 1) begin r_head[g] = rqm[g][rqh[g]]; r_req[g] = rqn[g] != 0; end
        r_head[RG] = {p_head[284], p_head[282:272]}; r_req[RG] = (pqn != 0) && !p_head[283];
    end
    // round-robin pick (lowest index at or after the pointer)
    reg [3:0] wptr, rptr; reg w_any, r_any; reg [3:0] w_sel, r_sel; reg dma_v;
    always @* begin
        dma_v = dq_r[280];
        w_any = 1'b0; w_sel = 4'd0;
        for (integer k = 2 * NWQ - 1; k >= 0; k = k - 1)
            if (k >= wptr && w_req[k % NWQ]) begin w_any = 1'b1; w_sel = 4'(k % NWQ); end
        r_any = 1'b0; r_sel = 4'd0;
        for (integer k = 2 * (RG + 1) - 1; k >= 0; k = k - 1)
            if (k >= rptr && r_req[k % (RG + 1)]) begin r_any = 1'b1; r_sel = 4'(k % (RG + 1)); end
    end
    wire w_gnt = w_any && !dma_v;                       // a queued writer is granted (DMA owns the port this cycle)
    wire [NWQ-1:0] w_pop = w_gnt ? (NWQ'(1) << w_sel) : '0;
    wire [RG:0]    r_pop = r_any ? ((RG+1)'(1) << r_sel) : '0;
    wire p_pop = w_pop[WG+2] | r_pop[RG];

    // ------------------------------------------------------------------ S1: granted ops
    // write: {v, port 4 (0..WG-1 lanes, WG kq, WG+1 xq, WG+2 pkt, 15 dma), rowm 11, data 256, wmask 8, tag 8}
    reg s1w_v; reg [3:0] s1w_p; reg [10:0] s1w_row; reg [255:0] s1w_d; reg [7:0] s1w_m; reg [7:0] s1w_tag;
    reg s1r_v; reg [3:0] s1r_p; reg [10:0] s1r_row; reg [7:0] s1r_tag;
    reg flt;
    // write-grant egress (a granted client mirror write is copied to both ring stops)
    wire [275:0] wgh = w_head[w_sel];
    wire egv = !dma_v && w_gnt && w_sel < 4'(WG) && wgh[274] && MUT != 1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            s1w_v <= 1'b0; s1r_v <= 1'b0; wptr <= 4'd0; rptr <= 4'd0; flt <= 1'b0; egc[0] <= 4'(EGC); egc[1] <= 4'(EGC); eg_v <= 1'b0;
            rq_cr <= '0; wq_cr <= '0; kq_cr <= 1'b0; xq_cr <= 1'b0; xq2_cr <= 1'b0; pq_cr <= 1'b0;
            for (integer g = 0; g < WG; g = g + 1) begin wqh[g] <= '0; wqt[g] <= '0; wqn[g] <= '0; end
            for (integer g = 0; g < RG; g = g + 1) begin rqh[g] <= '0; rqt[g] <= '0; rqn[g] <= '0; end
            kqh <= '0; kqt <= '0; kqn <= '0; xqh <= '0; xqt <= '0; xqn <= '0; x2h <= '0; x2t <= '0; x2n <= '0; pqh <= '0; pqt <= '0; pqn <= '0;
        end else begin : seq
            reg [11:0] dd;
            // queue pointers (the entries are written by the payload block below; decode at push)
            for (integer g = 0; g < WG; g = g + 1) begin
                if (wq_r[g*281 + 280]) begin
                    wqt[g] <= (wqt[g] == LQB'(wlq(g) - 1)) ? '0 : wqt[g] + 1'b1;
                    if (wqn[g] == (LQB+1)'(wlq(g)) && !w_pop[g]) flt <= 1'b1;    // client exceeded its credits
                end
                wqn[g] <= wqn[g] + (wq_r[g*281 + 280] ? 1 : 0) - (w_pop[g] ? 1 : 0);
                if (w_pop[g]) wqh[g] <= (wqh[g] == LQB'(wlq(g) - 1)) ? '0 : wqh[g] + 1'b1;
            end
            for (integer g = 0; g < RG; g = g + 1) begin
                if (rq_r[g*17 + 16]) begin
                    rqt[g] <= (rqt[g] == LQB'(rlq(g) - 1)) ? '0 : rqt[g] + 1'b1;
                    if (rqn[g] == (LQB+1)'(rlq(g)) && !r_pop[g]) flt <= 1'b1;
                end
                rqn[g] <= rqn[g] + (rq_r[g*17 + 16] ? 1 : 0) - (r_pop[g] ? 1 : 0);
                if (r_pop[g]) rqh[g] <= (rqh[g] == LQB'(rlq(g) - 1)) ? '0 : rqh[g] + 1'b1;
            end
            if (kq_r[280]) begin kqt <= kqt + 1'b1; if (kqn == (KQB+1)'(KQD) && !w_pop[WG]) flt <= 1'b1; end
            kqn <= kqn + (kq_r[280] ? 1 : 0) - (w_pop[WG] ? 1 : 0); if (w_pop[WG]) kqh <= kqh + 1'b1;
            if (xq_r[275]) begin xqt <= xqt + 1'b1; if (xqn == (XQB+1)'(XQD) && !w_pop[WG+1]) flt <= 1'b1; end
            xqn <= xqn + (xq_r[275] ? 1 : 0) - (w_pop[WG+1] ? 1 : 0); if (w_pop[WG+1]) xqh <= xqh + 1'b1;
            if (x2_r[275]) begin x2t <= x2t + 1'b1; if (x2n == (XQB+1)'(XQD) && !w_pop[WG+3]) flt <= 1'b1; end
            x2n <= x2n + (x2_r[275] ? 1 : 0) - (w_pop[WG+3] ? 1 : 0); if (w_pop[WG+3]) x2h <= x2h + 1'b1;
            if (pq_r[284]) begin pqt <= pqt + 1'b1; if (pqn == (PQB+1)'(PQ) && !p_pop) flt <= 1'b1; end
            pqn <= pqn + (pq_r[284] ? 1 : 0) - (p_pop ? 1 : 0); if (p_pop) pqh <= pqh + 1'b1;
            // credits (a pulse per pop)
            for (integer g = 0; g < WG; g = g + 1) wq_cr[g] <= w_pop[g];
            for (integer g = 0; g < RG; g = g + 1) rq_cr[g] <= r_pop[g];
            kq_cr <= w_pop[WG]; xq_cr <= w_pop[WG+1]; pq_cr <= p_pop; xq2_cr <= w_pop[WG+3];
            // write grant
            s1w_v <= dma_v || w_gnt;
            if (dma_v) begin dd = dsec(dq_r[264 +: 16], bid_r, sid_r); if (dd[11]) flt <= 1'b1; end
            else if (w_gnt) begin
                if (wgh[275]) flt <= 1'b1;
                wptr <= (w_sel + 4'd1 == 4'(NWQ)) ? 4'd0 : w_sel + 4'd1;
            end
            eg_v <= egv;
            for (integer d = 0; d < 2; d = d + 1) egc[d] <= egc[d] - (egv ? 4'd1 : 4'd0) + (eg_cr_r[d] ? 4'd1 : 4'd0);
            // read grant
            s1r_v <= r_any;
            if (r_any) begin
                if (r_head[r_sel][11]) flt <= 1'b1;
                rptr <= (r_sel + 4'd1 == 4'(RG + 1)) ? 4'd0 : r_sel + 4'd1;
            end
        end
    always @(posedge clk) begin : s1d
        reg [11:0] dd;
        // entries at or above a lane's own depth are never written (constant-false enable): a shallow lane (WRS 0: the SW
        // slice's in-parent COLL group) carries only its own 4 entries, not the array's LQ.  Defaults: every lane LQ deep.
        for (integer g = 0; g < WG; g = g + 1)
            if (wq_r[g*281 + 280]) begin
                dd = dsec(wq_r[g*281 + 264 +: 16], bid_r, sid_r);
                for (integer e = 0; e < LQ; e = e + 1) if (e < wlq(g) && wqt[g] == LQB'(e)) wqm[g][e] <= {dd, wq_r[g*281 +: 264]};
            end
        for (integer g = 0; g < RG; g = g + 1)
            if (rq_r[g*17 + 16])
                for (integer e = 0; e < LQ; e = e + 1) if (e < rlq(g) && rqt[g] == LQB'(e)) rqm[g][e] <= dsec(rq_r[g*17 +: 16], bid_r, sid_r);
        if (kq_r[280]) kqm[kqt] <= {dsec(kq_r[264 +: 16], bid_r, sid_r), kq_r[263:0]};
        if (xq_r[275]) xqm[xqt] <= {1'b0, xq_r[274:0]};
        if (x2_r[275]) x2m[x2t] <= {1'b0, x2_r[274:0]};
        if (pq_r[284]) pqm[pqt] <= {1'b0, pq_r[283:0]};
        if (dma_v) begin
            dd = dsec(dq_r[264 +: 16], bid_r, sid_r);
            s1w_p <= 4'd15; s1w_row <= dd[10:0]; s1w_d <= dq_r[263:8]; s1w_m <= dd[11] ? 8'd0 : dq_r[7:0];
        end else begin
            s1w_p <= w_sel; s1w_row <= wgh[274:264]; s1w_d <= wgh[263:8]; s1w_m <= wgh[275] ? 8'd0 : wgh[7:0];
        end
        s1w_tag <= p_head[7:0];
        eg_d <= wgh[274:0];
        s1r_p <= r_sel; s1r_row <= r_head[r_sel][10:0]; s1r_tag <= p_head[7:0];
    end

    // ------------------------------------------------------------------ S2: macro pins
    reg [9:0] m_ra, m_wa; reg m_rA, m_rC, m_rB, m_wA, m_wB, m_wC; reg [311:0] m_wd; reg [7:0] m_mA, m_mC; reg [15:0] m_mB;
    reg s2r_v; reg [3:0] s2r_p; reg s2r_mir; reg [7:0] s2r_tag;
    reg s2w_v; reg [3:0] s2w_p; reg [7:0] s2w_tag;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin m_rA <= 1'b0; m_rB <= 1'b0; m_rC <= 1'b0; m_wA <= 1'b0; m_wB <= 1'b0; m_wC <= 1'b0; s2r_v <= 1'b0; s2w_v <= 1'b0; end
        else begin
            m_rA <= s1r_v && !s1r_row[10]; m_rC <= s1r_v && s1r_row[10]; m_rB <= s1r_v;
            m_wA <= s1w_v && !s1w_row[10]; m_wC <= s1w_v && s1w_row[10]; m_wB <= s1w_v;
            s2r_v <= s1r_v; s2w_v <= s1w_v;
        end
    always @(posedge clk) begin
        m_ra <= s1r_row[9:0]; m_wa <= s1w_row[9:0];
        m_wd <= enc8(s1w_d);
        m_mA <= s1w_row[10] ? 8'd0 : s1w_m; m_mC <= s1w_row[10] ? s1w_m : 8'd0;
        m_mB <= s1w_row[10] ? {s1w_m, 8'd0} : {8'd0, s1w_m};
        s2r_p <= s1r_p; s2r_mir <= s1r_row[10]; s2r_tag <= s1r_tag;
        s2w_p <= s1w_p; s2w_tag <= s1w_tag;
    end
    // mask expansion is wiring only (each word-mask flop drives its 39 bit-mask pins)
    wire [255:0] mskA, mskC, mskB;
    genvar gk;
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_m
        assign mskA[gk*32 +: 32] = {32{m_mA[gk]}};
        assign mskC[gk*32 +: 32] = {32{m_mC[gk]}};
    end
    // B holds the check bits: main word k -> B[k*7 +: 7], mirror word k -> B[56 + k*7 +: 7]
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_mb
        assign mskB[gk*7 +: 7]      = {7{m_mB[gk]}};
        assign mskB[56 + gk*7 +: 7] = {7{m_mB[8 + gk]}};
    end
    assign mskB[255:112] = '0;
    // data / check split: word k = {chk 7, data 32} at m_wd[k*39 +: 39]
    wire [255:0] wdat; wire [55:0] wchk;
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_sp
        assign wdat[gk*32 +: 32] = m_wd[gk*39 +: 32];
        assign wchk[gk*7 +: 7]   = m_wd[gk*39 + 32 +: 7];
    end
    wire [255:0] rdA, rdB, rdC;
    ot_sram_1r1w_1024x256_m2_r2c2 u_a (.clk(clk), .r_ce_in(m_rA), .r_addr_in(m_ra), .rd_out(rdA),
        .w_ce_in(m_wA), .w_addr_in(m_wa), .wd_in(wdat), .w_mask_in(mskA), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_1024x256_m2_r2c2 u_b (.clk(clk), .r_ce_in(m_rB), .r_addr_in(m_ra), .rd_out(rdB),
        .w_ce_in(m_wB), .w_addr_in(m_wa), .wd_in({144'd0, wchk, wchk}), .w_mask_in(mskB), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_1024x256_m2_r2c2 u_c (.clk(clk), .r_ce_in(m_rC), .r_addr_in(m_ra), .rd_out(rdC),
        .w_ce_in(m_wC), .w_addr_in(m_wa), .wd_in(wdat), .w_mask_in(mskC), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));

    // ------------------------------------------------------------------ M (macro edge) -> C (capture) -> D -> R
    reg mr_v; reg [3:0] mr_p; reg mr_mir; reg [7:0] mr_tag; reg mw_v; reg [3:0] mw_p; reg [7:0] mw_tag;
    reg c_v; reg [3:0] c_p; reg c_mir; reg [7:0] c_tag; reg [255:0] c_a, c_c; reg [111:0] c_b; reg cw_v; reg [3:0] cw_p; reg [7:0] cw_tag;
    reg d_v; reg [3:0] d_p; reg [7:0] d_tag; reg [255:0] d_dat; reg [55:0] d_syn; reg dw_v; reg [3:0] dw_p; reg [7:0] dw_tag;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            mr_v <= 1'b0; mw_v <= 1'b0; c_v <= 1'b0; cw_v <= 1'b0; d_v <= 1'b0; dw_v <= 1'b0;
            wq_done <= '0; dq_done <= 1'b0; kq_done <= 1'b0; xq_done <= 1'b0; xq2_done <= 1'b0;
        end else begin
            mr_v <= s2r_v; mw_v <= s2w_v;
            // done = the write is in the macro (this edge wrote it)
            for (integer g = 0; g < WG; g = g + 1) wq_done[g] <= s2w_v && s2w_p == 4'(g);
            dq_done <= s2w_v && s2w_p == 4'd15; kq_done <= s2w_v && s2w_p == 4'(WG); xq_done <= s2w_v && s2w_p == 4'(WG + 1);
            xq2_done <= s2w_v && s2w_p == 4'(WG + 3);
            c_v <= mr_v; cw_v <= mw_v && mw_p == 4'(WG + 2);
            d_v <= c_v; dw_v <= cw_v;
        end
    // capture flops: the only load of the macro outputs (no enable, no reset)
    always @(posedge clk) begin : mcd
        reg [255:0] dat; reg [55:0] ck;
        mr_p <= s2r_p; mr_mir <= s2r_mir; mr_tag <= s2r_tag; mw_p <= s2w_p; mw_tag <= s2w_tag;
        c_p <= mr_p; c_mir <= mr_mir; c_tag <= mr_tag; c_a <= rdA; c_b <= rdB[111:0]; c_c <= rdC; cw_tag <= mw_tag;
        d_p <= c_p; d_tag <= c_tag; dw_tag <= cw_tag;
        dat = c_mir ? c_c : c_a; ck = c_mir ? c_b[111:56] : c_b[55:0];
        d_dat <= dat;
        for (integer k = 0; k < 8; k = k + 1) d_syn[k*7 +: 7] <= chk(dat[k*32 +: 32]) ^ ck[k*7 +: 7];
    end
    // R: correct, count, respond
    reg [255:0] cor; reg [3:0] nce; reg nue;
    always @* begin
        cor = d_dat; nce = 4'd0; nue = 1'b0;
        for (integer k = 0; k < 8; k = k + 1) begin : wk
            reg [6:0] s; reg hit; s = d_syn[k*7 +: 7]; hit = 1'b0;
            if (s != 7'd0) begin
                for (integer i = 0; i < 32; i = i + 1) if (s == COLS[i*7 +: 7]) begin cor[k*32 + i] = ~cor[k*32 + i]; hit = 1'b1; end
                if (s == 7'd1 || s == 7'd2 || s == 7'd4 || s == 7'd8 || s == 7'd16 || s == 7'd32 || s == 7'd64) hit = 1'b1;
                if (hit) nce = nce + 4'd1; else nue = 1'b1;
            end
        end
    end
    reg [15:0] ce; reg ue;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rr_v <= '0; pr_v <= 1'b0; ce <= 16'd0; ue <= 1'b0; status <= 18'd0; end
        else begin
            for (integer g = 0; g < RG; g = g + 1) rr_v[g] <= d_v && d_p == 4'(g);
            // a packet read (d_p == RG) and a packet write echo are never on the same edge (one packet op a cycle)
            pr_v <= (d_v && d_p == 4'(RG)) || dw_v;
            if (d_v) begin
                ce <= (ce + {12'd0, nce} < ce) ? 16'hffff : ce + {12'd0, nce};
                if (nue) ue <= 1'b1;
            end
            status <= {flt, ue, ce};
        end
    always @(posedge clk) begin
        for (integer g = 0; g < RG; g = g + 1) rr_d[g*256 +: 256] <= cor;
        pr_d <= (d_v && d_p == 4'(RG)) ? {1'b0, d_tag, cor} : {1'b1, dw_tag, 256'd0};
    end
endmodule
`default_nettype wire
