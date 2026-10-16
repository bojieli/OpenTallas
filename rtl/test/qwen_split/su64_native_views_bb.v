// Q-ELEM-SUC 2026-10-16: lint-only blackboxes of the closed native SU child views (the parent route binds their LEF/LIB).
(* blackbox *) module qfd_su_lane_h_native_crom5(input clk,input rst_n,input emit0,input live,input [17:0] i,input [18:0] fin_th,input i_last_r,
 input [23:0] cura0,curb0,curc0,curd0,rrow,asi,bsi,csi,dsi,input asrc,bsrc,csrc,mc,md,redsq,input [1:0] ma,mb,dst,red,input [2:0] ad,
 input [31:0] imm1,imm2,input [2:0] cls,input accept,input [2:0] i_sfu,output va_re,output [23:0] va_addr,input [31:0] va_q,
 output vb_re,output [23:0] vb_addr,input [31:0] vb_q,output vc_re,output [23:0] vc_addr,input [31:0] vc_q,output wrom_re,
 output [23:0] wrom_addr,input [255:0] wrom_q,output crom_re,output [23:0] crom_addr,input [63:0] crom_q,output vm_we,
 output [23:0] vm_waddr,output [31:0] vm_wdata,output kv_we,output [23:0] kv_waddr,output [31:0] kv_wdata,output l_ov,
 output [31:0] l_out,output [1:0] l_red,output l_redsq,output [23:0] l_raddr,output l_last,output retire,output l_fault,
 output sx_exp_v,output [31:0] sx_exp_x,input [31:0] sy_exp_y,input sy_exp_vo,input sy_exp_f,output sx_rcp_v,output [31:0] sx_rcp_x,
 input [31:0] sy_rcp_y,input sy_rcp_f,output sx_rsq_v,output [31:0] sx_rsq_x,input [31:0] sy_rsq_y,input sy_rsq_f);
endmodule
(* blackbox *) module qfd_su_sfu_exp_native45(input clk,rst_n,v,input [31:0] x,output [31:0] y,output vo,fault); endmodule
(* blackbox *) module qfd_su_sfu_rcp_native45(input clk,rst_n,v,input [31:0] x,output [31:0] y,output vo,fault); endmodule
(* blackbox *) module qfd_su_sfu_rsq_native45(input clk,rst_n,v,input [31:0] x,output [31:0] y,output vo,fault); endmodule
