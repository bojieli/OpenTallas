`timescale 1ns/1ps
`default_nettype none
// Opt-in distributed PC cache: four real wide banks, eight SRAM macros.
// Native response epoch MUST come from its allocation CAM, never current map.
// One-bit epochs require upstream no-wrap: allocations cannot recycle native
// debt, writes, or issued/held read publications. Four finite fetch contexts.
module ot_hbm_svc_dma_pc_cache_wide #(parameter integer ENABLE=0,parameter integer MUT_EPOCH=0) (
 input wire clk,rst_n,
 input wire alloc_v, output wire alloc_rdy,
 input wire [5:0] alloc_slot, input wire [7:0] alloc_idx,
 input wire [3:0] alloc_len, input wire [7:0] alloc_group,
 input wire [1:0] alloc_bank, input wire alloc_epoch,
 input wire ret_v, output wire ret_rdy, input wire [7:0] ret_group,
 input wire [1:0] ret_bank, input wire ret_epoch,
 input wire [255:0] ret_data, input wire ret_fault,
 output wire ret_reject,
 input wire fetch_v, output wire fetch_rdy, input wire [7:0] fetch_group,
 input wire fetch_epoch, input wire [3:0] fetch_mask,
 output wire out_v, input wire out_rdy,
 output wire [1023:0] out_data, output wire [3:0] out_fault,
 output reg metadata_fault
);
 // Status00 absent,01 native debt,10 write pending,11 ready.
 (* keep="true", dont_touch="true" *) reg [2:0] meta[0:1023];
 (* keep="true", dont_touch="true" *) reg [2:0] meta_inv[0:1023];
 // Request{mask4,epoch1,group8}; state{done4,issued4,active1}.
 (* keep="true", dont_touch="true" *) reg [12:0] req[0:3],req_inv[0:3];
 (* keep="true", dont_touch="true" *) reg [8:0] st[0:3],st_inv[0:3];
 (* keep="true", dont_touch="true" *) reg [1:0] head,tail,head_inv,tail_inv;
 reg [1023:0] payload[0:3];
 reg [3:0] faults[0:3];
 wire [9:0] ai={alloc_bank,alloc_group}, ri={ret_bank,ret_group};
 wire a_bad=meta[ai] != ~meta_inv[ai];
 wire r_bad=meta[ri] != ~meta_inv[ri];
 wire response_live=!r_bad && meta[ri][1:0]==1 && (MUT_EPOCH!=0 || meta[ri][2]==ret_epoch);
 reg recycle_read_busy;
 integer c,b,k,n0,n1,lane,off,d_lane;
 always @* begin
   recycle_read_busy=0;
   for(n0=0;n0<4;n0=n0+1)
     if(st[n0][0] && req[n0][7:0]==alloc_group &&
        (st[n0][1+alloc_bank] || st[n0][5+alloc_bank])) recycle_read_busy=1;
 end
 wire enabled=(ENABLE!=0) && rst_n && !metadata_fault;
 // idx is the native transaction tag and stays in the native CAM; this cache
 // stores group/epoch ownership only. len validation prices no new tag SRAM.
 wire descriptor_ok=alloc_slot==alloc_group[7:2] && alloc_len!=0;
 assign alloc_rdy=enabled && descriptor_ok && !a_bad &&
   (meta[ai][1:0]==0 || (meta[ai][1:0]==3 && meta[ai][2]!=alloc_epoch)) &&
   !recycle_read_busy;
 assign fetch_rdy=enabled && (!st[tail][0] || pop);
 wire a_take=alloc_v && alloc_rdy;
 wire f_take=fetch_v && fetch_rdy;
 wire [3:0] bwready,brready,bov,bof;
 wire [255:0] bod[0:3];
 reg [3:0] brv;
 reg [7:0] brgroup[0:3];
 reg [1:0] issue_ctx[0:3],publish_ctx[0:3];
 reg [3:0] issue_found,publish_found;
 reg context_bad;
 reg [3:0] fetch_meta_bad;
 integer scan;
 reg [1:0] ix;
 always @* begin
   brv=0;issue_found=0;publish_found=0;context_bad=0;fetch_meta_bad=0;
   for(n1=0;n1<4;n1=n1+1)
     if(req[n1]!=~req_inv[n1] || st[n1]!=~st_inv[n1]) context_bad=1;
   for(lane=0;lane<4;lane=lane+1) begin
     issue_ctx[lane]=0;publish_ctx[lane]=0;brgroup[lane]=0;
     for(off=0;off<4;off=off+1) begin
       ix=head+off;
       if(!issue_found[lane] && st[ix][0] && req[ix][9+lane] && !st[ix][1+lane]) begin
         issue_found[lane]=1;issue_ctx[lane]=ix;brgroup[lane]=req[ix][7:0];
         if(meta[{lane[1:0],req[ix][7:0]}]!=~meta_inv[{lane[1:0],req[ix][7:0]}])
           fetch_meta_bad[lane]=1;
         brv[lane]=enabled && meta[{lane[1:0],req[ix][7:0]}][1:0]==3 &&
                   meta[{lane[1:0],req[ix][7:0]}][2]==req[ix][8];
       end
       if(!publish_found[lane] && st[ix][0] && st[ix][1+lane] && !st[ix][5+lane]) begin
         publish_found[lane]=1;publish_ctx[lane]=ix;
       end
     end
   end
 end
 assign ret_rdy=enabled && (!response_live || bwready[ret_bank]);
 wire r_take=ret_v && ret_rdy;
 assign ret_reject=r_take && !response_live;
 wire write_take=r_take && response_live;
 // Three-edge bank write completion, source tag/epoch retained to publication.
 (* keep="true", dont_touch="true" *) reg [2:0] commit_v,commit_v_inv;
 (* keep="true", dont_touch="true" *) reg [32:0] commit_tag,commit_tag_inv;
 wire [10:0] commit_tail=commit_tag[32:22],commit_tail_inv=commit_tag_inv[32:22];
 wire commit_bad=(commit_v ^ commit_v_inv)!=3'b111 ||
   (commit_v[2] && (commit_tail ^ commit_tail_inv)!=11'h7ff);
 wire [9:0] ci=commit_tail[9:0];
 wire [3:0] out_mask=req[head][12:9];
 assign out_v=enabled && st[head][0] && ((st[head][8:5]&out_mask)==out_mask);
 assign out_data=out_v ? payload[head] : 1024'b0;
 assign out_fault=out_v ? faults[head] : 4'b0;
 wire pop=out_v && out_rdy;
 genvar g;
 generate for(g=0;g<4;g=g+1) begin:banks
   hbm_svc_dma_sram_bank_wide bank(
     .clk(clk),.rst_n(rst_n),.wr_v(write_take && ret_bank==g),.wr_rdy(bwready[g]),
     .wr_addr(ret_group),.wr_data(ret_data),.wr_fault(ret_fault),
     .rd_v(brv[g]),.rd_rdy(brready[g]),.rd_addr(brgroup[g]),
     .out_v(bov[g]),.out_rdy(enabled && publish_found[g]),.out_data(bod[g]),.out_fault(bof[g]));
 end endgenerate
 integer reset_i;
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin
     metadata_fault<=0;head<=0;tail<=0;head_inv<=3;tail_inv<=3;
     commit_v<=0;commit_v_inv<=7;
     for(reset_i=0;reset_i<1024;reset_i=reset_i+1) begin meta[reset_i]<=0;meta_inv[reset_i]<=7;end
     for(reset_i=0;reset_i<4;reset_i=reset_i+1) begin
       req[reset_i]<=0;req_inv[reset_i]<=13'h1fff;st[reset_i]<=0;st_inv[reset_i]<=9'h1ff;
     end
     commit_tag<=0;commit_tag_inv<=33'h1ffffffff;
   end else begin
     if((alloc_v && a_bad) || (ret_v && r_bad) || context_bad || (|fetch_meta_bad) ||
        commit_bad || head!=~head_inv || tail!=~tail_inv) metadata_fault<=1;
     commit_v<={commit_v[1:0],write_take};
     commit_v_inv<=~{commit_v[1:0],write_take};
     commit_tag<={commit_tag[21:0],ret_epoch,ri};
     commit_tag_inv<=~{commit_tag[21:0],ret_epoch,ri};
     if(commit_v[2] && !commit_bad && meta[ci][1:0]==2 && meta[ci][2]==commit_tail[10]) begin
       meta[ci]<={commit_tail[10],2'b11};meta_inv[ci]<=~{commit_tail[10],2'b11};
     end
     if(a_take) begin meta[ai]<={alloc_epoch,2'b01};meta_inv[ai]<=~{alloc_epoch,2'b01};end
     if(write_take) begin meta[ri]<={ret_epoch,2'b10};meta_inv[ri]<=~{ret_epoch,2'b10};end
     if(pop) begin st[head]<=0;st_inv[head]<=9'h1ff;head<=head+1'b1;head_inv<=~(head+2'b01);end
     if(f_take) begin
       req[tail]<={fetch_mask,fetch_epoch,fetch_group};req_inv[tail]<=~{fetch_mask,fetch_epoch,fetch_group};
       st[tail]<=9'b1;st_inv[tail]<=~9'b1;
       tail<=tail+1'b1;tail_inv<=~(tail+2'b01);
     end
     for(b=0;b<4;b=b+1) begin
       if(brv[b] && brready[b]) begin st[issue_ctx[b]][1+b]<=1;st_inv[issue_ctx[b]][1+b]<=0;end
       if(bov[b] && enabled && publish_found[b]) begin
         st[publish_ctx[b]][5+b]<=1;st_inv[publish_ctx[b]][5+b]<=0;
       end
     end
   end
 end
 // Masked sectors are explicitly zero, avoiding exposure of previous context.
 always @(posedge clk) begin
   if(f_take) begin payload[tail]<=0;faults[tail]<=0;end
   for(d_lane=0;d_lane<4;d_lane=d_lane+1)
     if(bov[d_lane] && enabled && publish_found[d_lane]) begin
       payload[publish_ctx[d_lane]][d_lane*256+:256]<=bod[d_lane];
       faults[publish_ctx[d_lane]][d_lane]<=bof[d_lane];
     end
 end
endmodule
`default_nettype wire
