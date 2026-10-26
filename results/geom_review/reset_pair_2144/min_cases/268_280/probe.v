module pair_probe(input ot_clk,input pr_reset_rst_rl_267,output pr_reset_rst_rl_268,output pr_reset_rst_rl_268_raw,output pr_reset_rst_rl_280,output pr_reset_rst_rl_280_raw);
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_268 (.CLK(ot_clk), .D(pr_reset_rst_rl_267), .QN(pr_reset_rst_rl_268_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_268_drive (.A(pr_reset_rst_rl_268_raw), .Y(pr_reset_rst_rl_268));
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_280 (.CLK(ot_clk), .D(pr_reset_rst_rl_268), .QN(pr_reset_rst_rl_280_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_280_drive (.A(pr_reset_rst_rl_280_raw), .Y(pr_reset_rst_rl_280));
endmodule
