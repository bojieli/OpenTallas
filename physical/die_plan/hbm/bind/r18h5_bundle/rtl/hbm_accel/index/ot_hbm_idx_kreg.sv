`timescale 1ns/1ps
`default_nettype none
// KEPT COPY primitives for the FAN32 IDX root (HBM-IDX6 2026-10-20; safe-design checklist item 3 / native32 census).
// Every replicated control register of ot_hbm_idx_topk_static_f32 / ot_hbm_idx_calendar_static_f32 / the F32 share
// leaf is ONE instance of ot_hbm_idx_kreg per copy: the module carries (* keep_hierarchy *) on its DEFINITION, so every
// $paramod derivative keeps it (tools/ref_tile/keep_module_audit.py: a kit SYNTH_KEEP_MODULES entry would not match a
// parameterised instance) and opt_merge can never fold two copies with the same D back into one register (they are
// cells of different hierarchy instances, not identical $dff cells of one module). A copy instance holds DISTINCT
// signals only (W bits = W different D nets), so nothing inside it can merge either.
// ot_hbm_idx_kbetter: the TOPK tournament comparator (entry total order: value descending, id ascending; TIEHI the bench
// mutant MUT 2) as a kept combinational instance, so a mux whose select would drive 54 bits is split over two
// comparator copies (ABC strash would merge two copies of the same cone inside one module).
(* keep_hierarchy *)
module ot_hbm_idx_kreg #(
    parameter integer W = 1,
    parameter integer RST = 0,             // 1: asynchronous active-low clear to RV
    parameter [W-1:0] RV = {W{1'b0}}
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    generate if (RST != 0) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= RV; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule

(* keep_hierarchy *)
module ot_hbm_idx_kbetter #(
    parameter integer IDW = 20,
    parameter integer TIEHI = 0
) (
    input  wire [IDW+33:0] x,
    input  wire [IDW+33:0] y,
    output wire            b                 // x beats y
);
    localparam integer EW = IDW + 34;
    assign b = x[EW-1] && (!y[EW-1] || x[IDW+32:IDW+1] > y[IDW+32:IDW+1] ||
               (x[IDW+32:IDW+1] == y[IDW+32:IDW+1] && ((TIEHI != 0) ? x[IDW-1:0] > y[IDW-1:0] : x[IDW-1:0] < y[IDW-1:0])));
endmodule
`default_nettype wire
