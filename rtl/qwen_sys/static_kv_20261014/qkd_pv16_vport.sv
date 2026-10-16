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
// without a V word on the selected group, any V word outside a slot or on the unselected group, a tag whose t[0]
// is not the selected group's parity (quarter agreement is checked by the landing rowctl).  ONE master for all 16 ports (no lane/stack straps): the
// pair checks every arrival's t against its own calendar, which catches a word routed to the wrong lane or stack.
// r4 ABI (Q-VMWB 2026-10-16): each side is the landing group's existing response face
// qkd_static_kv_landing_physical_grp.rsp_{valid,v,t,data} wired straight in (no die-top glue).  The landing rowctl
// already checks that the four quarter words agree (valid / tag / epoch / layer, sticky fault), so one valid, one
// K/V flag and one tag per side.  K responses share the bus (rsp_v = 0) and are ignored here; a K word on the
// selected group in a V slot is a fault (the compiler never schedules that).
// r5 (Q-VMWB 2026-10-16): the port is also the V ISSUER, so the die needs no calendar producer and no glue.  The pvw
// pair's own request for this port (req_valid[wp], req_t[14wp +: 14]) enters at pr_*; the port demuxes it by t[0]
// onto the V get face of landing group {lane, t[0]} (vq0_* / vq1_*, -> qkd_static_kv_landing_physical_grp VREQ=1
// vreq_*) and derives slot / sel itself from the same request through a fixed delay.  Die timing contract (all 16
// ports equal, the die balances relays): WP = relay edges pair req pin -> pr pin, RT = edges from the vq output
// register to the rsp words at this port's in pins (landing VREQ=1 is 8 + request / return relays).  The pair sees
// its word RL edges after its request (RL 19, ot_qwen_tp8_pv_wide_ctl FIRST_INPUT_AGE = RL + 1): the request waits
// DQ = RL - 4 - WP - RT edges inside the port (>= 0 is checked at elaboration).
// MUT (bench negative controls): 1 = sel inverted, 2 = quarter 1 and 2 swapped, 3 = K/V flag ignored,
// 4 = V get sent to the wrong group (t[0] inverted on the issue face).
module qkd_pv16_vport #(parameter integer MUT = 0, RL = 19, WP = 2, RT = 8) (
    input wire ck, rst_n,
    // the pvw pair's request for this port (static: one row t a slot, t[5:4] = lane)
    input wire pr_valid, input wire [13:0] pr_t,
    // V gets to landing group {lane, 0} / {lane, 1} (the landing's vreq face)
    output reg vq0_valid, output reg [13:0] vq0_t, output reg vq1_valid, output reg [13:0] vq1_t,
    // side 0 = landing group {lane, 0} (even q), side 1 = group {lane, 1} (odd q): the group's rsp face
    input wire in0_valid, input wire in0_vflag, input wire [13:0] in0_t, input wire [1023:0] in0_d,
    input wire in1_valid, input wire in1_vflag, input wire [13:0] in1_t, input wire [1023:0] in1_d,
    output reg out_valid, output reg [13:0] out_t,
    output reg [511:0] out_v_lo, output reg [511:0] out_v_hi,     // V row dims 0-63 (quarters 0-1) / 64-127 (2-3)
    output reg fault
);
    localparam integer DQ = RL - 4 - WP - RT;                  // request wait inside the port
    localparam integer SL = RL - 3 - WP;                       // pr register -> slot / sel at the in pins
    generate if (DQ < 0 || SL < 1) begin : g_bad
        initial $fatal(1, "qkd_pv16_vport: RL %0d too short for WP %0d + RT %0d", RL, WP, RT);
    end endgenerate
    // reset captured at its pin (r2); internal state uses the local copy (+1 cold-release edge, 0 production cycles)
    (* keep *) reg rst_q;
    always @(posedge ck) rst_q <= rst_n;
    wire rn = rst_q;
    // ---- request: pin register, DQ-edge wait, demux onto the group's V get face (output register) ----
    reg pr_v_q; reg [13:0] pr_t_q;
    always @(posedge ck or negedge rn) if (!rn) pr_v_q <= 1'b0; else pr_v_q <= pr_valid;
    always @(posedge ck) pr_t_q <= pr_t;
    reg [DQ:0] qv; reg [14*(DQ+1)-1:0] qt;                      // [0] = the pin register
    always @* begin qv[0] = pr_v_q; qt[13:0] = pr_t_q; end
    genvar w;
    generate for (w = 1; w <= DQ; w = w + 1) begin : g_wait
        always @(posedge ck or negedge rn) if (!rn) qv[w] <= 1'b0; else qv[w] <= qv[w-1];
        always @(posedge ck) qt[14*w +: 14] <= qt[14*(w-1) +: 14];
    end endgenerate
    wire iv = qv[DQ]; wire [13:0] it = qt[14*DQ +: 14];
    wire ig = it[0] ^ ((MUT == 4) ? 1'b1 : 1'b0);
    always @(posedge ck or negedge rn)
        if (!rn) begin vq0_valid <= 1'b0; vq1_valid <= 1'b0; end
        else begin vq0_valid <= iv && !ig; vq1_valid <= iv && ig; end
    always @(posedge ck) begin vq0_t <= it; vq1_t <= it; end
    // ---- slot / sel: the same request, SL edges later (aligned with the rsp words at the in pins) ----
    reg [SL:0] sv, ss;
    always @* begin sv[0] = pr_v_q; ss[0] = pr_t_q[0]; end
    generate for (w = 1; w <= SL; w = w + 1) begin : g_slot
        always @(posedge ck or negedge rn) if (!rn) sv[w] <= 1'b0; else sv[w] <= sv[w-1];
        always @(posedge ck) ss[w] <= ss[w-1];
    end endgenerate
    wire slot = sv[SL], sel = ss[SL];
    // ---- input pin registers (every port registered) ----
    reg slot_q, sel_q;
    reg [1:0] val_q, vf_q;
    reg [27:0] t_q;
    reg [2047:0] d_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin slot_q <= 1'b0; val_q <= 2'b0; end
        else begin slot_q <= slot; val_q <= {in1_valid, in0_valid}; end
    always @(posedge ck) begin
        sel_q <= sel ^ ((MUT == 1) ? 1'b1 : 1'b0);
        vf_q <= (MUT == 3) ? 2'b11 : {in1_vflag, in0_vflag};
        t_q <= {in1_t, in0_t}; d_q <= {in1_d, in0_d};
    end

    // ---- static select of group {lane, sel} ----
    wire [1:0] vw = val_q & vf_q;                          // V words on each side this edge
    wire gv = sel_q ? vw[1] : vw[0];
    wire ov = sel_q ? vw[0] : vw[1];
    wire [13:0] t0 = sel_q ? t_q[27:14] : t_q[13:0];
    wire [1023:0] gd = sel_q ? d_q[2047:1024] : d_q[1023:0];
    wire [1023:0] row = (MUT == 2) ? {gd[1023:768], gd[511:256], gd[767:512], gd[255:0]} : gd;
    wire own = t0[0] == sel_q;
    wire bad = slot_q ? (!gv || ov || !own) : (|vw);

    // ---- output pin registers ----
    always @(posedge ck or negedge rn)
        if (!rn) begin out_valid <= 1'b0; fault <= 1'b0; end
        else begin out_valid <= slot_q; if (bad) fault <= 1'b1; end
    always @(posedge ck) begin out_t <= t0; {out_v_hi, out_v_lo} <= row; end
endmodule
