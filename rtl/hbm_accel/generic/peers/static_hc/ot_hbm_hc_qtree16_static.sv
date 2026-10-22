`timescale 1ns/1ps
`default_nettype none
// HC quarter-hub TREE SLICE (HBM-HCBANK6 10-20, QHUB SAFE 2): one hard child of ot_hbm_hc_qhub_static / ot_hbm_hc_qcen_static
// SAFE 2 = levels 1..4 of the centre's 6-level pairwise subtree over 16 consecutive chunk sums (chunks 16c..16c+15 of
// bank 0's chain exit s_i), one master instanced x4 (g_qt[c].u_t).  Bit for bit the SAFE 1 subtree nodes:
//   pin register  s_q <= s_in (the SAFE 1 s_i pin register, this slice's 512 b) and vq <= v_i (the parent hands the leaf
//                 valid ONE edge early, vl[VD-2], so vq == the SAFE 1 leaf_v on the edge s_q holds the chunk sums);
//   nodes         15 x ot_hdc_fp32_add_lat_fan32 #(LAT 7, DRST 0, SAFE_DIST 1) (the reviewed native-fanout LAT-7 graph,
//                 520dbea3a: SAT-proven equal to ot_hdc_fp32_add_lat LAT 7 / DRST 0, every mapped driver <= 32 loads);
//                 node index n = OFF(l) + i as in ot_hbm_hc_qcen_static (l 1: 0..7, l 2: 8..11, l 3: 12..13, l 4: 14);
//   outputs       every node's valid_out / err (adder output registers, for the parent's sticky ps_f OR on the SAME edge)
//                 and the level-4 node y / valid (the parent's level-5 operands).  Every output pin is a flop.
//   reset         rst_n -> ot_rst_relay, 8 kept regions (2 adders = 14 async valid clears a copy); the kit lands rst_n in
//                 2 stages at the face first.  Release is a constant; tasks arrive long after reset.
// MUT (bench): 4 = level-1 pairs (0,2),(1,3) (the centre MUT 4, which never leaves a 4-chunk group).
module ot_hbm_hc_qtree16_static #(parameter integer TLA = 7, parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire          v_i,
    input  wire [511:0]  s_in,
    output wire [31:0]   y,
    output wire          v,
    output wire [14:0]   nv_o,
    output wire [29:0]   e_o
);
    initial if (TLA != 7) $fatal(1, "qtree16: the native-fanout adder graph is qualified for LAT 7 only");
    wire [7:0] rr;
    ot_rst_relay #(.REGIONS(8)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg vq; reg [511:0] s_q;
    always @(posedge clk or negedge rr[7]) if (!rr[7]) vq <= 1'b0; else vq <= v_i;
    always @(posedge clk) s_q <= s_in;
    wire [16*32-1:0] lv0;
    for (genvar i = 0; i < 16; i = i + 1) begin : g_perm
        localparam integer SRC = (MUT == 4) ? ((i & ~3) | ((i & 1) << 1) | ((i >> 1) & 1)) : i;
        assign lv0[i*32 +: 32] = s_q[SRC*32 +: 32];
    end
    wire [15*32-1:0] nd; wire [14:0] nvv; wire [29:0] ee;
    for (genvar l = 1; l <= 4; l = l + 1) begin : g_lvl
        localparam integer N = 16 >> l, OFF = 16 - (32 >> l), POFF = 16 - (64 >> l);
        for (genvar i = 0; i < N; i = i + 1) begin : g_n
            wire [31:0] a, b; wire va;
            if (l == 1) begin : g_leaf
                assign a = lv0[(2*i)*32 +: 32]; assign b = lv0[(2*i+1)*32 +: 32]; assign va = vq;
            end else begin : g_up
                assign a = nd[(POFF + 2*i)*32 +: 32]; assign b = nd[(POFF + 2*i + 1)*32 +: 32]; assign va = nvv[POFF + 2*i];
            end
            ot_hdc_fp32_add_lat_fan32 #(.LAT(TLA), .DRST(0), .SAFE_DIST(1)) u_a (.clk(clk), .rst_n(rr[(OFF + i) / 2]),
                .valid_in(va), .a(a), .b(b), .y(nd[(OFF + i)*32 +: 32]), .err(ee[(OFF + i)*2 +: 2]), .valid_out(nvv[OFF + i]));
        end
    end
    assign y = nd[14*32 +: 32]; assign v = nvv[14]; assign nv_o = nvv; assign e_o = ee;
endmodule
`default_nettype wire
