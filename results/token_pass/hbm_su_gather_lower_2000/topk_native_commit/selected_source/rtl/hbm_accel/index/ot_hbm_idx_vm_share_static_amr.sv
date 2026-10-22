`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// PIN-REGISTERED SW read-group share for the HARDENED IDX root ot_hbm_idx_rootctl_static_am (lane HBM-IDXAM2 2026-10-18).
// Why: hidx_rootctl_am_1018-r2-0385e1977 EARLY_FAIL_SETUP -577.7 ps / 3,621 endpoints at CTS. The share of
// ot_hbm_idx_vm_share_static(_am) is a ZERO-latency mux in the middle of a die link (index_rq/argmax_rq -> vm_rq and
// vm_rr -> index_rr are port-to-port combinational): inside a hard tile every such path gets in-max 518.7 + out-max
// 518.7 ps of the 773 ps the consistent link split allows (physical/common_flow/link_budget_consistent.sdc), so it can
// never close (2,194 in->out endpoints at -570..-815). This variant registers the share's boundary:
//   * requests: the caller pin-registers index_rq / argmax_rq (topk_rq is already the TOPK engine's register), so vm_rq
//     is register -> one-hot OR -> port;
//   * responses: each bank-pair leaf pin-registers its 514 vm_rr bits (no reset: data pin flops) and steers them with the
//     owner booked at the bank's sampling edge, read one edge later (own[7] instead of own[6]);
//   * ARGMAX: the 4-edge equal-latency OR chain is replaced by a 2-stage OR tree (stage A per half = lanes 0-3 / 4-7,
//     stage B = argmax_m register at the E face). Edges from the argmax engine's request to argmax_m are UNCHANGED:
//     request pin register +1, vm_rr pin register +1, tree 2 = the old chain's 4.
// Timing vs ot_hbm_idx_vm_share_static_am at the ports: INDEX request +1 and response +1 (round trip +2: the SW operand
// reader must capture at n+12); TOPK response +1 (engine RT_EXTRA 1); ARGMAX port to port +0.
// MUT (bench only): 1 leaf owner tap one edge short (own[6] against the registered vm_rr); AMMUT (bench only): 1 lanes
// 6-7 skip stage A (unequal tree); 2 lane valid bits mirrored (lane l at 7-l); 3 data not masked by the owner-steered
// valid; 4 the 8 fp32 elements of the data word reversed (tie-break order).
// VM_RT (VEH-TOPKFIX2 2026-10-19): fixed extra VM round-trip edges between this tile's vm_rq / vm_rr ports and the bank
// beyond the 7-edge non-face model (d4g hfd_vms_bank_native_q0_faces input pin flop = 1, plus any die relay / landing
// stages on the rq4 / rr4 lanes): the owner tap moves to own[7+VM_RT]. Every response face (INDEX, TOPK, ARGMAX) leaves
// VM_RT edges later. Default 0 = bit-identical to r3.
// F32 (HBM-IDX6 2026-10-20, native32 census of g2d: share.g_pair[].leaf o[]/rr_q drove 257 loads = the ARGMAX lane
// valid gating 256 data bits in the tree): 1 = the leaf masks the ARGMAX data per 32-bit word with its OWN kept copy of
// the steered valid (8 copies a bank: vm_rr valid pin-register copy AND own-tap copy, both loaded on the edges rr_q /
// own[7+VM_RT] are), and the tree ORs the pre-masked data (AMNOMASK 1 = bench mutant AMMUT 3: data left unmasked).
// Same argmax_m every edge. 0 = as built.
module ot_hbm_idx_vm_share_leaf_r #(parameter integer MUT = 0, parameter integer VM_RT = 0, parameter integer F32 = 0,
    parameter integer AMNOMASK = 0)(
    input  wire          clk, rst_n,
    input  wire [33:0]   index_rq, topk_rq, argmax_rq,   // registered sources (pin flops / TOPK request register)
    output reg  [33:0]   vm_rq,
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
        vm_rq = 34'd0; issue = 6'd0; v = 3'd0;
        for (integer b = 0; b < 2; b = b + 1) begin
            v = {argmax_rq[17*b+16], topk_rq[17*b+16], index_rq[17*b+16]};
            if (v == 3'b001) begin vm_rq[17*b +: 17] = index_rq[17*b +: 17]; issue[3*b] = 1'b1; end
            else if (v == 3'b010) begin vm_rq[17*b +: 17] = topk_rq[17*b +: 17]; issue[3*b+1] = 1'b1; end
            else if (v == 3'b100) begin vm_rq[17*b +: 17] = argmax_rq[17*b +: 17]; issue[3*b+2] = 1'b1; end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault <= 1'b0; for (integer d = 0; d < 8 + VM_RT; d = d + 1) own[d] <= 6'd0; end
        else begin
            own[0] <= issue;                    // sampled on the bank's own sampling edge n+1
            for (integer d = 1; d < 8 + VM_RT; d = d + 1) own[d] <= own[d-1];
            for (integer b = 0; b < 2; b = b + 1)
                if ({1'b0, index_rq[17*b+16]} + {1'b0, topk_rq[17*b+16]} + {1'b0, argmax_rq[17*b+16]} > 2'd1) fault <= 1'b1;
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
module ot_hbm_idx_vm_share_amtree #(parameter integer AMMUT = 0, parameter integer F32 = 0)(
    input  wire          clk,
    input  wire [2055:0] am_rr,             // 8 lanes {owner-steered valid, data256} from the leaves' pin registers
    output reg  [263:0]  argmax_m           // {lane valid8, data256}, stage B (place at the E face)
);
    function automatic [263:0] lanes(input [2055:0] rr, input integer lo, input integer hi);
        reg [263:0] w; reg [255:0] d; integer l, e;
        begin
            w = 264'd0;
            for (l = lo; l < hi; l = l + 1) begin
                w[(AMMUT == 2) ? 256 + 7 - l : 256 + l] = rr[257*l+256];
                d = rr[257*l +: 256];
                if (AMMUT == 4) for (e = 0; e < 8; e = e + 1) d[32*e +: 32] = rr[257*l + 32*(7-e) +: 32];
                if (rr[257*l+256] || AMMUT == 3 || F32 != 0) w[255:0] = w[255:0] | d;   // F32: d pre-masked by the leaf
            end
            lanes = w;
        end
    endfunction
    reg [263:0] a0, a1;
    wire [263:0] h0 = lanes(am_rr, 0, 4), h1a = lanes(am_rr, 4, 6), h1b = lanes(am_rr, 6, 8);
    always @(posedge clk) begin
        a0 <= h0;
        a1 <= (AMMUT == 1) ? h1a : (h1a | h1b);
        argmax_m <= a0 | a1 | ((AMMUT == 1) ? h1b : 264'd0);
    end
endmodule
module ot_hbm_idx_vm_share_static_amr #(parameter integer MUT = 0, parameter integer AMMUT = 0, parameter integer VM_RT = 0,
    parameter integer F32 = 0)(
    input  wire          clk,
    input  wire          rst_n,
    input  wire [135:0]  index_rq, topk_rq, argmax_rq,   // registered sources
    output wire [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output wire [2055:0] index_rr, topk_rr,
    output wire [263:0]  argmax_m,          // {lane valid8, data256}: 2 edges after the vm_rr pin register
    output wire          fault
);
    wire [3:0] f; wire [2055:0] am;
    for (genvar p = 0; p < 4; p = p + 1) begin : g_pair
        ot_hbm_idx_vm_share_leaf_r #(.MUT(MUT), .VM_RT(VM_RT), .F32(F32), .AMNOMASK(AMMUT == 3 ? 1 : 0)) leaf(.clk(clk), .rst_n(rst_n),
            .index_rq(index_rq[34*p +: 34]), .topk_rq(topk_rq[34*p +: 34]), .argmax_rq(argmax_rq[34*p +: 34]),
            .vm_rq(vm_rq[34*p +: 34]), .vm_rr(vm_rr[514*p +: 514]), .index_rr(index_rr[514*p +: 514]),
            .topk_rr(topk_rr[514*p +: 514]), .argmax_rr(am[514*p +: 514]), .fault(f[p]));
    end
    ot_hbm_idx_vm_share_amtree #(.AMMUT(AMMUT), .F32(F32)) tree(.clk(clk), .am_rr(am), .argmax_m(argmax_m));
    assign fault = |f;
endmodule
`default_nettype wire
