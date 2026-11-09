// SM-ASBUILT-1108 (DIE-HBM-92-SU-SM): parameter-set master of the as-built ot_hbm_sm_attn_be #(.CONTROL_DELAY(16), .IL(8), .LEV(4), .NH(4), .RMAX(4096), .RPT(2), .SUB(4), .TAGW(16)); wires + one static-pin register (COORD 11-09 01:0x: attn_column is tied by the parent; one flop gives each pin bit its own face register, no guard exemption, 0 cycles in operation).
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
    reg [2:0] attn_column_q;
    always @(posedge clk) attn_column_q <= attn_column;
    ot_hbm_sm_attn_be #(.CONTROL_DELAY(16), .IL(8), .LEV(4), .NH(4), .RMAX(4096), .RPT(2), .SUB(4), .TAGW(16)) u_be (.clk(clk), .rst_n(rst_n), .attn_column(attn_column_q), .command(command), .gin(gin), .qin(qin), .qout(qout));
endmodule
`default_nettype wire
