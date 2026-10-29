`timescale 1ns/1ps
// KV-TOK 10-24: the COMPUTE-DIE FAR END of the KV die's UCIe d2d link, for the token phase of tb_kvslice (+FAR=1).
// Bench side of the off-die boundary (owner 10-14: only PHY / off-chip modelled; this module is the peer die).
// Real RTL (the compute die's own link end, as the QC die binds it):
//   qfd_d2d_static   PR 1, TXDP = D2D_TXDP_C of the pair image the KV boot image carries (d2d_cal_image_kv41.svh)
//   ot_qwen_d2d_cal_seq  the compute calendar sequencer with that image's C calendars / segment bases / START table,
//                    ADM 1 (ADM_OFS / ADM_LEN), AUTO 1 (= the compute face's token loop on the same anchor rule:
//                    FIRST_OFS, then every PERIOD edges after the epoch strobe), EP_SKEW 0
//   qkd_native_attention_record KV_SIDE 0   the compute-side typed record codec (CMD / Q out, RESULT / STATUS in)
//   qfd_kvn_static_transport                the compute die's fixed-slot KVN transport (x3 words)
// Modelled: the compute die's seam relays between its d2d master and its producers / consumers as register chains of
//   the pair image's die stages (XDIE_DIE_STAGES compute half: CS_TXS 2, CS_RXV 2, CS_RXP 2, CS_X3S 3, SC_TX 2,
//   SC_X3 2); the producer capture latency so that the master's TXDP_C law holds (port 0 native: 8 = 2 pin flops +
//   CS_TXS + codec 1 + E0 + SC_TX -> E0 = 1; port 3 x3: 10 = 2 + CS_X3S + transport 1 + E3 + SC_X3 -> E3 = 2; port 1
//   witness: 3 = 2 + 1); the compute die's UCIe macro (the macro's own model, pin-to-pin LAT both ways);
//   the forwarded epoch / link-reset bump: compute pin = the KV die's bump pad (sys_c u_fwb_ep.a) + EPB package edges.
// Stimulus content (declared): every compute TX slot the calendar opens is filled by its compiled kind / beat:
//   kind 1 CMD = {position T-1, valid}, kind 2 Q beat b = q.hex words 16b..16b+15 (the same q every layer);
//   KVN word j (tags {010, 00000, j1 0 j0}) = the new position's K row (j 0, 1) / V row (j 2, 3), 512-b halves of
//   kv.hex row T-1 / 2T-1; record epoch / status epoch = the KV die's host token epoch (the compute die's own host
//   hands it the same epoch; fixture).  The witness record = a fixed observed record (as tb_qwen_d2d_program).
// TOK-QK-KVL 10-27 per-layer mode (+VECL=<dir>, replaces +VEC): every layer n has its own operands dir/L<n>/q.hex (512
//   FP32), gold.hex (512 FP32) and kvn.hex (2 lines of 1024 b: the new position's K row, then its V row), selected by the
//   layer the compute calendar is running (lay_q, for CMD / Q / KVN) and by the layer field of the received RESULT record
//   (ca_rl, for the check).  The KV history of layer n is that layer's own HBM rows (kv_preload.py per layer).
//   Mutant m4 +MUT_QSWAP: layer n is fed the q of layer n^1 (the per-layer selection must be visible in RESULT).
//   FAR_LAYER lines: per layer, RESULT beats ok / bad and the first / last RESULT cycle (the measured per-layer timing).
// Checks: every RESULT word (kind 3, beat b, word j) == gold[16b + j] for every layer run; STATUS (kind 4) = {done 1,
//   ready 1}; no compute-side fault (master, sequencer, codec, transport).  Counters reported by the bench.
module kvs_compute_end #(
    parameter integer CS_TXS = 2, CS_RXV = 2, CS_RXP = 2, CS_X3S = 3, SC_TX = 2, SC_X3 = 2,
    parameter integer E0 = 1, E3 = 2, PHY_LAT = 5, UP = 16
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         en,
    input  wire [4:0]   epb,
    input  wire [15:0]  epoch,
    input  wire [12:0]  pos,             // T - 1
    input  wire         kv_tx_v,         // KV die d2d TX at its UCIe bumps (macro line side)
    input  wire [582:0] kv_tx_flit,
    input  wire         kv_fwd_ep_pad,
    input  wire         kv_fwd_lrst_pad,
    input  wire         mut_cmd_late,    // m1: CMD record one edge late (producer)
    output wire         c2k_v,
    output wire [582:0] c2k_flit
);
    `include "d2d_cal_image_kv41.svh"
    localparam integer FW = 548;
    // ---------------- operands
    reg [31:0]   q   [0:511];
    reg [31:0]   gold[0:511];
    reg [1023:0] kv  [0:16383];
    localparam integer NL = 36;
    reg [31:0]   q_l   [0:NL*512-1];
    reg [31:0]   gold_l[0:NL*512-1];
    reg [1023:0] kvn_l [0:2*NL-1];
    reg          perlayer = 0, mut_qswap = 0;
    integer T = 256;
    initial begin : ld
        string v, vl;
        if (!$value$plusargs("VEC=%s", v)) v = "";
        if (!$value$plusargs("VECL=%s", vl)) vl = "";
        if (!$value$plusargs("CTX=%d", T)) T = 256;
        mut_qswap = $test$plusargs("MUT_QSWAP");
        if (vl != "") begin
            perlayer = 1;
            for (int n = 0; n < NL; n++) begin
                $readmemh($sformatf("%s/L%0d/q.hex", vl, n), q_l, 512 * n, 512 * n + 511);
                $readmemh($sformatf("%s/L%0d/gold.hex", vl, n), gold_l, 512 * n, 512 * n + 511);
                $readmemh($sformatf("%s/L%0d/kvn.hex", vl, n), kvn_l, 2 * n, 2 * n + 1);
            end
            $display("FAR_VECL %s layers %0d T %0d mut_qswap %0d q0 %h gold0 %h q35 %h", vl, NL, T, mut_qswap, q_l[0], gold_l[0],
                     q_l[512 * 35]);
        end else if (v != "") begin
            $readmemh({v, "/q.hex"}, q); $readmemh({v, "/gold.hex"}, gold); $readmemh({v, "/kv.hex"}, kv, 0, 2 * T - 1);
        end
    end
    // per-layer operand selection (lay_q: the layer the compute calendar runs; m4 feeds layer n^1's q)
    function automatic [31:0] q_at(input [5:0] l, input integer i);
        automatic integer ql = mut_qswap ? (l ^ 1) : l;
        q_at = perlayer ? q_l[512 * (ql % NL) + i] : q[i];
    endfunction
    function automatic [31:0] gold_at(input [5:0] l, input integer i);
        gold_at = perlayer ? gold_l[512 * (l % NL) + i] : gold[i];
    endfunction
    // ---------------- bumps (package edges after the KV pad)
    reg [31:0] ep_sr = 0, lr_sr = 32'hffffffff;
    always @(posedge ck) begin ep_sr <= {ep_sr[30:0], kv_fwd_ep_pad}; lr_sr <= {lr_sr[30:0], kv_fwd_lrst_pad}; end
    wire c_fwd_ep = (epb == 0) ? kv_fwd_ep_pad : ep_sr[epb - 1];
    wire c_fwd_lr = (epb == 0) ? kv_fwd_lrst_pad : lr_sr[epb - 1];
    // ---------------- PHY: the compute die's own UCIe macro (TOK-KV-1 10-28: the hard macro's simulation model, the far
    // macro of the KV die's sys_c u_ucie_rom; line side = the KV die top's sys_c_link_* / sys_c_far_* bumps)
    wire c_phy_rst_n, c_ptx_v; wire [582:0] c_ptx;
    wire c_up, c_prx_v0, c_lv; wire [582:0] c_prx, c_lf;
    ot_qkvd_ucie_x64_phy_model #(.LAT(PHY_LAT), .UP(UP), .FW(583)) u_cphy (.clk(ck), .rst_n(c_phy_rst_n), .tx_up(c_up),
        .tx_v(c_ptx_v), .tx_flit(c_ptx), .rx_v(c_prx_v0), .rx_flit(c_prx), .link_v(c_lv), .link_flit(c_lf),
        .far_v(kv_tx_v), .far_flit(kv_tx_flit));
    wire c_prx_v = c_prx_v0 & en;
    assign c2k_v = en & c_lv; assign c2k_flit = en ? c_lf : 583'd0;
    // ---------------- calendar sequencer (pair image C half)
    wire s_tx, s_rx, s_cs, s_sg, s_rdy, s_run, s_ad, s_ts, s_f, c_abort; wire [5:0] s_a, s_l; wire [31:0] s_d;
    ot_qwen_d2d_cal_seq #(.TX_IMG(D2D_CAL_C_TX_IMG), .RX_IMG(D2D_CAL_C_RX_IMG), .TX_SEG1(D2D_CAL_C_TX_SEG1),
        .RX_SEG1(D2D_CAL_C_RX_SEG1), .START(D2D_CAL_START), .ADM(1), .TX_SEG2(D2D_CAL_C_TX_SEG2), .RX_SEG2(D2D_CAL_C_RX_SEG2),
        .ADM_OFS(D2D_ADM_OFS), .ADM_LEN(D2D_ADM_LEN), .AUTO(1), .FIRST_OFS(D2D_FIRST_TOKEN), .PERIOD(D2D_TOKEN_PERIOD),
        .EP_SKEW(0)) u_cseq (.ck(ck), .rst_n(rst_n & en), .reload(1'b0), .tok_go(1'b0), .epoch_go(c_fwd_ep), .halt(c_abort),
        .cfg_tx_we(s_tx), .cfg_rx_we(s_rx), .cfg_addr(s_a), .cfg_data(s_d), .cal_start(s_cs), .cal_seg(s_sg),
        .cal_ready(s_rdy), .running(s_run), .layer(s_l), .adm_done(s_ad), .tok_start(s_ts), .fault(s_f));
    // ---------------- the compute die's d2d master
    wire c_txs0, c_rxe0, c_rxs0; wire [3:0] c_tk, c_rk; wire [4:0] c_tb, c_rb; wire [FW-1:0] c_rxp; wire c_tv0; wire [FW-1:0] c_tp0;
    wire c_f; wire [7:0] c_tf; wire c_prog_rxv, c_prog_auth, c_prog_ctx, c_prog_wslot, c_emb_v, c_emb_s, kv_x3_slot;
    wire [523:0] x3; wire [58:0] x3_id; wire [1:0] x3_gen;
    reg [5:0] lay_q = 0; always @(posedge ck) if (s_cs) lay_q <= s_l;
    reg st_res = 0; integer since_tok = 1 << 30;
    always @(posedge ck) begin since_tok <= (s_cs && s_sg && s_l == 0) ? 0 : since_tok + 1; st_res <= (since_tok == 20); end
    wire c_wit_v; wire [547:0] c_wit_p;
    reg c_wit_d = 0; always @(posedge ck) c_wit_d <= c_prog_wslot;
    assign c_wit_v = c_wit_d; assign c_wit_p = c_wit_d ? {18'h2a5a5, 2'd3, 528'h717} : 548'd0;
    qfd_d2d_static #(.MUT(0), .PR(1), .TXDP(D2D_TXDP_C)) u_c (.ck(ck), .por_n(rst_n & en), .rst_n(rst_n & en),
        .cfg_tx_we(s_tx), .cfg_rx_we(s_rx), .cfg_addr(s_a), .cfg_data(s_d), .cal_start(s_cs), .cal_seg(s_sg),
        .fwd_epoch(c_fwd_ep), .fwd_link_rst_n(c_fwd_lr),
        .native_tx_slot(c_txs0), .native_tx_slot_kind(c_tk), .native_tx_slot_beat(c_tb), .native_tx_v(c_tv0),
        .native_tx_payload(c_tp0), .rx_payload(c_rxp), .native_rx_v(c_rxe0), .native_rx_slot(c_rxs0),
        .native_rx_slot_kind(c_rk), .native_rx_slot_beat(c_rb),
        .prog_witness_slot(c_prog_wslot), .prog_auth_slot(c_prog_auth), .prog_context_slot(c_prog_ctx),
        .prog_tx_observed_v(c_wit_v), .prog_tx_record(c_wit_p), .prog_rx_v(c_prog_rxv), .emb_rx_v(c_emb_v), .emb_rx_slot(c_emb_s),
        .kv_x3_slot(kv_x3_slot), .x3(x3), .x3_identity(x3_id), .x3_generation(x3_gen),
        .status_epoch16(epoch), .vm_drained(1'b1), .collective_drained(1'b1), .collective_busy(1'b0),
        .crom_fault(1'b0), .execution_active(1'b1), .admit_ready(1'b1),
        .result_v(st_res), .result_done(1'b1), .result_fault(1'b0), .result_cause(4'd0), .result_tag(59'd0),
        .result_gen(2'd0), .result_token(18'd0), .result_value(32'd0), .result_cycles(32'd0),
        .fdi_tx_up(c_up), .fdi_tx_v(c_ptx_v), .fdi_tx_flit(c_ptx), .fdi_rx_v(c_prx_v), .fdi_rx_flit(c_prx),
        .phy_rst_n(c_phy_rst_n), .epoch_abort(c_abort), .transport_fault(c_tf), .fault(c_f));
    wire c_eb = u_c.u_core.eb;
    // ---------------- compute seam relays + producers
    wire n_txs; wire [3:0] n_tk; wire [4:0] n_tb; wire n_rxv, n_rxs; wire [3:0] n_rk; wire [4:0] n_rb; wire [FW-1:0] n_rxp;
    wire n_x3s; wire p_tv; wire [FW-1:0] p_tp; wire [523:0] p_x3; wire [58:0] p_x3id; wire [1:0] p_x3g;
    kvs_dly #(10, CS_TXS + E0) d_txs (.ck(ck), .a({c_txs0, c_tk, c_tb}), .b({n_txs, n_tk, n_tb}));
    kvs_dly #(11, CS_RXV) d_rxv (.ck(ck), .a({c_rxe0, c_rxs0, c_rk, c_rb}), .b({n_rxv, n_rxs, n_rk, n_rb}));
    kvs_dly #(FW, CS_RXP) d_rxp (.ck(ck), .a(c_rxp), .b(n_rxp));
    kvs_dly #(1, CS_X3S + E3) d_x3s (.ck(ck), .a(kv_x3_slot), .b(n_x3s));
    kvs_dly #(1 + FW, SC_TX) d_tx (.ck(ck), .a({p_tv, p_tp}), .b({c_tv0, c_tp0}));
    kvs_dly #(524 + 59 + 2, SC_X3) d_x3 (.ck(ck), .a({p_x3, p_x3id, p_x3g}), .b({x3, x3_id, x3_gen}));
    // m1: the CMD record one edge late (event and payload; the slot stays compiled)
    reg n_txs_q = 0; reg [3:0] n_tk_q = 0; reg [4:0] n_tb_q = 0;
    always @(posedge ck) begin n_txs_q <= n_txs; n_tk_q <= n_tk; n_tb_q <= n_tb; end
    wire       ev_cmd_late = mut_cmd_late && n_txs_q && n_tk_q == 4'd1;
    wire       ev = mut_cmd_late ? ((n_txs && n_tk != 4'd1) || ev_cmd_late) : n_txs;
    wire [3:0] ek = ev_cmd_late ? n_tk_q : n_tk;
    wire [4:0] eb = ev_cmd_late ? n_tb_q : n_tb;
    reg [511:0] ed;
    always @* begin
        ed = 512'd0;
        if (ek == 4'd1) ed = {493'd0, 5'd0, pos, 1'b1};
        else if (ek == 4'd2) for (int j = 0; j < 16; j++) ed[32*j +: 32] = q_at(lay_q, 16 * eb + j);
    end
    wire ca_rv, ca_f; wire [3:0] ca_rk, ca_fc; wire [15:0] ca_re; wire [5:0] ca_rl; wire [4:0] ca_rb; wire [511:0] ca_rd;
    qkd_native_attention_record #(.KV_SIDE(0)) u_ca (.ck(ck), .rst_n(rst_n & en & ~c_eb),
        .tx_event(ev), .tx_expected(n_txs), .tx_kind(ek), .tx_expected_kind(n_tk),
        .tx_epoch(epoch), .tx_expected_epoch(epoch), .tx_layer(lay_q), .tx_expected_layer(lay_q),
        .tx_beat(eb), .tx_expected_beat(n_tb), .tx_data(ed), .tx_valid(p_tv), .tx_payload(p_tp),
        .rx_event(n_rxv), .rx_expected(n_rxs), .rx_payload(n_rxp), .rx_expected_kind(n_rk),
        .rx_expected_epoch(epoch), .rx_expected_layer(lay_q), .rx_expected_beat(n_rb),
        .rx_valid(ca_rv), .rx_kind(ca_rk), .rx_epoch(ca_re), .rx_layer(ca_rl), .rx_beat(ca_rb), .rx_data(ca_rd),
        .fault(ca_f), .fault_cause(ca_fc));
    // KVN: word j pushed into the transport's 2 seats one edge before its x3 slot reaches the transport (as
    // tb_qwen_d2d_program); j counts the layer's x3 slots (reset at every run start)
    function automatic [2:0] ktag(input integer j); ktag = {1'(j >> 1), 1'b0, 1'(j & 1)}; endfunction
    wire x3_pre;
    kvs_dly #(1, CS_X3S + E3 - 1) d_x3pre (.ck(ck), .a(kv_x3_slot), .b(x3_pre));
    reg [2:0] kn = 0;
    always @(posedge ck) if (s_cs) kn <= 0; else if (x3_pre && kn < 4) kn <= kn + 1;
    wire kvn_push = en && x3_pre && kn < 4;
    wire [1:0] kj = kn[1:0];
    wire [1023:0] kn_k = perlayer ? kvn_l[2 * (lay_q % NL)] : kv[T - 1];
    wire [1023:0] kn_v = perlayer ? kvn_l[2 * (lay_q % NL) + 1] : kv[2 * T - 1];
    wire [511:0] kw_d = kj[1] ? (kj[0] ? kn_v[1023:512] : kn_v[511:0]) : (kj[0] ? kn_k[1023:512] : kn_k[511:0]);
    wire kvt_f;
    qfd_kvn_static_transport u_kvt (.ck(ck), .rst_n(rst_n & en & ~c_eb), .word_v(kvn_push), .word_tag({3'b010, 5'd0, ktag(kj)}),
        .word_data(kw_d), .word_identity({epoch, 6'(lay_q + 1), 18'd0, pos, 6'd0}), .word_generation(2'd0), .slot_v(n_x3s),
        .x3(p_x3), .x3_identity(p_x3id), .x3_generation(p_x3g), .fault(kvt_f));
    // ---------------- checks / counters
    integer n_res = 0, n_res_ok = 0, n_res_bad = 0, n_stat = 0, n_stat_ok = 0, n_tok = 0, n_adm = 0, n_layers = 0, n_emb = 0;
    integer f_first = -1, cyc = 0; reg [7:0] f_what = 0;
    integer lay_ok [0:63], lay_bad [0:63], lay_r0 [0:63], lay_r1 [0:63], lay_cs [0:63];
    initial for (int i = 0; i < 64; i++) begin lay_ok[i] = 0; lay_bad[i] = 0; lay_r0[i] = -1; lay_r1[i] = -1; lay_cs[i] = -1; end
    always @(posedge ck) if (en && rst_n) begin
        cyc <= cyc + 1;
        if (s_cs && s_l == 6'h3f) n_adm <= n_adm + 1;
        if (s_cs && s_l == 0 && s_sg) n_tok <= n_tok + 1;
        if (s_cs && s_l != 6'h3f) n_layers <= n_layers + 1;
        if (c_emb_v) n_emb <= n_emb + 1;
        if (ca_rv && ca_rk == 4'd3) begin
            automatic reg ok = 1;
            for (int j = 0; j < 16; j++) if (ca_rd[32*j +: 32] !== gold_at(ca_rl, 16 * ca_rb + j)) ok = 0;
            n_res <= n_res + 1;
            if (lay_r0[ca_rl] < 0) lay_r0[ca_rl] <= cyc;
            lay_r1[ca_rl] <= cyc;
            if (ok) begin n_res_ok <= n_res_ok + 1; lay_ok[ca_rl] <= lay_ok[ca_rl] + 1; end
            else begin
                n_res_bad <= n_res_bad + 1; lay_bad[ca_rl] <= lay_bad[ca_rl] + 1;
                if (n_res_bad < 8) $display("FAR_RESULT_MISMATCH cyc %0d layer %0d beat %0d got %h want %h..", cyc, ca_rl, ca_rb,
                                            ca_rd[31:0], gold_at(ca_rl, 16 * ca_rb));
            end
            if (ca_rb == 5'd31)
                $display("FAR_LAYER layer %0d cal_start %0d result_first %0d result_last %0d ok %0d bad %0d (beats of this word incl.)",
                         ca_rl, lay_cs[ca_rl], lay_r0[ca_rl] < 0 ? cyc : lay_r0[ca_rl], cyc, lay_ok[ca_rl] + ok, lay_bad[ca_rl] + !ok);
        end
        if (ca_rv && ca_rk == 4'd4) begin
            n_stat <= n_stat + 1;
            if (ca_rd[3] && ca_rd[0] && !ca_rd[2]) n_stat_ok <= n_stat_ok + 1;
            else $display("FAR_STATUS cyc %0d layer %0d word %h", cyc, ca_rl, ca_rd[7:0]);
        end
        if ((c_f || s_f || ca_f || kvt_f || c_abort) && f_first < 0) begin
            f_first <= cyc; f_what <= {3'd0, c_abort, kvt_f, ca_f, s_f, c_f};
            $display("FAR_FAULT cyc %0d master %0d seq %0d codec %0d (cause %b) kvn %0d abort %0d transport %h layer %0d",
                     cyc, c_f, s_f, ca_f, ca_fc, kvt_f, c_abort, c_tf, lay_q);
        end
    end
    always @(posedge ck) if (en && rst_n && s_cs && s_l != 6'h3f && lay_cs[s_l] < 0) lay_cs[s_l] <= cyc;
    always @(posedge ck) if (en && rst_n && s_cs)
        $display("FAR_CAL cyc %0d cal_start seg %0d layer %0d (adm %0d ready %0d)", cyc, s_sg, s_l, s_ad, s_rdy);
    task report;
        $display("FAR_SUMMARY admissions %0d tokens %0d runs %0d results %0d ok %0d bad %0d status %0d ok %0d emb_words %0d first_fault %0d (%b) cal_ready %0d",
                 n_adm, n_tok, n_layers, n_res, n_res_ok, n_res_bad, n_stat, n_stat_ok, n_emb, f_first, f_what, s_rdy);
        for (int n = 0; n < NL; n++)
            $display("FAR_LAYER_SUMMARY layer %0d ok %0d bad %0d cal_start %0d result_first %0d result_last %0d %s", n, lay_ok[n],
                     lay_bad[n], lay_cs[n], lay_r0[n], lay_r1[n], (lay_ok[n] == 32 && lay_bad[n] == 0) ? "PASS" : "FAIL");
    endtask
endmodule

module kvs_dly #(parameter integer W = 1, parameter integer D = 0) (input wire ck, input wire [W-1:0] a, output wire [W-1:0] b);
    generate if (D == 0) begin : g0
        assign b = a;
    end else begin : gd
        reg [W-1:0] r [0:D-1];
        always @(posedge ck) begin r[0] <= a; for (int i = 1; i < D; i++) r[i] <= r[i-1]; end
        assign b = r[D-1];
    end endgenerate
endmodule
