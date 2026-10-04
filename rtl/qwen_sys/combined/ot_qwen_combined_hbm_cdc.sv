`timescale 1ns/1ps
// Baseline HBM transport only. Actual accept/ready is preserved at both ends;
// no FIFO acceptance is a write completion. Mutable FIFO payload is SECDED.
module ot_qwen_combined_hbm_cdc #(
    parameter integer NPC=32,TAGW=13,REQ_DEPTH=16,RSP_DEPTH=8
)(
    input wire clk,rst_n,hclk,hrst_n,
    input wire [3:0] s_req_v,s_req_we,output wire [3:0] s_req_ready,
    input wire [95:0] s_req_addr,input wire [19:0] s_req_len,
    input wire [4*TAGW-1:0] s_req_tag,input wire [1023:0] s_req_wdata,
    output wire [4*NPC-1:0] s_rsp_v,s_rsp_wr,input wire [4*NPC-1:0] s_rsp_ready,
    output wire [4*NPC*TAGW-1:0] s_rsp_tag,
    output wire [4*NPC*4-1:0] s_rsp_beat,output wire [4*NPC*256-1:0] s_rsp_data,
    input wire [4*NPC-1:0] h_pc_room,output wire [4*NPC-1:0] s_pc_room,
    output wire [3:0] h_req_v,h_req_we,input wire [3:0] h_req_ready,
    output wire [95:0] h_req_addr,output wire [19:0] h_req_len,
    output wire [4*TAGW-1:0] h_req_tag,output wire [1023:0] h_req_wdata,
    input wire [4*NPC-1:0] h_rsp_v,h_rsp_wr,output wire [4*NPC-1:0] h_rsp_ready,
    input wire [4*NPC*TAGW-1:0] h_rsp_tag,
    input wire [4*NPC*4-1:0] h_rsp_beat,input wire [4*NPC*256-1:0] h_rsp_data,
    output wire fault,output wire h_fault
);
    import ot_gpu_w6_secded_pkg::*;
    localparam integer BW=320,CW=360;
    initial if(TAGW!=13 || NPC!=32)$fatal(1,"combined fullshape HBM ABI is four stacks/32PC/tag13");
    function automatic [CW-1:0] enc(input [BW-1:0] raw);
        for(integer b=0;b<5;b=b+1)enc[b*72 +:72]=encode64(raw[b*64 +:64]);
    endfunction
    wire [3:0] req_bad;wire [4*NPC-1:0] rsp_bad;
    // Advisory channel room is synchronized; FIFO/controller ready is always
    // authoritative. A stale room bit can defer a request, never accept it.
    (* async_reg="true" *) reg [4*NPC-1:0] room_sync1,room_sync2;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin room_sync1<=0;room_sync2<=0;end
        else begin room_sync1<=h_pc_room;room_sync2<=room_sync1;end
    assign s_pc_room=room_sync2;
    reg c_bad,h_bad;
    always @(posedge clk or negedge rst_n)if(!rst_n)c_bad<=0;else if(|rsp_bad)c_bad<=1;
    always @(posedge hclk or negedge hrst_n)if(!hrst_n)h_bad<=0;else if(|req_bad)h_bad<=1;
    (* async_reg="true" *) reg hb1,hb2,cb1,cb2;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin hb1<=0;hb2<=0;end else begin hb1<=h_bad;hb2<=hb1;end
    always @(posedge hclk or negedge hrst_n)if(!hrst_n)begin cb1<=0;cb2<=0;end else begin cb1<=c_bad;cb2<=cb1;end
    assign fault=c_bad|hb2;assign h_fault=h_bad|cb2;
    genvar s,p,b;
    generate for(s=0;s<4;s=s+1)begin:g_req
        wire wr_ready,rd_valid;wire [CW-1:0] code;
        wire [BW-1:0] raw;wire [4:0] ue;
        for(b=0;b<5;b=b+1)begin:g_dec
            wire [65:0] d=decode64(code[b*72 +:72]);
            assign raw[b*64 +:64]=d[63:0];assign ue[b]=d[65];
        end
        wire [BW-1:0] in_raw={{(BW-1-24-5-TAGW-256){1'b0}},s_req_we[s],s_req_addr[s*24 +:24],s_req_len[s*5 +:5],s_req_tag[s*TAGW +:TAGW],s_req_wdata[s*256 +:256]};
        ot_async_fifo #(.WIDTH(CW),.DEPTH(REQ_DEPTH)) fifo(
            .wr_clk(clk),.wr_rst_n(rst_n),.wr_valid(s_req_v[s]&&s_req_ready[s]),.wr_ready(wr_ready),.wr_data(enc(in_raw)),.wr_overflow(),
            .rd_clk(hclk),.rd_rst_n(hrst_n),.rd_valid(rd_valid),.rd_ready(h_req_v[s]&&h_req_ready[s]),.rd_data(code),.rd_underflow());
        assign req_bad[s]=rd_valid&&(|ue);
        assign s_req_ready[s]=wr_ready&&!fault;
        assign h_req_v[s]=rd_valid&&!(|ue)&&!h_fault;
        assign {h_req_we[s],h_req_addr[s*24 +:24],h_req_len[s*5 +:5],h_req_tag[s*TAGW +:TAGW],h_req_wdata[s*256 +:256]}=raw[1+24+5+TAGW+256-1:0];
    end
    for(p=0;p<4*NPC;p=p+1)begin:g_rsp
        wire wr_ready,rd_valid;wire [CW-1:0] code;
        wire [BW-1:0] raw;wire [4:0] ue;
        for(b=0;b<5;b=b+1)begin:g_dec
            wire [65:0] d=decode64(code[b*72 +:72]);
            assign raw[b*64 +:64]=d[63:0];assign ue[b]=d[65];
        end
        wire [BW-1:0] in_raw={{(BW-1-TAGW-4-256){1'b0}},h_rsp_wr[p],h_rsp_tag[p*TAGW +:TAGW],h_rsp_beat[p*4 +:4],h_rsp_data[p*256 +:256]};
        ot_async_fifo #(.WIDTH(CW),.DEPTH(RSP_DEPTH)) fifo(
            .wr_clk(hclk),.wr_rst_n(hrst_n),.wr_valid(h_rsp_v[p]&&h_rsp_ready[p]),.wr_ready(wr_ready),.wr_data(enc(in_raw)),.wr_overflow(),
            .rd_clk(clk),.rd_rst_n(rst_n),.rd_valid(rd_valid),.rd_ready(s_rsp_v[p]&&s_rsp_ready[p]),.rd_data(code),.rd_underflow());
        assign rsp_bad[p]=rd_valid&&(|ue);
        assign h_rsp_ready[p]=wr_ready&&!h_fault;
        assign s_rsp_v[p]=rd_valid&&!(|ue)&&!fault;
        assign {s_rsp_wr[p],s_rsp_tag[p*TAGW +:TAGW],s_rsp_beat[p*4 +:4],s_rsp_data[p*256 +:256]}=raw[1+TAGW+4+256-1:0];
    end endgenerate
endmodule
