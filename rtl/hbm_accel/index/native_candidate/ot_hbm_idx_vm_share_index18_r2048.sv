`timescale 1ns/1ps
`default_nettype none
// Explicit native INDEX18 candidate; legacy TOPK/ARGMAX retain exact17-bit fields.
// Zero added cycles. Never zero-extend legacy mirror bit. No production caller.
module ot_hbm_idx_vm_share_leaf_index18_r2048 #(parameter integer MUT = 0, parameter integer VM_RT = 0, parameter integer F32 = 0,
    parameter integer AMNOMASK = 0)(
    input  wire          clk, rst_n,
    input wire [35:0] index_rq,
    input wire [33:0] topk_rq, argmax_rq,   // registered sources (pin flops / TOPK request register)
    output reg  [35:0]   vm_rq,
    input  wire [513:0]  vm_rr,                          // port: registered here
    output wire [513:0]  index_rr, topk_rr, argmax_rr,   // from the vm_rr pin register
    output reg           fault
);
    reg [5:0] own [0:7+VM_RT];              // per bank b: {argmax, topk, index} at [3b +: 3]
    wire [5:0] o = own[((MUT == 1) ? 6 : 7) + VM_RT];
    reg [513:0] rr_q;                       // vm_rr pin register (no reset)
    always @(posedge clk) rr_q <= vm_rr;
    reg [5:0] issue; reg [2:0] v;
    always @* begin
        vm_rq = 36'd0; issue = 6'd0; v = 3'd0;
        for (integer b = 0; b < 2; b = b + 1) begin
            v = {argmax_rq[17*b+16], topk_rq[17*b+16], index_rq[18*b+17]};
            if (v == 3'b001) begin vm_rq[18*b +: 18] = index_rq[18*b +: 18]; issue[3*b] = 1'b1; end
            else if (v == 3'b010) begin vm_rq[18*b +: 18] = {topk_rq[17*b+16],topk_rq[17*b+15],1'b0,topk_rq[17*b +: 15]}; issue[3*b+1] = 1'b1; end
            else if (v == 3'b100) begin vm_rq[18*b +: 18] = {argmax_rq[17*b+16],argmax_rq[17*b+15],1'b0,argmax_rq[17*b +: 15]}; issue[3*b+2] = 1'b1; end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault <= 1'b0; for (integer d = 0; d < 8 + VM_RT; d = d + 1) own[d] <= 6'd0; end
        else begin
            own[0] <= issue;                    // sampled on the bank's own sampling edge n+1
            for (integer d = 1; d < 8 + VM_RT; d = d + 1) own[d] <= own[d-1];
            for (integer b = 0; b < 2; b = b + 1)
                if ({1'b0, index_rq[18*b+17]} + {1'b0, topk_rq[17*b+16]} + {1'b0, argmax_rq[17*b+16]} > 2'd1) fault <= 1'b1;
        end
    for (genvar b = 0; b < 2; b = b + 1) begin : g_b
        // the bank answers n+7+VM_RT (port); rr_q holds it one edge later, own[7+VM_RT] holds the owner booked at n+1 then
        assign index_rr[257*b +: 257]  = {rr_q[257*b+256] && o[3*b],   rr_q[257*b +: 256]};
        assign topk_rr[257*b +: 257]   = {rr_q[257*b+256] && o[3*b+1], rr_q[257*b +: 256]};
        if (F32 == 0) begin : g_am
            assign argmax_rr[257*b +: 257] = {rr_q[257*b+256] && o[3*b+2], rr_q[257*b +: 256]};
        end else begin : g_am32
            wire [7:0] vc, oc;                  // kept copies: vm_rr valid pin register / argmax own tap of bank b
            wire [5:0] o_pre = own[((MUT == 1) ? 6 : 7) + VM_RT - 1];
            for (genvar w = 0; w < 8; w = w + 1) begin : g_w
                ot_hbm_idx_kreg #(.W(1)) uv (.clk(clk), .rst_n(rst_n), .d(vm_rr[257*b+256]), .q(vc[w]));
                ot_hbm_idx_kreg #(.W(1)) uo (.clk(clk), .rst_n(rst_n), .d(o_pre[3*b+2]), .q(oc[w]));
                assign argmax_rr[257*b + 32*w +: 32] = (AMNOMASK != 0) ? rr_q[257*b + 32*w +: 32]
                                                                       : (rr_q[257*b + 32*w +: 32] & {32{vc[w] && oc[w]}});
            end
            assign argmax_rr[257*b+256] = rr_q[257*b+256] && o[3*b+2];
        end
    end
endmodule
module ot_hbm_idx_vm_share_index18_r2048 #(parameter integer MUT = 0, parameter integer AMMUT = 0, parameter integer VM_RT = 0,
    parameter integer F32 = 0)(
    input  wire          clk,
    input  wire          rst_n,
    input wire [143:0] index_rq,
    input wire [135:0] topk_rq, argmax_rq,   // registered sources
    output wire [143:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output wire [2055:0] index_rr, topk_rr,
    output wire [263:0]  argmax_m,          // {lane valid8, data256}: 2 edges after the vm_rr pin register
    output wire          fault
);
    wire [3:0] f; wire [2055:0] am;
    for (genvar p = 0; p < 4; p = p + 1) begin : g_pair
        ot_hbm_idx_vm_share_leaf_index18_r2048 #(.MUT(MUT), .VM_RT(VM_RT), .F32(F32), .AMNOMASK(AMMUT == 3 ? 1 : 0)) leaf(.clk(clk), .rst_n(rst_n),
            .index_rq(index_rq[36*p +: 36]), .topk_rq(topk_rq[34*p +: 34]), .argmax_rq(argmax_rq[34*p +: 34]),
            .vm_rq(vm_rq[36*p +: 36]), .vm_rr(vm_rr[514*p +: 514]), .index_rr(index_rr[514*p +: 514]),
            .topk_rr(topk_rr[514*p +: 514]), .argmax_rr(am[514*p +: 514]), .fault(f[p]));
    end
    ot_hbm_idx_vm_share_amtree #(.AMMUT(AMMUT), .F32(F32)) tree(.clk(clk), .am_rr(am), .argmax_m(argmax_m));
    assign fault = |f;
endmodule
`default_nettype wire
