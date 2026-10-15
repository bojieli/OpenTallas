`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_landing (claude S81 VM owner r8, 2026-10-14): STATIC LARM.  Row producers that send bare 512-b rows
// (HBM scan service aSW: two rows a beat; selector; collector) land at compiler-armed addresses with NO FIFO, drain
// arbiter, grant, room/credit or timeout (the legacy dsfd_vm_ll landing lanes + drain arbiter + t_cts room are void
// under the owner rule 2026-10-14T18:59).
//   LARM (engine 12 native code 6, arg[20:17] = group, arg[13:0] = base row): group 0 = scan service (lanes 0/1,
//   OFF 0/1, STRIDE 2), group 5 = selector (lane 2, STRIDE 1), group 6 = collector (lane 3, STRIDE 1).  The arm takes
//   effect for rows arriving at the landing pins on edges >= arm edge + 1 and resets the lane's row count.
//   Row k (k = 0, 1, ... since the arm) of lane L is written to base + OFF_L + STRIDE_L * k, full 16-word mask, on
//   write source L at the edge after its arrival (one register stage; the write service adds its own fixed stages).
//   Every row is therefore committed at a fixed, compiler-known cycle; the compiler places the rows so that the static
//   bank rule holds (a violation is a write-service fault, never a delay).
// Faults (sticky): [0] row on an unarmed lane, [1] address beyond 16383, [2] LARM of an unknown group.
// PINREG=1 (native, F8 2026-10-15): every input (LARM control, lane valids, row payload) is captured in a flop at its
// pin and the arm / row logic runs on that copy (native pin audit of the closed r1 view: capture 321 ps on the 22 LARM /
// valid pins that fed the arm compare / row adder / valid AND directly).  Arm and rows are delayed together, so the
// arm-to-row rule is unchanged; every landed row commits ONE edge later (landing age 1 -> 2, compiler constant
// LANDING_AGE).  PINREG=0 = the r1 timing (legacy / equivalence reference).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_static_landing #(parameter integer PINREG=1) (
    input  wire          ck, rst_n,
    input  wire          larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input  wire [3:0]    i_v,                  // lanes: 0/1 scan service rows a0/a1, 2 selector, 3 collector
    // row payload per lane pair (separate ports so each pair has its own pin face): 01 = scan service, 23 = sel/col
    input  wire [1023:0] i_d01, input wire [1023:0] i_d23,
    output reg  [3:0]    o_v,
    output reg  [55:0]   o_row,
    output reg  [1023:0] o_d01, output reg [1023:0] o_d23,
    output reg  [2:0]    fault
);
    // r4 (S-ELEM-A 2026-10-15, PINREG=1): rst_n is captured in a plain pin flop (a data input with its fixed hold stage)
    // and the release chain is synchronous: r3 routed FF -4.4 was rst_n -> rr RESETN removal (async pin path, no hold
    // stage possible) and larm_v -> its sync-reset pin flop (reset AND in front of D, so no pin hold stage).  Every
    // landing register was already synchronously reset by rn; assertion/release now take one more edge (init only).
    reg [1:0] rr; wire rn = rr[1];
    generate if (PINREG != 0) begin : g_rst
        reg rst_q;
        always @(posedge ck) rst_q <= rst_n;
        always @(posedge ck) if (!rst_q) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    end else begin : g_rst_async
        always @(posedge ck or negedge rst_n) if (!rst_n) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    end endgenerate
    // pin stage (PINREG=1): control flops reset by rn, payload flops plain
    wire q_larm_v; wire [3:0] q_larm_g; wire [13:0] q_larm_base; wire [3:0] q_i_v; wire [1023:0] q_d01, q_d23;
    generate if (PINREG != 0) begin : g_pin
        // every pin flop is plain (D straight from the port, fixed hold stage); the reset qualification of the two
        // valid groups is applied after the flop with rn delayed one edge (same values as the former rn-gated D).
        reg p_larm_v; reg [3:0] p_larm_g; reg [13:0] p_larm_base; reg [3:0] p_i_v; reg [1023:0] p_d01, p_d23; reg rn_d;
        always @(posedge ck) begin
            rn_d <= rn; p_larm_v <= larm_v; p_i_v <= i_v;
            p_larm_g <= larm_g; p_larm_base <= larm_base; p_d01 <= i_d01; p_d23 <= i_d23;
        end
        assign q_larm_v = p_larm_v & rn_d; assign q_larm_g = p_larm_g; assign q_larm_base = p_larm_base;
        assign q_i_v = p_i_v & {4{rn_d}}; assign q_d01 = p_d01; assign q_d23 = p_d23;
    end else begin : g_direct
        assign q_larm_v = larm_v; assign q_larm_g = larm_g; assign q_larm_base = larm_base;
        assign q_i_v = i_v; assign q_d01 = i_d01; assign q_d23 = i_d23;
    end endgenerate
    reg [3:0] armed; reg [14:0] nxt [0:3];
`ifdef OT_VM_LANDING_MUT_ROWSKEW
    wire [3:0] rv_mut = i_v;                                  // MUTANT: rows bypass the pin stage, arm/rows misaligned
`else
    wire [3:0] rv_mut = q_i_v;
`endif
    wire [3:0] arm_l = {q_larm_v && q_larm_g == 4'd6, q_larm_v && q_larm_g == 4'd5, q_larm_v && q_larm_g == 4'd0, q_larm_v && q_larm_g == 4'd0};
    always @(posedge ck) begin : p_l integer l; reg [14:0] st;
        if (!rn) begin armed <= 4'd0; o_v <= 4'd0; fault <= 3'd0; end
        else begin
            if (q_larm_v && q_larm_g != 4'd0 && q_larm_g != 4'd5 && q_larm_g != 4'd6) fault[2] <= 1'b1;
            for (l = 0; l < 4; l = l + 1) begin
                st = (l < 2) ? 15'd2 : 15'd1;
                o_v[l] <= rv_mut[l] && armed[l] && nxt[l] < 15'd16384;
                if (rv_mut[l] && !armed[l]) fault[0] <= 1'b1;
                if (rv_mut[l] && armed[l] && nxt[l] >= 15'd16384) fault[1] <= 1'b1;
                o_row[14*l +: 14] <= nxt[l][13:0];
`ifdef OT_VM_LANDING_MUT_STRIDE
                if (rv_mut[l] && armed[l]) nxt[l] <= nxt[l] + 15'd1;                  // MUTANT: scan rows interleave wrong
`else
                if (rv_mut[l] && armed[l]) nxt[l] <= nxt[l] + st;
`endif
                if (arm_l[l]) begin armed[l] <= 1'b1; nxt[l] <= {1'b0, q_larm_base} + ((l == 1) ? 15'd1 : 15'd0); end
            end
        end
    end
    always @(posedge ck) begin o_d01 <= q_d01; o_d23 <= q_d23; end
endmodule
`default_nettype wire
