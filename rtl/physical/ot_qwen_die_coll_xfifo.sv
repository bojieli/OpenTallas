`timescale 1ns/1ps
// sys-takeover 2026-10-09 (registry qfd_native_collective_binding): the Qwen ROM die's production collective local port
// between the sequencer (ckd) and the collective engine ot_rom_oneshot_die_m (ck, r21 master qfd_io_collective).
//   sq: sequencer -> engine, the full engine input word {tag32, mode, last, data512} (WSQ = 546) + valid, credits
//       (the engine's in_cr drives o_seq_coll_cr; its IB = 4 = this channel's OCRED)
//   cq: engine -> sequencer, the engine's push output {err, rank2, last, data512} (WCQ = 516) + valid; credits from the
//       sequencer (o_coll_seq_cr, one per returned word it consumes)
// The engine output has no back-pressure, so a ckd-side credit gate hands a forward credit to the sequencer only while
// the return path (cq receive buffer CQ_IB + async FIFO CQ_AD) can hold every result that word can produce: N for an
// all-gather word, 1 for an all-reduce word (N - 1 refunded when the accepted word is a reduce, read from its mode bit
// MB).  The sequencer keeps its 4 initial forward credits (pre-reserved at reset).  Pins are registered on both faces
// (ot_qwen_die_cdc_ch); no ready crosses a block face.  Instantiated by ot_qwen_die_io_xfifo NCOLL = 1, or standalone.
module ot_qwen_die_coll_xfifo #(
    parameter integer WSQ = 546,
    parameter integer WCQ = 516,
    parameter integer N = 4,
    parameter integer MB = 513,
    parameter integer CQ_AD = 64,
    parameter integer PIPE = 0,
    // sys-takeover 2026-10-09 lever (CR / ENG_IB / LCR, defaults = the original 4 / 4 / 4): the AR word rate across the
    // CDC is credit-bound (4 credits per ~8-edge round trip on every hop: 256-word AR 436 vs 296 engine-alone cycles).
    //   CR     sequencer forward credits = sq receive buffer slots (IBUF), sq async FIFO = max(8, 2 CR)
    //   ENG_IB engine input buffer / sq downstream credits (ot_rom_oneshot_die_m IB)
    //   LCR    sequencer landing slots = cq downstream credits
    parameter integer CR = 4,
    parameter integer ENG_IB = 4,
    parameter integer LCR = 4,
    // el1011-q-coll 2026-10-11 (owner easiest-deterministic-fix rule): HDLI / HDLO HB4xp67 hold-delay cells per bit on every
    // data / valid / credit input (ahead of its pin station) and every output (after its launching flop), ot_hdly,
    // dont_touch from PRE_FLOORPLAN (physical/qwen_die_masters/hdly_dont_touch.tcl).  Identity in function; 0 / 0 =
    // the unchanged block.  The routed l8 misses are FF hold on the IO class only (a: outputs -2.9 ps, b: outputs -13.1 /
    // inputs -6.5) with TT setup room on the same ports (inputs +205, outputs +146).
    parameter integer HDLI = 0,
    parameter integer HDLO = 0,
    // MEMM = 1 (el1011-q-coll 2026-10-11, textbook class 1): both CDC FIFO bodies (sq 16 x 546, cq 64 x 516) are dual-clock
    // 1R1W macros instead of ~41k flops on the ck / ckd roots; needs PIPE = 2.
    parameter integer MEMM = 0,
    parameter integer SQ_IBMEM = 0,
    parameter integer WR_FREE = 0
) (
    input  wire ck, input wire ckd, input wire rst_n,
    input  wire i_seq_coll_v,  input  wire [WSQ-1:0] i_seq_coll,  output wire i_seq_coll_cr,
    output wire o_seq_coll_v,  output wire [WSQ-1:0] o_seq_coll,  input  wire o_seq_coll_cr,
    input  wire i_coll_seq_v,  input  wire [WCQ-1:0] i_coll_seq,
    output wire o_coll_seq_v,  output wire [WCQ-1:0] o_coll_seq,  input  wire o_coll_seq_cr,
    output wire fault_ck, output wire fault_ckd
);
    wire x_i_seq_coll_v, x_o_seq_coll_cr, x_i_coll_seq_v, x_o_coll_seq_cr;
    wire [WSQ-1:0] x_i_seq_coll; wire [WCQ-1:0] x_i_coll_seq;
    wire x_i_seq_coll_cr, x_o_seq_coll_v, x_o_coll_seq_v, x_fault_ck, x_fault_ckd;
    wire [WSQ-1:0] x_o_seq_coll; wire [WCQ-1:0] x_o_coll_seq;
    ot_hdly #(.W(WSQ + 1), .N(HDLI)) u_hdly_isq (.a({i_seq_coll_v, i_seq_coll}), .y({x_i_seq_coll_v, x_i_seq_coll}));
    ot_hdly #(.W(WCQ + 1), .N(HDLI)) u_hdly_icq (.a({i_coll_seq_v, i_coll_seq}), .y({x_i_coll_seq_v, x_i_coll_seq}));
    ot_hdly #(.W(2), .N(HDLI)) u_hdly_icr (.a({o_seq_coll_cr, o_coll_seq_cr}), .y({x_o_seq_coll_cr, x_o_coll_seq_cr}));
    ot_hdly #(.W(WSQ + 1), .N(HDLO)) u_hdly_osq (.a({x_o_seq_coll_v, x_o_seq_coll}), .y({o_seq_coll_v, o_seq_coll}));
    ot_hdly #(.W(WCQ + 1), .N(HDLO)) u_hdly_ocq (.a({x_o_coll_seq_v, x_o_coll_seq}), .y({o_coll_seq_v, o_coll_seq}));
    ot_hdly #(.W(3), .N(HDLO)) u_hdly_octl (.a({x_i_seq_coll_cr, x_fault_ck, x_fault_ckd}), .y({i_seq_coll_cr, fault_ck, fault_ckd}));
    localparam integer CQ_IB = 4;
    localparam integer RRES = CQ_IB + CQ_AD;              // return words the path holds without overflow
    wire sq_icr, wf_sq, rf_sq, wf_cq, rf_cq;
    ot_qwen_die_cdc_ch #(.W(WSQ), .PIPE(PIPE), .MEMM(MEMM), .IBMEM(SQ_IBMEM), .WR_FREE(WR_FREE), .IBUF(CR), .OCRED(ENG_IB), .AD((2 * CR > 8) ? 2 * CR : 8)) u_sq (.wclk(ckd), .wrst_n(rst_n), .i_v(x_i_seq_coll_v), .i_d(x_i_seq_coll),
        .i_cr(sq_icr), .w_fault(wf_sq), .rclk(ck), .rrst_n(rst_n), .o_v(x_o_seq_coll_v), .o_d(x_o_seq_coll),
        .o_cr(x_o_seq_coll_cr), .r_fault(rf_sq));
    ot_qwen_die_cdc_ch #(.W(WCQ), .PIPE(PIPE), .MEMM(MEMM), .WR_FREE(WR_FREE), .IBUF(CQ_IB), .OCRED(LCR), .AD(CQ_AD)) u_cq (.wclk(ck), .wrst_n(rst_n), .i_v(x_i_coll_seq_v),
        .i_d(x_i_coll_seq), .i_cr(), .w_fault(wf_cq), .rclk(ckd), .rrst_n(rst_n), .o_v(x_o_coll_seq_v), .o_d(x_o_coll_seq),
        .o_cr(x_o_coll_seq_cr), .r_fault(rf_cq));
    // ckd credit gate (pins registered first: refunds and releases land one edge late, which is conservative)
    wire grs_n;
    ot_reset_sync u_grs (.clk(ckd), .async_rst_n(rst_n), .sync_rst_n(grs_n));
    reg red_q, ocr_q, gcr_q, gf_q;
`ifdef OT_NCOLL_MUT_NARROW_RR
    localparam integer RRW = 8; // negative control: native RRES260 truncates at256
`else
    localparam integer RRW = $clog2(RRES + 1);
`endif
    reg [RRW-1:0] rr;                                         // return words not yet reserved
    reg [5:0] pend;                                       // forward credits withheld for want of return space
    wire [5:0] avail = pend + {5'b0, sq_icr};
`ifdef OT_NCOLL_MUT_NOREFUND_CHECK
    wire       grant = (avail != 0);                      // mutant: forward credits ignore the return reservation
`else
    wire       grant = (avail != 0) && (rr >= N);
`endif
    wire [RRW-1:0] rr_n  = rr + (red_q ? N - 1 : 0) + {{(RRW-1){1'b0}}, ocr_q} - (grant ? N : 0);
    always @(posedge ckd or negedge grs_n)
        if (!grs_n) begin red_q <= 1'b0; ocr_q <= 1'b0; gcr_q <= 1'b0; gf_q <= 1'b0; rr <= RRES - CR * N; pend <= 6'd0; end
        else begin
            // a reservation is released when its word leaves the cq FIFO for the sequencer's landing buffer (x_o_coll_seq_v:
            // the word then sits in a slot the sequencer's own OCRED credits cover)
            red_q <= x_i_seq_coll_v && !x_i_seq_coll[MB]; ocr_q <= x_o_coll_seq_v;
            gcr_q <= grant; pend <= avail - {5'b0, grant}; rr <= rr_n;
            gf_q <= gf_q | (rr_n > RRES);
        end
    assign x_i_seq_coll_cr = gcr_q;
    reg f_ck, f_ckd;
    always @(posedge ck)  f_ck  <= rf_sq | wf_cq;
    always @(posedge ckd) f_ckd <= wf_sq | rf_cq | gf_q;
    assign x_fault_ck = f_ck; assign x_fault_ckd = f_ckd;
    initial if (MEMM != 0 && PIPE < 2) $fatal(1, "coll_xfifo: MEMM needs PIPE = 2");
    initial if (RRES < CR * N) $fatal(1, "coll_xfifo: return reservation below the sequencer's initial forward credits");
endmodule
