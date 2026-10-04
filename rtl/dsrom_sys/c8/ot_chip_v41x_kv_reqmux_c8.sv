`timescale 1ns/1ps
// Per-stack K-side request mux for packed window FP8 and selected main-CKV
// FP4 fetchers.  The existing per-PC arbiter still chooses between this K
// channel and the pooled indexer.  A tag bit distinguishes interleaved read
// responses; only the window writer may receive K write completions.
module ot_chip_v41x_kv_reqmux_c8 #(
    parameter integer C8_PUBLICATION=0,
    parameter integer HAW = 30,
    parameter integer TAGW = 16
) (
    input  wire [3:0]          w_v,
    output wire [3:0]          w_rdy,
    input  wire [4*HAW-1:0]    w_addr,
    input  wire [15:0]         w_len,
    input  wire [4*TAGW-1:0]   w_tag,
    input  wire [3:0]          w_we,
    input  wire [1023:0]       w_wdata,
    input  wire [127:0]        w_wstrb,
    output wire [3:0]          w_wr_done,
    output wire [3:0]          w_sv,
    input  wire [3:0]          w_srdy,
    output wire [4*TAGW-1:0]   w_stag,
    output wire [15:0]         w_sbeat,
    output wire [1023:0]       w_sdata,
    input  wire [3:0]          c_v,
    output wire [3:0]          c_rdy,
    input  wire [4*HAW-1:0]    c_addr,
    input  wire [15:0]         c_len,
    input  wire [4*TAGW-1:0]   c_tag,
    input  wire [3:0]          c_we,
    input  wire [1023:0]       c_wdata,
    input  wire [127:0]        c_wstrb,
    output wire [3:0]          c_wr_done,
    output wire [3:0]          c_sv,
    input  wire [3:0]          c_srdy,
    output wire [4*TAGW-1:0]   c_stag,
    output wire [15:0]         c_sbeat,
    output wire [1023:0]       c_sdata,
    output wire [3:0]          m_v,
    input  wire [3:0]          m_rdy,
    output wire [4*HAW-1:0]    m_addr,
    output wire [15:0]         m_len,
    output wire [4*TAGW-1:0]   m_tag,
    output wire [3:0]          m_we,
    output wire [1023:0]       m_wdata,
    output wire [127:0]        m_wstrb,
    input  wire [3:0]          m_wr_done,
    input  wire [3:0]          s_v,
    output wire [3:0]          s_rdy,
    input  wire [4*TAGW-1:0]   s_tag,
    input  wire [15:0]         s_beat,
    input  wire [1023:0]       s_data,
    input wire clk,rst_n
);
`ifndef SYNTHESIS
    initial if (TAGW < 6) $fatal(1, "KV mux needs a response-owner tag bit");
`endif
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        reg pending=0,owner_c=0;
        wire hold_write=C8_PUBLICATION && pending;
        wire choose_w = w_v[s];
        always @(posedge clk) begin
          if (!rst_n) begin pending<=0; owner_c<=0; end
          else if (C8_PUBLICATION) begin
            if (m_wr_done[s] && pending) pending<=0;
            if (m_v[s] && m_rdy[s] && m_we[s]) begin pending<=1;owner_c<=!choose_w;end
          end
        end
        wire rsp_c = s_tag[s*TAGW + TAGW-1];
        assign m_v[s] = rst_n && !hold_write && (w_v[s] || c_v[s]);
        assign w_rdy[s] = rst_n && !hold_write && choose_w && m_rdy[s];
        assign c_rdy[s] = rst_n && !hold_write && !choose_w && m_rdy[s];
        assign m_addr[s*HAW +: HAW] = choose_w ? w_addr[s*HAW +: HAW] : c_addr[s*HAW +: HAW];
        assign m_len[s*4 +: 4] = choose_w ? w_len[s*4 +: 4] : c_len[s*4 +: 4];
        assign m_tag[s*TAGW +: TAGW] = choose_w ?
            {1'b0, w_tag[s*TAGW +: TAGW-1]} :
            {1'b1, c_tag[s*TAGW +: TAGW-1]};
        // CKV is published by ingest, then read-only to this DMA.  Fail
        // closed if a future CKV requester accidentally asserts write.
        assign m_we[s] = choose_w ? w_we[s] : (C8_PUBLICATION ? c_we[s] : 1'b0);
        assign m_wdata[s*256 +: 256] = choose_w ? w_wdata[s*256 +: 256] : (C8_PUBLICATION ? c_wdata[s*256 +: 256] : '0);
        assign m_wstrb[s*32 +: 32] = choose_w ? w_wstrb[s*32 +: 32] : (C8_PUBLICATION ? c_wstrb[s*32 +: 32] : '0);
        assign w_wr_done[s] = C8_PUBLICATION ? (rst_n && pending && !owner_c && m_wr_done[s]) : m_wr_done[s];
        assign c_wr_done[s] = C8_PUBLICATION && rst_n && pending && owner_c && m_wr_done[s]; // selected CKV is read-only
        assign w_sv[s] = s_v[s] && !rsp_c;
        assign c_sv[s] = s_v[s] && rsp_c;
        assign w_stag[s*TAGW +: TAGW] = {1'b0, s_tag[s*TAGW +: TAGW-1]};
        assign c_stag[s*TAGW +: TAGW] = {1'b0, s_tag[s*TAGW +: TAGW-1]};
        assign w_sbeat[s*4 +: 4] = s_beat[s*4 +: 4];
        assign c_sbeat[s*4 +: 4] = s_beat[s*4 +: 4];
        assign w_sdata[s*256 +: 256] = s_data[s*256 +: 256];
        assign c_sdata[s*256 +: 256] = s_data[s*256 +: 256];
        assign s_rdy[s] = rsp_c ? c_srdy[s] : w_srdy[s];
    end endgenerate
endmodule
