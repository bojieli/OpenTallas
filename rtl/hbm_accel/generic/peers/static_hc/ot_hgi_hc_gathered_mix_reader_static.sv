`timescale 1ns/1ps
`default_nettype none
// Compiler-fixed 3-sector read per HC position, PERIOD edges apart. One
// landing register streams 24 words, so PERIOD is at least 24. A return must
// arrive inside the period; callers price the explicit cadence including idle
// slots. Legacy RESP_PHASE19/PERIOD24 is unchanged. No queues/ready/stalls.
module ot_hgi_hc_gathered_mix_reader_static #(
    parameter integer RESP_PHASE=19,
    parameter integer PERIOD=24
)(
    input wire clk,rst_n,launch,
    input wire [3:0] npos,
    input wire [15:0] base_sector,position_stride_sector,
    output reg [135:0] local_rq,
    output reg [7:0] local_read,
    input wire [2055:0] local_rr,
    output reg gathered_mix_v,
    output reg [4:0] gathered_mix_row,
    output reg [2:0] gathered_mix_pos,
    output reg [31:0] gathered_mix_data,
    output reg done,fault
);
    reg active,streaming;
    localparam integer PHW = PERIOD <= 32 ? 5 : $clog2(PERIOD);
    initial begin
        if(PERIOD<24||PERIOD>65536)$fatal(1,"gather PERIOD must be 24..65536");
        if(RESP_PHASE<1||RESP_PHASE>=PERIOD)$fatal(1,"RESP_PHASE must lie inside explicit gather PERIOD");
    end
    reg [767:0] landing;
    reg [15:0] issue_sector,return_sector,stride;
    reg [3:0] positions,issued,returned;
    reg [PHW-1:0] phase;
    reg [4:0] next_row;
    reg [2:0] output_pos;
    wire request_slot=active&&phase==0&&issued<positions;
    wire response_slot=active&&phase==PHW'(RESP_PHASE)&&returned<positions;
    wire [32:0] last_sector={17'd0,base_sector}+(npos-1)*{17'd0,position_stride_sector}+2;
    wire bounds_ok=npos>=1&&npos<=8&&!base_sector[15]&&last_sector<32768&&last_sector[14:13]==base_sector[14:13];
    reg [7:0] expected_valid,actual_valid;
    reg [767:0] arrived;
    always @*begin
        local_rq=0;local_read=0;expected_valid=0;actual_valid=0;arrived=0;
        for(integer b=0;b<8;b=b+1)actual_valid[b]=local_rr[b*257+256];
        for(integer j=0;j<3;j=j+1)begin:sector
            reg [15:0] q,r;
            q=issue_sector+16'(j);r=return_sector+16'(j);
            local_rq[q[2:0]*17+:17]={request_slot,q};local_read[q[2:0]]=request_slot;
            expected_valid[r[2:0]]=response_slot;
            arrived[j*256+:256]=local_rr[r[2:0]*257+:256];
        end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;streaming<=0;phase<=0;issue_sector<=0;return_sector<=0;stride<=0;
            positions<=0;issued<=0;returned<=0;next_row<=0;output_pos<=0;
            gathered_mix_v<=0;gathered_mix_row<=0;gathered_mix_pos<=0;gathered_mix_data<=0;done<=0;fault<=0;
        end else begin
            gathered_mix_v<=0;done<=0;
            if(actual_valid!==expected_valid)fault<=1;
            if(active)begin
                phase<=phase==PHW'(PERIOD-1)?{PHW{1'b0}}:phase+1'b1;
                if(request_slot)begin issue_sector<=issue_sector+stride;issued<=issued+1'b1;end
                if(response_slot)begin
                    landing<=arrived;returned<=returned+1'b1;return_sector<=return_sector+stride;
                    gathered_mix_v<=1;gathered_mix_row<=0;gathered_mix_pos<=returned[2:0];gathered_mix_data<=arrived[31:0];
                    streaming<=1;next_row<=1;output_pos<=returned[2:0];
                end else if(streaming)begin
                    gathered_mix_v<=1;gathered_mix_row<=next_row;gathered_mix_pos<=output_pos;
                    gathered_mix_data<=landing[next_row*32+:32];
                    next_row<=next_row+1'b1;
                    if(next_row==23)begin
                        streaming<=0;
                        if(returned==positions)begin active<=0;done<=1;end
                    end
                end
            end
            if(launch)begin
                if(active||!bounds_ok)fault<=1;
                else begin
                    active<=1;streaming<=0;phase<=0;issue_sector<=base_sector;return_sector<=base_sector;
                    stride<=position_stride_sector;positions<=npos;issued<=0;returned<=0;next_row<=0;output_pos<=0;
                end
            end
        end
    end
endmodule
`default_nettype wire
