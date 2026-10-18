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

module ot_hbm_idx_vm_share2_static #(parameter integer MUT = 0)(
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
        ot_hbm_idx_vm_share2_leaf #(.MUT(MUT)) leaf(.clk(clk_pair[p]), .rst_n(rst_n),
            .a_rq(a_rq[34*p +: 34]), .b_rq(b_rq[34*p +: 34]), .vm_rq(vm_rq[34*p +: 34]), .vm_rr(vm_rr[514*p +: 514]),
            .a_rr(a_rr[514*p +: 514]), .b_rr(b_rr[514*p +: 514]), .fault(f[p]));
    end
    assign fault = |f;
endmodule
`default_nettype wire
