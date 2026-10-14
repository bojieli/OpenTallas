`timescale 1ns/1ps
// Qualified-ready mux is owned by this hardened leaf, after input pin flops.
// Request/status and outputs retain the actual ND8 controller pin stations.
module qkd_host_ctl_pins #(parameter WDOG=1<<22)(
 input wire ck,rst_n,sys_ready,pb_fault,input wire[2:0]die_id,
 input wire[60:0]req,input wire[142:0]pr,input wire[743:0]tk,
 output wire[181:0]hc,output wire[119:0]res
);
 reg ready_q,pb_fault_q;reg[2:0]role_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin ready_q<=0;pb_fault_q<=0;role_q<=0;end
 else begin ready_q<=sys_ready;pb_fault_q<=pb_fault;role_q<=die_id;end
 qkd_host_ctl #(.ND(8),.WDOG(WDOG))u_core(.ck(ck),.rst_n(rst_n),
 .ready(ready_q && !pb_fault_q && role_q==0),.req(req),.pr(pr),.tk(tk),.hc(hc),.res(res));
endmodule
