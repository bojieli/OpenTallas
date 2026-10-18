`timescale 1ns/1ps
`default_nettype none
// Four real quadrant vmstat outputs -> the CP's single real vmstat19 input.
// Input pin, balanced pair sums, final saturating sum: three fixed rungs.
// NQ (H-NETLIST 1930, A2P half die): number of quadrants (2 or 4).  NQ=2 keeps the same three rungs (pin, pair sum,
// saturating total) with the second pair sum absent, so vmstat has the same latency; NQ=4 is the original exactly.
module ot_vms_status4_static #(parameter integer NQ=4) (
    input wire clk,rst_n,
    input wire [NQ*19-1:0] quadrant_status,
    output reg [18:0] vmstat
);
    reg [NQ*19-1:0] pin_q;
    reg [16:0] sum0,sum1;
    reg [2:0] flags;
    reg [1:0] valid;
    wire [17:0] total={1'b0,sum0}+{1'b0,sum1};
    reg [2:0] fl;
    integer k;
    always @* begin fl=3'd0; for(k=0;k<NQ;k=k+1) fl=fl|pin_q[19*k+16+:3]; end
    always @(posedge clk)begin
        pin_q<=quadrant_status;
`ifdef OT_VMS_STATUS_MUT
        sum0<={1'b0,pin_q[0+:16]};   // bench mutant: quadrant 1 dropped from the total
`else
        sum0<={1'b0,pin_q[0+:16]}+{1'b0,pin_q[19+:16]};
`endif
        sum1<=(NQ>2)?({1'b0,pin_q[(NQ>2?38:0)+:16]}+{1'b0,pin_q[(NQ>2?57:0)+:16]}):17'd0;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin flags<=0;valid<=0;vmstat<=0;end
        else begin
            flags<=fl;
            valid<={valid[0],1'b1};
            vmstat<=valid[1]?{flags,(|total[17:16])?16'hffff:total[15:0]}:19'd0;
        end
    initial if(NQ!=2&&NQ!=4)$fatal(1,"ot_vms_status4_static: NQ is 2 or 4");
endmodule
`default_nettype wire
