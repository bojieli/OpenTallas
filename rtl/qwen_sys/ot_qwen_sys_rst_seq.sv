`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_sys_rst_seq: power-up / reset sequencer of the Qwen ROM system top.
// NEW.  Every release is conditioned on a condition produced by real RTL:
//
//   POR      por_n (asynchronous) is conditioned by ot_reset_sync; the host
//            side (host interface, CSRs) leaves reset first so the host can
//            read SYS_STATUS while the rest of the system boots.
//   LINK     the die-to-die link layers leave reset and train; the step ends
//            when every link reports link_up (both ends saw UPN good flits).
//   HBM      the KV services leave reset and run their HBM round-trip check
//            (pattern write, tagged write-done, read-back compare); the step
//            ends when every die reports boot_done, and fails if any boot_ok
//            is low.
//   DIE      the decode cores, sequencers and collective engines leave reset.
//   READY    sys_ready: the package controller may accept host steps.
// Each wait has a bound (cycles); a missed bound or a failed check stops the
// sequence in FAULT with boot_err = the step that failed (1 link, 2 HBM
// timeout, 3 HBM check).  soft_rst (a CSR write) re-runs LINK..READY with the
// host side kept out of reset.
// ---------------------------------------------------------------------------
module ot_qwen_sys_rst_seq #(
    parameter integer NL       = 12,      // link ends
    parameter integer ND       = 4,       // dies
    parameter integer T_LINK   = 20000,
    parameter integer T_HBM    = 20000,
    parameter integer T_SETTLE = 4
) (
    input  wire          clk,
    input  wire          por_n,
    input  wire          soft_rst,
    input  wire [NL-1:0] link_up,
    input  wire [ND-1:0] boot_done,
    input  wire [ND-1:0] boot_ok,
    output wire          host_rst_n,
    output reg           link_rst_n,
    output reg           hbm_rst_n,
    output reg           boot_go,
    output reg           die_rst_n,
    output reg           sys_ready,
    output reg           boot_fault,
    output reg  [3:0]    boot_state,
    output reg  [3:0]    boot_err,
    output reg  [31:0]   boot_cycles
);
    localparam [3:0] S_POR = 0, S_LINK = 1, S_HBM = 2, S_HBMW = 3, S_DIE = 4, S_READY = 5, S_FAULT = 6;
    wire rst_n;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_por (.clk(clk), .async_rst_n(por_n), .sync_rst_n(rst_n));
    assign host_rst_n = rst_n;
    reg [31:0] t;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            boot_state <= S_POR; link_rst_n <= 1'b0; hbm_rst_n <= 1'b0; boot_go <= 1'b0; die_rst_n <= 1'b0;
            sys_ready <= 1'b0; boot_fault <= 1'b0; boot_err <= 0; t <= 0; boot_cycles <= 0;
        end else begin
            boot_go <= 1'b0;
            t <= t + 1;
            if (!sys_ready && !boot_fault) boot_cycles <= boot_cycles + 1;
            if (soft_rst) begin
                boot_state <= S_POR; link_rst_n <= 1'b0; hbm_rst_n <= 1'b0; die_rst_n <= 1'b0;
                sys_ready <= 1'b0; boot_fault <= 1'b0; boot_err <= 0; t <= 0; boot_cycles <= 0;
            end else case (boot_state)
                S_POR: if (t >= T_SETTLE) begin link_rst_n <= 1'b1; t <= 0; boot_state <= S_LINK; end
                S_LINK:
                    if (&link_up) begin hbm_rst_n <= 1'b1; t <= 0; boot_state <= S_HBM; end
                    else if (t >= T_LINK) begin boot_fault <= 1'b1; boot_err <= 4'd1; boot_state <= S_FAULT; end
                S_HBM: if (t >= T_SETTLE) begin boot_go <= 1'b1; t <= 0; boot_state <= S_HBMW; end
                S_HBMW:
                    if (&boot_done) begin
                        if (&boot_ok) begin die_rst_n <= 1'b1; t <= 0; boot_state <= S_DIE; end
                        else begin boot_fault <= 1'b1; boot_err <= 4'd3; boot_state <= S_FAULT; end
                    end else if (t >= T_HBM) begin boot_fault <= 1'b1; boot_err <= 4'd2; boot_state <= S_FAULT; end
                S_DIE: if (t >= T_SETTLE) begin sys_ready <= 1'b1; boot_state <= S_READY; end
                S_READY: ;
                default: ;
            endcase
        end
    end
endmodule
