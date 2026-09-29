`timescale 1ns/1ps
// Opt-in shared-service W ingress. 8 burst descriptors; 16 reserved return
// sectors/PC. 32 physical PCs, 32B sectors. Not a QE service guarantee.
module ot_chip_v41x_weight_pc_adapter #(
 parameter AW=30,TAGW=10,KTAGW=17,ND=8,DEPTH=16
)(
 input wire clk,rst_n,
 input wire[AW-1:0] region_base,region_count,
 input wire w_v,output wire w_rdy,input wire[AW-1:0] w_addr,
 input wire[5:0] w_len,input wire[TAGW-1:0] w_tag,
 output wire[31:0] w_room,
 output reg[31:0] req_v,input wire[31:0] req_rdy,
 output reg[32*AW-1:0] req_addr,
 output reg[32*(KTAGW+1)-1:0] req_tag,
 input wire[31:0] rsp_v,output wire[31:0] rsp_rdy,
 input wire[32*(KTAGW+1)-1:0] rsp_tag,input wire[8191:0] rsp_data,
 output wire[31:0] wr_v,input wire[31:0] wr_rdy,
 output wire[32*TAGW-1:0] wr_tag,output wire[159:0] wr_beat,
 output wire[8191:0] wr_data,output reg fault
);
 localparam PTR=$clog2(DEPTH);
 reg[ND-1:0] active;
 reg[AW-1:0] base[0:ND-1];reg[TAGW-1:0] tag[0:ND-1];
 reg[31:0] pending[0:ND-1];reg[31:0] taken[0:ND-1];
 reg[PTR:0] reserved[0:31],count[0:31];
 reg[PTR-1:0] rp[0:31],wp[0:31];
 reg[255:0] data[0:31][0:DEPTH-1];
 reg[TAGW+4:0] meta[0:31][0:DEPTH-1];
 integer need[0:31];integer slot,p,d,b; integer rd,rb,rpc,selected;
 reg[2:0] cursor[0:31];integer selected_slot[0:31];
 reg fit;reg[63:0] finish_addr,finish_region;
 function automatic integer pc(input reg[AW-1:0] a);
 pc=((a>>2)^(a>>7)^(a>>12))&31;
 endfunction
 initial if(ND!=8||DEPTH!=16||TAGW+5>KTAGW) $fatal(1,"unsupported shared W geometry");
 always @* begin
 slot=-1;for(d=0;d<ND;d=d+1) if(!active[d]&&slot<0) slot=d;
 for(p=0;p<32;p=p+1) need[p]=0;
 for(b=0;b<32;b=b+1) if(b<w_len) need[pc(w_addr+AW'(b))]=need[pc(w_addr+AW'(b))]+1;
 finish_addr=64'(w_addr)+64'(w_len);finish_region=64'(region_base)+64'(region_count);
 fit=(w_len>0&&w_len<=32&&w_addr>=region_base&&finish_addr<=finish_region&&finish_region<=(64'd1<<AW));
 for(p=0;p<32;p=p+1) if(reserved[p]+need[p]>DEPTH) fit=0;
 end
 assign w_rdy=(slot>=0)&&fit&&!fault;
 always @* begin
 req_v=0;req_addr=0;req_tag=0;selected=0;
 for(rd=0;rd<ND;rd=rd+1) taken[rd]=0;
 for(rpc=0;rpc<32;rpc=rpc+1) begin
 selected_slot[rpc]=0;
 for(rd=0;rd<ND;rd=rd+1) begin
 selected=(int'(cursor[rpc])+rd)%ND;
 for(rb=0;rb<32;rb=rb+1) if(active[selected]&&pending[selected][rb]&&!req_v[rpc]&&pc(base[selected]+AW'(rb))==rpc) begin
 req_v[rpc]=1;req_addr[rpc*AW+:AW]=base[selected]+AW'(rb);
 req_tag[rpc*(KTAGW+1)+:KTAGW+1]={1'b1,KTAGW'({tag[selected],5'(rb)})};
 selected_slot[rpc]=selected;
 if(req_rdy[rpc]) taken[selected][rb]=1;
 end
 end
 end
 end
 generate for(genvar c=0;c<32;c=c+1) begin:g_pc
 assign w_room[c]=(DEPTH-reserved[c]>=16)&&!fault;
 assign rsp_rdy[c]=(count[c]<DEPTH);
 assign wr_v[c]=(count[c]!=0);
 assign wr_data[c*256+:256]=data[c][rp[c]];
 assign wr_tag[c*TAGW+:TAGW]=meta[c][rp[c]][TAGW+4:5];
 assign wr_beat[c*5+:5]=meta[c][rp[c]][4:0];
 end endgenerate
 integer i;
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin
 active<=0;fault<=0;
 for(i=0;i<ND;i=i+1) begin base[i]<=0;tag[i]<=0;pending[i]<=0;end
 for(i=0;i<32;i=i+1) begin cursor[i]<=0;reserved[i]<=0;count[i]<=0;rp[i]<=0;wp[i]<=0;end
 end else begin
 // Full burst capacity reserved atomically; response consumption releases it.
 for(i=0;i<32;i=i+1) begin
 if(req_v[i]&&req_rdy[i]) cursor[i]<=3'(selected_slot[i]+1);
 reserved[i]<=reserved[i]+((w_v&&w_rdy)?need[i]:0)-((wr_v[i]&&wr_rdy[i])?1:0);
 count[i]<=count[i]+((rsp_v[i]&&rsp_rdy[i])?1:0)-((wr_v[i]&&wr_rdy[i])?1:0);
 if(rsp_v[i]&&rsp_rdy[i]) begin
 if(!rsp_tag[i*(KTAGW+1)+KTAGW]||reserved[i]==0) fault<=1;
 data[i][wp[i]]<=rsp_data[i*256+:256];
 meta[i][wp[i]]<=rsp_tag[i*(KTAGW+1)+:TAGW+5];wp[i]<=wp[i]+1'b1;
 end
 if(wr_v[i]&&wr_rdy[i]) rp[i]<=rp[i]+1'b1;
 end
 for(i=0;i<ND;i=i+1) if(active[i]) begin
 pending[i]<=pending[i]&~taken[i];
 if((pending[i]&~taken[i])==0) active[i]<=0;
 end
 if(w_v&&(w_len==0||w_len>32||w_addr<region_base||finish_addr>finish_region||finish_region>(64'd1<<AW))) fault<=1;
 if(w_v&&w_rdy) begin
 active[slot]<=1;base[slot]<=w_addr;tag[slot]<=w_tag;
 pending[slot]<=(w_len==32)?32'hffffffff:((32'd1<<w_len)-1);
 end
 end
 end
endmodule
