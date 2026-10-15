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
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_static_landing (
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
    reg [1:0] rr;
    always @(posedge ck or negedge rst_n) if (!rst_n) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    wire rn = rr[1];
    reg [3:0] armed; reg [14:0] nxt [0:3];
    wire [3:0] arm_l = {larm_v && larm_g == 4'd6, larm_v && larm_g == 4'd5, larm_v && larm_g == 4'd0, larm_v && larm_g == 4'd0};
    always @(posedge ck) begin : p_l integer l; reg [14:0] st;
        if (!rn) begin armed <= 4'd0; o_v <= 4'd0; fault <= 3'd0; end
        else begin
            if (larm_v && larm_g != 4'd0 && larm_g != 4'd5 && larm_g != 4'd6) fault[2] <= 1'b1;
            for (l = 0; l < 4; l = l + 1) begin
                st = (l < 2) ? 15'd2 : 15'd1;
                o_v[l] <= i_v[l] && armed[l] && nxt[l] < 15'd16384;
                if (i_v[l] && !armed[l]) fault[0] <= 1'b1;
                if (i_v[l] && armed[l] && nxt[l] >= 15'd16384) fault[1] <= 1'b1;
                o_row[14*l +: 14] <= nxt[l][13:0];
`ifdef OT_VM_LANDING_MUT_STRIDE
                if (i_v[l] && armed[l]) nxt[l] <= nxt[l] + 15'd1;                  // MUTANT: scan rows interleave wrong
`else
                if (i_v[l] && armed[l]) nxt[l] <= nxt[l] + st;
`endif
                if (arm_l[l]) begin armed[l] <= 1'b1; nxt[l] <= {1'b0, larm_base} + ((l == 1) ? 15'd1 : 15'd0); end
            end
        end
    end
    always @(posedge ck) begin o_d01 <= i_d01; o_d23 <= i_d23; end
endmodule
`default_nettype wire
