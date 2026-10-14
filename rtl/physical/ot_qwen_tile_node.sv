// q13 spec r5 leaf 2 (2026-10-13): the upper tree node of the W12 ROM tile as a hardened leaf: ot_qwen_me_node_w12 at the
// tile's parameters (W 16, one pin register stage on a / b / va, FP32 pair adders TREE_LAT 7 / ANR 1, y / vy registers).
// The leaf sits at the tile's W face so its a / b / va / y / vy pins ARE the tile's n_a / n_b / n_va / n_y / n_vy pins:
// pin -> flop and flop -> pin inside one short local clock tree.  Parameter-free top (as ot_qwen_tile_lsl).
// Data and valid are a pure re-hierarchy; the fault flag gets a pin register here (+1 cycle on the node's sticky-collected
// fault only).
//
// q14 r5-fp1 (2026-10-13):
//  * t_out / t_vout feed-through: the tile's t_out / t_vout pins lie on the W face BETWEEN n_b and n_y, i.e. inside this
//    leaf's pin band, so the tile's TOREG output pin registers live here: t_d / t_vd enter on the E face (seam), are
//    registered once and leave on the W face.  These ARE the TOREG registers (the parent builds none when NDH = 1):
//    same edge, same value, 0 cycles added.
//  * reset relay: the rst_n pin drives only ot_rst_relay (2 synchroniser + 4 region flops); every reset flop of the leaf
//    hangs on one of 4 region copies (<= ~150 loads each; the port net had 554).  Assert is asynchronous and immediate,
//    release is 3 clk edges later than the pin (no data / valid may arrive in the first 3 cycles after release; the tile
//    is idle for far longer after reset).
// The body below is ot_qwen_me_node_w12 #(W 16, WS 1, TREE_LAT 7, ANR 1) register for register, with the region resets.
module ot_qwen_tile_node (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  a,
    input  wire [511:0]  b,
    input  wire          va,
    output reg  [511:0]  y,
    output wire          vy,
    output wire          fault,
    input  wire [511:0]  t_d,
    input  wire          t_vd,
    output wire [511:0]  t_out,
    output wire          t_vout
);
    wire [3:0] rn;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));

    wire [511:0] ad, bd;
    wire         vd;
    ot_hdc_delay #(.W(1024), .D(1)) u_w (.clk(clk), .rst_n(rn[0]), .d({a, b}), .q({ad, bd}));
    ot_hdc_delay #(.W(1), .D(1), .RESET(1)) u_wv (.clk(clk), .rst_n(rn[0]), .d(va), .q(vd));
    wire [15:0] pf;
    genvar p;
    generate
        for (p = 0; p < 16; p = p + 1) begin : g_add
            wire [31:0] s;
            ot_qwen_w12_tadd #(.LAT(7), .ANR(1)) u_add (clk, rn[p / 4], vd, ad[32*p +: 32], bd[32*p +: 32], s, pf[p]);
            always @(posedge clk) y[32*p +: 32] <= s;
        end
    endgenerate
    ot_hdc_delay #(.W(1), .D(8), .RESET(1)) u_vy (.clk(clk), .rst_n(rn[3]), .d(vd), .q(vy));

    (* keep *) reg fault_q;
    always @(posedge clk or negedge rn[3])
        if (!rn[3]) fault_q <= 1'b0; else fault_q <= |pf;
    assign fault = fault_q;

    // the tile's t_out / t_vout pin registers (TOREG), fed through from the E seam to the W pins
    (* keep *) reg [511:0] t_out_q;
    (* keep *) reg         t_vout_q;
    always @(posedge clk) t_out_q <= t_d;
    always @(posedge clk or negedge rn[1]) if (!rn[1]) t_vout_q <= 1'b0; else t_vout_q <= t_vd;
    assign t_out = t_out_q;
    assign t_vout = t_vout_q;
endmodule
