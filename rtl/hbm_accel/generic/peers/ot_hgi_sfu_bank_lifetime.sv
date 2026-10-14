`timescale 1ps/1fs
`default_nettype none
// Source-bound client lifetime seam, not a cache or a granted group1 endpoint.
// Native untagged responses are ordered within a bank/lane. Credit returns
// release queue slots; committed done releases write identity and owner debt.
module ot_hgi_sfu_bank_lifetime #(parameter integer LQ=10, MUT_EARLY_RELEASE=0)(
 input wire clk,rst_n,begin_owner,fence,grant,path_quiet,
 input wire [2:0] bank_id,input wire [1:0] slice_id,
 output reg owner_req,rd_ready,wr_ready,idle,fault,
 input wire rd_v,input wire [15:0] rd_sec,rd_tag,
 input wire wr_v,input wire [15:0] wr_sec,wr_tag,
 input wire [255:0] wr_data,input wire [7:0] wr_mask,
 output reg [16:0] rq,output reg [280:0] wq,
 input wire rq_credit,wq_credit,wq_done,input wire [256:0] rr,
 output reg result_v,output reg [15:0] result_sec,result_tag,
 output reg [255:0] result_data,
 output reg commit_v,output reg [15:0] commit_sec,commit_tag
);
 reg fenced,g_q,quiet_q,rc_q,wc_q,done_q;reg [256:0] rr_q;
 reg [31:0] rid[0:LQ-1],wid[0:LQ-1];
 reg [3:0] rh,rt,wh,wt;reg [4:0] rn,wn,rc,wc;
 wire ra=rd_v&&rd_ready,wa=wr_v&&wr_ready;
 wire rv=rr_q[256]&&(rn!=0),wv=done_q&&(wn!=0);
 wire raddr=rd_sec[2:0]==bank_id&&(rd_sec[15]?rd_sec[14:13]==0:rd_sec[14:13]==slice_id);
 wire waddr=wr_sec[2:0]==bank_id&&(wr_sec[15]?wr_sec[14:13]==0:wr_sec[14:13]==slice_id);
 wire rs=ra&&raddr,ws=wa&&waddr;
 wire [5:0] nrn={1'b0,rn}+rs-rv,nwn={1'b0,wn}+ws-wv;
 wire [5:0] nrc={1'b0,rc}+rc_q-rs,nwc={1'b0,wc}+wc_q-ws;
 wire pipeline_empty=!(rq[16]||wq[280]||rr[256]||rr_q[256]||rq_credit||wq_credit||wq_done||rc_q||wc_q||done_q||result_v||commit_v);
 wire debt_clear=(rn==0&&wn==0&&rc==LQ&&wc==LQ&&pipeline_empty&&quiet_q&&path_quiet);
 wire early_clear=(rn==0&&rc==LQ&&wc==LQ&&!rq[16]&&!wq[280]);
 function automatic [3:0] advance(input [3:0] p);advance=(p==LQ-1)?0:p+1'b1;endfunction
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin
   owner_req<=0;rd_ready<=0;wr_ready<=0;idle<=1;fault<=0;fenced<=0;
   g_q<=0;quiet_q<=0;rc_q<=0;wc_q<=0;done_q<=0;rr_q<=0;
   rq<=0;wq<=0;result_v<=0;commit_v<=0;result_sec<=0;result_tag<=0;result_data<=0;commit_sec<=0;commit_tag<=0;
   rh<=0;rt<=0;wh<=0;wt<=0;rn<=0;wn<=0;rc<=LQ;wc<=LQ;
  end else begin
   g_q<=grant;quiet_q<=path_quiet;rc_q<=rq_credit;wc_q<=wq_credit;done_q<=wq_done;rr_q<=rr;
   rq<={rs,rd_sec};wq<={ws,wr_sec,wr_data,wr_mask};
   result_v<=rv;commit_v<=wv;
   if(rs)begin rid[rt]<={rd_sec,rd_tag};rt<=advance(rt);end
   if(ws)begin wid[wt]<={wr_sec,wr_tag};wt<=advance(wt);end
   if(rv)begin {result_sec,result_tag}<=rid[rh];result_data<=rr_q[255:0];rh<=advance(rh);end
   if(wv)begin {commit_sec,commit_tag}<=wid[wh];wh<=advance(wh);end
   rn<=nrn[4:0];wn<=nwn[4:0];rc<=nrc[4:0];wc<=nwc[4:0];
   if((ra&&!raddr)||(wa&&!waddr)||(rr_q[256]&&!rv)||(done_q&&!wv)||nrc>LQ||nwc>LQ||nrn>LQ||nwn>LQ||(owner_req&&!grant&&(rn!=0||wn!=0||rq[16]||wq[280]))) begin fault<=1;fenced<=1;end
   if(begin_owner&&!owner_req&&debt_clear)begin owner_req<=1;fenced<=0;end
   if(fence&&owner_req)fenced<=1;
   if(owner_req&&fenced&&(MUT_EARLY_RELEASE?early_clear:debt_clear))begin owner_req<=0;fenced<=0;end
   // These are registered promises for the next accepting edge. Requests
   // promised before a fence are included in debt; no combinational pin mux.
   rd_ready<=owner_req&&g_q&&grant&&!fence&&!fenced&&!fault&&nrc!=0&&nrn<LQ;
   wr_ready<=owner_req&&g_q&&grant&&!fence&&!fenced&&!fault&&nwc!=0&&nwn<LQ;
   idle<=!owner_req&&debt_clear;
  end
 end
endmodule
`default_nettype wire
