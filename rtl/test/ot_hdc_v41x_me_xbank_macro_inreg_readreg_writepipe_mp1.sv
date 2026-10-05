`timescale 1ns/1ps
// Physical cut for the checkpoint-exact one-position shared activation store.
// The cut contains eight 1R1W SRAM abstracts. The external ports are the
// registered VM/converter and adapter boundaries, not an entire ME tile.
module ot_hdc_v41x_me_xbank_macro_inreg_readreg_writepipe_mp1 (
    input wire clk,
    input wire wr_v,
    input wire wr_p,
    input wire [12:0] wr_e,
    input wire [63:0] wr_d,
    input wire pre_v,
    input wire pre_p,
    input wire [12:0] pre_e,
    input wire [1023:0] pre_d,
    input wire [1:0] rd_rot,
    input wire [7:0] rq_v,
    input wire [111:0] rq_q,
    input wire [31:0] rq_plg,
    output wire [1023:0] rd_x
);
    ot_hdc_v41x_me_xbank_macro_inreg_readreg_writepipe #(.MP(1)) u_store (.*);
endmodule
