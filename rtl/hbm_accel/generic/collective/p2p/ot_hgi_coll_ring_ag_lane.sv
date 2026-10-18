`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL3c (coordinator 0dr, 10-18): SECOND cross-quadrant all-gather ring (gather-only stop).
// d4g x all-gather over TWO rings: the compiler splits every quadrant's slice of x over ring A
// (the full COLL stop ot_hgi_coll_ring_ag, all-reduce + gather) and ring B (this stop: GATHER
// only, no add lanes, no carry/result state). Flit format, hop timing (2 edges), ttl rule,
// injection lead (state read 2 edges before the inject) and per-direction publish ports are
// IDENTICAL to ring A, so one static timeline format drives both rings; ring B doubles the
// XQ lane (2 x 280 b per direction) and halves the gather time.
// Static: the compiler reserves every lp write, read, inject, transit and arrival; no queue,
// credit, ready or arbitration; any mismatch raises the sticky fault (never stalls).
// Reset only on control state (valid bits, slot occupancy, read pipe valid, fault).
module ot_hgi_coll_ring_ag_lane #(
    parameter integer MUT_TTL=0, MUT_SRC=0
)(
    input wire clk, rst_n,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output wire [279:0] cw_o, ccw_o,
    input wire lp_we,
    input wire [2:0] lp_tag,
    input wire [255:0] lp_data,
    input wire state_read_tx,
    input wire [2:0] state_tx_tag,
    input wire [1:0] tx_inject, tx_forward,
    input wire [2:0] tx_tag,
    input wire [3:0] tx_ttl,
    input wire [1:0] rx_slot,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    output reg [1:0] ag_v,
    output reg [3:0] ag_src,
    output reg [5:0] ag_tag,
    output reg [511:0] ag_d,
    output reg fault
);
    // control
    reg [1:0] pin_v, out_v;
    reg [7:0] local_v;
    reg prep_v, read_v;
    reg [2:0] prep_tag, read_tag;
    // data (no reset)
    reg [278:0] pin_p [0:1];
    reg [278:0] out_p [0:1];
    reg [255:0] buf_d [0:7];
    reg [255:0] tx_q;
    wire [279:0] pin [0:1];
    assign pin[0]={pin_v[0],pin_p[0]};assign pin[1]={pin_v[1],pin_p[1]};
    assign cw_o={out_v[0],out_p[0]};assign ccw_o={out_v[1],out_p[1]};
    reg [279:0] nx_out [0:1];
    always @* begin:outs
        reg [279:0] x;
        for(integer d=0;d<2;d=d+1)begin
            x=pin[d];nx_out[d]=0;
            if(tx_forward[d])begin
                nx_out[d]=x;
                nx_out[d][272:271]=x[272:271]-(MUT_TTL?2'd2:2'd1);
            end
            if(tx_inject[d])nx_out[d]={1'b1,2'd3,qid,qid,tx_ttl[d*2+:2],tx_tag,1'b0,11'b0,tx_q};
        end
    end
    always @(posedge clk) begin:data
        reg [279:0] x;
        pin_p[0]<=cw_i[278:0];pin_p[1]<=ccw_i[278:0];
        out_p[0]<=nx_out[0][278:0];out_p[1]<=nx_out[1][278:0];
        if(lp_we)buf_d[lp_tag]<=lp_data;
        if(prep_v)tx_q<=buf_d[prep_tag];
        for(integer d=0;d<2;d=d+1)begin
            x=pin[d];
            if(rx_slot[d] && x[278:277]==3)begin
                ag_src[d*2+:2]<=MUT_SRC?qid:x[276:275];ag_tag[d*3+:3]<=x[270:268];ag_d[d*256+:256]<=x[255:0];
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin:step
        reg [279:0] x;
        if(!rst_n)begin
            pin_v<=0;out_v<=0;local_v<=0;prep_v<=0;read_v<=0;ag_v<=0;fault<=0;
        end else begin
            pin_v<={ccw_i[279],cw_i[279]};out_v<={nx_out[1][279],nx_out[0][279]};
            prep_v<=state_read_tx;prep_tag<=state_tx_tag;
            read_v<=prep_v;read_tag<=prep_tag;
            ag_v<=0;
            if((|tx_inject)!=read_v)fault<=1;
            if((|tx_inject) && tx_tag!=read_tag)fault<=1;
            if(state_read_tx && !local_v[state_tx_tag])fault<=1;
            if(state_read_tx && lp_we && lp_tag==state_tx_tag)fault<=1;
            if(lp_we)begin
                if(local_v[lp_tag])fault<=1;
                local_v[lp_tag]<=1;
            end
            for(integer d=0;d<2;d=d+1)begin
                x=pin[d];
                if(x[279]!=rx_slot[d])fault<=1;
                if(rx_slot[d])begin
                    if(x[278:277]!=3 || rx_kind[d*2+:2]!=3 || x[276:275]!=rx_src[d*2+:2] ||
                       x[270:268]!=rx_tag[d*3+:3] || x[267:256]!=0)fault<=1;
                    if(x[272:271]==0 || x[276:275]==qid)fault<=1;
                    ag_v[d]<=1;
                    if(x[272:271]>1)begin if(!tx_forward[d])fault<=1;end
                    else if(tx_forward[d])fault<=1;
                end else if(tx_forward[d])fault<=1;
                if(tx_inject[d])begin
                    if(tx_forward[d] || tx_ttl[d*2+:2]==0 || !local_v[tx_tag])fault<=1;
                end
            end
            if(|tx_inject)local_v[tx_tag]<=0;
        end
    end
endmodule
`default_nettype wire
