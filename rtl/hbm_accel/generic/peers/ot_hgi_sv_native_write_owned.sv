`timescale 1ps/1fs
`default_nettype none
// SV's global S15 transport. Native bank credits (dequeue) and global commit
// notifications are independent ordered streams. Preserve a ticket until BOTH
// streams have passed it; never turn native dequeue into legacy write-done.
module ot_hgi_sv_native_write_owned_bank #(
 parameter integer SID=0,BANK=0,SLOTS=8,NATIVE_CREDITS=10,MUT=0,
 parameter integer TW=$clog2(SLOTS),RW=$clog2(4*SLOTS)
)(
 input wire clk,rst_n,input wire[4*280-1:0]legacy_q,input wire granted,
 output reg[280:0]wq,input wire wq_cr,wq_done,
 output reg[5:0]routed_credit,output reg[5:0]routed_done,
 output wire drained,output reg fault
);
 reg[4*280-1:0]pin_q;reg pin_credit,pin_done,pin_grant;
 reg[278:0]fifo[0:3][0:SLOTS-1];reg[TW-1:0]head[0:3],tail[0:3];
 reg[TW:0]count[0:3],count_n[0:3];
 reg[1:0]route[0:4*SLOTS-1];reg[RW-1:0]wh,ch,dh;
 reg[RW:0]cn,cn_n,dn,dn_n;reg[4:0]credits,credits_n;
 reg[1:0]priority_q,pick;reg pick_v;reg[278:0]head_data[0:3],selected;
 always @*begin
  for(integer o=0;o<4;o++)begin
   head_data[o]=0;
   for(integer k=0;k<SLOTS;k++)if(head[o]==TW'(k))head_data[o]=head_data[o]|fifo[o][k];
  end
  pick=0;pick_v=0;
  for(integer k=3;k>=0;k--)if(count[2'(priority_q+2'(k))]!=0)begin pick_v=1;pick=2'(priority_q+2'(k));end
  selected=0;for(integer o=0;o<4;o++)if(pick==2'(o))selected=selected|head_data[o];
 end
 wire issue=pick_v&&credits!=0&&cn<4*SLOTS&&dn<4*SLOTS&&pin_grant&&!fault;
 wire credit_event=pin_credit&&cn!=0,done_event=pin_done&&dn!=0;
 wire[RW+1:0]next_cn={1'b0,cn}+issue-credit_event;
 wire[RW+1:0]next_dn={1'b0,dn}+issue-done_event;
 wire[5:0]next_credit={1'b0,credits}+pin_credit-issue;
 always @(posedge clk)for(integer o=0;o<4;o++)pin_q[o*280+:279]<=legacy_q[o*280+:279];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  for(integer o=0;o<4;o++)begin pin_q[o*280+279]<=0;head[o]<=0;tail[o]<=0;count[o]<=0;count_n[o]<='1;end
  pin_credit<=0;pin_done<=0;pin_grant<=0;wq[280]<=0;routed_credit[5]<=0;routed_done[5]<=0;
  wh<=0;ch<=0;dh<=0;cn<=0;cn_n<='1;dn<=0;dn_n<='1;credits<=NATIVE_CREDITS;credits_n<=~5'(NATIVE_CREDITS);priority_q<=0;fault<=0;
 end else begin
  pin_credit<=wq_cr;pin_done<=wq_done;pin_grant<=granted;
  for(integer o=0;o<4;o++)pin_q[o*280+279]<=legacy_q[o*280+279];
  wq[280]<=issue;routed_credit[5]<=credit_event;routed_done[5]<=done_event;
  credits<=next_credit[4:0];credits_n<=~next_credit[4:0];
  cn<=next_cn[RW:0];cn_n<=~next_cn[RW:0];dn<=next_dn[RW:0];dn_n<=~next_dn[RW:0];
  if(cn!=~cn_n||dn!=~dn_n||credits!=~credits_n||next_credit>NATIVE_CREDITS||next_cn>4*SLOTS||next_dn>4*SLOTS||(pin_credit&&cn==0)||(pin_done&&dn==0))fault<=1;
  if(issue)begin
   wq[279:0]<={1'b0,selected};// mirror0 + FULL globalS15; SID bits remain S14:13.
   route[wh]<=pick;wh<=wh+1'b1;priority_q<=pick+1'b1;
  end
  if(credit_event)begin routed_credit[4:0]<={route[ch]^((MUT==1)?2'b01:0),3'(BANK)};ch<=ch+1'b1;end
  if(done_event)begin routed_done[4:0]<={route[dh]^((MUT==2)?2'b01:0),3'(BANK)};dh<=dh+1'b1;end
  for(integer o=0;o<4;o++)begin:queues
   reg push,pop;reg[TW+1:0]nc;
   push=pin_q[o*280+279]&&pin_q[o*280+277+:2]==2'(SID);pop=issue&&pick==2'(o);
   nc={1'b0,count[o]}+push-pop;
   if(count[o]!=~count_n[o]||nc>SLOTS||(push&&pin_q[o*280+264+:5]!={2'(o),3'(BANK)}))fault<=1;
   count[o]<=nc[TW:0];count_n[o]<=~nc[TW:0];
   for(integer k=0;k<SLOTS;k++)if(push&&tail[o]==TW'(k))fifo[o][k]<=pin_q[o*280+:279];
   if(push)tail[o]<=tail[o]+1'b1;if(pop)head[o]<=head[o]+1'b1;
  end
 end
 wire qempty=count[0]==0&&count[1]==0&&count[2]==0&&count[3]==0;
 wire in_live=pin_q[279]|pin_q[559]|pin_q[839]|pin_q[1119]|legacy_q[279]|legacy_q[559]|legacy_q[839]|legacy_q[1119];
 assign drained=!fault&&qempty&&cn==0&&dn==0&&credits==NATIVE_CREDITS&&!in_live&&!wq[280]&&!pin_credit&&!pin_done&&!wq_cr&&!wq_done&&!routed_credit[5]&&!routed_done[5];
endmodule

// Four SIDs can report one legacy lane on the same edge. Capture EVERY event,
// then serialize credit and commit independently; an OR would lose3 events.
module ot_hgi_sv_native_write_owned_return #(
 parameter integer OWNER=0,BANK=0,SLOTS=8,MUT=0,
 parameter integer CW=$clog2(4*4*SLOTS+1)
)(
 input wire clk,rst_n,input wire[23:0]routed_credit,routed_done,
 output reg legacy_credit,legacy_done,output wire drained,output reg fault
);
 reg[23:0]pc,pd;reg[CW-1:0]nc,nc_n,nd,nd_n;reg[2:0]ic,id;
 always @*begin
  ic=0;id=0;
  for(integer s=0;s<4;s++)begin
   if(pc[s*6+5]&&pc[s*6+:5]=={2'(OWNER),3'(BANK)})ic=ic+1'b1;
   if(pd[s*6+5]&&pd[s*6+:5]=={2'(OWNER),3'(BANK)})id=id+1'b1;
  end
 end
 wire emit_c=nc!=0,emit_d=nd!=0;
 wire[CW:0]xc={1'b0,nc}+ic-emit_c,xd={1'b0,nd}+id-emit_d;
 always @(posedge clk)begin
  for(integer s=0;s<4;s++)begin pc[s*6+:5]<=routed_credit[s*6+:5];pd[s*6+:5]<=routed_done[s*6+:5];end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  for(integer s=0;s<4;s++)begin pc[s*6+5]<=0;pd[s*6+5]<=0;end
  nc<=0;nd<=0;nc_n<='1;nd_n<='1;legacy_credit<=0;legacy_done<=0;fault<=0;
 end else begin
  for(integer s=0;s<4;s++)begin pc[s*6+5]<=routed_credit[s*6+5];pd[s*6+5]<=routed_done[s*6+5];end
  legacy_credit<=emit_c;legacy_done<=(MUT==3)?emit_c:emit_d;
  nc<=xc[CW-1:0];nc_n<=~xc[CW-1:0];nd<=xd[CW-1:0];nd_n<=~xd[CW-1:0];
  if(nc!=~nc_n||nd!=~nd_n||xc>4*4*SLOTS||xd>4*4*SLOTS)fault<=1;
 end
 assign drained=!fault&&nc==0&&nd==0&&!legacy_credit&&!legacy_done&&!(pc[5]|pc[11]|pc[17]|pc[23]|pd[5]|pd[11]|pd[17]|pd[23])&&!(routed_credit[5]|routed_credit[11]|routed_credit[17]|routed_credit[23]|routed_done[5]|routed_done[11]|routed_done[17]|routed_done[23]);
endmodule

module ot_hgi_sv_native_write_owned #(
 parameter integer LEGACY_SLOTS=8,HARD_CLOCKS=0,MUT=0,TW=$clog2(LEGACY_SLOTS)
)(
 input wire clk,rst_n,input wire[63:0]leaf_clk,
 input wire[8960:0]legacy_q,output wire[31:0]legacy_credit,legacy_done,
 input wire[3:0]wgrant,wack,output wire[3:0]wreq,drained,released,
 output wire legacy_grant,output wire[32*281-1:0]native_wq,
 input wire[31:0]native_credit,native_done,output wire[64:0]fault
);
 wire[63:0]clocks=HARD_CLOCKS?leaf_clk:{64{clk}};
 wire[32*6-1:0]credit_events,done_events;wire[31:0]bank_idle,return_idle;
 reg[TW:0]pending[0:31],pending_n[0:31];reg[31:0]commits[0:31],commits_n[0:31];reg sf,busy;
 always @*begin busy=0;for(integer l=0;l<32;l++)if(pending[l]!=0||commits[l]!=0)busy=1;end
 for(genvar b=0;b<8;b++)begin:bank_number
  wire[4*280-1:0]requests;wire[23:0]credits,done;
  for(genvar o=0;o<4;o++)assign requests[o*280+:280]=legacy_q[(o*8+b)*280+:280];
  for(genvar s=0;s<4;s++)begin:slice
   ot_hgi_sv_native_write_owned_bank #(.SID(s),.BANK(b),.SLOTS(LEGACY_SLOTS),.MUT(MUT))u_router(
    .clk(clocks[s*8+b]),.rst_n(rst_n),.legacy_q(requests),.granted(wgrant[s]),
    .wq(native_wq[(s*8+b)*281+:281]),.wq_cr(native_credit[s*8+b]),.wq_done(native_done[s*8+b]),
    .routed_credit(credit_events[(s*8+b)*6+:6]),.routed_done(done_events[(s*8+b)*6+:6]),.drained(bank_idle[s*8+b]),.fault(fault[s*8+b]));
   assign credits[s*6+:6]=credit_events[(s*8+b)*6+:6];assign done[s*6+:6]=done_events[(s*8+b)*6+:6];
  end
  for(genvar o=0;o<4;o++)begin:old_lane
   ot_hgi_sv_native_write_owned_return #(.OWNER(o),.BANK(b),.SLOTS(LEGACY_SLOTS),.MUT(MUT))u_return(
    .clk(clocks[32+o*8+b]),.rst_n(rst_n),.routed_credit(credits),.routed_done(done),
    .legacy_credit(legacy_credit[o*8+b]),.legacy_done(legacy_done[o*8+b]),.drained(return_idle[o*8+b]),.fault(fault[32+o*8+b]));
  end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  sf<=0;for(integer l=0;l<32;l++)begin pending[l]<=0;pending_n[l]<='1;commits[l]<=0;commits_n[l]<='1;end
 end else for(integer l=0;l<32;l++)begin:ledger
  reg[TW+1:0]np;reg[32:0]nd;
  np={1'b0,pending[l]}+legacy_q[l*280+279]-legacy_credit[l];
  nd={1'b0,commits[l]}+legacy_q[l*280+279]-legacy_done[l];
  if(pending[l]!=~pending_n[l]||commits[l]!=~commits_n[l]||np>LEGACY_SLOTS||nd>32'(32*LEGACY_SLOTS)||(legacy_q[l*280+279]&&legacy_q[l*280+264+:5]!=5'(l)))sf<=1;
  pending[l]<=np[TW:0];pending_n[l]<=~np[TW:0];commits[l]<=nd[31:0];commits_n[l]<=~nd[31:0];
 end
 assign fault[64]=sf;
 wire idle=!busy&&(&bank_idle)&&(&return_idle)&&!legacy_q[8960]&&!(|fault);
 assign wreq={4{legacy_q[8960]||busy||!(&bank_idle)||!(&return_idle)}};
 assign drained={4{idle}};assign released=drained&wack&~wgrant;
 assign legacy_grant=(&wgrant)&&!(|fault)&&(|wreq);
endmodule
`default_nettype wire
