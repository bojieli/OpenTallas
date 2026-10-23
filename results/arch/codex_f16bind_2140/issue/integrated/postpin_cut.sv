`timescale 1ns/1ps
// Actual selected source cut AFTER the existing slice pin register and regional
// reset. All12 instances receive genuine SETID commands before any programme.
module qfd_dv_f16_postpin_cut #(parameter MUT=0)(input wire ck,rst,
 input wire[115:0]cmd_q,input wire[21:0]context_q,
 output reg[115:0]cmd_o,output wire[37:0]observation,output wire enumerated);
    reg  [3:0] sid_q; reg sid_ok;
    wire setid = cmd_q[0] && cmd_q[3:1] == 3'd7;
    always @(posedge ck or negedge rst)
        if (!rst) begin sid_q <= 4'd0; sid_ok <= 1'b0; cmd_o <= 116'd0; end
        else begin
            if (setid) begin sid_q <= cmd_q[7:4]; sid_ok <= 1'b1; end
            cmd_o <= setid ? {cmd_q[115:8], cmd_q[7:4] + ((MUT == 10) ? 4'd0 : 4'd1), cmd_q[3:0]} : cmd_q;
        end
    // ------------------------------------------------------------------ command decode
    reg        arx_arm, g_arm, g_tok_v, g_fault; reg [1:0] g_user; reg [2:0] g_cnt; reg [55:0] g_best; reg [23:0] g_tok_idx; reg [31:0] g_tok_val;
    wire       go = cmd_q[0] && sid_ok && (cmd_q[115:112] == sid_q || cmd_q[115:112] == 4'hF) && cmd_q[3:1] != 3'd7;
    wire [2:0] kind = cmd_q[3:1];
    wire c_su = go && kind == 3'd1, c_stn = go && kind == 3'd2, c_root = go && kind == 3'd3,
         c_prt = go && kind == 3'd4, c_stm = go && kind == 3'd5;

assign enumerated=sid_ok;
qfd_dv_f16_issue_tap tap(.ck(ck),.rst_n(rst),.program_re(c_su),.program_pidx(cmd_q[12:4]),.slice_id(sid_q),.command_context(context_q),.observation(observation));
endmodule
