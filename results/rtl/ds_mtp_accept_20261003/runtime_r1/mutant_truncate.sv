// Additive standalone component. Cold rst_n is externally allcopies-fenced;
// runtime reset is fence_rearm, never an asynchronous erase of accepted debt.
module ot_hdc_mtp_accept_guarded #(
 parameter integer NSLOT=8, NW=21, parameter bit ENABLE=0
)(
 input wire clk,rst_n,admission_stop,caller_bad,
 input wire start_v, input wire [20:0] start_pos,start_tok,input wire[2:0]start_g,output wire start_ready,
 input wire tokx_v,input wire[24:0]tokx_lease,input wire[2:0]tokx_slot,input wire[20:0]tokx_tok,output wire tokx_ready,
 input wire amax_v,input wire[24:0]amax_lease,input wire[2:0]amax_slot,input wire[20:0]amax_tok,output wire amax_ready,
 input wire accept_v,input wire[24:0]accept_lease,input wire[2:0]accept_g,output wire accept_ready,
 output wire[167:0]stok,ttok,output wire out_v,acc_done,acc_any,output wire[2:0]acc_a,output wire[3:0]n_emit,output wire[20:0]bonus,
 output wire[24:0]lease, input wire out_ready,input wire[24:0]ack_lease,
 input wire fence_v,input wire[24:0]fence_lease,input wire[5:0]fence_receipts,input wire fence_rearm,output wire fence_ready,
 output wire fault,corrected
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE) begin:g_enabled
 localparam integer H=16,F=17,R=18,A=19,SQ=20,TQ=21,FQ=22,M=23;
 localparam logic[2:0] IDLE=0,COLLECT=1,REDUCE=2,GUARD=3,OUTPUT=4,DRAIN=5;
 logic[71:0]q[0:23];wire[63:0]d[0:23];logic[63:0]n[0:23];wire[65:0]dec[0:23];
 logic bad,ce,base_s,base_t,base_a,base_start,base_f;integer i,j,a,ni;logic run,fresh;
 function automatic integer width_of(input integer x);
 if(x<16)width_of=22;else case(x) H:width_of=33;F:width_of=1;R:width_of=30;A:width_of=29;SQ,TQ:width_of=50;FQ:width_of=33;default:width_of=36;endcase
 endfunction
 wire[2:0]phase=d[H][28+:3];wire[2:0]gamma=d[H][25+:3];wire[24:0]key=d[H][24:0];
 genvar dx;for(dx=0;dx<24;dx=dx+1)begin:g_decode assign dec[dx]=decode64(q[dx]);assign d[dx]=dec[dx][63:0];end
 always @* begin
 bad=caller_bad;ce=0;
 for(i=0;i<24;i=i+1)begin
 bad=bad|dec[i][65]|(|(d[i]>>width_of(i)));ce=ce|dec[i][64];
 end
 bad=bad|d[F][0]|(phase>DRAIN)|({1'b0,d[H][20:0]}+{19'b0,gamma}>22'd2097151);
 for(i=0;i<16;i=i+1)if(d[i][20:0]>=21'd129280)bad=1;
 if(phase==GUARD||phase==OUTPUT||phase==DRAIN)
 if(d[R][0+:3]>gamma||d[R][5+:4]!=({1'b0,d[R][0+:3]}+4'd1)||d[R][9+:21]>=21'd129280||!d[R][4])bad=1;
 base_start=(phase==IDLE)&&!d[H][31];base_s=(phase==COLLECT)&&!d[H][31]&&!d[SQ][49];
 base_t=(phase==COLLECT)&&!d[H][31]&&!d[TQ][49];base_a=(phase==COLLECT)&&!d[H][31]&&!d[A][28];
 base_f=(phase==DRAIN&&!fence_rearm)||(phase==IDLE&&d[H][31]&&fence_rearm);
 if(start_v&&base_start)if(start_tok>=129280||({1'b0,start_pos}+{19'b0,start_g}>22'd2097151))bad=1;
 if(tokx_v&&base_s)if(tokx_lease!=key||tokx_slot==0||tokx_slot>gamma||tokx_tok>=129280||d[{2'b0,tokx_slot}][21])bad=1;
 if(amax_v&&base_t)if(amax_lease!=key||amax_slot>gamma||amax_tok>=129280||d[8+amax_slot][21])bad=1;
 if(accept_v&&base_a)if(accept_lease!=key||accept_g!=gamma)bad=1;
 if(out_ready&&phase==OUTPUT&&ack_lease!=key)bad=1;
 if(fence_v&&base_f)if(fence_lease!=key||fence_receipts!=63)bad=1;
 // A presented runtime-rearm request with owned debt fails closed.
 if(fence_v&&fence_rearm&&!base_f)bad=1;
 if(phase==IDLE&&(tokx_v||amax_v||accept_v))bad=1;
 if(d[SQ][49])if(phase!=COLLECT||d[SQ][24:0]!=key||d[SQ][25+:3]==0||d[SQ][25+:3]>gamma||d[SQ][28+:21]>=129280||d[{2'b0,d[SQ][25+:3]}][21])bad=1;
 if(d[TQ][49])if(phase!=COLLECT||d[TQ][24:0]!=key||d[TQ][25+:3]>gamma||d[TQ][28+:21]>=129280||d[8+d[TQ][25+:3]][21])bad=1;
 fresh=1;
 for(i=0;i<8;i=i+1)if(i<=gamma)fresh=fresh&d[i][21]&d[8+i][21];
 if(d[A][28]&&!d[SQ][49]&&!d[TQ][49])if(phase!=COLLECT||d[A][24:0]!=key||d[A][25+:3]!=gamma||!fresh)bad=1;
 if(phase==REDUCE)if(!d[M][28]||d[M][24:0]!=key||d[M][25+:3]!=gamma)bad=1;
 if(d[FQ][31])if(phase!=DRAIN||d[FQ][24:0]!=key||d[FQ][25+:6]!=63)bad=1;
 end
 always @* begin
 for(ni=0;ni<24;ni=ni+1)n[ni]=d[ni];
 n[H][32]=d[H][32]|ce;if(admission_stop)n[H][31]=1;
 if(start_v&&base_start)begin
 for(ni=0;ni<24;ni=ni+1)n[ni]=0;
 n[H][20:0]=start_pos;n[H][21+:4]=d[H][21+:4]+4'd1;n[H][25+:3]=start_g;n[H][28+:3]=COLLECT;
 n[0][20:0]=start_tok;n[0][21]=1;
 end
 if(tokx_v&&base_s)begin n[SQ]=0;n[SQ][24:0]=tokx_lease;n[SQ][25+:3]=tokx_slot;n[SQ][28+:21]={5'b0,tokx_tok[15:0]};n[SQ][49]=1;end
 if(amax_v&&base_t)begin n[TQ]=0;n[TQ][24:0]=amax_lease;n[TQ][25+:3]=amax_slot;n[TQ][28+:21]=amax_tok;n[TQ][49]=1;end
 if(d[SQ][49])begin n[{2'b0,d[SQ][25+:3]}]=0;n[{2'b0,d[SQ][25+:3]}][20:0]=d[SQ][28+:21];n[{2'b0,d[SQ][25+:3]}][21]=1;n[SQ][49]=0;end
 if(d[TQ][49])begin n[8+d[TQ][25+:3]]=0;n[8+d[TQ][25+:3]][20:0]=d[TQ][28+:21];n[8+d[TQ][25+:3]][21]=1;n[TQ][49]=0;end
 if(accept_v&&base_a)begin n[A]=0;n[A][24:0]=accept_lease;n[A][25+:3]=accept_g;n[A][28]=1;end
 if(d[A][28]&&!d[SQ][49]&&!d[TQ][49])begin
 n[M]=0;n[M][24:0]=key;n[M][25+:3]=gamma;n[M][28]=1;
 for(ni=0;ni<7;ni=ni+1)n[M][29+ni]=(d[ni+1][20:0]==d[8+ni][20:0]);
 n[A][28]=0;n[H][28+:3]=REDUCE;
 end
 a=0;run=1;
 for(j=0;j<7;j=j+1)if(j<gamma)begin run=run&d[M][29+j];if(run)a=j+1;end
 if(phase==REDUCE)begin
 n[R]=0;n[R][0+:3]=3'(a);n[R][4]=1;n[R][5+:4]=4'(a+1);n[R][9+:21]=d[8+a][20:0];
 n[M][28]=0;n[H][28+:3]=GUARD;
 end
 if(phase==GUARD)begin n[R][3]=1;n[H][28+:3]=OUTPUT;end
 if(phase==OUTPUT)begin n[R][3]=0;if(out_ready)n[H][28+:3]=DRAIN;end
 if(fence_v&&base_f)begin
 if(fence_rearm)n[H][31]=0;
 else begin n[FQ]=0;n[FQ][24:0]=fence_lease;n[FQ][25+:6]=fence_receipts;n[FQ][31]=1;end
 end
 if(d[FQ][31])begin
 for(ni=0;ni<16;ni=ni+1)n[ni]=0;
 n[A]=0;n[SQ]=0;n[TQ]=0;n[FQ]=0;n[M]=0;n[H][28+:3]=IDLE;
 end
 end
 integer k;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)for(k=0;k<24;k=k+1)q[k]<=encode64(0);
 else if(bad)q[F]<=encode64(64'd1);
 else for(k=0;k<24;k=k+1)if(n[k]!=d[k])q[k]<=encode64(n[k]);
 end
 assign start_ready=base_start&&!bad;assign tokx_ready=base_s&&!bad;assign amax_ready=base_t&&!bad;assign accept_ready=base_a&&!bad;
 assign fence_ready=base_f&&!bad;assign out_v=(phase==OUTPUT)&&!bad;
 assign acc_done=out_v&&d[R][3];assign acc_any=d[R][4]&&!bad;assign acc_a=d[R][0+:3];assign n_emit=d[R][5+:4];assign bonus=d[R][9+:21];assign lease=key;
 assign fault=bad;assign corrected=d[H][32]|ce;
 genvar gv;for(gv=0;gv<8;gv=gv+1)begin:g_bus assign stok[gv*21+:21]=d[gv][20:0];assign ttok[gv*21+:21]=d[8+gv][20:0];end
 initial if(NSLOT!=8||NW!=21)$fatal(1,"fullwidth8/21 geometry required");
 end else begin:g_disabled
 assign start_ready=0;assign tokx_ready=0;assign amax_ready=0;assign accept_ready=0;assign fence_ready=0;
 assign stok=0;assign ttok=0;assign out_v=0;assign acc_done=0;assign acc_any=0;assign acc_a=0;assign n_emit=0;assign bonus=0;assign lease=0;assign fault=0;assign corrected=0;
 end endgenerate
endmodule
