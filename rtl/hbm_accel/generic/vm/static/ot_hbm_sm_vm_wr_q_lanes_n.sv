`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// ot_hbm_sm_vm_wr_q_lanes_n (HBM-B-RTL1 2026-10-17, plan (b) d4g): ot_hbm_sm_vm_wr_q_lanes with NL SM lanes and a bank
// base LB.  Lane k (SM k of the writer) writes VM bank LB+k of quadrant `quad` (sector field {mir, quad, row10, bank3}).
// NL=8, LB=0 is ot_hbm_sm_vm_wr_q_lanes (d4f smw_<stack>, SM k -> bank k), statement for statement.  Plan (b): one writer per
// QUADRANT with its 4 SMs: W quadrant NL=4 LB=0 (SMs 0-3 of the stack -> banks 0-3), E quadrant NL=4 LB=4 (SMs 4-7 ->
// banks 4-7 of the E quadrant's OWN slice: same bank index as d4f, the quadrant strap now names the SM's own quadrant).
// The writer hub (cv_q/cmd_q, busy/fault, reset sync rs2) sits on the centre lane root clk_l[NL/2] (NL=8: clk_l[4], as
// before).  Timing unchanged: rv(t) -> wq slot 0 at t+3, calendar fire edge unchanged (0 edges added).
// NB2 (plan (b) quadrant writer: 2): a quadrant has 8 banks but 4 SMs, so every bank keeps the uniform q0 shape (its SM
// write group wq1 always driven) and lane k drives TWO banks: half 0 = bank LB+k, half 1 = bank (LB+k+4)%8, selected per
// writer descriptor by cmd[26] (the compiler's static choice per op; 2 banks = 2 x 1024 rows of VM per SM).  Each half
// has its own launch flops (flop-first output pins); both halves carry the same data/row/mask every edge, valid only on
// the selected half.  NB2 1 leaves the cmd 26 bits and one wq port per lane.
// MUT: 1/2/3 as ot_hbm_sm_vm_wr_q_lanes; 6 = bank base ignored (lane k writes bank k / k+4).
// Original header (unchanged behaviour):
// =====================================================================================================================
// ot_hbm_sm_vm_wr_q_lanes (H-WRQ 2026-10-17): the STATIC SM result -> VM writer of ot_hbm_sm_vm_wr_q_faces4 with ONE
// CLOCK ROOT PER SM LANE.  Behaviour, timing contract, address contract, descriptor ABI, faults and MUT 1/2/3 are those of
// ot_hbm_sm_vm_wr_q_faces4 / ot_hbm_sm_vm_wr_q (see the header there); only the clock partition differs:
//   clk_l[k] clocks EVERYTHING of SM lane k: its W pin flops (rv/rrow/rdata/sm_fault/sm_sched_fault), its DEPTH-row FIFO,
//            its serial server (wp/rp/cnt/ps/acc/flt), its wq launch flops (o_* with one o_wr copy per wq data pin) and a lane
//            copy of the descriptor (d_*: same reset, same update on cv_q as the shared copy it replaces).
//   clk_l[4] also clocks the writer hub (cv_q/cmd_q, cmd_fault, busy, fault, reset sync rs2) at the lane-column centre.
//   clk      the quad strap pin flop (the calendar and the other N-face pins live in the wrapper on the same root).
// Why (results/rtl/hsm_wrq_1017/DESIGN_NOTE.md): faces4 put the pin flops on face roots and the 8.6k FIFO flops on the
// core root, so every wide data path crossed clock entries (210 ps setup / 100 ps hold die-skew reserve each): f4hc TT
// -46.5 (rp -> o_w), ~32k hold buffers.  Here every wide path is inside one lane root; the only cross-entry signals are
// the quasi-static descriptor (hub -> lane), quad_q (core -> o_sec), the busy / fault OR terms (lane -> hub) and
// cmd/cmd_v, busy/fault between the calendar (core) and the hub.
// All roots are the same PLL output at phase 0 (benches tie them to one clock): zero edges added, rv(t) -> wq at t+3.
// =====================================================================================================================
module ot_hbm_sm_vm_wr_q_lanes_n #(
    parameter integer DEPTH = 4,
    parameter integer NL    = 8,     // SM lanes (plan (b) quadrant writer: 4)
    parameter integer LB    = 0,     // bank base: lane k writes bank LB+k (half 0)
    parameter integer LBPIN = 0,     // 1: the bank base is the strap pin lbase (0 -> LB 0, 1 -> LB 4; one master for W and E)
    parameter integer NB2   = 1,     // 2: each lane also drives bank (LB+k+4)%8 (half 1), chosen per descriptor by cmd[26]
    parameter integer MUT   = 0      // 1 wrong row (stride ignored), 2 wrong phase (one edge late), 3 quad strap ignored, 6 bank base ignored
) (
    input  wire          clk,               // shared core root
    input  wire [NL-1:0] clk_l,             // lane k root (SM k)
    input  wire          rst_n,
    input  wire [1:0]    quad,
    input  wire          lbase,             // LBPIN 1: bank-base strap (die constant; pin flop on the core root)
    input  wire [NL-1:0] rv,
    input  wire [12*NL-1:0]  rrow,
    input  wire [256*NL-1:0] rdata,
    input  wire          cmd_v,
    input  wire [25+NB2-1:0] cmd,
    input  wire [NL-1:0] sm_fault,
    input  wire [NL-1:0] sm_sched_fault,
    output wire [NB2*281*NL-1:0] wq,
    output reg           busy,
    output reg           fault
);
    initial if (DEPTH < 1 || DEPTH > 16) $fatal(1, "ot_hbm_sm_vm_wr_q_lanes_n: DEPTH 1..16");
    initial if (NL < 1 || NL > 8 || LB < 0 || LB + NL > 8) $fatal(1, "ot_hbm_sm_vm_wr_q_lanes_n: NL 1..8, LB+NL <= 8");
    initial if (NB2 < 1 || NB2 > 2 || (NB2 == 2 && NL > 4)) $fatal(1, "ot_hbm_sm_vm_wr_q_lanes_n: NB2 1..2, NB2 2 needs NL <= 4");
    localparam integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    function automatic [31:0] rb(input [31:0] x, input en);     // to_bf16 (RNE) as a BF16-valued FP32 word
        reg [31:0] r;
        begin
            if (!en) rb = x;
            else if (x[30:23] == 8'hFF && x[22:0] != 0) rb = {x[31:16] | 16'h0040, 16'd0};
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; rb = {r[31:16], 16'd0}; end
        end
    endfunction
    // ---------------- writer hub on the CENTRE lane root (clk_l[4]) ----------------
    // The descriptor register (cv_q/cmd_q) fans out to all 8 lanes and busy/fault/cmd_fault collect all 8 lanes, so
    // placement puts them at the lane-column centroid (r5 gate d2d62741a: 14 such core flops at y 160-280 stretched the
    // core tree to TT 193-253 at the N-face pin flops).  They are clocked by the centre lane's root, which they sit inside;
    // the core root keeps only the calendar and the N-face pins.  Same edges: cmd/cmd_v are registered once here as before.
    // Reset: wrapper rst_q (core pin flop) -> rs2 (here) is the 2-flop sync; hub flops clear synchronously from rs2;
    // every lane takes one registered relay rl of rs2 (regional synchronous reset, die standard item 2).
    wire hclk = clk_l[NL/2];
    reg rs2;
    always @(posedge hclk) rs2 <= rst_n;
    reg [1:0] quad_q;                                   // N-face strap pin flop (core root)
    always @(posedge clk) quad_q <= quad;
    reg lb_q;                                           // N-face bank-base strap pin flop (core root)
    always @(posedge clk) lb_q <= lbase;
    wire [2:0] lbv = (LBPIN != 0) ? {lb_q, 2'b00} : 3'(LB);
    reg cv_q; reg [25+NB2-1:0] cmd_q;
    always @(posedge hclk) cmd_q <= cmd;
    always @(posedge hclk) if (!rs2) cv_q <= 1'b0; else cv_q <= cmd_v;
    wire [NL-1:0] rv_q, smf_q, sms_q, sm_busy, lane_fault;
    reg cmd_fault;
    always @(posedge hclk)
        if (!rs2) cmd_fault <= 1'b0;
        else if (cv_q && (busy || (|rv_q) || cmd_q[23:20] == 4'd0 || cmd_q[23:20] > 4'd8)) cmd_fault <= 1'b1;
    always @(posedge hclk)
        if (!rs2) begin busy <= 1'b0; fault <= 1'b0; end
        else begin busy <= |sm_busy || |rv_q; fault <= fault | cmd_fault | (|lane_fault) | (|smf_q) | (|sms_q); end
    // ---------------- lanes ----------------
    genvar k;
    generate for (k = 0; k < NL; k = k + 1) begin : g_sm
        wire lclk = clk_l[k];
        // regional SYNCHRONOUS reset: rl is this lane's ONE registered relay of the hub's rs2 on its own root; every lane
        // flop clears synchronously from it (no async clear crosses into a lane root).  Lanes leave reset one edge after
        // the hub.
        reg rl;
        always @(posedge lclk) rl <= rs2;
        // pin flops (lane root)
        reg rv_r, smf_r, sms_r; reg [11:0] rrow_r; reg [255:0] rdata_r;
        always @(posedge lclk) begin rrow_r <= rrow[12*k +: 12]; rdata_r <= rdata[256*k +: 256]; end
        always @(posedge lclk)
            if (!rl) begin rv_r <= 1'b0; smf_r <= 1'b0; sms_r <= 1'b0; end
            else begin rv_r <= rv[k]; smf_r <= sm_fault[k]; sms_r <= sm_sched_fault[k]; end
        assign rv_q[k] = rv_r; assign smf_q[k] = smf_r; assign sms_q[k] = sms_r;
        // lane copy of the descriptor (identical update rule to the shared copy of ot_hbm_sm_vm_wr_q_faces4)
        reg d_v, d_fmt, d_mir, d_h; reg [3:0] d_p; reg [9:0] d_base, d_stride;
        always @(posedge lclk)
            if (!rl) begin d_v <= 1'b0; d_fmt <= 1'b0; d_mir <= 1'b0; d_h <= 1'b0; d_p <= 4'd0; d_base <= 10'd0; d_stride <= 10'd0; end
            else if (cv_q) begin
                d_v <= 1'b1; d_base <= cmd_q[9:0]; d_stride <= cmd_q[19:10]; d_p <= cmd_q[23:20];
                d_mir <= cmd_q[24]; d_fmt <= cmd_q[25]; d_h <= (NB2 == 2) ? cmd_q[25+NB2-1] : 1'b0;
            end
        // serial server.  Same cnt / ps / acc / flt / emission rule as ot_hbm_sm_vm_wr_q_faces4; the row FIFO is a
        // SHIFT-REGISTER FIFO with a FIXED HEAD (entry 0) whose 256-bit word rotates right by one 32-bit slot on every
        // emission that is not the row's last: the slot word is always ent[0][31:0] (no read pointer, no 4:1 x 268 read mux,
        // no 8:1 slot mux before the BF16 round).  Rotation (not shift) keeps the old col = hd[32*ps[2:0]] wrap for
        // P > 8 (descriptor fault case).  On pop the entries move down one; an accepted row lands at index cnt - pop.
        // f4hc / r5-gate: rp -> fq[rp] -> slot mux -> rb -> o_w was the only intra-root class near 0 (-3.4 ps pre-route).
        wire [267:0] ent [0:DEPTH];                 // entry i = {rrow12, rdata256}, one register per generate scope (g_e)
        assign ent[DEPTH] = 268'd0;
        reg [AW:0] cnt;
        reg [3:0] ps; reg [10:0] acc;
        reg flt;
        // wq launch flops: o_wr = 8 kept copies of the slot word, one launch flop per replicated wq data pin (recipe 4 has no
        // pin_reg_split; physical/common_flow/ot_keep_regs.tcl keeps every bit of a (* keep *) register its own flop)
        reg o_v; reg [15:0] o_sec; reg [7:0] o_m;
        (* keep *) reg [255:0] o_wr;
        reg l_v; reg [15:0] l_sec; reg [255:0] l_wr; reg [7:0] l_m;   // MUT 2 late copy
        // NB2 2: half-1 launch flops (own flop per wq pin of bank (LB+k+4)%8; same data/row/mask, valid only when d_h)
        reg o2_v; reg [15:0] o2_sec; reg [7:0] o2_m; (* keep *) reg [255:0] o2_wr;
        reg l2_v; reg [15:0] l2_sec; reg [255:0] l2_wr; reg [7:0] l2_m;
        wire [267:0] hd = ent[0];
        wire [11:0] hr = hd[267:256];
        wire [10:0] row = (ps == 4'd0 || MUT == 1) ? ({1'b0, d_base} + {2'b0, hr[11:3]}) : acc;
        wire push = rv_r;
        wire full = (cnt == DEPTH[AW:0]);
        wire emit = (cnt != 0);
        // DIE-HBM-61/RTL-C3 RE-FORM (zero latency, 11-03): last and pop come from flops.  ps -> (ps + 1 >= d_p) -> pop ->
        // 4 x 268 FIFO entry selects was the whole-core worst stage (pre-build gate TT -113 ps).  last_r holds
        // (ps + 1 >= d_p) of the CURRENT ps/d_p, computed one edge earlier from their next-state values (the same update
        // rules as the ps / d_p / cnt registers below); pop_e are kept copies of emit && last, one per FIFO entry (+1 for
        // the counters), each <= 268 loads.  Every sampled edge is unchanged.
        wire last;
        wire pop;
        wire acc_row;
        wire [3:0] ps_n  = !rl ? 4'd0 : (emit ? (last ? 4'd0 : ps + 4'd1) : ps);
        wire [3:0] d_p_n = !rl ? 4'd0 : (cv_q ? cmd_q[23:20] : d_p);
        wire [AW:0] cnt_n = !rl ? '0 : cnt + (acc_row ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
`ifdef C3MUT_LASTCUR
        wire last_n = (ps + 4'd1 >= d_p);
`elsif C3MUT_DPN
        wire last_n = (ps_n + 4'd1 >= d_p);
`else
        wire last_n = (ps_n + 4'd1 >= d_p_n);
`endif
        reg last_r, pop_r;
`ifdef C3MUT_CNTN
        wire pop_n = (cnt != 0) && last_n;
`else
        wire pop_n = (cnt_n != 0) && last_n;
`endif
        always @(posedge lclk) begin last_r <= last_n; pop_r <= pop_n; end
        assign last = last_r;
        assign pop = pop_r;
        // entry write selects from flops too (pop -> cnt - pop -> == i -> 268 entry bits was the next stage, TT +67):
        // wsel_e[i] = acc_row && (widx == i) of the NEXT edge, from the next-state values of rv_r / cnt / pop.
        wire rv_n = !rl ? 1'b0 : rv[k];
        wire full_n = (cnt_n == DEPTH[AW:0]);
        wire acc_n = rv_n && !(full_n && !pop_n);
`ifdef C3MUT_WSEL
        wire [AW:0] widx_n = cnt_n;
`else
        wire [AW:0] widx_n = cnt_n - {{AW{1'b0}}, pop_n};
`endif
        // Each 268-bit entry is split in NCH chunks (8 x 32 data + 12 row bits); every chunk has its own kept copy of the
        // write select, the pop shift and (entry 0) the emit rotate, so no select flop drives more than ~64 loads
        // (one wsel copy per entry drove 268 bits x 2 = TT +52).
        localparam integer NCH = 9;
        (* keep *) reg [DEPTH*NCH-1:0] wsel_c, pop_c;
        (* keep *) reg [NCH-1:0] emit_c;
        always @(posedge lclk) begin
            for (integer j = 0; j < DEPTH; j = j + 1)
                for (integer c = 0; c < NCH; c = c + 1) begin
                    wsel_c[j*NCH+c] <= acc_n && (widx_n == (AW+1)'(j));
`ifdef C3MUT_POPE0
                    pop_c[j*NCH+c] <= pop_n && !(j == 0 && c == 3);
`else
                    pop_c[j*NCH+c] <= pop_n;
`endif
                end
`ifdef C3MUT_EMITC
            for (integer c = 0; c < NCH; c = c + 1) emit_c[c] <= (cnt != 0);
`else
            for (integer c = 0; c < NCH; c = c + 1) emit_c[c] <= (cnt_n != 0);
`endif
        end
        wire [31:0] col = hd[31:0];
        assign acc_row = push && !(full && !pop);     // accepted row (write suppressed on overrun)
        wire [AW:0] widx = cnt - {{AW{1'b0}}, pop};
        assign sm_busy[k] = emit || o_v;
        assign lane_fault[k] = flt;
        always @(posedge lclk)
            if (!rl) begin cnt <= '0; ps <= 4'd0; acc <= 11'd0; flt <= 1'b0; end
            else begin
                if (push && !d_v) flt <= 1'b1;
                if (push && full && !pop) flt <= 1'b1;
                cnt <= cnt + (acc_row ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
                if (emit) begin ps <= last ? 4'd0 : ps + 4'd1; acc <= row + {1'b0, d_stride}; end
                if (emit && row[10]) flt <= 1'b1;
            end
        always @(posedge lclk)
            if (!rl) begin o_v <= 1'b0; l_v <= 1'b0; o2_v <= 1'b0; l2_v <= 1'b0; end
            else begin o_v <= emit && !row[10] && !d_h; l_v <= o_v; o2_v <= emit && !row[10] && d_h; l2_v <= o2_v; end
        for (genvar i = 0; i < DEPTH; i = i + 1) begin : g_e
            reg [267:0] q;
            assign ent[i] = q;
            wire [267:0] din = {rrow_r, rdata_r};
            for (genvar c = 0; c < NCH; c = c + 1) begin : g_c
                localparam integer LO = c * 32, CW = (c < 8) ? 32 : 12, RO = ((c + 1) % 8) * 32;
                always @(posedge lclk)
                    if (wsel_c[i*NCH+c]) q[LO +: CW] <= din[LO +: CW];
                    else if (pop_c[i*NCH+c]) begin
                        if (i < DEPTH - 1) q[LO +: CW] <= ent[i + 1][LO +: CW];
                    end else if (i == 0 && c < 8 && emit_c[c]) q[LO +: CW] <= q[RO +: CW];
            end
        end
        always @(posedge lclk) begin
            o_sec <= {d_mir, d_mir ? 2'b00 : ((MUT == 3) ? 2'b00 : quad_q), row[9:0], ((MUT == 6) ? 3'(k) : lbv + 3'(k))};
            o_wr <= {8{rb(col, d_fmt)}};
            o_m <= 8'd1 << hr[2:0];
            l_sec <= o_sec; l_wr <= o_wr; l_m <= o_m;
            o2_sec <= {d_mir, d_mir ? 2'b00 : ((MUT == 3) ? 2'b00 : quad_q), row[9:0], ((MUT == 6) ? 3'(k) : lbv + 3'(k)) + 3'd4};
            o2_wr <= {8{rb(col, d_fmt)}};
            o2_m <= 8'd1 << hr[2:0];
            l2_sec <= o2_sec; l2_wr <= o2_wr; l2_m <= o2_m;
        end
        if (MUT == 2) begin : g_late
            assign wq[k*281 +: 281] = {l_v, l_sec, l_wr, l_m};
        end else begin : g_on
            assign wq[k*281 +: 281] = {o_v, o_sec, o_wr, o_m};
        end
        if (NB2 == 2) begin : g_h1
            if (MUT == 2) begin : g_late2
                assign wq[(NL+k)*281 +: 281] = {l2_v, l2_sec, l2_wr, l2_m};
            end else begin : g_on2
                assign wq[(NL+k)*281 +: 281] = {o2_v, o2_sec, o2_wr, o2_m};
            end
        end
    end endgenerate
endmodule
`default_nettype wire
