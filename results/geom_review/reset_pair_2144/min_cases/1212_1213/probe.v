module pair_probe(input ot_clk,input pr_reset_rst_rl_1211,output pr_reset_rst_rl_1212,output pr_reset_rst_rl_1212_raw,output pr_reset_rst_rl_1213,output pr_reset_rst_rl_1213_raw);
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_1212 (.CLK(ot_clk), .D(pr_reset_rst_rl_1211), .QN(pr_reset_rst_rl_1212_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_1212_drive (.A(pr_reset_rst_rl_1212_raw), .Y(pr_reset_rst_rl_1212));
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_1213 (.CLK(ot_clk), .D(pr_reset_rst_rl_1212), .QN(pr_reset_rst_rl_1213_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_1213_drive (.A(pr_reset_rst_rl_1213_raw), .Y(pr_reset_rst_rl_1213));
endmodule
