module ot_hdc_mtp_source_holders #(parameter bit ENABLE=0)(
 input wire clk,rst_n,quarantine,
 input wire[1:0]p_v,p_finish,output wire[1:0]p_ready,
 input wire[49:0]p_lease,input wire[5:0]p_slot,input wire[41:0]p_token,
 output wire[1:0]req_v,input wire[1:0]req_ready,
 output wire[49:0]req_lease,output wire[5:0]req_slot,output wire[41:0]req_token,
 output wire caller_bad
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE)begin:g_enabled
 logic[71:0]q[0:3];logic[63:0]d[0:3],n[0:3];logic[65:0]dc[0:3];
 logic bad;logic[1:0]base;integer i,j;
 always @* begin
 bad=0;
 for(i=0;i<4;i=i+1)begin dc[i]=decode64(q[i]);d[i]=dc[i][63:0];n[i]=d[i];bad=bad|dc[i][65]|(|(d[i]>>((i%2==0)?22:29)));end
 for(i=0;i<2;i=i+1)begin
 if(d[2*i][20:0]>=129280||(d[2*i][21]&&!d[2*i+1][28]))bad=1;
 base[i]=p_finish[i]?(d[2*i+1][28]&&!d[2*i][21]):!d[2*i+1][28];
 if(p_v[i]&&base[i])begin
 if((i==0&&p_slot[3*i+:3]==0)||p_slot[3*i+:3]>7)bad=1;
 if(p_finish[i])begin
 if(p_lease[25*i+:25]!=d[2*i+1][24:0]||p_slot[3*i+:3]!=d[2*i+1][25+:3]||p_token[21*i+:21]>=129280)bad=1;
 end else if(p_token[21*i+:21]!=0)bad=1;
 end
 if(p_v[i]&&base[i])begin
 if(p_finish[i])begin n[2*i]=0;n[2*i][20:0]=p_token[21*i+:21];n[2*i][21]=1;end
 else begin n[2*i]=0;n[2*i+1]=0;n[2*i+1][24:0]=p_lease[25*i+:25];n[2*i+1][25+:3]=p_slot[3*i+:3];n[2*i+1][28]=1;end
 end
 if(req_v[i]&&req_ready[i])begin n[2*i]=0;n[2*i+1]=0;end
 end
 end
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)for(j=0;j<4;j=j+1)q[j]<=encode64(0);
 else if(!bad&&!quarantine)for(j=0;j<4;j=j+1)if(n[j]!=d[j])q[j]<=encode64(n[j]);
 end
 assign caller_bad=bad;
 genvar g;for(g=0;g<2;g=g+1)begin:g_port
 assign p_ready[g]=base[g]&&!bad&&!quarantine;
 assign req_v[g]=d[2*g+1][28]&&d[2*g][21]&&!bad;
 assign req_lease[g*25+:25]=d[2*g+1][24:0];assign req_slot[g*3+:3]=d[2*g+1][25+:3];assign req_token[g*21+:21]=d[2*g][20:0];
 end
 end else begin:g_disabled
 assign p_ready=0;assign req_v=0;assign req_lease=0;assign req_slot=0;assign req_token=0;assign caller_bad=0;
 end endgenerate
endmodule
