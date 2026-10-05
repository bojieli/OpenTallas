`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_hbm_wmux: per-stack WIDE read port for the S81 layer die (claude/dsrom-s81-window-bind-20261004).
// Default-off (ENABLE=0 is wires: the stack side is the karb side, every W output is zero).
//
// The as-built S81 die reaches each HBM3E stack through ot_chip_v41x_hbm_karb: the pooled indexer's
// per-pseudo-channel bridge (B, tag bit 16 = 0) and ONE K request channel a stack (bit 16 = 1; its owner bits
// [15:14] are 00 WINDOW / 01 CKV / 10 RoPE, ot_chip_v41x_kv_rope_reqmux_c8 refuses 11).  A single K channel
// issues at most one sector a cycle, so the packed WINDOW refill and the re-index candidate read cannot reach
// the stack's bandwidth through it (results/rtl/hbm_path_bandwidth_audit_20261004).
//
// This mux sits between the karb's stack side (a_*) and the stack (h_* / r_*) and adds NW read-only clients,
// each a request / response port per pseudo-channel (the ot_hdc_v41x_idx_hbm protocol):
//   client 0  ot_dsrom_window_stream_la (the WINDOW load, through ot_dsrom_window_attn_source_la);
//   client 1  ot_hdc_v41x_idx_kgather (the re-index layers' candidate-block read).
// Tag namespace on the stack: {1'b1, 2'b11, client (CW bits), client tag (WTAGW bits)} -- the K side's
// reserved owner code 11, so a W response can never be mistaken for a karb response (and a karb request
// carrying that code is a fault, never forwarded).  W requests are reads (h_we = 0).
// Per pseudo-channel and client, a one-entry request register: a W client's ready is that register being empty
// (or draining), so the client's issue never depends combinationally on the stack's ready (the stack's ready
// depends on the presented request's length: a loop otherwise), and a held W request is presented with fixed
// priority, client 0 > client 1 > ... > the karb.  A held request therefore takes the channel's next free
// queue slot, so a W stream cannot be starved by a saturating karb stream; W streams are bounded (69,632 B for
// the window, <= 9,197 sectors for the candidate read), so the karb is delayed, not starved.  One cycle of
// request latency.  Responses: W namespace -> that client's port (its rsp_rdy is honoured), else -> the karb.
// wr_done is the karb's (W never writes).
// ---------------------------------------------------------------------------
module ot_dsrom_hbm_wmux #(
    parameter integer ENABLE = 0,
    parameter integer NPC    = 32,
    parameter integer AW     = 30,
    parameter integer TAGW   = 17,     // stack tag (karb TAGW + 1)
    parameter integer LENW   = 4,
    parameter integer BEATW  = 4,
    parameter integer DW     = 256,
    parameter integer NW     = 2,
    parameter integer CW     = 1,      // client index bits (2^CW >= NW)
    parameter integer WTAGW  = 13      // client tag bits; TAGW - 3 - CW
) (
    input  wire                     clk,
    input  wire                     rst_n,
    // karb stack side
    input  wire [NPC-1:0]           a_v,
    output wire [NPC-1:0]           a_rdy,
    input  wire [NPC*AW-1:0]        a_addr,
    input  wire [NPC*LENW-1:0]      a_len,
    input  wire [NPC*TAGW-1:0]      a_tag,
    input  wire [NPC-1:0]           a_we,
    input  wire [NPC*DW-1:0]        a_wdata,
    input  wire [NPC*DW/8-1:0]      a_wstrb,
    output wire [NPC-1:0]           a_wr_done,
    output wire [NPC-1:0]           a_rsp_v,
    input  wire [NPC-1:0]           a_rsp_rdy,
    output wire [NPC*TAGW-1:0]      a_rsp_tag,
    output wire [NPC*BEATW-1:0]     a_rsp_beat,
    output wire [NPC*DW-1:0]        a_rsp_data,
    // W clients (client c, pseudo-channel p at index c*NPC + p)
    input  wire [NW*NPC-1:0]        w_v,
    output wire [NW*NPC-1:0]        w_rdy,
    input  wire [NW*NPC*AW-1:0]     w_addr,
    input  wire [NW*NPC*LENW-1:0]   w_len,
    input  wire [NW*NPC*WTAGW-1:0]  w_tag,
    output wire [NW*NPC-1:0]        w_rsp_v,
    input  wire [NW*NPC-1:0]        w_rsp_rdy,
    output wire [NW*NPC*WTAGW-1:0]  w_rsp_tag,
    output wire [NW*NPC*BEATW-1:0]  w_rsp_beat,
    output wire [NW*NPC*DW-1:0]     w_rsp_data,
    // the stack
    output wire [NPC-1:0]           h_v,
    input  wire [NPC-1:0]           h_rdy,
    output wire [NPC*AW-1:0]        h_addr,
    output wire [NPC*LENW-1:0]      h_len,
    output wire [NPC*TAGW-1:0]      h_tag,
    output wire [NPC-1:0]           h_we,
    output wire [NPC*DW-1:0]        h_wdata,
    output wire [NPC*DW/8-1:0]      h_wstrb,
    input  wire [NPC-1:0]           h_wr_done,
    input  wire [NPC-1:0]           r_v,
    output wire [NPC-1:0]           r_rdy,
    input  wire [NPC*TAGW-1:0]      r_tag,
    input  wire [NPC*BEATW-1:0]     r_beat,
    input  wire [NPC*DW-1:0]        r_data,
    // status
    output reg                      fault,        // karb request in the W namespace (sticky)
    output reg  [31:0]              w_grants,     // W requests accepted by the stack
    output reg  [31:0]              a_held        // karb request cycles held by a W request
);
    assign a_wr_done = h_wr_done;
    generate if (!ENABLE) begin : g_off
        assign h_v = a_v; assign a_rdy = h_rdy; assign h_addr = a_addr; assign h_len = a_len;
        assign h_tag = a_tag; assign h_we = a_we; assign h_wdata = a_wdata; assign h_wstrb = a_wstrb;
        assign a_rsp_v = r_v; assign r_rdy = a_rsp_rdy; assign a_rsp_tag = r_tag; assign a_rsp_beat = r_beat;
        assign a_rsp_data = r_data;
        assign w_rdy = '0; assign w_rsp_v = '0; assign w_rsp_tag = '0; assign w_rsp_beat = '0;
        assign w_rsp_data = '0;
        always @(posedge clk) begin fault <= 1'b0; w_grants <= 0; a_held <= 0; end
    end else begin : g_on
        initial if (TAGW != 3 + CW + WTAGW || (1 << CW) < NW || NW < 1)
            $fatal(1, "ot_dsrom_hbm_wmux tag namespace geometry");
        localparam [2:0] NS = 3'b111;
        reg [NPC-1:0] a_bad;
        wire [NPC-1:0] g_take;
        for (genvar p = 0; p < NPC; p = p + 1) begin : g_pc
            // held W requests (one per client), presented with fixed priority, client 0 first
            reg [NW-1:0] hv;
            reg [AW-1:0] ha [0:NW-1]; reg [LENW-1:0] hl [0:NW-1]; reg [WTAGW-1:0] ht [0:NW-1];
            reg [NW-1:0] win;          // one-hot: the held request presented this cycle
            reg any_w;
            always @* begin
                win = '0; any_w = 1'b0;
                for (integer c = 0; c < NW; c = c + 1)
                    if (hv[c] && !any_w) begin win[c] = 1'b1; any_w = 1'b1; end
            end
            wire take = any_w && h_rdy[p];            // the presented held request is accepted by the stack
            for (genvar c = 0; c < NW; c = c + 1) begin : g_wr
                assign w_rdy[c*NPC + p] = !hv[c] || (take && win[c]);
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) hv[c] <= 1'b0;
                    else if (w_v[c*NPC + p] && w_rdy[c*NPC + p]) begin
                        hv[c] <= 1'b1;
                        ha[c] <= w_addr[(c*NPC + p)*AW +: AW]; hl[c] <= w_len[(c*NPC + p)*LENW +: LENW];
                        ht[c] <= w_tag[(c*NPC + p)*WTAGW +: WTAGW];
                    end else if (take && win[c]) hv[c] <= 1'b0;
            end
            wire a_ns = a_tag[p*TAGW + TAGW-1 -: 3] == NS;
            always @* a_bad[p] = a_v[p] && a_ns;
            assign a_rdy[p] = h_rdy[p] && !any_w && !a_ns;
            reg [AW-1:0] wa; reg [LENW-1:0] wl; reg [TAGW-1:0] wt;
            always @* begin
                wa = '0; wl = '0; wt = '0;
                for (integer c = 0; c < NW; c = c + 1) if (win[c]) begin
                    wa = ha[c]; wl = hl[c]; wt = {NS, CW'(c), ht[c]};
                end
            end
            assign h_v[p] = any_w || (a_v[p] && !a_ns);
            assign h_addr[p*AW +: AW] = any_w ? wa : a_addr[p*AW +: AW];
            assign h_len[p*LENW +: LENW] = any_w ? wl : a_len[p*LENW +: LENW];
            assign h_tag[p*TAGW +: TAGW] = any_w ? wt : a_tag[p*TAGW +: TAGW];
            assign h_we[p] = any_w ? 1'b0 : a_we[p];
            assign h_wdata[p*DW +: DW] = any_w ? '0 : a_wdata[p*DW +: DW];
            assign h_wstrb[p*DW/8 +: DW/8] = any_w ? '0 : a_wstrb[p*DW/8 +: DW/8];
            assign g_take[p] = take;
            // response
            wire r_ns = r_tag[p*TAGW + TAGW-1 -: 3] == NS;
            wire [CW-1:0] r_c = r_tag[p*TAGW + WTAGW +: CW];
            reg rr;
            always @* begin
                rr = a_rsp_rdy[p];
                if (r_ns) begin
                    rr = 1'b0;
                    for (integer c = 0; c < NW; c = c + 1) if (r_c == CW'(c)) rr = w_rsp_rdy[c*NPC + p];
                end
            end
            assign r_rdy[p] = rr;
            assign a_rsp_v[p] = r_v[p] && !r_ns;
            assign a_rsp_tag[p*TAGW +: TAGW] = r_tag[p*TAGW +: TAGW];
            assign a_rsp_beat[p*BEATW +: BEATW] = r_beat[p*BEATW +: BEATW];
            assign a_rsp_data[p*DW +: DW] = r_data[p*DW +: DW];
            for (genvar c = 0; c < NW; c = c + 1) begin : g_wrsp
                assign w_rsp_v[c*NPC + p] = r_v[p] && r_ns && r_c == CW'(c);
                assign w_rsp_tag[(c*NPC + p)*WTAGW +: WTAGW] = r_tag[p*TAGW +: WTAGW];
                assign w_rsp_beat[(c*NPC + p)*BEATW +: BEATW] = r_beat[p*BEATW +: BEATW];
                assign w_rsp_data[(c*NPC + p)*DW +: DW] = r_data[p*DW +: DW];
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) fault <= 1'b0;
            else if (|a_bad) fault <= 1'b1;
        // status counters: simulation statistics only (not silicon)
`ifndef SYNTHESIS
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin w_grants <= 0; a_held <= 0; end
            else begin
                w_grants <= w_grants + 32'($countones(g_take));
                a_held <= a_held + 32'($countones(a_v & ~a_rdy & h_rdy));
            end
`else
        always @(posedge clk) begin w_grants <= 0; a_held <= 0; end
`endif
    end endgenerate
endmodule
