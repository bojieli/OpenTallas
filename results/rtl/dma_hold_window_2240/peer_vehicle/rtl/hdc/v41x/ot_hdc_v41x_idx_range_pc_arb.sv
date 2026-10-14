`timescale 1ns/1ps
// Four virtual direct-start range streams share one stack's NPC physical
// pseudo-channels. A context prefix is added to every HBM request tag and
// removed on response. The range controller reserves TAGW-3:TAGW-4, so this
// keeps the physical die HBM tag width unchanged. Each PC grants at most one
// context per cycle with a
// rotating priority. The range streams retain separate bounded ROB banks;
// this is a partitioned baseline, not the final shared-ROB area target.
module ot_hdc_v41x_idx_range_pc_arb #(
    parameter integer NPC=32,AW=28,LENW=4,TAGW=16,BEATW=4,DW=256,
    parameter integer QUANTUM=1
) (
    input wire clk,rst_n,
    input wire [4*NPC-1:0] i_req_v,
    output reg [4*NPC-1:0] i_req_rdy,
    input wire [4*NPC*AW-1:0] i_req_addr,
    input wire [4*NPC*LENW-1:0] i_req_len,
    input wire [4*NPC*TAGW-1:0] i_req_tag,
    output reg [NPC-1:0] h_req_v,
    input wire [NPC-1:0] h_req_rdy,
    output reg [NPC*AW-1:0] h_req_addr,
    output reg [NPC*LENW-1:0] h_req_len,
    output reg [NPC*TAGW-1:0] h_req_tag,
    input wire [NPC-1:0] h_rsp_v,
    output reg [NPC-1:0] h_rsp_rdy,
    input wire [NPC*TAGW-1:0] h_rsp_tag,
    input wire [NPC*BEATW-1:0] h_rsp_beat,
    input wire [NPC*DW-1:0] h_rsp_data,
    output reg [4*NPC-1:0] o_rsp_v,
    input wire [4*NPC-1:0] o_rsp_rdy,
    output reg [4*NPC*TAGW-1:0] o_rsp_tag,
    output reg [4*NPC*BEATW-1:0] o_rsp_beat,
    output reg [4*NPC*DW-1:0] o_rsp_data,
    output reg [31:0] dbg_grants
);
    reg [1:0] rr[0:NPC-1];
    localparam integer BW=TAGW-4;
    reg [15:0] served[0:NPC-1];
    reg [1:0] selected[0:NPC-1];
    reg has_req[0:NPC-1];
    integer p,d,c,idx,rctx;
    always @* begin
        i_req_rdy='0;h_req_v='0;h_req_addr='0;h_req_len='0;h_req_tag='0;
        o_rsp_v='0;o_rsp_tag='0;o_rsp_beat='0;o_rsp_data='0;h_rsp_rdy='0;
        for(p=0;p<NPC;p=p+1) begin
            has_req[p]=0;selected[p]=0;
            for(d=0;d<4;d=d+1) begin
                c=(int'(rr[p])+d)&3;idx=c*NPC+p;
                if(!has_req[p] && i_req_v[idx]) begin
                    has_req[p]=1;selected[p]=2'(c);
                end
            end
            if(has_req[p]) begin
                idx=selected[p]*NPC+p;
                h_req_v[p]=1;
                h_req_addr[p*AW +: AW]=i_req_addr[idx*AW +: AW];
                h_req_len[p*LENW +: LENW]=i_req_len[idx*LENW +: LENW];
                h_req_tag[p*TAGW +: TAGW]=i_req_tag[idx*TAGW +: TAGW] |
                                             (TAGW'(selected[p])<<BW);
                i_req_rdy[idx]=h_req_rdy[p];
            end
            rctx=int'(h_rsp_tag[p*TAGW+BW +: 2]);
            idx=rctx*NPC+p;
            o_rsp_v[idx]=h_rsp_v[p];
            o_rsp_tag[idx*TAGW +: TAGW]=h_rsp_tag[p*TAGW +: TAGW] &
                                           ~(TAGW'(3)<<BW);
            o_rsp_beat[idx*BEATW +: BEATW]=h_rsp_beat[p*BEATW +: BEATW];
            o_rsp_data[idx*DW +: DW]=h_rsp_data[p*DW +: DW];
            h_rsp_rdy[p]=o_rsp_rdy[idx];
        end
    end
    integer k;
    reg [6:0] grants;
    always @* begin
        grants=0;
        for(k=0;k<NPC;k=k+1) grants=grants+7'(has_req[k] && h_req_rdy[k]);
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            dbg_grants<=0;
            for(k=0;k<NPC;k=k+1) begin rr[k]<=0;served[k]<=0;end
        end else begin
            dbg_grants<=dbg_grants+32'(grants);
            for(k=0;k<NPC;k=k+1)
                if(has_req[k] && h_req_rdy[k]) begin
                    if(QUANTUM==1 || (selected[k]==rr[k] && served[k]==QUANTUM-1)) begin
                        rr[k]<=selected[k]+2'd1;
                        served[k]<=0;
                    end else if(selected[k]!=rr[k]) begin
                        rr[k]<=selected[k];
                        served[k]<=16'd1;
                    end else served[k]<=served[k]+16'd1;
                end
        end
    end
endmodule
