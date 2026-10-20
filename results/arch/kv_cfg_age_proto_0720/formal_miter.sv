module cfg_age_miter(input wire ck,por_n,cfg_we,input wire[7:0]cfg_addr,input wire[63:0]cfg_data,output wire equal_outputs);
wire[159:0] a0,b0,c0,a1,b1,c1;wire[343:0]r0,r1;wire cap0,cap1,s0,s1,f0,f1;wire[31:0]at0,at1;wire[15:0]pv0,pv1;wire[255:0]vp0,vp1;
qkd_kv_die_cfg_a #(.NRST(43),.CAP(1),.AGES(1))gold(.ck(ck),.por_n(por_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.ectl_a_cfg(a0),.ectl_b_cfg(b0),.ectl_c_cfg(c0),.rst_dly(r0),.fused_program_capability(cap0),.age_attn(at0),.age_pv(pv0),.age_vport(vp0),.sealed(s0),.fault(f0));
qkd_kv_die_cfg_a_s32_age #(.NRST(43),.CAP(1),.AGES(1),.S32(1))candidate(.ck(ck),.por_n(por_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.ectl_a_cfg(a1),.ectl_b_cfg(b1),.ectl_c_cfg(c1),.rst_dly(r1),.fused_program_capability(cap1),.age_attn(at1),.age_pv(pv1),.age_vport(vp1),.sealed(s1),.fault(f1));
assign equal_outputs=({a0,b0,c0,r0,cap0,at0,pv0,vp0,s0,f0}=={a1,b1,c1,r1,cap1,at1,pv1,vp1,s1,f1});
endmodule
