`timescale 1ns/1ps
// Port-only extraction of the existing four row clients: no KV fill arbiter,
// duplicate memory, new row engine, arithmetic, ownership model or queue.
module ot_qwen_combined_stream4_rows #(parameter integer R=8,NPC=32,RTAGW=12,MTAGW=13)(
    input wire clk,rst_n,start,input wire [17:0] pos,input wire [7:0] layer,input wire memory_ready,
    input wire [4*R-1:0] row_valid,row_v,row_g,input wire [4*R*13-1:0] row_t,
    output wire [4*R-1:0] row_rsp_valid,output wire [4*R*1024-1:0] row_rsp_data,
    output wire [3:0] m_req_v,m_req_we,input wire [3:0] m_req_ready,
    output wire [95:0] m_req_addr,output wire [19:0] m_req_len,
    output wire [4*MTAGW-1:0] m_req_tag,output wire [1023:0] m_req_wdata,
    input wire [4*NPC-1:0] m_pc_room,m_rsp_v,m_rsp_wr,output wire [4*NPC-1:0] m_rsp_ready,
    input wire [4*NPC*MTAGW-1:0] m_rsp_tag,input wire [4*NPC*4-1:0] m_rsp_beat,input wire [4*NPC*256-1:0] m_rsp_data,
    output wire fault,row_drained
);
    wire [3:0] r_fault,r_empty;
    wire [4*NPC-1:0] bad_return;
    reg identity_fault;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)identity_fault<=0;else if(|bad_return)identity_fault<=1;
    assign fault=identity_fault|(|r_fault);assign row_drained=&r_empty;
    assign m_req_we=0;assign m_req_wdata=0;
    genvar st,pc;
    generate for(st=0;st<4;st=st+1)begin:g_stack
        wire [RTAGW-1:0] tag;
        wire [NPC*RTAGW-1:0] rt;
        wire [NPC-1:0] rv,ready;wire req_pending;
        assign m_req_v[st]=req_pending&&!fault;
        for(pc=0;pc<NPC;pc=pc+1)begin:g_pc
            assign rt[pc*RTAGW +: RTAGW]=m_rsp_tag[(st*NPC+pc)*MTAGW +: RTAGW];
            assign bad_return[st*NPC+pc]=m_rsp_v[st*NPC+pc]&&(!m_rsp_tag[(st*NPC+pc)*MTAGW+RTAGW]||m_rsp_wr[st*NPC+pc]);
            assign rv[pc]=m_rsp_v[st*NPC+pc]&&!bad_return[st*NPC+pc]&&!fault;
            assign m_rsp_ready[st*NPC+pc]=ready[pc]&&!fault;
        end
        assign m_req_tag[st*MTAGW +: MTAGW]={1'b1,tag};
        ot_qwen_nearhbm_row_sectors #(.ENABLE(1),.S(st),.R(R),.NPC(NPC),.TAGW(RTAGW)) rows(
            .clk(clk),.rst_n(rst_n),.start(start),.pos(pos),.layer(layer),.memory_ready(memory_ready&&!fault),
            .row_valid(row_valid[st*R +: R]),.row_v(row_v[st*R +: R]),.row_g(row_g[st*R +: R]),.row_t(row_t[st*R*13 +: R*13]),
            .row_rsp_valid(row_rsp_valid[st*R +: R]),.row_rsp_data(row_rsp_data[st*R*1024 +: R*1024]),
            .req_v(req_pending),.req_ready(m_req_ready[st]&&!fault),.pc_room(m_pc_room[st*NPC +: NPC]),
            .req_addr(m_req_addr[st*24 +:24]),.req_len(m_req_len[st*5 +:5]),.req_tag(tag),
            .rsp_v(rv),.rsp_wr(m_rsp_wr[st*NPC +: NPC]),.rsp_ready(ready),.rsp_tag(rt),.rsp_beat(m_rsp_beat[st*NPC*4 +: NPC*4]),.rsp_data(m_rsp_data[st*NPC*256 +: NPC*256]),
            .fault(r_fault[st]),.fault_code(),.drained(r_empty[st]),.rows_retired(),.read_bursts());
    end endgenerate
endmodule
