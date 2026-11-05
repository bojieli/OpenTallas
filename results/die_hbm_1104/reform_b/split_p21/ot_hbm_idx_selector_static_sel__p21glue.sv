// HBM-REFORM-B d44v part 21: plan module ot_hbm_idx_selector_static_sel = thin parent glue of the split hard core (wires only).
`default_nettype none
module ot_hbm_idx_selector_static_sel__fcore (
    input wire clk_ctl, input wire [3:0] clk_q, input wire [11:0] clk_mem, input wire rst_n,
    input wire [3:0] op, input wire [1:0] pass, input wire [7:0] addr, input wire [9:0] k, input wire [2367:0] in_line,
    output wire [3:0] selected_v, output wire [2367:0] selected_line, output wire fault);
    ot_hbm_idx_selector_static_sel__p21comp u_core (.clk_ctl(clk_ctl), .clk_q(clk_q), .clk_mem(clk_mem), .rst_n(rst_n), .op(op), .pass(pass), .addr(addr), .k(k), .in_line(in_line), .selected_v(selected_v), .selected_line(selected_line), .fault(fault));
endmodule
module ot_hbm_idx_selector_static_sel (
    input wire clk_ctl, input wire [3:0] clk_q, input wire [11:0] clk_mem, input wire rst_n,
    input wire [3:0] op, input wire [1:0] pass, input wire [7:0] addr, input wire [9:0] k, input wire [2367:0] in_line,
    output wire [3:0] selected_v, output wire [2367:0] selected_line, output wire fault);
    ot_hbm_idx_selector_static_sel__fcore u_fcore (.clk_ctl(clk_ctl), .clk_q(clk_q), .clk_mem(clk_mem), .rst_n(rst_n), .op(op), .pass(pass), .addr(addr), .k(k), .in_line(in_line), .selected_v(selected_v), .selected_line(selected_line), .fault(fault));
endmodule
`default_nettype wire
