`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_ring_port -- the four stacks' index-key K-port side of the
// W11 quarter-per-stack ring layout: key writer + read/write arbiter.  It
// replaces ot_hdc_v41x_idx_pool_hbm_bridge (replicated key images) when the
// ring layout is selected (IDX_RING), with the same record input and HBM
// port interface.
//
// Records.  Each record is one encoded key from the core's writer
// (ot_hdc_v41x_idx_pool_kwr, unsharded): code sector w_csec, scale sector
// w_ssec, slot w_sslot.  That writer addresses key t of a region at block B0
// as scale sector B0*128 + t/8 (t < 1,024), so the record names its region
// (B0 = w_ssec / 128) and its row (t = {w_ssec mod 128, w_sslot}).  A record is
// a decode STEP of that region's ring (count t -> t + 1): the key goes to its
// quarter's stack and, every 32nd row, 48 keys migrate one stack down
// (ot_hdc_v41x_idx_ring_kwr, user 0, region base B0).  A RFQ-deep record FIFO
// decouples the core's writer from migrations.
//
// Arbitration, per pseudo-channel port: the writer's one request a cycle wins
// the port it targets; the reader (the pooled adapter's four ring streams)
// has every other port.  Responses are routed by tag: the port sets bit 12
// of every writer request (its migration reads return with it) (the ring readers' tags {offset, 00, block}
// keep bits 13:12 zero).
//   READ_FENCE = 1: reader requests wait while the writer holds any record
//     (the legacy bridge's rule: a scan of the same step needs its keys);
//   READ_FENCE = 0: writes and a scan run concurrently -- correct when the
//     scan does not need the in-flight writes (another user's keys, or the
//     same user's later steps: a step's new key and migrated keys land in
//     slots outside every stack's current range).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_ring_port #(
    parameter integer NPC=32, AW=28, TAGW=16, LENW=4, BEATW=4,
    parameter integer RSB=1, RTAIL=0, RFQ=4, READ_FENCE=1,
    parameter integer DIRECT=0      // 1: take (region block, count, key) commands on d_* instead of records
) (
    input  wire clk, rst_n,
    // key records (the bridge's record interface)
    input  wire w_v,
    output wire w_rdy,
    input  wire [AW-1:0] w_csec,
    input  wire [511:0] w_codes,
    input  wire [AW-1:0] w_ssec,
    input  wire [2:0] w_sslot,
    input  wire [31:0] w_scales,
    // DIRECT = 1: a decode step of the ring at block d_base (count d_n -> d_n + 1)
    input  wire d_v,
    output wire d_rdy,
    input  wire [AW-8:0] d_base,
    input  wire [AW+2:0] d_n,
    input  wire [543:0] d_key,
    // reader requests / responses
    input  wire [4*NPC-1:0] r_v,
    output wire [4*NPC-1:0] r_rdy,
    input  wire [4*NPC*AW-1:0] r_addr,
    input  wire [4*NPC*LENW-1:0] r_len,
    input  wire [4*NPC*TAGW-1:0] r_tag,
    output wire [4*NPC-1:0] r_rsp_v,
    input  wire [4*NPC-1:0] r_rsp_rdy,
    // HBM K ports
    output wire [4*NPC-1:0] h_v,
    input  wire [4*NPC-1:0] h_rdy,
    output wire [4*NPC*AW-1:0] h_addr,
    output wire [4*NPC*LENW-1:0] h_len,
    output wire [4*NPC*TAGW-1:0] h_tag,
    output wire [4*NPC-1:0] h_we,
    output wire [4*NPC*256-1:0] h_wdata,
    output wire [4*NPC*32-1:0] h_wstrb,
    input  wire [4*NPC-1:0] h_wr_done,
    input  wire [4*NPC-1:0] h_rsp_v,
    output wire [4*NPC-1:0] h_rsp_rdy,
    input  wire [4*NPC*TAGW-1:0] h_rsp_tag,
    input  wire [4*NPC*256-1:0] h_rsp_data,
    output wire busy,
    output reg  fault,
    output reg [31:0] dbg_records,
    output reg [31:0] dbg_writes,
    output reg [31:0] dbg_fifo_highwater,
    output reg [31:0] dbg_read_stalls,
    output reg [31:0] dbg_writer_stalls,
    output wire [47:0] dbg_migrations,
    output wire [47:0] dbg_copied_sectors
);
    localparam integer HW = AW - 7;
    localparam integer NW = HW + 10;
    localparam integer FW = $clog2(RFQ + 1);
    // ---- record FIFO ----
    reg [HW-1:0] fq_b0 [0:RFQ-1];
    reg [NW-1:0] fq_row [0:RFQ-1];
    reg [543:0]  fq_key [0:RFQ-1];
    reg [$clog2(RFQ)-1:0] rp, wp;
    reg [FW-1:0] cnt;
    assign w_rdy = DIRECT == 0 && cnt < RFQ;
    assign d_rdy = DIRECT != 0 && cnt < RFQ;
    wire push = DIRECT != 0 ? (d_v && d_rdy) : (w_v && w_rdy);
    wire c_rdy;
    wire pop = cnt != 0 && c_rdy;
    // ---- writer ----
    wire [4*NPC-1:0] wr_v, wr_we, wr_rsp_rdy;
    wire [4*NPC*AW-1:0] wr_addr;
    wire [4*NPC*LENW-1:0] wr_len;
    wire [4*NPC*TAGW-1:0] wr_tag;
    wire [4*NPC*256-1:0] wr_wdata;
    wire [4*NPC*32-1:0] wr_wstrb;
    wire wr_busy, wr_fault;
    wire [47:0] wr_keys;
    // responses: bit 12 marks the writer's migration reads
    wire [4*NPC-1:0] rsp_w;
    genvar gi;
    generate for (gi = 0; gi < 4*NPC; gi = gi + 1) begin : g_route
        assign rsp_w[gi] = h_rsp_tag[gi*TAGW + 12];
    end endgenerate
    ot_hdc_v41x_idx_ring_kwr #(.NPC(NPC),.AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),
        .DW(256),.UW(1),.RSB(RSB),.RTAIL(RTAIL)) u_w (
        .clk(clk),.rst_n(rst_n),.cfg_key_base_block(fq_b0[rp]),
        .c_v(cnt != 0),.c_rdy(c_rdy),.c_op(1'b0),.c_user(1'b0),.c_n(fq_row[rp]),.c_pos('0),
        .c_key(fq_key[rp]),.busy(wr_busy),.fault(wr_fault),
        .h_req_v(wr_v),.h_req_rdy(h_rdy),.h_req_addr(wr_addr),.h_req_len(wr_len),.h_req_tag(wr_tag),
        .h_req_we(wr_we),.h_req_wdata(wr_wdata),.h_req_wstrb(wr_wstrb),.h_wr_done(h_wr_done),
        .h_rsp_v(h_rsp_v & rsp_w),.h_rsp_rdy(wr_rsp_rdy),.h_rsp_tag(h_rsp_tag),.h_rsp_data(h_rsp_data),
        .cnt_keys(wr_keys),.cnt_migrations(dbg_migrations),.cnt_copied_sectors(dbg_copied_sectors));
    wire hold = READ_FENCE != 0 && (cnt != 0 || wr_busy || w_v || d_v);
    assign busy = cnt != 0 || wr_busy;
    generate for (gi = 0; gi < 4*NPC; gi = gi + 1) begin : g_port
        wire wsel = wr_v[gi];
        assign h_v[gi] = wsel || (!hold && r_v[gi]);
        assign r_rdy[gi] = !wsel && !hold && h_rdy[gi];
        assign h_addr[gi*AW +: AW] = wsel ? wr_addr[gi*AW +: AW] : r_addr[gi*AW +: AW];
        assign h_len[gi*LENW +: LENW] = wsel ? wr_len[gi*LENW +: LENW] : r_len[gi*LENW +: LENW];
        assign h_tag[gi*TAGW +: TAGW] = wsel ? (wr_tag[gi*TAGW +: TAGW] | (TAGW'(1) << 12)) : r_tag[gi*TAGW +: TAGW];
        assign h_we[gi] = wsel && wr_we[gi];
        assign h_wdata[gi*256 +: 256] = wr_wdata[gi*256 +: 256];
        assign h_wstrb[gi*32 +: 32] = wr_wstrb[gi*32 +: 32];
        assign r_rsp_v[gi] = h_rsp_v[gi] && !rsp_w[gi];
        assign h_rsp_rdy[gi] = rsp_w[gi] ? 1'b1 : r_rsp_rdy[gi];
    end endgenerate
    integer i, nw;
    always @* begin
        nw = 0;
        for (i = 0; i < 4*NPC; i = i + 1) nw = nw + (h_wr_done[i] ? 1 : 0);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rp <= 0; wp <= 0; cnt <= 0; fault <= 0;
            dbg_records <= 0; dbg_writes <= 0; dbg_fifo_highwater <= 0; dbg_read_stalls <= 0; dbg_writer_stalls <= 0;
        end else begin
            if (push && DIRECT != 0) begin
                fq_b0[wp] <= d_base; fq_row[wp] <= d_n; fq_key[wp] <= d_key; wp <= wp + 1'b1;
            end
            if (push && DIRECT == 0) begin
                fq_b0[wp] <= HW'(w_ssec >> 7);
                fq_row[wp] <= NW'({w_ssec[6:0], w_sslot});
                fq_key[wp] <= {w_scales, w_codes};
                wp <= wp + 1'b1;
                // the record's code sector must be the one its (region, row) implies
                if (w_csec != {HW'(w_ssec >> 7) + HW'(1) + HW'(w_ssec[6:3]), 7'd0} + AW'({w_ssec[2:0], w_sslot, 1'b0}))
                    fault <= 1'b1;
            end
            if (pop) begin rp <= rp + 1'b1; dbg_records <= dbg_records + 1; end
            cnt <= cnt + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            if (FW'(cnt) > dbg_fifo_highwater[FW-1:0]) dbg_fifo_highwater <= 32'(cnt);
            dbg_writes <= dbg_writes + 32'(nw);
            if (|(r_v & (~r_rdy))) dbg_read_stalls <= dbg_read_stalls + 1;
            if ((DIRECT != 0 ? d_v && !d_rdy : w_v && !w_rdy)) dbg_writer_stalls <= dbg_writer_stalls + 1;
            if (wr_fault) fault <= 1'b1;
        end
    end
endmodule
