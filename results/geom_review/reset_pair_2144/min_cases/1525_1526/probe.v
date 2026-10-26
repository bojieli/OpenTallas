module pair_probe(input ot_clk,input pr_reset_rst_rl_1501,output pr_reset_rst_rl_1525,output pr_reset_rst_rl_1525_raw,output pr_reset_rst_rl_1526,output pr_reset_rst_rl_1526_raw);
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_1525 (.CLK(ot_clk), .D(pr_reset_rst_rl_1501), .QN(pr_reset_rst_rl_1525_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_1525_drive (.A(pr_reset_rst_rl_1525_raw), .Y(pr_reset_rst_rl_1525));
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_1526 (.CLK(ot_clk), .D(pr_reset_rst_rl_1525), .QN(pr_reset_rst_rl_1526_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_1526_drive (.A(pr_reset_rst_rl_1526_raw), .Y(pr_reset_rst_rl_1526));
endmodule
