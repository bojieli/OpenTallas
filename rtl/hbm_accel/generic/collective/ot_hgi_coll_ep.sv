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
    parameter integer PIPE = 0,        // hgi-unitrate: pipelined ALL_GATHER (EQ epochs open, tagged flits, parking)
    parameter integer EQ = 4,          // pipelined gathers open at once (tags are mod 8 = 2 EQ: a peer leads <= EQ)
    parameter integer PPK = 512,       // parking depth per epoch queue (flits of a gather this rank has not started)
    parameter integer MUT_PIPE = 0     // bench mutants: 1 tag ignored (oldest epoch's context), 2 no parking (early
                                       //   flits formatted with the oldest context), 3 an epoch completes one flit early
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
    output wire [DEL*40-1:0]  hgi_del_obase  // PIPE: the O base of the gather each delivery lane's flit belongs to
);
    wire [7:0] r_rank, r_mg; wire r_mall, r_byp, r_amx, r_bf16; wire [3:0] r_gsz; wire [15:0] r_pf; wire r_go, r_done_ready;
    wire [39:0] r_abase, r_obase; wire rec_rdy, rec_done, rec_fault;
    wire rf_sv, rf_dr; wire [7:0] rf_g, rf_b, rf_d; wire [20:0] rf_rows; wire [15:0] rf_words; wire [31:0] rf_ctx;
    wire start_ready, done_valid, done_ready, m_done, m_done0;
    wire start_ready_p, r_pipe, p_inj_done; wire [2:0] p_inj_tag; reg [3:0] p_open; reg [2:0] p_next;
    wire g_slice, gs_we; wire [7:0] g_base; wire [6:0] gs_wa; wire [15:0] gs_wd;
    wire [DEL-1:0] a_dv; wire [DEL*PWT-1:0] a_df; wire [DEL-1:0] e_dv; wire [DEL*PWT-1:0] e_df;
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
    ot_hgi_coll_record #(.PIPE(PIPE)) u_rec (.clk(clk), .rst_n(rst_n), .cfg_coll_group_size(cfg_w46[7:0]), .cfg_die_id(hgi_rec[967:960]),
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
        .ep_start_ready_p(start_ready_p), .pipe_room(p_open < EQ), .pipe_idle(p_open == 0), .ep_pipe(r_pipe));
    reg own_hgi; always @(posedge clk or negedge rst_n) if (!rst_n) own_hgi <= 1'b0;
        else if (r_go) own_hgi <= 1'b1; else if (go) own_hgi <= 1'b0;
    wire sel = r_go | (own_hgi & ~go);
    assign done_ready = own_hgi ? r_done_ready : done_valid;   // the legacy path has no completion handshake
    ot_hbm_accel_tu_endpoint_psg #(.ENABLE(1), .REARM(1), .PFMAX(PFMAX), .BF16RT(1), .NOG(NOG), .RXAW(RXAW), .QAW(QAW), .TXAW(TXAW), .NPT(NPT), .INJ(INJ),
        .DEL(DEL), .LANES(LANES), .PIPE(PIPE)) u_ep (.clk(clk), .rst_n(rst_n), .pclk(pclk), .prst_n(prst_n),
        .rank(sel ? r_rank : rank), .mcast_group_size(sel ? r_mg : 8'd96), .mcast_all(sel & r_mall),
        .gsz(sel ? r_gsz : 4'hF), .byp(sel & r_byp), .res_bf16(sel ? r_bf16 : 1'b1), .pf(sel ? r_pf : pf), .go(r_go | go), .start_ready(start_ready),
        .done_valid(done_valid), .done_ready(done_ready), .fault_ack(1'b0),
        .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_data(inj_data), .ph_tx_v(ph_tx_v), .ph_tx_flit(ph_tx_flit),
        .sw_cr_ret(sw_cr_ret), .ph_rx_v(ph_rx_v), .ph_rx_flit(ph_rx_flit), .rx_credit(rx_credit),
        .del_valid(e_dv), .del_flit(e_df), .fault(ep_fault), .stat_credit_stall(stat_credit_stall),
        .pipe(r_pipe), .pipe_tag(p_next), .start_ready_p(start_ready_p), .pipe_inj_done(p_inj_done), .pipe_inj_tag(p_inj_tag));
    // ARGMAX_MERGE fold on the delivery lanes (pass-through otherwise)
    reg amx_run; always @(posedge clk or negedge rst_n) if (!rst_n) amx_run <= 1'b0;
        else if (r_go) amx_run <= r_amx; else if (go) amx_run <= 1'b0;
    ot_hgi_coll_amerge #(.DEL(DEL), .FW(FW), .PWT(PWT), .MUT_TIE(MUT_TIE)) u_amx (.clk(clk), .rst_n(rst_n),
        .en(amx_run | (r_go & r_amx)), .start(r_go), .rank(r_rank), .d_v(e_dv), .d_f(e_df), .ep_done(done_valid),
        .o_v(a_dv), .o_f(a_df), .done_out(m_done0));
    // F3 delivery formatter (one registered stage on every delivery lane; completion delayed with it): on a sliced
    // gather the delivered flit {1, FF, src q, gi, data} becomes {1, lanes, src, w, data}: w = s_q + 16 (gi - q pf) the
    // O word offset, lanes = min(16, s_{q+1} - w) the valid words (the SU deliver writes words w .. w + lanes - 1)
    reg [15:0] gs_t [0:96];
    always @(posedge clk) if (gs_we && PIPE == 0) gs_t[gs_wa] <= gs_wd;
    // PIPE: every sliced gather is pipelined; the record writes its slice table while setting it up, into the slot of
    // the NEXT epoch (free: the record waits for an open slot before it starts the table)
    reg [15:0] gs_p [0:EQ-1][0:96];
    always @(posedge clk) if (PIPE != 0 && gs_we) gs_p[p_next % EQ][gs_wa] <= gs_wd;
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
    // =================================================================================================================
    // PIPE: per-epoch contexts, delivery formatting, parking, completion and in-order retirement (hgi-unitrate)
    //   context slot t % EQ of epoch tag t, written at the pipelined go: {O base, slicing, group base / size, pf,
    //   expected deliveries T = G pf}; a delivered pipe flit (dst {11110, tag}) whose slot holds that tag is formatted
    //   with the slot's slice table (exactly the classic formatter) and counted (count, sum and xor of gi over
    //   0 .. T-1); one whose epoch this rank has not started yet is PARKED in queue tag % EQ (a peer may lead by up to
    //   EQ epochs: its started <= its completed + EQ <= this rank's injected + EQ) and replayed, one a cycle on a free
    //   lane, once the epoch starts.  An epoch completes when its injection is done and all T flits are delivered with
    //   the right gi set; the oldest completed epoch retires the record (rec_done), so retirement stays in order.
    // =================================================================================================================
    reg  [DEL-1:0] q_dv; reg [DEL*PWT-1:0] q_df; reg [DEL*40-1:0] q_ob;
    reg            p_done; reg p_flt;
    generate if (PIPE != 0) begin : g_pipe
        reg        c_v [0:EQ-1]; reg [2:0] c_tag [0:EQ-1]; reg c_inj [0:EQ-1];
        reg [39:0] c_ob [0:EQ-1]; reg c_sl [0:EQ-1]; reg [7:0] c_gb [0:EQ-1]; reg [15:0] c_pf [0:EQ-1];
        reg [7:0]  c_gn [0:EQ-1]; reg [16:0] c_T [0:EQ-1]; reg [16:0] c_n [0:EQ-1]; reg [31:0] c_sum [0:EQ-1];
        reg [15:0] c_xor [0:EQ-1];
        reg [2:0]  p_old;                                    // oldest open epoch tag
        reg [PWT-1:0] pk [0:EQ-1][0:PPK-1]; reg [$clog2(PPK):0] pk_n [0:EQ-1]; reg [$clog2(PPK)-1:0] pk_h [0:EQ-1], pk_t [0:EQ-1];
        // the group of the gather being started: as the endpoint derives it (mcast_all outer group, else 2^gsz)
        wire [7:0] gn_go = r_mall ? r_mg : (8'd1 << r_gsz[1:0]);
        wire [7:0] gb_go = r_mall ? ((r_mg == 8'd96) ? 8'd0 : (r_rank & ~(r_mg - 8'd1))) : (r_rank & ~((8'd1 << r_gsz[1:0]) - 8'd1));
        // format one pipe flit x with slot c (the classic F3 rewrite on that slot's table)
        function automatic [PWT-1:0] fmt(input [PWT-1:0] x0, input integer c);
            reg [PWT-1:0] x; reg [7:0] q; reg [15:0] m, w; reg [16:0] lim;
            begin
                x = x0;
                q = x[FW+16 +: 8] - c_gb[c];
                m = x[FW +: 16] - 16'(q * c_pf[c]);
                w = gs_p[c][q] + {m[11:0], 4'd0};
                lim = {1'b0, gs_p[c][q + 8'd1]} - {1'b0, w};
                if (c_sl[c]) begin x[FW +: 16] = w; x[FW+24 +: 8] = (lim >= 17'd16) ? 8'd16 : 8'(lim); end
                fmt = x;
            end
        endfunction
        integer c;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                q_dv <= '0; p_done <= 1'b0; p_flt <= 1'b0; p_open <= 4'd0; p_next <= 3'd0; p_old <= 3'd0;
                for (c = 0; c < EQ; c = c + 1) begin c_v[c] <= 1'b0; pk_n[c] <= '0; pk_h[c] <= '0; pk_t[c] <= '0; end
            end else begin : pp
                reg [DEL-1:0] used; reg [EQ-1:0] pop_q; reg [16:0] dn [0:EQ-1]; reg [31:0] ds [0:EQ-1]; reg [15:0] dx [0:EQ-1];
                reg [2:0] tg; integer s_, gi, lane; reg [PWT-1:0] x; reg drained, ret;
                reg [$clog2(PPK):0] pn [0:EQ-1]; reg [$clog2(PPK)-1:0] pt [0:EQ-1], ph [0:EQ-1];   // queue state this edge
                q_dv <= '0; p_done <= 1'b0; used = '0; pop_q = '0;
                for (c = 0; c < EQ; c = c + 1) begin dn[c] = c_n[c]; ds[c] = c_sum[c]; dx[c] = c_xor[c];
                    pn[c] = pk_n[c]; pt[c] = pk_t[c]; ph[c] = pk_h[c]; end
                // a pipelined go opens the next epoch's slot
                if (r_go && r_pipe) begin
                    s_ = p_next % EQ;
                    c_v[s_] <= 1'b1; c_tag[s_] <= p_next; c_inj[s_] <= 1'b0; c_ob[s_] <= r_obase; c_sl[s_] <= g_slice;
                    c_gb[s_] <= gb_go; c_gn[s_] <= gn_go; c_pf[s_] <= r_pf; c_T[s_] <= 17'(gn_go * r_pf) - ((MUT_PIPE == 3) ? 17'd1 : 17'd0);
                    dn[s_] = 17'd0; ds[s_] = 32'd0; dx[s_] = 16'd0;
                    p_next <= p_next + 3'd1;
                end
                if (p_inj_done) c_inj[p_inj_tag % EQ] <= 1'b1;
                // live delivery lanes
                for (integer l = 0; l < DEL; l = l + 1) if (e_dv[l]) begin
                    x = e_df[l*PWT +: PWT];
                    if (x[PWT-1] && x[FW+27 +: 5] == 5'b11110) begin
                        tg = x[FW+24 +: 3]; s_ = (MUT_PIPE == 1) ? (p_old % EQ) : (tg % EQ);
                        if ((c_v[s_] && c_tag[s_] == tg) || MUT_PIPE == 1 || (MUT_PIPE == 2 && c_v[p_old % EQ])) begin
                            if (MUT_PIPE == 2) s_ = (c_v[s_] && c_tag[s_] == tg) ? s_ : (p_old % EQ);
                            if (x[FW+16 +: 8] >= c_gb[s_] && x[FW+16 +: 8] < c_gb[s_] + c_gn[s_]) begin
                                q_dv[l] <= 1'b1; q_df[l*PWT +: PWT] <= fmt(x, s_); q_ob[l*40 +: 40] <= c_ob[s_]; used[l] = 1'b1;
                                gi = integer'(x[FW +: 16]); dn[s_] = dn[s_] + 17'd1; ds[s_] = ds[s_] + 32'(gi); dx[s_] = dx[s_] ^ 16'(gi);
                                if (gi >= integer'(c_T[s_]) || dn[s_] > c_T[s_]) p_flt <= 1'b1;
                            end
                        end else begin                       // an epoch this rank has not started: park it
                            s_ = tg % EQ;
                            if (pn[s_] == PPK) p_flt <= 1'b1;   // several lanes may park into one queue an edge
                            else begin pk[s_][pt[s_]] <= x; pt[s_] = pt[s_] + 1'b1; pn[s_] = pn[s_] + 1'b1; end
                        end
                    end
                end
                // replay one parked flit a cycle onto the first free lane, for a started epoch
                drained = 1'b0;
                for (c = 0; c < EQ; c = c + 1) if (!drained && pk_n[c] != 0 && c_v[c] && c_tag[c] == pk[c][pk_h[c]][FW+24 +: 3]) begin
                    lane = -1;
                    for (integer l = DEL - 1; l >= 0; l = l - 1) if (!used[l] && !e_dv[l]) lane = l;
                    if (lane >= 0) begin
                        x = pk[c][pk_h[c]]; drained = 1'b1;
                        ph[c] = ph[c] + 1'b1; pn[c] = pn[c] - 1'b1;
                        if (x[FW+16 +: 8] >= c_gb[c] && x[FW+16 +: 8] < c_gb[c] + c_gn[c]) begin
                            q_dv[lane] <= 1'b1; q_df[lane*PWT +: PWT] <= fmt(x, c); q_ob[lane*40 +: 40] <= c_ob[c];
                            gi = integer'(x[FW +: 16]); dn[c] = dn[c] + 17'd1; ds[c] = ds[c] + 32'(gi); dx[c] = dx[c] ^ 16'(gi);
                            if (gi >= integer'(c_T[c]) || dn[c] > c_T[c]) p_flt <= 1'b1;
                        end
                    end
                end
                for (c = 0; c < EQ; c = c + 1) begin c_n[c] <= dn[c]; c_sum[c] <= ds[c]; c_xor[c] <= dx[c];
                    pk_n[c] <= pn[c]; pk_t[c] <= pt[c]; pk_h[c] <= ph[c]; end
                // in-order retirement of the oldest epoch
                s_ = p_old % EQ;
                ret = c_v[s_] && c_tag[s_] == p_old && c_inj[s_] && c_n[s_] == c_T[s_];
                if (ret) begin : rt
                    reg [31:0] T; reg [15:0] xe;
                    T = {15'd0, c_T[s_]};
                    case (T[1:0]) 2'd1: xe = 16'(T - 1); 2'd2: xe = 16'd1; 2'd3: xe = 16'(T); default: xe = 16'd0; endcase
                    if (MUT_PIPE != 3 && (c_sum[s_] != (T * (T - 1)) >> 1 || c_xor[s_] != xe)) p_flt <= 1'b1;
                    c_v[s_] <= 1'b0; p_done <= 1'b1; p_old <= p_old + 3'd1;
                end
                p_open <= p_open + ((r_go && r_pipe) ? 4'd1 : 4'd0) - (ret ? 4'd1 : 4'd0);
            end
    end else begin : g_nopipe
        always @* begin q_dv = '0; q_df = '0; q_ob = '0; p_done = 1'b0; p_flt = 1'b0; p_open = 4'd0; p_next = 3'd0; end
    end endgenerate
    // classic deliveries (not pipe-tagged) take the classic formatter; pipe ones the block above (disjoint lanes)
    reg [DEL-1:0] f_pipe;
    always @(posedge clk) for (integer l = 0; l < DEL; l = l + 1)
        f_pipe[l] <= (PIPE != 0) && a_dv[l] && a_df[l*PWT + PWT - 1] && a_df[l*PWT + FW + 27 +: 5] == 5'b11110;
    reg [39:0] a_run;                                          // A base of the injecting collective (latched at go)
    always @(posedge clk) if (r_go || go) a_run <= r_abase;
    assign del_valid = (f_dv & ~f_pipe) | q_dv;
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_dsel
        assign del_flit[l*PWT +: PWT] = q_dv[l] ? q_df[l*PWT +: PWT] : f_df[l*PWT +: PWT];
        assign hgi_del_obase[l*40 +: 40] = q_dv[l] ? q_ob[l*40 +: 40] : r_obase;
    end
    assign m_done = f_done;
    assign fault = ep_fault | multi_err | p_flt;
    assign hgi_ret = {rec_fault | (p_flt && PIPE != 0), rec_done | p_done, rec_rdy};
    assign hgi_rowfmt_o = {rf_ctx, rf_words, rf_rows, rf_d, rf_b, rf_g, rf_dr, rf_sv};
    assign hgi_vmaddr = {r_obase, (PIPE != 0) ? a_run : r_abase};
endmodule
`default_nettype wire
