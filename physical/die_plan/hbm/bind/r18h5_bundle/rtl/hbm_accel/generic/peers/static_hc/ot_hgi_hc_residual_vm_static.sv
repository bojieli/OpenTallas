`timescale 1ns/1ps
`default_nettype none
// Static native eight-bank VM read producer -> PMAX8 residual macro landing.
// launch reserves320*npos consecutive read slots. Each group is8sectors;
// four returns form one32-sector logical x_wave. All bases must align32.
// Local HC tap emits rr at edge request+18; this registered consumer captures
// at request+19 and emits the assembled wave that edge, SRAM consumes+20.
// First complete wave is request0+22; successive waves every4 edges.
// Missing or unsolicited returns fault; the calendar never waits or retries.
// BEATS=4 (H-NETLIST hceng 0600, die cut V0.874/H0.929 of the 8,192-b wave): no assembly here; every captured
// 8-sector group (2,048 b) leaves as beat order[1:0] of wave order>>2 on the edge the BEATS=1 form would write it
// into the assembly register, so beat 3 leaves on the BEATS=1 wave edge (the reassembled wave lands at the
// consumer's pin level on the SAME edge: +0 latency, 2,048 b a wire edge). BEATS=1 = the original wave form.
// MUT_BEAT (bench): 1 = beats 1/2 sent in swapped order (wire order 0,2,1,3), 2 = beat 3 leaves one edge late.
module ot_hgi_hc_residual_vm_static #(
    parameter integer CAPTURE_LAT=19,
    parameter integer MUT_POSITION=0,
    parameter integer BEATS=1,
    parameter integer MUT_BEAT=0
)(
    input wire clk,rst_n,launch,
    input wire [3:0] npos,
    input wire [15:0] base_sector,
    output wire [135:0] local_rq,
    output wire [7:0] local_read,
    input wire [2055:0] local_rr,
    output reg x_wave_v,
    output reg [9:0] x_wave_word,
    output reg [8192/BEATS-1:0] x_wave,
    output reg [1:0] x_wave_beat,
    output reg done,fault
);
    reg active;
    reg [11:0] issue,total;
    reg [15:0] base;
    reg [CAPTURE_LAT-1:0] valid;
    reg [11:0] order[0:CAPTURE_LAT-1];
    initial if(BEATS!=1&&BEATS!=4)$fatal(1,"BEATS must be 1 or 4");
    wire [1:0] cap_beat=order[CAPTURE_LAT-1][1:0];
    wire [1:0] mut_beat=(MUT_BEAT==1&&cap_beat==1)?2'd2:(MUT_BEAT==1&&cap_beat==2)?2'd1:cap_beat;
    wire fire=active;
    assign local_read={8{fire}};
    for(genvar b=0;b<8;b=b+1)assign local_rq[b*17+:17]={fire,16'(base+issue*8+b)};
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;issue<=0;total<=0;base<=0;valid<=0;done<=0;fault<=0;end
        else begin
            valid<=(valid<<1)|fire;
            done<=0;
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
            if(valid[CAPTURE_LAT-1]&&order[CAPTURE_LAT-1]==total-1)done<=1;
        end
    end
    always @(posedge clk)begin
        order[0]<=issue;
        for(integer j=1;j<CAPTURE_LAT;j=j+1)order[j]<=order[j-1];
    end
    wire [9:0] cap_word=10'(order[CAPTURE_LAT-1]>>2)^(MUT_POSITION?10'd80:10'd0);
    wire [2047:0] cap_d;
    for(genvar b=0;b<8;b=b+1)assign cap_d[b*256+:256]=local_rr[b*257+:256];
    generate if(BEATS==1)begin:g_wave
        reg [6143:0] assembly;
        always @(posedge clk)
            if(valid[CAPTURE_LAT-1]&&cap_beat!=3)assembly[cap_beat*2048+:2048]<=cap_d;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)x_wave_v<=0;
            else x_wave_v<=valid[CAPTURE_LAT-1]&&cap_beat==3;
        always @(posedge clk)begin
            x_wave_beat<=2'd0;
            if(valid[CAPTURE_LAT-1]&&cap_beat==3)begin x_wave_word<=cap_word;x_wave<={cap_d,assembly};end
        end
    end else begin:g_beats
        reg late_v; reg [9:0] late_word; reg [2047:0] late_d;
        wire send=valid[CAPTURE_LAT-1]&&!(MUT_BEAT==2&&cap_beat==3);
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin x_wave_v<=0;late_v<=0;end
            else begin x_wave_v<=send||late_v;late_v<=valid[CAPTURE_LAT-1]&&MUT_BEAT==2&&cap_beat==3;end
        always @(posedge clk)begin
            if(late_v)begin x_wave_beat<=2'd3;x_wave_word<=late_word;x_wave<=late_d;end
            else if(send)begin x_wave_beat<=mut_beat;x_wave_word<=cap_word;x_wave<=cap_d;end
            late_word<=cap_word;late_d<=cap_d;
        end
    end endgenerate
endmodule
`default_nettype wire
