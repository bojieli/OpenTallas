`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// TMA-style bulk-copy weight engine of a GPU-organised SM (HBM comparator).
//
// A descriptor names a run of LINE-byte lines in HBM (the weight stream is
// static and pre-swizzled, so one descriptor covers a whole op, or several
// ops back to back).  The engine turns descriptors into line reads, up to
// MAX_OUT outstanding, each tagged with the staging slot it will land in.
// The memory system may return them in any order; the staging ring (SMEM,
// DEPTH lines) releases them to the tensor core strictly in stream order.
// A read is issued only when its staging slot is free, so the ring bounds the
// run-ahead and the engine keeps streaming through op boundaries and
// barriers until the ring is full.
//
// Sustained rate = min(port, MAX_OUT x LINE / latency, ring): the model's
// in-flight requirement (tools/uarch_model.hbm_gpu_design bulk_copy) is
// MAX_OUT x LINE >= the SM's share of HBM bandwidth x loaded latency.
// ---------------------------------------------------------------------------
module ot_gpu_bulk_copy #(
    parameter integer LINE_BITS = 1024,     // 128 B, the SM's ingest per cycle
    parameter integer DEPTH     = 1024,     // staging lines (128 KB)
    parameter integer MAX_OUT   = 512,      // outstanding reads (tracker entries)
    parameter integer AW        = 32,       // line address
    parameter integer DQ        = 4         // descriptor queue
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // descriptors
    input  wire                  d_valid,
    output wire                  d_ready,
    input  wire [AW-1:0]         d_base,
    input  wire [23:0]           d_lines,
    // read requests to the NoC / HBM controller
    output wire                  req_v,
    input  wire                  req_ready,
    output wire [AW-1:0]         req_addr,
    output wire [$clog2(DEPTH)-1:0] req_tag,
    // responses, any order
    input  wire                  rsp_v,
    input  wire [$clog2(DEPTH)-1:0] rsp_tag,
    input  wire [LINE_BITS-1:0]  rsp_data,
    // in-order stream to the tensor core
    output wire                  s_valid,
    input  wire                  s_ready,
    output wire [LINE_BITS-1:0]  s_data,
    output reg  [$clog2(MAX_OUT+1)-1:0] outstanding,
    output wire                  idle
);
    localparam integer TW = $clog2(DEPTH);
    localparam integer QW = (DQ <= 1) ? 1 : $clog2(DQ);
    // ---- descriptor queue ----
    reg [AW-1:0] q_base [0:DQ-1];
    reg [23:0]   q_len  [0:DQ-1];
    reg [QW:0]   q_cnt;
    reg [QW-1:0] q_wp, q_rp;
    assign d_ready = (q_cnt < DQ);
    // ---- active descriptor ----
    reg          act;
    reg [AW-1:0] a_addr;
    reg [23:0]   a_left;
    // ---- staging ring ----
    reg [LINE_BITS-1:0] ring [0:DEPTH-1];
    reg [DEPTH-1:0]     full;
    reg [TW:0]          alloc_p, cons_p;            // one extra bit: ring occupancy = alloc - cons
    wire [TW:0]         used = alloc_p - cons_p;
    wire                slot_free = used < DEPTH;
    assign req_v = act && slot_free && (outstanding < MAX_OUT);
    assign req_addr = a_addr;
    assign req_tag = alloc_p[TW-1:0];
    wire issue = req_v && req_ready;
    wire [TW-1:0] cslot = cons_p[TW-1:0];
    assign s_valid = full[cslot];
    assign s_data = ring[cslot];
    wire pop = s_valid && s_ready;
    assign idle = !act && (q_cnt == 0) && (outstanding == 0) && (used == 0);
    wire load = !act && (q_cnt != 0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q_cnt <= 0; q_wp <= 0; q_rp <= 0; act <= 1'b0; a_addr <= 0; a_left <= 0;
            alloc_p <= 0; cons_p <= 0; outstanding <= 0; full <= {DEPTH{1'b0}};
        end else begin
            q_cnt <= q_cnt + (d_valid && d_ready ? 1 : 0) - (load ? 1 : 0);
            if (d_valid && d_ready) q_wp <= (q_wp == DQ - 1) ? 0 : q_wp + 1'b1;
            if (load) begin
                act <= (q_len[q_rp] != 0);
                a_addr <= q_base[q_rp];
                a_left <= q_len[q_rp];
                q_rp <= (q_rp == DQ - 1) ? 0 : q_rp + 1'b1;
            end else if (issue) begin
                a_addr <= a_addr + 1'b1;
                a_left <= a_left - 1'b1;
                if (a_left == 1) act <= 1'b0;
            end
            if (issue) alloc_p <= alloc_p + 1'b1;
            if (pop) cons_p <= cons_p + 1'b1;
            outstanding <= outstanding + (issue ? 1 : 0) - (rsp_v ? 1 : 0);
            if (rsp_v) full[rsp_tag] <= 1'b1;
            if (pop) full[cslot] <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (d_valid && d_ready) begin q_base[q_wp] <= d_base; q_len[q_wp] <= d_lines; end
        if (rsp_v) ring[rsp_tag] <= rsp_data;
    end
endmodule
