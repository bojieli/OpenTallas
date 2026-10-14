`timescale 1ps/1fs
`default_nettype none
// Read-only successor. Current DMA GLQ32 is reserved honestly: a legacy credit
// returns with its ordered response, so one legacy lane owns at most SLOTS tickets.
// Global S15 is preserved; native SID=S14:13, bank=S2:0, old lane=S4:0.
module ot_hgi_dma_native_read_owned_bank #(
 parameter integer SID=0,BANK=0,SLOTS=32,NATIVE_CREDITS=10,MUT=0,
 parameter integer TW=$clog2(SLOTS),RW=$clog2(4*SLOTS)
)(
 input wire clk,rst_n,input wire [63:0] legacy_q,
 output reg [16:0] rq,input wire rq_cr,input wire [256:0] rr,
 output reg [258+TW:0] routed_return,output wire drained,output reg fault
);
 reg [63:0] pin_q;reg [4*TW-1:0] seq,seq_n,pin_seq;
 reg [256:0] pin_rr;reg pin_cr;
 reg [14+TW:0] fifo[0:3][0:SLOTS-1];
 reg [TW-1:0] head[0:3],tail[0:3];reg [TW:0] count[0:3],count_n[0:3];
 reg [TW+1:0] route[0:4*SLOTS-1];reg [RW-1:0] rh,rt;reg [RW:0] rn,rn_n;
 reg [4:0] credits,credits_n;reg [1:0] priority_q,pick;reg pick_v;
 wire pop_return=pin_rr[256]&&rn!=0;
 always @*begin
  pick_v=0;pick=0;
  for(integer k=3;k>=0;k--)if(count[2'(priority_q+2'(k))]!=0)begin pick_v=1;pick=2'(priority_q+2'(k));end
 end
 wire issue=pick_v&&credits!=0&&rn<4*SLOTS&&!fault;
 wire [RW+1:0] next_rn={1'b0,rn}+issue-pop_return;
 wire [5:0] next_credit={1'b0,credits}+pin_cr-issue;
 always @(posedge clk)begin
  for(integer o=0;o<4;o++)pin_q[o*16+:15]<=legacy_q[o*16+:15];
  pin_seq<=seq;pin_rr[255:0]<=rr[255:0];
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  for(integer o=0;o<4;o++)begin pin_q[o*16+15]<=0;head[o]<=0;tail[o]<=0;count[o]<=0;count_n[o]<='1;end
  pin_rr[256]<=0;pin_cr<=0;seq<=0;seq_n<='1;rq[16]<=0;routed_return[258+TW]<=0;
  rh<=0;rt<=0;rn<=0;rn_n<='1;credits<=NATIVE_CREDITS;credits_n<=~5'(NATIVE_CREDITS);priority_q<=0;fault<=0;
 end else begin
  pin_rr[256]<=rr[256];pin_cr<=rq_cr;
  for(integer o=0;o<4;o++)begin
   pin_q[o*16+15]<=legacy_q[o*16+15];
   if(legacy_q[o*16+15])begin seq[o*TW+:TW]<=seq[o*TW+:TW]+1'b1;seq_n[o*TW+:TW]<=~(seq[o*TW+:TW]+1'b1);end
  end
  rq[16]<=issue;routed_return[258+TW]<=pop_return;
  credits<=next_credit[4:0];credits_n<=~next_credit[4:0];rn<=next_rn[RW:0];rn_n<=~next_rn[RW:0];
  if(seq!=~seq_n||credits!=~credits_n||rn!=~rn_n||next_credit>NATIVE_CREDITS||next_rn>4*SLOTS||(pin_rr[256]&&rn==0))fault<=1;
  if(issue)begin
   rq[15:0]<={1'b0,fifo[pick][head[pick]][14:0]};
   route[rt]<={pick,fifo[pick][head[pick]][14+TW:15]};rt<=rt+1'b1;priority_q<=pick+1'b1;
  end
  if(pop_return)begin
   routed_return[257+TW:256]<=route[rh]^((MUT==1)?{2'b01,{TW{1'b0}}}:0);
   routed_return[255:0]<=pin_rr[255:0];rh<=rh+1'b1;
  end
  for(integer o=0;o<4;o++)begin:queue
   reg push,pop;reg [TW+1:0] nc;
   push=pin_q[o*16+15]&&pin_q[o*16+13+:2]==2'(SID);pop=issue&&pick==2'(o);
   nc={1'b0,count[o]}+push-pop;
   if(count[o]!=~count_n[o]||nc>SLOTS||(push&&pin_q[o*16+:3]!=3'(BANK)))fault<=1;
   count[o]<=nc[TW:0];count_n[o]<=~nc[TW:0];
   if(push)begin fifo[o][tail[o]]<={pin_seq[o*TW+:TW],pin_q[o*16+:15]};tail[o]<=tail[o]+1'b1;end
   if(pop)head[o]<=head[o]+1'b1;
  end
 end
 wire idle_queues=count[0]==0&&count[1]==0&&count[2]==0&&count[3]==0;
 wire pin_valid=pin_q[15]|pin_q[31]|pin_q[47]|pin_q[63];
 wire new_valid=legacy_q[15]|legacy_q[31]|legacy_q[47]|legacy_q[63];
 assign drained=!fault&&idle_queues&&rn==0&&credits==NATIVE_CREDITS&&!pin_valid&&!new_valid&&!rq[16]&&!pin_rr[256]&&!rr[256]&&!pin_cr&&!rq_cr;
endmodule

// A separate return leaf for EACH legacy lane: 32x256 response FFs plus tickets
// stay below15k own sinks. Four native slices may return different tickets on
// one edge. Every valid is stored before the expected ticket is emitted.
module ot_hgi_dma_native_read_owned_join #(
 parameter integer OWNER=0,SLOTS=32,MUT=0,TW=$clog2(SLOTS)
)(
 input wire clk,rst_n,input wire [4*(259+TW)-1:0] routed_return,
 output reg [256:0] legacy_return,output reg legacy_credit,
 output wire drained,output reg fault
);
 localparam integer W=259+TW;
 reg [4*W-1:0] pin_return;reg [255:0] data[0:SLOTS-1];
 reg [SLOTS-1:0] valid,valid_n;reg [TW-1:0] expected,expected_n;
 always @(posedge clk)for(integer s=0;s<4;s++)pin_return[s*W+:W-1]<=routed_return[s*W+:W-1];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  for(integer s=0;s<4;s++)pin_return[s*W+W-1]<=0;
  valid<=0;valid_n<='1;expected<=0;expected_n<='1;legacy_return[256]<=0;legacy_credit<=0;fault<=0;
 end else begin:join
  reg [SLOTS-1:0] nv,incoming;reg pop;reg [TW-1:0] ticket;
  if(valid!=~valid_n||expected!=~expected_n)fault<=1;
  pop=valid[expected];legacy_return[256]<=pop;legacy_credit<=pop;
  nv=valid;incoming=0;
  if(pop)begin legacy_return[255:0]<=data[expected];nv[expected]=0;expected<=expected+1'b1;expected_n<=~(expected+1'b1);end
  for(integer s=0;s<4;s++)begin
   pin_return[s*W+W-1]<=routed_return[s*W+W-1];
   ticket=pin_return[s*W+256+:TW]^((MUT==2)?TW'(1):TW'(0));
   if(pin_return[s*W+W-1]&&pin_return[s*W+256+TW+:2]==2'(OWNER))begin
    if(nv[ticket]||incoming[ticket])fault<=1;
    else begin data[ticket]<=pin_return[s*W+:256];nv[ticket]=1;incoming[ticket]=1;end
   end
  end
  valid<=nv;valid_n<=~nv;
 end
 wire incoming_valid=routed_return[W-1]|routed_return[2*W-1]|routed_return[3*W-1]|routed_return[4*W-1];
 wire pinned_valid=pin_return[W-1]|pin_return[2*W-1]|pin_return[3*W-1]|pin_return[4*W-1];
 assign drained=!fault&&valid==0&&!incoming_valid&&!pinned_valid&&!legacy_return[256]&&!legacy_credit;
endmodule

// Parent wiring-only64-root successor:32 request routers +32 response leaves.
// The actual parent owns all4 R leases; no hardcoded group permission is valid.
// HARD_CLOCKS0 is shared-clock functional simulation; physical clock closure OPEN.
module ot_hgi_dma_native_read_owned #(
 parameter integer HARD_CLOCKS=0,LEGACY_SLOTS=32,MUT=0,TW=$clog2(LEGACY_SLOTS)
)(
 input wire clk,rst_n,input wire [63:0] leaf_clk,
 input wire [512:0] legacy_q,output wire [8256:0] legacy_r,
 input wire [3:0] rgrant,rack,output wire [3:0] rreq,drained,released,
 output wire [543:0] native_rq,input wire [31:0] native_credit,
 input wire [8223:0] native_rr,output wire [64:0] fault
);
 initial begin
  if(LEGACY_SLOTS<2||LEGACY_SLOTS>32||(LEGACY_SLOTS&(LEGACY_SLOTS-1))!=0)$fatal(1,"native read reservation must be a power of two from2 through32");
 end
 localparam integer W=259+TW;
 wire [63:0] clocks=HARD_CLOCKS!=0?leaf_clk:{64{clk}};
 wire [32*W-1:0] returns;wire [31:0] bank_idle,join_idle;
 reg [TW:0] pending[0:31],pending_n[0:31];reg sf;reg busy;
 always @*begin busy=0;for(integer l=0;l<32;l++)if(pending[l]!=0)busy=1;end
 for(genvar b=0;b<8;b++)begin:bank_number
  wire [63:0] requests;wire [4*W-1:0] replies;
  for(genvar o=0;o<4;o++)assign requests[o*16+:16]=legacy_q[(o*8+b)*16+:16];
  for(genvar s=0;s<4;s++)begin:slice
   ot_hgi_dma_native_read_owned_bank #(.SID(s),.BANK(b),.SLOTS(LEGACY_SLOTS),.MUT(MUT)) router(
    .clk(clocks[s*8+b]),.rst_n(rst_n),.legacy_q(requests),.rq(native_rq[(s*8+b)*17+:17]),
    .rq_cr(native_credit[s*8+b]),.rr(native_rr[(s*8+b)*257+:257]),
    .routed_return(returns[(s*8+b)*W+:W]),.drained(bank_idle[s*8+b]),.fault(fault[s*8+b]));
   assign replies[s*W+:W]=returns[(s*8+b)*W+:W];
  end
  for(genvar o=0;o<4;o++)begin:legacy_lane
   ot_hgi_dma_native_read_owned_join #(.OWNER(o),.SLOTS(LEGACY_SLOTS),.MUT(MUT)) join(
    .clk(clocks[32+o*8+b]),.rst_n(rst_n),.routed_return(replies),
    .legacy_return(legacy_r[(o*8+b)*257+:257]),.legacy_credit(legacy_r[8224+o*8+b]),
    .drained(join_idle[o*8+b]),.fault(fault[32+o*8+b]));
  end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  sf<=0;for(integer l=0;l<32;l++)begin pending[l]<=0;pending_n[l]<='1;end
 end else for(integer l=0;l<32;l++)begin:ledger
  reg [TW+1:0] np;
  np={1'b0,pending[l]}+legacy_q[l*16+15]-legacy_r[l*257+256];
  if(pending[l]!=~pending_n[l]||np>LEGACY_SLOTS||(legacy_q[l*16+15]&&(!( &rgrant)||legacy_q[l*16+:5]!=5'(l))))sf<=1;
  pending[l]<=np[TW:0];pending_n[l]<=~np[TW:0];
 end
 assign fault[64]=sf;
 wire idle=!busy&&(&bank_idle)&&(&join_idle)&&!legacy_q[512]&&!(|fault);
 assign rreq={4{legacy_q[512]||busy||!(&bank_idle)||!(&join_idle)}};
 assign drained={4{idle}};
 assign legacy_r[8256]=(MUT==3)?1'b1:(&rgrant)&&!(|fault)&&(|rreq);
 assign released=drained&rack&~rgrant;
endmodule
`default_nettype wire
