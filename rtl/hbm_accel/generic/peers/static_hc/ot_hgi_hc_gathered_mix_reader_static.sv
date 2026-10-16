`timescale 1ns/1ps
`default_nettype none
// Compiler-fixed 3-sector read per HC position,24 edges apart. Request pins
// are functions of captured control state; far-HC tap samples launch+1.
// Its registered return is launch+19; this reader captures and emits word0
// at launch+20, downstream engine samples launch+21. No queues/ready/stalls.
// RESP_PHASE (H-NETLIST 2026-10-15): edge of the fixed 24-edge period at which the
// return is captured; 19 = direct tap connection (default, unchanged). A parent that
// adds pin/leaf register edges on the request and return paths adds them here.
module ot_hgi_hc_gathered_mix_reader_static #(parameter integer RESP_PHASE=19)(
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
    initial if(RESP_PHASE<1||RESP_PHASE>23)$fatal(1,"RESP_PHASE must lie inside the 24-edge period");
    reg [767:0] landing;
    reg [15:0] issue_sector,return_sector,stride;
    reg [3:0] positions,issued,returned;
    reg [4:0] phase,next_row;
    reg [2:0] output_pos;
    wire request_slot=active&&phase==0&&issued<positions;
    wire response_slot=active&&phase==5'(RESP_PHASE)&&returned<positions;
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
                phase<=phase==23?5'd0:phase+5'd1;
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
