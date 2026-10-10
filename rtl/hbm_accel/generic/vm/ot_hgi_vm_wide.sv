`timescale 1ns/1ps
`default_nettype none
// Modeled successor: 512 logical banks, two II2 physical phases each.
// Packet admission is a handshake, not an unconditional valid-only receipt.
module ot_hgi_vm_wide #(
 parameter integer ENABLE=0, NB=512, NC=3, OUT=8, CW=8, MUT=0,
 parameter integer LB=$clog2(NB), SB=LB+9, DW=1+SB+256+8
)(input wire clk,rst_n,
 input wire [NB*DW-1:0] dma, output reg [NB-1:0] dma_ready,dma_done,
 input wire [CW*(DW+16)-1:0] coll,output reg [CW-1:0] coll_ready,coll_done,
 output reg [CW*16-1:0] coll_done_tag,
 input wire [NC-1:0] req_v,output reg [NC-1:0] req_r,
 input wire [NC*337-1:0] req,
 output reg [NC-1:0] rsp_v,input wire [NC-1:0] rsp_r,
 output reg [NC*273-1:0] rsp,
 output reg fault,output reg [31:0] corrected_count);
 localparam integer PB=2*NB, SP=$clog2(OUT), CB=$clog2(OUT+1);
 reg [PB-1:0] wv,rv;
 wire [PB-1:0] wr,rr,wd,rd,bf,ue;
 reg [7:0] wa[0:PB-1],ra[0:PB-1],wm[0:PB-1];
 reg [255:0] data[0:PB-1];reg [19:0] wt[0:PB-1],rt[0:PB-1];
 wire [19:0] wtag[0:PB-1],rtag[0:PB-1];wire [255:0] rdata[0:PB-1];wire [3:0] ce[0:PB-1];
 reg [SP-1:0] head[0:NC-1],tail[0:NC-1],head_n[0:NC-1],tail_n[0:NC-1];
 reg [CB-1:0] count[0:NC-1],count_n[0:NC-1];
 reg [16:0] meta[0:NC-1][0:OUT-1],meta_n[0:NC-1][0:OUT-1];
 reg [1:0] state[0:NC-1][0:OUT-1],state_n[0:NC-1][0:OUT-1]; // 0 free,1 pending,2 committed
 reg [255:0] result[0:NC-1][0:OUT-1];
 integer p,c,s,l,b,ph,owner,slot;reg [336:0] q;
 reg [DW-1:0] d;reg [DW+15:0] n;reg [SB-1:0] sec;
 reg [PB-1:0] selected_w,selected_r;
 // Real SRAM has no reset contents. Allocation visibility is protected per word.
 reg [7:0] allocated[0:PB-1][0:255],allocated_n[0:PB-1][0:255];
 reg [4:0] iv[0:PB-1],iv_n[0:PB-1];
 reg [15:0] im[0:PB-1][0:4],im_n[0:PB-1][0:4];
 reg masks_ok; reg [2:0] native_rr[0:PB-1],native_rr_n[0:PB-1]; integer lane;
 generate for(genvar g=0;g<PB;g=g+1) begin:g_physical
 ot_hgi_vm_wide_bank #(.ENABLE(ENABLE)) u_bank(
 .clk(clk),.rst_n(rst_n),.w_v(wv[g]),.w_rdy(wr[g]),.w_addr(wa[g]),.w_data(data[g]),.w_mask(wm[g]),.w_tag(wt[g]),
 .w_done(wd[g]),.w_done_tag(wtag[g]),.r_v(rv[g]),.r_rdy(rr[g]),.r_addr(ra[g]),.r_tag(rt[g]),
 .r_done(rd[g]),.r_done_tag(rtag[g]),.r_data(rdata[g]),.r_ce(ce[g]),.r_ue(ue[g]),.fault(bf[g]),
 .inj_v(1'b0),.inj_word(3'd0),.inj_mask(39'd0));
 end endgenerate
 initial begin
 if(NB<2 || (1<<LB)!=NB || OUT<2 || (1<<SP)!=OUT || NC>7 || CW>8 || SB>18) $fatal(1,"wide VM parameters");
 end
 always @* begin
 dma_ready=0;coll_ready=0;req_r=0;rsp_v=0;rsp=0;wv=0;rv=0;selected_w=0;selected_r=0;
 for(p=0;p<PB;p=p+1)begin wa[p]=0;ra[p]=0;wm[p]=0;data[p]=0;wt[p]=0;rt[p]=0;end
 // Packet responses retire in client order despite different read/write publication.
 for(c=0;c<NC;c=c+1)if(ENABLE && state[c][head[c]]==2)begin
 rsp_v[c]=1;rsp[c*273+:273]={meta[c][head[c]][15:0],meta[c][head[c]][16],result[c][head[c]]};end
 if(ENABLE && !fault)begin
 // Native publishers have priority. Conflicting lane holds its transaction until admitted.
 for(p=0;p<PB;p=p+1)for(l=0;l<CW;l=l+1)begin
 lane=(native_rr[p]+l)%CW;
 n=coll[lane*(DW+16)+:DW+16];sec=n[280+:SB];b=sec[LB-1:0];ph=sec[LB];
 if(n[DW+15] && 2*b+ph==p && !selected_w[p])begin
 wa[p]=sec[LB+1+:8];data[p]=n[24+:256];wm[p]=n[16+:8];wt[p]={4'(lane),n[15:0]};
 coll_ready[lane]=wr[p];wv[p]=wr[p];selected_w[p]=1;end
 end
 // One admission per packet client; eight protected outstanding identities.
 for(c=0;c<NC;c=c+1)begin
 q=req[c*337+:337];masks_ok=1;
 for(s=0;s<8;s=s+1)if(q[16+s*4+:4]!=0 && q[16+s*4+:4]!=15)masks_ok=0;
 sec=q[309+:SB];b=sec[LB-1:0];ph=sec[LB];p=2*b+ph;
 if(req_v[c] && count[c]<OUT && q[335:309+SB]==0 && q[308:304]==0)begin
 
 if(q[336]==1'b0 && !selected_r[p] && allocated[p][sec[LB+1+:8]]==8'hff && allocated_n[p][sec[LB+1+:8]]==8'h00)begin
 ra[p]=sec[LB+1+:8];rt[p]={4'(9+c),16'(tail[c])};req_r[c]=rr[p];rv[p]=rr[p];selected_r[p]=1;end
 else if(q[336] && masks_ok && !selected_w[p])begin
 wa[p]=sec[LB+1+:8];data[p]=q[303:48];wm[p]=0;
 for(s=0;s<8;s=s+1)wm[p][s]=|q[16+s*4+:4];
 wt[p]={4'(9+c),16'(tail[c])};req_r[c]=wr[p];wv[p]=wr[p];selected_w[p]=1;end
 end
 end
 for(b=0;b<NB;b=b+1)begin
 d=dma[b*DW+:DW];sec=d[264+:SB];ph=sec[LB];p=2*b+ph;
 if(d[DW-1] && sec[LB-1:0]==b && !selected_w[p])begin
 wa[p]=sec[LB+1+:8];data[p]=d[8+:256];wm[p]=d[7:0];wt[p]={4'd8,16'(b)};
 dma_ready[b]=wr[p];wv[p]=wr[p];selected_w[p]=1;end
 end
 end
 end
 integer x,y,k,o,t;integer delta;reg bad;integer corrections;
 always @(posedge clk)begin
 if(!rst_n)begin
 fault<=0;corrected_count<=0;dma_done<=0;coll_done<=0;coll_done_tag<=0;
 for(x=0;x<PB;x=x+1)begin
 native_rr[x]<=0;native_rr_n[x]<=~3'd0;iv[x]<=0;iv_n[x]<=~5'd0;
 for(y=0;y<256;y=y+1)begin allocated[x][y]<=0;allocated_n[x][y]<=8'hff;end
 for(y=0;y<5;y=y+1)begin im[x][y]<=0;im_n[x][y]<=~16'd0;end
 end
 for(x=0;x<NC;x=x+1)begin head[x]<=0;tail[x]<=0;count[x]<=0;head_n[x]<=~SP'(0);tail_n[x]<=~SP'(0);count_n[x]<=~CB'(0);
 for(y=0;y<OUT;y=y+1)begin state[x][y]<=0;state_n[x][y]<=~2'd0;meta[x][y]<=0;meta_n[x][y]<=~17'd0;result[x][y]<=0;end end
 end else begin
 dma_done<=0;coll_done<=0;bad=|bf;corrections=0;
 for(x=0;x<NC;x=x+1)begin
 if(head_n[x]!=~head[x] || tail_n[x]!=~tail[x] || count_n[x]!=~count[x])bad=1;
 for(y=0;y<OUT;y=y+1)if(state_n[x][y]!=~state[x][y] || meta_n[x][y]!=~meta[x][y])bad=1;
 delta=0;
 if(req_v[x] && req_r[x])begin
 state[x][tail[x]]<=1;state_n[x][tail[x]]<=~2'd1;meta[x][tail[x]]<={req[x*337+336],req[x*337+:16]};meta_n[x][tail[x]]<=~{req[x*337+336],req[x*337+:16]};
 tail[x]<=tail[x]+1'b1;tail_n[x]<=~(tail[x]+1'b1);delta=delta+1;end
 if(rsp_v[x] && rsp_r[x])begin state[x][head[x]]<=0;state_n[x][head[x]]<=~2'd0;head[x]<=head[x]+1'b1;head_n[x]<=~(head[x]+1'b1);delta=delta-1;end
 count[x]<=count[x]+delta;count_n[x]<=~CB'(count[x]+delta);
 end
 for(k=0;k<PB;k=k+1)begin
 if(iv_n[k]!=~iv[k] || native_rr_n[k]!=~native_rr[k])bad=1;
 if(wv[k]&&wr[k]&&wt[k][19:16]<CW)begin native_rr[k]<=3'(wt[k][19:16]+1);native_rr_n[k]<=~3'(wt[k][19:16]+1);end
 for(y=0;y<5;y=y+1)if(im_n[k][y]!=~im[k][y])bad=1;
 iv[k]<={iv[k][3:0],wv[k]&&wr[k]};iv_n[k]<=~{iv[k][3:0],wv[k]&&wr[k]};
 for(y=1;y<5;y=y+1)begin im[k][y]<=im[k][y-1];im_n[k][y]<=~im[k][y-1];end
 im[k][0]<={wa[k],wm[k]};im_n[k][0]<=~{wa[k],wm[k]};
 if(iv[k][4])begin
 if(allocated_n[k][im[k][4][15:8]]!=~allocated[k][im[k][4][15:8]])bad=1;
 allocated[k][im[k][4][15:8]]<=allocated[k][im[k][4][15:8]]|im[k][4][7:0];
 allocated_n[k][im[k][4][15:8]]<=~(allocated[k][im[k][4][15:8]]|im[k][4][7:0]);
 end
 if(wd[k])begin
 o=wtag[k][19:16];t=wtag[k][15:0];
 if(o==8)begin if(t>=NB || k/2!=t)bad=1;else dma_done[t]<=1;end
 else if(o<CW)begin if(coll_done[o])bad=1;coll_done[o]<=1;coll_done_tag[o*16+:16]<=(MUT==1)?16'(t^1):16'(t);end
 else if(o>=9 && o<9+NC && t<OUT)begin
 if(state[o-9][t]!=1 || !meta[o-9][t][16])bad=1;
 state[o-9][t]<=2;state_n[o-9][t]<=~2'd2;result[o-9][t]<=0;end
 else bad=1;
 end
 if(rd[k])begin
 o=rtag[k][19:16];t=rtag[k][15:0];corrections=corrections+ce[k];bad=bad|ue[k];
 if(o>=9 && o<9+NC && t<OUT)begin
 if(state[o-9][t]!=1 || meta[o-9][t][16])bad=1;
 state[o-9][t]<=2;state_n[o-9][t]<=~2'd2;result[o-9][t]<=rdata[k];end else bad=1;
 end
 end
 corrected_count<=corrected_count+corrections;if(bad)fault<=1;
 end
 end
endmodule
`default_nettype wire
