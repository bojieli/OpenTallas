module tb_origin #(parameter integer PAD = 0, parameter bit EDGE_FALL = 0) (
    input wire clk, input wire rst_raw_n, input wire p_start, output wire start);
    ot_dp_landing_origin #(.PAD(PAD), .EDGE_FALL(EDGE_FALL)) u (.clk(clk), .rst_raw_n(rst_raw_n), .p_start(p_start), .start(start));
endmodule
