// Native full-payload wrapper; no generated PLL outputs and no packed proxy die-port aliases.
module ot_hbm_collective_die_entry #(
    parameter integer PACKET_SRAM = 0, // opt-in; queue II3, token composition pending
    parameter integer ENABLE = 0,
    parameter integer OWNER_REDUCER = 0, // default original parent
    parameter integer SLOTREG = 1,
    parameter integer OWNER_BANKED_HALF = 0, // default off; sender/receiver credits
    parameter integer OWNER_TRUE_CREDIT = 0, TC_FWD = 7, TC_RET = 7, // internal candidate; actual physical hops unqualified
    parameter integer OWNER_HUB_QAW = 6,
    parameter integer NC     = 8,
    parameter integer NOG    = 8,
    parameter integer PFMAX  = 64,
    parameter integer LANES  = 16,
    parameter integer BF16   = 1,
    parameter integer NPT    = 8,
    parameter integer INJ    = 2,
    parameter integer DEL    = 4,
    parameter integer HUBW   = 35,
    parameter integer WSTG   = 14,
    parameter integer BITS_X100 = 72000,
    parameter integer PWB    = 545,
    parameter integer RXAW   = 8,
    parameter integer QAW    = 6,
    parameter integer TXAW   = 6,
    parameter integer SWCRED = 256,
    parameter integer LAT    = 7,
    parameter integer FW     = 32 * LANES,
    parameter integer PWT    = FW + 33
) (
    input  wire                 clk_stream,
    input  wire                 por_stream,
    input  wire                 clk_link,            // this die's PHY (serializer) clock
    input  wire                 por_link,
    input  wire [7:0]           rank,
    input wire [63:0] context_operation, input wire [31:0] context_phase,
    output wire endpoint_rearm_ready, endpoint_quiet_core, endpoint_quiet_phy,
    input  wire [15:0]          pf,              // flits per contributor this collective (runtime)
    input  wire                 go,
    output wire [INJ*16-1:0]    inj_idx,
    output wire [INJ-1:0]       inj_rd,
    input  wire [INJ*FW-1:0]    inj_data,
    // switch side, PHY clock: one flit a clk_link at most per port, after the serializer
    output wire [NPT-1:0]       ph_tx_v,
    output wire [NPT*PWT-1:0]   ph_tx_flit,
    input  wire [NPT-1:0]       sw_cr_ret,       // switch ingress credit return (core clock)
    input  wire [NPT-1:0]       ph_rx_v,         // from the switch egress (PHY clock)
    input  wire [NPT*PWT-1:0]   ph_rx_flit,
    output wire [NPT-1:0]       rx_credit,       // receive-buffer pop (core clock) -> switch egress credit
    output wire [DEL-1:0]       del_valid,
    output wire [DEL*PWT-1:0]   del_flit,
    output wire                 fault,
    output wire [31:0]          stat_credit_stall
);
    wire rst_n, prst_n;
    ot_hbm_collective_reset_entry #(.ENABLE(ENABLE)) u_reset (.clk_stream(clk_stream), .clk_link(clk_link), .por_stream(por_stream), .por_link(por_link), .rst_n(rst_n), .prst_n(prst_n));
    ot_hbm_collective_full_candidate #(
        .PACKET_SRAM(PACKET_SRAM),
        .ENABLE(ENABLE),
        .OWNER_REDUCER(OWNER_REDUCER),
        .SLOTREG(SLOTREG),
        .OWNER_BANKED_HALF(OWNER_BANKED_HALF),
        .OWNER_TRUE_CREDIT(OWNER_TRUE_CREDIT),
        .TC_FWD(TC_FWD),
        .TC_RET(TC_RET),
        .OWNER_HUB_QAW(OWNER_HUB_QAW),
        .NC(NC),
        .NOG(NOG),
        .PFMAX(PFMAX),
        .LANES(LANES),
        .BF16(BF16),
        .NPT(NPT),
        .INJ(INJ),
        .DEL(DEL),
        .HUBW(HUBW),
        .WSTG(WSTG),
        .BITS_X100(BITS_X100),
        .PWB(PWB),
        .RXAW(RXAW),
        .QAW(QAW),
        .TXAW(TXAW),
        .SWCRED(SWCRED),
        .LAT(LAT),
        .FW(FW),
        .PWT(PWT)
    ) u_collective (
        .clk(clk_stream),
        .rst_n(rst_n),
        .pclk(clk_link),
        .prst_n(prst_n),
        .rank(rank),
        .context_operation(context_operation),
        .context_phase(context_phase),
        .endpoint_rearm_ready(endpoint_rearm_ready),
        .endpoint_quiet_core(endpoint_quiet_core),
        .endpoint_quiet_phy(endpoint_quiet_phy),
        .pf(pf),
        .go(go),
        .inj_idx(inj_idx),
        .inj_rd(inj_rd),
        .inj_data(inj_data),
        .ph_tx_v(ph_tx_v),
        .ph_tx_flit(ph_tx_flit),
        .sw_cr_ret(sw_cr_ret),
        .ph_rx_v(ph_rx_v),
        .ph_rx_flit(ph_rx_flit),
        .rx_credit(rx_credit),
        .del_valid(del_valid),
        .del_flit(del_flit),
        .fault(fault),
        .stat_credit_stall(stat_credit_stall)
    );
endmodule
