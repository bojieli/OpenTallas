`timescale 1ns/1ps
// Select one quarter's 16-key groups from a replicated full key image.
// Each group starts at an arbitrary key, including an 8-key offset within a
// 16-key HBM stream beat.  The current kstream starts at a super-block, so
// this correctness-rate wrapper discards the prefix before each group.
// A direct sector-start kstream is needed to remove that read amplification.
module ot_hdc_v41x_idx_pool_replica #(
    parameter integer S=0, NPC=32, AW=28, HW=20, TAGW=16, LENW=4, BEATW=4
) (
    input wire clk,rst_n,cmd_v,
    input wire [HW-1:0] cmd_base,
    input wire [29:0] cmd_nkeys,
    output wire busy,
    output wire [NPC-1:0] req_v,
    input wire [NPC-1:0] req_rdy,
    output wire [NPC*AW-1:0] req_addr,
    output wire [NPC*LENW-1:0] req_len,
    output wire [NPC*TAGW-1:0] req_tag,
    input wire [NPC-1:0] rsp_v,
    output wire [NPC-1:0] rsp_rdy,
    input wire [NPC*TAGW-1:0] rsp_tag,
    input wire [NPC*BEATW-1:0] rsp_beat,
    input wire [NPC*256-1:0] rsp_data,
    output wire o_valid,
    input wire o_ready,
    output reg [15:0] o_kv,
    output reg [16*544-1:0] o_key,
    output wire [47:0] cnt_keys_streamed,cnt_hbm_beats
);
    localparam [1:0] IDLE=0,LAUNCH=1,WAIT=2,OUT=3;
    reg [1:0] st;
    reg [HW-1:0] base;
    reg [29:0] n,qs,l3,groups,b;
    reg [10:0] skip, take, seen;
    wire [29:0] qlen=S==3 ? l3 : qs;
    wire [29:0] first=S*qs+b*30'd16;
    wire [29:0] remain=(b*30'd16<qlen) ? qlen-b*30'd16 : 30'd0;
    wire [10:0] take_now=remain>=16 ? 11'd16 : remain[10:0];
    wire [10:0] skip_now=first[9:0];
    wire raw_cmd=st==LAUNCH && take_now!=0;
    wire [HW-1:0] raw_base=base+17*(first>>10);
    wire [HW+9:0] raw_nkeys=skip_now+take_now;
    wire raw_busy,raw_v,raw_r;
    wire [15:0] raw_kv;
    wire [16*544-1:0] raw_key;
    assign raw_r=st==WAIT;
    ot_hdc_v41x_idx_kstream #(.NPC(NPC),.WB(32),.GA(64),.AW(AW),.HW(HW),
        .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(256)) stream (
        .clk(clk),.rst_n(rst_n),.cmd_v(raw_cmd),.cmd_base(raw_base),.cmd_nkeys(raw_nkeys),
        .busy(raw_busy),.req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),
        .req_len(req_len),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),
        .rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),
        .o_valid(raw_v),.o_ready(raw_r),.o_kv(raw_kv),.o_key(raw_key),
        .cnt_keys_streamed(cnt_keys_streamed),.cnt_hbm_beats(cnt_hbm_beats));
    assign o_valid=st==OUT;
    assign busy=st!=IDLE;
    integer j;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            st<=IDLE;base<=0;n<=0;qs<=0;l3<=0;groups<=0;b<=0;
            skip<=0;take<=0;seen<=0;o_kv<=0;o_key<=0;
        end else begin
            case(st)
                IDLE: if(cmd_v) begin
                    base<=cmd_base;n<=cmd_nkeys;qs<={cmd_nkeys[29:5],3'b000};
                    l3<=cmd_nkeys-3*{cmd_nkeys[29:5],3'b000};
                    groups<=(cmd_nkeys-3*{cmd_nkeys[29:5],3'b000}+15)/16;
                    b<=0;st<=LAUNCH;
                end
                LAUNCH: begin
                    o_kv<=0;o_key<=0;seen<=0;skip<=skip_now;take<=take_now;
                    st<=take_now==0 ? OUT : WAIT;
                end
                WAIT: begin
                    if(raw_v && raw_r) begin
                        for(j=0;j<16;j=j+1)
                            if(raw_kv[j] && seen+j>=skip && seen+j<skip+take) begin
                                o_kv[seen+j-skip]<=1;
                                o_key[544*(seen+j-skip) +: 544]<=raw_key[544*j +: 544];
                            end
                        seen<=seen+16;
                    end
                    if(!raw_busy && seen>=skip+take) st<=OUT;
                end
                OUT: if(o_ready) begin
                    if(b+1>=groups) st<=IDLE;
                    else begin b<=b+1;st<=LAUNCH;end
                end
            endcase
        end
    end
endmodule
