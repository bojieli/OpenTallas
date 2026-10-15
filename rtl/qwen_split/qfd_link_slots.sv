`timescale 1ns/1ps
// =====================================================================================================================
// Qwen3-8B TP8 split, COMPUTE die: die-name RTL of the link end and the clock / reset entry (compute-die lead r3,
// 2026-10-14; owner no-stub rule 08:05: every die instance binds to real RTL under its die name, every die net lands on
// a real port of the right width).  Contract: results/arch/qwen_split_compute_1014/CONTRACT.md section 4 and
// results/arch/qwen_split_1014/LINK.md (kvsys lead).
//
//   qfd_d2d_rom   the compute end of the die link = ot_qfd_split_romlink (ROM end ot_qkvd_rom_end + level-face codec)
//                 + ot_qkvd_d2d_llr (CRC-16 / go-back-N retry) toward the UCIe x64 PHY FDI (583-b PHY flit).
//                 Die faces: SU x3 / ea / eq, VM ar, ROM sequencer dc (sd 56 b levels) / dh (ds 187 b) / kvd (44 b
//                 posted), tree top pw (75 b), PHY FDI (abutted, no relay: C9 mirrors PHY + adapter).
//   qfd_ckbump    forwarded-clock / reset bump receiver (KV/system die PLL -> this die; mesochronous, no CDC)
//   qfd_rstsync   asynchronous assert / synchronous release of the forwarded reset in the link clock (d2d + PHY), and
//                 the synchronised copy forwarded to the die reset sequencer
//   qfd_rstseq    die reset sequencer: holds every domain in reset FLUSH cycles after release (the die data relays have
//                 no reset: their producers flush them, >= the longest relay chain) then releases in order
//                 io -> field -> spine -> tree top -> sequencer (the sequencer issues only into a released die)
// qfd_clkrx (one output per clock region of the build) is generated with the relays: tools/qwen_split/gen_relay_rtl.py.
// =====================================================================================================================

module qfd_d2d_rom #(
    parameter integer XS     = 64,      // x3 credits toward the KV die (>= 2 C_ST + 48, LINK.md)
    parameter integer OCR_AR = 64,      // ar credits at the VM face (>= 2 C_ST + 40)
    parameter integer RB_RES = 32,
    parameter integer FW     = 548,     // adapter flit
    parameter integer PW     = FW + 35, // PHY flit (llr header + CRC-16)
    parameter integer MUT    = 0        // bench mutant only: 1 = x3 tag bits 0 / 1 crossed (wrong die wiring) -- must FAIL
) (
    input  wire          ck,
    input  wire          rst_n,
    // SU: Q / KVN words out, embedding request out / rows back
    input  wire          x3_v,
    input  wire [511:0]  x3_d,
    input  wire [10:0]   x3_tag,
    output wire          x3_cr,
    input  wire          ea_v,
    input  wire          ea_kind,
    input  wire [23:0]   ea_addr,
    output wire          ea_cr,
    output wire          eq_v,
    output wire [511:0]  eq_d,
    // VM: attention result words
    output wire          ar_v,
    output wire [518:0]  ar_d,
    input  wire          ar_cr,
    // ROM sequencer (qfd_seq_su) and tree top (qfd_tt_ctlm)
    input  wire [55:0]   dc,             // sd levels -> KV/system-die stepper
    output wire [186:0]  dh,             // ds levels <- stepper
    output wire [74:0]   pw,             // pw levels / pulses -> tree top
    input  wire [43:0]   kvd,            // {v, kindk, pos 18, wbase 24} posted KV descriptor
    // UCIe x64 PHY FDI (abutted)
    input  wire          fdi_tx_up,
    output wire          fdi_tx_v,
    output wire [PW-1:0] fdi_tx_flit,
    input  wire          fdi_rx_v,
    input  wire [PW-1:0] fdi_rx_flit,
    output wire          fault,
    output wire [10:0]   fault_cause     // {llr 3, adapter 8}
);
    wire          a_up, a_txv, a_rxv;
    wire [FW-1:0] a_txf, a_rxf;
    wire          f_rl, f_llr;
    wire [7:0]    fc_rl;
    wire [2:0]    fc_llr;
    ot_qfd_split_romlink #(.XS(XS), .OCR_AR(OCR_AR), .RB_RES(RB_RES), .FW(FW)) u_rl (
        .clk(ck), .rst_n(rst_n),
        .x3_v(x3_v), .x3_d(x3_d), .x3_tag(MUT == 1 ? {x3_tag[10:2], x3_tag[0], x3_tag[1]} : x3_tag), .x3_cr(x3_cr),
        .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr),
        .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(ea_cr),
        .eq_v(eq_v), .eq_d(eq_d),
        .sd(dc), .kvd(kvd), .ds(dh), .pw(pw),
        .tx_up(a_up), .tx_v(a_txv), .tx_flit(a_txf), .rx_v(a_rxv), .rx_flit(a_rxf),
        .fault(f_rl), .fault_cause(fc_rl));
    ot_qkvd_d2d_llr #(.FW(FW), .PW(PW)) u_llr (
        .clk(ck), .rst_n(rst_n),
        .a_tx_up(a_up), .a_tx_v(a_txv), .a_tx_flit(a_txf), .a_rx_v(a_rxv), .a_rx_flit(a_rxf),
        .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_tx_flit(fdi_tx_flit), .p_rx_v(fdi_rx_v), .p_rx_flit(fdi_rx_flit),
        .fault(f_llr), .fault_cause(fc_llr));
    assign fault       = f_rl | f_llr;
    assign fault_cause = {fc_llr, fc_rl};
endmodule

// forwarded clock + reset bump receiver = HARD-MACRO MODEL (analog bump pair + receiver; port-bind --allow-model
// qfd_ckbump): the package-side forwarded clock / reset are not nets of this die.  Simulation behaviour: the 1.2 GHz
// forwarded clock and a reset that releases after RST_NS.
module qfd_ckbump #(parameter real HALF_NS = 0.41667, parameter real RST_NS = 20.0) (
    output reg pll_ck,
    output reg rs
);
    initial begin pll_ck = 1'b0; rs = 1'b0; #(RST_NS) rs = 1'b1; end
    always #(HALF_NS) pll_ck = ~pll_ck;
endmodule

// UCIe-A x64 PHY = HARD-MACRO MODEL (port-bind --allow-model ot_qkvd_ucie_x64_phy): exactly the abstract's die ports
// (clk, rst_n, FDI); the far die is not on this die's netlist, so the lanes end in the model (no received flits).
// PW = the 583-b llr PHY flit (kvsys LINK v1b).
module ot_qkvd_ucie_x64_phy #(parameter integer PW = 583) (
    input  wire          clk,
    input  wire          rst_n,
    output wire          tx_up,
    input  wire          tx_v,
    input  wire [PW-1:0] tx_flit,
    output wire          rx_v,
    output wire [PW-1:0] rx_flit
);
    wire          lv;
    wire [PW-1:0] lf;
    ot_qkvd_ucie_x64_phy_model #(.FW(PW)) u_m (.clk(clk), .rst_n(rst_n), .tx_up(tx_up), .tx_v(tx_v), .tx_flit(tx_flit),
        .rx_v(rx_v), .rx_flit(rx_flit), .link_v(lv), .link_flit(lf), .far_v(1'b0), .far_flit({PW{1'b0}}));
endmodule

module qfd_rstsync (
    input  wire ck,
    input  wire arst_n,
    output wire rso_d,                  // link end + PHY reset (link clock)
    output wire rso_f                   // synchronised release forwarded to the die reset sequencer
);
    (* async_reg = "true" *) reg [1:0] s;
    reg f;
    always @(posedge ck or negedge arst_n)
        if (!arst_n) begin s <= 2'b00; f <= 1'b0; end
        else begin s <= {s[0], 1'b1}; f <= s[1]; end
    assign rso_d = s[1];
    assign rso_f = f;
endmodule

module qfd_rstseq #(
    parameter integer FLUSH = 512,      // >= 2 x the longest die relay chain (C3: 149 stages) + margin
    parameter integer STEP  = 256       // edges between domain releases at the source: > the deepest domain reset
                                        // tree (C8 build: field 252, io 170, spine 122, tree top 48 cycles), so the
                                        // releases ARRIVE in order io -> field -> spine -> tree top -> sequencer
) (
    input  wire ck,
    input  wire rsi,                    // synchronised forwarded reset (qfd_rstsync rso_f), active low
    output reg  rso_io,
    output reg  rso_f,                  // tile field
    output reg  rso_s,                  // spine (SU, VM, slabs, constants)
    output reg  rso_ctlm,               // tree top
    output reg  rso_seq                 // ROM sequencer: last
);
    localparam integer CW = $clog2(FLUSH + 5 * STEP + 1);
    (* async_reg = "true" *) reg [1:0] s;
    reg [CW-1:0] n;
    always @(posedge ck or negedge rsi)
        if (!rsi) begin
            s <= 2'b00; n <= {CW{1'b0}};
            {rso_io, rso_f, rso_s, rso_ctlm, rso_seq} <= 5'b00000;
        end else begin
            s <= {s[0], 1'b1};
            if (s[1] && n != FLUSH + 4 * STEP) n <= n + 1'b1;
            rso_io   <= s[1] && n >= FLUSH;
            rso_f    <= s[1] && n >= FLUSH + STEP;
            rso_s    <= s[1] && n >= FLUSH + 2 * STEP;
            rso_ctlm <= s[1] && n >= FLUSH + 3 * STEP;
            rso_seq  <= s[1] && n >= FLUSH + 4 * STEP;
        end
endmodule
