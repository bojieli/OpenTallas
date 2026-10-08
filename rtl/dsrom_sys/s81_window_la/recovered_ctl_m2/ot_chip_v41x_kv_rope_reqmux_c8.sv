`timescale 1ns/1ps
// Three K-side clients on the same four stack ports: packed FP8 window,
// selected FP4 CKV, and read-only RoPE. The existing per-PC HBM arbiter then
// contends this one K channel with the indexer; RoPE gains no independent port.
// Master tag [TAGW-1:TAGW-2]: 00 window, 01 CKV, 10 RoPE. Client tags must
// keep both high bits zero. The inner window/CKV mux uses one of those bits.
module ot_chip_v41x_kv_rope_reqmux_c8 #(
    parameter integer C8_PUBLICATION=0,
    parameter integer HAW = 30,
    parameter integer TAGW = 16
) (
    input  wire clk, rst_n,
    input  wire [3:0] w_v,
    output wire [3:0] w_rdy,
    input  wire [4*HAW-1:0] w_addr,
    input  wire [15:0] w_len,
    input  wire [4*TAGW-1:0] w_tag,
    input  wire [3:0] w_we,
    input  wire [1023:0] w_wdata,
    input  wire [127:0] w_wstrb,
    output wire [3:0] w_wr_done,
    output wire [3:0] w_sv,
    input  wire [3:0] w_srdy,
    output wire [4*TAGW-1:0] w_stag,
    output wire [15:0] w_sbeat,
    output wire [1023:0] w_sdata,
    input  wire [3:0] c_v,
    output wire [3:0] c_rdy,
    input  wire [4*HAW-1:0] c_addr,
    input  wire [15:0] c_len,
    input  wire [4*TAGW-1:0] c_tag,
    input  wire [3:0] c_we,
    input  wire [1023:0] c_wdata,
    input  wire [127:0] c_wstrb,
    output wire [3:0] c_wr_done,
    output wire [3:0] c_sv,
    input  wire [3:0] c_srdy,
    output wire [4*TAGW-1:0] c_stag,
    output wire [15:0] c_sbeat,
    output wire [1023:0] c_sdata,
    input  wire [3:0] p_v,
    output wire [3:0] p_rdy,
    input  wire [4*HAW-1:0] p_addr,
    input  wire [15:0] p_len,
    input  wire [4*TAGW-1:0] p_tag,
    input  wire [3:0] p_we,
    input  wire [1023:0] p_wdata,
    input  wire [127:0] p_wstrb,
    output wire [3:0] p_wr_done,
    output wire [3:0] p_sv,
    input  wire [3:0] p_srdy,
    output wire [4*TAGW-1:0] p_stag,
    output wire [15:0] p_sbeat,
    output wire [1023:0] p_sdata,
    output wire [3:0] m_v,
    input  wire [3:0] m_rdy,
    output wire [4*HAW-1:0] m_addr,
    output wire [15:0] m_len,
    output wire [4*TAGW-1:0] m_tag,
    output wire [3:0] m_we,
    output wire [1023:0] m_wdata,
    output wire [127:0] m_wstrb,
    input  wire [3:0] m_wr_done,
    input  wire [3:0] s_v,
    output wire [3:0] s_rdy,
    input  wire [4*TAGW-1:0] s_tag,
    input  wire [15:0] s_beat,
    input  wire [1023:0] s_data,
    output reg  fault,
    output reg  [31:0] rope_grants,
    output reg  [31:0] rope_wait_cycles
);
`ifndef SYNTHESIS
    initial if (TAGW < 4) $fatal(1,"KV/RoPE mux needs two owner-tag bits");
`endif
    wire [4*TAGW-5:0] w_t, c_t, w_st, c_st;
    wire [3:0] k_v, k_we;
    wire [4*HAW-1:0] k_addr;
    wire [15:0] k_len;
    wire [1023:0] k_wdata;
    wire [127:0] k_wstrb;
    wire [3:0] k_master_rdy, k_master_wdone, k_master_sv, k_master_srdy;
    wire [4*(TAGW-1)-1:0] k_master_tag, k_master_stag;
    wire [15:0] k_master_sbeat;
    wire [1023:0] k_master_sdata;
    wire [3:0] bad_tag;
    wire [3:0] w_req_v,c_req_v,p_req_v;
    wire [3:0] w_inner_rdy,c_inner_rdy;
    wire [2:0] p_grant_n = {2'b0,p_v[0]&&p_rdy[0]}+{2'b0,p_v[1]&&p_rdy[1]}+
                           {2'b0,p_v[2]&&p_rdy[2]}+{2'b0,p_v[3]&&p_rdy[3]};
    wire [2:0] p_wait_n = {2'b0,p_v[0]&&!p_rdy[0]}+{2'b0,p_v[1]&&!p_rdy[1]}+
                          {2'b0,p_v[2]&&!p_rdy[2]}+{2'b0,p_v[3]&&!p_rdy[3]};
    reg [3:0] turn;
    genvar s;
    generate for (s=0;s<4;s=s+1) begin : g_s
        wire [TAGW-1:0] wt=w_tag[s*TAGW +: TAGW];
        wire [TAGW-1:0] ct=c_tag[s*TAGW +: TAGW];
        wire [TAGW-1:0] pt=p_tag[s*TAGW +: TAGW];
        assign w_t[s*(TAGW-1) +: TAGW-1]=wt[TAGW-2:0];
        assign c_t[s*(TAGW-1) +: TAGW-1]=ct[TAGW-2:0];
        assign w_req_v[s]=w_v[s] && !(|wt[TAGW-1:TAGW-2]);
        assign c_req_v[s]=c_v[s] && !(|ct[TAGW-1:TAGW-2]) && (!c_we[s] || C8_PUBLICATION);
        assign p_req_v[s]=p_v[s] && !(|pt[TAGW-1:TAGW-2]) && !p_we[s];
        assign w_rdy[s]=w_inner_rdy[s] && w_req_v[s];
        assign c_rdy[s]=c_inner_rdy[s] && c_req_v[s];
        assign bad_tag[s]=(w_v[s] && |wt[TAGW-1:TAGW-2]) ||
                           (c_v[s] && (|ct[TAGW-1:TAGW-2] || (c_we[s] && !C8_PUBLICATION))) ||
                           (p_v[s] && (|pt[TAGW-1:TAGW-2] || p_we[s])) ||
                           (s_v[s] && s_tag[s*TAGW+TAGW-1 -: 2] == 2'b11);
        wire choose_k=k_v[s] && (!p_req_v[s] || !turn[s]);
        assign k_master_rdy[s]=m_rdy[s] && choose_k;
        assign p_rdy[s]=m_rdy[s] && p_req_v[s] && !choose_k;
        assign m_v[s]=k_v[s] || p_req_v[s];
        assign m_addr[s*HAW +: HAW]=choose_k ? k_addr[s*HAW +: HAW] : p_addr[s*HAW +: HAW];
        assign m_len[s*4 +: 4]=choose_k ? k_len[s*4 +: 4] : p_len[s*4 +: 4];
        assign m_tag[s*TAGW +: TAGW]=choose_k ?
            {1'b0,k_master_tag[s*(TAGW-1) +: TAGW-1]} :
            {1'b1,pt[TAGW-2:0]};
        assign m_we[s]=choose_k ? k_we[s] : 1'b0;
        assign m_wdata[s*256 +: 256]=choose_k ? k_wdata[s*256 +: 256] : '0;
        assign m_wstrb[s*32 +: 32]=choose_k ? k_wstrb[s*32 +: 32] : '0;
        assign k_master_wdone[s]=m_wr_done[s];
        assign p_wr_done[s]=1'b0;
        assign k_master_sv[s]=s_v[s] && !s_tag[s*TAGW+TAGW-1];
        assign p_sv[s]=s_v[s] && s_tag[s*TAGW+TAGW-1] &&
                       !s_tag[s*TAGW+TAGW-2];
        assign k_master_stag[s*(TAGW-1) +: TAGW-1]=s_tag[s*TAGW +: TAGW-1];
        assign p_stag[s*TAGW +: TAGW]={1'b0,s_tag[s*TAGW +: TAGW-1]};
        assign k_master_sbeat[s*4 +: 4]=s_beat[s*4 +: 4];
        assign p_sbeat[s*4 +: 4]=s_beat[s*4 +: 4];
        assign k_master_sdata[s*256 +: 256]=s_data[s*256 +: 256];
        assign p_sdata[s*256 +: 256]=s_data[s*256 +: 256];
        assign s_rdy[s]=s_tag[s*TAGW+TAGW-1] ?
            (s_tag[s*TAGW+TAGW-2] ? 1'b1 : p_srdy[s]) : k_master_srdy[s];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) turn[s]<=0;
            else if (m_v[s] && m_rdy[s]) turn[s]<=choose_k;
    end endgenerate
    ot_chip_v41x_kv_reqmux_c8 #(.C8_PUBLICATION(C8_PUBLICATION), .HAW(HAW), .TAGW(TAGW-1)) u_kv (
        .clk(clk),.rst_n(rst_n),.w_v(w_req_v), .w_rdy(w_inner_rdy), .w_addr(w_addr), .w_len(w_len),
        .w_tag(w_t), .w_we(w_we), .w_wdata(w_wdata), .w_wstrb(w_wstrb),
        .w_wr_done(w_wr_done), .w_sv(w_sv), .w_srdy(w_srdy),
        .w_stag(w_st), .w_sbeat(w_sbeat), .w_sdata(w_sdata),
        .c_v(c_req_v), .c_rdy(c_inner_rdy), .c_addr(c_addr), .c_len(c_len),
        .c_tag(c_t), .c_we(c_we), .c_wdata(c_wdata), .c_wstrb(c_wstrb),
        .c_wr_done(c_wr_done), .c_sv(c_sv), .c_srdy(c_srdy),
        .c_stag(c_st), .c_sbeat(c_sbeat), .c_sdata(c_sdata),
        .m_v(k_v), .m_rdy(k_master_rdy), .m_addr(k_addr), .m_len(k_len),
        .m_tag(k_master_tag), .m_we(k_we), .m_wdata(k_wdata),
        .m_wstrb(k_wstrb), .m_wr_done(k_master_wdone),
        .s_v(k_master_sv), .s_rdy(k_master_srdy), .s_tag(k_master_stag),
        .s_beat(k_master_sbeat), .s_data(k_master_sdata));
    generate for (s=0;s<4;s=s+1) begin : g_tags
        assign w_stag[s*TAGW +: TAGW]={1'b0,w_st[s*(TAGW-1) +: TAGW-1]};
        assign c_stag[s*TAGW +: TAGW]={1'b0,c_st[s*(TAGW-1) +: TAGW-1]};
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault<=0; rope_grants<=0; rope_wait_cycles<=0; end
        else begin
            if (|bad_tag) fault<=1;
            rope_grants<=rope_grants+{29'd0,p_grant_n};
            rope_wait_cycles<=rope_wait_cycles+{29'd0,p_wait_n};
        end
endmodule
