module composed_syntax(input wire clk);
 tb_dsrom_system #(.KV_COMPLETION(1),.USERS(1),.LINK_RT(0)) system_top(.clk(clk));
 ot_dsrom_ckv_credit_completion #(.KV_COMPLETION(1),.AG_CREDIT(1),.K(16),.NSLOT(16)) credit(.clk(clk));
endmodule
