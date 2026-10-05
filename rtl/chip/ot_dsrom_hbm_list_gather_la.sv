`timescale 1ns/1ps
// DS ROM HBM list gather at full stack bandwidth (HBM path audit 2026-10-04): the re-index layers'
// candidate-key read.  Default-off (ENABLE=0 ties every output to zero); nothing pinned instantiates it.
//
// The as-built re-index layers (L24/L28/L32/L36) stream ALL 1,048,576 index keys (262,144 a rank, 557,056
// sectors a rank, measured 92% of the four stacks' peak) and mask the scores to the 16,384 candidates.  The
// candidates come in aligned 8-key groups (2,048 groups at the 1M token), so a rank needs only its ~512
// groups: per group the 8 keys' codes (16 sectors = four 128-B columns of one 4-KB code block, the key
// layout of ot_hdc_v41x_idx_kstream_range) and their 32 B of UE8M0 scales (one sector of the superblock's
// scale block): 17 sectors in 5 requests.  This element reads a request list (address, length 1..4, all
// sectors of a request on one pseudo-channel) of one stack:
//   * in list order, up to IW requests a cycle, each on a different pseudo-channel whose port is ready
//     (issue stops at the first request that cannot go this cycle, so the list order is the issue order);
//   * every pseudo-channel port of the stack in parallel, tag = list index, the whole list in flight up to
//     the controller queues;
//   * responses land by (tag, beat) into a sector buffer (on silicon one 1W1R bank per pseudo-channel, as
//     the W11 reader's ROB); `done` when every requested sector has landed exactly once.
// The landed sectors are the bytes the masked full scan would have scored for the candidate keys; the bench
// checks every one against the HBM backing pattern.
module ot_dsrom_hbm_list_gather_la #(
    parameter integer ENABLE = 0,
    parameter integer NPC    = 32,
    parameter integer AW     = 24,
    parameter integer TAGW   = 16,
    parameter integer LENW   = 5,
    parameter integer BEATW  = 4,
    parameter integer NMAX   = 1024,        // list entries
    parameter integer SMAX   = 4096,        // landed sectors
    parameter integer IW     = 8
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // list load (one entry a cycle) then start
    input  wire                  ld_v,
    input  wire [$clog2(NMAX)-1:0] ld_idx,
    input  wire [AW-1:0]         ld_addr,
    input  wire [2:0]            ld_len,
    input  wire [$clog2(SMAX)-1:0] ld_off,   // landing offset of the entry's first sector
    input  wire                  start,
    input  wire [$clog2(NMAX):0] n_req,
    input  wire [$clog2(SMAX):0] n_sect,
    output wire                  busy,
    output wire                  done,
    output reg                   fault,
    output wire [NPC-1:0]        req_v,
    input  wire [NPC-1:0]        req_rdy,
    output wire [NPC*AW-1:0]     req_addr,
    output wire [NPC*LENW-1:0]   req_len,
    output wire [NPC*TAGW-1:0]   req_tag,
    output wire [NPC-1:0]        req_we,
    output wire [NPC*256-1:0]    req_wdata,
    output wire [NPC*32-1:0]     req_wstrb,
    input  wire [NPC-1:0]        rsp_v,
    output wire [NPC-1:0]        rsp_rdy,
    input  wire [NPC*TAGW-1:0]   rsp_tag,
    input  wire [NPC*BEATW-1:0]  rsp_beat,
    input  wire [NPC*256-1:0]    rsp_data,
    input  wire [$clog2(SMAX)-1:0] rd_sect,
    output wire [255:0]          rd_data
);
    localparam integer LPC = $clog2(NPC);
    localparam integer NW = $clog2(NMAX), SW = $clog2(SMAX);
    assign req_we = '0; assign req_wdata = '0; assign req_wstrb = '0;
    generate if (!ENABLE) begin : g_off
        assign busy = 0; assign done = 0; assign req_v = 0; assign req_addr = 0; assign req_len = 0;
        assign req_tag = 0; assign rsp_rdy = 0; assign rd_data = 0;
        always @(posedge clk) fault <= 1'b0;
    end else begin : g_on
        function automatic integer pc_of(input [AW-1:0] s);
            pc_of = (((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1));
        endfunction
        reg [AW-1:0] l_addr [0:NMAX-1]; reg [2:0] l_len [0:NMAX-1]; reg [SW-1:0] l_off [0:NMAX-1];
        reg [255:0] buf_q [0:SMAX-1]; reg [SMAX-1:0] got;
        reg [NW:0] nxt, nreq; reg [SW:0] nsec, landed; reg run, fin;
        reg [NPC-1:0] v_c; reg [NPC*AW-1:0] a_c; reg [NPC*TAGW-1:0] t_c; reg [NPC*LENW-1:0] l_c; reg [NW:0] adv;
        // candidates: the longest PC-distinct prefix of the next IW entries (independent of ready, so the
        // request fields never depend on the controller's ready); issued: that prefix up to the first
        // entry whose PC is not ready
        always @* begin
            automatic reg stop = 0, gate = 0;
            automatic reg [NPC-1:0] used = 0;
            v_c = 0; a_c = 0; t_c = 0; l_c = 0; adv = 0;
            for (integer i = 0; i < IW; i = i + 1) begin
                automatic integer e = int'(nxt) + i;
                if (!stop && run && e < int'(nreq)) begin
                    automatic integer p = pc_of(l_addr[e]);
                    if (used[p]) stop = 1;
                    else begin
                        used[p] = 1'b1; a_c[p*AW +: AW] = l_addr[e]; t_c[p*TAGW +: TAGW] = TAGW'(e);
                        l_c[p*LENW +: LENW] = LENW'(l_len[e]);
                        if (!req_rdy[p]) gate = 1;
                        if (!gate) begin v_c[p] = 1'b1; adv = adv + 1'b1; end
                    end
                end
            end
        end
        assign req_v = v_c; assign req_addr = a_c; assign req_tag = t_c; assign req_len = l_c;
        assign rsp_rdy = {NPC{1'b1}};
        assign busy = run; assign done = fin; assign rd_data = buf_q[rd_sect];
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                run <= 0; fin <= 0; nxt <= 0; nreq <= 0; nsec <= 0; landed <= 0; got <= 0; fault <= 0;
            end else begin
                if (ld_v && !run) begin l_addr[ld_idx] <= ld_addr; l_len[ld_idx] <= ld_len; l_off[ld_idx] <= ld_off; end
                if (start && !run) begin
                    run <= 1; fin <= 0; nxt <= 0; nreq <= n_req; nsec <= n_sect; landed <= 0; got <= 0;
                end else if (run) begin
                    automatic reg [SW:0] nl = landed;
                    nxt <= nxt + adv;
                    for (integer p = 0; p < NPC; p = p + 1) if (rsp_v[p]) begin
                        automatic integer e = int'(rsp_tag[p*TAGW +: TAGW]);
                        automatic integer b = int'(rsp_beat[p*BEATW +: BEATW]);
                        automatic integer s = int'(l_off[e]) + b;
                        if (e >= int'(nreq) || b >= int'(l_len[e]) || pc_of(l_addr[e]) != p || got[s]) fault <= 1'b1;
                        else begin buf_q[s] <= rsp_data[p*256 +: 256]; got[s] <= 1'b1; nl = nl + 1'b1; end
                    end
                    landed <= nl;
                    if (nl == nsec) begin run <= 0; fin <= 1; end
                end
            end
        end
    end endgenerate
endmodule
