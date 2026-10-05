`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_coll_endpoint: per-die collective endpoint of the GPU-organised HBM
// comparator (the NVLink-port side of a GPU: SM-side request, records over a
// die->switch link, in-switch NVLS reduction / multicast back).
//
// clk_sm side: the spec's "Collective endpoint interface"
//   coll_req_v/rdy, coll_mode (0 ALL_REDUCE sum, 1 ALL_GATHER), coll_count
//   (lanes used, 1..NL), coll_data (lane l = [32l +: 32]);
//   coll_rsp_v/rdy, coll_rsp_data.  One collective outstanding: coll_req_rdy
//   is high only when idle (after the previous response was taken).
//   ALL_REDUCE: rsp lane l < count = the switch's sum (R = 2: r0 + r1, binary32
//               RNE, canonical +0); lanes >= count are 0.
//   ALL_GATHER: rsp lane r*count + i = rank r's lane i; other lanes 0.
//
// Records (the reused switch's format, rtl/link/ot_link_nvls_switch.sv):
//   {tag[TAGW], mode, last, data[LANES*32]}, tag = {src[7:0], seq[7:0],
//   count[7:0], word[7:0]}.  A request of count lanes is NREC = ceil(count /
//   LANES) records, word 0..NREC-1 in order (every rank emits the same fixed
//   order, which the switch's pop-together reduction requires); lanes >= count
//   are sent as +0.  The switch rewrites src to 8'hFF on reduce results.
//
// Clock crossing: records cross clk_sm -> clk_link and back in ot_gpu_cdc_fifo
// (rtl/link/ot_link_afifo.sv underneath).  TX depth 2^AW (AW = 3 sustains one
// record per link cycle, tools/gpu_sys/cdc_sizing.py sm_to_link_collective).
// The link side has no ready: the switch takes a record every cycle and
// multicasts with no backpressure, so flow control is by protocol bound --
//   * switch input FIFO: <= NL/LANES records per port per collective, one
//     collective outstanding per rank (checked against DEPTH in the fabric);
//   * RX: the endpoint drains its RX FIFO only while collecting.  While it
//     holds a response, another rank may already have issued the NEXT
//     collective; if that is a gather the switch forwards up to
//     (R-1)*ceil(NL/(R*LANES)) of its records here.  RX depth 2^AW_RX covers
//     that bound (elaboration check).  A push into a full RX FIFO latches
//     coll_fault (fail closed, never silent).
// Every received record's tag is checked (seq, count, mode, word, src);
// a mismatch latches coll_fault.
//
// ENABLE = 0 (default): inert, every output 0, no logic.
// ---------------------------------------------------------------------------
module ot_gpu_coll_endpoint #(
    parameter integer ENABLE = 0,
    parameter integer NL     = 128,
    parameter integer LANES  = 16,
    parameter integer R      = 2,
    parameter integer RANK   = 0,
    parameter integer TAGW   = 32,
    parameter integer AW     = 3,
    parameter integer AW_RX  = 4,
    parameter integer SYNC   = 2,
    parameter integer FW     = 32 * LANES,
    parameter integer PW     = FW + 2 + TAGW
) (
    // ---- clk_sm side ----
    input  wire              clk_sm,
    input  wire              rst_sm_n,
    input  wire              coll_req_v,
    output wire              coll_req_rdy,
    input  wire              coll_mode,
    input  wire [7:0]        coll_count,
    input  wire [NL*32-1:0]  coll_data,
    output wire              coll_rsp_v,
    input  wire              coll_rsp_rdy,
    output wire [NL*32-1:0]  coll_rsp_data,
    output wire              coll_fault,      // sticky (clk_sm): protocol / tag / overflow fault
    // ---- clk_link side: die -> switch, switch -> die ----
    input  wire              clk_link,
    input  wire              rst_link_n,
    output wire              lk_tx_v,
    output wire [PW-1:0]     lk_tx_rec,
    input  wire              lk_rx_v,
    input  wire [PW-1:0]     lk_rx_rec
);
    generate if (ENABLE != 0) begin : g_on
        localparam integer GPRE = (R - 1) * ((NL / R + LANES - 1) / LANES);   // early gather records bound
        localparam [7:0]   RK8  = RANK[7:0];
        if (TAGW != 32) begin : g_bad_tagw
            $error("ot_gpu_coll_endpoint: TAGW must be 32 (tag = {src, seq, count, word})");
        end
        if (NL > 255 || NL < 1) begin : g_bad_nl
            $error("ot_gpu_coll_endpoint: NL must be 1..255 (coll_count is 8 bits)");
        end
        if ((1 << AW_RX) < GPRE + 2) begin : g_bad_rx
            $error("ot_gpu_coll_endpoint: RX FIFO depth 2^AW_RX below the early-gather bound + 2");
        end
        if (RANK < 0 || RANK >= R || R > 255) begin : g_bad_rank
            $error("ot_gpu_coll_endpoint: RANK must be in 0..R-1 and R <= 255");
        end

        // ---------------- clk_sm: request, segmentation, reassembly, response ----------------
        localparam [1:0] S_IDLE = 2'd0, S_RUN = 2'd1, S_RSP = 2'd2;
        reg  [1:0]        st;
        reg  [NL*32-1:0]  dat;
        reg  [NL*32-1:0]  asmb;
        reg               mode_q;
        reg  [7:0]        cnt_q;
        reg  [7:0]        seq;
        reg  [7:0]        sw;        // next word to send
        reg  [7:0]        nrec;      // records this rank sends
        reg  [8:0]        nexp;      // records expected back
        reg  [8:0]        rcv;
        reg               flt_sm;

        // TX record of word sw
        reg  [FW-1:0]     txd;
        integer j;
        always @(*) begin
            for (j = 0; j < LANES; j = j + 1)
                if (32'(sw) * LANES + j < 32'(cnt_q) && 32'(sw) * LANES + j < NL)
                    txd[32*j +: 32] = dat[32 * (32'(sw) * LANES + j) +: 32];
                else
                    txd[32*j +: 32] = 32'd0;
        end
        wire [PW-1:0] tx_rec = {RK8, seq, cnt_q, sw, mode_q, (sw + 8'd1 == nrec), txd};
        wire          tx_in_v = (st == S_RUN) && (sw < nrec);
        wire          tx_in_rdy;

        // RX record
        wire          rx_out_v;
        wire [PW-1:0] rx_d;
        wire          rx_take = rx_out_v && (st == S_RUN);
        wire [7:0]    r_src  = rx_d[PW-1 -: 8];
        wire [7:0]    r_seq  = rx_d[PW-9 -: 8];
        wire [7:0]    r_cnt  = rx_d[PW-17 -: 8];
        wire [7:0]    r_word = rx_d[PW-25 -: 8];
        wire          r_mode = rx_d[FW + 1];
        wire          r_bad  = (r_seq != seq) || (r_cnt != cnt_q) || (r_mode != mode_q) || (r_word >= nrec) ||
                               (mode_q ? (32'(r_src) >= R) : (r_src != 8'hFF));

        wire [8:0]  req_nrec = 9'((32'(coll_count) + LANES - 1) / LANES);
        wire        req_bad  = (coll_count == 8'd0) || (32'(coll_count) > NL) ||
                               (coll_mode && 32'(coll_count) * R > NL);
        // the received record placed into the assembly (ALL_REDUCE: lane = word*LANES + k;
        // ALL_GATHER: lane = src*count + word*LANES + k); only lanes < count are written
        reg [NL*32-1:0] asmb_n;
        integer k, idx, dst;
        always @(*) begin
            asmb_n = asmb;
            for (k = 0; k < LANES; k = k + 1) begin
                idx = 32'(r_word) * LANES + k;
                dst = mode_q ? 32'(r_src) * 32'(cnt_q) + idx : idx;
                if (idx < 32'(cnt_q) && dst < NL) asmb_n[32 * dst +: 32] = rx_d[32*k +: 32];
            end
        end
        always @(posedge clk_sm or negedge rst_sm_n) begin
            if (!rst_sm_n) begin
                st <= S_IDLE; mode_q <= 1'b0; cnt_q <= 8'd0; seq <= 8'd0; sw <= 8'd0; nrec <= 8'd0;
                nexp <= 9'd0; rcv <= 9'd0; flt_sm <= 1'b0; asmb <= {NL*32{1'b0}};
            end else begin
                case (st)
                    S_IDLE: if (coll_req_v) begin
                        dat <= coll_data; mode_q <= coll_mode; cnt_q <= coll_count;
                        sw <= 8'd0; nrec <= req_nrec[7:0]; rcv <= 9'd0;
                        nexp <= coll_mode ? 9'(32'(req_nrec) * R) : req_nrec;
                        asmb <= {NL*32{1'b0}};
                        if (req_bad) flt_sm <= 1'b1;
                        st <= (req_nrec == 9'd0) ? S_RSP : S_RUN;
                    end
                    S_RUN: begin
                        if (tx_in_v && tx_in_rdy) sw <= sw + 8'd1;
                        if (rx_take) begin
                            if (r_bad) flt_sm <= 1'b1;
                            asmb <= asmb_n;
                            rcv <= rcv + 9'd1;
                            if (rcv + 9'd1 >= nexp) st <= S_RSP;
                        end
                    end
                    S_RSP: if (coll_rsp_rdy) begin
                        st <= S_IDLE; seq <= seq + 8'd1;
                    end
                    default: st <= S_IDLE;
                endcase
            end
        end
        assign coll_req_rdy  = (st == S_IDLE);
        assign coll_rsp_v    = (st == S_RSP);
        assign coll_rsp_data = asmb;

        // ---------------- clock crossings ----------------
        wire tx_ovf, rx_ovf, rx_in_rdy;
        ot_gpu_cdc_fifo #(.ENABLE(1), .W(PW), .AW(AW), .SYNC(SYNC)) u_tx_cdc (
            .wclk(clk_sm), .wrst_n(rst_sm_n), .in_v(tx_in_v), .in_rdy(tx_in_rdy), .in_d(tx_rec),
            .rclk(clk_link), .rrst_n(rst_link_n), .out_v(lk_tx_v), .out_rdy(1'b1), .out_d(lk_tx_rec),
            .ovf_fault(tx_ovf));
        ot_gpu_cdc_fifo #(.ENABLE(1), .W(PW), .AW(AW_RX), .SYNC(SYNC)) u_rx_cdc (
            .wclk(clk_link), .wrst_n(rst_link_n), .in_v(lk_rx_v), .in_rdy(rx_in_rdy), .in_d(lk_rx_rec),
            .rclk(clk_sm), .rrst_n(rst_sm_n), .out_v(rx_out_v), .out_rdy(st == S_RUN), .out_d(rx_d),
            .ovf_fault(rx_ovf));

        // link-side faults (a record arriving with the RX FIFO full), synchronised into clk_sm
        reg flt_lk;
        always @(posedge clk_link or negedge rst_link_n)
            if (!rst_link_n) flt_lk <= 1'b0;
            else if ((lk_rx_v && !rx_in_rdy) || rx_ovf) flt_lk <= 1'b1;
        reg [SYNC-1:0] flt_sync;
        always @(posedge clk_sm or negedge rst_sm_n)
            if (!rst_sm_n) flt_sync <= {SYNC{1'b0}};
            else flt_sync <= {flt_sync[SYNC-2:0], flt_lk};
        assign coll_fault = flt_sm || flt_sync[SYNC-1] || tx_ovf;
    end else begin : g_off
        assign coll_req_rdy  = 1'b0;
        assign coll_rsp_v    = 1'b0;
        assign coll_rsp_data = {NL*32{1'b0}};
        assign coll_fault    = 1'b0;
        assign lk_tx_v       = 1'b0;
        assign lk_tx_rec     = {PW{1'b0}};
        /* verilator lint_off UNUSED */
        wire unused_off = &{1'b0, clk_sm, rst_sm_n, coll_req_v, coll_mode, coll_count, coll_data, coll_rsp_rdy,
                            clk_link, rst_link_n, lk_rx_v, lk_rx_rec};
        /* verilator lint_on UNUSED */
    end endgenerate
endmodule
