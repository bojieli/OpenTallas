`timescale 1ns/1ps
// QTILE-R 10-23: lockstep bench, face-pin-registered HP13 cpub39 tt_ctlm (wtnbal24 core + QTILE-R pin regs, *_pr) vs the
// RELEASE master qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1 (5d45a822, what the die binds).  Same random stimulus every
// edge; the release sees each REGISTERED input port one edge late (the static schedule launches it one edge earlier for
// the new tile) and each REGISTERED output of the new tile is compared with the release output one edge earlier; every
// other port is compared on the same edge.  MUT (runtime +MUT=n): 0 exact (must PASS); 1 release fed undelayed inputs;
// 2 outputs compared with no offset; 3 one input bit (ss5[0]) of the new tile inverted from edge 300; 4 rst_n of the new
// tile held one extra edge.  Every MUT != 0 must FAIL.
module tb_hp13_pr_lockstep #(parameter integer NCYC = 20000);
  reg ck = 0; always #5 ck = ~ck;
  integer mut = 0; initial if (!$value$plusargs("MUT=%d", mut)) mut = 0;
  integer seed = 1; initial if (!$value$plusargs("SEED=%d", seed)) seed = 1;
  integer cyc = 0;
  reg rst_n = 0;
  reg [74:0] i_pw = 0, d_pw = 0;
  reg [186:0] i_dh = 0, d_dh = 0;
  reg [0:0] i_init_u0 = 0, d_init_u0 = 0;
  reg [128:0] i_ctx_x = 0, d_ctx_x = 0;
  reg [0:0] i_mu_fault = 0, d_mu_fault = 0;
  reg [1:0] i_dh_user = 0, d_dh_user = 0;
  reg [0:0] i_kok = 0, d_kok = 0;
  reg [0:0] i_kwd = 0, d_kwd = 0;
  reg [0:0] i_fab = 0, d_fab = 0;
  reg [94:0] i_native_ret = 0, d_native_ret = 0;
  reg [106:0] i_ss5 = 0, d_ss5 = 0;
  reg [9:0] i_ag5 = 0, d_ag5 = 0;
  reg [82:0] i_f16_auth = 0, d_f16_auth = 0;
  reg [37:0] i_f16_obs = 0, d_f16_obs = 0;
  wire [75:0] n_program_obs, r_program_obs; reg [75:0] rq_program_obs = 0;
  wire [0:0] n_control_stores_ready, r_control_stores_ready; reg [0:0] rq_control_stores_ready = 0;
  wire [0:0] n_layer_context_v, r_layer_context_v; reg [0:0] rq_layer_context_v = 0;
  wire [17:0] n_native_tok, r_native_tok; reg [17:0] rq_native_tok = 0;
  wire [17:0] n_native_pos, r_native_pos; reg [17:0] rq_native_pos = 0;
  wire [5:0] n_command_stage, r_command_stage; reg [5:0] rq_command_stage = 0;
  wire [75:0] n_cal_program_obs, r_cal_program_obs; reg [75:0] rq_cal_program_obs = 0;
  wire [68:0] n_cal_descriptor_obs, r_cal_descriptor_obs; reg [68:0] rq_cal_descriptor_obs = 0;
  wire [0:0] n_cal_image_ready, r_cal_image_ready; reg [0:0] rq_cal_image_ready = 0;
  wire [55:0] n_dc, r_dc; reg [55:0] rq_dc = 0;
  wire [379:0] n_native_cmd, r_native_cmd; reg [379:0] rq_native_cmd = 0;
  wire [452:0] n_hr, r_hr; reg [452:0] rq_hr = 0;
  wire [115:0] n_cmd, r_cmd; reg [115:0] rq_cmd = 0;
  wire [1087:0] n_tl, r_tl; reg [1087:0] rq_tl = 0;
  wire [0:0] n_emb_start, r_emb_start; reg [0:0] rq_emb_start = 0;
  wire [17:0] n_emb_token, r_emb_token; reg [17:0] rq_emb_token = 0;
  wire [17:0] n_emb_position, r_emb_position; reg [17:0] rq_emb_position = 0;
  wire [1:0] n_emb_user, r_emb_user; reg [1:0] rq_emb_user = 0;
  wire [0:0] n_cf, r_cf; reg [0:0] rq_cf = 0;
  wire [16:0] n_f16_st, r_f16_st; reg [16:0] rq_f16_st = 0;
  wire [8:0] n_table_req, r_table_req; reg [8:0] rq_table_req = 0;
  reg rst_nn; always @* rst_nn = (mut == 4 && cyc == 40) ? 1'b0 : rst_n;
  function automatic [1087:0] rnd(input integer w); integer k; reg [1087:0] v; begin v = 0; for (k = 0; k < w; k = k + 32) v[k +: 32] = $urandom; rnd = v; end endfunction
  initial begin void'($urandom(seed)); end
  always @(negedge ck) begin
    cyc <= cyc + 1; rst_n <= (cyc >= 39);
    i_pw <= (cyc < 30) ? '0 : 75'(rnd(75) & rnd(75) );
    i_dh <= (cyc < 30) ? '0 : 187'(rnd(187) & rnd(187) );
    i_init_u0 <= (cyc < 30) ? '0 : 1'($urandom % 7 == 0);
    i_ctx_x <= (cyc < 30) ? '0 : 129'(rnd(129) & rnd(129) );
    i_mu_fault <= (cyc < 30) ? '0 : 1'($urandom % 7 == 0);
    i_dh_user <= (cyc < 30) ? '0 : 2'(rnd(2) & rnd(2) );
    i_kok <= (cyc < 30) ? '0 : 1'($urandom % 7 == 0);
    i_kwd <= (cyc < 30) ? '0 : 1'($urandom % 7 == 0);
    i_fab <= (cyc < 30) ? '0 : 1'($urandom % 7 == 0);
    i_native_ret <= (cyc < 30) ? '0 : 95'(rnd(95) & rnd(95) );
    i_ss5 <= (cyc < 30) ? '0 : 107'(rnd(107) & rnd(107) );
    i_ag5 <= (cyc < 30) ? '0 : 10'(rnd(10) & rnd(10) );
    i_f16_auth <= (cyc < 30) ? '0 : 83'(rnd(83) & rnd(83) );
    i_f16_obs <= (cyc < 30) ? '0 : 38'(rnd(38) & rnd(38) );
  end
  always @(posedge ck) begin
    d_pw <= i_pw;
    d_dh <= i_dh;
    d_init_u0 <= i_init_u0;
    d_ctx_x <= i_ctx_x;
    d_mu_fault <= i_mu_fault;
    d_dh_user <= i_dh_user;
    d_kok <= i_kok;
    d_kwd <= i_kwd;
    d_fab <= i_fab;
    d_native_ret <= i_native_ret;
    d_ss5 <= i_ss5;
    d_ag5 <= i_ag5;
    d_f16_auth <= i_f16_auth;
    d_f16_obs <= i_f16_obs;
    rq_program_obs <= r_program_obs;
    rq_control_stores_ready <= r_control_stores_ready;
    rq_layer_context_v <= r_layer_context_v;
    rq_native_tok <= r_native_tok;
    rq_native_pos <= r_native_pos;
    rq_command_stage <= r_command_stage;
    rq_cal_program_obs <= r_cal_program_obs;
    rq_cal_descriptor_obs <= r_cal_descriptor_obs;
    rq_cal_image_ready <= r_cal_image_ready;
    rq_dc <= r_dc;
    rq_native_cmd <= r_native_cmd;
    rq_hr <= r_hr;
    rq_cmd <= r_cmd;
    rq_tl <= r_tl;
    rq_emb_start <= r_emb_start;
    rq_emb_token <= r_emb_token;
    rq_emb_position <= r_emb_position;
    rq_emb_user <= r_emb_user;
    rq_cf <= r_cf;
    rq_f16_st <= r_f16_st;
    rq_table_req <= r_table_req;
  end
  qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1_pr u_new (
    .ck_core(ck),
    .ck_hr(ck),
    .rst_n(rst_nn),
    .pw(i_pw),
    .dh(i_dh),
    .init_u0(i_init_u0),
    .ctx_x(i_ctx_x),
    .mu_fault(i_mu_fault),
    .dh_user(i_dh_user),
    .kok(i_kok),
    .kwd(i_kwd),
    .fab(i_fab),
    .native_ret(i_native_ret),
    .ss5(i_ss5 ^ ((mut == 3 && cyc >= 300) ? 107'd1 : '0)),
    .ag5(i_ag5),
    .f16_auth(i_f16_auth),
    .f16_obs(i_f16_obs),
    .program_obs(n_program_obs),
    .control_stores_ready(n_control_stores_ready),
    .layer_context_v(n_layer_context_v),
    .native_tok(n_native_tok),
    .native_pos(n_native_pos),
    .command_stage(n_command_stage),
    .cal_program_obs(n_cal_program_obs),
    .cal_descriptor_obs(n_cal_descriptor_obs),
    .cal_image_ready(n_cal_image_ready),
    .dc(n_dc),
    .native_cmd(n_native_cmd),
    .hr(n_hr),
    .cmd(n_cmd),
    .tl(n_tl),
    .emb_start(n_emb_start),
    .emb_token(n_emb_token),
    .emb_position(n_emb_position),
    .emb_user(n_emb_user),
    .cf(n_cf),
    .f16_st(n_f16_st),
    .table_req(n_table_req));
  qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1 u_rel (
    .ck_core(ck),
    .ck_hr(ck),
    .rst_n(rst_n),
    .pw((mut == 1) ? i_pw : d_pw),
    .dh((mut == 1) ? i_dh : d_dh),
    .init_u0((mut == 1) ? i_init_u0 : d_init_u0),
    .ctx_x((mut == 1) ? i_ctx_x : d_ctx_x),
    .mu_fault((mut == 1) ? i_mu_fault : d_mu_fault),
    .dh_user(i_dh_user),
    .kok(i_kok),
    .kwd(i_kwd),
    .fab((mut == 1) ? i_fab : d_fab),
    .native_ret((mut == 1) ? i_native_ret : d_native_ret),
    .ss5((mut == 1) ? i_ss5 : d_ss5),
    .ag5((mut == 1) ? i_ag5 : d_ag5),
    .f16_auth((mut == 1) ? i_f16_auth : d_f16_auth),
    .f16_obs((mut == 1) ? i_f16_obs : d_f16_obs),
    .program_obs(r_program_obs),
    .control_stores_ready(r_control_stores_ready),
    .layer_context_v(r_layer_context_v),
    .native_tok(r_native_tok),
    .native_pos(r_native_pos),
    .command_stage(r_command_stage),
    .cal_program_obs(r_cal_program_obs),
    .cal_descriptor_obs(r_cal_descriptor_obs),
    .cal_image_ready(r_cal_image_ready),
    .dc(r_dc),
    .native_cmd(r_native_cmd),
    .hr(r_hr),
    .cmd(r_cmd),
    .tl(r_tl),
    .emb_start(r_emb_start),
    .emb_token(r_emb_token),
    .emb_position(r_emb_position),
    .emb_user(r_emb_user),
    .cf(r_cf),
    .f16_st(r_f16_st),
    .table_req(r_table_req));
  integer nmis = 0, nchg = 0, first = -1; reg any;
  reg [8191:0] prev_sig = 0, sig;
  always @(negedge ck) if (cyc > 45) begin any = 0;
    if (n_program_obs !== r_program_obs) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=program_obs new=%h exp=%h", cyc, n_program_obs, r_program_obs); end
    if (n_control_stores_ready !== r_control_stores_ready) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=control_stores_ready new=%h exp=%h", cyc, n_control_stores_ready, r_control_stores_ready); end
    if (n_layer_context_v !== ((mut == 2) ? r_layer_context_v : rq_layer_context_v)) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=layer_context_v new=%h exp=%h", cyc, n_layer_context_v, ((mut == 2) ? r_layer_context_v : rq_layer_context_v)); end
    if (n_native_tok !== ((mut == 2) ? r_native_tok : rq_native_tok)) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=native_tok new=%h exp=%h", cyc, n_native_tok, ((mut == 2) ? r_native_tok : rq_native_tok)); end
    if (n_native_pos !== ((mut == 2) ? r_native_pos : rq_native_pos)) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=native_pos new=%h exp=%h", cyc, n_native_pos, ((mut == 2) ? r_native_pos : rq_native_pos)); end
    if (n_command_stage !== r_command_stage) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=command_stage new=%h exp=%h", cyc, n_command_stage, r_command_stage); end
    if (n_cal_program_obs !== r_cal_program_obs) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=cal_program_obs new=%h exp=%h", cyc, n_cal_program_obs, r_cal_program_obs); end
    if (n_cal_descriptor_obs !== r_cal_descriptor_obs) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=cal_descriptor_obs new=%h exp=%h", cyc, n_cal_descriptor_obs, r_cal_descriptor_obs); end
    if (n_cal_image_ready !== r_cal_image_ready) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=cal_image_ready new=%h exp=%h", cyc, n_cal_image_ready, r_cal_image_ready); end
    if (n_dc !== r_dc) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=dc new=%h exp=%h", cyc, n_dc, r_dc); end
    if (n_native_cmd !== ((mut == 2) ? r_native_cmd : rq_native_cmd)) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=native_cmd new=%h exp=%h", cyc, n_native_cmd, ((mut == 2) ? r_native_cmd : rq_native_cmd)); end
    if (n_hr !== r_hr) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=hr new=%h exp=%h", cyc, n_hr, r_hr); end
    if (n_cmd !== r_cmd) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=cmd new=%h exp=%h", cyc, n_cmd, r_cmd); end
    if (n_tl !== r_tl) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=tl new=%h exp=%h", cyc, n_tl, r_tl); end
    if (n_emb_start !== r_emb_start) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=emb_start new=%h exp=%h", cyc, n_emb_start, r_emb_start); end
    if (n_emb_token !== r_emb_token) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=emb_token new=%h exp=%h", cyc, n_emb_token, r_emb_token); end
    if (n_emb_position !== r_emb_position) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=emb_position new=%h exp=%h", cyc, n_emb_position, r_emb_position); end
    if (n_emb_user !== r_emb_user) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=emb_user new=%h exp=%h", cyc, n_emb_user, r_emb_user); end
    if (n_cf !== r_cf) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=cf new=%h exp=%h", cyc, n_cf, r_cf); end
    if (n_f16_st !== r_f16_st) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=f16_st new=%h exp=%h", cyc, n_f16_st, r_f16_st); end
    if (n_table_req !== r_table_req) begin any = 1; if (nmis < 8) $display("MISMATCH cyc=%0d port=table_req new=%h exp=%h", cyc, n_table_req, r_table_req); end
    sig = {r_program_obs, r_control_stores_ready, r_layer_context_v, r_native_tok, r_native_pos, r_command_stage, r_cal_program_obs, r_cal_descriptor_obs, r_cal_image_ready, r_dc, r_native_cmd, r_hr, r_cmd, r_tl, r_emb_start, r_emb_token, r_emb_position, r_emb_user, r_cf, r_f16_st, r_table_req};
    if (sig != prev_sig) nchg = nchg + 1; prev_sig = sig;
    if (any) begin nmis = nmis + 1; if (first < 0) first = cyc; end
    if (cyc == NCYC) begin
      $display("HP13PR_LOCKSTEP %s mut=%0d seed=%0d cycles=%0d mismatching_edges=%0d first=%0d release_output_change_edges=%0d", (nmis == 0) ? "PASS" : "FAIL", mut, seed, NCYC, nmis, first, nchg);
      $finish; end
  end
endmodule
