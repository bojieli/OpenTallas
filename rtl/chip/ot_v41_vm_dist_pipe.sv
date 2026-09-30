`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// D register stages of a VM_DIST tree (rtl/chip/ot_v41_vm_dist.sv): a write
// bundle entering in cycle t leaves in cycle t + D and lands in the lane-group
// banks at the end of that cycle -- D cycles after it would have landed in the
// flat vector memory.
//
// pending: a write that has not yet reached the last stage is in flight (this
// cycle's input included).  The last stage is excluded: its write lands at the
// end of this cycle, so a reader released now (issued at this edge) reads it --
// the chaining protocol's "written".  A producer's idle / ready are ANDed with
// !pending (ot_hdc_core_v41x VM_DIST).  D = 0: a wire.
// ---------------------------------------------------------------------------
module ot_v41_vm_dist_pipe #(
    parameter integer W = 32,
    parameter integer D = 6
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [W-1:0] d,
    output wire         v_o,
    output wire [W-1:0] d_o,
    output wire         pending
);
    generate if (D == 0) begin : g_wire
        assign v_o = v; assign d_o = d; assign pending = 1'b0;
    end else begin : g_pipe
        reg [D-1:0] pv;
        reg [W-1:0] pd [0:D-1];
        integer k;
        integer j;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) pv <= 0;
            else begin
                pv[0] <= v;
                for (j = 1; j < D; j = j + 1) pv[j] <= pv[j-1];
            end
        always @(posedge clk) begin
            pd[0] <= d;
            for (k = 1; k < D; k = k + 1) pd[k] <= pd[k-1];
        end
        assign v_o = pv[D-1];
        assign d_o = pd[D-1];
        wire [D-1:0] early = {pv[D-1:0] & ~(D'(1) << (D-1))};      // every stage but the last
        assign pending = v || (|early);
    end endgenerate
endmodule
