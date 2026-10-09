`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DSpark speculative decode on the V4.1 HBM comparator: control-plane bench
// (tools/dshbm_dspark_rtl_campaign.py).
//
// DUT: rtl/gpu/dshbm/ot_dshbm_dspark_top.sv (the loop, spec-state addressing, argmax
// epilogue, W19 router selectors, expert union) + W19's rtl/gpu/ot_gpu_expert_fetch.sv
// streaming every union from the timing-faithful HBM model rtl/hdc/kv/ot_hdc_hbm_model.sv.
//
// The ENGINE side (the SM cluster's matvecs and dedicated units, verified separately:
// tools/dshbm_dspark_sm_campaign.py on rtl/gpu/ot_gpu_sm_v.sv) is replayed from the
// golden's own run (tools/dshbm_dspark_trace.py script.hex): for every command the DUT
// issues, the bench checks the command (op, layer/stage, columns, position, tokens) and
// performs the golden's engine events against the DUT:
//   WR   asks the DUT's spec state for the row's address and stores the row's content tag
//        in the bench's HBM state array (window rows, DSpark rows, compressor slots,
//        compressed rows / index keys);
//   RD   asks the DUT for the gather's address stream, folds the tags found there
//        (FNV-1a) and compares with the fold of the rows the GOLDEN read -- a rejected
//        row a gather wrongly reaches, a stale or missing row, or a wrong order fails;
//   SEL  the selected compressed rows, one address each;
//   RV   router values into the DUT's selectors; the ids it emits are checked;
//   UNION the DUT's union (ids, column masks) is checked and streamed through the
//        expert fetch; every released SMEM line is checked against the HBM pattern;
//   LG   logit rows (with the Markov bias on draft rows) into the DUT's argmax epilogue;
//        each argmax is checked against the golden's, and the DUT itself consumes it.
// The emitted tokens and the per-step accept counts are checked against the golden.
// After the loop ends, the FINAL gathers at the last committed position are checked
// against the AUTOREGRESSIVE run's state: exact rollback.
// ---------------------------------------------------------------------------
module tb_dshbm_dspark;
    parameter SCRIPT = "script.hex", PROMPT = "prompt.hex", FORCEF = "force.hex", EXPECT = "expect.hex";
    parameter integer NSCR = 1 << 21, GAMMA = 5, FORCE = 0, NGEN = 16, PLEN = 8, NL = 40, B = 5;
    parameter integer MUT = 0, ACCEPT_LEAF = 0, WR = 136, SR = 10, W = 128, MAXPOS = 128;
    parameter integer NEXP = 12, NDEXP = 4, KV = 6, KD = 3, LP = 8, RP = 4;
    parameter integer TIMEOUT = 200000000;
    parameter integer TW = 17;                       // hbm-forks 2026-10-09: TW 18 (HGI-1 18-bit tokens) by -P override
    localparam integer PMAX = 8, IW = 9, AW = 32;
    localparam [7:0] OP_CMD = 8'h01, OP_TOK = 8'h02, OP_WR = 8'h10, OP_RD = 8'h11, OP_SEL = 8'h12, OP_RV = 8'h20,
                     OP_VAL = 8'h21, OP_ID = 8'h22, OP_UNION = 8'h30, OP_UID = 8'h31, OP_LG = 8'h40,
                     OP_LV = 8'h41, OP_END = 8'hFE, OP_FINAL = 8'hF0, OP_EOF = 8'hFF;
    localparam [3:0] K_CK_SEL = 9, K_TOK_RD = 10;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    // ---- memories ----
    reg [127:0] scr [0:NSCR-1];
    reg [31:0]  prm [0:255];
    reg [31:0]  frc [0:4095];
    reg [31:0]  expv [0:4095];
    reg [63:0]  kvm [0:(1 << 20) - 1];
    // ---- DUT ----
    reg start = 0;
    wire [15:0] p_addr, f_addr;
    wire e_v, done; wire [TW-1:0] e_tok; wire [15:0] e_idx;
    wire cmd_v; reg cmd_ready = 0; wire [3:0] cmd_op, cmd_ncol; wire [7:0] cmd_idx; wire [31:0] cmd_pos;
    wire [TW-1:0] cmd_tok1; wire [PMAX*TW-1:0] cmd_toks; reg eng_done = 0;
    reg lg_v = 0, lg_last = 0, lg_bias_en = 0; reg [LP-1:0] lg_mask = 0; reg [LP*32-1:0] lg_vals = 0, lg_bias = 0;
    wire am_v, am_fault; wire [TW-1:0] am_idx;
    reg sr_v = 0; wire sr_ready; reg [3:0] sr_kind = 0; reg [15:0] sr_idx = 0; reg [31:0] sr_pos = 0;
    wire sa_v, sa_pad, sa_last, sa_err; wire [AW-1:0] sa_addr; wire [TW-1:0] sa_tok; wire [31:0] n_committed;
    reg rv_v = 0, rv_draft = 0, rv_last = 0; reg [RP*32-1:0] rv_vals = 0; reg [2:0] rv_col = 0;
    wire t_v; wire [KV*IW-1:0] t_ids; wire [2:0] t_col;
    reg u_clr = 0, u_flush = 0; wire u_v, u_ready, u_last; wire [IW-1:0] u_id; wire [PMAX-1:0] u_mask;
    wire step_v; wire [2:0] step_a; wire [3:0] step_g; wire [15:0] steps;
    wire [31:0] cyc_total, cyc_engine, cyc_markov;
`ifdef HFD_MTP
    // mtp-hbm 2026-10-08: the same bench on the die block hfd_mtp (ot_hfd_mtp_core: registered pins, skid slices,
    // PRL 2 token reads); +define+HFD_MTP_XSEL feeds the selections from bench-side selectors (the die's hfd_router)
    localparam integer HM_FAST = `ifdef HFD_MTP_FAST 1 `else 0 `endif;
    localparam integer HM_XSEL = `ifdef HFD_MTP_XSEL 1 `else 0 `endif;
    localparam integer HM_SPECF = `ifdef HFD_MTP_SPECF2 2 `elsif HFD_MTP_SPECF 1 `else 0 `endif;   // hgi-takeover: 1 = ot_dshbm_spec_state_f, 2 = _r
    wire x_v, x_draft; wire [KV*IW-1:0] x_ids; wire [2:0] x_col; reg u_flush_d = 0;
    ot_hfd_mtp_core #(.B(B), .PMAX(PMAX), .TW(TW), .NL(NL), .NST(3), .MAXPOS(MAXPOS), .W(W), .WR(WR), .SR(SR),
        .TR(16), .NG(4), .NSRC(4), .RLOG(16'h0111), .CKMAX(1 << 16), .AW(AW), .LP(LP), .FLAT(7), .NEXP(NEXP),
        .KV(KV), .NDEXP(NDEXP), .KD(KD), .RP(RP), .IW(IW), .MUT(MUT), .FAST(HM_FAST), .SPECF(HM_SPECF), .UNF(NEXP >= 32 ? HM_FAST : 0), .AMF(HM_FAST),
        .XSEL(HM_XSEL)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_gamma(GAMMA[3:0]), .cfg_force(FORCE[0]),
        .cfg_ngen(NGEN[15:0]), .cfg_plen(PLEN[15:0]), .p_addr(p_addr), .p_tok(prm[p_addr[7:0]][TW-1:0]),
        .f_addr(f_addr), .f_tok(frc[f_addr[11:0]][TW-1:0]), .e_v(e_v), .e_tok(e_tok), .e_idx(e_idx), .done(done),
        .cmd_v(cmd_v), .cmd_ready(cmd_ready), .cmd_op(cmd_op), .cmd_idx(cmd_idx), .cmd_ncol(cmd_ncol),
        .cmd_pos(cmd_pos), .cmd_tok1(cmd_tok1), .cmd_toks(cmd_toks), .eng_done(eng_done),
        .lg_v(lg_v), .lg_last(lg_last), .lg_bias_en(lg_bias_en), .lg_mask(lg_mask), .lg_vals(lg_vals),
        .lg_bias(lg_bias), .am_v(am_v), .am_idx(am_idx), .am_fault(am_fault),
        .sr_v(sr_v), .sr_ready(sr_ready), .sr_kind(sr_kind), .sr_idx(sr_idx), .sr_pos(sr_pos),
        .sa_v(sa_v), .sa_addr(sa_addr), .sa_tok(sa_tok), .sa_pad(sa_pad), .sa_last(sa_last), .sa_err(sa_err),
        .n_committed(n_committed), .rv_v(rv_v), .rv_draft(rv_draft), .rv_vals(rv_vals), .rv_last(rv_last),
        .rv_col(rv_col), .x_v(x_v), .x_draft(x_draft), .x_ids(x_ids), .x_col(x_col),
        .t_v(t_v), .t_ids(t_ids), .t_col(t_col), .u_clr(u_clr), .u_flush(HM_XSEL ? u_flush_d : u_flush),
        .u_v(u_v), .u_ready(u_ready), .u_id(u_id), .u_mask(u_mask), .u_last(u_last),
        .step_v(step_v), .step_a(step_a), .step_g(step_g), .steps(steps),
        .cyc_total(cyc_total), .cyc_engine(cyc_engine), .cyc_markov(cyc_markov));
    // bench-side selectors (XSEL): the die selector's role, with the top's in-flight flush ordering
    wire bv_v, bd_v; wire [KV*IW-1:0] bv_ids; wire [KD*IW-1:0] bd_ids;
    ot_gpu_router_topk #(.N(NEXP), .P(RP), .K(KV), .IW(IW)) b_tv (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & ~rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(bv_v), .out_ids(bv_ids));
    ot_gpu_router_topk #(.N(NDEXP), .P(RP), .K(KD), .IW(IW)) b_td (.clk(clk), .rst_n(rst_n),
        .in_valid(rv_v & rv_draft), .in_vals(rv_vals), .in_last(rv_last), .out_valid(bd_v), .out_ids(bd_ids));
    reg [2:0] bq [0:7]; reg [3:0] bq_w = 0, bq_r = 0; reg bflush = 0;
    always @(posedge clk) begin
        if (rv_v && rv_last) begin bq[bq_w[2:0]] <= rv_col; bq_w <= bq_w + 1; end
        if (bv_v || bd_v) bq_r <= bq_r + 1;
        u_flush_d <= 1'b0;
        if (u_flush) bflush <= 1'b1;
        else if (bflush && bq_w == bq_r && !(rv_v && rv_last)) begin bflush <= 1'b0; u_flush_d <= 1'b1; end
    end
    assign x_v = bv_v | bd_v; assign x_draft = bd_v; assign x_col = bq[bq_r[2:0]];
    assign x_ids = bd_v ? {{(KV-KD)*IW{1'b0}}, bd_ids} : bv_ids;
`else
    ot_dshbm_dspark_top #(.B(B), .PMAX(PMAX), .TW(TW), .NL(NL), .NST(3), .MAXPOS(MAXPOS), .W(W), .WR(WR), .SR(SR),
        .TR(16), .NG(4), .NSRC(4), .RLOG(16'h0111), .CKMAX(1 << 16), .AW(AW), .LP(LP), .FLAT(7), .NEXP(NEXP),
        .KV(KV), .NDEXP(NDEXP), .KD(KD), .RP(RP), .IW(IW), .MUT(MUT), .ACCEPT_LEAF(ACCEPT_LEAF)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_gamma(GAMMA[3:0]), .cfg_force(FORCE[0]),
        .cfg_ngen(NGEN[15:0]), .cfg_plen(PLEN[15:0]), .p_addr(p_addr), .p_tok(prm[p_addr[7:0]][TW-1:0]),
        .f_addr(f_addr), .f_tok(frc[f_addr[11:0]][TW-1:0]), .e_v(e_v), .e_tok(e_tok), .e_idx(e_idx), .done(done),
        .cmd_v(cmd_v), .cmd_ready(cmd_ready), .cmd_op(cmd_op), .cmd_idx(cmd_idx), .cmd_ncol(cmd_ncol),
        .cmd_pos(cmd_pos), .cmd_tok1(cmd_tok1), .cmd_toks(cmd_toks), .eng_done(eng_done),
        .lg_v(lg_v), .lg_last(lg_last), .lg_bias_en(lg_bias_en), .lg_mask(lg_mask), .lg_vals(lg_vals),
        .lg_bias(lg_bias), .am_v(am_v), .am_idx(am_idx), .am_fault(am_fault),
        .sr_v(sr_v), .sr_ready(sr_ready), .sr_kind(sr_kind), .sr_idx(sr_idx), .sr_pos(sr_pos),
        .sa_v(sa_v), .sa_addr(sa_addr), .sa_tok(sa_tok), .sa_pad(sa_pad), .sa_last(sa_last), .sa_err(sa_err),
        .n_committed(n_committed), .rv_v(rv_v), .rv_draft(rv_draft), .rv_vals(rv_vals), .rv_last(rv_last),
        .rv_col(rv_col), .t_v(t_v), .t_ids(t_ids), .t_col(t_col), .u_clr(u_clr), .u_flush(u_flush),
        .u_v(u_v), .u_ready(u_ready), .u_id(u_id), .u_mask(u_mask), .u_last(u_last),
        .step_v(step_v), .step_a(step_a), .step_g(step_g), .steps(steps),
        .cyc_total(cyc_total), .cyc_engine(cyc_engine), .cyc_markov(cyc_markov));
`endif
    // ---- W19 expert fetch + HBM model ----
    localparam integer NSM = 2, NPC = 32, FAW = 24, LENW = 6, TAGW = 16, BEATW = 5, MEMW = 1 << 16, XL = 4;
    reg [FAW-3:0] f_base = 0;
    wire [NSM*16-1:0] f_off = {16'd2, 16'd0}, f_lines = {16'd2, 16'd2};    // SM j: lines 2j, 2j+1 of an expert
    wire f_req_v, m_rdy; wire [FAW-1:0] f_addr_h; wire [LENW-1:0] f_len; wire [TAGW-1:0] f_tag;
    wire [NPC-1:0] rsp_v, f_rsp_rdy; wire [NPC*TAGW-1:0] rsp_tag; wire [NPC*BEATW-1:0] rsp_beat;
    wire [NPC*256-1:0] rsp_data; wire [NPC-1:0] pc_room;
    wire [NSM-1:0] s_valid; wire [NSM*1024-1:0] s_data; wire f_idle;
    ot_gpu_expert_fetch #(.NSM(NSM), .NPC(NPC), .DEPTH(64), .MAX_OUT(32), .AW(FAW), .LENW(LENW), .TAGW(TAGW),
        .BEATW(BEATW), .IW(IW)) u_fetch (
        .clk(clk), .rst_n(rst_n), .cfg_base(f_base), .cfg_exp_lines(XL[15:0]), .cfg_off(f_off), .cfg_lines(f_lines),
        .e_valid(u_v), .e_ready(u_ready), .e_id(u_id),
        .req_v(f_req_v), .req_rdy(m_rdy & f_req_v), .req_addr(f_addr_h), .req_len(f_len), .req_tag(f_tag),
        .rsp_v(rsp_v), .rsp_rdy(f_rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data),
        .s_valid(s_valid), .s_ready({NSM{1'b1}}), .s_data(s_data), .idle(f_idle));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(FAW), .MEM_WORDS(MEMW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
        .CLK_PS(833), .REQ_PS(10000), .RSP_PS(10000), .PC_RDY(1), .QD(64), .RQD(32), .REFI_PS(3900000)) hbm (
        .clk(clk), .rst_n(rst_n), .req_v(f_req_v), .req_rdy(m_rdy), .pc_room(pc_room), .req_we(1'b0),
        .req_addr(f_addr_h), .req_len(f_len), .req_tag(f_tag), .req_wdata(256'd0),
        .rsp_v(rsp_v), .rsp_rdy(f_rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data));
    function automatic [255:0] pat(input [31:0] s);
        pat = {8{s ^ 32'hA500_0000}};
    endfunction
    // ---- checks ----
    integer bad_cmd = 0, bad_gather = 0, bad_ids = 0, bad_union = 0, bad_line = 0, bad_am = 0, bad_emit = 0,
            bad_acc = 0, bad_final = 0, n_gather = 0, n_wr = 0, n_rv = 0, n_union = 0, n_unionids = 0,
            n_rows = 0, n_emit = 0, n_steps = 0, n_lines = 0, n_final = 0;
    // fetched-id order and released lines
    reg [IW-1:0] fid [0:65535];
    reg [FAW-3:0] fbase [0:65535];
    integer nf = 0, cnt [0:NSM-1];
    integer j, k, e_e, e_l, ln;
    always @(posedge clk) if (rst_n) begin
        if (u_v && u_ready) begin fid[nf] = u_id; fbase[nf] = f_base; nf = nf + 1; end
        for (j = 0; j < NSM; j = j + 1) if (s_valid[j]) begin
            e_e = cnt[j] / 2; e_l = cnt[j] % 2;
            ln = fbase[e_e] + fid[e_e] * XL + 2 * j + e_l;
            for (k = 0; k < 4; k = k + 1)
                if (s_data[j*1024 + k*256 +: 256] !== pat(ln * 4 + k)) bad_line = bad_line + 1;
            cnt[j] = cnt[j] + 1; n_lines = n_lines + 1;
        end
    end
    // argmax results against the golden's, in row order
    reg [TW-1:0] amq [0:65535];
    integer amw = 0, amr = 0;
    always @(posedge clk) if (am_v) begin
        if (amr >= amw || am_idx !== amq[amr]) begin
            bad_am = bad_am + 1;
            if (bad_am < 10) $display("ARGMAX MISMATCH row %0d got %0d want %0d", amr, am_idx, amq[amr]);
        end
        amr = amr + 1;
    end
    // emitted tokens and per-step accepts
    always @(posedge clk) begin
        if (e_v) begin
            if (e_idx >= NGEN || e_tok !== expv[e_idx][TW-1:0]) begin
                bad_emit = bad_emit + 1;
                if (bad_emit < 10) $display("EMIT MISMATCH %0d got %0d want %0d", e_idx, e_tok, expv[e_idx]);
            end
            n_emit = n_emit + 1;
        end
        if (step_v) begin
            if (step_a !== expv[NGEN + n_steps][2:0]) begin
                bad_acc = bad_acc + 1;
                if (bad_acc < 10) $display("ACCEPT MISMATCH step %0d got %0d want %0d", n_steps, step_a, expv[NGEN + n_steps]);
            end
            n_steps = n_steps + 1;
        end
    end
    // ---- engine replay ----
    integer sp = 0;
    reg [127:0] r;
    function [7:0]  r_op  (input [127:0] x); r_op   = x[127:120]; endfunction
    function [7:0]  r_kind(input [127:0] x); r_kind = x[119:112]; endfunction
    function [15:0] r_idx (input [127:0] x); r_idx  = x[111:96];  endfunction
    function [31:0] r_pos (input [127:0] x); r_pos  = x[95:64];   endfunction
    function [63:0] r_dat (input [127:0] x); r_dat  = x[63:0];    endfunction
    function [63:0] fnv(input [63:0] h, input [63:0] t);
        fnv = (h ^ t) * 64'h0000_0100_0000_01B3;
    endfunction
    task automatic sreq(input [3:0] kd, input [15:0] ix, input [31:0] ps);
        begin
            @(negedge clk); sr_v = 1; sr_kind = kd; sr_idx = ix; sr_pos = ps;
            @(posedge clk); while (!sr_ready) @(posedge clk);
            #0.1 sr_v = 0;
        end
    endtask
    // one gather: returns the fold of what the DUT's addresses (or tokens) find
    task automatic gather(input [3:0] kd, input [15:0] ix, input [31:0] ps, output [63:0] h);
        reg fin;
        begin
            h = 64'hCBF2_9CE4_8422_2325;
            sreq(kd, ix, ps);
            fin = 0;
            while (!fin) begin
                @(negedge clk);
                if (sa_v) begin
                    if (kd == K_TOK_RD) h = fnv(h, sa_pad ? 64'd0 : {47'd0, sa_tok} + 64'd1);
                    else if (!sa_pad) h = fnv(h, kvm[sa_addr[19:0]]);
                    fin = sa_last;
                end
            end
        end
    endtask
    task automatic one_addr(input [3:0] kd, input [15:0] ix, input [31:0] ps, output [31:0] a);
        begin
            sreq(kd, ix, ps);
            @(negedge clk); while (!sa_v) @(negedge clk);
            a = sa_addr;
        end
    endtask
    reg [63:0] h; reg [31:0] ad;
    integer c, nv, kk, cnt_u, b, need;
    reg first_rv;
    task automatic do_events(input integer final_sec);
        begin
            first_rv = 1;
            while (r_op(scr[sp]) != OP_END && r_op(scr[sp]) != OP_EOF) begin
                r = scr[sp]; sp = sp + 1;
                case (r_op(r))
                    OP_WR: begin
                        one_addr(r_kind(r), r_idx(r), r_pos(r), ad);
                        kvm[ad[19:0]] = r_dat(r); n_wr = n_wr + 1;
                    end
                    OP_RD: begin
                        gather(r_kind(r), r_idx(r), r_pos(r), h);
                        n_gather = n_gather + 1;
                        if (final_sec) n_final = n_final + 1;
                        if (h !== r_dat(r)) begin
                            if (final_sec) bad_final = bad_final + 1; else bad_gather = bad_gather + 1;
                            if (bad_gather + bad_final < 10)
                                $display("GATHER MISMATCH kind %0d idx %0d pos %0d n %0d (%s)", r_kind(r), r_idx(r),
                                         r_pos(r), n_committed, final_sec ? "final, vs autoregressive" : "pass");
                        end
                    end
                    OP_SEL: begin
                        h = 64'hCBF2_9CE4_8422_2325;
                        nv = r_pos(r);
                        for (kk = 0; kk < nv; kk = kk + 1) begin
                            one_addr(K_CK_SEL, r_idx(r), r_dat(scr[sp]), ad);
                            h = fnv(h, kvm[ad[19:0]]);
                            sp = sp + 1;
                        end
                        n_gather = n_gather + 1;
                        if (h !== r_dat(r)) begin
                            bad_gather = bad_gather + 1;
                            if (bad_gather < 10) $display("SELECTED-ROW MISMATCH src %0d", r_idx(r));
                        end
                    end
                    OP_RV: begin
                        if (first_rv) begin @(negedge clk); u_clr = 1; @(negedge clk); u_clr = 0; first_rv = 0; end
                        nv = r_pos(r); need = r_dat(r);
                        for (b = 0; b < nv; b = b + RP) begin
                            @(negedge clk);
                            rv_v = 1; rv_draft = r[112]; rv_col = r_idx(r); rv_last = (b + RP >= nv);
                            for (kk = 0; kk < RP; kk = kk + 1)
                                rv_vals[32*kk +: 32] = (b + kk < nv) ? scr[sp + b + kk][31:0]
                                                                     : 32'hFF80_0000;   // -inf pad (never selected)
                        end
                        @(negedge clk); rv_v = 0; rv_last = 0;
                        sp = sp + nv;
                        while (!t_v) @(negedge clk);
                        for (kk = 0; kk < need; kk = kk + 1)
                            if (t_ids[kk*IW +: IW] !== r_dat(scr[sp + kk]) || t_col !== r_idx(r)) bad_ids = bad_ids + 1;
                        sp = sp + need; n_rv = n_rv + 1;
                    end
                    OP_UNION: begin
                        @(negedge clk);
                        f_base = (cmd_op == 4'd3 ? (NL + cmd_idx) : cmd_idx) * NEXP * XL;
                        u_flush = 1; @(negedge clk); u_flush = 0;
                        cnt_u = r_pos(r);
                        for (kk = 0; kk < cnt_u; kk = kk + 1) begin
                            @(posedge clk); while (!(u_v && u_ready)) @(posedge clk);
                            if (u_id !== scr[sp + kk][IW-1:0] || u_mask !== scr[sp + kk][16 +: PMAX] ||
                                u_last !== (kk == cnt_u - 1)) begin
                                bad_union = bad_union + 1;
                                if (bad_union < 10) $display("UNION MISMATCH got %0d/%b want %0h", u_id, u_mask,
                                                             r_dat(scr[sp + kk]));
                            end
                        end
                        sp = sp + cnt_u; n_union = n_union + 1; n_unionids = n_unionids + cnt_u;
                        // the layer's experts are in SMEM before the layer completes
                        while (n_lines < nf * NSM * 2) @(posedge clk);
                    end
                    OP_LG: begin
                        nv = r_pos(r);
                        amq[amw] = r_dat(r); amw = amw + 1; n_rows = n_rows + 1;
                        for (b = 0; b < nv; b = b + LP) begin
                            @(negedge clk);
                            lg_v = 1; lg_bias_en = r[112]; lg_last = (b + LP >= nv);
                            for (kk = 0; kk < LP; kk = kk + 1) begin
                                lg_mask[kk] = (b + kk < nv);
                                lg_vals[32*kk +: 32] = (b + kk < nv) ? scr[sp + b + kk][31:0] : 32'd0;
                                lg_bias[32*kk +: 32] = (b + kk < nv) ? scr[sp + b + kk][63:32] : 32'd0;
                            end
                        end
                        @(negedge clk); lg_v = 0; lg_last = 0;
                        sp = sp + nv;
                    end
                    default: begin
                        $display("SCRIPT ERROR op %02x at %0d", r_op(r), sp - 1);
                        bad_cmd = bad_cmd + 1;
                    end
                endcase
            end
        end
    endtask
    integer nc, nt;
    task automatic report;
        begin
            $display("DSHBM %s cmds=%0d steps=%0d emitted=%0d rows=%0d gathers=%0d writes=%0d router=%0d unions=%0d union_ids=%0d lines=%0d final=%0d bad_cmd=%0d bad_gather=%0d bad_ids=%0d bad_union=%0d bad_line=%0d bad_am=%0d bad_emit=%0d bad_acc=%0d bad_final=%0d sa_err=%0d am_fault=%0d n=%0d cyc_total=%0d cyc_engine=%0d cyc_markov=%0d",
                (bad_cmd + bad_gather + bad_ids + bad_union + bad_line + bad_am + bad_emit + bad_acc + bad_final == 0 &&
                 n_emit == NGEN && amr == amw && !sa_err) ? "PASS" : "FAIL",
                nc, n_steps, n_emit, n_rows, n_gather, n_wr, n_rv, n_union, n_unionids, n_lines, n_final, bad_cmd,
                bad_gather, bad_ids, bad_union, bad_line, bad_am, bad_emit, bad_acc, bad_final, sa_err, am_fault,
                n_committed, cyc_total, cyc_engine, cyc_markov);
        end
    endtask
`ifdef HELD_RELEASE_CHECK
    // GX7 (hgi-takeover): the RSTR 4-cycle reset-tree multicycle is valid only if no input is used within 4 cycles of

    integer rel_cyc = -1;
    always @(posedge clk) begin
        if (!dut.rst_s[1]) rel_cyc <= -1;
        else if (rel_cyc < 1000) rel_cyc <= rel_cyc + 1;
        if (dut.rst_s[1] && rel_cyc < 3 && (start || x_v || eng_done)) begin
            $display("DSHBM FAIL held-release: input sampled at edge %0d after reset release (< 4)", rel_cyc + 1);
            $finish;
        end
    end
`endif
    reg [3:0] want_ncol;
    initial begin
        $readmemh(SCRIPT, scr);
        $readmemh(PROMPT, prm);
        $readmemh(FORCEF, frc);
        $readmemh(EXPECT, expv);
        for (j = 0; j < NSM; j = j + 1) cnt[j] = 0;
        for (j = 0; j < MEMW; j = j + 1) hbm.mem[j] = pat(j);
        repeat (3) @(posedge clk);
        rst_n = 1;
        repeat (2) @(posedge clk);
`ifdef HFD_MTP
`ifndef HELD_RELEASE_MUT
        repeat (4) @(posedge clk);           // the block's reset synchroniser
`endif
`endif
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        nc = 0;
        while (r_op(scr[sp]) == OP_CMD && sp < NSCR - 1) begin
            r = scr[sp];
            @(negedge clk); while (!cmd_v && !done) @(negedge clk);
            if (done) begin
                $display("DUT finished early at script record %0d", sp);
                bad_cmd = bad_cmd + 1;
            end
            want_ncol = r[3:0];
            if (cmd_op !== r[115:112] || cmd_idx !== r[103:96] || cmd_pos !== r_pos(r) ||
                cmd_ncol !== want_ncol || (cmd_op == 4'd5 && cmd_tok1 !== r[32 +: TW])) begin
                bad_cmd = bad_cmd + 1;
                if (bad_cmd < 10) $display("COMMAND MISMATCH #%0d got op %0d idx %0d pos %0d ncol %0d tok %0d, want op %0d idx %0d pos %0d ncol %0d tok %0d",
                    nc, cmd_op, cmd_idx, cmd_pos, cmd_ncol, cmd_tok1, r_kind(r), r_idx(r), r_pos(r), want_ncol,
                    r[63:32]);
            end
            if (bad_cmd) begin               // the DUT left the golden's command sequence: stop here
                report;
                $finish;
            end
            sp = sp + 1;
            nt = 0;
            while (r_op(scr[sp]) == OP_TOK) begin
                if (cmd_toks[nt*TW +: TW] !== scr[sp][TW-1:0]) begin
                    bad_cmd = bad_cmd + 1;
                    if (bad_cmd < 10) $display("TOKEN MISMATCH cmd #%0d col %0d got %0d want %0d", nc, nt,
                                               cmd_toks[nt*TW +: TW], r_dat(scr[sp]));
                end
                nt = nt + 1; sp = sp + 1;
            end
            cmd_ready = 1; @(negedge clk); cmd_ready = 0;
            do_events(0);
            if (r_op(scr[sp]) == OP_END) sp = sp + 1;
            @(negedge clk); eng_done = 1; @(negedge clk); eng_done = 0;
            nc = nc + 1;
        end
        while (!done) @(negedge clk);
        if (cmd_v) begin bad_cmd = bad_cmd + 1; $display("DUT issued a command the golden never ran"); end
        repeat (40) @(negedge clk);
        if (r_op(scr[sp]) == OP_FINAL) begin
            if (n_committed !== r_pos(scr[sp])) begin
                bad_final = bad_final + 1;
                $display("FINAL committed count %0d, golden %0d", n_committed, r_pos(scr[sp]));
            end
            sp = sp + 1;
            do_events(1);
        end
        report;
        $finish;
    end
    initial begin
        #(TIMEOUT);
        $display("DSHBM FAIL TIMEOUT sp=%0d cyc=%0d", sp, cyc);
        $finish;
    end
endmodule
