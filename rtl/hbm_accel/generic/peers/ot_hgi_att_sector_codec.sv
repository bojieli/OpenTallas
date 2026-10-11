`timescale 1ns/1ps
`default_nettype none
// Exact sector codec. One additional output capture; SRAM stays outside.
module ot_hgi_att_sector_codec #(parameter integer MUT_ADDR=0) (
 input wire clk, rst_n, in_v,
 input wire [255:0] in_data,
 input wire [7:0] in_tag,
 input wire [1:0] in_es,
 output reg out_v,
 output reg [255:0] out_codes,
 output reg [31:0] out_mask, out_bad,
 output reg [7:0] out_addr
);
 reg vq; reg [255:0] dq; reg [7:0] tq; reg [1:0] eq;
 always @(posedge clk) begin dq <= in_data; tq <= in_tag; eq <= in_es; end
 always @(posedge clk or negedge rst_n)
  if (!rst_n) begin vq <= 0; out_v <= 0; end
  else begin vq <= in_v; out_v <= vq; end
    function automatic [8:0] e4m3(input [31:0] x);     // {bad, code}
        reg [7:0] e; reg [22:0] m; integer E; reg [3:0] sig;
        begin
            e = x[30:23]; m = x[22:0]; E = e - 127; sig = {1'b1, m[22:20]};
            if (x[30:0] == 31'd0) e4m3 = {1'b0, x[31], 7'd0};
            else if (e == 8'd0 || e == 8'hFF || m[19:0] != 20'd0) e4m3 = 9'h100;
            else if (E >= -6 && E <= 8) begin
                if (E == 8 && m[22:20] == 3'd7) e4m3 = 9'h100;
                else e4m3 = {1'b0, x[31], 4'(E + 7), m[22:20]};
            end
            else if (E == -7) e4m3 = sig[0] ? 9'h100 : {1'b0, x[31], 4'd0, sig[3:1]};
            else if (E == -8) e4m3 = (sig[1:0] != 0) ? 9'h100 : {1'b0, x[31], 4'd0, 1'b0, sig[3:2]};
            else if (E == -9) e4m3 = (sig[2:0] != 0) ? 9'h100 : {1'b0, x[31], 4'd0, 2'b00, sig[3]};
            else e4m3 = 9'h100;
        end
    endfunction
 integer i; reg [8:0] c;
 always @(posedge clk) begin
  out_addr <= (tq >> eq) ^ (MUT_ADDR ? 8'd1 : 8'd0);
  for (i=0;i<32;i=i+1) begin
   c = eq == 0 ? {1'b0,dq[8*i +: 8]} :
       eq == 1 ? e4m3({dq[16*(i%16) +: 16],16'd0}) :
                 e4m3(dq[32*(i%8) +: 32]);
   out_codes[8*i +: 8] <= c[7:0];
   out_mask[i] <= eq == 0 || (eq == 1 && tq[0] == i/16) ||
                            (eq == 2 && tq[1:0] == i/8);
   out_bad[i] <= c[8];
  end
 end
endmodule
`default_nettype wire
