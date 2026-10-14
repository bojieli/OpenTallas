// Wires-only functional parent: EP, RGX source service, RGX sink service, own-flop status.
// Child leaf cuts/registered seams and actual die clock entries remain required before adoption.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hfd_coll_r25gq ([link] 2026-10-10, lead: ONE hfd_coll regeneration + ONE route): the R25GQ collective block body.
//   * ot_hgi_coll_ep: NPT 9 (one port per hfd_lk_ep link endpoint), SWCRED 32 (= the lk_ep TX queue: the ~24-edge die
//     credit loop at 0.75 flit / cycle; backlog waits in the port slices' SRAM qp / qr queues), RXAW 8 (the slices'
//     256-flit SRAM receive buffer = the far link's credits), PIPE 1, RGXHW 1.
//   * ot_hgi_coll_rgx_hbm (row source + list-fetch VM client) and ot_hgi_coll_rgx_snk (VM W2 sink + 2 HBM write lanes),
//     hgi-1010/c main e6b6497d9.
//   * link session: config word SESSION_W0 [23:0] (ot_hgi_cfg_rx), the same 24 b to every link (lk_session, registered).
//   * fault: endpoint | RGX sink | any link endpoint fault (registered); lk_status = {locked[8:0], fault[8:0]} for debug.
// Link order k = 0..8 = die buses llk_S0..S4, llk_N0..N3.
// ---------------------------------------------------------------------------
module ot_hfd_coll_body_cluster #(
    parameter integer NPT = 9,
    parameter integer SWCRED = 32,
    parameter integer RGX_LQ = 32,         // the VM W2 group's LQ (hfd_hgi_vm, b: 32)
    parameter integer SESSION_W0 = 47,     // config word of LINK_SESSION [23:0]
    parameter integer INJ = 2,
    parameter integer DEL = 4,
    parameter integer LANES = 16,
    parameter integer FW = 32 * LANES,
    parameter integer PWT = FW + 33
) (
    input wire [3:0] child_clk,
    input wire[NPT-1:0]port_clk,
    input wire[7:0]column_clk,
    input wire[3:0]park_clk_q,input wire park_fault_clk,
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [7:0]           rank,
    input  wire [15:0]          pf,
    input  wire                 go,
    output wire [INJ*16-1:0]    inj_idx,
    output wire [INJ-1:0]       inj_rd,
    input  wire [4*INJ*FW-1:0]  inj_q,
    output wire [DEL-1:0]       del_valid,
    output wire [DEL*PWT-1:0]   del_flit,
    output wire                  fault,
    output wire [31:0]          stat_credit_stall,
    input  wire [967:0]         hgi_rec,
    output wire [2:0]           hgi_ret,
    input  wire [39:0]          hgi_cfg,
    output wire [93:0]          hgi_rowfmt_o,
    input  wire [2:0]           hgi_rowfmt_i,
    output wire [79:0]          hgi_vmaddr,
    output wire [DEL*40-1:0]    hgi_del_obase,
    // link endpoints (hfd_lk_ep k on llk_*)
    output wire [NPT-1:0]       lk_tx_v,
    output wire [NPT*PWT-1:0]   lk_tx_flit,
    output wire [NPT-1:0]       lk_rx_credit,
    input  wire [NPT-1:0]       lk_rx_v,
    input  wire [NPT*PWT-1:0]   lk_rx_flit,
    input  wire [NPT-1:0]       lk_sw_cr,
    output wire  [NPT*24-1:0]    lk_session,
    input  wire [NPT-1:0]       lk_fault,
    input  wire [NPT-1:0]       lk_locked,
    output wire  [2*NPT-1:0]     lk_status,
    // RGX memory lanes (hgi_rgx die nets)
    output wire [75:0]          rgx_xq,
    input  wire [513:0]         rgx_xr,
    output wire [337:0]         rgx_vmq,
    input  wire [273:0]         rgx_vmr,
    output wire                 rgx_c_req,
    input  wire                 rgx_c_gnt,
    output wire [32*280-1:0]    rgx_c_q,
    input  wire [31:0]          rgx_c_cr,
    input  wire [31:0]          rgx_c_rsp,
    output wire [2*326-1:0]     rgx_xw,
    input  wire [1:0]           rgx_xwa
);
    wire ep_fault, snk_fault;
    wire rg_lq_v, rg_lq_rdy, rg_lr_v, rg_w_vm;
    wire [31:0] rg_lq_addr; wire [511:0] rg_lr_data, rg_hr_data;
    wire [1:0] rg_hq_v, rg_hq_rdy, rg_hr_v; wire [69:0] rg_hq_addr; wire [15:0] rg_hq_tag, rg_hr_tag;
    wire [DEL-1:0] rg_w_v, rg_w_rdy; wire [DEL*40-1:0] rg_w_addr; wire [DEL*FW-1:0] rg_w_data;
    ot_hgi_coll_ep_cluster #(.COLUMN_HARD(1),.NPT(NPT), .SWCRED(SWCRED), .RXAW(8), .QAW(7), .TXAW(3), .PIPE(1), .RGXHW(1), .RFMT(0),
                     .INJ(INJ), .DEL(DEL), .LANES(LANES)) u_ep (
        .column_clk(column_clk),.port_clk(port_clk),.park_clk_q(park_clk_q),.park_fault_clk(park_fault_clk),.clk(child_clk[0]), .rst_n(rst_n), .pclk(child_clk[0]), .prst_n(rst_n), .rank(rank), .pf(pf), .go(go),
        .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_q(inj_q),
        .ph_tx_v(lk_tx_v), .ph_tx_flit(lk_tx_flit), .sw_cr_ret(lk_sw_cr), .ph_rx_v(lk_rx_v), .ph_rx_flit(lk_rx_flit),
        .rx_credit(lk_rx_credit), .del_valid(del_valid), .del_flit(del_flit), .fault(ep_fault),
        .stat_credit_stall(stat_credit_stall), .hgi_rec(hgi_rec), .hgi_ret(hgi_ret), .hgi_cfg(hgi_cfg),
        .hgi_rowfmt_o(hgi_rowfmt_o), .hgi_rowfmt_i(hgi_rowfmt_i), .hgi_vmaddr(hgi_vmaddr), .hgi_del_obase(hgi_del_obase),
        .rg_lq_v(rg_lq_v), .rg_lq_rdy(rg_lq_rdy), .rg_lq_addr(rg_lq_addr), .rg_lr_v(rg_lr_v), .rg_lr_data(rg_lr_data),
        .rg_hq_v(rg_hq_v), .rg_hq_rdy(rg_hq_rdy), .rg_hq_addr(rg_hq_addr), .rg_hq_tag(rg_hq_tag),
        .rg_hr_v(rg_hr_v), .rg_hr_tag(rg_hr_tag), .rg_hr_data(rg_hr_data),
        .rg_w_v(rg_w_v), .rg_w_addr(rg_w_addr), .rg_w_vm(rg_w_vm), .rg_w_data(rg_w_data), .rg_w_rdy(rg_w_rdy));
    ot_hgi_coll_rgx_hbm u_rh (.clk(child_clk[1]), .rst_n(rst_n),
        .rg_hq_v(rg_hq_v), .rg_hq_rdy(rg_hq_rdy), .rg_hq_addr(rg_hq_addr), .rg_hq_tag(rg_hq_tag),
        .rg_hr_v(rg_hr_v), .rg_hr_tag(rg_hr_tag), .rg_hr_data(rg_hr_data),
        .rg_lq_v(rg_lq_v), .rg_lq_rdy(rg_lq_rdy), .rg_lq_addr(rg_lq_addr), .rg_lr_v(rg_lr_v), .rg_lr_data(rg_lr_data),
        .xq(rgx_xq), .xr(rgx_xr), .vmq(rgx_vmq), .vmr(rgx_vmr));
    ot_hgi_coll_rgx_snk #(.DEL(DEL), .FW(FW), .LQ(RGX_LQ)) u_rs (.clk(child_clk[2]), .rst_n(rst_n),
        .rg_w_v(rg_w_v), .rg_w_addr(rg_w_addr), .rg_w_vm(rg_w_vm), .rg_w_data(rg_w_data), .rg_w_rdy(rg_w_rdy),
        .c_req(rgx_c_req), .c_gnt(rgx_c_gnt), .c_q(rgx_c_q), .c_cr(rgx_c_cr), .c_rsp(rgx_c_rsp),
        .xw(rgx_xw), .xwa(rgx_xwa), .fault(snk_fault));
    ot_hfd_coll_status_leaf #(.NPT(NPT),.SESSION_W0(SESSION_W0))u_status(
      .clk(child_clk[3]),.rst_n(rst_n),.hgi_cfg(hgi_cfg),.ep_fault(ep_fault),.snk_fault(snk_fault),
      .lk_fault(lk_fault),.lk_locked(lk_locked),.lk_session(lk_session),.lk_status(lk_status),.fault(fault));
endmodule
