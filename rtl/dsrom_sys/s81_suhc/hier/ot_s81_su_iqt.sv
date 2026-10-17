`timescale 1ns/1ps
// QI VM tap: six parameter rows, then32 reserved two-cycle operand epochs.
// Descriptor words:0 completion row,1 query FP32-row base,2 weight-row base.
// Parameter rows1..4 are cos[0:16],cos[16:32],sin[0:16],sin[16:32];
// row5 is the actual SVC type4 header. Phase0 is eight consecutive query rows;
// phase1 is one weight row on slot0. This avoids low5 bank collisions between
// the repeatedly used weight rows and query rows. FIELD already rounds to BF16.
// This leaf owns only its pin registers/counters; arithmetic lives in IQ leaves.
module ot_s81_su_iqt # (parameter integer S_RD=16,FIRST_DATA=27)(
    input wire clk,rst_n,dn_st,input wire [3:0] dn_kind,
    input wire [S_RD-1:0] dn_v,input wire [S_RD*512-1:0] dn_d,
    output wire start,output reg [511:0] header,
    output reg q_v,output reg [4:0] q_head,
    output reg [2047:0] q_bf16,output reg [15:0] weight_proj_bf16,
    output reg [1023:0] cos_t,sin_t,
    input wire iq_done,iq_fault,
    output wire o_v,output wire [13:0] o_a,
    output wire [15:0] o_m,output wire [511:0] o_d,
    output wire fault
);
    reg active,parameters,all_heads,local_fault;
    reg [13:0] ob;
    reg [4:0] next_head;
    reg [7:0] age;
    reg query_valid;
    assign start=q_v && q_head==0;
    assign o_v=active && iq_done;
    assign o_a=ob;
    assign o_m=16'hffff;
    // A completion receipt is emitted only after the actual final frame word.
    // The frame is the native numerical result; this row records its length.
    assign o_d={480'd0,32'd65};
    assign fault=local_fault|iq_fault;
    integer r,k;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;parameters<=0;all_heads<=0;local_fault<=0;
            q_v<=0;q_head<=0;next_head<=0;ob<=0;age<=0;query_valid<=0;
        end else begin
            q_v<=0;
            if(dn_st)begin
                if(active && dn_kind==15)local_fault<=1;
                active<=dn_kind==15;parameters<=0;all_heads<=0;next_head<=0;age<=0;query_valid<=0;
            end
            if(active && |dn_v)begin
                if(!parameters)begin
                    if(dn_v!={{(S_RD-6){1'b0}},6'b111111})local_fault<=1;
                    ob<=dn_d[0+:14];header<=dn_d[5*512+:512];
                    cos_t<=dn_d[512+:1024];sin_t<=dn_d[3*512+:1024];
                    if(dn_d[0+:32]>16383 || dn_d[32+:32]>16128 ||
                       dn_d[64+:32]>16382)local_fault<=1;
                    parameters<=1;age<=1;
                end
            end
            if(active&&parameters)begin
                if(age<255)age<=age+1;
                if(age>=FIRST_DATA && age<FIRST_DATA+64)begin
                    if((age-FIRST_DATA)%2==0)begin
                        query_valid<=dn_v=={{(S_RD-8){1'b0}},8'hff};
                        if(dn_v!={{(S_RD-8){1'b0}},8'hff})local_fault<=1;
                        for(r=0;r<8;r=r+1)for(k=0;k<16;k=k+1)begin
                            q_bf16[256*r+16*k+:16]<=dn_d[512*r+32*k+16+:16];
                            if(dn_d[512*r+32*k+:16]!=0)local_fault<=1;
                        end
                    end else begin
                        if(dn_v!={{(S_RD-1){1'b0}},1'b1})local_fault<=1;
                        q_v<=query_valid&&dn_v[0];q_head<=next_head;
                        weight_proj_bf16<=dn_d[32*next_head[3:0]+16+:16];
                        if(dn_d[32*next_head[3:0]+:16]!=0)local_fault<=1;
                        next_head<=next_head+1;
                        if(next_head==31)all_heads<=1;
                    end
                end else if(|dn_v)local_fault<=1;
            end
            if(iq_done && active)begin
                if(!all_heads)local_fault<=1;
                active<=0;
            end
        end
    end
endmodule
