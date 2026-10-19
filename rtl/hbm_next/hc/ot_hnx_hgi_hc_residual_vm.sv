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
// HBM-NEXT-UNITS 2026-10-19 (hnx fork, N-row records): a launch reads npos ROWS of SPR issue slots each; row r slot i
// group b reads sector base + r*row_stride + 8 i + b.  row_stride == 0 = the d4g dense form (stride = 8 SPR, which is
// bit-identical to the original reader at SPR 320).  The multi-user / verify rows of a P = 4 record sit in separate
// VM columns: one launch, one fixed calendar, no per-row relaunch.  Wave words stay sequential over the whole launch
// (the engine's ingest check is unchanged).  New faults: SPR % 4 != 0 (static), row_stride not 32-aligned, rows
// overlapping (0 < row_stride < 8 SPR), last row past the VM.  MUT_STRIDE (bench) = the reader ignores row_stride.
module ot_hnx_hgi_hc_residual_vm #(
    parameter integer CAPTURE_LAT=19,
    parameter integer MUT_POSITION=0,
    parameter integer BEATS=1,
    parameter integer MUT_BEAT=0,
    parameter integer SPR=320,
    parameter integer MUT_STRIDE=0,
    // HUBFIX 10-19: XFC 1 = four per-face copies of the x_wave_v / x_wave_beat output register (ot_hnx_hc_xbrep, same edge,
    // same next-state) on x_wave_vf / x_wave_beatf (face f = W, N, E, S); XFC 0 = the copies are wires of the original.
    // MUT_FC (bench) 1 = the E copy (f 2) is loaded from the original register's Q (a relay one edge late).
    parameter integer XFC=0,
    parameter integer MUT_FC=0
)(
    input wire clk,rst_n,launch,
    input wire [3:0] npos,
    input wire [15:0] base_sector,
    input wire [15:0] row_stride,
    output wire [135:0] local_rq,
    output wire [7:0] local_read,
    input wire [2055:0] local_rr,
    output reg x_wave_v,
    output reg [9:0] x_wave_word,
    output reg [8192/BEATS-1:0] x_wave,
    output reg [1:0] x_wave_beat,
    output wire [3:0] x_wave_vf,
    output wire [7:0] x_wave_beatf,
    output reg done,fault
);
    reg active;
    reg [11:0] issue,total;
    reg [15:0] base;
    reg [15:0] rbase,rstep;   // current row's base sector, row stride in sectors
    reg [11:0] rslot;         // slot within the current row
    initial if(SPR<4||SPR%4!=0||SPR>512)$fatal(1,"SPR: multiple of 4, 4..512");
    wire [16:0] eff_stride=(row_stride==16'd0||MUT_STRIDE!=0)?17'(SPR*8):{1'b0,row_stride};
    reg [CAPTURE_LAT-1:0] valid;
    reg [11:0] order[0:CAPTURE_LAT-1];
    initial if(BEATS!=1&&BEATS!=4)$fatal(1,"BEATS must be 1 or 4");
    wire [1:0] cap_beat=order[CAPTURE_LAT-1][1:0];
    wire [1:0] mut_beat=(MUT_BEAT==1&&cap_beat==1)?2'd2:(MUT_BEAT==1&&cap_beat==2)?2'd1:cap_beat;
    wire fire=active;
    assign local_read={8{fire}};
    for(genvar b=0;b<8;b=b+1)assign local_rq[b*17+:17]={fire,16'(rbase+rslot*8+b)};
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;issue<=0;total<=0;base<=0;rbase<=0;rstep<=0;rslot<=0;valid<=0;done<=0;fault<=0;end
        else begin
            valid<=(valid<<1)|fire;
            done<=0;
            if(launch)begin
                if(active||(|valid)||npos<1||npos>8||base_sector[4:0]!=0||eff_stride[4:0]!=0||eff_stride<17'(SPR*8)||
                   (32'(base_sector)+32'(npos-1)*32'(eff_stride)+32'(SPR*8))>32768)fault<=1;
                active<=1;issue<=0;total<=12'(npos*SPR);base<=base_sector;rbase<=base_sector;rstep<=16'(eff_stride);rslot<=0;
            end
            if(fire)begin
                issue<=issue+1;
                if(rslot==12'(SPR-1))begin rslot<=0;rbase<=rbase+rstep;end else rslot<=rslot+1;
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
    wire nx_v,nx_en; wire [1:0] nx_beat;   // next-state of x_wave_v / x_wave_beat (shared with the face copies)
    generate if(BEATS==1)begin:g_wave
        reg [6143:0] assembly;
        always @(posedge clk)
            if(valid[CAPTURE_LAT-1]&&cap_beat!=3)assembly[cap_beat*2048+:2048]<=cap_d;
        assign nx_v=valid[CAPTURE_LAT-1]&&cap_beat==3; assign nx_en=1'b1; assign nx_beat=2'd0;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)x_wave_v<=0;
            else x_wave_v<=nx_v;
        always @(posedge clk)begin
            x_wave_beat<=nx_beat;
            if(valid[CAPTURE_LAT-1]&&cap_beat==3)begin x_wave_word<=cap_word;x_wave<={cap_d,assembly};end
        end
    end else begin:g_beats
        reg late_v; reg [9:0] late_word; reg [2047:0] late_d;
        wire send=valid[CAPTURE_LAT-1]&&!(MUT_BEAT==2&&cap_beat==3);
        assign nx_v=send||late_v; assign nx_en=send||late_v; assign nx_beat=late_v?2'd3:mut_beat;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin x_wave_v<=0;late_v<=0;end
            else begin x_wave_v<=nx_v;late_v<=valid[CAPTURE_LAT-1]&&MUT_BEAT==2&&cap_beat==3;end
        always @(posedge clk)begin
            if(nx_en)x_wave_beat<=nx_beat;
            if(late_v)begin x_wave_word<=late_word;x_wave<=late_d;end
            else if(send)begin x_wave_word<=cap_word;x_wave<=cap_d;end
            late_word<=cap_word;late_d<=cap_d;
        end
    end endgenerate
    // ---- per-face copies (HUBFIX 10-19)
    generate if(XFC!=0)begin:g_fc
        for(genvar f=0;f<4;f=f+1)begin:g_f
            wire dv=(MUT_FC==1&&f==2)?x_wave_v:nx_v, de=(MUT_FC==1&&f==2)?1'b1:nx_en;
            wire [1:0] db=(MUT_FC==1&&f==2)?x_wave_beat:nx_beat;
            ot_hnx_hc_xbrep u_rep(.clk(clk),.rst_n(rst_n),.d_v(dv),.en(de),.d_beat(db),.q_v(x_wave_vf[f]),.q_beat(x_wave_beatf[2*f+:2]));
        end
    end else begin:g_nofc
        assign x_wave_vf={4{x_wave_v}}; assign x_wave_beatf={4{x_wave_beat}};
    end endgenerate
endmodule
`default_nettype wire
