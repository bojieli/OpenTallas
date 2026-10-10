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
    parameter integer PFMAX = 512,    // F4 (hgi-e2e): flits per contributor (Qwen all-reduce 256, DS gathers 80 / 144 / 320); was the PSG default 64
    parameter integer RXAW = 8,
    parameter integer QAW = 7,
    parameter integer TXAW = 3,
    parameter integer NPT = 8,
    parameter integer INJ = 2,
    parameter integer DEL = 4,
    parameter integer LANES = 16,
    parameter integer FW = 32 * LANES,
    parameter integer PWT = FW + 33,
    parameter integer MUT_MULTI = 0,   // bench mutant: the multi-driver flag never sets
    parameter integer MUT_TIE = 0,     // bench mutant: ARGMAX_MERGE ties to the higher id
    parameter integer RGXHW = 0        // 1: hardware COLL.ROW_GATHER (G25): owner-row source + list-order sink on this endpoint
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
    output wire [79:0]        hgi_vmaddr,    // {O base 40, A base 40}
    // hardware ROW_GATHER (RGXHW = 1; tied off otherwise): list read (VM, 512-bit words, in order), owner-row HBM reads
    // (2 sector lanes, any order, the ATT lane protocol), list-order writes (one per delivery lane)
    output wire               rg_lq_v,
    input  wire               rg_lq_rdy,
    output wire [31:0]        rg_lq_addr,
    input  wire               rg_lr_v,
    input  wire [511:0]       rg_lr_data,
    output wire [1:0]         rg_hq_v,
    input  wire [1:0]         rg_hq_rdy,
    output wire [69:0]        rg_hq_addr,
    output wire [15:0]        rg_hq_tag,
    input  wire [1:0]         rg_hr_v,
    input  wire [15:0]        rg_hr_tag,
    input  wire [511:0]       rg_hr_data,
    output wire [DEL-1:0]     rg_w_v,
    output wire [DEL*40-1:0]  rg_w_addr,
    output wire               rg_w_vm,       // the run's O space (0 HBM bytes, 1 VM words)
    output wire [DEL*FW-1:0]  rg_w_data,
    input  wire [DEL-1:0]     rg_w_rdy
);
    wire [7:0] r_rank, r_mg; wire r_mall, r_byp, r_amx, r_bf16; wire [3:0] r_gsz; wire [15:0] r_pf; wire r_go, r_done_ready;
    wire [39:0] r_abase, r_obase; wire rec_rdy, rec_done, rec_fault;
    wire rf_sv, rf_dr; wire [7:0] rf_g, rf_b, rf_d; wire [20:0] rf_rows; wire [15:0] rf_words; wire [31:0] rf_ctx;
    wire start_ready, done_valid, done_ready, m_done, m_done0;
    wire g_slice, gs_we; wire [7:0] g_base; wire [6:0] gs_wa; wire [15:0] gs_wd;
    wire [DEL-1:0] a_dv; wire [DEL*PWT-1:0] a_df; wire [DEL-1:0] e_dv; wire [DEL*PWT-1:0] e_df;
    // G25 hardware ROW_GATHER
    wire r_rgx, rg_start, rg_ovm, rs_v, rs_rdy, rs_end, rg_drained, rg_src_fault, rg_sink_fault;
    wire [16:0] r_rtot; wire [11:0] rg_k; wire [2:0] rg_lb; wire [7:0] rg_g, rg_rrel, rg_dests; wire [34:0] rg_abase;
    wire [15:0] rg_astride; wire [6:0] rg_sec; wire [5:0] rg_nflit; wire [31:0] rg_lbase, rg_ostride; wire [39:0] rg_obase;
    wire [15:0] rs_gi; wire [FW-1:0] rs_data; wire [DEL-1:0] rg_permit, rg_reserve;
    reg rgx_run;     // the current collective is a hardware ROW_GATHER: deliveries go to the sink, not the SU quarters
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
    ot_hgi_coll_record #(.RGXHW(RGXHW)) u_rec (.clk(clk), .rst_n(rst_n), .cfg_coll_group_size(cfg_w46[7:0]), .cfg_die_id(hgi_rec[967:960]),
        .rec_v(hgi_rec[0]), .rec_rdy(rec_rdy), .rec_hdr(hgi_rec[128:1]), .rec_a(hgi_rec[384:129]),
        .rec_o(hgi_rec[640:385]), .rec_i(hgi_rec[896:641]), .rec_n_a(hgi_rec[917:897]), .rec_n_o(hgi_rec[938:918]),
        .rec_n_i(hgi_rec[959:939]), .rec_done(rec_done), .rec_fault(rec_fault),
        .ep_rank(r_rank), .ep_mcast_group_size(r_mg), .ep_mcast_all(r_mall), .ep_gsz(r_gsz), .ep_byp(r_byp), .ep_amx(r_amx), .ep_bf16(r_bf16), .ep_pf(r_pf), .ep_go(r_go),
        .ep_start_ready(start_ready), .ep_done_valid(m_done), .ep_done_ready(r_done_ready),
        .ep_fault(fault), .ep_a_base(r_abase), .ep_o_base(r_obase),
        .ep_gslice(g_slice), .ep_gbase(g_base), .gs_we(gs_we), .gs_wa(gs_wa), .gs_wd(gs_wd),
        .rf_start_v(rf_sv), .rf_start_r(hgi_rowfmt_i[0]), .rf_group_size(rf_g), .rf_owner_block(rf_b),
        .rf_destinations(rf_d), .rf_row_count(rf_rows), .rf_row_words(rf_words), .rf_context_rows(rf_ctx),
.rf_done_v(hgi_rowfmt_i[1]), .rf_done_r(rf_dr), .rf_fault(hgi_rowfmt_i[2]),
        .ep_rgx(r_rgx), .ep_rgx_total(r_rtot), .rg_start(rg_start), .rg_k(rg_k), .rg_lb(rg_lb), .rg_g(rg_g), .rg_rrel(rg_rrel),
        .rg_dests(rg_dests), .rg_abase(rg_abase), .rg_astride(rg_astride), .rg_sec(rg_sec), .rg_nflit(rg_nflit),
        .rg_lbase(rg_lbase), .rg_obase(rg_obase), .rg_ostride(rg_ostride), .rg_ovm(rg_ovm), .rg_drained(rg_drained));
    reg own_hgi; always @(posedge clk or negedge rst_n) if (!rst_n) own_hgi <= 1'b0;
        else if (r_go) own_hgi <= 1'b1; else if (go) own_hgi <= 1'b0;
    wire sel = r_go | (own_hgi & ~go);
    assign done_ready = own_hgi ? r_done_ready : done_valid;   // the legacy path has no completion handshake
    always @(posedge clk or negedge rst_n) if (!rst_n) rgx_run <= 1'b0;
        else if (r_go) rgx_run <= (RGXHW != 0) && r_rgx; else if (go) rgx_run <= 1'b0;
    wire rgx_now = rgx_run | (r_go & r_rgx & (RGXHW != 0));
    ot_hbm_accel_tu_endpoint_psg #(.ENABLE(1), .REARM(1), .RGX(RGXHW), .DELCRED(RGXHW), .PFMAX(PFMAX), .BF16RT(1), .NOG(NOG), .RXAW(RXAW), .QAW(QAW), .TXAW(TXAW), .NPT(NPT), .INJ(INJ),
        .DEL(DEL), .LANES(LANES)) u_ep (.clk(clk), .rst_n(rst_n), .pclk(pclk), .prst_n(prst_n),
        .rank(sel ? r_rank : rank), .mcast_group_size(sel ? r_mg : 8'd96), .mcast_all(sel & r_mall),
        .gsz(sel ? r_gsz : 4'hF), .byp(sel & r_byp), .res_bf16(sel ? r_bf16 : 1'b1), .pf(sel ? r_pf : pf), .go(r_go | go), .start_ready(start_ready),
        .done_valid(done_valid), .done_ready(done_ready), .fault_ack(1'b0),
        .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_data(inj_data), .ph_tx_v(ph_tx_v), .ph_tx_flit(ph_tx_flit),
        .sw_cr_ret(sw_cr_ret), .ph_rx_v(ph_rx_v), .ph_rx_flit(ph_rx_flit), .rx_credit(rx_credit),
        .del_valid(e_dv), .del_flit(e_df),
        .rgx(sel & r_rgx), .rgx_total(r_rtot), .rs_v(rs_v), .rs_gi(rs_gi), .rs_data(rs_data), .rs_rdy(rs_rdy), .rs_end(rs_end),
        .del_permit(rgx_now ? rg_permit : {DEL{1'b1}}), .del_reserve(rg_reserve),
        .fault(ep_fault), .stat_credit_stall(stat_credit_stall));
    generate if (RGXHW != 0) begin : g_rgx
        ot_hgi_coll_rgx_src #(.FW(FW)) u_rsrc (.clk(clk), .rst_n(rst_n), .start(rg_start), .cfg_k(rg_k), .cfg_lb(rg_lb), .cfg_g(rg_g),
            .cfg_rrel(rg_rrel), .cfg_abase(rg_abase), .cfg_astride(rg_astride), .cfg_sec(rg_sec), .cfg_nflit(rg_nflit),
            .cfg_lbase(rg_lbase), .lq_v(rg_lq_v), .lq_rdy(rg_lq_rdy), .lq_addr(rg_lq_addr), .lr_v(rg_lr_v), .lr_data(rg_lr_data),
            .hq_v(rg_hq_v), .hq_rdy(rg_hq_rdy), .hq_addr(rg_hq_addr), .hq_tag(rg_hq_tag), .hr_v(rg_hr_v), .hr_tag(rg_hr_tag),
            .hr_data(rg_hr_data), .rs_v(rs_v), .rs_gi(rs_gi), .rs_data(rs_data), .rs_rdy(rs_rdy), .rs_end(rs_end), .busy(),
            .fault(rg_src_fault));
        ot_hgi_coll_rgx_sink #(.DEL(DEL), .FW(FW), .PWT(PWT)) u_rsink (.clk(clk), .rst_n(rst_n), .start(rg_start),
            .cfg_nflit(rg_nflit), .cfg_k(rg_k), .cfg_discard(rg_rrel >= rg_dests), .cfg_obase(rg_obase), .cfg_ostride(rg_ostride),
            .cfg_ovm(rg_ovm), .del_reserve(rgx_now ? rg_reserve : {DEL{1'b0}}), .del_permit(rg_permit),
            .del_valid(rgx_run ? e_dv : {DEL{1'b0}}), .del_flit(e_df), .w_v(rg_w_v), .w_x(), .w_f(), .w_addr(rg_w_addr),
            .w_data(rg_w_data), .w_rdy(rg_w_rdy), .drained(rg_drained), .fault(rg_sink_fault));
        reg ovm_q; always @(posedge clk) if (rg_start) ovm_q <= rg_ovm;
        assign rg_w_vm = ovm_q;
    end else begin : g_norgx
        assign rs_v = 1'b0; assign rs_gi = 16'd0; assign rs_data = {FW{1'b0}}; assign rs_end = 1'b0; assign rg_drained = 1'b1;
        assign rg_permit = {DEL{1'b1}}; assign rg_src_fault = 1'b0; assign rg_sink_fault = 1'b0;
        assign rg_lq_v = 1'b0; assign rg_lq_addr = 32'd0; assign rg_hq_v = 2'd0; assign rg_hq_addr = 70'd0; assign rg_hq_tag = 16'd0;
        assign rg_w_v = {DEL{1'b0}}; assign rg_w_addr = {DEL*40{1'b0}}; assign rg_w_data = {DEL*FW{1'b0}}; assign rg_w_vm = 1'b0;
    end endgenerate
    // ARGMAX_MERGE fold on the delivery lanes (pass-through otherwise)
    reg amx_run; always @(posedge clk or negedge rst_n) if (!rst_n) amx_run <= 1'b0;
        else if (r_go) amx_run <= r_amx; else if (go) amx_run <= 1'b0;
    ot_hgi_coll_amerge #(.DEL(DEL), .FW(FW), .PWT(PWT), .MUT_TIE(MUT_TIE)) u_amx (.clk(clk), .rst_n(rst_n),
        .en(amx_run | (r_go & r_amx)), .start(r_go), .rank(r_rank), .d_v(rgx_run ? {DEL{1'b0}} : e_dv), .d_f(e_df), .ep_done(done_valid),
        .o_v(a_dv), .o_f(a_df), .done_out(m_done0));
    // F3 delivery formatter (one registered stage on every delivery lane; completion delayed with it): on a sliced
    // gather the delivered flit {1, FF, src q, gi, data} becomes {1, lanes, src, w, data}: w = s_q + 16 (gi - q pf) the
    // O word offset, lanes = min(16, s_{q+1} - w) the valid words (the SU deliver writes words w .. w + lanes - 1)
    reg [15:0] gs_t [0:96];
    always @(posedge clk) if (gs_we) gs_t[gs_wa] <= gs_wd;
    reg [DEL-1:0] f_dv; reg [DEL*PWT-1:0] f_df; reg f_done;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin f_dv <= {DEL{1'b0}}; f_done <= 1'b0; end
        else begin
            f_dv <= a_dv; f_done <= m_done0;
            for (integer l = 0; l < DEL; l = l + 1) begin : fmt
                reg [PWT-1:0] x; reg [7:0] q; reg [15:0] m, w, e; reg [16:0] lim;
                x = a_df[l*PWT +: PWT];
                q = x[FW+16 +: 8] - g_base;
                m = x[FW +: 16] - 16'(q * r_pf);
                w = gs_t[q] + {m[11:0], 4'd0};
                lim = {1'b0, gs_t[q + 8'd1]} - {1'b0, w};
                if (g_slice && x[PWT-1]) begin
                    x[FW +: 16] = w;
                    x[FW+24 +: 8] = (lim >= 17'd16) ? 8'd16 : 8'(lim);
                end
                f_df[l*PWT +: PWT] <= x;
            end
        end
    assign del_valid = f_dv; assign del_flit = f_df; assign m_done = f_done;
    assign fault = ep_fault | multi_err | rg_src_fault | rg_sink_fault;
    assign hgi_ret = {rec_fault, rec_done, rec_rdy};
    assign hgi_rowfmt_o = {rf_ctx, rf_words, rf_rows, rf_d, rf_b, rf_g, rf_dr, rf_sv};
    assign hgi_vmaddr = {r_obase, r_abase};
endmodule
`default_nettype wire
