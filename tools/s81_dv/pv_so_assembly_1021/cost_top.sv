module pvso_cost_top(
 input wire clk,rst_n,
 input wire cfg_v,input wire[19:0]cfg_owner,input wire[20:0]cfg_position,input wire[7:0]cfg_se_jid,cfg_so_jid,
 input wire pv_v,input wire[1:0]pv_quarter,input wire[512:0]pv_d,
 input wire param_v,input wire[2:0]param_row,input wire[19:0]param_owner,input wire[20:0]param_position,input wire[511:0]param_d,
 input wire den_v,input wire[15:0]den_mask,input wire[19:0]den_owner,input wire[7:0]den_jid,
 input wire launch,
 output wire q_v,output wire[511:0]q_d,output wire ready,done,
 output wire fault,output wire[11:0]fault_code
);
 dsdv_pv_so_ingress #(.ENABLE(1))u(.*);
endmodule
