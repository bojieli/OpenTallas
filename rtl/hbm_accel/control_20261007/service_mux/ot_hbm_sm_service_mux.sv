// Model:tools/hbm_sm_service_mux_model.py. Local finite boundary, not a remote ready wire.
module ot_hbm_sm_service_mux #(parameter ENABLE=0,NCLIENT=4,SW=$clog2(NCLIENT),QB=404+SW)(
 input wire clk,rst_n,
 input wire[NCLIENT-1:0]c_req_v,output wire[NCLIENT-1:0]c_req_r,input wire[NCLIENT-1:0]c_req_we,
 input wire[NCLIENT*37-1:0]c_req_addr,input wire[NCLIENT*256-1:0]c_req_data,input wire[NCLIENT*16-1:0]c_req_tag,input wire[NCLIENT*94-1:0]c_req_context,
 output wire[NCLIENT-1:0]c_rsp_v,input wire[NCLIENT-1:0]c_rsp_r,output wire[NCLIENT-1:0]c_rsp_we,c_rsp_error,c_rsp_identity_checked,c_rsp_context_checked,
 output wire[NCLIENT*256-1:0]c_rsp_data,output wire[NCLIENT*16-1:0]c_rsp_tag,output wire[NCLIENT*192-1:0]c_rsp_identity,output wire[NCLIENT*94-1:0]c_rsp_context,
 output wire req_v,input wire req_r,output wire req_we,output wire[36:0]req_addr,
 output wire[255:0]req_data,output wire[15:0]req_tag,output wire[93:0]issuer_context,
 input wire rsp_v,output wire rsp_r,input wire rsp_we,input wire[255:0]rsp_data,input wire[15:0]rsp_tag,
 input wire[191:0]rsp_identity,input wire service_fault,output wire fault
);
 localparam[3:0]IDLE=1,SEND=2,WAIT=4,HELD=8;
 (* keep=1,dont_touch=1 *)reg[QB-1:0]q,qn;
 (* keep=1,dont_touch=1 *)reg[464:0]r,rn;
 (* keep=1,dont_touch=1 *)reg[3:0]state,state_n;
 (* keep=1,dont_touch=1 *)reg bad,bad_n;
 wire legal_state=state==IDLE||state==SEND||state==WAIT||state==HELD;
 wire mismatch=q!=~qn||r!=~rn||state!=~state_n||bad==bad_n||!legal_state;
 wire blocked=bad||mismatch||service_fault;
 assign fault=ENABLE&&blocked;
 reg[SW-1:0]select;reg found;
 always @*begin select=0;found=0;for(integer i=NCLIENT-1;i>=0;i=i-1)if(c_req_v[i])begin select=SW'(i);found=1;end end
 wire[SW-1:0]client=q[QB-1:404];
 assign issuer_context=q[93:0];
 assign req_addr=q[403:367];assign req_we=q[366];assign req_data=q[365:110];assign req_tag=q[109:94];
 assign req_v=ENABLE&&state==SEND&&!blocked;
 assign rsp_r=ENABLE&&state==WAIT&&!blocked;
 for(genvar k=0;k<NCLIENT;k=k+1)begin:c
 assign c_req_r[k]=ENABLE&&state==IDLE&&found&&select==k&&!blocked;
 assign c_rsp_v[k]=ENABLE&&state==HELD&&client==k&&!blocked;
 assign c_rsp_we[k]=r[464];assign c_rsp_tag[k*16+:16]=r[463:448];assign c_rsp_data[k*256+:256]=r[447:192];
 assign c_rsp_identity[k*192+:192]=r[191:0];assign c_rsp_context[k*94+:94]=q[93:0];assign c_rsp_error[k]=0;
 assign c_rsp_identity_checked[k]=c_rsp_v[k];assign c_rsp_context_checked[k]=c_rsp_v[k];
 end
 wire[QB-1:0]selected={select,c_req_addr[select*37+:37],c_req_we[select],c_req_data[select*256+:256],c_req_tag[select*16+:16],c_req_context[select*94+:94]};
 wire[464:0]returned={rsp_we,rsp_tag,rsp_data,rsp_identity};
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin q<=0;qn<={QB{1'b1}};r<=0;rn<=~465'b0;state<=IDLE;state_n<=~IDLE;bad<=0;bad_n<=1;end
 else if(ENABLE)begin
 if(blocked)begin bad<=1;bad_n<=0;end
 else begin
 if(rsp_v&&state!=WAIT)begin bad<=1;bad_n<=0;end
 case(state)
 IDLE:if(found)begin q<=selected;qn<=~selected;state<=SEND;state_n<=~SEND;end
 SEND:if(req_v&&req_r)begin state<=WAIT;state_n<=~WAIT;end
 WAIT:if(rsp_v&&rsp_r)begin
 if(rsp_we!=req_we||rsp_tag!=req_tag)begin bad<=1;bad_n<=0;end
 else begin r<=returned;rn<=~returned;state<=HELD;state_n<=~HELD;end end
 HELD:if(c_rsp_v[client]&&c_rsp_r[client])begin state<=IDLE;state_n<=~IDLE;end
 default:begin bad<=1;bad_n<=0;end
 endcase end end end
endmodule
