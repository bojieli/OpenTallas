`timescale 1ns/1ps
`default_nettype none
// HBM d4g plan (b) IDX quad client, NW quadrant (lane HBM-RTL4, 2026-10-18). The NW VM banks have no free read group: r0 LG,
// r1 DMA-back, r2 x-load, r3 host QDQ (hb_quant_NW), r4 COLL. The NW IDX operand reader (ot_hbm_idx_vm_query_static,
// quadrant 2 of ot_hbm_idx_client_static_quad) shares r3 with the host QDQ reader through this TWO-client static
// owner split. Same structure and timing as ot_hbm_idx_vm_share_static (four bank-pair leaves, own clock pin each,
// requests pass combinationally (sampled n+1 as each face expects), the response valid of bank b is steered at n+7 by
// the owner registered at n+1, so each face captures at n+8 exactly as on an unshared group: ZERO added latency).
// No arbitration: the compiler books each bank/edge for at most one of the two clients (IDX scans and host QDQ never
// overlap in a calendar); a double booking faults and reaches neither (never a silent winner).
// MUT (bench): 1 owner pipeline one edge short; 2 double booking passes the A request.
// REG (HBM-NSFIX/SHARE2 2026-10-18, coordinator decision 0hk): REG 1 selects the PIN-REGISTERED leaf
// ot_hbm_idx_vm_share2_leaf_r (the hardened tile; a comb port-to-port feed-through cannot close as a hard tile under
// physical/common_flow/link_budget_consistent.sdc). REG 1 timing at the ports: request +1 (a_rq/b_rq pin flops; the bank
// samples n+2), response +1 (vm_rr pin flops), fault +1 => each client's VM round trip is n+10 instead of n+8 (+2 edges).
// REG 0 (default) is this file's original zero-latency body, byte-for-byte behaviour (kept for the COLL read split
// hcollrs_<q>: hb_coll v8x and hcollgi capture at a FIXED n+8 inside closed/submitted tiles -- see the SHARE2 log).
// ot_hbm_idx_vm_share2_static_r = this parent at REG 1 under its own name (die master for hb_idx__nwsh).
module ot_hbm_idx_vm_share2_leaf #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [33:0]   a_rq, b_rq,
    output reg  [33:0]   vm_rq,
    input  wire [513:0]  vm_rr,
    output wire [513:0]  a_rr, b_rr,
    output reg           fault
);
    reg [3:0] own [0:6];                    // per bank b: {b, a} at [2b +: 2]
    wire [3:0] o = own[(MUT == 1) ? 5 : 6];
    reg [3:0] issue; reg [1:0] v;
    always @* begin
        vm_rq = 34'd0; issue = 4'd0; v = 2'd0;
        for (integer k = 0; k < 2; k = k + 1) begin
            v = {b_rq[17*k+16], a_rq[17*k+16]};
            if (v == 2'b01 || (MUT == 2 && v[0])) begin vm_rq[17*k +: 17] = a_rq[17*k +: 17]; issue[2*k] = 1'b1; end
            else if (v == 2'b10) begin vm_rq[17*k +: 17] = b_rq[17*k +: 17]; issue[2*k+1] = 1'b1; end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault <= 1'b0; for (integer d = 0; d < 7; d = d + 1) own[d] <= 4'd0; end
        else begin
            own[0] <= issue;                    // sampled on the bank's own sampling edge n+1
            for (integer d = 1; d < 7; d = d + 1) own[d] <= own[d-1];
            for (integer k = 0; k < 2; k = k + 1)
                if (a_rq[17*k+16] && b_rq[17*k+16]) fault <= 1'b1;
        end
    for (genvar k = 0; k < 2; k = k + 1) begin : g_b
        assign a_rr[257*k +: 257] = {vm_rr[257*k+256] && o[2*k],   vm_rr[257*k +: 256]};
        assign b_rr[257*k +: 257] = {vm_rr[257*k+256] && o[2*k+1], vm_rr[257*k +: 256]};
    end
endmodule

// Pin-registered bank-pair leaf (REG 1; THE hardened tile, replicated 4x beside the bank pairs, one clock pin each).
// OWN-SHARE2P 10-18 (native FAIL fix of view r1-984038a3d: launch 247.5 > 220 on 41 pins): REGISTERED OUTPUT FACES.
// r1 had flop -> gate -> pin outputs: vm_rq = AND-OR of the W/E request pin flops, so the E (or W) flop drove ~108 um to the
// S corner (34 x 238-247 ps), and one vm_rr flop drove BOTH a_rr (W face) and b_rr (E face) (7 pins 222-238 ps).
// Now EVERY OUTPUT IS A FLOP Q at its pin: vm_rq flops (owner select = one AND-OR in front of the flop, inputs straight
// from the a_rq/b_rq pins), one response flop set PER CLIENT FACE (a_q at W, b_q at E; valid = vm_rr valid AND the owner
// tap folded in front of the flop), fault flop. vm_rr / a_rr / b_rr are split per bank (0 / 1 of the pair; ports only, the
// parent wiring is unchanged) so the kit puts vm_rq in the MIDDLE of the S face between the two banks' response buses (each
// request path <= ~60 um) and orders each client face far-bank-low: W = a_rr1 low / a_rr0 high, E = b_rr0 low / b_rr1 high
// (worst S pin -> client pin Manhattan ~163 um instead of ~212 um, r1's a_rr[511] corner-to-corner).
// Port timing at the parent ports is IDENTICAL to r1 (bench unchanged): request +1 (vm_rq flop at n+1, bank samples n+2),
// response +1 (face flops at n+9, clients capture n+10), fault +1 (double-booking flop n+1, sticky fault n+2).
// Owner pipeline: own[0] booked at n+1 (from the pins, the edge the vm_rq flop launches), own[7] = the booking at the
// response flop edge n+9. MUT (bench only): 1 owner tap one edge short (own[6]); 2 double booking passes the A request;
// 3 owner select swapped (A steered by B's owner and vice versa); 4 request flop bypassed (vm_rq straight from the port,
// self-consistent owner tap own[6]: round trip n+9, latency off by one); 5 double booking does not fault.
module ot_hbm_idx_vm_share2_leaf_r #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [33:0]   a_rq, b_rq,
    output wire [33:0]   vm_rq,
    input  wire [256:0]  vm_rr0, vm_rr1,
    output wire [256:0]  a_rr0, a_rr1, b_rr0, b_rr1,
    output reg           fault
);
    wire [513:0] vm_rr = {vm_rr1, vm_rr0};
    reg  [513:0] a_rr, b_rr;                // per-face response flops
    assign {a_rr1, a_rr0} = a_rr;
    assign {b_rr1, b_rr0} = b_rr;
    // AD3-HBM-SHARE2 10-18 (native FAIL fix of view r2-a1d3f7d2c: capture a_rq/b_rq[16]/[33] 186-207 > 190, data bits 122-145):
    // the valid pins no longer meet the OTHER face's valid before fanning out to the data select. Each client's data is
    // gated by ITS OWN valid only (AND-OR, a-side gates sit by the a pins' path, b-side by the b pins'); the bank valid is
    // a_v XOR b_v (one gate). The compiler books each bank/edge for at most one client: a double booking issues NOTHING
    // (valid 0, fault as before); only the data bits under that valid-0 request differ (a|b instead of 0), and the bank
    // samples request data only under valid (ot_vms_bank_static: r_active / selected_read gate rd_decode and its fault).
    reg [33:0] rq_d; reg [3:0] issue;
    always @* begin
        rq_d = 34'd0; issue = 4'd0;
        for (integer k = 0; k < 2; k = k + 1) begin
            rq_d[17*k +: 16] = (a_rq[17*k +: 16] & {16{a_rq[17*k+16]}}) | (b_rq[17*k +: 16] & {16{b_rq[17*k+16]}});
            rq_d[17*k+16]    = (MUT == 2) ? (a_rq[17*k+16] | b_rq[17*k+16]) : (a_rq[17*k+16] ^ b_rq[17*k+16]);
            issue[2*k]       = a_rq[17*k+16] && (!b_rq[17*k+16] || MUT == 2);
            issue[2*k+1]     = b_rq[17*k+16] && !a_rq[17*k+16];
        end
    end
    // local reset release at the rst_n pin (AD3-HBM-SHARE2 10-18, native capture rule; r2 rst_n capture 280 > 190): rst_n
    // lands on ONE async-clear flop (assert async, release synchronous one edge later); every other flop clears from rst_q.
    // No operation edge changes (requests start long after release).
    reg rst_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_q <= 1'b0; else rst_q <= 1'b1;
    reg [33:0] rq_q;                        // vm_rq output flops (reset: idle on the bank face out of reset)
    reg [3:0]  own [0:7];                   // per bank b: {b, a} at [2b +: 2]; own[0] = booking of the vm_rq flop edge
    reg        dbl_q;                       // double booking seen at the pins (flop), fault sticky one edge later
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin rq_q <= 34'd0; dbl_q <= 1'b0; fault <= 1'b0; for (integer d = 0; d < 8; d = d + 1) own[d] <= 4'd0; end
        else begin
            rq_q <= rq_d;
            own[0] <= issue;
            for (integer d = 1; d < 8; d = d + 1) own[d] <= own[d-1];
            dbl_q <= (a_rq[16] && b_rq[16]) || (a_rq[33] && b_rq[33]);
            if (MUT != 5 && dbl_q) fault <= 1'b1;
        end
    assign vm_rq = (MUT == 4) ? rq_d : rq_q;
    wire [3:0] o = own[(MUT == 1 || MUT == 4) ? 6 : 7];
    // per-face response flops: data reset-free; valid (bit 256 of each bank) = vm_rr valid AND owner, folded in front of
    // the flop, reset (idle out of reset as r1's AND with the reset owner pipeline)
    always @(posedge clk)
        for (integer k = 0; k < 2; k = k + 1) begin
            a_rr[257*k +: 256] <= vm_rr[257*k +: 256];
            b_rr[257*k +: 256] <= vm_rr[257*k +: 256];
        end
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin a_rr[256] <= 1'b0; a_rr[513] <= 1'b0; b_rr[256] <= 1'b0; b_rr[513] <= 1'b0; end
        else for (integer k = 0; k < 2; k = k + 1) begin
            a_rr[257*k+256] <= vm_rr[257*k+256] && ((MUT == 3) ? o[2*k+1] : o[2*k]);
            b_rr[257*k+256] <= vm_rr[257*k+256] && ((MUT == 3) ? o[2*k]   : o[2*k+1]);
        end
endmodule

module ot_hbm_idx_vm_share2_static #(parameter integer MUT = 0, parameter integer REG = 0)(
    input  wire [3:0]    clk_pair,
    input  wire          rst_n,
    input  wire [135:0]  a_rq, b_rq,
    output wire [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output wire [2055:0] a_rr, b_rr,
    output wire          fault
);
    wire [3:0] f;
    for (genvar p = 0; p < 4; p = p + 1) begin : g_pair
        if (REG != 0) begin : g_r
            ot_hbm_idx_vm_share2_leaf_r #(.MUT(MUT)) leaf(.clk(clk_pair[p]), .rst_n(rst_n),
                .a_rq(a_rq[34*p +: 34]), .b_rq(b_rq[34*p +: 34]), .vm_rq(vm_rq[34*p +: 34]),
                .vm_rr0(vm_rr[514*p +: 257]), .vm_rr1(vm_rr[514*p+257 +: 257]),
                .a_rr0(a_rr[514*p +: 257]), .a_rr1(a_rr[514*p+257 +: 257]),
                .b_rr0(b_rr[514*p +: 257]), .b_rr1(b_rr[514*p+257 +: 257]), .fault(f[p]));
        end else begin : g_c
            ot_hbm_idx_vm_share2_leaf #(.MUT(MUT)) leaf(.clk(clk_pair[p]), .rst_n(rst_n),
                .a_rq(a_rq[34*p +: 34]), .b_rq(b_rq[34*p +: 34]), .vm_rq(vm_rq[34*p +: 34]), .vm_rr(vm_rr[514*p +: 514]),
                .a_rr(a_rr[514*p +: 514]), .b_rr(b_rr[514*p +: 514]), .fault(f[p]));
        end
    end
    assign fault = |f;
endmodule

// Die master for hb_idx__nwsh (REG 1 under its own name; port-identical to ot_hbm_idx_vm_share2_static).
module ot_hbm_idx_vm_share2_static_r #(parameter integer MUT = 0)(
    input  wire [3:0]    clk_pair,
    input  wire          rst_n,
    input  wire [135:0]  a_rq, b_rq,
    output wire [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output wire [2055:0] a_rr, b_rr,
    output wire          fault
);
    ot_hbm_idx_vm_share2_static #(.MUT(MUT), .REG(1)) u(.clk_pair(clk_pair), .rst_n(rst_n), .a_rq(a_rq), .b_rq(b_rq),
        .vm_rq(vm_rq), .vm_rr(vm_rr), .a_rr(a_rr), .b_rr(b_rr), .fault(fault));
endmodule
`default_nettype wire
