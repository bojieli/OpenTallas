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
// Every input is a pin flop (a_rq/b_rq valids reset; request data and vm_rr reset-free); every output is a flop or
// flop -> one gate (vm_rq = one-hot AND-OR of the two registered requests; a_rr/b_rr valid = registered vm_rr valid
// AND the owner flop; a_rr/b_rr data = the vm_rr pin flops).
// Edges: request at the port before edge n+1 -> pin flop n+1 -> bank samples n+2 (own[0] booked there) -> bank answers
// at vm_rr after n+8 -> pin flop n+9 (own[7] holds the n+2 booking) -> each client captures at n+10.
// MUT (bench only): 1 owner tap one edge short (own[6]); 2 double booking passes the A request; 3 owner select swapped
// (A steered by B's owner and vice versa); 4 request pin flop bypassed (round trip n+9 with a self-consistent owner
// pipeline: latency off by one); 5 double booking does not fault.
module ot_hbm_idx_vm_share2_leaf_r #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [33:0]   a_rq, b_rq,
    output reg  [33:0]   vm_rq,
    input  wire [513:0]  vm_rr,
    output wire [513:0]  a_rr, b_rr,
    output reg           fault
);
    reg [31:0]  a_d, b_d;                   // request data pin flops {bank1 [15:0], bank0 [15:0]} (no reset)
    reg [1:0]   a_v, b_v;                   // request valid pin flops (reset)
    reg [513:0] rr_q;                       // vm_rr pin flops (no reset)
    always @(posedge clk) begin
        a_d <= {a_rq[32:17], a_rq[15:0]};
        b_d <= {b_rq[32:17], b_rq[15:0]};
        rr_q <= vm_rr;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_v <= 2'd0; b_v <= 2'd0; end
        else begin a_v <= {a_rq[33], a_rq[16]}; b_v <= {b_rq[33], b_rq[16]}; end
    // the request the bank samples on the next edge (MUT 4: straight from the port)
    wire [1:0]  av = (MUT == 4) ? {a_rq[33], a_rq[16]} : a_v;
    wire [1:0]  bv = (MUT == 4) ? {b_rq[33], b_rq[16]} : b_v;
    wire [31:0] ad = (MUT == 4) ? {a_rq[32:17], a_rq[15:0]} : a_d;
    wire [31:0] bd = (MUT == 4) ? {b_rq[32:17], b_rq[15:0]} : b_d;
    reg [3:0] own [0:7];                    // per bank b: {b, a} at [2b +: 2]
    wire [3:0] o = own[(MUT == 1) ? 6 : 7];
    reg [3:0] issue;
    always @* begin
        vm_rq = 34'd0; issue = 4'd0;
        for (integer k = 0; k < 2; k = k + 1) begin
            if ((av[k] && !bv[k]) || (MUT == 2 && av[k])) begin vm_rq[17*k +: 17] = {1'b1, ad[16*k +: 16]}; issue[2*k] = 1'b1; end
            else if (bv[k] && !av[k]) begin vm_rq[17*k +: 17] = {1'b1, bd[16*k +: 16]}; issue[2*k+1] = 1'b1; end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault <= 1'b0; for (integer d = 0; d < 8; d = d + 1) own[d] <= 4'd0; end
        else begin
            own[0] <= issue;                    // booked on the bank's sampling edge
            for (integer d = 1; d < 8; d = d + 1) own[d] <= own[d-1];
            if (MUT != 5 && |(av & bv)) fault <= 1'b1;
        end
    for (genvar k = 0; k < 2; k = k + 1) begin : g_b
        wire oa = (MUT == 3) ? o[2*k+1] : o[2*k];
        wire ob = (MUT == 3) ? o[2*k]   : o[2*k+1];
        assign a_rr[257*k +: 257] = {rr_q[257*k+256] && oa, rr_q[257*k +: 256]};
        assign b_rr[257*k +: 257] = {rr_q[257*k+256] && ob, rr_q[257*k +: 256]};
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
                .a_rq(a_rq[34*p +: 34]), .b_rq(b_rq[34*p +: 34]), .vm_rq(vm_rq[34*p +: 34]), .vm_rr(vm_rr[514*p +: 514]),
                .a_rr(a_rr[514*p +: 514]), .b_rr(b_rr[514*p +: 514]), .fault(f[p]));
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
