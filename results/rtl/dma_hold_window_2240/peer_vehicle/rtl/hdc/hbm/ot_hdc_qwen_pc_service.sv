`timescale 1ns/1ps
// One physical HBM pseudo-channel shared by all Qwen traffic classes. Each
// client holds its request until accepted; a bounded credit tracks every
// accepted request through a read response or write completion. The high tag
// bits route out-of-order returns to their owner. Round-robin grants prevent
// a streaming matrix preload from starving KV writes and reads.
module ot_hdc_qwen_pc_service #(
    parameter integer NC=5,
    parameter integer AW=32,
    parameter integer CTAGW=17,
    parameter integer MAX_OUT=16,
    parameter integer CW=$clog2(MAX_OUT+1),
    parameter integer SIDW=$clog2(NC),
    parameter integer PTAGW=SIDW+CTAGW
) (
    input wire clk, rst_n,
    input wire [NC-1:0] c_req_v,
    output reg [NC-1:0] c_req_rdy,
    input wire [NC-1:0] c_req_we,
    input wire [NC*AW-1:0] c_req_addr,
    input wire [NC*CTAGW-1:0] c_req_tag,
    input wire [NC*256-1:0] c_req_data,
    output reg [NC-1:0] c_rsp_v,
    input wire [NC-1:0] c_rsp_rdy,
    output reg [NC*CTAGW-1:0] c_rsp_tag,
    output reg [NC*256-1:0] c_rsp_data,
    output reg [NC-1:0] c_wr_done_v,
    output reg [NC*CTAGW-1:0] c_wr_done_tag,
    output reg p_req_v,
    input wire p_req_rdy,
    output reg p_req_we,
    output reg [AW-1:0] p_req_addr,
    output reg [PTAGW-1:0] p_req_tag,
    output reg [255:0] p_req_data,
    input wire p_rsp_v,
    output reg p_rsp_rdy,
    input wire [PTAGW-1:0] p_rsp_tag,
    input wire [255:0] p_rsp_data,
    input wire p_wr_done_v,
    input wire [PTAGW-1:0] p_wr_done_tag,
    output reg fault
);
    initial if (NC<2 || NC>(1<<SIDW) || MAX_OUT<1 || PTAGW!=SIDW+CTAGW)
        $fatal(1,"unsupported Qwen PC service geometry");

    reg [SIDW-1:0] rr_head;
    reg [CW-1:0] outstanding [0:NC-1];
    reg grant;
    reg [SIDW-1:0] grant_id;
    integer candidate;
    wire [SIDW-1:0] rsp_id=p_rsp_tag[PTAGW-1:CTAGW];
    wire [SIDW-1:0] wr_id=p_wr_done_tag[PTAGW-1:CTAGW];
    wire rsp_take=p_rsp_v && p_rsp_rdy;
    wire req_take=p_req_v && p_req_rdy;
    integer c;
    always @(*) begin
        grant=0; grant_id=0;
        c_req_rdy=0;
        p_req_v=0; p_req_we=0; p_req_addr=0; p_req_tag=0; p_req_data=0;
        for (integer step=0;step<NC;step=step+1) begin
            candidate=rr_head+step;
            if (candidate>=NC) candidate=candidate-NC;
            if (!grant && c_req_v[candidate] && outstanding[candidate]<MAX_OUT) begin
                grant=1;
                grant_id=SIDW'(candidate);
            end
        end
        if (grant) begin
            p_req_v=1;
            p_req_we=c_req_we[grant_id];
            p_req_addr=c_req_addr[grant_id*AW +: AW];
            p_req_tag={grant_id,c_req_tag[grant_id*CTAGW +: CTAGW]};
            p_req_data=c_req_data[grant_id*256 +: 256];
            c_req_rdy[grant_id]=p_req_rdy;
        end
        c_rsp_v=0; c_rsp_tag=0; c_rsp_data=0; p_rsp_rdy=0;
        if (p_rsp_v && rsp_id<NC) begin
            c_rsp_v[rsp_id]=1;
            c_rsp_tag[rsp_id*CTAGW +: CTAGW]=p_rsp_tag[CTAGW-1:0];
            c_rsp_data[rsp_id*256 +: 256]=p_rsp_data;
            p_rsp_rdy=c_rsp_rdy[rsp_id];
        end
        c_wr_done_v=0; c_wr_done_tag=0;
        if (p_wr_done_v && wr_id<NC) begin
            c_wr_done_v[wr_id]=1;
            c_wr_done_tag[wr_id*CTAGW +: CTAGW]=p_wr_done_tag[CTAGW-1:0];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rr_head<=0; fault<=0;
            for (c=0;c<NC;c=c+1) outstanding[c]<=0;
        end else begin
            if (req_take) rr_head <= (grant_id == NC-1) ? '0 : grant_id+1'b1;
            if ((p_rsp_v && rsp_id>=NC) || (p_wr_done_v && wr_id>=NC) ||
                (p_rsp_v && p_wr_done_v && rsp_id==wr_id && outstanding[rsp_id]<2))
                fault<=1;
            for (c=0;c<NC;c=c+1) begin
                if (rsp_take && rsp_id==c && outstanding[c]==0) fault<=1;
                if (p_wr_done_v && wr_id==c && outstanding[c]==0) fault<=1;
                outstanding[c] <= outstanding[c] +
                    CW'(req_take && grant_id==c) -
                    CW'(rsp_take && rsp_id==c) -
                    CW'(p_wr_done_v && wr_id==c);
            end
        end
    end
endmodule
