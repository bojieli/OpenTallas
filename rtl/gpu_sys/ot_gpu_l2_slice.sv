`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_l2_slice: one address-interleaved L2 slice (clk_mem), the point of
// coherence for the addresses it owns (die-global byte address bits
// [7 +: log2(NS)] == this slice's index; the crossbar guarantees it).
//
// Cache: sectored, direct-mapped.  128-byte lines (one tag each) of four
// 32-byte sectors (a valid bit each), L2_BYTES of data.  Indexing uses the
// partition-local address (slice-select bits removed), so every line is used.
//   * read hit: data from the array;
//   * read miss: one-sector read to the partition, fills only that sector on
//     return (a line whose tag differs is replaced: new tag, only that sector
//     valid);
//   * write hit: merge the bytes into the line (update on write hit), then
//     write the WHOLE merged sector through (strobe all ones, so the partition
//     needs no read-modify-write);
//   * write miss: no allocate, written through with the client's strobe;
//   * a write is acknowledged only when the partition acknowledged it.
//
// Ordering (in-order, non-blocking): requests are serialised at acceptance
// (one per cycle) into an in-order completion queue of OSD entries; the queue
// index is the downstream tag, so up to OSD misses/writes are outstanding and
// responses return to the crossbar in acceptance order.  Serialisation at
// acceptance is the coherence order: a read hit reads the array at its
// acceptance edge, misses and writes reach the partition in acceptance order
// and the partition orders same-sector accesses.  Two hazards stall the
// acceptance of a new request:
//   * a read miss to the same sector is outstanding (its fill would otherwise
//     overwrite a later write to that sector with pre-write data);
//   * a fill writes the same line index this cycle.
// ENABLE = 0 (default): inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_l2_slice #(
    parameter integer ENABLE   = 0,
    parameter integer NS       = 2,
    parameter integer TW       = 18,         // upstream (slice-side) tag width
    parameter integer L2_BYTES = 32768,
    parameter integer OSD      = 64,         // outstanding requests (completion queue entries)
    parameter integer LOSD     = (OSD > 1) ? $clog2(OSD) : 1,   // downstream tag width
    parameter integer LNS      = (NS > 1) ? $clog2(NS) : 0
) (
    input  wire            clk,
    input  wire            rst_n,
    // upstream MREQ (from the crossbar)
    input  wire            req_v,
    output reg             req_rdy,
    input  wire            req_we,
    input  wire [31:0]     req_addr,
    input  wire [255:0]    req_wdata,
    input  wire [31:0]     req_wstrb,
    input  wire [TW-1:0]   req_tag,
    output reg             rsp_v,
    input  wire            rsp_rdy,
    output reg  [TW-1:0]   rsp_tag,
    output reg             rsp_we,
    output reg  [255:0]    rsp_data,
    // downstream MREQ (to the HBM partition); address is the die-global byte address
    output reg             d_req_v,
    input  wire            d_req_rdy,
    output reg             d_req_we,
    output reg  [31:0]     d_req_addr,
    output reg  [255:0]    d_req_wdata,
    output reg  [31:0]     d_req_wstrb,
    output reg  [LOSD-1:0] d_req_tag,
    input  wire            d_rsp_v,
    output reg             d_rsp_rdy,
    input  wire [LOSD-1:0] d_rsp_tag,
    input  wire            d_rsp_we,
    input  wire [255:0]    d_rsp_data,
    // statistics and protocol fault (unexpected downstream response)
    output reg  [31:0]     stat_rd_hit,
    output reg  [31:0]     stat_rd_miss,
    output reg  [31:0]     stat_wr_hit,
    output reg  [31:0]     stat_wr_miss,
    output reg             fault
);
    generate if (ENABLE != 0) begin : g_on
        localparam integer NLINES = L2_BYTES / 128;
        localparam integer LIW    = (NLINES > 1) ? $clog2(NLINES) : 1;
        localparam integer SECW   = 27 - LNS;                 // partition-local sector address bits
        localparam integer LTW    = SECW - 2 - LIW;           // line tag bits
        initial if ((NLINES & (NLINES - 1)) != 0 || (OSD & (OSD - 1)) != 0)
            $fatal(1, "ot_gpu_l2_slice: L2_BYTES/128 and OSD must be powers of two");

        // cache state
        reg [LTW-1:0] c_tag [0:NLINES-1];
        reg [3:0]     c_val [0:NLINES-1];
        reg [255:0]   c_dat [0:NLINES*4-1];
        // completion queue
        reg            e_done [0:OSD-1];
        reg            e_we   [0:OSD-1];
        reg            e_miss [0:OSD-1];       // read miss awaiting its fill
        reg [TW-1:0]   e_tag  [0:OSD-1];
        reg [255:0]    e_data [0:OSD-1];
        reg [SECW-1:0] e_sec  [0:OSD-1];
        reg [LOSD-1:0] hp, tp;
        reg [LOSD:0]   qn;

        integer i, b;

        function automatic [SECW-1:0] lsec(input [31:0] a);   // partition-local sector address
            reg [31:0] la;
            begin
                la = (NS > 1) ? (((a >> (7 + LNS)) << 7) | (a & 32'h7f)) : a;
                lsec = SECW'(la >> 5);
            end
        endfunction

        // decode of the offered request
        reg [SECW-1:0] n_sec;
        reg [LIW-1:0]  n_idx;
        reg [LTW-1:0]  n_ltag;
        reg [1:0]      n_sub;
        reg            n_hit, n_haz, n_down, n_take;
        reg [255:0]    n_merged;
        // fill this cycle
        reg            f_take;
        reg [LOSD-1:0] f_e;
        reg [SECW-1:0] f_sec;
        reg            r_load;   // head retires into the response register

        always @(*) begin
            n_sec  = lsec(req_addr);
            n_sub  = n_sec[1:0];
            n_idx  = n_sec[2 +: LIW];
            n_ltag = n_sec[SECW-1 : 2+LIW];
            n_hit  = c_val[n_idx][n_sub] && (c_tag[n_idx] == n_ltag);
            for (b = 0; b < 32; b = b + 1)
                n_merged[b*8 +: 8] = req_wstrb[b] ? req_wdata[b*8 +: 8] : c_dat[{n_idx, n_sub}][b*8 +: 8];
            f_take = d_rsp_v;
            f_e    = d_rsp_tag;
            f_sec  = e_sec[d_rsp_tag];
            n_haz  = f_take && !e_we[f_e] && (f_sec[2 +: LIW] == n_idx);
            for (i = 0; i < OSD; i = i + 1)
                if (e_miss[i] && e_sec[i] == n_sec) n_haz = 1'b1;
            n_down = req_we || !n_hit;
            req_rdy = (qn < (LOSD+1)'(OSD)) && !n_haz && (!n_down || !d_req_v || d_req_rdy) && !fault;
            n_take = req_v && req_rdy;
            d_rsp_rdy = 1'b1;     // every downstream tag owns a reserved queue entry
            r_load = (qn != 0) && e_done[hp] && (!rsp_v || rsp_rdy);
        end

        always @(posedge clk) begin
            if (!rst_n) begin
                for (i = 0; i < NLINES; i = i + 1) begin c_val[i] <= 4'd0; c_tag[i] <= '0; end
                for (i = 0; i < OSD; i = i + 1) begin e_done[i] <= 1'b0; e_miss[i] <= 1'b0; e_we[i] <= 1'b0; end
                hp <= '0; tp <= '0; qn <= '0;
                rsp_v <= 1'b0; rsp_tag <= '0; rsp_we <= 1'b0; rsp_data <= '0;
                d_req_v <= 1'b0; d_req_we <= 1'b0; d_req_addr <= '0; d_req_wdata <= '0; d_req_wstrb <= '0;
                d_req_tag <= '0;
                stat_rd_hit <= 0; stat_rd_miss <= 0; stat_wr_hit <= 0; stat_wr_miss <= 0; fault <= 1'b0;
            end else begin
                // downstream response: fill / write ack
                if (f_take) begin
                    if (qn == 0 || e_done[f_e] || (d_rsp_we != e_we[f_e])) fault <= 1'b1;
                    e_done[f_e] <= 1'b1;
                    if (!e_we[f_e]) begin
                        e_data[f_e] <= d_rsp_data;
                        e_miss[f_e] <= 1'b0;
                        c_dat[f_sec[LIW+1:0]] <= d_rsp_data;
                        if (c_tag[f_sec[2 +: LIW]] == f_sec[SECW-1 : 2+LIW])
                            c_val[f_sec[2 +: LIW]][f_sec[1:0]] <= 1'b1;
                        else begin
                            c_tag[f_sec[2 +: LIW]] <= f_sec[SECW-1 : 2+LIW];
                            c_val[f_sec[2 +: LIW]] <= 4'b0001 << f_sec[1:0];
                        end
                    end
                end
                if (d_req_v && d_req_rdy) d_req_v <= 1'b0;
                // accept a new request
                if (n_take) begin
                    tp <= tp + 1'b1;
                    e_we[tp] <= req_we; e_tag[tp] <= req_tag; e_sec[tp] <= n_sec;
                    if (!req_we && n_hit) begin
                        e_done[tp] <= 1'b1; e_miss[tp] <= 1'b0; e_data[tp] <= c_dat[{n_idx, n_sub}];
                        stat_rd_hit <= stat_rd_hit + 1;
                    end else begin
                        e_done[tp] <= 1'b0; e_miss[tp] <= !req_we;
                        d_req_v <= 1'b1; d_req_we <= req_we; d_req_addr <= req_addr; d_req_tag <= tp;
                        if (req_we && n_hit) begin
                            c_dat[{n_idx, n_sub}] <= n_merged;
                            d_req_wdata <= n_merged; d_req_wstrb <= 32'hffff_ffff;
                            stat_wr_hit <= stat_wr_hit + 1;
                        end else begin
                            d_req_wdata <= req_wdata; d_req_wstrb <= req_we ? req_wstrb : 32'd0;
                            if (req_we) stat_wr_miss <= stat_wr_miss + 1;
                            else stat_rd_miss <= stat_rd_miss + 1;
                        end
                    end
                end
                // retire the head in order
                if (rsp_v && rsp_rdy) rsp_v <= 1'b0;
                if (r_load) begin
                    rsp_v <= 1'b1; rsp_tag <= e_tag[hp]; rsp_we <= e_we[hp]; rsp_data <= e_we[hp] ? 256'd0 : e_data[hp];
                    e_done[hp] <= 1'b0;
                    hp <= hp + 1'b1;
                end
                qn <= qn + (n_take ? 1 : 0) - (r_load ? 1 : 0);
            end
        end
    end else begin : g_off
        assign req_rdy = 1'b0;
        assign rsp_v = 1'b0;
        assign rsp_tag = '0;
        assign rsp_we = 1'b0;
        assign rsp_data = '0;
        assign d_req_v = 1'b0;
        assign d_req_we = 1'b0;
        assign d_req_addr = '0;
        assign d_req_wdata = '0;
        assign d_req_wstrb = '0;
        assign d_req_tag = '0;
        assign d_rsp_rdy = 1'b0;
        assign stat_rd_hit = 0;
        assign stat_rd_miss = 0;
        assign stat_wr_hit = 0;
        assign stat_wr_miss = 0;
        assign fault = 1'b0;
    end endgenerate
endmodule
