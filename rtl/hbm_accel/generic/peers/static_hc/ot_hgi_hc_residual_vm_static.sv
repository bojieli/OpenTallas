`timescale 1ns/1ps
`default_nettype none
// Static native eight-bank VM read producer -> PMAX8 residual macro landing.
// launch reserves320*npos consecutive read slots. Each group is8sectors;
// four returns form one32-sector logical x_wave. All bases must align32.
// Local HC tap emits rr at edge request+18; this registered consumer captures
// at request+19 and emits the assembled wave that edge, SRAM consumes+20.
// First complete wave is request0+22; successive waves every4 edges.
// Missing or unsolicited returns fault; the calendar never waits or retries.
module ot_hgi_hc_residual_vm_static #(
    parameter integer CAPTURE_LAT=19,
    parameter integer MUT_POSITION=0
)(
    input wire clk,rst_n,launch,
    input wire [3:0] npos,
    input wire [15:0] base_sector,
    output wire [135:0] local_rq,
    output wire [7:0] local_read,
    input wire [2055:0] local_rr,
    output reg x_wave_v,
    output reg [9:0] x_wave_word,
    output reg [8191:0] x_wave,
    output reg done,fault
);
    reg active;
    reg [11:0] issue,total;
    reg [15:0] base;
    reg [CAPTURE_LAT-1:0] valid;
    reg [11:0] order[0:CAPTURE_LAT-1];
    reg [8191:0] assembly;
    wire fire=active;
    assign local_read={8{fire}};
    for(genvar b=0;b<8;b=b+1)assign local_rq[b*17+:17]={fire,16'(base+issue*8+b)};
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;issue<=0;total<=0;base<=0;valid<=0;x_wave_v<=0;done<=0;fault<=0;end
        else begin
            valid<=(valid<<1)|fire;
            x_wave_v<=0;done<=0;
            if(launch)begin
                if(active||(|valid)||npos<1||npos>8||base_sector[4:0]!=0||({1'b0,base_sector}+npos*2560)>32768)fault<=1;
                active<=1;issue<=0;total<=npos*320;base<=base_sector;
            end
            if(fire)begin
                issue<=issue+1;
                if(issue==total-1)active<=0;
            end
            for(integer b=0;b<8;b=b+1)
                if(local_rr[b*257+256]!=valid[CAPTURE_LAT-1])fault<=1;
            if(valid[CAPTURE_LAT-1]&&order[CAPTURE_LAT-1][1:0]==3)begin
                x_wave_v<=1;
                x_wave_word<=10'(order[CAPTURE_LAT-1]>>2)^(MUT_POSITION?10'd80:10'd0);
                x_wave[0+:6144]<=assembly[0+:6144];
                for(integer b=0;b<8;b=b+1)x_wave[6144+b*256+:256]<=local_rr[b*257+:256];
                if(order[CAPTURE_LAT-1]==total-1)done<=1;
            end
        end
    end
    always @(posedge clk)begin
        order[0]<=issue;
        for(integer j=1;j<CAPTURE_LAT;j=j+1)order[j]<=order[j-1];
        if(valid[CAPTURE_LAT-1])for(integer b=0;b<8;b=b+1)
            assembly[order[CAPTURE_LAT-1][1:0]*2048+b*256+:256]<=local_rr[b*257+:256];
    end
endmodule
`default_nettype wire
