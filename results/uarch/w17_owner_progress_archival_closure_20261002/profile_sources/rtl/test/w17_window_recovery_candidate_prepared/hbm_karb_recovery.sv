`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// K-port arbiter of one HBM3E stack of the adopted V4.1 layer die: shares the
// stack's 32 pseudo-channel request / response ports (ot_hdc_v41x_idx_hbm
// protocol, ot_chip_v41x_hbm3e_phy K port) between two requesters:
//
//   B  the pooled indexer's key bridge (ot_hdc_v41x_idx_pool_hbm_bridge): a
//      port per pseudo-channel, reads and one-sector masked writes, one write
//      outstanding per stack, completion by wr_done on the written channel;
//   K  the attention KV prefetch (ot_chip_v41x_kv_prefetch): ONE request
//      channel for the stack, steered to pseudo-channel pc_of(addr) (a request
//      must stay inside one pseudo-channel, as the model requires), and one
//      response per cycle.
//
// Per pseudo-channel: when both present a request the grant alternates
// (round robin); a requester's requests keep their order (each has at most
// one request presented per channel, held until accepted).  Tags widen by one
// bit, the requester (1 = K); responses are routed back by that bit, so each
// requester sees its own responses in the channel's order.  wr_done carries no
// tag, so a channel never holds writes of both requesters at once: a write is
// granted only while the other requester has no write outstanding on that
// channel, and wr_done goes to the requester that has.
// ---------------------------------------------------------------------------
module ot_chip_v41x_hbm_karb_recovery #(
    parameter integer NPC  = 32,
    parameter integer AW   = 28,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    // One registered request per pseudo-channel.  Ready acknowledges enqueue;
    // the HBM handshake may occur a cycle later.  Default keeps the reduced
    // die's previously verified combinational timing and cycle counts.
    parameter integer PIPE_OUT = 0,
    parameter integer PIPE_RSP = 0,
    parameter bit OPT_RECOVERY = 0,
    parameter integer SELECT_STACK = 2
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // B: per pseudo-channel
    input  wire [NPC-1:0]       b_v,
    output wire [NPC-1:0]       b_rdy,
    input  wire [NPC*AW-1:0]    b_addr,
    input  wire [NPC*LENW-1:0]  b_len,
    input  wire [NPC*TAGW-1:0]  b_tag,
    input  wire [NPC-1:0]       b_we,
    input  wire [NPC*DW-1:0]    b_wdata,
    input  wire [NPC*DW/8-1:0]  b_wstrb,
    output wire [NPC-1:0]       b_wr_done,
    output wire [NPC-1:0]       b_rsp_v,
    input  wire [NPC-1:0]       b_rsp_rdy,
    output wire [NPC*TAGW-1:0]  b_rsp_tag,
    output wire [NPC*BEATW-1:0] b_rsp_beat,
    output wire [NPC*DW-1:0]    b_rsp_data,
    // K: one channel
    input  wire                 k_v,
    output wire                 k_rdy,
    input  wire [AW-1:0]        k_addr,
    input  wire [LENW-1:0]      k_len,
    input  wire [TAGW-1:0]      k_tag,
    input  wire                 k_we,
    input  wire [DW-1:0]        k_wdata,
    input  wire [DW/8-1:0]      k_wstrb,
    output wire                 k_wr_done,
    output wire                 k_rsp_v,
    input  wire                 k_rsp_rdy,
    output wire [TAGW-1:0]      k_rsp_tag,
    output wire [BEATW-1:0]     k_rsp_beat,
    output wire [DW-1:0]        k_rsp_data,
    // the stack
    output wire [NPC-1:0]       h_v,
    input  wire [NPC-1:0]       h_rdy,
    output wire [NPC*AW-1:0]    h_addr,
    output wire [NPC*LENW-1:0]  h_len,
    output wire [NPC*(TAGW+1)-1:0] h_tag,
    output wire [NPC-1:0]       h_we,
    output wire [NPC*DW-1:0]    h_wdata,
    output wire [NPC*DW/8-1:0]  h_wstrb,
    input  wire [NPC-1:0]       h_wr_done,
    input  wire [NPC-1:0]       r_v,
    output wire [NPC-1:0]       r_rdy,
    input  wire [NPC*(TAGW+1)-1:0] r_tag,
    input  wire [NPC*BEATW-1:0] r_beat,
    input  wire [NPC*DW-1:0]    r_data,
    // status
    output reg  [31:0]          k_grants,
    output reg  [31:0]          b_grants,
    output reg  [31:0]          contended
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
ot_chip_v41x_hbm_karb_recovery_legacy #(
    .NPC(NPC),
    .AW(AW),
    .TAGW(TAGW),
    .LENW(LENW),
    .BEATW(BEATW),
    .DW(DW),
    .PIPE_OUT(PIPE_OUT),
    .PIPE_RSP(PIPE_RSP)
) u_impl (
    .clk(clk),
    .rst_n(rst_n),
    .b_v(b_v),
    .b_rdy(b_rdy),
    .b_addr(b_addr),
    .b_len(b_len),
    .b_tag(b_tag),
    .b_we(b_we),
    .b_wdata(b_wdata),
    .b_wstrb(b_wstrb),
    .b_wr_done(b_wr_done),
    .b_rsp_v(b_rsp_v),
    .b_rsp_rdy(b_rsp_rdy),
    .b_rsp_tag(b_rsp_tag),
    .b_rsp_beat(b_rsp_beat),
    .b_rsp_data(b_rsp_data),
    .k_v(k_v),
    .k_rdy(k_rdy),
    .k_addr(k_addr),
    .k_len(k_len),
    .k_tag(k_tag),
    .k_we(k_we),
    .k_wdata(k_wdata),
    .k_wstrb(k_wstrb),
    .k_wr_done(k_wr_done),
    .k_rsp_v(k_rsp_v),
    .k_rsp_rdy(k_rsp_rdy),
    .k_rsp_tag(k_rsp_tag),
    .k_rsp_beat(k_rsp_beat),
    .k_rsp_data(k_rsp_data),
    .h_v(h_v),
    .h_rdy(h_rdy),
    .h_addr(h_addr),
    .h_len(h_len),
    .h_tag(h_tag),
    .h_we(h_we),
    .h_wdata(h_wdata),
    .h_wstrb(h_wstrb),
    .h_wr_done(h_wr_done),
    .r_v(r_v),
    .r_rdy(r_rdy),
    .r_tag(r_tag),
    .r_beat(r_beat),
    .r_data(r_data),
    .k_grants(k_grants),
    .b_grants(b_grants),
    .contended(contended)
);
assign rec_owner_empty = 1'b0;
assign rec_visible_empty = 1'b0;
assign rec_token_ack = 1'b0;
end else begin : g_recovery
ot_chip_v41x_hbm_karb_recovery_enabled #(
    .NPC(NPC),
    .AW(AW),
    .TAGW(TAGW),
    .LENW(LENW),
    .BEATW(BEATW),
    .DW(DW),
    .PIPE_OUT(PIPE_OUT),
    .PIPE_RSP(PIPE_RSP),
    .OPT_RECOVERY(OPT_RECOVERY),
    .SELECT_STACK(SELECT_STACK)
) u_impl (
    .clk(clk),
    .rst_n(rst_n),
    .b_v(b_v),
    .b_rdy(b_rdy),
    .b_addr(b_addr),
    .b_len(b_len),
    .b_tag(b_tag),
    .b_we(b_we),
    .b_wdata(b_wdata),
    .b_wstrb(b_wstrb),
    .b_wr_done(b_wr_done),
    .b_rsp_v(b_rsp_v),
    .b_rsp_rdy(b_rsp_rdy),
    .b_rsp_tag(b_rsp_tag),
    .b_rsp_beat(b_rsp_beat),
    .b_rsp_data(b_rsp_data),
    .k_v(k_v),
    .k_rdy(k_rdy),
    .k_addr(k_addr),
    .k_len(k_len),
    .k_tag(k_tag),
    .k_we(k_we),
    .k_wdata(k_wdata),
    .k_wstrb(k_wstrb),
    .k_wr_done(k_wr_done),
    .k_rsp_v(k_rsp_v),
    .k_rsp_rdy(k_rsp_rdy),
    .k_rsp_tag(k_rsp_tag),
    .k_rsp_beat(k_rsp_beat),
    .k_rsp_data(k_rsp_data),
    .h_v(h_v),
    .h_rdy(h_rdy),
    .h_addr(h_addr),
    .h_len(h_len),
    .h_tag(h_tag),
    .h_we(h_we),
    .h_wdata(h_wdata),
    .h_wstrb(h_wstrb),
    .h_wr_done(h_wr_done),
    .r_v(r_v),
    .r_rdy(r_rdy),
    .r_tag(r_tag),
    .r_beat(r_beat),
    .r_data(r_data),
    .k_grants(k_grants),
    .b_grants(b_grants),
    .contended(contended),
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
// ---------------------------------------------------------------------------
// K-port arbiter of one HBM3E stack of the adopted V4.1 layer die: shares the
// stack's 32 pseudo-channel request / response ports (ot_hdc_v41x_idx_hbm_recovery_legacy
// protocol, ot_chip_v41x_hbm3e_phy K port) between two requesters:
//
//   B  the pooled indexer's key bridge (ot_hdc_v41x_idx_pool_hbm_bridge): a
//      port per pseudo-channel, reads and one-sector masked writes, one write
//      outstanding per stack, completion by wr_done on the written channel;
//   K  the attention KV prefetch (ot_chip_v41x_kv_prefetch): ONE request
//      channel for the stack, steered to pseudo-channel pc_of(addr) (a request
//      must stay inside one pseudo-channel, as the model requires), and one
//      response per cycle.
//
// Per pseudo-channel: when both present a request the grant alternates
// (round robin); a requester's requests keep their order (each has at most
// one request presented per channel, held until accepted).  Tags widen by one
// bit, the requester (1 = K); responses are routed back by that bit, so each
// requester sees its own responses in the channel's order.  wr_done carries no
// tag, so a channel never holds writes of both requesters at once: a write is
// granted only while the other requester has no write outstanding on that
// channel, and wr_done goes to the requester that has.
// ---------------------------------------------------------------------------
module ot_chip_v41x_hbm_karb_recovery_legacy #(
    parameter integer NPC  = 32,
    parameter integer AW   = 28,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    // One registered request per pseudo-channel.  Ready acknowledges enqueue;
    // the HBM handshake may occur a cycle later.  Default keeps the reduced
    // die's previously verified combinational timing and cycle counts.
    parameter integer PIPE_OUT = 0,
    parameter integer PIPE_RSP = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // B: per pseudo-channel
    input  wire [NPC-1:0]       b_v,
    output wire [NPC-1:0]       b_rdy,
    input  wire [NPC*AW-1:0]    b_addr,
    input  wire [NPC*LENW-1:0]  b_len,
    input  wire [NPC*TAGW-1:0]  b_tag,
    input  wire [NPC-1:0]       b_we,
    input  wire [NPC*DW-1:0]    b_wdata,
    input  wire [NPC*DW/8-1:0]  b_wstrb,
    output wire [NPC-1:0]       b_wr_done,
    output wire [NPC-1:0]       b_rsp_v,
    input  wire [NPC-1:0]       b_rsp_rdy,
    output wire [NPC*TAGW-1:0]  b_rsp_tag,
    output wire [NPC*BEATW-1:0] b_rsp_beat,
    output wire [NPC*DW-1:0]    b_rsp_data,
    // K: one channel
    input  wire                 k_v,
    output wire                 k_rdy,
    input  wire [AW-1:0]        k_addr,
    input  wire [LENW-1:0]      k_len,
    input  wire [TAGW-1:0]      k_tag,
    input  wire                 k_we,
    input  wire [DW-1:0]        k_wdata,
    input  wire [DW/8-1:0]      k_wstrb,
    output wire                 k_wr_done,
    output wire                 k_rsp_v,
    input  wire                 k_rsp_rdy,
    output wire [TAGW-1:0]      k_rsp_tag,
    output wire [BEATW-1:0]     k_rsp_beat,
    output wire [DW-1:0]        k_rsp_data,
    // the stack
    output wire [NPC-1:0]       h_v,
    input  wire [NPC-1:0]       h_rdy,
    output wire [NPC*AW-1:0]    h_addr,
    output wire [NPC*LENW-1:0]  h_len,
    output wire [NPC*(TAGW+1)-1:0] h_tag,
    output wire [NPC-1:0]       h_we,
    output wire [NPC*DW-1:0]    h_wdata,
    output wire [NPC*DW/8-1:0]  h_wstrb,
    input  wire [NPC-1:0]       h_wr_done,
    input  wire [NPC-1:0]       r_v,
    output wire [NPC-1:0]       r_rdy,
    input  wire [NPC*(TAGW+1)-1:0] r_tag,
    input  wire [NPC*BEATW-1:0] r_beat,
    input  wire [NPC*DW-1:0]    r_data,
    // status
    output reg  [31:0]          k_grants,
    output reg  [31:0]          b_grants,
    output reg  [31:0]          contended
);
    localparam integer LPC = (NPC > 1) ? $clog2(NPC) : 1;
    // the model's address -> pseudo-channel map (ot_hdc_v41x_idx_hbm_recovery_legacy pc_of)
    function automatic [LPC-1:0] pc_of(input [AW-1:0] s);
        pc_of = (NPC > 1) ? LPC'(((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1)) : '0;
    endfunction
    wire [LPC-1:0] kpc = pc_of(k_addr);
    reg  [NPC-1:0] rr;                              // 1: K has priority on the next contention
    reg  [7:0]     bw_out [0:NPC-1], kw_out [0:NPC-1];
    wire [NPC-1:0] gk, gb, room;
    // K response select: lowest channel holding a K response
    reg  [LPC-1:0] ksel; reg kany;
    integer i;
    always @(*) begin
        ksel = '0; kany = 1'b0;
        for (i = NPC - 1; i >= 0; i = i - 1)
            if (r_v[i] && r_tag[i*(TAGW+1) + TAGW]) begin ksel = LPC'(i); kany = 1'b1; end
    end
    genvar p;
    generate for (p = 0; p < NPC; p = p + 1) begin : g_pc
        wire kv = k_v && (kpc == p);
        wire k_ok = kv && !(k_we && bw_out[p] != 0);
        wire b_ok = b_v[p] && !(b_we[p] && kw_out[p] != 0);
        assign gk[p] = k_ok && (!b_ok || rr[p]);
        assign gb[p] = b_ok && !gk[p];
        wire [AW-1:0] req_addr = gk[p] ? k_addr : b_addr[p*AW +: AW];
        wire [LENW-1:0] req_len = gk[p] ? k_len : b_len[p*LENW +: LENW];
        wire [TAGW:0] req_tag = gk[p] ? {1'b1, k_tag} : {1'b0, b_tag[p*TAGW +: TAGW]};
        wire req_we = gk[p] ? k_we : b_we[p];
        wire [DW-1:0] req_wdata = gk[p] ? k_wdata : b_wdata[p*DW +: DW];
        wire [DW/8-1:0] req_wstrb = gk[p] ? k_wstrb : b_wstrb[p*DW/8 +: DW/8];
        if (PIPE_OUT != 0) begin : g_pipe
            reg v_q, we_q;
            reg [AW-1:0] addr_q;
            reg [LENW-1:0] len_q;
            reg [TAGW:0] tag_q;
            reg [DW-1:0] wdata_q;
            reg [DW/8-1:0] wstrb_q;
            assign room[p] = !v_q || h_rdy[p];
            assign h_v[p] = v_q;
            assign h_addr[p*AW +: AW] = addr_q;
            assign h_len[p*LENW +: LENW] = len_q;
            assign h_tag[p*(TAGW+1) +: TAGW+1] = tag_q;
            assign h_we[p] = we_q;
            assign h_wdata[p*DW +: DW] = wdata_q;
            assign h_wstrb[p*DW/8 +: DW/8] = wstrb_q;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    v_q <= 1'b0;
                    addr_q <= '0; len_q <= '0; tag_q <= '0;
                    we_q <= 1'b0; wdata_q <= '0; wstrb_q <= '0;
                end else if (room[p]) begin
                    v_q <= gk[p] || gb[p];
                    if (gk[p] || gb[p]) begin
                        addr_q <= req_addr; len_q <= req_len; tag_q <= req_tag;
                        we_q <= req_we; wdata_q <= req_wdata; wstrb_q <= req_wstrb;
                    end
                end
        end else begin : g_direct
            assign room[p] = h_rdy[p];
            assign h_v[p] = gk[p] || gb[p];
            assign h_addr[p*AW +: AW] = req_addr;
            assign h_len[p*LENW +: LENW] = req_len;
            assign h_tag[p*(TAGW+1) +: TAGW+1] = req_tag;
            assign h_we[p] = req_we;
            assign h_wdata[p*DW +: DW] = req_wdata;
            assign h_wstrb[p*DW/8 +: DW/8] = req_wstrb;
        end
        assign b_rdy[p] = room[p] && gb[p];
        assign b_wr_done[p] = h_wr_done[p] && bw_out[p] != 0;
        // responses
        wire mine_k = r_tag[p*(TAGW+1) + TAGW];
        assign b_rsp_v[p] = r_v[p] && !mine_k;
        assign b_rsp_tag[p*TAGW +: TAGW] = r_tag[p*(TAGW+1) +: TAGW];
        assign b_rsp_beat[p*BEATW +: BEATW] = r_beat[p*BEATW +: BEATW];
        assign b_rsp_data[p*DW +: DW] = r_data[p*DW +: DW];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                rr[p] <= 1'b0; bw_out[p] <= 8'd0; kw_out[p] <= 8'd0;
            end else begin
                if (k_ok && b_ok && room[p]) rr[p] <= !gk[p];
                bw_out[p] <= bw_out[p] + {7'd0, gb[p] && room[p] && b_we[p]}
                             - {7'd0, h_wr_done[p] && bw_out[p] != 0};
                kw_out[p] <= kw_out[p] + {7'd0, gk[p] && room[p] && k_we}
                             - {7'd0, h_wr_done[p] && bw_out[p] == 0 && kw_out[p] != 0};
            end
    end endgenerate
    assign k_rdy = room[kpc] && gk[kpc];
    reg [NPC-1:0] kwd;
    always @(*) for (i = 0; i < NPC; i = i + 1) kwd[i] = h_wr_done[i] && bw_out[i] == 0 && kw_out[i] != 0;
    assign k_wr_done = |kwd;
    generate if (PIPE_RSP != 0) begin : g_rsp_pipe
        ot_chip_v41x_hbm_rsp_pipe #(.NPC(NPC), .TAGW(TAGW), .BEATW(BEATW), .DW(DW)) u_rsp (
            .clk(clk), .rst_n(rst_n), .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag),
            .r_beat(r_beat), .r_data(r_data), .b_rsp_rdy(b_rsp_rdy),
            .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_tag(k_rsp_tag),
            .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data));
    end else begin : g_rsp_direct
        for (genvar q = 0; q < NPC; q = q + 1) begin : g_pc
            wire mine_k = r_tag[q*(TAGW+1) + TAGW];
            assign r_rdy[q] = mine_k ? (kany && ksel == q && k_rsp_rdy) : b_rsp_rdy[q];
        end
        assign k_rsp_v = kany;
        assign k_rsp_tag = r_tag[ksel*(TAGW+1) +: TAGW];
        assign k_rsp_beat = r_beat[ksel*BEATW +: BEATW];
        assign k_rsp_data = r_data[ksel*DW +: DW];
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin k_grants <= 0; b_grants <= 0; contended <= 0; end
        else begin
            if (k_v && k_rdy) k_grants <= k_grants + 1;
            b_grants <= b_grants + 32'($countones(gb & room));
            contended <= contended + {31'd0, k_v && b_v[kpc]};
        end
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// K-port arbiter of one HBM3E stack of the adopted V4.1 layer die: shares the
// stack's 32 pseudo-channel request / response ports (ot_hdc_v41x_idx_hbm_recovery_legacy
// protocol, ot_chip_v41x_hbm3e_phy K port) between two requesters:
//
//   B  the pooled indexer's key bridge (ot_hdc_v41x_idx_pool_hbm_bridge): a
//      port per pseudo-channel, reads and one-sector masked writes, one write
//      outstanding per stack, completion by wr_done on the written channel;
//   K  the attention KV prefetch (ot_chip_v41x_kv_prefetch): ONE request
//      channel for the stack, steered to pseudo-channel pc_of(addr) (a request
//      must stay inside one pseudo-channel, as the model requires), and one
//      response per cycle.
//
// Per pseudo-channel: when both present a request the grant alternates
// (round robin); a requester's requests keep their order (each has at most
// one request presented per channel, held until accepted).  Tags widen by one
// bit, the requester (1 = K); responses are routed back by that bit, so each
// requester sees its own responses in the channel's order.  wr_done carries no
// tag, so a channel never holds writes of both requesters at once: a write is
// granted only while the other requester has no write outstanding on that
// channel, and wr_done goes to the requester that has.
// ---------------------------------------------------------------------------
module ot_chip_v41x_hbm_karb_recovery_enabled #(
    parameter integer NPC  = 32,
    parameter integer AW   = 28,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    // One registered request per pseudo-channel.  Ready acknowledges enqueue;
    // the HBM handshake may occur a cycle later.  Default keeps the reduced
    // die's previously verified combinational timing and cycle counts.
    parameter integer PIPE_OUT = 0,
    parameter integer PIPE_RSP = 0,
    parameter bit OPT_RECOVERY = 0,
    parameter integer SELECT_STACK = 2
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // B: per pseudo-channel
    input  wire [NPC-1:0]       b_v,
    output wire [NPC-1:0]       b_rdy,
    input  wire [NPC*AW-1:0]    b_addr,
    input  wire [NPC*LENW-1:0]  b_len,
    input  wire [NPC*TAGW-1:0]  b_tag,
    input  wire [NPC-1:0]       b_we,
    input  wire [NPC*DW-1:0]    b_wdata,
    input  wire [NPC*DW/8-1:0]  b_wstrb,
    output wire [NPC-1:0]       b_wr_done,
    output wire [NPC-1:0]       b_rsp_v,
    input  wire [NPC-1:0]       b_rsp_rdy,
    output wire [NPC*TAGW-1:0]  b_rsp_tag,
    output wire [NPC*BEATW-1:0] b_rsp_beat,
    output wire [NPC*DW-1:0]    b_rsp_data,
    // K: one channel
    input  wire                 k_v,
    output wire                 k_rdy,
    input  wire [AW-1:0]        k_addr,
    input  wire [LENW-1:0]      k_len,
    input  wire [TAGW-1:0]      k_tag,
    input  wire                 k_we,
    input  wire [DW-1:0]        k_wdata,
    input  wire [DW/8-1:0]      k_wstrb,
    output wire                 k_wr_done,
    output wire                 k_rsp_v,
    input  wire                 k_rsp_rdy,
    output wire [TAGW-1:0]      k_rsp_tag,
    output wire [BEATW-1:0]     k_rsp_beat,
    output wire [DW-1:0]        k_rsp_data,
    // the stack
    output wire [NPC-1:0]       h_v,
    input  wire [NPC-1:0]       h_rdy,
    output wire [NPC*AW-1:0]    h_addr,
    output wire [NPC*LENW-1:0]  h_len,
    output wire [NPC*(TAGW+1)-1:0] h_tag,
    output wire [NPC-1:0]       h_we,
    output wire [NPC*DW-1:0]    h_wdata,
    output wire [NPC*DW/8-1:0]  h_wstrb,
    input  wire [NPC-1:0]       h_wr_done,
    input  wire [NPC-1:0]       r_v,
    output wire [NPC-1:0]       r_rdy,
    input  wire [NPC*(TAGW+1)-1:0] r_tag,
    input  wire [NPC*BEATW-1:0] r_beat,
    input  wire [NPC*DW-1:0]    r_data,
    // status
    output reg  [31:0]          k_grants,
    output reg  [31:0]          b_grants,
    output reg  [31:0]          contended
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
    assign rec_owner_empty = rec_freeze && rec_down_empty && !(k_v && k_tag[TAGW-1 -: 2] == 0) && !k_wr_done && !(k_rsp_v && k_rsp_tag[TAGW-1 -: 2] == 0);
    assign rec_visible_empty = rec_down_visible;
    assign rec_token_ack = (rec_owner_empty && rec_visible_empty &&
        rec_down_token_ack == rec_token) ? rec_token : !rec_token;
    initial if (SELECT_STACK != 2 || NPC != 32 || TAGW != 16 || AW != 30 || LENW != 4 || BEATW != 4 || DW != 256 || PIPE_OUT || PIPE_RSP)
        $fatal(1,"recovery direct-path aperture");

    localparam integer LPC = (NPC > 1) ? $clog2(NPC) : 1;
    // the model's address -> pseudo-channel map (ot_hdc_v41x_idx_hbm_recovery_legacy pc_of)
    function automatic [LPC-1:0] pc_of(input [AW-1:0] s);
        pc_of = (NPC > 1) ? LPC'(((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1)) : '0;
    endfunction
    wire [LPC-1:0] kpc = pc_of(k_addr);
    reg  [NPC-1:0] rr;                              // 1: K has priority on the next contention
    reg  [7:0]     bw_out [0:NPC-1], kw_out [0:NPC-1];
    wire [NPC-1:0] gk, gb, room;
    // K response select: lowest channel holding a K response
    reg  [LPC-1:0] ksel; reg kany;
    integer i;
    always @(*) begin
        ksel = '0; kany = 1'b0;
        for (i = NPC - 1; i >= 0; i = i - 1)
            if (r_v[i] && r_tag[i*(TAGW+1) + TAGW]) begin ksel = LPC'(i); kany = 1'b1; end
    end
    genvar p;
    generate for (p = 0; p < NPC; p = p + 1) begin : g_pc
        wire kv = k_v && (kpc == p);
        wire k_ok = kv && !(k_we && bw_out[p] != 0);
        wire b_ok = b_v[p] && !(b_we[p] && kw_out[p] != 0);
        assign gk[p] = k_ok && (!b_ok || rr[p]);
        assign gb[p] = b_ok && !gk[p];
        wire [AW-1:0] req_addr = gk[p] ? k_addr : b_addr[p*AW +: AW];
        wire [LENW-1:0] req_len = gk[p] ? k_len : b_len[p*LENW +: LENW];
        wire [TAGW:0] req_tag = gk[p] ? {1'b1, k_tag} : {1'b0, b_tag[p*TAGW +: TAGW]};
        wire req_we = gk[p] ? k_we : b_we[p];
        wire [DW-1:0] req_wdata = gk[p] ? k_wdata : b_wdata[p*DW +: DW];
        wire [DW/8-1:0] req_wstrb = gk[p] ? k_wstrb : b_wstrb[p*DW/8 +: DW/8];
        if (PIPE_OUT != 0) begin : g_pipe
            reg v_q, we_q;
            reg [AW-1:0] addr_q;
            reg [LENW-1:0] len_q;
            reg [TAGW:0] tag_q;
            reg [DW-1:0] wdata_q;
            reg [DW/8-1:0] wstrb_q;
            assign room[p] = !v_q || h_rdy[p];
            assign h_v[p] = v_q;
            assign h_addr[p*AW +: AW] = addr_q;
            assign h_len[p*LENW +: LENW] = len_q;
            assign h_tag[p*(TAGW+1) +: TAGW+1] = tag_q;
            assign h_we[p] = we_q;
            assign h_wdata[p*DW +: DW] = wdata_q;
            assign h_wstrb[p*DW/8 +: DW/8] = wstrb_q;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    v_q <= 1'b0;
                    addr_q <= '0; len_q <= '0; tag_q <= '0;
                    we_q <= 1'b0; wdata_q <= '0; wstrb_q <= '0;
                end else if (room[p]) begin
                    v_q <= gk[p] || gb[p];
                    if (gk[p] || gb[p]) begin
                        addr_q <= req_addr; len_q <= req_len; tag_q <= req_tag;
                        we_q <= req_we; wdata_q <= req_wdata; wstrb_q <= req_wstrb;
                    end
                end
        end else begin : g_direct
            assign room[p] = h_rdy[p];
            assign h_v[p] = gk[p] || gb[p];
            assign h_addr[p*AW +: AW] = req_addr;
            assign h_len[p*LENW +: LENW] = req_len;
            assign h_tag[p*(TAGW+1) +: TAGW+1] = req_tag;
            assign h_we[p] = req_we;
            assign h_wdata[p*DW +: DW] = req_wdata;
            assign h_wstrb[p*DW/8 +: DW/8] = req_wstrb;
        end
        assign b_rdy[p] = room[p] && gb[p];
        assign b_wr_done[p] = h_wr_done[p] && bw_out[p] != 0;
        // responses
        wire mine_k = r_tag[p*(TAGW+1) + TAGW];
        assign b_rsp_v[p] = r_v[p] && !mine_k;
        assign b_rsp_tag[p*TAGW +: TAGW] = r_tag[p*(TAGW+1) +: TAGW];
        assign b_rsp_beat[p*BEATW +: BEATW] = r_beat[p*BEATW +: BEATW];
        assign b_rsp_data[p*DW +: DW] = r_data[p*DW +: DW];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                rr[p] <= 1'b0; bw_out[p] <= 8'd0; kw_out[p] <= 8'd0;
            end else begin
                if (k_ok && b_ok && room[p]) rr[p] <= !gk[p];
                bw_out[p] <= bw_out[p] + {7'd0, gb[p] && room[p] && b_we[p]}
                             - {7'd0, h_wr_done[p] && bw_out[p] != 0};
                kw_out[p] <= kw_out[p] + {7'd0, gk[p] && room[p] && k_we}
                             - {7'd0, h_wr_done[p] && bw_out[p] == 0 && kw_out[p] != 0};
            end
    end endgenerate
    assign k_rdy = room[kpc] && gk[kpc];
    reg [NPC-1:0] kwd;
    always @(*) for (i = 0; i < NPC; i = i + 1) kwd[i] = h_wr_done[i] && bw_out[i] == 0 && kw_out[i] != 0;
    assign k_wr_done = |kwd;
    generate if (PIPE_RSP != 0) begin : g_rsp_pipe
        ot_chip_v41x_hbm_rsp_pipe #(.NPC(NPC), .TAGW(TAGW), .BEATW(BEATW), .DW(DW)) u_rsp (
            .clk(clk), .rst_n(rst_n), .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag),
            .r_beat(r_beat), .r_data(r_data), .b_rsp_rdy(b_rsp_rdy),
            .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_tag(k_rsp_tag),
            .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data));
    end else begin : g_rsp_direct
        for (genvar q = 0; q < NPC; q = q + 1) begin : g_pc
            wire mine_k = r_tag[q*(TAGW+1) + TAGW];
            assign r_rdy[q] = mine_k ? (kany && ksel == q && k_rsp_rdy) : b_rsp_rdy[q];
        end
        assign k_rsp_v = kany;
        assign k_rsp_tag = r_tag[ksel*(TAGW+1) +: TAGW];
        assign k_rsp_beat = r_beat[ksel*BEATW +: BEATW];
        assign k_rsp_data = r_data[ksel*DW +: DW];
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin k_grants <= 0; b_grants <= 0; contended <= 0; end
        else begin
            if (k_v && k_rdy) k_grants <= k_grants + 1;
            b_grants <= b_grants + 32'($countones(gb & room));
            contended <= contended + {31'd0, k_v && b_v[kpc]};
        end
endmodule
