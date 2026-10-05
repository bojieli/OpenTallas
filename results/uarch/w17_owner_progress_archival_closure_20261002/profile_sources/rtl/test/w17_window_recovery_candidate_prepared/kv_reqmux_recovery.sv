`timescale 1ns/1ps
// Per-stack K-side request mux for packed window FP8 and selected main-CKV
// FP4 fetchers.  The existing per-PC arbiter still chooses between this K
// channel and the pooled indexer.  A tag bit distinguishes interleaved read
// responses; only the window writer may receive K write completions.
module ot_chip_v41x_kv_reqmux_recovery #(
    parameter integer HAW = 30,
    parameter integer TAGW = 16,
    parameter bit OPT_RECOVERY = 0,
    parameter integer SELECT_STACK = 2
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
    input  wire [1023:0]       s_data
,
    input wire rec_freeze,
    input wire rec_token,
    input wire rec_commit,
    input wire rec_down_empty,
    input wire rec_down_visible,
    input wire rec_down_token_ack,
    output wire rec_owner_empty,
    output wire rec_visible_empty,
    output wire rec_token_ack
);
generate if (!OPT_RECOVERY) begin : g_legacy
ot_chip_v41x_kv_reqmux_recovery_legacy #(
    .HAW(HAW),
    .TAGW(TAGW)
) u_impl (
    .w_v(w_v),
    .w_rdy(w_rdy),
    .w_addr(w_addr),
    .w_len(w_len),
    .w_tag(w_tag),
    .w_we(w_we),
    .w_wdata(w_wdata),
    .w_wstrb(w_wstrb),
    .w_wr_done(w_wr_done),
    .w_sv(w_sv),
    .w_srdy(w_srdy),
    .w_stag(w_stag),
    .w_sbeat(w_sbeat),
    .w_sdata(w_sdata),
    .c_v(c_v),
    .c_rdy(c_rdy),
    .c_addr(c_addr),
    .c_len(c_len),
    .c_tag(c_tag),
    .c_we(c_we),
    .c_wdata(c_wdata),
    .c_wstrb(c_wstrb),
    .c_wr_done(c_wr_done),
    .c_sv(c_sv),
    .c_srdy(c_srdy),
    .c_stag(c_stag),
    .c_sbeat(c_sbeat),
    .c_sdata(c_sdata),
    .m_v(m_v),
    .m_rdy(m_rdy),
    .m_addr(m_addr),
    .m_len(m_len),
    .m_tag(m_tag),
    .m_we(m_we),
    .m_wdata(m_wdata),
    .m_wstrb(m_wstrb),
    .m_wr_done(m_wr_done),
    .s_v(s_v),
    .s_rdy(s_rdy),
    .s_tag(s_tag),
    .s_beat(s_beat),
    .s_data(s_data)
);
assign rec_owner_empty = 1'b0;
assign rec_visible_empty = 1'b0;
assign rec_token_ack = 1'b0;
end else begin : g_recovery
ot_chip_v41x_kv_reqmux_recovery_enabled #(
    .HAW(HAW),
    .TAGW(TAGW),
    .OPT_RECOVERY(OPT_RECOVERY),
    .SELECT_STACK(SELECT_STACK)
) u_impl (
    .w_v(w_v),
    .w_rdy(w_rdy),
    .w_addr(w_addr),
    .w_len(w_len),
    .w_tag(w_tag),
    .w_we(w_we),
    .w_wdata(w_wdata),
    .w_wstrb(w_wstrb),
    .w_wr_done(w_wr_done),
    .w_sv(w_sv),
    .w_srdy(w_srdy),
    .w_stag(w_stag),
    .w_sbeat(w_sbeat),
    .w_sdata(w_sdata),
    .c_v(c_v),
    .c_rdy(c_rdy),
    .c_addr(c_addr),
    .c_len(c_len),
    .c_tag(c_tag),
    .c_we(c_we),
    .c_wdata(c_wdata),
    .c_wstrb(c_wstrb),
    .c_wr_done(c_wr_done),
    .c_sv(c_sv),
    .c_srdy(c_srdy),
    .c_stag(c_stag),
    .c_sbeat(c_sbeat),
    .c_sdata(c_sdata),
    .m_v(m_v),
    .m_rdy(m_rdy),
    .m_addr(m_addr),
    .m_len(m_len),
    .m_tag(m_tag),
    .m_we(m_we),
    .m_wdata(m_wdata),
    .m_wstrb(m_wstrb),
    .m_wr_done(m_wr_done),
    .s_v(s_v),
    .s_rdy(s_rdy),
    .s_tag(s_tag),
    .s_beat(s_beat),
    .s_data(s_data),
    .rec_freeze(rec_freeze),
    .rec_token(rec_token),
    .rec_commit(rec_commit),
    .rec_down_empty(rec_down_empty),
    .rec_down_visible(rec_down_visible),
    .rec_down_token_ack(rec_down_token_ack),
    .rec_owner_empty(rec_owner_empty),
    .rec_visible_empty(rec_visible_empty),
    .rec_token_ack(rec_token_ack)
);
end endgenerate
endmodule

`timescale 1ns/1ps
// Per-stack K-side request mux for packed window FP8 and selected main-CKV
// FP4 fetchers.  The existing per-PC arbiter still chooses between this K
// channel and the pooled indexer.  A tag bit distinguishes interleaved read
// responses; only the window writer may receive K write completions.
module ot_chip_v41x_kv_reqmux_recovery_legacy #(
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
    input  wire [1023:0]       s_data
);
`ifndef SYNTHESIS
    initial if (TAGW < 6) $fatal(1, "KV mux needs a response-owner tag bit");
`endif
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        wire choose_w = w_v[s];
        wire rsp_c = s_tag[s*TAGW + TAGW-1];
        assign m_v[s] = w_v[s] || c_v[s];
        assign w_rdy[s] = choose_w && m_rdy[s];
        assign c_rdy[s] = !choose_w && m_rdy[s];
        assign m_addr[s*HAW +: HAW] = choose_w ? w_addr[s*HAW +: HAW] : c_addr[s*HAW +: HAW];
        assign m_len[s*4 +: 4] = choose_w ? w_len[s*4 +: 4] : c_len[s*4 +: 4];
        assign m_tag[s*TAGW +: TAGW] = choose_w ?
            {1'b0, w_tag[s*TAGW +: TAGW-1]} :
            {1'b1, c_tag[s*TAGW +: TAGW-1]};
        // CKV is published by ingest, then read-only to this DMA.  Fail
        // closed if a future CKV requester accidentally asserts write.
        assign m_we[s] = choose_w ? w_we[s] : 1'b0;
        assign m_wdata[s*256 +: 256] = choose_w ? w_wdata[s*256 +: 256] : '0;
        assign m_wstrb[s*32 +: 32] = choose_w ? w_wstrb[s*32 +: 32] : '0;
        assign w_wr_done[s] = m_wr_done[s];
        assign c_wr_done[s] = 1'b0; // selected CKV is read-only
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

`timescale 1ns/1ps
// Per-stack K-side request mux for packed window FP8 and selected main-CKV
// FP4 fetchers.  The existing per-PC arbiter still chooses between this K
// channel and the pooled indexer.  A tag bit distinguishes interleaved read
// responses; only the window writer may receive K write completions.
module ot_chip_v41x_kv_reqmux_recovery_enabled #(
    parameter integer HAW = 30,
    parameter integer TAGW = 16,
    parameter bit OPT_RECOVERY = 0,
    parameter integer SELECT_STACK = 2
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
    input  wire [1023:0]       s_data
,
    input wire rec_freeze,
    input wire rec_token,
    input wire rec_commit,
    input wire rec_down_empty,
    input wire rec_down_visible,
    input wire rec_down_token_ack,
    output wire rec_owner_empty,
    output wire rec_visible_empty,
    output wire rec_token_ack
);
    // Direct mux/arbiter: control only, no new request/response holding state.
    assign rec_owner_empty = rec_freeze && rec_down_empty && !w_v[SELECT_STACK] && !w_sv[SELECT_STACK] && !w_wr_done[SELECT_STACK];
    assign rec_visible_empty = rec_down_visible;
    assign rec_token_ack = (rec_owner_empty && rec_visible_empty &&
        rec_down_token_ack == rec_token) ? rec_token : !rec_token;
    initial if (SELECT_STACK != 2 || TAGW != 15 || HAW != 30)
        $fatal(1,"recovery direct-path aperture");

`ifndef SYNTHESIS
    initial if (TAGW < 6) $fatal(1, "KV mux needs a response-owner tag bit");
`endif
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        wire choose_w = w_v[s];
        wire rsp_c = s_tag[s*TAGW + TAGW-1];
        assign m_v[s] = w_v[s] || c_v[s];
        assign w_rdy[s] = choose_w && m_rdy[s];
        assign c_rdy[s] = !choose_w && m_rdy[s];
        assign m_addr[s*HAW +: HAW] = choose_w ? w_addr[s*HAW +: HAW] : c_addr[s*HAW +: HAW];
        assign m_len[s*4 +: 4] = choose_w ? w_len[s*4 +: 4] : c_len[s*4 +: 4];
        assign m_tag[s*TAGW +: TAGW] = choose_w ?
            {1'b0, w_tag[s*TAGW +: TAGW-1]} :
            {1'b1, c_tag[s*TAGW +: TAGW-1]};
        // CKV is published by ingest, then read-only to this DMA.  Fail
        // closed if a future CKV requester accidentally asserts write.
        assign m_we[s] = choose_w ? w_we[s] : 1'b0;
        assign m_wdata[s*256 +: 256] = choose_w ? w_wdata[s*256 +: 256] : '0;
        assign m_wstrb[s*32 +: 32] = choose_w ? w_wstrb[s*32 +: 32] : '0;
        assign w_wr_done[s] = m_wr_done[s];
        assign c_wr_done[s] = 1'b0; // selected CKV is read-only
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
