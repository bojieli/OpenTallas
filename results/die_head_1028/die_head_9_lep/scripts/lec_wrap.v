// gold = PAIR=0 (original flat g_lane), gate = PAIR=1 (peer pair children)
module lec_gold(input ck,rst_n,input[513:0]coll_i0,coll_i1,coll_i2,coll_i3,
 output[511:0]coll_o0,coll_o1,coll_o2,coll_o3,input[1103:0]lepk_i0,output[1103:0]lepk_o0,
 input lepf_i0,input[44:0]unit_i0,output[31:0]ctrl_o0,output fault_o0,output[10:0]lw_o);
 ot_s81hd_lep0N_noidx_core #(.CH_B(4'b1111),.PAIR(0))u(.ck(ck),.rst_n(rst_n),.coll_i0(coll_i0),.coll_i1(coll_i1),
 .coll_i2(coll_i2),.coll_i3(coll_i3),.coll_o0(coll_o0),.coll_o1(coll_o1),.coll_o2(coll_o2),.coll_o3(coll_o3),
 .lepk_i0(lepk_i0),.lepk_o0(lepk_o0),.lepf_i0(lepf_i0),.unit_i0(unit_i0),.ctrl_o0(ctrl_o0),.fault_o0(fault_o0),.lw_o(lw_o));
endmodule
module lec_gate(input ck,rst_n,input[513:0]coll_i0,coll_i1,coll_i2,coll_i3,
 output[511:0]coll_o0,coll_o1,coll_o2,coll_o3,input[1103:0]lepk_i0,output[1103:0]lepk_o0,
 input lepf_i0,input[44:0]unit_i0,output[31:0]ctrl_o0,output fault_o0,output[10:0]lw_o);
 ot_s81hd_lep0N_noidx_core #(.CH_B(4'b1111),.PAIR(1))u(.ck(ck),.rst_n(rst_n),.coll_i0(coll_i0),.coll_i1(coll_i1),
 .coll_i2(coll_i2),.coll_i3(coll_i3),.coll_o0(coll_o0),.coll_o1(coll_o1),.coll_o2(coll_o2),.coll_o3(coll_o3),
 .lepk_i0(lepk_i0),.lepk_o0(lepk_o0),.lepf_i0(lepf_i0),.unit_i0(unit_i0),.ctrl_o0(ctrl_o0),.fault_o0(fault_o0),.lw_o(lw_o));
endmodule
