`timescale 1ns/1ps
// CLAUDE S81-PH ctrl v2 (redesign pass, 2026-10-06): one pseudo-channel TILE of the S81 HBM controller boundary.
// The 8.5 mm dsfd_ctrl slab (ctrl_m4: one cks/ckh tree over 8.5 mm, CTS path depth 98-101) is composed of 32 of these
// tiles (121.068 x 248.376 um, one per PC column at x = p * 265.584 um, the PHY's PC pitch) plus the centre tile
// dsfd_ctrl_ctr (resets / PHY reset / status) and composition-level tie cells for the unused PHY W port inputs
// (physical/s81_ph_views/ctrl/composition.json).  Each tile has its own cks / ckh / rst pins (the die clock tree
// drives every tile), so no tree spans more than one column.
// Function: ot_s81ph_ctrl_pc unchanged (every die pin a flop; PHY k_rdy into the hold register enable is the PHY's
// abutted valid/ready).  Status chain {fault, live}: registered at the tile input from BOTH faces (the unused face is
// tied {0, 1} = neutral by the composition), co on both faces from the one chain flop.  +1 cks per column on the
// status chain only (live / fault are level signals; no data path latency changes).
`default_nettype none
module dsfd_ctrl_pc (
    input  wire [0:0]   cks,
    input  wire [0:0]   ckh,
    input  wire [0:0]   rst,
    input  wire [1:0]   ci_w,
    input  wire [1:0]   ci_e,
    output wire [1:0]   co_w,
    output wire [1:0]   co_e,
    input  wire [340:0] rq,
    output wire [0:0]   rk,
    output wire [0:0]   wd,
    output wire [0:0]   rv,
    output wire [255:0] r_data,
    output wire [16:0]  r_tag,
    output wire [3:0]   r_beat,
    output wire [0:0]   k_v,
    input  wire [0:0]   k_rdy,
    output wire [29:0]  k_addr,
    output wire [3:0]   k_len,
    output wire [16:0]  k_tag,
    output wire [0:0]   k_we,
    output wire [255:0] k_wdata,
    output wire [31:0]  k_wstrb,
    input  wire [0:0]   k_wr_done,
    input  wire [0:0]   kr_v,
    output wire [0:0]   kr_rdy,
    input  wire [16:0]  kr_tag,
    input  wire [3:0]   kr_beat,
    input  wire [255:0] kr_data
);
    // status input register (cks; reset with the column's synchronised reset is not needed: the chain value is
    // only observed after every column's own reset release, and a stale value settles within one cycle)
    reg [1:0] ci_q;
    always @(posedge cks[0]) ci_q <= {ci_w[1] | ci_e[1], ci_w[0] & ci_e[0]};
    wire [1:0] co;
    wire s_ovf;
    ot_s81ph_ctrl_pc u_pc (.cks(cks[0]), .ckh(ckh[0]), .rst(rst[0]), .ci(ci_q), .co(co),
        .rq(rq), .rk(rk[0]), .rv(rv[0]), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .wd(wd[0]), .s_ovf(s_ovf),
        .k_v(k_v[0]), .k_rdy(k_rdy[0]), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we[0]), .k_wdata(k_wdata),
        .k_wstrb(k_wstrb), .k_wr_done(k_wr_done[0]), .kr_v(kr_v[0]), .kr_rdy(kr_rdy[0]), .kr_tag(kr_tag), .kr_beat(kr_beat),
        .kr_data(kr_data));
    assign co_w = co;
    assign co_e = co;
endmodule
`default_nettype wire
