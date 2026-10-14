`timescale 1ns/1ps
// q18 (2026-10-13) MEASUREMENT VEHICLE, not a product: the clock skeleton of a thin qfd_tile_nk parent.  The 14 closed
// hard children of floorplan r5-fp1 (5 x ot_qwen_tile_rpair, ot_qwen_tile_node, 8 x ot_qwen_tile_lsl) at their r5-fp1
// places, the tile's clk / rst_n pins, and NO parent register: the parent clock net has 14 child clock pins and nothing
// else.  The --cts gate on this kit measures what a wires-only tile parent can reach from the slot's single clk pin
// (E face, y 660-664): distribution delay to the farthest child pin + that child's own insertion.  Data pins are tied
// off; no function is claimed.
module ot_qwen_tile_nk_ckskel (
    input  wire clk,
    input  wire rst_n,
    output wire fault
);
    wire [4:0]  nf;
    wire [7:0]  tf;
    wire        ndf;
    genvar i;
    generate
        for (i = 0; i < 5; i = i + 1) begin : g_rp
            wire [1023:0] rq;
            ot_qwen_tile_rpair u_rp (.clk(clk), .rst_n(rst_n), .ce_d(1'b0), .any_d(1'b0), .ad_d(12'd0), .r_q(rq));
            assign nf[i] = rq[0];
        end
        for (i = 0; i < 8; i = i + 1) begin : g_sl
            wire [63:0] t; wire [7:0] lf;
            ot_qwen_tile_lsl u_lh (.clk(clk), .rst_n(rst_n), .v_d(1'b0), .first_d(1'b0), .split_d(4'd0), .w_d(256'd0),
                                   .x_d(128'd0), .t_out(t), .lfault(lf), .tfault(tf[i]));
        end
    endgenerate
    wire [511:0] y, to; wire vy, tvo;
    ot_qwen_tile_node u_node (.clk(clk), .rst_n(rst_n), .a(512'd0), .b(512'd0), .va(1'b0), .y(y), .vy(vy), .fault(ndf),
                              .t_d(512'd0), .t_vd(1'b0), .t_out(to), .t_vout(tvo));
    assign fault = ndf | (|tf) | (|nf);
endmodule
