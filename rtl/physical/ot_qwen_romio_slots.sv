`timescale 1ns/1ps
// Qwen ROM TP8 die (track B): ROM-side IO masters of contract v3 (results/arch/hier_contract_1012/qwen_rom_tp8.json).
// qfd_io_serdes (3 x, slot 2,557.848 x 1,563.816) and qfd_io_ucie (1 x, 6,394.872 x 1,563.816) are CLUSTERS: the slot is
// the PHY-sized frame (licensed PHY abstract, physical/qwen_missing_phy), the routed logic is one small link adapter.
//
//   qfd_link_adp512   the hardened M5 leaf child of BOTH masters (hardened once, replicated): WIRING ONLY around
//                     ot_qfd_link_adapter #(W=1024, RXD=512, SRAM=1, PINREG=1) (body closed TT +6.61 / FF +16.92 at
//                     600.048^2 as qfd_io_serdes_adapter_rxd512_pin-073694e6b, M8-era layers, other cell name).
//                     No logic, no flop is added or removed.  Every port is a flop at its pin in the body: c_* captured
//                     (ci_v / ci_d), c_cr / r_v / r_d (PINREG) / tx_v / tx_flit / fault launched from flops, rx_* and
//                     tx_up captured (rq_v / rq_f / up_q), r_cr feeds the o_cred counter only.
//                     237.6 x 583.2, 8 SRAMs in one column.  Faces: die bus c_* / r_* S (toward the slot's c / r pins), PHY FDI tx_* / rx_* N.
//                     UCIe uses the same child (the abstract's RXD = 32 flop buffer is 32 k flops on one root: over
//                     the 15 k clock rule; with RXD = 512 in SRAM both links share one view and one flit width 1,043).
//
// MUT (bench mutant only, never synthesized with MUT != 0): the body's extra link credit (far-buffer overrun).
module qfd_link_adp512 #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          c_v,
    input  wire [1023:0] c_d,
    output wire          c_cr,
    output wire          r_v,
    output wire [1023:0] r_d,
    input  wire          r_cr,
    input  wire          tx_up,
    output wire          tx_v,
    output wire [1042:0] tx_flit,
    input  wire          rx_v,
    input  wire [1042:0] rx_flit,
    output wire          fault
);
    ot_qfd_link_adapter #(.W(1024), .RXD(512), .SRAM(1), .PINREG(1), .NG(8), .MUT(MUT)) u_body (
        .clk(ck), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .c_cr(c_cr), .r_v(r_v), .r_d(r_d), .r_cr(r_cr),
        .tx_up(tx_up), .tx_v(tx_v), .tx_flit(tx_flit), .rx_v(rx_v), .rx_flit(rx_flit), .fault(fault));
endmodule
