`timescale 1ns/1ps
`default_nettype none
// Real status producer for command processor vmstat19. Three balanced adder
// rungs saturate the eight bank CE counters; all faults follow the same delay.
module ot_vms_status_static (
    input wire clk,rst_n,
    input wire [143:0] bank_status,
    input wire [2:0] hub_status,
    input wire ring_fault,
    output reg [18:0] vmstat
);
    reg [16:0] pair_sum[0:3];
    reg [17:0] half_sum[0:1];
    reg [2:0] flags0,flags1;
    reg [1:0] sum_valid;
    wire [18:0] total={1'b0,half_sum[0]}+{1'b0,half_sum[1]};
    reg [2:0] flags;
    always @* begin
        flags={hub_status[2]|hub_status[0]|ring_fault,hub_status[1],1'b0};
        for(integer b=0;b<8;b=b+1)begin
            flags[2]=flags[2]|bank_status[b*18+17];
            flags[0]=flags[0]|bank_status[b*18+16];
        end
    end
    always @(posedge clk)begin
        for(integer i=0;i<4;i=i+1)
            pair_sum[i]<={1'b0,bank_status[(i*2)*18+:16]}+{1'b0,bank_status[(i*2+1)*18+:16]};
        half_sum[0]<={1'b0,pair_sum[0]}+{1'b0,pair_sum[1]};
        half_sum[1]<={1'b0,pair_sum[2]}+{1'b0,pair_sum[3]};
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin flags0<=0;flags1<=0;sum_valid<=0;vmstat<=0;end
        else begin
            flags0<=flags;flags1<=flags0;sum_valid<={sum_valid[0],1'b1};
            vmstat<=sum_valid[1]?{flags1,(|total[18:16])?16'hffff:total[15:0]}:19'd0;
        end
endmodule
`default_nettype wire
