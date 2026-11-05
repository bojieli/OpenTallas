// HBM-REFORM-B d44v part 20: plan module ot_pdie_serdes = thin parent glue of the split hard core (wires only).
`default_nettype none
module ot_pdie_serdes__fcore (
    input wire clk, input wire rst, input wire [511:0] tx, output wire [511:0] rx, output wire [1:0] st,
    output wire [543:0] pma_tx, output wire pma_tck, input wire [543:0] pma_rx, input wire pma_rck);
    ot_pdie_serdes__p20comp u_core (.clk(clk), .rst(rst), .tx(tx), .rx(rx), .st(st), .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck));
endmodule
module ot_pdie_serdes (
    input wire clk, input wire rst, input wire [511:0] tx, output wire [511:0] rx, output wire [1:0] st,
    output wire [543:0] pma_tx, output wire pma_tck, input wire [543:0] pma_rx, input wire pma_rck);
    ot_pdie_serdes__fcore u_fcore (.clk(clk), .rst(rst), .tx(tx), .rx(rx), .st(st), .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck));
endmodule
`default_nettype wire
