`timescale 1ns/1ps
// HBM-UCIE8 10-20 (DRIVE-HBM): ot_pdie_ucie_col_flat, the WIRES-ONLY flat parent of the HBM host UCIe column (child
// instances and wires only) from which tools/landed_parent/lp.py generates the landed column ot_pdie_ucie_col
// (spec tools/landed_parent/specs/ot_pdie_ucie_col.json; kit physical/ref_tile/hbm_pdie_ucie_col).  The HBM GEN2e4 die
// binds one ot_pdie_ucie (host_N, the host UCIe-A link); the column replaces it with the method of the S81 SerDes column
// lp6 (claude/s81-serdes6-1020 41cccbc13): PMA tx/rx hard abstracts, dual-clock SRAM rate matcher, regional clocks/resets.
// Function = ot_pdie_ucie (rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv), same pads, no FEC (UCIe adapter CRC/retry is the
// link_ep above):
//   TX (core clk):     tx face reg u_txf + live flag u_live_t -> analog PMA TX u_ptx: pads pma_tx[512:0] = {valid, beat}
//   RX (pma_rck):      analog PMA RX u_prx -> output reg u_prr -> rate matcher write side (u_rm wclk) + SRAM write port (u_rmm wclk)
//   CDC (pma_rck is the far die's forwarded clock, NOT the core PLL): the ONLY rck -> clk crossings are the gray-pointer
//                      rate matcher u_rm (ot_s81_rate_match_sr, same function as the closed s81lk_rate_match tile; elastic:
//                      deletes IDLE beats) with its dual-clock SRAM u_rmm, and the 2-flop status synchroniser u_sts.
// Clock ports clk / pma_rck are replaced by lp.py with one port per region; rst is landed per region by the lp regional
// reset ports (2 registered stages on the region clock).  HBM-UCIE9 10-21 (ucie2 gate: one ck_core root over the tx AND rx
// pin groups, boundary spread 88.8 TT / 107.2 FF): clk is split into two regional roots that share NO net -- ck_tx (tx face
// reg u_txf, live flag, PMA TX u_ptx) and ck_rx (rate-matcher read side, SRAM read port, status, rx/st out regs) -- so no
// landing is needed between them; pma_rck -> ck_rck (PMA RX, its output register u_prr, rate-matcher write side).
module ot_pdie_ucie_col_flat (
    input  wire          clk,
    input  wire          pma_rck,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [512:0]  pma_tx,
    output wire          pma_tck,
    input  wire [512:0]  pma_rx
);
    // ---- transmit
    wire [511:0] tx_f; wire t_live;
    ot_pl_pad #(.W(512), .N(1)) u_txf (.ck(clk), .d(tx), .q(tx_f));
    ot_s81_col_live u_live_t (.clk(clk), .rst_n(rst), .q(t_live));
    ot_ucie_pma_txm u_ptx (.ck(clk), .d({t_live, tx_f}), .pma_tx(pma_tx), .pma_tck(pma_tck));
    // ---- receive
    wire [512:0] r_q, r_d;
    ot_ucie_pma_rxm u_prx (.pma_rck(pma_rck), .pma_rx(pma_rx), .q(r_q));
    // HBM-UCIE9 10-21: PMA RX output register in the rck region (ucie2 gate: u_prx/q -> u_rm comb -> u_rmm/w_ce_in was a
    // macro->macro single-cycle path, -306.7 ps): every rate-matcher / SRAM-write / status cone now starts at a flop beside
    // the rxm q face.  +1 pma_rck edge on RX, ahead of the elastic rate matcher (priced: lp record / kit README).
    ot_pl_pad #(.W(513), .N(1)) u_prr (.ck(pma_rck), .d(r_q), .q(r_d));
    // ---- CDC children (rck -> clk)
    wire rm_flt, m_wce, m_rce; wire [3:0] m_waddr, m_raddr; wire [545:0] m_wd, m_wmask, m_rd;
    ot_ucie_rate_match_pf u_rm (.wclk(pma_rck), .wrst_n(rst), .w_v(r_d[512]), .w_d(r_d[511:0]), .rclk(clk), .rrst_n(rst),
        .r_d(rx), .fault(rm_flt), .m_wce(m_wce), .m_waddr(m_waddr), .m_wd(m_wd), .m_wmask(m_wmask), .m_rce(m_rce),
        .m_raddr(m_raddr), .m_rd(m_rd));
    ot_sram_1r1w2c_16x546_m1 u_rmm (.wclk(pma_rck), .rclk(clk), .r_ce_in(m_rce), .r_addr_in(m_raddr), .rd_out(m_rd),
        .w_ce_in(m_wce), .w_addr_in(m_waddr), .wd_in(m_wd), .w_mask_in(m_wmask));
    ot_ucie_col_sts u_sts (.ck_r(pma_rck), .rst_r_n(rst), .r_v(r_d[512]), .ck_t(clk), .rst_t_n(rst), .rm_flt(rm_flt),
        .st(st));
endmodule
