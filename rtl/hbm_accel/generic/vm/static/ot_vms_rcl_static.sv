`timescale 1ns/1ps
`default_nettype none
// Fixed cycle ring packet replay. The returned packet tag itself carries the
// return route; no FIFO, lease, response credit or arrival arbitration exists.
module ot_vms_rcl_static #(parameter integer MUT=0) (
    input wire clk,rst_n,
    input wire [1:0] sid,
    input wire rx_enable,rx_source,
    input wire [287:0] rce0,rce1,
    output reg [337:0] hq,
    input wire [273:0] hr,
    output reg [265:0] ri0,ri1,
    output reg fault
);
    reg [287:0] a,b;
    reg [273:0] response;
    reg [1:0] me;
    reg select_q,enable_q;
    wire [287:0] e=select_q?b:a;
    wire [14:0] sec={e[274]?2'b00:me,e[273:264],e[277:275]};
    wire [31:0] addr={11'b0,e[274],sec,5'b0};
    wire [15:0] tag={6'b0,~select_q,e[286:285],e[284:281],e[280:279],e[278]};
    wire return_port=response[266] ^ (MUT==1);
    reg [31:0] mask;
    always @* for(integer k=0;k<8;k=k+1) mask[k*4+:4]={4{e[256+k]}};
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin
            a<=0;b<=0;response<=0;me<=0;select_q<=0;enable_q<=0;
            hq<=0;ri0<=0;ri1<=0;fault<=0;
        end else begin
            a<=rce0;b<=rce1;response<=hr;me<=sid;
            select_q<=rx_source;enable_q<=rx_enable;
            hq<={enable_q && e[287],e[278],addr,e[255:0],mask,tag};
            ri0<={response[273] && !return_port,response[265:264],response[263:260],response[259:258],response[256],response[255:0]};
            ri1<={response[273] && return_port,response[265:264],response[263:260],response[259:258],response[256],response[255:0]};
            if((a[287] && (!enable_q || select_q)) ||
               (b[287] && (!enable_q || !select_q))) fault<=1;
            // Upper tag bits are reserved. A malformed return cannot be treated
            // as an uncorrelated response from another compiler transaction.
            if(response[273] && response[272:267]!=0) fault<=1;
        end
endmodule
`default_nettype wire
