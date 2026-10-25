module wrap (input clk, input rst_n, input clr, input i_v, input [15:0] i_en, input [127:0] i_dg, input [3:0] gsel,
             output [29:0] gsum, output [175:0] gbin, output busy);
  gate u (.clk(clk), .rst_n(rst_n), .clr({17{clr}}), .i_v(i_v), .i_en(i_en), .i_dg(i_dg), .gsel({16{gsel}}),
          .gsum(gsum), .gbin(gbin), .busy(busy));
endmodule
