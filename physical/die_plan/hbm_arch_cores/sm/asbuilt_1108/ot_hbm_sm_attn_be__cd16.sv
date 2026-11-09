// SM-ASBUILT-1108 (DIE-HBM-92-SU-SM): parameter-set master of the as-built ot_hbm_sm_attn_be #(.CONTROL_DELAY(16), .IL(8), .LEV(4), .NH(4), .RMAX(4096), .RPT(2), .SUB(4), .TAGW(16)); wires only.
`default_nettype none
module ot_hbm_sm_attn_be__cd16 (
    input wire clk,
    input wire rst_n,
    input wire [2:0] attn_column,
    input wire [28:0] command,
    input wire [199:0] gin,
    input wire [137:0] qin,
    output wire [183:0] qout
);
    ot_hbm_sm_attn_be #(.CONTROL_DELAY(16), .IL(8), .LEV(4), .NH(4), .RMAX(4096), .RPT(2), .SUB(4), .TAGW(16)) u_be (.clk(clk), .rst_n(rst_n), .attn_column(attn_column), .command(command), .gin(gin), .qin(qin), .qout(qout));
endmodule
`default_nettype wire
