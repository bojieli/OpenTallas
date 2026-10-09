`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B ROM die IO-band link adapter (qwen-missing 2026-10-07): the routed digital logic of die masters
// qfd_io_ucie and qfd_io_serdes, between the die bus (the io_xfifo / collective relays: valid + W-bit word +
// credit pulse, the r21 interface rule "no same-cycle cross-block handshake") and a PHY hard macro
// (ot_qfd_ucie_x64_phy / ot_qfd_serdes_112g_x12, abstracts in physical/qwen_missing_phy: LEF + SS/TT/FF LIB with
// published area / latency, ASSUMED where no figure is published -- see their README).
//
//   die TX face   c_v / c_d captured at the pin; IBUF-word receive buffer; c_cr = one registered credit pulse per word
//                 taken out of it (the xfifo sender starts with IBUF credits).
//   link TX       a flit {payload valid, payload W, credit return CRW, sequence 8} is launched from flops to the PHY's
//                 FDI each cycle the link is up (tx_up, a slow status captured at the macro pin): a payload goes only
//                 with a link credit in hand (the far adapter's RXD-word receive buffer); every flit carries the
//                 count of receive-buffer words this side has freed since the last flit (piggy-backed credit return).
//   link RX       the PHY's FDI flit is captured by a flop at the macro pins (no logic before it); a payload is
//                 pushed into the RXD-word receive buffer, the credit field adds to the TX link credits, and the
//                 sequence number is checked (a lost / repeated flit is a fault: the PHY's D2D adapter / FEC owns
//                 retry, a sequence gap here means it failed).
//   die RX face   r_v / r_d launched from flops, one word per r_cr credit (OCRED initial credits).
//   faults        sticky, flop-launched: die-face overrun, link receive-buffer overrun, sequence error, credit
//                 overflow.
// Order and values are preserved exactly; latency is not cycle-fixed (credit flow control end to end).
//
// gaps-design 2026-10-08 (link at line rate): with RXD = 128 the SerDes link (223 FDI cycles one way, credit round trip
// ~460 cycles) ran at ~28 % of line rate (credit-starved: RXD / RTT).  The receive buffer is now RXD = 512 words held in
// SRAM (SRAM = 1: 8 x ot_sram_1r1w_512x128_m4_r2c2 through ot_s81ph_mem1r1w, registered read) with a capture flop at
// the macro outputs (no logic before it) and a SKD-entry register skid in front of the die RX face; a word's link
// credit returns when it is read out of the SRAM (its skid slot is reserved before the read issues, so the skid cannot
// overrun).  Receive latency +3 FDI cycles (registered read, macro-output capture, skid); rate sweep in
// rtl/test/tb_qfd_link_adapter.sv (RATE = 1).  SRAM = 0 keeps a flop array of the same cycle behaviour (benches).
// ---------------------------------------------------------------------------
module ot_qfd_link_adapter #(
    parameter integer W = 1024,
    parameter integer IBUF = 4,          // die-face receive buffer (credits given to the die-bus sender)
    parameter integer OCRED = 4,         // credits for the die-bus receiver (xfifo RX side)
    parameter integer RXD = 32,          // link receive buffer (credits given to the far adapter): >= link RTT
    parameter integer SRAM = 0,          // 1: receive buffer in SRAM macros (RXD <= 512)
    parameter integer SKD = 4,           // die-RX skid entries (>= read pipeline depth 2 + 1 for full rate)
    parameter integer PINREG = 0,        // 1: r_v / r_d leave through one more register placed at the die-RX pins (+1 cycle a word;
                                         //    the die receiver gets one more credit, OCRED + 1, so the longer credit loop keeps full rate)
    parameter integer MUT = 0            // bench mutant: 1 = one extra link credit (overruns the far buffer)
) (
    input  wire          clk,
    input  wire          rst_n,
    // die TX face
    input  wire          c_v,
    input  wire [W-1:0]  c_d,
    output reg           c_cr,
    // die RX face
    output wire          r_v,
    output wire [W-1:0]  r_d,
    input  wire          r_cr,
    // PHY FDI (hard macro)
    input  wire          tx_up,
    output reg           tx_v,
    output reg  [W+CRW+8:0] tx_flit,     // {payload valid, payload, credit return, sequence}
    input  wire          rx_v,
    input  wire [W+CRW+8:0] rx_flit,
    output reg           fault
);
    localparam integer CRW = $clog2(RXD + 1);
    localparam integer IA = (IBUF <= 2) ? 1 : $clog2(IBUF);
    localparam integer RA = $clog2(RXD);
    localparam integer CB = $clog2(RXD + 2) + 1;
    localparam integer OCR = OCRED + ((PINREG != 0) ? 1 : 0);
    localparam integer OB = $clog2(OCR + 1) + 1;
    reg          rr_v;                   // die-RX word register (the pin register when PINREG = 0)
    reg [W-1:0]  rr_d;
    // ---- reset copy ----
    reg rs0, rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    // ---- die TX face: pin capture + IBUF ----
    reg          ci_v;
    reg [W-1:0]  ci_d;
    always @(posedge clk) ci_d <= c_d;
    always @(posedge clk or negedge rs) if (!rs) ci_v <= 1'b0; else ci_v <= c_v;
    reg [W-1:0]  ib [0:IBUF-1];
    reg [IA:0]   ib_n;
    reg [IA-1:0] ib_wp, ib_rp;
    reg          f_die_ovr, f_link_ovr, f_seq, f_cred;
    // ---- link credits / TX ----
    reg [CB-1:0] tx_cred;                // far receive-buffer words we may still send
    reg [CRW-1:0] cr_owed;               // receive-buffer words freed here, not yet returned
    reg [7:0]    tx_seq, rx_seq;
    reg          up_q;                   // macro status captured at the pin
    always @(posedge clk or negedge rs) if (!rs) up_q <= 1'b0; else up_q <= tx_up;
    wire send = up_q && (ib_n != 0) && (tx_cred != 0);
    wire flit = up_q && (send || cr_owed != 0);
    // ---- link RX: macro capture flops, receive buffer ----
    reg          rq_v;
    reg [W+CRW+8:0] rq_f;
    always @(posedge clk) rq_f <= rx_flit;
    always @(posedge clk or negedge rs) if (!rs) rq_v <= 1'b0; else rq_v <= rx_v;
    wire          rx_pay_v = rq_v && rq_f[W+CRW+8];
    wire [W-1:0]  rx_pay = rq_f[CRW+8 +: W];
    wire [CRW-1:0] rx_cr = rq_f[8 +: CRW];
    wire [7:0]    rx_sq = rq_f[7:0];
    reg [RA:0]   rb_n;                   // words written to the receive buffer and not yet read out
    reg [RA-1:0] rb_wp, rb_rp;
    reg [OB-1:0] o_cred;
    // receive buffer: registered-read 1R1W array; a read issues only with a skid slot reserved
    localparam integer SA = (SKD <= 2) ? 1 : $clog2(SKD);
    reg [SA:0]   sk_res;                 // skid slots reserved: reads in flight + words held
    wire rd_go = (rb_n != 0) && (sk_res != SKD);
    wire [W-1:0] rb_q;
    ot_s81ph_mem1r1w #(.W(W), .DEPTH(RXD), .SRAM(SRAM)) u_rb (.clk(clk), .we(rx_pay_v), .wa(rb_wp), .wd(rx_pay),
        .re(rd_go), .ra(rb_rp), .q(rb_q));
    reg          rd_v0, rd_v1;           // read issued / word in the capture flop
    reg [W-1:0]  rb_cap;                 // capture flop at the macro outputs (no logic before it)
    always @(posedge clk) rb_cap <= rb_q;
    reg [W-1:0]  sk [0:SKD-1];
    reg [SA:0]   sk_n;
    reg [SA-1:0] sk_wp, sk_rp;
    wire pop_rb = (sk_n != 0) && (o_cred != 0);
    always @(posedge clk) begin
        if (ci_v) ib[ib_wp] <= ci_d;
        if (rd_v1) sk[sk_wp] <= rb_cap;
        if (send) tx_flit[CRW+8 +: W] <= ib[ib_rp];
        tx_flit[W+CRW+8] <= send;
        tx_flit[8 +: CRW] <= flit ? cr_owed : {CRW{1'b0}};
        tx_flit[7:0] <= tx_seq;
        if (pop_rb) rr_d <= sk[sk_rp];
    end
    always @(posedge clk or negedge rs) begin
        if (!rs) begin
            ib_n <= 0; ib_wp <= 0; ib_rp <= 0; c_cr <= 1'b0; tx_v <= 1'b0; tx_seq <= 0; rx_seq <= 0;
            tx_cred <= RXD + ((MUT != 0) ? 1 : 0); cr_owed <= 0;
            rb_n <= 0; rb_wp <= 0; rb_rp <= 0; o_cred <= OCR; rr_v <= 1'b0;
            sk_res <= 0; sk_n <= 0; sk_wp <= 0; sk_rp <= 0; rd_v0 <= 1'b0; rd_v1 <= 1'b0;
            f_die_ovr <= 1'b0; f_link_ovr <= 1'b0; f_seq <= 1'b0; f_cred <= 1'b0; fault <= 1'b0;
        end else begin
            // die TX face
            if (ci_v) ib_wp <= (ib_wp == IBUF - 1) ? 0 : ib_wp + 1'b1;
            if (send) ib_rp <= (ib_rp == IBUF - 1) ? 0 : ib_rp + 1'b1;
            ib_n <= ib_n + (ci_v ? 1'b1 : 1'b0) - (send ? 1'b1 : 1'b0);
            if (ci_v && ib_n == IBUF && !send) f_die_ovr <= 1'b1;
            c_cr <= send;
            // link TX: one flit a cycle while up; the credit field returns everything owed so far
            tx_v <= flit;
            if (flit) tx_seq <= tx_seq + 1'b1;
            cr_owed <= (flit ? {CRW{1'b0}} : cr_owed) + (rd_go ? 1'b1 : 1'b0);   // the SRAM slot is free once read
            tx_cred <= tx_cred - (send ? 1'b1 : 1'b0) + (rq_v ? rx_cr : {CRW{1'b0}});
            if (rq_v && tx_cred + rx_cr > RXD + ((MUT != 0) ? 1 : 0)) f_cred <= 1'b1;
            // link RX
            if (rq_v) begin
                rx_seq <= rx_seq + 1'b1;
                if (rx_sq != rx_seq) f_seq <= 1'b1;
            end
            if (rx_pay_v) rb_wp <= (rb_wp == RXD - 1) ? 0 : rb_wp + 1'b1;
            if (rd_go) rb_rp <= (rb_rp == RXD - 1) ? 0 : rb_rp + 1'b1;
            rb_n <= rb_n + (rx_pay_v ? 1'b1 : 1'b0) - (rd_go ? 1'b1 : 1'b0);
            if (rx_pay_v && rb_n == RXD && !rd_go) f_link_ovr <= 1'b1;
            // read pipeline and skid
            rd_v0 <= rd_go;
            rd_v1 <= rd_v0;
            if (rd_v1) sk_wp <= (sk_wp == SKD - 1) ? 0 : sk_wp + 1'b1;
            if (pop_rb) sk_rp <= (sk_rp == SKD - 1) ? 0 : sk_rp + 1'b1;
            sk_n <= sk_n + (rd_v1 ? 1'b1 : 1'b0) - (pop_rb ? 1'b1 : 1'b0);
            sk_res <= sk_res + (rd_go ? 1'b1 : 1'b0) - (pop_rb ? 1'b1 : 1'b0);
            // die RX face
            rr_v <= pop_rb;
            o_cred <= o_cred - (pop_rb ? 1'b1 : 1'b0) + (r_cr ? 1'b1 : 1'b0);
            fault <= f_die_ovr | f_link_ovr | f_seq | f_cred;
        end
    end
    generate if (PINREG != 0) begin : g_pin
        reg          p_v;
        reg [W-1:0]  p_d;
        always @(posedge clk) p_d <= rr_d;
        always @(posedge clk or negedge rs) if (!rs) p_v <= 1'b0; else p_v <= rr_v;
        assign r_v = p_v; assign r_d = p_d;
    end else begin : g_nopin
        assign r_v = rr_v; assign r_d = rr_d;
    end endgenerate
endmodule
