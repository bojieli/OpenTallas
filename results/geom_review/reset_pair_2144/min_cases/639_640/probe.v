module pair_probe(input ot_clk,input pr_reset_rst_rl_638,output pr_reset_rst_rl_639,output pr_reset_rst_rl_639_raw,output pr_reset_rst_rl_640,output pr_reset_rst_rl_640_raw);
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_639 (.CLK(ot_clk), .D(pr_reset_rst_rl_638), .QN(pr_reset_rst_rl_639_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_639_drive (.A(pr_reset_rst_rl_639_raw), .Y(pr_reset_rst_rl_639));
  DFFHQNx1_ASAP7_75t_R pr_reset_u_rrl_640 (.CLK(ot_clk), .D(pr_reset_rst_rl_639), .QN(pr_reset_rst_rl_640_raw));
  (* keep, dont_touch *) BUFx4f_ASAP7_75t_R pr_reset_u_rrl_640_drive (.A(pr_reset_rst_rl_640_raw), .Y(pr_reset_rst_rl_640));
endmodule
