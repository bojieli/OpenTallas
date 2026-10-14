`timescale 1ns/1ps
// Stage-bound HC transfer control. This is a candidate component, not a
// replacement for missing native120 stage programs. store_begin must be the
// accepted H_STORE descriptor; queued hop descriptor must precede hop_go.
// Writes are observed at the VM commit boundary, not at HC issue. All masks
// must cover the full row. Reads are held until their particular row commits,
// so cut-through remains correct across an arbitrarily stalled producer.
// The external VM returns ordered responses and must use return-valid mode.
module ot_s81_htransfer #(
 parameter integer XW=640,VWA=14,TXB=2048,S_WR=8,DEPTH=4,HWM=8,MUT=0,
 parameter integer CW=$clog2(XW+1),QB=$clog2(DEPTH)
)(
 input wire clk,rst_n,
 input wire store_begin,store_slot,
 input wire [S_WR-1:0] wr_v,
 input wire [S_WR*VWA-1:0] wr_a,
 input wire [S_WR*16-1:0] wr_mask,
 output reg hop_go,
 input wire hop_re,
 input wire [VWA-1:0] hop_ra,
 output reg vm_re,
 output reg [VWA-1:0] vm_ra,
 output reg fault,
 output reg [3:0] fault_code,
 output reg [2*CW-1:0] committed_rows
);
 reg [XW-1:0] ready[0:1];
 reg [1:0] active,launched;
 reg [VWA-1:0] queue[0:DEPTH-1];
 reg [QB-1:0] rp,wp;
 reg [QB:0] n;
 reg [QB:0] queued_h[0:1];
 integer i,s,row,c0,c1;
 reg [XW-1:0] next_ready[0:1];
 reg [VWA-1:0] a;
 wire [VWA-1:0] head=queue[rp];
 wire is_h=head>=TXB && head<TXB+2*XW;
 wire hs=(head-TXB)>=XW;
 wire [VWA-1:0] hr=head-TXB-(hs ? XW : 0);
 wire push_ok=hop_re && (n<DEPTH || pop);
 wire push_h=hop_ra>=TXB && hop_ra<TXB+2*XW;
 wire push_slot=(hop_ra-TXB)>=XW;
 wire pop=n!=0 && (!is_h || MUT==1 || ready[hs][hr]);
 initial begin
   if (HWM<1 || HWM>XW || DEPTH<2 || (1<<QB)!=DEPTH)
     $fatal(1,"invalid transfer parameters");
 end
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin
   ready[0]<=0;ready[1]<=0;active<=0;launched<=0;
   hop_go<=0;vm_re<=0;vm_ra<=0;fault<=0;fault_code<=0;
   rp<=0;wp<=0;n<=0;committed_rows<=0;queued_h[0]<=0;queued_h[1]<=0;
 end else begin
   hop_go<=0;vm_re<=pop;
   if(pop) begin vm_ra<=head;rp<=rp+1'b1;end
   if(hop_re) begin
     if(n==DEPTH && !pop) begin fault<=1;fault_code<=1;end
     else begin queue[wp]<=hop_ra;wp<=wp+1'b1;end
   end
   case({hop_re && (n<DEPTH || pop),pop})
    2'b10:n<=n+1'b1;2'b01:n<=n-1'b1;default:;
   endcase
   for(integer qs=0;qs<2;qs=qs+1)begin
     case({push_ok && push_h && push_slot==qs,pop && is_h && hs==qs})
       2'b10:queued_h[qs]<=queued_h[qs]+1'b1;
       2'b01:queued_h[qs]<=queued_h[qs]-1'b1;
       default:;
     endcase
   end
   next_ready[0]=ready[0];next_ready[1]=ready[1];
   c0=committed_rows[0+:CW];c1=committed_rows[CW+:CW];
   if(store_begin) begin
     next_ready[store_slot]=0;active[store_slot]<=1;
     if(store_slot) c1=0;else c0=0;
     // A new store may overlap queued reads of the OTHER job slot. Only
     // reusing the slot whose old reads remain queued violates ownership.
     if(queued_h[store_slot]!=0 || (push_ok && push_h && push_slot==store_slot))begin
       fault<=1;fault_code<=4;
     end
     launched[store_slot]<=0;
   end
   for(i=0;i<S_WR;i=i+1) if(wr_v[i]) begin
     a=wr_a[i*VWA+:VWA];
     if(a>=TXB && a<TXB+2*XW) begin
       s=(a-TXB)>=XW;row=a-TXB-s*XW;
       if(!(active[s] || (store_begin && store_slot==s)) ||
          wr_mask[i*16+:16]!=16'hffff || next_ready[s][row]) begin
          fault<=1;fault_code<=2;
       end else begin next_ready[s][row]=1;
          if(s) c1=c1+1;else c0=c0+1;end
     end
   end
   ready[0]<=next_ready[0];ready[1]<=next_ready[1];
   committed_rows<={CW'(c1),CW'(c0)};
   // A single hop engine accepts one ordered stream. The stage lowering must
   // order the store slots; simultaneous thresholds are an explicit fault.
   if(!store_begin) begin
     if(active[0] && !launched[0] && c0>=HWM) begin
       hop_go<=1;launched[0]<=1;
     end
     if(active[1] && !launched[1] && c1>=HWM) begin
       hop_go<=1;launched[1]<=1;
       if(active[0] && !launched[0] && c0>=HWM) begin fault<=1;fault_code<=3;end
     end
   end
 end end
endmodule
