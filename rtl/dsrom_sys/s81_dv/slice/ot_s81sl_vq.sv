`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): vq = the act-quant sub-leaf of one BEAT of a DV vector slice (x5 per slice, own
// clock root).  It takes the beat's normed y from vn (8 lanes a cycle, sub-beats j = 0..7), assembles the two golden
// 32-element act-quant blocks (block 0 = sub-beats 0..3, block 1 = 4..7: blocks are aligned to the slice's 320-element
// ownership, so no amax crosses a beat) and runs them through ot_dsrom_aq12 (tools/hdc_golden_v41.quant_fp8 bit for bit,
// latency 18).  Output = ring-format x beats of this leaf (SLICE_CONTRACT section 3), sent as 4 x 276-b FRAGMENTS (the V
// rung format: fragment 0 = bits [275:0] with the header, then [551:276], [827:552], [1103:828]) on xf with xf_v (fragment
// valid) and xf_s (fragment 0); header: v, kind, hops 1, src sid, idx = the global beat 5 sid + k (straps, captured):
//   XQ  the q family of the beat, payload {e1 10, q1 256, e0 10, q0 256} (dsfd_pq_lx x0 / x1 fields)
//   XB  the BF16 family: the 64 normed y as BF16 (lane l at payload [16 l +: 16]) for BF16 field phases
// The gather mode (m_q / m_b, set per norm by vp) selects the families.  The beats leave STAGGERED by the leaf strap k
// with stride 4 (one V rung beat = 4 x 276-b fragments): XQ at q + 4k, XB at q + 20 + 4k (q = the quantiser output
// edge), so the 5 leaves' beats reach the ring stop one every 4 cycles (equal-latency glue paths) and are injected on
// the tier line and sent over the V rung without any staging.
// Every input lands in a flop; every output leaves a flop.  Static schedule: a y beat index out of order is a fault.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vq (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          y_v,
    input  wire [2:0]    y_i,
    input  wire [255:0]  y,
    input  wire [3:0]    sid,        // straps: slice id, leaf index
    input  wire [2:0]    k,
    input  wire          m_v,        // gather mode for the next norm: families q / BF16
    input  wire          m_q,
    input  wire          m_b,
    output reg           xf_v,
    output reg           xf_s,
    output reg  [275:0]  xf,
    output reg           fault
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_q = rsv[1];
    reg yv_c; reg [2:0] yi_c; reg [255:0] y_c; reg [3:0] sid_c; reg [2:0] k_c; reg mq, mb;
    always @(posedge clk or negedge rs_c) if (!rs_c) yv_c <= 1'b0; else yv_c <= y_v;
    always @(posedge clk) begin yi_c <= y_i; y_c <= y; sid_c <= sid; k_c <= k; end
    always @(posedge clk or negedge rs_c) if (!rs_c) begin mq <= 1'b1; mb <= 1'b0; end else if (m_v) begin mq <= m_q; mb <= m_b; end
    // block assembly: 4 sub-beats of 8 FP32 words -> 32 words; BF16 copy of all 64
    reg [1023:0] blk; reg bv, bbk; reg [2:0] nexp; reg ord_f;
    reg [1023:0] bf;
    integer l, j;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin bv <= 1'b0; nexp <= 3'd0; ord_f <= 1'b0; end
        else begin
            bv <= yv_c && yi_c[1:0] == 2'd3;
            if (yv_c) begin nexp <= yi_c + 3'd1; if (yi_c != nexp) ord_f <= 1'b1; end
        end
    always @(posedge clk) bbk <= yi_c[2];
    always @(posedge clk)
        if (yv_c) begin
            for (j = 0; j < 4; j = j + 1) if (yi_c[1:0] == j) blk[256 * j +: 256] <= y_c;
            for (j = 0; j < 8; j = j + 1) if (yi_c == j) for (l = 0; l < 8; l = l + 1) bf[(8 * j + l) * 16 +: 16] <= y_c[l * 32 + 16 +: 16];
        end
    // the quantiser registers x itself (aq12 S0): blk feeds it directly; bv is high in the cycle after the block's last
    // sub-beat was written, so aq12 samples the complete block (the next sub-beat lands on the same edge)
    wire vo, af; wire [255:0] q; wire signed [9:0] e; wire [511:0] qy;
    ot_dsrom_aq12 u_aq (.clk(clk), .rst_n(rs_q), .v(bv), .x(blk), .vo(vo), .q(q), .e(e), .y(qy), .fault(af));
    // block index rides the quantiser latency
    wire blo;
    ot_hdc_delay #(.W(1), .D(18)) u_bi (.clk(clk), .rst_n(rs_q), .d(bbk), .q(blo));
    reg [255:0] q0; reg [9:0] e0; reg [531:0] xqd;   // the BF16 family is read from bf (stable until the next norm)
    // stagger: a step counter from the quantiser output; XQ leaves at step 4k, XB at step 20 + 4k
    reg [5:0] st; reg run;
    wire [1103:0] xb_full;
    wire [7:0] gidx = {2'b00, sid_c, 2'b00} + {4'd0, sid_c} + {5'd0, k_c};   // 5 sid + k
    // the beat being sent: header {idx, src sid, hops 1, kind, v} + payload
    assign xb_full = (st >= 6'd20) ? {59'd0, bf, gidx, sid_c, 5'd1, 3'd2, 1'b1} : {551'd0, xqd, gidx, sid_c, 5'd1, 3'd1, 1'b1};
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin run <= 1'b0; st <= 6'd0; xf_v <= 1'b0; xf_s <= 1'b0; fault <= 1'b0; end
        else begin
            if (vo && blo) begin run <= 1'b1; st <= 6'd0; end
            else if (run) begin st <= st + 6'd1; if (st == 6'd39) run <= 1'b0; end
            xf_v <= run && ((mq && st[5:2] == {1'b0, k_c}) || (mb && st[5:2] == 4'd5 + {1'b0, k_c}));
            xf_s <= run && ((mq && st == {1'b0, k_c, 2'b00}) || (mb && st == 6'd20 + {1'b0, k_c, 2'b00}));
            fault <= fault | (vo && af) | ord_f | (vo && blo && run);
        end
    always @(posedge clk) begin
        if (vo && !blo) begin q0 <= q; e0 <= e; end
        if (vo && blo) xqd <= {e, q, e0, q0};
        case (st[1:0])
            2'd0: xf <= xb_full[275:0];
            2'd1: xf <= xb_full[551:276];
            2'd2: xf <= xb_full[827:552];
            default: xf <= xb_full[1103:828];
        endcase
    end
endmodule
