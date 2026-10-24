`timescale 1ns/1ps
// bind_tiny structural parent (dissolved by the binder): two leaves + a little glue.
module par #(parameter integer K = 1) (input wire ck, input wire rst_n, input wire [7:0] x, input wire [3:0] id,
                                     output wire [7:0] y, output wire f);
    wire [7:0] a_o;
    lf_a #(.ID(K)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));
    lf_b u_b (.clk(ck), .i(a_o), .id(id), .o(y), .flt(f));
endmodule
// plan variant of par for a chain head (test_substitute_parent): no id port, the id-less leaf variant
module par_nid #(parameter integer K = 1) (input wire ck, input wire rst_n, input wire [7:0] x,
                                         output wire [7:0] y, output wire f);
    wire [7:0] a_o;
    lf_a #(.ID(K)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));
    lf_b_nid u_b (.clk(ck), .i(a_o), .o(y), .flt(f));
endmodule
