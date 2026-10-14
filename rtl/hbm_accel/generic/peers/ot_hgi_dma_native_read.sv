`timescale 1ns/1ps
`default_nettype none
// One native bank, four legacy lanes b,b+8,b+16,b+24. The CLOSED KV
// issuer reserves at most two responses per legacy lane. Sector addresses
// retain their global meaning. Every replicated slice sees the same issuer
// pulses, so its seq_q ticket agrees even when consecutive requests change slice.
module ot_hgi_dma_native_read_bank #(
 parameter integer SID=0, BANK=0, NATIVE_CREDITS=10, MUT=0
)(
 input wire clk,rst_n,input wire [63:0] legacy_q,
 output reg [3:0] legacy_cr,
 output reg [16:0] rq,input wire rq_cr,input wire [256:0] rr,
 output reg [259:0] routed_return,output reg fault
);
 reg [63:0] pin_q; reg [3:0] pin_seq, seq_q;
 reg [256:0] pin_rr; reg pin_cr;
 reg [15:0] fifo[0:3][0:1]; // ticket + sector15
 reg [3:0] head,tail; reg [1:0] count[0:3];
 reg [2:0] route[0:7]; reg [2:0] rh,rt; reg [3:0] rn;
 reg [4:0] credits; reg [1:0] prio_q;
 reg pick_v; reg [1:0] pick;
 wire pop_return=pin_rr[256] && rn!=0;
 always @* begin
  pick_v=0;pick=0;
  for(integer k=3;k>=0;k=k-1) begin
   if(count[2'(prio_q+2'(k))]!=0) begin pick_v=1;pick=2'(prio_q+2'(k));end
  end
 end
 wire issue=pick_v && credits!=0 && rn<8 && !fault;
 always @(posedge clk) begin
  for(integer o=0;o<4;o=o+1)pin_q[o*16 +:15]<=legacy_q[o*16 +:15];
  pin_seq<=seq_q;pin_rr[255:0]<=rr[255:0];
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   pin_q[15]<=0;pin_q[31]<=0;pin_q[47]<=0;pin_q[63]<=0;
   pin_rr[256]<=0;pin_cr<=0;seq_q<=0;head<=0;tail<=0;
   legacy_cr<=0;rq[16]<=0;routed_return[259]<=0;fault<=0;
   rh<=0;rt<=0;rn<=0;credits<=5'(NATIVE_CREDITS);prio_q<=0;
   for(integer o=0;o<4;o=o+1)count[o]<=0;
  end else begin
   pin_rr[256]<=rr[256];pin_cr<=rq_cr;
   for(integer o=0;o<4;o=o+1)pin_q[o*16+15]<=legacy_q[o*16+15];
   for(integer o=0;o<4;o=o+1)
    if(legacy_q[o*16+15])seq_q[o]<=!seq_q[o];
   legacy_cr<=0;rq[16]<=issue;routed_return[259]<=pop_return;
   if(pin_rr[256] && rn==0)fault<=1;
   credits<=credits+5'(pin_cr)-5'(issue);
   if(pin_cr && credits==NATIVE_CREDITS && !issue)fault<=1;
   rn<=rn+4'(issue)-4'(pop_return);
   if(issue)begin
    rq[15:0]<={1'b0,fifo[pick][head[pick]][14:0]};
    route[rt]<={pick,fifo[pick][head[pick]][15]};rt<=rt+1'b1;
    prio_q<=pick+1'b1;
   end
   if(pop_return)begin
    routed_return[258:256]<=route[rh] ^ ((MUT==1)?3'b010:3'b000);
    routed_return[255:0]<=pin_rr[255:0];rh<=rh+1'b1;
   end
   for(integer o=0;o<4;o=o+1)begin:owners
    reg push,pop;
    push=pin_q[o*16+15] && pin_q[o*16+13 +:2]==2'(SID);
    pop=issue && pick==2'(o);
    if(push && pin_q[o*16 +:3]!=3'(BANK))fault<=1;
    if(push && count[o]==2 && !pop)fault<=1;
    else begin
     count[o]<=count[o]+2'(push)-2'(pop);
     if(push)begin fifo[o][tail[o]]<={pin_seq[o],pin_q[o*16 +:15]};tail[o]<=!tail[o];legacy_cr[o]<=1;end
     if(pop)head[o]<=!head[o];
    end
   end
  end
 end
endmodule

// One bank number joins returns from its four native slices. A ticket is local
// protocol state, never a VM data or packet-tag bit. Two distinct requests may
// return on the same edge from different slices; both land before ordered drain.
module ot_hgi_dma_native_read_join #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [1039:0] routed_return,
 input wire [15:0] request_credit,
 output reg [1027:0] legacy_return,output reg [3:0] legacy_credit,
 output reg fault
);
 reg [1039:0] pin_return;reg [15:0] pin_credit;
 reg [255:0] data[0:3][0:1];reg [1:0] valid[0:3];reg [3:0] expected;
 always @(posedge clk)begin
  for(integer s=0;s<4;s=s+1)pin_return[s*260 +:259]<=routed_return[s*260 +:259];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   for(integer s=0;s<4;s=s+1)pin_return[s*260+259]<=0;
   pin_credit<=0;legacy_credit<=0;expected<=0;fault<=0;
   for(integer o=0;o<4;o=o+1)begin valid[o]<=0;legacy_return[o*257+256]<=0;end
  end else begin
   pin_credit<=request_credit;
   for(integer s=0;s<4;s=s+1)pin_return[s*260+259]<=routed_return[s*260+259];
   for(integer o=0;o<4;o=o+1)begin:owners
    reg [1:0] incoming;reg [1:0] next_valid;reg pop;
    incoming=0;pop=valid[o][expected[o]];
    legacy_return[o*257+256]<=pop;
    if(pop)begin legacy_return[o*257 +:256]<=data[o][expected[o]];expected[o]<=!expected[o];end
    next_valid=valid[o];if(pop)next_valid[expected[o]]=0;
    legacy_credit[o]<=pin_credit[o]|pin_credit[4+o]|pin_credit[8+o]|pin_credit[12+o];
    for(integer s=0;s<4;s=s+1)begin:sources
     reg [259:0] r;reg ticket;r=pin_return[s*260 +:260];ticket=r[256] ^ (MUT==2);
     if(r[259] && r[258:257]==2'(o))begin
      if(next_valid[ticket]||incoming[ticket])fault<=1;
      else begin data[o][ticket]<=r[255:0];next_valid[ticket]=1;incoming[ticket]=1;end
     end
    end
    valid[o]<=next_valid;
   end
  end
 end
endmodule
`default_nettype wire

`default_nettype none
// Wires-only native fabric. Thirty-two bank routers and eight return joins each
// have a real independent compensated clock entry. Shared clock is simulation only.
module ot_hgi_dma_native_read_fabric #(parameter integer HARD_CLOCKS=0,MUT=0)(
 input wire clk,rst_n,input wire [39:0] leaf_clk,
 input wire [512:0] legacy_q,output wire [8256:0] legacy_r,
 output wire [543:0] native_rq,input wire [31:0] native_cr,
 input wire [8223:0] native_rr,output wire [39:0] fault
);
 wire [39:0] clocks=HARD_CLOCKS!=0?leaf_clk:{40{clk}};
 wire [32*260-1:0] bank_return;wire [127:0] request_credit;
 for(genvar b=0;b<8;b=b+1)begin:bank_number
  wire [63:0] requests;wire [1039:0] returns;wire [15:0] credits;
  wire [1027:0] joined;wire [3:0] joined_credit;
  for(genvar o=0;o<4;o=o+1)begin:legacy_lane
   assign requests[o*16 +:16]=legacy_q[(o*8+b)*16 +:16];
   assign legacy_r[(o*8+b)*257 +:257]=joined[o*257 +:257];
   assign legacy_r[8224+o*8+b]=joined_credit[o];
  end
  for(genvar s=0;s<4;s=s+1)begin:slice
   ot_hgi_dma_native_read_bank #(.SID(s),.BANK(b),.MUT(MUT)) u_bank(
    .clk(clocks[s*8+b]),.rst_n(rst_n),.legacy_q(requests),
    .legacy_cr(request_credit[(s*8+b)*4 +:4]),
    .rq(native_rq[(s*8+b)*17 +:17]),.rq_cr(native_cr[s*8+b]),
    .rr(native_rr[(s*8+b)*257 +:257]),
    .routed_return(bank_return[(s*8+b)*260 +:260]),.fault(fault[s*8+b]));
   assign returns[s*260 +:260]=bank_return[(s*8+b)*260 +:260];
   assign credits[s*4 +:4]=request_credit[(s*8+b)*4 +:4];
  end
  ot_hgi_dma_native_read_join #(.MUT(MUT)) u_join(
   .clk(clocks[32+b]),.rst_n(rst_n),.routed_return(returns),.request_credit(credits),
   .legacy_return(joined),.legacy_credit(joined_credit),.fault(fault[32+b]));
 end
 // Dedicated native DMA read group: no legacy group arbitration is present.
 // This constant permission is valid only with the allocated native RG kept
 // exclusive for the complete transaction and all response/credit drain.
 assign legacy_r[8256]=1'b1;
endmodule
`default_nettype wire
