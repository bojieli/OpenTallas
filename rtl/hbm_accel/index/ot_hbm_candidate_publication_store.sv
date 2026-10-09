`timescale 1ps/1fs
`default_nettype none
// Literal15-slot storage; rank extent advances ONLY positive macro completion.
// Rank publication requires its actual final quarter packet, not elapsed time.
module ot_hbm_candidate_publication_store #(
 parameter integer ENABLE=0,OWNER_W=73,MUT_SLOT=0
)(
 input wire clk,por_n,start,input wire[OWNER_W-1:0] start_frame,
 output wire start_r,input wire owner_valid,input wire[OWNER_W-1:0] owner_frame,
 input wire retire,input wire consumer_retained,
 input wire flit_v,output wire flit_r,input wire[544:0] flit,input wire[OWNER_W-1:0] flit_owner,
 input wire expected_kind,input wire[7:0] expected_dst,
 input wire empty_v,output wire empty_r,input wire[6:0] empty_rank,input wire[OWNER_W-1:0] empty_frame,
 output wire publication_complete,output wire retained,output wire fault,
 input wire read_v,output wire read_r,input wire[OWNER_W-1:0] read_frame,
 input wire[6:0] read_rank,input wire[16:0] read_ordinal,
 output wire rsp_v,input wire rsp_r,output wire[OWNER_W-1:0] rsp_frame,
 output wire[6:0] rsp_rank,output wire[16:0] rsp_ordinal,
 output wire[33:0] rsp_tuple,output wire rsp_last,rsp_empty,output wire rsp_ce
);
 localparam integer BANKS=70;
 localparam[2:0] IDLE=0,READY=1,WREQ=2,WWAIT=3,RREQ=4,RWAIT=5,RESPONSE=6;
 reg[2:0] st;reg live,failed;
 reg[OWNER_W-1:0] frame;
 reg[95:0] published;
 reg[6:0] count[0:95];reg[1:0] quarter[0:95];
 reg[4:0] beat[0:95];
 reg[6:0] rank_q,bank_q;reg[6:0] address_q;reg[3:0] slot_q;
 reg[16:0] ordinal_q;reg[511:0] payload_q;reg final_q;
 reg[33:0] tuple_q;reg last_q,empty_q,ce_q;
 wire active=live;
 wire control_ok=st<=RESPONSE;
 wire safe=ENABLE&&control_ok&&!failed;
 wire[69:0] br,bv,bf,bp,bc,bw;wire[511:0] bd[0:BANKS-1];
 for(genvar b=0;b<BANKS;b=b+1)begin:g_bank
 ot_hbm_candidate_sram_bank #(.ENABLE(ENABLE)) bank(.clk(clk),.por_n(por_n),
 .req_v(safe&&active&&(st==WREQ||st==RREQ)&&bank_q==b),.req_r(br[b]),
 .req_write(st==WREQ),.req_address(address_q),.req_data(payload_q),
 .rsp_v(bv[b]),.rsp_r(safe&&(st==WWAIT||st==RWAIT)&&bank_q==b),
 .rsp_data(bd[b]),.rsp_write(bw[b]),.rsp_ce(bc[b]),.rsp_poison(bp[b]),.fault(bf[b]));
 end
 assign start_r=safe&&!live&&st==IDLE;
 assign flit_r=safe&&active&&st==READY&&!publication_complete;
 assign empty_r=flit_r&&!flit_v;
 assign publication_complete=safe&&active&&(&published);
 assign retained=ENABLE&&live;
 assign fault=ENABLE&&(!control_ok||failed||(|bf));
 assign read_r=safe&&active&&publication_complete&&st==READY;
 assign rsp_v=safe&&active&&st==RESPONSE;
 assign rsp_frame=frame;assign rsp_rank=rank_q;assign rsp_ordinal=ordinal_q;
 assign rsp_tuple=tuple_q;assign rsp_last=last_q;assign rsp_empty=empty_q;assign rsp_ce=ce_q;
 integer a;
 always @(posedge clk or negedge por_n)begin
 if(!por_n)begin
 st<=IDLE;live<=0;frame<=0;
 published<=0;failed<=0;rank_q<=0;bank_q<=0;address_q<=0;slot_q<=0;
 ordinal_q<=0;payload_q<=0;final_q<=0;tuple_q<=0;last_q<=0;empty_q<=0;ce_q<=0;
 for(integer r=0;r<96;r=r+1)begin count[r]<=0;quarter[r]<=0;beat[r]<=0;end
 end else if(ENABLE)begin
 if(!control_ok||(|bf))failed<=1;
 if(retire&&live)begin
 if(st!=READY||consumer_retained||!publication_complete)failed<=1;
 else begin live<=0;st<=IDLE;end
 end else if(safe)case(st)
 IDLE:if(start&&start_r)begin
 if(!owner_valid||start_frame!=owner_frame)failed<=1;
 else begin live<=1;frame<=start_frame;published<=0;
 for(integer r=0;r<96;r=r+1)begin count[r]<=0;quarter[r]<=0;beat[r]<=0;end
 st<=READY;end
 end
 READY:begin
 if(flit_v&&flit_r)begin
 if(flit_owner!=frame||flit[544]!=expected_kind||flit[543:536]!=expected_dst||flit[535:528]>=96||flit[510])failed<=1;
 else if(published[flit[535:528]]||flit[527:526]!=quarter[flit[535:528]]||flit[525:512]!=beat[flit[535:528]]||beat[flit[535:528]]>=23||count[flit[535:528]]>=92)failed<=1;
 else begin
 rank_q<=flit[535:528];payload_q<=flit[511:0];final_q<=flit[511];
 a=int'(flit[535:528])*92+int'(count[flit[535:528]]);bank_q<=7'(a>>7);address_q<=7'(a);
 st<=WREQ;end
 end else if(empty_v&&empty_r)begin
 if(empty_frame!=frame||empty_rank>=96)failed<=1;
 else if(published[empty_rank]||count[empty_rank]!=0)failed<=1;
 else begin published[empty_rank]<=1;end
 end else if(read_v&&read_r)begin
 if(read_frame!=frame||read_rank>=96)failed<=1;
 else if(count[read_rank]!=0&&read_ordinal>=17'(count[read_rank])*15)failed<=1;
 else if(count[read_rank]==0&&read_ordinal!=0)failed<=1;
 else begin
 rank_q<=read_rank;ordinal_q<=read_ordinal;empty_q<=count[read_rank]==0;ce_q<=0;
 last_q<=count[read_rank]==0||read_ordinal+1==17'(count[read_rank])*15;
 if(count[read_rank]==0)begin tuple_q<=0;st<=RESPONSE;end
 else begin a=int'(read_rank)*92+int'(read_ordinal)/15;bank_q<=7'(a>>7);address_q<=7'(a);slot_q<=4'(read_ordinal%15);st<=RREQ;end
 end
 end
 end
 WREQ:if(br[bank_q])begin st<=WWAIT;end
 WWAIT:if(bv[bank_q])begin
 if(bp[bank_q]||!bw[bank_q])failed<=1;
 else begin
 count[rank_q]<=count[rank_q]+1'b1;
 if(final_q)begin beat[rank_q]<=0;
 if(quarter[rank_q]==3)begin published[rank_q]<=1;end
 else begin quarter[rank_q]<=quarter[rank_q]+1'b1;end
 end else if(beat[rank_q]==22)failed<=1;
 else begin beat[rank_q]<=beat[rank_q]+1'b1;end
 st<=READY;
 end
 end
 RREQ:if(br[bank_q])begin st<=RWAIT;end
 RWAIT:if(bv[bank_q])begin
 if(bp[bank_q]||bw[bank_q])failed<=1;
 else begin tuple_q<=bd[bank_q][34*((int'(slot_q)+MUT_SLOT)%15)+:34];ce_q<=bc[bank_q];st<=RESPONSE;end
 end
 RESPONSE:if(rsp_r)begin st<=READY;end
 default:failed<=1;
 endcase
 end
 end
endmodule
`default_nettype wire
