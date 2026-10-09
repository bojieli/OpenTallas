`timescale 1ns/1ps
// Plain control FIFO restores GLOBAL host-acceptance order after per-stack
// source1 prefix completions. This is not a new lease/epoch/identity protocol.
module ot_hbm_ingest_global_prefix #(parameter integer ENABLE=0,DEPTH=1024,MUT_SUM_ACK=0)(
 input wire ck,rst_n,input wire issue_v,input wire[1:0]issue_stack,
 output wire issue_rdy,input wire[23:0]stack_ack_n,
 output wire[5:0]ack_n,output wire pending,output wire fault
);
 localparam integer PW=$clog2(DEPTH);
 generate if(!ENABLE)begin:off
 assign issue_rdy=0;assign ack_n=0;assign pending=0;assign fault=0;
 end else begin:on
 reg[1:0]stack[0:DEPTH-1];reg[PW-1:0]wp,rp;
 reg[PW:0]count,owed[0:3],credit[0:3];reg fault_q;
 reg[5:0]ack_q;reg[PW+1:0]available[0:3];reg bad,retire;integer s;
 wire fire=issue_v&&issue_rdy;
 assign issue_rdy=!fault_q&&count<DEPTH;
 assign pending=count!=0;assign fault=fault_q;
 assign ack_n=MUT_SUM_ACK?(stack_ack_n[5:0]+stack_ack_n[11:6]+stack_ack_n[17:12]+stack_ack_n[23:18]):ack_q;
 always @*begin
 bad=0;
 for(integer j=0;j<4;j=j+1)begin
 available[j]={1'b0,credit[j]}+stack_ack_n[6*j+:6];
 if(available[j]>({1'b0,owed[j]}+((fire&&issue_stack==j)?1'b1:1'b0)))bad=1;
 end
 retire=count!=0&&available[stack[rp]]!=0&&!bad&&!fault_q;
 end
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin wp<=0;rp<=0;count<=0;fault_q<=0;ack_q<=0;
 for(s=0;s<4;s=s+1)begin owed[s]<=0;credit[s]<=0;end end
 else begin ack_q<=0;if(bad)fault_q<=1;
 if(!fault_q&&!bad)begin
 count<=count+fire-retire;
 if(fire)begin stack[wp]<=issue_stack;wp<=wp+1'b1;end
 if(retire)begin rp<=rp+1'b1;ack_q<=1;end
 for(s=0;s<4;s=s+1)begin
 owed[s]<=owed[s]+((fire&&issue_stack==s)?1'b1:1'b0)-((retire&&stack[rp]==s)?1'b1:1'b0);
 credit[s]<=available[s]-((retire&&stack[rp]==s)?1'b1:1'b0);
 end end end end
 end endgenerate
`ifndef SYNTHESIS
 initial if(DEPTH<2||(1<<PW)!=DEPTH)$fatal(1,"globalprefix depth poweroftwo>=2");
`endif
endmodule
