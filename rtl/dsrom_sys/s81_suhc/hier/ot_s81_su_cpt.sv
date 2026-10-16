`timescale 1ns/1ps
// CP14 descriptor pin leaf. The engine issues its immutable VM calendar;
// neither this tap nor the parent arbitrates, waits or grants credits.
module ot_s81_su_cpt #(parameter integer S_RD=16)(
    input wire clk,rst_n,dn_st,input wire [3:0] dn_kind,
    input wire [S_RD-1:0] dn_v,input wire [511:0] dn_d,
    input wire cp_done,
    output reg start,output reg [511:0] descriptor,
    output wire [1:0] cp_rs_v,output reg fault
);
    reg active,parameters;
    assign cp_rs_v=(active&&parameters)?dn_v[1:0]:2'b00;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;parameters<=0;start<=0;fault<=0;end
        else begin
            start<=0;
            if(dn_st)begin
                if(active)fault<=1;
                active<=dn_kind==14;parameters<=0;
            end
            if(active&&!parameters&&|dn_v)begin
                if(dn_v!={{(S_RD-1){1'b0}},1'b1})fault<=1;
                descriptor<=dn_d;parameters<=1;start<=1;
            end
            if(active&&parameters&&|(dn_v>>2))fault<=1;
            if(cp_done)active<=0;
        end
    end
endmodule
