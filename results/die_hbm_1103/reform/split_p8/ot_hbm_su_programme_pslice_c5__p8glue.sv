// DIE-HBM-62/CUTS d44v part 8: plan module ot_hbm_su_programme_pslice_c5 = thin parent glue of the split hard core (wires only).
`default_nettype none
module ot_hbm_su_programme_pslice_c5__fcore (
    input wire clk, input wire rst_n, input wire cfg_we, input wire [15:0] cfg_bank, input wire [6:0] cfg_row,
    input wire [255:0] cfg_data, input wire start, input wire [15:0] length, output wire busy, output wire valid,
    output wire done, output wire fault, output wire [15:0] edge_index, output wire [2469:0] command);
    ot_hbm_su_programme_pslice_c5__p8comp u_core (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_bank(cfg_bank), .cfg_row(cfg_row), .cfg_data(cfg_data), .start(start), .length(length), .busy(busy), .valid(valid), .done(done), .fault(fault), .edge_index(edge_index), .command(command));
endmodule
module ot_hbm_su_programme_pslice_c5 (
    input wire clk, input wire rst_n, input wire cfg_we, input wire [15:0] cfg_bank, input wire [6:0] cfg_row,
    input wire [255:0] cfg_data, input wire start, input wire [15:0] length, output wire busy, output wire valid,
    output wire done, output wire fault, output wire [15:0] edge_index, output wire [2469:0] command);
    ot_hbm_su_programme_pslice_c5__fcore u_fcore (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_bank(cfg_bank), .cfg_row(cfg_row), .cfg_data(cfg_data), .start(start), .length(length), .busy(busy), .valid(valid), .done(done), .fault(fault), .edge_index(edge_index), .command(command));
endmodule
`default_nettype wire
