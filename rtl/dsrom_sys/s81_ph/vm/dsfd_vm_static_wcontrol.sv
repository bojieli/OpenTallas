`timescale 1ns/1ps
`default_nettype none
// Actual control leaf. Owns prefix lane logic, fixed drain calendar,
// fault observations and reset release on one native clock root. No arbitration,
// ready, runtime scheduling or stage addition. The parent is wires only.
// LANE AT THE SOURCE EDGE (claude S81 VM F1, 2026-10-15, structural): the lane function reads the SOURCE pins
// (src_v, row bits [7:0] = the bank hash inputs) and is registered at edge P, the same edge the W0 header registers
// pv/pr, so lane/lv leave this leaf from flops and the dispatch samples them at P+1 exactly as before (zero cycles).
// Measured cause: lane computed combinationally from the header outputs pv/pr made a 34-level in->out path through
// this leaf (TT -1119 ps at the native IO budget, CTS gate 2026-10-15); now in->reg with a balanced saturating
// (0,1,2,3+) count tree instead of a 52-deep serial increment chain.
module dsfd_vm_static_wcontrol #(parameter integer NSRC=53)(
 input wire ck_control,rst_n,
 input wire [NSRC-1:0] src_v,input wire [8*NSRC-1:0] src_bank,
 input wire [95:0] cap_v,input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output reg [2*NSRC-1:0] lane,output reg [NSRC-1:0] lv,
 output reg [31:0] dr_v,output reg [63:0] dr_s,output reg [2:0] own
);
    reg [1:0] rr;
    always @(posedge ck_control or negedge rst_n) if (!rst_n) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    wire rn = rr[1];

    reg [2:0] control_epoch;
    always @(posedge ck_control) if (!rn) control_epoch <= 3'd0; else control_epoch <= control_epoch + 3'd1;
    wire phase_bad = (header_epoch != control_epoch) ||
        (payload_epoch[2:0] != control_epoch) || (payload_epoch[5:3] != control_epoch) ||
        (payload_epoch[8:6] != control_epoch) || (payload_epoch[11:9] != control_epoch);
    // saturating 2-bit add: 3 = "3 or more"
    function automatic [1:0] sat3(input [1:0] a, input [1:0] b);
        reg [2:0] t; begin t = a + b; sat3 = t[2] ? 2'd3 : t[1:0]; end
    endfunction
    localparam integer NP = 64;                            // tree width >= NSRC
    reg [NSRC-1:0] lane_v_d; reg [2*NSRC-1:0] lane_d; reg lane_bad_d;
    always @* begin : p_lane integer c, d, w, k; reg [4:0] bc, bd; reg [1:0] t [0:NP-1]; reg [1:0] n;
        lane_bad_d = 1'b0;
        for (c = 0; c < NSRC; c = c + 1) begin
            bc = src_bank[8*c +: 5] ^ {src_bank[8*c+5 +: 3], 2'b00};
            for (d = 0; d < NP; d = d + 1) begin
                t[d] = 2'd0;
                if (d < c) begin
                    bd = src_bank[8*d +: 5] ^ {src_bank[8*d+5 +: 3], 2'b00};
                    t[d] = {1'b0, src_v[d] && bd == bc};
                end
            end
            for (w = NP / 2; w >= 1; w = w / 2)              // balanced tree, log2(NP) levels
                for (k = 0; k < w; k = k + 1) t[k] = sat3(t[2*k], t[2*k+1]);
            n = t[0];
`ifdef OT_VM_WSCHED_MUT_LANE
            lane_d[2*c +: 2] = 2'd0;                  // MUTANT: every record on lane 0 (dispatch duplicate)
`else
            lane_d[2*c +: 2] = n;
`endif
            lane_v_d[c] = src_v[c] && n != 2'd3;
            if (src_v[c] && n == 2'd3) lane_bad_d = 1'b1;
        end
    end
    reg lane_bad;                                          // lane fault of the records registered at P (owned at P+1)
    always @(posedge ck_control) begin
        lane <= lane_d;
        if (!rn) begin lv <= {NSRC{1'b0}}; lane_bad <= 1'b0; end
        else begin lv <= lane_v_d; lane_bad <= lane_bad_d; end
    end

    // ---------------------------------------------------------------- fixed drain rule (from slice 0's captures)
    // h1 = dispatch o_v sampled at P+3 (the storage capture edge): lane 0 drains into the P+4 scatter sample, h2 lane 1
    // at P+5, h3 lane 2 at P+6
    reg [95:0] h1, h2, h3; reg drain_bad;
    always @(posedge ck_control) begin
        if (!rn) begin h1 <= 96'd0; h2 <= 96'd0; h3 <= 96'd0; end
        else begin h1 <= cap_v; h2 <= h1; h3 <= h2; end
    end
    always @* begin : p_drain integer k; reg l0, l1, l2;
        drain_bad = 1'b0;
        for (k = 0; k < 32; k = k + 1) begin
            l0 = h1[3*k]; l1 = h2[3*k+1]; l2 = h3[3*k+2];
`ifdef OT_VM_WSCHED_MUT_DRAIN
            l1 = h1[3*k+1];                              // MUTANT: lane 1 drains one edge early (P+4, not P+5)
`endif
            dr_v[k] = l0 | l1 | l2;
            dr_s[2*k +: 2] = l0 ? 2'd0 : l1 ? 2'd1 : 2'd2;
            if ((l0 && l1) || (l0 && l2) || (l1 && l2)) drain_bad = 1'b1;
        end
    end

    always @(posedge ck_control) if (!rn) own <= 3'b000; else own <= own | {phase_bad, drain_bad, lane_bad};
endmodule
`default_nettype wire
