`timescale 1ns/1ps
`default_nettype none
// HGI-1 collective block body (hgi-takeover 2026-10-09): the TU endpoint (ot_hbm_accel_tu_endpoint_psg, group sizes,
// GROUP_REDUCE_MCAST, done / fault handshake) driven either by the legacy config word {go, pf, rank} or by a normative
// record through ot_hgi_coll_record (whichever issued the last go owns the control fields), the static group size
// from the HGI config station bus (word 46), and the record's ROW_GATHER start fields / A-O bases leaving for the row
// formatter and the SU addressing.  The same logic as physical/hbm_accel_die_views/coll/rtl_hgi/hfd_coll.sv, as one
// module for the spec-generated wrapper (coll_hgi/rtl/spec.json).
module ot_hgi_coll_ep #(
    parameter integer NOG = 12,       // 12 x 8 = the 96-rank TU fabric (DS TP96: rank = die mod 96)
    parameter integer RXAW = 8,
    parameter integer QAW = 7,
    parameter integer TXAW = 3,
    parameter integer NPT = 8,
    parameter integer INJ = 2,
    parameter integer DEL = 4,
    parameter integer LANES = 16,
    parameter integer FW = 32 * LANES,
    parameter integer PWT = FW + 33,
    parameter integer MUT_MULTI = 0    // bench mutant: the multi-driver flag never sets
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               pclk,
    input  wire               prst_n,
    input  wire [7:0]         rank,
    input  wire [15:0]        pf,
    input  wire               go,
    output wire [INJ*16-1:0]  inj_idx,
    output wire [INJ-1:0]     inj_rd,
    input  wire [4*INJ*FW-1:0] inj_q,      // the four SU quarters' inject data {NE, SE, NW, SW}: the owner drives, the rest 0
    output wire [NPT-1:0]     ph_tx_v,
    output wire [NPT*PWT-1:0] ph_tx_flit,
    input  wire [NPT-1:0]     sw_cr_ret,
    input  wire [NPT-1:0]     ph_rx_v,
    input  wire [NPT*PWT-1:0] ph_rx_flit,
    output wire [NPT-1:0]     rx_credit,
    output wire [DEL-1:0]     del_valid,
    output wire [DEL*PWT-1:0] del_flit,
    output wire               fault,
    output wire [31:0]        stat_credit_stall,
    input  wire [967:0]       hgi_rec,       // {die_id 8, n_I, n_O, n_A, desc_I, desc_O, desc_A, header 128, valid}
    output wire [2:0]         hgi_ret,       // {fault, done, ready}
    input  wire [39:0]        hgi_cfg,       // config station bus
    output wire [93:0]        hgi_rowfmt_o,  // {context 32, words 16, rows 21, dest 8, block 8, group 8, done_r, start_v}
    input  wire [2:0]         hgi_rowfmt_i,  // {fault, done_v, start_r}
    output wire [79:0]        hgi_vmaddr     // {O base 40, A base 40}
);
    wire [7:0] r_rank, r_mg; wire r_mall, r_byp; wire [3:0] r_gsz; wire [15:0] r_pf; wire r_go, r_done_ready;
    wire [39:0] r_abase, r_obase; wire rec_rdy, rec_done, rec_fault;
    wire rf_sv, rf_dr; wire [7:0] rf_g, rf_b, rf_d; wire [20:0] rf_rows; wire [15:0] rf_words; wire [31:0] rf_ctx;
    wire start_ready, done_valid, done_ready;
    // SU-quarter inject OR (ownership contract: flit i is quarter i mod 4's, the other three drive 0) and the review-1149
    // multi-driver flag: two or more non-zero quarters on one inject lane in a cycle sets a sticky fault (cleared by rst_n only).  The
    // data path is the plain OR (zero cycles); the flag is a parallel OR-reduce per quarter into one flop.
    wire [INJ*FW-1:0] inj_data = inj_q[0 +: INJ*FW] | inj_q[INJ*FW +: INJ*FW] | inj_q[2*INJ*FW +: INJ*FW] | inj_q[3*INJ*FW +: INJ*FW];
    // per inject lane h: the quarters driving a non-zero word on lane h (each quarter drives only the lanes it owns)
    reg multi;
    always @* begin : mdet
        reg [3:0] nz;
        multi = 1'b0;
        for (integer h = 0; h < INJ; h = h + 1) begin
            for (integer q = 0; q < 4; q = q + 1) nz[q] = |inj_q[q*INJ*FW + h*FW +: FW];
            if ((nz[0] & nz[1]) | (nz[0] & nz[2]) | (nz[0] & nz[3]) | (nz[1] & nz[2]) | (nz[1] & nz[3]) | (nz[2] & nz[3])) multi = 1'b1;
        end
    end
    reg multi_err;
    always @(posedge clk or negedge rst_n) if (!rst_n) multi_err <= 1'b0; else if (multi && MUT_MULTI == 0) multi_err <= 1'b1;
    wire ep_fault;
    wire [31:0] cfg_w46;
    ot_hgi_cfg_rx #(.W0(46), .NW(1), .RST(32'd96)) u_cfg (.clk(clk), .rst_n(rst_n), .bus(hgi_cfg), .act(cfg_w46));
    ot_hgi_coll_record u_rec (.clk(clk), .rst_n(rst_n), .cfg_coll_group_size(cfg_w46[7:0]), .cfg_die_id(hgi_rec[967:960]),
        .rec_v(hgi_rec[0]), .rec_rdy(rec_rdy), .rec_hdr(hgi_rec[128:1]), .rec_a(hgi_rec[384:129]),
        .rec_o(hgi_rec[640:385]), .rec_i(hgi_rec[896:641]), .rec_n_a(hgi_rec[917:897]), .rec_n_o(hgi_rec[938:918]),
        .rec_n_i(hgi_rec[959:939]), .rec_done(rec_done), .rec_fault(rec_fault),
        .ep_rank(r_rank), .ep_mcast_group_size(r_mg), .ep_mcast_all(r_mall), .ep_gsz(r_gsz), .ep_byp(r_byp), .ep_pf(r_pf), .ep_go(r_go),
        .ep_start_ready(start_ready), .ep_done_valid(done_valid), .ep_done_ready(r_done_ready),
        .ep_fault(fault), .ep_a_base(r_abase), .ep_o_base(r_obase),
        .rf_start_v(rf_sv), .rf_start_r(hgi_rowfmt_i[0]), .rf_group_size(rf_g), .rf_owner_block(rf_b),
        .rf_destinations(rf_d), .rf_row_count(rf_rows), .rf_row_words(rf_words), .rf_context_rows(rf_ctx),
        .rf_done_v(hgi_rowfmt_i[1]), .rf_done_r(rf_dr), .rf_fault(hgi_rowfmt_i[2]));
    reg own_hgi; always @(posedge clk or negedge rst_n) if (!rst_n) own_hgi <= 1'b0;
        else if (r_go) own_hgi <= 1'b1; else if (go) own_hgi <= 1'b0;
    wire sel = r_go | (own_hgi & ~go);
    assign done_ready = own_hgi ? r_done_ready : done_valid;   // the legacy path has no completion handshake
    ot_hbm_accel_tu_endpoint_psg #(.ENABLE(1), .REARM(1), .NOG(NOG), .RXAW(RXAW), .QAW(QAW), .TXAW(TXAW), .NPT(NPT), .INJ(INJ),
        .DEL(DEL), .LANES(LANES)) u_ep (.clk(clk), .rst_n(rst_n), .pclk(pclk), .prst_n(prst_n),
        .rank(sel ? r_rank : rank), .mcast_group_size(sel ? r_mg : 8'd96), .mcast_all(sel & r_mall),
        .gsz(sel ? r_gsz : 4'hF), .byp(sel & r_byp), .pf(sel ? r_pf : pf), .go(r_go | go), .start_ready(start_ready),
        .done_valid(done_valid), .done_ready(done_ready), .fault_ack(1'b0),
        .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_data(inj_data), .ph_tx_v(ph_tx_v), .ph_tx_flit(ph_tx_flit),
        .sw_cr_ret(sw_cr_ret), .ph_rx_v(ph_rx_v), .ph_rx_flit(ph_rx_flit), .rx_credit(rx_credit),
        .del_valid(del_valid), .del_flit(del_flit), .fault(ep_fault), .stat_credit_stall(stat_credit_stall));
    assign fault = ep_fault | multi_err;
    assign hgi_ret = {rec_fault, rec_done, rec_rdy};
    assign hgi_rowfmt_o = {rf_ctx, rf_words, rf_rows, rf_d, rf_b, rf_g, rf_dr, rf_sv};
    assign hgi_vmaddr = {r_obase, r_abase};
endmodule
`default_nettype wire
