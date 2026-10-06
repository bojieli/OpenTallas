`timescale 1ns/1ps
// Native numerical glue extracted from ot_dsrom_head_bundle. No die transport adapter.
module ot_dsrom_head_bundle_glue #(
 parameter integer BST=2,
 parameter [8:0] CUT=9'b1_0111_1011,
 parameter integer SK=1+CUT[0]+CUT[1]+CUT[2]+CUT[3]+CUT[4]+CUT[5]+CUT[6]+CUT[7]+CUT[8]
)(
 input wire clk,rst_n,go,
 input wire [16:0] row0,
 input wire [255:0] xa,xb,
 input wire bo_v,b_fault,
 input wire [31:0] bo_d,
 input wire [3:0] a_done,a_fault,
 input wire [67:0] a_row_flat,
 input wire [127:0] a_bits_flat,a_key_flat,
 output wire go_d,
 output wire [255:0] xsa,xsb,
 output reg [3:0] bv_r,
 output reg [31:0] bd_r,
 output wire [67:0] row0_a,
 output wire [16:0] row0_b,
 output reg res_v,
 output reg [16:0] res_row,
 output reg [31:0] res_bits,
 output wire fault
);
 wire [16:0] a_row[0:3];
 wire [31:0] a_bits[0:3],a_key[0:3];
 genvar a;
 generate for(a=0;a<4;a=a+1) begin:g_ports
   assign a_row[a]=a_row_flat[17*a+:17];
   assign a_bits[a]=a_bits_flat[32*a+:32];
   assign a_key[a]=a_key_flat[32*a+:32];
   assign row0_a[17*a+:17]=row0+17'd32*a;
 end endgenerate
 assign row0_b=17'd0;
    // registered broadcast
    wire [511:0] x_d;
    ot_hdc_delay #(.W(1), .D(BST), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go), .q(go_d));
    ot_hdc_delay #(.W(512), .D(BST)) u_x (.clk(clk), .rst_n(rst_n), .d({xa, xb}), .q(x_d));
    // systolic lane skew
    genvar j, q;
    generate for (j = 0; j < 16; j = j + 1) begin : g_sk
        ot_hdc_delay #(.W(16), .D(SK * (j % 8))) u_a (.clk(clk), .rst_n(rst_n), .d(x_d[256 + 16*j +: 16]), .q(xsa[16*j +: 16]));
        ot_hdc_delay #(.W(16), .D(SK * (j % 8))) u_b (.clk(clk), .rst_n(rst_n), .d(x_d[16*j +: 16]), .q(xsb[16*j +: 16]));
    end endgenerate
    reg [1:0]  bq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin bq <= 2'd0; bv_r <= 4'd0; end
        else begin
            if (go_d) bq <= 2'd0; else if (bo_v) bq <= bq + 2'd1;
            bv_r <= bo_v ? (4'd1 << bq) : 4'd0;
        end
    always @(posedge clk) if (bo_v) bd_r <= bo_d;
    // 2-level compare tree (lowest-id first max): level 1 (0,1) (2,3), level 2
    function automatic [80:0] pick(input [80:0] u, input [80:0] v);   // {key, row, bits}
        pick = (v[80:49] > u[80:49] || (v[80:49] == u[80:49] && v[48:32] < u[48:32])) ? v : u;
    endfunction
    reg [80:0] c1 [0:1];
    reg        c1_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin c1_v <= 1'b0; res_v <= 1'b0; end
        else begin
            c1_v <= &a_done && !go_d;
            res_v <= c1_v && !go_d;
        end
    always @(posedge clk) begin
        c1[0] <= pick({a_key[0], a_row[0], a_bits[0]}, {a_key[1], a_row[1], a_bits[1]});
        c1[1] <= pick({a_key[2], a_row[2], a_bits[2]}, {a_key[3], a_row[3], a_bits[3]});
        {res_row, res_bits} <= pick(c1[0], c1[1]);
    end
    assign fault = b_fault | (|a_fault);
endmodule
