`timescale 1ns/1ps
// Experimental one-stack common timing owner. Opt-in separate module; not PHY RTL.
// W addresses already relocated into the disjoint physical region. K owns writes.
module ot_chip_v41x_shared_hbm_model #(
 parameter AW=30,KTAGW=17,WTAGW=10,MEM_WORDS=65536,WN=3,WD=5
)(
 input wire clk,rst_n,input wire[AW-1:0] kbase,kcount,wbase,wcount,
 input wire[31:0] k_v,output wire[31:0] k_rdy,input wire[32*AW-1:0] k_addr,
 input wire[127:0] k_len,input wire[32*KTAGW-1:0] k_tag,input wire[31:0] k_we,
 input wire[8191:0] k_data,input wire[1023:0] k_strb,output wire[31:0] k_done,
 output wire[31:0] kr_v,input wire[31:0] kr_rdy,output wire[32*KTAGW-1:0] kr_tag,
 output wire[127:0] kr_beat,output wire[8191:0] kr_data,
 input wire w_v,output wire w_rdy,input wire[AW-1:0] w_addr,input wire[5:0] w_len,
 input wire[WTAGW-1:0] w_tag,output wire[31:0] w_room,
 output wire[31:0] wr_v,input wire[31:0] wr_rdy,output wire[32*WTAGW-1:0] wr_tag,
 output wire[159:0] wr_beat,output wire[8191:0] wr_data,output wire fault
);
 localparam MT=KTAGW+1;
 wire ledger_ok=(64'(kbase)+64'(kcount)<=MEM_WORDS)&&
 (64'(wbase)+64'(wcount)<=MEM_WORDS)&& kcount!=0&&wcount!=0&&
 ((64'(kbase)+64'(kcount)<=64'(wbase))||(64'(wbase)+64'(wcount)<=64'(kbase)));
 reg bad;wire wb;
 wire[31:0] av,ar,sv,sr,mv,mr,mwe;
 wire[32*AW-1:0] aa,ma;wire[32*MT-1:0] at,mt,st;
 wire[127:0] ml,sb;wire[8191:0] sd;
 reg[31:0] last_w;
 wire[31:0] choose_w,k_ok;
 assign fault=bad||wb;
 ot_chip_v41x_weight_pc_adapter #(.AW(AW),.TAGW(WTAGW),.KTAGW(KTAGW)) u_w(
 .clk(clk),.rst_n(rst_n),.region_base(wbase),.region_count(wcount),
 .w_v(w_v&&ledger_ok&&!bad),.w_rdy(w_ready),.w_addr(w_addr),.w_len(w_len),.w_tag(w_tag),.w_room(w_room),
 .req_v(av),.req_rdy(ar),.req_addr(aa),.req_tag(at),
 .rsp_v(sv),.rsp_rdy(sr),.rsp_tag(st),.rsp_data(sd),
 .wr_v(wr_v),.wr_rdy(wr_rdy),.wr_tag(wr_tag),.wr_beat(wr_beat),.wr_data(wr_data),.fault(wb));
 wire w_ready;assign w_rdy=w_ready&&ledger_ok&&!bad;
 wire[31:0] rv,rr;wire[31:0] done_unused;
 generate for(genvar p=0;p<32;p=p+1) begin:g_pc
 assign k_ok[p]=k_len[p*4+:4]!=0&&k_addr[p*AW+:AW]>=kbase&&
 (64'(k_addr[p*AW+:AW])+64'(k_len[p*4+:4])<=64'(kbase)+64'(kcount))&&
 (!k_we[p]||k_len[p*4+:4]==1);
 assign choose_w[p]=av[p]&&(!k_v[p]||!k_ok[p]||!last_w[p]);
 assign mv[p]=ledger_ok&&!bad&&(choose_w[p]?av[p]:(k_v[p]&&k_ok[p]));
 assign ma[p*AW+:AW]=choose_w[p]?aa[p*AW+:AW]:k_addr[p*AW+:AW];
 assign mt[p*MT+:MT]=choose_w[p]?at[p*MT+:MT]:{1'b0,k_tag[p*KTAGW+:KTAGW]};
 assign ml[p*4+:4]=choose_w[p]?4'd1:k_len[p*4+:4];
 assign mwe[p]=!choose_w[p]&&k_we[p];
 assign ar[p]=mr[p]&&choose_w[p]&&ledger_ok&&!bad;
 assign k_rdy[p]=mr[p]&&!choose_w[p]&&k_ok[p]&&ledger_ok&&!bad;
 assign sv[p]=rv[p]&&st[p*MT+KTAGW];
 assign kr_v[p]=rv[p]&&!st[p*MT+KTAGW];
 assign rr[p]=st[p*MT+KTAGW]?sr[p]:kr_rdy[p];
 assign kr_tag[p*KTAGW+:KTAGW]=st[p*MT+:KTAGW];
 end endgenerate
 assign kr_beat=sb;assign kr_data=sd;
 ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(AW),.TAGW(MT),.LENW(4),.BEATW(4),.MEM_WORDS(MEM_WORDS),
 .MEM_MODE(0),.REFPB(3),.SHARE_W_NUM(WN),.SHARE_DEN(WD)) u_mem(
 .clk(clk),.rst_n(rst_n),.req_v(mv),.req_rdy(mr),.req_addr(ma),.req_len(ml),.req_tag(mt),
 .req_we(mwe),.req_wdata(k_data),.req_wstrb(k_strb),.wr_done(k_done),
 .rsp_v(rv),.rsp_rdy(rr),.rsp_tag(st),.rsp_beat(sb),.rsp_data(sd));
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin bad<=0;last_w<=0;end else begin
 if((w_v||(|k_v))&&!ledger_ok) bad<=1;
 for(integer i=0;i<32;i=i+1) begin
 if(k_v[i]&&!k_ok[i]) bad<=1;
 if(mv[i]&&mr[i]) last_w[i]<=choose_w[i];
 end
 end end
endmodule
