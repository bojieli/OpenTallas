module add_wrap(input wire clk, rst_n, use_, input wire [31:0] head, b, output wire [31:0] y, output wire f);
  wire [31:0] a = use_ ? head : 32'd0;
  ot_hdc_v41x_qaddf #(.LAT(5), .F12(1)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(a), .b(b), .y(y), .fault(f));
endmodule
module add_plain(input wire clk, rst_n, v, input wire [31:0] a, b, output wire [31:0] y, output wire [1:0] err, output wire vo);
  ot_hdc_fp32_add_f12_l5x u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
endmodule
