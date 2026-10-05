`timescale 1ns/1ps
// One local QE qtile ROM bank bridge. Eight FP8 banks store one 264-bit
// {UE8M0,codes} lane each; eight 274-bit FP4 banks store two 136-bit
// {UE8M0,packed E2M1 codes} lanes per row. The extra macro bits are unused.
// Requests are qtile-local beats, after matrix placement has removed wbase.
// The bank SRAM/ROM reads at the request edge; this module captures its data
// at the next edge, preserving the qtile's RL=2 read contract.
module ot_chip_v41x_qtile_pair_bank (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              fp4,
    input  wire [7:0]        req_v,
    input  wire [8*20-1:0]   req_beat,
    output reg  [15:0]       bank_re,
    output reg  [16*13-1:0] bank_addr,
    input  wire [16*274-1:0] bank_q,
    output reg  [7:0]        rd_v,
    output reg  [8*264-1:0] rd_w,
    output reg               conflict,
    output reg               address_fault,
    output reg               reserved_fault
);
    reg [3:0] bank_sel [0:7];
    reg [3:0] bank_sel_d [0:7];
    reg [7:0] req_v_d;
    reg fp4_d;
    reg [7:0] half_d;
    reg [19:0] beat;
    reg [19:0] row;
    reg [3:0] bank;
    integer c;
    always @(*) begin
        bank_re='0;
        bank_addr='0;
        conflict=1'b0;
        address_fault=1'b0;
        for (c=0;c<8;c=c+1) begin
            beat=req_beat[c*20 +:20];
            row=fp4 ? beat>>1 : beat;
            bank=fp4 ? (4'd8 + {beat[0],2'b00} + 4'(c>>1)) : 4'(c);
            bank_sel[c]=bank;
            if (req_v[c]) begin
                if (row >= 20'd8192) address_fault=1'b1;
                if (bank_re[bank] && bank_addr[bank*13 +:13] != row[12:0])
                    conflict=1'b1;
                bank_re[bank]=1'b1;
                bank_addr[bank*13 +:13]=row[12:0];
            end
        end
    end
    integer k;
    reg [273:0] selected;
    reg [135:0] compact;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req_v_d<='0; rd_v<='0; rd_w<='0; fp4_d<=1'b0;
            half_d<='0; reserved_fault<=1'b0;
            for (k=0;k<8;k=k+1) bank_sel_d[k]<='0;
        end else begin
            req_v_d<=req_v;
            fp4_d<=fp4;
            for (k=0;k<8;k=k+1) begin
                bank_sel_d[k]<=bank_sel[k];
                half_d[k]<=k[0];
                rd_v[k]<=req_v_d[k];
                if (req_v_d[k]) begin
                    selected=bank_q[bank_sel_d[k]*274 +:274];
                    if (fp4_d) begin
                        compact=half_d[k] ? selected[271:136] : selected[135:0];
                        rd_w[k*264 +:264]<={compact[135:128],128'b0,compact[127:0]};
                        if (selected[273:272] != 2'b00) reserved_fault<=1'b1;
                    end else begin
                        rd_w[k*264 +:264]<=selected[263:0];
                        if (selected[273:264] != 10'b0) reserved_fault<=1'b1;
                    end
                end
            end
        end
    end
endmodule
