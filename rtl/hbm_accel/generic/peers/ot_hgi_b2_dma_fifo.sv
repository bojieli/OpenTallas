`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hgi_b2_dma_fifo: a first-word-fall-through FIFO of W-bit records stored in
// the catalog's ASAP7 1R1W SRAM macros (physical/asap7_memory_macros), tiled
// ceil(W / MBITS) wide, for the collective engines' receive buffers (W15; root
// decision 2026-09-29: flop FIFOs of 100s of kbit are the wrong implementation).
//
//   push  : one record a cycle; never refused (the engine's credits bound the
//           occupancy; an overflow is latched in ovf).
//   head  : valid while hv; pop consumes it; one pop a cycle, sustained.
//
// The macro reads synchronously (data the cycle after r_ce), so the FIFO keeps
// a 2-entry register output buffer in front of the array: a read is issued
// whenever the buffer plus the read in flight is below 2 after this cycle's
// pop.  A record pushed while the array holds nothing and no read is in
// flight goes straight into the output buffer (bypass), so an empty FIFO shows
// a pushed record the next cycle -- the same as the flop FIFO it replaces.
// Records are delivered strictly in push order.
//
// MACRO: 0 ot_sram_1r1w_64x512_m1_r2c2, 1 ot_sram_1r1w_256x256_m2_r2c2,
//        2 ot_sram_1r1w_128x256_m1_r2c2, 3 ot_sram_1r1w_64x16_m1 (el1011 ctlw lane FIFOs).  DEPTH <= the macro's words.
// Repair ports are tied off (no spares in use).
// ---------------------------------------------------------------------------
module ot_hgi_b2_dma_fifo #(
    parameter integer W     = 547,
    parameter integer DEPTH = 64,
    parameter integer MACRO = 0,
    parameter integer ESL   = 0            // > 0: the output buffer in ESL-bit slices, each with its own kept copy of the
                                            //      head / occupancy / landing state (no buffer-wide select or enable net;
                                            //      hbm-hcvm 10-11, class 2).  0: unchanged
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          push,
    input  wire [W-1:0]  wdata,
    input  wire          pop,
    output wire          hv,
    output wire [W-1:0]  head,
    output reg           ovf
);
    localparam integer MWORDS = (MACRO == 0 || MACRO == 3) ? 64 : (MACRO == 1) ? 256 : 128;
    localparam integer MBITS  = (MACRO == 0) ? 512 : (MACRO == 3) ? 16 : 256;
    localparam integer MAW    = $clog2(MWORDS);
    localparam integer NT     = (W + MBITS - 1) / MBITS;
    localparam integer AW     = $clog2(DEPTH);
    initial if (DEPTH > MWORDS || (1 << AW) != DEPTH) $fatal(1, "ot_hgi_b2_dma_fifo: DEPTH must be a power of two <= %0d", MWORDS);

    // ---- array --------------------------------------------------------------------------------------------
    reg  [AW:0]   wp, rp;                          // array write / read pointers (records in the array: wp - rp)
    wire [AW:0]   in_arr = wp - rp;
    reg           inflight;                        // a read issued last cycle lands in rq this cycle
    wire [NT*MBITS-1:0] rq;
    // ---- output buffer: 2 registers ----------------------------------------------------------------------
    reg  [W-1:0]  ob [0:1];
    reg  [1:0]    oc;                              // occupancy
    reg           oh;                              // index of the head register
    assign hv = oc != 0;
    generate if (ESL == 0) begin : g_head
        assign head = ob[oh];
    end endgenerate
    wire          do_pop = pop && hv;
    wire [1:0]    oc_after = oc - (do_pop ? 1'b1 : 1'b0);
    // Exact pointer equality avoids subtract-to-zero on the bypass path.
    wire          arr_empty = wp == rp;
    wire          room = !oc_after[1] && !(oc_after[0] && inflight);
    wire          bypass = push && arr_empty && !inflight && room;
    wire          wr_arr = push && !bypass;
    wire [AW:0]   in_arr_next = in_arr + (wr_arr ? 1'b1 : 1'b0);
    // issue a read when the array (before this cycle's write) holds a record and the buffer has room for it
    wire          rd_arr = !arr_empty && room;

    genvar t;
    generate for (t = 0; t < NT; t = t + 1) begin : g_tile
        wire [MBITS-1:0] wd = {{(NT*MBITS-W){1'b0}}, wdata} >> (t * MBITS);
        wire [MAW-1:0] waddr = {{(MAW-AW){1'b0}}, wp[AW-1:0]};
        wire [MAW-1:0] raddr = {{(MAW-AW){1'b0}}, rp[AW-1:0]};
        if (MACRO == 0) begin : g_m0
            ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(rd_arr), .r_addr_in(raddr), .rd_out(rq[t*MBITS +: MBITS]),
                .w_ce_in(wr_arr), .w_addr_in(waddr), .wd_in(wd), .w_mask_in({MBITS{1'b1}}),
                .rr_en(2'b00), .rr_addr({(2*MAW){1'b0}}), .cr_en(2'b00), .cr_sel({(2*$clog2(MBITS)){1'b0}}));
        end else if (MACRO == 1) begin : g_m1
            ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(rd_arr), .r_addr_in(raddr), .rd_out(rq[t*MBITS +: MBITS]),
                .w_ce_in(wr_arr), .w_addr_in(waddr), .wd_in(wd), .w_mask_in({MBITS{1'b1}}),
                .rr_en(2'b00), .rr_addr({(2*(MAW-1)){1'b0}}), .cr_en(2'b00), .cr_sel({(2*$clog2(MBITS)){1'b0}}));
        end else if (MACRO == 3) begin : g_m3
            ot_sram_1r1w_64x16_m1 u_m (.clk(clk), .r_ce_in(rd_arr), .r_addr_in(raddr), .rd_out(rq[t*MBITS +: MBITS]),
                .w_ce_in(wr_arr), .w_addr_in(waddr), .wd_in(wd), .w_mask_in({MBITS{1'b1}}));
        end else begin : g_m2
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(rd_arr), .r_addr_in(raddr), .rd_out(rq[t*MBITS +: MBITS]),
                .w_ce_in(wr_arr), .w_addr_in(waddr), .wd_in(wd), .w_mask_in({MBITS{1'b1}}),
                .rr_en(2'b00), .rr_addr({(2*MAW){1'b0}}), .cr_en(2'b00), .cr_sel({(2*$clog2(MBITS)){1'b0}}));
        end
    end endgenerate

    // ---- state -------------------------------------------------------------------------------------------
    // entries entering the buffer this cycle, in order: the landing read (older), then a bypassed push
    wire [1:0] n_in = (inflight ? 2'd1 : 2'd0) + (bypass ? 2'd1 : 2'd0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; inflight <= 1'b0; oc <= 0; oh <= 1'b0; ovf <= 1'b0;
        end else begin
            if (wr_arr) begin
                wp <= wp + 1'b1;
                if (in_arr == DEPTH) ovf <= 1'b1;
            end
            if (rd_arr) rp <= rp + 1'b1;
            inflight <= rd_arr;
            if (do_pop) oh <= ~oh;
            oc <= oc_after + n_in;
            if (oc_after + n_in > 2) ovf <= 1'b1;
        end
    end
    // write slots: the first free register after the (post-pop) head
    generate if (ESL == 0) begin : g_ob
    always @(posedge clk) begin
        if (inflight) ob[do_pop ? (~oh ^ oc_after[0]) : (oh ^ oc[0])] <= rq[W-1:0];
        if (bypass) ob[(do_pop ? ~oh : oh) ^ (oc_after[0] ^ inflight)] <= wdata;
    end
    end else begin : g_esl
        localparam integer NS = (W + ESL - 1) / ESL;
        wire [1:0] oc_nx = oc_after + n_in;
        genvar s;
        for (s = 0; s < NS; s = s + 1) begin : g_s
            localparam integer LO = s * ESL;
            localparam integer WS = (W - LO < ESL) ? (W - LO) : ESL;
            (* keep *) reg oh_c, oc0_c, inf_c;           // copies of oh, oc[0], inflight for this slice
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin oh_c <= 1'b0; oc0_c <= 1'b0; inf_c <= 1'b0; end
                else begin oh_c <= do_pop ? ~oh_c : oh_c; oc0_c <= oc_nx[0]; inf_c <= rd_arr; end
            wire oa0 = oc0_c ^ do_pop;                    // oc_after[0]
            wire ia = do_pop ? (~oh_c ^ oa0) : (oh_c ^ oc0_c);
            wire ib = (do_pop ? ~oh_c : oh_c) ^ (oa0 ^ inf_c);
            reg [WS-1:0] b0, b1;
            always @(posedge clk) begin
                if (inf_c && !ia) b0 <= rq[LO +: WS];
                if (inf_c &&  ia) b1 <= rq[LO +: WS];
                if (bypass && !ib) b0 <= wdata[LO +: WS];
                if (bypass &&  ib) b1 <= wdata[LO +: WS];
            end
            assign head[LO +: WS] = oh_c ? b1 : b0;
        end
    end endgenerate
endmodule
