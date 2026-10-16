`timescale 1ns/1ps
`default_nettype none
// F20 registered distribution tree relay (H-NETLIST/H-ELEM 1445, H-DIE d4a census: the flat F20 broadcast -- 320 nets,
// fanout 106, 55.7 mm -- cost ~4.6M repair buffers). ONE master, hardened once, placed by H-DIE as tree nodes.
// Frame (320 b) = {launch_v, desc_loops[15:0], desc_limit[12:0], desc_base[11:0], desc_v, cfg_data[255:0],
// cfg_addr[11:0], cfg_target[7:0], cfg_v}. Static: no ready/credit/backpressure; every node adds exactly LAT = 2 edges
// (input pin flop, then one flop bank per output face group), so a sink at tree depth d sees the host frame
// 2d edges later. The compiler charges ONE constant for every sink (H-DIE equalises depths: idle branch nodes are
// the same master), so programme frame-to-frame gaps are unchanged (they are relative to the target's capture).
// Outputs o0..o3 are flop Q (one flop bank per output, placed at its face); unused outputs are left open.
// MUT (bench): 1 = output 2 drops cfg_data[17] (data path), 2 = output 1 one edge early (latency).
module ot_hgi_f20_relay4 #(parameter integer MUT = 0)(
 input  wire         clk,
 input  wire         rst_n,
 input  wire [319:0] fi,
 output wire [319:0] o0, o1, o2, o3
);
 // Only the 3 valid bits (cfg_v [0], desc_v [277], launch_v [319]) carry RESETN (15 loads, no 1.6k-load reset net);
 // the payload is unreset and ignored by every target unless its frame's valid bit is set.
 wire [319:0] fq, q0, q1, q2, q3;
 wire [319:0] o1n = (MUT == 2) ? fi : fq;
 wire [319:0] o2n = (MUT == 1) ? (fq & ~(320'd1 << 21)) : fq;
 for (genvar i = 0; i < 320; i = i + 1) begin : g_b
  if (i == 0 || i == 277 || i == 319) begin : g_v
   reg f, a, b, c, d;
   always @(posedge clk or negedge rst_n)
    if (!rst_n) begin f <= 1'b0; a <= 1'b0; b <= 1'b0; c <= 1'b0; d <= 1'b0; end
    else begin f <= fi[i]; a <= fq[i]; b <= o1n[i]; c <= o2n[i]; d <= fq[i]; end
   assign fq[i] = f; assign q0[i] = a; assign q1[i] = b; assign q2[i] = c; assign q3[i] = d;
  end else begin : g_p
   reg f, a, b, c, d;
   always @(posedge clk) begin f <= fi[i]; a <= fq[i]; b <= o1n[i]; c <= o2n[i]; d <= fq[i]; end
   assign fq[i] = f; assign q0[i] = a; assign q1[i] = b; assign q2[i] = c; assign q3[i] = d;
  end
 end
 assign o0 = q0; assign o1 = q1; assign o2 = q2; assign o3 = q3;
endmodule

`default_nettype wire
