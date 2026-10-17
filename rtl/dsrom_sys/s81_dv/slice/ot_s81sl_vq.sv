`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): vq = the act-quant sub-leaf of one BEAT of a DV vector slice (x5 per slice, own
// clock root).  It takes the beat's normed y from vn (8 lanes a cycle, sub-beats j = 0..7), assembles the two golden
// 32-element act-quant blocks (block 0 = sub-beats 0..3, block 1 = 4..7: blocks are aligned to the slice's 320-element
// ownership, so no amax crosses a beat) and runs them through ot_dsrom_aq12 (tools/hdc_golden_v41.quant_fp8 bit for bit,
// latency 18).  Outputs, both to the slice's ring / x path:
//   xq  the q family of the beat, the lane packing {e1 10, q1 256, e0 10, q0 256} (dsfd_pq_lx x0 / x1 fields)
//   xb  the BF16 family of the beat: the 64 normed y as BF16 (lane l at [16 l +: 16]) for BF16 field phases
// Every input lands in a flop; every output leaves a flop.  Static schedule: a y beat index out of order is a fault.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vq (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          y_v,
    input  wire [2:0]    y_i,
    input  wire [255:0]  y,
    output reg           xq_v,
    output reg  [531:0]  xq_d,
    output reg           xb_v,
    output reg  [1023:0] xb_d,
    output reg           fault
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_q = rsv[1];
    reg yv_c; reg [2:0] yi_c; reg [255:0] y_c;
    always @(posedge clk or negedge rs_c) if (!rs_c) yv_c <= 1'b0; else yv_c <= y_v;
    always @(posedge clk) begin yi_c <= y_i; y_c <= y; end
    // block assembly: 4 sub-beats of 8 FP32 words -> 32 words; BF16 copy of all 64
    reg [1023:0] blk; reg bv, bbk; reg [2:0] nexp; reg ord_f;
    reg [1023:0] bf;
    integer l;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin bv <= 1'b0; nexp <= 3'd0; ord_f <= 1'b0; end
        else begin
            bv <= yv_c && yi_c[1:0] == 2'd3;
            if (yv_c) begin nexp <= yi_c + 3'd1; if (yi_c != nexp) ord_f <= 1'b1; end
        end
    always @(posedge clk) bbk <= yi_c[2];
    always @(posedge clk)
        if (yv_c) begin
            blk[yi_c[1:0] * 256 +: 256] <= y_c;
            for (l = 0; l < 8; l = l + 1) bf[(yi_c * 8 + l) * 16 +: 16] <= y_c[l * 32 + 16 +: 16];
        end
    reg [1023:0] aqx; reg aqv; reg aqb;
    always @(posedge clk or negedge rs_q) if (!rs_q) aqv <= 1'b0; else aqv <= bv;
    always @(posedge clk) begin aqx <= blk; aqb <= bbk; end
    wire vo, af; wire [255:0] q; wire signed [9:0] e; wire [511:0] qy;
    ot_dsrom_aq12 u_aq (.clk(clk), .rst_n(rs_q), .v(aqv), .x(aqx), .vo(vo), .q(q), .e(e), .y(qy), .fault(af));
    // block index rides the quantiser latency
    wire blo;
    ot_hdc_delay #(.W(1), .D(18)) u_bi (.clk(clk), .rst_n(rs_q), .d(aqb), .q(blo));
    reg [255:0] q0; reg [9:0] e0;
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin xq_v <= 1'b0; xb_v <= 1'b0; fault <= 1'b0; end
        else begin
            xq_v <= vo && blo;
            xb_v <= vo && blo;
            fault <= fault | (vo && af) | ord_f;
        end
    always @(posedge clk) begin
        if (vo && !blo) begin q0 <= q; e0 <= e; end
        if (vo && blo) begin xq_d <= {e, q, e0, q0}; xb_d <= bf; end
    end
endmodule
