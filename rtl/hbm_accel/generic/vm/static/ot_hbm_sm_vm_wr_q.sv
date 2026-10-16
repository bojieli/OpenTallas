`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// ot_hbm_sm_vm_wr_q (H-NETLIST/smvm 2026-10-16): STATIC SM result -> VM writer of one quadrant (decision 23:21: SM
// results write the VM directly; plan link SM_OUT sm_<q>k -> vmh_<q>). One parameterised master, 4 instances.
//
// Inputs: the 8 SMs' existing result ports (rv / rrow[11:0] / rdata = 8 x FP32, column p = slot p; no ready) and one
// per-op descriptor command (cmd_v/cmd, from the compiler command calendar ot_static_cmd_target MODE 1, TARGET 136+QID).
// Output: ONE VM wide write group wq[8 x 281] (bank b lane = {v, sector16, data256, mask8}, the ot_vms_bank_static ABI).
//
// Address contract (fixed, no arbitration): SM k writes ONLY bank k.  Result (SM k, row r, slot p < P) is the FP32 word
//     VM word  W = 64*(base_row + p*stride_row + r[11:3]) + 8*k + r[2:0]
//     sector   = {mirror, mirror ? 2'b00 : quad, row10 = base_row + p*stride_row + r[11:3], bank3 = k}, lane r[2:0]
// i.e. the compiler interleaves output rows over the 8 SMs in blocks of 8 (global row g -> SM g[5:3], r = {g>>6, g[2:0]}),
// so every slot vector is contiguous in VM (the x-load reads it as base + p*stride + i) and no two SMs ever share a bank.
// One masked single-word write per (row, slot): data = the word replicated on all 8 lanes, mask = 1 << r[2:0].
// fmt=1 rounds each word to BF16 (RNE, NaN quieted; the golden to_bf16 of ot_hgi_sm_pub) stored as a BF16-valued FP32 word.
// mirror=1 writes the mirror window (bank egress to the ring: LM-head logits reach the SW slice from any quadrant).
//
// Descriptor cmd[25:0] = {fmt, mirror, P[3:0] (1..8), stride_row[9:0], base_row[9:0]}.  It is latched at its pin edge and
// applies to every emission until the next cmd_v; the compiler fires the next descriptor only while busy == 0
// (a descriptor while busy is a sticky FAULT, never a reorder).
//
// Fixed timing (edges after the SM's rv cycle t):  t+1 pin capture, t+2 row FIFO, t+3 wq pin register (slot 0);
// slot p of that row leaves at t+3+p.  Per SM the writer is a serial server of P cycles per row: a row arriving while
// earlier rows still emit waits in a DEPTH-row FIFO; its emissions start at max(t+3, previous row end).  All times are
// compiler-known (SM rv cycles are fixed by the SM programme), so the VM calendar (hfd_hgi_vm_calendar_<q>) reserves
// wslot_v[k]=1 / wslot[k]=GROUP on exactly those cycles: one write owner per bank per cycle by construction.
// No ready, no credit, no stall: FIFO overrun, rv without descriptor, row overflow (>1023) and P=0/P>8 are sticky FAULTs
// (the faulting write is suppressed, never deferred).  Every input and output is registered at its pin.
// Status: the quadrant's 8 SM fault / schedule_fault outputs land in pin flops and join the sticky `fault` (2 edges), which
// reaches the host status join through the descriptor target's tgt_fault (no separate OR tile; participation per target).
// =====================================================================================================================
module ot_hbm_sm_vm_wr_q #(
    parameter integer DEPTH = 4,     // rows buffered per SM (the SM retires SUB=4 rows back to back)
    parameter integer MUT   = 0      // bench mutants: 1 wrong row (stride ignored), 2 wrong phase (one edge late), 3 quad strap ignored
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    quad,              // die strap (H-SM DEDUPE 2026-10-16, was parameter QUAD): quadrant id carried in
                                            // non-mirror sectors (SW0 SE1 NW2 NE3); one hardened master for all 4 instances
    input  wire [7:0]    rv,
    input  wire [95:0]   rrow,
    input  wire [2047:0] rdata,
    input  wire          cmd_v,
    input  wire [25:0]   cmd,
    input  wire [7:0]    sm_fault,          // the 8 SMs' sticky result faults (status only)
    input  wire [7:0]    sm_sched_fault,    // the 8 SMs' static-schedule faults (status only)
    output wire [2247:0] wq,
    output reg           busy,
    output reg           fault
);
    initial if (DEPTH < 1 || DEPTH > 16) $fatal(1, "ot_hbm_sm_vm_wr_q: DEPTH 1..16");
    localparam integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    function automatic [31:0] rb(input [31:0] x, input en);     // to_bf16 (RNE) as a BF16-valued FP32 word
        reg [31:0] r;
        begin
            if (!en) rb = x;
            else if (x[30:23] == 8'hFF && x[22:0] != 0) rb = {x[31:16] | 16'h0040, 16'd0};
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; rb = {r[31:16], 16'd0}; end
        end
    endfunction
    // ---------------- local reset release at the rst_n pin (H-SM 2026-10-16, native capture rule): rst_n lands on ONE
    // async-clear flop at the pin face (assert async, release synchronous, one edge later); every other flop clears
    // from rst_q (reg->recovery inside the tile).  No operation edge changes.
    reg rst_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_q <= 1'b0; else rst_q <= 1'b1;
    // ---------------- pin flops ----------------
    reg [7:0] rv_q; reg [95:0] rrow_q; reg [2047:0] rdata_q;
    reg cv_q; reg [25:0] cmd_q; reg [7:0] smf_q, sms_q; reg [1:0] quad_q;
    always @(posedge clk) begin rrow_q <= rrow; rdata_q <= rdata; cmd_q <= cmd; quad_q <= quad; end
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin rv_q <= 8'd0; cv_q <= 1'b0; smf_q <= 8'd0; sms_q <= 8'd0; end
        else begin rv_q <= rv; cv_q <= cmd_v; smf_q <= sm_fault; sms_q <= sm_sched_fault; end
    // ---------------- descriptor ----------------
    reg d_v, d_fmt, d_mir; reg [3:0] d_p; reg [9:0] d_base, d_stride;
    wire [7:0] sm_busy, lane_fault;
    reg cmd_fault;
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin d_v <= 1'b0; d_fmt <= 1'b0; d_mir <= 1'b0; d_p <= 4'd0; d_base <= 10'd0; d_stride <= 10'd0; cmd_fault <= 1'b0; end
        else if (cv_q) begin
            if (busy || (|rv_q) || cmd_q[23:20] == 4'd0 || cmd_q[23:20] > 4'd8) cmd_fault <= 1'b1;
            d_v <= 1'b1; d_base <= cmd_q[9:0]; d_stride <= cmd_q[19:10]; d_p <= cmd_q[23:20];
            d_mir <= cmd_q[24]; d_fmt <= cmd_q[25];
        end
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin busy <= 1'b0; fault <= 1'b0; end
        else begin busy <= |sm_busy || |rv_q; fault <= fault | cmd_fault | (|lane_fault) | (|smf_q) | (|sms_q); end
    // ---------------- per-SM serial servers (statically indexed) ----------------
    genvar k;
    generate for (k = 0; k < 8; k = k + 1) begin : g_sm
        reg [267:0] fq [0:DEPTH-1];                 // {rrow12, rdata256}
        reg [AW-1:0] wp, rp; reg [AW:0] cnt;
        reg [3:0] ps; reg [10:0] acc;
        reg flt;
        reg o_v; reg [15:0] o_sec; reg [31:0] o_w; reg [7:0] o_m;
        reg l_v; reg [15:0] l_sec; reg [31:0] l_w; reg [7:0] l_m;   // MUT 2 late copy
        wire [267:0] hd = fq[rp];
        wire [11:0] hr = hd[267:256];
        wire [10:0] row = (ps == 4'd0 || MUT == 1) ? ({1'b0, d_base} + {2'b0, hr[11:3]}) : acc;
        wire push = rv_q[k];
        wire full = (cnt == DEPTH[AW:0]);
        wire emit = (cnt != 0);
        wire last = (ps + 4'd1 >= d_p);
        wire pop = emit && last;
        wire [31:0] col = hd[32*ps[2:0] +: 32];
        assign sm_busy[k] = emit || o_v;
        assign lane_fault[k] = flt;
        always @(posedge clk or negedge rst_q)
            if (!rst_q) begin wp <= '0; rp <= '0; cnt <= '0; ps <= 4'd0; acc <= 11'd0; flt <= 1'b0; o_v <= 1'b0; l_v <= 1'b0; end
            else begin
                if (push && !d_v) flt <= 1'b1;
                if (push && full && !pop) flt <= 1'b1;
                else if (push) wp <= (wp == AW'(DEPTH-1)) ? '0 : wp + 1'b1;
                if (pop) rp <= (rp == AW'(DEPTH-1)) ? '0 : rp + 1'b1;
                cnt <= cnt + ((push && !(full && !pop)) ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
                if (emit) begin ps <= last ? 4'd0 : ps + 4'd1; acc <= row + {1'b0, d_stride}; end
                o_v <= emit && !row[10];
                if (emit && row[10]) flt <= 1'b1;
                l_v <= o_v;
            end
        always @(posedge clk) begin
            if (push && !(full && !pop)) fq[wp] <= {rrow_q[12*k +: 12], rdata_q[256*k +: 256]};
            o_sec <= {d_mir, d_mir ? 2'b00 : ((MUT == 3) ? 2'b00 : quad_q), row[9:0], 3'(k)};
            o_w <= rb(col, d_fmt);
            o_m <= 8'd1 << hr[2:0];
            l_sec <= o_sec; l_w <= o_w; l_m <= o_m;
        end
        if (MUT == 2) begin : g_late
            assign wq[k*281 +: 281] = {l_v, l_sec, {8{l_w}}, l_m};
        end else begin : g_on
            assign wq[k*281 +: 281] = {o_v, o_sec, {8{o_w}}, o_m};
        end
    end endgenerate
endmodule
`default_nettype wire
