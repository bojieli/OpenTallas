`timescale 1ns/1ps
// DIAGNOSTIC ONLY: credit-based servicing is not a production static schedule.
// Owner 2026-10-14 requires compiler-known issue/response slots with no credits,
// back-pressure or completion rescheduling. This module measures correctness and
// cost; a production master must use the fixed service contract instead.
// Bounded, ordered stream-domain adapter for the VM's existing ctrl row ports.
// rq_credit/wq_credit are pulses, not ready levels: one initial token per slot,
// returned when its buffered transaction retires. Registered die wires may delay
// them freely. Request pulses spend tokens; sending without a token faults.
// All slots accepted on one clock retain slot order (reads, then writes). Later
// batches cannot overtake an earlier batch even when some slots return sooner.
// Masked writes are atomic read/merge/write against other traffic through this
// adapter. Other VM producers must target disjoint live regions, as required by
// the row-completion contract. This is a functioning bandwidth baseline; its
// measured production cost determines whether additional row ports are needed.
module dsfd_vm_clients #(parameter integer NR=18, NW=24, WCOMMIT=0)(
 input wire ck, rst_n,
 input wire [NR-1:0] rq_v, input wire [NR*14-1:0] rq_row,
 output reg [NR-1:0] rq_credit, output reg [NR-1:0] rs_v,
 output reg [NR*512-1:0] rs_d,
 input wire [NW-1:0] wq_v, input wire [NW*14-1:0] wq_row,
 input wire [NW*16-1:0] wq_mask, input wire [NW*512-1:0] wq_data,
 output reg [NW-1:0] wq_credit,
 input wire v_ready, output reg vwe, output reg [13:0] vwa,
 output reg [511:0] vwd, output reg [15:0] vwm, output reg [7:0] vwt,
 input wire vwv, input wire [7:0] vack_tag, input wire [15:0] vack_mask,
 output reg vre, output reg [13:0] vra,
 input wire vrv, input wire [511:0] vrq, output reg fault
);
 localparam integer N=NR+NW;
 reg [N-1:0] busy, issued;
 reg [5:0] ret_slot[0:31]; reg [4:0] ret_head, ret_tail; reg [5:0] ret_n;
 reg [13:0] row [0:N-1]; reg [15:0] mask [0:N-1];
 reg [511:0] data [0:N-1]; reg [31:0] age [0:N-1];
 reg [31:0] next_age;
 reg online; reg [2:0] reset_wait;
 reg [1:0] st; // 0 select, 1 wait read, 2 merged write
 integer active;
 reg [511:0] merged;
 integer pick, i; reg found; reg [31:0] oldest;
 always @* begin
  found=0; pick=0; oldest=32'hffffffff;
  for (i=0;i<N;i=i+1) if (busy[i] && !issued[i] && (!found || age[i]<oldest)) begin
   found=1; pick=i; oldest=age[i];
  end
 end
 always @(posedge ck or negedge rst_n) begin : run
  integer k,w; reg [31:0] a; reg ret_push, ret_pop;
  if (!rst_n) begin
   busy<=0; issued<=0; ret_head<=0; ret_tail<=0; ret_n<=0; next_age<=0; online<=0; reset_wait<=0; st<=0;
   rq_credit<=0; wq_credit<=0; rs_v<=0; vwe<=0; vre<=0; fault<=0;
  end else begin
   rq_credit<=0; wq_credit<=0; rs_v<=0; vwe<=0; vre<=0; ret_push=0; ret_pop=0;
   if (!online) begin
    if (reset_wait==7 && v_ready) begin online<=1; rq_credit<={NR{1'b1}}; wq_credit<={NW{1'b1}}; end
    else if (reset_wait!=7) reset_wait<=reset_wait+1'b1;
   end else begin
    a=next_age;
    for (k=0;k<NR;k=k+1) if (rq_v[k]) begin
     if (busy[k]) fault<=1;
     else begin busy[k]<=1; issued[k]<=0; row[k]<=rq_row[14*k+:14]; age[k]<=a; a=a+1; end
    end
    for (k=0;k<NW;k=k+1) if (wq_v[k]) begin
     if (busy[NR+k]) fault<=1;
     else begin busy[NR+k]<=1; issued[NR+k]<=0; row[NR+k]<=wq_row[14*k+:14];
      mask[NR+k]<=wq_mask[16*k+:16]; data[NR+k]<=wq_data[512*k+:512];
      age[NR+k]<=a; a=a+1;
     end
    end
    next_age<=a;
    if(WCOMMIT && vwv)begin
     if(vack_tag>=NW || !busy[NR+vack_tag] || !issued[NR+vack_tag])fault<=1;
     else begin
      if(vack_mask!=mask[NR+vack_tag])fault<=1;
      busy[NR+vack_tag]<=0;issued[NR+vack_tag]<=0;wq_credit[vack_tag]<=1;
     end
    end
    if (st==0 && found && v_ready && !vwe && !vre) begin
     active<=pick;
     if (pick<NR && ret_n<32) begin
      vre<=1; vra<=row[pick]; issued[pick]<=1;
      ret_slot[ret_tail]<=pick; ret_tail<=ret_tail+1'b1; ret_push=1;
     end else if (!WCOMMIT && pick>=NR && mask[pick]!=16'hffff && ret_n==0) begin
      vre<=1; vra<=row[pick]; st<=1;
     end
     else if (pick>=NR && (WCOMMIT || mask[pick]==16'hffff)) begin
      vwe<=1; vwa<=row[pick]; vwd<=data[pick]; vwm<=mask[pick]; vwt<=pick-NR;
      if(WCOMMIT)issued[pick]<=1;else begin busy[pick]<=0;wq_credit[pick-NR]<=1;end
     end
    end
    if (vrv) begin
     if (st==1) begin
      `ifdef OT_VMCLIENT_MUT_MASK
      merged<=data[active]; // negative control: masked-off words are overwritten
`else
      for (w=0;w<16;w=w+1) merged[32*w+:32]<=mask[active][w] ? data[active][32*w+:32] : vrq[32*w+:32];
`endif
      st<=2;
     end else if (ret_n!=0) begin
      rs_v[ret_slot[ret_head]]<=1; rs_d[512*ret_slot[ret_head]+:512]<=vrq;
      busy[ret_slot[ret_head]]<=0; issued[ret_slot[ret_head]]<=0; rq_credit[ret_slot[ret_head]]<=1;
      ret_head<=ret_head+1'b1; ret_pop=1;
     end else fault<=1;
    end
    ret_n<=ret_n+(ret_push?1:0)-(ret_pop?1:0);
    if (st==2 && v_ready && !vwe && !vre) begin
     vwe<=1; vwa<=row[active]; vwd<=merged;
     busy[active]<=0; wq_credit[active-NR]<=1; st<=0;
    end
   end
  end
 end
endmodule
