`timescale 1ns/1ps
// Native numerical glue extracted from ot_dsrom_head_bundle. No die transport adapter.
module ot_dsrom_head_bundle_glue #(
 parameter integer BST=2,
 parameter integer USE_HARD_DELAY8=0,
 parameter integer USE_MIN_DELAY_CELLS=0,
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
    ot_s81_head_min_delay #(.W(512), .D(BST), .ENABLE(USE_MIN_DELAY_CELLS)) u_x (.clk(clk), .rst_n(rst_n), .d({xa, xb}), .q(x_d));
    // systolic lane skew
    genvar j, q, h;
    generate
      if (USE_HARD_DELAY8 && SK != 8) begin : g_unsupported_sk
        // Deliberately fail elaboration rather than silently change skew.
        ERROR_hardened_head_delay_requires_SK8 invalid_configuration();
      end
      for (j = 0; j < 16; j = j + 1) begin : g_sk
        if (USE_HARD_DELAY8) begin : g_hard
          wire [31:0] chain [0:j%8];
          assign chain[0] = {x_d[256+16*j+:16],x_d[16*j+:16]};
          for (h=0; h<j%8; h=h+1) begin : g_stage
            ot_s81_head_delay8x32 u_delay(.clk(clk),.d(chain[h]),.q(chain[h+1]));
          end
          assign {xsa[16*j+:16],xsb[16*j+:16]} = chain[j%8];
        end else begin : g_flat
          ot_s81_head_min_delay #(.W(16), .D(SK * (j % 8)), .ENABLE(USE_MIN_DELAY_CELLS)) u_a (.clk(clk), .rst_n(rst_n), .d(x_d[256 + 16*j +: 16]), .q(xsa[16*j +: 16]));
          ot_s81_head_min_delay #(.W(16), .D(SK * (j % 8)), .ENABLE(USE_MIN_DELAY_CELLS)) u_b (.clk(clk), .rst_n(rst_n), .d(x_d[16*j +: 16]), .q(xsb[16*j +: 16]));
        end
      end
    endgenerate
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
    // Pad only the short payload forwarding branches. Key/row comparison
    // control paths retain their original setup depth and rounding/order.
    wire [31:0] c1_bits0,c1_bits1;
    ot_s81_head_min_buffer #(.W(32),.ENABLE(USE_MIN_DELAY_CELLS)) u_result_payload0(.d(c1[0][31:0]),.q(c1_bits0));
    ot_s81_head_min_buffer #(.W(32),.ENABLE(USE_MIN_DELAY_CELLS)) u_result_payload1(.d(c1[1][31:0]),.q(c1_bits1));
    always @(posedge clk) begin
        c1[0] <= pick({a_key[0], a_row[0], a_bits[0]}, {a_key[1], a_row[1], a_bits[1]});
        c1[1] <= pick({a_key[2], a_row[2], a_bits[2]}, {a_key[3], a_row[3], a_bits[3]});
        {res_row, res_bits} <= pick({c1[0][80:32],c1_bits0}, {c1[1][80:32],c1_bits1});
    end
    assign fault = b_fault | (|a_fault);
endmodule
