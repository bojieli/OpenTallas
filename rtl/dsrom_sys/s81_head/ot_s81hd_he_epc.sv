// HEAD-92/H2 11-10 (COORD ruling: hd_host_e form H2): hard-core cut of the hd_host_e lane-1 link endpoint.
// ot_s81hd_he_epc = the lane reset relay tree u_rr + the endpoint u_ep of ot_s81ph_coll_lane_safe4_hd, moved one level
// down with the SAME parameters, instance names and wiring; pure hierarchy change (0 added cycles).  The parent
// ot_s81ph_coll_lane_safe4_hd instantiates it only under `define OT_HE_EPC (default = the original flat circuit).
// The parent keeps every rr leaf it used before: rr_lo = rr[R_LOC .. R_HEAD+HEAD_RL-1], rr_gb = rr[R_GB +: GB_RN].
module ot_s81hd_he_epc #(
    parameter integer CH_UCIE = 100,
    parameter integer CH_BOARD = 700,
    parameter integer IDLE_P = 1024,
    parameter integer REACH = 2,
    parameter integer RBL = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ch_b,
    input  wire          in_valid,
    output wire          in_ready,
    input  wire [551:0]  in_data,
    input  wire          in_last,
    output wire          out_valid,
    input  wire [2:0]    out_ready_v,
    output wire [551:0]  out_data,
    output wire          out_last,
    output wire          f_tx_v,
    output wire [594:0]  f_tx,
    input  wire          f_rx_v,
    input  wire [594:0]  f_rx,
    output wire          r_tx_v,
    output wire [52:0]   r_tx,
    input  wire          r_rx_v,
    input  wire [52:0]   r_rx,
    output wire          fault,
    output wire [7:0]    rr_lo,
    output wire [21:0]   rr_gb
);
    localparam integer FB = 69, CREDITS = 512, SEQW = 10;
    localparam integer W = FB * 8;
    localparam integer PNUM = FB * 3 * (IDLE_P - 1);
    localparam integer PDEN = 4 * IDLE_P;
    localparam integer HEAD_NS = (W + 1 + 15) / 16;
    localparam integer HEAD_RL = (HEAD_NS + 7) / 8;
    localparam integer MEM_NS = (W + 1 + 7) / 8, MEM_NA = (MEM_NS + 3) / 4, MEM_RST = 2 * (MEM_NS + MEM_NA);
`ifdef OT_COLL_NATIVE32
    localparam integer EP_RN = (REACH >= 2) ? 17 : 16, GB_RN = 22;
`else
    localparam integer EP_RN = (REACH >= 2) ? 13 : 12, GB_RN = 22;
`endif
    localparam integer R_LOC = 0, R_CRX = 1, R_CTX = 2, R_HEAD = 3, R_EP = R_HEAD + HEAD_RL, R_MEM = R_EP + EP_RN,
                       R_GB = R_MEM + MEM_RST, NREG = R_GB + GB_RN;
    wire [NREG-1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(NREG)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    assign rr_lo = rr[R_EP-1:0];
    assign rr_gb = rr[R_GB +: GB_RN];
    ot_s81ph_link_ep_safe4_hd #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(REACH != 0 ? 5 : 3), .CHANNEL_CYCLES(CH_UCIE), .CHANNEL_CYCLES_B(CH_BOARD),
        .CREDITS(CREDITS), .SEQW(SEQW), .PHY_NUM(PNUM), .PHY_DEN(PDEN), .SRAM(1), .PIPE(2), .RXPIPE(1), .TOREG(1), .MWR(1),
        .DNR(1), .OLDREAD(1), .RN(EP_RN), .ORN(3), .FCOPY(REACH != 0 ? 1 : 0), .WRL(REACH >= 2 ? 2 : 0), .RBL(RBL)) u_ep (
        .clk(clk), .rst_v(rr[R_EP +: EP_RN]), .mem_rst_n(rr[R_MEM +: MEM_RST]), .ch_b(ch_b),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready_v(out_ready_v), .out_data(out_data), .out_last(out_last),
        .f_tx_v(f_tx_v), .f_tx(f_tx), .f_rx_v(f_rx_v), .f_rx(f_rx), .r_tx_v(r_tx_v), .r_tx(r_tx), .r_rx_v(r_rx_v), .r_rx(r_rx),
        .credit_stalls(), .fault(fault), .fault_code(), .st_flits_tx(), .st_flits_rx_ok(), .st_crc_err(),
        .st_naks(), .st_replays(), .st_timeouts(), .st_retx_flits(), .st_max_replay_occ());
endmodule
