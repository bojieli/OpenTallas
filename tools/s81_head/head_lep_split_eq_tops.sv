`default_nettype none
module eq_gold(input wire ck,rst_n,input wire[513:0]coll_i0,coll_i1,coll_i2,coll_i3,output wire[511:0]coll_o0,coll_o1,coll_o2,coll_o3,
 input wire[1103:0]lepk_i0,output wire[1103:0]lepk_o0,input wire lepf_i0,input wire[44:0]unit_i0,
 output wire[31:0]ctrl_o0,output wire fault_o0,output wire[10:0]lw_o);
 ot_s81hd_lep0N_noidx_core #(.CH_B(4'b1111),.PAIR(1)) w(.ck(ck),.rst_n(rst_n),.coll_i0(coll_i0),.coll_i1(coll_i1),.coll_i2(coll_i2),.coll_i3(coll_i3),
  .coll_o0(coll_o0),.coll_o1(coll_o1),.coll_o2(coll_o2),.coll_o3(coll_o3),.lepk_i0(lepk_i0),.lepk_o0(lepk_o0),.lepf_i0(lepf_i0),
  .unit_i0(unit_i0),.ctrl_o0(ctrl_o0),.fault_o0(fault_o0),.lw_o(lw_o));
endmodule
module eq_gate(input wire ck,rst_n,input wire[513:0]coll_i0,coll_i1,coll_i2,coll_i3,output wire[511:0]coll_o0,coll_o1,coll_o2,coll_o3,
 input wire[1103:0]lepk_i0,output wire[1103:0]lepk_o0,input wire lepf_i0,input wire[44:0]unit_i0,
 output wire[31:0]ctrl_o0,output wire fault_o0,output wire[10:0]lw_o);
 ot_s81hd_lep0N_split_core #(.CH_B(4'b1111),.LOCAL_RST(0)) w(.ck(ck),.rst_n(rst_n),.coll_i0(coll_i0),.coll_i1(coll_i1),.coll_i2(coll_i2),.coll_i3(coll_i3),
  .coll_o0(coll_o0),.coll_o1(coll_o1),.coll_o2(coll_o2),.coll_o3(coll_o3),.lepk_i0(lepk_i0),.lepk_o0(lepk_o0),.lepf_i0(lepf_i0),
  .unit_i0(unit_i0),.ctrl_o0(ctrl_o0),.fault_o0(fault_o0),.lw_o(lw_o));
endmodule
`default_nettype wire
