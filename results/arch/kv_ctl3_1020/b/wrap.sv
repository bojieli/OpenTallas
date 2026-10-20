module dcfg_wrap #(parameter integer S32 = 1) (input ck, por_n, cfg_we, input [7:0] cfg_addr, input [63:0] cfg_data,
  output [159:0] ea, output cap, sealed, fault);
  qkd_kv_die_cfg #(.NRST(43),.CAP(1),.MUT(0),.PCOPIES(1),.S32(S32)) u(.ck(ck),.por_n(por_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
   .ectl_a_cfg(ea),.ectl_b_cfg(),.ectl_c_cfg(),.rst_dly(),.fused_program_capability(cap),.sealed(sealed),.fault(fault));
endmodule
