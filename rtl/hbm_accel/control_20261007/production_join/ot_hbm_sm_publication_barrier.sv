// Prebuild model tools/hbm_sm_publication_barrier_model.py; local finite protocol.
module ot_hbm_sm_publication_barrier #(parameter ENABLE=0)(
 input wire clk,rst_n,input wire source_valid,output wire source_ready,input wire[93:0]source_context,
 output wire su_publication_valid,input wire su_publication_ready,output wire[93:0]su_publication_context,
 input wire su_release_valid,output wire su_release_ready,input wire[93:0]su_release_context,
 output wire owner_valid,input wire owner_ready,output wire fault
);
 localparam[2:0]PUBLISH=1,CONSUME=2,RETIRE=4;
 (* keep=1,dont_touch=1 *)reg[2:0]state,state_n;
 (* keep=1,dont_touch=1 *)reg bad,bad_n;
 wire mismatch=state!=~state_n||bad==bad_n||!(state==PUBLISH||state==CONSUME||state==RETIRE);
 wire wrong_release=su_release_valid&&(state==PUBLISH||su_release_context!=source_context);
 wire dropped=state!=PUBLISH&&!source_valid;
 wire blocked=bad||mismatch||wrong_release||dropped;
 assign fault=ENABLE&&blocked;
 assign su_publication_valid=ENABLE&&state==PUBLISH&&source_valid&&!blocked;
 assign su_publication_context=source_context;
 assign su_release_ready=ENABLE&&state==CONSUME&&source_valid&&!blocked;
 assign owner_valid=ENABLE&&state==RETIRE&&source_valid&&!blocked;
 assign source_ready=owner_valid&&owner_ready;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin state<=PUBLISH;state_n<=~PUBLISH;bad<=0;bad_n<=1;end
 else if(ENABLE)begin
 if(blocked)begin bad<=1;bad_n<=0;end
 else begin
 if(su_publication_valid&&su_publication_ready)begin state<=CONSUME;state_n<=~CONSUME;end
 if(su_release_valid&&su_release_ready)begin state<=RETIRE;state_n<=~RETIRE;end
 if(source_ready)begin state<=PUBLISH;state_n<=~PUBLISH;end
 end end end
endmodule
