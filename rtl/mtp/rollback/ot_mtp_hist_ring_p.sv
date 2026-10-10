`timescale 1ns/1ps
// Opt-in registered successor of ot_mtp_hist_ring; original stays pinned.
// Full production shape: 16 slots, 17-bit token, 32-bit position, four-token stream.
// Pin requests -> registered bank selection -> registered tag comparison/output.
// A streamed decrementing position replaces p_q-k before the 16:1 read mux.
// First output is three cycles after read acceptance (+2 vs original); throughput
// remains one token/cycle. Writes/commit become visible one cycle later. Readiness
// includes the request register, so a read cannot overwrite a pending request.
module ot_mtp_hist_ring_p #(
    parameter integer TR=16, NG=4, TW=17, PMAX=8, PW=32,
    parameter integer MUT_APPEND=0
)(
    input wire clk, rst_n,
    input wire n_set, input wire [PW-1:0] n_val,
    input wire tw_v, input wire [PW-1:0] tw_pos, input wire [TW-1:0] tw_tok,
    input wire rd_v, output wire rd_ready, input wire [PW-1:0] rd_pos,
    output reg h_v, output reg [TW-1:0] h_tok,
    output reg h_pad, h_last, err
);
    localparam integer TB=$clog2(TR), KB=$clog2(NG+1);
    initial if ((1<<TB)!=TR || TR<NG-1+PMAX)
        $fatal(1,"hist ring requires power-of-two TR >= NG-1+PMAX");
    reg [TW-1:0] mem [0:TR-1];
    reg [PW-1:0] tag [0:TR-1];
    reg tv [0:TR-1];
    reg n_set_q, tw_v_q, rd_v_q;
    reg [PW-1:0] n_val_q, tw_pos_q, rd_pos_q;
    reg [TW-1:0] tw_tok_q;
    reg [PW-1:0] n, wcount, rp_q;
    reg busy;
    reg [KB-1:0] k;
    reg bank_v, bank_pad, bank_last, bank_tv;
    reg [TW-1:0] bank_tok;
    reg [PW-1:0] bank_tag, bank_pos;
    reg reach_v;
    reg [PW-1:0] reach_q;
    integer i;
    assign rd_ready=!busy && !rd_v_q;
    wire [PW-1:0] wp=MUT_APPEND ? wcount : tw_pos_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_set_q<=0;tw_v_q<=0;rd_v_q<=0;
            n_val_q<=0;tw_pos_q<=0;rd_pos_q<=0;tw_tok_q<=0;
            n<=0;wcount<=0;rp_q<=0;busy<=0;k<=0;
            bank_v<=0;bank_pad<=0;bank_last<=0;bank_tv<=0;
            bank_tok<=0;bank_tag<=0;bank_pos<=0;reach_v<=0;reach_q<=0;
            h_v<=0;h_tok<=0;h_pad<=0;h_last<=0;err<=0;
            for(i=0;i<TR;i=i+1) tv[i]<=0;
        end else begin
            n_set_q<=n_set;n_val_q<=n_val;
            tw_v_q<=tw_v;tw_pos_q<=tw_pos;tw_tok_q<=tw_tok;
            rd_v_q<=rd_v && rd_ready;rd_pos_q<=rd_pos;
            if(n_set_q) n<=n_val_q;
            if(tw_v_q) begin
                mem[wp[TB-1:0]]<=tw_tok_q;
                tag[wp[TB-1:0]]<=MUT_APPEND ? tw_pos_q : wp;
                tv[wp[TB-1:0]]<=1;
                wcount<=wcount+1'b1;
            end
            reach_v<=tw_v_q;
            reach_q<=tw_pos_q-n;
            if(!MUT_APPEND && reach_v && ($signed(reach_q)>=PMAX || $signed(reach_q)<-(TR-PMAX))) err<=1;
            bank_v<=busy;
            if(!busy && rd_v_q) begin
                busy<=1;rp_q<=rd_pos_q;k<=0;
            end else if(busy) begin
                bank_tok<=mem[rp_q[TB-1:0]];
                bank_tag<=tag[rp_q[TB-1:0]];
                bank_tv<=tv[rp_q[TB-1:0]];
                bank_pos<=rp_q;
                bank_pad<=rp_q[PW-1];
                bank_last<=k==NG-1;
                rp_q<=rp_q-1'b1;
                if(k==NG-1) begin busy<=0;end
                else k<=k+1'b1;
            end
            h_v<=bank_v;h_pad<=bank_v && bank_pad;h_last<=bank_v && bank_last;
            if(bank_v) begin
                h_tok<=bank_pad ? {TW{1'b0}} : bank_tok;
                if(!MUT_APPEND && !bank_pad && (!bank_tv || bank_tag!=bank_pos)) err<=1;
            end
        end
    end
endmodule
