`timescale 1ns/1ps
`default_nettype none
// Four source heads -> four destination slices for one native bank. Registered DMA outputs.
// Ticket queues retain the owner until actual macro commit; mirror joins all four tickets.
module ot_hgi_dma_vm_router #(parameter integer MUT=0)(input wire clk,rst_n,
 input wire [31:0] head_v,head_epoch,input wire [32*280-1:0] head_d,output reg [31:0] ack_epoch,
 output reg [4*281-1:0] dma_q,input wire [3:0] dma_done,output reg [3:0] source_done,output reg fault);
 reg [31:0] hv,he,seen;reg [32*280-1:0] hd;
 reg [2:0] hr[0:3];reg [3:0] src_v;reg [279:0] src_d[0:3];reg [3:0] take;
 always @(posedge clk)hd<=head_d;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin hv<=0;he<=0;end else begin hv<=head_v;he<=head_epoch;end
 always @*begin
 for(integer s=0;s<4;s++)begin
 src_v[s]=0;src_d[s]=0;
 for(integer h=0;h<8;h++)begin
 src_v[s]=src_v[s]|(hr[s]==3'(h)&&hv[s*8+h]&&he[s*8+h]!=seen[s*8+h]);
 src_d[s]=src_d[s]|(hd[(s*8+h)*280+:280]&{280{hr[s]==3'(h)}});
 end
 end
 end
 reg [1:0] rr;reg mirror_pending;reg [1:0] mirror_owner;reg [3:0] mirror_left;
 reg [2:0] tickets[0:3][0:15];reg [3:0] th[0:3],tt[0:3];reg [4:0] tn[0:3];
 reg [3:0] done_q;reg [7:0] completion_pending[0:3];
 reg [3:0] grant_v;reg [1:0] owner[0:3];reg grant_mirror;reg [1:0] grant_mowner;
 reg [2:0] events[0:3];reg [3:0] mirror_ack;
 always @*begin
 take=0;grant_v=0;grant_mirror=0;grant_mowner=0;
 for(integer d=0;d<4;d++)owner[d]=0;
 // One mirror atomically reserves every destination ticket queue.
 for(integer k=3;k>=0;k--)begin
 integer s;s=(int'(rr)+k)%4;
 if(src_v[s]&&src_d[s][279]&&!mirror_pending&&tn[0]<16&&tn[1]<16&&tn[2]<16&&tn[3]<16)begin grant_mirror=1;grant_mowner=2'(s);end
 end
 if(grant_mirror)begin
 take[grant_mowner]=1;grant_v=4'hf;
 for(integer d=0;d<4;d++)owner[d]=grant_mowner;
 end else for(integer d=0;d<4;d++)begin
 for(integer k=3;k>=0;k--)begin
 integer s;s=(int'(rr)+k)%4;
 if(src_v[s]&&!src_d[s][279]&&src_d[s][277+:2]==2'(d)&&tn[d]<16)begin grant_v[d]=1;owner[d]=2'(s);end
 end
 if(grant_v[d])take[owner[d]]=1;
 end
 mirror_ack=0;for(integer s=0;s<4;s++)events[s]=0;
 for(integer d=0;d<4;d++)if(done_q[d]&&tn[d]!=0)begin
 if(tickets[d][th[d]][2])mirror_ack[d]=1;else events[tickets[d][th[d]][1:0]]=events[tickets[d][th[d]][1:0]]+3'd1;
 end
 if(mirror_pending && ((mirror_left&~mirror_ack)==0))events[mirror_owner]=events[mirror_owner]+3'd1;
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 seen<=0;ack_epoch<=0;for(integer s=0;s<4;s++)hr[s]<=0;rr<=0;mirror_pending<=0;mirror_owner<=0;mirror_left<=0;dma_q<=0;done_q<=0;source_done<=0;fault<=0;
 for(integer d=0;d<4;d++)begin th[d]<=0;tt[d]<=0;tn[d]<=0;completion_pending[d]<=0;end
 end else begin
 rr<=rr+1'b1;done_q<=dma_done;dma_q<=0;
 for(integer s=0;s<4;s++)if(take[s])begin
 hr[s]<=hr[s]+1'b1;
 for(integer h=0;h<8;h++)if(hr[s]==3'(h))begin
 seen[s*8+h]<=he[s*8+h];ack_epoch[s*8+h]<=he[s*8+h];
 end
 end
 for(integer d=0;d<4;d++)begin
 if(done_q[d]&&tn[d]==0)fault<=1;
 if(grant_v[d])begin
 dma_q[d*281+:281]<={1'b1,src_d[owner[d]]};
 tickets[d][tt[d]]<={grant_mirror,(MUT==1)?2'(d):owner[d]};tt[d]<=tt[d]+1'b1;
 end
 if(done_q[d]&&tn[d]!=0)th[d]<=th[d]+1'b1;
 tn[d]<=tn[d]+{4'd0,grant_v[d]}-{4'd0,done_q[d]&&tn[d]!=0};
 source_done[d]<=completion_pending[d]!=0;
 completion_pending[d]<=completion_pending[d]+{5'd0,events[d]}-(completion_pending[d]!=0?8'd1:8'd0);
 end
 if(grant_mirror)begin mirror_pending<=1;mirror_owner<=grant_mowner;mirror_left<=(MUT==2)?4'b0001:4'hf;end
 else if(mirror_pending)begin mirror_left<=mirror_left&~mirror_ack;if((mirror_left&~mirror_ack)==0)mirror_pending<=0;end
 end
endmodule
`default_nettype wire
