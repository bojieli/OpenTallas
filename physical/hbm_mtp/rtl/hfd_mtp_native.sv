`timescale 1ns/1ps
`default_nettype none
// Default-off wiring facade. Physical x-master closure does not qualify these bus pins.
module hfd_mtp_native #(parameter integer ENABLE=0) (
  input wire clk, input wire rst_n,
  input wire [128:0] f_cmdproc,
  output wire [493:0] t_cmdproc,
  input wire [522:0] f_su_red,
  input wire [58:0] f_router,
  output wire [57:0] t_router,
  output wire [18:0] t_coll,
  input wire [0:0] f_coll
);
  generate if (ENABLE == 0) begin: off
    assign t_cmdproc = '0;
    assign t_router = '0;
    assign t_coll = '0;
  end else begin: on
    hfd_mtp_x core (
      .clk(clk), .rst_n(rst_n),
      .start(f_cmdproc[0 +: 1]),
      .cfg_gamma(f_cmdproc[1 +: 4]),
      .cfg_force(f_cmdproc[5 +: 1]),
      .cfg_ngen(f_cmdproc[6 +: 16]),
      .cfg_plen(f_cmdproc[22 +: 16]),
      .p_tok(f_cmdproc[38 +: 17]),
      .f_tok(f_cmdproc[55 +: 17]),
      .cmd_ready(f_cmdproc[72 +: 1]),
      .eng_done(f_cmdproc[73 +: 1]),
      .sr_v(f_cmdproc[74 +: 1]),
      .sr_kind(f_cmdproc[75 +: 4]),
      .sr_idx(f_cmdproc[79 +: 16]),
      .sr_pos(f_cmdproc[95 +: 32]),
      .u_clr(f_cmdproc[127 +: 1]),
      .u_flush(f_cmdproc[128 +: 1]),
      .p_addr(t_cmdproc[0 +: 16]),
      .f_addr(t_cmdproc[16 +: 16]),
      .e_v(t_cmdproc[32 +: 1]),
      .e_tok(t_cmdproc[33 +: 17]),
      .e_idx(t_cmdproc[50 +: 16]),
      .done(t_cmdproc[66 +: 1]),
      .cmd_v(t_cmdproc[67 +: 1]),
      .cmd_op(t_cmdproc[68 +: 4]),
      .cmd_idx(t_cmdproc[72 +: 8]),
      .cmd_ncol(t_cmdproc[80 +: 4]),
      .cmd_pos(t_cmdproc[84 +: 32]),
      .cmd_tok1(t_cmdproc[116 +: 17]),
      .cmd_toks(t_cmdproc[133 +: 136]),
      .am_v(t_cmdproc[269 +: 1]),
      .am_idx(t_cmdproc[270 +: 17]),
      .am_fault(t_cmdproc[287 +: 1]),
      .sr_ready(t_cmdproc[288 +: 1]),
      .sa_v(t_cmdproc[289 +: 1]),
      .sa_addr(t_cmdproc[290 +: 32]),
      .sa_tok(t_cmdproc[322 +: 17]),
      .sa_pad(t_cmdproc[339 +: 1]),
      .sa_last(t_cmdproc[340 +: 1]),
      .sa_err(t_cmdproc[341 +: 1]),
      .n_committed(t_cmdproc[342 +: 32]),
      .step_v(t_cmdproc[374 +: 1]),
      .step_a(t_cmdproc[375 +: 3]),
      .step_g(t_cmdproc[378 +: 4]),
      .steps(t_cmdproc[382 +: 16]),
      .cyc_total(t_cmdproc[398 +: 32]),
      .cyc_engine(t_cmdproc[430 +: 32]),
      .cyc_markov(t_cmdproc[462 +: 32]),
      .lg_v(f_su_red[0 +: 1]),
      .lg_last(f_su_red[1 +: 1]),
      .lg_bias_en(f_su_red[2 +: 1]),
      .lg_mask(f_su_red[3 +: 8]),
      .lg_vals(f_su_red[11 +: 256]),
      .lg_bias(f_su_red[267 +: 256]),
      .x_v(f_router[0 +: 1]),
      .x_draft(f_router[1 +: 1]),
      .x_ids(f_router[2 +: 54]),
      .x_col(f_router[56 +: 3]),
      .t_v(t_router[0 +: 1]),
      .t_ids(t_router[1 +: 54]),
      .t_col(t_router[55 +: 3]),
      .u_v(t_coll[0 +: 1]),
      .u_id(t_coll[1 +: 9]),
      .u_mask(t_coll[10 +: 8]),
      .u_last(t_coll[18 +: 1]),
      .u_ready(f_coll[0 +: 1])
    );
  end endgenerate
endmodule
`default_nettype wire
