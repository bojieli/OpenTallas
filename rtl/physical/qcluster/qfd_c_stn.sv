`timescale 1ns/1ps
// Q-CLUSTER3 (2026-10-17, coordinator decision HANDOFF 0de+5): the qfd_c_b16_dv fabric stations as small replicated HARD
// tiles.  Each master has its own clock pin and local tree; every data input pin drives a flop D (flop-first) and every
// data output pin is a flop Q (flop-last), so the cluster clock reaches only the child clock pins (station tiles + A0
// leaves + the 1-bit reset stages) instead of ~78k loose fabric flops.  Logic is exactly the soft stations they replace:
//   qfd_c_stn516 / qfd_c_stn514 = qfd_q3h_stn #(.W(516 / 514), .N(1))  (one registered stage, q = d one edge later);
//   qfd_c_xstn                  = qfd_xcst_n without its die strap tie outputs (the cluster left them open).
// No reset on data (static schedule), no ready / credit / backpressure.

module qfd_c_stn516 (
    input  wire         ck,
    input  wire [515:0] d,
    output wire [515:0] q
);
    (* keep *) reg [515:0] q_r;
    always @(posedge ck) q_r <= d;
    assign q = q_r;
endmodule

module qfd_c_stn514 (
    input  wire         ck,
    input  wire [513:0] d,
    output wire [513:0] q
);
    (* keep *) reg [513:0] q_r;
    always @(posedge ck) q_r <= d;
    assign q = q_r;
endmodule

// column station: corridor word b_d (S) -> a_d (N) one edge later, tap_d to the A0 tile (E face; MY for a W-side tile)
module qfd_c_xstn (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [2:0]   sidx,
    input  wire [515:0] b_d,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
    ot_qfd_xcst #(.AW(24), .NW(18), .XOFF(3)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d), .a_r(),
        .b_d(a_d), .b_r(1'b1), .tap_d(tap_d));
endmodule

// the same column station with its tap on the W face (a tile W of the lane: columns 1 and 3).  A separate master, not
// qfd_c_xstn placed MY: a mirrored 34.56-um tile puts its S / N M3 / M5 pins off the track lattice (no width is
// mirror-legal for both the 0.036 M3 and the 0.048 M5 pitch), as qfd_xcst_n_my did.
module qfd_c_xstnw (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [2:0]   sidx,
    input  wire [515:0] b_d,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
    ot_qfd_xcst #(.AW(24), .NW(18), .XOFF(3)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d), .a_r(),
        .b_d(a_d), .b_r(1'b1), .tap_d(tap_d));
endmodule
