`timescale 1ns/1ps
`default_nettype none
// Actual 296-flop control leaf. Owns prefix lane logic, fixed drain calendar,
// fault observations and reset release on one native clock root. No arbitration,
// ready, runtime scheduling or stage addition. The parent is wires only.
module dsfd_vm_static_wcontrol #(parameter integer NSRC=53)(
 input wire ck_control,rst_n,
 input wire [NSRC-1:0] pv,input wire [14*NSRC-1:0] pr,
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
    reg lane_bad;
    always @* begin : p_lane integer c, d; reg [4:0] bc, bd; reg [5:0] n;
        lane_bad = 1'b0;
        for (c = 0; c < NSRC; c = c + 1) begin
            bc = pr[14*c +: 5] ^ {pr[14*c+5 +: 3], 2'b00};
            n = 6'd0;
            for (d = 0; d < c; d = d + 1) begin
                bd = pr[14*d +: 5] ^ {pr[14*d+5 +: 3], 2'b00};
                if (pv[d] && bd == bc) n = n + 6'd1;
            end
`ifdef OT_VM_WSCHED_MUT_LANE
            lane[2*c +: 2] = 2'd0;                    // MUTANT: every record on lane 0 (dispatch duplicate)
`else
            lane[2*c +: 2] = (n > 6'd2) ? 2'd3 : n[1:0];
`endif
            lv[c] = pv[c] && n <= 6'd2;
            if (pv[c] && n > 6'd2) lane_bad = 1'b1;
        end
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
