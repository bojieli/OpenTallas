`timescale 1ns/1ps
`default_nettype none
// hfd_ckgen (HBM die contract v14, 2026-10-14): the die clock root block.  The four domain clocks come from the PLL hard
// macro (ot_hbm_pll_bb: analog core, its interface is the macro's; Liberty / LEF / GDS are the vendor's) and leave on
// pll_<domain> into the die clock trees (the trees' first levels are the four quadrant roots: per-quadrant phi - R at
// every tile pin).  Each domain's reset release is real logic here: por_n AND the PLL lock, synchronised by two flops
// in the domain's own clock, leaves on por_<domain> (active low = rst_n) into that domain's staged reset tree
// (die-generated hfd_rrl register stages, one per tree level, so the release reaches every sink a fixed number of
// edges later and never as one die-wide net).
module hfd_ckgen (
    input  wire refclk,          // die top pin (bump at the ckgen site)
    input  wire por_n,           // die top pin: power-on reset, active low, asynchronous assert
    output wire pll_stream, output wire pll_serial, output wire pll_hbm, output wire pll_link,
    output wire por_stream, output wire por_serial, output wire por_hbm, output wire por_link
);
    wire locked;
    ot_hbm_pll_bb u_pll (.refclk(refclk), .reset_n(por_n), .clk_stream(pll_stream), .clk_serial(pll_serial),
                         .clk_hbm(pll_hbm), .clk_link(pll_link), .locked(locked));
    // One hardened release leaf per domain (H-HARDEN 10-15): each takes por_n and the PLL lock itself, so the
    // hb_ckgen group is the PLL hard macro + four identical leaves and wires only (no glue gate in the parent).
    hfd_ckgen_rel u_rs (.ck(pll_stream), .por_n(por_n), .locked(locked), .rst_n(por_stream));
    hfd_ckgen_rel u_rr (.ck(pll_serial), .por_n(por_n), .locked(locked), .rst_n(por_serial));
    hfd_ckgen_rel u_rh (.ck(pll_hbm),    .por_n(por_n), .locked(locked), .rst_n(por_hbm));
    hfd_ckgen_rel u_rl (.ck(pll_link),   .por_n(por_n), .locked(locked), .rst_n(por_link));
endmodule

// asynchronous assert, two-flop synchronous release in the domain clock
module hfd_ckgen_rel (input wire ck, input wire por_n, input wire locked, output wire rst_n);
    wire arm_n = por_n & locked;
    reg [1:0] s;
    always @(posedge ck or negedge arm_n)
        if (!arm_n) s <= 2'b00;
        else        s <= {s[0], 1'b1};
    assign rst_n = s[1];
endmodule
`default_nettype wire
