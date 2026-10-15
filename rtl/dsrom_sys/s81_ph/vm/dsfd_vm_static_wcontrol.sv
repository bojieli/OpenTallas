`timescale 1ns/1ps
`default_nettype none
// Actual control leaf of the static VM write edge. Owns the prefix lane function, the fixed drain calendar, fault
// observations and reset release on one native clock root. No arbitration, ready, runtime scheduling or credit.
// REGISTERED BOUNDARY (claude S81 VM F1, 2026-10-15, structural; native pin rule launch O-R <= 220 / capture S+R <= 190,
// no combinational pin-to-pin arc). Every input is a pin register, every output a flop:
//   P    src_v / src_bank (row[7:0] = the bank-hash inputs) registered beside the W0 header's first stage
//   P+1  lane / lv flops (lane function register-to-register: balanced saturating 0/1/2/3+ count tree)
//   P+2  per-bank lane-use u1[k][c] (from the P+1 lane flops and the registered bank)
//   P+3+c  drain flop dr for lane c of bank k (u1 -> u2 -> u3 delay line), at the stage's drain pin register P+4+c
// The drain calendar is derived from this leaf's own lanes (the dispatch o_v observation input cap_v is retired).
// Measured causes: lane from the header outputs was a 34-level in->out path (TT -1119 ps); lane from the source pins
// into a P register 16 levels in->reg (TT -204 ps); drain outputs were combinational from the h registers.
module dsfd_vm_static_wcontrol #(parameter integer NSRC=53)(
 input wire ck_control,rst_n,
 input wire [NSRC-1:0] src_v,input wire [8*NSRC-1:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output reg [2*NSRC-1:0] lane,output reg [NSRC-1:0] lv,
 output reg [31:0] dr_v,output reg [63:0] dr_s,output reg [2:0] own
);
    reg [1:0] rr;
    always @(posedge ck_control or negedge rst_n) if (!rst_n) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    wire rn = rr[1];

    // ---------------------------------------------------------------- root phase observation (fault only)
    // epochs are pin-registered; at edge E the registered value is the producer's E-1 count = control_prev
    reg [2:0] control_epoch, control_prev, e_h; reg [11:0] e_p;
    always @(posedge ck_control) begin
        if (!rn) control_epoch <= 3'd0; else control_epoch <= control_epoch + 3'd1;
        control_prev <= control_epoch; e_h <= header_epoch; e_p <= payload_epoch;
    end
    wire phase_bad = (e_h != control_prev) || (e_p[2:0] != control_prev) || (e_p[5:3] != control_prev) ||
                     (e_p[8:6] != control_prev) || (e_p[11:9] != control_prev);

    // ---------------------------------------------------------------- P: source pin registers
    reg [NSRC-1:0] s_v; reg [8*NSRC-1:0] s_bank;
    always @(posedge ck_control) begin
        s_bank <= src_bank;
        if (!rn) s_v <= {NSRC{1'b0}}; else s_v <= src_v;
    end

    // ---------------------------------------------------------------- P -> P+1: lane function
    function automatic [1:0] sat3(input [1:0] a, input [1:0] b);
        reg [2:0] t; begin t = a + b; sat3 = t[2] ? 2'd3 : t[1:0]; end
    endfunction
    localparam integer NP = 64;                            // tree width >= NSRC
    reg [NSRC-1:0] lane_v_d; reg [2*NSRC-1:0] lane_d; reg lane_bad_d; reg [5*NSRC-1:0] bank_d;
    always @* begin : p_lane integer c, d, w, k; reg [4:0] bc, bd; reg [1:0] t [0:NP-1]; reg [1:0] n;
        lane_bad_d = 1'b0;
        for (c = 0; c < NSRC; c = c + 1) begin
            bc = s_bank[8*c +: 5] ^ {s_bank[8*c+5 +: 3], 2'b00};
            bank_d[5*c +: 5] = bc;
            for (d = 0; d < NP; d = d + 1) begin
                t[d] = 2'd0;
                if (d < c) begin
                    bd = s_bank[8*d +: 5] ^ {s_bank[8*d+5 +: 3], 2'b00};
                    t[d] = {1'b0, s_v[d] && bd == bc};
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
            lane_v_d[c] = s_v[c] && n != 2'd3;
            if (s_v[c] && n == 2'd3) lane_bad_d = 1'b1;
        end
    end
    reg lane_bad; reg [5*NSRC-1:0] bank1;
    always @(posedge ck_control) begin                     // P+1
        lane <= lane_d; bank1 <= bank_d;
        if (!rn) begin lv <= {NSRC{1'b0}}; lane_bad <= 1'b0; end
        else begin lv <= lane_v_d; lane_bad <= lane_bad_d; end
    end

    // ---------------------------------------------------------------- P+2: per-bank lane use, drain calendar
    reg [95:0] u_d;
    always @* begin : p_use integer c, k;
        u_d = 96'd0;
        for (c = 0; c < NSRC; c = c + 1)
            for (k = 0; k < 32; k = k + 1)
                if (lv[c] && bank1[5*c +: 5] == k[4:0]) u_d[3*k + lane[2*c +: 2]] = 1'b1;
    end
    reg [95:0] u1, u2, u3;
    always @(posedge ck_control) begin
        if (!rn) begin u1 <= 96'd0; u2 <= 96'd0; u3 <= 96'd0; end
        else begin u1 <= u_d; u2 <= u1; u3 <= u2; end
    end
    // lane c of bank k: drain flop at P+3+c -> stage drain pin register P+4+c -> stage output register P+5+c ->
    // scatter sample P+6+c
    reg [31:0] dv_d; reg [63:0] ds_d; reg drain_bad;
    always @* begin : p_drain integer k; reg l0, l1, l2;
        drain_bad = 1'b0;
        for (k = 0; k < 32; k = k + 1) begin
            l0 = u1[3*k]; l1 = u2[3*k+1]; l2 = u3[3*k+2];
`ifdef OT_VM_WSCHED_MUT_DRAIN
            l1 = u1[3*k+1];                              // MUTANT: lane 1 drains one edge early
`endif
            dv_d[k] = l0 | l1 | l2;
            ds_d[2*k +: 2] = l0 ? 2'd0 : l1 ? 2'd1 : 2'd2;
            if ((l0 && l1) || (l0 && l2) || (l1 && l2)) drain_bad = 1'b1;
        end
    end
    always @(posedge ck_control) begin
        dr_s <= ds_d;
        if (!rn) dr_v <= 32'd0; else dr_v <= dv_d;
    end

    always @(posedge ck_control) if (!rn) own <= 3'b000; else own <= own | {phase_bad, drain_bad, lane_bad};
endmodule
`default_nettype wire
