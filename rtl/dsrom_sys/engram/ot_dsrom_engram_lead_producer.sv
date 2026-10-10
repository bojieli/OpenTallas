`timescale 1ns/1ps
// One bounded token transaction. History changes only on accepted tokens;
// window/context remains stable through downstream stalls. No token truncation.
module ot_dsrom_engram_lead_producer #(
    parameter [16:0] PAD = 17'd2
) (
    input wire clk,rst_n,
    input wire t_v,
    output wire t_ready,
    input wire [11:0] t_user,
    input wire [20:0] t_pos,t_tok,
    input wire t_first,t_dead,t_slot,
    input wire rb_v,
    input wire [11:0] rb_user,
    input wire [2:0] rb_n,
    output wire rb_ready,
    output reg out_v,
    input wire out_ready,
    output reg [67:0] out_ids,
    output reg out_dead,out_slot,
    output reg [11:0] out_user,
    output reg [20:0] out_pos,out_tok,
    output wire fault
);
    reg busy, bad;
    reg [11:0] usr;
    reg [20:0] pos,tok;
    reg first,dead,slot;
    reg [21:0] count [0:63];
    wire accept=t_v && t_ready;
    wire legal=t_user<64 && t_tok<129280 &&
        ((t_first && t_pos==0) || (!t_first && t_user<64 && {1'b0,t_pos}==count[t_user[5:0]]));
    wire rollback=rb_v && rb_ready;
    wire rb_legal=rb_user<64 && rb_n>=1 && rb_n<=5 && {19'b0,rb_n}<=count[rb_user[5:0]];
    assign t_ready=!busy && !out_v && !rb_v && !fault;
    assign rb_ready=!busy && !out_v && !fault;
    wire map_v,map_fault,win_v,win_dead;
    wire [16:0] cid;
    wire [67:0] ids;
    assign fault=bad | map_fault;
    ot_dsrom_engram_token_map map(.clk(clk),.rst_n(rst_n),.in_v(accept && legal),
        .in_tok(t_tok),.out_v(map_v),.out_cid(cid),.fault(map_fault));
    ot_dsrom_engram_idwin #(.PAD(PAD)) history(.clk(clk),.rst_n(rst_n),
        .t_valid(map_v),.t_user(usr[5:0]),.t_cid(cid),.t_first(first),.t_dead(dead),
        .rb_valid(rollback && rb_legal),.rb_user(rb_user[5:0]),.rb_n(rb_n),
        .win_valid(win_v),.win_ids(ids),.win_dead(win_dead));
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            busy<=0;bad<=0;out_v<=0;usr<=0;pos<=0;tok<=0;first<=0;dead<=0;slot<=0;
            out_ids<=0;out_dead<=0;out_slot<=0;out_user<=0;out_pos<=0;out_tok<=0;
            for(i=0;i<64;i=i+1) count[i]<=0;
        end else begin
            if(out_v && out_ready) out_v<=0;
            if(accept) begin
                if(!legal) bad<=1;
                else begin
                    busy<=1;usr<=t_user;pos<=t_pos;tok<=t_tok;first<=t_first;dead<=t_dead;slot<=t_slot;
                    count[t_user[5:0]]<={1'b0,t_pos}+22'd1;
                end
            end
            if(rollback) begin
                if(!rb_legal) bad<=1;
                else count[rb_user[5:0]]<=count[rb_user[5:0]]-{19'b0,rb_n};
            end
            if(win_v) begin
                busy<=0;out_v<=1;out_ids<=ids;out_dead<=win_dead;
                out_slot<=slot;out_user<=usr;out_pos<=pos;out_tok<=tok;
            end
        end
    end
endmodule
