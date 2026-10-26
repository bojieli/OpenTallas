module pair_probe(input ot_clk,input pr_reset_rst_rl_585,output pr_reset_rst_rl_586,output pr_reset_rst_rl_586_raw,output pr_reset_rst_rl_587,output pr_reset_rst_rl_587_raw);
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_586 (.CLK(ot_clk), .D(pr_reset_rst_rl_585), .QN(pr_reset_rst_rl_586_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_586_drive (.A(pr_reset_rst_rl_586_raw), .Y(pr_reset_rst_rl_586));
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_587 (.CLK(ot_clk), .D(pr_reset_rst_rl_586), .QN(pr_reset_rst_rl_587_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_587_drive (.A(pr_reset_rst_rl_587_raw), .Y(pr_reset_rst_rl_587));
endmodule
