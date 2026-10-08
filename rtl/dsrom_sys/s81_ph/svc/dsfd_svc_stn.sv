`timescale 1ns/1ps
// dsfd_svc_stn -- link station TILE of the scan service (CLAUDE S81-PH svc, 2026-10-06): one quadrant <-> IO hub
// link crosses up to ~6.5 mm of the 8.5-mm svc slab (hub at the N-E pin group, quadrants 0..2 to its west), so the
// composition chains stations every <= 430 um (stream 1.2 GHz SS reach ~504 um / stage).  One station carries:
//   q   hub -> quadrant (E -> W), 515 b, valid-only (bit 0 = v): one register (valid reset)
//   od  quadrant -> hub (W -> E), 512 b valid / ready: 2-slot skid (registered valid, data and ready)
//   a0  quadrant -> hub (W -> E), 512 b valid / ready: 2-slot skid
// Every pin is a flop (or the skid's registered ready); latency-insensitive, full throughput, +1 cycle per station.
module dsfd_svc_stn (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,          // async die reset (active low), synchronised here
    input  wire [514:0] q_e,          // from the hub side (E)
    output reg  [514:0] q_w,          // to the quadrant side (W)
    input  wire [0:0]   od_wv,        // from the quadrant side (W)
    input  wire [511:0] od_wd,
    output wire [0:0]   od_wr,
    output wire [0:0]   od_ev,        // to the hub side (E)
    output wire [511:0] od_ed,
    input  wire [0:0]   od_er,
    input  wire [0:0]   a0_wv,
    input  wire [511:0] a0_wd,
    output wire [0:0]   a0_wr,
    output wire [0:0]   a0_ev,
    output wire [511:0] a0_ed,
    input  wire [0:0]   a0_er
);
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rn = rst_s[1];
    always @(posedge ck[0] or negedge rn) if (!rn) q_w[0] <= 1'b0; else q_w[0] <= q_e[0];
    always @(posedge ck[0]) q_w[514:1] <= q_e[514:1];
    ot_s81ph_skid2 #(.W(512)) u_od (.clk(ck[0]), .rst_n(rn), .in_v(od_wv[0]), .in_r(od_wr[0]), .in_d(od_wd),
        .out_v(od_ev[0]), .out_r(od_er[0]), .out_d(od_ed));
    ot_s81ph_skid2 #(.W(512)) u_a0 (.clk(ck[0]), .rst_n(rn), .in_v(a0_wv[0]), .in_r(a0_wr[0]), .in_d(a0_wd),
        .out_v(a0_ev[0]), .out_r(a0_er[0]), .out_d(a0_ed));
endmodule
