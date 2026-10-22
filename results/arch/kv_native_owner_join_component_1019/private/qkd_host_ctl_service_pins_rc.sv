// Private same-clock COMPONENT join; no public binding activation.
// New candidate, original ND8 controller remains unchanged. Captured fault
// flags block ready even when the original done/current-generation test has
// not yet become applicable. Every intertile input is captured before logic.
// MU (MU-QWEN-HOST 10-18, opt-in, 0 = unchanged): qkd_host_ctl MU, 4-slot static calendar.
module qkd_host_ctl_service_pins_rc #(parameter WDOG=1<<22,ENABLE_SERVICE=0,MUT=0,MU=0)(
 input wire ck,rst_n,sys_ready,pb_fault,input wire[2:0]die_id,
 input wire[60:0]req,input wire[142:0]pr,input wire[743:0]tk,
 input wire service_abort,service_ready,begin_block,epoch_fault,input wire[7:0]service_ready8,
 output wire package_start_v,output wire[17:0]package_token,package_pos,output wire[1:0]package_gen,
 output wire[181:0]hc,output wire[119:0]res
);
 reg ready_q,pb_q,abort_q,service_q,block_q,epoch_fault_q;reg[60:0]req_q;reg[142:0]pr_q;reg[743:0]tk_q;reg[2:0]role_q;
 reg[7:0]services_q,faults_q;
 integer i;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
 ready_q<=0;block_q<=0;epoch_fault_q<=0;req_q<=0;pr_q<=0;tk_q<=0;pb_q<=0;abort_q<=0;service_q<=0;role_q<=0;services_q<=0;faults_q<=0;
 end else begin
 epoch_fault_q<=epoch_fault;req_q<=req;pr_q<=pr;tk_q<=tk;block_q<=begin_block;ready_q<=sys_ready;pb_q<=pb_fault;abort_q<=service_abort;service_q<=service_ready;
 role_q<=die_id;services_q<=service_ready8;
 for(i=0;i<8;i=i+1)faults_q[i]<=tk[93*i+88];
 end
 qkd_host_ctl_rc #(.ND(8),.WDOG(WDOG),.MU(MU))u_core(.ck(ck),.rst_n(rst_n),
 .ready(ready_q&&!pb_q&&role_q==0&&(MUT==1||(!abort_q&&!epoch_fault_q&&service_q&&!(|faults_q)))&&(!ENABLE_SERVICE||(MUT==2)||((&services_q)&&!block_q))),
 .package_start_v(package_start_v),.package_token(package_token),.package_pos(package_pos),.package_gen(package_gen),.req(req_q),.pr(pr_q),.tk(tk_q),.hc(hc),.res(res));
endmodule
