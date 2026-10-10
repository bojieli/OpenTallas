`timescale 1ns/1ps
// HGI-1 plain accept endpoint. Legacy DS width remains default; routes enable18.
module ot_hgi_mtp_accept18 #(
    parameter integer GENERIC18 = 0,
    parameter integer TW = GENERIC18 ? 18 : 17,
    parameter integer PINREG = 0
)(
    input wire clk, rst_n, start_v, tokx_v, amax_v, acc_v,
    input wire [TW-1:0] start_tok, tokx_tok, amax_tok,
    input wire [2:0] tokx_slot, amax_slot, acc_g,
    output wire [8*TW-1:0] stok, ttok,
    output wire acc_done, acc_any,
    output wire [2:0] acc_a,
    output wire [3:0] n_emit,
    output wire [TW-1:0] bonus
);
    wire start_v_i,tokx_v_i,amax_v_i,acc_v_i;
    wire [TW-1:0] start_tok_i,tokx_tok_i,amax_tok_i;
    wire [2:0] tokx_slot_i,amax_slot_i,acc_g_i;
    generate if(PINREG) begin:g_seat
        reg [4+3*TW+9-1:0] command_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) command_q<=0; else command_q<={start_v,tokx_v,amax_v,acc_v,start_tok,tokx_tok,amax_tok,tokx_slot,amax_slot,acc_g};
        assign {start_v_i,tokx_v_i,amax_v_i,acc_v_i,start_tok_i,tokx_tok_i,amax_tok_i,tokx_slot_i,amax_slot_i,acc_g_i}=command_q;
    end else begin:g_direct
        assign {start_v_i,tokx_v_i,amax_v_i,acc_v_i,start_tok_i,tokx_tok_i,amax_tok_i,tokx_slot_i,amax_slot_i,acc_g_i}={start_v,tokx_v,amax_v,acc_v,start_tok,tokx_tok,amax_tok,tokx_slot,amax_slot,acc_g};
    end endgenerate
    ot_hdc_accept #(.NSLOT(8),.NW(TW)) u_accept (
        .clk(clk),.rst_n(rst_n),.start_v(start_v_i),.start_tok(start_tok_i),
        .tokx_v(tokx_v_i),.tokx_slot(tokx_slot_i),.tokx_tok(tokx_tok_i),
        .amax_v(amax_v_i),.amax_slot(amax_slot_i),.amax_tok(amax_tok_i),
        .acc_v(acc_v_i),.acc_g(acc_g_i),.stok(stok),.ttok(ttok),
        .acc_done(acc_done),.acc_any(acc_any),.acc_a(acc_a),
        .n_emit(n_emit),.bonus(bonus));
endmodule
