`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Physical top of the HBM B2 MTP swap dispatcher S (el1013-ds-mtp-lead [mtp-phys] 2026-10-13): ot_hgi_b2_swap_disp with
// its per-cluster links as separate ports, so the pin plan puts cluster q's down {move 227, v} / up {fault, quiet, src}
// on the face toward cluster q.  Wires only: no logic, no flop (the bench runs the same ot_hgi_b2_swap_disp).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swap_disp_t (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          g_v,
    output wire          g_rdy,
    input  wire          g_last,
    input  wire [1:0]    g_q,
    input  wire [226:0]  g_mv,
    output wire [227:0]  dn0, dn1, dn2, dn3,
    input  wire [2:0]    up0, up1, up2, up3,
    output wire          fence_quiet,
    output wire          done,
    output wire          fault
);
    ot_hgi_b2_swap_disp #(.MUT(0)) u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_rdy(g_rdy), .g_last(g_last), .g_q(g_q),
        .g_mv(g_mv), .dn({dn3, dn2, dn1, dn0}), .up({up3, up2, up1, up0}), .fence_quiet(fence_quiet), .done(done),
        .fault(fault));
endmodule
`default_nettype wire
