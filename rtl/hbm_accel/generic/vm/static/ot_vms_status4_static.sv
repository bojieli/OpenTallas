`timescale 1ns/1ps
`default_nettype none
// Four real quadrant vmstat outputs -> the CP's single real vmstat19 input.
// Input pin, balanced pair sums, final saturating sum: three fixed rungs.
module ot_vms_status4_static (
    input wire clk,rst_n,
    input wire [4*19-1:0] quadrant_status,
    output reg [18:0] vmstat
);
    reg [75:0] pin_q;
    reg [16:0] sum0,sum1;
    reg [2:0] flags;
    reg [1:0] valid;
    wire [17:0] total={1'b0,sum0}+{1'b0,sum1};
    always @(posedge clk)begin
        pin_q<=quadrant_status;
        sum0<={1'b0,pin_q[0+:16]}+{1'b0,pin_q[19+:16]};
        sum1<={1'b0,pin_q[38+:16]}+{1'b0,pin_q[57+:16]};
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin flags<=0;valid<=0;vmstat<=0;end
        else begin
            flags<=pin_q[18:16]|pin_q[37:35]|pin_q[56:54]|pin_q[75:73];
            valid<={valid[0],1'b1};
            vmstat<=valid[1]?{flags,(|total[17:16])?16'hffff:total[15:0]}:19'd0;
        end
endmodule
`default_nettype wire
