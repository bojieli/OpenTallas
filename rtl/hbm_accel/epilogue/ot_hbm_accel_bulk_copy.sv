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
module ot_hbm_accel_bulk_copy #(
    parameter integer ENABLE = 0,
    parameter integer LINE_BITS = 1024,     // 128 B, the SM's ingest per cycle
    parameter integer DEPTH     = 1024,     // staging lines (128 KB)
    parameter integer MAX_OUT   = 512,      // outstanding reads (tracker entries)
    parameter integer AW        = 32,       // line address
    parameter integer DQ        = 4,        // descriptor queue
    parameter integer SRAM_RING = 0         // 1: the ring is LINE_BITS/256 hard SRAM macros (1024 deep)
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
    generate if (ENABLE == 0) begin : g_original
        ot_gpu_bulk_copy #(.LINE_BITS(LINE_BITS), .DEPTH(DEPTH), .MAX_OUT(MAX_OUT),
            .AW(AW), .DQ(DQ), .SRAM_RING(SRAM_RING)) u_original (.*);
    end else begin : g_lookahead
    // Look-ahead successor (HA3; retimed 2026-10-04 for 1.2 GHz SS). Same request/tag/order/data
    // contract and cycle behaviour as the original; the clock-limited loops are cut by:
    //  * head/next full flags carried in registers (no DEPTH:1 full-bit mux behind take); the
    //    look-ahead mux is addressed by registered next_slot/next2_slot;
    //  * full-bit set and clear both applied one edge late from registered, pre-decoded
    //    (32 x 32 one-hot) slot selects, so neither take nor the response tag fans out to DEPTH
    //    flops; the late set is covered by matching the registered response in the look-ahead;
    //  * request eligibility (ring space, outstanding credit) as registered flags with
    //    next-state look-ahead; counter increments as kept nets selected by the handshakes;
    //  * the SRAM output queue is a ping-pong pair written through per-256-bit-bank registered,
    //    duplicated write enables, read through a registered pointer.
    localparam integer TW = $clog2(DEPTH);
    localparam integer QW = (DQ <= 1) ? 1 : $clog2(DQ);
    localparam integer LO = TW / 2;                 // pre-decode split of a slot index
    localparam integer HI = TW - LO;
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
    reg [DEPTH-1:0]     full;
    reg [TW:0]          alloc_p, cons_p;            // one extra bit: ring occupancy = alloc - cons
    wire [TW:0]         used = alloc_p - cons_p;
    reg free_q, cred_q;                             // used < DEPTH ; outstanding < MAX_OUT
    assign req_v = act && free_q && cred_q;
    assign req_addr = a_addr;
    assign req_tag = alloc_p[TW-1:0];
    wire issue = req_v && req_ready;
    wire [TW-1:0] cslot = cons_p[TW-1:0];
    wire take;                                      // a line leaves the ring (to the output) this cycle
    (* keep *) wire [TW:0] alloc_inc; assign alloc_inc = alloc_p + 1'b1;
    (* keep *) wire [TW:0] cons_inc;  assign cons_inc = cons_p + 1'b1;
    (* keep *) wire [AW-1:0] addr_inc; assign addr_inc = a_addr + 1'b1;
    (* keep *) wire [23:0] left_dec; assign left_dec = a_left - 1'b1;
    localparam integer OW = $clog2(MAX_OUT+1);
    (* keep *) wire [OW-1:0] out_inc; assign out_inc = outstanding + 1'b1;
    (* keep *) wire [OW-1:0] out_dec; assign out_dec = outstanding - 1'b1;
    // look-ahead candidates for the eligibility flags, from registers only
    wire free_up = (used + 1'b1 < DEPTH), free_eq = (used < DEPTH), free_dn = (used - 1'b1 < DEPTH);
    wire cred_up = (outstanding + 1 < MAX_OUT), cred_eq = (outstanding < MAX_OUT), cred_dn = (outstanding - 1 < MAX_OUT);
    reg head_full, next_full;
    reg [TW-1:0] next_slot, next2_slot;
    (* keep *) wire [TW-1:0] n2_inc; assign n2_inc = next2_slot + 1'b1;
    reg rsp_q; reg [TW-1:0] rsp_tag_q;
    reg [(1<<HI)-1:0] set_hi, clr_hi; reg [(1<<LO)-1:0] set_lo, clr_lo;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            next_slot <= 1; next2_slot <= 2; rsp_q <= 0; rsp_tag_q <= 0;
            set_hi <= 0; set_lo <= 0; clr_hi <= 0; clr_lo <= 0;
            free_q <= 1; cred_q <= (MAX_OUT > 0);
        end else begin
            if (take) begin next_slot <= next2_slot; next2_slot <= n2_inc; end
            rsp_q <= rsp_v; rsp_tag_q <= rsp_tag;
            for (k = 0; k < (1<<HI); k = k + 1) begin
                set_hi[k] <= rsp_v && (rsp_tag[TW-1:LO] == k);
                clr_hi[k] <= take && (cslot[TW-1:LO] == k);
            end
            for (k = 0; k < (1<<LO); k = k + 1) begin
                set_lo[k] <= (rsp_tag[LO-1:0] == k);
                clr_lo[k] <= (cslot[LO-1:0] == k);
            end
            case ({issue, take})
                2'b10: free_q <= free_up;
                2'b01: free_q <= free_dn;
                default: free_q <= free_eq;
            endcase
            case ({issue, rsp_v})
                2'b10: cred_q <= cred_up;
                2'b01: cred_q <= cred_dn;
                default: cred_q <= cred_eq;
            endcase
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin head_full <= 0; next_full <= 0; end
        else if (take) begin
            head_full <= next_full || (rsp_v && rsp_tag == next_slot);
            next_full <= full[next2_slot] || (rsp_v && rsp_tag == next2_slot) || (rsp_q && rsp_tag_q == next2_slot);
        end else begin
            if (rsp_v && rsp_tag == cslot) head_full <= 1;
            if (rsp_v && rsp_tag == next_slot) next_full <= 1;
        end
    end
    wire load = !act && (q_cnt != 0);
    if (SRAM_RING == 0) begin : g_regs
        reg [LINE_BITS-1:0] ring [0:DEPTH-1];
        assign s_valid = head_full;
        assign s_data = ring[cslot];
        assign take = s_valid && s_ready;
        always @(posedge clk) if (rsp_v) ring[rsp_tag] <= rsp_data;
        assign idle = !act && (q_cnt == 0) && (outstanding == 0) && (used == 0);
    end else begin : g_sram
        // hard macros: a one-cycle read into a two-entry output queue keeps one line a cycle
        localparam integer NB = (LINE_BITS + 255) / 256;
        wire [NB*256-1:0] rd;
        wire [NB*256-1:0] wpad = {{(NB*256-LINE_BITS){1'b0}}, rsp_data};
        reg [NB*256-1:0] oq0, oq1;
        reg [1:0] oq_n;
        reg rd_v;
        wire pop_o = s_valid && s_ready;
        wire [1:0] after_pop = oq_n - (pop_o ? 1 : 0);
        reg space_q;
        wire [2:0] reserved = {1'b0,oq_n} + rd_v;
        assign take = head_full && (space_q || pop_o);
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) space_q <= 1;
            else case ({take,pop_o})
                2'b10: space_q <= (reserved == 0);
                2'b01: space_q <= 1;
                default: space_q <= space_q;
            endcase
        end
        genvar mb;
        for (mb = 0; mb < NB; mb = mb + 1) begin : g_mb
            ot_sram_1r1w_1024x256_m2_r2c2 u_ring (
                .clk(clk), .r_ce_in(take), .r_addr_in(cslot), .rd_out(rd[256*mb +: 256]),
                .w_ce_in(rsp_v), .w_addr_in(rsp_tag), .wd_in(wpad[256*mb +: 256]), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
        // two-entry ping-pong queue: the landing line goes to the entry named by the write pointer,
        // the output is the entry named by the read pointer. Per-bank write enables are registered
        // copies (we0/we1 = rd_v of the next cycle AND the then-current write pointer).
        reg oq_wp, oq_rp;
        (* keep *) reg [NB-1:0] we0, we1;
        assign s_valid = oq_n != 0;
        assign s_data = oq_rp ? oq1[LINE_BITS-1:0] : oq0[LINE_BITS-1:0];
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin oq_n <= 0; rd_v <= 1'b0; oq_wp <= 0; oq_rp <= 0; we0 <= 0; we1 <= 0; end
            else begin
                rd_v <= take;
                oq_n <= after_pop + (rd_v ? 1 : 0);
                if (rd_v) oq_wp <= ~oq_wp;
                if (pop_o) oq_rp <= ~oq_rp;
                we0 <= {NB{take && !(oq_wp ^ rd_v)}};
                we1 <= {NB{take &&  (oq_wp ^ rd_v)}};
            end
        end
        for (mb = 0; mb < NB; mb = mb + 1) begin : g_oq
            always @(posedge clk) begin
                if (we0[mb]) oq0[256*mb +: 256] <= rd[256*mb +: 256];
                if (we1[mb]) oq1[256*mb +: 256] <= rd[256*mb +: 256];
            end
        end
        assign idle = !act && (q_cnt == 0) && (outstanding == 0) && (used == 0) && (oq_n == 0) && !rd_v;
    end
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
                a_addr <= addr_inc;
                a_left <= left_dec;
                if (a_left == 1) act <= 1'b0;
            end
            if (issue) alloc_p <= alloc_inc;
            if (take) cons_p <= cons_inc;
            case ({issue, rsp_v})
                2'b10: outstanding <= out_inc;
                2'b01: outstanding <= out_dec;
                default: ;
            endcase
            // one-edge-late clear and set from the registered pre-decoded selects; a set wins
            for (k = 0; k < DEPTH; k = k + 1)
                if (set_hi[k >> LO] && set_lo[k % (1<<LO)]) full[k] <= 1'b1;
                else if (clr_hi[k >> LO] && clr_lo[k % (1<<LO)]) full[k] <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (d_valid && d_ready) begin q_base[q_wp] <= d_base; q_len[q_wp] <= d_lines; end
    end
    end endgenerate
endmodule
