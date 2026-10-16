`timescale 1ns/1ps
// Q-ATTN-RATE 2026-10-16: PV16 V port of the KV die (one per stack lane; 16 per die = 2 pairs x 8 ports).
//
// Replaces the "8-sector double-buffered transposer" with a placement change (qkd_kv_static_writer VMAP=1):
// V row t lives in group {t[5:4], t[0]} of stack t[8:7], quarter Q holds dims 32Q..32Q+31, PC sector
// {1,0,t[6],t[12:9],t[3:1]}.  The w16 pair asks, in cycle q, port k of stack s for row t with t[5:4] = k and
// t[3:0] = q[3:0]; so port k is fed only by groups {k,0} (even q) and {k,1} (odd q), and every PC of those groups
// delivers its rows in the controller's existing v_consumer_order (= ascending ordinal {t[12:9], t[6], t[3:1]}),
// one sector every second core edge.  The port is a STATIC 2:1 select of two 4-PC sector quads.
//
// Static schedule, no credits: the compiler pops the four return rings of group {k, sel} at the slot whose word
// this port must present 2 edges later (input pin register + output pin register) and drives sel (= q[0]) and
// slot with it.  Nothing here waits, retries or reorders.  Checks (sticky fault, never move a slot): a slot
// without all four quarter words, any word outside a slot or on the unselected group, quarter tags that differ,
// a tag whose t[0] is not the selected group's parity.  ONE master for all 16 ports (no lane/stack straps): the
// pair checks every arrival's t against its own calendar, which catches a word routed to the wrong lane or stack.
// MUT (bench negative controls): 1 = sel inverted, 2 = quarter 1 and 2 swapped.
module qkd_pv16_vport #(parameter integer MUT = 0) (
    input wire ck, rst_n,
    input wire slot, input wire sel,                       // compiled: this edge's word, group parity
    // group {lane, 0} (even q) and group {lane, 1} (odd q): per quarter Q a ring word valid, tag (row t), sector
    input wire [3:0] in_v0, input wire [4*14-1:0] in_t0, input wire [4*256-1:0] in_d0,
    input wire [3:0] in_v1, input wire [4*14-1:0] in_t1, input wire [4*256-1:0] in_d1,
    output reg out_valid, output reg [13:0] out_t,
    output reg [511:0] out_v_lo, output reg [511:0] out_v_hi,     // V row dims 0-63 (quarters 0-1) / 64-127 (2-3)
    output reg fault
);
    // ---- reset captured at its pin (r2: r1's routed rst_n -> async-clear fanout measured capture 203.2 ps > 190):
    // one flop, synchronous capture; internal state uses the local copy.  Cold release is one edge later; the
    // production slot timeline is unchanged (the compiler's first slot is >= 2 edges after release).
    (* keep *) reg rst_q;
    always @(posedge ck) rst_q <= rst_n;
    wire rn = rst_q;
    // ---- input pin registers (every port registered) ----
    reg slot_q, sel_q;
    reg [7:0] v_q;
    reg [8*14-1:0] t_q;
    reg [8*256-1:0] d_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin slot_q <= 1'b0; v_q <= 8'b0; end
        else begin slot_q <= slot; v_q <= {in_v1, in_v0}; end
    always @(posedge ck) begin sel_q <= sel ^ ((MUT == 1) ? 1'b1 : 1'b0); t_q <= {in_t1, in_t0}; d_q <= {in_d1, in_d0}; end

    // ---- static select of the 4-quarter quad of group {lane, sel} ----
    wire [3:0] gv = sel_q ? v_q[7:4] : v_q[3:0];
    wire [3:0] ov = sel_q ? v_q[3:0] : v_q[7:4];
    wire [4*14-1:0] gt = sel_q ? t_q[4*14 +: 4*14] : t_q[0 +: 4*14];
    wire [1023:0] gd = sel_q ? d_q[1024 +: 1024] : d_q[0 +: 1024];
    wire [1023:0] row = (MUT == 2) ? {gd[1023:768], gd[511:256], gd[767:512], gd[255:0]} : gd;
    wire [13:0] t0 = gt[13:0];
    wire tags_eq = gt[27:14] == t0 && gt[41:28] == t0 && gt[55:42] == t0;
    wire own = t0[0] == sel_q;
    wire bad = slot_q ? (gv != 4'hf || ov != 4'h0 || !tags_eq || !own) : (|v_q);

    // ---- output pin registers ----
    always @(posedge ck or negedge rn)
        if (!rn) begin out_valid <= 1'b0; fault <= 1'b0; end
        else begin out_valid <= slot_q; if (bad) fault <= 1'b1; end
    always @(posedge ck) begin out_t <= t0; {out_v_hi, out_v_lo} <= row; end
endmodule
