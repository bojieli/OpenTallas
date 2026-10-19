`timescale 1ns/1ps
// Real completion order leaf. Each admitted sector contributes its destination
// PC to a bounded256-entry issue queue. Physical host-write ACKs are ordered
// within each PC but may arrive in any inter-PC order. Only the contiguous
// globally issued prefix returns credit/visibility. No payload is changed.
// Control FF storage and <=8:1 registered stages; no unprotected SRAM.
`ifndef OT_HOST_ORDER_S2_DEFAULT
`define OT_HOST_ORDER_S2_DEFAULT 0
`endif
module qkd_host_commit_order #(parameter integer MUT=0,KEPT_SELECT=`OT_HOST_ORDER_S2_DEFAULT)(
 input wire ck,rst_n,input wire issue_v,input wire[6:0]issue_pc,input wire[127:0]acks,
 output reg prefix_v,output reg[31:0]prefix_count,output reg fault
);
 reg iqv;reg[6:0]iqpc;reg[127:0]aq;
 reg[7:0]wp,rp;reg[8:0]unread,total;
 reg[8:0]outstanding[0:127],pending[0:127];
 reg[6:0]s1[0:31],s2[0:3],s3;reg[4:0]sel1;reg[1:0]sel2;
 reg v1,v2,v3;reg[6:0]front[0:7];reg[2:0]fw,fr;reg[3:0]fc,read_credit;
 wire fetch=unread!=0&&read_credit!=0&&!fault;
 // HRORDER 10-18 (route qkd_hr_core_order-r2-c420f015e TT -30 ps: fr -> front[fr] -> 128 compares -> pop -> pending):
 // head_oh = one-hot of front[fr], a register kept exact by write-bypass whenever fc!=0 (pop and consume only use it
 // then). Cycle-exact with the previous form (bench tools/qwen_kv_die/host_cluster/bench/hrorder_equiv).
 reg[127:0]head_oh;
 wire[127:0]head_ready;
 for(genvar k=0;k<128;k++)begin:g_ready
  assign head_ready[k]=head_oh[k]&&pending[k]!=0;
 end
 wire pop=fc!=0&&!fault&&((|head_ready)||MUT==1);
 wire[2:0]fr1=fr+3'd1;
 wire[6:0]head_adv=(v3&&fw==fr1)?s3:front[fr1],head_hold=(v3&&fw==fr)?s3:front[fr];
 always @(posedge ck)head_oh<=pop?(128'd1<<head_adv):(128'd1<<head_hold);
 wire take=iqv&&!fault&&total<256;
 always @(posedge ck)begin
  iqpc<=issue_pc;
  if(!KEPT_SELECT)for(integer k=0;k<4;k++)s2[k]<=s1[k*8+sel1[2:0]];
  sel1<=rp[7:3];sel2<=sel1[4:3];s3<=s2[sel2];
  if(v3)front[fw]<=s3;
 end
 for(genvar b=0;b<32;b++)begin:g_bank
  reg[6:0]words[0:7];
  always @(posedge ck)begin
   if(take&&wp[7:3]==5'(b))words[wp[2:0]]<=iqpc;
   if(!KEPT_SELECT)s1[b]<=words[rp[2:0]];
  end
 end
 generate if(KEPT_SELECT)begin:g_kept_select
  for(genvar b=0;b<32;b++)begin:g_local
   (* keep=1 *)reg[7:0]read_oh;
   always @(posedge ck or negedge rst_n)
    if(!rst_n)read_oh<=8'b1;
    else if(fetch)read_oh<={read_oh[6:0],read_oh[7]};
   reg[6:0]picked;
   always @*begin
    picked=0;
    for(integer j=0;j<8;j++)picked=picked|(g_bank[b].words[j]&{7{read_oh[j]}});
   end
   always @(posedge ck)s1[b]<=picked;
  end
  (* keep=1 *)reg[7:0]stage2_oh;
  always @(posedge ck)stage2_oh<=8'b1<<rp[5:3];
  for(genvar k=0;k<4;k++)begin:g_s2
   reg[6:0]picked;
   always @*begin
    picked=0;
    for(integer j=0;j<8;j++)picked=picked|(s1[k*8+j]&{7{stage2_oh[j]}});
   end
   always @(posedge ck)s2[k]<=picked;
  end
 end endgenerate
 for(genvar k=0;k<128;k++)begin:g_pc
  wire add=take&&iqpc==7'(k),physical=aq[k],consume=pop&&head_oh[k];
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin outstanding[k]<=0;pending[k]<=0;end
   else begin
    case({add,physical})2'b10:outstanding[k]<=outstanding[k]+1'b1;2'b01:if(outstanding[k]!=0)outstanding[k]<=outstanding[k]-1'b1;default:;endcase
    case({physical,consume})2'b10:pending[k]<=pending[k]+1'b1;2'b01:if(pending[k]!=0)pending[k]<=pending[k]-1'b1;default:;endcase
   end
  end
 end
 wire[127:0]bad_ack;
 for(genvar k=0;k<128;k++)begin:g_guard
  assign bad_ack[k]=aq[k]&&outstanding[k]==0&&!(take&&iqpc==7'(k));
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   iqv<=0;aq<=0;wp<=0;rp<=0;unread<=0;total<=0;v1<=0;v2<=0;v3<=0;fw<=0;fr<=0;fc<=0;read_credit<=8;
   prefix_v<=0;prefix_count<=0;fault<=0;
  end else begin
   iqv<=issue_v;aq<=acks;v1<=fetch;v2<=v1;v3<=v2;prefix_v<=pop;
   if(iqv&&total==256)fault<=1;
   if(|bad_ack)fault<=1;
   if(take)wp<=wp+1'b1;
   if(fetch)rp<=rp+1'b1;
   case({take,fetch})2'b10:unread<=unread+1'b1;2'b01:unread<=unread-1'b1;default:;endcase
   case({take,pop})2'b10:total<=total+1'b1;2'b01:total<=total-1'b1;default:;endcase
   case({pop,fetch})2'b10:read_credit<=read_credit+1'b1;2'b01:read_credit<=read_credit-1'b1;default:;endcase
   if(v3)begin if(fc==8&&!pop)fault<=1;fw<=fw+1'b1;end
   if(pop)begin fr<=fr1;prefix_count<=prefix_count+1'b1;if(prefix_count==32'hffffffff)fault<=1;end
   case({v3,pop})2'b10:fc<=fc+1'b1;2'b01:fc<=fc-1'b1;default:;endcase
  end
 end
endmodule
