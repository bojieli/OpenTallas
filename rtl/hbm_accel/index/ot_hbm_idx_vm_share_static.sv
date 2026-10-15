`timescale 1ns/1ps
`default_nettype none
// Static owner split of the ONE SW IDX read group between the INDEX operand face (ot_hbm_idx_vm_static) and the
// static TOPK engine (ot_hbm_idx_topk_static) (H-IDX 2026-10-15). Physically four bank-pair leaves (banks 2p, 2p+1),
// each with its own clock pin, request/response port group and 7-edge owner pipeline, so the pin plan exposes four
// port groups per quadrant, one beside each bank pair (v15 engine_lg_port_group_rule bit split: rq [(2p)*17,(2p+2)*17),
// rr [(2p)*257,(2p+2)*257)). No arbitration: the compiler books each bank/edge for at most one client; a double
// booking faults and neither request reaches the bank (never a silent winner). Zero added latency: requests pass
// combinationally to the bank (sampled n+1, as each client's face expects), the response valid of bank b is
// steered at n+7 by the owner registered at n+1, so each face still captures at n+8 and its own unexpected-valid
// check stays exact. MUT (bench): 1 owner pipeline one edge short; 2 double booking passes the INDEX request.
module ot_hbm_idx_vm_share_leaf #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [33:0]   index_rq, topk_rq,
    output reg  [33:0]   vm_rq,
    input  wire [513:0]  vm_rr,
    output wire [513:0]  index_rr, topk_rr,
    output reg           fault
);
    reg [3:0] own [0:6];                    // {topk1, index1, topk0, index0}
    wire [3:0] o = own[(MUT == 1) ? 5 : 6];
    reg [3:0] issue;
    always @* begin
        vm_rq = 34'd0; issue = 4'd0;
        for (integer b = 0; b < 2; b = b + 1) begin
            if (index_rq[17*b+16] && !topk_rq[17*b+16]) begin vm_rq[17*b +: 17] = index_rq[17*b +: 17]; issue[2*b] = 1'b1; end
            if (topk_rq[17*b+16] && !index_rq[17*b+16]) begin vm_rq[17*b +: 17] = topk_rq[17*b +: 17]; issue[2*b+1] = 1'b1; end
            if (MUT == 2 && topk_rq[17*b+16] && index_rq[17*b+16]) begin vm_rq[17*b +: 17] = index_rq[17*b +: 17]; issue[2*b] = 1'b1; end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault <= 1'b0; for (integer d = 0; d < 7; d = d + 1) own[d] <= 4'd0; end
        else begin
            own[0] <= issue;                    // sampled on the bank's own sampling edge n+1
            for (integer d = 1; d < 7; d = d + 1) own[d] <= own[d-1];
            for (integer b = 0; b < 2; b = b + 1)
                if (index_rq[17*b+16] && topk_rq[17*b+16]) fault <= 1'b1;
        end
    for (genvar b = 0; b < 2; b = b + 1) begin : g_b
        // own[6] (registered n+7) holds the owner booked at n+1 during the n+7..n+8 response cycle
        assign index_rr[257*b +: 257] = {vm_rr[257*b+256] && o[2*b],   vm_rr[257*b +: 256]};
        assign topk_rr[257*b +: 257]  = {vm_rr[257*b+256] && o[2*b+1], vm_rr[257*b +: 256]};
    end
endmodule

module ot_hbm_idx_vm_share_static #(parameter integer MUT = 0)(
    input  wire [3:0]    clk_pair,
    input  wire          rst_n,
    input  wire [135:0]  index_rq, topk_rq,
    output wire [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output wire [2055:0] index_rr, topk_rr,
    output wire          fault
);
    wire [3:0] f;
    for (genvar p = 0; p < 4; p = p + 1) begin : g_pair
        ot_hbm_idx_vm_share_leaf #(.MUT(MUT)) leaf(.clk(clk_pair[p]), .rst_n(rst_n),
            .index_rq(index_rq[34*p +: 34]), .topk_rq(topk_rq[34*p +: 34]), .vm_rq(vm_rq[34*p +: 34]),
            .vm_rr(vm_rr[514*p +: 514]), .index_rr(index_rr[514*p +: 514]), .topk_rr(topk_rr[514*p +: 514]),
            .fault(f[p]));
    end
    assign fault = |f;
endmodule
`default_nettype wire
